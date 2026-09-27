---
title: "Lapis vs Lor vs Sailor in 2026: Which Lua Web Framework Should You Actually Ship On?"
date: "2026-09-28"
tags: ["lua", "web-frameworks", "openresty", "self-hosted", "comparison"]
draft: false
cover: "/img/screenshots/lua-language-logo.jpg"
description: "Lapis, Lor and Sailor compared with live 2026 repository data, real installation commands and deployment configs for OpenResty — including which two you should avoid."
---

Lua web development is a small world with an outsized reputation: sites like itch.io serve enormous traffic from code that runs *inside* Nginx, not in front of it. That efficiency comes from OpenResty, which pairs Nginx with LuaJIT. But once you decide to build on it, you hit the real question — and the honest answer surprises most developers.

Of the three frameworks everyone finds first, **only one is actively maintained in 2026**. The other two have their last commits in 2024 and 2022 respectively, and one of them has a maintainer-wanted banner at the top of its README. Picking a framework whose repository went quiet two years ago is how a weekend project becomes an unmaintainable liability. This comparison uses repository data pulled on **2026-09-28**, real install commands from each project's own documentation, and a deployment config you can actually run.

## TL;DR: Quick Verdict

- **Building anything new in 2026 → use Lapis.** It is the only one of the three with a commit in the last week (2026-09-27), it ships routing, templating, sessions, CSRF protection and a database ORM in one package, and it runs either on OpenResty or on plain `lua-http` if you prefer to avoid Nginx.
- **Already running Lor in production → keep it, but freeze the dependency tree.** Lor's last commit was **2024-01-02**. It is a clean, minimalist router and it still works, but nobody is fixing bugs.
- **Considering Sailor → don't start new work on it.** Its last commit was **2022-10-28**, its own README asks for new maintainers, and its LuaRocks release is still 0.5.0.
- **If your real goal is raw throughput, the framework barely matters.** The platform underneath — OpenResty — does the heavy lifting. Start from the platform, then add the thinnest framework that fits.

## The Three Contenders, Side by Side

All repository data fetched **2026-09-28**.

| | **Lapis** | **Lor** | **Sailor** |
|---|---|---|---|
| Repository | `leafo/lapis` | `sumory/lor` | `sailorproject/sailor` |
| Stars | **3,344** | 1,018 | 938 |
| Last commit | **2026-09-27** | 2024-01-02 | 2022-10-28 |
| Maintenance status | Active | Dormant (~2.7 years) | Abandoned, maintainers wanted |
| Runtime | OpenResty, or `lua-http` (`--cqueues`) | OpenResty (LuaJIT) | Apache2 mod_lua, Nginx/OpenResty, Mongoose, Lighttpd, Xavante, Lwan |
| Language flavour | Lua + MoonScript | Lua | Lua |
| Structure | Routing, etlua templates, ORM, sessions, CSRF | Minimalist router | Full MVC + ORM + validation |
| Templates | `etlua` (ERB-style) | Bring your own | Lua pages, built-in |
| Database | `pgmoon` (Postgres), MySQL, SQLite via modules | Bring your own | MySQL, PostgreSQL, SQLite via `luasql` |
| Install | LuaRocks | `make install`, `opm`, Homebrew | LuaRocks (0.5.0) |
| Licence | MIT | MIT | MIT |

The star counts are close enough to be meaningless as a ranking signal. **Last-commit date is the column that should decide your project.**

## Decision Matrix: Pick in Ten Seconds

| Your situation | Choose | Why |
|---|---|---|
| Greenfield Lua web app in 2026 | **Lapis** | Only actively maintained option; batteries included |
| You want Lua behind Nginx with the least framework possible | **Lor** or plain `lua-resty-*` | Lor's router is genuinely minimal; plain modules avoid a dead dependency |
| You need a full MVC scaffold with generated CRUD | **Sailor** (legacy only) | It ships generation, but you accept an unmaintained core |
| You must run on Apache with `mod_lua` | **Sailor** | The only one of the three that supports mod_lua |
| You want HTTP/2 or HTTP/3 termination with Lua glue | **Lapis on OpenResty** | You inherit Nginx's protocol support directly |
| You need sub-millisecond JSON APIs | **Lapis** with `lua-cjson` | Lapis depends on `lua-cjson` for fast encoding by default |

## Lapis — The Only One You Should Start With

**3,344 stars · last commit 2026-09-27 · MIT**

Lapis is written for Lua and MoonScript and, by default, targets OpenResty. Its own documentation explains the architecture plainly: *"Your web application is run directly inside of Nginx."* That single sentence is the whole performance argument — request routing happens in Nginx's event loop, and Lua coroutines let you write synchronous-looking code that is event-driven underneath.

Installation follows the standard LuaRocks path, with one critical detail from the official guide:

```bash
# OpenResty runs on LuaJIT, which targets Lua 5.1
luarocks install lapis --lua-version=5.1

# Scaffold a project (writes the files listed below)
lapis new
```

Running `lapis new` writes a complete, working skeleton — this is the actual file list from the documentation:

```text
write   config.lua
write   nginx.conf
write   mime.types
write   app.lua
write   models.lua
```

If you would rather not run Nginx at all, `lapis new --cqueues` generates a project that runs on `lua-http` instead. That is a genuinely useful escape hatch: you develop without Nginx, then deploy behind it.

What you get out of the box, per the project's own feature description: environment-based configuration, URL routing, HTML templating with `etlua`, **CSRF protection**, session support, and a relational database object-relational mapper. The rockspec shows the dependency footprint you are accepting:

```lua
dependencies = {
  "lua",
  "ansicolors",
  "argparse",
  "date",
  "etlua",
  "loadkit",
  "lpeg",
  "lua-cjson",
  "luaossl",
  "luasocket",
  "pgmoon",
}
```

Two things stand out. First, **`lua-cjson` is a hard dependency**, so JSON serialisation is fast by default rather than an optimisation you bolt on later. Second, `pgmoon` means Postgres is first-class, while MySQL and SQLite come from additional modules. If your stack is Postgres, Lapis is the shortest path from zero to a deployable API.

For testing your application layer, our [Lua testing frameworks comparison](../2026-09-05-lua-testing-frameworks-busted-luaunit-luassert-comparison/) covers `busted`, which is what the wider Lua ecosystem reaches for.

## Lor — Elegant, Minimal, and Asleep

**1,018 stars · last commit 2024-01-02 · MIT**

Lor describes itself as *"a fast and minimalist web framework based on OpenResty"*, and its API is about as small as a router can be. This is the complete example from its README:

```lua
local lor = require("lor.index")
local app = lor()

app:get("/", function(req, res, next)
    res:send("hello world!")
end)

app:run()
```

That is the entire mental model: match a method and path, send a response. There is no ORM, no template engine and no session layer to learn — you bring your own, or use `lua-resty-*` modules directly.

Installation gives you three routes, also from the README:

```bash
# 1) From source, with an install prefix
git clone https://github.com/sumory/lor
cd lor
make install LOR_HOME=/path/to/lor LORD_BIN=/path/to/lord

# 2) Via OpenResty's package manager (v0.2.2+)
opm install sumory/lor

# 3) Homebrew on macOS
brew install syhily/lor/lor
```

The problem is not the design — it is the calendar. **No commit since 2024-01-02.** Lor still runs, and its dependency-free router is unlikely to rot the way a framework with ten transitive dependencies would, but you are adopting a codebase where a LuaJIT version bump or an OpenResty API change may never be addressed.

A fair way to use Lor in 2026: treat it as **vendored code you own**. Copy it in, pin every dependency, and be prepared to maintain it yourself. If that sounds unappealing, write the same routing table with `lua-resty-*` modules and remove the abandoned dependency from your tree entirely.

## Sailor — A Full MVC Framework Looking for a Home

**938 stars · last commit 2022-10-28 · MIT**

Sailor is the most feature-complete of the three on paper, and every item below is from its own README. It supports **Lua 5.1, Lua 5.2 and LuaJIT**, and uniquely among these projects it runs over Apache2 with `mod_lua`, plus Nginx via OpenResty, Mongoose, Lighttpd, Xavante and Lwan.

It bundles an MVC structure, Lua page parsing, routing, a basic ORM, validation, transactions, sessions, cookies, a login module, form generation and friendly URLs, with MySQL, PostgreSQL and SQLite access through `luasql`. Projects also come shipped with Bootstrap.

Scaffolding uses its own CLI:

```bash
sailor create "app name" /dir/to/app
```

And that is exactly where the caution belongs. The README carries an all-caps banner — **"WE ARE LOOKING FOR NEW MAINTAINERS!"** — and links to an open issue requesting them. The last commit was **2022-10-28**, meaning roughly four years without maintenance, and its LuaRocks release remains **0.5.0**, which signals a project that never reached a stability milestone.

Use Sailor only if you are inheriting an application that already depends on it, or if `mod_lua` on Apache is a hard requirement you cannot move away from. For new builds, the maintenance gap outweighs the feature list.

## The Platform Underneath: OpenResty

**14,049 stars · last commit 2026-09-21**

Every framework above except Sailor's Apache path runs on OpenResty — *"High Performance Web Platform Based on Nginx and LuaJIT"* — and OpenResty itself is in excellent health. It is also the part you should learn first, because the framework you choose is a thin layer over it.

The official container images are built by the OpenResty team and published to the GitHub Container Registry first, then mirrored to Docker Hub as `openresty/openresty`. Real tags from the project's own README include:

| Image tag | Description |
|---|---|
| `openresty/openresty:1.31-alpine` | Latest in the OpenResty 1.31 release series |
| `openresty/openresty:1.29.2.4-1-alpine` | Built-from-source Alpine |
| `openresty/openresty:1.29.2.4-1-bookworm-fat` | Built-from-upstream Debian Bookworm |
| `openresty/openresty:1.29.2.4-1-noble` | Built-from-source Ubuntu Noble |

A minimal deployment built on the team's own image, using the log-streaming behaviour documented for `docker-openresty`:

```yaml
services:
  openresty:
    image: openresty/openresty:1.31-alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/usr/local/openresty/nginx/conf/nginx.conf:ro
      - ./app.lua:/usr/local/openresty/nginx/app.lua:ro
      - openresty-tmp:/var/run/openresty
    restart: unless-stopped

volumes:
  openresty-tmp:
```

Two details from the official documentation that will save you a debugging session. The image symlinks `/usr/local/openresty/nginx/logs/access.log` and `error.log` to `/dev/stdout` and `/dev/stderr` so Docker logging works — **if you change the log paths in your `nginx.conf`, you must recreate those symlinks yourself** or your logs silently vanish. Second, temporary paths such as `client_body_temp_path` live under `/var/run/openresty/`, which is exactly why the volume above exists: mount it rather than writing into the container's ephemeral filesystem.

If you are deciding how to terminate TLS and route traffic in front of this, our [OpenResty vs Nginx vs Caddy comparison](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/) covers the trade-offs. And for teams comparing the Lua approach with other dynamic languages, our [Raku web frameworks comparison](../2026-09-23-raku-web-frameworks-cro-bailador-humming-bird/) makes an instructive parallel — small ecosystems converge on very similar trade-offs.

## Pitfalls and Migration Traps

**1. Installing Lapis against the wrong Lua version.** OpenResty uses LuaJIT, which targets Lua 5.1. The official guide is explicit: use `--lua-version=5.1` with LuaRocks when you plan to run inside OpenResty, or the module will not load in OpenResty's runtime.

**2. Judging frameworks by star count.** Lor (1,018) and Sailor (938) have comparable popularity to many healthy projects, but their last commits are 2024 and 2022. A star count is a historical signal; a commit date is a current one.

**3. Mixing `opm` and LuaRocks carelessly.** Lor installs through two different package managers depending on the route you pick, and the README notes that the `lord` CLI is not supported with the `opm` installation. Pick one package manager per project and stay on it.

**4. Assuming a dormant router is harmless.** A dependency-free router like Lor is low-risk, but "low-risk" is not "no-risk". Vendor it, pin it, and own it.

**5. Forgetting CSRF and sessions when you skip a framework.** If you route with raw `lua-resty-*` modules instead of Lapis, you must implement request-forgery protection and session storage yourself. Lapis includes both; hand-rolled versions usually ship with holes.

**6. Deploying a `config.lua` with development defaults.** Lapis scaffolds environment-based configuration precisely so credentials stay out of the image. Mount configuration at deploy time rather than baking it into the container layer.

## FAQ

**Is Lua still worth using for web development in 2026?**
Yes, in a specific niche: high-throughput request handling where the application logic runs inside Nginx. The performance comes from running in the same process as the server, not from the language. For CPU-bound business logic, a general-purpose language with a larger library ecosystem will usually be more productive.

**Which of these frameworks should I choose for a new project?**
Lapis, without much deliberation. It is the only one of the three with commits in the last week of September 2026, and its feature set — routing, `etlua` templating, sessions, CSRF protection and a relational ORM — removes the need to assemble those pieces yourself.

**Can I use Lor in 2026 if I already have it in production?**
Yes, but treat it as frozen. Its last commit was 2024-01-02, so vendor the source, pin every dependency, and plan to maintain it internally. Do not adopt it for new work when Lapis is available and active.

**Does Sailor still receive security fixes?**
Nothing suggests it does. Its last commit was 2022-10-28 and its README explicitly asks for new maintainers. Running an unmaintained framework that handles sessions and form input in front of the public internet is a risk worth avoiding.

**Do I need Nginx to use Lapis?**
No. `lapis new --cqueues` scaffolds a project that runs on `lua-http` instead of OpenResty, which is convenient for development and for environments where you cannot run Nginx. OpenResty remains the recommended production target.

**What does LuaJIT's Lua 5.1 compatibility actually mean for me?**
Modules written against newer Lua syntax may not load. The practical rule from Lapis's own guide is to install with `luarocks install lapis --lua-version=5.1` whenever OpenResty is the runtime, and to verify each dependency supports that target before you commit to it.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Lapis vs Lor vs Sailor in 2026: Which Lua Web Framework Should You Actually Ship On?",
  "description": "Lapis, Lor and Sailor compared with live 2026 repository data, real installation commands and OpenResty deployment configs, including which two to avoid.",
  "datePublished": "2026-09-28",
  "dateModified": "2026-09-28",
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
