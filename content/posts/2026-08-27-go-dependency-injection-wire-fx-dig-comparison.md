---
title: "Go Dependency Injection in 2026: Wire vs Fx vs Dig — Which One Should You Actually Use?"
cover: "/img/screenshots/wire-di-cover.jpg"
date: "2026-08-27"
tags: ["go", "dependency-injection", "golang", "developer-tools", "library-comparison"]
draft: false
---

Google just abandoned the most popular dependency injection tool in Go, and most teams have not noticed. The `google/wire` README now opens with a warning that the project is **no longer maintained** — after 14,400+ stars made it the default answer to every "how do I do DI in Go" question. Meanwhile Uber's two DI libraries, Fx and dig, keep shipping behind a strict v1 SemVer promise, and the Go ecosystem has quietly split into three very different philosophies: compile-time code generation, runtime application frameworks, and a bare reflection container. If you are starting a new service in 2026 — or maintaining one that already wires dependencies by hand — this comparison tells you exactly which tool fits your situation and, just as important, which one is now a migration risk.

## TL;DR — Quick Verdict

**If you want compile-time safety and are starting a brand-new project, choose Fx** — it is the only one of the three that is both actively maintained and still gaining traction (7,645 stars, last push December 2025). **Choose Wire only if you already have Wire-generated code in production and a plan to fork it** — Google will not fix bugs for you anymore. **Choose dig only if you are building your own framework on top of a DI container** — Fx itself is built on dig, and using dig directly for an application is explicitly discouraged by its own README. If you want zero dependencies and a small codebase, skip all three and keep constructor injection with a `main()` wiring function; Wire's own documentation admits its generated code works fine hand-written.

## Comparison Table — Wire vs Fx vs dig (live GitHub data, 2026-08-27)

| Dimension | google/wire | uber-go/fx | uber-go/dig |
|---|---|---|---|
| GitHub stars | 14,406 | 7,645 | 4,497 |
| License | Apache-2.0 | MIT | MIT |
| Last push | 2025-08-22 | 2025-12-27 | 2025-05-13 |
| DI mechanism | Compile-time code generation | Runtime reflection container + app framework | Runtime reflection container |
| Version promise | v0.x (beta status declared) | v1, strict SemVer | v1, strict SemVer |
| Main maintainer | Google (unmaintained) | Uber | Uber |
| Error detection | At `wire generate` time (compile) | At startup, with structured error paths | At startup, with path traces |
| Lifecycle management | None (plain `main()` calls) | `fx.Lifecycle` hooks, graceful shutdown | None |
| Code generation step | Required (`wire generate`) | Not required | Not required |
| Startup reflection cost | Zero (generated code) | Moderate | Moderate |
| Best for | One-shot DI at binary init | Whole application assembly | Frameworks, containers, plugins |
| **Status 2026** | **Deprecated — no longer maintained** | Active | Active |

## Scenario Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| New production service, need DI without reflection overhead | **Fx** | Maintained, battle-tested at Uber, no codegen step |
| You already have Wire-generated code in production | **Wire (fork) or Fx migration** | Google stopped maintenance; plan a fork or an incremental migration |
| Building a library or framework that needs a container | **dig** | It is the low-level container Fx itself uses |
| Tiny service, 5–10 dependencies, team is new to Go | **None — hand-wired `main()`** | Constructor injection is idiomatic; DI tools add a layer you do not need |
| Strict dependency on compile-time validation | **Wire (forked) or fx + unit tests** | Wire is the only compile-time option, but it is unmaintained |

## google/wire — Compile-Time Code Generation (But Unmaintained)

Wire's philosophy is unique in the Go ecosystem: instead of a runtime container, it reads your `wire.Build()` provider sets and **generates plain Go code** at build time. The generated `wire_gen.go` file contains explicit constructor calls — no reflection, no interfaces, no global state. Install it with:

```bash
go install github.com/google/wire/cmd/wire@latest
```

A minimal provider set looks like this:

```go
//go:build wireinject
// +build wireinject

package main

import "github.com/google/wire"

func InitializeServer() *Server {
    wire.Build(NewConfig, NewLogger, NewServer)
    return nil // wire ignores the return value
}
```

You then run `wire generate ./...` in the module, and Wire produces `wire_gen.go` with the plain constructor calls spelled out. The appeal is obvious: if a provider's dependencies are missing, the generator fails with a compile error instead of a runtime panic.

**The problem in 2026:** the README now states, verbatim: *"This project is no longer maintained. If you wish to update or extend wire, please do so in a fork."* Version 0.3.0 was declared "feature complete" and the project has been in maintenance limbo since; the deprecation banner just makes it official. Newer Go versions, generics, and toolchain changes are not being tracked. If your module already depends on Wire, pin the version, fork the repository, or budget for a migration — do not start a new project on it today.

## uber-go/fx — The Application Framework Approach

Fx treats dependency injection as one part of a larger problem: assembling an application from modules, managing lifecycle, and shutting down cleanly. It is built on top of dig, and its README lists the benefits it brings: eliminating globals (`init()` functions), enabling code reuse across teams, and being "the backbone of nearly all Go services at Uber."

```bash
go get go.uber.org/fx@v1
```

A typical Fx application looks like this:

```go
package main

import (
    "go.uber.org/fx"
    "go.uber.org/zap"
)

func main() {
    app := fx.New(
        fx.Provide(NewConfig),        // constructor -> type
        fx.Provide(NewLogger),        // depends on *Config
        fx.Provide(NewHTTPServer),    // depends on *Logger
        fx.Invoke(func(srv *HTTPServer) {
            srv.Start()
        }),
        fx.NopLogger,                 // quiet mode for tests
    )
    app.Run()
}
```

Fx resolves the dependency graph at startup, and if a provider is missing or ambiguous it fails with a path trace that shows exactly which constructors were involved. It also provides `fx.Lifecycle` hooks (`OnStart` / `OnStop`) so your HTTP server, database pool, and background workers get deterministic startup order and graceful shutdown — something neither Wire nor raw dig give you.

The trade-off: Fx is opinionated. It wants to own your `main()` function, it introduces reflection at startup, and its error messages, while good, are not compile-time. For a small service you may find the framework overhead unnecessary — which is exactly what dig's README warns about when it says dig is "bad for using in place of an application framework."

## uber-go/dig — The Low-Level Reflection Container

dig is the foundation Fx stands on. It is a small, focused dependency injection container: you provide constructors, ask for values, and dig resolves the graph — including named values and parameter groups for slice-style dependencies.

```go
package main

import (
    "go.uber.org/dig"
)

func main() {
    c := dig.New()

    // Provide a constructor for *Config
    c.Provide(func() *Config { return loadConfig() })

    // Provide *Logger, depending on *Config
    c.Provide(func(cfg *Config) *Logger { return NewLogger(cfg) })

    // Invoke a function with resolved dependencies
    c.Invoke(func(logger *Logger) {
        logger.Info("container resolved")
    })
}
```

dig's README is unusually honest about scope. It is "good for: powering an application framework (e.g. Fx)" and "resolving the object graph during process startup." It is "bad for: using in place of an application framework" and "resolving dependencies after the process has already started." If you find yourself reaching for dig directly in an application, the maintainers would rather you use Fx. dig shines where you are building something like a plugin loader, a command dispatcher, or a test harness that assembles objects on demand.

## Pitfalls and Migration Guide

- **Do not start new projects on Wire.** The deprecation banner is the official word. If you need compile-time DI, fork Wire (the maintainers explicitly bless this) and track Go releases yourself, or pin the last version and accept the risk.
- **Wire + generics is awkward.** Wire predates Go 1.18 generics; provider functions that return generic types or that use type parameters can produce confusing generator errors. This is a growing problem as more libraries adopt generics.
- **dig is not a service locator.** The README explicitly warns against exposing the container to user-land code. Handing `*dig.Container` around your codebase turns invisible dependencies into runtime surprises and makes static analysis useless.
- **Reflection costs are real at scale.** Both Fx and dig pay a startup cost to walk the graph. For a CLI tool that must boot in milliseconds this matters; for a long-running server it is noise. Benchmark your startup, do not guess.
- **Fx lifecycle ordering is deterministic but subtle.** `OnStart` hooks run in registration order and `OnStop` hooks run in reverse. Registering a database pool's `OnStart` after the HTTP server's means your server can accept requests before the pool is ready.
- **Migrating from Wire to Fx is incremental.** Wire-generated files are plain constructor calls, so you can move one component at a time into an `fx.Provide` block while the rest of `main()` stays hand-wired. Run both side by side during the transition and delete `wire_gen.go` last.
- **Pin your dependency versions.** Uber's v1 SemVer promise means no breaking changes before v2, but the Go toolchain moves faster than either project's release cadence. Use `go mod tidy` and review upgrades in CI, especially for Fx which pulls in a dozen transitive dependencies.

DI is only one piece of the Go service puzzle. Pair your wiring choice with a solid framework — our [Go web framework comparison](../2026-07-06-go-web-frameworks-gin-echo-fiber-chi/) covers Gin, Echo, Fiber and chi — and read our [Go testing frameworks guide](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/) before you write your first test. Teams migrating legacy services should also study how [Go error handling libraries](../2026-07-24-go-error-handling-pkg-errors-cockroachdb-stdlib-guide/) evolved, because the same "pick the maintained option" logic applies there.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Dependency Injection in 2026: Wire vs Fx vs Dig — Which One Should You Actually Use?",
  "description": "Compare google/wire, uber-go/fx and uber-go/dig for dependency injection in Go. Live GitHub stats, code examples, migration guide and the 2026 google/wire deprecation warning.",
  "datePublished": "2026-08-27",
  "dateModified": "2026-08-27",
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

**Is google/wire still safe to use in production?** The project is no longer maintained — Google's README says so explicitly. The last version works, but you will not get bug fixes or Go toolchain updates. Fork it, pin it, or migrate.

**What is the difference between fx and dig?** dig is a bare reflection-based container for resolving an object graph. Fx is an application framework built on dig that adds lifecycle management, module organization, and graceful shutdown. Use dig only if you are building your own framework.

**Does Go even need a dependency injection framework?** For small services, no — constructor injection with a hand-written `main()` is idiomatic and what most of the standard library does. DI frameworks pay off when you have dozens of components, cross-team shared modules, or a need for deterministic lifecycle ordering.

**Which Go DI tool has the best performance?** Wire generates plain code with zero runtime overhead. Fx and dig use reflection at startup; the cost is proportional to graph size and is typically negligible for servers but measurable for short-lived CLI tools.

**How do I migrate from Wire to Fx?** Component by component. Wire's generated code is explicit constructor calls, so each provider can move into an `fx.Provide()` call independently. Keep both in place during the transition, then delete `wire_gen.go` and the `wire` dependency.

**Are there alternatives to Wire, Fx and dig worth watching?** The manual approach — constructor injection with explicit `main()` wiring — remains the most popular answer in the Go community. Among frameworks, Fx dominates. For compile-time DI, community forks of Wire exist but none have reached critical mass yet.

**Does Fx work with gRPC, HTTP servers and database pools?** Yes. Fx is framework-agnostic: any constructor that returns a value can be provided, and `fx.Lifecycle` gives you OnStart/OnStop hooks to start gRPC listeners, open database pools, and coordinate graceful shutdown. Uber runs it across nearly all its Go services.

**How do I test code that uses Fx or dig?** Fx supports `fx.NopLogger` and test-friendly options like `fx.Replace` to swap real providers for fakes. dig containers can be constructed in tests with test doubles provided the same way as production code, and `dig.Visualize` can export the graph for debugging.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
