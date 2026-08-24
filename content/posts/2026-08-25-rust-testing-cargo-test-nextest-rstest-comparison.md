---
title: "Rust Testing in 2026: cargo test vs cargo-nextest vs rstest — Which Should You Use?"
date: "2026-08-25"
tags: ["rust", "testing", "cargo", "nextest", "rstest"]
draft: false
cover: "/img/screenshots/nextest-cover.jpg"
---

Your Rust test suite is probably twice as slow as it needs to be, and the culprit is the default test runner you have never questioned. `cargo test` runs every test binary sequentially, executes tests inside one process per binary, and gives you no retry story for flaky tests. The ecosystem has moved on: **cargo-nextest** runs the same tests in parallel with per-test process isolation and is faster by an order of magnitude on real-world crates, while **rstest** fixes the ergonomics gap — fixtures, parameterized cases, and matrix tests — that drives developers to copy-paste test setup. None of these tools competes with the others; they stack. This guide shows you how to combine them and where each one's sharp edges cut.

## TL;DR — Quick Verdict

Keep `cargo test` for local development and quick checks — it is built in, runs doctests (which nextest cannot), and needs zero configuration. Adopt **cargo-nextest** for CI and any suite over a few hundred tests: it parallelizes aggressively, isolates each test in its own process (leak detection included), and supports retries, filtersets, and JUnit output out of the box. Add **rstest** when your tests share setup or repeat the same assertions over many inputs — `#[fixture]` replaces hand-rolled setup functions and `#[case]` generates one independent test per input row. The three compose cleanly: rstest generates tests, nextest runs them faster. The only genuine either/or decision is cargo test vs nextest as your runner, and for a serious project the answer is "nextest in CI, cargo test locally."

## Quick Comparison

| Dimension | cargo test (built-in) | cargo-nextest | rstest |
|---|---|---|---|
| Type | Default test runner | Parallel test runner | Fixture/parametrization framework |
| Repo | rust-lang/cargo (15,422⭐) | nextest-rs/nextest (3,241⭐) | la10736/rstest (1,576⭐) |
| Last push | 2026-08-24 (active) | 2026-08-20 (active) | 2026-03-26 (active) |
| License | Apache-2.0 / MIT | Apache-2.0 / MIT | Apache-2.0 / MIT |
| Doctests | ✅ Yes | ❌ No | n/a (works with both runners) |
| Parallelism | Per-binary threads | **Per-test processes, parallel** | Test generation (runner-independent) |
| Per-test isolation | No (shared process per binary) | **Yes — one process per test** | n/a |
| Flaky-test retries | Manual re-run | **`--retries` built in** | n/a |
| JUnit/CI output | Manual | **Built in** | n/a |
| Fixtures & parameterized cases | `#[test]` only | n/a | **`#[fixture]`, `#[case]`, `#[values]`** |

## Decision Matrix — Which One for Your Use Case?

| Use Case | Recommendation | Why |
|---|---|---|
| Local dev loop, quick `cargo check`-style feedback | **cargo test** | Zero setup, runs doctests, good enough at small scale |
| CI pipeline for a real project | **cargo-nextest** | Parallel + retries + JUnit; cuts CI time by 2–10× on large suites |
| Tests share database/temp-dir/state setup | **rstest fixtures** | `#[fixture]` injects setup as parameters; no more `setup_()` calls |
| Same assertions, many inputs | **rstest `#[case]`** | One test function, N independent test cases with clear names |
| Async (tokio) tests with timeouts | **rstest** | `async-timeout` feature adds per-test timeouts |
| Doctests in your docs | **cargo test** | nextest explicitly does not run doctests — keep cargo test for those |

## cargo test — The Baseline You Already Have

`cargo test` is the default runner compiled into Cargo itself (rust-lang/cargo, 15,422 stars, Apache-2.0/MIT). It builds your crate's test binaries and runs them: within a binary, tests execute on a thread pool; across binaries, execution is sequential. For small crates that is instant; for workspace monorepos with dozens of integration-test binaries, the sequential-binary behavior alone can add minutes to CI.

```bash
# The entire suite
cargo test

# One module's tests
cargo test parser::

# Show println! output
cargo test -- --nocapture

# Run only ignored tests
cargo test -- --ignored
```

The built-in runner has two genuine advantages that keep it relevant: **doctests** (`cargo test --doc` compiles and runs every example in your rustdoc comments) and **zero configuration**. It is also the only runner that works before you install anything. Its weaknesses are structural: no cross-binary parallelism, no per-test isolation (a test that leaks a thread or holds a global lock can poison its siblings), no retry policy, and no structured output for CI dashboards.

## cargo-nextest — The Faster Runner for CI

cargo-nextest (nextest-rs/nextest, 3,241 stars, Apache-2.0/MIT, last push August 2026) is a re-implementation of the test runner, not a test framework. It builds on `cargo test`'s compilation and discovery, then executes differently: **each test runs in its own process**, test binaries run in parallel, and results stream as they finish. The project grew out of Diem's internal tooling and is used across large Rust shops precisely because of the per-test isolation: a test that panics, leaks threads, or writes to a shared path cannot take down its neighbors.

```bash
# Install (or use cargo-binstall / dist)
cargo install cargo-nextest --locked

# Run the suite — drop-in replacement for cargo test
cargo nextest run

# Retry flaky tests up to 2 times
cargo nextest run --retries 2

# JUnit XML for GitLab/Jenkins/dashboards
cargo nextest run --message-format junit
```

Configuration lives in `.config/nextest.toml`, where you can define profiles for CI:

```toml
[profile.ci]
# Don't stop the world on the first failure
fail-fast = false

# Retry flaky tests twice before reporting failure
retries = 2

[profile.ci.junit]
path = "target/nextest/junit.xml"
```

`cargo nextest run --profile ci` then produces both results and a JUnit artifact in one shot. The cost: nextest **cannot run doctests** (its process model does not fit doc examples), and it requires a reasonably recent Rust toolchain to build (the README's stated minimum for building is Rust 1.91; running works on much older versions). Teams typically keep `cargo test --doc` as a separate CI step and use nextest for everything else. For the error-handling and CLI patterns that often surround test code, our [Rust error handling guide](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/) is a useful companion read.

## rstest — Fixtures and Parameterized Tests Without Boilerplate

rstest (la10736/rstest, 1,576 stars, Apache-2.0/MIT, last push March 2026) is a procedural-macro framework that generates tests from declarative descriptions. Its headline feature is **fixture injection**: instead of calling a setup function at the top of every test, you declare a `#[fixture]` and receive it as a test argument.

```rust
use rstest::*;

#[fixture]
pub fn fixture() -> u32 { 42 }

#[rstest]
fn should_succeed(fixture: u32) {
    assert_eq!(fixture, 42);
}

#[rstest]
fn should_fail(fixture: u32) {
    assert_ne!(fixture, 42);
}
```

Parameterization is where it shines. The same test function runs once per `#[case]`, and each case is reported as an independent test with its own pass/fail status:

```rust
use rstest::rstest;

#[rstest]
#[case(0, 0)]
#[case(1, 1)]
#[case(2, 1)]
#[case(3, 2)]
#[case(4, 3)]
fn fibonacci_test(#[case] input: u32, #[case] expected: u32) {
    assert_eq!(expected, fibonacci(input))
}
```

Running `cargo test` (or `cargo nextest run` — rstest output is runner-agnostic) executes five tests named `fibonacci_test::case_1` through `case_5`. For inputs you do not want to enumerate, `#[values(list, of, values)]` runs the test once per value, and combining several `#[values]` arguments produces the cartesian product — a matrix test. When the same case list must drive multiple test functions, the companion `rstest_reuse` crate provides `#[template]`/`#[apply]` to define the cases once and reuse them. Async tests work out of the box with tokio; the `async-timeout` feature (enabled by default) adds per-test timeouts, which pair naturally with property-based approaches like the ones in our [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/).

## Putting It Together — A Modern Rust Test Stack

The composition is the point. rstest generates the tests (fixtures, cases, values), nextest executes them (parallel, isolated, retried, JUnit-reported), and cargo test remains the fallback that runs doctests and works everywhere:

```bash
# Local fast loop — keep it simple
cargo test

# CI — parallel, isolated, retried, with JUnit output
cargo nextest run --profile ci

# Docs examples still verified
cargo test --doc
```

A workspace `[dev-dependencies]` section that gets you there:

```toml
[dev-dependencies]
rstest = "0.26"
cargo-nextest = "0.9"   # binary; install via cargo install or dist

[profile.ci]
# applied when running: cargo nextest run --profile ci
```

This is also the stack to standardize on before your suite grows past the point where `cargo test`'s sequential binaries start costing you CI minutes — the same way picking the right HTTP client early pays off later (see our [Rust HTTP client comparison](../2026-08-17-rust-http-client-libraries-reqwest-hyper-ureq-comparison/)).

## Pitfalls and Migration Gotchas

1. **nextest does not run doctests.** If your CI switches wholesale to `cargo nextest run`, your rustdoc examples silently stop being tested. Add `cargo test --doc` as an explicit step.
2. **Per-test process isolation changes assumptions.** Tests that relied on sharing state across tests within one binary (a lazily-initialized static, a common temp directory) will fail under nextest because each test starts fresh. This is usually a *correctness fix* in disguise, but budget time for the first nextest run on a legacy suite.
3. **Leak detection is real.** nextest fails tests whose threads outlive the test body (`run-leak`). A background thread you never joined will surface as a failure that `cargo test` never reported.
4. **Global setup is not a fixture.** rstest fixtures are per-test arguments, not `before_all` hooks. For one-time heavy setup (spin up a database container), combine rstest with a lazy static or a test harness — fixtures alone will recreate the resource per test.
5. **`#[values]` explodes combinatorially.** Two `#[values]` arguments with 10 values each generate 100 tests. That is usually what you want, but with slow tests it turns a 30-second suite into a 10-minute one — profile before shipping matrix tests to CI.
6. **proc-macro compile time.** rstest adds a few seconds to cold builds; it is negligible on incremental builds, but if your crate is proc-macro-sensitive, be aware the first build after adding it takes longer.
7. **Filterset syntax differs from cargo test filters.** `cargo test parser::` filters by name substring; nextest filtersets use `cargo nextest run -E 'test(parser)'` with a richer expression language. When porting CI commands, translate the filters, do not copy them.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Testing in 2026: cargo test vs cargo-nextest vs rstest — Which Should You Use?",
  "description": "Compare Rust test runners cargo test vs cargo-nextest and the rstest fixture framework: parallelism, isolation, retries, fixtures, and the modern CI test stack.",
  "datePublished": "2026-08-25",
  "dateModified": "2026-08-25",
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

### Can cargo-nextest run rstest tests?

Yes — rstest generates ordinary `#[test]` functions, and nextest executes whatever `cargo test` would discover. The two are complementary: rstest for authoring, nextest for execution.

### Does nextest work on stable Rust?

Yes, running nextest works with any Rust released in the past year (the README's minimum to *run* is Rust 1.41; the minimum to *build* nextest itself is Rust 1.91, which only matters if you compile it from source rather than installing a prebuilt binary).

### Why is cargo test slower than nextest?

Two structural reasons: cargo test runs test binaries sequentially, and it executes all tests in a binary inside one process using threads. nextest runs binaries in parallel and spawns one process per test, which both parallelizes better and avoids cross-test interference. On large crates the difference is typically 2–10×.

### Does rstest work with async tests?

Yes. rstest supports async test functions (including `#[fixture]` returning futures), and the default-enabled `async-timeout` feature adds per-test timeout handling.

### Is there a way to retry flaky tests with cargo test?

Not built in — you re-run the whole command manually. nextest's `--retries N` flag (or a `retries` setting in a profile) retries only the failed tests, which is the practical fix for flaky tests in CI.

### Should I remove cargo test entirely?

No. Keep it as the zero-config default and for doctests; adopt nextest for CI and rstest for test ergonomics. All three coexist in a typical modern Rust workspace.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
