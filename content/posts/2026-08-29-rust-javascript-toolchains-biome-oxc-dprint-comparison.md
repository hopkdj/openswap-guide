---
title: "Biome vs Oxc vs dprint in 2026: The Rust Rewrite of the JavaScript Toolchain"
date: "2026-08-29"
tags: ["javascript", "typescript", "rust", "developer-tools", "linting"]
draft: false
cover: "/img/screenshots/biome-cover.jpg"
---

Your monorepo's lint-and-format step used to take eleven seconds. Then the codebase crossed a million lines, the TypeScript types got deeper, and that same step now eats forty seconds on every push — and the CI queue is backing up because ESLint plus Prettier are single-threaded Node processes grinding through files one at a time. This is exactly the pain that launched a wave of Rust-based replacements for the JavaScript toolchain: Biome has 25,668 stars, Oxc has 22,546, and dprint has 4,058 — and together they represent the biggest shift in frontend tooling since esbuild made bundling fast. They are not interchangeable, though. One is an all-in-one toolchain, one is a compiler platform that powers the next generation of bundlers, and one is a formatter platform with a plugin system. Picking the wrong one for your project means either fighting rule parity gaps or re-architecting your CI for the second time in a year.

## TL;DR — Quick Verdict

**Choose Biome** if you want one tool to replace both ESLint and Prettier today — it ships a formatter with 97% Prettier compatibility, a linter with 500+ rules, zero configuration, and a `check` command that does both. **Choose Oxc** if you want the raw performance leader and are comfortable with its ecosystem — `oxlint` is the fastest linter in the Rust wave and the same compiler powers Rolldown, Vite's new bundler. **Choose dprint** if you want a formatter-only platform that unifies formatting across many languages through plugins — it can even wrap Biome, Oxc, Prettier, or Ruff as formatter backends. If you need linting *and* formatting with minimal migration pain, Biome is the safest default in 2026.

## Comparison at a Glance

| Criterion | Biome | Oxc | dprint |
|---|---|---|---|
| **GitHub stars** | 25,668 | 22,546 | 4,058 |
| **License** | MIT or Apache-2.0 | MIT | MIT |
| **Last push** | 2026-08-29 | 2026-08-29 | 2026-08-27 |
| **What it is** | All-in-one toolchain: formatter + linter + assist | Compiler platform: parser, transformer, minifier, resolver, oxlint | Pluggable code formatting platform |
| **Lints?** | Yes — 500+ rules from ESLint and typescript-eslint | Yes — via oxlint, used by Preact, Shopify, ByteDance | No — formatting only |
| **Formats?** | Yes — 97% Prettier-compatible | Yes — via oxfmt (newer) | Yes — plugin-based, many languages |
| **Requires Node.js?** | No (standalone binary) | No (native binaries via npm) | No (native binary; npm/cargo/brew) |
| **Config** | Sane defaults, zero-config friendly | Per-tool config, ESLint-compatible options | `dprint.json` with plugins |
| **Best for** | Replacing ESLint + Prettier in one move | Maximum speed, toolchain building blocks | Multi-language formatting standardization |

## Decision Matrix: Use Case → Tool → Why

| Use case | Recommended tool | Why |
|---|---|---|
| Replace ESLint + Prettier in one migration | **Biome** | `npx @biomejs/biome check --write` handles both; 500+ rules cover the common ESLint rule set |
| Fastest possible lint on a huge monorepo | **Oxc (oxlint)** | Purpose-built for performance; used at scale by Preact, Shopify, ByteDance, and Shopee |
| Format many languages with one tool and config | **dprint** | Plugin platform for TypeScript, JSON, Markdown, TOML, Dockerfile, and more — one binary, one config |
| Building a bundler or compiler on fast parsing | **Oxc** | The parser/transformer/minifier/resolver stack powers Rolldown and Nuxt |
| Zero-config editor-integrated formatting | **Biome** | First-class LSP support and it can format and lint malformed code as you type |
| Incremental migration while keeping Prettier | **dprint** | Ships a `dprint-plugin-prettier` wrapper, so you can standardize on dprint without rewriting configs |

## Biome — The All-in-One Toolchain

Biome's bet is that formatter, linter, and import organizer belong in one binary built on one parser. It targets JavaScript, TypeScript, JSX, JSON, CSS, and GraphQL, claims **97% compatibility with Prettier** (measured against the Prettier benchmark suite), and ships **more than 500 lint rules** ported from ESLint, typescript-eslint, and other sources. The design goals from the official README are explicit: sane defaults, no configuration required, no Node.js required to function, and first-class LSP support with a parser that represents source text in full fidelity with strong error recovery. Usage is deliberately simple:

```shell
npm install --save-dev --save-exact @biomejs/biome

# format files
npx @biomejs/biome format --write

# lint files and apply the safe fixes
npx @biomejs/biome lint --write

# run format, lint, etc. and apply the safe fixes
npx @biomejs/biome check --write

# check all files against format, lint, etc. in CI environments
npx @biomejs/biome ci
```

The `ci` command is the migration story in one line: it replaces your `eslint . && prettier --check .` pipeline with a single fast binary, and the `--write` flag applies safe fixes automatically. The trade-offs are the usual ones for a consolidator: rule coverage is broad but not exhaustive (deeply custom ESLint rule sets need auditing), and version churn is real — Biome has moved fast since its fork of Rome, so pin the exact version (`--save-exact` in the install command is not an accident). Biome is dual-licensed MIT or Apache-2.0, so there is no license anxiety for commercial use.

## Oxc — The Oxidation Compiler

Oxc — pronounced like "ox-see" — is the Oxidation Compiler, a collection of high-performance JavaScript and TypeScript tools written in Rust, and the README's positioning matters: it is part of **VoidZero's** vision of a unified high-performance toolchain, and it already powers **Rolldown, Vite's bundler**. The project is MIT-licensed and built as a platform: a parser, a transformer (TypeScript, JSX, modern JavaScript), a minifier, and a module resolver, with `oxlint` as the linter and `oxfmt` as the formatter:

```shell
# Lint a codebase
npx oxlint@latest

# Format a codebase
npx oxfmt@latest
```

The adoption list from the README is the strongest evidence of production readiness: **Rolldown and Nuxt use Oxc for parsing; Rolldown uses it for transformation and minification; Nova, swc-node, and knip use the oxc_resolver for module resolution; and Preact, Shopify, ByteDance, and Shopee use oxlint for linting.** That is a different maturity profile from a fresh rewrite — the parser is already embedded in the most-watched bundler work in the ecosystem. The practical difference versus Biome: Oxc is not trying to be a drop-in Prettier replacement with an opinionated zero-config experience; it is a family of focused tools with ESLint-compatible configuration surfaces, so you compose it into your existing pipeline rather than replacing the pipeline. If your pain is specifically lint speed at monorepo scale, oxlint is currently the tool with the most convincing benchmark claims and the largest production deployments.

## dprint — The Formatter Platform

dprint takes a third route: it is not a linter and it is not a compiler — it is a **pluggable code formatting platform**, a single native binary that formats whatever language via plugins. The official README lists plugins for TypeScript/JavaScript, JSON/JSONC, Markdown, TOML, Dockerfile, and Jupyter notebooks, plus community plugins for CSS (Malva), HTML/Vue/Svelte/Astro (markup_fmt), GraphQL, YAML, Go via gofumpt, Swift, and more. The clever part is the wrapper plugins:

```shell
# install via your package manager of choice
npm i -g dprint
# or: cargo install dprint
# or: brew install dprint

# in a project, generate dprint.json, then format
dprint fmt
```

dprint ships wrapper plugins that delegate to other formatters — `dprint-plugin-biome`, `dprint-plugin-oxc`, `dprint-plugin-prettier`, and `dprint-plugin-ruff` — which means you can standardize every language in a repository on one binary and one config file while individual languages still use the best formatter underneath. That is the strongest argument for dprint in polyglot repos: one `dprint.json` at the root, one CI step, one local `dprint fmt`, and per-language engines behind the scenes. The trade-off is scope: dprint does not lint, so you still need a linter per language (or Biome/Oxc for the JavaScript parts), and the platform is effectively a solo-maintained project — the README's sponsorship note ("I do a lot of this development in my spare time") is honest about bus-factor risk for companies standardizing their whole formatting workflow on it.

## Pitfalls & Practical Advice

**Audit your ESLint rules before migrating.** Biome's 500+ rules cover the common ESLint + typescript-eslint surface, but exotic or heavily customized rule sets will have gaps. Run both tools in parallel in CI for a week and diff the warnings before you delete your ESLint config — silent rule drops are the worst migration failure mode.

**Pin your versions.** Biome, Oxc, and dprint all move fast. Biome's install command uses `--save-exact` for a reason; Oxc's tooling is versioned per-component. In CI, pin exact versions or you will chase flaky diffs when a formatter's opinion changes between releases.

**Prettier compatibility is 97%, not 100%.** Biome's formatter is benchmarked at 97% Prettier compatibility. The remaining 3% can produce noisy diffs on legacy codebases that were formatted with older Prettier versions. Budget a one-time `format --write` commit and review the diff — do not expect byte-identical output.

**dprint does not lint.** It is a formatting platform. If your workflow relies on one tool doing everything, dprint needs a companion linter; the wrapper-plugin model (dprint-plugin-biome, dprint-plugin-oxc) lets you keep dprint as the orchestrator and Biome/Oxc as the JavaScript engines.

**Oxc is a platform, not just a CLI.** `npx oxlint@latest` is the entry point, but Oxc's value compounds when you build on its parser, transformer, and resolver — as Rolldown, Nuxt, and knip do. Evaluate it as a dependency for tooling, not only as a lint command.

**CI speed gains require warm caches.** All three tools are dramatically faster than the Node-based stack, but the headline numbers assume cache reuse. Configure caching in CI (Biome and oxlint both cache) or the cold-start gain shrinks on short-lived runners.

For the baseline tools these projects replace, see our [ESLint vs Prettier vs Ruff code quality comparison](../2026-06-20-code-linter-formatter-tools-eslint-prettier-ruff-black-rubocop/). This Rust wave in tooling follows the same pattern as the earlier bundler rewrites covered in our [JavaScript build bundlers guide](../2026-06-21-javascript-build-bundlers-esbuild-rollup-parcel-swc-turbopack/), and the parsers underneath are the subject of our [Rust parsing libraries comparison](../2026-07-30-rust-parsing-libraries-nom-pest-lalrpop-chumsky-combine-winnow/).

## FAQ

**Is Biome a drop-in replacement for ESLint and Prettier?**
Mostly, yes. Its formatter is benchmarked at 97% Prettier compatibility and its linter includes 500+ rules from ESLint and typescript-eslint. Custom rule sets and exotic ESLint plugins need auditing, but the standard surface migrates cleanly.

**Is Oxc the same thing as Biome?**
No. Biome is an all-in-one formatter + linter toolchain. Oxc is a compiler platform — parser, transformer, minifier, resolver — with oxlint as its linter, and it powers Rolldown, Vite's bundler.

**Does dprint format JavaScript?**
Yes, through the dprint-plugin-typescript plugin, and it can delegate to Biome, Oxc, or Prettier through wrapper plugins if you prefer those engines.

**Are these tools production-ready?**
Yes. Oxc's components are used by Rolldown, Nuxt, Preact, Shopify, ByteDance, and Shopee; Biome is dual-licensed MIT/Apache-2.0 with enterprise support offerings; dprint is used broadly for formatting standardization, though it is a smaller, mostly solo-maintained project.

**Do I still need Node.js for these tools?**
No. Biome explicitly does not require Node.js, and dprint and Oxc ship native binaries. You can install them via npm, cargo, or Homebrew depending on the tool.

**Which is fastest for linting large codebases?**
Oxlint is currently the performance leader with the largest production deployments at monorepo scale, though Biome is close and offers the simpler all-in-one migration path.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Biome vs Oxc vs dprint in 2026: The Rust Rewrite of the JavaScript Toolchain",
  "description": "Compare Biome, Oxc, and dprint — the Rust-powered replacements for ESLint and Prettier. All-in-one toolchains, compiler platforms, formatter plugins, benchmarks, migration pitfalls, and a decision matrix for 2026.",
  "datePublished": "2026-08-29",
  "dateModified": "2026-08-29",
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
