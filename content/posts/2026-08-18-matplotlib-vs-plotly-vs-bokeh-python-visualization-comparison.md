---
title: "matplotlib vs Plotly vs Bokeh in 2026: Which Python Visualization Library Should You Use?"
date: "2026-08-18"
tags: ["python", "matplotlib", "plotly", "bokeh", "data-visualization", "data-science", "developer-tools"]
draft: false
cover: "/img/screenshots/matplotlib-cover.jpg"
---

Data visualization is where data science projects go to die or get funded, and the Python ecosystem's three heavyweights — matplotlib, Plotly, and Bokeh — look interchangeable until the moment your stakeholder asks for something specific: a publication-ready PDF figure, a zoomable dashboard with live streaming data, or a chart embedded in a web app. Pick the wrong one and you spend a week fighting the API to do what the other library does in three lines.

The 2026 reality: **matplotlib (23,083 stars) is the static, publication-grade standard. Plotly (18,743 stars) is the interactive charting library with the friendliest high-level API. Bokeh (20,430 stars) is the interactive library built for browser dashboards and live data.** They are not competitors in the way most lists imply — they are three different tools for three different jobs, and senior teams routinely use two of them in the same project.

## TL;DR: Quick Verdict

- **Use matplotlib** for scientific publications, static reports, and any figure that will end up in a PDF, paper, or slide deck — its typography, layout engine, and 60+ years of collective plotting wisdom remain unmatched.
- **Use Plotly** for interactive exploration in Jupyter, dashboards that need hover/tooltips/zooming out of the box, and web embedding — `plotly.express` turns a pandas DataFrame into a polished interactive chart in one line.
- **Use Bokeh** when you need server-backed interactivity: live-updating dashboards, streaming data, and plots that share state with a Python backend.
- **Skip** the religious wars. Start with Plotly for exploration, switch to matplotlib for final figures, reach for Bokeh when the dashboard needs to be alive.

## Feature Comparison: matplotlib vs Plotly vs Bokeh (2026)

| Feature | matplotlib | Plotly (plotly.py) | Bokeh |
|---|---|---|---|
| GitHub stars (2026-08-18) | **23,083** | 18,743 | 20,430 |
| Last commit | 2026-08-16 | 2026-08-07 | 2026-08-17 |
| License | BSD (PSF-based) | MIT | BSD-3-Clause |
| Default output | Static images (PNG/PDF/SVG) | Interactive HTML/JSON | Interactive HTML/JSON |
| High-level API | pyplot (stateful) | **plotly.express (DataFrame-native)** | bokeh.plotting figure |
| Interactivity | Limited (widgets via mpl) | **Hover, zoom, pan, tooltips built in** | Hover, zoom, pan + **server callbacks** |
| Server-backed state | No | Partial (Dash apps) | **Yes (Bokeh Server)** |
| Streaming / live data | Manual redraw | Via callbacks | **Native streaming support** |
| Jupyter experience | Good (inline) | **Excellent (renderers)** | Good (notebook + server) |
| Web app framework | None built-in | **Dash (companion)** | **Bokeh Server / Embed** |
| 3D plots | Yes (mplot3d) | **Yes (WebGL)** | Limited |
| Large datasets | Slow beyond ~1M points | WebGL renderers help | **CDS columnar model scales well** |
| Static export quality | **Best-in-class (PDF/SVG)** | Good (static via kaleido) | Good |
| Learning curve | Steep (two APIs) | Gentle (express) | Moderate |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Paper / thesis / journal figure | **matplotlib** | Vector PDF/SVG output, LaTeX-style math, exact axis control, publication typography |
| Exploratory analysis in Jupyter | **Plotly** | Hover tooltips, zooming, and subplot interactions with zero configuration |
| Internal monitoring dashboard with live data | **Bokeh** | Bokeh Server pushes updates to the browser; no web framework needed |
| Embedding charts in a company web app | **Plotly + Dash** | Dash gives you layout, callbacks, and auth around the same chart objects |
| Time-series with millions of points | **Bokeh** | Columnar data source + WebGL canvas handle density that freezes matplotlib |
| One-off static chart in a report | **matplotlib** | `plt.plot` + `plt.savefig` is still the fastest path to a clean PNG |
| Interactive scientific exploration (surface, volume) | **Plotly** | WebGL-powered 3D surfaces and scatter with tooltips outperform mplot3d |

## matplotlib — The Publication Standard

matplotlib is the foundation of scientific visualization in Python. It started as a MATLAB clone and grew into the tool that renders figures in tens of thousands of published papers. At **23,083 stars**, it does not have the largest community of the three (that honor goes to the broader scientific stack), but its ecosystem of extensions — seaborn for statistical styling, Cartopy for maps, mplfinance for financial charts, and the enormous gallery of official examples — makes it the safest default when correctness and output quality matter more than interactivity.

The official "Line plot" gallery example shows the modern object-oriented style, which is what you should use for anything beyond a scratch chart:

```python
"""
Line plot
=========

Create a basic line plot.
"""

import matplotlib.pyplot as plt
import numpy as np

# Data for plotting
t = np.arange(0.0, 2.0, 0.01)
s = 1 + np.sin(2 * np.pi * t)

fig, ax = plt.subplots()
ax.plot(t, s)

ax.set(xlabel='time (s)', ylabel='voltage (mV)',
       title='About as simple as it gets, folks')
ax.grid()

fig.savefig("test.png")
plt.show()
```

Two APIs coexist: the stateful `pyplot` interface (`plt.plot(...)`) for quick interactive work, and the object-oriented interface (`fig, ax = plt.subplots()` then `ax.plot(...)`) for real figures. Teams that skip learning the object-oriented API hit a wall the first time they need two subplots with shared axes, custom legends, or precise colorbars — the OO style is non-negotiable for production work.

Where matplotlib still dominates: **static output quality**. Vector PDF/SVG export, exact font control, LaTeX-style math rendering (`$x^2$` in labels), and pixel-perfect layout make it the only real choice for anything going to print. Its weaknesses are equally clear: interactivity is bolted on via widgets, and rendering a few million scatter points will grind any machine. For exploration-heavy work, most teams use matplotlib for the *final* figure after exploring with something interactive — the pattern we also cover in our [scientific data visualization comparison](../2026-06-09-self-hosted-scientific-data-visualization-paraview-visit-vtkjs-pyvista/).

## Plotly — The Interactive-First Charting Library

Plotly's thesis is that every chart should be interactive by default. plotly.py, at **18,743 stars**, wraps plotly.js and gives Python users a declarative API where the same chart object can render in Jupyter, be saved as a standalone HTML file, or be embedded in a Dash web app. The README's entire quickstart is three lines:

```python
import plotly.express as px
fig = px.bar(x=["a", "b", "c"], y=[1, 3, 2])
fig.show()
```

That is `plotly.express` — a high-level API that takes pandas DataFrames directly. The one-liner pattern scales to real analysis:

```python
import plotly.express as px
df = px.data.gapminder()  # built-in dataset
fig = px.scatter(df, x="gdpPercap", y="lifeExp", color="continent",
                 size="pop", log_x=True, animation_frame="year")
fig.show()
```

Every chart gets hover tooltips, zoom/pan, legend toggling, and export-to-PNG controls for free. The chart is a JSON-serializable object (`fig.to_json()`), which is why Plotly integrates so cleanly with web stacks: the frontend renders the same spec, no Python process needed after generation.

The companion framework is **Dash**, which turns the same figure objects into full web applications with callbacks, layouts, and authentication. That is the standard pattern for internal analytics tools: a Dash app that queries your data warehouse, renders Plotly charts, and serves the whole thing on one port. For self-hosted analytics platforms that already solve this at a larger scale, our [BI dashboard comparison](../2026-04-27-redash-vs-metabase-vs-apache-superset-self-hosted-bi-dashboard-guide-2026/) is worth reading before you build.

Plotly's weaknesses: static export requires the extra `kaleido` package, very large datasets need the WebGL-based renderers (scattergl, heatmapgl), and the express API's convenience can hide the underlying graph_objects API — which you will eventually need for anything non-standard.

## Bokeh — The Server-Backed Dashboard Engine

Bokeh's differentiator is that interactivity is not just client-side eye candy: the Python backend and the browser share state through a **Columnar Data Source (CDS)**, and the Bokeh Server can push updates to connected browsers in real time. It is a NumFOCUS-sponsored project with **20,430 stars**, actively maintained (last commit 2026-08-17), and it is the tool of choice for operational dashboards where data changes while users watch.

The official first-steps example shows the standalone (client-side) pattern:

```python
from bokeh.plotting import figure, show

# prepare some data
x = [1, 2, 3, 4, 5]
y = [6, 7, 2, 4, 5]

# create a new plot with a title and axis labels
p = figure(title="Simple line example", x_axis_label="x", y_axis_label="y")

# add a line renderer with legend and line thickness
p.line(x, y, legend_label="Temp.", line_width=2)

# show the results
show(p)
```

What the example does not show is the server mode: `bokeh serve app.py` runs a plot whose data source can be updated from Python — a sensor stream, a log tail, a metrics poller — and every connected browser updates automatically. The CDS model also handles large data more gracefully than matplotlib: millions of points render through WebGL canvases, and you can downsample client-side with decimation.

Bokeh's trade-offs: the API surface is larger (figure, glyphs, models, widgets, server concepts), and building a multi-page dashboard with authentication and layout takes real effort — that is where Plotly+Dash or a full BI platform often wins. But for the specific job of "live, browser-based, Python-backed visualization," Bokeh is still the most direct tool. If your data is already in time-series stores, our [terminal data visualization guide](../2026-06-17-terminal-data-visualization/) covers the complementary skill of inspecting that same data from the shell.

## Pitfalls and Gotchas

1. **The static/interactive trap.** Teams pick one library for everything. matplotlib for a dashboard is painful; Plotly for a journal figure fights you on fonts and vector export. Decide per deliverable: interactive exploration → Plotly, final figures → matplotlib, live dashboards → Bokeh.
2. **matplotlib's two APIs cause real bugs.** Mixing `plt` stateful calls with OO `ax` calls in the same script produces mysterious "figure already exists" behavior, double-plotting, and misapplied styles. Pick the OO style for anything longer than ten lines, and put `plt.style.use(...)` at the top, once.
3. **Interactive libraries need a rendering pipeline.** Plotly figures in Jupyter need the `plotly` renderer configured; Bokeh needs `bokeh.io.output_notebook()`. In headless CI, `fig.show()` blocks or produces nothing — use `fig.write_html()` / `fig.write_image()` for automated report generation.
4. **Static export of Plotly requires kaleido.** `fig.write_image()` fails silently without it. Add `kaleido` to your environment explicitly, or pin a specific version — kaleido major versions have broken API compatibility.
5. **Large data strategy differs wildly.** matplotlib with 5M scatter points is a slideshow; switch to `scattergl` in Plotly or Bokeh's WebGL canvas. For time series, downsample before plotting (or use Bokeh's decimation) — nobody sees 5M pixels anyway.
6. **Timezone and datetime axes.** All three libraries mishandle naive vs aware datetimes differently. Normalize every datetime column to UTC (or a fixed timezone) *before* plotting, or your axis labels and tooltips will disagree with the data.
7. **License and vendor lock-in review.** All three are permissively licensed (BSD/MIT), but Plotly's commercial offerings (Chart Studio, Dash Enterprise) are not — if you evaluate Dash Enterprise, know what is open source (Dash, plotly.py) and what is not. Self-hosted BI platforms like Apache Superset are the open alternative when you outgrow library-level dashboards; our [BI dashboard comparison](../2026-04-27-redash-vs-metabase-vs-apache-superset-self-hosted-bi-dashboard-guide-2026/) breaks down the options.
8. **Web bundle size.** Embedding Plotly or Bokeh in a web page pulls a multi-hundred-KB JS runtime. If you only need a few charts, consider server-side rendering to static SVG/PNG (matplotlib or plotly + kaleido) and reserve the JS runtime for genuinely interactive views.

## FAQ

**Which Python visualization library is best for beginners?**
Plotly's `plotly.express` is the gentlest entry point — one line turns a DataFrame into an interactive chart with tooltips and zooming. matplotlib is also fine to start with but has two APIs to learn. Bokeh is the least beginner-friendly of the three because the server concepts add cognitive load.

**Can I use matplotlib and Plotly together?**
Yes, and many teams do. A common workflow: explore interactively with Plotly, then rebuild the final figure in matplotlib for publication quality. They coexist in one environment; the only friction is keeping both import styles clean and avoiding state bleed (matplotlib's global style, Plotly's renderer config).

**Is Bokeh still maintained in 2026?**
Yes. Bokeh's last commit was 2026-08-17 and it is an active NumFOCUS-sponsored project with 20,430 stars. Its niche — server-backed live dashboards — remains underserved by the other two libraries, which is why it persists despite Plotly's broader marketing footprint.

**Does Plotly work offline?**
Yes. plotly.py renders locally in Jupyter and can export self-contained HTML files that need no internet. Only Chart Studio (the hosted service) requires connectivity. For fully offline web serving, the exported HTML works from any static host — including the same GitHub Pages-style setup we use for this site.

**Which library handles huge datasets best?**
Bokeh's columnar data source with WebGL rendering is the strongest for interactive large-data work, and Plotly's `scattergl`/WebGL trace types are close behind. matplotlib degrades first because it renders everything server-side through its 2D drawing engine. For truly massive data, consider server-side downsampling before rendering.

**Do these libraries support 3D plots?**
Plotly has the best out-of-the-box 3D (surface, scatter3d, mesh via WebGL). matplotlib has mplot3d, which is fine for simple surface plots but slow and limited. Bokeh's 3D support is minimal — it is not the right tool for volume or mesh visualization.

**Which one should I use for a web dashboard without writing frontend code?**
Bokeh Server if the dashboard is primarily live data views with minimal layout requirements; Plotly + Dash if you need pages, forms, authentication, and a more app-like experience. Both are pure Python — no JavaScript required — though Dash is the closer analog to a web framework.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "matplotlib vs Plotly vs Bokeh in 2026: Which Python Visualization Library Should You Use?",
  "description": "Compare matplotlib, Plotly, and Bokeh in 2026 — the three dominant Python data visualization libraries. Interactive vs static, GitHub stats, code examples, and use-case recommendations.",
  "datePublished": "2026-08-18",
  "dateModified": "2026-08-18",
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
