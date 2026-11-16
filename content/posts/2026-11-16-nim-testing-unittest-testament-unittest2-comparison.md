---
title: "Nim Testing in 2026: std/unittest vs Testament vs unittest2 — Pick the Right Harness Before You Regret It"
date: "2026-11-16"
tags: ["nim", "testing", "developer-tools", "compiler", "ci-cd"]
draft: false
cover: "/img/screenshots/nim-testing-logo.jpg"
description: "Nim's three test harnesses compared: std/unittest for unit tests, Testament for compiler-grade test specs, unittest2 for JUnit XML in CI. Real code, real commands, real traps."
---

Nim compiles to C, C++, Objective-C and JavaScript, catches errors at compile time that other languages only discover in production, and still has one of the smallest testing ecosystems of any mainstream compiled language. That combination creates a specific kind of confusion: the standard library ships a test module, the compiler ships a completely different test runner, and a third-party library reimplements the first one with better output.

Pick wrong and you end up with a `nimble test` task that silently skips half your suite, or a CI pipeline with no machine-readable results. Pick right and you get compile-time assertions, process-isolated tests, JUnit XML, and a compiler test matrix — all from the same `nim` binary.

Here is the honest breakdown, with the data pulled from GitHub today.

## TL;DR — Quick Verdict

**Use `std/unittest` for library unit tests, add `unittest2` the moment you need JUnit XML or compile-time tests, and reach for Testament only when you are testing a compiler, a macro-heavy library, or anything that needs `discard """ ... """` specs with expected output and exit codes.**

- **Small library, `nimble test`, no CI reporting?** `std/unittest` is enough — zero dependencies.
- **CI pipeline that needs XML, isolated test processes, or `static:` blocks under test?** `unittest2` — a near drop-in replacement.
- **Testing code generation, error messages, macro expansions, or multiple backends (C, C++, JS)?** Testament. Nothing else models "this file must fail to compile with this exact message" as a first-class citizen.

## The Three Harnesses Side by Side

| Dimension | `std/unittest` | Testament | `unittest2` |
|---|---|---|---|
| Ships with | Nim standard library | Nim compiler repo (`testament/`) | `nimble install unittest2` |
| GitHub stars (parent repo) | **18,312** (`nim-lang/Nim`) | **18,312** (`nim-lang/Nim`) | **32** (`status-im/nim-unittest2`) |
| Last push | Nov 16, 2026 | Nov 16, 2026 | Nov 16, 2026 |
| Syntax | `suite` / `test` / `check` | Spec block in `discard """ """` | `suite` / `test` / `check` (compatible) |
| Process isolation | No — same process | **Yes**, one process per test | Yes, each test in its own proc |
| Expected-output assertions | No | **Yes** (`output`, `nimout`, `errormsg`) | No |
| Compile-failure tests | No | **Yes** (`action: reject`) | Partial (`static:` blocks) |
| Multi-target matrix | No | **Yes** (`--targets:"c cpp js"`) | No |
| JUnit XML for CI | No | HTML report only (`html` command) | **Yes** |
| Valgrind integration | No | **Yes** (`--valgrind:on`) | No |
| Learning curve | 10 minutes | An afternoon | 15 minutes |
| Best fit | Application logic | Compiler / macro / FFI code | CI-reported application suites |

The star gap between 32 and 18,312 is not a quality signal here — it reflects that `unittest2` is a focused library maintained by Status for their own Nim codebase, while the other two ride along with the compiler repository.

## Scenario Decision Matrix

| Your situation | Recommended harness | Why |
|---|---|---|
| Web service with 200 handlers, GitHub Actions | `unittest2` | JUnit XML → native CI test reports |
| CLI tool, `nimble test`, local only | `std/unittest` | No extra dependency, instant setup |
| Macro or template library where error text matters | Testament | `errormsg` + `action: reject` assertions |
| Code that must work on both C and JS backends | Testament | `--targets:"c js"` runs the same file twice |
| Testing memory safety of FFI wrappers | Testament | Built-in Valgrind toggle |
| Legacy suite written with `import unittest` | `std/unittest` (or swap to `unittest2`) | Identical API, no rewrite needed |
| Need to test something at compile time | `unittest2` | `static:` tests run in the Nim VM |

## std/unittest — the Baseline Everyone Starts With

The standard library module is small and predictable. `check` records a failure and continues; `require` aborts the current test; `expect` asserts that a specific exception type is raised.

```nim
import std/unittest

proc computeBackoff(attempt: int): int =
  if attempt <= 0:
    raise newException(ValueError, "attempt must be positive")
  result = min(100 * (1 shl (attempt - 1)), 30_000)

suite "retry policy":
  test "exponential growth":
    check computeBackoff(1) == 100
    check computeBackoff(4) == 800

  test "caps at thirty seconds":
    check computeBackoff(20) == 30_000

  test "rejects zero attempts":
    expect ValueError:
      discard computeBackoff(0)

  test "rejects negative attempts":
    expect ValueError:
      discard computeBackoff(-3)
```

Run it with `nim c -r tests/test_retry.nim`, or wire it into the `.nimble` file so `nimble test` picks it up:

```nim
# mylib.nimble
version       = "0.4.0"
author        = "Your Name"
description   = "Retry helpers"
license       = "MIT"
srcDir        = "src"

requires "nim >= 2.0.0"

task test, "Run the test suite":
  exec "nim c -r --hints:off tests/test_retry.nim"
```

**Where it stops being enough:** no XML output, no process isolation (a segfault in one test kills the whole run and you get no results for the other 199), no compile-time tests, and failure output is a plain-text dump that CI systems cannot parse into a test report. For a library that only ever runs on the developer's laptop, none of that matters. For a service, all of it does.

## Testament — the Compiler's Own Test Runner, and Why You Might Want It

Testament is what the Nim compiler itself uses. It is not a library you import; it is a runner that reads test files from `./tests/<category>/*.nim` and interprets a spec block at the top of each file.

The spec is the whole point. It lets a test declare not just "this should work" but "this exact program must fail to compile with this exact message":

```nim
discard """
  action: reject
  errormsg: "type mismatch: got <int, string>"
  line: 8
"""

proc addInts(a, b: int): int = a + b

echo addInts(1, "two")
```

For behaviour-level tests, the spec carries expected stdout and exit codes, plus a matrix of compiler options:

```nim
discard """
  output: "attempts=3 total=700"
  exitcode: 0
  matrix: "--mm:orc; --mm:arc"
  targets: "c cpp"
"""

import std/strutils

var total = 0
for attempt in 1 .. 3:
  total += 100 * attempt

echo "attempts=3 total=" & $total
```

Run it from the project root:

```bash
# build testament from the Nim repo (or install via nimble)
nim c -d:release testament/testament.nim

./testament/testament category "mylib"
./testament/testament pattern "tests/**/*.nim"
./testament/testament run tests/mylib/tbackoff.nim
./testament/testament --targets:"c js" --print category "mylib"
./testament/testament html          # generates testresults.html
```

Useful flags straight from the official documentation: `--simulate` to see what would run without running it, `--failing` to show only broken and ignored tests, `--megatest:on|off` to batch megatest-compatible files, `--valgrind:on|off`, and `--skipFrom:file` to skip a list of tests during a migration.

**Honest assessment:** Testament's ergonomics are those of a compiler test harness, because that is exactly what it is. There is no `check` macro, no IDE integration, no XML output — only an HTML report from its internal database. Setup cost is real: you build it from source, or install it and keep the binary in your CI image.

**But nothing else in the Nim ecosystem can assert on error messages, line numbers, and compilation failure.** If your library is a macro that generates code, or a DSL where the value is in the diagnostics, Testament is not optional polish — it is the only tool that can test your actual product.

## unittest2 — the Pragmatic CI Choice

`unittest2` is maintained by Status and started as an evolution of `std/unittest`. The compatibility claim is accurate: in most suites, changing `import unittest` to `import unittest2` is the entire migration.

```nim
import unittest2

suite "header parsing":
  test "accepts a well-formed header":
    let h = parseHeader("Content-Length: 42\r\n")
    check h.name == "Content-Length"
    check h.value == "42"

  test "rejects a header with no colon":
    expect ValueError:
      discard parseHeader("Content-Length 42")

  test "length prefix above the limit is refused":
    check not acceptsLength(10_000_000)
```

Install and run:

```bash
nimble install unittest2
nim c -r --hints:off tests/test_header.nim
```

What you gain over the standard library:

- **JUnit-compatible XML output**, which GitHub Actions, GitLab, Jenkins and Buildkite all render as a native test report instead of a wall of stdout.
- **Per-test process isolation**, so a crash in one test does not erase the results of the rest.
- **Cleaner reporting** with a two-phase collect-and-run model — the runner first enumerates tests, then executes them, which produces correct totals and progress in CI logs.
- **Compile-time tests** via `static:` blocks, verified in the Nim VM before your code ever runs on the target backend.
- **Strict exception tracking compatibility**, which matters in code compiled with `--panics:on` or effect-heavy libraries.

The trade-off is a 32-star dependency in your supply chain instead of the standard library. For most teams that is a fair trade for machine-readable CI output; for a zero-dependency library targeting the smallest possible footprint, it is not.

## Pitfalls, Migration Notes and Performance Traps

- **`check` does not stop the test.** It records a failure and continues executing, so a nil dereference after a failed `check` crashes the run. Use `require` for preconditions that later lines depend on.
- **`expect` only catches the exact type.** An `IOError` raised where you expect `ValueError` fails the test rather than passing — good, but teams migrating from other languages are often surprised that there is no implicit "any exception" catch.
- **Testament will not find your tests outside `tests/<category>/`.** The default glob is `./tests/category/*.nim`; anything else needs an explicit `pattern` argument, which is the number one reason a "passing" Testament run reports zero tests.
- **`--megatest:on` is the default** and batches compatible files into one binary for speed. When debugging a single failing test, pass `--megatest:off` — otherwise the failure appears in a combined binary and the stack trace points at generated code.
- **Compiled test binaries are not cleaned up.** Long CI runs accumulate `testresults/` and megatest artefacts; add both to `.gitignore` and prune them in your cache step.
- **Do not mix harnesses in one binary.** Importing both `unittest` and `unittest2` in the same module produces duplicate suite registration and confusing double counts.
- **JavaScript target tests need Node on `PATH`.** Testament will happily report a pass count of zero rather than an error if the JS runtime is missing in a slim CI image.

## Why Keep the Suite In-Repo Instead of Behind a Service

For a compiled language with a small ecosystem, the cost of a hosted test service is higher than it looks: uploading artefacts, matching compiler versions, and debugging why a test passes locally and fails remotely. Nim's own compiler team solved this by keeping the entire test matrix in the repository and running Testament locally and in CI from the same files — 18,000+ stars of project history sit in that same pattern.

That pattern is worth copying. `nimble test` runs on a laptop with no network; Testament specs are plain `.nim` files reviewed like any other code, and `unittest2`'s XML output slots into whatever CI you already pay for.

For adjacent reading, our [Nim toolchain comparison](../2026-10-25-nim-toolchain-nimble-choosenim-atlas-comparison/) covers `nimble`, `choosenim` and `atlas` — the build layer your test task depends on. If your suite touches async code, the [Nim async I/O breakdown](../2026-10-29-nim-async-io-chronos-asyncdispatch-threadpool/) explains why async tests need explicit dispatcher teardown. And for a cross-ecosystem view of the same problem, see our [Elixir testing frameworks comparison](../2026-08-21-elixir-testing-frameworks-exunit-mox-streamdata-comparison/).

## FAQ

**Do I need Testament if I already use unittest?**
Only if you need to assert on compiler output, compilation failure, line numbers, or multiple backends. Testament's unique value is `action: reject` with `errormsg` and `line` — no `unittest`-style harness can express "this code must not compile, and here is the exact diagnostic". For ordinary runtime behaviour, stay with `std/unittest` or `unittest2`.

**Is unittest2 a drop-in replacement for std/unittest?**
In most codebases, yes: change the import and everything else compiles. The differences appear with custom reporters and code that relies on `std/unittest` internals rather than its public macros. Pin the version in your `.nimble` file and run your suite once after swapping.

**How do I get JUnit XML out of a Nim test suite?**
Use `unittest2`, which emits JUnit-compatible XML that CI systems parse natively. `std/unittest` and Testament do not produce JUnit XML — Testament generates an HTML report from its own database via the `html` command instead.

**Why does Testament report zero tests when I know the files exist?**
Because the default discovery path is `./tests/<category>/*.nim` relative to the working directory. Run it from the project root, or pass an explicit glob: `testament pattern "tests/**/*.nim"`. Use `--simulate` to confirm what would run before blaming the tests.

**Can I run the same test file against the C and JavaScript backends?**
Yes — with Testament, via `--targets:"c js"` or a `targets:` field in the spec block. The file is compiled and executed once per backend, which is the cheapest way to catch code that silently assumes pointer semantics. `std/unittest` and `unittest2` have no equivalent and require you to script the matrix yourself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nim Testing in 2026: std/unittest vs Testament vs unittest2 — Pick the Right Harness Before You Regret It",
  "description": "Nim's three test harnesses compared: std/unittest for unit tests, Testament for compiler-grade test specs, unittest2 for JUnit XML in CI.",
  "datePublished": "2026-11-16",
  "dateModified": "2026-11-16",
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
