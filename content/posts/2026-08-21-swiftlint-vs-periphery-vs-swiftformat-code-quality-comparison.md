---
title: "SwiftLint vs Periphery vs SwiftFormat in 2026: Which Swift Code Quality Tool Should You Use?"
date: "2026-08-21"
tags: ["swift", "code-quality", "linting", "developer-tools", "xcode"]
draft: false
cover: "/img/screenshots/swiftlint-cover.jpg"
---

Your Swift codebase is 200,000 lines, five developers are merging into `main` daily, and the review queue is backed up because every pull request sparks the same argument: "your braces are wrong", "you left an unused function", "this should be a `guard`". Style debates burn more engineering time than any other single source of friction — and the fixes are mechanical. That is exactly the class of problem that tooling should solve, and Swift now has three mature open-source tools that approach it from completely different angles: **SwiftLint**, **Periphery**, and **SwiftFormat**. They are not interchangeable, and most teams reach for only one — which is the mistake.

This guide compares all three with live GitHub data, official setup instructions, and honest trade-offs, then gives you a concrete pipeline that combines them so the arguments stop happening at review time.

## TL;DR — Quick Verdict

If you can only adopt one tool, **SwiftLint** is the default choice: it has the largest rule set, the biggest community, and it plugs into Xcode, CI, and pre-commit in minutes. Add **SwiftFormat** when you want deterministic, opinionated formatting that ends whitespace debates permanently — run it with `--lint` in CI so it only reports, never rewrites, on pull requests. Add **Periphery** only if you are serious about removing dead code: it catches unused declarations that neither linter nor formatter will ever see, at the cost of a full build per scan. A pragmatic 2026 stack is SwiftLint + SwiftFormat in CI and Periphery in a nightly or pre-release job.

## Swift Code Quality Tools at a Glance

| Tool | SwiftLint | Periphery | SwiftFormat |
|---|---|---|---|
| **What it does** | Lints style + correctness rules | Detects unused (dead) code | Formats code deterministically |
| **GitHub repo** | realm/SwiftLint | peripheryapp/periphery | nicklockwood/SwiftFormat |
| **Stars (Aug 2026)** | 19,702 | 6,186 | 8,915 |
| **Last push (Aug 2026)** | 2026-08-09 | 2026-08-12 | 2026-08-20 |
| **Language** | Swift | Swift | Swift |
| **License** | MIT | MIT | MIT |
| **Install** | Homebrew / Mint / pre-commit | Homebrew / Mint | Homebrew / Mint / Xcode extension |
| **Modes** | lint, autocorrect, analyze | scan | format, lint (check-only), infer |
| **Requires a build?** | No (analyzer rules: yes) | **Yes — full build (index store)** | No |
| **Xcode integration** | Built-in plugin + warning banners | CLI / CI | Built-in Xcode extension |
| **Best for** | Enforcing style + catching bugs | Removing dead code | Ending formatting debates |

## Decision Matrix: Which Tool for Which Situation?

| Use Case | Recommendation | Why |
|---|---|---|
| One tool, zero budget, maximum value | **SwiftLint** | 400+ rules, huge community, catches real bugs (`force_unwrapping`, `empty_count`) not just style |
| Formatting wars in code review | **SwiftFormat** | Deterministic output; `swiftformat --lint` reports without rewriting, so CI can gate on it |
| Dead code piling up in a mature app | **Periphery** | Static analysis alone can't see cross-file dead references; index-store graph analysis can |
| Strict enterprise compliance / style guide | **SwiftLint + SwiftFormat** | Linter enforces the rules, formatter enforces the whitespace; complementary, not overlapping |
| Greenfield project, opinionated defaults | **SwiftFormat + SwiftLint (opt-in rules)** | Start with defaults, add `opt_in_rules` as the team matures |

## SwiftLint — The Community Standard

SwiftLint is the oldest and most widely adopted tool in this trio, maintained by Realm. Its core idea is simple: a YAML-configured rule engine with **400+ built-in rules** covering style (naming conventions, whitespace), correctness (force unwrapping, retain cycles, empty collections), and performance traps. It runs directly on your source tree — no build required — and integrates with Xcode natively: violations surface as inline warnings and can be configured to break the build.

```bash
# Install via Homebrew
brew install swiftlint

# Run it
swiftlint lint        # report violations
swiftlint autocorrect # fix what can be fixed safely
swiftlint analyze     # run analyzer rules (requires a build)
```

Configuration lives in a `.swiftlint.yml` file at your project root. The documented rule-inclusion model is worth understanding before you touch it: `disabled_rules` removes rules from the default set, `opt_in_rules` enables rules that are deliberately off by default (usually because they produce false positives like `empty_count`, or are too opinionated like `force_unwrapping`), and `only_rules` replaces the entire set — and cannot be combined with the other two.

```yaml
disabled_rules:
  - trailing_whitespace
  - line_length
opt_in_rules:
  - empty_count
  - force_unwrapping
  - private_over_fileprivate
analyzer_rules:
  - unused_import
excluded:
  - .build
  - DerivedData
  - Pods
```

For one-off violations, SwiftLint supports inline control — `// swiftlint:disable force_unwrapping` scoped to a line or a region — which is the idiomatic escape hatch when a rule is genuinely wrong for one spot in your code. The project also ships a first-party pre-commit hook, pinned by revision so your team all runs the same rules:

```yaml
repos:
  - repo: https://github.com/realm/SwiftLint
    rev: 0.57.1
    hooks:
      - id: swiftlint
```

**The 2026 reality:** SwiftLint remains the safest first adoption because the ecosystem around it — editor plugins, CI actions, Danger integration — dwarfs the alternatives, and its `analyzer_rules` (like `unused_import`) give you a taste of compiler-index-powered analysis without committing to Periphery's build cost.

## Periphery — Find the Dead Code Nobody Admits Exists

Periphery solves a problem that no linter can: **unused code that spans files**. Every mature Swift project accumulates dead types, functions, and properties — the leftovers of features that shipped, pivoted, or died. The compiler won't warn you about most of them (they're internal, so they compile fine), and grep-based searches produce noise because identifiers are reused. Periphery's approach is fundamentally different: it **builds your project**, reads the resulting *index store* (the same on-disk data Xcode uses for navigation and rename), builds an in-memory graph of every declaration and every reference, and traverses the graph from entry points to find declarations nothing references.

```bash
# Install
brew install periphery

# Guided first scan — detects project type and prints the full command
periphery scan --setup

# Typical Xcode project scan
periphery scan --project MyApp.xcodeproj --schemes MyApp --targets MyApp --format xcode
```

The key practical detail is that the index store only contains source files that were **compiled during the scan's build**. If a class is referenced only from a file that wasn't part of the build, Periphery will flag it as unused — a false positive you can avoid by listing every scheme that matters. For projects that ship standalone frameworks, the `--retain-public` flag tells Periphery to treat all public API as used (consumers outside the project reference it). Mixed Objective-C and Swift projects need extra care, because ObjC can reach Swift declarations dynamically; the README dedicates an entire section to the implications.

```bash
# Non-Xcode projects (e.g., Bazel, CMake): point at a JSON config
periphery scan --generic-project-config config.json

# Force a clean rebuild of the index store after an interrupted scan
periphery scan --clean-build
```

**The trade-off to understand:** every scan is a full build. That's seconds-to-minutes on every CI run, which is why Periphery fits a nightly or pre-release job better than a per-commit gate. It also has real blind spots — code reached only through runtime string selectors, storyboard identifiers, or preprocessor branches that aren't compiled (debug vs release) will be reported as unused. `--clean-build` is the documented fix when a force-terminated scan leaves the index store corrupt and results start pointing at wrong locations. At 6,186 stars with regular pushes, it is actively maintained and now supports Linux for Swift Package Manager projects — useful if your CI runs on Linux runners.

## SwiftFormat — Deterministic Formatting, No Debate

SwiftFormat is the peacemaker. Where SwiftLint tells you *what's wrong* and Periphery tells you *what's dead*, SwiftFormat rewrites your code to a canonical style. It's a formatter in the gofmt/prettier tradition: given the same input, it always produces the same output, so the whitespace-and-braces part of code review simply disappears. It supports an enormous range of configurable options (indentation width, semicolon policy, operator spacing, `guard let` vs `if let` rewrites) and can infer your existing style from a codebase so the first run doesn't explode your diff.

```bash
# Install
brew install swiftformat

# Format everything in the current directory (and subdirectories!)
swiftformat .

# Safe first run: infer a config that matches your existing style
swiftformat --infer-options "/path/to/your/code/"

# CI mode: only check, never rewrite
swiftformat --lint .
```

The README's warning is worth quoting in full: **`swiftformat .` will overwrite any Swift files it finds in the current directory, and any subfolders therein** — if you run it in your home directory, it will reformat your entire hard drive. Always point it at a project directory, run `--infer-options` first, and use source control to review the diff before committing. For scripted pipelines, stdin/stdout mode is handy:

```bash
cat /path/to/file.swift | swiftformat --output /path/to/file.swift
```

Configuration is a `.swiftformat` file auto-discovered in the project root, and options can be disabled per rule (`--disable`), which matters when a default rule conflicts with your team's style. A dedicated Xcode extension ships with the app so formatting runs on save if you want it. The sweet spot in 2026: run `swiftformat --lint` in CI as a hard gate (zero maintenance once configured), and let developers run `swiftformat .` locally before pushing — the two never disagree because the output is deterministic.

## Common Pitfalls and How to Avoid Them

**1. Lint and format overlap.** If you enable formatting-style rules in SwiftLint *and* run SwiftFormat, they can fight each other — SwiftFormat rewrites a line, SwiftLint flags the result. Keep SwiftLint focused on semantic rules and let SwiftFormat own whitespace and layout. The two projects' rule sets overlap (both cover trailing whitespace, for example); pick one owner per rule.

**2. Forgetting generated and dependency code.** `Pods/`, `.build/`, `DerivedData`, and Tuist/XcodeGen-generated files will produce thousands of violations. Both SwiftLint (via `excluded:`) and SwiftFormat (via path arguments) need your generated directories in their ignore lists, or the noise buries real findings.

**3. Periphery's build dependency surprises people.** A scan that doesn't compile a target will report everything in it as unused. If your CI scans without building all schemes — or builds only a Debug config — you'll see false positives on release-only code guarded by `#if DEBUG` preprocessor branches.

**4. Deleting "unused" code that isn't.** Periphery can't see ObjC selectors, storyboard/nib references, `@objc` exposure, or runtime string lookups. Treat its output as a strong candidate list, not a delete order — especially in mixed-language codebases. The README's `--retain-public` flag exists precisely because removing public API from frameworks breaks external consumers.

**5. Autocorrect in CI is a footgun.** `swiftlint autocorrect` and `swiftformat .` mutate files — running them silently in CI can commit changes nobody reviewed. Use `--lint`-style check-only modes in CI, and let developers run the mutating commands locally.

**6. Rule-drift across the team.** SwiftLint rules change between versions; pin your tool versions (the pre-commit `rev:` field exists for exactly this) or two developers will get different results from the "same" config. The same logic applies to SwiftFormat's options file — commit it, don't recreate it per machine.

## Building a Complete Quality Pipeline

The three tools are complementary, and the modern setup wires them in sequence. A pre-commit hook runs **SwiftFormat** first (fast, rewrites), then **SwiftLint** (catches what formatting can't, autocorrects trivial fixes), and blocks on remaining violations. CI runs the same two in `--lint`/check-only mode plus a test build, so the merge gate is deterministic. **Periphery** runs in a separate nightly or release-prep job: its output becomes a ticket backlog of dead code to remove, not a per-commit blocker. This division of labor — formatter for layout, linter for style and correctness, index-based analysis for dead code — is the only combination that removes all three categories of review noise.

Swift tooling pairs naturally with the rest of the ecosystem we've covered elsewhere on this site: installing all three tools cleanly requires a solid [Swift Package Manager setup](../2026-07-31-swift-package-managers-spm-cocoapods-carthage/), and quality gates work best when your [Swift testing frameworks](../2026-07-23-swift-testing-frameworks-xctest-quick-nimble-snapshottesting/) and [Swift logging libraries](../2026-08-13-swift-logging-libraries-swiftlog-cocoalumberjack-swiftybeaver/) follow the same pinned, tooled approach. If you're on a server-side Swift stack, the same trio applies to [Vapor and Hummingbird projects](../2026-07-06-swift-server-side-frameworks-vapor-hummingbird-grpc-swift/) without modification.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SwiftLint vs Periphery vs SwiftFormat in 2026: Which Swift Code Quality Tool Should You Use?",
  "description": "Deep comparison of SwiftLint, Periphery, and SwiftFormat with live GitHub stats, official setup instructions, and a complete 2026 Swift code quality pipeline.",
  "datePublished": "2026-08-21",
  "dateModified": "2026-08-21",
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

### Can SwiftLint, Periphery, and SwiftFormat be used together?

Yes — and that's the recommended setup. SwiftFormat owns whitespace and layout, SwiftLint owns style and correctness rules, and Periphery finds unused declarations across files. Their rule sets overlap slightly (both handle trailing whitespace), so disable the redundant rule in one of them. The only tool that genuinely conflicts with the others is running two formatters; these three each do a distinct job.

### Does Periphery require a full build on every scan?

Yes. Periphery compiles your project to produce the index store, then analyzes the reference graph. That means a scan takes as long as a build — seconds to minutes. It's the reason Periphery fits a nightly or release-prep job rather than a per-commit gate. The `--clean-build` flag forces a rebuild when the index store is corrupt or out of sync.

### What's the difference between SwiftLint autocorrect and SwiftFormat?

SwiftLint's autocorrect fixes only the subset of lint violations that can be safely machine-repaired (whitespace, some naming issues). SwiftFormat rewrites entire files to a canonical style and supports broad structural transforms — indentation, spacing, semicolons, `guard` conversion. SwiftFormat is deterministic and configurable via `.swiftformat`; SwiftLint's corrections are a side effect of its rule engine.

### Does SwiftLint need an Xcode project to work?

No. SwiftLint operates on source files directly, which is why it works with Swift Package Manager projects, server-side Swift (Vapor, Hummingbird), and CI on Linux. Only its `analyzer_rules` (like `unused_import`) require a build — those run via `swiftlint analyze` and need an Xcode project. Periphery also supports SPM projects but on Linux supports only SPM, not Xcode projects.

### How do I stop SwiftFormat from reformatting my entire disk?

`swiftformat .` formats the current directory and everything below it. Run it inside your project directory, verify the path before executing, and use `--infer-options` on the first run so it matches your existing style and produces a minimal diff. For CI, use `swiftformat --lint .` which only reports.

### Which tool catches unused functions in Swift?

Periphery is the only one of the three that detects cross-file dead code. SwiftLint has an `unused_import` analyzer rule and a few local unused-declaration checks, but it can't build the reference graph that Periphery constructs from the index store. That graph-based traversal is what makes Periphery unique in the Swift ecosystem.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
