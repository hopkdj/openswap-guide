---
title: "Hunchentoot vs Caveman2 vs Clack in 2026: Which Common Lisp Web Stack Should You Actually Use?"
date: "2026-09-11"
tags: ["common-lisp", "web-frameworks", "self-hosted", "developer-tools", "lisp"]
draft: false
---

Common Lisp is the oldest language in this series and, by a strange coincidence, the one whose web stack is structured more sensibly than most modern alternatives. Ruby has Rack. Python has WSGI and ASGI. Node.js has a pile of competing abstractions. Common Lisp has had **one** standard answer for over a decade, and the three projects people argue about are not really competitors at all — they are three layers of the same stack.

That confusion is why so many developers bounce off Lisp web development. They read a comparison, conclude they must choose between Hunchentoot, Caveman2, and Clack, pick one, and then discover halfway through that the thing they picked was never supposed to do what they assumed.

## The Crucial Framing: Server vs Framework vs Abstraction Layer

Before comparing anything, settle the layering — because getting this wrong is the actual failure mode.

| Layer | Project | What it is | Analogy |
|---|---|---|---|
| **Abstraction layer** | **Clack** | A web application environment that standardizes how an app is invoked | Rack (Ruby), WSGI (Python) |
| **Server** | **Hunchentoot**, Woo, Wookie, Toot | Listens on a socket, speaks HTTP, hands requests to the abstraction layer | Puma, gunicorn, Unicorn |
| **Framework** | **Caveman2** | Routing, project skeletons, database integration, templating — built *on* Clack | Sinatra / Rails |

Clack's own README states the analogy outright: it is "a web application environment for Common Lisp inspired by Python's WSGI and Ruby's Rack." Caveman2's README confirms the dependency direction in the other direction: "As Caveman is based on Clack/Lack, you can choose which server to run on — Hunchentoot, Woo or Wookie, etc."

**So the real question is never "Caveman2 or Clack."** You always use Clack. The question is whether you want Caveman2's opinionated framework on top, and which server you deploy behind it.

## TL;DR: The Quick Verdict

- **Start with Hunchentoot** if your app is small, or if you are learning. It is a complete web server plus a toolkit for dynamic sites, and it is the reference implementation everyone tests against. Its own author's ecosystem recommends it for local development.
- **Add Caveman2** the moment you need routing, a project skeleton, and database connections that do not have to be hand-wired. It is the only one of the three that is a framework in the "here is a project layout" sense.
- **Always understand Clack**, because it is the contract everything else implements. Even if you never call `clackup` directly, your Caveman2 app is a Clack application, and that is what makes server swapping a one-line change.

Live project health, September 2026:

| Project | GitHub stars | Last push | Role |
|---|---|---|---|
| [Hunchentoot](https://github.com/edicl/hunchentoot) | **752** | 2026-05-04 | Web server + toolkit |
| [Woo](https://github.com/fukamachi/woo) | **1,397** | 2026-03-21 | Fast non-blocking server on libev |
| [Clack](https://github.com/fukamachi/clack) | **1,108** | 2026-02-10 | Web application environment |
| [Caveman2](https://github.com/fukamachi/caveman) | **825** | 2024-05-26 | Web application framework |
| [Lack](https://github.com/fukamachi/lack) | **178** | 2026-04-06 | Core of Clack (middleware) |

Two observations that matter more than the numbers. **Hunchentoot, Woo, Clack, and Lack all received commits within the last eight months** — this is maintained infrastructure, not archaeology. And **Caveman2's last push is 2024**, which is worth reading correctly: it is a stable framework whose README documents `caveman2` as "now available on Quicklisp," so the practical install path is unchanged. A quiet repository for a mature framework is not the same signal as an abandoned one, but you should know which you are looking at.

## Head-to-Head Comparison

| Dimension | Hunchentoot | Caveman2 | Clack |
|---|---|---|---|
| **Kind of project** | Server | Framework | Abstraction layer |
| **HTTP/1.1 chunking** | Yes (both directions) | Inherited from server | Delegated to server |
| **Keep-alive** | Yes | Inherited | Delegated |
| **SSL** | Yes | Inherited | Delegated |
| **Session handling** | Yes, built in (with and without cookies) | Via framework layer | Not applicable |
| **Routing DSL** | None (you dispatch yourself) | `@route` and `defroute` | None |
| **HTML generation** | **Deliberately not included** | Templates (`render`, Djula) | Not applicable |
| **Database integration** | No | Yes, via CL-DBI | No |
| **Project scaffolding** | No | `caveman2:make-project` | No |
| **Multi-threading** | Yes (multiprocessing) | Inherited | Inherited |
| **License** | BSD-style | MIT | MIT |
| **Production server recommended** | Local development | Swappable (Woo) | Swappable |

The most surprising row for newcomers is **HTML generation**. Hunchentoot explicitly does not generate HTML and says so in its own README: it "does *not* include functionality to programmatically generate HTML output." That is a feature, not a gap — it means the server has no opinion about your templating. If you are coming from frameworks where the server and the template engine are the same product, this separation is the part that takes getting used to.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Pick | Why |
|---|---|---|
| Writing your first Lisp web app | **Hunchentoot** | Smallest concept count; sessions and SSL included |
| Need routing, templates, and a DB | **Caveman2** | Only option with scaffolding and CL-DBI integration |
| Building middleware or a reusable abstraction | **Clack** (+ Lack) | The middleware interface is the entire point |
| Serving high concurrency in production | **Clack + Woo** | Woo is a non-blocking server on libev, designed for load |
| Want to serve static files only | **Clack + any server** | Minimal code; no framework needed |
| Swapping servers later without a rewrite | **Any, via Clack** | The abstraction layer makes this a config change |
| Deploying a self-contained binary | **Any + buildapp** | Bundles the app into a standalone SBCL executable |
| Learning how Lisp web apps actually work | **Clack first** | Everything else is a layer on top of this contract |

## Clack — The Foundation You Always End Up Using

Clack's entire value proposition fits in its README's usage example. A complete web server, in eight lines:

```common-lisp
(defvar *handler*
    (clack:clackup
      (lambda (env)
        (declare (ignore env))
        '(200 (:content-type "text/plain") ("Hello, Clack!")))))
```

The application is a **function that takes an environment association list and returns a three-element list**: status, headers, body. That is the whole contract. It is unglamorous, and it is the reason Lisp's web ecosystem has been server-agnostic for fifteen years while other ecosystems still argue about it.

Stopping the server is equally explicit:

```common-lisp
(clack:stop *handler*)
```

Installation is one Quicklisp call:

```common-lisp
(ql:quickload :clack)
```

The production story is where Clack earns its keep. It ships a `clackup` command-line script for starting applications, and the README documents the exact sequence:

```sh
$ ros install clack
$ which clackup
/Users/nitro_idiot/.roswell/bin/clackup

$ cat <<EOF >> app.lisp
(lambda (env)
  (declare (ignore env))
  '(200 (:content-type "text/plain") ("Hello, Clack!")))
EOF
$ clackup app.lisp
Hunchentoot server is started.
Listening on localhost:5000.
```

Note what happened there: an app file containing a bare lambda was started, and **Hunchentoot was the default server**. That is the abstraction layer working as designed. The server list Clack documents includes Hunchentoot, Wookie, Toot, and Woo — you change servers by changing a flag, not by rewriting your application.

`clackup` depends on **Roswell**, the Lisp implementation manager and launcher. The Roswell README covers the installable implementations directly:

```sh
$ ros install sbcl-bin      # default sbcl
$ ros install sbcl          # The newest released version of sbcl
$ ros install ccl-bin       # default prebuilt binary of ccl
$ ros list installed sbcl   # Listing the installed implementations
```

If you are setting up a Lisp environment for the first time, this is the order that works: Roswell first, then an implementation, then `ros install clack`, then your framework.

## Hunchentoot — The Workhorse Server

Hunchentoot is "a web server written in Common Lisp and at the same time a toolkit for building dynamic websites." That dual description is accurate and explains why it is the right first stop: it works as a plain server, and it also gives you the conveniences you would otherwise miss from a framework.

Start it with an easy acceptor — the standard idiom for a development server:

```common-lisp
(ql:quickload :hunchentoot)

(defvar *acceptor*
  (make-instance 'hunchentoot:easy-acceptor :port 4242))

(hunchentoot:start *acceptor*)
```

From the README, the feature list is longer than you would expect from a 752-star project: **HTTP/1.1 chunking in both directions, persistent connections (keep-alive), and SSL**. On top of the protocol layer it provides automatic session handling with and without cookies, logging, customizable error handling, and easy access to GET and POST parameters.

The architectural constraint is deliberate and total: Hunchentoot communicates "with its front-end or with the client over TCP/IP sockets and optionally uses multiprocessing to handle several requests at the same time," which is why it cannot be implemented in portable Common Lisp and depends on **usocket** and **Bordeaux Threads** compatibility layers. In practice this means Hunchentoot runs on SBCL, CCL, LispWorks, and any other implementation with those layers working — which is all of the ones you would consider.

For HTML, you bring your own. Hunchentoot's README names two of the ecosystem's long-standing options, **CL-WHO** and **HTML-TEMPLATE**, and adds "you can use any library you like." Full documentation lives in the project's `docs` directory and at `edicl.github.io/hunchentoot/`.

**The honest trade-off:** you will write your own dispatch. Hunchentoot gives you request objects and parameters; mapping URLs to handlers is your job unless you adopt a framework. That is fine for an API endpoint or a small internal tool and increasingly annoying as route count grows — which is exactly the pressure that makes people adopt Caveman2.

## Caveman2 — The Opinionated Framework

Caveman2 is where Common Lisp web development starts to feel like a modern framework. It is a rewrite of the original Caveman (the README says "Caveman2 was written from scratch"), and it is built on **ningle**, giving it Sinatra-style routing.

The framework's purpose is stated as a design goal: "Caveman is intended to be a collection of common parts of web applications," governed by three rules — be extensible, be practical, don't force anything. What that buys you concretely is database integration with connection management via **CL-DBI** and a separate configuration system via **Envy**. The README is explicit that the original Caveman lacked database support and that Caveman2 exists partly to fix that.

Routing has two syntaxes, and you can use either. The annotation style:

```common-lisp
@route GET "/"
(defun index ()
  (render #P"index.tmpl"))

@route GET "/hello"
(defun say-hello (&key (|name| "Guest"))
  (format nil "Hello, ~A" |name|))
```

And the macro style with identical semantics:

```common-lisp
(defroute index "/" ()
  ...)

(defroute "/welcome" (&key (|name| "Guest"))
  (format nil "Welcome, ~A" |name|))
```

Route parameters are Sinatra-like and pleasant to write:

```common-lisp
(defroute "/hello/:name" (&key name)
  (format nil "Hello, ~A" name))
```

Wildcards come through `splat`, regular expressions are available with `:regexp t`, and — a detail I appreciate — **you can fall through to the next matching route** with `next-route`, which makes dispatch-order workarounds unnecessary:

```common-lisp
(defroute "/guess/:who" (&key who)
  (if (string= who "Eitaro")
      "You got me!"
      (next-route)))

(defroute "/guess/*" ()
  "You missed!")
```

Handlers may return a string, a pathname, or a Clack response list, so you can drop to the raw abstraction layer at any point without leaving the framework. `redirect` handles redirection, and `url-for` gives you reverse URL lookup by route name — the small convenience that stops you hardcoding paths.

Project creation is a single call that writes a full skeleton: `app.lisp`, `db/schema.sql`, `src/config.lisp`, `src/db.lisp`, `src/view.lisp`, `templates/`, tests, and a system definition file:

```common-lisp
(ql:quickload :caveman2)

(caveman2:make-project #P"/path/to/myapp/"
                       :author "<Your full name>")
```

You get generated `start` and `stop` functions, which makes the running of the app feel like Go or Node rather than like Lisp:

```common-lisp
(ql:quickload :myapp)
(myapp:start :port 8080)
```

The most valuable sentence in Caveman2's README for production planning is a direct recommendation from its author: **"I recommend you use Hunchentoot on a local machine, and use Woo in a production environment."** Because Caveman2 is a Clack application, honoring that advice is a one-argument change:

```common-lisp
(myapp:start :server :hunchentoot :port 8080)
(myapp:start :server :fcgi :port 8080)
```

Deployment through the CLI follows the same pattern, and the README's example uses an environment variable to select configuration:

```sh
$ APP_ENV=development clackup --server :fcgi --port 8080 app.lisp
```

**The honest trade-off:** 2024 was the last commit, so you are adopting a stable-but-quiet dependency. For a framework whose job is routing and scaffolding, that is a reasonable bet — the framework is small, Clack underneath it is actively maintained, and a framework that has stopped changing is not necessarily a framework that has stopped working. But if you require an actively-developed framework with frequent releases, Caveman2 is not that in 2026.

## Deploying a Lisp Web Application

Lisp deployment has a reputation for being exotic. It is not — the container story is ordinary, and the standalone-binary story is better than most languages'.

The Docker Hub image **`clfoundation/sbcl`** (described simply as "Steel Bank Common Lisp") is the clean base. A realistic image that installs Roswell, installs Quicklisp dependencies, and serves through `clackup`:

```dockerfile
FROM clfoundation/sbcl:latest

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates make build-essential libev-dev \
    && rm -rf /var/lib/apt/lists/*

# Roswell: the Lisp implementation manager and script launcher
RUN curl -L https://raw.githubusercontent.com/roswell/roswell/release/scripts/install-for-ci.sh | sh

ENV PATH="/root/.roswell/bin:${PATH}"

WORKDIR /app
COPY . .

# Pull dependencies and start the app behind the Clack abstraction layer
RUN ros install clack && ros run -- --version
EXPOSE 5000
CMD ["clackup", "--server", ":woo", "--port", "5000", "app.lisp"]
```

Two notes on that file. `libev-dev` is there because **Woo is a non-blocking server built on libev** — if you plan to use Woo in production, that is a required build dependency, not an optional one. And the `CMD` deliberately uses `clackup` rather than `sbcl --script`, because the abstraction layer means you can swap `:woo` for `:hunchentoot` in production debugging without touching the application.

Behind a reverse proxy, the Lisp app is just another upstream:

```nginx
upstream lisp_app {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    server_name app.example.com;

    location / {
        proxy_pass http://lisp_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
    }
}
```

For a single-file deployable artifact, **buildapp** (129 stars, "makes it easy to build application executables with SBCL") bundles your system and its dependencies into a standalone executable — no Quicklisp at runtime, no source tree on the server. It has not been pushed since January 2024, which reflects its nature: it does one small thing that SBCL's save-lisp-and-die already supports.

## Pitfalls and Migration Notes

**Hunchentoot**

- Set `easy-acceptor` for development only. In production you want explicit `acceptor` configuration so you control read timeouts, backlog, and address binding.
- Session state lives in memory by default. If you run multiple processes, sessions do not follow the request unless you configure shared storage — this is the classic "works fine with one worker" bug.
- You own routing. Budget real time for dispatch once your URL count passes a couple of dozen; that is the signal to adopt Caveman2.

**Clack**

- The environment is an association list. Destructuring it wrong produces confusing runtime failures rather than compile-time errors; validate with `getf` lookups before you assume a key exists.
- Clack does not include HTML generation or routing — resist the urge to build a mini-framework on top before you have tried Caveman2, which already did that work.
- `clackup` requires Roswell. If you are not using Roswell, use `clack:clackup` from your own build script instead of expecting the CLI to be present.

**Caveman2**

- The 2024 last-commit date is a real planning input. Pin your dependency versions and test upgrades in a branch rather than tracking master.
- The generated skeleton is opinionated about configuration via Envy. Read `src/config.lisp` before adding environment variables, or you will end up with two competing config mechanisms.
- Templates are handled by the framework's rendering layer; if you want to use a different engine, do it explicitly rather than assuming the default will swap itself.

**All three**

- **Compilation is a deployment step in Lisp.** Loading a large system on startup can take seconds; use `buildapp` to pre-compile, or warm your image and snapshot it, rather than paying compile cost on every container start.
- **Keep the server behind a proxy.** Every server here benefits from nginx or Caddy in front for TLS termination, static files, and connection buffering.
- **Pin your implementation version.** SBCL behavior changes between releases, and "works on SBCL latest" is not a support policy.

## FAQ

**Do I need to choose between Hunchentoot and Clack?**

No, and framing the question that way causes most of the confusion around Lisp web development. Clack is an abstraction layer that standardizes how an application is invoked; Hunchentoot is an HTTP server. Clack starts Hunchentoot by default, so using Clack means you are already using a server. The genuine choice is whether to add a framework like Caveman2 on top of Clack.

**Which Common Lisp web server should I use in production?**

Woo, for most production deployments, and this recommendation comes directly from the Caveman2 author's README: use Hunchentoot on a local machine and Woo in production. Woo is a non-blocking server built on libev, so it handles many concurrent idle connections efficiently. Hunchentoot's multiprocessing model is perfectly capable but consumes a thread per in-flight request, which matters at high concurrency and does not at all at low traffic.

**Is Common Lisp a reasonable choice for a new web application in 2026?**

Yes, if you value stability and long-horizon maintainability over ecosystem size and hiring pool. The stack described here has been API-stable for years, Quicklisp dependency management works well, and the ability to compile a standalone executable with buildapp gives you a deployment artifact most dynamic languages cannot match. What you give up is library breadth: for any given third-party SaaS integration, assume you are writing the client yourself.

**How do sessions work if I run multiple processes?**

Not automatically. Hunchentoot provides session handling with and without cookies, but the default store is in-process memory. With more than one worker in a load-balanced setup, a request has no guarantee of landing on the worker that holds the session. You need shared session storage or sticky routing, and you should decide which before you scale past one process — retrofitting this after launch is painful.

**Can I use Clack without a framework and still have a maintainable app?**

Yes, up to a point that is larger than you would expect. A Clack application is just a function returning a three-element list, and the middleware layer (Lack) lets you compose request handling cleanly. What you lose without a framework is routing, configuration management, and database connection handling — all three of which you would end up rebuilding, badly at first. If you are writing more than a handful of endpoints, Caveman2 saves you that work.

**Why does Hunchentoot not generate HTML?**

By design. Hunchentoot's README states plainly that it does not include functionality to programmatically generate HTML output and points at separate libraries for the job. Keeping the server free of templating means you can use any engine — or none — without the server having an opinion, and it is a large part of why the server has remained useful for so long across changing template-engine fashions.

**What is Lack, and do I need to care about it?**

Lack is the core of Clack and provides the middleware interface. You do not need to think about it for a normal application, but it is what you reach for when you want to add cross-cutting behavior — request logging, authentication, response header manipulation — in a composable way. It is the piece that makes Clack feel like Rack rather than merely resembling it.

## Related Reading

This article is part of a series on web stacks across smaller language ecosystems. For the Erlang/OTP equivalent, see our [Erlang HTTP servers comparison: Cowboy vs Mochiweb vs Yaws](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/), which solves the same server-versus-framework layering problem with a different concurrency model. The functional-language counterpart is our [OCaml web frameworks comparison: Dream vs Opium vs Ocsigen](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/). For a language that got its web story right much later, see [Crystal web frameworks: Kemal vs Lucky vs Amber](../2026-08-31-crystal-web-frameworks-kemal-lucky-amber-comparison/) — and for the mainstream contrast, our [Java web frameworks comparison: Spring Boot vs Quarkus vs Micronaut vs Helidon vs Javalin](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Hunchentoot vs Caveman2 vs Clack in 2026: Which Common Lisp Web Stack Should You Actually Use?",
  "description": "A practical 2026 guide to the Common Lisp web stack: how Clack, Hunchentoot and Caveman2 layer together, real code and Docker deployment configs, production server advice and migration pitfalls.",
  "datePublished": "2026-09-11",
  "dateModified": "2026-09-11",
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
