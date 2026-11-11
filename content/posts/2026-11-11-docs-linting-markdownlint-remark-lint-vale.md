---
title: "markdownlint vs remark-lint vs Vale in 2026: The Docs Linting Stack That Ends Review Nitpicks"
date: "2026-11-11"
tags: ["documentation", "markdown", "linting", "developer-tooling", "technical-writing"]
draft: false
description: "A practical comparison of markdownlint-cli2, remark-lint, and Vale for documentation CI — real configs, rule coverage, autofix support, and how to combine all three."
---

A documentation repository with four hundred pages and six contributors has a predictable failure mode: heading levels drift, code fences lose their language tag, the same word gets spelled three different ways, and every pull request collects a dozen "can you fix the spacing" comments. None of that is a writing problem. It is a missing build step.

Three tools cover that gap, and they operate at different depths. **markdownlint-cli2** checks Markdown structure against a fixed rule set. **remark-lint** parses Markdown into an abstract syntax tree and lints it with a plugin ecosystem. **Vale** ignores structure entirely and lints the prose itself — terminology, tone, and banned phrases — while still understanding markup well enough not to flag code blocks.

This is how they differ in practice, what each configuration really looks like, and how to chain them into one CI job that fails on the things that matter and stays quiet about the rest.

## TL;DR: Pick by What You Are Actually Linting

**markdownlint-cli2 for structural rules with autofix; remark-lint when you need AST-level custom rules or already live in the unified/remark ecosystem; Vale when the problem is inconsistent wording rather than broken syntax.** In a serious docs repo, you run all three — they barely overlap, and the combined runtime is under five seconds for a few hundred files.

If you only add one today: add markdownlint-cli2 with `--fix` in a pre-commit hook. It eliminates the most review comments for the least configuration.

| | markdownlint-cli2 | remark-lint | Vale |
|---|---|---|---|
| **Stars** | 974 | 1,041 | 6,374 |
| **Last push** | 2026-11-09 | 2026-01-05 | 2026-11-09 |
| **License** | MIT | MIT | MIT |
| **Runtime** | Node.js | Node.js | Single Go binary |
| **What it checks** | Markdown structure (50+ rules) | Markdown structure via AST plugins | Prose style, terminology, markup-aware |
| **Rule model** | Fixed rule set, configurable thresholds | Composable plugins and presets | YAML rules + external style packages |
| **Autofix** | Yes, `--fix` on most rules | Partial, via plugin support | No |
| **Custom rules** | Limited to rule options | Full — write a plugin | Full — write YAML, or extend a package |
| **Best at** | Fast baseline in any repo | Teams deep in the unified ecosystem | House style, inclusive language, banned phrases |
| **Config file** | `.markdownlint-cli2.jsonc` | `.remarkrc.mjs` | `.vale.ini` |
| **Speed on 400 files** | ~1-2s | ~2-4s | <1s |

## Decision Matrix: Which Tool for Which Symptom

| Symptom in your docs repo | Tool | Why |
|---|---|---|
| Inconsistent heading levels, missing code-fence languages | **markdownlint-cli2** | Direct rule coverage, fixes most of it automatically |
| Trailing spaces, hard tabs, multiple blank lines | **markdownlint-cli2** | `--fix` handles these without human review |
| You need a rule that does not exist ("every H2 must be followed by a paragraph") | **remark-lint** | Write a plugin against the AST |
| Your build pipeline already runs unified/remark for MDX | **remark-lint** | Shares the parser; no second Markdown dialect |
| "e-mail" vs "email", "log in" vs "login", "whitelist" vs "allowlist" | **Vale** | Terminology enforcement is its core job |
| Passive voice and 40-word sentences in user guides | **Vale** | Prose metrics with configurable severity |
| Docs published in three languages with shared terminology | **Vale** | Vocabularies are shareable across projects |
| You want one gate that catches everything | **All three** | Different layers, negligible combined cost |

## markdownlint-cli2: Structure, Fast

markdownlint-cli2 wraps the markdownlint library with a glob-aware CLI, parallel file processing, and a config format that understands JSON with comments. The rule set is numbered and stable — MD013 is line length, MD033 is inline HTML, MD041 is first-line-heading — which makes it easy to find documentation for a specific failure and easy to suppress one rule deliberately.

Install and run:

```bash
npm install --save-dev markdownlint-cli2
npx markdownlint-cli2 "**/*.md" "#node_modules"
npx markdownlint-cli2 --fix "**/*.md"
```

The `#` prefix is an ignore pattern — a small detail that saves people from writing a separate ignore file. A realistic configuration for a documentation site:

```jsonc
// .markdownlint-cli2.jsonc
{
  "config": {
    "MD013": { "line_length": 120, "tables": false, "code_blocks": false },
    "MD033": { "allowed_elements": ["details", "summary", "kbd"] },
    "MD041": false,
    "MD024": { "siblings_only": true }
  },
  "globs": ["docs/**/*.md", "README.md"],
  "ignores": ["node_modules", "CHANGELOG.md", "docs/generated/**"]
}
```

Three of those settings are the ones teams actually need. `MD013` with `tables: false` and `code_blocks: false` keeps a line-length rule without forcing you to reflow tables and shell examples — the single most common reason people disable line length entirely. `MD033` with an allow-list lets you keep `<details>` collapsibles while still catching stray `<div>` soup. `MD024` with `siblings_only: true` permits repeated headings under different parents, which is normal in reference documentation where every section has an "Example" subsection.

The autofix path is the reason to prefer this over hand-written checks: `--fix` resolves whitespace, list markers, fence styles, and heading increments mechanically. Run it in a pre-commit hook and the diff never reaches a reviewer.

Where it stops: markdownlint knows nothing about words. It will happily pass a page that calls the same feature three different names.

## remark-lint: Linting the Syntax Tree

remark-lint is not a CLI with rules — it is a set of unified plugins that operate on the Markdown AST. That distinction matters when you need a rule nobody wrote. Because the AST exposes headings, list items, link nodes, and their positions, a custom plugin is a short function rather than a parser project.

```bash
npm install --save-dev remark-cli remark-preset-lint-recommended remark-preset-lint-consistent
npx remark docs --frail --quiet
```

`--frail` makes warnings exit non-zero, and `--quiet` suppresses success output so CI logs stay readable. Configuration uses the standard unified config format:

```js
// .remarkrc.mjs
import remarkPresetLintConsistent from 'remark-preset-lint-consistent'
import remarkPresetLintRecommended from 'remark-preset-lint-recommended'
import remarkLintNoUndefinedReferences from 'remark-lint-no-undefined-references'

export default {
  plugins: [
    remarkPresetLintConsistent,
    remarkPresetLintRecommended,
    [remarkLintNoUndefinedReferences, { collapse: false }]
  ]
}
```

The two presets split cleanly: `consistent` enforces internal consistency (list markers, emphasis characters, fence style) and `recommended` enforces rules that are almost always correct (no duplicate definitions, no empty URLs, valid heading increments). Starting with both and removing individual rules is a far better workflow than enabling rules one at a time.

The real differentiator is the plugin ecosystem. Need to assert that every document ends with a "See also" section? That is a fifteen-line plugin walking the root node's children. Need to reject relative links that escape the docs directory? Also short — and impossible to express in markdownlint's option model.

The cost is maintenance gravity. remark-lint's last push was **2026-01-05**, roughly ten months behind the other two tools, and its plugin ecosystem is large but uneven in quality. If your build does not already use unified, you are adding a second Markdown parser to your toolchain, and the two will eventually disagree about edge cases like MDX or GFM tables.

## Vale: Prose Style With Markup Awareness

Vale is a Go binary that lints the words. It is markup-aware — it skips code spans, code blocks, and link URLs by default — which is the property that makes prose linting usable rather than infuriating. At 6,374 stars it is by far the most adopted tool in this comparison, and its last push was **2026-11-09**.

```bash
# macOS
brew install vale

# Linux: grab the release binary, then
vale sync      # download the style packages declared in .vale.ini
vale docs/     # lint a directory
vale --output=JSON docs/ > vale.json
```

Configuration is an INI file. This is Vale's own repository config, which is a good model to copy because it shows the two patterns you need — a package list, and per-path style assignment:

```ini
StylesPath = .github/styles
MinAlertLevel = suggestion

Vocab = Vale
Packages = Microsoft, Readability, Commits

[README.md]
BasedOnStyles = Vale

[COMMIT_EDITMSG]
BasedOnStyles = Commits, Conventional, Commitlint
```

`Packages` pulls shared style packages at `vale sync` time, `Vocab` accepts a project word list so product names are not flagged as misspellings, and the `[path]` sections let you apply different style rules to a README than to commit messages. Applying `Microsoft` to user-facing docs and `Vale` alone to internal design notes is a normal split.

Writing a house rule is a YAML file, not code:

```yaml
# styles/House/Terminology.yml
extends: substitution
message: "Use '%s' instead of '%s'."
level: error
ignorecase: true
swap:
  e-mail: email
  whitelist: allowlist
  blacklist: denylist
  master branch: main branch
```

```yaml
# styles/House/Hedging.yml
extends: existence
message: "Avoid hedging word '%s' — state the behavior directly."
level: warning
ignorecase: true
tokens:
  - simply
  - obviously
  - of course
  - just
```

Those twenty lines of configuration do more for documentation quality than most style guides, because they run on every pull request instead of living in a wiki. The `substitution` rule catches terminology drift; the `existence` rule catches the hedging language that makes technical writing vague.

Vale has no autofix. Everything it reports is a human decision, which is correct — you cannot mechanically rewrite a sentence about passive voice without risking meaning. Budget review time accordingly: a first run on a 400-page docs site can produce thousands of alerts, so start with `MinAlertLevel = error` and raise it after the baseline is clean.

## Chaining All Three Into One Gate

The layers are complementary and cheap, so run them in increasing cost order. markdownlint fixes structure, remark validates the AST-level invariants markdownlint cannot express, and Vale reads the prose:

```yaml
name: docs
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Structure (autofixable)
        uses: DavidAnson/markdownlint-cli2-action@v19
        with:
          globs: "docs/**/*.md"

      - name: AST invariants
        run: |
          npm ci
          npx remark docs --frail --quiet

      - name: Prose style
        run: |
          brew install vale
          vale docs/
```

Two ordering decisions matter. Put markdownlint first because it is the fastest and its failures are the easiest to fix. Vale also ships an official GitHub Action that posts findings as inline review annotations instead of a wall of log output nobody reads — worth wiring up once the baseline is clean.

For local enforcement, add the structural checks to pre-commit and leave prose checks to CI:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/DavidAnson/markdownlint-cli2
    rev: v0.18.1
    hooks:
      - id: markdownlint-cli2
        args: ["--fix"]
```

Autofixing in pre-commit is safe for structural rules. Do not wire Vale's `--fix`-equivalent behavior into a hook, because there isn't one — and a hook that rewrites prose would be worse than no hook.

## Pitfalls That Make Teams Abandon Docs Linting

**Enabling every rule on day one.** A 400-page repo will produce hundreds of MD013 and MD033 violations. Teams respond by disabling the tool, not by fixing the files. Start with autofixable rules only, commit that baseline, then add one rule family at a time.

**Fighting line-length rules on tables.** MD013 counting table rows forces you to restructure comparison tables for no reader benefit. Set `tables: false` and `code_blocks: false` — this is a configuration decision, not a compromise.

**Running Vale at `suggestion` level immediately.** Vale's suggestion level includes style preferences that are genuinely optional. A first run with `MinAlertLevel = suggestion` on legacy docs produces thousands of alerts and destroys trust in the tool. Start at `error`.

**Forgetting `vale sync` in CI.** Vale's style packages are downloaded, not bundled. A CI job that skips `vale sync` fails with "style not found" and looks like a config bug.

**Linting generated files.** Auto-generated API references and changelogs will never pass prose rules. Exclude them explicitly (`ignores` in markdownlint-cli2, `.valeignore` for Vale) instead of adding a dozen inline suppressions.

**Two Markdown parsers, two truths.** remark and markdownlint disagree on some GFM and MDX constructs. If you run both, pin the versions and treat disagreements as a build failure to resolve, not as flakiness to ignore.

**Suppressing with HTML comments and never revisiting.** `<!-- markdownlint-disable MD033 -->` at the top of a file is a permanent mute button. Scope disables to the specific line or block, and add a comment explaining why.

For adjacent tooling, see our comparison of [static site search with Pagefind, Orama, and FlexSearch](../2026-11-04-pagefind-vs-orama-vs-flexsearch-static-site-search/) and the guide to [self-hosted documentation generators: MkDocs vs Docusaurus vs VitePress](../mkdocs-vs-docusaurus-vs-vitepress-self-hosted-documentation-generators-2026/).

## FAQ

### Do I need markdownlint if I already use remark-lint?

Often yes, because the two check different things even though both parse Markdown. markdownlint ships a stable, numbered rule set with autofix; remark-lint gives you composable plugins and custom AST rules. Most teams that run both use markdownlint for the mechanical rules and remark for project-specific invariants.

### Can Vale check Markdown structure like heading levels?

No. Vale is markup-aware in the sense that it skips code and link targets, but it does not validate document structure. Use markdownlint-cli2 or remark-lint for structural rules and keep Vale focused on wording, terminology, and tone.

### How do I stop Vale from flagging product names as misspellings?

Add them to a vocabulary. Create a `Vocab/<Project>` directory with one word per line and set `Vocab = <Project>` in `.vale.ini`. Vale's `Vocab` mechanism is designed exactly for proper nouns and internal jargon, and it is preferable to adding inline ignores.

### Is `--fix` safe to run in CI?

Run it locally or in a pre-commit hook, not in CI. In CI you want the check to fail so the author learns the rule; a CI job that silently rewrites files produces diffs nobody reviews. The exception is a scheduled job that opens a formatting pull request, which is a deliberate workflow.

### What about MDX and MDX-specific components?

markdownlint has limited MDX support and can produce false positives on JSX blocks. remark handles MDX natively because it uses the same unified pipeline, which is the main reason MDX-heavy documentation sites choose remark-lint over markdownlint.

### How long does the full three-tool pipeline take on a large docs site?

On roughly four hundred Markdown files: markdownlint around one to two seconds, remark two to four seconds, and Vale under a second because it is a compiled binary. The dominant cost in CI is `npm ci`, not the linting itself — cache the Node modules and the total gate stays under a minute.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "markdownlint vs remark-lint vs Vale in 2026: The Docs Linting Stack That Ends Review Nitpicks",
  "description": "Practical comparison of markdownlint-cli2, remark-lint, and Vale for documentation CI, with real configs, rule coverage, autofix support, and a combined pipeline.",
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
