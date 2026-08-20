---
title: "Go Template Engines in 2026: pongo2 vs fasttemplate vs quicktemplate — Which One Should You Use?"
date: "2026-08-20"
tags: ["golang", "templating", "performance", "web-development"]
draft: false
cover: "/img/screenshots/pongo2-cover.jpg"
---

Go's standard `text/template` renders a trivial page in **3,333 ns with 19 heap allocations** — fast enough for a request path, ruinous for a hot loop that renders the same snippet a million times. The Go ecosystem splits template engines into two camps: **Django-style logic templates** for application views, and **zero-allocation substitution engines** for performance-critical output. pongo2, fasttemplate, and quicktemplate represent all three philosophies, and choosing wrong means either fighting the syntax or leaving 10× performance on the table. Here is the 2026 decision.

## TL;DR

**If you need logic and filters in your templates, use pongo2** — it is the only one of the three with Django-style control flow, and it is MIT-licensed and maintained (last commit May 2026). **If you need the absolute fastest string substitution on a hot path, use fasttemplate** — 383 ns/op with zero allocations, but it has no loops, no conditionals, and has been stale since 2023. **If you need compile-time-checked, zero-allocation templates with logic, use quicktemplate** — it generates Go code from `.qtpl` files and is the best of both worlds, at the cost of a code-generation step in your build.

## Quick Comparison Table

| Dimension | pongo2 | fasttemplate | quicktemplate |
|---|---|---|---|
| GitHub repo | flosch/pongo2 | valyala/fasttemplate | valyala/quicktemplate |
| Stars | 3,082 | 912 | 3,325 |
| Last commit | 2026-05 | 2023-08 (stale) | 2024-07 |
| Syntax style | Django (`{% %}`/`{{ }}`) | Custom delimiters | Custom `.qtpl` |
| Logic support | ✅ loops, if, macros, filters | ❌ pure substitution | ✅ loops, if, funcs |
| Auto-escaping | ✅ (autoescape on) | ❌ none | ❌ none (you escape) |
| Memory allocations | low | **zero** | **zero** |
| Render speed | fast | **383 ns/op** | **~200 ns/op** |
| Compile-time checking | runtime parse | runtime parse | ✅ generated code |
| Codegen step | none | none | `qtc` required |
| Used by | community projects | VictoriaMetrics | VictoriaMetrics |
| License | MIT | MIT | MIT |

## Decision Matrix

| Use case | Recommendation | Why |
|---|---|---|
| View layer with loops/conditionals/filters | **pongo2** | Django syntax, filters, macros, and sandboxing — closest to a full engine |
| Hot loop, tiny repeated snippets | **fasttemplate** | Zero allocations, custom delimiters, dead simple API |
| High-throughput API with logic needed | **quicktemplate** | Compile-time errors + zero allocs + real control flow |
| Generate HTML with user input | **pongo2 (autoescape) or stdlib** | fasttemplate/quicktemplate do not escape output — XSS risk without manual escaping |
| Existing text/template migration, perf-critical | **quicktemplate** | Same mental model, generated code instead of reflection |
| Build pipeline must stay simple | **pongo2 or fasttemplate** | No code generation step |

## pongo2 — The Django-Style Engine for Go

pongo2 brings Django/Jinja2 template semantics to Go: `{% if %}`, `{% for %}`, `{% macro %}`, filters like `|capfirst`, template inheritance, and sandboxing. It is the right tool when your templates are written by people who think in Django, and when you need real presentation logic without scattering it through Go code.

```sh
go get -u github.com/flosch/pongo2/v7
```

A template with logic, straight from the project README:

```django
{% macro user_details(user, is_admin=false) %}
<div class="user_item">
  <h2 {% if (user.karma>= 40) || (user.karma > calc_avg_karma(userlist)+5) %} class="karma-good"{% endif %}>
    {{ user }}
  </h2>
</div>
{% endmacro %}
```

Rendering is a two-step parse-then-execute, so you compile once and reuse:

```go
// Compile the template first (i.e. creating the AST)
tpl, err := pongo2.FromString("Hello {{ name|capfirst }}!")
if err != nil {
    panic(err)
}
// Render with the given context as often as you want
out, err := tpl.Execute(pongo2.Context{"name": "florian"})
if err != nil {
    panic(err)
}
```

pongo2 supports template sets with filesystem loaders, template inheritance via `{% extends %}`, automatic caching, and a security-focused `sandbox` mode that restricts access to dangerous Go functions. Its autoescape is on by default, which makes it the only one of the three safe to feed user-generated content without thinking. Performance is solid for a runtime engine — you pay a parse step and map-based context lookups, but that is invisible next to typical I/O.

## fasttemplate — The Zero-Allocation Substitution Engine

fasttemplate is a deliberately tiny engine: it replaces `{{placeholder}}` tags in a string with values from a map or a callback. **No loops. No conditionals. No filters. No escaping.** What it does instead is render at 383 ns/op with zero heap allocations — 8.7× faster than `text/template` on the maintainer's own benchmarks:

```text
BenchmarkFmtFprintf-4                     2000000   790 ns/op    0 B/op    0 allocs/op
BenchmarkStringsReplace-4                  500000  3474 ns/op 2112 B/op     14 allocs/op
BenchmarkTextTemplate-4                    500000  3333 ns/op  336 B/op     19 allocs/op
BenchmarkFastTemplateExecute-4            3000000   383 ns/op    0 B/op     0 allocs/op
BenchmarkFastTemplateExecuteFunc-4        5000000   349 ns/op    0 B/op     0 allocs/op
```

Basic usage with configurable delimiters:

```go
template := "http://{{host}}/?q={{query}}&foo={{bar}}{{bar}}"
t := fasttemplate.New(template, "{{", "}}")
s := t.ExecuteString(map[string]interface{}{
    "host":  "google.com",
    "query": url.QueryEscape("hello=world"),
    "bar":   "foobar",
})
fmt.Printf("%s", s)

// Output:
// http://google.com/?q=hello%3Dworld&foo=foobarfoobar
```

For dynamic values, `ExecuteFuncString` hands each tag to a callback:

```go
template := "Hello, [user]! You won [prize]!!! [foobar]"
t, err := fasttemplate.NewTemplate(template, "[", "]")
if err != nil {
    log.Fatalf("unexpected error when parsing template: %s", err)
}
s := t.ExecuteFuncString(func(w io.Writer, tag string) (int, error) {
    switch tag {
    case "user":
        return w.Write([]byte("John"))
    case "prize":
        return w.Write([]byte("$100500"))
    default:
        return w.Write([]byte(fmt.Sprintf("[unknown tag %q]", tag)))
    }
})
```

fasttemplate powers VictoriaMetrics, where it renders thousands of metric labels per second. The catch is maintenance: the repo has had no commits since **August 2023**, so treat it as frozen-stable — it is a solved problem that does not need updates, but do not expect new features or Go-version-specific fixes.

## quicktemplate — Compile-Time Templates With Zero Allocations

quicktemplate takes the opposite architectural bet from the other two: **templates are compiled to Go code at build time** by the `qtc` generator. Instead of parsing strings at runtime, you get real Go functions — with compile-time type errors, full debugger support, and zero allocations because every string is written straight into a buffer. It is the fastest engine in this comparison and the safest to refactor, because a typo in a template fails the build instead of the request.

Write a template in `templates/hello.qtpl`:

```go
{% func Hello(name string) %}
Hello, {%s name %}!
{% endfunc %}
```

Run the generator, then call the generated function:

```go
package main

import (
    "fmt"

    "./templates"
)

func main() {
    fmt.Printf("%s\n", templates.Hello("Foo"))
    fmt.Printf("%s\n", templates.Hello("Bar"))
}
```

The `qtc` codegen also produces `Write*` variants that accept an `io.Writer`, which is where the zero-alloc wins come from — output streams straight into an `http.ResponseWriter` or `bytes.Buffer`:

```go
package main

import (
    "bytes"
    "fmt"

    "./templates"
)

func main() {
    names := []string{"Kate", "Go", "John", "Brad"}

    // qtc creates Write* function for each template function.
    var buf bytes.Buffer
    templates.WriteGreetings(&buf, names)

    fmt.Printf("buf=\n%s", buf.Bytes())
}
```

quicktemplate's control flow (`{% for %}`, `{% if %}`), its `{% code %}` blocks for arbitrary Go expressions, and its mandatory `qtc` step make it the most powerful option here — but also the one with the most moving parts. It is also the only one that lets you preview templates with syntax highlighting (the generator ships a `-ext` flag for `.qtpl.html` files) and the only one whose templates are type-safe by construction.

## Pitfalls and Traps When Picking a Go Template Engine

1. **fasttemplate is not a template engine.** Newcomers reach for it and then discover it cannot loop or branch. If you need logic, quicktemplate (same author, same zero-alloc philosophy) is the upgrade path — not a pile of string concatenation.
2. **No autoescaping outside pongo2.** fasttemplate and quicktemplate write raw strings into the output. Feeding user input into either without `html/template`-style escaping or an explicit `html.EscapeString` produces stored XSS. This is the single most common security misconfiguration with these libraries.
3. **quicktemplate changes your build.** `go build` alone will fail on `.qtpl` files until `qtc` has generated the `.go` outputs. Commit the generated files or wire `qtc` into your CI; forgetting either breaks the build for every contributor.
4. **fasttemplate is frozen (2023).** It is stable and used in production by VictoriaMetrics, but "stable" here means "no fixes will arrive". If you need a new Go version guarantee, prefer quicktemplate or pongo2, both of which have recent activity.
5. **Benchmark claims need context.** The 383 ns/op figure is for a pre-parsed template executed against a small map. Your real workload — big templates, `ExecuteFuncString` callbacks, buffered writes — will differ. Re-run the benchmarks on your own shapes before betting an architecture on them.
6. **pongo2 parse errors are runtime errors.** Unlike quicktemplate, a bad template is only discovered when `FromString`/`FromFile` executes. Wrap template compilation at startup (fail fast) instead of per-request.
7. **Context map allocation defeats the purpose.** With fasttemplate/quicktemplate, build your `map[string]interface{}` (or function arguments) outside the hot loop — otherwise the *context* allocation dominates and the zero-alloc template saves nothing.

## Migration and Benchmarking Strategy

Moving from `text/template` or `html/template` to a performance engine is a surgical refactor, not a rewrite:

1. **Find the hot templates first.** Profile with `go test -bench` and `pprof`; in most services only a handful of templates render more than 1,000 times per second. Those are the only ones worth migrating — the rest can stay on the standard library, which has better escaping and ecosystem support.
2. **For pure substitution hot spots, switch to fasttemplate.** The API maps 1:1: `tpl.Execute(w, data)` becomes `t.ExecuteWriter(w, data)`. Keep the template string compiled once at init.
3. **When you need logic too, go straight to quicktemplate.** Port the control-flow templates to `.qtpl`, run `qtc`, and delete the `text/template` parse code. The generated functions fail compilation on type errors, which is a strict upgrade in safety.
4. **Verify with allocation profiling.** Run `go test -bench=. -benchmem` before and after. The goal is not zero — it is "no allocation on the hot path". Anything under one alloc per render is typically fine for a request handler.
5. **Keep escaping explicit.** Whatever you migrate, add a test that renders a string containing `<script>` and assert the output is escaped (or assert the raw output if that is the intended design). This is the regression that silently reopens XSS.
6. **Apply the same profiling discipline to the rest of the stack.** Our [Go HTTP client comparison](../2026-08-17-go-http-client-libraries-resty-vs-fasthttp-vs-req-comparison/) and [Go caching libraries guide](../2026-06-19-self-hosted-cache-libraries-golang-lru-gocache-bigcache-tinylfu/) follow the same pattern — measure the hot path, then pick the tool that eliminates its costs. For keeping the codebase healthy while you change engines, the [Go code-quality tooling guide](../2026-07-23-go-code-quality-tools-golangci-lint-staticcheck-revive-gofumpt-gosec/) shows which linters catch template-escaping mistakes automatically.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Template Engines in 2026: pongo2 vs fasttemplate vs quicktemplate — Which One Should You Use?",
  "description": "Comparison of Go template engines: pongo2 (Django syntax), fasttemplate (zero allocations), and quicktemplate (code generation) with benchmarks, security trade-offs, and migration strategy.",
  "datePublished": "2026-08-20",
  "dateModified": "2026-08-20",
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

### Is fasttemplate safe to use with user-generated content?
Not by itself. fasttemplate performs pure string substitution with no output escaping — `{{name}}` renders exactly what you give it. Any user-controlled value must be escaped explicitly (`html.EscapeString` for HTML output) before substitution, or you will introduce stored XSS. pongo2 is the only engine here with autoescaping enabled by default.

### Does quicktemplate require a code-generation step?
Yes. You write templates in `.qtpl` files and run the bundled `qtc` generator, which produces plain `.go` files with a function per template. Those generated files must be committed or regenerated in CI — `go build` does not understand `.qtpl` directly. The payoff is compile-time type checking and zero-allocation rendering.

### Which Go template engine is the fastest?
By the maintainers' own benchmarks, quicktemplate and fasttemplate are the fastest — both render in the low hundreds of nanoseconds per operation with zero heap allocations, roughly an order of magnitude faster than `text/template`. pongo2 is fast for a runtime engine but cannot compete because it parses and interprets at runtime. For absolute numbers, benchmark on your own template shapes.

### Can I use these engines alongside html/template?
Yes, and it is common: keep `html/template` for pages that render untrusted input (it autoescapes correctly), and switch only the performance-critical fragments — metric labels, JSON-ish text, cache-busting snippets — to fasttemplate or quicktemplate. The engines are independent packages and compose in the same process.

### Which engine is best maintained in 2026?
pongo2 has the most recent commits (May 2026) and an active issue tracker. quicktemplate's last commit was July 2024. fasttemplate has been frozen since August 2023 — the code is stable and production-proven (VictoriaMetrics uses all three valyala tools), but no new features or fixes should be expected.

### Are pongo2, fasttemplate, and quicktemplate free to use commercially?
Yes — all three are MIT-licensed, so you can use, modify, fork, and redistribute them in commercial and closed-source products without restrictions or attribution obligations beyond preserving the license notice.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
