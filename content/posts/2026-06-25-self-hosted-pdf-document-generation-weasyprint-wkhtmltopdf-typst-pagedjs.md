---
title: "Self-Hosted PDF Document Generation: WeasyPrint vs wkhtmltopdf vs Typst vs Paged.js (2026)"
date: "2026-06-25"
tags: ["pdf", "document-generation", "self-hosted", "typesetting", "html-to-pdf", "developer-tools", "reporting"]
draft: false
---

## Introduction

Every business application eventually needs to produce a PDF — invoices, contracts, reports, certificates, compliance documents, eBooks, and receipts. The conventional approach is to pay a cloud API service per document, but for organizations generating thousands of PDFs monthly, the costs add up quickly while sensitive document data crosses third-party servers. Self-hosting your PDF generation stack eliminates per-document costs, keeps data on-premises, and gives you full control over rendering quality.

Four open-source tools dominate the self-hosted PDF generation landscape: **WeasyPrint** (9,320 stars), **wkhtmltopdf** (14,557 stars), **Typst** (54,554 stars), and **Paged.js** (1,403 stars). Each takes a fundamentally different approach — HTML/CSS rendering engines, modern typesetting systems, and browser-based pagination polyfills. This comparison examines their architectures, output quality, self-hosting deployment, and fitness for common document generation workflows.

## Quick Comparison Table

| Feature | WeasyPrint | wkhtmltopdf | Typst | Paged.js |
|---------|-----------|-------------|-------|----------|
| Stars | 9,320 | 14,557 | 54,554 | 1,403 |
| Language | Python | C++ | Rust | JavaScript |
| Input Format | HTML + CSS | HTML + CSS | Typst markup | HTML + CSS |
| Rendering Engine | Custom (Cairo) | QtWebKit | Custom (tiny-skia) | Browser layout engine |
| CSS Paged Media | Full (Level 3) | Partial | N/A | Full (via polyfill) |
| Typographic Quality | Excellent | Good | Professional | Excellent (browser-dependent) |
| SVG Support | Yes (CairoSVG) | Limited | Yes (resvg) | Yes (native) |
| JavaScript in Document | No | Limited | N/A | Yes (full) |
| Deployment Model | Python library + CLI | Binary + CLI | Binary + CLI | Node.js + Puppeteer/Playwright |
| Docker Available | Yes | Yes | Yes | Yes |
| Last Updated | Jun 2026 | Nov 2022 | Jun 2026 | Apr 2026 |

## Architecture Deep Dive

### WeasyPrint: CSS Paged Media Done Right

WeasyPrint is a Python library that renders HTML and CSS directly to PDF using Cairo, Pango, and its own CSS layout engine — no headless browser required. It implements the full CSS Paged Media Module Level 3 specification, giving you precise control over page size, margins, headers, footers, page breaks, and footnotes through standard CSS. This is a fundamentally different approach from browser-based PDF tools: WeasyPrint understands document semantics natively rather than converting a web page screenshot into a PDF.

```python
from weasyprint import HTML

# Generate PDF with full CSS paged media support
HTML('invoice.html').write_pdf('invoice.pdf',
    presentational_hints=True,
    optimize_size=('fonts', 'images'))

# With external stylesheet and custom page size
HTML('report.html').write_pdf('report.pdf',
    stylesheets=['report.css'],
    optimize_size=('fonts',))
```

Docker deployment is straightforward:

```yaml
# docker-compose.yml for WeasyPrint as a microservice
version: '3.8'
services:
  weasyprint:
    image: ghcr.io/kozea/weasyprint:latest
    ports:
      - "5001:80"
    volumes:
      - ./templates:/app/templates
      - ./output:/app/output
    environment:
      - WKHTMLTOPDF_DEBUG=1
```

WeasyPrint's standout feature is its CSS support quality. Unlike wkhtmltopdf which uses the aging QtWebKit engine, WeasyPrint implements modern CSS features including CSS custom properties (variables), flexbox, grid layout, and the full `@page` rule set. This means your PDF templates can use the same CSS you use for web pages — reducing the design-to-PDF iteration cycle dramatically.

### wkhtmltopdf: The Veteran Workhorse

wkhtmltopdf converts HTML to PDF using the QtWebKit rendering engine. It has been the go-to HTML-to-PDF tool for over a decade, powering countless invoice generators, report systems, and document pipelines. Its command-line interface is legendary for its simplicity:

```bash
# Basic HTML to PDF conversion
wkhtmltopdf input.html output.pdf

# With custom page size, margins, and header/footer
wkhtmltopdf \
  --page-size A4 \
  --margin-top 20mm \
  --margin-bottom 20mm \
  --header-html header.html \
  --footer-center "Page [page] of [topage]" \
  input.html output.pdf

# Docker-based self-hosted usage
docker run --rm -v $(pwd):/data \
  ghcr.io/surnet/alpine-wkhtmltopdf:latest \
  /data/input.html /data/output.pdf
```

The Docker compose setup uses Surnet's maintained Alpine image:

```yaml
version: '3.8'
services:
  wkhtmltopdf:
    image: ghcr.io/surnet/alpine-wkhtmltopdf:latest
    volumes:
      - ./documents:/data
    command: tail -f /dev/null
```

wkhtmltopdf's main limitation is its rendering engine: QtWebKit is essentially frozen at a 2016-era WebKit fork. Modern CSS features (grid, custom properties, flexbox gap) are not supported, and JavaScript execution is limited. However, for straightforward HTML documents with tables, images, and basic CSS, wkhtmltopdf remains the fastest option — its binary completes most conversions in under 100ms, making it ideal for high-throughput document pipelines.

### Typst: The Modern Typesetting Revolution

Typst is a markup-based typesetting system that aims to replace LaTeX for scientific and technical document production. It compiles `.typ` files directly to PDF using a custom Rust rendering engine, producing output that matches or exceeds LaTeX's typographic quality at compilation speeds 10-50x faster. Typst's 54,554 GitHub stars reflect its meteoric adoption since its 2023 public release.

```typst
// invoice.typ — professional invoice template
#set page(margin: (top: 20mm, bottom: 20mm))
#set text(font: "Inter", size: 11pt)

#align(center)[
  = INVOICE
  #v(5mm)
  #table(
    columns: (1fr, 1fr),
    [*Invoice Number:* INV-2026-0642],
    [*Date:* June 25, 2026],
  )
]

#v(10mm)
#table(
  columns: (3fr, 1fr, 1fr, 1.5fr),
  table.header[*Description*, *Qty*, *Unit Price*, *Total*],
  [Web Development Services], [40], [$150.00], [$6,000.00],
  [Server Configuration], [8], [$200.00], [$1,600.00],
  table.footer[*Total*, [], [], [*$7,600.00*]],
)

#v(20mm)
#align(right)[
  Thank you for your business!
]
```

Docker deployment:

```yaml
version: '3.8'
services:
  typst:
    image: ghcr.io/typst/typst:latest
    volumes:
      - ./documents:/data
    working_dir: /data
    command: watch /data
```

Typst's typesetting engine supports mathematical equations (comparable to LaTeX's math mode), automatic figure numbering and cross-referencing, bibliography management, and conditional content — all expressed in a clean, readable markup syntax. For organizations producing technical documentation, academic papers, or formatted reports, Typst offers professional output quality that HTML-to-PDF tools cannot match.

### Paged.js: Browser-Based Pagination for the Web Era

Paged.js takes the opposite approach from dedicated PDF engines: it is a JavaScript polyfill that implements the CSS Paged Media specification inside any modern browser. Instead of using a custom layout engine, Paged.js transforms a continuous web page into paginated content directly in the browser's rendering pipeline. This means you get native browser CSS support (including flexbox, grid, and all modern CSS features) with proper page breaks, running headers, and page counters.

```html
<!-- Template with CSS paged media -->
<style>
  @page {
    size: A4;
    margin: 25mm 20mm;
    @bottom-center {
      content: "Page " counter(page) " of " counter(pages);
    }
  }
  h1 { break-before: page; }
  .chapter { break-after: page; }
</style>

<script src="paged.polyfill.js"></script>
<div class="chapter">
  <h1>Annual Report 2026</h1>
  <p>Content flows across pages automatically...</p>
</div>
```

Docker deployment with Puppeteer for headless PDF output:

```yaml
version: '3.8'
services:
  pagedjs:
    image: node:22-alpine
    working_dir: /app
    volumes:
      - ./templates:/app/templates
      - ./output:/app/output
    command: >
      sh -c "npm install pagedjs-cli puppeteer &&
             npx pagedjs-cli /app/templates/report.html -o /app/output/report.pdf"
```

Paged.js's key advantage is browser fidelity: since documents render in a real browser engine, you can use any CSS framework, web font, or layout technique that browsers support. Complex responsive designs, custom fonts, SVG animations, and even interactive JavaScript all work within paginated documents. The trade-off is deployment complexity — you need a headless browser (Puppeteer or Playwright) in your stack.

## Why Self-Host Your PDF Generation Pipeline

Running your own PDF generation stack means zero per-document API fees, complete data privacy (invoices and contracts never leave your servers), and the ability to customize every aspect of the rendering pipeline. A single Docker host with 2 vCPUs can generate thousands of PDFs per hour across all four tools — a workload that would cost hundreds of dollars monthly via cloud API services.

The self-hosting model also gives you control over versioning: your PDF output remains consistent across deployments because you pin exact tool versions, unlike cloud APIs that may change their rendering engines without notice. For regulated industries where document output must be auditable and reproducible, this determinism is essential.

For organizations that need browser-based PDF and screenshot generation APIs, see our comparison of [Gotenberg, Playwright, and Puppeteer for headless rendering](../self-hosted-screenshot-pdf-generation-apis-gotenberg-playwright-puppeteer-guide-2026/). If you need PDF manipulation (merging, splitting, form filling) rather than document generation, our [Stirling PDF self-hosted toolkit guide](../stirling-pdf-self-hosted-pdf-toolkit-guide/) covers the full-featured PDF Swiss Army knife available for local deployment.

## Choosing the Right Tool for Your Document Type

- **Invoices and business documents**: WeasyPrint excels here. Its CSS Paged Media support produces pixel-perfect corporate documents with repeating headers/footers, and its Python API integrates naturally with Django, Flask, and FastAPI backends.

- **High-throughput HTML-to-PDF conversion**: wkhtmltopdf remains the speed king for simple HTML documents. Its sub-100ms per-document conversion time makes it ideal for bulk operations like generating PDF snapshots of archived web pages or converting thousands of markdown documents to PDF.

- **Academic papers, theses, and technical reports**: Typst provides professional typesetting quality that HTML-to-PDF tools cannot approach. Its equation support, automatic bibliography management, and cross-referencing system match LaTeX while being far more approachable for new users.

- **Interactive web dashboards exported as PDF**: Paged.js is the only option that preserves interactive JavaScript behavior during pagination. For applications that need to export complex single-page apps with charts, maps, and data visualizations to PDF, Paged.js running in a headless browser captures the full fidelity of modern web rendering.

## FAQ

### Can I use WeasyPrint for server-side HTML-to-PDF in a Python web app?

Yes, WeasyPrint integrates seamlessly with Python web frameworks. Call `HTML(string=html_content).write_pdf()` directly in your Django view or Flask route handler. For production, run WeasyPrint as a separate microservice (via the Docker image) to avoid blocking your web server during large PDF renderings.

### Is wkhtmltopdf still maintained?

The original wkhtmltopdf project is in maintenance mode — its last release was in 2016 (0.12.6) and the QtWebKit engine it depends on is no longer actively developed. However, community forks and Docker images (particularly `surnet/alpine-wkhtmltopdf`) keep the tool functional on modern systems. For new projects, WeasyPrint or Typst are generally better long-term investments.

### How does Typst compare to LaTeX?

Typst compiles 10-50x faster than LaTeX, uses a cleaner markup syntax, and produces equivalent or better typographic output. It lacks LaTeX's 40-year ecosystem of packages, but covers the 80% of use cases that most users need: academic papers, technical reports, presentations, and formatted documents. For new projects starting in 2026, Typst is the recommended alternative to LaTeX unless you depend on specific LaTeX packages with no Typst equivalent.

### Do I need a headless browser to use Paged.js?

Yes, Paged.js requires a browser engine to run — it operates by injecting pagination logic into a running browser's layout pipeline. The standard setup pairs Paged.js with Puppeteer (Chromium) or Playwright, which adds approximately 300 MB to your Docker image. If you cannot tolerate this dependency, use WeasyPrint for CSS-driven PDF generation without a browser.

### What's the output file size difference between these tools?

WeasyPrint and wkhtmltopdf produce similar file sizes for equivalent documents (100-500 KB for a typical 10-page report). Typst outputs are typically smaller (50-200 KB) because its custom engine outputs optimized PDF streams. Paged.js through headless browsers produces the largest files (200 KB - 2 MB) due to embedded fonts and the browser engine's less aggressive PDF optimization. For production pipelines, post-process all outputs with `gs -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress` to standardize file sizes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PDF Document Generation: WeasyPrint vs wkhtmltopdf vs Typst vs Paged.js (2026)",
  "description": "Complete comparison of four self-hosted PDF document generation tools — WeasyPrint, wkhtmltopdf, Typst, and Paged.js. Docker deployment guides, code examples, output quality comparison, and tool selection guidance for invoices, reports, and technical documents.",
  "datePublished": "2026-06-25",
  "dateModified": "2026-06-25",
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
