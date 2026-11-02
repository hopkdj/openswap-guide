---
title: "Go Dependency Injection in 2026: Wire vs Dig vs Fx — Compile-Time, Runtime, or Framework?"
date: "2026-11-02"
tags: ["go", "dependency-injection", "architecture", "testing"]
draft: false
description: "Wire, Dig and Fx compared for Go in 2026: generated code vs runtime reflection vs full app framework, with real provider code, lifecycle hooks and the pitfalls that bite in production."
---

Go's standard advice used to be "you don't need dependency injection, just pass the struct." Then the service grew to forty constructors, `main.go` became a hand-written wiring diagram eleven screens long, and every new handler needed three edits in three files. That is the moment teams reach for a DI library — and immediately disagree about which one.

The disagreement is real, because the three popular options are not variations on a theme. They solve different problems:

- **`google/wire`** generates the wiring code at build time. Nothing runs at runtime.
- **`uber-go/dig`** resolves the object graph at runtime with reflection.
- **`uber-go/fx`** is `dig` plus an application lifecycle: modules, start/stop hooks, structured logging.

## TL;DR: the verdict

**Pick `wire` when you want zero runtime cost and errors at compile time.** You write providers, run `wire`, and commit a generated `wire_gen.go`. If a dependency is missing, the build fails — not a 2 a.m. panic after deploy.

**Pick `dig` when you need dynamic or config-driven wiring**, or when you are wiring something that is not a plain application entry point: a plugin registry, a test harness that composes different subsets, a multi-tenant worker pool.

**Pick `fx` when you want a framework**, not a container: lifecycle hooks, module boundaries, and a startup log that shows exactly what got constructed. It is the right choice for a long-running server and the wrong choice for a small CLI.

**Do not pick two.** Mixing `wire` with `fx` in one binary means two graphs that can disagree, and the failure shows up as a nil pointer in production.

## Comparison table (live GitHub data, November 2026)

| | **google/wire** | **uber-go/dig** | **uber-go/fx** |
|---|---|---|---|
| Stars | 14,377 | 4,507 | 7,720 |
| Last push | 2025-08-22 | 2025-05-13 | 2025-12-27 |
| Mechanism | Code generation (`wire_gen.go`) | Runtime reflection | Runtime reflection + lifecycle |
| Errors found | Compile time | Runtime (`dig` panics) | Runtime, plus `fx.ValidateApp` |
| Runtime overhead | **None** | Reflection at startup | Reflection + hook orchestration |
| Learning curve | Low (one command) | Low | Medium-high |
| Lifecycle hooks | No | No | **Yes** (`OnStart` / `OnStop`) |
| Modules / scoping | Provider sets | Named values, groups | **`fx.Module`** |
| Best fit | Services, libs, CLIs | Tooling, plugins, tests | Long-running servers |
| Generated files in repo | Yes | No | No |

The star gap reflects age more than quality — `wire` was the default answer for years. The more useful signal is the mechanism column: generation, reflection, or framework.

## Decision matrix

| If this is your situation | Choose | Because |
|---|---|---|
| Monolith with a 300-line `main.go` | `wire` | Generated code is readable and greppable |
| Library or SDK shipped to other teams | `wire` | No reflection, no hidden startup cost |
| CLI that should start in milliseconds | `wire` | No container initialization at all |
| Plugin system loading providers by config | `dig` | Graph built from data, not code |
| Tests that need different dependency subsets | `dig` | Build ad-hoc containers per test |
| HTTP server with DB pools and queues | `fx` | Hook ordering for graceful shutdown |
| Team unfamiliar with DI at all | `wire` | Smallest conceptual surface |

## google/wire: build-time generation

`wire` takes a list of constructors and writes the code you would have written by hand. Two files: the injector declaration and the generated implementation.

```bash
go install github.com/google/wire/cmd/wire@latest
```

```go
// providers.go
package main

import "database/sql"

type Config struct{ DSN string }

type Store struct{ db *sql.DB }
type Service struct {
    store *Store
    cfg   Config
}

func NewConfig() Config                  { return Config{DSN: "postgres://localhost/app"} }
func NewDB(cfg Config) (*sql.DB, error)  { return sql.Open("postgres", cfg.DSN) }
func NewStore(db *sql.DB) *Store         { return &Store{db: db} }
func NewService(s *Store, cfg Config) *Service { return &Service{store: s, cfg: cfg} }
```

```go
// wire.go
//go:build wireinject
// +build wireinject

package main

import "github.com/google/wire"

func InitApp() (*Service, error) {
    wire.Build(NewConfig, NewDB, NewStore, NewService)
    return nil, nil
}
```

Run `wire ./...` and it emits `wire_gen.go` containing the literal construction order, including the `error` from `sql.Open`. The `//go:build wireinject` tag keeps the injector declaration out of normal builds, so the generated file is the only version that compiles into your binary.

Provider sets are how you keep this maintainable as the graph grows:

```go
var StorageSet = wire.NewSet(NewDB, NewStore)
var AppSet = wire.NewSet(StorageSet, NewConfig, NewService)

func InitApp() (*Service, error) {
    wire.Build(AppSet)
    return nil, nil
}
```

The win is that a missing constructor is a **build error with a readable message** naming the type nobody provides. The cost is a generated file in your repository — which is a feature, not a bug: code review shows exactly how the app is wired, and `git diff` on `wire_gen.go` reveals accidental dependency changes.

For structs with many fields, `wire.Struct(new(Server), "*")` fills every field from the graph, and `wire.Bind(new(Notifier), new(*EmailNotifier))` wires interfaces to implementations — which is the pattern that makes `wire` usable with hexagonal architectures.

## uber-go/dig: reflection at startup

`dig` builds the same graph, but at runtime. You register constructors and then invoke a function; `dig` figures out what to pass.

```bash
go get go.uber.org/dig
```

```go
package main

import (
    "log"

    "go.uber.org/dig"
)

func main() {
    c := dig.New()

    must(c.Provide(NewConfig))
    must(c.Provide(NewDB))
    must(c.Provide(NewStore))
    must(c.Provide(NewService))

    if err := c.Invoke(func(s *Service) {
        log.Printf("service ready with %d workers", s.workers)
    }); err != nil {
        log.Fatal(err)
    }
}

func must(err error) {
    if err != nil {
        panic(err)
    }
}
```

`dig` proves its value when the graph is data-driven. Parameter objects request several dependencies at once, and result objects publish several:

```go
type HandlerParams struct {
    dig.In
    Store *Store
    Log   *log.Logger
}

func NewHandler(p HandlerParams) *Handler { return &Handler{store: p.Store, log: p.Log} }
```

Groups solve the plugin case that `wire` handles awkwardly — many implementations of one interface, collected into a slice:

```go
c.Provide(NewEmailNotifier, dig.Group("notifiers"))
c.Provide(NewSlackNotifier, dig.Group("notifiers"))

type NotifierParams struct {
    dig.In
    Notifiers []Notifier `group:"notifiers"`
}
```

That is genuinely hard to express with compile-time generation, because the set is decided by registration order at runtime.

The trade-off is failure mode. `dig` reports a missing dependency as a runtime error when you call `Invoke`, and a constructor panic takes the process down at startup rather than failing a build. In a container with health checks this is survivable; in a library it is unacceptable.

## uber-go/fx: dig plus an application lifecycle

`fx` wraps `dig` and answers the question `dig` ignores: what happens at startup and shutdown?

```bash
go get go.uber.org/fx
```

```go
package main

import (
    "context"
    "net/http"
    "time"

    "go.uber.org/fx"
)

func main() {
    app := fx.New(
        fx.Provide(NewConfig, NewDB, NewStore, NewService, NewHTTPServer),
        fx.Invoke(RegisterRoutes),
        fx.Invoke(StartServer),
        fx.WithLogger(func() fxevent.Logger { return fxevent.NopLogger }),
    )
    app.Run() // blocks, handles SIGINT/SIGTERM
}

func StartServer(lc fx.Lifecycle, srv *http.Server) {
    lc.Append(fx.Hook{
        OnStart: func(ctx context.Context) error {
            go srv.ListenAndServe()
            return nil
        },
        OnStop: func(ctx context.Context) error {
            return srv.Shutdown(ctx)
        },
    })
}
```

Hook ordering is the reason teams adopt `fx`: dependencies start before their dependents and stop in reverse, so the database closes after the HTTP server drains. Writing that by hand in `main.go` is exactly the code people get wrong.

`fx.Module` gives you boundaries with visibility rules, and `fx.Annotate` + `fx.As` wire interfaces without a separate `Provide` line per implementation:

```go
var HTTPServerModule = fx.Module("http",
    fx.Provide(
        fx.Annotate(NewRouter, fx.As(new(http.Handler))),
        NewHTTPServer,
    ),
)

app := fx.New(HTTPServerModule, fx.Provide(NewConfig, NewDB))
```

Always call `fx.ValidateApp` in tests. It builds the graph without running hooks, so a missing provider fails in CI instead of on deploy:

```go
func TestAppWiring(t *testing.T) {
    err := fx.ValidateApp(
        fx.Provide(NewConfig, NewDB, NewStore, NewService, NewHTTPServer),
        fx.Invoke(RegisterRoutes),
    )
    if err != nil {
        t.Fatal(err)
    }
}
```

The cost of `fx` is indirection. A stack trace through an `fx` app has frames from the framework, `dig` reflection, and your constructor, and new team members spend their first week learning what `fx.Invoke` actually does. For a 200-line service, that cost is not repaid.

## Pitfalls worth knowing before you commit

**1. `wire` needs the build tag.** Forgetting `//go:build wireinject` makes the injector compile into your binary and produce nil values at runtime. The generated file must be the only implementation in normal builds.

**2. Regenerating `wire_gen.go` is a manual step.** Nothing in `go build` runs `wire`. Wire it into CI (`wire ./... && git diff --exit-code`) or the graph silently drifts from the code.

**3. `dig` panics on duplicate types.** Two providers returning `*Config` are ambiguous. Use named values (`dig.Name("readonly")`) or distinct types — wrapping a primitive in a named struct is the cleaner fix.

**4. `fx` hook errors abort startup, not shutdown.** An error from `OnStart` stops the app with a partially started graph. Keep `OnStart` hooks minimal and idempotent.

**5. Interface binding is verbose in both.** `wire.Bind`, `fx.Annotate(fx.As(...))`, and a manual `dig` provider all exist because Go's type system cannot express "this satisfies that" at the container level. Budget for it.

**6. Tests are where DI pays for itself.** The point of the container is not `main.go`; it is building a `Service` with a fake store in three lines instead of eleven. If your tests still construct everything by hand, you have added a dependency without collecting the benefit.

## FAQ

**Is Wire still maintained in 2026?**
The repository's last push was in August 2025 and it remains widely used. It needs little maintenance because it generates plain Go code — there is no runtime library to keep in sync with language changes.

**Can I use `wire` and `dig` together?**
You can, but you should not. Two graphs in one binary means two sources of truth, and mismatches surface as nil dependencies at runtime. Choose one per binary.

**Does Dig use reflection at every request?**
No. Reflection happens during `Provide` and `Invoke` at startup. Resolved instances are stored in the container, so request-time lookups are map accesses.

**How do I do graceful shutdown with Dig?**
`dig` has no lifecycle concept; you manage shutdown yourself in `main` or in a `Runner` struct you invoke. If graceful shutdown of many components is a requirement, use `fx`.

**What about generics — do they change the picture?**
Generics make typed containers possible for small cases (`type Container[T any]`), but they do not replace graph resolution across many types. `wire` and `dig` remain the practical options.

**Which one produces better stack traces?**
`wire` — by far. The generated code is ordinary function calls, so a nil pointer points directly at your `wire_gen.go` line. `fx` traces include framework frames and are noticeably harder to read.

## Related reading

For more Go engineering trade-offs, our [Go SQL query builder comparison](../2026-07-27-go-sql-query-builders-squirrel-goqu-dbr-sqlboiler/) covers the layer directly below DI, and the [Go CLI libraries guide](../2026-06-22-go-cli-libraries-cobra-urfave-cli-bubble-tea-promptui/) shows how command wiring interacts with dependency graphs. If you are choosing test tooling for the constructors you are about to write, see the [Go testing frameworks comparison](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Dependency Injection in 2026: Wire vs Dig vs Fx — Compile-Time, Runtime, or Framework?",
  "description": "Wire, Dig and Fx compared for Go in 2026: generated code vs runtime reflection vs full app framework, with real provider code, lifecycle hooks and production pitfalls.",
  "datePublished": "2026-11-02",
  "dateModified": "2026-11-02",
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
