---
title: "Dream vs Opium vs Ocsigen in 2026: The Best OCaml Web Framework for Your Next API"
date: "2026-09-04"
tags: ["ocaml", "web-framework", "functional-programming", "backend", "api"]
draft: false
cover: "/img/screenshots/dream-cover.jpg"
---

OCaml used to be the language you reached for when you needed a compiler, a proof assistant, or a high-assurance library — not when you needed to ship a Web API by Friday. That changed. The modern OCaml toolchain (`opam`, `dune`, a mature Lwt ecosystem) now makes server-side Web development practical, and in 2026 the framework choice has narrowed to three serious options: **Dream**, **Opium**, and the **Ocsigen** stack built around Eliom. They embody three completely different philosophies: a batteries-included monolith, a Sinatra-style micro toolkit, and a research-grade full-stack platform where the same OCaml code runs on server *and* browser. Picking wrong means fighting your framework's worldview for years, so here is the data-driven breakdown.

## TL;DR: Quick Verdict

**If you want one dependency that covers routing, sessions, templates, WebSockets, GraphQL and TLS — pick Dream.** It is the modern default: one flat module, one page of documentation, and the largest community of the three. **If you need a lean, composable API layer and like assembling your own stack from Lwt/Cohttp pieces, pick Opium.** **Choose Ocsigen/Eliom only if you genuinely want typed, multi-tier apps** — shared server/client code with statically checked links — and have time for its steep learning curve. For 95% of teams, Dream is the answer.

## Quick Comparison Table

| | Dream | Opium | Ocsigen (Eliom) |
|---|---|---|---|
| **GitHub stars** | 1,879 | 783 | 332 (Eliom) / 105 (server) |
| **Last push** | 2026-05 | 2026-01 | 2026-08 |
| **License** | MIT | MIT | LGPL-2.1 w/ exception |
| **Style** | Full framework, flat module | Micro toolkit (Sinatra-like) | Multi-tier full-stack platform |
| **Routing** | `Dream.router` (typed-ish patterns) | `App.get "/person/:name"` | Services with typed paths/params |
| **Templates** | Embedded OCaml/Reason | Bring your own | TyXML (typed HTML) |
| **Sessions** | Built-in, pluggable backends | Add-on | Built-in, advanced |
| **WebSockets / GraphQL** | ✅ built-in | WebSocket add-on | ✅ (via Ocsigen) |
| **Client-side story** | Melange / ReScript / js_of_ocaml | None | First-class (js_of_ocaml) |
| **Learning curve** | Gentle | Gentle | Steep |

*GitHub stats fetched via API on 2026-09-04.*

## Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| REST/GraphQL API, product CRUD, small SaaS | **Dream** | One opam install, one module to learn, TLS + sessions included |
| JSON API in an existing Lwt app | **Opium** | Rock middleware + Lwt streaming, minimal footprint |
| App where server & client share logic | **Ocsigen/Eliom** | `let%client`/`let%server` annotations in one codebase |
| Realtime (WebSockets, SSE) | **Dream** | Built-in WebSocket support, no proxy gymnastics |
| Teaching OCaml Web dev | **Dream** | Tutorial examples 1-hello → z-streaming are superb |
| High-assurance, research-grade stack | **Ocsigen** | TyXML typed HTML + typed links = fewer runtime 404s |

## Dream: The Batteries-Included Monolith

Dream (1,879 stars, MIT) calls itself "easy-to-use, feature-complete Web framework without boilerplate," and it delivers on that slogan in an unusual way: the entire framework is **one flat module in one package**, documented on one page. Instead of the Java-style sprawl of sub-projects, you learn a single namespace (`Dream.run`, `Dream.router`, `Dream.html`, `Dream.websocket`, …). Web apps are just functions — a handler is `string option -> request -> response promise`, and middleware composes with `@@`. The official hello world is three lines:

```ocaml
let () =
  Dream.run
  @@ Dream.logger
  @@ fun _ -> Dream.html "Good morning, world!"
```

Routing uses URL patterns with named parameters, straight from the official `3-router` example:

```ocaml
let () =
  Dream.run
  @@ Dream.logger
  @@ Dream.router [

    Dream.get "/"
      (fun _ ->
        Dream.html "Good morning, world!");

    Dream.get "/echo/:word"
      (fun request ->
        Dream.html (Dream.param request "word"));

  ]
```

What makes Dream the pragmatic winner: **WebSockets, GraphQL, HTML templating (embedded OCaml or Reason), sessions with pluggable backends, secure cookies, CSRF-safe forms, and native HTTPS/HTTP-2** are all included — you can run Dream without a reverse proxy. Deployment is documented for DigitalOcean, Heroku, and Fly.io with sample CI scripts. The example directory (`1-hello` through `z-streaming`) doubles as a tutorial, and the project's GitHub activity (last push May 2026) reflects a healthy maintenance cadence. If you want full-stack, Dream compiles the same handlers to the browser via Melange, ReScript, or js_of_ocaml — optional, but present.

## Opium: The Sinatra-Style Micro Toolkit

Opium (783 stars, MIT) is deliberately small. Its README describes it as a "Sinatra like web toolkit," and it is built on the **Rock** middleware specification, Lwt, and Cohttp — you compose rather than inherit. You define routes with a builder chain, handlers receive a request and return a response wrapped in `Lwt`:

```ocaml
let print_param_handler req =
  Printf.sprintf "Hello, %s\n" (Router.param req "name")
  |> Response.of_plain_text
  |> Lwt.return
;;

let streaming_handler req =
  let length = Body.length req.Request.body in
  let content = Body.to_stream req.Request.body in
  let body = Lwt_stream.map String.uppercase_ascii content in
  Response.make ~body:(Body.of_stream ?length body) () |> Lwt.return
;;

let _ =
  App.empty
  |> App.get "/hello/:name" print_param_handler
  |> App.post "/hello/stream" streaming_handler
  |> App.run_command
;;
```

That snippet, adapted from the official `example/hello_world` app, shows Opium's personality: path parameters via `Router.param`, request/response bodies as **Lwt streams** for backpressure-friendly uploads, JSON through Yojson combinators, and a `cmdliner`-based `App.run_command` that gives you a real CLI for free. Opium is the right tool when you are building a small service inside a larger Lwt/OCaml codebase and want the framework to stay out of your way. The trade-off: sessions, templating, and WebSockets are your responsibility — Opium gives you HTTP and middleware, not an opinionated stack. Development activity is slower than Dream's (last push January 2026), so check open issues before committing to it for a long-lived product.

## Ocsigen: Eliom and the Typed Full-Stack Dream (from 2006)

Ocsigen is the oldest and most ambitious project here — and the least known. Born in the French academic community (PPS lab, INRIA-adjacent) around 2006, it comprises the **Ocsigenserver** (the HTTP server, 105 stars, last push August 2026) and **Eliom** (the framework, 332 stars, last push August 2026 — still actively developed). Eliom's pitch is radical even in 2026: **OCaml is a multi-tier language**; you write one program, annotate pieces with `let%server`, `let%client`, and `let%shared`, and Eliom compiles the client parts to JavaScript via js_of_ocaml. Types flow across the network boundary. Links are *typed values*, not strings — a route cannot silently rot into a 404 because the compiler checks it.

The official README shows the core model — registering a service on path `/foo`:

```ocaml
let myservice =
  Eliom_service.create
    ~path:(Eliom_service.Path ["foo"])
    ~meth:(Eliom_service.Get (Eliom_parameter.any))
    ()

let () =
  Eliom_registration.Html.register ~service:myservice
    (fun get_params () ->
      Lwt.return
         Eliom_content.Html.F.(html (head (title (txt "")))
                                    (body [h1 [txt "Hello"]])))
```

HTML itself is built with **TyXML**, so your markup is type-checked — invalid nesting or a misspelled attribute is a compile error. Sessions are sophisticated (the project pioneered advanced session mechanisms and server-to-client communication). If your application genuinely needs shared client/server code — say, validation rules or domain logic that must run in both places — Eliom is still the most principled way to get it in the OCaml world, years before "full-stack OCaml" became fashionable.

The costs are real: the learning curve is the steepest of the three (Eliom_service, Eliom_registration, Eliom_parameter, TyXML…), documentation assumes patience, and the LGPL-2.1-with-exception license (rather than MIT) matters if your legal team is strict. Choose it for its unique strengths, not for CRUD convenience.

## Pitfalls and Migration Gotchas

1. **Dream handlers are promises — don't block.** A handler returns `response Lwt.t` (actually Dream's own promise type). If you call `Lwt_main.run` or a blocking `Unix` call inside a handler, you stall the whole server. Use `Dream.sql`, `Lwt_io`, or non-blocking DB drivers throughout.
2. **`Dream.param` name must match the route pattern.** `/echo/:word` + `Dream.param request "word"` works; a mismatch raises `Not_found` at runtime — the pattern variables are *not* compile-time checked in plain Dream (they are in Eliom — that is the trade-off).
3. **Opium bodies are one-shot streams.** `Body.to_stream` can only be consumed once. If you read the body to validate JSON and then try to stream it again, you get an empty stream. Buffer early or restructure.
4. **Opium's Lwt vs Lwt.Syntax.** Mixing `let+` (Lwt.Syntax) with `>>=` style in one handler compiles fine but confuses reviewers — pick one style per module, matching the examples.
5. **Ocsigen is a platform, not a library.** You do not sprinkle Eliom into an existing app; you build inside its server and config model (XML site files, `ocsigenserver.conf`). Budget a week of ramp-up before productivity.
6. **js_of_ocaml size discipline.** Eliom (and Dream's Melange path) compile OCaml to JavaScript — keep the shared code lean, or your browser bundle grows. Measure with a bundler from day one.
7. **Version churn:** Dream 1.x APIs are stable, but examples on the internet from the alpha era (pre-1.0, 2020-2022) show `Dream.run` signatures that changed. Prefer the official `example/` directory as your reference.

## Which One Should You Actually Use?

For new OCaml Web projects in 2026, **Dream is the default choice** — its documentation quality, one-module design, and built-in feature set (WebSockets, GraphQL, TLS, sessions) map directly onto what production APIs need, and the examples make onboarding fast. **Opium** remains excellent for minimal Lwt-native services where you want Rock-style middleware control. **Eliom/Ocsigen** is a specialized instrument: magnificent when you need typed, multi-tier apps, and overkill otherwise. There is no wrong answer among MIT-licensed Dream and Opium — only the wrong expectations about how much framework you want.

For more functional-language Web comparisons, see our [Haskell Web frameworks guide (Yesod, Scotty, Servant)](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) — Servant's typed APIs are the closest spiritual cousin to Eliom's typed links — and the [Clojure Web framework comparison (Ring, Compojure, Reitit)](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/) for the middleware-pipeline philosophy that Opium's Rock echoes. If you are testing OCaml code, our [OCaml testing libraries guide (OUnit, Alcotest, QCheck)](../2026-08-01-ocaml-testing-libraries-ounit-alcotest-qcheck/) pairs naturally with any of these frameworks.

## FAQ

**Is Dream production-ready in 2026?**
Yes. Dream has been stable since its 1.0 line, is MIT-licensed, and is used in production across fintech, internal tooling, and research projects. Its last push was May 2026 and the maintainer keeps the example directory and CI current.

**Does Opium support WebSockets?**
Not built-in. Opium is an HTTP toolkit; realtime needs an additional WebSocket implementation or a companion server. If WebSockets are a core requirement, Dream (built-in) or Ocsigen are better fits.

**What is the difference between Ocsigen, Eliom, and Ocsigenserver?**
Ocsigen is the umbrella project. Ocsigenserver is the HTTP server (configured via XML site files), Eliom is the multi-tier Web framework that runs on it, and TyXML provides typed HTML. Most articles say "Eliom" when they mean the whole stack.

**Can I use Dream with a database?**
Yes — Dream itself stays database-agnostic (the docs demonstrate `Dream.sql` helpers for PostgreSQL/MySQL/SQLite), and it composes with Caqti or direct Lwt drivers. Sessions can persist to SQL backends too.

**Which OCaml framework has the best type safety for URLs?**
Eliom, by design: service paths are typed values, so links between pages are checked at compile time. In Dream, path parameters are strings matched at runtime; in Opium, `Router.param` raises if the parameter is absent.

**Is Ocsigen still maintained?**
Yes. Eliom's repository was pushed as recently as August 2026 and the Ocsigen team continues releasing through opam. Development is slower-paced and community-driven rather than corporate-backed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dream vs Opium vs Ocsigen in 2026: The Best OCaml Web Framework for Your Next API",
  "description": "Deep comparison of OCaml Web frameworks: Dream's batteries-included design, Opium's Sinatra-style micro toolkit, and Ocsigen/Eliom's typed full-stack platform. Real code from official repos, 2026 GitHub stats, decision matrix, and pitfalls.",
  "datePublished": "2026-09-04",
  "dateModified": "2026-09-04",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide"},
  "mainEntityOfPage": "https://www.pistack.xyz/posts/2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/"
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
