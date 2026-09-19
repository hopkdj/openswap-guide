---
title: "Kotlin Database Libraries in 2026: Exposed vs SQLDelight vs Ktorm — Which One Should You Actually Use?"
date: "2026-09-20"
tags: ["kotlin", "databases", "orm", "exposed", "sqldelight", "ktorm", "jvm"]
draft: false
---

Your Kotlin service works, your SQL is fine, and yet every `ResultSet` you unwrap by hand is a small tax you keep paying. The three libraries people actually reach for — JetBrains' Exposed, Cash App's SQLDelight, and Ktorm — represent three genuinely different philosophies about who owns your SQL: the Kotlin compiler, the build plugin, or you. Choosing wrong means months of fighting generated code you cannot edit.

Here is the honest breakdown, with dependency coordinates and code taken from each project's own repository rather than from memory.

## TL;DR: Quick Verdict

- **Writing queries as Kotlin code, with an escape hatch to raw SQL → Exposed.** JetBrains-backed, 9,287 stars, both JDBC and R2DBC transports, and two APIs (type-safe DSL for queries, DAO for entity mapping) so you can start simple and add structure later.
- **SQL is the source of truth and you want compile-time verification → SQLDelight.** 6,881 stars. You write `.sq` files; the Gradle plugin verifies your schema, statements, and migrations at compile time and generates type-safe Kotlin APIs from them.
- **You want a lightweight ORM on pure JDBC with no annotations, no XML, no magic → Ktorm.** 2,344 stars, Apache-2.0, table objects declared as Kotlin objects, strong-typed SQL DSL plus entity sequence APIs.

If you are writing a JVM backend in 2026 and want one answer: **Exposed**. If your team already writes SQL by hand and wants the compiler to check it: **SQLDelight**. If you liked the shape of a classic ORM but refuse to fight annotations: **Ktorm**.

## The Three Contenders at a Glance

| Dimension | Exposed | SQLDelight | Ktorm |
|---|---|---|---|
| GitHub stars | **9,287** | 6,881 | 2,344 |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Last repo activity | 2026-09-18 | 2026-09-18 | 2026-06-20 |
| Maintainer | JetBrains | Cash App | Community (`kotlin-orm`) |
| Query style | Kotlin DSL or DAO API | `.sq` SQL files, generated APIs | Kotlin DSL + entity sequences |
| Transports | JDBC and R2DBC | SQLite, MySQL, PostgreSQL, H2 | Pure JDBC only |
| Multiplatform | JVM | JVM, Android, Native, JS | JVM |
| Schema management | `SchemaUtils` in code | Migration files verified at build time | DDL in code or your own tooling |
| Compile-time SQL checking | No | **Yes** | Partial (types, not SQL validity) |
| Best fit | Kotlin-first backends | SQL-first apps, mobile/KMP | Lightweight JVM services |

Star counts and activity dates above were pulled from GitHub at publish time. Re-check before you commit: `gh repo view JetBrains/Exposed --json stargazerCount,pushedAt`.

## Decision Matrix: Which One for Your Use Case

| Your situation | Pick | Why |
|---|---|---|
| New Kotlin backend, team knows SQL but prefers Kotlin | **Exposed** | DSL keeps queries in Kotlin; DAO is there when you want entities |
| Existing hand-written SQL you refuse to rewrite | **SQLDelight** | Your `.sq` files *are* the schema; you get types for free |
| Kotlin Multiplatform app (Android + iOS + JVM) | **SQLDelight** | SQLite dialects on Android, Native, JS, and JVM from one codebase |
| Reactive stack with non-blocking drivers | **Exposed (R2DBC)** | `exposed-r2dbc` module alongside `exposed-jdbc` |
| Tiny service, minimal dependencies, no code generation | **Ktorm** | Pure JDBC, no annotations, no XML, no generated sources |
| You need repeatable migrations in CI | **SQLDelight** | `verifyMigrations` fails the build when a migration is missing |
| Encrypted or JSON columns | **Exposed** | `exposed-crypt` and `exposed-json` extension modules |

## Exposed: SQL as Kotlin, With Two Doors

Exposed is the most complete of the three, and version 1.x reorganized it into clearly separated modules. The core split matters because it decides what you actually ship:

| Module | What it gives you |
|---|---|
| `exposed-core` | Type-safe DSL primitives — the foundation |
| `exposed-jdbc` | Transport-level implementation on the JDBC API |
| `exposed-r2dbc` | Reactive transport instead of JDBC |
| `exposed-dao` | Optional Data Access Object API (JDBC only, not R2DBC) |
| `exposed-java-time`, `exposed-kotlin-datetime` | Date-time column types |
| `exposed-json` | JSON and JSONB column types |
| `exposed-crypt` | Encrypted and one-way hashed columns |
| `exposed-migration-core` | Shared migration functionality |

Add the parts you need from Maven Central under the `org.jetbrains.exposed` group:

```kotlin
dependencies {
    implementation("org.jetbrains.exposed:exposed-core:$exposedVersion")
    implementation("org.jetbrains.exposed:exposed-jdbc:$exposedVersion")
    implementation("org.jetbrains.exposed:exposed-dao:$exposedVersion")
}
```

Tables are Kotlin objects, and the DSL path looks like this (imports are the v1 packages, which changed in the 1.x line — copy them carefully or your migration will not compile):

```kotlin
import org.jetbrains.exposed.v1.core.*
import org.jetbrains.exposed.v1.jdbc.*
import org.jetbrains.exposed.v1.jdbc.transactions.transaction

object Cities : Table() {
    val id = integer("id").autoIncrement()
    val name = varchar("name", 50)

    override val primaryKey = PrimaryKey(id)
}

object Users : Table() {
    val id = varchar("id", 10)
    val name = varchar("name", length = 50)
    val cityId = integer("city_id").references(Cities.id).nullable()

    override val primaryKey = PrimaryKey(id, name = "PK_User_ID")
}

fun main() {
    Database.connect("jdbc:h2:mem:test", driver = "org.h2.Driver", user = "root", password = "")

    transaction {
        addLogger(StdOutSqlLogger)
        // insert and query with the DSL here
    }
}
```

The DAO path is the same schema with entity classes, and Exposed explicitly documents that DAO **does not** work with the R2DBC module — a detail that sinks reactive migrations when discovered late:

```kotlin
object Cities : IntIdTable() {
    val name = varchar("name", 50)
}

object Users : IntIdTable() {
    val name = varchar("name", length = 50).index()
    val city = reference("city", Cities)
    val age = integer("age")
}

class User(id: EntityID<Int>) : IntEntity(id) {
    companion object : IntEntityClass<User>(Users)

    var name by Users.name
    var age by Users.age
}
```

**Choose Exposed if** you want your persistence layer written in Kotlin and you value JetBrains' release cadence. **Do not choose it if** your team's contract is "SQL lives in SQL files" — Exposed will feel like a translation layer you did not ask for.

## SQLDelight: Your SQL Files Are the API

SQLDelight inverts the usual relationship. Instead of mapping Kotlin objects onto tables, you write SQL and let the Gradle plugin generate the typesafe Kotlin API — and verify schema, statements, and migrations at compile time. You also get IDE features like autocomplete and refactoring on your SQL.

Everything starts with a plain schema file:

```sql
CREATE TABLE hockey_player (
  id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  number INTEGER NOT NULL
);
```

Then the Gradle DSL declares your databases:

```kotlin
sqldelight {
  databases {
    create("MyDatabase") {
      packageName.set("com.example")
    }
  }
}
```

Dialects are selected with a Gradle dependency, which is how one project targets several engines:

```kotlin
dialect("app.cash.sqldelight:sqlite-3-24-dialect:{{ versions.sqldelight }}")
```

Available dialects cover SQLite (3.18 through 3.44), MySQL, PostgreSQL, and HSQL/H2 on the JVM, with SQLite additionally supported on Android, Native (iOS, macOS, Windows), JavaScript, and Kotlin Multiplatform. Schema dependencies let one module compile against another module's database:

```kotlin
sqldelight {
  databases {
    create("MyDatabase") {
      packageName.set("com.example.projecta")
      dependency(project(":ProjectB"))
    }
  }
}
```

Two operational properties are worth more than any feature table. First, **`verifyMigrations`** turns "someone forgot the migration" from a production incident into a failed build. Second, because SQLDelight understands your existing schema, adopting it does not require rewriting queries — you move them into `.sq` files and let the plugin generate the accessors.

**Choose SQLDelight if** SQL is genuinely the interface between your data and your code, or if you are shipping Kotlin Multiplatform. **Do not choose it if** you dislike generated code in your source tree — SQLDelight generates a lot of it, by design.

## Ktorm: The Lightweight ORM That Skips the Ceremony

Ktorm's README makes a blunt promise: **no configuration files, no XML, no annotations, even no third-party dependencies**. It sits directly on pure JDBC and gives you a strong-typed SQL DSL plus entity sequence APIs.

Dependencies are a single line:

```groovy
compile "org.ktorm:ktorm-core:${ktorm.version}"
```

Schema definition is plain Kotlin, using objects as tables:

```kotlin
object Departments : Table<Nothing>("t_department") {
    val id = int("id").primaryKey()
    val name = varchar("name")
    val location = varchar("location")
}

object Employees : Table<Nothing>("t_employee") {
    val id = int("id").primaryKey()
    val name = varchar("name")
    val job = varchar("job")
    val managerId = int("manager_id")
    val hireDate = date("hire_date")
    val salary = long("salary")
}
```

Connecting and querying needs no session manager, no EntityManager, no context object:

```kotlin
fun main() {
    val database = Database.connect("jdbc:mysql://localhost:3306/ktorm", user = "root", password = "***")

    for (row in database.from(Employees).select()) {
        println(row[Employees.name])
    }
}
```

The trade-offs are equally clear. Ktorm is JVM-only — no R2DBC, no multiplatform. Its ecosystem is smaller (2,344 stars versus Exposed's 9,287), and its last repository activity in this comparison was 2026-06-20 rather than mid-September. None of that disqualifies it; it just means you are choosing a smaller, quieter project with fewer moving parts.

**Choose Ktorm if** you want typed queries without a plugin, a generator, or a framework's opinion about your project layout. **Do not choose it if** you need reactive transports or non-JVM targets.

## Operating These Libraries in Production

The persistence layer you pick quietly sets your deployment constraints, and this is where the three diverge most.

**Connection pooling is your problem, not the library's.** All three sit on top of a driver — HikariCP by default in most JVM services. Size the pool against your database's connection limit, not your CPU count, and remember that `exposed-r2dbc` moves you to a non-blocking driver with an entirely different pooling story.

**Migrations deserve a system, not a habit.** SQLDelight ships verification in the build. Exposed keeps migration functionality in `exposed-migration-core`, and most teams pair it with Flyway or Liquibase. Ktorm expects you to bring your own. Whichever you pick, the failure mode is identical: a schema change that lands in staging but not production.

**Test against a real engine.** An in-memory H2 database is convenient and lies to you — dialect differences in generated SQL are exactly the bugs a type-safe DSL cannot catch. Run integration tests against a containerized instance of the engine you deploy. Our guide to [Kotlin testing frameworks](../2026-07-06-kotlin-testing-frameworks-kotest-mockk-mockito-kotlin/) covers how to structure those suites.

**Know your serialization boundary.** Database rows become API responses somewhere. If that boundary uses kotlinx.serialization, the [Kotlin serialization comparison](../2026-07-13-kotlin-serialization-libraries-kotlinx-moshi-klaxon/) covers the trade-offs. And if your DAO calls fan out concurrently, the [Kotlin concurrency comparison](../2026-08-26-kotlin-concurrency-coroutines-rxjava-flow-comparison/) is the companion piece on coroutines versus Flow versus RxJava.

## Common Pitfalls and Migration Notes

**Exposed 1.x moved its packages.** The imports are now `org.jetbrains.exposed.v1.core.*` and `org.jetbrains.exposed.v1.jdbc.*`. Old tutorials showing `org.jetbrains.exposed.sql.*` will not compile against the current line.

**DAO does not work with R2DBC.** If you adopt Exposed for a reactive service, you are writing DSL queries — plan for that before you start, not after.

**SQLDelight needs the plugin, not just the runtime.** Adding the dialect dependency without the Gradle plugin produces the confusing result of generated code that never regenerates. Wire the plugin first, then the dialect.

**Type safety is not SQL correctness.** Exposed and Ktorm check your Kotlin types; SQLDelight checks your SQL. A type-safe query against a missing index still takes four seconds in production.

**Watch the escape hatches.** Every one of these libraries lets you drop to raw SQL. That is a feature — but a query written three ways in one codebase is a maintenance problem no ORM solves for you.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kotlin Database Libraries in 2026: Exposed vs SQLDelight vs Ktorm",
  "description": "Practical comparison of Exposed, SQLDelight and Ktorm for Kotlin persistence in 2026: Gradle coordinates, DSL versus SQL-first workflow, JDBC versus R2DBC transports, and migration tooling.",
  "datePublished": "2026-09-20",
  "dateModified": "2026-09-20",
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

## FAQ

**Is Exposed an ORM or a SQL library?**
Both, depending on which module you use. `exposed-core` with `exposed-jdbc` gives you a type-safe SQL DSL; `exposed-dao` adds an entity-based Data Access Object API. The DAO module is JDBC-only and does not work with `exposed-r2dbc`.

**Does SQLDelight work with PostgreSQL and MySQL, or only SQLite?**
It supports PostgreSQL, MySQL, and HSQL/H2 on the JVM, plus SQLite across Android, Native, JavaScript, and Kotlin Multiplatform. You select the dialect with a dialect dependency such as `app.cash.sqldelight:sqlite-3-24-dialect`.

**Which of the three is best for Kotlin Multiplatform?**
SQLDelight. It generates code for Android, iOS and macOS via Native, JavaScript, JVM, and multiplatform SQLite targets. Exposed is JVM-only and Ktorm is JVM-only.

**Do I still need Flyway or Liquibase if I use SQLDelight?**
Usually not for schema verification — SQLDelight verifies schema, statements, and migrations at compile time and offers a `verifyMigrations` build setting. Exposed and Ktorm expect you to bring your own migration tooling; many teams pair them with Flyway.

**Which library has the strongest maintainer backing?**
Exposed is an official JetBrains project. SQLDelight is maintained by Cash App. Ktorm is community-maintained under the `kotlin-orm` organization, with a smaller but focused contributor base.

**Can I use these with an in-memory database for tests?**
Yes — Exposed's own examples connect to `jdbc:h2:mem:test`, and H2 works with SQLDelight through its HSQL/H2 dialect. Treat in-memory runs as unit tests only and keep integration tests against a real engine, because dialect differences are exactly what type checking does not catch.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
