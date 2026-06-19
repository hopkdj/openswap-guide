---
title: "Dead Code Detection Tools: knip vs ts-prune vs Vulture vs unimported Compared"
date: "2026-06-19"
tags: ["dead-code", "static-analysis", "developer-tools", "code-quality", "javascript", "typescript", "python", "linting"]
draft: false
description: "Compare knip, ts-prune, Vulture, and unimported for detecting and removing dead code. Language-specific dead code analysis for JavaScript, TypeScript, Python, and Nix projects."
---

## Why Dead Code Detection Matters

Dead code is code that's never executed — unused functions, unreachable branches, dangling imports, and abandoned exports. It accumulates silently in every codebase, inflating build times, increasing cognitive load for developers, and bloating deployment artifacts. A 2025 Stripe developer survey found that engineers spend 17% of their time understanding code they'll never need to modify.

Automated dead code detection tools catch what linters and compilers miss. While TypeScript's `noUnusedLocals` catches unused local variables, it won't detect an exported function that no consumer imports. A dead dependency in `package.json` passes every linter but ships unnecessary kilobytes to every user.

For a broader view of code quality tooling, see our [code quality platforms comparison](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/) and [linting tools overview](../2026-04-23-megalinter-vs-super-linter-vs-reviewdog-self-hosted-linting-guide-2026/). If you want to enforce standards alongside dead code removal, our [Git commit convention tools guide](../2026-06-17-shell-script-linting-shellcheck-shfmt-bashate/) covers complementary practices.

## Comparison Table

| Tool | Language Focus | Stars | Type | Key Feature | CI-Friendly |
|------|---------------|-------|------|-------------|-------------|
| knip | JS/TS/Node.js | 11,529 | CLI | Multi-plugin: unused files, exports, deps, members | Yes |
| ts-prune | TypeScript only | 2,067 | CLI | Finds unused exports via TS compiler API | Yes |
| Vulture | Python | 4,661 | CLI | AST-based dead code detection, whitelist support | Yes |
| unimported | JS/TS | 1,968 | CLI | Finds unused files and dependencies in JS projects | Yes |
| deadnix | Nix | 763 | CLI | Scans Nix files for unused code | Yes |

## knip: The Swiss Army Knife for JavaScript Dead Code

knip (11,529 stars) is the most comprehensive dead code detection tool for the JavaScript/TypeScript ecosystem. Unlike simpler tools that check only one dimension, knip analyzes five categories simultaneously: unused files, unused dependencies (`package.json`), unused exports, unused enum/type members, and duplicate exports.

knip automatically detects your project's entry points from `package.json` fields (`main`, `bin`, `exports`), Next.js pages, Vite config, Storybook stories, and test files. Each detection is powered by a plugin system — there are 50+ built-in plugins for popular frameworks and tools.

```bash
# Install and run
npm install -D knip
npx knip

# Sample output:
# Unused files (2):
# src/legacy-auth.ts
# scripts/migrate-v1.ts
#
# Unused dependencies (3):
# lodash   package.json
# moment   package.json
# ramda    package.json
#
# Unused exports (5):
# formatCurrency in src/utils.ts:42
# validateToken in src/auth.ts:78
```

For configuration, `knip.json` lets you include/exclude files, ignore specific exports, and configure per-workspace settings in monorepos:

```json
{
  "$schema": "https://unpkg.com/knip@5/schema.json",
  "entry": ["src/index.ts", "src/cli.ts"],
  "project": ["src/**/*.ts"],
  "ignore": ["src/generated/**"],
  "ignoreExportsUsedInFile": true,
  "ignoreDependencies": ["eslint"]
}
```

**Key features:** Monorepo support via workspaces, auto-fix mode (`--fix`), ESLint integration, GitHub Actions annotations output, and incremental adoption — start with `--include=files` to only check unused files, then progressively enable more categories.

## ts-prune: Surgical Precision for TypeScript Exports

ts-prune (2,067 stars) takes a focused approach: it uses the TypeScript compiler API to find exports that are not imported anywhere in the project. It doesn't check unused files, dead dependencies, or unreachable code — just exports.

This narrow focus makes ts-prune extremely fast and zero-config for any TypeScript project. It's ideal for library authors who need to ensure their public API surface is minimal, or for teams that want a lightweight CI check alongside their existing tooling.

```bash
# Install: npm install -D ts-prune
npx ts-prune

# Output:
# src/components/DeprecatedBanner.tsx:42 - DeprecatedBanner (default export)
# src/utils/math.ts:17 - calculateMedian
# src/hooks/useLegacyFetch.ts:8 - useLegacyFetch
```

For libraries, add a `.ts-prunerc` to mark intentional public exports:

```json
{
  "ignore": "src/index\.ts|src/public-api\.ts"
}
```

**Key features:** Zero configuration needed, fast (runs in seconds on large codebases), supports both default and named exports, and can be combined with tools like ESLint for automatic removal of unused imports.

## Vulture: Python Dead Code Scavenger

Vulture (4,661 stars) is the standard dead code detector for Python projects. It uses Python's AST module to parse source code without executing it, identifying unused classes, functions, variables, and imports. Vulture intentionally reports false positives for code that's "used" through dynamic mechanisms (string-based imports, `getattr`, entry points in `setup.py`), but provides a whitelist system to suppress known-good hits.

```bash
pip install vulture
vulture myproject/

# Sample output:
# myproject/old_api.py:15: unused function 'legacy_endpoint' (60% confidence)
# myproject/models.py:203: unused class 'DeprecatedUserModel' (90% confidence)
# myproject/utils.py:8: unused import 'collections.OrderedDict' (100% confidence)
```

Confidence levels help prioritize: 100% confidence means the code is definitely unreachable through static analysis; 60% confidence means it might be used through dynamic dispatch or metaprogramming.

```python
# vulture_whitelist.py — mark intentionally kept code
from myproject.old_api import legacy_endpoint  # used in migration scripts
```

**Key features:** High confidence scoring, whitelist support via Python files, integration with pytest via `pytest-vulture`, and the ability to scan Jupyter notebooks (`.ipynb` files).

## unimported: Find Dangling Dependencies and Orphan Files

unimported (1,968 stars) detects two categories of dead code in JavaScript/TypeScript projects: unused dependencies in `package.json` (packages installed but never imported) and orphan files (files present in the repository but not imported by any other file).

Its standout feature is the "preset" system that understands framework conventions. The `node` preset knows that files imported through `require()` are used. The `react` preset recognizes that components referenced in JSX are used even without explicit imports.

```bash
npx unimported

# Output:
# summary
# ───────
#  Unused Dependencies (3)
#  Unresolved Imports (0)
#  Unused Files (5)
#
# Unused Dependencies
#  axios        package.json  (not imported anywhere)
#  cheerio      package.json
#  uuid         package.json
#
# Unused Files
#  src/components/OldHeader.tsx
#  src/pages/legacy-dashboard.tsx
```

**Key features:** Preset system for framework conventions, `--fix` to automatically remove unused dependencies, monorepo awareness, and clear terminal output with summary statistics.

## CI/CD Integration Patterns for Continuous Dead Code Detection

Integrating dead code detection into CI/CD pipelines transforms it from a one-time cleanup into an ongoing quality practice. The key is gradual enforcement — blocking CI on day one will alienate teams with legacy codebases. Here are battle-tested integration patterns for each tool.

**knip in GitHub Actions:** Start with reporting-only mode in a pull request workflow. knip's `--reporter=json` output can be fed to a custom script that comments on PRs with a summary of newly introduced dead code (not existing legacy). After a sprint or two, switch to blocking mode for new files only. knip's `--include` filter lets you scope checks to changed directories in CI:

```yaml
# .github/workflows/dead-code.yml
name: Dead Code Check
on: [pull_request]
jobs:
  knip:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - name: Check for dead code in changed files
        run: |
          CHANGED=$(git diff --name-only origin/main... | grep -E '\.(ts|tsx|js|jsx)$' | xargs dirname | sort -u | head -5)
          if [ -n "$CHANGED" ]; then
            npx knip --include="$CHANGED" || echo "::warning::Dead code detected"
          fi
```

**Vulture in pre-commit hooks:** Python projects benefit from running Vulture in pre-commit for fast feedback. The `--min-confidence 80` flag reduces noise by only flagging high-confidence dead code. Combine with a vulture whitelist checked into the repository for known intentional exclusions:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: vulture
        name: vulture
        entry: vulture . --min-confidence 80
        language: system
        types: [python]
        pass_filenames: false
```

**Incremental adoption strategy:** Don't try to achieve zero dead code overnight. Track the count of dead code instances as a metric in your dashboard. Set a target of reducing it by 10% per sprint. When the count reaches a manageable number (under 20 items), switch knip or ts-prune to blocking mode in CI — this prevents regressions while the team chips away at the backlog. Teams that follow this pattern typically eliminate 80% of dead code within two months.


## FAQ

### How do dead code detection tools differ from tree-shaking?

Tree-shaking (performed by bundlers like Webpack, Rollup, esbuild) removes dead code at build time from the final bundle. Dead code detection tools operate at the source level, identifying code that should be deleted from the repository entirely. They complement each other: detection finds what to remove; tree-shaking ensures removed code doesn't reach production.

### Can I run these in CI without false positives blocking builds?

Yes. knip supports `--no-exit-code` to report issues without failing CI. ts-prune can be configured with an ignore file. Vulture provides whitelisting. Gradually tighten thresholds — start with reporting mode, then switch to blocking mode once the backlog is cleared. The knip approach of incrementally enabling categories (files → deps → exports → members) is the most practical.

### Why does Vulture report items with low confidence?

Python's dynamic nature means static analysis can't be certain. A function might be called through `getattr(obj, "method_name")`, a string import, or a Celery task decorator. Vulture's confidence scoring acknowledges this uncertainty. Use the whitelist to suppress false positives rather than ignoring the tool entirely.

### Can these tools automatically delete dead code?

Some can. knip supports `--fix` for unused dependencies and exports. unimported has `--fix` for package.json cleanup. However, automatic deletion of files and functions is generally not recommended for safety — review the output manually first. The exception is removing unused npm dependencies, which is safe since they can be reinstalled.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dead Code Detection Tools: knip vs ts-prune vs Vulture vs unimported Compared",
  "description": "Compare knip, ts-prune, Vulture, and unimported for detecting and removing dead code. Language-specific dead code analysis for JavaScript, TypeScript, Python, and Nix projects.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
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
