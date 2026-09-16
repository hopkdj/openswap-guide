---
title: "Zap vs http.zig vs Tokamak in 2026: Which Zig HTTP Server Should You Actually Build On?"
date: "2026-09-17"
tags: ["zig", "web-frameworks", "http", "backend", "systems-programming"]
description: "Zap 3.4k stars, http.zig 1.6k stars and Tokamak compared for Zig 0.15/0.16/0.17 in 2026 — real router code, version-branch traps, Windows and TLS limitations, and production pitfalls."
cover: "/img/screenshots/zap-zig-mascot.jpg"
draft: false
---

The fastest way to lose a weekend in Zig is to pick an HTTP server whose target Zig version is one release behind the compiler you just installed. Zig's standard library moves fast, `std.http` has been reworked more than once, and by 2026 the ecosystem has split into three credible camps that disagree about almost everything: how much framework you should get, whether the server should terminate TLS itself, and whether the whole thing should even be considered production-ready.

This is a decision guide rather than a cheerleading piece. **Zap** (3,416 stars) built a full application framework on top of the C library facil.io. **http.zig** (1,602 stars) offers a lean HTTP/1.1 server with a surprisingly complete feature list. **Tokamak** (634 stars) is a dependency-injection framework that *builds on top of http.zig*. They occupy three genuinely different positions, and the right answer depends on how much you want to own.

## TL;DR: The Quick Verdict

- **Pick Zap if you want batteries included and you are deploying on Linux.** Application context, endpoint structs, per-request arena allocators, an error strategy, auth helpers, TLS through system OpenSSL and a built-in documentation server. The catch: it depends on facil.io and **does not run on Windows natively**.
- **Pick http.zig if you want a substrate, not a framework.** A router with `:captures`, WebSockets, server-sent events, middleware, per-request contexts, metrics, testing helpers and documented HTTP compliance — while staying close enough to the metal that you own the architecture.
- **Pick Tokamak if you want structure across a real codebase.** It layers dependency injection, hierarchical routes and basic Swagger generation on top of http.zig, and it is explicit that it is **not meant to be exposed directly to the internet** — put Nginx or a CDN in front.

If you take nothing else away: **http.zig is the foundation, Zap is the alternative foundation, and Tokamak is the framework you put on the foundation.**

## Head-to-Head Comparison (September 2026 data)

Stars and last-commit dates pulled live from GitHub on 2026-09-17.

| Dimension | Zap (zigzap/zap) | http.zig (karlseguin/http.zig) | Tokamak (cztomsik/tokamak) |
|:---|:---|:---|:---|
| GitHub stars | 3,416 | 1,602 | 634 |
| Last commit | 2026-09-06 | 2026-08-26 | 2026-08-28 |
| License | MIT | MIT | MIT |
| Underlying stack | facil.io (C library) | Own HTTP/1.1 implementation | **Built on http.zig** |
| Target Zig version | Stable + separate `zig-master` branch | `master` = latest stable, `dev` = tip, `zig-X.YY` branches | **Zig 0.17.x** |
| Windows support | ❌ (WSL2 or container only) | ✅ | ✅ (inherits http.zig) |
| TLS in-process | ✅ via system OpenSSL | Handled by reverse proxy / TLS terminator | ❌ by design — expects a proxy |
| Router with captures | ✅ endpoint per path | ✅ `:CAPTURE_NAME` | ✅ hierarchical routes |
| Dependency injection | Application context | Per-request context | ✅ full DI container |
| WebSockets | ✅ | ✅ | Via http.zig |
| Server-sent events | Via facil.io | ✅ documented | Via http.zig |
| Static file serving | ✅ | ✅ | ✅ `tk.static.dir()` |
| Generated API docs | Built-in doc server (`zig build run-docserver`) | ❌ | ✅ basic Swagger support |
| Metrics | Manual | ✅ built-in metrics | Manual |
| Maturity posture | Production-oriented, Linux-first | HTTP/1.1 server, feature-complete | Explicitly unstable release line |

## Decision Matrix: Pick In Ten Seconds

| Your situation | Choose | Why |
|:---|:---|:---|
| First Zig web service, Linux deployment | **Zap** | Most guidance, examples and batteries for the least code |
| You need TLS terminated by the app itself | **Zap** | Only one of the three that does OpenSSL in-process |
| Windows developers on the team | **http.zig** | Zap's facil.io dependency rules Windows out |
| You want to control the architecture end to end | **http.zig** | It is a server and router, not an opinionated app model |
| Multi-module service with shared services | **Tokamak** | The DI container is the whole point |
| You are already running Nginx or a CDN | **Tokamak** | It assumes a proxy handles TLS and caching |
| You need WebSockets plus generated docs | **Tokamak** | WebSockets from http.zig, Swagger from Tokamak |
| You must pin to one Zig version for a year | **http.zig** | Versioned `zig-X.YY` branches make pinning explicit |

## Zap: The Framework With Batteries

Zap's design centres on two ideas: a **global application context** available to every handler, and **endpoints** — structs that own a URL path and expose one function per HTTP method. The framework hands each callback a per-request arena allocator, so short-lived allocations can be made freely and freed in bulk when the request ends.

```zig
const zap = @import("zap");
const Allocator = std.mem.Allocator;

// The global Application Context — your database handle, config, anything shared.
const MyContext = struct {
    db_connection: []const u8,

    pub fn init(connection: []const u8) MyContext {
        return .{ .db_connection = connection };
    }
};

const SimpleEndpoint = struct {
    // zap.App.Endpoint interface
    path: []const u8,
    error_strategy: zap.Endpoint.ErrorStrategy = .log_to_response,
    some_data: []const u8,
    io: std.Io,

    pub fn init(io: std.Io, path: []const u8, data: []const u8) SimpleEndpoint {
        return .{ .path = path, .some_data = data, .io = io };
    }

    pub fn get(e: *SimpleEndpoint, arena: Allocator, context: *MyContext, r: zap.Request) !void {
        r.setStatus(.ok);
        // Allocations from `arena` are freed in bulk after the response.
        const body = try std.fmt.allocPrint(
            arena,
            "db: {s} / endpoint: {s}\n",
            .{ context.db_connection, e.some_data },
        );
        try r.sendBody(body);
    }
};
```

Wiring it up is three calls — create the app, register endpoints, listen:

```zig
pub fn main(init: std.process.Init) !void {
    const io = init.io;

    var gpa: std.heap.DebugAllocator(.{ .thread_safe = true }) = .{};
    defer std.debug.print("Leaks detected: {}\n", .{gpa.deinit() != .ok});
    const allocator = gpa.allocator();

    var my_context = MyContext.init("connection established");

    const App = zap.App.Create(MyContext);
    try App.init(io, allocator, &my_context, .{});
    defer App.deinit();

    var endpoint = SimpleEndpoint.init(io, "/test", "endpoint data");
    try App.register(&endpoint);

    try App.listen(.{ .interface = "0.0.0.0", .port = 3000 });
}
```

The details that decide whether Zap fits you are in its own documentation:

- **Windows is not supported.** The dependency on facil.io means your options on Windows are WSL2 or a container. This is the single most common reason teams choose http.zig instead.
- **TLS works in-process.** Zap can use the system OpenSSL, enabled with `-Dopenssl` or the environment variable `ZAP_USE_OPENSSL=true`. If you do not want a reverse proxy on every deployment, this matters.
- **There is a documentation server.** `zig build run-docserver` serves the API docs locally — a small touch that saves real time when you are learning an unfamiliar API.
- **The `zig-master` branch is unsupported.** It tracks compiler tip and comes with **no tagged releases**. Pin to tagged versions if you value reproducibility.

One more design detail worth importing into your own code: Zap's `DebugAllocator` pattern in `main()` prints a leak report at shutdown, and the example repository includes a `/stop` endpoint specifically so tests can shut the server down and trigger that report. Building leak detection into the development loop is the right instinct for a language where you manage memory manually.

## http.zig: The Substrate

http.zig is an HTTP/1.1 server written directly against the Zig standard library, and its README is refreshingly honest about the current state of Zig's own HTTP work. The example is compact enough to read in full:

```zig
const std = @import("std");
const httpz = @import("httpz");

pub fn main(init: std.process.Init) !void {
    const allocator = init.gpa;

    // More advanced cases use a custom "Handler" instead of "void".
    var server = try httpz.Server(void).init(init.io, allocator, .{
        .address = .localhost(5882),
    }, {});
    defer {
        server.stop();   // clean shutdown: finishes serving live requests
        server.deinit();
    }

    var router = try server.router(.{});
    router.get("/api/user/:id", getUser, .{});

    try server.listen();   // blocks
}

fn getUser(req: *httpz.Request, res: *httpz.Response) !void {
    res.status = 200;
    try res.json(.{ .id = req.param("id").?, .name = "Teg" }, .{});
}
```

Behind that small surface sits a much larger feature set than the star count suggests. The table of contents alone lists custom dispatch, per-request context, custom not-found and error handlers, dispatch takeover, memory and arena management, router capture parameters, middlewares, configuration, **built-in metrics**, testing helpers, documented HTTP compliance, server-sent events and WebSockets.

Two practical warnings come straight from the project:

1. **Version branches are the whole game.** `master` targets the latest *stable* Zig, `dev` targets compiler tip, and `zig-X.YY` branches exist for specific releases. If your team pins a Zig version for a year, pin the matching branch and read the release notes before moving.
2. **The newest branch may be ahead of its own test coverage.** The Zig 0.16 line of http.zig carries an explicit note that it is not well tested and should be considered experimental, mirroring the state of Zig 0.16 itself. On a new-project timeline, that is a scheduling risk you should write down rather than discover at launch.

Where http.zig wins decisively is that it does not decide anything for you. There is no application context object, no endpoint enum, no framework lifecycle — you write `fn getUser(req, res)` and you write the rest of the architecture yourself. For a small service or an embedded HTTP API inside a larger binary, that is exactly right.

## Tokamak: Dependency Injection On Top Of http.zig

Tokamak makes two architectural choices that differentiate it immediately. First, it **builds on http.zig** rather than the standard library's HTTP server, citing better performance. Second, it is built around a **dependency injection container** — services are registered in bundles and injected into route handlers.

```bash
zig fetch --save "git+https://github.com/cztomsik/tokamak#main"
```

```zig
const tokamak = @import("tokamak");

pub fn build(b: *std.Build) void {
    const exe = b.addExecutable(.{ /* ... */ });

    // Wires the module, dependencies and any generated code.
    tokamak.setup(exe, .{});
}
```

Routing is declared as data, and handlers are ordinary functions that receive router by dependency injection:

```zig
const std = @import("std");
const tk = @import("tokamak");

const routes: []const tk.Route = &.{
    .get("/", hello),
};

fn hello() ![]const u8 {
    return "Hello";
}

pub fn main(init: std.process.Init) !void {
    var server = try tk.Server.init(init.io, init.gpa, routes, .{
        .listen = .{ .port = 8080 },
    });
    defer server.deinit();

    try server.start();
}
```

The project's documentation is unusually candid about intended deployment. Tokamak states plainly that it is **not designed to be used alone** — it expects a reverse proxy such as Nginx or CloudFront in front of it to handle TLS, caching and sanitisation. That is a legitimate architecture (it is how a great many production services are deployed), but it is a requirement rather than a suggestion, and it removes Tokamak from the "single static binary serving HTTPS in a container" use case that makes Zap attractive.

Its feature list explains the star count trajectory: multi-module support with cross-module initializers, providers and overrides; hierarchical and introspectable routes; basic Swagger generation; `tk.static.dir()` for serving whole directories; a CLI module; and a work-in-progress TUI module for interactive applications. The main branch targets **Zig 0.17.x**, and the project warns that the 0.17 release line may still be unstable with **occasional breaking changes from upstream**. There is also an explicit chicken-and-egg worth noting: Tokamak's own stability is bounded by http.zig's stability, and its migration notes show a rename of `inj.call0(fun)` to `inj.call(fun)` and a reworked multi-module API — the churn is visible in the changelog, which is a good sign for transparency and a caution for production timelines.

## Pitfalls That Bite In Production

**Zig version drift is the number one cause of wasted time.** All three projects track a moving compiler, and each carries branches for multiple Zig releases. Decide your pinned Zig version first, then pick the framework branch that matches it — not the other way round. A container image with `zig` on `latest` and a framework pinned to an old branch is a build failure waiting for a Tuesday.

**Windows support is not universal.** Zap cannot run natively on Windows because of facil.io. If a developer on your team works on Windows without WSL2, that is a hard blocker regardless of how much you like the application context model.

**Decide who terminates TLS before you write code.** Zap can do it in-process with OpenSSL. Tokamak expects a proxy to do it and does not ship in-process TLS. http.zig leaves the choice to you. This affects certificates, renewal, health checks and your container topology — it is an infrastructure decision disguised as a framework detail.

**Arena allocators are a discipline, not a convenience.** Zap hands handlers a per-request arena whose contents are freed in bulk. That is excellent for building a response, and wrong for anything that must outlive the request. Storing an arena-allocated slice in a global cache or a long-lived connection produces use-after-free bugs that only appear under load.

**Do not put a framework without TLS in front of the internet.** Tokamak says this about itself. Believe it. Serving plain HTTP directly on a public interface, even behind a proxy you forgot to configure, is how credentials end up in logs.

**Test HTTP compliance for your specific needs rather than assuming.** http.zig documents its compliance posture, which is exactly the right thing to do and also a hint: read it before assuming HTTP/1.1 edge cases (chunked transfers, `Expect: 100-continue`, header limits) behave the way your client expects.

**Plan for breaking changes across minor versions.** The migration notes in these projects rename functions and rework APIs between releases. Wrap third-party framework types behind your own thin layer so a rename is a one-file change instead of a repository-wide refactor.

## Where This Fits In A Real Stack

Zig's selling point is the single static binary — compile once, copy, run. On Linux that story is strongest with Zap (TLS, no proxy required) and most flexible with http.zig (own the architecture, compose what you need). If you are still building out the toolchain around the language, our [Zig toolchain guide covering zig build, ZLS and zig cc](../2026-09-14-zig-toolchain-zig-build-zls-zig-cc-guide/) is the natural next read, and the [Zig vs Rust vs Go systems programming comparison](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) covers when reaching for Zig is the right call at all.

For a sense of how the same decision plays out in other ecosystems, the trade-offs rhyme remarkably well: the [Gleam HTTP server comparison](../2026-09-12-gleam-http-servers-mist-wisp-cowboy-comparison/) shows the same split between minimal servers and opinionated frameworks, and the [Erlang HTTP server round-up](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) covers the opposite end of the maturity curve, where all three options have been in production for a decade. The lesson across all of them is identical: the framework decision is mostly a decision about who owns TLS, routing and application structure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Zap vs http.zig vs Tokamak in 2026: Which Zig HTTP Server Should You Actually Build On?",
  "description": "Zap, http.zig and Tokamak compared as Zig HTTP servers in 2026, covering Zig version branches, Windows and TLS limitations, dependency injection, real router code and production pitfalls.",
  "datePublished": "2026-09-17",
  "dateModified": "2026-09-17",
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

**Which Zig HTTP server should a beginner start with?**

Start with **Zap** if you are on Linux and want the shortest path to a working service: it provides an application context, endpoint structs, a per-request arena allocator and a built-in documentation server, so there is less architecture to invent on day one. Start with **http.zig** instead if you want to learn how HTTP servers actually work in Zig — its example is about fifteen lines, and you will understand every piece of it. The blocking factor to check first is Windows: Zap requires WSL2 or a container there, while http.zig does not.

**Does Zap run on Windows?**

No. Zap depends on the facil.io C library, which does not support Windows, and the project's own documentation states this plainly. The recommended options are WSL2 or a Docker container. If native Windows execution is a requirement, http.zig or Tokamak (which builds on http.zig) are the practical choices.

**Can http.zig terminate TLS itself?**

http.zig focuses on being an HTTP/1.1 server; the standard deployment pattern is to terminate TLS at a reverse proxy or load balancer in front of it. Zap is the outlier here — it supports TLS in-process using the system OpenSSL, enabled at build time with `-Dopenssl` or via the `ZAP_USE_OPENSSL=true` environment variable. Choose based on whether you want certificate management inside your process or outside it.

**Is Tokamak production-ready in 2026?**

Tokamak is honest that its main branch targets Zig 0.17.x and that the release line may still be unstable with occasional breaking changes from upstream. It is a young framework with visible API churn, and it explicitly expects a reverse proxy in front of it. For internal services and teams comfortable tracking a fast-moving compiler, that is workable. For a service you will not touch for a year, the version-pinning risk is real and should be budgeted for rather than ignored.

**How do I handle Zig version updates across these projects?**

Pin your Zig version and pick the framework branch that matches it. http.zig makes this explicit with `master` for the latest stable Zig, `dev` for compiler tip and `zig-X.YY` branches for individual releases; Zap ships a `zig-master` branch that has no tagged releases and is described as unsupported. Update the compiler and the framework together in one pull request, with your integration tests running in CI against the pinned pair.

**Which one has the best WebSocket support?**

http.zig documents WebSockets and server-sent events as first-class features with dedicated examples, and since Tokamak builds directly on http.zig it inherits both. Zap handles WebSockets through facil.io, which is a mature C implementation. All three can do it; the deciding factor is usually the surrounding architecture — routing, DI and generated documentation — rather than the WebSocket layer itself.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
