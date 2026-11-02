---
title: "TypeDoc vs API Extractor vs JSDoc in 2026: Which One Actually Generates Docs Developers Read?"
date: "2026-11-03"
tags: ["typescript", "documentation", "developer-tools", "api-design", "static-site"]
draft: false
description: "A practical comparison of TypeDoc, API Extractor and JSDoc for TypeScript libraries in 2026 — configs that work, monorepo traps, and how to ship docs that stay correct."
---

Every TypeScript library has the same three-week window: the code is clean, the README is honest, and nobody has published API docs yet. Then the first external contributor opens an issue asking what an options object actually accepts, and you realize the types are the documentation — except nobody can browse a `.d.ts` file comfortably.

Picking a documentation generator feels like a solved problem until you try to do it in a monorepo. TypeDoc, API Extractor and JSDoc all claim to solve it, and all three fail in different, instructive ways. The star counts are close enough to be unhelpful — **TypeDoc at 8,453**, **JSDoc at 15,471**, and **API Extractor's home repo, Rush Stack, at 6,506** — so the decision has to be made on output quality and maintenance cost, not popularity.

This comparison uses the actual configuration formats from each project, and the pitfalls come from monorepo reality rather than the quickstart.

## TL;DR: The Short Verdict

- **TypeDoc** if you are publishing a TypeScript library and want a browsable HTML site plus Markdown output for a docs platform. Best output quality per unit of configuration.
- **API Extractor** if you ship a library with a public API contract you need to *enforce* — it generates `.d.ts` rollups and API reports that fail CI when the surface changes unexpectedly.
- **JSDoc** if your codebase is JavaScript with JSDoc comments, or you need one tool that spans both `.js` and legacy `.ts` files.
- **TypeDoc + API Extractor together** if you are serious: API Extractor guards the contract, TypeDoc renders it. This is the combination most large libraries converge on.

The blunt version: **TypeDoc is the best documentation generator, API Extractor is the best API *governance* tool, and JSDoc is the one you inherit rather than choose.**

## The 2026 Comparison Table

| Dimension | TypeDoc | API Extractor | JSDoc |
|---|---|---|---|
| Repository | `TypeStrong/typedoc` | `microsoft/rushstack` | `jsdoc/jsdoc` |
| Stars | 8,453 | 6,506 (Rush Stack) | 15,471 |
| Last push | 2026-07-13 | 2026-11-02 | 2026-11-02 |
| Input | TypeScript source or `.d.ts` | `.d.ts` entry point | `.js` / `.ts` with comment blocks |
| Output | HTML site, JSON, Markdown (plugin) | `.api.md` report, `.api.json` model, rolled-up `.d.ts` | HTML site, JSON |
| Understands TS types | Natively, via compiler API | Natively, via compiler API | Partially (types are comments) |
| API change detection | No | Yes — report diff fails CI | No |
| Bundle rollup | No | Yes (`dtsRollup`) | No |
| Monorepo support | Yes, via entry point mapping | Yes, designed for it | Weak |
| Config style | `typedoc.json` | `api-extractor.json` | `jsdoc.json` / `conf.json` |
| Learning curve | Low | High | Medium |
| Best fit | Published library docs | Enforced public API contracts | JavaScript projects |

## Decision Matrix: Match the Tool to the Job

| Your situation | Pick | Why |
|---|---|---|
| One TypeScript package, docs site wanted this sprint | TypeDoc | One config file, one command |
| Multi-package monorepo with a public SDK | API Extractor | Handles per-package entry points and rollups |
| You must not break semver accidentally | API Extractor | API report diffs are a CI gate |
| Docs must render on an existing docs platform | TypeDoc + Markdown plugin | Emits `.md` files you can commit |
| Codebase is plain JavaScript | JSDoc | TypeDoc needs types to be useful |
| Legacy mix of `.js` and `.ts` | JSDoc (or migrate first) | Only tool that tolerates both |

If you take one thing from this table: **TypeDoc answers "how do we document this?" and API Extractor answers "how do we stop this from changing by accident?"** Those are different problems, and mature projects solve both.

## TypeDoc: The Best Default for TypeScript

TypeDoc reads your TypeScript through the compiler API, so it knows about generics, discriminated unions, `readonly` modifiers and default type parameters without being told. That is the core advantage over comment-scraping tools — the output cannot drift from the types, because the types are the input.

```bash
npm install --save-dev typedoc
```

A `typedoc.json` that covers most libraries:

```json
{
  "$schema": "https://typedoc.org/schema.json",
  "entryPoints": ["src/index.ts"],
  "out": "docs/api",
  "tsconfig": "tsconfig.json",
  "excludePrivate": true,
  "excludeInternal": true,
  "categorizeByGroup": true,
  "navigationLinks": {
    "GitHub": "https://github.com/your-org/your-lib"
  }
}
```

Run it:

```bash
npx typedoc
```

For a monorepo you map multiple entry points to named modules instead of duplicating configuration per package:

```json
{
  "entryPoints": [
    "packages/core/src/index.ts",
    "packages/client/src/index.ts",
    "packages/cli/src/index.ts"
  ],
  "entryPointStrategy": "expand",
  "out": "docs/api"
}
```

The Markdown route is what most teams actually want, because it lets the generated reference live in the same docs site as the hand-written guides:

```bash
npm install --save-dev typedoc-plugin-markdown
```

```json
{
  "plugin": ["typedoc-plugin-markdown"],
  "entryPoints": ["src/index.ts"],
  "out": "docs/reference",
  "hidePageHeader": true,
  "useCodeBlocks": true
}
```

Two honest caveats. First, TypeDoc's release cadence is slower than the other two — the repository's last push was **July 2026**, roughly three and a half months before this comparison, while JSDoc and Rush Stack both pushed within the last day. That is not abandonment, but it does mean new TypeScript syntax occasionally takes a release cycle to render correctly. Second, the plugin ecosystem is the fragile part: a plugin that pins an older TypeDoc minor will block your upgrade, so treat plugins as dependencies you own.

## API Extractor: Documentation as a Contract

API Extractor is not really a documentation generator. It is a **public API surface manager** that happens to emit documentation artifacts. It reads a `.d.ts` entry point and produces three things: an `.api.md` report (a human-readable summary of your public surface), an `.api.json` doc model, and a rolled-up single-file `.d.ts` bundle.

```bash
npm install --save-dev @microsoft/api-extractor
```

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/api-extractor/v7/api-extractor.schema.json",
  "projectFolder": ".",
  "mainEntryPointFilePath": "<projectFolder>/dist/index.d.ts",
  "compiler": {
    "tsconfigFilePath": "<projectFolder>/tsconfig.json"
  },
  "apiReport": {
    "enabled": true,
    "reportFolder": "<projectFolder>/etc/",
    "reportTempFolder": "<projectFolder>/temp/"
  },
  "docModel": {
    "enabled": true,
    "apiJsonFilePath": "<projectFolder>/temp/<unscopedPackageName>.api.json"
  },
  "dtsRollup": {
    "enabled": true,
    "untrimmedFilePath": "<projectFolder>/dist/<unscopedPackageName>.d.ts"
  }
}
```

```bash
npx api-extractor run --local
```

The workflow this enables is the real product. Commit the `etc/your-lib.api.md` report. In CI, run `api-extractor run` **without** `--local`. If a contributor changes a public signature, the report no longer matches and the build fails with a diff showing exactly what moved. To accept the change deliberately, they regenerate the report and commit it — which turns an accidental breaking change into a reviewed decision.

The `dtsRollup` output is quietly valuable too: a single `.d.ts` file is faster for consumers to resolve than hundreds of individual declaration files, and it prevents leaking internal types into your published package.

The cost is configuration complexity. Path placeholders (`<projectFolder>`, `<unscopedPackageName>`), the requirement that declaration emit happen before extractor runs, and per-package configs in a monorepo all add up. Budget half a day for the first setup, not twenty minutes.

## JSDoc: The Incumbent That Still Works

JSDoc predates TypeScript by a decade and is still the most-used tool of the three. It parses comment blocks rather than types, which is both its weakness and its portability.

```bash
npm install --save-dev jsdoc
```

```json
{
  "source": {
    "include": ["src/"],
    "includePattern": ".+\\.js$",
    "excludePattern": "(node_modules|dist)"
  },
  "opts": {
    "destination": "docs/api",
    "recurse": true,
    "template": "node_modules/docdash"
  },
  "plugins": ["plugins/markdown"],
  "templates": {
    "cleverLinks": true,
    "monospaceLinks": false
  }
}
```

```bash
npx jsdoc -c jsdoc.json
```

Where JSDoc genuinely wins: a JavaScript codebase where the comments *are* the contract. It also handles mixed `.js`/`.ts` trees, which neither TypeScript-native tool does gracefully. The `@typedef` and `@property` tags let you describe shapes that have no type declaration to point at.

Where it loses: on a TypeScript project, JSDoc re-parses information the compiler already knows and gets it subtly wrong. Generic type parameters, conditional types and mapped types all degrade into prose. You end up maintaining a second, less accurate description of your own API — and the two drift.

The template ecosystem is the other risk. Many popular JSDoc themes have been unmaintained for years, and a stale theme is the most common reason a JSDoc build breaks after a Node upgrade.

## The Monorepo Traps Nobody Mentions

**1. Declaration emit must precede extraction.** API Extractor consumes `.d.ts` files, not source. If your build runs `api-extractor` before `tsc --emitDeclarationOnly`, you are documenting the previous build. Chain them explicitly: `tsc -b && api-extractor run`.

**2. `entryPointStrategy: "expand"` changes URLs.** Switching TypeDoc from a single entry point to expanded packages rewrites every generated path. If your docs site has inbound links or a search index, plan the redirects in the same change.

**3. API reports are noisy without a scope decision.** Everything exported is "public" by default. Decide up front what is internal (`@internal` plus `stripInternal` in `tsconfig`) or your report will grow to thousands of lines and reviewers will start rubber-stamping diffs.

**4. Docs builds are a cache-invalidation problem.** Generated HTML is large and changes on nearly every commit. Build docs in CI and deploy as an artifact; committing generated HTML to `main` produces merge conflicts on every branch that touches public types.

**5. Version skew between docs and release.** If docs are built from `main` but users install `v2.3.1`, they will read signatures that do not exist in their version. Generate a docs version per release tag, and keep a version switcher — retrofitting one later is far more work than adding it at the start.

**6. Markdown output needs a frontmatter strategy.** TypeDoc's Markdown plugin emits files with no frontmatter. Static site generators like Hugo will render them with default titles and no dates unless you post-process. A five-line script that injects `title` and `weight` saves hours of layout debugging.

## Why Self-Host Your API Documentation?

The path of least resistance is a hosted docs platform, and for a small open-source project it is often the right call. But hosted documentation has a specific failure mode: when the vendor changes its pricing tier or pivots, your reference URLs — the ones your users have bookmarked and your Stack Overflow answers link to — move or break.

Generating docs into a static site you control keeps those URLs stable. It also means the docs are built in the same CI pipeline as the code, deployed by the same mechanism, and reviewable in the same pull request. There is no second system to keep in sync, and no third party that can decide your API reference is now a paid feature.

If your public surface is HTTP rather than TypeScript, the same reasoning applies to OpenAPI tooling — our [API documentation comparison of Scalar, Redoc and RapiDoc](../2026-05-01-self-hosted-api-documentation-scalar-redoc-rapiddoc-openapi-guide/) covers the rendering side, and [OpenAPI Generator vs Swagger Codegen vs JHipster](../2026-04-30-openapi-generator-vs-swagger-codegen-vs-jhipster-self-hosted-code-generation-guide-2026/) covers generating clients from that same spec. Once you have a machine-readable contract, [breaking-change detection with oasdiff](../2026-05-24-self-hosted-api-breaking-change-detection-oasdiff-openapi-diff-azure-guide/) extends exactly the API Extractor idea to HTTP APIs.

## FAQ

**Can TypeDoc document a plain JavaScript project?**

It can, but poorly. TypeDoc relies on the TypeScript compiler for its output, so a JavaScript project needs either `allowJs` with `checkJs` enabled or JSDoc annotations rich enough to be inferred as types. If you cannot add type information, use JSDoc instead — it was designed for that case.

**Does API Extractor replace TypeDoc?**

No, and treating them as alternatives is a common mistake. API Extractor produces an API report for change detection, a JSON doc model and a rolled-up `.d.ts`. It does not produce a browsable documentation site. Large projects run API Extractor as a CI gate and TypeDoc to render the human-readable reference from the same source.

**How do I keep generated docs from breaking my build when a plugin updates?**

Pin the generator and its plugins to exact versions and upgrade them in a dedicated pull request. Plugin incompatibility is the single most common cause of a suddenly failing docs build, and a caret range on a docs plugin is a license for a surprise on a Friday afternoon.

**What is the `.api.md` file supposed to be committed to git?**

Yes — that is the point. The API report lives in `etc/` and is committed alongside the code. CI compares the freshly generated report against the committed one; a mismatch means the public surface changed. Accepting the change is an explicit `api-extractor run --local` followed by a commit, which is exactly the review moment you want.

**Should the generated docs be in the same repository as the code?**

Yes, generated into `docs/` during CI and deployed as an artifact, but not committed. Keeping them in the same repo means the docs build is versioned with the code and breaking a public type breaks the docs build immediately, which is the feedback loop you want. Committing the HTML output itself adds churn without adding safety.

**How do I document overloads and generic constraints properly?**

Write real TypeScript overload signatures and real generic constraints, then let TypeDoc render them. Do not try to describe overload behavior in prose in a doc comment — the compiler already encodes it, and hand-written descriptions of type behavior are the fastest way to publish documentation that is confidently wrong.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TypeDoc vs API Extractor vs JSDoc in 2026: Which One Actually Generates Docs Developers Read?",
  "description": "A practical comparison of TypeDoc, API Extractor and JSDoc for TypeScript libraries in 2026 — configs that work, monorepo traps, and how to ship docs that stay correct.",
  "datePublished": "2026-11-03",
  "dateModified": "2026-11-03",
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
