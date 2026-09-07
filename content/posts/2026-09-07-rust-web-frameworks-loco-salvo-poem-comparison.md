---
title: "Next-Gen Rust Web Frameworks in 2026: Loco vs Salvo vs Poem — Which One Should You Actually Use?"
date: "2026-09-07"
tags: ["rust", "web-frameworks", "backend", "developer-tools", "libraries"]
draft: false
---

The classic Rust web framework trio — Actix-web, Rocket, and Axum — answered the question "can Rust do web servers at all?" The second generation now arriving answers a harder one: "can Rust feel as productive as Rails, Django, or Express while keeping its performance?" **Loco (9,121 stars) scaffolds an entire application with ORM, auth, and background jobs baked in — Rails for Rust. Salvo (4,435 stars) strips the framework down to handlers and middleware "hoops" that read like plain functions. Poem (4,440 stars) composes a full-featured toolkit — OpenAPI, gRPC, Lambda support — from small opt-in crates.** All three are built on Tokio, all three shipped updates within the last month, and all three are Rust-idiomatic enough that your Axum knowledge transfers instead of going to waste.

## TL;DR — Quick Verdict

**Building a solo project or startup MVP and want to go from `cargo new` to a working app with a database, auth, and a job queue in one evening? Use Loco** — its CLI generates the whole structure and it standardizes the ecosystem's best parts (Axum, SeaORM, Tokio) behind one opinionated framework. **Building a focused HTTP service where you want total control over middleware order, routing, and request handling without framework opinions? Use Salvo** — handler functions and hoops are the whole mental model, and you can read the entire framework surface in an afternoon. **Building an API-first product where clients consume an OpenAPI spec, gRPC, or serverless functions? Use Poem** — its first-party `poem-openapi`, `poem-grpc`, and `poem-lambda` crates turn your endpoint definitions into living documentation with zero code generation. If you already run Axum in production and just want more batteries, Loco is the upgrade path — it wraps Axum rather than replacing it.

## Quick Comparison Table

| Dimension | Loco | Salvo | Poem |
|---|---|---|---|
| GitHub stars | 9,121 | 4,435 | 4,440 |
| Last push (2026) | Aug 19 | Sep 06 | Aug 03 |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 / MIT (dual) |
| Philosophy | Batteries-included fullstack | Minimalist handler + middleware | Composable feature crates |
| Scaffolding CLI | Yes (`loco new`) | No | No |
| Bundled ORM | SeaORM (default) | Optional (any) | Optional (any) |
| Auth / jobs / assets | Built-in generators | Bring your own | Bring your own |
| First-party OpenAPI | Via SeaORM/Axum ecosystem | `oapi` feature + `salvo-oapi` | `poem-openapi` crate |
| gRPC / serverless | No | No | `poem-grpc`, `poem-lambda` |
| Middleware model | Tower-based (Axum) | Hoops | Endpoint middleware / Tower |
| Unsafe code | No (relies on Axum/Tokio) | Minimal | Forbidden by policy |
| MSRV | Recent stable | Recent stable | rustc 1.85+ |

## Decision Matrix — Pick in 10 Seconds

| Use Case | Recommended Framework | Why |
|---|---|---|
| Solo developer shipping a side project with DB + auth + jobs | Loco | Generators produce a working vertical slice in minutes |
| Internal API service behind a gateway, few routes, strict control | Salvo | Hoops and routers are transparent; no magic |
| Public API consumed by many clients, docs must stay correct | Poem | `poem-openapi` derives the spec from your handlers |
| Migrating an existing Axum service to something more structured | Loco | Wraps Axum — your handlers and Tower middleware keep working |
| Serverless deployment (AWS Lambda) with the same codebase | Poem | `poem-lambda` is first-party |
| Team already fluent in Actix-web/Axum and happy | None — stay put | The classic trio is mature; adopt these for *new* services only |

## Loco — The One-Person Framework for Rust

Loco's README describes it as "the one-person framework for Rust for side-projects and startups," and the pitch is honest: it is what you get when you take Axum, SeaORM, Tokio, and a job-queue implementation and bolt on a Rails-style generator. The CLI flow is straight from the project README:

```bash
$ cargo install loco
$ cargo install sea-orm-cli # Only when DB is needed
$ loco new
✔ ❯ App name? · myapp
✔ ❯ What would you like to build? · Saas App with client side rendering
✔ ❯ Select a DB Provider · Sqlite
✔ ❯ Select your background worker type · Async (in-process tokio async tasks)

🚂 Loco app generated successfully in:
myapp/

$ cargo loco start

                      ▄     ▀
                                ▀  ▄
                  ▄       ▀     ▄  ▄ ▄▀
                                    ▄ ▀▄▄
                        ▄     ▀    ▀  ▀▄▀█▄
▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄▄▄ ▀▀█
██████  █████   ███ █████   ███ █████   ███ ▀█
██████  █████   ███ █████   ▀▀▀ █████   ███ ▄█▄
██████  █████   ███ █████       █████   ███ ████▄
██████  █████   ███  ████   ███ █████   ███ █████
  ▀▀▀██▄ ▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀ ██▀
      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
                https://loco.rs

listening on port 5150
```

The generated app is a real vertical slice: controllers, models with SeaORM migrations, mailers, workers, and — in the client-side-rendering template — a frontend you build with `npm install && npm run build` from the `frontend/` directory. If the template fits your project, Loco removes the "Rust web apps take forever to stand up" tax completely. The trade-off is that you are adopting Loco's conventions: its controller/model/worker layout, its config format, and its upgrade cadence. If your project outgrows the template's assumptions, you are un-learning conventions rather than just deleting code.

## Salvo — Handlers and Hoops, Nothing Else

Salvo's design goal is stated in its tagline — "a powerful web framework built with a simplified design" — and the simplification is real: you write plain `#[handler]` functions and chain routers with middleware called **hoops**. The hello world from the README is the entire core API:

```rust
use salvo::prelude::*;

#[handler]
async fn hello() -> &'static str {
    "Hello World"
}

#[tokio::main]
async fn main() {
    let router = Router::new().get(hello);
    let acceptor = TcpListener::new("127.0.0.1:7878").bind().await;
    Server::new(acceptor).serve(router).await;
}
```

Middleware is a hoop you attach to any router node, and it applies to every route under that node — which makes per-subtree policies (logging, auth, CORS) visually obvious:

```rust
#[handler]
async fn add_header(res: &mut Response) {
    res.headers_mut().insert(header::SERVER, HeaderValue::from_static("Salvo"));
}

Router::new().hoop(add_header).get(hello)
```

Nested routers compose the same way, with hoops applied per subtree:

```rust
Router::new()
    // Public routes
    .push(Router::with_path("articles").get(list_articles))
    // Protected routes
    .push(Router::with_path("articles").hoop(auth_check).post(create_article).delete(delete_article))
```

Request bodies become typed via extractor-style parameters — no macro ceremony beyond `#[handler]`:

```rust
#[derive(Deserialize)]
struct CreateTodo { text: String }

#[handler]
async fn create_todo(req: &mut Request) -> Result<Json<Todo>, ParseError> {
    // ... parse and persist
}
```

Salvo's own `oapi` feature plus the `salvo-oapi` crate add OpenAPI generation, but the core value is different: the framework is small enough that you can hold it in your head. That makes it excellent for services where you want Axum-like control with a lighter, handler-oriented syntax — and it means fewer framework surprises when you need to do something unusual, because "unusual" just means writing another handler or hoop.

## Poem — Composable, OpenAPI-First, Unsafe-Free

Poem describes itself as "a full-featured and easy-to-use web framework," and its distinguishing trait is the crate layout: the core `poem` crate is deliberately lean, while `poem-openapi`, `poem-grpc`, and `poem-lambda` bolt on major capabilities without dragging them into every build. The project also enforces `unsafe`-free code by policy — a meaningful trust signal for security-sensitive services. Its README example shows the routing and path-extractor style:

```rust
use poem::{get, handler, listener::TcpListener, web::Path, Route, Server};

#[handler]
fn hello(Path(name): Path<String>) -> String {
    format!("hello: {}", name)
}

#[tokio::main]
async fn main() -> Result<(), std::io::Error> {
    let app = Route::new().at("/hello/:name", get(hello));
    Server::new(TcpListener::bind("0.0.0.0:3000"))
      .run(app)
      .await
}
```

Where Poem pulls ahead of the others is the API-first workflow: with `poem-openapi`, you declare an endpoint object with `#[OpenApi]` and the crate derives both the handler and its OpenAPI specification from the same source of truth — no separate spec file, no drift between docs and implementation. Production users include Databend (a cloud-native data warehouse) and Warpgate (a smart SSH bastion), which is a decent real-world vote for the framework's stability at scale. The main cost is the same one every Rust web framework charges: large dependency trees when you enable the optional integrations, and multi-minute cold builds on first compile.

## Pitfalls — What the Tutorials Do Not Tell You

**Cold compile times are the hidden onboarding tax.** All three frameworks sit on Tokio + Hyper + a pile of proc macros; a first `cargo build` on a modest laptop can take 3-6 minutes and hundreds of crates. Mitigations: keep dev dependencies thin, use `cargo check` during development, and consider a shared workspace so incremental builds stay warm. This is a one-time cost per machine, but it surprises every team that evaluates Rust web frameworks on a first build.

**Loco's scaffold is a commitment, not a suggestion.** The generator creates a specific layout (controllers, models, views, workers) and specific choices (SeaORM, its config file, its auth scaffold). Deviating later — swapping SeaORM for sqlx, or replacing the built-in job worker with a custom one — means working against the framework rather than with it. Evaluate the template against your project shape *before* running `loco new`, not after three weeks of development.

**Salvo hoop ordering is semantic, not cosmetic.** Hoops on a router run in registration order, and a hoop that short-circuits (auth rejection, rate limiting) must come before handlers that assume the request is valid. When you nest routers, remember that parent hoops run before child hoops — the same mental model as Tower layers, but the failure mode (a route that bypasses your auth hoop because it was mounted on a sibling subtree) is easier to create by accident.

**Poem's OpenAPI magic has a learning curve around types.** `poem-openapi` requires your request and response types to implement its `ApiResponse`/`Object` traits, and certain ordinary Rust types need wrapper types to be expressible in the spec. The payoff is a spec that cannot drift from the code, but budget a day of reading trait errors when you first build a non-trivial endpoint set.

**Version churn is real across all three.** Loco, Salvo, and Poem all move faster than the classic trio — SemVer bumps that change scaffolding output or hoop signatures do happen. Pin your dependencies, follow each project's changelog, and do not blindly `cargo update` in CI. For context on how the first-generation frameworks compare, see our [Actix-web vs Rocket vs Axum guide](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/), and if you are choosing an HTTP client stack to go with your server, our [reqwest vs hyper vs ureq comparison](../2026-08-17-rust-http-client-libraries-reqwest-hyper-ureq-comparison/) covers that layer. Rust persistence choices are examined in our [Diesel vs SeaORM vs rusqlite comparison](../2026-06-23-rust-database-libraries-diesel-seaorm-rusqlite/), and the async runtime underneath all three is dissected in our [Tokio vs async-std vs smol comparison](../2026-09-03-rust-async-runtimes-tokio-async-std-smol-comparison/).

## FAQ

**Is Loco built on Axum, and does that mean my Axum knowledge transfers?**
Yes — Loco wraps Axum rather than reimplementing it. Your Axum handlers, Tower middleware, and extractor knowledge mostly carry over, which is precisely why Loco describes itself as an opinionated layer on top of the ecosystem's de facto standard. The new material is Loco's own conventions: the app structure, SeaORM-based models, config system, and the `loco` CLI generators.

**Which of the three is fastest at runtime?**
All three are Tokio + Hyper-based and land in the same performance class — within a few percent of each other on comparable benchmarks, and within reach of Actix-web's numbers for typical JSON/CRUD workloads. Framework choice here is a developer-experience decision, not a performance decision; if raw throughput is your differentiator, you should be profiling your database and serialization layers first, not the HTTP framework.

**Can I use Salvo or Poem with Tower middleware written for Axum?**
Partially. Salvo's hoop model is its own abstraction (though it can interoperate with Tower via adapters), while Poem supports Tower-compatible middleware through its `endpoint` middleware machinery. Neither is a drop-in Tower ecosystem citizen the way Axum is. If you have a large investment in custom Tower layers, Loco (being Axum-based) is the only one of the three that consumes them unchanged.

**Do these frameworks support WebSockets and Server-Sent Events?**
Yes — all three support WebSockets and streaming responses as first-class features. Salvo documents WebSocket handling via its `WebSocketUpgrade` extractor, Poem has built-in WebSocket support in the core crate, and Loco inherits Axum's WebSocket support. For long-lived connection workloads, review each project's current docs, since streaming APIs have seen active API refinement across all three in 2025-2026.

**Which one has the gentlest learning curve for a team coming from Express or FastAPI?**
Salvo, by a wide margin — handler functions with `#[handler]`, routers, and hoops map almost one-to-one onto Express routes and middleware, and the framework surface is small. Loco has the steepest initial curve because you are also learning SeaORM, its generator conventions, and its config format — but the payoff is that you stop making boilerplate decisions. Poem sits in the middle: the core is simple, while `poem-openapi` adds its own type-system vocabulary.

**Are Loco, Salvo, and Poem production-ready, or experiments?**
Production-ready in different senses. Poem powers Databend and Warpgate; Salvo is used in production Chinese internet companies and has a large documentation site; Loco is the youngest but has the fastest-growing adoption for MVPs and internal tools. All three have stable releases, active maintainers (each repo pushed within the last month), and permissive licenses (Apache-2.0; Poem dual Apache-2.0/MIT). The honest caveat: the classic trio still has the largest hiring pool and Stack Overflow footprint — choose a second-generation framework for its productivity, not for its recruiter recognition.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Next-Gen Rust Web Frameworks in 2026: Loco vs Salvo vs Poem — Which One Should You Actually Use?",
  "description": "Compare Loco 9.1k stars, Salvo, and Poem — the new generation of Rust web frameworks in 2026. Batteries-included scaffolding vs minimalist handlers vs composable OpenAPI-first crates, with code examples and a decision matrix.",
  "datePublished": "2026-09-07",
  "dateModified": "2026-09-07",
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
