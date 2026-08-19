---
title: "Kotlin Linting in 2026: detekt vs ktlint vs Spotless — Which Tool Actually Keeps Your Code Clean?"
date: "2026-08-20"
tags: ["kotlin", "linting", "static-analysis", "code-quality", "gradle", "developer-tools"]
draft: false
cover: "/img/screenshots/detekt-cover.png"
---

A Kotlin codebase starts clean, and within six months it is a battlefield: half the team formats with Android Studio's auto-indent, a reviewer keeps moving braces around in comments, and the `when` expressions nobody dares to touch have grown to 400 lines. If you have ever merged a pull request and then watched the style war erupt in the comments, you know the fix is not another convention meeting — it is a tool that enforces the rules mechanically. The problem is that Kotlin developers now have **three serious options** — detekt, ktlint, and Spotless — and they overlap just enough to make the choice confusing.

Here is the data that matters before we compare: **detekt has 7,031 stars, ktlint 6,733, and Spotless 5,617**, and all three were pushed to within the last 24 hours as of this writing (August 2026). All three are actively maintained, all three are free, and all three will happily fail your CI build. But they enforce *different things* in *different ways*, and picking the wrong combination wastes weeks. This guide gives you a decisive answer for your team size, your build system, and your tolerance for configuration.

## TL;DR — Quick Verdict

If you can only install one tool, install **ktlint** — it is zero-config, follows the official Kotlin coding conventions, and its built-in formatter means your team never argues about whitespace again. If you want to catch actual bugs and code smells, not just formatting, add **detekt** alongside it: its 600+ rules (complexity, potential bugs, coroutines) find problems that ktlint is not designed to look for. If you have a polyglot repo (Kotlin + Java + Python + frontend files in one Gradle build), choose **Spotless** as the single formatting gateway and plug ktlint into it. The winning setup for most teams: **ktlint for formatting + detekt for static analysis**, both wired into CI, with Spotless only when other languages share the repository.

## Quick Comparison Table

| Feature | detekt | ktlint | Spotless |
|---|---|---|---|
| Primary job | Static code analysis (smells, bugs, complexity) | Formatting + style linting | Formatting engine (multi-language) |
| GitHub stars | 7,031 | 6,733 | 5,617 |
| License | Apache-2.0 | MIT | Apache-2.0 |
| Last push | 2026-08-19 | 2026-08-19 | 2026-08-19 |
| Config file | `detekt.yml` (rule sets, thresholds) | `.editorconfig` (shared with IDE) | Gradle `spotless {}` block |
| Rule count | 600+ rules in ~19 rule sets | Standard + experimental sets (style-focused) | N/A (delegates to ktlint/ktfmt) |
| Auto-fix / format | No (reports only) | Yes — `ktlint --format` | Yes — `spotlessApply` |
| Report formats | HTML, Markdown, SARIF, XML, TXT | plain, json, html, checkstyle | N/A (console + custom) |
| Baseline / ratchet | Baseline XML to onboard legacy code | N/A | `ratchetFrom` to only check changed lines |
| Best for | Finding real defects and complexity hotspots | Enforcing one consistent style everywhere | Polyglot repos, license headers, import order |

## Use Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Greenfield Kotlin project, want style enforced with zero setup | **ktlint** | Defaults match the official Kotlin style guide; one command formats the whole repo |
| Legacy codebase with existing violations, need to stop the bleeding | **detekt + baseline** | Generate a baseline once, then CI only fails on *new* issues |
| Catch bugs like empty catch blocks, unsafe casts, complexity explosions | **detekt** | `potential-bugs` and `complexity` rule sets go far beyond style |
| Monorepo mixing Kotlin, Java, TypeScript, Python | **Spotless** | One Gradle plugin covers every language with `spotlessApply` |
| Enforce license headers and import ordering | **Spotless** | `licenseHeaderFile()` and `importOrder()` are first-class features |
| Android or Kotlin Multiplatform module | **ktlint + detekt** | Both integrate with Gradle; detekt supports type resolution per source set |
| You want CI to refuse ugly code, not just warn | **Any — but wire it to fail** | All three support `check`-task integration; failing the build is the point |

## detekt — The Static Analysis Powerhouse

detekt's tagline is "static code analysis for Kotlin," and it takes the role seriously. Where a formatter only cares about how code *looks*, detekt cares about how code *behaves*. Its rule catalog spans complexity (nested blocks, long methods, cyclomatic complexity), coroutines (`GlobalScope` usage, unsafe suspending calls), potential bugs (empty `catch` blocks, `equals` on enums, `Double` comparisons), exceptions, naming, and performance. That is why it pairs so naturally with ktlint: one tool fixes the style, the other finds the defects.

Integration with Gradle is a first-party plugin:

```kotlin
plugins {
    id("io.gitlab.arturbosch.detekt") version "1.23.8"
}

detekt {
    config.setFrom("$projectDir/config/detekt/detekt.yml")
    buildUponDefaultConfig = true   // start from defaults, add your overrides
    parallel = true                 // faster analysis on multi-module builds
}
```

Running `./gradlew detekt` produces reports in HTML, Markdown, SARIF, or XML (Checkstyle-compatible). The SARIF output plugs straight into GitHub Code Scanning, which turns detekt findings into PR annotations — a workflow detail that makes the tool dramatically stickier in teams that use GitHub.

For a legacy codebase, the baseline feature is the killer:

```bash
detekt --input src --baseline detekt-baseline.xml --report html:build/reports/detekt.html
```

The first run records every existing violation in `detekt-baseline.xml`; every later CI run fails only when a *new* issue appears. This is the single most effective pattern for introducing static analysis on a codebase that has years of accumulated debt — no 4,000-violation fix-a-thon required.

The trade-off: detekt does **not** format code and it is the slowest of the three tools, especially when you enable type resolution (which unlocks rules that need the compiler's semantic model, like `UndocumentedPublicClass` or unused-declaration detection). On a large multi-module project, budget a few extra minutes per CI run, or use the `parallel = true` flag and the `detekt` task's incremental support.

## ktlint — The Anti-Bikeshedding Formatter

ktlint describes itself as "an anti-bikeshedding Kotlin linter with built-in formatter." The philosophy is blunt: your team should not spend review cycles debating where the newline goes, because the tool already decided, based on the **official Kotlin coding conventions** published by JetBrains. Out of the box, ktlint enforces those conventions with zero configuration — no config file needed for the defaults, which is a huge deal for adoption.

Style settings that teams actually customize live in `.editorconfig`, the same file your IDE reads. This is one of ktlint's smartest design decisions: you configure style once, and Android Studio, IntelliJ, and the CLI all agree:

```ini
# .editorconfig
root = true

[*.{kt,kts}]
max_line_length = 120
indent_size = 4
ktlint_standard_no-wildcard-imports = disabled
```

Usage from the command line is refreshingly simple:

```bash
ktlint "src/**/*.kt" --format          # check and auto-fix
ktlint "src/**/*.kt"                   # check-only (CI mode)
```

`--format` rewrites files in place, which makes onboarding painless: run it once, commit the formatting change, and from then on CI runs the check-only variant. Reporters include `plain`, `json`, `html`, and `checkstyle`, so ktlint also drops into Jenkins or GitHub Actions annotations.

The community Gradle plugin (`org.jlleitschuh.gradle.ktlint`) adds `ktlintCheck` and `ktlintFormat` tasks with a one-line config block, plus per-source-set scoping for Android modules. The limitation to keep in mind: ktlint is deliberately **style-only**. It will not tell you that your `when` expression is too complex or that you swallowed an exception — that is detekt's job. For the formatting layer, though, it is the most frictionless option in the Kotlin ecosystem, and its active development (last push August 19, 2026) means new Kotlin language features are covered quickly.

## Spotless — The Polyglot Formatting Gateway

Spotless, from the Diffplug team, is not a Kotlin tool — it is a **formatting engine** that happens to support Kotlin exceptionally well. You configure it entirely in Gradle, and it delegates to the best formatter for each language: ktlint or ktfmt for Kotlin, google-java-format or Eclipse for Java, Prettier for JavaScript/TypeScript, Black for Python, and so on.

```gradle
plugins {
    id 'com.diffplug.spotless' version '7.0.2'
}

spotless {
    kotlin {
        ktlint()                        // or ktfmt()
        licenseHeaderFile('spotless.license')
        importOrder('java', 'javax', 'kotlin', '')
    }
    kotlinGradle {
        ktlint()
    }
}
```

Two Spotless features make it genuinely better than raw ktlint for many repos. First, **`ratchetFrom`** — you can tell Spotless to only format files that changed since `origin/main`, so a giant legacy repo gets incremental formatting instead of one catastrophic diff:

```gradle
spotless {
    ratchetFrom 'origin/main'
    kotlin { ktlint() }
}
```

Second, **license headers and import ordering** are first-class. `licenseHeaderFile('spotless.license')` stamps every Kotlin file with your project's license automatically, and `importOrder(...)` enforces a deterministic import sequence — both are common audit requirements that ktlint alone does not cover.

The workflow tasks are memorable: `./gradlew spotlessCheck` fails the build on violations, `./gradlew spotlessApply` fixes everything. In a monorepo with a backend in Kotlin, services in Java, and a web frontend, Spotless unifies all of it behind one plugin and one task name, which is why polyglot teams usually adopt it even when ktlint would suffice for Kotlin alone. The trade-off is configuration surface: Spotless is more powerful but demands more setup, and it is a Gradle-only tool (Maven support exists but is less mature).

## Pitfalls and Gotchas — What Nobody Tells You

**1. ktlint and detekt solve different problems — do not force a choice.** The most common mistake is picking one and declaring victory. ktlint will happily pass code with an empty `catch` block; detekt will happily pass code that violates the official style guide. Teams that want quality run **both**, each in its lane.

**2. Version skew between ktlint and Spotless.** Spotless bundles its own ktlint version, which may lag the standalone ktlint release. You can pin it explicitly (`ktlint("1.6.0")` inside the `kotlin {}` block) — if you do not, `spotlessApply` and `ktlint --format` can produce *different* output on the same file, and CI fails on code that looks locally fine. Always pin, and ideally standardize the team on one tool for the format step.

**3. The two-config-file trap.** detekt reads `detekt.yml`; ktlint reads `.editorconfig`; Spotless reads your `build.gradle`. Newcomers assume one config file controls everything and then wonder why changing `max_line_length` in detekt.yml does nothing for ktlint. Document the split (`.editorconfig` = style, `detekt.yml` = analysis rules, Gradle = orchestration) or your team will chase phantom config bugs.

**4. Baselines rot silently.** detekt's baseline is a blessing and a trap: it is a generated XML file that teams commit and then forget. If a PR removes 50 baseline-listed violations and the baseline is regenerated naively, new violations can slip in unnoticed. Review baseline diffs in pull requests — a baseline file should only ever shrink.

**5. `--format` before commit, check-only in CI.** Running `ktlint --format` locally and `ktlint` (no format) in CI is correct. The mistake is running `--format` in CI too, which silently rewrites files during the build and can mask what actually changed. Keep the formatter a local/developer operation.

**6. Type resolution makes detekt slow — budget for it.** The jump from syntactic rules to type-resolved rules is where detekt's run time grows. On big modules, enable `parallel = true` and consider running the deep analysis only on `main` (nightly) while keeping the fast syntactic pass on every PR.

For context on how Kotlin tooling fits the wider ecosystem, see our [Kotlin testing frameworks comparison](../2026-07-06-kotlin-testing-frameworks-kotest-mockk-mockito-kotlin/) and the [cross-language linter and formatter guide](../2026-06-20-code-linter-formatter-tools-eslint-prettier-ruff-black-rubocop/). If you are moving beyond linting into full quality gates, our [SonarQube vs Semgrep vs CodeQL comparison](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/) covers the platform layer, and the [Kotlin HTTP clients guide](../2026-08-01-kotlin-http-clients-ktor-fuel-http4k-comparison/) shows the same ecosystem thinking applied to networking.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kotlin Linting in 2026: detekt vs ktlint vs Spotless — Which Tool Actually Keeps Your Code Clean?",
  "description": "Deep comparison of detekt, ktlint, and Spotless for Kotlin code quality in 2026: features, GitHub stats, configuration, pitfalls, and a decision matrix for CI integration.",
  "datePublished": "2026-08-20",
  "dateModified": "2026-08-20",
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

### Should I use detekt or ktlint?

Use **both** — they do not compete. ktlint enforces the official Kotlin style and formats your code; detekt performs static analysis for bugs, complexity, and smells. The common production setup is ktlint for the formatting gate plus detekt (with a baseline) for the analysis gate, both failing CI. If you can only add one, start with ktlint for style, then add detekt when you want defect detection.

### What is the difference between a linter and a formatter?

A formatter (ktlint, Spotless) rewrites code to match a style — indentation, line length, import order. A linter (detekt, and partially ktlint's rule engine) *reports* problems without fixing them: dead code, empty catch blocks, excessive complexity, unsafe constructs. Formatters remove style debates; linters remove defect patterns. Modern tools blur the line — ktlint both lints and formats — but the mental model still helps you pick what to install.

### How do I add detekt to a Gradle project?

Apply the plugin `io.gitlab.arturbosch.detekt` and optionally point `config` at your `detekt.yml`: `detekt { config.setFrom("$projectDir/config/detekt/detekt.yml"); buildUponDefaultConfig = true }`. Then run `./gradlew detekt`. For legacy code, generate a baseline with `--baseline detekt-baseline.xml` so CI only flags new violations.

### How do I suppress a single detekt rule?

Use `@Suppress("RuleName")` on the offending declaration, or `@file:Suppress("RuleName")` at the top of the file. For project-wide changes, disable the rule in `detekt.yml` under its rule set (for example, `complexity > LongMethod: active: false`). Suppressions in code are visible in review, which is better than silently relaxing the config.

### Is ktlint compatible with JetBrains' official Kotlin style?

Yes — ktlint implements the official Kotlin coding conventions by default, which is its core design goal ("anti-bikeshedding"). Deviations are configured through `.editorconfig` keys like `ktlint_standard_*`, so a team can relax specific rules (for example wildcard imports) without abandoning the standard entirely.

### Does Spotless work with Maven?

Spotless has a Maven plugin (`com.diffplug.spotless:spotless-maven-plugin`) but it is less mature and less documented than the Gradle plugin, and some features (notably `ratchetFrom`) are Gradle-first. For Kotlin projects on Maven, the pragmatic route is ktlint's Maven plugin or a standalone CLI step in your build script.

### How do I make CI fail on formatting issues?

Wire the tool into the `check` lifecycle: `./gradlew ktlintCheck` (community plugin), `./gradlew detekt` (detekt), or `./gradlew spotlessCheck` (Spotless). All three return a non-zero exit code on violations, which fails the build. Developers fix locally with the corresponding apply/format task before pushing.

### Do these tools work for Kotlin Multiplatform and Android?

Yes, all three support KMP and Android modules. detekt offers per-source-set configuration and type resolution for each target; ktlint's Gradle plugin scopes rules per source set; Spotless handles the shared and platform source sets in one `kotlin {}` block. Android projects should ensure `targetSdk`/lint rules are not duplicated with Android Lint itself, which overlaps detekt in a few areas.

### Which Kotlin tool is best for a solo developer?

For a solo developer, ktlint wins: zero config, one command to format, and it enforces the official style so your future self (and any collaborator) never argues about formatting. Add detekt later if you want a second pair of eyes on bugs; its defaults are sensible without a config file too.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
