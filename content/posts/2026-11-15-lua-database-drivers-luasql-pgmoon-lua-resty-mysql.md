---
title: "Lua Database Drivers in 2026: LuaSQL vs pgmoon vs lua-resty-mysql — Which One Won't Bite You?"
date: "2026-11-15"
description: "A hands-on comparison of the three Lua database drivers people actually deploy in 2026: LuaSQL, pgmoon and lua-resty-mysql. Real code, real pooling behaviour, and the pitfalls that take down production gateways."
tags: ["lua", "database", "openresty", "postgresql", "mysql"]
cover: "/img/screenshots/lua-database-drivers.jpg"
draft: false
---

Your nginx worker just froze for 800 milliseconds. No CPU spike, no disk pressure — just one Lua handler doing a blocking `SELECT` inside a cosocket-driven gateway. That single line of code stalls every request that worker was multiplexing, and your p99 latency graph turns into a cliff. Choosing a Lua database driver is not a style preference; it decides whether your gateway stays concurrent under load or collapses one worker at a time.

This guide compares the three drivers that still matter in 2026, with live repository data, real API examples pulled from each project, and the operational traps that only show up in production.

**TL;DR:** Use **lua-resty-mysql** if you are on OpenResty and speak MySQL. Use **pgmoon** if you are on OpenResty and speak PostgreSQL — it is the only pure-Lua Postgres driver worth deploying. Use **LuaSQL** only when you need one API across SQLite, Oracle, ODBC or Firebird, and you are not inside an nginx event loop.

## The Contenders at a Glance

| | **LuaSQL** | **pgmoon** | **lua-resty-mysql** |
|---|---|---|---|
| **GitHub stars** | 580 | 436 | 727 |
| **Last push** | 2026-08-03 | 2026-09-09 | 2026-06-20 |
| **Implementation** | C bindings per driver | Pure Lua (MoonScript source) | Pure Lua, cosocket-based |
| **Databases** | MySQL, PostgreSQL, SQLite, Oracle, ODBC, ADO, Firebird | PostgreSQL only | MySQL / MariaDB only |
| **Execution model** | Blocking | Non-blocking inside OpenResty, blocking via LuaSocket | Non-blocking (ngx_lua cosockets) |
| **Parameterised queries** | No (manual escaping) | Yes (`$1`, `$2`) | No (manual escaping) |
| **Connection pooling** | None built in | `keepalive()` into the cosocket pool | `set_keepalive()` into the cosocket pool |
| **Install** | `luarocks install luasql-postgres` (one rock per driver) | `luarocks install pgmoon` (+ `luaossl` for TLS) | Copy `lib/resty/mysql.lua` or use a bundle |
| **License** | Same as Lua 5.1 (MIT-style) | MIT | BSD-style (OpenResty) |

The star counts are close, which is misleading. They solve different problems: LuaSQL is a compatibility layer, pgmoon is a protocol implementation, and lua-resty-mysql is a cosocket integration.

## Decision Matrix: Pick by Use Case

| Your situation | Pick | Why |
|---|---|---|
| OpenResty gateway, MySQL/MariaDB backend | **lua-resty-mysql** | Production-ready cosocket driver, zero C dependencies, pools per worker |
| OpenResty gateway, PostgreSQL backend | **pgmoon** | Only maintained pure-Lua Postgres driver; parameterised queries and `keepalive()` |
| Standalone Lua script (cron job, CLI, migration tool) | **LuaSQL** | Works outside nginx; single API over six database families |
| SQLite embedded in a desktop or edge tool | **LuaSQL** | `luasql.sqlite3` is the shortest path to a cursor API |
| Oracle / ODBC / Firebird legacy integration | **LuaSQL** | Nothing else in the Lua ecosystem covers these |
| Need `LISTEN/NOTIFY` with PostgreSQL | **pgmoon** | `wait_for_notification()` is built in |
| You want prepared statements as a hard requirement | **pgmoon** | `$1` placeholders; the other two require manual quoting |

## LuaSQL: The Polyglot That Speaks to Everything

LuaSQL is the oldest option and still the widest. Its own README states the scope plainly: connect to ODBC, ADO, Oracle, MySQL, SQLite, Firebird and PostgreSQL databases; execute arbitrary SQL; retrieve results row by row through a cursor. With **580 stars** and a commit in **August 2026**, it is maintained but not modernised.

Install one rock per backend — the drivers are separate shared objects:

```bash
luarocks install luasql-postgres
luarocks install luasql-mysql
luarocks install luasql-sqlite3
```

The API is a three-object dance: environment, connection, cursor.

```lua
local luasql = require "luasql.postgres"
local env  = luasql.postgres()
local conn = assert(env:connect("appdb", "app", "secret", "127.0.0.1", 5432))

local cur = assert(conn:execute("select id, email from users where status = 'active'"))
local row = cur:fetch({}, "a")          -- "a" = associative table
while row do
  print(row.id, row.email)
  row = cur:fetch({}, "a")
end

cur:close()
conn:close()
env:close()
```

Two things to notice. First, `env:connect` takes positional arguments — `sourcename, username, password, hostname, port` — so every configuration value ends up in argument order rather than a named table. Second, `fetch({}, "a")` allocates a fresh table per row unless you pass the same table back in, which matters on large result sets.

**Where LuaSQL hurts in 2026:** it blocks. If you `require "luasql.postgres"` inside an `content_by_lua_block`, that C call holds the nginx worker for the duration of the query, and every other request multiplexed onto that worker waits. It also has no pooling, no parameter binding, and no async story. Treat it as the right tool for offline scripts and legacy integrations, not for request-path code.

## pgmoon: PostgreSQL for OpenResty Without a C Extension

pgmoon is a pure-Lua PostgreSQL driver that speaks the wire protocol directly. **436 stars**, last push **2026-09-09**, MIT licensed, and it works both inside OpenResty (cosockets) and in plain Lua via LuaSocket.

```bash
luarocks install pgmoon
luarocks install luaossl     # only if you need TLS
```

The documented example is compact, and it is the API you will actually write:

```lua
local pgmoon = require("pgmoon")
local pg = pgmoon.new({
  host = "127.0.0.1",
  port = "5432",
  database = "mydb",
  user = "postgres"
})

assert(pg:connect())

local res = assert(pg:query("select * from users where status = 'active' limit 20"))

assert(pg:query("update users set name = $1 where id = $2", "leafo", 99))
```

That `$1` form is the reason to prefer pgmoon over manual escaping. Values are sent as protocol parameters, not concatenated into SQL text, so a name containing a quote cannot rewrite your statement.

Inside OpenResty, hand the socket back to the connection pool instead of closing it:

```lua
pg:keepalive()
```

pgmoon's README documents the caveats honestly, and you should internalise them before shipping:

- **Duplicate column names collapse.** `select 1 as dog, 'hello' as dog` yields `{ { dog = "hello" } }` because results land in a Lua table. Alias your columns.
- **Connections are not safe to share across concurrently running coroutines.** The driver tracks a `busy` flag across `connect`, `query`, `disconnect`, `keepalive` and `wait_for_notification`, and will refuse re-entry — so one connection per in-flight coroutine, managed through the pool.
- **Arrays and HStore need `lpeg` installed** to parse complex types.
- **TLS needs an extra dependency**; `luaossl` is the maintained choice, while the README explicitly calls LuaCrypto abandoned.

## lua-resty-mysql: The Production Workhorse for MySQL

lua-resty-mysql is the driver most OpenResty deployments end up using, and its README labels it production ready. **727 stars**, last push **2026-06-20**, maintained under the OpenResty organisation. It requires ngx_lua 0.9.11 or newer and the `bit` library (already present in LuaJIT 2 builds of ngx_lua).

Install by making the module visible to nginx:

```nginx
lua_package_path "/path/to/lua-resty-mysql/lib/?.lua;;";
```

The documented synopsis, trimmed to the essential calls:

```lua
local mysql = require "resty.mysql"
local db, err = mysql:new()
if not db then
  ngx.say("failed to instantiate mysql: ", err)
  return
end

db:set_timeout(1000)   -- 1 second

local ok, err, errcode, sqlstate = db:connect{
  host = "127.0.0.1",
  port = 3306,
  database = "ngx_test",
  user = "ngx_test",
  password = "ngx_test",
  charset = "utf8",
  max_packet_size = 1024 * 1024,
}

if not ok then
  ngx.say("failed to connect: ", err, ": ", errcode, " ", sqlstate)
  return
end

local res, err, errcode, sqlstate = db:query("select * from cats order by id asc", 10)
if not res then
  ngx.say("bad result: ", err, ": ", errcode, ": ", sqlstate, ".")
  return
end
```

Every call returns the OpenResty error tuple. Resist the temptation to `assert()` inside a request handler — a failed `query` should produce a 503, not an nginx 500 with an unreadable traceback.

The driver's practical features are the ones you need at scale: `set_timeout` bounds a stalled query, `set_keepalive(max_idle_timeout, pool_size)` returns the connection to the pool, `get_reused_times()` tells you whether pooling is actually working, and `set_compact_arrays(true)` returns result rows as plain arrays instead of `{ field = ..., value = ... }` pairs, which cuts allocation noticeably on wide result sets. Multi-resultset support and automatic error logging are documented as well.

The trade-off is real: **lua-resty-mysql has no prepared statements.** You must quote values yourself, and the README provides an SQL literal quoting section for exactly this reason. Inside nginx you can reach for `ngx.quote_sql_str()`, but a hand-rolled `"'" .. value .. "'"` is how injection bugs get shipped.

## Running All Three Side by Side

For a realistic lab, start PostgreSQL and MySQL next to OpenResty using the official images. Nothing here is project-specific glue — it is the same compose file you would use to reproduce a latency problem on your laptop.

```yaml
services:
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  mysql:
    image: mysql:8.4
    environment:
      MYSQL_DATABASE: appdb
      MYSQL_USER: app
      MYSQL_PASSWORD: secret
      MYSQL_ROOT_PASSWORD: rootsecret
    ports: ["3306:3306"]
    volumes: ["mysqldata:/var/lib/mysql"]

  openresty:
    image: openresty/openresty:alpine
    ports: ["8080:80"]
    volumes:
      - ./nginx.conf:/usr/local/openresty/nginx/conf/nginx.conf:ro
    depends_on: [postgres, mysql]

volumes:
  pgdata:
  mysqldata:
```

Then wire a single endpoint that exercises the pool:

```nginx
server {
  listen 80;

  location /pg {
    content_by_lua_block {
      local pgmoon = require("pgmoon")
      local pg = pgmoon.new({
        host = "postgres", port = "5432",
        database = "appdb", user = "app", password = "secret"
      })
      assert(pg:connect())
      local res = assert(pg:query("select now() as ts"))
      pg:keepalive()
      ngx.say(res[1].ts)
    }
  }

  location /mysql {
    content_by_lua_block {
      local mysql = require("resty.mysql")
      local db = assert(mysql:new())
      db:set_timeout(1000)
      assert(db:connect{
        host = "mysql", port = 3306, database = "appdb",
        user = "app", password = "secret", charset = "utf8"
      })
      local res = assert(db:query("select now() as ts"))
      db:set_keepalive(10000, 100)
      ngx.say(res[1].ts)
    }
  }
}
```

Run `wrk -t4 -c100 -d30s http://localhost:8080/pg` and then the same against `/mysql`. Do not trust a blog post's benchmark table (including this one) — measure against your schema, your payload size and your network. What you are looking for is not raw throughput but **latency stability**: p99 should stay flat as concurrency rises. If it climbs linearly with `-c`, pooling is broken or a query is blocking.

## Performance and Concurrency: What Actually Decides

Driver choice affects throughput through three mechanisms, and only one of them is the driver's own speed.

**1. Blocking versus non-blocking.** A cosocket driver yields the worker while the database works; a C-binding driver does not. Inside nginx this is not a micro-optimisation — with `worker_connections 1024` and four workers, one blocked handler can strand hundreds of queued requests. If you must use LuaSQL in a request path, run it in a separate process, never inside `content_by_lua*`.

**2. Pool reuse.** Both OpenResty drivers rely on the cosocket connection pool, sized per worker and keyed by host/port. `set_keepalive(10000, 100)` in lua-resty-mysql and `keepalive()` in pgmoon both return a socket for reuse; forgetting the call means a fresh TCP handshake, TLS negotiation and database authentication on every request. On PostgreSQL that can cost several milliseconds per request before your query even starts.

**3. Allocation per row.** LuaSQL's cursor with `fetch({}, "a")` builds a table per row. lua-resty-mysql's default result shape is a table of single-key tables unless you enable compact arrays. pgmoon builds associative rows directly. For a 10,000-row export, the difference shows up as GC pauses, not query time.

An honest comparison also has to say what these drivers cannot do: none of them is an ORM, none of them manages migrations, and none of them will retry a failed transaction for you. If you want that layer, you are choosing a framework, not a driver — which is a different decision than the one this article covers.

## Pitfalls and Migration Notes

These are the failures I would warn a team about before they deploy any of the three.

- **String-concatenated SQL is the default failure mode of two of these drivers.** pgmoon supports `$1` placeholders; lua-resty-mysql and LuaSQL do not. In OpenResty, use `ngx.quote_sql_str(value)` and never interpolate raw input.
- **A forgotten `keepalive()` looks like a database problem.** Connection counts climb, `too many connections` appears in the database log, and latency rises in steps. Check `get_reused_times()` first — if it stays at 0, you are not pooling.
- **LuaSQL needs one rock per backend.** `luasql-postgres` will not talk to MySQL. This bites when a container image is built with only one driver and a second integration is added later.
- **Charset and packet size are explicit in both OpenResty drivers.** Set `charset = "utf8mb4"` for MySQL if you store emoji, and raise `max_packet_size` for large blobs; the default 1 MB silently limits what you can return in one query.
- **Transactions are manual.** `BEGIN` / `COMMIT` / `ROLLBACK` are just queries. Wrap them in `pcall` and roll back on error, or a failed statement leaves the connection in an aborted transaction inside the pool — and the next request inherits it.
- **Duplicate column names overwrite each other in pgmoon.** Always alias: `select u.id as user_id, o.id as order_id`.
- **Do not share one connection across coroutines.** OpenResty may resume a different coroutine on the same connection; both drivers guard against re-entry, which means you get an error instead of corrupted protocol state. One connection per in-flight request, via the pool.

## Which Should You Actually Use?

**If you run OpenResty, the answer is decided by your database engine, not by benchmarks.** MySQL or MariaDB: lua-resty-mysql, because it is maintained under the OpenResty org, cosocket-native, and has the pool and timeout knobs you need. PostgreSQL: pgmoon, because it is the only pure-Lua option that supports parameter binding and `LISTEN/NOTIFY`, and because it does not require compiling C extensions into a container.

**If you are writing scripts outside nginx** — a nightly export, a migration runner, a CLI tool — LuaSQL remains the pragmatic choice. Its cursor API is dated, its performance is unremarkable, and it will not win a concurrency contest, but it covers SQLite, Oracle, ODBC and Firebird in a single interface, and nothing else in the Lua ecosystem does.

The combination I would actually ship in 2026: **pgmoon for request-path Postgres**, **lua-resty-mysql for MySQL**, and **LuaSQL for offline tooling only**. Do not mix a blocking driver into a request path "just for one query" — that one query is exactly the one that will freeze a worker during your next traffic spike.

For related reading, see our [Lua web frameworks comparison](../2026-09-28-lua-web-frameworks-lapis-lor-sailor-comparison/) to pick the framework these drivers sit under, our [Lua testing frameworks guide](../2026-09-05-lua-testing-frameworks-busted-luaunit-luassert-comparison/) for wiring integration tests against a real database, and our [C++ database client libraries comparison](../2026-06-22-cpp-database-client-libraries-libpqxx-soci-redisplusplus-mongocxx/) if you are evaluating drivers in a compiled stack instead.

## FAQ

### Is lua-resty-mysql still maintained in 2026?

Yes. The repository received commits in June 2026 and the README still labels the library production ready. It is maintained under the OpenResty organisation alongside lua-resty-redis and lua-resty-core, which is a reasonable proxy for long-term support.

### Can I use pgmoon outside OpenResty?

Yes. pgmoon works with LuaSocket in plain Lua, but then it blocks like any socket client. Its real advantage — cosocket-based non-blocking I/O and `keepalive()` pooling — only applies inside OpenResty or another ngx_lua environment.

### Why does lua-resty-mysql not support prepared statements?

The driver speaks the MySQL text protocol through ngx_lua cosockets and exposes `query`, `send_query` and `read_result`. Parameter binding would require the binary protocol and per-connection statement handles, which the project has not implemented. Use `ngx.quote_sql_str()` for escaping, or move the query into a service written in a language with a full driver.

### Which driver is fastest?

There is no universal answer, and any table claiming otherwise is measuring someone else's schema. What is measurable in your own environment is latency stability under concurrency: run `wrk` against each endpoint and watch p99 as you raise `-c`. A blocking driver will show a p99 that degrades sharply; pooled cosocket drivers stay flat until the database itself saturates.

### How many connections should I keep in the pool?

Start with `set_keepalive(10000, 100)` for MySQL and pool sizes proportional to `worker_connections` for pgmoon, then watch the database's connection count. The pool is per worker, so the effective maximum is roughly pool size × worker count — a number that surprises people who size the pool from a single-worker test.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Lua Database Drivers in 2026: LuaSQL vs pgmoon vs lua-resty-mysql",
  "description": "Hands-on comparison of LuaSQL, pgmoon and lua-resty-mysql: pooling, parameterised queries, blocking behaviour and production pitfalls for Lua and OpenResty database access.",
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
