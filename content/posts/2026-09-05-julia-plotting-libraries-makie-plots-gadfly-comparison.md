---
title: "Julia Plotting Libraries in 2026: Makie.jl vs Plots.jl vs Gadfly.jl — Which Should You Use?"
date: "2026-09-05"
tags: ["julia", "data-visualization", "plotting", "scientific-computing", "developer-tools"]
draft: false
cover: "/img/screenshots/julia-plotting-cover.jpg"
---

Every Julia user hits the same wall within a week: the language is glorious, the data pipelines fly, and then you need a chart — and suddenly you are staring at three plotting ecosystems that disagree about everything from how a figure is created to what a "backend" even means. **Makie.jl (2,806 stars), Plots.jl (1,949 stars), and Gadfly.jl (1,927 stars) are not three versions of the same tool.** They encode three different philosophies about what plotting should be: retained interactive scenes, a backend-agnostic recipe layer, and a strict grammar of graphics. Pick wrong and you will pay for it in rewrites — pick right and plotting becomes the boring, reliable part of your day.

This comparison uses code pulled from the official repositories and documentation, with live GitHub data captured in September 2026. If you publish figures for papers, build dashboards for browsers, or just want the least painful path from dataframe to PNG, read on.

## TL;DR — Which Julia Plotting Library Should You Pick?

**If you want publication-quality static figures with full layout control, or interactive 3D and browser-based visualization, use Makie** — it is the most active of the three (last push September 4, 2026) and its CairoMakie backend produces vector-perfect output for papers. **If you want the fastest route from data to a decent chart, with a huge recipe ecosystem, use Plots** — it is the most downloaded Julia plotting package and its `plot()` interface is the closest thing the ecosystem has to a lingua franca. **If you already think in ggplot2 layers and value the grammar of graphics, Gadfly is elegant — but its development has slowed to a crawl (last push October 2025), so treat it as a maintenance-risk choice for new projects in 2026.**

## Makie.jl vs Plots.jl vs Gadfly.jl: The 2026 Comparison

| Dimension | Makie.jl | Plots.jl | Gadfly.jl |
|---|---|---|---|
| GitHub stars | 2,806 | 1,949 | 1,927 |
| Last push | Sep 4, 2026 | Sep 4, 2026 | Oct 2025 |
| License | MIT | MIT | MIT |
| Core idea | Retained scene graph + GPU | Recipe pipeline over pluggable backends | Grammar of graphics |
| Canonical backend | CairoMakie / GLMakie / WGLMakie / RPRMakie | GR / Plotly / PGFPlotsX / UnicodePlots | Native SVG rendering |
| Outputs | PNG, SVG, PDF, HTML (WGLMakie) | PNG, SVG, PDF, HTML, EPS, LaTeX | SVG, PNG, PDF, PostScript |
| Interactivity | Native (desktop + browser) | Limited (Plotly backend) | Snap.svg pan/zoom (legacy) |
| 3D support | First-class, GPU-accelerated | Via Plotly/GR | None |
| Large data | Designed for millions of points | OK with GR; slow elsewhere | Struggles |
| Publishing focus | Yes — vector exports, layout system | Yes — via PGFPlotsX/LaTeX recipes | Yes — classic journal style |
| Learning curve | Steep (scenes, attributes, themes) | Gentle (attributes dictionary) | Moderate (aesthetics + geoms) |
| Maintenance velocity | Very high | High (v2 monorepo restructure) | Low — dormant since late 2025 |

**Decision matrix — 10-second pick**

| Use case | Recommendation | Why |
|---|---|---|
| Paper figures with precise layout | Makie (CairoMakie) | `Figure`/`Axis`/`Layout` model gives subplot grids and insets without hacks |
| Interactive 3D surface or volume exploration | Makie (GLMakie) | GPU rendering, orbiting camera, colormap brushing built in |
| Dashboard in the browser without JavaScript | Makie (WGLMakie) | Renders to WebGL in HTML; pairs with Genie/Pluto |
| Quick charts from arrays or DataFrames | Plots | `plot(df, x=:a, y=:b)` just works; recipes for StatsPlots add `@df` macros |
| ggplot2-style layered charts from a Python background | Gadfly | Familiar `Geom`/`Guide`/`Theme` vocabulary — if you accept slower development |
| Vector output for LaTeX papers | Plots (PGFPlotsX) or Makie | Both produce crisp TikZ/vector; Plots has deeper LaTeX recipe history |
| Teaching or notebooks | Plots | Shortest code, gentlest errors, works in IJulia and Pluto out of the box |

## Makie.jl — The High-Performance Scene-Graph Ecosystem

Makie (pronounced *mah-kee*) bills itself as "an interactive data visualization and plotting ecosystem," and the word *ecosystem* is doing real work: the core repo — now under the **MakieOrg** organization — ships four backends with different purposes. **CairoMakie** renders publication-quality 2D vector graphics to PNG, SVG, and PDF. **GLMakie** gives you GPU-accelerated interactive windows for 3D and large datasets on the desktop. **WGLMakie** renders the same scene in the browser via WebGL, which makes it the only Julia plotting option that can power a live web dashboard natively. **RPRMakie** adds physically accurate ray-traced rendering. The project was described in the *Journal of Open Source Software* (JOSS, 2021), which gives it unusual academic legitimacy — citing it in a paper is a one-liner.

A canonical CairoMakie figure from the official docs shows the retained model: you build a `Figure`, add an `Axis`, and plot into it with mutating functions:

```julia
using CairoMakie

fig = Figure(size = (600, 400))
ax = Axis(fig[1, 1], xlabel = "x", ylabel = "y",
          title = "Scatter + lines")
scatterlines!(ax, 1:10, rand(10))

save("scatter.png", fig)   # PNG for the web
save("scatter.pdf", fig)   # vector for the paper
```

Everything in the scene — axes, colorbars, legends, text — is an object you can mutate after creation, which is why Makie handles complex multi-panel layouts that make other libraries cry. The cost is conceptual: you think in *scenes*, *attributes*, and *themes* rather than function calls, and the first figure takes longer to write. The payoff is that **Makie scales from a two-line scatter to an interactive 3D volume renderer without switching tools**, which no other Julia plotting library can claim. At 2,806 stars with commits landing the day before this article was written, it is unambiguously the ecosystem's momentum pick.

## Plots.jl — The Recipe Layer and the v2 Monorepo

Plots.jl takes the opposite design bet: instead of owning a renderer, it defines a **recipe pipeline** and delegates drawing to interchangeable backends — GR (fast, default), Plotly (interactive HTML), PGFPlotsX (LaTeX), and more. Your code stays the same while the backend switches the output medium. Its GitHub description from the v2 branch calls the project a **monorepo** hosting the core package plus `RecipesBase`, `RecipesPipeline`, `PlotsBase`, and ecosystem packages like `GraphRecipes` and `StatsPlots` — a restructure that has been the project's main development thread through 2026 and explains why the default branch is literally named `v2`.

The flagship interface is deliberately boring — that is the point:

```julia
using Plots

x = 1:10
y = rand(10)
plot(x, y, title = "My Plot", xlabel = "x",
     label = "measurement", lw = 2, markershape = :circle)
```

That `plot()` call hides the real superpower: **recipes**. Any package can teach Plots how to visualize its own types, which is why the StatsPlots ecosystem adds `@df` dataframe macros, `corrplot`, marginals, and grouped boxplots with a few characters. For most working scientists Plots is the default choice not because it is the best at any one thing, but because it is *good enough at everything* and its error messages are the friendliest in the Julia plotting world. It also remains the most-downloaded plotting package in the Julia ecosystem by a wide margin. The v2 transition is the one thing to watch: the monorepo split means some old import paths and recipe internals are moving, so pin your environment if you depend on a large recipe stack in production.

## Gadfly.jl — The Grammar of Graphics, Frozen in Time

Gadfly is Julia's direct descendant of Leland Wilkinson's *Grammar of Graphics* and Hadley Wickham's ggplot2: you compose plots from **aesthetics** (mappings like `x`, `y`, `color`), **geoms** (point, line, bar...), **guides** (axes, legends), and **themes**. Its README quickstart is almost suspiciously simple:

```julia
Pkg.add("Gadfly")

using Gadfly
plot(y = [1, 2, 3])
```

and layered charts follow the grammar faithfully:

```julia
using Gadfly, DataFrames, RDatasets

df = dataset("datasets", "iris")
plot(df, x = :SepalLength, y = :SepalWidth, color = :Species,
     Geom.point, Geom.smooth(method = :loess))
```

The output is rendered natively to SVG, PNG, PostScript, and PDF, and the vector quality is genuinely beautiful — Gadfly charts have graced thousands of journal pages. The project's stated influences (Wilkinson, ggplot2) also make it the most *portable* mental model: knowledge transfers directly to ggplot2 and other grammar systems. The problem is momentum: **the last commit to GiovineItalia/Gadfly.jl was October 2025**, the issue tracker accumulates stale PRs, and the browser-interactivity features (Snap.svg pan/zoom) date from an earlier web era. At 1,927 stars Gadfly is not abandoned by community usage, but in 2026 it is best treated as a stable, complete tool for classic static charts — not a platform to build new interactive work on. If you want the ggplot2 paradigm with active development, Makie's `algebraofgraphics` companion and Plots recipes both cover parts of that ground with living maintainers.

## Pitfalls, Migrations, and Performance Traps

1. **First-call compilation latency hits all three, but differently.** Julia compiles on first use, so the *first* figure in a fresh session can take 5–30 seconds depending on backend. Makie (CairoMakie) is the heaviest; Plots with the GR backend is lightest; Gadfly sits in between. Use `PrecompileTools` workloads or a persistent session (Pluto, VS Code REPL) and the pain disappears.
2. **Backend leakage in Plots.** Code that works with GR may look different or fail under Plotly (e.g., `markershape`, some attribute names, NaN handling). If you switch backends, re-test your figure code — do not assume the recipe layer abstracts away every attribute.
3. **Makie's implicit-figure era is over.** Very old tutorials show top-level `scatter(x, y)` creating a figure implicitly; current Makie (0.20+) wants an explicit `Figure`/`Axis`. Old snippets error with hints — when you see "no current axis", modernize the snippet rather than hunting for a compat flag.
4. **Gadfly on new Julia versions.** Because Gadfly's cadence has slowed, newer Julia minor releases occasionally break parts of it (notably around dependency upgrades). If you must use Gadfly, pin both Julia and the package; test before a big language upgrade.
5. **Plots v2 migration is real.** The monorepo restructure is moving code between `Plots.jl` and `PlotsBase`; packages that reach into Plots internals (custom backends, advanced recipes) may need updates. Application code calling `plot()` is unaffected — the risk is at the library boundary.
6. **WGLMakie ≠ desktop GLMakie.** WebGL rendering in the browser drops some features and behaves differently with very large meshes. Prototype in CairoMakie for correctness, check interactivity in GLMakie, then export to WGLMakie for the web — each hop can reveal surprises.
7. **If your chart is going into a product, look at the serving layer too.** Browser-rendered Makie figures fit naturally into a Julia web app — our [Julia web frameworks comparison](../2026-09-04-julia-web-frameworks-genie-oxygen-httpjl-comparison/) covers the Genie/Oxygen/HTTP.jl side of that stack. For server-side chart APIs aimed at JavaScript consumers, the [React charting library comparison](../2026-08-20-react-charting-libraries-recharts-visx-react-chartjs-2-comparison/) is the better reference, and if you are really building a shared BI dashboard for a team, a self-hosted stack like [Redash vs Metabase vs Apache Superset](../2026-04-27-redash-vs-metabase-vs-apache-superset-self-hosted-bi-dashboard-guide-2026/) will beat any embedded notebook plots for non-technical users.

## What About Notebooks, DataFrames, and Big Data?

All three libraries work inside IJulia and Pluto, but with different ergonomics. Plots is the classic notebook citizen: short calls render inline automatically, and `StatsPlots` recipes make dataframe exploration nearly write-only. Gadfly also renders inline out of the box and remains popular in Pluto because its immutable, declarative plots play nicely with reactive cells. Makie in notebooks is excellent but opinionated: you must pick a backend for the environment — `CairoMakie` for static inline output, `WGLMakie` if you want interactive plots inside Pluto, and GLMakie only in a local desktop session. For genuinely huge datasets (millions of points), Makie's GPU pipeline is the only one of the three that keeps interaction fluid; Plots with GR degrades to acceptable static rendering; Gadfly will stall. For interactive exploratory work on tabular data, the [Jupyter/Polynote/Zeppelin notebooks comparison](../2026-05-18-apache-zeppelin-vs-polynote-vs-jupyterlab-self-hosted-notebooks-guide/) and the [reactive notebooks roundup (Marimo/LiveBook/JupyterLite)](../2026-06-09-self-hosted-reactive-notebooks-marimo-livebook-jupyterlite-guide/) are worth reading alongside this one, since your plotting choice often lives inside the notebook server you already self-host.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Julia Plotting Libraries in 2026: Makie.jl vs Plots.jl vs Gadfly.jl — Which Should You Use?",
  "description": "Deep comparison of Julia's three plotting ecosystems — Makie.jl, Plots.jl, and Gadfly.jl — with live GitHub stats, official code samples, feature and decision-matrix tables, migration pitfalls, and FAQs for 2026.",
  "datePublished": "2026-09-05",
  "dateModified": "2026-09-05",
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

**Is Makie or Plots faster for large datasets?**
Makie is the clear winner for interactive work with millions of points because it renders on the GPU through GLMakie/WGLMakie. For static publication figures, Plots with the GR backend is often faster to *produce* (less compile time, simpler pipeline), though Makie's vector export quality is higher for complex layouts.

**Which Julia plotting library is best for papers and journals?**
Makie with CairoMakie produces the most controllable vector output (PNG/SVG/PDF with a precise layout system), and it has a citable JOSS paper. Plots with the PGFPlotsX backend is the traditional route for LaTeX-native TikZ output. Both are used heavily in published research.

**Is Gadfly still maintained in 2026?**
Barely. The last push to GiovineItalia/Gadfly.jl was October 2025, so the project is dormant rather than dead: it still works for classic static charts, but new Julia versions may break it and fixes arrive slowly. New projects should prefer Makie or Plots unless they specifically want Gadfly's grammar-of-graphics API.

**Can I use Julia plotting libraries in the browser?**
Yes — WGLMakie renders Makie scenes to WebGL in HTML pages, which is the only first-class browser plotting path in Julia. Plots offers interactive HTML output through the Plotly backend, and Gadfly's SVG output embeds in pages but its interactivity is legacy.

**What is the Plots.jl v2 monorepo restructure?**
Plots.jl's default branch is now named `v2`, reorganizing the project as a monorepo that hosts the core package plus RecipesBase, RecipesPipeline, PlotsBase, StatsPlots, and GraphRecipes. It is a structural refactor: end-user `plot()` code stays stable, while package authors targeting Plots internals need to track the new layout.

**Do these libraries work with DataFrames.jl?**
Yes. Plots via StatsPlots recipes (`@df` macro, grouped plots, correlation matrices) is the most dataframe-native. Gadfly accepts DataFrames directly with column symbols (`plot(df, x=:a, y=:b, Geom.point)`). Makie works with DataFrames through `Makie.jl`'s data interface or by passing columns explicitly — slightly more verbose but fully supported.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
