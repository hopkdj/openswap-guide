---
title: "Clippy vs rustfmt vs cargo-deny in 2026: Building a Rust Quality Gate That Catches Real Bugs"
date: "2026-11-11"
tags: ["rust", "code-quality", "linting", "supply-chain-security", "developer-tooling"]
draft: false
cover: "/img/screenshots/cargo-deny-advisories.jpg"
description: "How to combine Clippy, rustfmt, cargo-deny, and cargo-audit into a single Rust CI quality gate — with real configuration files and the lint settings that actually pay off."
---

Most Rust projects run `cargo test` in CI and call it quality assurance. Then a dependency picks up a transitive crate with a known CVE, a `clone()` habit creeps into a hot loop, and a contributor reformats half the repository in an unrelated pull request. None of those failures are caught by tests — they are caught by the toolchain nobody wired up.

The Rust ecosystem ships four tools that cover those gaps, and they overlap less than people assume: **Clippy** finds suspicious code, **rustfmt** ends formatting debates, **cargo-deny** enforces dependency policy, and **cargo-audit** checks published vulnerability advisories. This is what each one actually does, how to configure it without drowning in warnings, and how to assemble them into one CI gate that fails fast.

## TL;DR: The Four-Tool Split

**Clippy catches logic smells; rustfmt removes formatting from code review; cargo-deny enforces licence, duplicate, and source policy; cargo-audit reports known vulnerabilities.** Run all four in CI, in that order, cheapest first — `cargo fmt --check` takes under a second, Clippy takes a full compile, and the dependency tools work on `Cargo.lock` without compiling anything.

If you only adopt one thing today: add `cargo clippy --all-targets -- -D warnings` to CI. It is the highest signal-to-effort ratio in the entire toolchain.

| | Clippy | rustfmt | cargo-deny | cargo-audit |
|---|---|---|---|---|
| **Stars** | 13,637 | 7,025 | 2,488 | 1,990 (rustsec/rustsec) |
| **Last push** | 2026-11-10 | 2026-11-10 | 2026-10-26 | 2026-11-11 |
| **License** | Apache-2.0 | Apache-2.0 | Apache-2.0 | Other (RustSec) |
| **Install** | `rustup component add clippy` | `rustup component add rustfmt` | `cargo install cargo-deny` | `cargo install cargo-audit` |
| **Input** | Source code | Source code | `Cargo.lock` + manifests | `Cargo.lock` |
| **Needs compile?** | Yes | No | No | No |
| **Typical CI time** | 30s-5min | <1s | 2-10s | 1-5s |
| **Fails on** | Lints at chosen level | Formatting drift | Banned crates, licences, sources, duplicates | Advisory matches |
| **Config file** | `clippy.toml` | `rustfmt.toml` | `deny.toml` | `.cargo/audit.toml` |

## Decision Matrix: Which Tool for Which Problem

| Problem | Tool | Reason |
|---|---|---|
| Reviewers argue about line width and import order | **rustfmt** | Deterministic output; the debate ends permanently |
| `unwrap()` on user input, needless clones, suspicious casts | **Clippy** | Lint coverage for correctness and performance patterns |
| Two versions of the same crate in the lockfile | **cargo-deny** | `multiple-versions = "deny"` surfaces the tree immediately |
| GPL dependency silently linked into a proprietary binary | **cargo-deny** | Licence allow-list per crate |
| Published CVE in a transitive dependency | **cargo-audit** | Reads the RustSec advisory database |
| Dependency pulled from an unknown git fork | **cargo-deny** | `unknown-git = "deny"` blocks it |
| You want one command that covers all of it | **All four in CI** | They answer different questions |

## Clippy: The Compiler's Opinionated Sibling

Clippy is a lint suite that runs as a compiler driver, so it sees type information — which is why it finds things a regex-based linter never could. It ships with the toolchain, so there is no version skew to manage.

```bash
rustup component add clippy
cargo clippy --all-targets --all-features -- -D warnings
```

`--all-targets` matters: without it, Clippy skips tests, examples, and benchmarks — which is exactly where sloppy `unwrap()` calls accumulate. `-D warnings` promotes every lint to an error, turning the run into a gate instead of a suggestion.

The lint surface is grouped into levels you should treat differently:

```bash
# Correctness and suspicious constructs (default, always on)
cargo clippy -- -D clippy::correctness

# Style and complexity — good for new code, noisy on legacy
cargo clippy -- -W clippy::pedantic

# Restriction lints — opt-in individually, never as a group
cargo clippy -- -D clippy::unwrap_used -D clippy::panic
```

Do not enable `clippy::pedantic` or `clippy::restriction` wholesale on an existing codebase. `restriction` in particular contains mutually contradictory lints and will produce hundreds of warnings on day one, which is how teams learn to ignore Clippy output entirely. A pragmatic configuration in `clippy.toml`:

```toml
# clippy.toml — project-wide lint tuning
too-many-arguments-threshold = 8
type-complexity-threshold = 250
large-error-threshold = 128
disallowed-methods = [
    { path = "std::env::var", reason = "use a typed config loader instead" },
]
```

`disallowed-methods` is the most underused feature in the file: it lets you ban a specific standard-library call project-wide with a reason attached to the error message, which is far more effective than a wiki page nobody reads.

For automatic cleanup of mechanical lints:

```bash
cargo clippy --fix --allow-dirty --all-targets
```

Review the diff before committing. `--fix` handles style and simplification lints but will not silently change behavior — it only applies suggestions marked machine-applicable.

## rustfmt: End the Formatting Argument

rustfmt is the least controversial tool in the list and the one most often missing from CI. The default style is fine; the point is not the style but that it is enforced by a machine rather than by review comments.

```bash
rustup component add rustfmt
cargo fmt --all -- --check
```

`--check` exits non-zero on any drift, which is what you want in CI. Locally, drop the flag to rewrite files in place. A minimal `rustfmt.toml`:

```toml
# rustfmt.toml
edition = "2021"
max_width = 100
use_field_init_shorthand = true
newline_style = "Unix"
```

Two warnings here. First, most `rustfmt.toml` options are **nightly-only** — `imports_granularity`, `group_imports`, and `wrap_comments` are unstable, so setting them on stable silently does nothing. If your CI runs stable, stick to the stable options and do not copy a config from a nightly project.

Second, formatting is only stable if everyone uses the same rustfmt version. Pin the toolchain in `rust-toolchain.toml` so that a CI run and a local run produce byte-identical output:

```toml
# rust-toolchain.toml
[toolchain]
channel = "1.83.0"
components = ["rustfmt", "clippy"]
```

Without this, a contributor on a newer nightly will reformat files that CI then reformats back — a review churn loop that wastes more time than the formatting saved.

## cargo-deny: Policy as a Configuration File

cargo-deny inspects `Cargo.lock` and your manifests without compiling, which makes it fast enough to run on every pull request. It covers four concerns that tests cannot: advisories, licence compliance, dependency bans, and registry provenance.

The configuration below is adapted from cargo-deny's own `deny.toml` — a real-world file from a project that ships to six target platforms:

```toml
# deny.toml
[graph]
targets = [
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
    "x86_64-pc-windows-msvc",
]
all-features = true

[advisories]
unmaintained = "all"
unsound = "all"
ignore = []

[bans]
multiple-versions = "deny"
wildcards = "deny"
deny = [
    { crate = "openssl", use-instead = "rustls" },
    { crate = "openssl-sys", use-instead = "rustls" },
    { crate = "git2", use-instead = "git cli" },
]
skip-tree = [
    { crate = "windows-sys", reason = "foundational crate, bumps constantly" },
]

[sources]
unknown-registry = "deny"
unknown-git = "deny"

[licenses]
allow = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Unicode-3.0"]
confidence-threshold = 0.93
```

Three settings carry most of the value. `multiple-versions = "deny"` catches duplicate crates the moment a dependency bump introduces them — a classic source of bloated binaries and confusing trait mismatches. `unknown-git = "deny"` ensures every dependency resolves through crates.io rather than a random fork. And the licence allow-list turns a legal review that happens once per year into a build-time check that happens on every commit.

`skip-tree` is the escape hatch you will need on day one. `windows-sys` and `getrandom` bump versions faster than the ecosystem can converge, and without a scoped skip the whole check fails on a duplicate you cannot fix.

![cargo-deny bans output](/img/screenshots/cargo-deny-bans.jpg "cargo-deny reporting banned dependency output in a terminal")

Run it with:

```bash
cargo deny check
cargo deny check bans licenses sources   # skip advisories, fastest mode
cargo deny check --format json           # machine-readable for dashboards
```

Note the interaction with `cargo-audit`: cargo-deny's `[advisories]` section covers the same RustSec database. Running both is redundant unless you specifically want cargo-audit's `--json` output or its `Cargo.lock`-only mode in a job that cannot build. Pick one for advisory checking and use cargo-deny for the policy layers around it.

## cargo-audit: Direct CVE Lookup

cargo-audit is the original RustSec client: it reads `Cargo.lock`, compares it against the advisory database, and prints affected crates with the patched version.

```bash
cargo install cargo-audit
cargo audit
cargo audit --json > audit.json
```

Ignore a specific advisory only with a written justification, and only temporarily:

```toml
# .cargo/audit.toml
[advisories]
ignore = [
    "RUSTSEC-2024-0001", # no fix available; crate removed in next major
]
```

The weakness of a bare `cargo audit` run is noise: it reports unmaintained crates and unsound crates alongside exploit-relevant vulnerabilities, so a run can fail for something that cannot be exploited in your usage. That is why the combined configuration above uses cargo-deny's `unmaintained = "all"` deliberately — you want the signal, but you want it in a policy file that documents the exceptions.

## Wiring It Into One CI Gate

Order matters. Formatting is instant, linting is expensive, and dependency policy is cheap — so run them cheapest-first and fail fast:

```yaml
name: quality
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy

      - name: Formatting
        run: cargo fmt --all -- --check

      - name: Dependency policy
        uses: EmbarkStudios/cargo-deny-action@v2

      - name: Lints
        run: cargo clippy --all-targets --all-features -- -D warnings
```

Three practical notes. Cache `~/.cargo` and `target/` or the Clippy step dominates wall-clock time. Pin the toolchain version rather than using `stable`, because new Rust releases add lints and a toolchain bump will fail CI on code nobody touched — that should be a deliberate, separate commit. And run `cargo deny check` before Clippy, so a banned dependency fails in ten seconds instead of after a five-minute compile.

## Pitfalls That Waste Weeks

**Turning on `clippy::pedantic` across a legacy codebase.** You will get hundreds of warnings, add `#![allow(clippy::pedantic)]` at the crate root to silence them, and never look at Clippy again. Enable pedantic lints one at a time, starting with the ones that map to real bugs.

**Using `#[allow(...)]` without a reason.** Every allow attribute is a decision someone will question later. Write `#[allow(clippy::too_many_arguments)] // builder pattern, refactor tracked in #412` or the lint suppression becomes permanent.

**Expecting rustfmt defaults to match your style.** rustfmt is deliberately not configurable on most style points. If your team cannot accept the default, do not adopt rustfmt — a half-enforced formatter creates merge conflicts without ending the debate.

**Running cargo-deny without `skip-tree` on a large workspace.** The first run will fail on duplicate `windows-sys` or `getrandom` versions that no single maintainer controls. Scope the skip to the specific crate and revisit quarterly.

**Confusing "unmaintained" with "vulnerable".** cargo-deny's `unmaintained = "all"` and cargo-audit both flag crates with no maintainer. That is a real risk signal, but it is not a CVE, and treating it as one produces alert fatigue that hides the actual advisories.

**Forgetting that `-D warnings` includes future lints.** A Rust upgrade adds lints, so `-D warnings` turns a routine toolchain bump into a CI failure. Pin the toolchain and upgrade deliberately — the failure is informative, but only if it is not blocking an unrelated release.

**Assuming Clippy sees feature-gated code.** Without `--all-features`, lints inside `#[cfg(feature = "...")]` blocks are skipped entirely. Code that only compiles under a non-default feature is exactly the code most likely to be wrong.

For deeper Rust coverage, see our guides to [error handling with anyhow, thiserror, and eyre](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/), [structured logging with env_logger, log4rs, and tracing](../2026-07-27-rust-logging-libraries-env-logger-log4rs-tracing-slog/), and [web frameworks actix-web vs rocket vs axum](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/).

## FAQ

### Do I need both cargo-deny and cargo-audit?

Usually not. cargo-deny's `[advisories]` section queries the same RustSec database that cargo-audit uses, and it also enforces licence, ban, and source policy in the same run. Keep cargo-audit only if you need its standalone `--json` output or want an advisory check in a job that cannot run the deny configuration.

### Why does `cargo fmt --check` pass locally but fail in CI?

Almost always a rustfmt version mismatch. Local nightly rustfmt applies unstable options that stable rustfmt ignores or formats differently. Pin the toolchain in `rust-toolchain.toml` with the `rustfmt` component so both environments run the same binary.

### Is `-D warnings` too strict for a real project?

It is the right default for the correctness lint group, and it is too strict for pedantic and restriction lints until the codebase is clean. Start with `-D clippy::correctness`, add individual lints as you fix them, and only promote the whole set once the baseline is green.

### How long does the full gate add to CI?

On a mid-sized crate: rustfmt under a second, cargo-deny two to ten seconds, cargo-audit one to five seconds, and Clippy thirty seconds to five minutes depending on cache state. With `target/` cached, Clippy typically lands in the thirty-to-sixty-second range, which is why the dependency checks run first.

### What licence list should go in `[licenses] allow`?

The permissive set covers most projects: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, and Unicode-3.0. Add MPL-2.0 only if you are comfortable with file-level copyleft, and treat GPL and AGPL entries as decisions requiring review rather than entries to append to the allow list.

### Can cargo-deny block a specific crate version rather than the whole crate?

Yes — the `deny` and `skip` entries accept `crate@version` syntax such as `getrandom@0.2.17`, which lets you ban one version while allowing another. This is the correct tool for a known-bad release that is still pulled in transitively.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clippy vs rustfmt vs cargo-deny in 2026: Building a Rust Quality Gate That Catches Real Bugs",
  "description": "How to combine Clippy, rustfmt, cargo-deny, and cargo-audit into one Rust CI quality gate, with real configuration files and lint settings that pay off.",
  "datePublished": "2026-11-11",
  "dateModified": "2026-11-11",
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
