---
title: "Rust Supply-Chain Security in 2026: cargo-audit vs cargo-deny vs cargo-geiger — Which One Should You Actually Use?"
date: "2026-08-19"
tags: ["rust", "supply-chain-security", "security", "cargo", "developer-tools"]
draft: false
---

Rust's safety guarantees stop at the boundary of your own code. The moment you add a dependency, you inherit the implementation choices of every crate in the tree — and the Rust ecosystem has learned that lesson the hard way. Typosquatted crates with malicious payloads, compromised maintenance accounts, and a steady stream of `RUSTSEC` advisories for widely used libraries like `serde` and `tokio` have made supply-chain auditing a mandatory part of Rust CI. Three tools dominate the space: **cargo-audit** (the RustSec advisory scanner), **cargo-deny** (Embark Studios' all-in-one policy engine), and **cargo-geiger** (the unsafe-code radar). They overlap less than you think, and production teams typically end up using more than one.

## TL;DR: Quick Verdict

- **cargo-audit** is the baseline: it checks your `Cargo.lock` against the RustSec advisory database and tells you what is vulnerable. Install it, run it in CI, and treat any `cargo audit` failure as a blocking issue.
- **cargo-deny** is the enforcer: it does advisories *plus* license compliance, crate bans, duplicate-version checks, and source registry restrictions from a single `deny.toml` policy file. If you need license governance or a hardened crate allowlist, this is your tool.
- **cargo-geiger** is the visibility tool: it counts `unsafe` usage across your entire dependency tree so you know how much of what you ship sits outside the borrow checker's protection. It informs risk review rather than blocking CI.

**The 2026 answer: run all three.** cargo-audit in CI as a hard gate, cargo-deny for policy (licenses + bans + advisories in one place), and cargo-geiger as a quarterly manual review aid. If you can only adopt one, start with cargo-deny — it subsumes cargo-audit's advisory checking and adds the policy layer.

## Comparison at a Glance

| Feature | cargo-audit (RustSec) | cargo-deny (Embark) | cargo-geiger |
|---|---|---|---|
| **Primary job** | Scan for known vulnerabilities | Policy enforcement: advisories + licenses + bans + sources | Detect unsafe code usage in deps |
| **Stars** | 1,935 (rustsec/rustsec) | 2,404 | 1,644 |
| **Last update** | Aug 2026 | Aug 2026 | Jun 2026 |
| **Data source** | RustSec advisory-db | RustSec + SPDX license db | Local source analysis |
| **Checks vulnerabilities** | ✅ `cargo audit` | ✅ `cargo deny check advisories` | ❌ |
| **License compliance** | ❌ | ✅ `check licenses` | ❌ |
| **Crate bans / allowlists** | ❌ | ✅ `check bans` | ❌ |
| **Registry source rules** | ❌ | ✅ `check sources` | ❌ |
| **Unsafe usage metrics** | ❌ | ❌ | ✅ `cargo geiger` |
| **CI-friendly exit codes** | ✅ | ✅ | ⚠️ (informational) |
| **License** | Apache-2.0/MIT | Apache-2.0/MIT | MIT/Apache-2.0 |

## Decision Matrix: Which Tool for Your Use Case?

| Use Case | Recommended Tool | Why |
|---|---|---|
| Minimal CI gate: "are any of my deps vulnerable?" | **cargo-audit** | One command, one data source (RustSec advisory-db), clear blocking failures |
| Company policy: licenses, banned crates, duplicate versions | **cargo-deny** | Single `deny.toml` encodes license allowlists, ban rules, and advisory policy |
| Auditing a dependency-heavy app for unsafe code risk | **cargo-geiger** | Counts `unsafe` blocks per crate so you can review high-risk leaves of the tree |
| Open-source library with strict license obligations | **cargo-deny** | `check licenses` catches GPL/AGPL drift before release, not after a legal complaint |
| Full hardened pipeline (recommended baseline) | **cargo-deny + cargo-audit** | cargo-deny for policy, cargo-audit as the dedicated advisory gate with `fix` support |
| Supply-chain review before every release | **All three** | advisories (what is broken), policy (what is allowed), unsafe metrics (what is risky) |

## cargo-audit: The Vulnerability Baseline

cargo-audit is the RustSec project's official scanner. It reads your `Cargo.lock`, matches every package against the RustSec advisory database (`rustsec/advisory-db`), and reports known vulnerabilities with their `RUSTSEC-YYYY-NNNN` identifiers, affected versions, and patched versions. It is deliberately single-purpose — and that focus makes it the most trustworthy first line of defense.

```shell
cargo install cargo-audit
```

```shell
# Scan the current project
cargo audit

# Scan without touching the network (use a local/cached advisory db)
cargo audit --offline

# Show only JSON output for custom tooling
cargo audit --json
```

When a vulnerability is found, output looks like this:

```text
Crate:     serde_yaml
Version:   0.9.29
Title:     Uncontrolled recursion leading to abort in Deserializer::deserialize_any
Date:      2024-07-10
ID:        RUSTSEC-2024-0006
URL:       https://rustsec.org/advisories/RUSTSEC-2024-0006
Solution:  Upgrade to >= 0.9.34
```

The killer feature is `cargo audit fix`:

```shell
# Show what would change without changing anything
cargo audit fix --dry-run

# Actually update Cargo.lock to patched versions where possible
cargo audit fix
```

`fix` rewrites `Cargo.lock` to the nearest patched versions that still satisfy your semver constraints — often a zero-code-change resolution to a vulnerability. In CI, `cargo audit` returns a non-zero exit code when any advisory affects your lockfile, which makes it a perfect hard gate:

```yaml
# .github/workflows/security.yml
name: Security
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: rustsec/audit-action@v2
```

The limitation is scope: cargo-audit only knows what is in the advisory database. It will not tell you about license violations, duplicate crate versions, or unsafe code — and if a crate is compromised but no advisory has been filed yet, cargo-audit stays silent. It answers one question perfectly: *"do my dependencies have known, published vulnerabilities?"*

## cargo-deny: The Policy Enforcer

cargo-deny, from Embark Studios, is a Cargo plugin that consolidates four checks under one configuration file: **advisories** (same RustSec database), **licenses** (SPDX matching against your allowlist), **bans** (blocklisted crates, duplicate versions, wildcard deps), and **sources** (which registries are permitted). It was born from the observation that license compliance and dependency governance were being handled with ad-hoc scripts across projects.

```shell
cargo install --locked cargo-deny
```

```shell
# Generate a starter deny.toml
cargo deny init

# Run every check
cargo deny check

# Or target individual checks
cargo deny check advisories
cargo deny check licenses
cargo deny check bans
cargo deny check sources
```

The `deny.toml` policy file is where cargo-deny becomes a governance tool rather than a scanner:

```toml
[advisories]
db-path = "~/.cargo/advisory-db"
yanked = "deny"  # deny yanked crates in the tree

[bans]
multiple-versions = "warn"  # flag duplicate versions of the same crate
wildcards = "deny"          # no `*` version requirements

[licenses]
allow = ["MIT", "Apache-2.0", "BSD-3-Clause"]
deny = ["GPL-3.0", "AGPL-3.0"]
copyleft = "deny"
```

This is the tool that catches the things vulnerability scanners never will: a transitive dependency that pulled in a `*` version requirement, a duplicate `tokio` major version quietly doubling your compiled code, or an AGPL crate in a commercial product. cargo-deny's GitHub Action (`EmbarkStudios/cargo-deny-action`) runs all four checks in CI and renders a summary comment on PRs.

The trade-off is configuration burden: `cargo deny init` generates a policy, but you must curate the license allowlist for your project's reality (a large dependency tree typically needs a few common permissive licenses plus a `confidence` threshold for ambiguous matches). Teams that skip the curation step find themselves triaging false positives; teams that invest an hour get a repeatable policy that runs everywhere.

## cargo-geiger: The Unsafe-Code Radar

cargo-geiger answers a question the other two cannot: **how much `unsafe` code is in my dependency tree, and where?** Rust's safety story is that `unsafe` is contained and reviewable — but you cannot review what you cannot see. cargo-geiger statically analyzes every crate in the tree and counts `unsafe fn`, `unsafe impl`, `unsafe trait`, and bare `unsafe { }` blocks, then aggregates the results per crate.

```shell
cargo install --locked cargo-geiger
```

```shell
# Scan the whole dependency tree (use --all-features for full coverage)
cargo geiger --all-features
```

The output is a per-crate table:

```text
Crate                              Safe  Unsafe  UFn  UImpl  UTrait  Metrics
libc                                ✓✓✓    ✓       3     0      0
winapi                              ✓✓     ✓✓     61    0      0
memchr                              ✓✓✓    ✓       0     0      0
crossbeam-utils                     ✓✓     ✓✓     12     1      0
```

Each cell in the metrics columns shows the count of unsafe functions, implementations, and traits — letting you spot the leaf crates carrying the most risk. The workflow is a *review aid*, not a gate: you run it, look at the high-unsafe crates, verify they are widely deployed and actively maintained (a `libc` or `winapi` with lots of unsafe is expected and fine; an obscure single-purpose crate with hundreds of unsafe blocks is worth a hard look), and record the review in your release notes.

cargo-geiger is deliberately informational — its output is a table, not a pass/fail, and forcing it into CI as a gate produces noise rather than security. Use it quarterly, at dependency-tree milestones, and before adopting a new heavy dependency. Combined with cargo-audit and cargo-deny, it turns "we scanned for vulnerabilities" into "we know what is broken, what is allowed, and what is risky."

## Building a Layered Defense: The 2026 CI Baseline

A pragmatic pipeline combines all three without letting any single tool become a bottleneck:

1. **On every push/PR**: run `cargo deny check` (advisories + licenses + bans + sources) via `EmbarkStudios/cargo-deny-action`. Fail the build on denied advisories, license violations, and yanked crates.
2. **On every push/PR**: run `cargo audit` via `rustsec/audit-action` as an independent advisory gate. Duplication with cargo-deny's advisory check is intentional — two scanners, one database, zero excuses.
3. **Weekly (scheduled)**: run `cargo audit` on the main branch to catch advisories published since the last PR, and run `cargo geiger --all-features` to review unsafe-usage drift after dependency updates.
4. **Before release**: re-run everything, review the geiger table for new high-unsafe crates, and check that `Cargo.lock` has no `cargo audit fix` actions pending.

The full flow is documented in our [supply-chain security guide for signed artifacts](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/) — the signing side (cosign, notation, in-toto) protects your *published* artifacts, while the three cargo tools protect your *dependency tree* before anything ships.

## Common Pitfalls and Hard-Won Lessons

**1. The advisory database only knows what it knows.** A zero-clean `cargo audit` does not mean "safe" — it means "no published advisories match." Recent Rust ecosystem incidents showed the gap between *detection* and *publication*: a compromised crate can sit in the tree while the advisory is still being drafted. Layered checks (geiger for unsafe, deny for policy) are the mitigation.

**2. `cargo audit` needs network or a fresh advisory-db.** The default `cargo audit` clones/updates `rustsec/advisory-db` on first run. In offline CI runners, use `cargo audit --offline` and keep the DB updated in your base image, or the scan silently checks a stale database.

**3. cargo-deny license false positives are a curation problem, not a bug.** SPDX matching flags "unknown" licenses and unusual combinations (e.g., "MIT OR Apache-2.0" vs plain "MIT"). Budget time to maintain `deny.toml` — set `confidence = 0.8` for ambiguous matches and add explicit `exceptions` for crates you have manually reviewed.

**4. `multiple-versions = "warn"` hides real bloat.** Two versions of `serde` in one tree is a compile-time warning you should actually fix: it means some dependency pins an older major/minor. cargo-deny shows the dependency path for each duplicate — use `cargo tree -i <crate>@<version>` to find and eliminate the culprit.

**5. cargo-geiger numbers are an upper bound.** Static analysis over-counts unsafe in macros and generated code (e.g., `#[derive]` output, bindgen-generated FFI). Use the table to *prioritize review*, not to rank crates as "good" or "bad" by raw counts.

**6. `cargo deny init` defaults are permissive on purpose.** The generated `deny.toml` allows common permissive licenses and warns (not denies) on several categories. A hardened policy requires editing `[licenses]` (copyleft, deny list), `[bans]` (wildcards, yanked), and `[sources]` (restrict registries to crates.io) — the template is a starting point, not a security control.

**7. Tool version drift.** `cargo install` binaries go stale fast; advisories published after your last install are invisible. Prefer the CI actions (which pin recent releases) and upgrade local tools monthly (`cargo install cargo-audit cargo-deny cargo-geiger --locked`).

**8. Do not ignore `RUSTSEC` warnings in transitive deps "just for now."** The `cargo audit fix` path exists precisely because patching a transitive lockfile entry is cheap. A suppressed advisory is a liability that survives for years — and if you self-host a crate registry, see our [Rust crate registry comparison](../2026-06-16-self-hosted-rust-crate-registries-kellnr-alexandrie-panamax/) for where mirroring fits into this pipeline.

## FAQ

**What is the difference between cargo-audit and cargo-deny?**
cargo-audit is a focused vulnerability scanner using the RustSec advisory database. cargo-deny is a policy engine that checks advisories *plus* licenses, crate bans, duplicate versions, and registry sources from one `deny.toml`. cargo-deny can replace cargo-audit's advisory checking, but many teams run both as independent gates.

**How do I add vulnerability scanning to my Rust CI?**
Use the `rustsec/audit-action` GitHub Action for cargo-audit and/or `EmbarkStudios/cargo-deny-action` for cargo-deny. Both run on every push/PR and fail the build when their respective checks fail. A scheduled weekly run catches advisories published between PRs.

**Is cargo-geiger a security scanner?**
Not in the vulnerability sense. It statically counts `unsafe` usage across your dependency tree to help you review which crates carry the most risk outside the borrow checker's guarantees. It does not detect vulnerabilities or enforce policy.

**Do I need all three tools?**
For production Rust, yes — they cover different layers: cargo-audit (known vulnerabilities), cargo-deny (policy: licenses, bans, sources), cargo-geiger (unsafe-code risk visibility). If you must start with one, cargo-deny gives the broadest coverage per tool.

**What does `cargo audit fix` do?**
It rewrites `Cargo.lock` to the nearest versions that resolve the advisory while respecting your semver constraints — often with zero code changes. Always run `cargo audit fix --dry-run` first to review what will change.

**How do these tools handle private/self-hosted registries?**
cargo-deny's `[sources]` section explicitly controls which registries are allowed (e.g., crates.io, your private mirror). cargo-audit checks advisories by crate name/version regardless of registry. For mirroring strategy, see our [self-hosted crate registries guide](../2026-06-16-self-hosted-rust-crate-registries-kellnr-alexandrie-panamax/).

**Which has more stars: cargo-deny or cargo-audit?**
cargo-deny leads with 2,404 stars, followed by the rustsec/cargo-audit monorepo at 1,935 and cargo-geiger at 1,644. Both cargo-audit and cargo-deny are actively maintained as of August 2026; cargo-geiger's last release is June 2026.

**Can these tools be used outside GitHub Actions?**
Yes — all three are plain Cargo plugins (`cargo audit`, `cargo deny`, `cargo geiger`) that work in any CI system, GitLab CI, Buildkite, or a cron job. The GitHub Actions just package the install step for you.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Supply-Chain Security in 2026: cargo-audit vs cargo-deny vs cargo-geiger — Which One Should You Actually Use?",
  "description": "Deep comparison of cargo-audit, cargo-deny, and cargo-geiger for Rust supply-chain security: vulnerability scanning with the RustSec advisory database, license and ban policy enforcement, and unsafe-code visibility, with CI setup examples.",
  "datePublished": "2026-08-19",
  "dateModified": "2026-08-19",
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
