---
title: "Ring vs Compojure vs Reitit in 2026: Which Clojure Web Stack Should You Actually Use?"
date: "2026-08-29"
tags: ["clojure", "web-frameworks", "jvm", "functional-programming"]
draft: false
---

Clojure is having a quiet renaissance in 2026. Teams building data-heavy backends, trading systems, and long-lived services keep discovering what the community has known for a decade: the REPL-driven workflow is still the fastest way to build software. But when you ask "which web framework should I use?", you get three different answers that are actually the same answer at different levels: **Ring** (3,884 GitHub stars), **Compojure** (4,112 stars), and **Reitit** (1,581 stars). The confusion is understandable — they are not competitors in the way Rails and Django are. Ring is the HTTP foundation, and Compojure and Reitit are two routing layers that sit on top of it. Here is how they fit together, and which combination you should ship in 2026.

## TL;DR: Quick Verdict

**Ring is not optional** — it is the HTTP abstraction every Clojure web service uses, the same way Rack underpins Ruby. **If you want the simplest possible routing and a huge base of existing tutorials, use Compojure** — a tiny macro DSL that turns `GET`/`POST` into handler routes, mature and stable since 2010. **If you are starting a new project, use Reitit** — routes as plain data, blazing startup compilation, built-in schema coercion, and OpenAPI/Swagger generation for free. My recommendation: **new projects → Ring + Reitit; existing codebases or minimal services → Ring + Compojure.** Both are free, MIT/Eclipse-licensed, and battle-tested in production.

## Feature Comparison at a Glance

| Feature | Ring | Compojure | Reitit |
|---|---|---|---|
| GitHub stars | 3,884 | 4,112 | 1,581 |
| License | MIT | Eclipse Public 1.0 | MIT |
| Last push (2026) | Jun 23 | Sep 2025 | Aug 24 |
| Role | HTTP foundation | Routing DSL (macros) | Data-driven router |
| Handler model | fn request → response | defroutes macros | Data + fn handlers |
| Path params | manual | `:id` destructuring | `:path-params` + coercion |
| Middleware | ✅ core concept | via Ring | ✅ registry + per-route |
| OpenAPI/Swagger | ❌ | ❌ | ✅ built-in |
| Schema coercion | ❌ | ❌ | ✅ (malli/clojure.spec) |
| REPL-friendly | ✅ | ✅ | ✅ |
| Learning curve | Low | Low | Medium |

## Scenario Decision Matrix

| Use Case | Recommended Stack | Why |
|---|---|---|
| New greenfield API service | **Ring + Reitit** | Data-driven routes, coercion, Swagger generation, per-route middleware |
| Legacy app maintenance | **Ring + Compojure** | Existing codebases are almost all Compojure; keep momentum |
| One-file prototype / script | **Ring + Compojure** | Minimal boilerplate; 5 lines to a running server |
| Public API with documented contracts | **Ring + Reitit** | OpenAPI spec generated from routes, no drift |
| Team without Clojure experience | **Ring + Compojure** | Most tutorials, most Stack Overflow answers, simplest mental model |
| High-throughput routing (1000s of routes) | **Ring + Reitit** | Router compiled at startup; faster dispatch than macro chains |

## Ring — The Foundation Every Clojure Web App Stands On

Ring, maintained by the ring-clojure org, defines the contract that makes every other Clojure web library work: **a handler is just a function that takes a request map and returns a response map**. That one idea — no classes, no interfaces, no framework magic — is why the Clojure web ecosystem has stayed so clean for over a decade. Ring ships adapters for Jetty, Aleph, http-kit, and servlet containers, plus a middleware library for cookies, sessions, and params.

A minimal Ring app (using the Jetty adapter):

```clojure
(ns my-app.core
  (:require [ring.adapter.jetty :refer [run-jetty]]
            [ring.util.response :refer [response]]))

(defn handler [request]
  (response "Hello, world!"))

(run-jetty handler {:port 3000})
```

Add it to `deps.edn`:

```clojure
{:deps {org.clojure/clojure {:mvn/version "1.12.0"}
        ring/ring {:mvn/version "1.12.2"}}}
```

The middleware concept is where Ring earns its keep. Middleware is a function that wraps a handler and augments the request or response — logging, auth, CORS, compression, CSRF. Because it is just function composition, you can compose, reorder, and reason about your stack without a framework opinion getting in the way. This is Ring's entire philosophy, and it has not changed since 2009 because it does not need to.

## Compojure — The Classic Macro DSL

Compojure, by James Reeves (the same person who wrote Ring), is the routing layer that defined Clojure web development for a decade. It uses **macros to turn route definitions into handler functions**: `GET`, `POST`, `PUT`, `DELETE`, and friends, with destructuring of path parameters built into the macro syntax. At **4,112 stars**, it is still the most-installed Clojure routing library — and it remains the safest choice for anyone maintaining existing code.

```clojure
(ns my-app.routes
  (:require [compojure.core :refer [defroutes GET POST]]
            [compojure.route :as route]))

(defroutes app
  (GET "/" [] "Hello, world!")
  (GET "/users/:id" [id] (str "User " id))
  (POST "/users" [name] (str "Created user " name))
  (route/not-found "Not found"))
```

Add the dependency (version 1.7.2 is the current stable line):

```clojure
{:deps {compojure/compojure {:mvn/version "1.7.2"}}}
```

Compojure's genius is its simplicity: routes read top-to-bottom, first match wins, and the macro takes care of grouping routes into a single Ring handler. The cost of that simplicity is that **routes are code, not data** — you cannot easily iterate over them, generate docs from them, or attach per-route middleware without extra plumbing. For small to medium services this never matters. Compojure's last push was September 2025, which worries some people — but it is feature-complete and stable, and "not changing" is a feature for a library this mature.

## Reitit — The Modern, Data-Driven Router

Reitit, from Metosin (the Finnish consultancy behind many core Clojure libraries), approaches routing from the opposite direction: **routes are plain Clojure data**, and everything — middleware, coercion, docs, name generation — falls out of that data. At **1,581 stars** it is smaller by the numbers but is the default choice in 2026 for new projects, and it received a commit on August 24, 2026.

```clojure
(ns my-app.routes
  (:require [reitit.ring :as ring]))

(def app
  (ring/ring-handler
    (ring/router
      [["/" {:get {:handler (fn [_] {:status 200 :body "Hello, world!"})}}]
       ["/users/:id"
        {:get {:handler (fn [{{{:keys [id]} :path-params} :parameters}]
                          {:status 200 :body (str "User " id)})}}]])
    (ring/create-default-handler)))
```

The data-driven model unlocks capabilities that macros cannot offer:

- **Per-route middleware** — attach auth or rate limiting to a single route via the route data, not by wrapping handlers by hand.
- **Schema coercion** — declare parameters with Malli or clojure.spec and Reitit validates and coerces them automatically, eliminating an entire class of bugs.
- **OpenAPI generation** — point `reitit-openapi` at your router and get a complete Swagger spec, with zero drift because it is generated from the same data that dispatches requests.
- **Compiled dispatch** — the router builds an optimized lookup structure at startup, which keeps dispatch fast even with thousands of routes.

Reitit also composes with everything Ring: it produces a plain Ring handler, so middleware and adapters behave exactly as you expect. The learning curve is the price — route data syntax, the `:parameters` destructuring pattern, and coercion setup take a day or two to internalize.

## Common Pitfalls and Migration Notes

**1. Middleware order is the #1 source of bugs.** In Ring, middleware wraps handlers, so the LAST wrap in your `->` threading is the FIRST to run on the request. A CSRF middleware placed inside the session middleware sees no session; a logging middleware placed outside error handling misses errors. Draw the onion — middleware order is request order.

**2. Jetty adapter versions matter.** `ring-jetty-adapter` tracks Jetty major versions (Jetty 9, 10, 11). If you mix a Jetty 9 adapter with Jetty 11 transitive deps, you get confusing classloader errors. Pin `ring/ring-jetty-adapter` and let Ring resolve the rest.

**3. Compojure routes are first-match-wins.** A catch-all `(GET "/:id" ...)` placed before your real routes will shadow them. Order matters, and there is no compiler warning. Reitit's data structure makes the same mistake visible at a glance.

**4. Path parameter syntax differs between the two routers.** Compojure uses `:id` (keyword) and destructures in the route vector; Reitit uses `:id` in the path string and reads it from `:path-params`. When migrating, your handler code changes shape — budget for it and use Reitit's `:parameters` destructuring consistently.

**5. Don't reach for the servlet API.** Ring adapters expose the servlet world, but writing servlet-specific code (request attributes, `getParameter`) couples you to Jetty and breaks REPL-driven testing. Stay in Ring's request map abstraction; that is the entire point.

**6. Coercion is not magic — declare it.** Reitit only coerces what you declare with `:parameters`. Forgetting the declaration silently passes raw strings through, which reintroduces exactly the bugs coercion was meant to kill. Always pair `:parameters` with a Malli schema in production routes.

**7. REPL workflow: reload namespaces, not the server.** The Ring+Reitit stack makes hot reload trivial: redefine the handler var and re-run `ring-handler` to rebind the running server's handler. Wrap this in a `dev` namespace with a `reset` function and you get instant feedback loops without restarting Jetty.

If you are exploring functional programming patterns in other ecosystems, our [TypeScript functional programming comparison](../2026-08-19-typescript-functional-programming-effect-fp-ts-neverthrow-comparison/) and the [C# functional programming guide](../2026-07-05-csharp-functional-programming-languageext-fsharp-patterns/) are good companions, and for the build side of the JVM, see the [Gradle vs Maven vs SBT comparison](../2026-06-24-jvm-build-tools-gradle-maven-sbt-bazel/).

## FAQ

**Q: Do I need Ring if I use Reitit?**
A: Yes. Reitit is a router that produces a Ring handler — you still need Ring (and an adapter like `ring-jetty-adapter`) to serve HTTP. Ring is the foundation of the whole Clojure web stack, including Compojure and Reitit.

**Q: Is Compojure abandoned?**
A: No. Its last push was September 2025, and it is feature-complete and stable after 15 years of production use. Low commit activity on a mature library is normal; the project is not dead, and it remains the most widely deployed Clojure router.

**Q: Which is faster, Compojure or Reitit?**
A: Reitit. It compiles routes into an optimized dispatch structure at startup, which is measurably faster than Compojure's linear macro expansion, especially with hundreds or thousands of routes. For small apps the difference is irrelevant.

**Q: Can I migrate an existing Compojure app to Reitit incrementally?**
A: Yes. Reitit's `ring-handler` produces a standard Ring handler, and Compojure routes also reduce to Ring handlers, so you can mount both behind one adapter while you migrate route-by-route. Path parameter and destructuring differences are the main adjustments.

**Q: What about Pedestal or other Clojure frameworks?**
A: Pedestal (2,779 stars) is a full framework with interceptor pipelines and a different philosophy — worth evaluating for very large services, but it is heavier and has a steeper learning curve. For most teams, Ring + Reitit covers everything with far less machinery.

**Q: Does Reitit support OpenAPI documentation?**
A: Yes. The `reitit-openapi` integration generates an OpenAPI 3 spec directly from your route data, and `reitit-swagger-ui` serves a live Swagger UI for it. Because the spec is generated from the same data that dispatches requests, it never drifts from the actual API.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ring vs Compojure vs Reitit in 2026: Which Clojure Web Stack Should You Actually Use?",
  "description": "A practical comparison of the Clojure web stack in 2026 — Ring, Compojure, and Reitit — covering how they layer, routing styles, middleware, coercion, OpenAPI generation, and migration guidance.",
  "datePublished": "2026-08-29",
  "dateModified": "2026-08-29",
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
