---
title: "HSQLDB vs Apache Derby vs H2 in 2026: Which Embedded Java Database Should You Actually Ship?"
date: "2026-09-11"
tags: ["java", "database", "embedded-database", "jvm", "self-hosted"]
draft: false
cover: "/img/screenshots/h2-console.jpg"
---

Your application needs a database, but not a database *server*. No DBA, no separate process to monitor, no connection string pointing at a machine that might be down. Embedded databases ship **inside** your jar, create their files next to your application, and start in milliseconds. They power unit test suites, desktop tools, edge gateways, and surprisingly large single-node services.

Three Java engines have held this niche for two decades: **H2, HSQLDB, and Apache Derby**. They look interchangeable in a tutorial and behave very differently in production. This guide compares them with current release data, real JDBC configurations, and the failure modes that only appear after you ship.

## TL;DR: The Quick Verdict

**Use H2** for tests, prototypes, and desktop applications — it is the fastest to set up, has a genuinely useful built-in web console, and is what every Spring Boot tutorial assumes. **Use HSQLDB** when you want strict SQL standard compliance and a lightweight database that can also run as a standalone server with minimal footprint. **Use Apache Derby** when you need an Apache-licensed engine with a long, conservative maintenance record and you are shipping into a Java EE or Apache-heavy stack. If you are building something new and portable, H2 wins by default; if correctness of standard SQL matters more than convenience, look hard at HSQLDB.

## Side-by-Side Comparison (data pulled 2026-09-11)

| | **H2 Database** | **HSQLDB** | **Apache Derby** |
|---|---|---|---|
| GitHub stars | **4,627** | not on GitHub (SourceForge / hsqldb.org) | 378 (official Apache mirror) |
| Last activity | 2026-09-11 | 2.7.x line, stable | 2026-05-15 (mirror push) |
| Maven artifact | `com.h2database:h2` **2.5.250** | `org.hsqldb:hsqldb` **2.7.4** | `org.apache.derby:derby` **10.17.1.0** |
| License | MPL-2.0 or EPL-1.0 (dual) | BSD-style | Apache-2.0 |
| Jar size | ~2.6 MB | ~1.6 MB | ~3.3 MB |
| Web console | Yes, built in | SqlTool only | No (use ij) |
| Server mode | Yes (TCP, PG, web) | Yes (hsqldb / hsql protocols) | Yes (DRDA network server) |
| In-memory mode | Yes | Yes | Yes |
| SQL standard compliance | Good, some extensions | **Strictest** | Good |
| Best known for | Tests, desktop apps, console | Compact standalone engine | Long-term conservative releases |

## Which One for Which Job

| Use case | Recommended | Why |
|---|---|---|
| Unit and integration tests | **H2** | In-memory mode plus `DB_CLOSE_DELAY=-1` makes per-test resets trivial |
| Spring Boot local profile | **H2** | Auto-configured console, no external dependency, ubiquitous examples |
| Desktop application data store | **H2** or **HSQLDB** | Both embed cleanly; HSQLDB has the smaller footprint |
| Strict SQL standard behaviour | **HSQLDB** | Closest to the standard, fewer vendor-specific surprises |
| Embedded engine inside a Java EE stack | **Derby** | Apache governance, conservative release cadence, Java EE heritage |
| Reading a cached dataset in memory | **HSQLDB** | Its in-memory tables and cached tables are well optimised for read-mostly data |
| Needing a database that can grow into a server | **HSQLDB** | Same files, same driver, switch the URL prefix |
| Shipping under a permissive corporate license review | **Derby** | Plain Apache-2.0, no dual-license discussion |

## H2: The Pragmatic Default

H2 (4,627 stars, actively pushed — the repository saw commits on 2026-09-11) has become the default embedded engine of the Java ecosystem. The current Maven release is `2.5.250`, published to Central on 2026-09-04.

```xml
<dependency>
  <groupId>com.h2database</groupId>
  <artifactId>h2</artifactId>
  <version>2.5.250</version>
  <scope>runtime</scope>
</dependency>
```

Its JDBC URLs make the deployment mode explicit:

```java
// In-memory: dies with the JVM unless you keep it open
String mem = "jdbc:h2:mem:appdb;DB_CLOSE_DELAY=-1";

// File-backed: creates ./data/appdb.mv.db
String file = "jdbc:h2:file:./data/appdb;AUTO_SERVER=TRUE";

// Server mode, reachable from other processes
String tcp = "jdbc:h2:tcp://localhost:9092/./data/appdb";
```

`AUTO_SERVER=TRUE` is the feature to know about when migrating an embedded app to a multi-process setup: the first process opens the file directly and later processes connect to it over an internal socket, with no separate server to start.

H2's built-in web console is a real operational advantage. Start it alongside your application in server mode:

```bash
java -cp h2-2.5.250.jar org.h2.tools.Server -tcp -web -tcpPort 9092 -webPort 8082
```

![H2 database web console running in a browser](/img/screenshots/h2-console.jpg "Official H2 Console screenshot from the h2database repository")

**Where it hurts:** H2 2.x removed the compatibility shortcuts that people relied on in 1.4.x. Tables are case-sensitive by default now, so `CREATE TABLE Users` and `SELECT * FROM users` are different objects unless you configure `CASE_INSENSITIVE_IDENTIFIERS=TRUE`. Applications that used H2 as a stand-in for PostgreSQL often discover that `MERGE`, sequence handling, and `ON CONFLICT` syntax differ. It is a testing engine, not a PostgreSQL emulator — do not run production workloads against it and expect the same plans.

## HSQLDB: Small, Standard, and Ignored at Your Peril

HSQLDB (also known as HyperSQL) is the oldest of the three in active use and the least fashionable — which is unfair, because it is the one that behaves most like a standards-compliant SQL engine. It is not developed on GitHub; releases come from its SourceForge project and Maven Central, where `org.hsqldb:hsqldb` currently sits at **2.7.4**.

```xml
<dependency>
  <groupId>org.hsqldb</groupId>
  <artifactId>hsqldb</artifactId>
  <version>2.7.4</version>
</dependency>
```

The JDBC URL prefix selects the mode, exactly like H2, but the naming is more consistent across in-memory, file, and server deployments:

```java
String mem    = "jdbc:hsqldb:mem:testdb";                    // in-memory
String file   = "jdbc:hsqldb:file:data/mydb;shutdown=true";   // file-backed
String server = "jdbc:hsqldb:hsql://localhost:9001/mydb";     // server mode
```

Starting the standalone server is a single command with no configuration file, and `shutdown=true` means the engine flushes and closes cleanly when the last connection goes away — a detail that saves you from the "database is locked" support tickets that file-backed engines generate:

```bash
java -cp hsqldb-2.7.4.jar org.hsqldb.server.Server \
  --database.0 file:data/mydb --dbname.0 mydb
```

Command-line access comes from SqlTool, which is included in the distribution and can run inline SQL against any JDBC URL — handy in CI pipelines where you want to seed a schema without an extra dependency:

```bash
java -jar sqltool-2.7.4.jar --inlineRc=url=jdbc:hsqldb:mem:testdb,user=SA \
  --sql "CREATE TABLE account(id INT PRIMARY KEY, balance DECIMAL(12,2));"
```

**Where it hurts:** the in-memory tables are not durable unless you ask for `CREATE MEMORY TABLE` semantics carefully, and the type system is stricter than MySQL's, so schemas ported from MySQL often fail on implicit conversions. Documentation is thorough but spread across a PDF guide and the project wiki. The ecosystem is thin: you will find fewer Stack Overflow answers than for H2, so budget time for reading the guide rather than guessing.

## Apache Derby: The Conservative Choice

Apache Derby is the engine IBM contributed to the Apache Software Foundation, and it still carries the DB2 lineage in its SQL dialect and tools. The canonical artifact is `org.apache.derby:derby` **10.17.1.0**; Apache also publishes a GitHub mirror at `apache/derby`, last pushed 2026-05-15, while actual development happens on Apache's own GitBox infrastructure.

```xml
<dependency>
  <groupId>org.apache.derby</groupId>
  <artifactId>derby</artifactId>
  <version>10.17.1.0</version>
</dependency>
```

Derby's embedded URL uses a distinct syntax worth memorising, because the `create=true` flag is what makes a database appear on first connection:

```java
String mem    = "jdbc:derby:memory:testdb;create=true";
String file   = "jdbc:derby:data/mydb;create=true";
String client = "jdbc:derby://localhost:1527/mydb;create=true";
```

Since JDBC 4 driver auto-loading, no `Class.forName` call is needed for the embedded driver. Network access requires starting the DRDA server first:

```bash
java -jar derbyrun.jar server start -p 1527
```

The administration tool is `ij`, a scriptable JDBC shell with a small but precise command language that has not changed in years:

```bash
java -jar derbyrun.jar ij
# ij> connect 'jdbc:derby:memory:testdb;create=true';
# ij> create table notes(id int primary key, body clob);
```

**Where it hurts:** release cadence is slow and the JDK floor rises with each major version, so older JDK environments pin you to older Derby lines. The ecosystem is small compared with H2, and Derby's dialect differs just enough from both PostgreSQL and MySQL that ORM-generated SQL needs review. Derby is a good fit when stability and Apache governance outweigh starting a database in one line of code.

## Running These Engines in the Real World

Whichever engine you pick, the connection pool configuration is what determines whether the embedded database behaves itself under load. HikariCP with a small maximum pool size is the standard pairing:

```java
HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:h2:file:./data/appdb;AUTO_SERVER=TRUE");
config.setMaximumPoolSize(4);
config.setConnectionTimeout(10_000);
DataSource ds = new HikariDataSource(config);
```

Embedded engines serialize writes on a single file lock. A pool of fifty connections pointed at one file-backed H2 database performs worse than a pool of four, because the extra threads spend their time waiting on the same lock. Size the pool to the number of CPU cores, not to the number of HTTP worker threads.

For test suites, the same engines are available through container-based testing if you want the production database instead of a stand-in. Our [database testing with Testcontainers guide](../2026-05-02-testcontainers-java-go-python-self-hosted-database-testing-guide/) walks through that trade-off, and our [self-hosted SQL database comparison](../2026-04-25-firebird-vs-postgresql-vs-mariadb-self-hosted-sql-database-guide-2026/) covers the server-class options when the embedded engine outgrows its files. If query performance becomes the bottleneck, our [database query profiling and optimization tools guide](../2026-04-23-self-hosted-database-query-profiling-optimization-tools-guide-2026/) covers where to look first.

## Pitfalls: What Breaks After You Ship

1. **In-memory databases disappear between test classes.** With `jdbc:h2:mem:test`, the database vanishes when the last connection closes. Add `DB_CLOSE_DELAY=-1` so the schema survives for the duration of the JVM.
2. **File locking blocks the second process.** File-backed engines take an exclusive lock. `AUTO_SERVER=TRUE` (H2), a `shutdown=true` URL (HSQLDB), or a real server mode solves it — but only if you plan for it before release.
3. **Case sensitivity changed in H2 2.x.** Unquoted identifiers are uppercased in older versions and treated differently in 2.x depending on configuration. Applications that generate DDL from ORM metadata often need `DATABASE_TO_LOWER=TRUE`.
4. **H2 is not PostgreSQL.** Do not use it to validate queries you intend to run against PostgreSQL in production; the planner and function set differ. Use Testcontainers with the real engine for those tests.
5. **Backups are file copies.** There is no `pg_dump` equivalent to schedule. Use the engine's own backup command (`SCRIPT` in H2/HSQLDB, `SYSCS_UTIL.SYSCS_BACKUP_DATABASE` in Derby) or stop the process before copying files, otherwise you will restore a torn database.
6. **Upgrading the engine can require an upgrade step.** File formats change between major versions. Test the upgrade path on a copy of production data, never in place.
7. **Derby's JDK floor moves.** Each Derby line requires a newer minimum JDK, so verify the supported matrix before pinning a version in a long-lived product.

## FAQ

**Which embedded Java database is fastest?**
For read-mostly workloads the three perform within a few percent of each other, and the JVM's JIT matters more than the engine. H2 generally starts fastest and Javassist-era HSQLDB handles cached tables well; Derby's strength is predictable behaviour, not raw speed. Benchmark with your own schema before choosing on performance grounds.

**Can I use H2 in production?**
Yes, for single-process applications where the database is a private data store — desktop software, edge appliances, internal tools. It is not a good fit for multi-user concurrent writes at scale, and it should never be the shared database behind a cluster of application servers.

**Is HSQLDB dead?**
No. The 2.7.x line is maintained, and version 2.7.4 is the current artifact on Maven Central. Development is slower and happens outside GitHub, which is why it looks abandoned in star counts — there is no official repository to star.

**Does Derby come with a web console?**
No. Derby ships the `ij` command-line tool instead, and network deployments are usually administered with external SQL clients over DRDA. If you want a browser console, H2 is the easier path.

**How do I migrate from H2 to HSQLDB or Derby?**
Dump the schema with the engine's `SCRIPT` command, translate the DDL by hand — types such as `IDENTITY`, `CLOB`, and boolean handling differ — and reload through JDBC. There is no reliable automatic converter, so treat it as a schema rewrite with tests, not a configuration change.

**Do these engines work with an ORM?**
All three expose standard JDBC drivers, so Hibernate, JPA, and MyBatis work with any of them. The friction is dialect-level: identifier casing, sequence generation, and `LIMIT`/`OFFSET` translation. Expect to configure a dialect and re-run your integration tests after switching.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "HSQLDB vs Apache Derby vs H2 in 2026: Which Embedded Java Database Should You Actually Ship?",
  "description": "Comparison of H2, HSQLDB, and Apache Derby as embedded Java databases in 2026, with Maven coordinates, JDBC URLs, server mode commands, and production pitfalls.",
  "datePublished": "2026-09-11",
  "dateModified": "2026-09-11",
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
