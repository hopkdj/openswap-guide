---
title: "Nitrogen vs Nova vs Zotonic in 2026: Which Erlang Web Framework Should You Actually Use?"
date: "2026-10-01"
description: "A hands-on 2026 comparison of the three surviving Erlang-native web frameworks — Nitrogen, Nova and Zotonic — with real commit data, real build commands and a decision matrix."
tags: ["erlang", "web-frameworks", "beam", "backend", "self-hosted"]
draft: false
cover: "/img/screenshots/nova-framework.jpg"
---

You can serve a million concurrent WebSocket connections from a single box — that is the promise everybody quotes about the BEAM virtual machine. Then you go looking for an Erlang-native web framework to actually build on, and you find something uncomfortable: almost every modern BEAM tutorial quietly points you at Elixir and Phoenix. If you write plain Erlang, your realistic choices in 2026 come down to **three** maintained codebases. Nitrogen, Nova and Zotonic.

This guide compares all three with data pulled from their repositories on **1 October 2026**, shows the real build and controller code for each, and tells you which one to pick — including the one I would not start a new project on.

## Quick Verdict (TL;DR)

**If you are starting a new API or product backend in Erlang, use Nova.** It is the only one of the three with a modern routing model, first-class JSON handlers, and a release path that fits a container workflow. **If you need a CMS and a framework in the same box — editorial content, admin UI, multi-site — use Zotonic**, and accept that you are adopting a platform, not a library. **Pick Nitrogen only if you have an existing Nitrogen application or you specifically want its element-and-postback programming model.** It is stable, it is maintained, but it is the least conventional of the three and its ecosystem is the thinnest.

## The Three Erlang Frameworks Side by Side

| Framework | Stars | Latest release | Last commit | License | Model | Templating | Database | Containers |
|---|---|---|---|---|---|---|---|---|
| **Nova** | 307 | v0.18.1 (18 Sep 2026) | 18 Sep 2026 | Apache-2.0 | Controller + router (`nova_router` behaviour) | DTL templates (.dtl) | Any Ecto-style/custom repo | Builds to a relx release; runs in a slim image |
| **Zotonic** | 848 | tag 0.94.1 (1 Sep 2026); `master` VERSION `1.0.0-rc.17` | 1 Oct 2026 | Apache-2.0 | Full framework + CMS with admin, multi-site | Django-style `.tpl` templates | PostgreSQL (required) | Ships its own `docker-compose.yml` + `start-docker.sh` |
| **Nitrogen** | 982 | 3.0.0 series (no GitHub release tags) | 26 Jul 2026 | MIT | Element + postback (Ajax/WebSocket event model) | Erlang element DSL, no external template language | Mnesia / any Erlang store you wire up | `make package_cowboy` produces a deployable package |

Star counts and commit dates above were read live from GitHub with `gh repo view` and `gh api` on 1 October 2026. Stars are a rough proxy for mindshare, not for activity — note that Nitrogen has the most stars but the oldest last-commit of the three.

## Decision Matrix: Pick in Ten Seconds

| Your use case | Pick | Why |
|---|---|---|
| JSON API or backend for a SPA | **Nova** | Handler tuples (`{json, Map}`) return JSON without ceremony; routing file is explicit and testable |
| Real-time dashboard pushed over WebSockets | **Nitrogen** | Postback/event model was built for Ajax-rich, long-lived connections |
| Content site, multi-tenant CMS, editorial workflow | **Zotonic** | Admin UI, page module, media handling and search are part of the product |
| Greenfield Erlang service that must ship as a container | **Nova** | `rebar3 as prod tar` gives you a relx release you can COPY into a slim runtime image |
| Existing Nitrogen 2 codebase | **Nitrogen 3** | There is an official upgrade script; rewriting to Nova is a bigger project |
| You want to learn BEAM web development | **Nova** | Closest to modern framework conventions; the smallest conceptual jump |
| You need a headless CMS with Postgres and Docker Compose today | **Zotonic** | It is the only one of the three shipping a maintained compose file |

## Nova — The One I Would Build On

Nova is described by its maintainers as a *lightweight and modern web framework for the BEAM VM, with full support for Erlang, Elixir and LFE*. The Phoenix influence is obvious and deliberate: application skeleton, generated config, router behaviour, and a release profile.

Installation is a `rebar3` plugin. Add the plugin to your global rebar config:

```erlang
{plugins,[{rebar3_nova,{git,"https://github.com/novaframework/rebar3_nova.git",
                            {branch,"master"}}}]}.
```

Then generate a project and start it:

```bash
rebar3 new nova my_first_nova
cd my_first_nova
rebar3 shell
```

A controller is a plain Erlang module whose exported functions are named in the router. This is the controller the skeleton generator writes for you:

```erlang
-module({{name}}_main_controller).
-export([
    index/1
]).

index(_Req) ->
    {ok, [{message, "Hello world!"}]}.
```

Routing lives in its own module that implements the `nova_router` behaviour. Each application owns a routes file, and routes can be grouped under a prefix with security applied per group:

```erlang
-module(my_app_router).
-behaviour(nova_router).

-export([routes/1]).

routes(_Environment) ->
  [#{prefix => "/admin",
    security => false,
    routes => [
      {"/", fun my_controller:main/1, #{methods => [get]}}
    ]}
  ].
```

The part that makes Nova pleasant for APIs is that the response is just a tuple, and the **first atom of the tuple selects the handler**. Return `{json, #{status => <<"ok">>}}` and you get HTTP 200 with a JSON body; the advanced form `{json, 201, Headers, Body}` lets you set the status and response headers in the same expression. There is no separate "render" step to learn.

Deploying is the standard Erlang story done properly. Nova defines `dev` and `prod` profiles and uses relx for releases:

```bash
rebar3 as prod tar
```

That produces a tarball containing the release (with ERTS bundled by default, configurable in `rebar.config`). Copy it into a slim base image, run it, and you have a self-contained service with no framework runtime to install on the host.

**Where Nova hurts:** it is at v0.18.1, so API churn is a real risk. The ecosystem is small — you will write more of your own middleware than you would in Phoenix. And its documentation is a set of Markdown guides in the repo rather than a polished book.

## Zotonic — Framework and CMS in One Process

Zotonic is the outlier here: it is not a framework you build an application on top of, it is a **framework plus a content management system** with an admin UI, a page model, media handling, multi-site support, and real-time updates. Its README describes it as *the open source, high speed, real-time web framework and content management system, built with Erlang*.

The reason to take Zotonic seriously for self-hosting is that it is the only one of the three with a maintained container workflow in the repository. The project ships a `docker-compose.yml` which starts PostgreSQL and the Zotonic build container together:

```yaml
services:
    postgres:
        image: docker.io/library/postgres:16.2-alpine
        hostname: postgres
        restart: always
        environment:
            POSTGRES_USER: zotonic
            POSTGRES_DB: zotonic
            POSTGRES_PASSWORD: zotonic
        volumes:
            - pgdata:/var/lib/postgresql/data
        ports:
            - '${DB_FORWARD_PORT:-5432}:5432'

    zotonic:
        build:
            dockerfile: docker/Dockerfile.dev
            context: .
        environment:
            ZOTONIC_PORT: 8000
            ZOTONIC_SSL_PORT: 8443
            ZOTONIC_APPS: /opt/zotonic/apps_user
        depends_on:
            - postgres
        volumes:
            - ./:/opt/zotonic:delegated
        ports:
            - 8000:8000
            - 8443:8443

volumes:
    pgdata:
```

Start it with the script the repository ships, `./start-docker.sh`, and Zotonic comes up on port 8000 with its own HTTPS listener on 8443. Templates are Django-flavoured `.tpl` files, application modules are normal Erlang/OTP applications under `apps/`, and `apps_user/` is where your own site code belongs.

**The version trap:** the repository's `VERSION` file on `master` reads `1.0.0-rc.17`, while the newest tagged release on GitHub is `0.94.1` from 1 September 2026. If you are pinning a deployment, decide explicitly whether you want the release branch or the 1.0 release candidate — the two are not interchangeable, and PostgreSQL is a hard dependency either way.

## Nitrogen — The Ajax-Era Veteran

Nitrogen's pitch has not changed in a decade: *infinitely scaleable, Ajax-rich web applications using a pure Erlang technology stack*. Instead of writing HTML templates and wiring JavaScript by hand, you build pages out of Erlang element records, and user interaction comes back to the server as **postbacks** over WebSockets. If you have ever wished your UI state lived in the same process as your business logic, this is that design taken to its logical conclusion.

Nitrogen 3 projects are built through a `Makefile` that downloads `rebar3.mk` if it is missing and exposes guided targets:

```bash
# interactive build helper
make build

# non-interactive: cowboy-based slim or release builds
make slim_cowboy
make rel_cowboy
make package_cowboy
```

On FreeBSD the same targets run through `gmake`. Upgrading an existing Nitrogen 2 project is supported by an official script in the repository, but read the project's own warning first: it rewrites your working directory structure, so commit before running it.

**Where Nitrogen hurts:** there is no template language to reach for, so the framework's element DSL becomes mandatory rather than optional. Its release cadence is slower than Nova's, there are no GitHub release tags to pin against, and the ecosystem of third-party plugins is small. Choose it deliberately, not by default.

## Pitfalls and Migration Notes

**Do not mix Zotonic release tags with `master`.** The `VERSION` file (`1.0.0-rc.17`) and the newest tag (`0.94.1`) tell different stories. Pin a commit, not a branch name.

**Roughly size your BEAM for WebSockets.** A long-lived-connection design like Nitrogen's shifts memory pressure from request handlers into per-connection processes. Set `+K true`-style scheduler and `+P` process-limit flags in `vm.args` deliberately rather than inheriting defaults.

**Pin your `rebar3` version in CI.** Nova is generated through a `rebar3` plugin, so an unexpected plugin refresh can change your skeleton between builds. Vendor the plugin at a commit SHA in `rebar.config`.

**Budget for PostgreSQL if you pick Zotonic.** The compose file above is not optional scaffolding — the content model expects a relational store, and the default credentials in the file are development values you must change before exposing port 5432.

**Expect to write middleware under Nova.** Anything Phoenix gives you for free — plugs, contexts, generators — you assemble yourself. That is the actual cost of the smaller ecosystem.

**Watch the release-engineering path on all three.** Getting from `rebar3 shell` to a reproducible artifact is a separate skill; the Erlang/Elixir release pipeline is worth studying before you commit to a framework.

## Why Self-Host an Erlang Framework at All?

The honest answer is concurrency economics. A BEAM release on a single mid-sized VPS can hold tens of thousands of idle connections without a thread-per-connection tax, which is why telecom, chat and real-time trading systems have lived on this runtime for decades. When your workload is "many quiet connections with occasional bursts", the BEAM's scheduler and per-process garbage collection beat a request-per-thread stack on the same hardware — and you own the whole artifact, so there is no runtime vendor in the critical path.

For related reading in this series, see our [comparison of Erlang HTTP servers, Cowboy vs Mochiweb vs Yaws](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) — Nova sits on top of Cowboy, so the server layer matters even when the framework hides it. If you want the Elixir side of the same runtime, our [Phoenix vs Plug vs Ash breakdown](../2026-08-12-elixir-web-frameworks-phoenix-plug-ash-comparison/) covers the frameworks that dominate BEAM tutorials. And before you ship anything to production, read the [Erlang and Elixir release engineering guide](../2026-09-20-erlang-elixir-release-engineering-rebar3-relx-mix-releases/) — it is the step that separates a demo from a deployable service.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nitrogen vs Nova vs Zotonic in 2026: Which Erlang Web Framework Should You Actually Use?",
  "description": "A hands-on 2026 comparison of the three surviving Erlang-native web frameworks — Nitrogen, Nova and Zotonic — with real commit data, build commands and a decision matrix.",
  "datePublished": "2026-10-01",
  "dateModified": "2026-10-01",
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

**Is Erlang worth learning for web development in 2026, or should I just use Elixir?**
Elixir gets the tutorials, the hiring market and the framework polish. Erlang gets you the same runtime with a smaller dependency surface and no need to layer a second language's tooling on top. If your team already writes Erlang for telecom, messaging or embedded networking, staying in Erlang for the HTTP layer is reasonable. If you are starting from zero and want the fastest path to a production web app, Elixir and Phoenix are the pragmatic choice.

**Can I use Elixir libraries with Nova?**
Yes. Nova targets the BEAM VM and explicitly supports Erlang, Elixir and LFE, so an Elixir library is compiled to the same bytecode your Erlang application runs. The friction is tooling, not runtime: mixing Mix dependencies into a rebar3 project takes deliberate configuration, and you lose some of the single-toolchain simplicity.

**Does Zotonic require PostgreSQL?**
Yes. PostgreSQL is a hard dependency of the content model, and the project's own Docker Compose setup starts a `postgres:16.2-alpine` container alongside the application. Plan for a database backup routine before you go live.

**Which of the three is best for a real-time dashboard?**
Nitrogen, if your dashboard is dominated by many small server-driven interactions — its postback model was designed for exactly that. For a dashboard that is mostly a JSON API polled by a separate frontend, Nova is the better fit because the JSON handler path is so direct.

**Can all three run in Docker on a small VPS?**
Yes, but the effort differs. Zotonic ships a working `docker-compose.yml` and a start script. Nova gives you `rebar3 as prod tar`, which produces a self-contained release you can copy into a slim image. Nitrogen produces a deployable package through `make package_cowboy`. A 2 GB VPS is enough to evaluate any of them; size the production box by concurrent connections, not by framework choice.

**Is Nitrogen still maintained?**
The repository received commits as recently as July 2026 and the project is on its 3.0.0 series, so it is maintained rather than abandoned — but the cadence and contributor count are well below Nova's, and there are no tagged GitHub releases to pin against. Treat it as stable-and-quiet.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
