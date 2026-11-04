---
title: "Racket Web Frameworks in 2026: Built-in web-server vs Koyo vs Spin — Which One Actually Ships?"
date: "2026-11-04"
tags: ["racket", "scheme", "web-frameworks", "self-hosted", "lisp", "libraries"]
draft: false
description: "Racket's built-in web-server, Koyo and Spin compared in 2026: real routing code, continuation vs stateless servlets, database and migration tooling, deployment with raco distribute, and a decision matrix."
---

Racket has shipped a production web server in its default distribution since long before "batteries included" became a marketing line. That is the good news. The confusing news is that Racket now has three plausible ways to build a web application — the built-in `web-server`, the Koyo toolkit layered on top of it, and Spin, a REST micro-framework that has been frozen since 2017 — and the documentation for each assumes you already know which one you want.

This is a practical comparison for someone who has to pick one this week: what each layer actually gives you, where the sharp edges are, and which parts of the ecosystem are still alive.

## TL;DR / Quick Verdict

- **Small service, internal tool, teaching example, or anything where you want zero dependencies beyond `raco pkg install racket`:** use the **built-in `web-server`**. It is in the default distribution, has continuations, `dispatch-rules` routing, an LRU session manager and static file serving. Roughly 15 lines to a running app.
- **A real application with a database, migrations, templates, sessions, config from environment variables, a REPL console and a project generator:** use **Koyo**. It is Racket's closest thing to Django, BSD-3-Clause licensed, and actively maintained (last push October 2026).
- **Do not start anything new with Spin.** It is a pleasant 200-line convenience layer over `web-server` with an expressive routing DSL, MIT licensed, and its last commit was **July 2017**. Its README still tells you to `(require (planet dmac/spin))` — PLaneT, the package system Racket retired years ago.

The one-sentence rule: **`web-server` is the runtime, Koyo is the framework, Spin is a museum piece.**

## Side-by-Side Comparison

| Dimension | Racket `web-server` | Koyo | Spin |
|---|---|---|---|
| Status in 2026 | Maintained, part of core distribution | Maintained (last push 2026-10-19) | **Abandoned** (last push 2017-07-27) |
| GitHub stars | 5,231 (racket/racket) | 159 | 230 |
| License | Apache-2.0 / MIT / LGPL-3.0 (tri-licensed) | BSD-3-Clause | MIT |
| Install | Already present | `raco pkg install koyo` | `raco pkg install <git url>` |
| Routing | `dispatch-rules` | `dispatch-rules+roles` (adds role checks) | `get` / `post` / `put` / `patch` / `delete` |
| Request model | Continuation-based by default, opt-in stateless | Continuation-safe wrappers, session middleware | Continuation-based via `web-server` |
| Templates | X-expressions (`response/xexpr`) | Blueprint template helper + X-expressions | None — you return strings |
| Database layer | `db` library only | `koyo/database`, `define-schema`, migrations | None |
| Auth | Roll your own | Users, roles, password hashing in the `saas` blueprint | None |
| Project generator | None | `raco koyo new` (`minimal` and `saas` blueprints) | None |
| Config management | `getenv` by hand | `define-option` with env prefix, defaults, coercion | None |
| Dev console | `racket` REPL | `koyo/console` with stubbed components | None |
| Deployment story | `raco exe` + `raco distribute`, or plain `racket` | Same, plus its own CLI | Same, if the package still installs |

The star counts deserve a warning label. **`racket/racket`'s 5,231 stars measure interest in the language, not the web server**, and Spin's 230 stars were earned before most current Racket users started writing Racket. Activity dates are the honest signal here.

## Decision Matrix: Pick by Situation

| Your situation | Recommended | Why |
|---|---|---|
| JSON API with a handful of routes | `web-server` + `dispatch-rules` | No dependencies, no framework to learn |
| Internal admin panel with logins | Koyo (`saas` blueprint) | Users, roles, hashing, sessions already wired |
| Prototype you want to delete in a week | `web-server` | Smallest possible surface area |
| App with schema migrations | Koyo | `define-schema` plus migration tooling |
| Teaching continuations or HTTP | `web-server` | The reference implementation of the idea |
| Existing Spin codebase | Migrate to `web-server` or Koyo | No security updates since 2017 |
| You want a Django-like `startproject` | Koyo | `raco koyo new example` |
| You refuse to learn a DSL | `web-server` | Plain functions and `dispatch-rules` patterns |

## Racket's Built-in web-server: The Runtime Everything Else Builds On

The `web-server` library lives in the default Racket distribution. Nothing to install, no version matrix, no dependency drift. A complete application is a request handler plus one `serve/servlet` call:

```racket
#lang racket/base

(require web-server/servlet
         web-server/servlet-env
         web-server/http)

(define (start req)
  (response/xexpr
   `(html
     (head (title "Hello"))
     (body (h1 "Hello from Racket")))))

;; Development server: http://127.0.0.1:8000
(serve/servlet start
               #:port 8000
               #:servlet-path "/"
               #:launch-browser? #f)
```

Those keyword arguments are the real API, not pseudocode. `serve/servlet` defaults to `#:listen-ip "127.0.0.1"`, `#:port 8000`, `#:servlet-path "/servlets/standalone.rkt"` and `#:launch-browser? #t` unless the program is running in command-line mode. Overriding `#:servlet-path "/"` is what turns it from a mounted servlet into an application root — forget it and you will spend twenty minutes wondering why `/` returns a directory listing.

Routing uses `dispatch-rules`, which compiles patterns into a dispatcher and gives you a reverse-URL function for free:

```racket
#lang racket/base

(require web-server/dispatch
         web-server/servlet
         web-server/servlet-env
         web-server/http)

(define (home req)
  (response/xexpr `(html (body (h1 "Index")))))

(define (user-page req id)
  (response/xexpr `(html (body (h1 ,(format "User ~a" id))))))

(define-values (dispatch reverse-uri)
  (dispatch-rules
   [("") home]
   [("users" (integer-arg)) user-page]))

(serve/servlet dispatch
               #:port 8000
               #:servlet-path "/"
               #:launch-browser? #f)
```

The continuation model is the part that surprises people coming from Express or Flask. By default the server captures the continuation of a request so that a handler can be resumed later — the feature that makes multi-step wizards trivial and makes naive servers leak memory under load. For APIs and anything stateless, pass `#:stateless? #t` and the capture is skipped. That single flag is the difference between a predictable memory profile and a slow leak you diagnose in production.

Serving static assets is built in as well, via `#:extra-files-paths`, and sessions come from the bundled LRU manager:

```racket
(require web-server/managers/lru)

(define sessions (make-lru-session-manager #:timeout 3600))
```

What it does not give you: an ORM, migrations, a project layout, authentication, or an admin interface. That is precisely the gap Koyo fills.

## Koyo: Racket's Django-Shaped Toolkit

Koyo describes itself as "a web application development toolkit that expands upon Racket's built-in web-server with all the functionality that a web app typically needs in a complete package", and — importantly — **its components are decoupled**, so you can take the database layer without the templating layer.

Install and scaffold:

```bash
raco pkg install koyo
raco koyo new example           # full scaffold
raco koyo new -b minimal example  # minimal scaffold
cd example && cat README.md
```

The minimal blueprint's router shows the shape of a Koyo app. This is the generated `components/app.rkt`, not an illustration:

```racket
#lang racket/base

(require koyo
         threading
         (prefix-in sequencer: web-server/dispatchers/dispatch-sequencer)
         web-server/managers/lru
         web-server/servlet-dispatch
         "../pages/all.rkt")

(define-values (dispatch reverse-uri _req-roles)
  (dispatch-rules+roles
   [("") home-page]))

(define ((wrap-params handler) req)
  (parameterize ([current-continuation-key-cookie-secure? (not debug?)])
    (handler req)))

(define (stack handler)
  (~> handler
      (wrap-protect-continuations)
      ((wrap-session sessions))
      (wrap-preload)
      (wrap-cors)
      (wrap-profiler)
      (wrap-params)))
```

Three things are worth noticing. `dispatch-rules+roles` extends `dispatch-rules` with role annotations, so authorisation lives next to the route instead of in a middleware you forget to apply. The middleware stack is composed with `threading`'s `~>` — readable, and each wrapper is a plain function you can drop. And `wrap-profiler` is opt-in per configuration, which means you can leave request profiling compiled in and turn it off in production.

Configuration in Koyo is environment-variable driven with typed defaults, using `define-option` and a project-wide prefix:

```racket
#lang racket/base

(require koyo/config)

(current-option-name-prefix "APP_NAME_HERE")

(define-option http-port
  #:default (or (getenv "PORT") "8000")
  (string->number http-port))

(define-option log-level
  #:default "info"
  (string->symbol log-level))
```

That produces `APP_NAME_HERE_HTTP_PORT` and `APP_NAME_HERE_LOG_LEVEL` — a twelve-factor pattern that most Racket tutorials skip entirely, and the reason Koyo apps are deployable without editing source.

The database layer is where Koyo earns its keep. Schemas are declared as data, with types, contracts, defaults and hooks:

```racket
#lang racket/base

(require koyo/database
         koyo/random)

(define-schema user
  ([id id/f #:primary-key #:auto-increment]
   [username string/f #:contract non-empty-string? #:wrapper string-downcase]
   [(password-hash "") string/f]
   [(verification-code (generate-random-string)) string/f]
   [(created-at (now/moment)) datetime-tz/f])
  #:pre-persist-hook
  (lambda (u)
    (set-user-updated-at u (now/moment))))
```

The `saas` blueprint goes further: users, roles, sessions, password hashing, mail, JSON components, workspace and invite models — a working multi-tenant skeleton rather than a hello world. It is also the honest reason to choose Koyo: without it you would be writing that schema layer yourself, badly, over a weekend.

## Spin: Why You Should Not Start Here in 2026

Spin's design is genuinely nice. Routes are declared with HTTP verbs, handlers are plain functions, and parameters are pulled from query string, form body or URL in one call:

```racket
#lang racket

(require spin)

(get "/" (lambda () "Hello!"))

(get "/hi/:name"
  (lambda (req)
    (string-append "Hello, " (params req 'name) "!")))

(run)
```

For a micro-framework written in a few hundred lines of Racket, that is a clean API — and it is the reason Spin still appears in old blog posts. But the maintenance facts are brutal: last push **July 2017**, no releases, no security review, and a README that instructs you to use PLaneT (`(require (planet dmac/spin))`), a package distribution system Racket discontinued. Installing it today means pinning a Git URL and hoping nothing in the `web-server` API it wraps has changed in nine years. It has.

If you like Spin's ergonomics, put `dispatch-rules` in front of your own three-line `params` helper. That is a forty-minute exercise, and it leaves you on a maintained runtime.

## Deployment: What "Shipping a Racket App" Looks Like

Racket's deployment story is better than its reputation. Two options, both boring in the right way.

**Option 1 — run the source under a supervisor.** Build a standalone executable so the server does not need the Racket toolchain at runtime:

```bash
raco exe --orig-exe -o server server.rkt
raco distribute /opt/myapp server
```

Then supervise it with systemd, binding to loopback and letting a reverse proxy terminate TLS:

```ini
[Unit]
Description=Racket web app
After=network.target

[Service]
WorkingDirectory=/opt/myapp/bin
ExecStart=/opt/myapp/bin/server
Environment=APP_NAME_HERE_HTTP_PORT=8000
Environment=APP_NAME_HERE_LOG_LEVEL=info
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

**Option 2 — `serve/servlet` with `#:command-line? #t`.** The built-in server already parses `--port` and friends when that flag is set, which makes the same binary usable in development and production without a second entry point.

Either way: `serve/servlet` listens on `127.0.0.1` by default. Put Nginx or Caddy in front, forward `X-Forwarded-*` headers, and you are done — no application server, no WSGI, no process manager beyond systemd.

## Common Traps

- **Leaving continuation capture on for an API.** Always set `#:stateless? #t` (or Koyo's `wrap-protect-continuations` equivalent) unless you genuinely need resumable handlers. Memory growth under load is the symptom; the flag is the fix.
- **Forgetting `#:servlet-path`.** The default is `/servlets/standalone.rkt`, not `/`. Your routes are fine, your URLs are not.
- **Installing Koyo at user scope on a server.** `raco pkg install` defaults to user scope; a service running as another user will not see the package. Use `--scope installation` or bundle with `raco distribute`.
- **X-expression escaping.** `response/xexpr` escapes text automatically; if you build HTML with `string-append` you own escaping, including the XSS bugs.
- **Racket CS vs BC startup.** Expecting to launch a process per request is a mistake in any Scheme; keep a long-lived server and let systemd restart it on failure.
- **Assuming Spin still installs.** Its README's PLaneT instruction fails on modern Racket. Use the Git URL only if you must, and budget a rewrite.
- **No official container image for your app.** There is a Racket base image, but build the distribution with `raco distribute` and copy the result into a slim runtime image rather than shipping the whole toolchain.

## FAQ

**Is Racket's built-in web server production-ready in 2026?**
Yes. It ships in the default distribution, is actively maintained (commits in November 2026), supports stateless servlets, session managers, dispatcher-based routing and static files, and it is the runtime Koyo itself builds on.

**Do I need Koyo to build a real application with Racket?**
No — but you will end up writing Koyo's missing pieces yourself. Database schemas, migrations, password hashing, session middleware and a project layout are exactly what the built-in server leaves out.

**Is Spin abandoned?**
Effectively yes. Its last commit is from July 2017, and its README still references PLaneT, which Racket retired. It is a fine reference for a minimal routing DSL, not a dependency for new work.

**How do I deploy a Racket web app without installing Racket on the server?**
Use `raco exe --orig-exe` to produce an executable, then `raco distribute` to collect it with its dependencies into a directory you copy to the server. Supervise it with systemd behind a reverse proxy.

**Does Koyo work with the `minimal` blueprint only?**
No. `raco koyo new` generates the full scaffold by default; `raco koyo new -b minimal example` generates a smaller one. The `saas` blueprint adds users, roles, mail and workspace models on top.

**Can I mix Koyo components with plain `web-server` code?**
Yes — that is the design. Koyo's pieces (config, database, templates, middleware wrappers) are decoupled, so you can adopt the database layer and keep your own routing.

For how other small-language ecosystems solve the same problem, our [Nim web frameworks comparison](../2026-07-25-nim-web-frameworks-jester-prologue-httpbeast-mofuw/) covers Jester and Prologue, the [OCaml web frameworks guide](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/) covers Dream and Opium, and the [Smalltalk web stacks review](../2026-09-15-smalltalk-web-stacks-pharo-seaside-squeak-gnu-smalltalk/) looks at Seaside's continuation-based model — the same idea Racket's server ships by default.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Racket Web Frameworks in 2026: Built-in web-server vs Koyo vs Spin",
  "description": "Racket's built-in web-server, Koyo and Spin compared: real routing code, continuation vs stateless servlets, database tooling, deployment and a decision matrix.",
  "datePublished": "2026-11-04",
  "dateModified": "2026-11-04",
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
