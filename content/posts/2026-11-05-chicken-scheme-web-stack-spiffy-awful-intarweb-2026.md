---
title: "CHICKEN Scheme Web Stack in 2026: Spiffy vs Awful vs intarweb"
date: "2026-11-05"
tags: ["scheme", "chicken-scheme", "web-frameworks", "self-hosted", "lisp"]
draft: false
cover: "/img/screenshots/chicken-scheme-logo.jpg"
description: "A practical 2026 guide to building web services in CHICKEN Scheme: Spiffy for serving, Awful for full applications, intarweb for protocol-level control, with real configuration examples."
---

Every few years someone announces that Lisp is back, writes a blog post about macros, and disappears. Meanwhile CHICKEN Scheme has been quietly compiling Scheme to C since 2000 — producing small static binaries, with a web stack that has served production traffic for over fifteen years and an egg (package) ecosystem that still ships releases in 2026. Awful, its application framework, published **version 1.0.5 on 2026-10-05**. The compiler line is at **CHICKEN 5.4.0**.

So the interesting question is not "is Scheme web development viable" — it is "which of CHICKEN's three layers do I actually need?" Because the stack is unusual: **Spiffy** is a real HTTP server with a handler framework, **Awful** is a full application framework built on top of Spiffy, and **intarweb** is the protocol library both of them use. Choosing wrong means either writing session handling by hand or dragging a framework into a static file server.

I installed all three, built the same small service in each style, and documented what the docs do not tell you.

## TL;DR: The 30-Second Verdict

- **Spiffy** — pick it when you need a hardened HTTP server with virtual hosts, static files, logging and privilege dropping, plus a handful of dynamic endpoints. It is a server with hooks, not an application framework.
- **Awful** — pick it when you are building an actual application: pages, sessions, login, AJAX endpoints, HTML generation. Awful gives you `define-page`, SXML templating and session parameters out of the box.
- **intarweb** — pick it when you are writing a proxy, a protocol test harness, an HTTP client, or middleware that needs to inspect and rewrite requests and responses. It is the layer beneath the other two, not a competitor.

If you just want to serve a directory of files: `csi -e "(import spiffy) (start-server)"`. That is the entire program.

## What Each Layer Actually Is

**Spiffy** is the server. It listens on a TCP port (8080 by default), accepts connections, spawns a thread per connection, parses requests with intarweb, and dispatches them to handlers. Its configuration surface is a set of SRFI-39 parameters you set before `start-server`: `server-port`, `root-path` (default `./web`), `vhost-map`, `access-log`, `error-log`, `spiffy-user`, `spiffy-group`. It can bind port 80 or 443 as root and then drop privileges — that is a production feature most hobby servers never implement.

**Awful** is the application framework. It sits on Spiffy and adds the things a web app needs: a page registry (`define-page` / `undefine-page`), session parameters and authentication helpers, AJAX support (`ajax`, `periodical-ajax`, `ajax-link`), an `app-root-path`, and SXML-based HTML generation (`enable-sxml`). It is closer in spirit to a small Rails than to a router.

**intarweb** is the protocol implementation: `make-request`, `read-request`, `write-request`, `make-response`, header objects, `http-status-codes`. Spiffy uses it internally. You will touch it directly only when you need to speak HTTP at a level below routing — reverse proxies, clients, or custom accept loops.

## Comparison Table (2026)

| Dimension | Spiffy | Awful | intarweb |
|---|---|---|---|
| Layer | HTTP server + handler dispatch | Application framework on Spiffy | HTTP protocol library |
| Primary use | Static files, vhosts, thin endpoints | Pages, sessions, forms, AJAX | Proxies, clients, middleware |
| Templating | None (you write handlers) | SXML or `$` string substitution | None |
| Sessions | Not provided | Built in (`enable-sessions`, `session-set!`) |
| AJAX helpers | No | Yes (`enable-ajax`, `ajax-link`) |
| TLS | openssl egg + `ssl-listen` + `accept-loop` | Inherits Spiffy | Not applicable |
| Concurrency | Thread per connection | Thread per connection, shared session store | Caller's choice |
| Install | `chicken-install spiffy` | `chicken-install awful` | `chicken-install intarweb` |
| Latest activity | Ships with the CHICKEN 5.x egg set | 1.0.5 (2026-10-05) | Maintained alongside Spiffy |
| GitHub stars | Not hosted on GitHub | Not hosted on GitHub | Not hosted on GitHub |

That last row is deliberate. CHICKEN eggs live in the project's own repositories at `code.call-cc.org`, not on GitHub, so star counts do not exist and popularity badges are meaningless here. Judge the stack on release cadence and documentation quality instead — both are visible and current.

## Decision Matrix

| Your situation | Use | Why |
|---|---|---|
| Serve a static site with two or three dynamic routes | Spiffy | No framework overhead, privilege dropping built in |
| Multi-tenant hosting with different docroots | Spiffy + `vhost-map` | Virtual hosts are a first-class parameter |
| Login, sessions, forms, admin pages | Awful | Sessions and page registry come free |
| JSON endpoints behind an existing auth layer | Awful (page with a JSON content type) | Faster than hand-rolling routing |
| Reverse proxy or HTTP fuzzing harness | intarweb | Full control of request and response objects |
| You need Websockets | Neither, add a separate layer | Not part of this stack |
| You want a single self-contained binary | Any of them, compiled with `csc -static` | CHICKEN compiles to C |

## Spiffy: A Server You Can Reason About

Install the egg, then configure parameters before starting. This is the pattern the documentation recommends, and it is refreshingly explicit — no magic config file, no environment-variable guessing:

```scheme
(import spiffy)

(server-port 8080)
(root-path "/srv/www")
(access-log "/var/log/spiffy/access.log")
(error-log "/var/log/spiffy/error.log")
(spiffy-user "www-data")
(spiffy-group "www-data")

(start-server)
```

Two details matter in production. First, `spiffy-user` and `spiffy-group` only take effect when the process starts as root, and group switching needs the `posix-groups` egg installed. Second, `access-log` defaults to `#f` — if you never set it, you get no access logs and will discover this during your first incident.

Virtual hosts are an alist of host regex to handler. Each handler receives a `continue` procedure, so you can parameterize the environment and then hand control back to the normal file-serving path:

```scheme
(import spiffy)

(vhost-map
 `(("app\\.example\\.org"
    . ,(lambda (continue)
         (parameterize ((root-path "/srv/app/public"))
           (continue))))
   ("example\\.org"
    . ,(lambda (continue)
         (parameterize ((root-path "/srv/site/public"))
           (continue))))))

(start-server)
```

For TLS you do not pass a certificate path to `start-server`. You build the listener yourself and hand it to `accept-loop`, which is documented and gives you a place to drop privileges after binding:

```scheme
(import spiffy openssl)

(server-port 443)
(define listener (ssl-listen (server-port) cert: "/etc/ssl/app.pem" key: "/etc/ssl/app.key"))
(spiffy-user "www-data")
(accept-loop listener tcp-accept)
```

The cost of this minimalism: Spiffy gives you no routing DSL, no templating and no sessions. A handler is a procedure that writes to the response port. That is either exactly what you want or a sign you should be using Awful.

## Awful: The Application Layer

Awful is where CHICKEN web development becomes productive. Pages are registered globally with `define-page`, and with `enable-sxml` you return SXML lists that Awful renders:

```scheme
(import awful)

(enable-sxml)

(define-page "/"
  (lambda ()
    `(html
       (head (title "Deploy status"))
       (body
         (h1 "All systems nominal")
         (p "Last deploy: " ,(deploy-timestamp))))))

(define-page "/healthz"
  (lambda () "ok"))

(awful-start)
```

Sessions are parameters, not middleware. You enable them once, then read and write session keys inside handlers — which keeps authentication logic close to the page that needs it:

```scheme
(import awful)

(enable-sessions)

(define-page "/login"
  (lambda ()
    (if (equal? ($ 'token) "expected-token")
        (begin (session-set! 'user "ada")
               (redirect-to "/dashboard"))
        `(html (body (form (@ (method "post"))
                           (input (@ (type "password") (name "token")))
                           (button "Sign in")))))))

(define-page "/dashboard"
  (lambda ()
    (if (session-ref 'user)
        `(html (body (h1 "Welcome back")))
        (redirect-to "/login"))))
```

AJAX is a first-class citizen: `enable-ajax`, `ajax-link` and `periodical-ajax` exist because Awful predates the era of bolting a JSON API onto a server-rendered app. For a dashboard polling a status endpoint, that is a two-line win:

```scheme
(import awful)

(enable-ajax)

(define-page "/stats"
  (lambda () (number->string (queue-depth))))

(define-page "/"
  (lambda ()
    `(html (body (div (@ (id "stats")))
                 ,(periodical-ajax "/stats" "stats" 5000)))))
```

The honest limitations: Awful stores sessions in memory by default, so a restart logs everyone out and multiple app servers need a shared store. Its templating is SXML, which is pleasant once your editor indents it correctly and painful if you expect HTML files on disk. And there is no hot reload — Scheme images are not PHP.

## intarweb: Speaking HTTP Directly

intarweb is what you reach for when routing is the wrong abstraction. Building a request by hand makes header manipulation and status inspection explicit:

```scheme
(import intarweb uri-common)

(define req
  (make-request uri: (uri-reference "http://127.0.0.1:8080/healthz")
                method: 'GET))

(define resp (make-response code: 200 reason: "OK"))
(response-class resp)   ; => 200
```

The same objects are what Spiffy hands to its parser, which is why writing a reverse proxy in CHICKEN is a matter of reading a request, mutating its URI, forwarding it, and copying the response back — no framework required. If you have ever fought an opinionated proxy config, the appeal is obvious: the protocol is data, and you can transform it.

## Deployment and Operational Pitfalls

**Compile to a binary.** CHICKEN's compiler emits C, and `csc -O3 -static app.scm -o app` produces a self-contained executable. On a minimal container image this eliminates the runtime install step entirely — the same property that makes Go deployments pleasant.

**Pin your eggs.** `chicken-install` without arguments resolves latest versions. For reproducible builds, record versions in a manifest (the `chicken-install -version` output alongside the egg list) and rebuild from it. Egg updates have broken APIs before; Awful's own version history shows a 2023-to-2025 gap, which is exactly the kind of window where an unpinned dependency drifts.

**Thread-per-connection has a ceiling.** Spiffy fires off a thread per connection, which is fine for hundreds of concurrent clients and wrong for tens of thousands. Put it behind a reverse proxy with keepalive, or accept the limit knowingly.

**Sessions are memory, and memory is finite.** Awful's default session store grows with active users. A long-running service with many anonymous visitors will accumulate entries; set expiry deliberately rather than discovering the leak via OOM.

**Privilege dropping is not automatic.** Binding 80/443 as root without setting `spiffy-user` means you keep running as root. The parameters exist; use them.

If you are comparing across Lisp dialects, our [Common Lisp web stack comparison](../2026-09-11-common-lisp-web-stack-hunchentoot-caveman-clack/) covers Hunchentoot, Caveman and Clack, the [Tcl web stacks guide](../2026-09-16-tcl-web-stacks-naviserver-apache-rivet-openacs-comparison/) handles NaviServer and OpenACS, and the [Scheme implementations comparison](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/) explains how CHICKEN differs from Racket, Chez and Guile before you commit to a dialect.

## FAQ

**Is CHICKEN Scheme fast enough for production web services?**
It compiles to C, so request handling and string processing run at native speed. The realistic bottlenecks are thread-per-connection concurrency and whatever database driver you choose, not the language. For server-rendered pages and small JSON endpoints it is comfortably fast; for connection-heavy workloads put a reverse proxy in front.

**What is the difference between Spiffy and Awful?**
Spiffy is the HTTP server plus a handler dispatch mechanism, with virtual hosts, logging and privilege dropping. Awful is an application framework layered on Spiffy that adds page registration, sessions, authentication helpers, AJAX utilities and SXML templating. Use Spiffy alone for file serving and thin endpoints; add Awful when you need application structure.

**Do I need to know Scheme macros to be productive with Awful?**
No. `define-page`, `enable-sxml`, `session-set!` and `periodical-ajax` are ordinary procedures and macros used as documented. Macros become relevant when you want custom page definers, which the documentation explicitly covers as an advanced step.

**Why are there no GitHub star counts for these projects?**
Because the eggs are not hosted on GitHub. CHICKEN's ecosystem lives in the project's own repositories at code.call-cc.org, with the egg index at eggs.call-cc.org. Popularity metrics from GitHub simply do not apply, so release dates and documentation are the honest signals — Awful 1.0.5 shipped on 2026-10-05.

**How do I deploy a CHICKEN web app in a container?**
Compile statically with `csc -O3 -static` and copy the resulting binary into a minimal image. That avoids shipping the compiler and the egg tree, keeps the image small, and makes rollbacks a matter of swapping a single file. Mount your static root and log directory, and run as a non-root user with `spiffy-user` set if you bind privileged ports.

**Can I use Spiffy or Awful with nginx or Caddy in front?**
Yes, and it is the recommended topology for anything with real traffic: the proxy terminates TLS, serves static assets from disk, and forwards application routes to Spiffy on a loopback port. That also sidesteps thread-per-connection scaling limits.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CHICKEN Scheme Web Stack in 2026: Spiffy vs Awful vs intarweb",
  "description": "Practical guide to CHICKEN Scheme web development: Spiffy server configuration, Awful application framework, intarweb protocol control, and production pitfalls.",
  "datePublished": "2026-11-05",
  "dateModified": "2026-11-05",
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
