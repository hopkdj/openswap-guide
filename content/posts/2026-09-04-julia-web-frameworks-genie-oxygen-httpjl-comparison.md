---
title: "Julia Web Development in 2026: Genie vs Oxygen vs HTTP.jl — Full-Stack, Micro, or Bare Metal?"
date: "2026-09-04"
tags: ["julia", "web-frameworks", "backend", "data-science", "api"]
draft: false
cover: "/img/screenshots/genie-julia-cover.jpg"
---

Julia won the scientific computing crowd with speed that feels like C and syntax that feels like Python. For years that was the whole story — libraries, notebooks, papers — while the web stayed a JavaScript monopoly. In 2026 the situation is unrecognizable: **Genie.jl (2,414 stars), Oxygen.jl (503 stars), and HTTP.jl (688 stars) form a complete Julia web stack**, from batteries-included MVC frameworks to bare-metal transport, and teams are shipping data dashboards, model-serving APIs, and internal tools written entirely in Julia.

The pitch is compelling if you live in the scientific world: your analysis code, your model code, and your web server are one language, one process, no Python bridge, no serialization layer. The confusion starts when you try to pick a framework — the three projects sit at completely different altitudes, and comparing them like-for-like is a category error. This guide maps the terrain with code pulled straight from the official repositories.

## TL;DR — Which Julia Web Stack Should You Pick?

**If you are building a database-backed web application with templates, auth, and background tasks, use Genie** — it is the only full-stack MVC framework in the Julia ecosystem, and it is aggressively maintained (last push September 4, 2026). **If you want to expose a few routes over your existing Julia code — a model, a query, a script — in minutes, use Oxygen** — it is a micro-framework that wraps HTTP.jl with Express-style macros. **If you are writing a library, need WebSocket/HTTP2 primitives, or want to own the request lifecycle, use HTTP.jl directly** — it is the transport layer that Oxygen (and much of the ecosystem) builds on.

## Genie vs Oxygen vs HTTP.jl: The 2026 Comparison

| Dimension | Genie.jl | Oxygen.jl | HTTP.jl |
|---|---|---|---|
| GitHub stars | 2,414 | 503 | 688 |
| Last push (2026) | Sep 4 | Sep 3 | Aug 31 |
| License | MIT | MIT | MIT |
| Layer | Full-stack MVC framework | Micro-framework | HTTP client + server library |
| Routing | `route()` macro + controller files | `@get` / `@post` / `@put` / `@delete` macros | Manual dispatch in your handler |
| Templates | Built-in HTML/JSON/Markdown views | No (return strings/JSON) | No |
| Database | SearchLight ORM (models + migrations) | None (call your own code) | None |
| WebSockets | Yes — `channel()` routes | Yes — `@websocket` macro | Yes — raw upgrade handling |
| Auth | `GenieAuthentication` plugin | Via manual middleware | None |
| Tasks / cron | Built-in task runner | No | No |
| Best for | Data apps, full products | Scripts-to-API, small services | Libraries, custom servers, HTTP clients |

**Decision matrix — 10-second pick**

| Use case | Recommendation | Why |
|---|---|---|
| Internal data app with auth + DB (replaces a Shiny app) | Genie | MVC structure, SearchLight ORM, templates, auth plugin — everything included |
| Expose a trained model or a query as an endpoint | Oxygen | `@get "/predict"` + `serve()` is the whole deployment |
| Library author needing an HTTP server or client | HTTP.jl | Primitives without framework opinions; also the ecosystem's transport |
| WebSocket dashboards pushing live updates | Genie or Oxygen | Both have first-class WS support (`channel()` vs `@websocket`) |
| Script that must also serve an API on demand | Oxygen | Zero project scaffolding; runs from a single file |
| Multi-page app with HTML views | Genie | Template renderer built in; Oxygen expects JSON-first clients |

## Genie — The Only Full-Stack MVC Framework in Julia

Genie, from the GenieFramework organization, is Julia's answer to Rails or Django: an opinionated MVC framework with routing, view templates, an ORM (SearchLight), authentication, WebSockets, and a task runner. Its GitHub description — "The highly productive Julia web framework" — undersells how far it has come; the project now powers commercial "data apps" products and has a documented path from REPL experiment to deployed application.

The README's hello world shows how routing composes with the framework's HTML and JSON renderers:

```julia
# Genie Hello World!
# As simple as Hello
using Genie
route("/hello") do
    "Welcome to Genie!"
end

# Powerful high-performance HTML view templates
using Genie.Renderer.Html
route("/html") do
    h1("Welcome to Genie!") |> html
end
```

WebSocket endpoints are declared with the `channel` macro, which wires a route to a function that processes live messages — the REPL output in the README shows the server registering the handler immediately:

```julia-repl
julia> using Genie, Genie.Router

julia> channel("/foo/bar") do
         # process request
       end
[WS] /foo/bar => #1 | :foo_bar
```

Beyond routing, the README tours the pieces that make Genie a full platform: database-backed authentication via `Pkg.add("GenieAuthentication")` followed by `GenieAuthentication.install(@__DIR__)`, and a task system that "allows you to perform various operations and hook them with cron jobs for automation." For teams that need scheduling, that is the difference between a framework and a toy.

**Where Genie costs you**: it is the most opinionated option — projects adopt its directory structure, its SearchLight ORM conventions, and its REPL-driven workflow. Julia compilation latency also bites hardest here: a large Genie app has a noticeable first-load compile, which is why the ecosystem pushes precompilation and containerized warm starts.

## Oxygen — The Micro-Framework for Script-to-API

Oxygen describes itself as "a breath of fresh air for programming web apps in Julia" and, more precisely, as "a micro-framework built on top of the HTTP.jl library." It brings Express-style decorators to Julia: annotate a function with a route macro, call `serve()`, and your script is a web service.

The entire hello world from the official README:

```julia
using Oxygen
using HTTP

@get "/greet" function(req::HTTP.Request)
    return "hello world!"
end

# start the web server
serve()
```

Request handlers can be plain functions, and the macro system extends to the full HTTP verb set plus streaming and WebSockets:

```julia
# Stream Handler
@stream "/stream" function(stream::HTTP.Stream)
    ...
end

# Websocket Handler
@websocket "/ws" function(ws::HTTP.WebSockets.WebSocket)
    ...
end
```

Because handlers are ordinary Julia functions, everything you can do in a Julia process — query a DataFrame, evaluate a model, read a file — is directly callable inside a route. That is Oxygen's whole thesis: **no project scaffolding, no ORM decision, no config files**; add the package and annotate.

**Where Oxygen costs you**: there is no built-in templating, auth, or persistence — you bring them. Route registration happens at module load time via the macros, so dynamic route registration needs `@register`-style workarounds. And with ~500 stars and a small contributor base, you are closer to the bleeding edge than with Genie's larger community.

## HTTP.jl — The Transport Layer Everything Sits On

HTTP.jl is the official low-level HTTP client and server for Julia — "HTTP client and server functionality" with HTTP/2, WebSockets, Server-Sent Events, cookies, multipart forms, retries, and proxy-aware transports. It targets Julia 1.10 and later, and version 2.0 was a deliberate breaking release with a published migration guide covering response fields, connection pooling, and server APIs.

The official documentation's server example shows the do-block style:

```julia
using HTTP

server = HTTP.serve!("127.0.0.1", 0; listenany = true) do req
    payload = "hello from HTTP.jl docs"
    return HTTP.Response(
        200;
        headers = ["Content-Type" => "text/plain"],
        body = payload,
    )
end

url = "http://127.0.0.1:$(HTTP.port(server))/hello"
resp = HTTP.get(url; proxy = HTTP.ProxyConfig())
HTTP.forceclose(server)
String(resp.body)
```

The same package gives you the client side — note the `HTTP.get` call and the `HTTP.ProxyConfig()` plumbing in the example above, which shows how seriously the project treats production concerns like proxies and connection lifecycle. Installation is a one-liner in either Pkg mode or function form: `pkg> add HTTP`.

**Where HTTP.jl costs you**: it is a toolkit. Routing, middleware, static files, and request logging are yours to implement or assemble. Its value proposition is control: Oxygen is built on it (per the Oxygen README), Genie's networking stack interoperates with it, and if you outgrow both, you drop to HTTP.jl without learning a new transport.

## Pitfalls When Building Julia Web Services

1. **First-request latency is real.** Julia compiles on first execution; a cold endpoint can take seconds before serving. Mitigate with package precompilation, `--compile=min` tuning for servers, and warm-up pings after container start. Do not benchmark "hello world" before the second request.
2. **Don't fight Genie's structure.** Genie apps expect the MVC layout and SearchLight models. Hand-rolling SQL while ignoring SearchLight works, but you lose migrations and the admin conventions — adopt the framework or pick a lighter one.
3. **Oxygen macro registration happens at load time.** Routes defined inside functions or conditionals won't register until that code runs; define routes at module top level. If you need dynamic endpoints, use HTTP.jl directly or rework the design.
4. **WebSockets behind a reverse proxy need upgrade support.** nginx and Caddy must pass the `Upgrade` and `Connection` headers (or you use a proxy with native WS support) or your `channel()`/`@websocket` routes will silently fail for remote clients while working locally.
5. **Container size surprises.** Julia images are large (hundreds of MB) unless you use the slim variants and `--strip` builds; budget CI time for precompilation layers so deploys stay fast.
6. **HTTP.jl 1.x → 2.x breakage.** Third-party packages may still target HTTP.jl 1.x APIs (response fields, pooling). Check compat before upgrading a project that depends on the ecosystem — the migration guide exists because the changes are not cosmetic.
7. **If your endpoint is a thin wrapper over a dataframe or a model, skip the framework entirely** — HTTP.jl's do-block server is ~10 lines. For comparison, see how [Crystal's Kemal/Lucky/Amber](../2026-08-31-crystal-web-frameworks-kemal-lucky-amber-comparison/) or [Erlang's Cowboy/MochiWeb/Yaws](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) solve the same spectrum — and if your "data app" is really an R Shiny workload, our [Shiny Server vs ShinyProxy deployment guide](../2026-06-09-self-hosted-r-shiny-deployment-shiny-server-shinyproxy-rstudio-connect/) may be the better fit.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Julia Web Development in 2026: Genie vs Oxygen vs HTTP.jl — Full-Stack, Micro, or Bare Metal?",
  "description": "Compare Genie.jl, Oxygen.jl, and HTTP.jl — the three Julia web stacks of 2026 — with official code samples, GitHub stats, a feature table, and a decision matrix for data apps, model APIs, and library authors.",
  "datePublished": "2026-09-04",
  "dateModified": "2026-09-04",
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

**Is Julia fast enough for production web servers?**
Yes for typical API and data-app workloads — Julia's compiled performance plus the async HTTP.jl transport handles thousands of concurrent requests on modest hardware. The caveat is compile-time latency on cold starts, which precompilation and warm-up strategies mitigate.

**What is the difference between Genie and Oxygen?**
Genie is a full-stack MVC framework (templates, ORM, auth, tasks, WebSockets) for complete applications. Oxygen is a micro-framework built on HTTP.jl that turns scripts into APIs with route macros. Genie is the Rails of Julia; Oxygen is the Express.

**Does Julia have an ORM for web development?**
Yes — Genie ships with SearchLight, its own ORM with models and migrations, and Genie's database tooling is part of the framework's `app` generators. Oxygen and HTTP.jl deliberately leave data access to your own code.

**Can I serve a machine learning model with Julia web frameworks?**
Easily — loading a model and calling it inside an Oxygen `@post` handler or a Genie route is idiomatic Julia, with no separate serving process or serialization bridge. This is one of the most common production uses of Oxygen in the scientific ecosystem.

**Does HTTP.jl support HTTP/2 and WebSockets?**
Yes — HTTP.jl provides HTTP/2, WebSockets, and Server-Sent Events on both client and server sides, which is why higher-level frameworks build on it rather than reimplementing transport.

**Which Julia web framework has the biggest community in 2026?**
Genie is the largest by a wide margin (2,414 stars, very active development through September 2026) and the only one with a commercial ecosystem around it. Oxygen (~503 stars) is smaller but growing quickly among researchers, while HTTP.jl (~688 stars) has the broadest *usage* because it underpins client and server code across the package ecosystem.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
