---
title: "Crystal Web Frameworks in 2026: Kemal vs Lucky vs Amber"
date: "2026-08-31"
tags: ["crystal", "web-frameworks", "backend", "programming-languages"]
draft: false
cover: "/img/screenshots/kemal-cover.jpg"
---

Crystal compiles Ruby-like syntax into a single native binary that starts in milliseconds and handles tens of thousands of requests per second — no JVM warmup, no Node event loop, no Ruby VM. That performance story has been true for years, yet the language's web framework ecosystem remains one of the best-kept secrets in backend development: three actively maintained frameworks — Kemal, Lucky, and Amber — each with more than 2,500 GitHub stars and commits pushed within the last month, and almost nobody writing about them. If you have ever wished Sinatra were compiled, Rails were type-safe, or Phoenix ran on a language that did not need the BEAM, one of these three is the framework you have been looking for.

**TL;DR:** Choose **Kemal** for APIs, microservices, and WebSocket-heavy services where you want minimal boilerplate and maximum performance — it is the Sinatra of Crystal, and its hello-world benchmark (~85K req/s) tells you what the language is capable of. Choose **Lucky** for full-stack applications where compile-time safety across routes, models, queries, and HTML will save you more debugging time than it costs in learning curve — it is the closest thing to a type-safe Rails. Choose **Amber** if you want a batteries-included MVC framework with its own CLI, multi-database support, and pipeline-based middleware — a middle ground that feels like Phoenix with fewer opinions than Lucky.

## Quick Feature Comparison

| Feature | Kemal | Lucky | Amber |
|---|---|---|---|
| GitHub stars | 3,912 | 2,724 | 2,605 |
| Last release activity | Aug 2026 | Aug 2026 | Aug 2026 |
| Style | Micro (Sinatra-like) | Full-stack (Rails-like) | Full-stack MVC (Phoenix-like) |
| Built-in ORM | No (bring your own) | **Yes (Avram, Postgres)** | Optional (Granite) |
| CLI generator | No | **Yes (`lucky gen`)** | **Yes (`amber new`)** |
| WebSocket support | **Built-in** | Via ActionWebSocket | **Built-in** |
| Template engine | ECR built-in | Crystal-native HTML DSL | ECR / Slang |
| Compile-time route safety | Partial | **Excellent** | Partial |
| Database support | Any (via shards) | Postgres (Avram) | **Postgres, MySQL, SQLite** |
| JSON APIs | Native, minimal boilerplate | Serializers | Native |
| Learning curve | Lowest | Highest | Medium |
| License | MIT | MIT | MIT |
| Downloads / track record | 5M+ since 2015 | Since 2017 | Since 2016 |

## Decision Matrix: Which Crystal Framework Should You Use?

| Use Case | Recommended Framework | Why |
|---|---|---|
| JSON API / microservice, performance-critical | **Kemal** | Thin abstraction, native JSON, hello world ~85K req/s, ~0.5 KB memory per request |
| Real-time features (WebSocket, streaming) | **Kemal** | First-class built-in WebSocket with zero extra dependencies |
| Full-stack web app with long maintenance horizon | **Lucky** | Compile-time checks on routes, queries, and HTML eliminate whole bug classes |
| Team migrating from Ruby on Rails | **Lucky** | Rails-inspired conventions, but compiled and type-safe; Avram replaces ActiveRecord |
| Team migrating from Phoenix/Elixir | **Amber** | Similar philosophy, pipeline middleware, built-in WebSockets, multiple DB adapters |
| Need MySQL or SQLite support | **Amber** | Lucky's Avram is Postgres-first; Amber ships Postgres, MySQL, and SQLite adapters |
| Small internal tool, single file | **Kemal** | A working server in under 20 lines of Crystal |

## Kemal — Fast, Effective, Simple

Kemal is the oldest and most battle-tested framework in the Crystal ecosystem — the README claims 5M+ downloads since 2015 — and it has stayed true to a simple philosophy: a thin abstraction layer over Crystal's HTTP stack, with the essentials (routing, middleware, templates, static files) built in and advanced concerns left to shards. It is the framework you reach for when you want C-level performance with Ruby-like syntax, and nothing in your way.

The quick start from the official README gets a server running in under a minute:

```bash
crystal init app my-app
cd my-app
```

Add Kemal to `shard.yml`:

```yaml
dependencies:
  kemal:
    github: kemalcr/kemal
```

Replace `src/my-app.cr` with:

```crystal
require "kemal"

get "/" do
  "Hello World!"
end

get "/api" do |env|
  env.response.content_type = "application/json"
  {status: "ok"}.to_json
end

Kemal.run
```

```bash
shards install
crystal run src/my-app.cr
```

Visit http://localhost:3000 — done. The README's performance table is worth reading carefully: approximately 85,000 req/s for hello world at 100 connections, ~50,000 req/s for JSON serialization, ~0.5 KB memory per request, and a ~2 MB binary with dependencies. No JVM, no Node, no Ruby VM — just a native executable you can copy onto a server and run. That single-binary deployment story is one of Crystal's biggest practical wins, and Kemal is its purest expression.

Kemal ships WebSocket support out of the box (no extra gems), ECR templates, session management via `kemal-session`, and a composable middleware system. It deliberately has no opinion about ORMs, project layout, or how you structure your application. That freedom is a feature for small services and a liability for large teams that want guardrails — which is exactly what the other two frameworks exist to provide.

## Lucky — The Type-Safe Rails

Lucky's stated goal, from its README, is to "prevent bugs, forget about most performance issues, and spend more time on code instead of debugging and fixing tests." It pursues that goal with a ruthless compile-time strategy: routes, database queries, and HTML pages are all checked by the Crystal compiler before your binary ever runs. If a route parameter is missing, a column name is mistyped, or you try to render a page without the data it needs, the build fails — not your production deployment.

A JSON endpoint in Lucky looks like this:

![Lucky](/img/screenshots/lucky-dashboard.jpg "Lucky — a Crystal web framework focused on compile-time safety")

```crystal
class Api::Users::Show < ApiAction
  get "/api/users/:user_id" do
    user = UserQuery.find(user_id)
    json UserSerializer.new(user)
  end
end
```

Models are declared with typed columns, and the compiler enforces them everywhere:

```crystal
class User < BaseModel
  table do
    column last_active_at : Time
    column last_name : String
    column nickname : String?
  end
end
```

Queries are chainable, type-safe method calls — mistyping a column name is a compile error, not a runtime 500:

```crystal
class UserQuery < User::BaseQuery
  def recently_active
    last_active_at.gt(1.week.ago)
  end

  def sorted_by_last_name
    last_name.lower.desc_order
  end
end

UserQuery.new.recently_active.sorted_by_last_name
```

HTML pages are written as Crystal methods with automatically closed tags, and the `needs` keyword makes required data explicit:

```crystal
class Users::IndexPage < MainLayout
  needs users : UserQuery

  def content
    render_new_user_button
    render_user_list
  end

  private def render_user_list
    ul class: "user-list" do
      users.each do |user|
        li do
          link user.name, to: Users::Show.with(user.id)
        end
      end
    end
  end
end
```

Because a page cannot compile unless everything it needs is passed to it, Lucky eliminates an entire class of "undefined variable in template" and "nil printed into HTML" bugs that plague dynamic-language frameworks. The cost is a genuinely steeper learning curve: Lucky has its own CLI, its own conventions, and its own ORM (Avram, which is Postgres-first), and you must internalize how the pieces fit before you are productive. Teams coming from Rails will recognize the shape of the conventions — that is deliberate; the README credits Rails directly — but the type system is the differentiator.

## Amber — The Balanced MVC Middle Ground

Amber describes itself as "a web application framework written in Crystal inspired by Kemal, Rails, Phoenix and other popular application frameworks," with a purpose statement that reads "Productivity. Performance. Happiness." It sits between Kemal's minimalism and Lucky's opinionated safety: a full MVC framework with a CLI, pipeline-based middleware, built-in WebSockets, and — uniquely among the three — first-class support for Postgres, MySQL, and SQLite.

The README's installation path on Linux builds the CLI from source:

```bash
sudo apt-get install libreadline-dev libsqlite3-dev libpq-dev libmysqlclient-dev libssl-dev libyaml-dev libpcre3-dev libevent-dev
git clone https://github.com/amberframework/amber.git
cd amber
shards install
make
sudo make install
```

Or, per project, add it to `shard.yml`:

```yaml
dependencies:
  amber:
    github: amberframework/amber
```

Then compile a local `bin/amber` with `shards build amber`. Amber's CLI (`amber new`, `amber generate`, `amber db`) scaffolds controllers, models, and migrations, and its pipeline system lets you compose middleware chains per-route-group — a concept borrowed from Phoenix that keeps auth, rate limiting, and logging concerns neatly layered. Its default ORM is Granite, with adapters for all three major databases, which makes Amber the pragmatic choice when you cannot commit to Postgres.

Amber's history is its main caveat: it went through a long period of slower development (the README still references a 2019 TechEmpower benchmark), and its docs are less polished than Kemal's or Lucky's. It is actively maintained again in 2026, but the community energy in Crystal today clearly sits with Kemal and Lucky.

## Pitfalls and Migration Traps

**1. Crystal compile times are real.** Full-stack Lucky applications can take minutes to compile from cold, which makes tight inner loops feel sluggish. Use `crystal watch` (or `lucky watch`) for development, keep your test binary compiled, and budget CI time for the build. The compiled binary is fast; getting there takes patience.

**2. There is no drop-in "Rails migration."** If you are coming from Ruby on Rails, Lucky will feel familiar but nothing ports automatically: models, migrations, routes, and views all have different APIs. Budget a real rewrite — the payoff is compile-time guarantees, but it is a rewrite.

**3. Kemal has no ORM and no project structure — that is your job.** Teams that pick Kemal for a large application end up inventing their own architecture. If you want guardrails, choose Lucky or Amber from the start rather than bolting structure onto Kemal later.

**4. Avram is Postgres-first.** Lucky's ORM assumes Postgres. If your infrastructure is MySQL or SQLite, Amber (Granite) is the pragmatic choice — or use Kemal with a database shard of your choice.

**5. WebSocket performance is a Crystal strength, but test your proxy.** Crystal's fiber-based concurrency handles thousands of concurrent WebSocket connections, but you must configure your reverse proxy (nginx, Caddy, HAProxy) with correct timeouts and upgrade headers. A misconfigured proxy will kill long-lived connections regardless of framework.

**6. Compare with adjacent ecosystems before committing.** Crystal is a small language with a small job market, and that matters for long-term staffing. If your team already knows Elixir, [Phoenix versus Plug versus Ash](../2026-08-12-elixir-web-frameworks-phoenix-plug-ash-comparison/) may be the lower-risk path; if they know Clojure, the [Ring versus Compojure versus Reitit comparison](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/) covers the JVM side of the same "compiled and fast" story. For the record, [Haskell's Yesod, Scotty, and Servant](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) offer even stronger type safety at an even higher learning cost.

## How to Evaluate Crystal Frameworks in One Weekend

The fastest way to decide is to build the same small service in all three. Start with Kemal: a JSON API with three endpoints and a WebSocket echo takes an evening and shows you the language's performance ceiling. Then scaffold a Lucky app (`lucky gen`) and recreate the API with a model, a query, and a serializer — you will feel the compile-time safety immediately, along with the learning curve. Finally, `amber new` and walk through the CLI's generator and pipeline. Pay attention to which framework made you feel productive by Sunday, because the biggest cost in a framework choice is the team's daily experience, not the benchmark numbers. And remember that all three compile to the same native binary story — whichever you pick, deployment is a single executable and a reverse proxy.

## FAQ

**Is Crystal production-ready for web applications?**
Yes. Crystal has been used in production since 2015 (Kemal alone claims 5M+ downloads), and the language's native compilation makes it well suited to high-throughput services. The ecosystem is smaller than Node.js or Go, but the core frameworks are mature and actively maintained.

**Which Crystal web framework is the fastest?**
Kemal publishes the strongest headline numbers (~85K req/s hello world, ~50K req/s JSON serialization), but all three compile to native code, and framework overhead is small compared with the underlying HTTP stack. Lucky and Amber add ORM and template layers that cost some throughput.

**Does Lucky work with MySQL or SQLite?**
Avram is Postgres-first. For MySQL or SQLite, use Amber with Granite, or Kemal with a database shard of your choice.

**How does Crystal compare with Go for backend services?**
Both compile to native binaries with excellent performance. Crystal offers Ruby-like syntax and fiber-based concurrency, while Go has a much larger ecosystem and simpler mental model. If you value expressive syntax and are comfortable with a smaller ecosystem, Crystal is competitive.

**Is there a Crystal equivalent of Ruby on Rails?**
Lucky is the closest match: Rails-inspired conventions, an ORM (Avram), generators, and a focus on developer happiness — with the crucial difference that Lucky's routes, models, and views are type-checked at compile time.

**Does Kemal support WebSockets?**
Yes, built-in, with no extra dependencies. WebSocket support is a first-class feature of the framework and one of the reasons it is popular for real-time services.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Crystal Web Frameworks in 2026: Kemal vs Lucky vs Amber",
  "description": "Compare Crystal web frameworks — Kemal, Lucky, and Amber — on performance, type safety, ORM support, and learning curve to choose the right one for 2026.",
  "datePublished": "2026-08-31",
  "dateModified": "2026-08-31",
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
