---
title: "Cowboy vs MochiWeb vs Yaws in 2026: Which Erlang HTTP Server Should You Use?"
date: "2026-09-04"
tags: ["erlang", "http-server", "websocket", "backend", "otp"]
draft: false
cover: "/img/screenshots/cowboy-cover.jpg"
---

Your RabbitMQ management console, your Phoenix endpoints, and the STOMP bridge your message broker exposes all have one thing in common: an Erlang HTTP server underneath. Erlang/OTP's battle-tested concurrency model makes it a favorite for telecom-grade, low-latency backends, and the HTTP layer you pick determines latency, memory footprint, and how much boilerplate your team writes. In 2026 the choice still comes down to three projects: **Cowboy**, **MochiWeb**, and **Yaws**. They look interchangeable at a glance — all three speak HTTP/1.1 on the Beam — but they target completely different jobs.

## TL;DR: Quick Verdict

**If you are embedding an HTTP server inside your own Erlang application — the 95% case today — use Cowboy.** It is the smallest, fastest, best-documented option, it is the default server under Phoenix and the one RabbitMQ's management UI ships, and it gives you WebSockets and HTTP/2 without breaking a sweat. **If you want a full standalone web server with virtual hosts, dynamic configuration, and zero Erlang code required to serve static sites, use Yaws.** **MochiWeb** is the legacy option: fine for tiny embedded endpoints in codebases that already use it, but its sparse docs and manual routing make it the wrong default for new projects.

## Quick Comparison Table

| | Cowboy | MochiWeb | Yaws |
|---|---|---|---|
| **GitHub stars** | 7,526 | 1,891 | 1,312 |
| **Last push** | 2026-08 | 2026-08 | 2026-05 |
| **License** | ISC | MIT | BSD-3-Clause |
| **Latest release** | 2.18.0 | 2.3.0 (maintained) | 2.2.x |
| **HTTP/2** | ✅ (TLS) | ❌ | ✅ (behind TLS) |
| **WebSockets** | ✅ first-class | via library | ✅ appmod |
| **Routing** | Built-in router + middlewares | Manual in your loop | Config-file + appmods |
| **Config style** | Code (Erlang terms) | Code | `yaws.conf` file, hot-reloadable |
| **Best for** | Embedding in apps | Legacy embedded | Standalone multi-site server |

*Stats fetched via the GitHub API on 2026-09-04.*

## Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| HTTP API inside your OTP app | **Cowboy** | Router, middlewares, TLS and WebSockets in one small dependency |
| You are building on Phoenix / Plug | **Cowboy** | It *is* the default Phoenix adapter — zero extra decisions |
| Standalone server for many vhosts, non-Erlang operators | **Yaws** | Reload config without recompiling; `.yaws` pages; apt-installable |
| Maintaining an old Erlang codebase | **MochiWeb** | Match existing patterns; don't migrate what isn't broken |
| Max throughput WebSocket fan-out | **Cowboy** | Ranch-managed connections, binary-optimized, proven at scale |

## Cowboy: The Modern Default

Cowboy is a small, fast, modern HTTP server written by Loïc Hoguin, first released in 2011 and now at **v2.18.0 (August 2026)** with **7,526 stars** on GitHub. It deliberately provides "a complete HTTP stack in a small code base," optimized for low latency and low memory usage. Connections are managed by **Ranch** (a separate library from the same author), which means you get robust acceptor pools, connection limits, and TLS termination without writing any of that yourself. Cowboy ships with a URL router (`cowboy_router`), a middleware system, and first-class WebSocket and Server-Sent Events support.

Because it is a library rather than a daemon, you start it from your application's supervision tree. The canonical hello world from the official 2.18.0 examples repo says it all:

```erlang
%% toppage_h.erl — the request handler
-module(toppage_h).
-export([init/2]).

init(Req0, Opts) ->
	Req = cowboy_req:reply(200, #{
		<<"content-type">> => <<"text/plain">>
	}, <<"Hello world!">>, Req0),
	{ok, Req, Opts}.
```

```erlang
%% hello_world_app.erl — wiring the listener into your app
start(_Type, _Args) ->
	Dispatch = cowboy_router:compile([
		{'_', [
			{"/", toppage_h, []}
		]}
	]),
	{ok, _} = cowboy:start_clear(http, [{port, 8080}], #{
		env => #{dispatch => Dispatch}
	}),
	hello_world_sup:start_link().
```

That is the entire mental model: compile a dispatch table, start a listener, write handlers. Streaming responses, chunked transfer, trailers, and upgrade to WebSocket are all handled by the `cowboy_req` API rather than special frameworks.

Why it won the ecosystem: **Phoenix uses Cowboy as its default HTTP adapter**, RabbitMQ ships Cowboy for its management and Web STOMP interfaces, and a large share of the Erlang SaaS world runs it in production. The documentation (ninenines.eu) is thorough, versioned, and actively maintained — which is more than can be said for the alternatives.

## MochiWeb: The Lightweight Veteran

MochiWeb began life inside Mochi Media around 2007 as the HTTP layer for their ad-serving and analytics infrastructure, and it became the first Erlang HTTP library many companies embedded. Today it sits at **1,891 stars**, is MIT-licensed, and still receives commits (last push August 2026). It is a library in the strictest sense: you hand it a **loop fun** that receives a `mochiweb_request` object, and you do your own dispatch.

The official example project shows the shape:

```erlang
start(Options) ->
    {DocRoot, Options1} = get_option(docroot, Options),
    Loop = fun (Req) -> (?MODULE):loop(Req, DocRoot) end,
    mochiweb_http:start([{name, ?MODULE}, {loop, Loop}
			 | Options1]).

loop(Req, DocRoot) ->
    "/" ++ Path = mochiweb_request:get(path, Req),
    case mochiweb_request:get(method, Req) of
        Method when Method =:= 'GET'; Method =:= 'HEAD' ->
            case Path of
                "hello_world" ->
                    mochiweb_request:respond(
                        {200, [{"Content-Type", "text/plain"}],
                         "Hello world!\n"}, Req);
                _ ->
                    mochiweb_request:serve_file(Path, DocRoot, Req)
            end;
        'POST' ->
            mochiweb_request:not_found(Req);
        _ ->
            mochiweb_request:respond({501, [], []}, Req)
    end.
```

MochiWeb's strengths are its tiny footprint and its long production history — it ran behind some of the busiest Erlang deployments of the 2010s. Its weaknesses are real, though: no built-in router (you write the `case` yourself), documentation that has not kept pace with Cowboy's, and no first-class HTTP/2 story. If you are starting a greenfield service today, you are choosing a 2007 design philosophy for no benefit.

## Yaws: The Standalone Server with the Config File

Yaws — "Yet Another Web Server" — was started by Claes "klacke" Wikström in 2001 and is the oldest of the three. At **1,312 stars** (BSD-3-Clause) it is smaller on GitHub, but it targets a different deployment model: a **standalone daemon** that non-Erlang operators can install, configure, and run like Apache or nginx. Debian and Ubuntu ship it as the plain `yaws` package, and it manages **virtual servers** from a single Erlang-syntax config file, `yaws.conf`:

```text
# Global settings apply to all virtual servers
logdir = /var/log/yaws

# Extra beam code directories
ebin_dir = /usr/lib/yaws/examples/ebin

max_connections = nolimit
keepalive_maxuses = nolimit

# Virtual server section
<server www.example.com>
    port = 80
    listen = 0.0.0.0
    docroot = /var/www/example
    <directory /downloads>
        allow = 127.0.0.1
    </directory>
</server>
```

The killer feature for ops teams: **you can edit `yaws.conf` and reload it at runtime** — Yaws re-reads the configuration and applies changes to live virtual servers without a restart and without recompiling anything. The other differentiator is the `.yaws` page model: files that mix HTML with embedded Erlang, evaluated server-side, similar in spirit to PHP but on the Beam. For request handling beyond static files you write **appmods** — Erlang modules that hook into the request lifecycle.

Yaws has genuine WebSocket support (exposed through appmods) and HTTP/2 when terminated behind TLS, but its architecture predates the "everything is a library, compose it yourself" philosophy that dominates modern Erlang. If you need to scale one specific endpoint with fine-grained control, you will fight the config-file model; if you need to hand a server to an ops person who does not write Erlang, Yaws is the only one of the three that fits out of the box.

## Pitfalls and Migration Gotchas

1. **Cowboy 1.x vs 2.x is a rewrite.** If you find old tutorials showing `cowboy:start_http/3` and `Req` as a record accessed via `Req#req.method`, that is Cowboy 1.x. The 2.x line (current: 2.18) uses `cowboy:start_clear/3` and the map-based `cowboy_req` API. Porting is mechanical but touches every handler.
2. **Ranch owns your sockets.** Cowboy 2.x delegates connection handling to Ranch 2.x. If you also use Ranch directly (RabbitMQ-style use), pin one version — mixed Ranch 1.x/2.x in one release will fail at startup with callback-module errors.
3. **WebSockets need `cowboy:start_clear` + upgrade in the handler** — there is no magic flag. The handler returns `{cowboy_websocket, Req, State}` from `init/2` and implements `websocket_handle/2`. Missing the upgrade path is the #1 cause of "it returns 200 but never upgrades".
4. **MochiWeb's API is frozen in time.** `mochiweb_request` still exposes the old-style `Req:get(method)` in many codebases; the current API is `mochiweb_request:get/2`. Both work, neither is documented well. Budget time for reading source.
5. **Yaws + TLS:** modern Yaws versions removed some legacy SSL options; configure TLS per-`<server>` block with a `keyfile`/`certfile`, and expect to consult the changelog if you upgrade from a pre-2019 release.
6. **Don't put blocking calls in handlers.** This applies to all three: Erlang HTTP handlers run on scheduler threads. A `gen_server:call` or `timer:sleep` in a handler stalls that scheduler. Use `cowboy_req:cast`-style patterns or hand off to a worker process — the classic Erlang mistake is treating handlers like blocking middleware.

## Which One Should You Actually Deploy?

For 2026 greenfield work the answer is unambiguous: **Cowboy**, embedded in a standard OTP application with `rebar3`. You get routing, middlewares, TLS, WebSockets, and a supervision-tree-friendly lifecycle, and you inherit an ecosystem where Phoenix and RabbitMQ already exercise the same code paths. Choose **Yaws** only when you need an operator-managed standalone server with dynamic virtual hosts — it remains uniquely good at that job. Keep **MochiWeb** for the legacy systems already running it; migrating off it is rarely worth the risk.

If you are exploring the Erlang/OTP ecosystem, also see our [Elixir web framework comparison (Phoenix, Plug & friends)](../2026-08-12-elixir-web-frameworks-phoenix-plug-ash-comparison/) — Phoenix's production HTTP layer *is* Cowboy, so that guide shows the framework side of the same stack. For the messaging side of Erlang deployments, our [message broker high-availability guide (RabbitMQ, Kafka, NATS)](../2026-06-01-self-hosted-message-broker-ha-rabbitmq-kafka-nats-guide/) covers the RabbitMQ/OTP runtime these servers often sit next to, and the [Elixir HTTP client comparison](../2026-08-21-elixir-http-clients-tesla-req-httpoison-comparison/) is the natural companion if you are building both ends of the connection.

## FAQ

**Is Cowboy used by Phoenix?**
Yes. Phoenix's default HTTP adapter is Plug.Cowboy, which wraps Cowboy's listener and routes requests through the Plug pipeline. Upgrading Phoenix usually means upgrading Cowboy underneath, so Phoenix users get its fixes automatically.

**Does Yaws support WebSockets?**
Yes — Yaws supports WebSocket connections through appmods, and modern releases handle the upgrade handshake. It is functional but more involved than Cowboy's first-class `cowboy_websocket` behaviour, which is why most teams doing heavy realtime traffic pick Cowboy.

**Can MochiWeb handle HTTP/2?**
No. MochiWeb is an HTTP/1.1 library. If HTTP/2 is a requirement — for example to avoid head-of-line blocking on high-latency links or to use server push — Cowboy is the only one of the three with first-class HTTP/2 support (over TLS).

**How do I choose between Cowboy and Yaws for a small internal tool?**
If you (or your team) write Erlang and want the server embedded in the application, use Cowboy. If the tool must be operated by someone who does not write Erlang, or you need many virtual hosts with per-host docroots that change at runtime, Yaws' config-file model is a better operational fit.

**Is Yaws still actively maintained in 2026?**
Yes. The erlyaws/yaws repository received its last push in May 2026, and releases continue. Development velocity is lower than Cowboy's, but the project is stable, packaged in Debian/Ubuntu, and not abandoned.

**What license should I worry about?**
Cowboy is ISC, MochiWeb is MIT, and Yaws is BSD-3-Clause — all permissive, all safe to embed in commercial products without copyleft obligations.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Cowboy vs MochiWeb vs Yaws in 2026: Which Erlang HTTP Server Should You Use?",
  "description": "Compare the three Erlang/OTP HTTP servers: embed Cowboy in your app, run Yaws as a standalone multi-vhost daemon, or keep MochiWeb for legacy systems. Includes real code, 2026 GitHub stats, and migration pitfalls.",
  "datePublished": "2026-09-04",
  "dateModified": "2026-09-04",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide"},
  "mainEntityOfPage": "https://www.pistack.xyz/posts/2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/"
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
