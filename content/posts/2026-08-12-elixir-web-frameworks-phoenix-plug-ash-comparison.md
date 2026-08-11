---
title: "Elixir Web Development in 2026: Phoenix vs Plug vs Ash — Which Stack Should You Build On?"
date: "2026-08-12"
tags: ["elixir", "phoenix", "web-frameworks", "developer-tools"]
draft: false
cover: "/img/screenshots/phoenix-logo.jpg"
---

Elixir keeps winning the "language I want to use but my team won't let me" polls, and the reason is usually the same: the ecosystem around Phoenix has become genuinely excellent — but the choice of *how* to build your web application is now three-way. Do you reach for the full batteries-included Phoenix framework with LiveView and Ecto? Do you compose bare functions with Plug and pick every piece yourself? Or do you adopt Ash, the declarative framework that generates your API, your authorization rules, and your persistence layer from resource definitions? In 2026 this is not a religious debate — it is a scoping decision with real consequences for team velocity, maintenance cost, and how long your abstractions survive. This guide compares all three with real code from the official repositories so you can decide on facts, not folklore.

## TL;DR / Quick Verdict

**Pick Phoenix (23,114 stars, MIT) if you want the fastest path from idea to production** — LiveView, Ecto, and the router are integrated, documented, and boring in the best way. **Pick Plug (3,011 stars) if you are building a small service, an internal tool, or a custom middleware layer and you want zero framework opinion** — it is the specification Phoenix itself is built on. **Pick Ash (2,472 stars) if your domain model is complex and you want authorization, validation, and API exposure declared once in your resources** — it is the most ambitious of the three, and the one with the steepest learning curve. For most teams building a new product in 2026, Phoenix is the right default; Ash is the right default if you already know your domain is data-heavy; Plug is the right default for microservices and libraries.

## Quick Comparison Table

| Criterion | Phoenix | Plug | Ash |
|---|---|---|---|
| **GitHub stars** | 23,114 | 3,011 | 2,472 |
| **Last update** | Aug 2026 | Jul 2026 | Aug 2026 |
| **What it is** | Full web framework | Conn specification + adapters | Declarative domain framework |
| **Router** | Built-in (`Phoenix.Router`) | `Plug.Router` | Optional (`AshPhoenix`) |
| **LiveView** | Built-in | No | Via Phoenix integration |
| **Persistence** | Ecto (separate) | None | Built-in data layers (AshPostgres, AshSqlite) |
| **Authorization** | Policy libs (Bodyguard) | None | Built-in `Ash.Policy.Authorizer` |
| **JSON API / GraphQL** | Libraries | None | `AshJsonApi`, `AshGraphql` |
| **WebSockets** | Channels built-in | Via `WebSockAdapter` | Via Phoenix |
| **License** | MIT | MIT (Apache parts) | MIT |
| **Best for** | Full applications | Minimal services, middleware | Domain-driven complex apps |

## Decision Matrix: Which One for Your Case?

| Use Case | Recommendation | Why |
|---|---|---|
| New SaaS product, solo dev or small team | **Phoenix** | Router + LiveView + Ecto + auth conventions ship as one coherent stack |
| Internal admin tool with a few forms | **Phoenix LiveView** | No JS build step needed; server-rendered reactivity for free |
| Microservice that only serves JSON to other services | **Plug** | A `Plug.Router` with two routes is less moving parts than a full Phoenix app |
| Domain with heavy business rules, roles, and audit trails | **Ash** | Policies, validations, and multi-step actions live next to the data model |
| GraphQL-first API team | **Ash** | `AshGraphql` generates the schema from resources; Phoenix needs Absinthe wiring |
| Library or OTP application with no HTTP | **Plug** | The conn spec is the interface; no framework baggage |
| Team already knows Rails/Django conventions | **Phoenix** | Familiar MVC-ish structure with `controllers`, `schemas`, and `contexts` |

## Phoenix — The Batteries-Included Default

Phoenix is the framework that made Elixir famous outside the Erlang world, and in 2026 it is comfortably the most productive full-stack framework on the BEAM. Created by Chris McCord in 2014 and MIT-licensed, it now powers production systems at companies like Discord (for live presence), Bleacher Report, and the Financial Times. The headline feature remains LiveView: real-time, server-rendered UIs without writing client-side JavaScript. The router, controllers, channels, and pub/sub are all integrated and documented to an exceptionally high standard.

Creating a project is one command, and the installer generates a complete, deployable application:

```bash
mix archive.install hex phx_new
mix phx.new my_app --database postgres
cd my_app && mix deps.get && mix ecto.create
mix phx.server
# http://localhost:4000
```

The router shows the shape of the whole framework — pipelines compose plugs, and scopes map URLs to controllers or LiveView modules:

```elixir
defmodule MyAppWeb.Router do
  use MyAppWeb, :router

  pipeline :browser do
    plug :accepts, ["html"]
    plug :fetch_session
    plug :fetch_flash
    plug :protect_from_forgery
    plug :put_secure_browser_headers
  end

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/", MyAppWeb do
    pipe_through :browser
    get "/", PageController, :index
    live "/dashboard", DashboardLive
    resources "/users", UserController
  end
end
```

Phoenix ships with `phx.gen.html` and `phx.gen.live` generators that scaffold full CRUD modules with migrations, schemas, contexts, and tests. That scaffolding is the framework's secret weapon: a new Phoenix app with working auth, a database, and a real-time dashboard is a weekend of work, not a month. The trade-off is that Phoenix makes structural decisions for you — you live inside its conventions, and fighting them is more painful than choosing another tool.

## Plug — The Conn Specification Phoenix Is Built On

Plug is deliberately minimal: a specification for composing web applications from functions, plus connection adapters for Cowboy and Bandit. The core idea is the `%Plug.Conn{}` struct flowing through a pipeline of modules and functions, each transforming the connection. Phoenix is literally a large collection of plugs; when you understand Plug, you understand the plumbing underneath every Phoenix request.

A complete HTTP service in Plug, straight from the official README, is under 20 lines:

```elixir
Mix.install([:plug, :plug_cowboy])

defmodule MyPlug do
  import Plug.Conn

  def init(options), do: options

  def call(conn, _opts) do
    conn
    |> put_resp_content_type("text/plain")
    |> send_resp(200, "Hello world")
  end
end

require Logger
webserver = {Plug.Cowboy, plug: MyPlug, scheme: :http, options: [port: 4000]}
{:ok, _} = Supervisor.start_link([webserver], strategy: :one_for_one)
Logger.info("Plug now running on localhost:4000")
Process.sleep(:infinity)
```

Routing is available via `Plug.Router`, and WebSockets work out of the box through the connection upgrade API and `WebSockAdapter`:

```elixir
defmodule Router do
  use Plug.Router

  plug Plug.Logger
  plug :match
  plug :dispatch

  get "/" do
    send_resp(conn, 200, "Hello from Plug.Router")
  end

  get "/websocket" do
    conn
    |> WebSockAdapter.upgrade(EchoServer, [], timeout: 60_000)
    |> halt()
  end
end
```

The beauty of Plug is that every piece is replaceable and visible: you can read the entire request path — router, middleware, handlers — in one file. The cost is that you assemble everything yourself: sessions, CSRF protection, parameter parsing, error pages, static asset handling. For a tiny service that is liberating; for a product with user accounts and admin panels, you will spend weeks reimplementing what Phoenix gives you in an afternoon.

## Ash — The Declarative Domain Framework

Ash is the most interesting and the most polarizing option in 2026. Instead of writing controllers, routes, and authorization checks separately, you declare **resources** — the entities of your domain — and Ash derives the rest: CRUD actions, validation, authorization policies, relationships, and even JSON API and GraphQL endpoints. It is a framework for *building frameworks around your domain*, backed by data layers that let the same resource definition talk to PostgreSQL, SQLite, CSV, or ETS.

The official get-started tutorial shows the core pattern. First you define a resource:

```elixir
# lib/helpdesk/support/ticket.ex

defmodule Helpdesk.Support.Ticket do
  use Ash.Resource, domain: Helpdesk.Support

  actions do
    defaults [:read]
    create :create
  end

  attributes do
    uuid_primary_key :id
    attribute :subject, :string
  end
end
```

Then a domain module registers it, and Ash wires up the rest:

```elixir
defmodule Helpdesk.Support do
  use Ash.Domain

  resources do
    resource Helpdesk.Support.Ticket
  end
end
```

Authorization is declared with policies, not scattered across controllers:

```elixir
policies do
  policy action_type(:read) do
    authorize_if expr(owner == actor)
  end
end
```

The appeal is architectural: business rules live in one place, the API surface is generated consistently, and changing a domain rule changes every endpoint that touches it. The cost is a genuinely steep learning curve — Ash's DSL is large, error messages assume you know the framework, and you are betting that Ash's abstractions map onto your domain's shape. Teams that embrace it report that complex authorization and multi-step workflows become dramatically simpler; teams that fight it report spending weeks just understanding how to express what they want. The `mix igniter.new` installer has first-class Phoenix integration (`AshPhoenix`), so the pragmatic path in 2026 is Phoenix for the web layer plus Ash for the domain layer.

## Pitfalls and Migration Notes

**Do not use Plug when you need sessions, CSRF, and flash messages.** The Plug README itself is clear: it is a specification, not an application framework. Teams that build "mini-Phoenix" on top of Plug usually end up reimplementing Phoenix badly — use `Plug.Session` and friends only if you truly have a small surface.

**LiveView's single-process-per-client model changes your deployment assumptions.** Long-lived WebSocket connections mean your load balancer must support sticky sessions or your PubSub must be distributed (Phoenix.PubSub with Redis or Postgres adapters). This is the single most common production surprise for teams migrating from request/response frameworks.

**Ash + Ecto is not "Ecto with extra steps" — it is a different mental model.** If you adopt Ash, do not keep writing Ecto queries directly against the same tables; Ash's data layer owns the schema. Mixed access patterns cause subtle consistency bugs where Ash policies are bypassed by raw queries. Choose one authority for data access.

**Version pins matter more than usual in the Elixir world.** Phoenix 1.7 and 1.8 changed router and HTML helpers; Ash 3.0 was a major rewrite with different DSL. When reading tutorials, match the tutorial's version to your installed versions or you will chase phantom errors. See our [Elixir JSON libraries comparison](../2026-07-25-elixir-json-libraries-jason-poison-jsex-jsonrs/) for a taste of how fast this ecosystem's libraries move.

**Heterogeneous teams: Elixir's type system is gradual.** None of these frameworks gives you the compile-time guarantees of a typed language, so invest in `dialyxir` (the Dialyzer wrapper) and property-based testing from day one — the Elixir community's discipline here is what keeps large Phoenix codebases maintainable. Pair this with the patterns in our [Ruby testing frameworks guide](../2026-07-06-ruby-testing-frameworks-rspec-minitest-capybara/) if you are coming from the Ruby world.

## Performance and Scaling Considerations

The BEAM's per-process model gives all three options excellent concurrency, but the scaling profiles differ. Plug-based services are the cheapest to deploy: no LiveView connections to keep alive, no PubSub topology — a handful of instances behind a load balancer handle enormous request rates. Phoenix with LiveView shifts load from the frontend to the server: every connected client holds a process, so a 10,000-user dashboard means 10,000 long-lived processes plus PubSub fan-out. Elixir handles this gracefully — that is the point of the VM — but your memory budget and your WebSocket-terminating infrastructure need to be planned for. Ash sits in the middle: it adds a thin interpretation layer over queries, which costs microseconds per operation but buys you consistent policies and validations across every access path. In practice, database queries dominate response time in data-heavy apps, so Ash's overhead is rarely the bottleneck.

For deployment, all three run fine in Docker on a single VPS, and the standard build produces a release with `mix release`. LiveView apps benefit from being behind a CDN that terminates WebSockets properly (Cloudflare handles this transparently). If you are comparing deployment setups, our [Go web frameworks comparison](../2026-07-06-go-web-frameworks-gin-echo-fiber-chi/) shows the same trade-offs from the Go ecosystem's perspective.

## FAQ

### Is Phoenix still the best Elixir web framework in 2026?

Yes. Phoenix remains the default choice with 23,114 stars, an active maintainer team, and the largest production footprint. LiveView, Ecto integration, and the generator ecosystem make it the highest-velocity option for full applications. Ash is a specialized alternative for domain-heavy apps, not a general replacement.

### Can I use Plug without Phoenix?

Absolutely — that is its purpose. Plug is a standalone specification with its own router, and thousands of production services run on Plug + Cowboy or Plug + Bandit without Phoenix. You lose LiveView, channels, and generators, but for JSON microservices that is usually acceptable.

### Does Ash require Phoenix?

No. Ash is a domain framework; it works in any Elixir application, including plain OTP apps and Plug services. The `AshPhoenix` package adds LiveView and router conveniences when you do use Phoenix, but the resources, policies, and data layers are framework-agnostic.

### What is the learning curve like for Ash?

The steepest of the three. The DSL covers resources, actions, policies, data layers, and extensions — expect a week or two of focused learning before you are productive, versus hours for Plug and days for Phoenix. The payoff is a single source of truth for domain rules, which pays off in long-lived, rule-heavy applications.

### Which option is best for real-time features?

Phoenix, hands down. LiveView and Channels are first-class, and the PubSub system scales to large fan-out with the right adapter. Plug supports WebSockets via `WebSockAdapter`, but you assemble the whole real-time layer yourself.

### How do I choose between Ecto and Ash's data layers?

If you want explicit control over queries, migrations, and the data layer, use Ecto directly with Phoenix. If you want your domain rules (validation, authorization, relationships) to be the single source of truth and are comfortable with a higher-level DSL, Ash's data layers — backed by AshPostgres — give you that at the cost of some low-level control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Elixir Web Development in 2026: Phoenix vs Plug vs Ash — Which Stack Should You Build On?",
  "description": "Compare Phoenix, Plug, and Ash for Elixir web development in 2026: LiveView, routers, declarative domain modeling, authorization, performance, and migration guidance with real code.",
  "datePublished": "2026-08-12",
  "dateModified": "2026-08-12",
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
