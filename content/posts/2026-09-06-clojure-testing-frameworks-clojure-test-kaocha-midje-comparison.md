---
title: "Clojure Testing in 2026: clojure.test vs Kaocha vs Midje — Which Testing Stack Should You Use?"
date: "2026-09-06"
tags: ["clojure", "testing", "functional-programming", "libraries"]
draft: false
---

Every Clojure project starts with the same three-line test file — and then reality hits: the REPL is the real test runner, nobody remembers the `lein test` incantation, and CI logs are a wall of `FAIL in (foo-test)`. The Clojure ecosystem has three serious answers to "how do I test this?" — the standard-library **clojure.test** (shipped inside clojure/clojure, 10,955 stars), the modern runner **Kaocha** (860 stars) and the BDD-style framework **Midje** (1,696 stars). They are not three competitors so much as three *layers* — and understanding which layer you actually need saves you from building a whole testing culture on the wrong foundation.

## TL;DR — Quick Verdict

**If you are starting a new project in 2026, standardize on clojure.test assertions and run them with Kaocha.** clojure.test is the zero-dependency bedrock — every Clojure developer can read it, and it is what the Clojure core team tests Clojure itself with. Kaocha is the runner that turns those tests into a real developer experience: watch mode, pretty output, plugin hooks, and proper exit codes for CI. **Pick Midje only if you have an existing Midje codebase or you strongly want BDD-style `fact`/`=>` syntax** — it is MIT-licensed and beloved, but its last commit was January 2024, so treat it as legacy technology you maintain rather than new infrastructure you adopt. A pragmatic combo: clojure.test + Kaocha today, with Midje-style readable facts only where your team insists on them.

## Quick Comparison Table

| Dimension | clojure.test | Kaocha | Midje |
|---|---|---|---|
| Role | **Assertion framework (stdlib)** | **Test runner** | BDD test framework |
| Home | clojure/clojure repo | lambdaisland/kaocha | marick/Midje |
| GitHub stars | 10,955 (Clojure repo) | 860 | **1,696** |
| Last push | **2026-09-04** | 2025-10-09 | 2024-01-04 |
| License | EPL-1.0 | EPL-1.0 | MIT |
| Dependency footprint | **None (built into Clojure)** | One library | One library + lein plugin |
| Test syntax | `deftest` + `is`/`are` | Runs existing clojure.test | `fact`/`facts` + `=>` arrows |
| Watch/autotest | No | **Yes** | Yes (lein-midje) |
| CI exit codes | Partial | **Correct by design** | Via lein-midje |
| Plugins/extensions | Via macros | **Yes (junit-xml, cloverage, cucumber)** | Checkers, notifiers |
| Mocking/stubbing | Manual | n/a (uses clojure.test) | **`provided` built in** |
| Failure output | Standard | **Pretty diffs + deep-diff plugin** | Colored, message-oriented |
| REPL friendliness | **Excellent** | Excellent (run from REPL) | Excellent (autotest in REPL) |
| Property-testing support | Via test.check integration | **First-class (test.check plugin)** | Via clojure.test compatibility |

## Decision Matrix — Which One for Your Use Case?

| Use case | Recommended tool | Why |
|---|---|---|
| New project, zero-dependency baseline | **clojure.test** | Ships with Clojure; every library and every Clojure dev already speaks it |
| Serious local dev loop (watch + pretty failures) | **Kaocha** | Watch mode reloads only what changed; deep diffs make failures obvious |
| CI pipeline that must fail correctly | **Kaocha** | Designed so a failing suite returns a non-zero exit code deterministically |
| Existing Midje codebase that needs maintenance | **Midje** | `facts`/`provided` still work on modern Clojure; no rewrite required to keep the lights on |
| Team that wants BDD-readable specs | **Midje** (or Kaocha + careful naming) | `(fact (+ 1 1) => 2)` reads like documentation |
| Property-based testing | **Kaocha + test.check** | Run thousands of generated cases with the same runner UX |
| Testing a web app end to end | Kaocha + your HTTP lib | See our [Clojure web framework comparison](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/) for the stack around it |

## clojure.test — The Bedrock

clojure.test is not a library you add; it is part of `clojure/clojure` itself — the same repository (10,955 stars, last push 2026-09-04) that contains the compiler. It has been stable since Clojure 1.1 and its macro docstrings are the specification. The core assertion macro is `is`, whose own docstring gives the canonical form:

```clojure
(is (= 4 (+ 2 2)) "Two plus two should be 4")
```

The `is` macro also provides the exception-assertion special forms, straight from the source:

```clojure
(is (thrown? c body))            ; checks that an instance of c is thrown
(is (thrown-with-msg? c re body)) ; thrown AND message matches re
```

`deftest` defines the test function — its docstring notes that "Test functions may call other tests, so tests may be composed," and that when `*load-tests*` is false, `deftest` is ignored (that is how tools disable test loading in production contexts). For table-driven assertions, `are` expands a template across many input rows:

```clojure
(are [x y] (= x y)
  2 (+ 1 1)
  4 (* 2 2))
;; Expands to:
;; (do (is (= 2 (+ 1 1)))
;;     (is (= 4 (* 2 2))))
```

Add `testing` strings for nested context, `use-fixtures` for per-namespace setup/teardown, and `run-tests` to execute — and you have a complete, dependency-free testing story. The entire Clojure standard library and most of the ecosystem test themselves this way, which means examples are everywhere and any Clojure developer can contribute to your test suite without learning a DSL.

**Best for:** the baseline. If you do nothing else, do this. **Trade-off:** the runner experience is spartan — no watch mode, no fancy reporting, and historically awkward exit-code behavior in CI shells.

## Kaocha — The Modern Runner

Kaocha calls itself "the full featured next generation test runner for Clojure," and the key word is **runner**: it does not replace clojure.test, it makes clojure.test (and other test types) a pleasure to operate. Its design philosophy is visible in the quick start — you add it as a dev alias and create a `bin/kaocha` binstub:

```clojure
;; deps.edn
{:deps { ,,, }
 :aliases
 {:test {:extra-deps {lambdaisland/kaocha {:mvn/version "1.91.1392"}}
         :main-opts ["-m" "kaocha.runner"]}}}
```

```shell
mkdir -p bin
echo '#!/usr/bin/env sh' > bin/kaocha
echo 'clojure -M:test "$@"' >> bin/kaocha
chmod +x bin/kaocha
```

Configuration lives in a `tests.edn` file at the project root. The catch-all example from the official docs:

```clojure
;; tests.edn
#kaocha/v1
{:tests [{:id          :unit
          :test-paths  ["test" "src"]
          :ns-patterns [".*"]}]
          ;; :reporter kaocha.report.progress/report
          ;; :plugins [:kaocha.plugin/profiling :kaocha.plugin/notifier]
 }
```

From there the workflow features compound: watch mode that reloads only the namespaces you touched, `:skip-meta :slow` to exclude tagged tests, `:fail-fast?` for tight loops, a plugin system (kaocha-junit-xml for CI dashboards, kaocha-cloverage for coverage, kaocha-cucumber for BDD scenarios), and selectable suites via the CLI. Because it executes clojure.test namespaces by default, adopting Kaocha is a **drop-in change** — your existing `deftest`/`is` tests run unmodified, and unadopted tests still run under it, which removes the political friction that usually blocks test-tooling upgrades. The honest caveat: the lambdaisland/kaocha repo's last push was October 2025, so the project is in maintenance mode — but it is mature, widely deployed, and its release line (1.91.x) is what most of the Clojure community runs in CI today.

**Best for:** teams that want clojure.test's semantics with a modern dev loop and CI-grade behavior. **Trade-off:** one more dependency and a config file; and you are betting on a project whose commit cadence has slowed.

## Midje — The Readable BDD Layer

Midje is the framework that made Clojure testing *readable* before readability was fashionable. Its thesis, from the project README: tests should look like examples in a Clojure book. Instead of assertions, you write *facts* with an arrow between expression and expectation — the canonical shape from the official wiki tutorial:

```clojure
(fact "`split` splits strings on regular expressions and returns a vector"
  (str/split "a/b/c" #"/") => ["a" "b" "c"]
  (str/split "" #"irrelevant") => [""]
  (str/split "no regexp matches" #"a+\s+[ab]") => ["no regexp matches"])
```

Facts can nest inside `facts`, and Midje replaces plain equality with its own *extended equality*: when the right-hand side is a regular expression, the check becomes a partial match rather than identity — verified live at the REPL in the official docs:

```clojure
user=> (fact "O wad    some pow'r" => #"wad\s+some")
true
```

Where Midje historically shined for BDD work is its built-in stubbing via `provided` (no separate mocking library needed) and its two autotest paths: `lein midje :autotest` from the command line, or in-REPL autotesting where Midje watches files, reloads changed namespaces, and re-runs while leaving your REPL prompt live for interactive checks. Setup is the classic Leiningen two-parter:

```clojure
;; ~/.lein/profiles.clj
{:user {:plugins [[lein-midje "3.2.1"]]}}
```

```clojure
;; project.clj
:profiles {:dev {:dependencies [[midje "..."]]}}
```

The uncomfortable truth: marick/Midje's last push was **January 2024**, and the project has been in slow-fade since its creator stepped back. It still works on modern Clojure, and its 1,696 stars reflect genuine community affection, but starting new work on Midje in 2026 means accepting a framework with no active maintainer.

**Best for:** existing Midje suites and teams that prioritize BDD readability. **Trade-off:** legacy status; `provided`-based tests are harder to port to other runners than plain clojure.test assertions are.

## Migration and Coexistence Strategies

The good news: these three tools interoperate far better than their marketing suggests, which makes migration a gradual process rather than a big-bang rewrite. Kaocha runs plain clojure.test namespaces natively — in fact, that is its default test type — so a codebase migrating from `lein test` to Kaocha changes only its tooling, not a single test body. Midje sits on top of clojure.test-compatible infrastructure, and its facts can be executed alongside clojure.test suites in the same build, which means a legacy Midje project can adopt Kaocha as the runner while Midje facts and clojure.test `deftest`s coexist in the same suite definition. The pragmatic 2026 migration path is therefore: (1) introduce Kaocha as your runner while keeping every existing test untouched, (2) write all *new* tests in plain clojure.test so they stay portable, and (3) migrate Midje `fact` blocks to clojure.test only when you touch that file anyway — a line-by-line translation of `(fact (f x) => y)` into `(is (= y (f x)))` that preserves intent without a dedicated migration tool. Teams that want property-based coverage on top can add test.check and run it through Kaocha, getting thousands of generated cases with the same watch/CI workflow — the same pattern we documented for [Haskell's testing ecosystem](../2026-08-01-haskell-testing-frameworks-hspec-quickcheck-tasty-hunit/), where QuickCheck-style property tests sit alongside unit frameworks. And because Clojure tests are just functions with metadata, nothing stops you from keeping a REPL-centric workflow: whichever runner you choose, the REPL remains the fastest feedback loop in the language.

## Pitfalls (What the Tutorials Skip)

1. **Kaocha and clojure.test are not alternatives — using both is the point.** Kaocha's whole job is running clojure.test (and other) suites. Choosing "Kaocha vs clojure.test" as a framework question is a category error; choose your assertion style (clojure.test, Midje facts, test.check properties) and your runner (Kaocha or raw `clojure -M:test`) separately.
2. **`*load-tests*` matters in production.** The clojure.test source explicitly makes `deftest` a no-op when `*load-tests*` is false. If you AOT-compile libraries with tests on the classpath, understand how your build sets this var or you will ship dead test vars — or accidentally run them.
3. **Midje's extended equality is not `=`.** Regexes on the right-hand side do partial matching (`#"wad\s+some"` matches a longer string). Porting a Midje fact to clojure.test by blindly substituting `is` can silently change a substring check into an equality check. Translate `=> #"..."` to `(re-find #"..." actual)` — not `=`.
4. **REPL state leaks into tests.** Clojure's mutable atoms and dynamic vars make tests order-dependent. Use `use-fixtures :each` (or Kaocha's isolation features) to reset state per test; Midje's in-REPL autotest makes this trap especially easy to hit because the same JVM accumulates state across reloads.
5. **Watch mode and CI mode are different contracts.** A watcher that reloads only changed namespaces is great locally but wrong for CI — that is why Kaocha separates the concepts and why you should always run a clean full suite in CI rather than trusting green local watch sessions.
6. **Don't test implementation details through `provided`/mocking.** Midje's `provided` makes stubbing so easy that teams over-mock, then suffer when refactors break every test. Prefer testing public behavior and reserving stubs for genuine I/O boundaries — the same discipline applies to clojure.test code that hand-rolls with `with-redefs`.

For adjacent tooling in the Clojure ecosystem, see our [Clojure data validation comparison](../2026-09-05-clojure-data-validation-malli-schema-spec-comparison/) (Malli, Schema, clojure.spec — the layer that guarantees the *inputs* your tests feed) and the [Clojure async libraries guide](../2026-09-04-clojure-async-libraries-core-async-manifold-aleph-comparison/) for testing stateful, concurrent code.

## FAQ

**Is Kaocha compatible with my existing clojure.test tests?**
Yes — that is its default mode. Kaocha discovers and runs plain clojure.test namespaces without modification. Adding it to a project is a tooling change, not a test rewrite: add the alias and `tests.edn`, create the `bin/kaocha` binstub, and run `bin/kaocha`. Your `deftest`/`is` tests execute exactly as before, with better reporting and exit codes.

**Is Midje still maintained? Should I use it in 2026?**
The repository's last push was January 2024 and there is no active maintainer, so Midje is effectively legacy. It still runs on current Clojure releases and remains a fine choice for maintaining an existing Midje suite. For new projects, prefer clojure.test + Kaocha; if you want BDD-style readability, consider expressing intent through well-named `testing` contexts instead of adopting a dormant framework.

**How do clojure.test, Kaocha and Midje relate to property-based testing?**
Property-based testing is a separate layer: libraries like test.check generate inputs and verify properties over thousands of cases. clojure.test can run test.check properties through its `is`/`testing` integration, and Kaocha has first-class support for running property tests with the same watch and CI workflow. Midje provides clojure.test compatibility for running such tests too. Our [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/) covers the concepts across languages.

**How do I get watch/autotest without leaving the REPL?**
Kaocha supports running from the REPL (`(require 'kaocha.repl)` / `(kaocha.repl/run)`) and offers watch mode via its CLI. Midje's lein-midje plugin provides `lein midje :autotest` and in-REPL autotesting that reloads changed files while keeping the prompt live. Plain clojure.test has no built-in watcher — that is precisely the gap Kaocha fills.

**What is the difference between `is`, `are` and Midje's `=>`?**
`is` asserts a single predicate/form, optionally with a message; `are` expands a template across many rows of data (both are clojure.test macros). Midje's `=>` is the expectation arrow inside `fact`/`facts`, backed by extended equality that supports regex partial matches and function-based checks on the right-hand side. They express the same intent differently; choose one style per project and be consistent.

**Which tool gives the best CI experience?**
Kaocha, by design — correct non-zero exit codes on failure, selectable suites, `--fail-fast`, and the kaocha-junit-xml plugin for JUnit-style CI dashboards. Midje via lein-midje works but is less configurable; plain `lein test` has historically been the weakest of the three for CI exit-code semantics.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clojure Testing in 2026: clojure.test vs Kaocha vs Midje — Which Testing Stack Should You Use?",
  "description": "Comparison of Clojure testing options: clojure.test, Kaocha and Midje. Covers runner vs framework roles, BDD facts syntax, watch mode, CI exit codes, migration paths and maintenance status in 2026.",
  "datePublished": "2026-09-06",
  "dateModified": "2026-09-06",
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
