---
title: "TeX Live vs MiKTeX vs Tectonic in 2026: Which LaTeX Distribution Should You Actually Use?"
date: "2026-10-09"
tags: ["latex", "typesetting", "developer-tools", "self-hosted", "documentation"]
draft: false
cover: "/img/screenshots/tectonic-logo.jpg"
---

Installing LaTeX is where a shocking number of otherwise well-run projects die. You start with a simple goal — turn a `.tex` file into a PDF — and end up choosing between a 7 GB download, a Windows-first installer that behaves strangely on Linux, and a Rust binary that quietly fetches packages from a CDN. Pick wrong and you lose hours every week: CI pipelines that rebuild the same image for ten minutes, containers that are 6 GB before they compile a single chapter, and "works on my machine" build scripts that nobody dares touch.

The good news is that in 2026 there are only **three distributions that matter** for serious work: **TeX Live**, **MiKTeX**, and **Tectonic**. They are not interchangeable, and the right choice depends almost entirely on where your documents are built — a laptop, a Windows desktop, or a container in a CI runner.

## TL;DR — The Quick Verdict

- **Choose TeX Live** if you want the reference implementation with the complete package universe, and you are willing to pay for it with disk space. It is the default on Linux, the base of every serious Docker image, and the distribution most academic templates assume.
- **Choose MiKTeX** if you work on Windows, or you want a small initial install that pulls packages **on demand** the first time a document needs them.
- **Choose Tectonic** if you build in containers or CI and want a **single static binary**, a lockfile for reproducible builds, and no 7 GB cache to keep warm.

If you only remember one line: **TeX Live for completeness, MiKTeX for Windows and small installs, Tectonic for CI and reproducibility.**

## Quick Comparison: TeX Live vs MiKTeX vs Tectonic

| Dimension | TeX Live | MiKTeX | Tectonic |
|---|---|---|---|
| **Best for** | Reference distribution, full TeX universe | Windows desktops, on-demand installs | CI/CD, containers, reproducible builds |
| **Install footprint** | 100 MB (basic) to ~7 GB (full scheme) | ~200–400 MB base, grows on demand | Single binary (~30 MB) + package cache |
| **Package model** | `tlmgr`, explicit install/update | Auto-install missing packages at compile time | Fetches from a bundle on demand, then caches |
| **Engine core** | pdfTeX, XeTeX, LuaTeX | pdfTeX, XeTeX, LuaTeX | XeTeX-derived (modernized) |
| **Reproducible builds** | Manual (pin `tlmgr` snapshots) | No lockfile concept | Yes — lockfile + pinned bundle |
| **Shell escape** | Opt-in (`-shell-escape`) | Opt-in | Disabled by design |
| **Official Docker image** | `texlive/texlive` (weekly updates) | `miktex/miktex` | Not official — use release binaries |
| **License** | Free software (multiple) | Free software | Open source (MIT) |
| **GitHub stars / last push** | 367★ (mirror), 2026‑10‑08 | 983★, 2026‑08‑02 | 5,156★, 2026‑08‑01 |
| **Latest release** | Rolling (annual snapshot) | Rolling | 0.17.0 |

The star counts tell an interesting story: Tectonic has **5× the GitHub attention** of MiKTeX despite being the youngest of the three, because it solves a problem (deterministic container builds) that the older distributions were never designed for.

## Decision Matrix — Pick in Ten Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| Linux workstation, academic paper, unknown template | **TeX Live** | Templates assume the full `texlive-full` package set |
| Windows desktop, occasional documents | **MiKTeX** | On-demand installs keep the disk small; native GUI console |
| GitHub Actions / GitLab CI building a PDF on every push | **Tectonic** | One binary, no multi-gigabyte cache, lockfile reproducibility |
| Multi-language documents (CJK, Arabic, Devanagari) | **TeX Live** or **MiKTeX** (XeTeX/LuaTeX) | Mature fontspec + polyglossia support and font handling |
| Publishing pipeline where you must rebuild a 2023 document byte-identically | **Tectonic** | `Tectonic.lock` pins the exact bundle version |
| You want the smallest possible container image | **Tectonic** | Static binary beats any TeX Live scheme |
| You need obscure packages from CTAN | **TeX Live** | The only distribution that ships the entire universe |

## TeX Live — The Reference Distribution

TeX Live is what people mean when they say "LaTeX" without qualification. It is maintained by the TeX Users Group, ships the overwhelming majority of CTAN, and is the distribution every Linux package manager falls back to. The annual snapshot model means you get a frozen, tested package set each year, with rolling updates through `tlmgr` between releases.

The source mirror on GitHub (`TeX-Live/texlive-source`) shows a project that is very much alive — **last push 2026‑10‑08** — even though the canonical development happens over Subversion on `tug.org`.

Install it on Linux or macOS with the official network installer:

```bash
# Download the installer
wget https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz
tar -xzf install-tl-unx.tar.gz
cd install-tl-*/

# Choose a scheme interactively, or use a scheme file
./install-tl --scheme=scheme-full

# Afterwards, manage packages with tlmgr
tlmgr update --self
tlmgr install booktabs geometry hyperref
```

For containers, the **official `texlive/texlive` image is updated weekly**, which is a meaningful advantage over hand-rolled images that drift out of date:

```bash
docker run --rm -v "$PWD":/work -w /work texlive/texlive:latest \
  pdflatex -interaction=nonstopmode main.tex
```

The trade-off is size. A `scheme-full` installation lands around **7 GB**, and even the `texlive/texlive` image is heavy. If your CI bills by the minute and your cache is cold, that cost is real.

![The LaTeX Project logo](/img/screenshots/latex-project-logo.jpg "The LaTeX Project — the document preparation system that TeX Live, MiKTeX and Tectonic all compile")

## MiKTeX — Small Installs and On-Demand Packages

MiKTeX's defining feature is **automatic package installation**. When a document requests a package you do not have, MiKTeX pauses and fetches it rather than failing with `File 'foo.sty' not found`. On a Windows desktop this is genuinely pleasant: install once, never think about packages again.

The GitHub repository (`MiKTeX/miktex`, **983★**, last push 2026‑08‑02) is the source of truth for the engine, while installers live on the project's own site. The Docker image is the practical way to use it in a server context:

```bash
docker run --rm -v "$PWD":/miktex/work -w /miktex/work miktex/miktex:latest \
  pdflatex -interaction=nonstopmode main.tex
```

There is a real operational caveat, and it is the reason many teams abandon MiKTeX for CI: **on-demand installs make builds non-deterministic and slow the first time.** A container that finds every package already present is fast; one that must download twenty packages mid-build is not, and if the package server is unreachable the build simply fails. MiKTeX also has a desktop-oriented configuration model (the MiKTeX Console) that maps awkwardly onto ephemeral containers.

Use MiKTeX when a human is in the loop and disk space matters. Do not use it as the base of a production PDF pipeline unless you pre-install every package you need.

## Tectonic — One Binary, Lockfile, Zero Drama

Tectonic is the distribution that took CI seriously. It is a **single, self-contained binary** — install it and you are done:

```bash
# From crates.io (requires a Rust toolchain)
cargo install tectonic

# Or grab a static release binary (Linux/macOS/Windows)
# https://github.com/tectonic-typesetting/tectonic/releases/latest
```

When it compiles a document, Tectonic reads a **bundle manifest** that specifies which TeX Live packages to use, fetches exactly those files, and caches them locally. The build writes a `Tectonic.lock` file recording the precise bundle revision, which means a document built today can be rebuilt byte-identically years from now. That property is why reproducible-research projects and documentation pipelines gravitate to it.

A representative CI step looks like this:

```yaml
- name: Build PDF
  uses: actions/checkout@v4
- run: |
    curl -fsSL https://github.com/tectonic-typesetting/tectonic/releases/latest/download/tectonic-0.17.0-x86_64-unknown-linux-musl.tar.gz \
      | tar -xz -C /usr/local/bin tectonic
    tectonic --keep-logs main.tex
```

Tectonic also disables shell escape by default, which removes an entire class of "my build ran arbitrary code from a template" incidents. The cost is compatibility: it is XeTeX-derived, so pdfTeX-only packages and heavy LuaTeX scripting are out of reach, and the on-demand bundle fetch needs network access (or a pre-warmed cache) on the first build.

## Common Pitfalls When You Switch Distributions

- **Missing packages after a move to Tectonic.** Tectonic only fetches what its bundle contains. If a document depends on an obscure CTAN package, it will fail — test early, not on release day.
- **Assuming TeX Live's full scheme is available everywhere.** Debian's `texlive-full` is not identical to the upstream `scheme-full`, and package names differ. Pin your distribution in CI to avoid "it compiles locally" surprises.
- **Letting MiKTeX auto-install in production.** Set the package repository explicitly and pre-install, or accept random first-build latency.
- **Forgetting the cache.** Tectonic without a persistent bundle cache re-downloads on every cold container, which can be slower than a warm TeX Live image. Cache `~/.cache/Tectonic`.
- **Version drift between authors.** If two people build the same paper with different TeX Live snapshots, output can differ subtly. Commit a lockfile (Tectonic) or pin a `tlmgr` revision.

For a broader look at turning source files into deliverable PDFs, our [self-hosted PDF generation guide](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-pagedjs/) covers the HTML-to-PDF half of the problem, and the [collaborative LaTeX editors comparison](../2026-06-11-collaborative-latex-editors-overleaf-swiftlatex-fiduswriter/) covers what to do when several authors edit the same document. If your documents are generated from templates rather than written by hand, the [document automation tools guide](../2026-05-03-docassemble-vs-docxtemplater-vs-pandoc-self-hosted-document-automation-guide/) is the natural next read.

## FAQ

### Is TeX Live still the best LaTeX distribution in 2026?

For completeness, yes. TeX Live ships essentially all of CTAN, it is the default on Linux, and academic templates are written against it. It is not the best choice for container-based builds, where Tectonic's single binary and lockfile win on speed and reproducibility.

### Can Tectonic compile any LaTeX document?

Almost, but not all. Tectonic is XeTeX-derived, so XeTeX-compatible documents work well. Documents that rely on pdfTeX-specific primitives, heavy LuaTeX scripting, or packages outside the Tectonic bundle may fail. Test your most complex document before migrating a pipeline.

### Does MiKTeX work on Linux and in Docker?

Yes. MiKTeX builds for Linux and there is an official `miktex/miktex` Docker image. The catch is that its on-demand package installation was designed for interactive desktops; in ephemeral containers, pre-install your packages to keep builds fast and deterministic.

### How large is a full TeX Live installation?

A full `scheme-full` TeX Live installation is roughly 7 GB, and the `texlive/texlive` image is comparable. A basic scheme is closer to 100–200 MB. Tectonic avoids the question entirely by fetching only the files a document actually needs.

### Which distribution should I use in GitHub Actions?

Tectonic in most cases: one binary to download, a bundle cache you can persist, and a lockfile that makes rebuilds reproducible. Use the `texlive/texlive` image if your project depends on the full package set and you are comfortable caching a multi-gigabyte layer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TeX Live vs MiKTeX vs Tectonic in 2026: Which LaTeX Distribution Should You Actually Use?",
  "description": "A practical 2026 comparison of TeX Live, MiKTeX and Tectonic: install footprint, package models, Docker images, reproducibility and CI suitability.",
  "datePublished": "2026-10-09",
  "dateModified": "2026-10-09",
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
