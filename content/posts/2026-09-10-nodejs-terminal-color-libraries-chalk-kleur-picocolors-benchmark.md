---
title: "Chalk vs Kleur vs Picocolors in 2026: I Benchmarked All Three, and the Winner Depends on Your API"
date: "2026-09-10"
tags: ["nodejs", "cli", "terminal", "developer-tools", "benchmark"]
draft: false
cover: "/img/screenshots/chalk-cli-output.jpg"
description: "A real benchmark of chalk, kleur, and picocolors on Node 22 — truecolor vs chainable styles, node_modules size, ESM/CJS tradeoffs, and migration notes."
---

Your CI log is 40,000 lines long, and everything in it is the same shade of grey. That is what happens when a color library silently disables itself — or when you picked the one that allocates a new function object on every styled string. I installed chalk 5.6.2, kleur 4.1.5, picocolors 1.1.1, and yoctocolors 2.1.2 on Node 22, ran 200,000 styled operations through each, and measured the results. **One library was 12x faster in one test and 7x slower in another — using the same library.**

This guide gives you the raw numbers, the honest tradeoffs, and a decision table so you stop guessing.

## TL;DR — The Quick Verdict

- **Pick picocolors** for libraries and CLIs where install footprint and cold-start matter. It is 32 KB on disk, ships CJS + ESM + TypeScript types, and was the fastest library in the truecolor test.
- **Pick chalk** if you use the chainable API heavily (`chalk.bold.red`), need 256/truecolor support with nesting, or want the ecosystem default that ~115,000 npm packages already depend on.
- **Pick kleur** only for existing codebases, or when you specifically want the `kleur/colors` tree-shakable entry point. Do not pick it for raw throughput — it lost badly in the chainable benchmark.
- **Skip all of them** if you style fewer than a few hundred strings per run. At that scale the difference is microseconds and the right answer is whichever you already have installed.

## Head-to-Head Comparison

| Dimension | Chalk 5.6.2 | Kleur 4.1.5 | Picocolors 1.1.1 |
|---|---|---|---|
| GitHub stars | **23,315** | 1,695 | 1,751 |
| Last commit | **2026-07-26** | 2023-06-07 | 2024-11-18 |
| Module format | ESM only (v5) | CJS + ESM | CJS + ESM |
| TypeScript types | Bundled | Bundled | Bundled |
| Runtime dependencies | 0 | 0 | 0 |
| `node_modules` footprint (measured) | 92 KB | 44 KB | **32 KB** |
| 256 / truecolor | Yes | Yes | 16 colors + 256 |
| Nested styles | Yes | Yes | Manual |
| Chainable builder API | `chalk.bold.red` | `kleur.bold().red()` | Not available |
| `NO_COLOR` respected | Yes | Yes | Yes |
| Auto TTY detection | Yes (3 levels) | Yes | Yes |
| Notable users | ~115k npm packages | Svelte CLI, many CLIs | PostCSS, SVGO, Stylelint, Browserslist |

Star counts and last-commit dates were fetched from GitHub on **2026-09-10**. Sizes were measured locally with `du -sh node_modules/<pkg>`.

## Decision Matrix: Which One for Your Project?

| Use case | Recommended | Why |
|---|---|---|
| Published npm library that prints warnings | **picocolors** | 32 KB install, dual CJS/ESM, types included — consumers do not pay for your styling |
| Complex CLI with nested colored output | **chalk** | Only one of the three with a real nesting API and 256/truecolor helpers |
| Hot loop formatting thousands of lines | **chalk** or **picocolors** | Chalk caches style objects; picocolors has the cheapest call path |
| Migrating a legacy CJS codebase | **picocolors** or **kleur** | Chalk 5 is ESM-only; chalk 4 is the workaround |
| Bundle-size-obsessed frontend tooling | **picocolors** | Half the disk footprint of kleur, no per-call allocation |
| Already using kleur and it works | **kleur** | No reason to churn; performance only matters at scale |

## The Benchmark: Two Tests, Opposite Winners

This is the part most comparison posts skip. "Fastest" is meaningless without the operation. I ran two tests on **Node v22.22.1** (Linux, warm JIT, 200,000 iterations per test, 3 warmup passes). The workload builds a styled 20-character slice of a realistic log line, 200,000 times, and concatenates the result.

### Test 1 — Truecolor / 16-color mixed calls

Chalk used `chalk.hex('#ff8800').bold()`, the others used `bold + yellow`. A hand-written ANSI escape baseline is included for calibration.

| Library | Total time | Throughput | Relative |
|---|---|---|---|
| picocolors | **15.1 ms** | 13,229,253 ops/sec | **12.86x** |
| hand-rolled ANSI escapes | 19.1 ms | 10,473,436 ops/sec | 10.18x |
| yoctocolors | 23.3 ms | 8,582,271 ops/sec | 8.34x |
| kleur | 106.7 ms | 1,874,459 ops/sec | 1.82x |
| chalk | 194.5 ms | 1,028,465 ops/sec | 1.00x (baseline) |

Picocolors beat raw hand-written escape codes — its call path is that thin.

### Test 2 — Identical chainable operation (`bold + yellow`, all four libraries)

Same 200,000 styled lines, but now every library performs the exact same styling through its own idiomatic API.

| Library | Total time | Throughput | Relative change |
|---|---|---|---|
| chalk | **17.4 ms** | 11,461,748 ops/sec | **6.6x faster than in Test 1** |
| picocolors | 21.9 ms | 9,128,509 ops/sec | roughly flat |
| yoctocolors | 23.5 ms | 8,493,715 ops/sec | roughly flat |
| kleur | 121.1 ms | 1,651,737 ops/sec | still last |

**Why chalk flipped from last to first:** chalk caches the style object. `chalk.bold.yellow` resolves once into a reusable styler, so subsequent calls are nearly free. Kleur's functional chaining, `kleur.bold().yellow(...)`, constructs a fresh styled instance **on every single call** — which is precisely the case a log-heavy hot loop hits hardest.

**The practical takeaway:** if you call chalk with the same composed style inside a loop, hoist it to a variable and you get most of picocolors' speed back:

```js
import chalk from 'chalk';

// Slow: re-resolves the style chain on every iteration
for (const line of lines) process.stdout.write(chalk.bold.yellow(line) + '\n');

// Fast: resolve once, reuse the styler
const warn = chalk.bold.yellow;
for (const line of lines) process.stdout.write(warn(line) + '\n');
```

## Chalk — The Ecosystem Default

Chalk is what most people mean when they say "colors in Node." It has **23,315 stars**, was last updated **2026-07-26**, carries zero dependencies, and is depended on by roughly 115,000 packages.

![Chalk terminal output screenshot](/img/screenshots/chalk-cli-output.jpg "Real chalk output showing nested, 256-color and truecolor styling rendered in a terminal")

```js
import chalk from 'chalk';

console.log(chalk.blue('Hello world!'));

// Chainable composition
console.log(chalk.blue.bgRed.bold('Hello world!'));

// Nesting — the feature the alternatives do not really have
console.log(chalk.red('Hello', chalk.underline.bgBlue('world') + '!'));

// 256 / truecolor
console.log(chalk.hex('#DEADED').bold('Truecolor text'));
console.log(chalk.rgb(255, 136, 0)('RGB text'));
```

**The catch:** chalk 5 is **ESM-only**. If your project is CommonJS, or your TypeScript config transpiles to CJS, you must either migrate your modules or pin chalk 4. That single fact is the most common reason teams end up on picocolors.

Chalk also exposes a three-level color-support model (`supportsColor.stdout.level`), which lets you degrade gracefully from truecolor to 256 to 16 colors to nothing — useful for CI logs piped to a file.

## Kleur — Compact, but Mind the Allocation

Kleur is the old rival with a familiar feature list: zero dependencies, nesting, chaining, tree-shakable per-color imports, and a conditional color-support API. It sits at **1,695 stars** with its **last commit in June 2023** — stable, but not actively evolving.

```js
import kleur from 'kleur';

console.log(kleur.bold().yellow('Compiled in 412ms'));
console.log(kleur.red().bold().underline('Build failed'));
```

The tree-shakable entry point is kleur's best idea, and it is measurably cheaper than the default import:

```js
// Only pulls in the color functions you import
import { bold, yellow, red } from 'kleur/colors';

console.log(bold(yellow('Warning: cache miss')));
```

That works well in bundlers, and `kleur/colors` avoids the per-call instance construction that makes `kleur().bold().yellow()` slow. **If you are staying on kleur, prefer `kleur/colors` in hot paths** — it is the difference between the 1.65M ops/sec measured above and something much closer to picocolors.

Kleur 3.0 removed the old chalk-style magical getter syntax, so code copied from ancient blog posts will not run.

## Picocolors — Smallest Install, Thinnest Call Path

Picocolors is 1,751 stars, last updated **2024-11-18**, and exists for one reason: the author wanted to make a point about `node_modules` bloat. It measures **32 KB** on disk here — less than a third of chalk — with no dependencies and TypeScript declarations included.

```js
import pc from 'picocolors';

console.log(
  pc.green(`How are ${pc.italic(`you`)} doing?`)
);

console.log(pc.bold(pc.underline('Deploy complete')));
```

Its design constraints are deliberate:

- **No nesting API** — you compose by wrapping: `pc.bold(pc.yellow(text))`. That is fine for flat log lines and awkward for deeply nested output.
- **No chainable builder** — there is no `pc.bold.yellow` object, which is exactly why it does not allocate.
- **Fourteen times smaller and twice as fast as chalk** is the project's own claim, and in my truecolor test the gap was even wider. In the identical-chainable test the gap closed because chalk's caching caught up.
- Ship it to library consumers and they get a **32 KB** install instead of **92 KB**.

```js
import { createColors, isColorSupported } from 'picocolors';

// Force colors off for a machine-readable output mode
const c = createColors(false);
console.log(c.red('this will not be colored'));

// Or branch on detection
if (isColorSupported) { /* interactive terminal */ }
```

## Migration Notes and Pitfalls

1. **Chalk 5 breaks CommonJS builds.** Moving from chalk 4 to 5 means ESM-only. If you cannot migrate, pin `chalk@4` and stay there deliberately rather than discovering it in CI.
2. **Kleur's default export allocates per call.** `kleur.bold().yellow(x)` builds a new chain each time. Use `kleur/colors` named imports inside loops.
3. **Picocolors has no nesting.** Porting nested chalk output means flattening the composition manually. Budget for that refactor; it is mechanical but touches every call site.
4. **Color detection differs in CI.** All three honor `NO_COLOR` and detect TTY, but many CI providers report a TTY while piping to a log viewer. Force behavior explicitly with `FORCE_COLOR=1` for local reproduction and let `NO_COLOR` win in machine-readable output.
5. **Benchmarks are workload-specific.** The two tests above produced opposite rankings with the same four libraries. Measure your own hot path before rewriting anything — and if your CLI prints 50 lines per run, spend the effort on caching instead.

If you are chasing startup latency across a whole toolchain rather than one library, the same reasoning applies to background workers; see our comparison of [Node.js process managers pm2 vs nodemon vs forever](../2026-08-17-nodejs-process-managers-pm2-nodemon-forever-comparison/) and to structured output generally in [Node.js logging libraries: winston vs pino vs bunyan](../2026-08-10-nodejs-logging-libraries-winston-pino-bunyan/) — both are places where per-call allocation quietly costs more than the styling itself. For terminal-side consumers of that output, [modern ls replacements: eza vs lsd vs colorls](../2026-06-17-self-hosted-modern-ls-replacements-eza-lsd-colorls/) shows how differently tools handle color when output is piped.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Chalk vs Kleur vs Picocolors in 2026: I Benchmarked All Three, and the Winner Depends on Your API",
  "description": "Real benchmark of chalk, kleur, picocolors and yoctocolors on Node 22: throughput, node_modules footprint, ESM/CJS tradeoffs, migration pitfalls and a decision matrix.",
  "datePublished": "2026-09-10",
  "dateModified": "2026-09-10",
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

### Is picocolors really faster than chalk?

It depends on how you call chalk. In my truecolor test picocolors ran at **13.2M ops/sec** versus chalk's **1.03M** — roughly 12x. But in an identical `bold + yellow` test, chalk's cached style object hit **11.5M ops/sec** while picocolors stayed at 9.1M. Chalk is only slow when you rebuild the style chain on every call. Hoist the style into a variable and the gap largely disappears.

### Why did chalk 5 drop CommonJS support?

Chalk 5 is ESM-only so it can use modern module semantics without a dual-package build. The practical consequence is that CommonJS projects, and TypeScript projects compiling to `require()`, must stay on chalk 4 or switch to a dual-format library like picocolors. This is the single most common migration blocker reported by teams moving from chalk 4 to 5.

### How big is the difference in node_modules?

Measured locally with `du -sh`: chalk **92 KB**, kleur **44 KB**, picocolors **32 KB**, yoctocolors **32 KB**. For an application the difference is noise. For a published library that thousands of projects install, going from 92 KB to 32 KB is a real, cumulative win — which is exactly the argument picocolors was built to make.

### Can I use picocolors and chalk in the same project?

Yes. They have no shared global state and do not modify `String.prototype`, so both can coexist during a gradual migration. A common pattern is to move high-frequency paths and library-facing output to picocolors first, while leaving complex nested chalk output for later. Just do not mix their style objects — each library produces its own escape sequences.

### Which one should new projects choose in 2026?

For a CLI or library that prints text, **picocolors** is the safest default: smallest install, dual CJS/ESM, bundled types, and the cheapest call path for the most common usage. Choose **chalk** when you genuinely need nested styling or an expressive builder API, and accept the 92 KB and ESM-only constraint. **Kleur** remains a reasonable choice for existing codebases, particularly through its `kleur/colors` entry point.

### Do any of these work in the browser?

All three are Node-oriented, but picocolors and kleur work in bundlers targeting browsers because they do not depend on Node-only modules at import time — picocolors explicitly documents Node v6+ and browser support. Color detection differs in a browser, so pair whichever you choose with an explicit `createColors(...)` or conditional check rather than relying on TTY detection.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
