---
title: "F# Web Frameworks in 2026: Giraffe vs Falco vs Saturn"
date: "2026-08-13"
tags: ["fsharp", "dotnet", "web-frameworks", "developer-tools"]
draft: false
cover: "/img/screenshots/giraffe-hello.png"
---

You've decided to build your next web service in F#, and the first thing you discover is that the .NET ecosystem gives you three different ways to do it — Giraffe, Falco, and Saturn — and they all sit on top of ASP.NET Core. That's both a blessing and a trap. The frameworks look similar at a glance (all functional-first, all built on Kestrel, all NuGet-installable in minutes), but they encode fundamentally different philosophies about how F# web development should work. Pick wrong, and you'll spend months fighting a routing model that fights back.

The F# web framework scene was quiet for years — Suave and Giraffe were the only real options, and Suave's standalone server model fell out of favor as ASP.NET Core became the industry standard. Now the ecosystem has settled into a clear three-way race. This guide breaks down what each framework actually gives you, with code from the official repositories, real community data, and a decision matrix you can use today.

## TL;DR — Quick Verdict

**Choose Giraffe if you want the mature, battle-tested standard** — it's the safest default with the largest community (2,250 stars), deep ASP.NET Core integration, and the richest ecosystem of companion libraries. **Choose Falco if you want a lean, modern, all-in-one toolkit** — it's the newest contender (638 stars but actively developed), pairs HTTP handling with a native markup DSL, and feels like F# was designed for it. **Choose Saturn if you want Rails-style productivity** — its `application` computation expression and MVC conventions give you the fastest path from idea to working CRUD app, at the cost of magic you'll eventually need to understand.

## Comparison at a Glance

| Feature | Giraffe | Falco | Saturn |
|---|---|---|---|
| GitHub Stars | 2,250 | 638 | 726 |
| Last Update | Aug 2026 | Jul 2026 | Jul 2024 |
| License | MIT | Apache 2.0 | MIT |
| Built On | ASP.NET Core | ASP.NET Core | ASP.NET Core (via Giraffe) |
| Core Abstraction | `HttpHandler` functions | `HttpHandler` + markup DSL | `application` computation expression |
| Routing Style | `route`, `choose`, `>=>` combinators | `route` + `Request.bind` | MVC controllers + `router` CE |
| View/Markup | External (Giraffe.ViewEngine, Razor) | Native `Falco.Markup` DSL | External (Giraffe.ViewEngine, Razor) |
| Learning Curve | Medium | Low-Medium | Low (conventions do the work) |
| WebSockets/SSE | Via ASP.NET Core | Via ASP.NET Core | Via ASP.NET Core |
| OpenAPI Support | Manual / community | First-party `Falco.OpenApi` | Manual |
| htmx Integration | Community | First-party `Falco.Htmx` | Community |
| Ecosystem Maturity | Large (years of libraries, blog posts, Stack Overflow answers) | Growing fast | Established (SAFE Stack) |
| Suited For | Full control, large teams | Lean APIs and full-stack apps | Convention-driven CRUD apps |

## Decision Matrix — Which One for Your Use Case?

| Use Case | Recommended Tool | Why |
|---|---|---|
| Production API for a large team | **Giraffe** | Most community knowledge, best documentation, safest hiring pool |
| Greenfield full-stack app (HTML + htmx) | **Falco** | Markup DSL + htmx support means no JS framework needed for the UI |
| Rapid internal CRUD tool | **Saturn** | `application` CE and controllers ship a working app in one file |
| Microservice that needs to be tiny | **Falco** | Minimal dependencies; the "Hello World" is a single function |
| Team coming from ASP.NET MVC | **Saturn** | Controller and routing conventions map directly to MVC mental models |
| Library author building F# HTTP tooling | **Giraffe** | `HttpHandler` is the de facto standard abstraction; Saturn itself is built on it |

## Giraffe — The Standard-Bearer

Giraffe is the framework that made functional web development viable on ASP.NET Core. Its core idea: every handler is a function of type `HttpFunc -> HttpContext -> Async<HttpContext option>`, and you compose them with the `>=>` (bind) and `choose` combinators. This gives you a pipeline model where middleware, routing, and response generation are all the same kind of thing — composable functions.

```fsharp
open System
open Microsoft.AspNetCore.Builder
open Microsoft.AspNetCore.Hosting
open Microsoft.Extensions.Hosting
open Microsoft.Extensions.Logging
open Microsoft.Extensions.DependencyInjection
open Giraffe

let webApp =
    choose [
        route "/ping"   >=> text "pong"
        route "/"       >=> htmlFile "/pages/index.html" ]

type Startup() =
    member __.ConfigureServices (services : IServiceCollection) =
        services.AddGiraffe() |> ignore

    member __.Configure (app : IApplicationBuilder)
                        (env : IHostEnvironment)
                        (loggerFactory : ILoggerFactory) =
        app.UseGiraffe webApp

[<EntryPoint>]
let main args =
    Host.CreateDefaultBuilder(args)
        .ConfigureWebHostDefaults(
            fun webHostBuilder ->
                webHostBuilder
                    .UseStartup<Startup>()
                    |> ignore)
        .Build()
        .Run()
    0
```

Giraffe's real strength is that it doesn't try to hide ASP.NET Core from you. Middleware, authentication, static files, dependency injection — everything from the underlying platform remains accessible, which means every ASP.NET Core tutorial and library works with your F# app. The trade-off is ceremony: you wire up a `Startup` class (or the functional alternative with `WebApplication.CreateBuilder`) and configure services by hand.

The ecosystem is the deepest of the three: Giraffe.ViewEngine for type-safe HTML, community packages for OpenAPI, feature flags, GraphQL, and countless blog posts and Stack Overflow answers. Its 2,250 stars understate its influence — Saturn itself is built on Giraffe's `HttpHandler`, so learning Giraffe teaches you the substrate of the whole F# web world.

## Falco — The Lean Contender

Falco is the framework designed by someone who used Giraffe and decided the F# community deserved better ergonomics. Built by Phil Broughton (whose Kestrel homage gives the project its name), Falco keeps the `HttpHandler` philosophy but wraps it in a tighter, more opinionated API. The Hello World is almost absurdly small:

```fsharp
open Falco
open Microsoft.AspNetCore.Builder

let wapp = WebApplication.Create()

wapp.Run(Response.ofPlainText "Hello world")
```

That's the whole program. No Startup class, no service registration ceremony — just a web application that responds. What makes Falco genuinely different is its scope: it's not just HTTP handling. `Falco.Markup` provides a native F# DSL for authoring HTML, `Falco.Htmx` brings server-driven interactivity, and `Falco.OpenApi` generates OpenAPI docs from your routes. The framework's design goal is "simple, extensible, and integrate with existing .NET libraries" — it wants to be the toolkit you reach for when you want to build the whole app, not just the routing layer.

```fsharp
// Falco routing with a typed GET handler
let handleGetId : HttpHandler =
    fun ctx ->
        let id = Request.getRoute "id" ctx
        Response.ofJson {| id = id; status = "ok" |} ctx

let endpoints = [
    get "/api/items/{id}" handleGetId
    post "/api/items" (Request.bindJson createItem)
]
```

The request-handling API is uniform — `Request.bindJson`, `Request.bindForm`, `Request.getQuery` all funnel through the same abstractions — which eliminates the "which binder do I use today" friction of larger frameworks. The community momentum is real: developers who switch from Giraffe to Falco (there are blog posts about exactly that) cite the smaller API surface and the fact that the framework ships the view layer instead of leaving you to assemble it.

## Saturn — The Opinionated Workhorse

Saturn answers a different question: what if F# web development felt like Ruby on Rails or Elixir's Phoenix? It implements a server-side MVC pattern with an `application` computation expression that configures the entire app declaratively. Saturn is built on Giraffe — the underlying handlers are still `HttpHandler` functions — but it layers conventions on top so you write far less boilerplate.

```fsharp
open Saturn

let app = application {
    url "http://0.0.0.0:8085"
    use_router (text "Hello World")
    memory_cache
    use_static "static"
    use_gzip
}

run app
```

That's a complete, production-shaped web application: URL binding, routing, caching, static files, and compression in a dozen lines. Controllers follow a familiar pattern — `controller { index; show; create; update; delete }` — so anyone who's written ASP.NET MVC or Rails feels at home immediately. The framework ships a router CE, a pipeline CE, and integrates with the ASP.NET Core middleware ecosystem through the same `use_*` declarations.

Saturn's home is the SAFE Stack (Saturn + Azure + Fable + Elmish), a full-stack template that gives you F# on the server and F#-compiled-to-JavaScript on the client. If you want a single language across your entire stack, SAFE Stack with Saturn underneath is the most polished way to get there. The cost is the same as any opinionated framework: when your app outgrows the conventions, you're debugging generated behavior instead of your own code. Development has slowed (last push July 2024), but the framework is stable and the SAFE Stack keeps it relevant.

## Pitfalls and Migration Notes

**1. Saturn is Giraffe underneath — don't mix abstractions blindly.** Saturn handlers ARE `HttpHandler` functions, so you can drop raw Giraffe code into a Saturn app. But `Saturn.Controller` and Giraffe's `choose` route composition solve the same problem differently; combining both in one codebase creates routing confusion. Pick one style per controller.

**2. F# version and .NET version coupling.** Giraffe and Falco track .NET releases aggressively (Giraffe requires recent ASP.NET Core; Falco targets current .NET). Saturn's last release predates some .NET 8/9 features. Check the target framework of the package you're installing against your SDK — a template from two years ago may not restore cleanly today.

**3. The `>=>` operator trips up newcomers.** In Giraffe and Falco, `>=>` composes handlers sequentially (think `|>` for HTTP pipelines), while `choose` picks the first matching route. New F# web developers routinely write `route "/x" >=> text "hi"` when they meant to use `choose` for alternatives — get the combinator semantics straight before writing real routes.

**4. Async is everywhere and it's easy to block.** Handlers return async results; calling `.Result` or `.Wait()` on a task inside a handler deadlocks under load. Use `task {}` or `async {}` consistently and let the framework await your handler. This is the #1 cause of "my F# web app hangs" issues.

**5. JSON serialization defaults differ from your expectations.** Falco's `Response.ofJson` uses System.Text.Json with F#-friendly settings; Giraffe historically defaulted to Newtonsoft.Json in older versions. If you're migrating between them, field-name casing and `Option` handling will differ — verify your API contract after switching.

**6. Static files and SPA fallback need explicit config.** None of the three serves `index.html` for client-side routes by default. You need `UseStaticFiles` + a fallback route (`route "/" >=> htmlFile` in Giraffe, `Response.ofHtml` in Falco, `use_static` in Saturn). Forgetting this is why your API works but your frontend 404s.

## FAQ

**Is Saturn compatible with the latest .NET / ASP.NET Core?**
Saturn's core targets .NET 6+ and is built on Giraffe, so it works with modern .NET — but because it's a convention layer, its release cadence is slower than Giraffe and Falco. For the newest .NET features, check the package's target framework first. The SAFE Stack template is the easiest way to get a known-good Saturn setup.

**Can I use Razor pages with Giraffe or Falco?**
Yes. Both run on ASP.NET Core, so Razor views, Blazor components, and traditional MVC middleware all work alongside functional handlers. Giraffe and Falco don't force you to use their markup DSLs — you can mix Giraffe.ViewEngine, Falco.Markup, or plain Razor per route.

**Which framework has the best performance?**
All three run on Kestrel, so raw throughput is comparable — routing overhead is nanoseconds relative to your actual handler work. The Giraffe repository publishes benchmark results, and Falco's minimal abstraction layer tends to measure marginally lower overhead. For real-world services, choose by ergonomics, not benchmarks.

**What's the difference between Giraffe and Suave?**
Suave is a standalone HTTP server with its own WebPart model; Giraffe is a middleware layer on ASP.NET Core. Suave gives you a self-contained F#-native server but misses the ASP.NET Core ecosystem (identity, caching, hosting, cloud integrations). Giraffe/Falco/Saturn all chose the ASP.NET Core path, which is why Suave is rarely recommended for new production services today.

**Is F# web development production-ready in 2026?**
Yes. Giraffe has run in production at scale for years; Falco and Saturn power real SaaS products. Microsoft's continued investment in F# tooling, plus the ASP.NET Core substrate, makes this a mature stack. The main risk is community size — F# web is a smaller pond than C# or TypeScript, so evaluate your team's comfort with functional patterns honestly.

**How do I handle authentication in these frameworks?**
Through ASP.NET Core's built-in auth middleware. All three frameworks let you use `UseAuthentication`/`UseAuthorization` and the standard cookie/JWT schemes. Giraffe has the most documented examples; Falco ships auth utilities; Saturn integrates via `use_authentication` in the application CE.

## Related Reading

For more on the .NET ecosystem, check our [C# functional programming comparison](../2026-07-05-csharp-functional-programming-languageext-fsharp-patterns/), the [C# HTTP client library guide](../2026-08-02-csharp-http-client-libraries-restsharp-refit-httpclientfactory/), and the [C# DI containers face-off](../2026-07-04-csharp-di-containers-autofac-ninject-castle-windsor-simpleinjector/). If you're exploring functional languages broadly, our [Haskell web frameworks comparison](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) covers the same trade-offs in the Haskell world.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "F# Web Frameworks in 2026: Giraffe vs Falco vs Saturn",
  "description": "Compare Giraffe, Falco, and Saturn — the three F# web frameworks built on ASP.NET Core. Real code examples, GitHub stats, decision matrix, and migration pitfalls.",
  "datePublished": "2026-08-13",
  "dateModified": "2026-08-13",
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
