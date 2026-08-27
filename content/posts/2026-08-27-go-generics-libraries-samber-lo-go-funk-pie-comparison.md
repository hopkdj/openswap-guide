---
title: "Go Generics Libraries in 2026: samber/lo vs go-funk vs pie — Which One Should You Actually Use?"
cover: "/img/screenshots/samberlo-cover.jpg"
date: "2026-08-27"
tags: ["go", "generics", "golang", "developer-tools", "library-comparison"]
draft: false
---

Go developers spend an absurd amount of time writing the same five loops: filter a slice, map over it, check if it contains a value, find the first match, sum the results. Before Go 1.18 there was no type-safe way to share that code, so the ecosystem split into two camps: reflection-based helpers that work with any type but panic at runtime, and hand-written per-type functions that are safe but tedious. Generics changed the calculus in 2022 — and by 2026 the landscape has consolidated around three libraries with very different philosophies: **samber/lo** (21,412 stars, a Lodash-style toolbox built on generics), **go-funk** (the reflection-era veteran, now effectively dormant), and **pie** (a focused, type-safe slice-and-map library). Here is how they compare with live repository data and real code, and which one you should reach for in your next module.

## TL;DR — Quick Verdict

**Choose samber/lo** — it is the only one of the three that is both actively maintained (last push August 2026) and comprehensive, with 300+ generic helpers covering slices, maps, channels, tuples and concurrency. **Choose pie if you want a minimal, auditable dependency** with clean chaining via `pie.Of` and nothing beyond slices and maps. **Avoid go-funk for new code** — it is reflection-based, its last push was July 2024, and its own README warns that its helpers "run exclusively on runtime so you must have a good test suite." If you need just one or two operations, consider inlining them: the standard library's `slices` and `maps` packages already cover `Contains`, `Index`, `DeleteFunc` and `Collect`, which removes the dependency entirely.

## Comparison Table — samber/lo vs go-funk vs pie (live data, 2026-08-27)

| Dimension | samber/lo | go-funk | pie |
|---|---|---|---|
| GitHub stars | 21,412 | 4,932 | 2,038 |
| License | MIT | MIT | MIT |
| Last push | 2026-08-24 | 2024-07-24 | 2025-12-22 |
| Requires Go | 1.18+ (generics) | Any (reflection) | 1.18+ (v2) / 1.17 (v1) |
| Mechanism | Compile-time generics | Runtime reflection | Compile-time generics |
| Type safety | Full | None (panics on mismatch) | Full |
| Function count | 300+ (slices, maps, channels, tuples, concurrency) | ~40 (slices, strings, structs) | ~70 slice/map helpers |
| Chaining API | Partial (via `lo.Tuple` / manual) | None | `pie.Of(...)` chainable |
| Error-aware variants | Yes (`FilterErr`, `MapErr`…) | No | No |
| Concurrency helpers | Yes (`lo.Async`, `ChannelDispatcher`) | No | No |
| Performance | Near-handwritten (generics inline) | Reflection overhead | Near-handwritten |
| **Status 2026** | **Active, default choice** | Dormant | Active, minimal |

## Scenario Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Production service needing map/filter/find + concurrency helpers | **samber/lo** | Largest API surface, generics type safety, actively maintained |
| Minimize dependencies in a library you publish | **pie** | Tiny, focused, chainable, no surprises |
| Supporting ancient Go codebases (pre-1.18) | **go-funk** | Only option that works without generics — but pin it and test hard |
| One-off `Contains`/`DeleteFunc` in a small app | **stdlib `slices`/`maps`** | Zero dependencies, already in your toolchain |
| Data pipelines with mixed error handling | **samber/lo** | `FilterErr`/`MapErr`/`Try` variants model fallible steps natively |

## samber/lo — The Lodash of Generics Go

samber/lo describes itself as "a Lodash-style Go library based on Go 1.18+ Generics". Its pitch is breadth with safety: because every helper is a generic function, the compiler checks your element types at build time instead of `reflect` panicking at runtime. A basic filter is exactly what you would write by hand:

```go
package main

import "github.com/samber/lo"

func main() {
    even := lo.Filter([]int{1, 2, 3, 4}, func(x int, _ int) bool {
        return x%2 == 0
    })
    // even == []int{2, 4}
}
```

Where lo pulls ahead of the pack is the error-aware family and the concurrency toolbox — operations that plain generics do not give you for free:

```go
// FilterErr stops at the first error instead of swallowing it
result, err := lo.FilterErr([]int{1, 2, 3, 4}, func(x int, _ int) (bool, error) {
    if x == 3 {
        return false, fmt.Errorf("number 3 is not allowed")
    }
    return x%2 == 0, nil
})
// result == nil, err == "number 3 is not allowed"

// Async runs a function in a goroutine and returns a channel
ch := lo.Async(func() int { return 42 })

// ChannelDispatcher fans a channel out to N consumers
dispatcher := lo.ChannelDispatcher(make(chan int), 3, 10, lo.DispatchingStrategyRoundRobin)
```

The library also provides `lo.Associate`, `lo.GroupBy`, `lo.MapValues`, `lo.Retry`, `lo.Ternary`, and tuple helpers (`lo.T2`/`T3`), which makes it the closest thing Go has to a standard utility belt. Install with `go get github.com/samber/lo@latest`. The trade-off is size and style: with 300+ functions the import surface is big, code-review overhead is real, and some helpers (especially the channel dispatchers and `lo.Retry` with backoff) are more machinery than most services need.

## go-funk — The Reflection-Era Veteran (Dormant)

go-funk was the answer before generics existed. Its README is candid: "go-funk is a modern Go library based on reflect. Generic helpers rely on reflect, be careful this code runs exclusively on runtime so you must have a good test suite." That sentence contains the whole story — flexible, zero-boilerplate, and dangerous without tests.

```bash
go get github.com/thoas/go-funk
```

```go
package main

import "github.com/thoas/go-funk"

func main() {
    // Works on slices, maps and strings alike
    funk.Contains([]string{"foo", "bar"}, "foo") // true
    funk.Contains("foobar", "oba")               // true

    names := []string{"Bob", "Sally", "John"}
    funk.Filter(names, func(name string) bool {
        return len(name) > 3
    }) // []string{"Sally", "John"}
}
```

Because every call funnels through `reflect.ValueOf`, a wrong type argument does not fail at compile time — it panics deep inside the call stack, often far from where the bug lives. The project also has a typesafe section in its godoc, but the headline API is the reflection one. The bigger issue in 2026 is maintenance: the last push to `thoas/go-funk` was July 2024, meaning it predates Go 1.22's `slices` package improvements and has not seen a release in two years. It still works — reflection APIs rarely break — but you are betting your correctness on a dormant project whose own author documented the runtime risk.

## pie — Small, Type-Safe, Chainable

pie takes the opposite stance to go-funk: minimal surface, maximum type safety, and a chaining API for pipeline-style transformations. Its tagline is "Enjoy a slice!" — a utility library for common operations on slices and maps.

```go
package main

import (
    "fmt"
    "strings"

    "github.com/elliotchance/pie/v2"
)

func main() {
    names := pie.FilterNot([]string{"Bob", "Sally", "John", "Jane"},
        func(name string) bool {
            return strings.HasPrefix(name, "J")
        })
    fmt.Println(names) // "[Bob Sally]"
}
```

For multi-step pipelines, `pie.Of` wraps a slice and exposes chainable methods:

```go
result := pie.Of([]int{3, 1, 4, 1, 5}).
    Filter(func(x int) bool { return x > 2 }).
    Map(func(x int) int { return x * 10 }).
    Sort().
    All() // []int{30, 40, 50}
```

pie v2 requires Go 1.18+ (a v1 branch exists for Go 1.17 and below), and the project is healthy if modest — 2,038 stars, last push December 2025. Its weakness is scope: there is no map-of-slices deep API, no error-aware variants, and no concurrency helpers. When you need `MapErr` or a dispatcher, you will reach for samber/lo anyway. But as a single, auditable dependency for slice-and-map work, it is hard to beat.

## Pitfalls and Migration Guide

- **Reflection helpers panic, generics compile.** If you migrate go-funk code to lo or pie, the first thing you gain is compile-time type checking — bugs that were latent panics become build errors. That alone justifies the migration in most codebases.
- **`funk.Contains` on strings is a trap.** It matches substrings, not whole elements, so `Contains("foobar", "oba")` returns true. If you move to `slices.Contains`, the semantics change — audit every string check during migration.
- **go-funk is dormant, not dead.** It still compiles on current Go versions, but there have been no releases since 2024. Do not add it to new projects; if you depend on it, pin the version and add a fork-ready escape hatch in `go.mod`.
- **Generics do not inline everything.** lo and pie generate code per concrete type, which can bloat binary size if you instantiate helpers for dozens of types. The `go build -ldflags="-s -w"` savings usually dwarf this, but measure if your binary size is a hard constraint.
- **Prefer stdlib first.** Go 1.21+ ships `slices` and `maps` in the standard library. `slices.Contains`, `slices.Index`, `slices.DeleteFunc`, `slices.Sort` and `maps.Collect` cover a large share of real needs with zero dependencies. Use a third-party helper library for the long tail, not the basics.
- **Chaining hides allocations.** `pie.Of(...).Filter(...).Map(...)` allocates a new slice at each step. For hot loops processing millions of items, the handwritten single-pass loop still wins; benchmark before you assume.
- **Version discipline.** lo moves fast (frequent minor releases). Adopt a versioned `go.mod` requirement and let Dependabot/Renovate open the upgrade PRs rather than `go get @latest` in production builds.

If you are building a Go service, these helpers will live alongside your web layer and your tests. For the framework side, see our [Go web framework comparison](../2026-07-06-go-web-frameworks-gin-echo-fiber-chi/); for keeping that helper-heavy code honest, the [Go testing frameworks guide](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/) covers testify, GoConvey and Ginkgo. And when you validate the structs your pipelines produce, our [Go validation libraries guide](../2026-06-22-go-validation-libraries-goplayground-ozzo-govalidator-guide/) compares go-playground/validator, ozzo-validation and govalidator.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Generics Libraries in 2026: samber/lo vs go-funk vs pie — Which One Should You Actually Use?",
  "description": "Compare samber/lo, go-funk and pie for generic functional helpers in Go. Live GitHub stats, real code examples, reflection vs generics trade-offs and migration guidance.",
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

**Is samber/lo production-ready?** Yes. It is the most popular generics utility library for Go (21,412 stars), actively maintained (pushed August 2026), MIT-licensed, and used in production by many teams. Its helpers are generic functions compiled per type, so there is no runtime reflection.

**What is the difference between go-funk and samber/lo?** go-funk is built on runtime reflection and works with any type without generics, at the cost of type safety and performance. samber/lo uses Go 1.18+ generics, giving compile-time type checks and near-handwritten performance. go-funk's last push was July 2024, so lo is the recommended choice for new code.

**Does pie work with Go versions before 1.18?** pie v2 requires Go 1.18+ for generics. A v1 branch supports Go 1.17 and below. If you are stuck on an old toolchain, go-funk is the only generic-friendly option of the three, but pin it and test thoroughly.

**Are these libraries mutually exclusive?** No. Many projects use pie or stdlib for simple slice operations and samber/lo for the long tail (error-aware variants, concurrency helpers, tuples). They are small, MIT-licensed dependencies that compose fine.

**Does the standard library replace these libraries now?** Partially. Go 1.21+ ships `slices` and `maps` packages covering Contains, Index, DeleteFunc, Sort and Collect. For those operations, the stdlib is the best answer. The third-party libraries win on breadth: grouping, chaining, error-aware filters, and concurrency helpers do not exist in the stdlib.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
