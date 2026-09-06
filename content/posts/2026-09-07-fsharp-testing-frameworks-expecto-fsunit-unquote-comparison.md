---
title: "F# Testing in 2026: Expecto vs FsUnit vs Unquote — Which One Should You Actually Use?"
date: "2026-09-07"
tags: ["fsharp", "dotnet", "testing", "unit-testing", "libraries"]
draft: false
---

F# gives you a type system that eliminates entire bug classes — and then the language's own testing ecosystem quietly fragments into three philosophies that are easy to confuse. **Expecto** (740 stars) is a full standalone test runner where tests are *values* you compose like data. **FsUnit** (445 stars) is not a runner at all — it is an assertion language that makes NUnit, xUnit, or MSTest feel functional. **Unquote** (298 stars) replaces assertions with F# *quoted expressions* that print step-by-step failure evaluations. Pick the wrong one for your project and you either fight your IDE's test explorer, surrender F#'s expressiveness to C#-style attributes, or lose the readable failure messages that make F# tests worth writing.

## TL;DR — Quick Verdict

**Starting a fresh F# library and want zero ceremony plus built-in property and stress testing? Use Expecto** — write tests as values, run them from a console entry point, get parallelism for free, and reach for its FsCheck integration when examples are not enough. **Already standardized on NUnit or xUnit in a mixed C#/F# codebase and need the IDE test explorer, CI adapters, and team conventions to keep working? Use FsUnit** — it layers `should` syntax onto your existing framework instead of replacing it. **Writing assertions that deserve forensic failure messages — complex list transformations, string manipulation, boundary logic? Add Unquote** — `test <@ ... @>` decompiles the expression and shows every reduction step when it fails, and it drops into any exception-based runner with zero configuration.

## Quick Comparison Table

| | Expecto | FsUnit | Unquote |
|---|---|---|---|
| Primary role | Full test framework + runner | Assertion syntax for NUnit/xUnit/MSTest | Quoted-expression assertion engine |
| Repo / stars | `haf/expecto` — 740⭐ | `fsprojects/FsUnit` — 445⭐ | `SwensenSoftware/unquote` — 298⭐ |
| License | Apache-2.0 | MIT | Apache-2.0 |
| Last push | 2026-06-17 | 2025-07-11 | 2024-12-01 |
| Test discovery | Composition (no attributes) | Attributes of host framework | Attributes of host framework |
| Runner | ✅ Built-in console runner | ❌ Uses NUnit/xUnit/MSTest runner | ❌ Uses host runner (xUnit, NUnit, Fuchu…) |
| Parallel by default | ✅ Yes (async/parallel) | Depends on host framework | Depends on host framework |
| Property-based tests | ✅ FsCheck integration | ❌ | ❌ |
| Stress / performance tests | ✅ Built in | ❌ | ❌ |
| Failure messages | Standard + diffs | `should` syntax messages | **Step-by-step expression reduction** |
| IDE test explorer | Via adapters | ✅ Native | Via host framework |
| Works in FSI | ✅ | ✅ | ✅ |

## Decision Matrix — Which One for Your Use Case?

| Use case | Recommended tool | Why |
|---|---|---|
| New F#-only library, no legacy runner | Expecto | Tests-as-values, parallel by default, one NuGet package |
| Mixed C#/F# repo standardized on NUnit or xUnit | FsUnit | Keeps team tooling; adds functional assertions |
| A failing assertion you need to *understand* | Unquote | Prints every evaluation step down to `false` |
| Property-based checks alongside unit tests | Expecto | Built-in FsCheck API, no second framework |
| Hunting threading bugs under load | Expecto | Parallel-by-default doubles as a stress-test harness |
| CI with existing .NET test adapters | FsUnit or Unquote | Both ride on framework runners your CI already knows |
| Testing an F# web service end to end | Expecto or xUnit+FsUnit | Pair with the runners from our F# web frameworks guide |

## Expecto — Tests as Values, Batteries Included

Expecto's founding idea is that **tests are values**, not attribute-decorated methods: they can be composed, filtered, repeated, and passed around like any other F# data. Setup and teardown are plain functions — no attributes, no base classes. The second pillar is that **tests are parallel and async by default**, so a multi-core machine runs your suite across all cores, which also turns the suite into an informal stress test for threading bugs. Performance testing and an FsCheck-based property API ship in the same package.

The runner is the test assembly itself — compile as a console application and hook tests into the entry point:

```fsharp
open Expecto

let tests =
  test "A simple test" {
    let subject = "Hello World"
    Expect.equal subject "Hello World" "The strings should equal"
  }

[<EntryPoint>]
let main args =
  runTestsWithCLIArgs [] args tests
```

Individual cases use the `testCase` form, and the `Expect` module carries the assertion vocabulary:

```fsharp
open Expecto

let simpleTest =
  testCase "A simple test" <| fun () ->
    let expected = 4
    Expect.equal expected (2+2) "2+2 = 4"

// <| is just associativity sugar; equivalent to:
let simpleTest' =
  testCase "A simple test" (fun () ->
    Expect.equal 4 (2+2) "2+2 should equal 4")
```

Run it and the return value is CI-ready: `runTestsWithCLIArgs` returns **1 if any test failed, otherwise 0** — exactly what an operating system exit code wants. Group tests with `testList`, skip work-in-progress with pending tests, focus a single case while debugging, and mark cases `sequenced` when they must not run in parallel:

```fsharp
let allTests =
  testList "math" [
    testCase "addition" <| fun () -> Expect.equal 4 (2 + 2) "sum"
    testCase "multiplication" <| fun () -> Expect.equal 6 (2 * 3) "product"
  ]
```

Because tests are values, you can also build them programmatically — generate a `testList` from a table of inputs and expected outputs instead of copy-pasting cases. The project also publishes a dotnet template (`dotnet new install "Expecto.Template::*"`, then `dotnet new expecto`) so a new suite is one command away. For property-based coverage, Expecto's FsCheck integration follows the same cross-language ideas we mapped in our [property-based testing comparison](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/) — the gap between example-based and generative tests is the same on every platform.

## FsUnit — Functional Assertions on Top of Your Existing Framework

FsUnit makes a deliberately conservative bet: **do not replace the runner; replace the assertion syntax.** It targets NUnit, xUnit, and MSTest, and its packages (`FsUnit.NUnit`, `FsUnit.Xunit`, `FsUnit.MsTestUnit`) drop into projects that already use those frameworks — which matters when your CI, coverage tooling, and IDE test explorer are wired to them, as they likely are in the .NET ecosystem we surveyed in our [C# testing frameworks comparison](../2026-07-05-csharp-testing-frameworks-xunit-nunit-mstest-fluentassertions-shouldly/).

The payoff is assertions that read like F# instead of C# — pipe the subject into `should`, then a matcher. This is verbatim from the project's own test suite:

```fsharp
namespace FsUnit.Test

open Microsoft.VisualStudio.TestTools.UnitTesting
open FsUnit.MsTest

[<TestClass>]
type ``beEmptyTests``() =

    [<TestMethod>]
    member _.``empty List should be Empty``() =
        [] |> should be Empty

    [<TestMethod>]
    member _.``non-empty List should fail to be Empty``() =
        shouldFail(fun () -> [ 1 ] |> should be Empty)

    [<TestMethod>]
    member _.``non-empty List should not be Empty``() =
        [ 1 ] |> should not' (be Empty)
```

The matcher vocabulary covers the usual ground — `should equal`, `should be greaterThan`, `should contain`, `should haveLength`, `should be ofExactType<'a>`, `should startWith` — and negations read as `should not' (be Empty)`. The `shouldFail` wrapper asserts that a block throws, which keeps negative-path tests honest. F# value types are pretty-printed in failure messages via a custom formatter (`FSharpCustomMessageFormatter`) you register once per assembly — without it, error output falls back to `ToString()` and loses the F# shape of your data.

FsUnit is the right layer when your team says "we use NUnit here" and you want F# tests that do not feel like C# in a trench coat. Its syntax sits on top of the framework rather than fighting it — which is exactly why it stays relevant in 2026 while more ambitious runners churn.

## Unquote — Assertions That Explain Themselves

Unquote attacks the other end of the problem: **not how you write assertions, but what you learn when they fail.** Instead of a DSL, you write the assertion as a plain F# *quoted expression* — statically checked by the compiler — and Unquote decompiles and incrementally evaluates it on failure, printing every reduction step down to the final `false`. Its author credits Groovy Power Asserts as the inspiration.

A failing xUnit test, verbatim from the project README:

```fsharp
[<Fact>]
let ``demo Unquote xUnit support`` () =
    test <@ [3; 2; 1; 0] |> List.map ((+) 1) = [1 + 3..1 + 0] @>
```

produces this failure message:

```
Test 'Module.demo Unquote xUnit support' failed:

[3; 2; 1; 0] |> List.map ((+) 1) = [1 + 3..1 + 0]
[4; 3; 2; 1] = [4..1]
[4; 3; 2; 1] = []
false
```

The `[4; 3; 2; 1] = []` line is the moment the bug becomes obvious — the right-hand range `[1 + 3..1 + 0]` evaluates to `[4..1]`, which is empty, and the reduction trace shows you exactly that instead of a bare assertion failed. Unquote integrates with **any exception-based framework** — xUnit, NUnit, MbUnit, Fuchu, MSTest — with no configuration, and it works in FSI sessions, so the ad-hoc checks you type while exploring can migrate into the formal suite unchanged.

For simpler comparisons there are convenience operators, and exceptions get first-class treatment:

```fsharp
// Operator forms
x =! y          // equal
x >! y          // greater than — plus <!, >=!, <=!, <>!

// Exception assertions
raises<System.DivideByZeroException> <@ 1 / 0 @>
raisesWith <@ ... @> (fun e -> <@ e.Message.Contains "expected" @>)
```

Unquote is the smallest of the three (last push December 2024, copyright 2011–2024 — call it *finished*, not abandoned) and it is deliberately single-purpose. It composes with everything else here: FsUnit handles the everyday `should` assertions, and Unquote steps in for the gnarly transformations where you want the decompiled trace. In a functional codebase like the ones our [F# web frameworks guide](../2026-08-13-fsharp-web-frameworks-giraffe-falco-saturn/) builds with Giraffe or Saturn, that kind of diagnostic power earns its keep fast.

## Pitfalls and Migration Notes (What Nobody Tells You)

- **Do not use FsUnit without its host framework's adapter.** FsUnit alone has no runner. `dotnet test` discovers nothing until the NUnit/xUnit/MSTest test SDK and adapter are referenced — a very common first-run confusion.
- **Expecto parallelism can break stateful tests.** Tests are parallel *and async by default*. Anything touching shared mutable state, static caches, or the filesystem needs a `sequenced` case or explicit synchronization — or you will get flaky failures that only appear on loaded CI machines.
- **Expecto's console runner means no magic discovery.** Each test assembly must call `runTestsWithCLIArgs` from its entry point. Forgetting the `[<EntryPoint>]` wiring compiles fine and runs nothing.
- **Unquote is slow on huge expressions — and that is fine.** Decompiling and incrementally evaluating quotations costs more than a plain comparison. Reserve `test <@ @>` for assertions whose failure you need to *read*; use `=!` / `<>!` operators for the hot path.
- **F# list range gotchas hide in plain sight.** `[1 + 3..1 + 0]` parses as `[4..1]`, not `[4; 3; 2; 1]` — an empty range. This is the exact class of bug Unquote's reduction trace exposes and a plain `should equal` never will.
- **Mixed-language repos: keep one runner.** Introducing Expecto into a repo whose CI already runs `dotnet test` with xUnit means two discovery mechanisms and two result formats. Prefer FsUnit (same runner) unless the F#-only portion is substantial enough to own its own console runner.
- **Version-pin your FsCheck/Expecto pairing.** Expecto's FsCheck integration tracks FsCheck releases; a mismatched transitive version produces confusing missing-member errors at compile time rather than runtime.

## FAQ

**Are Expecto, FsUnit and Unquote mutually exclusive?**
No — FsUnit and Unquote are assertion layers that ride on a runner (NUnit/xUnit/MSTest), and Expecto is a runner with its own assertions. A pragmatic stack: Expecto as the F#-only runner, with Unquote's `test <@ @>` for the assertions you want decompiled failure traces on. You cannot use FsUnit's `should` syntax with Expecto's runner, since FsUnit targets the attribute-based frameworks.

**Which framework does FsUnit support?**
NUnit, xUnit, and MSTest — pick the matching package (`FsUnit.NUnit`, `FsUnit.Xunit`, or `FsUnit.MsTestUnit`). The syntax is identical across all three.

**Does Expecto work with `dotnet test`?**
Expecto has its own console runner and returns process exit codes, but it also ships adapters so results can surface in tooling that expects the standard test-result format. Many teams invoke it directly in CI (`dotnet run` on the test project) rather than through `dotnet test`.

**Which one gives the best failure messages?**
Unquote, by design — it prints step-by-step evaluation of the failing expression. FsUnit prints matcher-oriented messages with F# value formatting (if you register `FSharpCustomMessageFormatter`). Expecto prints standard assertion messages and diffs.

**Can I do property-based testing with these?**
Expecto has a built-in FsCheck integration. FsUnit and Unquote do not — pair them with FsCheck directly if you want generative tests in those setups. See our [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/) for the general pattern.

**Is Unquote abandoned?**
It is *stable*, not abandoned: last push December 2024 after more than a decade of maintenance, with no open issues blocking adoption. For a single-purpose assertion library that has not needed changes, that is closer to "finished" — but factor the slower cadence into your decision if you need active issue response.

**Which is best for testing F# web services (Giraffe/Saturn)?**
All three work, since they test plain functions and values. Expecto's parallel runner suits endpoint test suites well; if your web project already uses xUnit, FsUnit or Unquote ride along with zero new runner infrastructure. Either way, the HTTP-level tests pair naturally with the frameworks in our [F# web frameworks comparison](../2026-08-13-fsharp-web-frameworks-giraffe-falco-saturn/).

**What about F# in a C# codebase — is this still relevant?**
Very. FsUnit exists precisely for that case: keep the C# team's NUnit/xUnit conventions, add F#-idiomatic assertions in the F# modules. Expecto makes more sense when the F# surface is large enough to own its runner. And if the team is adopting more F#, the functional-style assertions in our [C# functional programming patterns article](../2026-07-05-csharp-functional-programming-languageext-fsharp-patterns/) show where the language idioms pay off.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "F# Testing in 2026: Expecto vs FsUnit vs Unquote — Which One Should You Actually Use?",
  "description": "Hands-on comparison of the three F# testing approaches: Expecto (tests-as-values runner with FsCheck integration), FsUnit (functional assertions for NUnit/xUnit/MSTest) and Unquote (quoted-expression assertions with step-by-step failure traces).",
  "datePublished": "2026-09-07",
  "dateModified": "2026-09-07",
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
