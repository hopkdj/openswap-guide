---
title: "Rust Code Coverage in 2026: cargo-llvm-cov vs Tarpaulin vs grcov"
date: "2026-11-12"
tags: ["rust", "code-coverage", "testing", "developer-tools", "ci-cd"]
draft: false
cover: "/img/screenshots/rust-coverage.jpg"
---

Your Rust test suite is green. Your CI badge says "passing." Then someone asks the only question that matters before a refactor: *how much of this crate is actually exercised by those tests?* If you cannot answer with a number, you are refactoring blind.

Rust makes this worse than most ecosystems. There is no built-in `--coverage` flag, no single blessed tool, and the three popular answers — **cargo-llvm-cov**, **cargo-tarpaulin**, and **grcov** — use different instrumentation strategies and therefore report different numbers for the same code. Pick wrong and you will either babysit a 3x slower CI job or ship a coverage report that quietly lies to you.

This guide compares all three with current release data, real command lines pulled from their repositories, and the failure modes nobody documents until their coverage gate blocks a release at 11pm.

## TL;DR: Quick Verdict

- **Default choice for 9 out of 10 projects: `cargo-llvm-cov`.** LLVM source-based instrumentation, first-class `cargo nextest` support, built-in `--fail-under-lines` gate, and it cleans stale artifacts for you. Install it, add one CI step, done.
- **Choose `cargo-tarpaulin`** if you are on x86_64 Linux and want the lowest-friction single binary with XML/Cobertura output for legacy CI systems — or if you need its `#[cfg_attr(tarpaulin, ignore)]` attributes. Use `--engine llvm` for numbers that match rustc's own view.
- **Choose `grcov`** when you must merge profiles from many binaries, fuzz targets, or a polyglot monorepo (it also ingests lcov, Go, and JaCoCo files), and when you want full control over the filter pipeline.

Everything else is detail. The detail matters, though, because the three tools disagree by 5–20 percentage points on the same crate.

## Side-by-Side Comparison

| Dimension | cargo-llvm-cov | cargo-tarpaulin | grcov |
|---|---|---|---|
| GitHub stars | **1,488** | **3,027** | **1,372** |
| Latest release | v0.9.1 | 0.37.6 | v0.10.8 |
| Last push | 2026-11-01 | 2026-11-10 | 2026-11-11 |
| Instrumentation | LLVM `-C instrument-coverage` | ptrace (default on x86_64 Linux) or `--engine llvm` | Raw LLVM profile data |
| Platform support | Linux, macOS, Windows | x86_64 Linux for ptrace; llvm engine on macOS/Windows | Linux, macOS, Windows |
| Test runner integration | `cargo test`, `cargo nextest`, `cargo run` | `cargo test` (runs the whole suite itself) | Any — you run tests, it aggregates |
| Report formats | text, html, lcov, cobertura, json | Stdout, Json, Xml, Html, Lcov | html, lcov, coveralls, coveralls+, covdir |
| Threshold gate | `--fail-under-lines/regions/functions` | `--fail-under <pct>` | No native gate (post-process the lcov) |
| License | Apache-2.0 | Apache-2.0 | MPL-2.0 |
| Setup cost | 2 commands | 1 command | 4 env vars + 2 commands |

Star counts and release tags were pulled from each repository at publish time. They move weekly; treat the ratios, not the exact numbers, as the signal.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Use this | Why |
|---|---|---|
| Standard application crate or workspace | **cargo-llvm-cov** | Zero configuration, accurate line/region data, threshold flags built in |
| CI already uses `cargo nextest` | **cargo-llvm-cov** | `cargo llvm-cov nextest` is a supported subcommand, not a hack |
| You need Cobertura XML for an old CI server | **cargo-tarpaulin** | `--out Xml` is a first-class format |
| You must know which lines a fuzz target reached | **grcov** | Aggregates hundreds of `.profraw` files from many binaries |
| macOS or Windows developer machines | **cargo-llvm-cov** or `tarpaulin --engine llvm` | ptrace tracing is Linux-only |
| Monorepo mixing Rust, Go, and Kotlin | **grcov** | Reads lcov, Go coverage, and JaCoCo inputs directly |
| You want coverage gates on a legacy nightly-only toolchain | **cargo-tarpaulin** | Historically the least opinionated about toolchain layout |

## cargo-llvm-cov: The Default That Earned It

`cargo-llvm-cov` wraps LLVM's source-based coverage. It compiles your crate with `-C instrument-coverage`, runs the tests through a cargo-compatible interface, and turns the resulting profile data into text, HTML, lcov, cobertura, or json.

Install it with the LLVM tools component, which is the step people forget:

```bash
rustup component add llvm-tools-preview
cargo install cargo-llvm-cov
```

Generate a browsable HTML report:

```bash
cargo llvm-cov --html --open
```

Produce an lcov file for Codecov, Coveralls, or a self-hosted dashboard:

```bash
cargo llvm-cov --lcov --output-path lcov.info
```

Enforce a threshold so a pull request cannot drop coverage below 80% of lines:

```bash
cargo llvm-cov --fail-under-lines 80 --lcov --output-path lcov.info
```

The `report` subcommand is the underrated feature. If you already have a directory of `.profraw` files — from a fuzzer, a manually run binary, or a previous test run — you can convert them without re-running tests:

```bash
cargo llvm-cov report --lcov --output-path coverage/lcov.info
```

Because it speaks cargo's CLI, it composes with the rest of your workflow. Running the suite through nextest inside a workspace, with integration tests excluded from the denominator:

```bash
cargo llvm-cov nextest --workspace --all-features \
  --ignore-filename-regex '(tests/|benches/|examples/)' \
  --lcov --output-path coverage/lcov.info
```

Two behavioral details worth knowing. First, `cargo llvm-cov` **cleans build artifacts by default** to avoid false positives from stale object files; pass `--no-clean` if you deliberately want incremental reuse. Second, doctests are **not included by default** — there is a `--doctests` flag, but it is explicitly marked unstable in the README. A doc-heavy crate will therefore look under-covered unless you account for that.

## cargo-tarpaulin: The Battle-Tested Workhorse

Tarpaulin predates stable LLVM instrumentation in Rust, which explains both its 3,027 stars and its architecture. Its original engine traces test processes with `ptrace` on x86_64 Linux rather than instrumenting the compiler output. A newer `--engine llvm` backend brings it in line with instrumentation-based collection, and the README notes that llvm is the default on macOS and Windows while ptrace remains the Linux default.

```bash
cargo install --locked cargo-tarpaulin
cargo tarpaulin --out Lcov --output-dir coverage
```

Cobertura XML for CI servers that only understand that dialect:

```bash
cargo tarpaulin --out Xml --output-dir coverage
```

A coverage gate with exclusions and a clean build:

```bash
cargo tarpaulin --engine llvm \
  --fail-under 80 \
  --exclude-files 'src/main.rs' 'benches/*' \
  --ignore-tests \
  --out Lcov --output-dir coverage
```

Per-function exclusions use an attribute instead of a CLI flag, which is genuinely convenient for generated or unreachable code:

```rust
#[cfg_attr(tarpaulin, ignore)]
fn unreachable_error_path() {
    // platform-specific branch that CI never executes
}
```

Project defaults belong in `tarpaulin.toml` (or `.tarpaulin.toml`) next to `Cargo.toml`. Arguments that would follow `--` on the command line go under `args` in that file. There is also an official Docker image (`xd009642/tarpaulin`), which is how many teams avoid the nightly-toolchain and seccomp friction that ptrace tracing introduces in containers.

The honest caveat: ptrace tracing cannot see code the optimizer inlined into another function, so ptrace numbers routinely read **lower** than LLVM numbers for release-style builds, and the README itself warns that results can differ a lot between the two engines. If your only goal is a stable, comparable trend line, pick one engine and never mix them in the same dashboard.

## grcov: The Aggregator for People Who Own Their Pipeline

grcov does not run your tests. It consumes `.profraw`/`.profdata` files (and lcov, Go, and JaCoCo inputs) and emits a report. That division of labor is exactly why it survives: you control compilation flags and test execution, it handles merging and filtering.

The full sequence from the README:

```bash
cargo install grcov

export RUSTFLAGS="-Cinstrument-coverage"
export LLVM_PROFILE_FILE="app-%p-%m.profraw"

cargo test

grcov . -s . --binary-path ./target/debug/ \
  -t html --branch --ignore-not-existing \
  -o ./target/debug/coverage/
```

Swap the output type for lcov when uploading to Codecov:

```bash
grcov . --binary-path ./target/debug/ -s . -t lcov --branch \
  --ignore-not-existing --ignore "/*" -o lcov.info
```

`%p` expands to the process ID and `%m` to the binary signature, which is what allows hundreds of separate profile files to coexist without overwriting each other. That is the feature that matters when a fuzz corpus, an integration binary, and a benchmark all contribute to the same report.

The cost is operational. You own `RUSTFLAGS`, so you own cache invalidation — every change to instrumentations flags rebuilds the world. You also own filtering: `--ignore-not-existing` and `--ignore "$HOME/.cargo/**"` are not optional polish, they are what stops standard-library and dependency noise from dominating your percentages. And there is no `--fail-under`; if you want a gate, you parse the lcov file yourself or use a reporting service.

## A CI Pipeline That Actually Gates Merges

This is the shape that works for a workspace crate on GitHub Actions. It fails fast, uploads an lcov artifact, and enforces a floor rather than a delta:

```yaml
name: coverage
on: [pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: llvm-tools-preview
      - uses: Swatinem/rust-cache@v2
      - run: cargo install cargo-llvm-cov --locked
      - name: Test with coverage gate
        run: |
          cargo llvm-cov --workspace --all-features \
            --ignore-filename-regex '(tests/|benches/)' \
            --lcov --output-path lcov.info \
            --fail-under-lines 80
      - uses: actions/upload-artifact@v4
        with:
          name: lcov
          path: lcov.info
```

Two design choices in that workflow are deliberate. The floor is a **whole-project** number, not a per-patch delta — per-patch gates punish refactors that delete tested code and are the fastest way to make engineers hate coverage. And the artifact upload means you can add a reporting service later without touching the test job.

## Pitfalls That Will Bite You

**Stale profile data silently corrupts results.** `.profraw` files accumulate. If you switch from one test filter to another without cleaning, you can report coverage for code paths no current test touches. `cargo-llvm-cov` cleans by default; grcov does not. Delete `*.profraw` in CI before every run.

**Doc tests are usually missing from the denominator.** Rust crates document behavior in examples, and those examples are executed — but neither tarpaulin nor a default `cargo llvm-cov` run counts them. Do not chase a 95% target on a crate whose public API is exercised mainly through doc examples; you will waste a week instrumenting the wrong code.

**Proc macros and generics distort the picture.** Monomorphized generic code and macro-expanded code produce regions that map poorly to source lines. Region coverage is usually a better signal than line coverage for heavily generic crates, which is why `cargo-llvm-cov` exposes `--fail-under-regions` separately.

**100% coverage with zero assertions is worse than 70% with real ones.** Coverage measures execution, not verification. A test that calls a function and asserts nothing inflates the number while providing no safety.

**Mixing engines breaks your trend line.** ptrace and LLVM numbers are not comparable. If you migrate from tarpaulin's ptrace engine to llvm, your dashboard will show a jump that looks like an improvement and is actually a methodology change. Annotate the switch or reset the series.

**Container ptrace needs seccomp tweaks.** Running tarpaulin's ptrace engine inside Docker often fails until you relax the seccomp profile — the README ships a GitHub Actions example for exactly this reason. `cargo-llvm-cov` avoids the problem entirely because it does not trace processes.

For the wider toolchain context around these gates, our [Rust code quality gate guide covering clippy, rustfmt and cargo-deny](../2026-11-11-rust-code-quality-gate-clippy-rustfmt-cargo-deny/) pairs well with this article. If you are coming from a C++ background, the [C++ coverage toolchain comparison of gcov, lcov, gcovr and kcov](../2026-06-26-cpp-code-coverage-tools-gcov-lcov-gcovr-kcov/) maps the same concepts onto a different ecosystem, and teams instrumenting database-heavy services will find our [Rust database library comparison](../2026-06-23-rust-database-libraries-diesel-seaorm-rusqlite/) useful for deciding where test effort pays off.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Code Coverage in 2026: cargo-llvm-cov vs Tarpaulin vs grcov",
  "description": "A hands-on comparison of cargo-llvm-cov, cargo-tarpaulin and grcov for measuring Rust code coverage, including CI configuration, threshold gates and the accuracy pitfalls of ptrace versus LLVM instrumentation.",
  "datePublished": "2026-11-12",
  "dateModified": "2026-11-12",
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

### Which Rust coverage tool is the most accurate?

Whichever one uses LLVM source-based instrumentation: `cargo-llvm-cov`, `cargo tarpaulin --engine llvm`, or `grcov` fed with instrumented builds. They measure the same compiler-emitted data. ptrace tracing, tarpaulin's legacy default on x86_64 Linux, cannot observe inlined code and typically reports lower percentages.

### Do I need a nightly Rust toolchain for code coverage?

No. LLVM instrumentation coverage has been available on stable Rust for years, and all three tools install and run on stable. Individual optional flags — `cargo llvm-cov --doctests` among them — are still marked unstable and may require nightly.

### Why is my coverage lower with tarpaulin than with cargo-llvm-cov?

Because the engines differ. ptrace tracing misses code the optimizer inlined into callers, so the reported line set is smaller and the unexecuted fraction looks larger. Run `cargo tarpaulin --engine llvm` and the numbers converge with `cargo-llvm-cov`. Never compare numbers gathered with different engines.

### How do I include doc tests in a coverage report?

Run `cargo llvm-cov --doctests`, understanding that the flag is documented as unstable. The stable alternative is to mirror critical doc examples as integration tests under `tests/`, which both instruments reliably and runs faster in CI.

### How do I fail a pull request when coverage drops?

With `cargo-llvm-cov --fail-under-lines 80` or `cargo tarpaulin --fail-under 80`, both of which exit non-zero when the measured percentage falls below the number. grcov has no native gate; parse its lcov output or delegate the decision to a reporting service.

### Can I combine coverage from multiple test binaries or fuzz targets?

Yes — that is grcov's core strength. Point `LLVM_PROFILE_FILE` at a directory using the `%p-%m` placeholders, run every binary, then aggregate with `grcov . --binary-path ./target/debug/ -t lcov`. With cargo-llvm-cov, use `cargo llvm-cov report` against the same profile directory.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
