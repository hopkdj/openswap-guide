---
title: "Embedded Expression Languages in 2026: CEL vs expr-lang vs JSONata vs Starlark"
date: "2026-09-27"
tags: ["expression-languages", "developer-tools", "go", "javascript", "rust", "rule-engines", "json"]
draft: false
cover: "/img/screenshots/jsonata-expression-language-logo.jpg"
description: "CEL, expr-lang, JSONata, Starlark, govaluate and Rhai compared for 2026: which embedded expression language to put in your product so users can write their own rules without waiting for a release, with real code and live star counts."
---

The feature request always arrives the same way: *"can we write our own filter rules without waiting for your release cycle?"* You have two options. Either you build a plugin SDK that nobody adopts because it requires a compiler and a code review, or you embed an expression language and let users write `severity == 'critical' && service in allowed_services`. The second option is a product decision with a security dimension, and the language you pick decides how much of that dimension you have to own.

This comparison covers the six expression engines that are actually deployed in 2026 — **expr-lang/expr (8,029 stars), Rhai (5,697), govaluate (3,929), cel-go (3,112), Starlark (2,774) and JSONata (2,694)** — with live repository data from 2026-09-27 and code from each project's own documentation.

## TL;DR — Quick Verdict

- **User-supplied rules in a Go service**: [CEL](https://github.com/cel-expr/cel-go) (`cel-go`). It is deliberately **non-Turing complete** — no unbounded loops — has gradual typing, and a compiled program is stateless, thread-safe and cacheable. That combination is what you want when the expressions come from customers.
- **Go, with a smaller footprint and a friendly compiler**: [expr-lang/expr](https://github.com/expr-lang/expr). Simpler embedding story, good error messages, built-in `filter`/`map`/`all`. Use it for internal config, CEL for external input.
- **JSON in, JSON out, on the wire or in the browser**: [JSONata](https://github.com/jsonata-js/jsonata). It is a query and transformation language, not a boolean rule language, and `$sum(example.value)` is a one-liner that would be a loop anywhere else.
- **User-authored configuration that needs real logic**: [Starlark](https://github.com/google/starlark-go). Deterministic, no I/O by default, and the language Bazel and Buck have already stress-tested.
- **Rust**: [Rhai](https://github.com/rhaiscript/rhai) for a scripting surface, [evalexpr](https://github.com/ISibboI/evalexpr) if you only ever need one expression evaluated.
- **Do not start new Go work on `govaluate`** — 3,929 stars, but its last commit was 2025-03-25 and `expr-lang/expr` covers the same ground with an actively maintained compiler.

## Live Comparison Table (2026-09-27)

| Engine | Language | Stars | License | Last commit | Turing complete? | Type checking | Best fit |
|---|---|---|---|---|---|---|---|
| expr-lang/expr | Go | **8,029** | MIT | 2026-07-07 | yes (bounded by you) | compile-time with `expr.Env` | internal + service rules |
| Rhai | Rust | **5,697** | Apache-2.0 | 2026-09-23 | yes | dynamic, typed variants available | user scripting in Rust apps |
| govaluate | Go | **3,929** | MIT | **2025-03-25** | no | none (dynamic) | legacy — migrate to expr-lang |
| cel-go | Go | **3,112** | Apache-2.0 | 2026-09-25 | **no** | gradual, static where possible | untrusted user rules |
| starlark-go | Go | **2,774** | BSD-3-Clause | 2026-09-12 | yes | none (dynamic) | user config with logic |
| jsonata | JavaScript | **2,694** | MIT | 2026-09-10 | limited | none (dynamic) | JSON query + transform |
| evalexpr | Rust | **414** | AGPL-3.0 | 2026-09-26 | no | dynamic | single-expression evaluation |

Note the two entries at the top of that table by activity: Rhai and cel-go both shipped commits within the last five days, and both are the maintained options in their niches. The one bolded date in the middle — govaluate — is not broken, it is simply frozen, and its README still describes the API most Go developers remember.

## Decision Matrix

| Your use case | Pick this | Why |
|---|---|---|
| Customer-defined alert conditions | cel-go | Non-Turing complete by design; you cannot be DoS'd by a `while` loop that never ends |
| Internal config file with logic (`if env == "prod"`) | expr-lang/expr | Two functions to embed, and compile errors at start-up rather than runtime |
| Filter/transform a JSON document into another shape | JSONata | The language is a querier: `$sum`, `$map`, path expressions and no boilerplate |
| Build-system-style config that users extend | Starlark | Deterministic, hermetic, no file or network access unless you grant it |
| Feature-flag targeting rules | cel-go or expr-lang | Both compile once and evaluate per request; see the [feature-flag comparison](../2026-04-28-unleash-vs-flagsmith-vs-flipt-self-hosted-feature-flag-management-guide-2026/) for how existing tools model this |
| Embedded scripting inside a Rust application | Rhai | Real language with sandboxing knobs, actively maintained |
| One arithmetic/boolean expression, nothing more | evalexpr | Smallest possible dependency for the smallest possible job |
| Workflow automation with per-node expressions | n8n/Automatisch-style engines | Covered in our [workflow automation comparison](../2026-04-29-automatisch-vs-n8n-vs-activepieces-self-hosted-workflow-automation-2026/) |

## The Engines in Depth

### cel-go — the safe choice for untrusted expressions

CEL (Common Expression Language) exists because Google needed one rule language shared across products. Its defining property is not speed but **the absence of unbounded loops**: CEL is intentionally non-Turing complete, which removes the entire category of "a customer wrote an expression that runs forever."

An environment declares the variables the expression may reference, with types:

```go
env, err := cel.NewEnv(
    cel.Variable("name", cel.StringType),
    cel.Variable("group", cel.StringType),
)
```

That's it. The environment is ready to be used for parsing and type-checking, and after parsing and checking you build a program:

```go
prg, err := env.Program(ast)
if err != nil {
    log.Fatalf("program construction error: %s", err)
}
```

The `cel.Program` generated at the end of parse and check is, in the project's own words, **stateless, thread-safe, and cacheable**. That sentence is the single most important line in the README: it means you parse and check at deploy time (or first use), cache the program per rule, and evaluate it on every request with no locking. Type-checking is optional but strongly encouraged, and it rejects semantically invalid expressions at build time and produces metadata that speeds up later evaluation.

### expr-lang/expr — the pragmatic Go embed

expr is what you reach for when the expressions are yours rather than your customers'. You compile an expression against an environment and then run it:

```go
program, err := expr.Compile(code, expr.Env(env))
if err != nil {
    panic(err)
}

output, err := expr.Run(program, env)
if err != nil {
    panic(err)
}
```

The compile step is where the value is. Because the environment declares types, a mismatched operation fails at compile time with a pointed error rather than at 03:00 in production:

```go
out, err := expr.Compile(`name + age`)
// err: invalid operation + (mismatched types string and int)
// | name + age
// | .....^
```

The standard library includes `all`, `none`, `any`, `one`, `filter` and `map` out of the box, which is why expr feels like a query language more than a calculator: `filter(users, .age > 18)` is one expression, not a hand-rolled loop. Under the hood it is an optimizing compiler plus a bytecode virtual machine, which is the difference between "fine for config" and "fine for the request path".

Practical rule: **use expr for expressions you ship in your own repo, and CEL for expressions your users write.** The security posture of the two is different on purpose.

### JSONata — query and transform, not evaluate

JSONata is a different kind of tool that gets filed under the same heading. It is a query and transformation language for JSON, and its reference implementation is the JavaScript package used by everything from editors to integration platforms:

```bash
npm install jsonata
```

```javascript
const jsonata = require('jsonata');

const data = {
    example: [
        {value: 4},
        {value: 7},
        {value: 13}
    ]
};

(async () => {
    const expression = jsonata('$sum(example.value)');
    const result = await expression.evaluate(data);  // returns 24
})()
```

Read that expression carefully, because it is the whole pitch: `$sum(example.value)` sums a mapped field across an array without an explicit loop, and the same language handles reshaping — select fields, build new objects, group, sort and aggregate. If your requirement is "let users define how to pull metrics out of a JSON payload," JSONata is a better fit than any boolean rule language, and it runs the same in Node and the browser.

Its weakness is the flip side of its flexibility: it is dynamically typed and evaluated, so there is no compile-time check that `example.value` exists. Treat user-authored JSONata the way you treat any dynamic query — with a sandbox and a bounded execution budget.

### Starlark — configuration that is allowed to have logic

Starlark is the language Bazel uses for build files, and its design goals are the ones you want for user-authored configuration: deterministic execution, no implicit I/O, hermetic evaluation and a Python-like syntax that non-programmers can read. The Go implementation embeds in a handful of lines:

```go
// Execute Starlark program in a file.
thread := &starlark.Thread{Name: "my thread"}
globals, err := starlark.ExecFile(thread, "fibonacci.star", nil, nil)
if err != nil { ... }

// Retrieve a module global.
fibonacci := globals["fibonacci"]

// Call Starlark function from Go.
v, err := starlark.Call(thread, fibonacci, starlark.Tuple{starlark.MakeInt(10)}, nil)
if err != nil { ... }
fmt.Printf("fibonacci(10) = %v\n", v) // fibonacci(10) = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

The pattern worth copying is the last three lines: you evaluate a script once to obtain **functions**, then call those functions from your host program. That is how you get user extensions without giving users a socket. If you need a general-purpose embedded language instead, Rhai fills that role for Rust with 5,697 stars and commits this week.

### govaluate — recognise it, then migrate

`govaluate` is still in production in a lot of Go services, and it is worth knowing its shape so you can read the code you inherit:

```go
expression, err := govaluate.NewEvaluableExpression("10 > 0");
result, err := expression.Evaluate(nil);
// result is now set to "true", the bool value.
```

```go
expression, err := govaluate.NewEvaluableExpression("(requests_made * requests_succeeded / 100) >= 90");

parameters := make(map[string]interface{}, 8)
parameters["requests_made"] = 100;
parameters["requests_succeeded"] = 80;

result, err := expression.Evaluate(parameters);
// result is now set to "false", the bool value.
```

The API is pleasant and the semantics are dynamic — no environment, no type checking, parameters supplied as a map. The problem is temporal: last commit 2025-03-25. It still works, and migration is not urgent, but new features (typed environments, compile-time errors, query functions) are arriving in `expr-lang/expr` instead. If you are starting today, start there.

## Pitfalls That Reach Production

**1. Turing completeness is a security property, not a style choice.** Starlark and Rhai can express loops; CEL and govaluate cannot. If end users can submit expressions, a language without unbounded loops is a materially smaller attack surface, and it removes the need for a timeout-plus-thread-kill harness.

**2. Compile once, evaluate many.** `cel.Program` is documented as stateless and thread-safe; expr programs are the same. Parsing per request is the most common performance mistake in embedded-expression code, and it also re-introduces parse errors as runtime 500s instead of start-up failures.

**3. Type checking is the feature you are paying for.** `expr.Env` and CEL's environment give you a compile step that can reject `name + age` when `name` is a string. Deploy-time rejection is the entire difference between a rule engine and a stringly-typed `eval`.

**4. Declare the environment explicitly.** CEL requires variables to be declared with types; expr does too. Undefined variables are errors, not `nil`. This is good, and it means adding a field to your context is a code change you can review — not something a user silently invents.

**5. Numbers are not all floats, but JSON numbers are.** JSONata and JavaScript-backed engines treat numbers as doubles. Large identifiers (payment ids, 64-bit counters) can lose precision when they travel as JSON numbers. Serialise identifiers as strings and compare them as strings.

**6. Missing data is a correctness question, not an error-handling afterthought.** Decide once whether `severity == 'critical'` on a payload without `severity` means false, an error, or an alert. Every engine behaves slightly differently, and the difference shows up in your alert volume.

**7. Expression syntax is a public API.** The moment users save rules, the language is a contract. Renaming a standard function or changing comparison semantics is a breaking change; version your expression dialect and keep a fixture file of saved rules with expected results in your test suite.

**8. Sandbox the host, not just the language.** Even a non-Turing-complete language needs an execution timeout, a memory bound and a ban on unbounded output size. Bound the input size, bound the evaluation, and log the expression that was evaluated alongside the result.

## Where Embedded Expressions Show Up in Self-Hosted Stacks

Expression languages are already inside the software most self-hosters run, which is why the choice matters beyond your own product. Workflow automation platforms build per-node expressions into their editors — the [n8n vs Automatisch vs Activepieces comparison](../2026-04-29-automatisch-vs-n8n-vs-activepieces-self-hosted-workflow-automation-2026/) shows how each exposes them to end users, and it is a good proxy for how much rope a tool hands its operators. Feature-flag platforms compile targeting rules into an evaluation engine and then run them on every request; the [self-hosted flag platform comparison](../2026-04-28-unleash-vs-flagsmith-vs-flipt-self-hosted-feature-flag-management-guide-2026/) covers the operational half of that trade-off.

If your stack also has to *inspect* the JSON these expressions operate on, our [JSON visualisation tools guide](../2026-06-15-self-hosted-json-visualization-tools-jsoncrack-jsonhero-jsoneditor/) is the companion piece: JSONata answers "what does this document reduce to", JSON Crack answers "what shape is this document". Deploying an expression engine itself requires no container of its own — these are libraries compiled into your binary or bundled into your JavaScript — so the whole decision is which semantics you are willing to support for the next three years.

## FAQ

**What is the difference between CEL and expr-lang/expr?**
Both are Go expression engines with a compile step and typed environments. CEL is deliberately non-Turing complete with gradual typing, and its compiled program is documented as stateless and thread-safe — designed for expressions authored by users or other teams. expr uses the same compile-then-run shape with a friendlier standard library (`filter`, `map`, `all`) and no loop restrictions, which suits expressions you ship yourself.

**Is it safe to let end users write expressions?**
Only with a language that cannot loop forever, an explicit environment, an evaluation timeout and a size bound on input. CEL is the mainstream answer because non-Turing completeness is a design property rather than a configuration flag. Never expose a general scripting language to untrusted authors unless you can isolate the runtime, not just the syntax.

**Should I use JSONata or a normal expression language for JSON?**
JSONata if the task is querying and transforming JSON — it maps fields, aggregates with `$sum`, and reshapes documents in one expression. A boolean rule language is a better fit if the output is a yes/no decision on a request. Many products need both, and running JSONata for transforms plus CEL for decisions is a reasonable split.

**Why is govaluate not recommended for new projects?**
Because it has had no commit since 2025-03-25 while the ecosystem moved to typed environments and compile-time checking. Its API still works and existing code is not in danger, but new Go work should start on `expr-lang/expr`, which covers the same use cases with an actively maintained compiler and better diagnostics.

**How do I keep expression performance predictable?**
Compile once per rule and cache the compiled program, evaluate with a prepared context object, and measure the evaluation separately from the surrounding request. If you are re-parsing on every call, you are paying parser cost per request and you will see it as latency long before you see it as CPU saturation.

**Can I use these languages for build or deployment configuration?**
Yes — Starlark is exactly that, and it is why Bazel, Buck and their ecosystem use it. Determinism and the absence of implicit I/O are the properties that make a configuration language safe to evaluate in a build system, and both come from the language design rather than from a sandbox you have to build.

**Do I need a separate service to run an expression engine?**
No. Every engine here is a library: `go get github.com/expr-lang/expr`, `npm install jsonata`, `cargo add rhai`, or a `go get` for `cel-go` and `starlark-go`. Keep rules in your database or config, compile at start-up, and evaluate in-process — a network hop adds failure modes without adding safety.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Embedded Expression Languages in 2026: CEL vs expr-lang vs JSONata vs Starlark",
  "description": "CEL, expr-lang, JSONata, Starlark, govaluate and Rhai compared for 2026: which embedded expression language to put in your product so users can write their own rules without waiting for a release, with real code and live star counts.",
  "datePublished": "2026-09-27",
  "dateModified": "2026-09-27",
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
