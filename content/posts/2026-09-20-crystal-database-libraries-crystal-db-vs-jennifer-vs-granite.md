---
title: "crystal-db vs Jennifer vs Granite in 2026: Picking a Crystal Database Layer Without Regret"
date: "2026-09-20"
tags: ["crystal", "database", "orm", "developer-tools"]
draft: false
cover: "/img/screenshots/crystal-db-orm-cover.jpg"
description: "crystal-db, Jennifer and Granite compared for Crystal applications in 2026: real shard.yml, model, migration and query code from official repos, plus maintenance signals and a decision matrix."
---

Crystal compiles to a single fast binary, has a Ruby-like syntax, and — less happily — gives you exactly **three serious ways to talk to a database**. The signs are contradictory. **crystal-db**, the official driver abstraction, sits at **312 stars** with commits as recent as **2026-08-20**. **Jennifer**, the richest ORM in the ecosystem at **424 stars**, has not been pushed since **2025-01-25** and its README carries a blunt warning: MySQL **8.0.36 and above is not supported**. **Granite**, the ORM built for the Amber framework at **308 stars** and an **2026-08-05** push, has a README headline that simply says "Looking for maintainers."

So the choice is not "which is best" — it is "which failure mode can you live with." Here is what each layer actually gives you, based on the current state of their repositories.

## TL;DR: Quick Verdict

**Use crystal-db directly if your app has a handful of queries per endpoint** — you get the official shard, connection pooling, and no ORM abstraction tax. **Use Jennifer if you need real ORM features** (associations, validations, migration DSL, CTEs, JSON operators) and your database is MySQL < 8.0.36, PostgreSQL or SQLite. **Use Granite if you are already building on Amber or Kemal** and want model classes with a plain SQL fallback — but read the maintainership notice before you commit two years of code to it.

## Feature Comparison at a Glance

| Dimension | crystal-db | Jennifer | Granite |
|---|---|---|---|
| GitHub stars | 312 | 424 | 308 |
| Last repository push | 2026-08-20 | **2025-01-25** | 2026-08-05 |
| Abstraction level | Driver API (no models) | Full ActiveRecord-style ORM | Model layer + query builder |
| Config file | `shard.yml` + connection URI | `shard.yml` + `database.yml` / `DATABASE_URL` | `shard.yml` + registered connection |
| Migrations | None (bring your own) | Built in, via `sam.cr` | Delegated to **micrate** |
| Query style | SQL strings, parameterised | Chainable DSL + SQL | Query builder + raw SQL via `#all` |
| Associations | Manual joins | `belongs_to`, `has_many`, `has_one`, HABTM, polymorphic | `belongs_to`, `has_many`, `has_one` |
| Validations | None | Built in, extendable | Built in |
| License | MIT | MIT | MIT |
| Maintenance signal | Officially maintained by the Crystal team | Slow; MySQL 8.0.36+ unsupported | Actively seeking maintainers |
| Best fit | Small services, analytics jobs, maximum control | Feature-complete apps on older MySQL/PG/SQLite | Amber or Kemal projects, SQL-first teams |

## Decision Matrix: Pick by Use Case

| Your situation | Recommended layer | Why |
|---|---|---|
| A service with 10 endpoints and simple queries | **crystal-db** | Pooling and prepared statements are enough; an ORM adds mapping code you will not use |
| A CRUD app with many relations | **Jennifer** | Associations, validations and eager loading are exactly what you would otherwise hand-roll |
| Already on Amber (or Kemal) | **Granite** | Framework integration, model conventions and micrate migrations are ready to use |
| Reporting or batch jobs with heavy SQL | **crystal-db** | You want the SQL verbatim plus pooled connections, not an AST |
| MySQL 8.0.36 or newer | **crystal-db** | Jennifer explicitly does not support it; the driver layer does |
| Teams that prefer explicit schema files | **Granite + micrate** | Migrations are plain SQL files with an Up/Down marker |
| Apps that must survive upstream abandonment | **crystal-db** | It is the officially maintained building block the other two sit on |
| You need CTEs and JSON operators in the DSL | **Jennifer** | CTE support and JSON operators are first-class in its DSL |

## crystal-db: The Layer Everything Else Sits On

crystal-db is not an ORM and does not pretend to be. It defines a common API, and each database is a separate driver. The installation instructions from the README are deliberately split by intent — a library that should work with any driver depends on the abstraction; an application depends on the driver:

```yaml
# For a shard that must work with any driver
dependencies:
  db:
    github: crystal-lang/crystal-db
```

```yaml
# For an application targeting specific drivers
dependencies:
  sqlite3:
    github: crystal-lang/crystal-sqlite3
```

The available drivers, taken from the project's own README, are SQLite (`crystal-lang/crystal-sqlite3`), MySQL (`crystal-lang/crystal-mysql`), PostgreSQL (`will/crystal-pg`), ODBC (`naqvis/crystal-odbc`), Cassandra (`kaukas/crystal-cassandra`), DuckDB (`amauryt/crystal-duckdb`), Microsoft SQL Server (`wonderix/crystal-tds`) and Mimer SQL (`majorproblem/crystal-mimer`). Of those, the PostgreSQL driver is the most actively developed at **481 stars** with a push on **2026-09-07**, and SQLite sits at **161 stars** with an **2026-08-09** push.

Usage is plain SQL with real parameter binding. The example below is the README's, with the PostgreSQL note it makes in the comment:

```crystal
require "db"
require "sqlite3"

DB.open "sqlite3:./file.db" do |db|
  # When using the pg driver, use $1, $2, etc. instead of ?
  db.exec "create table contacts (name text, age integer)"
  db.exec "insert into contacts values (?, ?)", "John Doe", 30

  args = [] of DB::Any
  args << "Sarah"
  args << 33
  db.exec "insert into contacts values (?, ?)", args: args

  puts "max age:"
  puts db.scalar "select max(age) from contacts" # => 33

  puts "contacts:"
  db.query "select name, age from contacts order by age desc" do |rs|
    puts "#{rs.column_name(0)} (#{rs.column_name(1)})"
    # => name (age)
    rs.each do
      puts "#{rs.read(String)} (#{rs.read(Int32)})"
      # => Sarah (33)
      # => John Doe (30)
    end
  end
end
```

Two things in that snippet matter at scale. `DB.open` returns a pooled connection object, so you are not opening a socket per query; and `db.scalar` avoids materialising a result set when you only want one value. The SQL is not interpreted — `?` versus `$1` placeholders are the driver's business, as the comment states. What you do not get is any of the ORM conveniences: no model classes, no migrations, no validations. If you find yourself writing a third `ResultSet`-to-struct mapper, that is the signal to move up a layer. And if pooling becomes the bottleneck, the operational patterns in our [connection pool monitoring guide for PgBouncer, Pgpool and Odyssey](../2026-05-21-self-hosted-connection-pool-monitoring-pgbouncer-pgpool-odyssey-guide/) apply to Crystal services exactly as they do to any other PostgreSQL client.

## Jennifer: Full ORM, With One Sharp Caveat

Jennifer is the most complete ORM Crystal has. Its README states the feature set plainly: flexible model schema definition, relationships including polymorphic ones, extendable validations, query scopes, callbacks, database view support and SQL translations. It also ships a migration system driven by a small CLI called Sam.

Start with the shard entry, exactly as documented:

```yaml
dependencies:
  jennifer:
    github: imdrasil/jennifer.cr
    version: "~> 0.13.0"
```

Migrations are generated and then written in Crystal. This is the README's own example:

```crystal
class CreateContact < Jennifer::Migration::Base
  def up
    # Postgres requires to create specific enum type
    create_enum(:gender_enum, ["male", "female"])
    create_table(:contacts) do |t|
      t.string :name, {:size => 30}
      t.integer :age
      t.integer :tags, {:array => true}
      t.field :gender, :gender_enum
      t.timestamps
    end
  end

  def down
    drop_table :contacts
    drop_enum(:gender_enum)
  end
end
```

Models declare a `mapping` block and relationships:

```crystal
class Contact < Jennifer::Model::Base
  with_timestamps
  mapping(
    id: Primary64, # is an alias for Int64? primary key
    name: String,
    gender: { type: String?, default: "male" },
    age: { type: Int32, default: 10 },
    description: String?,
    created_at: Time?,
    updated_at: Time?
  )

  has_many :facebook_profiles, FacebookProfile
  has_and_belongs_to_many :countries, Country
  has_one :passport, Passport

  validates_inclusion :age, 13..75
  validates_length :name, minimum: 1, maximum: 15

  scope :older { |age| where { _age >= age } }
end
```

The query DSL is where Jennifer earns its keep — eager loading, aggregates and null ordering are all expressible without dropping to SQL:

```crystal
Contact
  .all
  .left_join(Passport) { _contact_id == _contact__id }
  .order(id: :asc).order(Contact._name.asc.nulls_last)
  .with_relation(:passport)
  .to_a

Contact.all.group(:gender).group_avg(:age, PG::Numeric)
Contact.all.explain # => Seq Scan on contacts  (cost=0.00..14.30 rows=100.0 width=320)
```

`#explain` on a query object is the underrated feature here: you can assert on plans in specs instead of guessing why a page slowed down. Logging integrates with Crystal's standard `Log` module rather than a private framework:

```crystal
Log.setup "db", :debug, Log::IOBackend.new(formatter: Jennifer::Adapter::DBFormatter)
```

Now the caveats, which are the reason this layer needs a decision rather than a default. The README states that **MySQL 8.0.36 and above is not supported at the moment** — that rules Jennifer out for many current-managed MySQL deployments. The last repository push was **2025-01-25**, so upstream velocity is low. And its tooling assumes you adopt Sam as a command runner. None of these are fatal for a PostgreSQL application with a stable schema, but all three should be part of your risk assessment.

## Granite: Models for Amber and Kemal

Granite is what most Amber applications use, and its README points out it works with Kemal or anything else too.

![The Amber framework, which Granite was originally built to serve](/img/screenshots/granite-amber-logo.jpg "Amber framework, the original target of the Granite ORM")

Dependencies are declared per driver:

```yaml
dependencies:
  granite:
    github: amberframework/granite

  # Pick your database
  pg:
    github: will/crystal-pg
```

A connection is registered before the models are loaded, and a model looks like this:

```crystal
Granite::Connections << Granite::Adapter::Pg.new(name: "pg", url: "YOUR_DATABASE_URL")

require "granite/adapter/pg"

class Post < Granite::Base
  connection pg
  table posts # Name of the table to use for the model, defaults to class name snake cased

  column id : Int64, primary: true # Primary key, defaults to AUTO INCREMENT
  column name : String? # Nilable field
  column body : String # Not nil field
end
```

Queries use a builder that supports operators and raw clauses side by side, which is Granite's main ergonomic advantage over hand-written SQL:

```crystal
posts = Post.where(published: true, author_id: User.first!.id)
Post.where(:created_at, :gt, Time.local - 7.days)
Post.order(created_at: :desc, title: :asc)

# Raw clause with a placeholder — not validated, so parameterise everything
Post.where(:created_at, :gt, Time.local - 7.days)
  .where("LOWER(author_name) = $", name)
```

Supported operators are `:eq`, `:gteq`, `:lteq`, `:neq`, `:gt`, `:lt`, `:nlt`, `:ngt`, `:ltgt`, `:in`, `:nin`, `:like` and `:nlike`. Migrations are not built in; the docs delegate them to **micrate**, with a tiny CLI shim and plain SQL migration files:

```crystal
#! /usr/bin/env crystal
require "micrate"
require "pg"

Micrate::DB.connection_url = ENV["DATABASE_URL"]
Micrate::Cli.run
```

```sql
-- +micrate Up
CREATE TABLE posts(
  id BIGSERIAL PRIMARY KEY,
  title VARCHAR NOT NULL,
  body TEXT NOT NULL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- +micrate Down
DROP TABLE posts;
```

The trade-off is the same as any SQL-file workflow: nothing infers your schema from your models, so the two can drift. Granite's own repository even ships a Docker Compose setup for running its specs against a real database, which is a good starting point for a reproducible development stack:

```yaml
version: '2'
services:
  spec:
    extends:
      file: ../docker-compose.yml
      service: spec
    environment:
      CURRENT_ADAPTER: pg
    depends_on:
      - pg
  pg:
    image: postgres:${PG_VERSION}
    environment:
      POSTGRES_PASSWORD: pass
```

Rename `spec` to your application service, keep the `pg` service, and you have the same topology the maintainers test against. That is the strongest argument for Granite: a real, versioned Postgres pair in the repo rather than a wiki page. The strongest argument against it is the maintainership notice — a project asking for volunteers is a project you should depend on with a plan B, which in this case is crystal-db plus your own structs.

## Pitfalls and Gotchas

- **Placeholder syntax is driver-specific.** `?` for SQLite and MySQL, `$1`/`$2` for PostgreSQL. Copying a query between drivers without changing placeholders is the most common silent failure in Crystal database code.
- **Crystal is compiled, so schema drift breaks at build time or at 3 a.m.** A model with a `String` column against a nullable database column compiles fine and explodes on a real `NULL`. Make database columns match your type nilability, not the reverse.
- **Jennifer's MySQL ceiling is a hard limit.** If you are on MySQL 8.0.36+, do not plan a migration to Jennifer without checking the issue tracker first.
- **Granite needs a second tool for schema.** Adding micrate is not optional if you want versioned migrations; the ORM does not generate them.
- **Acknowledged single-maintainer risk.** Both ORMs depend heavily on one or two people. Either is fine as a dependency, but pin versions in `shard.lock` and commit that file — Crystal's shard resolution is reproducible only if you keep the lock.
- **Pool size defaults bite under load.** `DB.open` pools connections, and an under-sized pool turns into latency that looks like database slowness. Set the pool size explicitly and monitor it, exactly as you would for any other PostgreSQL client.
- **Do not map everything.** Wrapping every table in a model forces the ORM to materialise objects you never use. For reporting endpoints, drop to `db.query` and read columns directly.

## FAQ

**Is Granite or Jennifer abandoned?**
Neither is abandoned today, but both carry maintenance risk signals worth reading. Granite's README explicitly asks for maintainers, and its last push was 2026-08-05. Jennifer's last push was 2025-01-25, with a documented gap on MySQL 8.0.36 and newer. crystal-db is the only layer in this comparison that is maintained as part of the official Crystal organisation.

**Can I mix crystal-db and an ORM in one project?**
Yes, and it is a common pattern. The ORM sits on top of crystal-db, so both share the same drivers and pooling. Teams typically use the ORM for CRUD and drop to `db.query` for reporting or bulk operations inside the same binary.

**Which one has the best migration story?**
Jennifer, because migrations are Crystal classes with an explicit `up` and `down` and are part of the same tool. Granite delegates to micrate and plain SQL files, which some teams prefer because the SQL is visible. crystal-db has no migration system at all — you choose one.

**What about connection pooling?**
All three share crystal-db's pool, so the tuning knobs are identical. The design question is sizing: high-throughput Crystal services often benefit from a smaller pool plus an external pooler, as described in our [PgBouncer, Pgpool and Odyssey comparison](../2026-05-21-self-hosted-connection-pool-monitoring-pgbouncer-pgpool-odyssey-guide/).

**Does any of this change what framework I should use?**
If you have not picked a framework yet, our [Crystal web framework comparison covering Kemal, Lucky and Amber](../2026-08-31-crystal-web-frameworks-kemal-lucky-amber-comparison/) is the better starting point — Amber pairs with Granite, Kemal is framework-agnostic, and either can run on crystal-db directly. The same trade-offs appear in other ecosystems too: see our [Rust database library comparison of Diesel, SeaORM and rusqlite](../2026-06-23-rust-database-libraries-diesel-seaorm-rusqlite/) for a different language's answer to the same problem.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "crystal-db vs Jennifer vs Granite in 2026: Picking a Crystal Database Layer Without Regret",
  "description": "crystal-db, Jennifer and Granite compared for Crystal applications in 2026: real shard.yml, model, migration and query code from official repos, plus maintenance signals and a decision matrix.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
