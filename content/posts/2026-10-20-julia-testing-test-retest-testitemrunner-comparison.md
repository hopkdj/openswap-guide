---
title: "Test.jl vs ReTest.jl vs TestItemRunner.jl in 2026: How to Stop Waiting 4 Minutes for One Test"
date: "2026-10-20"
description: "Julia testing compared: the Test stdlib, ReTest.jl (testset filtering, shuffling, deferred tests) and TestItemRunner.jl (test items, editor integration, parallel runs). Real code, CI setup and migration notes."
tags: ["julia", "testing", "developer-tools", "ci-cd", "quality-assurance"]
draft: false
cover: "/img/screenshots/julia-testing-logo.jpg"
---

Julia's standard testing story is deceptively simple: put a `runtests.jl` in `test/`, wrap everything in `@testset`, and run `Pkg.test()`. It works, it is in the standard library, and it is what the vast majority of packages ship. It is also the reason a one-line change in a helper function makes you sit through a four-minute suite that recompiles half the dependency tree, and why "run only the tests related to what I just changed" has been an open request in the language repository for years.

The ecosystem answered with two very different tools. **ReTest.jl** keeps the Test.jl syntax but adds deferred tests, regex filtering, shuffling and statistics. **TestItemRunner.jl** throws out `runtests.jl` in favour of standalone `@testitem` blocks that an editor, a REPL or CI can run individually and in parallel.

Here is how the three fit together in 2026, with real code and the parts the READMEs do not tell you.

## TL;DR — the two-line decision

- **Your package already has `test/runtests.jl` and you just want faster iteration?** Add **ReTest.jl**, keep your `@testset` blocks, and filter by regex: `retest(MyPkg, r"parser")`.
- **You want to run a single test from your editor, get inline failures, and run items in parallel across processes?** Use **TestItemRunner.jl** with `@testitem` blocks.
- **You are shipping a normal package and only run tests in CI?** Stay on the **Test stdlib**. Adding a framework for a suite that runs once per push is pure overhead.

The important nuance: these are not mutually exclusive. TestItemRunner runs Test.jl macros inside each test item, and ReTest re-exports most of the `Test` API. You can adopt either one without rewriting your assertions — only your test *organisation* changes.

## Comparison at a glance

| Dimension | Test (stdlib) | ReTest.jl | TestItemRunner.jl |
|---|---|---|---|
| Maintainer | JuliaLang (stdlib) | JuliaTesting org | julia-vscode org |
| Current state | Ships with Julia (repo: 49,219 stars) | 112 stars, pushed 2026-09-18 | 101 stars, pushed 2026-09-14 |
| Test unit | `@testset` inside `runtests.jl` | `@testset`, optionally inline in `src/` | `@testitem` in any `.jl` file |
| Run one test by name | No | Yes, `Regex` patterns | Yes, per item in editor or CLI |
| Randomised order | No | Yes, `shuffle = true` | Per-item independence |
| Parallel execution | No (single process by default) | Advertised via `Distributed` | Yes, across worker processes |
| Editor integration | Generic (run file) | REPL-driven workflow | First-class (Testing panel, inline results) |
| Requires `runtests.jl` | Yes | Yes (can call `retest()`) | No |
| Coverage support | `--code-coverage=user` | Via Julia flags | Built into the runner (Julia 1.11+) |
| Learning cost | Zero (you know it already) | Low (drop-in) | Medium (new project layout) |
| Maturity risk | None | Low, small team | Low, but CLI is prerelease |

## Decision matrix

| Your situation | Pick | Why |
|---|---|---|
| Library with a stable suite, tests only in CI | Test | Zero dependencies, `Pkg.test()` just works |
| 800-test suite, you change one module per hour | ReTest | Regex filtering cuts the loop from minutes to seconds |
| Tests that belong next to the code they cover | ReTest | Deferred `@testset` can live in `src/` |
| Multi-language repo where developers expect a Testing panel | TestItemRunner | VS Code discovers items as you type |
| Slow integration tests you want to run in parallel | TestItemRunner | Items are independent by design, runner parallelises them |
| Teaching or debugging a single failing assertion | TestItemRunner | Failure shows expected vs actual inline |
| Monorepo with several packages and shared fixtures | TestItemRunner + `@testmodule` | Shared setup without a global `runtests.jl` |

## Test.jl — the baseline you should not abandon casually

The stdlib `Test` package gives you the macros everyone knows, and it is genuinely good at reporting *nested* failures:

```julia
# test/runtests.jl
using Test
using MyPkg

@testset "MyPkg" begin
    @testset "parsing" begin
        @test MyPkg.parse("42") == 42
        @test MyPkg.parse("3.5") === 3.5
        @test_throws ArgumentError MyPkg.parse("nope")
        @test MyPkg.parse("") === nothing
    end

    @testset "numeric edge cases" begin
        @test MyPkg.mean([1.0, 2.0]) ≈ 1.5
        @test isnan(MyPkg.mean(Float64[]))
        @test_broken MyPkg.mean([Inf, -Inf]) == 0.0   # known limitation
        @test_skip MyPkg.mean(big.(1:10))
    end
end
```

`@test_broken` is the most underrated macro in the language: it records a known failure without breaking the suite, and it starts failing (as "unexpectedly passing") once someone fixes the underlying issue. `@test_logs` and `@test_deprecated` cover logging and deprecation paths, which matters if your package emits warnings that downstream users filter on.

To run it the way CI does:

```bash
julia --project=. -e 'using Pkg; Pkg.test()'
```

`Pkg.test()` builds a temporary environment from the `[extras]`/`[targets]` section of `Project.toml`, so test-only dependencies never leak into the package's real dependency graph:

```toml
[extras]
Test = "8dfed614-e22c-5e08-85e1-65c5234f0b40"

[targets]
test = ["Test"]
```

Where the stdlib model breaks down is scale and ergonomics: there is no supported way to say "run only testsets whose description matches `parser`", and no built-in parallel execution of independent testsets. You either split test files and call them selectively by hand, or you adopt one of the two packages below.

## ReTest.jl — same syntax, better control

ReTest.jl is the least disruptive upgrade. It re-exports `@test`, `@test_throws`, `@test_broken`, `@test_logs` and friends from `Test`, adds its own `@testset` implementation, and gives you a `retest()` entry point with filtering.

```julia
# test/runtests.jl
using ReTest
using MyPkg

@testset "parser" begin
    @test MyPkg.parse("42") == 42
end

@testset "formatter" begin
    @test MyPkg.format(42) == "42"
end

retest()
```

Now the useful part — run only the testsets whose description matches a pattern:

```julia
retest(MyPkg, r"parser")          # only testsets matching /parser/
retest(MyPkg, r"parser"; shuffle = true)   # randomise top-level order
retest(MyPkg; stats = true)       # report per-testset timings
```

Patterns can be strings, regexes or arrays, and `not(...)` negates them, so `retest(MyPkg, not(r"slow"))` is a legitimate way to skip the expensive half of a suite during development. The same filtering applies recursively to submodules, and `Mod => pattern` scopes a pattern to one module when you need finer control.

ReTest's second feature is deferred tests: you can place a `@testset` in a source file next to the function it tests, and it will not execute until `retest()` is called. For code that is not yet organised as a package — analysis scripts, internal tooling — this removes the usual "separate test tree that drifts out of sync" problem.

Two practical caveats:

1. **Version pinning matters.** The 0.4 line requires a recent Julia (1.13+ per its README), so if your CI matrix still covers older runtimes, pin ReTest in a test-only environment rather than adding it to shared dependencies.
2. **Parallelism is not a keyword you can trust blindly.** The README advertises running testsets in parallel via `Distributed`; whether a given suite benefits depends on whether your testsets actually mutate shared state. Start with `shuffle = true` — it exposes inter-test dependencies far more cheaply than parallel runs do.

## TestItemRunner.jl — test items instead of a test tree

TestItemRunner takes the opposite approach: no central `runtests.jl`, no testset hierarchy. A test item is a self-contained block that declares its own name and can be discovered anywhere in the project.

```julia
# test/parser_items.jl
using Test
using MyPkg

@testitem "parses integers" begin
    @test MyPkg.parse("42") == 42
    @test MyPkg.parse("-7") == -7
end

@testitem "rejects junk" begin
    @test_throws ArgumentError MyPkg.parse("nope")
    @test MyPkg.parse("") === nothing
end
```

Shared setup goes in a `@testmodule`, which is instantiated per test item and avoids the "global mutable fixture" pattern that makes test order matter:

```julia
@testmodule Fixtures begin
    using MyPkg
    const SAMPLE = MyPkg.load_fixture("sample.csv")
end

@testitem "loads the sample fixture" setup = [Fixtures] begin
    @test length(Fixtures.SAMPLE) == 100
end
```

From there, discovery is handled for you:

- **In VS Code**, the Testing panel scans every `.jl` file as you type and shows each item with an inline run button; failures display expected versus actual values in the editor.
- **In the REPL and CI**, the same items run through the project's test runner; the command-line runner (currently prerelease) discovers items under a folder, filters by name, runs them in parallel worker processes and can emit machine-readable results.
- **Configuration** lives in `JuliaTestItems.toml`, which controls which files are searched — essential in a monorepo where you do not want every vendored dependency scanned.

The parallel model is the real payoff for large suites. Because each item is independent and gets its own process, 40 items across 8 workers finishes in roughly the time of the slowest 5. That is a structural improvement the stdlib cannot give you, since `@testset` blocks in one file share one process and one global state.

The cost is a different mental model: items cannot share mutable state (by design), setup must be declared explicitly, and a package with an existing deeply nested `runtests.jl` needs a real migration rather than a one-line change. Also budget for the maturity gap — the CLI runner is prerelease, so keep `Pkg.test()` working as the fallback path in CI.

## Pitfalls and migration notes

**1. Failures inside a `@testset` do not fail the process by default.** `Pkg.test()` returns an error for a failing testset, but if you run `runtests.jl` directly with `julia test/runtests.jl`, a failing `@testset` prints a summary and exits 0. CI then goes green on a broken suite. Either use `Pkg.test()` or check the testset result explicitly.

**2. Test order dependence is the most common hidden bug.** The stdlib runs testsets in file order, so shared mutable fixtures appear to work. Turning on `shuffle = true` in ReTest, or splitting into test items, usually surfaces two or three genuinely order-dependent tests within the first run. Fix them, do not disable shuffling.

**3. `@test a ≈ b` needs the tolerance you think it has.** The default `≈` uses `rtol = √eps`, which is far too loose for some numerical work and too tight for iterative solvers. Pass explicit tolerances: `@test x ≈ y rtol = 1e-10`.

**4. Precompilation dominates small test runs.** A filtered run that takes 3 seconds of actual testing still pays 20-60 seconds of compilation. Use a persistent Julia session (the REPL, or the editor's test integration) instead of spawning `julia` per run — that alone is usually a bigger win than any filtering.

**5. Coverage and filtering interact badly.** `--code-coverage=user` with a filtered subset produces a coverage report that looks alarming because most of the package was never executed. Only measure coverage on full runs.

**6. Do not mix runners in one package.** A repo with both a `runtests.jl` and a set of `@testitem` blocks will happily run both in some configurations and neither in others, depending on which entry point CI calls. Pick one entry point and document it in the README.

For the surrounding tooling, our [Julia development toolchain comparison](../2026-09-13-julia-development-toolchain-juliaup-pkg-revise-comparison/) covers `juliaup`, `Pkg` and `Revise` — the last one is what makes REPL-driven test loops feel instant. If your tests operate on tabular data, the [Julia DataFrames vs TidierData comparison](../2026-10-16-julia-dataframes-tidierdata-dataframesmeta-comparison/) shows which API changes break test fixtures most often, and cross-language readers may enjoy the [Perl testing frameworks comparison](../2026-10-20-perl-testing-test2-vs-test-more-vs-test-deep/) for a very different take on the same problem.

## FAQ

### Can I use ReTest.jl without rewriting my tests?

Yes. ReTest re-exports the `Test` macros, so switching usually means changing `using Test` to `using ReTest` and adding a `retest()` call at the end of your runner. Assertions themselves are unchanged.

### Does TestItemRunner.jl replace `Pkg.test()`?

No. Test items still execute under the package's test environment, and `Pkg.test()` remains the canonical CI entry point for many projects. TestItemRunner adds discovery, per-item execution and parallelism on top of the same assertion macros.

### How do I run a single test in Julia without a framework?

There is no supported way to select a single `@testset` by name in the stdlib. The practical options are extracting that test into its own file and `include`-ing it, or adopting ReTest (regex filtering) / TestItemRunner (per-item runs).

### Are these tools fast enough for large suites?

Filtering and per-item parallelism cut wall-clock time significantly, but precompilation is usually the dominant cost on small runs. Keep a warm session (REPL or editor integration) for development loops, and reserve cold `Pkg.test()` runs for CI.

### Which one should a new Julia package use in 2026?

Start with the `Test` stdlib — it is zero-cost and universally understood. Add TestItemRunner when you want editor-driven, parallel test items, or ReTest when your suite is large enough that filtering by description changes how you work. Adding either later is cheap; adding both is a maintenance trap.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Test.jl vs ReTest.jl vs TestItemRunner.jl in 2026: How to Stop Waiting 4 Minutes for One Test",
  "description": "Comparison of Julia testing tools: the Test standard library, ReTest.jl for testset filtering and shuffling, and TestItemRunner.jl for parallel test items with editor integration.",
  "datePublished": "2026-10-20",
  "dateModified": "2026-10-20",
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
