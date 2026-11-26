---
title: "Node.js Database Migrations in 2026: Umzug vs node-pg-migrate vs Prisma Migrate"
date: "2026-11-27"
tags: ["nodejs", "database", "postgresql", "migrations", "prisma", "devops"]
draft: false
cover: "/img/screenshots/prisma-migrate-cover.jpg"
description: "Umzug vs node-pg-migrate vs Prisma Migrate compared for 2026: SQL vs DSL trade-offs, transactional DDL, zero-downtime patterns, baselining and the checksum traps that break deploys."
---

Every team eventually ships a migration that takes forty minutes and locks a table at peak traffic. The tool is rarely the root cause — the workflow around it is. But the tool decides what the workflow *can* look like: whether you can review plain SQL, whether a failed migration rolls back cleanly, and whether a hotfix at 2am is one command or an archaeology project.

Three Node.js options dominate in 2026: **Umzug (2,224 stars)**, **node-pg-migrate (1,496 stars)** and **Prisma Migrate**, which ships with Prisma (47,775 stars). They are not interchangeable, and the differences show up in production, not in the README.

## TL;DR: The 60-Second Verdict

- **Already using Prisma ORM** → Prisma Migrate. Fighting it means maintaining two schema sources of truth.
- **PostgreSQL shop that writes real SQL** → node-pg-migrate. Plain `.sql` and JS migrations, transactional by default, no DSL between you and the planner.
- **Framework-agnostic runner over existing migration files, or Sequelize** → Umzug. It orchestrates; it does not generate.
- **Knex query builder in the stack** → use Knex's own migration runner; adding a fourth tool is how you get three sources of truth.

If you want one sentence: **node-pg-migrate gives you the most control per unit of setup, Prisma Migrate gives you the least control but the tightest type safety, and Umzug is a scheduler rather than a migration system.**

## Comparison Table: What Each Tool Actually Does

| Dimension | node-pg-migrate | Umzug | Prisma Migrate |
|---|---|---|---|
| GitHub stars | 1,496 | 2,224 | 47,775 (Prisma) |
| License | MIT | MIT | Apache-2.0 |
| Last push | 2026-11-26 | 2026-11-25 | 2026-11-26 |
| Migration format | SQL or JS/TS API | Any files you provide | Generated SQL from schema |
| Primary database | PostgreSQL | Any (driver-agnostic) | PostgreSQL, MySQL, SQLite, SQL Server, CockroachDB |
| Schema source of truth | Migration files | Migration files | `schema.prisma` |
| Generates migrations | Yes (`create`) | No | Yes (`migrate dev`) |
| `down` migrations | Yes, handwritten | Yes, if you define them | No (rollback = new migration) |
| Transactional by default | Yes | Depends on your runner | Per-migration on Postgres |
| State tracking | `pgmigrations` table | Your storage adapter | `_prisma_migrations` table |
| Programmatic API | Yes | Yes (its whole point) | Limited |
| CLI | `node-pg-migrate` | None (you write a script) | `prisma migrate` |
| Learning curve | Low | Medium | Medium |

## Decision Matrix: Ten Seconds to a Choice

| Your situation | Recommended | Why |
|---|---|---|
| Postgres + Prisma Client in the app | Prisma Migrate | One schema, generated types stay in sync |
| Postgres, hand-written SQL, strong DBAs | node-pg-migrate | Reviewable SQL, no abstraction layer |
| Sequelize models already in place | Umzug | Purpose-built for Sequelize storage |
| Multiple databases with one workflow | Umzug | Driver-agnostic orchestration |
| Need rollback scripts for compliance | node-pg-migrate | Explicit `down` blocks |
| Zero-downtime deploys on hot tables | node-pg-migrate | Full control of transaction boundaries |
| Monorepo with per-service schemas | Prisma Migrate | Each service owns its `schema.prisma` |
| Migrations from a legacy system, mixed formats | Umzug | Runs whatever files you already have |

## node-pg-migrate: SQL First, No DSL in the Way

This is the tool to pick when the database is the product, not an implementation detail. Migrations are files you can read in a pull request, and the JS API is a thin layer over DDL rather than a schema language.

```bash
npm install -D node-pg-migrate
export DATABASE_URL="postgres://app:secret@localhost:5432/app"

npx node-pg-migrate create add-orders \
  --migration-file-language sql

npx node-pg-migrate up        # apply pending
npx node-pg-migrate down 1    # roll back the last one
npx node-pg-migrate up --dry-run
```

The generated JS form is usually more useful than raw SQL because it stays readable across dialects of intent:

```js
// migrations/1732800000000_add-orders.js
exports.up = (pgm) => {
  pgm.createTable("orders", {
    id: "id",
    customer_id: { type: "integer", notNull: true, references: "customers", onDelete: "CASCADE" },
    total_cents: { type: "bigint", notNull: true, default: 0 },
    status: { type: "text", notNull: true, default: "pending" },
    created_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
  });

  pgm.createIndex("orders", ["customer_id", "created_at"]);
  pgm.addConstraint("orders", "orders_total_positive", { check: "total_cents >= 0" });
};

exports.down = (pgm) => {
  pgm.dropTable("orders");
};
```

For index creation on a live table, escape the transaction — `CREATE INDEX CONCURRENTLY` cannot run inside one:

```js
// migrations/1732800100000_orders-status-index.js
exports.up = (pgm) => {
  pgm.noTransaction();
  pgm.sql("CREATE INDEX CONCURRENTLY IF NOT EXISTS orders_status_idx ON orders (status)");
};

exports.down = (pgm) => {
  pgm.noTransaction();
  pgm.sql("DROP INDEX CONCURRENTLY IF EXISTS orders_status_idx");
};
```

**Where node-pg-migrate hurts:** PostgreSQL only. If you need MySQL or SQL Server in the same repo, this is the wrong tool, and the JS API still cannot express everything — you will drop into `pgm.sql()` regularly.

## Umzug: An Orchestrator, Not a Generator

Umzug does one thing: it runs an ordered list of migration files, records what ran, and gives you a programmatic API. It does not create files, does not know your SQL dialect, and has no CLI. That is a feature if you want migrations embedded in an existing deployment script.

```ts
// migrate.ts
import { Umzug, SequelizeStorage } from "umzug";
import { Sequelize } from "sequelize";

const sequelize = new Sequelize(process.env.DATABASE_URL!, { logging: false });

export const umzug = new Umzug({
  migrations: {
    glob: ["migrations/*.{js,ts}", { cwd: __dirname }],
    resolve: ({ name, path, context }) => {
      const mod = require(path!);
      return {
        name,
        up: async () => mod.up({ context }),
        down: async () => mod.down({ context }),
      };
    },
  },
  context: sequelize.getQueryInterface(),
  storage: new SequelizeStorage({ sequelize }),
  logger: console,
});

if (require.main === module) {
  const cmd = process.argv[2] ?? "up";
  umzug[cmd as "up" | "down"]().then(() => sequelize.close());
}
```

Run it as part of the release, not as a manual step:

```bash
node dist/migrate.js up
node dist/migrate.js down --to 1732800000000-add-orders.js
node dist/migrate.js pending    # print what would run
```

**Where Umzug hurts:** it will happily run a destructive migration with no guard rails, because it has no opinion about SQL. Also, `SequelizeStorage` ties you to Sequelize even if your app no longer uses it — there is a `JSONStorage` for file-based tracking, but that is not safe for multiple replicas.

## Prisma Migrate: Schema-Driven, Type-Safe, Opinionated

![Prisma official project mark](/img/screenshots/prisma-migrate-cover.jpg "Prisma - schema-first migration workflow with generated client types")

Prisma Migrate inverts the workflow: you edit `schema.prisma`, and the tool computes the SQL. The upside is that your types and your tables cannot drift. The downside is that you stop reading your own DDL.

```prisma
// schema.prisma
model Order {
  id         Int      @id @default(autoincrement())
  customerId Int
  totalCents BigInt   @default(0)
  status     String   @default("pending")
  createdAt  DateTime @default(now()) @map("created_at")

  customer Customer @relation(fields: [customerId], references: [id], onDelete: Cascade)
  @@index([customerId, createdAt])
  @@map("orders")
}
```

```bash
npx prisma migrate dev --name add_orders   # dev: generate + apply + regenerate client
npx prisma migrate deploy                  # CI/prod: apply pending only
npx prisma migrate status                  # what is applied vs pending
npx prisma migrate resolve --applied 20261127093000_add_orders  # mark as applied
```

Two operational facts that catch teams out:

1. **`migrate dev` requires a shadow database.** Prisma creates and drops a temporary database to detect drift. Your production role usually cannot do that, which is why `deploy` exists and why CI roles need `CREATEDB` on the dev instance.
2. **There is no `down`.** Rollback means writing a new migration that reverses the change. That is defensible (forward-only is how most mature shops operate) but it must be a conscious decision, because it changes your incident runbook.

**Where Prisma Migrate hurts:** complex DDL — partial indexes, expression indexes, triggers, `CONCURRENTLY` — often requires editing the generated SQL by hand into a custom migration (`prisma migrate dev --create-only`). At that point you are maintaining two mental models.

## Zero-Downtime Patterns That Apply to All Three

Tool choice does not save you from table locks. These rules do:

1. **Never add a `NOT NULL` column with a default on a large table in one step.** Add it nullable, backfill in batches, then add the constraint with `NOT VALID` and validate separately.
2. **Rename in three deploys.** Add the new column, dual-write, backfill, switch reads, then drop the old one. A single `ALTER TABLE ... RENAME` breaks every running instance of the previous release.
3. **Set `lock_timeout` on migration sessions.** A migration waiting behind a long query will block every query behind it. `SET lock_timeout = '3s';` turns a stall into a fast, retryable failure.
4. **Build indexes concurrently, outside transactions.** This is the most common reason a migration "hangs forever" in production and runs instantly on staging.
5. **Batch backfills with a `LIMIT` loop and commit between batches.** One `UPDATE` over 10 million rows generates a WAL flood and holds row locks for the entire duration.
6. **Baseline, do not replay.** For an existing database, mark the current schema as the starting point (`node-pg-migrate up` with a pre-created baseline, `prisma migrate resolve --applied`, or an Umzug storage row) instead of re-running historical migrations.

For the broader landscape of migration tooling in other ecosystems, see our [Go migration tools comparison](../2026-05-14-self-hosted-lightweight-database-migrations-goose-dbmate-atlas-guide/) and the [Rust migrations deep dive](../2026-11-15-rust-database-migrations-refinery-sqlx-diesel/). Migrations are not backups — if you need point-in-time recovery when a migration goes wrong, our [PostgreSQL backup comparison](../2026-10-27-databasus-vs-pgbackrest-vs-pg-probackup-postgresql-backup-2026/) covers the options.

## FAQ

### Does node-pg-migrate work with MySQL?

No. It is PostgreSQL-specific by design, which is why it can expose PostgreSQL features like `CONCURRENTLY` and check constraints directly. For multi-database support, use Umzug or a driver-aware tool.

### Can Prisma Migrate roll back a migration?

Not directly. Prisma is forward-only: you write a new migration that reverses the previous one. `migrate resolve` only marks migrations as applied or rolled back in the tracking table, it does not undo schema changes.

### How does Umzug decide which migrations to run?

It compares the filenames (sorted lexicographically) against the rows in its storage table. Name files with a sortable timestamp or sequential prefix — `20261127_add-orders.js` — or you will get an unpredictable order.

### What happens if two deploy replicas run migrations at once?

You get a race: both read the same pending list and both try to apply. node-pg-migrate and Prisma take advisory locks, so the second waits. Umzug does not lock by default — run migrations as a separate job before scaling up, not inside every container's entrypoint.

### Is it safe to run migrations during business hours?

Yes, if the migration is written to be online: nullable columns, concurrent index builds, batched backfills, short `lock_timeout`. Destructive changes and type rewrites on large tables are the ones to schedule.

### Do I still need a DBA if I use Prisma?

For small schemas, no. For tables above a few million rows, yes — generated SQL does not know your traffic pattern, and the difference between a lock-free migration and a service outage is often one hand-written statement.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js Database Migrations in 2026: Umzug vs node-pg-migrate vs Prisma Migrate",
  "description": "Umzug, node-pg-migrate and Prisma Migrate compared: SQL vs schema-driven workflows, transactional DDL, zero-downtime patterns and baselining.",
  "datePublished": "2026-11-27",
  "dateModified": "2026-11-27",
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
