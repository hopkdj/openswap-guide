---
title: "D Web Frameworks in 2026: vibe.d vs Hunt vs Diamond — Which One Should You Actually Ship?"
date: "2026-09-15"
tags: ["d-language", "web-frameworks", "self-hosted", "programming-languages", "comparison"]
draft: false
cover: "/img/screenshots/vibed-title.png"
---

D is the language people rediscover every five years: native compilation, C ABI interop, compile-time function evaluation, and a garbage collector you can switch off when you need to. What nobody tells you is that the D web ecosystem is **three frameworks wide** — vibe.d, Hunt, and Diamond — and two of them stopped moving years ago. If you are picking a D stack in 2026, you are not choosing between equals. You are choosing between one actively maintained toolkit and two cautionary tales.

Here is the honest state of the D web ecosystem, with live repository data, real install commands, and a deployment path that actually survives production.

## TL;DR — Quick Verdict

**Use vibe.d.** It is the only D web framework with releases inside the last 12 months (**v0.10.3**, plus commits through **July 2026**), a modular architecture (vibe-core, vibe-http, vibe-stream), and a documented fiber-based async model. **Use Hunt only if you are maintaining an existing Hunt codebase** — its last release was 2022 and it pins you to a narrow compiler window. **Do not start anything new on Diamond** — its last commit was March 2020. If you want a compiled, single-binary web service and you like D's syntax, vibe.d is the answer and everything else is archaeology.

## Framework Comparison at a Glance

| Dimension | **vibe.d** | **Hunt** | **Diamond** |
|---|---|---|---|
| GitHub stars | 1,215 | 300 | 176 |
| Last commit | 2026-07-04 | 2024-03-11 | 2020-03-31 |
| Latest release | v0.10.3 (Dec 2025) | v3.3.31-rc.4 (Mar 2022) | none (rolling master) |
| Async model | Fiber-based event loop (eventcore) | Synchronous + thread pool | Delegates to vibe.d |
| Template engine | diet (pug-inspired, compile-time) | Mustache-style views | diet via vibe.d |
| ORM / DB | vibe.db (MySQL, PostgreSQL, MongoDB, Redis) | Hunt entity/ORM layer | ActiveRecord-style wrapper |
| Compiler constraint | 10 latest DMD minor releases | DMD **2.095.0 – 2.098.0 only** | pinned to old vibe.d |
| License | MIT | Apache-2.0 | MIT |
| Single static binary | Yes | Yes | Yes |
| Production verdict | **Recommended** | Maintain-only | Abandoned |

Two numbers in that table decide the whole article. vibe.d is the only project with a release in the current cycle. Hunt's README still advertises DMD **≤ 2.098.0** — a compiler from 2021 — which means every new D compiler release silently invalidates your build until you patch the framework yourself.

## Decision Matrix: Pick Your Stack in 10 Seconds

| Your Use Case | Recommended Tool | Why |
|---|---|---|
| REST or JSON API you self-host behind nginx | **vibe.d** | Mature HTTP layer, WebSocket support, predictable fiber scheduling |
| Full-stack app with file-based routing config | **vibe.d + diet** | Compile-time templates, no runtime template parsing |
| Existing Hunt application | **Hunt (frozen DMD)** | Rewriting is more expensive than pinning the compiler |
| Full-stack MVC with a Ruby-on-Rails-like structure | Hunt | Closest to MVC conventions, but note the compiler window |
| New greenfield project in 2026 | **vibe.d** | Everything else is unmaintained |
| Docker/container deployment | **vibe.d** | Trivial multi-stage build, ~10 MB runtime image |
| Legacy Diamond app | Migrate to vibe.d | Diamond is a thin layer on vibe.d anyway |

## vibe.d — The Only Framework With a Pulse

vibe.d describes itself as "a high-performance asynchronous I/O, concurrency and web application toolkit written in D." That word *toolkit* matters: you get HTTP client and server, WebSockets, TLS, sessions, SMTP, Redis, MongoDB, and the **diet** template engine in one dependency tree. The project is deliberately split into focused repositories — `vibe-http`, `vibe-stream`, `vibe-core`, `vibe-serialization`, `vibe-container` — so you can depend on just the HTTP layer without dragging in the ORM.

![vibe.d official project banner](/img/screenshots/vibed-title.png "vibe.d web application toolkit for the D programming language")

Installation goes through DUB. The official README recommends the template route rather than adding the dependency by hand:

```bash
# Install the D toolchain (Debian/Ubuntu, from the official vibe.d setup notes)
sudo apt-get install g++ gcc-multilib xdg-utils libssl-dev
wget https://downloads.dlang.org/releases/2.x/2.098.0/dmd_2.098.0-0_amd64.deb
sudo dpkg -i dmd_2.098.0-0_amd64.deb

# Create a vibe.d project the supported way
dub init myapi -t vibe.d
cd myapi
dub
```

The smallest working server is four lines of routing, straight from the project README:

```d
#!/usr/bin/env dub
/+ dub.sdl:
   name "hello_vibed"
   dependency "vibe-d" version="~>0.9.0"
+/
import vibe.vibe;

void main()
{
    listenHTTP("127.0.0.1:8080", (req, res) {
        res.writeBody("Hello Vibe.d: " ~ req.path);
    });

    runApplication();
}
```

Save that as `hello.d` and run it with `dub hello.d` — no project scaffolding, no manifest edits. That single-file ergonomics is why vibe.d keeps winning D comparisons: the feedback loop is seconds, not minutes, because the D compiler is fast and DUB caches aggressively in `~/.dub`.

A production Dockerfile using a multi-stage build keeps the image small. Copy the manifest first so DUB's dependency resolution is cached in its own layer:

```dockerfile
# ---- build stage ----
FROM ubuntu:24.04 AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl xz-utils gcc g++ libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://dlang.org/install.sh | bash -s dmd-2.109.1
ENV PATH="/root/dlang/dmd-2.109.1/linux/bin64:${PATH}"
WORKDIR /src
COPY dub.json dub.selections.json ./
RUN dub fetch --all-packages 2>/dev/null || true
RUN dub build --build=release --compiler=dmd --skip-registry=all --dry-run || true
COPY . .
RUN dub build --build=release --compiler=dmd

# ---- runtime stage ----
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /src/myapi /app/myapi
EXPOSE 8080
USER 1000:1000
ENTRYPOINT ["/app/myapi"]
```

The runtime stage contains a static binary, OpenSSL, and nothing else — that is the entire point of choosing D over a runtime-heavy stack.

### Running vibe.d Behind a Reverse Proxy

vibe.d speaks plain HTTP on a local port; terminate TLS at nginx and keep the app unprivileged. This is the same shape you would use for any compiled service:

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

And the systemd unit — note that vibe.d's own Linux setup script creates a dedicated user/group pair for privilege lowering (`./setup-linux.sh`), which is the pattern to copy:

```ini
[Unit]
Description=vibe.d application
After=network-online.target

[Service]
Type=simple
User=vibeapp
Group=vibeapp
WorkingDirectory=/opt/myapi
ExecStart=/opt/myapi/myapi
Restart=always
RestartSec=3
LimitNOFILE=65535
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

## Hunt — Good Ideas, Frozen in 2022

Hunt is the framework that looks most like a "batteries-included" stack: file-based route configuration, controllers with an `@Action` attribute, sessions, validation, an entity/ORM layer, Redis, queues, and scheduling. The routing config is refreshingly declarative — you edit a config file instead of decorating every function:

```conf
#
# [GET,POST,PUT...]    path    controller.action
#
GET     /               index.index
GET     /users          user.list
POST    /user/login     user.login
*       /images         staticDir:public/images
```

Controllers are terse and typed:

```d
module app.controller.index;

import hunt.framework;

class IndexController : Controller
{
    mixin MakeController;

    @Action
    string index()
    {
        return "Hello world!";
    }
}
```

![Hunt framework banner from the official repository](/img/screenshots/hunt-framework.png "Hunt web framework for the D programming language")

Scaffolding is a git clone rather than a CLI:

```bash
git clone https://github.com/huntlabs/hunt-skeleton.git myproject
cd myproject
dub run -v
# then open http://localhost:8080/
```

Now the hard part. Hunt's README states the requirement as **"DMD <= 2.098.0 and >= 2.095.0"**. The last release tag is `v3.3.31-rc.4` from **March 2022**, and the repository's last push was **March 2024**. In practice this means: if your server ships a newer D compiler, Hunt may fail to compile, and there is no upstream release train to fix it. You can pin DMD in your Docker image and freeze the framework, and for an existing application that is a rational choice — a frozen toolchain in a container is stable, if not fashionable. For anything new, it means adopting a dependency tree nobody is patching.

## Diamond — A Reminder That Abandonment Is a Cost

Diamond brands itself as "a full-stack web-framework written in The D Programming Language using vibe.d." It has 176 stars and its last commit was **March 2020**. It is a thin MVC layer on top of vibe.d, which means its technical ideas live on inside vibe.d itself. If you inherit a Diamond application, the migration path is unusually clean: keep your templates and route handlers, port the glue to vibe.d directly, and delete the abstraction layer that stopped receiving security attention six years ago.

## Production Pitfalls Before You Commit to a D Stack

**1. The compiler compatibility matrix is the real risk.** vibe.d explicitly supports only the **10 latest DMD minor releases** and equivalent LDC versions. Containerize your compiler version. "Whatever the distro ships" is how you get a build that breaks on a Tuesday.

**2. DUB's cache is your build cache — treat it that way.** Copy `dub.json` and `dub.selections.json` before your sources. Without that, every image rebuild recompiles the entire dependency tree. Keep `dub.selections.json` pinned in version control so resolutions are reproducible.

**3. OpenSSL is a hard runtime dependency.** vibe.d's own Linux instructions list `libssl-dev` as a prerequisite. Add `libssl3` (or the matching soname) to the runtime stage or your binary starts and immediately dies on the first HTTPS request.

**4. Garbage collection is a design decision, not a footnote.** vibe.d's fiber scheduler is efficient, but allocation-heavy request handlers still produce GC pauses. Budget for object pooling or `@nogc` hot paths if you have tail-latency SLOs.

**5. Bus factor is the price of a small ecosystem.** You will not hire D developers the way you hire Go or Node developers. The trade is the opposite: a statically compiled 10 MB container, no runtime, fast cold starts, and no dependency-management surface to patch.

**6. Cross-compilation is manual.** D builds for the host by default. Build inside the target architecture (or in a multi-arch container) rather than trying to cross-compile from your laptop.

## Related Reading

If you are mapping the compiled-language web landscape, our [Crystal web framework comparison](../2026-08-31-crystal-web-frameworks-kemal-lucky-amber-comparison/) covers another small ecosystem with the same bus-factor tradeoff, and the [Nim web framework comparison](../2026-07-25-nim-web-frameworks-jester-prologue-httpbeast-mofuw/) is the closest analogue to vibe.d in terms of philosophy. For the broader language choice, the [systems programming guide covering Zig, Rust, and Go](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) explains why compiled runtimes keep winning back services that were originally written in scripting languages.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "D Web Frameworks in 2026: vibe.d vs Hunt vs Diamond — Which One Should You Actually Ship?",
  "description": "Live-data comparison of the three D programming language web frameworks: vibe.d, Hunt and Diamond, including Dockerfile, nginx and systemd deployment configs, compiler compatibility risks and a use-case decision matrix.",
  "datePublished": "2026-09-15",
  "dateModified": "2026-09-15",
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

**Is vibe.d fast enough for production HTTP services?**
Yes for typical API workloads. It uses a fiber-based asynchronous event loop over `eventcore`, so thousands of concurrent connections are handled without one thread per request. The practical bottleneck is usually your database driver and allocation behavior rather than the HTTP layer. Compile with `dub build --build=release` and benchmark your own handlers instead of trusting synthetic framework benchmarks.

**Can I run vibe.d behind nginx, Caddy, or Traefik?**
Yes, and you should. Bind the app to `127.0.0.1:8080`, let the reverse proxy handle TLS, HTTP/2, compression, and rate limiting, and forward `X-Forwarded-Proto` so your application can generate correct absolute URLs. This keeps the D process unprivileged and out of the certificate-renewal business.

**Why do Hunt example projects fail to compile on a modern DMD?**
Hunt's documented compiler support window is DMD 2.095.0 through 2.098.0. Newer compilers changed front-end behavior that the framework's last release (March 2022) predates. The fix is to pin the compiler inside your container image — for example by installing a specific DMD release from `downloads.dlang.org` in the build stage — rather than changing the host toolchain.

**Do I need Docker, or can I just ship a single binary?**
A single static binary plus a systemd unit is a perfectly good deployment for a self-hosted D service, and it is lighter than a container runtime. Use Docker when you want reproducible compiler versions and painless rollbacks; use a bare binary plus systemd when the host is yours and you want the fewest moving parts.

**Is Diamond worth evaluating for a new project?**
No. Its last commit was in March 2020 and it is a thin layer over vibe.d. Everything Diamond offers conceptually — MVC structure, ORM convenience — you can get by using vibe.d directly, with an actively maintained dependency tree and a current release cycle.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
