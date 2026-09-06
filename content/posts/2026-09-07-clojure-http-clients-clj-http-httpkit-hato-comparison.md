---
title: "Clojure HTTP Clients in 2026: clj-http vs http-kit vs hato — Which One Should You Actually Use?"
date: "2026-09-07"
tags: ["clojure", "http", "http-client", "networking", "libraries", "jvm"]
draft: false
---

Clojure does not ship an HTTP client in its standard library — a deliberate gap that leaves every project to pick from a menu of wrappers, each gluing Clojure idioms onto a different Java networking stack. Pick wrong and you discover it only under load: **threads you did not know existed, connection pools that silently exhaust, or responses that arrive on callback threads you never joined**. The three clients every Clojure developer evaluates — **clj-http** (1,824 stars), **http-kit** (2,565 stars) and **hato** (418 stars) — are not three flavors of the same thing. They encode three different answers to one question: *who owns the connection, and how does the response get back to you?*

## TL;DR — Quick Verdict

**Building a server-side integration that talks to a handful of well-behaved REST APIs? Use clj-http** — it is the mature default, wraps Apache HttpClient, and its option map (`:query-params`, `:basic-auth`, `:timeout`) is the vocabulary every other client copied. **Writing an event-driven service that juggles hundreds of concurrent outbound calls, WebSockets, or long-polling? Use http-kit** — its client is a promise-returning, non-blocking API backed by an nginx-style event loop, and it is the only one of the three that also replaces your Ring server. **Targeting HTTP/2, or running on JDK 11+ with zero extra dependencies to manage? Use hato** — it wraps the JDK's built-in `java.net.http.HttpClient`, gives you HTTP/2 by default, and keeps the dependency footprint at exactly one JAR. All three are MIT or Apache-2.0, Clojure-idiomatic, and actively maintained in 2026 — but the concurrency model you choose is the one you will live with.

## Quick Comparison Table

| | clj-http | http-kit | hato |
|---|---|---|---|
| Underlying engine | Apache HttpClient (sync) / core.async (async ns) | Own event-driven NIO loop | JDK `java.net.http.HttpClient` |
| Repo / stars | `dakrone/clj-http` — 1,824⭐ | `http-kit/http-kit` — 2,565⭐ | `gnarroway/hato` — 418⭐ |
| Latest version | 3.13.1 | 2.8.1 (2.9.0-beta4) | 1.0.0 |
| Last push | 2026-07-30 | 2026-08-21 | 2025-07-16 |
| License | MIT | Apache-2.0 | MIT |
| HTTP/2 | Via Apache (opt-in) | No | ✅ Default (falls back to 1.1) |
| Async style | `clj-http.async` + core.async channels | Promises + callbacks | `CompletableFuture` + callbacks |
| WebSocket client | No | ✅ Yes | ✅ Yes |
| Streaming bodies | ✅ `:as :stream` | ✅ `:as :stream` / `:as :byte-array` | ✅ `:as :stream` |
| Can act as Ring server | ❌ | ✅ Yes | ❌ |
| JAR size / deps | Moderate (Apache stack) | ~90 kB, zero deps | One JAR, JDK-provided engine |
| JDK floor | Java 8+ | Java 8+ | **JDK 11+** |

## Decision Matrix — Which One for Your Use Case?

| Use case | Recommended client | Why |
|---|---|---|
| Classic REST calls with JSON, auth, timeouts | clj-http | Option-map ergonomics, huge community mindshare |
| Hundreds of concurrent outbound requests | http-kit | Non-blocking event loop, promises, no thread-per-request |
| WebSockets + HTTP in one service | http-kit | Unified client+server API, long-polling built in |
| HTTP/2 endpoints, modern JDK baseline | hato | HTTP/2 by default, zero transitive deps |
| Streaming a large file download | clj-http or http-kit | Both support `:as :stream`; pick your concurrency model |
| Ring app that also needs a client | http-kit | One dependency covers server and client |
| GraalVM native-image service | http-kit | Repo runs dedicated Graal test CI |

## clj-http — The Default That Everyone Copies

clj-http has been the community default since 2010, and its design decision was simple: wrap Apache HttpClient, then expose every knob as a flat Clojure map. Functions like `client/get` are sugar over the general `client/request`, which accepts anything the specialized calls do:

```clojure
(require '[clj-http.client :as client])

(client/get "http://example.com/resources/id")

;; Options are just data
(client/get "http://example.com/resources/3" {:accept :json})
(client/get "http://example.com/resources/3"
            {:accept :json :query-params {"q" "foo, bar"}})

;; Nested maps become nested query strings: a[e][f]=6&a[b][c]=5
(client/get "http://example.com/search"
            {:query-params {:a {:b {:c 5} :e {:f 6}}}})

;; Headers as strings or keywords
(client/get "http://example.com"
            {:headers {"X-Custom" "value"}})

;; Timeouts, redirects, TLS
(client/get "https://api.example.com"
            {:socket-timeout 1000
             :connection-timeout 1000
             :insecure? false
             :max-redirects 5
             :redirect-strategy :graceful})
```

POSTs follow the same shape — the option map is the whole API surface:

```clojure
(client/post "http://example.com/api"
             {:basic-auth ["user" "pass"]
              :body "{\"json\": \"input\"}"
              :headers {"X-Api-Version" "2"}
              :content-type :json
              :accept :json
              :socket-timeout 1000
              :connection-timeout 1000})
```

clj-http transparently decompresses `gzip`/`deflate`, follows redirects on 30x statuses (the full chain lands in `:trace-redirects`), and gives you cookie policies from `:none` to RFC 6265 `:standard-strict`. When the response map comes back, decoding is your job: pair it with `cheshire` or `jsonista` and thread `(:body resp)` through your parser — see our [Erlang JSON libraries comparison](../2026-09-05-erlang-json-libraries-jiffy-jsx-jsone-comparison/) for why explicit decoding beats magic.

**Async exists but is bolted on.** The `clj-http.async` namespace returns core.async channels and needs a core.async dependency plus a thread pool — workable, but it shows its age next to the native async models below. If most of your calls are fire-and-forget or you are already deep in core.async pipelines (the style we covered in our [Clojure async libraries comparison](../2026-09-04-clojure-async-libraries-core-async-manifold-aleph-comparison/)), it fits right in; otherwise the next two clients feel cleaner.

## http-kit — Event-Driven Client and Server in ~90 kB

http-kit began as a fast Ring server and grew a client with the same philosophy: **event-driven, non-blocking, zero dependencies** — the whole client+server JAR is roughly 90 kB and about 3,000 lines of code, with an nginx-style architecture that the project has demonstrated serving 600,000+ concurrent connections. Created by Feng Shen and now community-maintained, it is the Clojure client that behaves least like the JVM.

The client API is modelled after clj-http but returns **promises** instead of blocking:

```clojure
(ns my-ns
  (:require [org.httpkit.client :as hk-client]))

;; Returns almost immediately; deref to block for the result
(def resp-promise (hk-client/get "http://host.com/path"))
@resp-promise
;; or with a timeout and fallback value
(deref resp-promise 5000 :my-timeout-val)

;; Two simultaneous requests
(let [resp1 (hk-client/get "http://http-kit.org/")
      resp2 (hk-client/get "http://clojure.org/")]
  (println "Status 1:" (:status @resp1))
  (println "Status 2:" (:status @resp2)))
```

Or skip deref-ing entirely and pass a callback — every request option is forwarded to it, so you can carry state along:

```clojure
(hk-client/get "http://host.com/path"
  {:timeout      200            ; milliseconds
   :basic-auth   ["user" "pass"]
   :query-params {:param "value"}
   :user-agent   "my-service/1.0"
   :headers      {"X-Header" "Value"}}
  (fn async-callback [{:keys [status headers body error]}]
    (if error
      (println "Failed:" error)
      (println "Async HTTP GET:" status))))
```

Streaming and keep-alive are first-class: `{:as :stream}` hands you an `InputStream`, `{:as :byte-array}` buffers, and `:keepalive` lets you pin or disable connection reuse per request. Because the server and client share the event loop, one http-kit dependency can power an entire Ring service *and* its outbound calls — a pairing worth remembering when you read our [Erlang HTTP server comparison](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) and compare BEAM-style event loops with what a JVM library can do.

**The trade-off:** http-kit does not speak HTTP/2, and its callback/promise model takes getting used to if you are accustomed to plain blocking calls — accidental deref-ing on the event loop thread is the classic way to stall a whole service.

## hato — HTTP/2 on the JDK's Own HttpClient

hato is the youngest of the three and the most opinionated about the modern JDK: it wraps `java.net.http.HttpClient` — built into every JDK since 11 — which means **no Apache stack, no Netty, no transitive dependencies**, and HTTP/2 enabled by default with automatic fallback to HTTP/1.1. Its README is explicit about the floor: JDK 11 and above; on older Java, use clj-http.

The quickstart is as simple as the others:

```clojure
(ns my.app
  (:require [hato.client :as hc]))

(hc/get "https://httpbin.org/get")
;; => {:request-time 112, :status 200, :body "{\"url\" ...}", ...}
```

hato pushes you toward a reusable client with connection pooling, which is the right habit anyway:

```clojure
;; Build once, reuse for every request
(def c (hc/build-http-client {:connect-timeout 10000
                              :redirect-policy :always}))

(hc/get "https://httpbin.org/get"  {:http-client c})
(hc/head "https://httpbin.org/head" {:http-client c})
```

Async requests return a `CompletableFuture` — or take `respond`/`raise` callbacks, with non-2xx statuses routed to `raise` so you can recover via `ex-data`:

```clojure
;; Synchronous (default)
(hc/get "https://httpbin.org/get")

;; Async: deref the CompletableFuture
(-> @(hc/get "https://httpbin.org/get" {:async? true}) :body)

;; Async with callbacks
(hc/get "https://httpbin.org/get"
        {:async? true}
        (fn [resp] (println "Got status" (:status resp)))
        identity)

;; Exceptional statuses land in raise with the response in ex-data
@(hc/get "https://httpbin.org/status/400"
         {:async? true} identity #(-> % ex-data :status))
;; => 400
```

WebSocket support is built in via `hato.websocket`, and hato's own docs suggest wrapping its futures in manifold when you want promise chains — the exact pattern we explored in our [core.async and manifold comparison](../2026-09-04-clojure-async-libraries-core-async-manifold-aleph-comparison/). The one honest caveat is cadence: the project is stable and complete rather than frenetically active (last push July 2025), so it is a better bet for teams that value a fixed, boring dependency than for those chasing new features. If your testing story matters as much as your HTTP story, you can exercise any of these clients inside the frameworks from our [Clojure testing comparison](../2026-09-06-clojure-testing-frameworks-clojure-test-kaocha-midje-comparison/) — all three return plain maps and plain values, which is exactly what good tests want.

## Pitfalls and Migration Notes (What Nobody Tells You)

- **Create one client, not one per request.** clj-http and hato both pool connections per client; building a fresh client per call throws away the pool and, with clj-http, can leak Apache connection managers under load. Build once at app start.
- **Two different timeouts, two different failure modes.** `:connection-timeout` fires when the socket cannot connect; `:socket-timeout` fires mid-response. Set both — a server that accepts then stalls will hang you forever with only one configured. clj-http defaults are generous; be explicit.
- **Never deref a promise on http-kit's event loop.** Blocking the loop thread stalls every other request and callback in the process. Deref from worker threads, or structure the code around callbacks.
- **clj-http async is a separate namespace with real dependencies.** `clj-http.async` pulls in core.async and manages its own thread pool. Budget for it before promising "async with zero new deps."
- **HTTP/2 changes your debugging assumptions.** With hato, multiplexing means one TCP connection carries many requests — tools that count connections (and naive connection-pool limits) will mislead you. Check the actual negotiated version with `:version :http-1.1` if you suspect it.
- **JVM DNS caching bites long-lived services.** The JVM caches DNS lookups (default TTL 30s+ or forever with the security-manager property). Long-running clients keep hitting dead IPs after a failover; tune `networkaddress.cache.ttl` or build a fresh client on retry loops.
- **`insecure?` is a footgun, not a feature.** Skipping TLS verification to "make it work" ships straight to prod. Prefer loading the real cert into a truststore — and if you must bypass in dev, keep it behind a config flag.
- **Migrating from clj-http to hato?** The response maps and option names line up closely (`:query-params`, `:basic-auth`, `:timeout`), but hato's `raise`-callback error model and `CompletableFuture` return type differ from clj-http's exception-on-error and core.async channels. Translate error handling first, then the call sites.

## FAQ

**Which Clojure HTTP client is the most popular?**
clj-http, by a wide margin — 1,824 stars, over a decade of production use, and its option map became the de facto vocabulary for Clojure HTTP. http-kit (2,565 stars) is the more-starred project overall because it includes a Ring server, but as a *client* clj-http remains the default answer in most codebases.

**Does clj-http support HTTP/2?**
Only through the underlying Apache HttpClient's opt-in HTTP/2 support, and not with the turnkey ergonomics of hato. If HTTP/2 is a requirement, hato (JDK HttpClient, HTTP/2 by default) is the straightforward choice — on JDK 11+.

**Can I use http-kit as both server and client?**
Yes — that is its signature feature. A single ~90 kB dependency gives you a Ring-compatible event-driven server, a promise-based client, WebSocket support on both sides, and HTTP long-polling.

**Which client is best for WebSockets?**
http-kit for a unified client+server experience; hato also ships a `hato.websocket` client. clj-http has no WebSocket story — pair it with a separate library if you need one.

**Does hato work on Java 8?**
No. hato requires JDK 11+ because it wraps `java.net.http.HttpClient`, which does not exist in Java 8. For Java 8 projects, clj-http is the stated fallback.

**How do I decode JSON responses?**
None of the three deserialize JSON for you — they return the raw body string (or stream). Use cheshire or jsonista and decode explicitly. The response map's `:body` plus `:status` and `:headers` is the contract across all three clients.

**Are these clients compatible with GraalVM native-image?**
http-kit explicitly tests GraalVM native-image in its CI. clj-http, sitting on the Apache stack, is heavier to native-compile. hato, on the JDK HttpClient, is feasible but less battle-tested in that mode.

**Which one should a new Clojure project pick in 2026?**
For a conventional REST integration: clj-http. For a realtime or high-concurrency service: http-kit (it also covers your server). For a JDK 11+ team that wants HTTP/2 and minimal dependencies: hato. All three are maintained and MIT/Apache-2.0 licensed — you are choosing a concurrency model, not gambling on maintenance.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clojure HTTP Clients in 2026: clj-http vs http-kit vs hato — Which One Should You Actually Use?",
  "description": "Hands-on comparison of the three mainstream Clojure HTTP clients: clj-http (Apache HttpClient), http-kit (event-driven, promise-based) and hato (JDK HttpClient with HTTP/2). Covers async models, WebSockets, streaming, licensing and migration pitfalls.",
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
