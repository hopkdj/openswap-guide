---
title: "SVGO vs svgcleaner vs Scour in 2026: Which SVG Optimizer Actually Shrinks Your Assets?"
date: "2026-10-26"
tags: ["svg", "web-performance", "developer-tools", "asset-optimization", "cli"]
description: "A hands-on comparison of SVGO, svgcleaner and Scour: real CLI flags, working configs, compression behavior, and the pitfalls that silently break icons in production."
draft: false
---

Your designer exports a 14 KB logo from Figma. Your build ships it as a 14 KB logo, plus 60 % of that file is editor metadata, unused `defs`, and decimal coordinates with six digits. Multiply that by the 200 icons in your design system and you have shipped a megabyte of XML that nobody wrote and nobody reviews.

SVG is text, so it compresses — but it does not optimize itself. Three command-line optimizers dominate the space in 2026: **SVGO** (the Node.js default), **svgcleaner** (the Rust brute-force cleaner), and **Scour** (the Python classic that still powers Inkscape's "Optimized SVG" export). They look interchangeable. They are not: they disagree on what "safe" means, they handle precision very differently, and one of them has not shipped a release since 2021.

## TL;DR: Quick Verdict

**Use SVGO** if you have a Node toolchain, want a maintained plugin ecosystem, and need reproducible config checked into your repo. **Use svgcleaner** when you need maximum lossless shrinkage on a one-off batch and can pin a version, because it squeezes harder than SVGO out of the box — but it is unmaintained. **Use Scour** when your pipeline is Python or when you need conservative, geometry-preserving output you can audit line by line. For new projects in 2026, SVGO is the correct default; the other two are specialist tools.

## Side-by-Side Comparison

| Dimension | SVGO | svgcleaner | Scour |
|---|---|---|---|
| GitHub stars | **22,766** | 1,669 | 877 |
| Last commit | **2026-10-24** | 2021-10-30 (dormant) | 2024-08-16 |
| Language / runtime | JavaScript (Node.js) | Rust (static binary) | Python 3 |
| License | MIT | GPL-2.0 | Apache-2.0 |
| Config model | JS module (`svgo.config.js`), plugin pipeline | ~90 CLI flags | ~50 CLI flags + Python API |
| Multiround optimization | `--multipass` | `--multipass` | Single pass (rerun manually) |
| Precision control | Per-plugin params (`floatPrecision`) | `--paths-coordinates-precision` | `--set-precision` |
| Batch mode | Yes (`-f` folder, `-r` recursive) | Shell loop / pipes | Shell loop / pipes |
| Best fit | Build pipelines, design systems | Offline archive compression | Python toolchains, Inkscape parity |

Star counts and last-commit dates were read from the GitHub API at publish time; they move, the maintenance gap between SVGO and svgcleaner does not.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| Webpack/Vite/Next.js build, icons imported as components | **SVGO** | Official loader (`svgo-loader`), SVGR integration, config lives in the repo |
| One-off cleanup of 5,000 legacy SVGs before archiving | **svgcleaner** | Strongest defaults, single static binary, no runtime install |
| Python data pipeline generating charts as SVG | **Scour** | Native Python API, no subprocess, deterministic output |
| You must never alter geometry (technical drawings, maps) | **Scour** with precision flags | Conservative defaults, explicit viewBox control |
| You need brand logos to stay pixel-identical | **SVGO** with a locked plugin allow-list | Disable `removeViewBox`, `cleanupIds`, `convertShapeToPath` explicitly |
| Air-gapped machine, no package manager | **svgcleaner** | Static Rust binary, zero dependencies |

## SVGO: The Maintained Default

SVGO is the only one of the three with an active plugin community. It ships four official interfaces — CLI, Node.js library, browser bundle, and a Webpack loader — plus a long list of community integrations (SVGR, `postcss-svgo`, `grunt-svgmin`, Figma export plugins).

### Install and basic usage

```bash
# one-off, no install
npx svgo logo.svg -o logo.min.svg

# whole icon directory, recursive, multiple passes
npx svgo -f ./src/icons -r --multipass
```

The `--multipass` flag matters more than people expect: pass one removes metadata and collapses whitespace, which exposes duplicated attributes and unreferenced `defs` that only become visible on pass two.

### A production config that does not break icons

SVGO's defaults are aggressive. This `svgo.config.js` keeps accessibility attributes, preserves the `viewBox` (the single most common cause of "my icon disappeared" bugs), and caps numeric precision:

```javascript
// svgo.config.js
export default {
  multipass: true,
  floatPrecision: 3,
  plugins: [
    {
      name: 'preset-default',
      params: {
        overrides: {
          // keep viewBox — removing it breaks responsive scaling
          removeViewBox: false,
          // keep ids when CSS or SMIL animations target them
          cleanupIds: false,
          // do not convert <rect>/<circle> to <path> in hand-edited art
          convertShapeToPath: false,
        },
      },
    },
    'sortAttrs',
    {
      name: 'removeAttrs',
      params: { attrs: '(data-name|data-testid)' },
    },
  ],
};
```

Two overrides carry most of the weight in practice. `removeViewBox: false` prevents the classic failure where an icon scales to zero inside a flex container. `cleanupIds: false` prevents breakage when your CSS or a `<use href="#id">` sprite references an id that SVGO decided was unused.

### Where SVGO is weak

The plugin pipeline is JavaScript, so a build machine needs Node. Config drift is real: a plugin rename between minor versions silently changes output, and the actual compression ratio depends entirely on which plugins you left enabled. On a typical Figma export it removes 35–60 % of bytes; on an already-clean hand-written SVG it may remove under 10 %, and occasionally makes the file marginally larger because of attribute reordering.

## svgcleaner: Maximum Squeeze, Zero Maintenance

svgcleaner is a Rust binary with roughly ninety flags and defaults tuned for aggressive cleaning. Its own help output is the best documentation:

```text
USAGE:
    svgcleaner [FLAGS] [OPTIONS] <in-file> <out-file>

EXAMPLES:
    clean a file with default options:
    svgcleaner in.svg out.svg

    clean a file with custom options:
    svgcleaner --indent=2 --paths-coordinates-precision=5 \
      --join-arcto-flags=yes in.svg out.svg

    clean a file without default options:
    svgcleaner --no-defaults --remove-comments=yes in.svg out.svg

    clean a stream using UNIX pipes:
    cat in.svg | svgcleaner -c - > out.svg
```

Batch processing is a shell loop, which is fine because the binary starts in milliseconds:

```bash
mkdir -p out
find ./raw -name '*.svg' -print0 | while IFS= read -r -d '' f; do
  svgcleaner --multipass --indent=none "$f" "out/$(basename "$f")" || cp "$f" "out/"
done
```

Its defaults are more aggressive than SVGO's: `--convert-shapes`, `--ungroup-groups`, `--remove-title`, `--remove-desc`, and `--remove-metadata` are all **on** by default. If your SVGs are part of an accessible interface, that default set silently deletes `<title>` and `<desc>`, which are what screen readers announce. Start from `--no-defaults` when accessibility matters:

```bash
svgcleaner --no-defaults \
  --remove-comments=yes --remove-metadata=yes --remove-editor-data=yes \
  --paths-coordinates-precision=4 --indent=none in.svg out.svg
```

**The maintenance caveat is the deciding factor.** The repository's last commit is October 2021. It still compiles and still produces the smallest output of the three on most illustration-heavy files, but it does not understand newer SVG features (some filter primitives, newer `mask` usage) and its GPL-2.0 license is a problem if you plan to link it into a commercial product rather than call the binary.

## Scour: The Python Workhorse

Scour is what Inkscape calls when you choose "Optimized SVG". It is conservative, deterministic, and scriptable:

```bash
pip install scour

# standard
scour -i input.svg -o output.svg

# maximum scrubbing, with compressed SVGZ output
scour -i input.svg -o output.svgz --enable-viewboxing \
  --enable-id-stripping --enable-comment-stripping \
  --shorten-ids --indent=none
```

Note that `--enable-viewboxing` is opt-in. Scour deliberately will not restructure the document unless you ask, which is exactly why it is the safe choice for drawings where a coordinate transformation would be catastrophic.

Batch usage in Python — the reason to prefer Scour over shelling out to a Node CLI from a Python pipeline:

```python
from scour.scour import scourString
from scour.svg_regex import serialize

with open("chart.svg", encoding="utf-8") as fh:
    raw = fh.read()

optimized = scourString(
    raw,
    options="--enable-viewboxing --shorten-ids "
            "--set-precision=4 --indent=none",
)

with open("chart.min.svg", "w", encoding="utf-8") as fh:
    fh.write(optimized)
```

Scour's compression is usually the weakest of the three — expect 20–45 % on typical exports — because it refuses the structural rewrites (shape-to-path conversion, group flattening) that produce the big wins. In exchange, its output diffs cleanly, which matters if optimized assets are committed to git and reviewed.

## How to Benchmark Honestly

Do not trust blog-post percentages, including this one. Measure on your own corpus, because output size depends on who authored the file:

```bash
#!/usr/bin/env bash
# compare.sh — run all three optimizers over a folder of SVGs
total_raw=0; total_svgo=0; total_cleaner=0; total_scour=0
mkdir -p /tmp/bench/{svgo,cleaner,scour}

for f in raw/*.svg; do
  b=$(basename "$f")
  npx --yes svgo "$f" -o "/tmp/bench/svgo/$b" >/dev/null 2>&1
  svgcleaner --multipass --indent=none "$f" "/tmp/bench/cleaner/$b" >/dev/null 2>&1
  scour -i "$f" -o "/tmp/bench/scour/$b" --shorten-ids --indent=none >/dev/null 2>&1
  total_raw=$((total_raw + $(stat -c%s "$f")))
done

for t in svgo cleaner scour; do
  s=$(du -sb "/tmp/bench/$t" | cut -f1)
  echo "$t: $s bytes ($(( 100 - 100*s/total_raw ))% smaller)"
done
echo "raw: $total_raw bytes"
```

Always validate the result visually before shipping. A 70 % reduction that turns a two-tone icon monochrome is not an optimization, it is data loss.

## Pitfalls That Break Real Sites

**Removing `viewBox`.** The default in older SVGO configs and the most common cause of icons collapsing to 0×0 inside flex layouts. Keep it, always.

**Stripping ids referenced by CSS or `<use>`.** If your sprite sheet uses `<use href="#icon-arrow">`, id cleanup turns every icon blank. Either disable `cleanupIds`, or prefix ids instead of removing them.

**Float precision too low.** `floatPrecision: 1` is fine for flat UI icons and disastrous for maps, charts, and technical illustrations — curves visibly polygonize. Use 3–4 for anything non-trivial.

**Losing accessibility metadata.** `removeTitle` / `removeDesc` / `--remove-title` delete what screen readers announce. If the SVG is `role="img"`, those elements are the accessible name.

**Editor-specific attributes.** `data-name`, `inkscape:label`, and Figma's `id="paint0_linear_..."` are safe to strip — but only if no build step or test selector depends on them.

**Assuming output is stable across versions.** Pin the optimizer version in `package.json` or your Docker image. A plugin default flip between minor releases can change thousands of files in one commit and make review impossible.

**Optimizing already-optimized files repeatedly.** Multipass is not idempotent forever; run it once in CI, cache the output, and stop.

## Integrating Into a Build Pipeline

For a typical static site, the honest answer is a single `npm run` step, not a custom pipeline:

```json
{
  "scripts": {
    "optimize:svg": "svgo -f src/icons -r --multipass"
  }
}
```

If you generate charts server-side, keep the optimizer in the same language as the generator (Scour for Python, SVGO for Node) so you avoid a second runtime in the image. If you are optimizing an archive of legacy assets once, use svgcleaner and commit the binaries, because you will not want to rebuild a 2021 Rust project in three years.

For the broader picture, our [image optimization pipeline comparison](../2026-06-20-image-optimization-libraries-libvips-sharp-imagemagick-pillow/) covers raster compression, and the [web font toolkit comparison](../2026-10-06-font-manipulation-toolkits-fonttools-fontkit-opentypejs-fontforge/) handles the other half of asset weight. If your goal is measuring the effect rather than the file size, see [self-hosted web performance monitoring](../2026-04-21-sitespeedio-vs-webpagetest-vs-lighthouse-self-hosted-web-performance-monitoring-2026/), and if you serve assets from a static generator, the [static site generator comparison](../self-hosted-static-site-generators-hugo-jekyll-astro-eleventy-guide/) explains where the optimization step belongs.

## FAQ

**Is SVGO still the best SVG optimizer in 2026?**
Yes for maintained projects. It is the only one of the three with commits in 2026, an active plugin ecosystem, and first-class integrations for Webpack, Vite/PostCSS, and React via SVGR. svgcleaner produces slightly smaller files but has been dormant since 2021.

**Does optimizing SVG reduce quality?**
Not if precision is kept at 3–4 decimal places and structural rewrites are limited. Lossless-looking output is normal for UI icons. Problems appear when precision drops to 1–2 or when `convertShapeToPath` and id cleanup are enabled on artwork that depends on them.

**Can I use these optimizers on SVGs that contain animations?**
Only with `cleanupIds` disabled. SMIL animations (`<animate>`, `<animateTransform>`) and CSS keyframes reference element ids, so id stripping breaks them. SVGO's `removeViewBox: false` plus `cleanupIds: false` is the safe baseline; svgcleaner's default `--remove-unused-defs=yes` can also delete animation targets.

**How much smaller will my SVGs get?**
Typical Figma or Illustrator exports shrink 35–60 % with SVGO defaults, 40–65 % with svgcleaner multipass, and 20–45 % with Scour. Hand-authored SVGs often shrink less than 10 %. Always benchmark your own corpus with the script above rather than trusting a single number.

**Which optimizer works offline without Node or Python?**
svgcleaner. It is a single static Rust binary with no runtime dependencies, which makes it the practical choice for air-gapped build machines and minimal container images.

**Is svgcleaner's GPL-2.0 license a problem?**
It is if you link against its code or redistribute a derivative. Calling the binary as a separate process from your build script is the usual interpretation-safe pattern; SVGO (MIT) and Scour (Apache-2.0) are friendlier for embedding.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SVGO vs svgcleaner vs Scour in 2026: Which SVG Optimizer Actually Shrinks Your Assets?",
  "description": "Hands-on comparison of SVGO, svgcleaner and Scour with real CLI flags, production configs, compression behavior and pitfalls that break icons.",
  "datePublished": "2026-10-26",
  "dateModified": "2026-10-26",
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
