---
title: "OCaml Database Libraries in 2026: Caqti vs PostgreSQL-OCaml vs SQLite3 Compared"
date: "2026-09-21"
tags: ["ocaml", "databases", "postgresql", "sqlite", "library-comparison"]
draft: false
cover: "/img/screenshots/ocaml-data-cover.jpg"
description: "A practical comparison of the three maintained OCaml database libraries — Caqti, PostgreSQL-OCaml and SQLite3-OCaml — with real code, licensing and version constraints."
---

OCaml's database story is small, and that is exactly why so many teams pick the wrong layer and live with it for years. There are only three libraries worth considering in 2026, and they are not interchangeable: one is an abstraction that lets you swap PostgreSQL for SQLite without touching your code, and two are thin, faithful bindings straight to `libpq` and `libsqlite3`.

Worse, the most-recommended name on the internet — **PGX** — has been effectively dead since 2020. This guide covers the three libraries that are actually maintained, with real opam commands, real code, and the version constraints that will bite you during a build.

## TL;DR — Quick Verdict

- **Choose Caqti** for anything larger than a script. It gives you a uniform API over **MariaDB, PostgreSQL, and SQLite3** selected by a URI at runtime, with typed query parameters and Lwt, Async, or Eio connectors. LGPL-3.0 with a linking exception, 355 stars, and the most active of the three (last push 2026-08-26).
- **Choose PostgreSQL-OCaml** when you want the raw `libpq` surface: `COPY`, `LISTEN`/`NOTIFY`, prepared statements, and precise control over session behaviour. It is the thinnest possible layer over PostgreSQL, but note it requires **OCaml 5.00 or newer**.
- **Choose SQLite3-OCaml** for embedded databases and local-first tools. MIT licensed, 132 stars, and directly usable from OCaml 4.12 upward — the lowest-friction option if you are on an older compiler.

One-sentence summary: **Caqti is architecture, PostgreSQL-OCaml is control, SQLite3-OCaml is convenience.**

## Quick Comparison Table

All figures pulled from GitHub and the published `opam` metadata on 2026-09-21.

| Dimension | Caqti | PostgreSQL-OCaml | SQLite3-OCaml |
|---|---|---|---|
| Stars | **355** | 155 | 132 |
| Forks | 44 | 24 | 40 |
| Open issues | 10 | 4 | **2** |
| Last push | 2026-08-26 | 2026-08-11 | 2026-08-12 |
| License | LGPL-3.0-or-later **with linking exception** | LGPL-2.1-or-later **with OCaml linking exception** | **MIT** |
| Backends | MariaDB, PostgreSQL, SQLite3 | PostgreSQL only | SQLite3 only |
| Minimum OCaml | 4.11 | **5.00** | 4.12 |
| Concurrency | Lwt, Async, blocking unix, experimental Eio/Miou | Blocking, OCaml 5 domains | Blocking |
| Query style | Templated SQL + typed parameters | Raw `libpq` C API mirror | Raw `sqlite3` C API mirror |
| SQL generation | None — bring your own SQL | None | None |
| Representative use | Services with swappable databases | PostgreSQL-heavy backends | Embedded / local-first apps |

## Scenario Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| You want to develop against SQLite and ship on PostgreSQL | **Caqti** | Same code path, only the connection URI changes |
| You need `COPY`, `LISTEN`/`NOTIFY` or long-lived prepared statements | **PostgreSQL-OCaml** | Caqti deliberately does not model those |
| You are writing a CLI tool with a local database file | **SQLite3-OCaml** | Zero server, MIT licence, OCaml 4.12+ |
| Your app is Lwt-based and already has a connection pool abstraction | **Caqti** | `caqti-lwt` drops straight into an Lwt pool |
| You are on OCaml 4.14 and cannot upgrade yet | **Caqti or SQLite3-OCaml** | PostgreSQL-OCaml needs 5.00 |
| You need MirageOS support | **Caqti** | Its `pgx://` scheme targets MirageOS specifically |

## Caqti — One API, Three Databases

Caqti (paurkedal/ocaml-caqti, 355 stars) is the only one of the three that is an abstraction rather than a binding. Connections are described by a URI, and Caqti loads the driver that can handle the scheme: `postgresql://`, `mariadb://`, or `sqlite3://`. Crucially, it does **not** generate or analyse SQL — it gives you templating and uniform parameter encoding and decoding, then hands the statement to the driver.

```bash
# Core library plus the Lwt connector and the PostgreSQL driver
opam install caqti caqti-lwt caqti-driver-postgresql

# Add other backends only if you actually need them
opam install caqti-driver-sqlite3 caqti-driver-mariadb
```

Declare the libraries you actually use in `dune`:

```lisp
(executable
 (name main)
 (libraries caqti-lwt caqti-driver-postgresql lwt.unix))
```

A query is typed on both sides, so a mismatch is a compile error rather than a runtime surprise:

```ocaml
(* The URI is the only place the database choice lives. *)
let uri () = Uri.of_string "postgresql://app:secret@localhost:5432/shop"

let find_sku conn id =
  let query =
    Caqti_request.find_opt Caqti_type.int Caqti_type.string
      "SELECT sku FROM orders WHERE id = ?"
  in
  Caqti_lwt.exec conn query id
```

Because the SQL dialect is yours and the parameters are typed, moving from `sqlite3://shop.db` in development to `postgresql://...` in production is a one-line change — provided you keep the statements portable. That is the whole point of the library, and it is why it is the default recommendation for service code.

The release includes `caqti`, `caqti-lwt`, `caqti-async`, experimental `caqti-eio` and `caqti-miou` connectors, the MirageOS connector, and one driver package per database. The Eio and Miou connectors are worth watching if you are building on OCaml 5 effects, but they are still labelled experimental — do not put them in production without a fallback plan.

## PostgreSQL-OCaml — The Full libpq Surface

PostgreSQL-OCaml (155 stars) mirrors the C API closely using objects for connections and result sets. It does not try to abstract anything away, which is precisely its value: if `libpq` can do it, this library can too.

![Official PostgreSQL project logo](/img/screenshots/postgresql-ocaml-elephant.jpg "PostgreSQL-OCaml exposes the complete libpq client API to OCaml")

```bash
opam install postgresql
```

Building requires the PostgreSQL client headers (`libpq-dev` on Debian/Ubuntu) because the bindings compile against the C library. Usage keeps the imperative feel of `libpq`:

```ocaml
let conn = new Postgresql.connection
    ~host:"localhost" ~port:5432
    ~user:"app" ~password:"secret" ~database:"shop" () in

let res = conn#exec
    "INSERT INTO orders (sku, qty) VALUES ($1, $2)"
    [| Some "ABC-1"; Some "2" |] in

Printf.printf "inserted %d row(s)\n" res#ntuples;
conn#finish
```

Two facts decide whether this library is right for you. First, the published opam metadata requires **OCaml 5.00 or newer** — on a 4.14 codebase it will not build. Second, this is a blocking binding: for concurrent servers you either run each connection on its own OCaml 5 domain or wrap calls carefully, because a slow query will hold the calling thread.

The payoff is directness. Bulk loads via `COPY`, listening on `NOTIFY` channels, per-session `SET` statements, and manual transaction control are all one method call away rather than an abstraction you have to work around.

## SQLite3-OCaml — Embedded Databases Done Right

SQLite3-OCaml (132 stars, MIT) is the smallest dependency in this comparison and the one most likely to end up in a shipped binary. It binds the `sqlite3` C API with statement handles, explicit stepping, and typed data marshalling.

```bash
# Needs pkg-config and the SQLite3 development headers on the build machine
sudo apt install pkg-config libsqlite3-dev
opam install sqlite3
```

The API is deliberately low-level, and stepping through rows is explicit:

```ocaml
let db = Sqlite3.db_open "shop.db" in
let stmt = Sqlite3.prepare db "SELECT sku FROM orders WHERE qty > ?" in
Sqlite3.bind stmt 1 (Sqlite3.Data.INT 0L);

let rec dump () =
  match Sqlite3.step stmt with
  | Sqlite3.Rc.ROW ->
      Printf.printf "%s\n" (Sqlite3.column_text stmt 0);
      dump ()
  | Sqlite3.Rc.DONE -> ()
  | rc -> failwith (Sqlite3.Rc.to_string rc)
in
dump ();
ignore (Sqlite3.finalize stmt);
ignore (Sqlite3.db_close db)
```

**Why it wins for local-first software:** MIT licence, only two open issues, no server process to deploy, and the database is a single file your users can back up themselves. It also coexists cleanly with older `ocaml-sqlite` code, which matters if you maintain a long-lived codebase.

**Where it hurts:** you manage statement lifetimes, explicit transaction boundaries, and error branches yourself — every `Sqlite3.step` return code is a case you should handle. There is no query abstraction, and the library will happily let you write SQL that deadlocks two writers against each other. For anything multi-user, add Caqti on top and keep the same file.

## Running PostgreSQL Locally

All three libraries are easier to develop against with a disposable PostgreSQL instance. This compose file uses the official image and a real readiness probe so your OCaml process does not start before the database accepts connections:

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: shop
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d shop"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
```

## Avoid These Pitfalls

- **Do not start a new project on PGX.** It appears in older recommendations and in Caqti's driver table, but the upstream repository has been dormant since 2020 and carries essentially no community. Caqti's own documentation recommends its `pgx://` driver only for MirageOS, and calls it experimental.
- **Caqti is not an ORM.** There is no model layer, no migration system, and no SQL generation. You write SQL, you manage schema changes (use a migration tool or plain SQL files), and you keep statements portable yourself if you want the swap-a-URI promise to hold.
- **OCaml version constraints are real build blockers.** PostgreSQL-OCaml requires OCaml 5.00+, SQLite3-OCaml requires 4.12+, and Caqti requires 4.11+. Check `ocaml -version` before you add a dependency, and remember that upgrading to OCaml 5 also changes how thread-safety and domains behave.
- **Blocking calls in a concurrent server.** PostgreSQL-OCaml and SQLite3-OCaml are blocking bindings. Calling them directly inside an Lwt or Eio scheduler stalls other fibers. Either use Caqti's Lwt connector or confine blocking calls to a dedicated domain or thread pool.
- **Native library headers are a build-time dependency, not a runtime one.** `libpq-dev`, `libsqlite3-dev`, and `pkg-config` must exist wherever you compile — including CI images and Alpine-based containers. This is the single most common "it works on my machine" failure for OCaml database builds.
- **SQLite write concurrency is single-writer.** Enable WAL mode and set a busy timeout, or serialise writes in your application. Two processes writing aggressively to one file will produce `SQLITE_BUSY` errors that are easy to misread as data corruption.

## Why Self-Host Your Data Layer?

Every library here talks to a database you operate yourself — a PostgreSQL instance in your own compose stack, or a SQLite file on your own disk. Nothing about the data path leaves your infrastructure, and there is no client library that phones home, no usage telemetry, and no per-connection licence to account for.

That last point is worth stating plainly: all three are permissively licensed for commercial work. Caqti is LGPL-3.0 with an explicit linking exception, PostgreSQL-OCaml is LGPL-2.1 with the OCaml linking exception, and SQLite3-OCaml is MIT. In practice that means you can link them into proprietary applications, which is exactly why the linking exceptions exist.

If you are building the rest of the stack around these libraries, our [OCaml web framework comparison](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/) covers the HTTP side, the [OCaml concurrency guide](../2026-09-12-ocaml-concurrency-lwt-vs-eio-vs-async/) explains which connector to pair with which runtime, and the [OCaml testing libraries roundup](../2026-08-01-ocaml-testing-libraries-ounit-alcotest-qcheck/) shows how to test the queries you end up writing.

## FAQ

### Which OCaml database library should I start with?

Start with **Caqti** unless you have a specific reason not to. It is the only one that gives you a stable API across MariaDB, PostgreSQL, and SQLite3, so a prototype written against a local SQLite file can run against PostgreSQL in production with a connection URI change. Reach for the thinner bindings only when you need functionality Caqti does not expose.

### Is Caqti an ORM?

No. Caqti provides a typed query interface and connection pooling, not object-relational mapping. It does not generate SQL, does not define models, and does not manage schema migrations. You write the SQL yourself, which is why it stays out of the way of complex queries and database-specific features.

### Can I use these libraries with Lwt or Eio?

Caqti can: it ships `caqti-lwt`, `caqti-async`, and experimental `caqti-eio` and `caqti-miou` connectors, so the same query code runs on whichever scheduler your application uses. PostgreSQL-OCaml and SQLite3-OCaml are blocking bindings and should be confined to a dedicated thread or domain when used inside an asynchronous application.

### Why does PostgreSQL-OCaml require OCaml 5.00?

The published opam metadata declares `ocaml {>= "5.00"}`, largely to take advantage of the multicore runtime and domains for parallelism while calling into blocking `libpq` code. If your project is still on OCaml 4.14, either stay with Caqti and its PostgreSQL driver or plan a compiler upgrade — the build will fail outright otherwise.

### Is PGX still a viable option?

Practically, no. The upstream repository has seen no meaningful development since 2020 and has negligible community activity, so bug reports and PostgreSQL version changes go unhandled. Use Caqti with `caqti-driver-postgresql` for the same job, or PostgreSQL-OCaml if you need the raw client API.

### Do I need a database server to develop with these libraries?

Not necessarily. Caqti and SQLite3-OCaml both work against a local SQLite file, which removes the server from your development loop entirely. That is a common pattern: run the test suite against an in-file database, then point the production URI at PostgreSQL. Just be aware a few SQL constructs differ between dialects, so keep an integration test against real PostgreSQL in CI.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OCaml Database Libraries in 2026: Caqti vs PostgreSQL-OCaml vs SQLite3 Compared",
  "description": "Comparison of the three maintained OCaml database libraries — Caqti, PostgreSQL-OCaml and SQLite3-OCaml — with opam commands, real code examples and licensing details.",
  "datePublished": "2026-09-21",
  "dateModified": "2026-09-21",
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
