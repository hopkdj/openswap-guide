---
title: "Semantic Versioning Libraries in 2026: node-semver vs Masterminds vs python-semver"
date: "2026-09-27"
tags: ["semver", "developer-tools", "versioning", "go", "python", "javascript", "php", "rust"]
draft: false
cover: "/img/screenshots/semver-specification-logo.jpg"
description: "A hands-on comparison of six Semantic Versioning libraries — npm/node-semver, composer/semver, hashicorp/go-version, Masterminds/semver, dtolnay/semver and python-semver — with real code, live star counts and the range-syntax traps that break deploys."
---

Your release pipeline just published a "patch" that silently deleted an API field. Nobody touched the code. What happened is that a comparator matched `2.0.0-rc.1` against `>=1.0.0 <2.0.0`, a resolver decided the release candidate was good enough, and the deploy bot rolled it out. Version comparison is one of those problems that looks like string manipulation and behaves like a parser spec: six mainstream ecosystems each implement it slightly differently, and the differences are exactly where production breaks.

This article compares the six libraries that actually do the work — **npm/node-semver (5,466 stars), composer/semver (3,308), hashicorp/go-version (1,773), Masterminds/semver (1,439), dtolnay/semver (671) and python-semver (524)** — using live repository data pulled on 2026-09-27 and code lifted straight from each project's own README.

## TL;DR — Quick Verdict

- **JavaScript/Node**: use [npm/node-semver](https://github.com/npm/node-semver). It *is* the reference implementation of npm range syntax and everything else copies it.
- **Go services validating config or user input**: use [Masterminds/semver](https://github.com/Masterminds/semver) — it returns structured validation errors instead of a bare boolean, which is what you want in an API handler.
- **Go tooling that sorts version lists or handles prefixed tags**: use [hashicorp/go-version](https://github.com/hashicorp/go-version) — `version.Collection` plus `WithPrefix` handles Terraform-provider-style tag soup.
- **PHP/Composer**: use [composer/semver](https://github.com/composer/semver) — and use `Intervals::haveIntersections` when you need to know whether two constraints can ever coexist.
- **Rust/Cargo**: use [dtolnay/semver](https://github.com/dtolnay/semver) and accept that it implements *Cargo's* dialect, not npm's.
- **Python**: [python-semver](https://github.com/python-semver/python-semver) for parsing, comparison and bumping — but it ships no constraint parser. If you need ranges in Python you compose them yourself.

Pick one library per language boundary and convert at the edges. Running two comparators in one service is how you get two opinions about the same tag.

## Live Comparison Table (2026-09-27)

| Library | Language | Stars | License | Last commit | Range / constraint syntax | Prerelease handling |
|---|---|---|---|---|---|---|
| npm/node-semver | JavaScript | **5,466** | ISC | 2026-09-10 | caret, tilde, hyphen, x-range, `\|\|` | excluded unless `includePrerelease` |
| composer/semver | PHP | **3,308** | MIT | 2026-09-24 | Composer caret/tilde/wildcard + stability flags | excluded by default, stability flags opt in |
| hashicorp/go-version | Go | **1,773** | MPL-2.0 | 2026-09-03 | comma-separated comparators | prerelease sorts below the release |
| Masterminds/semver | Go | **1,439** | MIT | 2026-08-14 | comma comparators, hyphen, `\|\|` | excluded unless `IncludePrerelease` |
| dtolnay/semver | Rust | **671** | Apache-2.0 | 2026-06-24 | Cargo caret by default + comparators | excluded unless the requirement names one |
| python-semver | Python | **524** | BSD-3-Clause | 2026-09-26 | **none** — comparison API only | you compare explicitly |

All six are actively maintained; python-semver had a commit within the last 24 hours of writing and composer/semver within the last three days. There is no abandoned option in this list, which means the tie-breaker is dialect compatibility, not maintenance risk.

## Decision Matrix

| Your use case | Pick this | Why |
|---|---|---|
| Publishing npm packages or resolving a JS lockfile | npm/node-semver | Byte-for-byte agreement with what `npm install` will do |
| HTTP handler that validates a `min_version` query param | Masterminds/semver | `Validate()` returns `(bool, []error)` — you can return 400 with a real reason |
| Helm/CI tool that sorts messy release tags (`deployment-v1.2.3-beta`) | hashicorp/go-version | `version.WithPrefix` + `version.Collection` sort is built in |
| Deciding whether two dependency constraints can be satisfied together | composer/semver | `Intervals::haveIntersections` / `isSubsetOf` is not offered by the others |
| Cargo build script or Rust CLI parsing `Cargo.toml`-style ranges | dtolnay/semver | Cargo semantics, including its caret rules and `no_std` friendliness |
| Python app that needs to parse, bump and compare versions | python-semver | Explicit `Version` objects; no hidden range magic to get wrong |
| You need ranges **in Python** | python-semver + your own comparison helpers | Stop looking for `satisfies`; it was removed from the modern API |

## The Libraries in Depth

### npm/node-semver — the reference implementation

node-semver is what npm itself uses, which makes it the de facto spec for every JavaScript tool that claims to understand ranges. Install and use it in two lines:

```bash
npm install semver
```

```javascript
const semver = require('semver')

semver.satisfies('1.2.3', '1.x || >=2.5.0 || 5.0.0 - 7.2.3') // true
semver.gt('1.2.3', '9.8.7') // false
semver.lt('1.2.3', '9.8.7') // true
semver.minVersion('>=1.0.0') // '1.0.0'
semver.valid(semver.coerce('v2')) // '2.0.0'
```

Two things about that snippet matter more than they look. First, `minVersion` is the correct way to answer "what is the lowest version that satisfies this range" — do not try to parse the range string yourself, because x-ranges expand to two-sided bounds (`1.x` is defined as `>=1.0.0 <2.0.0-0`). Second, `coerce` is a *repair* function, not a validator: it will happily turn `42.6.7.9.3-alpha` into `42.6.7`, dropping the segments it cannot understand. Never run `coerce` on untrusted input and then treat the result as authoritative.

Prereleases are excluded from range matching by default. If you genuinely want release candidates to satisfy a range, pass the option explicitly rather than widening the range:

```javascript
const semver = require('semver')

// 1.3.0-rc.1 does NOT satisfy ">=1.2.3" by default
semver.satisfies('1.3.0-rc.1', '>=1.2.3') // false

// opt in deliberately, per call site
semver.satisfies('1.3.0-rc.1', '>=1.2.3', { includePrerelease: true }) // true
```

For automated bumps, `inc` accepts a prerelease identifier, so `1.2.3` → `1.2.4-rc.0` → `1.2.4` is a clean state machine — which is exactly what the tooling in our [dependency automation comparison](../2026-04-19-renovate-vs-dependabot-vs-updatecli-self-hosted-dependency-automation-guide-2026/) relies on.

### Masterminds/semver — constraints with real error messages

Masterminds/semver is the Go library you want at an API boundary because it separates the two failure modes: "this string is not a version" and "this version does not satisfy the range".

```go
c, err := semver.NewConstraint(">= 1.2.3")
if err != nil {
    // Handle constraint not being parsable.
}

v, err := semver.NewVersion("1.3")
if err != nil {
    // Handle version not being parsable.
}
// Check if the version meets the constraints. The variable a will be true.
a := c.Check(v)
```

When you need to explain *why* a version was rejected, use `Validate`, which returns the failed comparators as messages:

```go
c, err := semver.NewConstraint("<= 1.2.3, >= 1.4")
// ...
a, msgs := c.Validate(v)
// a is false, msgs holds the reasons
```

Prerelease behaviour is per-constraint via an exported field, so a single service can treat "stable only" and "allow RCs" differently without forking the parsing layer:

```go
// Constraints returned by NewConstraint expose IncludePrerelease.
c.IncludePrerelease = true
```

The one trap in this library is whitespace. Hyphen ranges mean an inclusive set, but only when spaced: `1.2 - 1.4.5` is `>= 1.2 <= 1.4.5`, while `1.2-1.4.5` is parsed completely differently because it is read as a prerelease. If your config files are user-editable, normalise whitespace before parsing.

### hashicorp/go-version — sorting and prefixed tags

Hashicorp's library is the one to reach for when the job is "take this pile of tags and tell me the newest one", including tags that do not look like clean semver.

```go
v1, err := version.NewVersion("1.2")
v2, err := version.NewVersion("1.5+metadata")

// Comparison example. There is also GreaterThan, Equal, and just
// a simple Compare that returns an int allowing easy >=, <=, etc.
if v1.LessThan(v2) {
    fmt.Printf("%s is less than %s", v1, v2)
}
```

Prefixes are handled natively, which matters for infrastructure repositories where the tag is `deployment-v1.2.3-beta+metadata` and the version is buried inside it:

```go
v1, _ := version.NewVersion("deployment-v1.2.3-beta+metadata", version.WithPrefix("deployment-"))
v2, _ := version.NewVersion("deployment-v1.2.4", version.WithPrefix("deployment-"))

if v1.LessThan(v2) {
    fmt.Printf("%s (%s) is less than %s (%s)\n", v1, v1.Original(), v2, v2.Original())
    // Outputs: 1.2.3-beta+metadata (deployment-v1.2.3-beta+metadata) is less than 1.2.4 (deployment-v1.2.4)
}
```

Constraints use plain comma-separated comparators, and sorting a mixed list is a one-liner over `version.Collection`:

```go
v1, err := version.NewVersion("1.2")

constraints, err := version.NewConstraint(">= 1.0, < 1.4")
if constraints.Check(v1) {
	fmt.Printf("%s satisfies constraints %s", v1, constraints)
}
```

```go
versionsRaw := []string{"1.1", "0.7.1", "1.4-beta", "1.4", "2"}
versions := make([]*version.Version, len(versionsRaw))
for i, raw := range versionsRaw {
    v, _ := version.NewVersion(raw)
    versions[i] = v
}
sort.Sort(version.Collection(versions))
```

`v.Original()` is underrated: keep the raw string for display and the parsed struct for logic, and you never have to guess which form you are holding.

### composer/semver — the only one with interval math

composer/semver is extracted from Composer itself and is upfront that it cannot implement semver strictly, because PHP's `version_compare` semantics and years of backwards compatibility constrain it. Two consequences you must know:

```bash
composer require composer/semver
```

1. Numeric versions are normalised to four components — `1.2.3` becomes `1.2.3.0` — for internal consistency with `version_compare`. Normalised strings are for comparison, not for display.
2. Stability (dev/alpha/beta/RC/stable) is part of comparison, not decoration.

Parsing and validation live on `VersionParser` (`isValid`, `normalize`, `normalizeBranch`, `parseConstraints`, `parseStability`), comparison lives on `Comparator`, and set logic lives on `Semver` and `Intervals`:

```php
use Composer\Semver\Comparator;

Comparator::greaterThan('1.25.0', '1.24.0'); // 1.25.0 > 1.24.0
```

```php
use Composer\Semver\Intervals;

// Checks whether $candidate is a subset of $constraint
Intervals::isSubsetOf(ConstraintInterface $candidate, ConstraintInterface $constraint);

// Checks whether $a and $b have any intersection, equivalent to $a->matches($b)
Intervals::haveIntersections(ConstraintInterface $a, ConstraintInterface $b);
```

`haveIntersections` is the feature the other five libraries do not have, and it is the correct way to answer "can these two plugins ever be installed together?" — a question that otherwise turns into a pile of hand-written range algebra.

`Semver::satisfies($version, $constraints)`, `satisfiedBy`, `sort` and `rsort` cover the common cases.

### dtolnay/semver — Cargo's dialect, explicitly

The Rust crate is deliberate about scope: it implements *Cargo's interpretation* of Semantic Versioning, and where ecosystems disagree it follows Cargo. Its own README says that if you are operating on versions from another ecosystem, you want a different library. Take that seriously.

```toml
[dependencies]
semver = "1.0"
```

```rust
use semver::{BuildMetadata, Prerelease, Version, VersionReq};

fn main() {
    let req = VersionReq::parse(">=1.2.3, <1.8.0").unwrap();

    // Check whether this requirement matches version 1.2.3-alpha.1 (no)
    let version = Version {
        major: 1,
        minor: 2,
        patch: 3,
        pre: Prerelease::new("alpha.1").unwrap(),
        build: BuildMetadata::EMPTY,
    };
    assert!(!req.matches(&version));

    // Check whether it matches 1.3.0 (yes it does)
    let version = Version::parse("1.3.0").unwrap();
    assert!(req.matches(&version));
}
```

Note the assertion that a prerelease does *not* match `>=1.2.3, <1.8.0`. That is the same rule npm and Masterminds apply, and it is the rule most people assume is not there.

### python-semver — explicit, no ranges

python-semver follows `MAJOR.MINOR.PATCH` with prerelease and build metadata, and gives you a real `Version` object instead of string helpers:

```python
>>> import semver
>>> ver = semver.Version.parse('1.2.3-pre.2+build.4')
>>> ver.major
1
>>> ver.minor
2
>>> ver.patch
3
>>> ver.prerelease
'pre.2'
>>> ver.build
'build.4'
```

Bumping is immutable and chainable, which makes release scripts trivial to test — `bump_major` returns a new object and leaves the original untouched:

```python
>>> ver = semver.Version.parse("3.4.5")
>>> ver.bump_major()
Version(major=4, minor=0, patch=0, prerelease=None, build=None)
>>> ver.bump_major().bump_minor()
Version(major=4, minor=1, patch=0, prerelease=None, build=None)
```

Comparison returns the usual three-way integer, so it drops directly into `sorted(key=...)` or a filter:

```python
>>> semver.compare("1.0.0", "2.0.0")
-1
>>> semver.compare("2.0.0", "1.0.0")
1
>>> semver.compare("2.0.0", "2.0.0")
0
```

What python-semver does **not** give you is a constraint string parser. You write the comparisons, which is either a feature (nothing hidden) or a chore (you now own the range algebra). When you need npm-style ranges in Python, the honest answer is that you are building a small internal resolver.

## The Five Constraint Dialects on One Table

| Syntax | node-semver | Masterminds (Go) | hashicorp (Go) | composer | Cargo |
|---|---|---|---|---|---|
| `>=1.2.3 <2.0.0` | space = AND | comma = AND (`>= 1.2.3, < 2.0.0`) | comma = AND | space/comma | comma = AND |
| `^1.2.3` | yes | yes | **no** | yes | yes (default for `1.2`) |
| `~1.2.3` | yes | yes | no | yes | yes |
| `1.x` / `1.*` | yes | yes | partial | yes | no |
| `1.2 - 1.4.5` hyphen | yes | yes (whitespace-sensitive) | no | yes | no |
| `\|\|` OR | yes | yes | no | yes | no |
| Prerelease included by default | no | no | no (sorted lower) | no | no |
| Interval/subset math | no | no | no | **yes** | no |

The dialect table is the practical takeaway: Go's hashicorp library and Cargo's requirements deliberately support *fewer* syntax forms. Copying an npm range into a Go config file is the most common way to ship a constraint that parses successfully and means something else.

## Pitfalls That Actually Cost You a Deploy

**1. Prereleases are invisible to ranges.** `>=1.2.3` does not match `1.3.0-rc.1` in any of these libraries. That is correct behaviour and it surprises people every week. If you want release candidates in a channel, opt in per call site (`includePrerelease`, `IncludePrerelease`, or a requirement that names the prerelease) instead of loosening the bound.

**2. `coerce` is lossy by design.** `v2` becomes `2.0.0`, and `42.6.7.9.3-alpha` becomes `42.6.7`. It is a migration tool for messy historical data, never a validator for input you are about to trust.

**3. Whitespace changes meaning in hyphen ranges.** `1.2 - 1.4.5` is an inclusive set; `1.2-1.4.5` is a version with `1.4.5` as prerelease. Normalise whitespace in user-supplied constraints before parsing.

**4. Composer's normalised versions are internal.** `1.2.3` becomes `1.2.3.0`. Show `Original`/raw strings to humans and keep normalised values for comparisons only.

**5. Build metadata is not ordering information.** `1.5+metadata` and `1.5` have the same precedence. Sorting by the raw string will disagree with every library in this table — and with the lockfiles the resolver wrote.

**6. Ecosystem dialects do not compose.** Cargo's caret rules are not npm's, and Composer's stability handling is not a decoration on top of semver. Parse versions with the library of the ecosystem you are *reading from*, then convert to a neutral representation before you compare across boundaries.

**7. Never re-implement comparison with string formatting.** Zero-padded sorting, `v`-prefix stripping and split-on-dot comparison all fail on prereleases, build metadata and four-component versions. Every one of these six libraries exists because that approach was tried first.

## Why Self-Hosted Teams Should Pin One Version Library

If you run your own registry, release automation or CI runners, version comparison is not an abstract concern — it is the code path that decides what your builders download. A self-hosted stack typically has three places where version semantics leak in: the dependency-update bot that proposes bumps, the release pipeline that computes the next tag, and the lockfile/artifact gateway that has to agree with both. When those three use different parsers, you get the classic failure where the bot proposes `2.0.0-rc.1`, CI accepts it because its own check was looser, and the registry faithfully serves it.

The fix is unglamorous: pick one library per language, pin it, and put the constraint strings in version control next to the code that consumes them. Our [release automation comparison](../2026-04-25-goreleaser-vs-semantic-release-vs-changesets-self-hosted-release-automation-guide/) covers the tag-computation half, and the [JavaScript package manager deep dive](../2026-08-31-javascript-package-managers-npm-pnpm-yarn-bun-comparison/) shows how differently npm, pnpm, Yarn and Bun resolve the same range when their lockfiles disagree. Version parsing looks like a solved problem right up until two tools in the same pipeline solve it differently.

For deployment, none of these libraries need a container of their own — they are build-time and request-time dependencies. Pin them in your lockfile like any other dependency, and add one test that asserts your project's own compatibility policy: feed it a prerelease that should be rejected and assert it is rejected. That single test catches a range rewrite that would otherwise ship.

## FAQ

**Is Semantic Versioning parsed identically in every language?**
No. The spec describes precedence rules, not range syntax, and range syntax is where ecosystems diverge. npm's caret, Composer's stability flags, Cargo's requirements and Go's comma-separated comparators are four different grammars. The precedence rules (major, minor, patch, prerelease, ignoring build metadata) are consistent, which is why cross-language comparison of *already-parsed* versions is safe.

**Does `>=1.0.0` match `1.0.0-beta`?**
Not in any of the six libraries by default. Prereleases are excluded from range matching unless you opt in — `{ includePrerelease: true }` in node-semver, `IncludePrerelease` in Masterminds/semver, or naming the prerelease in a Cargo requirement.

**What is the safest way to compare versions from untrusted input?**
Strict-parse first and reject on failure, then compare parsed objects. Avoid `coerce` for anything you intend to trust, because it repairs malformed input by discarding segments. In Go, prefer `NewVersion` plus `NewConstraint` and surface the error from `Validate` to the caller.

**Should I use Masterminds/semver or hashicorp/go-version in Go?**
Masterminds/semver if you need constraint expressions with per-comparator error messages and an `IncludePrerelease` switch. hashicorp/go-version if you need to sort large tag lists or handle prefixed tags such as `deployment-v1.2.4`, where `WithPrefix` and `version.Collection` do the work for you. Both are actively maintained; the choice is about the operations you need, not the library quality.

**Why did python-semver drop range matching?**
The modern API exposes `Version.parse`, `bump_*` and `compare` — explicit operations with no hidden grammar. That removes an entire class of "the range said something I did not expect" bugs, at the cost of you writing the comparisons yourself when you need range behaviour.

**Do these libraries need to run as a service or in a container?**
No. They are ordinary build-time and runtime dependencies: `npm install semver`, `composer require composer/semver`, `go get github.com/Masterminds/semver/v3`, and `semver = "1.0"` in `Cargo.toml` are the whole installation story. Pin them in your lockfile and keep the constraint strings in version control.

**How do I test a compatibility policy without waiting for CI to fail?**
Write one unit test per boundary that asserts a prerelease is rejected by the production range and accepted by the release-candidate range. It runs in milliseconds and catches a rewritten range before it reaches your registry.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Semantic Versioning Libraries in 2026: node-semver vs Masterminds vs python-semver",
  "description": "A hands-on comparison of six Semantic Versioning libraries — npm/node-semver, composer/semver, hashicorp/go-version, Masterminds/semver, dtolnay/semver and python-semver — with real code, live star counts and the range-syntax traps that break deploys.",
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
