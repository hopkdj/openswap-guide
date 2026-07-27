---
title: "Go SQL Query Builders Compared: squirrel vs goqu vs dbr vs sqlboiler"
date: "2026-07-27"
tags: ["go", "golang", "sql", "database", "orm", "query-builder"]
draft: false
---

Go's `database/sql` package provides a solid foundation for database access, but writing raw SQL strings quickly becomes tedious and error-prone. String concatenation for dynamic WHERE clauses, manual placeholder counting, and type coercion are recurring pain points. This is where SQL query builders shine — they provide a fluent, type-safe API for constructing SQL queries while leaving you in full control of the generated SQL.

In this guide, we compare four popular Go SQL query construction libraries — **squirrel**, **goqu**, **dbr**, and **sqlboiler** — across API design, type safety, performance, and integration patterns with the standard library.

## Why Not a Full ORM?

Go's philosophy favors explicitness over magic. Full ORMs like GORM exist (and we cover them in our [Go web frameworks comparison](../2026-07-06-go-web-frameworks-gin-echo-fiber-chi/)), but many Go developers prefer query builders that generate SQL without hiding the database. Query builders give you:

- **Compile-time safety** for column names and query structure
- **Readable, composable query construction** instead of string building
- **Direct SQL visibility** — you always know what query will execute
- **No hidden N+1 problems** common with lazy-loading ORMs

## Comparison Table

| Feature | squirrel | goqu | dbr | sqlboiler |
|---------|----------|------|-----|-----------|
| GitHub Stars | 7,200+ | 2,400+ | 900+ | 6,900+ |
| Approach | Fluent query builder | Expression-based DSL | Lightweight struct mapping | Code generation from schema |
| Type Safety | Partial (string columns) | Strong (expression types) | Partial (struct tags) | Full (generated types) |
| SQL Dialects | PostgreSQL, MySQL, SQLite | PostgreSQL, MySQL, SQLite | PostgreSQL, MySQL, SQLite | PostgreSQL, MySQL, SQLite, MSSQL |
| Learning Curve | Low | Moderate | Low | Low (codegen is automatic) |
| NULL Handling | Manual (pointers) | Expression-based | Manual (pointers) | Generated nullable types |
| Migration Support | None | None | None | None (use golang-migrate) |
| Last Commit | 2026 | 2026 | 2026 | 2026 |

## squirrel: The Fluent Query Builder

`squirrel` (by Masterminds) is the most popular Go query builder, used by thousands of projects including Grafana and Mattermost. Its API reads like SQL translated into method chains.

```go
// go get github.com/Masterminds/squirrel

import (
    "github.com/Masterminds/squirrel"
    _ "github.com/lib/pq"
)

func FindActiveUsers(db *sql.DB, minAge int, limit uint64) ([]User, error) {
    query, args, err := squirrel.
        Select("id", "name", "email", "created_at").
        From("users").
        Where(squirrel.Eq{"status": "active"}).
        Where(squirrel.Gt{"age": minAge}).
        OrderBy("created_at DESC").
        Limit(limit).
        PlaceholderFormat(squirrel.Dollar).
        ToSql()

    if err != nil {
        return nil, err
    }

    rows, err := db.Query(query, args...)
    // ... scan rows
}
```

Dynamic WHERE clauses compose naturally:

```go
func SearchUsers(db *sql.DB, filters UserFilter) ([]User, error) {
    q := squirrel.Select("*").From("users")
    
    if filters.Status != "" {
        q = q.Where(squirrel.Eq{"status": filters.Status})
    }
    if filters.MinAge > 0 {
        q = q.Where(squirrel.Gt{"age": filters.MinAge})
    }
    if filters.Search != "" {
        q = q.Where("name ILIKE ?", "%"+filters.Search+"%")
    }
    
    query, args, _ := q.ToSql()
    // ...
}
```

**Best for:** Teams that want a simple, proven query builder with minimal abstraction, projects with complex dynamic query requirements.

## goqu: Expression-Based Type Safety

`goqu` takes a more strongly-typed approach, using Go expressions to build queries with compile-time guarantees. Column names are checked, and complex joins are expressed through a composable expression model.

```go
// go get github.com/doug-martin/goqu/v9

import (
    "github.com/doug-martin/goqu/v9"
    _ "github.com/doug-martin/goqu/v9/adapters/postgres"
)

func ActiveUsersWithOrders(db *sql.DB) error {
    dialect := goqu.Dialect("postgres")
    users := dialect.From("users")
    orders := dialect.From("orders")
    
    query, args, _ := dialect.From(users).
        Select("users.id", "users.name", goqu.COUNT("orders.id").As("order_count")).
        InnerJoin(orders, goqu.On(users.Col("id").Eq(orders.Col("user_id")))).
        Where(users.Col("status").Eq("active")).
        GroupBy("users.id", "users.name").
        Having(goqu.COUNT("orders.id").Gt(5)).
        ToSQL()
    
    rows, _ := db.Query(query, args...)
    // ...
}
```

The expression-based API means join conditions and WHERE clauses are expressed as typed expressions, not strings. If you misspell a column name, the compiler catches it.

```go
// Type-safe column reference
users.Col("status")  // compile-time checked

// Complex WHERE with AND/OR composition
goqu.Or(
    users.Col("role").Eq("admin"),
    goqu.And(
        users.Col("status").Eq("active"),
        users.Col("age").Gt(18),
    ),
)
```

**Best for:** Teams that prioritize type safety, complex queries with many joins, projects where query correctness is critical.

## dbr: Lightweight Struct-to-SQL

`dbr` (by gocraft) keeps things minimal. It maps Go structs to SQL rows with minimal ceremony, providing just enough abstraction over `database/sql` to eliminate boilerplate without hiding the database.

```go
// go get github.com/gocraft/dbr/v2

import (
    "github.com/gocraft/dbr/v2"
    _ "github.com/lib/pq"
)

type User struct {
    ID        int64     `db:"id"`
    Name      string    `db:"name"`
    Email     string    `db:"email"`
    Status    string    `db:"status"`
    CreatedAt time.Time `db:"created_at"`
}

func GetActiveUsers(sess *dbr.Session) ([]User, error) {
    var users []User
    _, err := sess.
        Select("*").
        From("users").
        Where("status = ?", "active").
        OrderBy("created_at DESC").
        Load(&users)
    return users, err
}

func InsertUser(sess *dbr.Session, u *User) error {
    _, err := sess.
        InsertInto("users").
        Columns("name", "email", "status").
        Record(u).
        Exec()
    return err
}
```

`dbr` also supports transactions with automatic rollback:

```go
func TransferCredits(sess *dbr.Session, from, to int64, amount float64) error {
    tx, _ := sess.Begin()
    defer tx.RollbackUnlessCommitted()
    
    tx.Update("accounts").
        Set("balance", dbr.Expr("balance - ?", amount)).
        Where("id = ? AND balance >= ?", from, amount).
        Exec()
    
    tx.Update("accounts").
        Set("balance", dbr.Expr("balance + ?", amount)).
        Where("id = ?", to).
        Exec()
    
    return tx.Commit()
}
```

**Best for:** Teams that want minimal abstraction, simple CRUD operations, projects that prefer explicit SQL with struct mapping.

## sqlboiler: Code Generation from Database Schema

`sqlboiler` takes a fundamentally different approach: instead of writing queries by hand, it reads your database schema and generates type-safe Go code. Every table becomes a struct, every column becomes a typed field, and every relationship becomes a generated method.

```bash
# Install
go install github.com/volatiletech/sqlboiler/v4@latest
go install github.com/volatiletech/sqlboiler/v4/drivers/sqlboiler-psql@latest

# Generate models from database
sqlboiler psql -c sqlboiler.toml -o models
```

The generated code provides fully typed query APIs:

```go
import (
    "context"
    "github.com/volatiletech/sqlboiler/v4/queries/qm"
)

func ActiveUsers(ctx context.Context, db *sql.DB) (models.UserSlice, error) {
    return models.Users(
        qm.Where("status = ?", "active"),
        qm.OrderBy("created_at DESC"),
        qm.Limit(10),
    ).All(ctx, db)
}

// With eager loading of related orders
func UsersWithOrders(ctx context.Context, db *sql.DB) (models.UserSlice, error) {
    return models.Users(
        qm.Load(models.UserRels.Orders),
        qm.Where("users.status = ?", "active"),
    ).All(ctx, db)
}
```

Because the models are generated from your actual schema, column names, types, and relationships are always correct. If you rename a column and regenerate, compilation fails wherever you use the old name — a powerful safety net as schemas evolve.

**Best for:** Teams with well-defined database schemas, projects that value compile-time safety, applications with complex relationships and eager loading needs.

## Why Self-Host Your Database Layer?

Choosing the right query builder affects more than just developer experience — it impacts database performance, connection management, and operational visibility. All four libraries work with standard `database/sql` connection pools, which you can configure for optimal throughput with your self-hosted PostgreSQL or MySQL instances. For connection pooling at scale, pair your query builder with PgBouncer to manage hundreds of concurrent connections efficiently.

For more Go database ecosystem guides, see our [Go web frameworks comparison](../2026-07-06-go-web-frameworks-gin-echo-fiber-chi/) and our [Go caching libraries overview](../2026-06-19-self-hosted-cache-libraries-golang-lru-gocache-bigcache-tin/).

## Choosing Your Approach: Decision Matrix

Your choice depends on where your team sits on the abstraction spectrum:

| Use Case | Recommended Tool |
|----------|-----------------|
| Simple CRUD, minimal dependencies | dbr |
| Dynamic queries, proven track record | squirrel |
| Complex joins, type safety priority | goqu |
| Schema-first, compile-time guarantees | sqlboiler |
| Full ORM with migrations | GORM (separate guide) |

The Go community's preference for explicitness means you can start with `squirrel` or `dbr` for a new project and migrate to `sqlboiler` as your schema stabilizes — the standard `database/sql` interface ensures all these tools interoperate cleanly.

## FAQ

### Do I need a query builder or should I just write raw SQL?

Raw SQL with `database/sql` works well for simple applications with few tables and static queries. Query builders add value when you have dynamic WHERE clauses (search filters, faceted navigation), need to compose queries from multiple conditions, or want to avoid manual placeholder counting bugs. If you find yourself string-concatenating SQL with `fmt.Sprintf`, it's time for a query builder.

### Can I mix query builders with raw SQL?

Yes — all four libraries ultimately produce `(string, []interface{})` that you pass to `db.Query()`. You can use a query builder for complex dynamic queries and write raw SQL for simple static ones in the same codebase. `dbr` makes this especially natural since it's just a thin wrapper around `database/sql`.

### How does sqlboiler handle schema changes?

You regenerate the models after each schema migration. The typical workflow: run your migration (e.g., `golang-migrate up`), then run `sqlboiler psql` to regenerate models. If the migration removes a column that your code references, compilation fails — catching the issue before it reaches production. Most teams add the regeneration step to their CI pipeline.

### Is there a performance overhead to query builders?

Minimal — typically under one microsecond per query construction. The database execution time dominates total query latency by orders of magnitude. `sqlboiler` has zero runtime query construction overhead since models are generated code. The other three do light string building at runtime, but it's negligible compared to network and database I/O.

### How do I handle complex transactions with query builders?

All four libraries work with `database/sql` transactions. Use `db.Begin()` to create a transaction, pass the `*sql.Tx` to your query builder methods (they accept the `sql.Executor` interface), and commit or rollback as normal. `dbr` provides the cleanest transaction API with `defer tx.RollbackUnlessCommitted()`.
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go SQL Query Builders Compared: squirrel vs goqu vs dbr vs sqlboiler",
  "description": "Compare Go SQL query construction libraries — squirrel, goqu, dbr, and sqlboiler — covering fluent APIs, code generation, type safety, and integration with database/sql for self-hosted PostgreSQL and MySQL.",
  "datePublished": "2026-07-27",
  "dateModified": "2026-07-27",
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
