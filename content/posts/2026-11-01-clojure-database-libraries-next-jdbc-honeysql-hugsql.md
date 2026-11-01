---
title: "Clojure Database Libraries in 2026: next.jdbc vs HoneySQL vs HugSQL"
date: "2026-11-01"
tags: ["clojure", "database", "sql", "jdbc", "developer-tools"]
draft: false
---

You have a Clojure service, a Postgres database, and three libraries that all claim to be "the SQL layer." Pick wrong and you will spend the next two years writing `(first (jdbc/query ...))` wrappers around a wrapper — or worse, string-concatenating user input into a `WHERE` clause.

The confusion is structural: **next.jdbc, HoneySQL, and HugSQL solve three different problems**, and most teams need two of them. Treating them as competitors is the single most common architectural mistake in Clojure data code. Next.jdbc executes SQL and maps result sets. HoneySQL builds SQL from Clojure data structures. HugSQL loads SQL from files and turns them into functions.

Here is the short version before you read 1,600 more words.

## The 30-Second Verdict

**Use next.jdbc for everything that touches a database connection — no exceptions.** It is the foundation, and it replaced `clojure.java.jdbc` for good reason: less per-row overhead, protocol-based, `datafy`-aware.

**Add HoneySQL when your queries are dynamic** — filters assembled from request parameters, admin tables with 12 optional sort columns, reporting endpoints where the `GROUP BY` changes at runtime. You get composable data instead of string surgery.

**Add HugSQL when your queries are static and long** — CTEs, window functions, `LATERAL` joins, `ON CONFLICT DO UPDATE`. SQL is a language; write it in `.sql` files where your DBA can read it and your editor can highlight it.

If you only take one thing from this article: **next.jdbc + HugSQL is the strongest pairing for application backends, next.jdbc + HoneySQL for admin and reporting surfaces.** Very few projects need all three.

## Comparison Table: Three Layers, Not Three Rivals

| Dimension | next.jdbc | HoneySQL | HugSQL |
|---|---|---|---|
| Role | Execution + result mapping | SQL generation from data | SQL templates in files |
| Latest release | 1.4.72 | 2.8.85 | 0.5.3 |
| GitHub stars | 870 | 1,931 | 710 |
| Last repo activity | 2026-10-27 | 2026-10-28 | 2024-12-02 |
| License | EPL-1.0 | EPL-2.0 | Apache-2.0 |
| Composable at runtime | No (SQL string in) | Yes (maps all the way down) | Partially (fragments) |
| Dynamic `WHERE` clauses | Manual | Native | Awkward |
| Long SQL readability | Poor | Poor | Excellent |
| Result set → Clojure maps | Yes, qualified keywords | N/A | Delegates to next.jdbc |
| Streaming 1M rows | `plan` + `reduce` | N/A | Yes, via next.jdbc |
| Learning curve | 1 hour | 3 hours | 1 hour + SQL fluency |

Note the last-activity column. HugSQL's *artifact* is stable at 0.5.3 and its repo has been quiet since late 2024, while next.jdbc and HoneySQL ship snapshots continuously. Stable is not abandoned — HugSQL's API is small and SQL-shaped — but you should know that you are adopting a finished library, not an actively evolving one.

## Decision Matrix: Pick by Use Case

| Your situation | Recommended stack | Why |
|---|---|---|
| REST API with 20 fixed queries | next.jdbc + HugSQL | SQL stays readable and reviewable in PRs |
| Admin panel with dynamic filters | next.jdbc + HoneySQL | Build `:where` vectors from request params |
| Reporting / analytics endpoints | next.jdbc + HoneySQL | `:group-by`, `:having`, window fns compose |
| Migrating off `clojure.java.jdbc` | next.jdbc only | 1:1 functional mapping, drop-in |
| Batch ETL over millions of rows | next.jdbc alone (`plan`) | Avoid realizing maps you throw away |
| Multi-tenant with per-tenant schemas | next.jdbc + HoneySQL | Schema names as data, not strings |
| Team has SQL-fluent DBAs | next.jdbc + HugSQL | `.sql` files are the contract |
| Prototype / script | next.jdbc alone | Fewer moving parts |

## next.jdbc — The Execution Layer You Should Not Skip

Add it to `deps.edn`:

```clojure
{:deps {org.clojure/clojure       {:mvn/version "1.12.0"}
        com.github.seancorfield/next.jdbc {:mvn/version "1.4.72"}
        com.zaxxer/HikariCP       {:mvn/version "6.2.1"}
        org.postgresql/postgresql {:mvn/version "42.7.4"}}}
```

The core discipline is **DataSource first, everything else second**. Create one pooled `DataSource` at startup and pass it around; never build a connection per request:

```clojure
(ns app.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defonce ds
  (jdbc/get-datasource
    {:dbtype   "postgresql"
     :host     "localhost"
     :port     5432
     :dbname   "shop"
     :user     "app"
     :password (System/getenv "DB_PASSWORD")
     :maximumPoolSize 20}))

;; Single row -> map with qualified keys like :orders/id
(jdbc/execute-one! ds
  ["select id, total_cents, status from orders where id = ?" 42]
  {:builder-fn rs/as-unqualified-lower-maps})
```

That `:builder-fn` option matters more than it looks. By default next.jdbc returns **qualified keywords** — `:orders/id`, `:orders/total_cents`. That is excellent for joins (no column-name collisions) and mildly annoying for templates. Use `rs/as-unqualified-lower-maps` for API layers, keep the qualified default inside your domain code.

For large result sets, stop using `execute!`. It realizes the entire vector of maps:

```clojure
;; BAD for 1M rows: allocates 1M persistent maps
(count (jdbc/execute! ds ["select * from events"]))

;; GOOD: stream, reduce, short-circuit with `reduced`
(transduce
  (map :events/kind)
  (frequencies)
  (jdbc/plan ds ["select kind from events"]))
```

`plan` returns an `IReduceInit` that holds the `ResultSet` open only for the duration of the reduction. Peak heap stays flat. If you have ever watched a Clojure service OOM on a `select *` that "worked fine in staging," this is the fix.

Transactions are explicit and nest correctly:

```clojure
(jdbc/with-transaction [tx ds {:isolation :serializable}]
  (jdbc/execute-one! tx ["update accounts set balance = balance - ? where id = ?" 500 1])
  (jdbc/execute-one! tx ["update accounts set balance = balance + ? where id = ?" 500 2]))
```

**What it does not do:** build SQL. Every call passes a vector of SQL string + parameters. If you need conditional SQL, you are back to `str`/`cond` — which is exactly the pain that pushes teams to HoneySQL.

## HoneySQL — SQL as Data, Composable at Runtime

HoneySQL turns a Clojure map into `[sql & params]`. It is the right answer to a very specific problem: **a query whose shape is not known until a request arrives.**

```clojure
(require '[honey.sql :as sql])

(defn order-search [{:keys [status min-total sort limit]}]
  (-> {:select   [:o/id :o/total_cents :c/name]
       :from     [[:orders :o]]
       :join     [[:customers :c] [:= :c/id :o/customer_id]]
       :where    [:and
                   [:= :o.deleted_at nil]
                   (when status [:= :o/status (keyword status)])
                   (when min-total [:>= :o/total_cents min-total])]
       :order-by [(or (keyword "o" (name (or sort :id))) :o/id)]
       :limit    (or limit 50)}
      (update :where (fn [w] (if (= :and (first w))
                               (into [:and] (remove nil? (rest w)))
                               w)))
      sql/format))
```

Called with `{:status "paid" :min-total 5000}`, that produces:

```clojure
["SELECT o.id, o.total_cents, c.name FROM orders AS o
  JOIN customers AS c ON c.id = o.customer_id
  WHERE ((o.deleted_at IS NULL) AND (o.status = ?) AND (o.total_cents >= ?))
  ORDER BY o.id LIMIT ?"
 "paid" 5000 50]
```

Three things to internalise:

1. **`nil` in `:where` must be stripped** before `sql/format`, otherwise you get a `nil` inside `[:and ...]` and a broken statement. The `update` above is the smallest honest fix; production code usually builds a vector with `cond->`.
2. **`sql/format` accepts `:params` for `IN` clauses.** `{:where [:in :o/id ids]}` expands to `IN (?, ?, ?)` automatically — no string building.
3. **v2 changed function syntax.** `[:count :*]` is no longer valid in v2; use `[[:count :*] :total]` in `:select` or the `:helper` style. Old blog posts showing `[:count :*]` are v1 and will fail.

HoneySQL generates SQL; it does not run it. Pair it with next.jdbc:

```clojure
(let [[sql & params] (order-search params)]
  (jdbc/execute! ds (into [sql] params)
                 {:builder-fn rs/as-unqualified-lower-maps}))
```

That two-line bridge is the whole integration. There is no adapter library to keep in sync.

**Where it hurts:** a 200-line analytical query with four CTEs becomes a 400-line nested map that nobody can review. For those, write the SQL in a file and use HugSQL. HoneySQL wins on shape variability, not on length.

## HugSQL — SQL Files That Compile Into Functions

HugSQL reads `.sql` files with annotation comments and generates Clojure functions from them. Your SQL lives where SQL belongs.

```clojure
;; deps.edn
{:deps {com.layerware/hugsql {:mvn/version "0.5.3"}}}
```

`resources/sql/orders.sql`:

```sql
-- :name top-customers :? :*
-- :doc Customers ranked by lifetime spend, excluding refunded orders
select c.id, c.email, sum(o.total_cents) as lifetime_cents
from customers c
join orders o on o.customer_id = c.id
where o.status = 'paid'
  and o.created_at >= now() - (:window_days || ' days')::interval
  and (:min_total::int is null or o.total_cents >= :min_total::int)
group by c.id, c.email
having sum(o.total_cents) > 0
order by lifetime_cents desc
limit :limit
```

And the namespace:

```clojure
(ns app.sql
  (:require [hugsql.core :as hugsql]))

(hugsql/def-db-fns "sql/orders.sql")

;; (top-customers ds {:window_days 30 :min_total nil :limit 20})
```

The `-- :name ... :? :*` header says: function name `top-customers`, accepts parameters, returns a sequence of maps. The other sigils you will use constantly:

| Sigil | Meaning | Returns |
|---|---|---|
| `:?` | takes params | — |
| `:!` | DML / insert | update count |
| `:<!` | insert returning | inserted row |
| `:n` | no params | — |
| `:*` | many rows | seq of maps |
| `:1` | one row | map or nil |
| `:affected` | update count | number |

The conditional-SQL trick above (`(:min_total::int is null or ...)`) is the standard way to express optional filters without building strings — Postgres lets you cast the parameter inline. It reads oddly the first time and then becomes second nature.

HugSQL delegates execution to next.jdbc under the hood in 0.5.x, so `ds` is the same DataSource and the result maps behave identically.

**Where it hurts:** anything assembled at runtime. Building a `-- :name` query with a variable `IN` list from user input is exactly the kind of string surgery HugSQL was meant to eliminate, and you will end up back in HoneySQL for those endpoints. Also note the repo's quiet since 2024: it works, it is done, but do not expect new sigils.

## Where Each One Breaks: Real Pitfalls

**1. `execute!` with a large `IN` clause.** `{:where [:in :id (range 20000)]}` generates 20,000 placeholders. Postgres has a hard limit near 32,767 bind parameters and query planning degrades long before that. Batch into chunks of 1,000 or use `= any(?)` with a JDBC array.

**2. Qualified keywords leaking into JSON.** next.jdbc's default `:table/column` keys serialize as `{"orders/id": 1}` when you hand them to Cheshire. Either normalize at the boundary with `rs/as-unqualified-lower-maps` or map keys explicitly — do not let a naming choice in the DB layer become your public API contract.

**3. `with-transaction` without an isolation level.** The default is the driver's default, which is `READ COMMITTED` on Postgres. Read-modify-write on a balance needs `:serializable` or an explicit `SELECT ... FOR UPDATE`. Clojure's immutability does not make your database atomic.

**4. HoneySQL and `nil` sort columns.** `:order-by [(keyword sort-col)]` where `sort-col` comes from a query string is an injection vector. Whitelist the column names:

```clojure
(def sortable #{:id :created_at :total_cents})
(let [col (if (contains? sortable (keyword sort)) (keyword sort) :id)]
  ...)
```

**5. HugSQL parameter names are not validated at compile time** unless you enable `:quoting`/snippet checks. A typo in `:limit` versus `:max` compiles fine and silently sends the wrong map key. Write one test per HugSQL query namespace that calls each function with a dummy DataSource — the failure mode is a runtime `NullPointerException` deep in the JDBC driver.

**6. Connection pool sizing.** HikariCP's default `maximumPoolSize` is 10, which silently caps your concurrency. With 20 HTTP worker threads and 10 connections, 10 threads queue. Set the pool explicitly and keep it below your Postgres `max_connections` divided by instance count.

## Migration Notes

From `clojure.java.jdbc`, the mapping is mostly mechanical: `query` → `execute!`, `query` + `:result-set-fn first` → `execute-one!`, `db-do-commands` → `jdbc/execute!`. The one real behavioural change is **qualified result keys**, which is why the migration guide is worth reading in full rather than skimming.

Between HoneySQL and HugSQL there is no migration — pick per endpoint. A codebase with both is normal and healthy, as long as the boundary is documented: *dynamic queries in HoneySQL, fixed queries in `.sql` files.*

If you are coming from an ORM (Eloquent, Hibernate, ActiveRecord), the mental shift is that all three libraries are **SQL-first**. There is no lazy loading, no identity map, no dirty checking. You write the query, you get maps. For read-heavy APIs that is a feature; for deep object graphs it means more explicit joins.

## Why Bother With Any of This?

The alternative is JDBC directly, and the cost is real: `ResultSet` iteration is verbose, closing resources correctly needs `with-open` at every level, and column extraction by index breaks on every schema change. next.jdbc gives you maps and pooled DataSources in a few lines.

The second alternative is a full Clojure ORM such as Toucan or a Next.jdbc wrapper like HoneySQL-plus-repository stack. Those add a layer you will fight the moment a query needs a CTE. The three libraries here stay out of your way, which is why they have survived a decade with near-identical APIs.

For the rest of the Clojure stack, our [Clojure testing frameworks comparison](../2026-09-06-clojure-testing-frameworks-clojure-test-kaocha-midje-comparison/) covers Kaocha and Midje, the [Clojure JSON libraries guide](../2026-09-08-clojure-json-libraries-cheshire-jsonista-data-json-comparison/) handles the serialization boundary where your result maps turn into JSON, and the [Ring vs Compojure vs Reitit comparison](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/) covers the HTTP layer sitting above all of it. If you are validating the parameters that feed these queries, the [Clojure data validation article](../2026-09-05-clojure-data-validation-malli-schema-spec-comparison/) is the natural companion.

## FAQ

**Do I need HoneySQL if I already use HugSQL?**
Only for endpoints whose query shape changes at runtime. If every query in your app is written by hand and reviewed in a PR, HugSQL alone plus next.jdbc is enough. The moment you build a `WHERE` clause from optional request parameters, HoneySQL pays for itself.

**Is HugSQL abandoned because its repo has not been updated since 2024?**
HugSQL 0.5.3 is a finished, small library. It has no runtime dependencies of its own beyond next.jdbc and the Clojure CLI. "No commits" here means "no bugs to fix," not "unmaintained." That said, if you need a feature added, you will be writing it yourself.

**Which one is fastest?**
next.jdbc's `plan` is the fastest path because it never realizes intermediate maps. Between HoneySQL and HugSQL the difference is SQL generation overhead measured in microseconds — irrelevant next to the database round trip. Optimise your indexes before your SQL builder.

**Can I use all three together?**
Yes, and many production codebases do: next.jdbc as the execution primitive, HoneySQL for the admin and reporting surfaces, HugSQL for the fixed application queries. Keep them in separate namespaces so a reviewer knows which style to expect.

**What about ClojureScript or Babashka?**
next.jdbc works in Babashka with the built-in `next.jdbc` namespace. HoneySQL runs in Babashka too. HugSQL requires reading resources at runtime, which works but is less convenient in a single-file script — for scripts, HoneySQL or plain `jdbc/execute!` is usually simpler.

**How do I handle migrations?**
None of these three do migrations. Use Migratus or Ragtime, run them from the same `deps.edn` alias, and keep migration SQL in `.sql` files alongside your HugSQL queries so the schema and the queries are reviewed together.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clojure Database Libraries in 2026: next.jdbc vs HoneySQL vs HugSQL",
  "description": "A practical comparison of next.jdbc, HoneySQL, and HugSQL for Clojure database access, with real code examples, a decision matrix, and migration pitfalls.",
  "datePublished": "2026-11-01",
  "dateModified": "2026-11-01",
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
