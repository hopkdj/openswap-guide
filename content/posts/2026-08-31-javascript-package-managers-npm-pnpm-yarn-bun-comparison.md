---
title: "JavaScript Package Managers in 2026: npm vs pnpm vs Yarn vs Bun"
date: "2026-08-31"
tags: ["javascript", "nodejs", "package-manager", "build-tools", "monorepo"]
draft: false
cover: "/img/screenshots/bun-cover.jpg"
---

A typical JavaScript project in 2026 resolves somewhere between 500 and 5,000 packages into its dependency tree, and a cold `npm install` on a laptop can still burn two to four minutes while the terminal scrolls past thousands of lines of noise. The same install with pnpm takes seconds and consumes a fraction of the disk space — and with Bun it is often faster than the time it takes you to blink. This is not a marginal developer-experience question: install time, disk usage, and dependency-resolution correctness directly affect CI pipeline costs, developer onboarding time, and the reliability of every build you ship. The four major package managers — npm, pnpm, Yarn, and Bun — have diverged sharply in how they answer those questions, and picking the right one is now a strategic decision, not a default.

**TL;DR:** For new projects in 2026, use **pnpm** if you want the best balance of speed, disk efficiency, and correctness on the standard Node.js runtime — it is the safest default for both apps and monorepos. Use **Bun** if you want to collapse your runtime, package manager, bundler, and test runner into one fast native binary and you can tolerate some ecosystem edge cases. Use **npm** only when you want zero extra tooling on machines that already have Node.js. Use **Yarn** (Berry) only if you are already committed to its Plug'n'Play model or its constraints system. Whatever you do, do not start a new project on Yarn 1.x — its line is frozen.

## Quick Feature Comparison

| Feature | npm | pnpm | Yarn (Berry) | Bun |
|---|---|---|---|---|
| GitHub stars | 10,077 | 36,324 | 41,485 (1.x) | 95,813 |
| Last release activity | Aug 2026 | Aug 2026 | Active (Berry) | Aug 2026 |
| Install mechanism | `node_modules`, nested | Content-addressable store + hard links | PnP by default, node_modules optional | Content-addressable cache + hard links |
| Disk usage | High (duplicated per project) | **Lowest** (single global store) | Low (PnP has no node_modules) | Low (global cache) |
| Install speed | Baseline | 2-3x faster than npm | Faster than npm | **Fastest** (native) |
| Monorepo workspaces | Yes (npm v7+) | **Best-in-class** (`pnpm-workspace.yaml`) | Yes | Yes (partial) |
| Lockfile | package-lock.json | pnpm-lock.yaml | yarn.lock | bun.lockb / bun.lock |
| Strict dependency isolation | No (phantom deps) | **Yes** (symlinked, strict) | Yes (PnP) | Yes |
| Runtime bundled | No | No | No | **Yes** (Bun runtime) |
| Written in | JavaScript | TypeScript/Go | TypeScript | Zig |
| License | Artistic-2.0 | MIT | BSD-2-Clause | MIT |
| Node version requirement | Ships with Node | Node >= 18 | Node >= 18 | None (standalone binary) |

## Decision Matrix: Which Package Manager Should You Use?

| Use Case | Recommended Tool | Why |
|---|---|---|
| New app or library, team on standard Node.js | **pnpm** | Fastest correct installs on the Node runtime, strict `node_modules` prevents phantom-dependency bugs, best monorepo support |
| Monorepo with many interdependent packages | **pnpm** | `pnpm-workspace.yaml` + `workspace:` protocol is the most mature workspace UX of the four |
| You want one binary for runtime + bundler + tests | **Bun** | `bun install` is a side feature of a full toolchain; zero-JS-dependency toolchain in one install |
| Corporate/locked-down environment, no extra installs allowed | **npm** | Already present with every Node.js installation; zero adoption cost |
| You live inside the Yarn ecosystem (PnP, constraints) | **Yarn Berry** | PnP and constraints are genuinely unique features worth staying for |
| CI pipeline where every second of install costs money | **Bun or pnpm** | Both are dramatically faster than npm cold installs; Bun also caches globally across projects |

## npm — The Default That Everyone Forgets to Question

npm ships with every Node.js installation, which makes it the path of least resistance and, for many teams, the default they never consciously chose. It is the reference implementation: every other tool in this comparison measures itself against npm's registry protocol, its lockfile semantics, and its lifecycle script behavior. The CLI is maintained actively (10,077 stars, pushed August 2026), and modern npm — versions 7 and later — includes workspaces, `npm ci` for reproducible CI installs, and significantly faster installs than the npm of five years ago.

The cost of that legacy is architectural. npm's `node_modules` is a nested tree with packages hoisted to the top level where possible, which means two projects on the same machine each carry their own full copy of every dependency — dozens or hundreds of megabytes of duplication per project. Worse, hoisting produces the phantom-dependency problem: your code can `require()` a package that is not in your `package.json` simply because it happens to be hoisted into your `node_modules` by a transitive dependency. That works locally, breaks in CI, and confuses every new developer who touches the project.

```sh
# standard npm workflow
npm install
npm ci              # reproducible install from package-lock.json (CI)
npm install --workspace @myorg/web
npm add <package>
```

npm remains a perfectly fine choice for small projects, throwaway scripts, and environments where installing anything else is friction. It is not the best choice for anything else in 2026.

## pnpm — The Correctness-First Speed Demon

pnpm (36,324 stars, pushed August 2026) attacks the two structural weaknesses of npm head-on. First, it keeps a single content-addressable store on your machine, and every project's `node_modules` is made of hard links (or symlinks on filesystems that do not support them) pointing into that store. Install the same dependency in ten projects and you pay for its bytes once. Second, pnpm's `node_modules` is strict: your code can only import packages that are declared in your `package.json`. The phantom-dependency class of bugs disappears, and the structure mirrors the actual dependency graph instead of a hoisted approximation.

```sh
# installation
corepack enable && corepack prepare pnpm@latest --activate
# or: npm install -g pnpm

# everyday commands
pnpm install
pnpm add <package>
pnpm add -D <package>
pnpm --filter @myorg/web add lodash
pnpm dlx <package>   # run a package without installing it
```

For monorepos, pnpm's workspace support is the most mature of the four. A workspace is declared with a single `pnpm-workspace.yaml` at the root:

![pnpm](/img/screenshots/pnpm-dashboard.jpg "pnpm — fast, disk space efficient JavaScript package manager")

```yaml
packages:
  - "packages/*"
  - "apps/*"
```

Inside the workspace, packages reference each other through the `workspace:` protocol — for example, a package `bar` can declare `"foo": "workspace:../foo"` — and these specs are converted to regular version ranges before publishing. The `pnpm --filter` flag lets you run commands against specific workspace packages, and `pnpm -r` runs across all of them. This combination — fast installs, strict isolation, first-class workspaces — is why pnpm has become the default recommendation for serious Node.js projects, and why the tooling ecosystem (Next.js, Vite, Turborepo, and virtually every modern monorepo guide) documents pnpm as the reference setup. Our [monorepo build systems guide](../2026-06-16-self-hosted-monorepo-build-systems-nx-turborepo-bazel/) covers the orchestration layer you would pair with it.

The trade-offs are minor: pnpm's symlinked structure occasionally confuses tooling that walks `node_modules` naively (older bundlers, some native module post-install scripts), and the store needs occasional cleanup (`pnpm store prune`). Both are well-understood and documented.

## Yarn — The Pioneer That Split Into Two Worlds

Yarn's story is the strangest of the four. The original Yarn 1.x line — which overtook npm in the mid-2010s with its parallel installs and deterministic lockfile — is now **frozen**: the repository description reads "The 1.x line is frozen - features and bugfixes now happen on https://github.com/yarnpkg/berry." All active development lives in Yarn Berry (v2+), which made a radical bet: instead of `node_modules`, Berry defaults to **Plug'n'Play (PnP)**, where the dependency map is stored in a single `.pnp.cjs` file and packages are resolved from zip archives. There is no `node_modules` directory at all on the default setup.

```sh
# enable modern Yarn in a project
corepack enable
corepack prepare yarn@stable --activate
yarn set version stable

# everyday commands
yarn install
yarn add <package>
yarn dlx <package>
```

The PnP model delivers real benefits: installs are fast, disk usage is minimal, and resolution is deterministic — the `.pnp.cjs` file is a complete, machine-readable dependency graph that can be committed (the "zero-install" workflow where CI never runs `yarn install` at all). Yarn's constraints system adds declarative, Prolog-style rules for enforcing dependency policies across a monorepo, something no other tool matches.

The cost is ecosystem friction. PnP's zip-based resolution breaks tools that expect a real `node_modules` directory, and while Yarn ships a `nodeLinker` option to fall back to classic installs, teams end up maintaining compatibility shims for native modules, older bundlers, and anything that shells out to `node_modules` paths. Berry is an excellent tool for teams that commit to its model; for everyone else, it is the highest-friction option on this list.

## Bun — The All-in-One Native Runtime

Bun (95,813 stars, pushed August 2026) is not primarily a package manager — it is a JavaScript runtime written in Zig, and `bun install` is one component alongside its bundler, test runner, and TypeScript transpiler. The package manager inherits the runtime's philosophy: native code, no Node.js dependency, and performance as the headline feature. Installs are routinely an order of magnitude faster than npm cold installs, and Bun keeps a global content-addressable cache with hard links, so repeated installs across projects are nearly instant and disk-cheap.

```sh
# install Bun (single binary, no Node.js required)
curl -fsSL https://bun.sh/install | bash

# everyday commands
bun install
bun add <package>
bun add -D <package>
bun remove <package>
bun update
bunx <package>   # run a package without installing it
```

Bun's configuration file, `bunfig.toml`, sits alongside `package.json` and is only used for Bun-specific settings — Bun reads `package.json` and `tsconfig.json` for everything else:

```toml title="bunfig.toml"
# scripts to run before `bun run`-ing a file or script
# register plugins by adding them to this list
preload = ["./preload.ts"]
```

A `bunfig.toml` in the project root is local config; a `~/.bunfig.toml` applies globally, and local keys override global ones. Bun reads the same npm registry, so it works with private registries and existing packages, and it writes its own lockfile (`bun.lockb` historically, `bun.lock` in newer versions).

The honest caveats: Bun's package manager is younger than pnpm's, its workspace support is functional but less battle-tested, and because it does not run on Node.js, some postinstall scripts and native modules that assume a Node environment need workarounds. Bun is also not a drop-in for the Node runtime in every production scenario yet, although the gap narrows with every release. If your whole toolchain lives in Bun, `bun install` is a joy; if you use Bun only as a package manager inside a Node.js project, it works, but you lose some of the coherence that makes it special.

## Pitfalls and Migration Traps

**1. Never mix lockfile generations.** If your repository's lockfile is `package-lock.json`, do not let a stray `yarn install` or `bun install` create a second lockfile. Inconsistent dependency resolution between developers and CI is the classic "works on my machine" trigger. Pick one manager, commit its lockfile, and enforce it in CI by failing the build if another lockfile appears.

**2. pnpm's strict `node_modules` will break code that was written for npm's hoisting.** The most common migration pain: code that imports a package it never declared. pnpm surfaces these as hard errors, which is the point — but expect a cleanup pass across your codebase during migration. Run `pnpm approve-builds` (or the equivalent allowlist) for packages with postinstall scripts that pnpm blocks for security.

**3. Yarn 1.x is frozen — stop starting projects on it.** It still works, but it receives no features and only critical fixes. If you are on Yarn 1, either migrate to Berry (with the `nodeLinker: node-modules` fallback if PnP is too disruptive) or move to pnpm.

**4. Native modules and PnP do not mix without configuration.** PnP's zip-based resolution breaks `node-gyp` rebuilds and any package that expects physical paths. If your project depends on native modules (sharp, bcrypt, canvas), budget time for Yarn's `nodeLinker` settings or skip PnP entirely.

**5. Bun is fast, but verify your production runtime.** Using `bun install` for dependency management while deploying on Node.js is fine. Deploying your application on the Bun runtime is a separate decision — benchmark your workloads, check native module compatibility, and keep a Node.js fallback path until you are confident.

**6. Self-hosting the registry changes the equation.** All four tools talk to the npm registry, which means you can [self-host a package registry or proxy](../2026-05-02-self-hosted-extension-marketplace-package-registry-guide/) — or pin one of the [self-hosted registry servers like Nexus, Verdaccio, or Pulp](../self-hosted-package-registry-nexus-verdaccio-pulp-guide-2026/) — without changing your package manager. Cache and mirror policies can matter more to CI speed than the client you pick.

**7. Workspaces are not a replacement for build orchestration.** A package manager resolves and links workspace packages; it does not decide what to build in what order. For large monorepos, pair your package manager with a proper build system — see our [monorepo build systems comparison (Nx, Turborepo, Bazel)](../2026-06-16-self-hosted-monorepo-build-systems-nx-turborepo-bazel/) for how the pieces fit together.

## How to Migrate Without Breaking Everything

The safest migration path is the same for all four tools: start on a branch, commit the new lockfile, and run the full test suite plus a production build before merging. For npm → pnpm, the strict `node_modules` will surface undeclared imports immediately — treat every error as a genuine bug fix, not a nuisance. For npm → Bun, run `bun install` after deleting the old lockfile and verify that postinstall scripts for native modules completed. Keep the old lockfile in git history, never in your working tree, and add a CI check that the canonical lockfile is unchanged after install. If you manage multiple languages, note that [Swift's package managers have their own ecosystem](../2026-07-31-swift-package-managers-spm-cocoapods-carthage/) and [JavaScript bundlers like esbuild, Rollup, and Turbopack](../2026-06-21-javascript-build-bundlers-esbuild-rollup-parcel-swc-turbopack/) sit one layer above the package manager — choices there are orthogonal to this one.

## FAQ

**Which JavaScript package manager is fastest in 2026?**
Bun is the fastest on cold and warm installs thanks to its native Zig implementation and global content-addressable cache. pnpm is the fastest of the Node.js-based managers, typically 2-3x faster than npm on cold installs.

**Does pnpm work with npm's lockfile?**
No. pnpm uses its own `pnpm-lock.yaml`. Migrating from npm means deleting `package-lock.json` and generating a fresh lockfile — resolution results will be equivalent, but the files are not interchangeable.

**Is Yarn dead?**
Yarn 1.x is frozen, but Yarn Berry (v2+) is actively developed. If you encounter "Yarn" advice from before 2021, check which major version it refers to — the ecosystem has effectively split into two tools with the same name.

**Can Bun be used just as a package manager with Node.js?**
Yes. `bun install` works against the npm registry and produces a Bun lockfile while your application still runs on Node.js. Bun only needs to be installed on machines where you run package manager commands.

**What is the phantom dependency problem?**
With npm's hoisted `node_modules`, your code can import a package that is not listed in your `package.json` because it was hoisted from a transitive dependency. This works until something changes the tree and breaks CI. pnpm's strict layout eliminates this class of bug.

**Which package manager should a monorepo use?**
pnpm is the community default for monorepos: `pnpm-workspace.yaml` plus the `workspace:` protocol plus `--filter` targeting is the most complete workspace implementation. Yarn Berry is a strong alternative if you adopt PnP and constraints.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript Package Managers in 2026: npm vs pnpm vs Yarn vs Bun",
  "description": "Compare npm, pnpm, Yarn Berry, and Bun package managers on install speed, disk usage, monorepo support, and migration risk to choose the right one for 2026.",
  "datePublished": "2026-08-31",
  "dateModified": "2026-08-31",
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
