---
title: "JavaScript Monorepo Build Tools in 2026: Nx vs Turborepo vs Rush"
date: "2026-09-08"
tags: ["monorepo", "build-tools", "nx", "turborepo", "rush", "javascript", "typescript", "developer-tools"]
draft: false
---

Your CI pipeline just rebuilt every package in the repository — again — even though you changed one file in one library. At 20 packages that is annoying. At 200 packages it burns hours of engineer time and turns every merge into a coin flip on whether the shared cache is warm. Monorepo build tools exist to kill exactly this waste, and in 2026 the JavaScript ecosystem has settled on three serious contenders: **Nx (29,318 stars)**, **Turborepo (31,069 stars)**, and **Rush (part of the Microsoft Rush Stack, 6,495 stars)**. All three are open source, all three are MIT-licensed, and all three were pushed within the last 48 hours — but they approach the problem from surprisingly different angles.

## TL;DR / Quick Verdict

If you just adopted pnpm workspaces and want task caching with almost zero configuration, pick **Turborepo**. If you need a platform that grows with you — code generation, per-project plugins, affected-based CI for polyglot repos — pick **Nx**. If you run a large organization that ships many independently versioned npm packages and needs change-management and publishing governance, pick **Rush**. If you are a solo developer with fewer than five packages, you do not need any of them — plain `npm run` with `--workspaces` is fine.

## The Problem: Why Plain Scripts Stop Scaling

A JavaScript monorepo is a collection of package.json workspaces: applications that depend on libraries, libraries that depend on each other. Running `turbo build`, `nx run-many -t build`, or `rush build` replaces the naive approach of building everything topologically with a **task graph**: the tool figures out which tasks depend on which outputs, skips tasks whose inputs did not change (when a cache hit is found), and runs remaining tasks in parallel across CPU cores.

The three tools all share this core idea but differ in how much they assume about your workflow:

| Feature | Nx | Turborepo | Rush |
|---|---|---|---|
| Repository | nrwl/nx | vercel/turborepo | microsoft/rushstack |
| GitHub stars (2026-09-08) | **29,318** | **31,069** | 6,495 |
| License | MIT | MIT | MIT |
| Last push | 2026-09-07 | 2026-09-07 | 2026-09-07 |
| Core language | Rust + TypeScript | Rust | TypeScript |
| Task caching | Yes (local + Nx Cloud) | Yes (local + Vercel Remote Cache) | Yes (build-cache.json, local or blob storage) |
| Affected-only execution | Yes (`nx affected`) | Via Turborepo filters | Partial (rush build skips up-to-date) |
| Workspace visualization | `nx graph` interactive | `turbo build --dry-run` / TUI | `rush list` |
| Code generation | **Yes** (generators, plugins) | No | No |
| Package publishing flow | External (release tools) | External (changesets, etc.) | **Built-in** (`rush change`, `rush publish`) |
| Package manager | npm / pnpm / yarn / bun | npm / pnpm / yarn | npm / pnpm / yarn (pinned version) |
| Plugin ecosystem | Very large (Vite, Jest, ESLint, Gradle, .NET, Go…) | Minimal | Phased out in favor of standard Node tooling |
| Best for | Growing polyglot repos | Fast, minimal caching | Enterprise multi-team publishing |

## Decision Matrix

| Use case | Recommended tool | Why |
|---|---|---|
| Existing pnpm/npm workspaces, want caching in under an hour | **Turborepo** | One `turbo.json`, tasks auto-discovered from package.json scripts, no project reconfiguration |
| Repo mixes JS with Go, Rust, or .NET and needs affected CI | **Nx** | Plugins understand non-JS toolchains; `nx affected` runs only what a PR touches |
| You scaffold new apps/libraries weekly | **Nx** | Generators create consistent project structure with the right config baked in |
| Multiple teams publish dozens of versioned npm packages | **Rush** | Change files, version policies, and approval workflows are built in, not bolted on |
| Small repo, 1-3 packages | **None** | Native workspace scripts are simpler and faster to reason about |

## Turborepo: The Minimal Cache Layer

Turborepo describes itself as "the build system for coding agents," and its design philosophy matches: a small Rust binary that reads task definitions and executes them with caching, leaving everything else to you. The canonical configuration from the official examples repository is a single file:

```json
{
  "$schema": "https://turborepo.dev/schema.json",
  "ui": "tui",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "inputs": ["$TURBO_DEFAULT$", ".env*"],
      "outputs": [".next/**", "!.next/cache/**", "!.next/dev/**"]
    },
    "lint": {
      "dependsOn": ["^lint"]
    },
    "check-types": {
      "dependsOn": ["^check-types"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

Semantics worth internalizing: `"dependsOn": ["^build"]` means "run the `build` task of my dependencies first" (the caret refers to the package's topological dependencies). `inputs` declares which files participate in the cache key, while `outputs` tells Turbo which generated files to save and restore on a hit — note the negative globs excluding `.next/cache` and dev artifacts. Long-running tasks such as dev servers are marked `"cache": false, "persistent": true` so they never poison the cache.

Getting started is intentionally boring:

```bash
npx create-turbo@latest        # scaffold a fresh monorepo
cd my-turbo-app
turbo build                    # run build across all packages
turbo run lint --filter=@repo/ui   # target a single package
turbo login && turbo link      # enable Vercel Remote Cache for CI
```

**The honest trade-off:** Turborepo deliberately has no opinion about how you structure projects, version packages, or publish releases. Teams that need those answers add changesets or similar tools themselves. That is a feature for minimalists and a gap for enterprises.

## Nx: The Platform Approach

Nx's README states it plainly: "Nx is a monorepo solution for TypeScript and polyglot codebases. Built with Rust for performance, extensible via TypeScript. Caches what didn't change, runs only what's affected." The key differentiator versus Turborepo is that Nx understands *project types* through plugins, which lets it do far more than run scripts — it can generate code, migrate configs between major versions, and compute affected graphs across mixed toolchains.

You can adopt Nx without restructuring anything:

```bash
npx nx init      # detects your existing npm/pnpm/yarn workspace
                 # and wires up caching + affected detection
npx nx affected -t test        # run tests only for projects touched by your branch
npx nx run-many -t build       # topological build across all projects
npx nx graph                   # interactive visualization of the task graph
```

Nx configuration centers on `nx.json`. The Nx repository's own file shows the `namedInputs` pattern that production teams use to distinguish dev-time from production inputs:

```json
{
  "$schema": "packages/nx/schemas/nx-schema.json",
  "namedInputs": {
    "default": ["{projectRoot}/**/*", "sharedGlobals"],
    "production": [
      "default",
      "!{projectRoot}/**/?(*.)+(spec|test).[jt]s?(x)?(.snap)",
      "!{projectRoot}/jest.config.[jt]s",
      "!{projectRoot}/eslint.config.@(js|cjs|mjs|ts|cts|mts)",
      "!{projectRoot}/.storybook/**/*"
    ],
    "sharedGlobals": [
      "{workspaceRoot}/babel.config.json",
      "{workspaceRoot}/.github/workflows/ci.yml"
    ]
  }
}
```

Here `production` excludes test files, Jest configs, ESLint configs, and Storybook stories from the production input set — so editing a test does not invalidate the production build cache, while anything in `sharedGlobals` (CI workflow changes!) invalidates everything. This granular input modeling is where Nx shines, and it is the reason big polyglot shops pick it over simpler caches.

Remote caching and CI distribution run through **Nx Cloud**, which has a free tier for open source and small teams but is a paid SaaS beyond that. The core Nx CLI remains MIT-licensed and fully functional without it.

**The honest trade-off:** Nx's plugin system and generator conventions are powerful but opinionated. Teams that refuse Nx's project layout conventions will find themselves fighting the tool instead of being helped by it.

## Rush: The Enterprise Release Manager

Rush comes from the Microsoft Rush Stack and answers a question the other two ignore: *how do dozens of teams publish hundreds of packages without stepping on each other?* A Rush repository is governed by `rush.json`, whose official template (the exact file `rush init` generates) pins the toolchain and enumerates every project:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/rush/v5/rush.schema.json",
  "rushVersion": "5.140.0",
  "pnpmVersion": "9.15.9",
  "nodeSupportedVersionRange": ">=24.11.1 <25.0.0",
  "projects": [
    {
      "packageName": "my-app",
      "projectFolder": "apps/my-app",
      "reviewCategory": "production"
    },
    {
      "packageName": "my-lib",
      "projectFolder": "libraries/my-lib",
      "reviewCategory": "production"
    }
  ]
}
```

Rush installs its **own private copy of pnpm** at the pinned version, so developer machines and CI are guaranteed to use identical resolution behavior. `nodeSupportedVersionRange` hard-fails with a readable error if a contributor's Node version falls outside the approved range.

The workflow commands are the visible difference from the other two tools:

```bash
rush init        # generate rush.json + config files
rush update      # install dependencies, write shrinkwrap + approved-packages files
rush build       # build all projects, skipping up-to-date ones
rush change      # create a change file describing your PR's impact
rush publish     # bump versions and publish only affected packages
```

`rush change` feeds a **version policy** engine: each PR touching a published package must record a change file describing whether the change is major/minor/patch, and `rush publish` orchestrates the actual npm release in dependency order. Add `rush version --bump` and bulk version bumps across many packages become a single command. Newer Rush releases also ship **subspaces**, which split one repository into several independent install groups with separate lockfiles — the Rush Stack repository itself now runs with `subspaces.json` and `pnpm-config.json`.

**The honest trade-off:** Rush's governance is its moat and its cost. The change-file ritual and approval whitelists feel like bureaucracy to small teams, and Rush does not attempt code generation or rich plugin-driven project modeling the way Nx does.

## Migration and Adoption Pitfalls

1. **Cache misses from environment variables.** Turborepo hashes task inputs but not your shell environment by default. If a build reads `NODE_ENV` or an API token, declare it in the task's `env`/`passThroughEnv` list — the Turborepo repository's own `turbo.json` passes `VERCEL_TOKEN` through explicitly (`"passThroughEnv": ["VERCEL_TOKEN"]`) for exactly this reason. Otherwise you get cache hits that produce wrong artifacts.
2. **Do not forget `.env*` files.** The official Turborepo basic example lists `.env*` under `inputs`; a build that embeds environment files must include them in the cache key or your "cached" output will be stale.
3. **Nx daemon memory in CI.** Nx runs a background daemon for speed on developer machines. In constrained CI containers, disable it (`NX_DAEMON=false`) rather than debugging mysterious OOM kills.
4. **Rush pins your package manager.** The `pnpmVersion` field means "whatever pnpm your team installed globally is irrelevant." Embrace it — but budget time for the first `rush update`, which does a full cold install into `common/temp`.
5. **Change files are mandatory, not optional.** If you adopt Rush for publishing, every merged PR touching a published package without a `rush change` file will fail the gate. Wire `rush change --verify` into CI on day one.
6. **Never run two caching layers.** Adding Turborepo inside an existing Nx workspace doubles cache bookkeeping and confuses developers about which cache a CI log refers to. Pick one task runner per repository.
7. **Migrating from Lerna.** Turborepo is the gentlest path (`turbo.json` plus moving tasks out of Lerna's script), Nx offers an automated Lerna migration, and Rush requires restructuring into its project folder conventions. Time the migration when you are already touching CI, not in the middle of a release.

## FAQ

### Do I need a monorepo build tool at all?

If you have one application and one library, no — native npm/pnpm/yarn workspace scripts are simpler. The crossover point is roughly when you have 5+ packages with shared build steps and you notice CI rebuilding unchanged packages, or when cross-package refactors require coordinated version bumps. At that point a task graph with caching pays for itself within a week.

### Nx vs Turborepo: which is actually faster?

Both ship Rust cores and benchmark within a few percent of each other on plain task execution; the practical difference is cache-hit rates and ecosystem fit. Nx's named inputs and plugin-aware hashing tend to produce more precise cache keys on heterogeneous repos, while Turborepo's simpler model is easier to get right on homogeneous TypeScript-only repos. Measure with `--dry-run` output rather than trusting marketing numbers.

### Is Turborepo free for commercial use?

Yes — the Turborepo binary is MIT-licensed, and local caching is entirely free. Vercel's hosted Remote Cache is a paid service (with a free tier), but the tool works fully offline. The same applies to Nx: MIT core, Nx Cloud as an optional paid SaaS.

### Can Nx work without Nx Cloud?

Completely. Local cache and affected detection are in the open-source CLI. Nx Cloud adds remote cache sharing across machines and CI distribution; without it, CI starts from a cold cache on every fresh runner unless you add a self-hosted remote cache.

### What makes Rush different from Nx and Turborepo?

Rush is first and foremost a **release and versioning governance system** with build orchestration attached, whereas Nx and Turborepo are build orchestrators that leave publishing to external tools. If your pain is "we cannot ship packages safely," Rush targets you; if your pain is "CI is slow," start with Turborepo or Nx.

### Which package managers do they support?

All three support npm, pnpm, and yarn workspaces; Nx also works with bun. Rush is the most opinionated: it installs its own pinned copy of the chosen manager and records approvals in generated files, which is a feature for audits and a nuisance for experiments.

### Is Turborepo configuration optional?

Yes — with no `turbo.json`, Turborepo discovers tasks from each package's `package.json` scripts and runs them topologically with default caching heuristics. Adding a `turbo.json` is how you refine inputs, outputs, and environment variables. This is why it remains the fastest tool to bolt onto an existing repository.

## Why the Choice Matters in 2026

Task-graph tooling has quietly become the backbone of large JavaScript codebases: every major open-source monorepo in the ecosystem runs one of these three engines. The tools are converging on Rust-powered speed while diverging on philosophy — Turborepo stays a thin cache layer, Nx grows into a platform with generators and plugins, and Rush doubles down on enterprise release governance. Picking correctly means your tooling *enables* the next two years of growth instead of fighting it. For build-system fundamentals from the polyglot world, our [comparison of Bazel, Pants, and Please](../2026-04-29-bazel-vs-pants-vs-please-self-hosted-build-systems-guide-2026/) shows what hermetic, language-agnostic build engines do differently. If you are still deciding between pnpm, npm, and yarn underneath all of this, our [JavaScript package manager comparison](../2026-08-31-javascript-package-managers-npm-pnpm-yarn-bun-comparison/) covers resolution behavior and disk usage in depth, and the [C++ build system generators roundup](../2026-06-28-cpp-build-system-generators-xmake-premake-scons-buck2/) is a good reminder that monorepo-scale build thinking is not unique to JavaScript.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript Monorepo Build Tools in 2026: Nx vs Turborepo vs Rush",
  "description": "Compare Nx, Turborepo, and Rush for JavaScript monorepo build orchestration: task caching, affected detection, code generation, release governance, and real configuration examples from each official repository.",
  "datePublished": "2026-09-08",
  "dateModified": "2026-09-08",
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
