---
title: "Scala Database Libraries in 2026: doobie vs Slick vs Quill vs Skunk Compared"
date: "2026-09-19"
tags: ["scala", "database", "developer-tools", "jvm"]
draft: false
cover: "/img/screenshots/scala-doobie-logo.jpg"
description: "doobie, Slick, Quill and Skunk compared with real code from their official docs, live GitHub activity data, and a decision matrix for picking a Scala database layer."
---

You picked Scala for its type system, then handed your persistence layer to a string-concatenating ORM and lost every guarantee you paid for. Or worse — you picked Slick for the type safety and discovered that mapping a complex join to your domain model now requires more code than the SQL would have.

Scala has four serious database libraries in 2026, and they sit at genuinely different points on the type-safety-versus-control spectrum. This comparison uses live repository data and code taken directly from each project's own documentation, so you can judge them on what they actually look like in a codebase.

## TL;DR — Quick Verdict

**Choose `doobie` if you want full control over SQL with functional composition** — you write real SQL in an interpolator, it is checked for type correctness at compile time, and the effect type is whatever your program already uses. **Choose `Slick` if you want to write queries in Scala collections syntax** and let the query compiler generate dialect-specific SQL for you. **Choose `Quill` if compile-time query generation is the priority** and you are already on ZIO or Cats Effect. **Choose `Skunk` only if you are Postgres-only** — the constraint is real, but the payoff is a purpose-built protocol implementation with no JDBC in the stack.

One sentence: *doobie for SQL purists, Slick for Scala-native query DSLs, Quill for compile-time generation, Skunk for Postgres-only shops.*

## The Contenders at a Glance

Live GitHub figures, pulled at publication time:

| Library | Stars | Last commit | Query style | Database support | Effect integration |
|---|---|---|---|---|---|
| **[doobie](https://github.com/typelevel/doobie)** | 2,225 | 2026-09-19 | SQL string interpolator (`sql"..."`) | Any JDBC database | Cats Effect (`Async`/`Sync`) |
| **[Slick](https://github.com/slick/slick)** | 2,665 | 2026-09-11 | Scala collections-like DSL + query compiler | Broad JDBC coverage | Cats Effect 3 (`db.run` returns `F[R]`) |
| **[Quill](https://github.com/zio/zio-quill)** | 2,166 | 2026-09-05 | Quoted DSL compiled at build time | JDBC + ZIO-native modules | ZIO, Cats Effect |
| **[Skunk](https://github.com/typelevel/skunk)** | 1,667 | 2026-09-19 | SQL interpolator over the Postgres wire protocol | **Postgres only** | Cats Effect + fs2 |

All four are actively releasing. Note that Skunk and doobie both received commits on the day of writing — that is not typical, but it does tell you neither project is abandoned.

## Scenario Decision Matrix

| Your situation | Recommendation | Reason |
|---|---|---|
| Complex reporting queries with CTEs and window functions | **doobie** | You write the SQL; nothing gets in the way of the planner |
| Standard CRUD over an existing schema | **Slick** or **Quill** | Generated queries eliminate hand-written boilerplate |
| Postgres-only, want maximum throughput | **Skunk** | Bypasses JDBC entirely, streams results via fs2 |
| Existing ZIO codebase | **Quill** | `Quill.Postgres[SnakeCase]` slots into a `ZLayer` cleanly |
| Existing Cats Effect codebase | **doobie** or **Skunk** | Both are Typelevel projects with the same idioms |
| Team that must read generated SQL for auditing | **doobie** | The SQL in your source is the SQL that runs |
| Cannot change databases ever | **Skunk** | The best Postgres experience available in Scala |

## doobie — SQL You Can Read, Types the Compiler Checks

doobie's design premise is that SQL is a good language and you should keep writing it. What it adds is an interpolator that makes your query type-check, plus `ConnectionIO` so that composing queries is just function composition — and so that nothing actually executes until you say so.

Start with a transactor, which is the object that knows how to get connections:

```scala
// A transactor that gets connections from java.sql.DriverManager and executes blocking operations
// on our synchronous EC.
val xa = Transactor.fromDriverManager[IO](
  driver = "org.postgresql.Driver",  // JDBC driver classname
  url = "jdbc:postgresql:world",     // Connect URL
  user = "postgres",                 // Database user name
  password = "password",             // Database password
  logHandler = None                  // Don't setup logging for now
)
```

Then a query is an interpolator, a row decoder, and a `transact` call. This snippet is from doobie's own documentation, on the standard `world` sample database:

```scala
sql"select name from country"
  .query[String]    // Query0[String]
  .to[List]         // ConnectionIO[List[String]]
  .transact(xa)     // IO[List[String]]
  .unsafeRunSync()  // List[String]
  .take(5)
  .foreach(println)
```

The critical property here is that `.to[List]` returns a `ConnectionIO`, not an `IO`. Nothing has touched the database yet. That means you can compose three queries into one transaction by sequencing them and calling `transact` once — which is exactly what you want and is awkward to express with a connection-pool-and-try/finally approach.

The trade-off: doobie will not generate SQL for you, and it does not attempt to model your schema. For teams used to SQL, that is a feature. For teams that want the compiler to catch a renamed column, it is not.

## Slick — Queries as Scala Collections

Slick's proposition is that relational data should feel like Scala collections while retaining compile-time safety and composability, with the ability to drop to raw SQL when needed. Its query compiler translates the same Scala query into dialect-specific SQL for different engines.

Here is Slick's canonical example, straight from the project README — a table definition, a `TableQuery`, and an insert:

```scala
import slick.jdbc.PostgresProfile.api.*

// First declare our Scala object
final case class Coffee(name: String, price: Double)

// Next define how Slick maps from a database table to Scala objects
class Coffees(tag: Tag) extends Table[Coffee](tag, "COFFEES") {
  def name  = column[String]("NAME")
  def price = column[Double]("PRICE")
  def * = (name, price).mapTo[Coffee]
}

// The `TableQuery` object gives us access to Slick's rich query API
val coffees = TableQuery[Coffees]

// Inserting is done by appending to our query object
// as if it were a regular Scala collection
// SQL: insert into COFFEES (NAME, PRICE) values ('Latte', 2.50)
coffees += Coffee("Latte", 2.50)
```

The `coffees += Coffee(...)` line is the whole appeal. But the mapping layer is also the cost: your `Table` class is a second schema definition that must be kept in sync with the database, which is why Slick ships a code generator that reads the live schema and emits these classes for you. If you are not using the generator, you are hand-maintaining a shadow schema.

Modern Slick is not the Slick of 2015. It now offers an asynchronous API built on Cats Effect 3 — `db.run(action)` returns `F[R]` for any effect type with an `Async` instance, including `IO` and ZIO `Task` — plus a streaming API returning an fs2 `Stream[F, T]`. That means you can compose it with the broader Typelevel ecosystem rather than fighting it.

## Quill — Compile-Time Query Generation

Quill's differentiator is when the query is built: at compile time, from a Scala quotation. `query[Person]` is not reflected on at runtime; it is expanded into a query AST by a macro, then rendered per-dialect. That eliminates the runtime reflection that older Scala query DSLs relied on, and it gives you compile-time errors for schema mismatches.

The ZIO quickstart from the official docs is compact — a case class, a service that owns a `Quill.Postgres[SnakeCase]` context, and a query:

```scala
case class Person(name: String, age: Int)

class DataService(quill: Quill.Postgres[SnakeCase]) {
  import quill._
  def getPeople: ZIO[Any, SQLException, List[Person]] = run(query[Person])
}
object DataService {
  def getPeople: ZIO[DataService, SQLException, List[Person]] =
    ZIO.serviceWithZIO[DataService](_.getPeople)

  val live = ZLayer.fromFunction(new DataService(_))
}
```

And the dependency declaration from that same quickstart:

```scala
libraryDependencies ++= Seq(
  "io.getquill"    %% "quill-jdbc-zio" % "<latest>",
  "org.postgresql" %  "postgresql"     % "42.3.1"
)
```

The `SnakeCase` naming strategy in the type parameter is doing real work — it maps `case class` field names like `firstName` to `first_name` columns without annotations. If your schema follows a different convention, that is where the configuration lives.

The honest caveat with Quill is macro error messages. When a quotation does not compile, the diagnostic can be long and the offending expression can be several expansion layers away from the reported position. Budget ramp-up time for the team.

## Skunk — Postgres, and Only Postgres

Skunk deserves a separate category. It does not sit on JDBC at all; it implements the Postgres wire protocol directly in Scala, with `fs2` for streaming. That removes a layer of blocking JDBC calls and gives you real back-pressure on large result sets.

Session construction from the official reference is a fluent builder, and SSL handling is explicit rather than configured through a JDBC URL:

```scala
Session.Builder[IO]
  .withUserAndPassword("jimmy", "banana")
  .withDatabase("world")
  .withSSL(SSL.System)  // Use SSL with the system default SSLContext
  .single
```

Skunk documents its TLS modes as a table in the reference docs — `SSL.None` (the default, no SSL requested), `SSL.Trusted` (connect via SSL and trust all certificates, appropriate for self-signed certs), and `SSL.System` (connect via SSL using the system `SSLContext` to verify certificates, for CA-signed certs). That explicitness is refreshing compared to the JDBC string-URL tradition.

![The Quill project logo from the official zio-quill repository](/img/screenshots/scala-quill-logo.jpg "Quill project logo")

The constraint is unambiguous: Skunk is for Postgres. No MySQL, no SQL Server, no Oracle. If you need portability, this is not your library. If you are Postgres-only and you want the lowest-latency, most streaming-friendly option in the ecosystem, it is.

## Pitfalls and Migration Notes

**Do not mix query styles inside one module.** A codebase where half the repositories use `sql"..."` and half use `TableQuery` is harder to review than either alone, because reviewers must context-switch on correctness criteria. Pick one style per bounded context.

**Connection pool configuration is where production incidents live.** doobie and Skunk hand you a `Resource`-based session; Slick manages its own pool via config. Whatever you choose, set the pool size explicitly and verify it against your database's `max_connections` — the default pool of 10 per instance multiplies fast across replicas.

**N+1 queries hide behind collection syntax.** `coffees.map(_.name)` reads like an in-memory operation. Slick's query compiler will generally fuse it correctly, but the only way to know is to enable statement logging and count the statements during a realistic request. This applies to every library in this list.

**Streaming is not the same as an unbounded `to[List]`.** doobie's `.to[List]` materialises the entire result set. For a report returning 400k rows, use the streaming API and process in chunks. Skunk's fs2 integration makes this natural; doobie supports it via `fs2.Stream`; Slick exposes `Stream[F, T]`.

**Version drift between modules breaks macro-generated code quietly.** Quill modules are coupled to the Quill core version and to the dialect module's version. Pin them together and upgrade as a unit rather than letting your dependency resolver pick.

**Test against the real database engine.** H2 is convenient for unit tests, but dialect differences mean a passing H2 suite can hide a failing Postgres migration. Testcontainers is the pragmatic middle ground and is the approach we recommend when you are also validating your schema.

For related reading, see our [Scala effect systems comparison](../2026-09-03-scala-effect-systems-cats-effect-zio-monix-comparison/) to understand how these libraries behave inside `IO` and `ZIO`, and the [Scala HTTP client comparison](../2026-07-25-scala-http-clients-http4s-akka-http-sttp-zio-http/) if you are wiring data access into an `http4s` or `sttp` service. Teams evaluating query-building abstractions across languages will find the [cross-language SQL query builder comparison](../2026-06-20-sql-query-builder-libraries-knex-jooq-diesel-squirrel/) useful for context.

## FAQ

**Is Slick still maintained in 2026?**

Yes. The repository received commits in September 2026 and has 2,665 stars, making it the most-starred library in this comparison. Slick has also modernised its execution model: `db.run(action)` now returns `F[R]` for any effect type with a `cats.effect.Async` instance, and there is an fs2 `Stream[F, T]` streaming API for composition with the Typelevel ecosystem. The "Slick is dead" claim that circulated years ago is not supported by repository activity.

**Should I use doobie or Slick for a new Scala project?**

Use doobie if your team writes and reviews SQL directly and you want the query in the source to be the query that runs. Use Slick if you want to write queries in collection syntax and have the query compiler emit dialect-specific SQL for multiple engines. A useful tie-breaker: if your schema is code-generated from a database that already exists, Slick's generator fits naturally; if you are writing complex analytics SQL by hand, doobie stays out of your way.

**What is the difference between Quill and doobie?**

Both are compile-time-safe. The difference is who writes the query. With doobie you write SQL inside a `sql"..."` interpolator, and the compiler validates the parameters and the row decoder. With Quill you write Scala — `query[Person]` — and a macro expands it into a query AST that is rendered per dialect at build time. doobie gives you exact SQL control with no reflection; Quill gives you less SQL to write in exchange for accepting macro-generated queries and their error messages.

**Can Skunk connect to MySQL or MariaDB?**

No. Skunk is purpose-built for Postgres and implements the Postgres wire protocol directly rather than going through JDBC. That is the source of its performance and streaming advantages, and also its hard limitation. If you need multi-database support, use doobie or Slick instead.

**How do I avoid N+1 queries with these libraries?**

Enable statement logging in development — doobie has configurable `logHandler` support, Slick can log statements, and Skunk exposes observability hooks — and count statements for a representative request. Collection-style APIs make N+1 easy to write accidentally because a nested query looks like a nested collection operation. If you see one statement per element in a result set, rewrite it as a single join or a batched `WHERE id = ANY(...)` query.

**Do these libraries work with connection poolers like PgBouncer?**

Yes, with one important caveat. Transaction-mode pooling (PgBouncer's default) breaks server-side prepared statements, which Slick, doobie and Quill all use by default. Either run PgBouncer in session mode, disable prepared statement caching in your library, or use a pooler that supports statement multiplexing. Getting this wrong shows up as intermittent "prepared statement does not exist" errors under load rather than as a startup failure.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Scala Database Libraries in 2026: doobie vs Slick vs Quill vs Skunk Compared",
  "description": "doobie, Slick, Quill and Skunk compared with real code from their official docs, live GitHub activity data, and a decision matrix for picking a Scala database layer.",
  "datePublished": "2026-09-19",
  "dateModified": "2026-09-19",
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
