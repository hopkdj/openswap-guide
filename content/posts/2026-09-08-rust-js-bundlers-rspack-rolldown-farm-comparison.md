---
title: "Rust JavaScript Bundlers in 2026: Rspack vs Rolldown vs Farm — Is Webpack Finally Dead?"
date: "2026-09-08"
tags: ["javascript", "typescript", "bundler", "build-tools", "rust", "frontend", "developer-tools"]
draft: false
---

Your CI build time is a tax you pay on every commit, and for large frontend monorepos that tax used to be measured in minutes of webpack grinding. Between 2024 and 2026 the entire bundler landscape was rewritten in Rust: **Rspack** (12,890 stars, MIT) modernizes the webpack API so existing projects can swap engines, **Rolldown** (13,943 stars, MIT) is the Rollup-compatible Rust bundler destined to power Vite itself, and **Farm** (5,590 stars, MIT) is a Vite-compatible, production-ready build tool that declares itself 1.0 stable. All three are MIT-licensed, all three are written in Rust, and all three are fast enough that the question is no longer "should I leave webpack?" but "which Rust bundler do I migrate to — and what breaks along the way?"

## TL;DR / Quick Verdict

If you maintain a **large webpack project** (loaders, plugins, Module Federation) and want the least-risk speedup, choose **Rspack** — it is explicitly built as a drop-in webpack replacement with first-class Module Federation support. If you live in the **Rollup/Vite ecosystem** — library authoring, Vite apps, Rollup plugin chains — choose **Rolldown**, which shares Rollup's plugin interface and is positioned as the future bundler inside Vite. If you want a **fresh Vite-style setup** with persistent caching and direct Vite plugin compatibility but no webpack baggage, evaluate **Farm**, which has been stable since its 1.0 release. Do not migrate any of them for benchmark bragging alone: your real win is measured in dev-server latency and CI minutes, and each tool extracts that win differently.

## Head-to-Head Comparison Table

| Dimension | Rspack | Rolldown | Farm |
|---|---|---|---|
| **Stars (Sep 2026)** | 12,890 | 13,943 | 5,590 |
| **License** | MIT | MIT | MIT |
| **Core language** | Rust | Rust | Rust |
| **Last push (Sep 2026)** | 2026-09-08 | 2026-09-08 | 2026-06-14 |
| **API lineage** | webpack-compatible | Rollup-compatible | Vite-compatible |
| **Plugin ecosystem** | webpack loaders/plugins | Rollup plugins | Vite plugins (since v0.13) |
| **Module Federation** | First-class | No | No |
| **Vite integration** | Via Rsbuild layer | Future Vite bundler (rolldown-vite) | Vite-compatible API |
| **Persistent cache** | Yes (incremental) | Yes | Yes (default since v0.14) |
| **Backing org** | Rstack (ByteDance ecosystem) | VoidZero Inc. | Farm ecosystem |
| **Stability signal** | Production webpack replacement | Pre-1.0 but powers Vite previews | 1.0 stable, "production ready" |
| **Best for** | Existing webpack apps | Rollup/Vite/library tooling | New Vite-style projects |

## Decision Matrix: Pick in 10 Seconds

| Use case | Recommendation | Why |
|---|---|---|
| Existing webpack app, want speed without rewriting config | **Rspack** | Seamless webpack API replacement; loaders, plugins, and Module Federation carry over |
| Library author publishing ESM/CJS builds via Rollup | **Rolldown** | Rollup-compatible plugin interface; same output mental model, Rust speed |
| Vite app waiting for the next-generation core | **Rolldown** | Explicitly "intended to serve as the future bundler used in Vite" |
| Greenfield project, Vite-style DX, want caching out of the box | **Farm** | 1.0 stable, Vite plugins usable directly, persistent cache on by default |
| Monorepo with 20+ webpack packages | **Rspack + Rsbuild** | Rstack tooling is designed around unified fast builds (see the monorepo guide below) |
| You need webpack-exclusive loaders with no Rust equivalent | **Stay on webpack (for now)** | Plugin parity is broad but not absolute; audit before committing |

## Rspack — The Webpack Successor

Rspack's README states the mission precisely: "a fast Rust-based bundler for the web. It modernizes the webpack API to enable seamless replacement of webpack while delivering lightning-fast build speeds." The compatibility bet is what makes it the safest migration: webpack plugins and loaders from the community ecosystem keep working, tree shaking and minification are built in, and Module Federation — the orchestration feature large micro-frontend setups depend on — is a first-class citizen rather than an afterthought. Rspack is part of Rstack, a unified Rust toolchain that also includes Rsbuild (build tool), Rspress (static site generator), and Rsdoctor (bundle analysis).

A real project config from the official examples directory shows how close the API feels to webpack:

```js
// examples/basic/rspack.config.mjs from the rspack repo
import path from 'node:path';
import { defineConfig } from '@rspack/cli';

export default defineConfig({
  context: import.meta.dirname,
  entry: {
    index: './src/index.js',
  },
  output: {
    path: path.resolve(import.meta.dirname, 'dist'),
  },
});
```

For a webpack team, migrating means renaming the package and fixing the few configuration keys that differ — then watching startup and rebuild times drop by an order of magnitude on typical applications. The main cost is trust: webpack's long tail of niche loaders is large, and while Rspack's compatibility story is the strongest of the three, your specific exotic loader is the one thing to verify in a spike before you commit the whole team.

## Rolldown — The Rollup-Compatible Future of Vite

Rolldown describes itself as "a JavaScript/TypeScript bundler written in Rust intended to serve as the future bundler used in Vite. It provides Rollup-compatible APIs and plugin interface, but will be more similar to esbuild in scope." That sentence matters twice: it inherits Rollup's *plugin interface* (so Rollup plugins are the compatibility target), and it inherits esbuild's *scope* (fast, focused, no kitchen sink). It is a project of VoidZero, the company founded by Evan You, and it builds on the oxc project for its parser, resolver, and sourcemap support — the same oxc lineage that powers the Biome-adjacent Rust toolchain wave.

Its config surface is deliberately small. The official `basic-typescript` example shows a genuine edge worth knowing about: the oxc resolver does not yet assume default export conditions, so you must say so explicitly:

```js
// examples/basic-typescript/rolldown.config.js from the rolldown repo
import { defineConfig } from 'rolldown';

export default defineConfig({
  input: {
    entry: './index.ts',
  },
  resolve: {
    // This needs to be explicitly set for now because oxc resolver doesn't
    // assume default exports conditions. Rolldown will ship with a default
    // that aligns with Vite in the future.
    conditionNames: ['import'],
  },
  plugins: [
    // Rollup-style plugin objects work here
    {
      name: 'example',
      renderChunk(code) {
        return code;
      },
    },
  ],
});
```

If your world is Rollup — library builds, dual ESM/CJS output, plugin chains like `@rollup/plugin-node-resolve` — Rolldown is the least surprising Rust upgrade, because the plugin contract you already know is the contract it speaks. Its legal housekeeping is also worth a footnote: the project is MIT-licensed but contains code derived from Rollup and esbuild, with those third-party MIT licenses listed in `THIRD-PARTY-LICENSE`.

## Farm — The Vite-Compatible Independent

Farm's README opens with a sharp critique of the status quo: webpack "is too slow," and Vite — while fast for small projects — "has a lot of drawbacks" on large ones: a huge number of dev-time requests per page (hundreds or thousands of modules, so refreshes take seconds), inconsistency between development and production (different strategies and tools in each phase make online bugs hard to debug), and inflexible code splitting. Farm's answer is a Rust core with module-level caching — "any module won't be compiled twice until it's changed" — and it has shipped the two features that make it practical today: Vite plugins usable directly since v0.13, and persistent disk cache enabled by default since v0.14. The project declares itself **1.0 stable and production ready**, with HMR updates claimed in the 20 ms range for most situations.

Getting started is a one-liner, straight from the README:

```bash
# with npm
npm create farm@latest
# with yarn
yarn create farm@latest
# with pnpm
pnpm create farm@latest
```

A real configuration from the repo's React example shows the shape — Farm keeps everything under a `compilation` object, with persistent caching configured explicitly:

```js
// examples/react/farm.config.js from the farm repo
import { defineConfig } from "@farmfe/core";
import react from "@farmfe/plugin-react";

export default defineConfig(() => {
  return {
    compilation: {
      sourcemap: true,
      persistentCache: {
        cacheDir: "node_modules/adny/cache",
      },
      presetEnv: false,
      minify: false,
      progress: false,
      runtime: {
        isolate: true,
      },
    },
    server: {
      port: 4000,
      proxy: {
        "^/(api|login|register|messages)": {
          target: "https://petstore.swagger.io/v2",
        },
      },
    },
  };
});
```

Farm is the most "new project" of the three: you would not migrate a webpack app to it, but a team starting fresh — especially one that liked Vite's DX but hit its large-project ceilings — gets a coherent, caching-first tool with a smaller ecosystem gamble than betting on a pre-1.0 core.

## Migration and Operational Pitfalls

- **Benchmark claims are vendor-published.** Farm's README asserts it is "20x faster than webpack and 10x faster than Vite," with a linked performance-compare repository; Rspack and Rolldown publish CodSpeed dashboards. Treat all of these as directional. Rebuild *your* app with each candidate and measure cold CI install, cold build, warm rebuild, and HMR latency separately — the ordering of tools can differ per metric.
- **Plugin parity is the real migration cost, not speed.** Rspack targets webpack loaders/plugins, Rolldown targets Rollup's interface, Farm targets Vite plugins. Your lock-in is whichever plugin chain your app actually uses. Audit every loader/plugin in `package.json` against the target's compatibility list before committing — the long tail is where migrations stall.
- **Oxc resolver semantics differ from Node.** Rolldown's own example documents that `conditionNames: ['import']` must be set explicitly because the oxc resolver does not yet assume default export conditions. If a package suddenly resolves differently after migration, check export conditions before blaming the package.
- **Development/production consistency is a feature, not an accident.** Vite's dev server serves unbundled ESM while production builds a bundle — the mismatch bites in subtle ways. All three Rust bundlers unify the pipeline; if your team has been bitten by "works in dev, breaks in prod," that consistency is worth more than raw speed.
- **Module Federation locks you to the webpack lineage.** If your architecture depends on Module Federation, Rspack (first-class support) is effectively your only choice among the three; Rolldown and Farm do not offer it. Conversely, if you do *not* need it, Rspack's webpack compatibility is a smaller advantage.
- **Version pinning and release cadence.** Rolldown is pre-1.0 and moving fast (its config defaults are still changing — the `conditionNames` note says a Vite-aligned default "will ship in the future"); Farm's last push at the time of writing was mid-June 2026. Pin exact versions in CI and re-run your benchmark suite after every upgrade rather than trusting semver ranges.
- **Native binaries multiply in monorepos.** Rust bundlers ship platform-specific native bindings (napi-rs style). Ensure your CI matrix and self-hosted runners can fetch or cache those binaries — air-gapped environments need a mirror strategy or every build re-downloads them.

These tools sit on top of a fast-moving JavaScript platform. For the runtime layer underneath, our [Node.js vs Bun vs Deno runtime comparison](../2026-08-28-nodejs-vs-bun-vs-deno-javascript-runtimes-comparison/) matters because native-binary tooling behaves differently across runtimes, and the [JavaScript build bundlers guide (esbuild vs Rollup vs Parcel vs SWC vs Turbopack)](../2026-06-21-javascript-build-bundlers-esbuild-rollup-parcel-swc-turbopack/) documents the previous generation these Rust tools are replacing. If you are choosing a bundler as part of a larger repo restructure, our [monorepo build tools comparison (Nx vs Turborepo vs Rush)](../2026-09-08-javascript-monorepo-build-tools-nx-turborepo-rush-comparison/) shows how task orchestration layers on top of whichever bundler you pick.

## FAQ

**Is webpack dead in 2026?**
Not dead, but its successor is clear. Rspack implements the webpack API in Rust, so the webpack ecosystem's plugins and loaders continue to run on a much faster engine. For new projects, none of the three Rust bundlers pushes webpack itself; for existing projects, Rspack is the migration path that preserves the most investment.

**Which Rust bundler is used by Vite?**
Rolldown is the one positioned for Vite: its README states it is "intended to serve as the future bundler used in Vite," and it provides a Rollup-compatible API and plugin interface. Farm is *Vite-compatible* in API shape but is an independent project, not Vite's engine.

**Can I use my existing webpack loaders with Rspack?**
Mostly yes — webpack ecosystem compatibility is Rspack's core promise, including loaders, plugins, and Module Federation. The caveat is the long tail: exotic or unmaintained loaders may not be covered, so audit your exact dependency list before migrating.

**Do these bundlers work with React, Vue, or framework X?**
Yes. All three are framework-agnostic: Rspack's examples include React and vanilla projects, Rolldown's examples cover TypeScript, Vue, and HMR scenarios, and Farm ships create-farm templates for React, Vue, Solid, Svelte, and vanilla. Framework-specific transforms come from plugins (for example Farm's `@farmfe/plugin-react`).

**How much faster are Rust bundlers in practice?**
Vendor benchmarks claim 10-20x over webpack, but realistic gains depend on your project. The consistent, reproducible wins are faster cold starts and incremental rebuilds thanks to persistent caches; HMR improvements matter most for large dev servers. Measure your own app before and after — CI minutes and dev-server latency are the numbers that count.

**Are Rspack, Rolldown, and Farm all truly open source?**
Yes — all three are MIT-licensed with public repositories. Rolldown's MIT license covers code it derives from Rollup and esbuild, with the third-party licenses documented in its repository. Rspack is developed under the Rstack umbrella and Rolldown under VoidZero; both are funded commercial ecosystems around open cores.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust JavaScript Bundlers in 2026: Rspack vs Rolldown vs Farm — Is Webpack Finally Dead?",
  "description": "Deep comparison of the three Rust-based JavaScript bundlers in 2026: Rspack (webpack-compatible), Rolldown (Rollup-compatible, future Vite core), and Farm (Vite-compatible, 1.0 stable), with real configs, benchmarks guidance, and migration pitfalls.",
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
