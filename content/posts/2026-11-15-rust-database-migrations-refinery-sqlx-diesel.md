---
title: "Refinery vs SQLx vs Diesel Migrations in 2026: Which Rust Migration Tool Actually Ships?"
date: "2026-11-15"
draft: false
tags: ["rust", "database", "migrations", "sqlx", "diesel", "devops"]
description: "A hands-on comparison of Rust's three migration systems — Refinery, SQLx CLI and Diesel CLI — with real commands, checksum behavior, async support and production pitfalls."
cover: "/img/screenshots/rust-migrations-cover.jpg"
---

Your Rust service boots, connects to Postgres, and immediately panics because the `users` table is missing `deleted_at`. Nobody remembers which migration created it, `cargo run` worked on the developer's laptop, and production is now serving 500s. Schema drift is the least glamorous failure mode in backend engineering, and it is exactly what a migration tool exists to prevent.

Rust has three serious answers to this problem, and they disagree about almost everything: **Refinery** treats migrations as embeddable code that ships inside your binary, **SQLx CLI** treats them as timestamped SQL files checked against a live database, and **Diesel CLI** treats them as bidirectional `up.sql`/`down.sql` pairs tied to a schema-printing workflow. Picking the wrong one costs you weeks of CI plumbing later.

## TL;DR: Quick Verdict

**Pick Refinery if migrations must run from inside your application binary** — it embeds SQL or Rust migrations at compile time, works with any driver (sqlx, tokio-postgres, rusqlite, deadpool, bb8), and needs no external CLI in production. **Pick SQLx CLI if you already use `sqlx::query!` compile-time checked queries** — its checksum-and-history model is the most predictable, and `sqlx migrate run` is a one-liner in CI. **Pick Diesel CLI if you use Diesel as your ORM** — `diesel migration generate` plus `diesel print-schema` keeps Rust structs and SQL schema in lockstep, and it is the only one of the three with first-class down migrations by default. Teams that just want "apply pending SQL at deploy time" and hate magic should take SQLx. Teams that deploy single static binaries to environments without `psql` installed should take Refinery.

## Head-to-Head Comparison (November 2026)

| Dimension | Refinery | SQLx CLI | Diesel CLI |
|---|---|---|---|
| GitHub stars | **1,715** | **17,669** | **14,251** |
| Latest release | v0.10.0 | v0.9.0 | v2.4.0 |
| Last commit | 2026-11-01 | 2026-11-10 | 2026-11-15 |
| License | MIT | Apache-2.0 | Apache-2.0 |
| Migration format | SQL or Rust files | Timestamped `.sql` files | `up.sql` + `down.sql` pairs |
| Runs inside app binary | **Yes** (`embed_migrations!`) | No (CLI only) | Yes (`diesel_migrations`) |
| CLI required in prod | No | Yes | Optional |
| Async runner | **Yes** (`run_async`) | Yes (CLI is sync) | Yes (`run_pending_migrations`) |
| Checksum verification | No | **Yes** (SHA-384 log table) | No |
| Reversible migrations | Only via `U`/`V` naming tricks | Opt-in (`--reversible`) | **Yes, default** |
| Out-of-order execution | Yes (`U` prefix) | Yes (`--ignore-missing`/versioned) | No (strict order) |
| Driver support | sqlx, rusqlite, postgres, mysql, tokio-postgres | Postgres, MySQL, SQLite | Postgres, MySQL, SQLite |
| Schema printing | No | No | **Yes** (`print-schema`) |
| Compile-time query checks | No | **Yes** (`query!` macros) | Partial (`dsl`/`sql_query`) |

Star counts and release data pulled from the GitHub API on 2026-11-15.

## Decision Matrix: Which One Fits Your Stack?

| Your situation | Recommended tool | Why |
|---|---|---|
| Static binary deployed to a minimal container, no `psql` | **Refinery** | Migrations are compiled in; a single `runner().run()` call at boot applies them |
| Already using `sqlx::query!` and `cargo sqlx prepare` | **SQLx CLI** | One toolchain, one `DATABASE_URL`, offline mode covered |
| Diesel ORM with generated schema | **Diesel CLI** | `print-schema` regenerates `schema.rs` after every migration |
| Multiple services sharing one database | **SQLx CLI** | Serialized history table + checksums catch concurrent edits |
| Need guaranteed rollback scripts | **Diesel CLI** | `down.sql` is mandatory, not an afterthought |
| Embedded/offline device or air-gapped deploy | **Refinery** | No network, no CLI, no `sqlx` binary to ship |
| Migrations authored by several people in parallel | **Refinery (U-prefix) or SQLx** | Both tolerate out-of-order arrivals; Diesel does not |

## Refinery: Migrations as Compiled Code

Refinery's core bet is that your schema history is part of your application, not part of your deployment scripts. The `embed_migrations!` macro reads a directory at compile time and generates a `runner()` you call with any connection.

```rust
use rusqlite::Connection;

mod embedded {
    use refinery::embed_migrations;
    embed_migrations!("./tests/sql_migrations");
}

fn main() {
    let mut conn = Connection::open_in_memory().unwrap();
    embedded::migrations::runner().run(&mut conn).unwrap();
}
```

For async pools — sqlx, deadpool, bb8 — the same runner has an `run_async` variant, which is where Refinery pulls ahead of the CLI-only tools in serverless and container-first setups:

```rust
let mut conn = pool.get().await?;
let client = conn.deref_mut().deref_mut();
let report = embedded::migrations::runner().run_async(client).await?;
```

The CLI is optional, but useful for generating and testing migrations outside the app:

```bash
cargo install refinery_cli
export DATABASE_URL="postgres://postgres:secret@localhost:5432/your-db"

# Apply everything in ./src, stopping at version 1
refinery migrate -e DATABASE_URL -p ./src -t 1

# Inspect state without applying
refinery migrate -e DATABASE_URL -p ./src -t 0
```

The naming convention matters more than most tutorials admit. `V1__init.sql`, `V2__add_users.sql` are **contiguous**: Refinery refuses to run a migration whose version is lower than the highest applied one. `U11__update_cars.sql` is **non-contiguous** and tolerates gaps, which is what you want when two engineers open PRs on the same afternoon. Refinery's own README explains the failure mode precisely: developer A's `U11` sits in review for a week while developer B's `U12` merges and deploys — with contiguous numbering, A's migration would never run again.

Refinery does **not** verify checksums. If someone edits an already-applied migration file, Refinery will happily keep the edited file and never notice the divergence. That is a real operational gap, and it is the main reason teams with many contributors choose SQLx instead.

## SQLx CLI: The Checksum-Guarded Standard

SQLx's migration system is deliberately boring: a `migrations/` directory, timestamped filenames, and a `_sqlx_migrations` table that stores a SHA-384 checksum of every applied file. If a checked-in migration changes after it has run somewhere, `sqlx migrate run` fails loudly instead of silently diverging — a property you only appreciate after your first production incident caused by a sneaky `ALTER TABLE` edit.

```bash
cargo install sqlx-cli --no-default-features --features rustls,postgres

# DATABASE_URL can live in .env in the working directory
sqlx database create

sqlx migrate add create_users_table
# => migrations/20261115120300_create_users_table.sql

sqlx migrate run      # apply everything pending
sqlx migrate info     # show applied / pending / missing
sqlx migrate revert   # roll back the last migration (if reversible)
```

A detail that trips up monorepos: `--source` lets you keep migrations outside the crate root, which is how you share one migration history between a workspace member and its integration tests.

```bash
sqlx migrate info --source ../relative/migrations
sqlx migrate run  --source ../relative/migrations
```

The trade-off is structural. SQLx migrations are **forward-only by default**; reversibility is opt-in via `sqlx migrate add --reversible <name>`, which generates `up`/`down` halves. Most teams never use it, writing a compensating forward migration instead — a discipline that matches how Postgres shops actually operate. You also need the `sqlx` binary in CI and in any deploy job that runs migrations, which is a real constraint when your runtime image is `FROM scratch`.

Where SQLx wins outright is coupling with compile-time verification: `sqlx::query!("SELECT id, email FROM users")` fails the build if the query no longer matches the live schema, and `cargo sqlx prepare` caches that metadata for offline CI builds. Refinery can apply the same schema but cannot check your queries against it.

## Diesel CLI: Bidirectional by Default, Schema-Aware

Diesel's model is the oldest of the three and the most opinionated: every migration is a directory containing `up.sql` and `down.sql`, applied in strict sequential order, with a `diesel print-schema` step regenerating Rust types afterwards.

```bash
cargo install diesel_cli --no-default-features --features "postgres sqlite"
diesel setup --database-url='postgres://localhost/my_db'
diesel migration generate create_users_table
```

That generates `migrations/{timestamp}_create_users_table/up.sql` and `down.sql`:

```sql
-- up.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    favorite_color VARCHAR
);
```

```sql
-- down.sql
DROP TABLE users;
```

```bash
diesel migration run     # apply pending
diesel migration redo    # down + up for the last migration
diesel migration list
diesel print-schema > src/schema.rs
```

`diesel migration redo` is genuinely useful during development: it exercises your `down.sql` every single time, which is the only reliable way to keep rollbacks honest. In SQLx and Refinery, rollback paths tend to rot because nothing forces you to test them.

Diesel also runs migrations from inside the application through the `diesel_migrations` crate, so you can combine "no CLI in production" with "Diesel ORM". The cost is coupling: strict ordering means a hotfix migration merged out of order will fail with `Migration ... was applied before ...`, and the fixes are unpleasant (renumber files, or manually insert rows into `__diesel_schema_migrations`). If your team merges frequently, this is the sharpest edge in the whole comparison.

## The Pitfalls Nobody Warns You About

**1. Checksum drift is silent in Refinery and Diesel.** Only SQLx stores hashes. If you edit an applied migration in Refinery or Diesel, every environment keeps whatever it originally ran. Rule: never edit an applied file — add a new one, in all three tools.

**2. Concurrent deploys need a lock.** Two pods booting simultaneously will both try to migrate. Postgres advisory locks are the portable answer: take `pg_advisory_lock(hashtext('migrations'))` before `migrate run` and release after. SQLx serializes inside its own transaction, but the leader-election problem still belongs to you — run migrations as a separate Kubernetes `Job` or an init container with `concurrencyPolicy`, never in every replica's entrypoint.

**3. Timestamp collisions are real.** Two branches creating `20261115120300_add_index.sql` will conflict at merge time. Prefer smaller, frequently merged migrations, and let Refinery's `U`-prefix handle the ordering.

**4. SQLite cannot drop columns cleanly.** All three tools will happily generate `ALTER TABLE ... DROP COLUMN`, and older SQLite builds reject it. On SQLite, do the table-rebuild dance (create new table, copy, drop, rename) inside one transaction.

**5. Compose-based migration jobs need health checks.** A very common pattern that breaks: the app container starts before Postgres accepts connections. Gate the migration job on `pg_isready` instead of sleeping.

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: app
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app"]
      interval: 3s
      retries: 20

  migrate:
    image: ghcr.io/your-org/api:latest
    command: ["./api", "--migrate-only"]
    environment:
      DATABASE_URL: postgres://postgres:secret@db:5432/app
    depends_on:
      db:
        condition: service_healthy
```

With Refinery, `--migrate-only` is trivial to implement: call `runner().run(&mut conn)`, log the applied versions from the returned `Report`, and exit. With SQLx you would run the CLI in a sidecar image instead, and with Diesel you would ship the `diesel` binary or use `diesel_migrations` in-process.

## FAQ

**Which Rust migration tool is fastest?**
All three are bound by the database, not the tool. Refinery has a small edge in cold-start environments because there is no CLI process to spawn, but the difference is milliseconds against migrations that often take seconds of DDL time.

**Can I use SQLx migrations without the SQLx query macros?**
Yes. `sqlx-cli` is a standalone binary; `sqlx migrate run` works with any driver, including Diesel-based projects that want checksum verification. Many teams use `sqlx-cli` purely as a migration runner while querying through another library.

**Does Refinery support down migrations?**
Not in the Diesel sense. Refinery applies migrations forward only; rollback is expressed as a new migration that reverses the previous change. This is intentional and matches how most production teams operate, but it means rollback scripts are never exercised automatically.

**How do I run migrations in Kubernetes without races?**
Run them in a dedicated `Job` (or a Helm pre-upgrade hook) with a Postgres advisory lock, and make the application pods depend on that Job's completion. Never put `migrate run` in a container entrypoint that every replica executes.

**Can I switch migration tools later?**
Practically, no — each tool keeps its own history table (`refinery_schema_history`, `_sqlx_migrations`, `__diesel_schema_migrations`). Migrating means baselining the new tool against the current schema and freezing the old history. Choose deliberately at project start; a rewrite at month eighteen is a week of careful work plus a maintenance window.

## Further Reading

If you are still choosing a database layer, our [Rust database library comparison](../2026-06-23-rust-database-libraries-diesel-seaorm-rusqlite/) covers Diesel, SeaORM and rusqlite in depth, and the [SQL query builder shootout](../2026-06-20-sql-query-builder-libraries-knex-jooq-diesel-squirrel/) explains why query builders and migration tools solve different problems. Teams running migrations across several languages will find the [lightweight migration tools guide](../2026-05-14-self-hosted-lightweight-database-migrations-goose-dbmate-atlas-guide/) — goose, dbmate and Atlas — a useful counterpoint to the Rust-native options here.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Refinery vs SQLx vs Diesel Migrations in 2026: Which Rust Migration Tool Actually Ships?",
  "description": "Hands-on comparison of Rust migration tools: Refinery embedded migrations, SQLx CLI checksum-verified migrations, and Diesel CLI bidirectional migrations, with real commands and production pitfalls.",
  "datePublished": "2026-11-15",
  "dateModified": "2026-11-15",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
