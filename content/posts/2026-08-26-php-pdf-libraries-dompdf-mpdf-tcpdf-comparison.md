---
title: "PHP PDF Generation in 2026: Dompdf vs mPDF vs TCPDF — Which One Should You Actually Use?"
date: "2026-08-26"
tags: ["php", "pdf", "pdf-generation", "library-comparison", "php-libraries"]
draft: false
cover: "/img/screenshots/dompdf-cover.png"
---

If your PHP application has ever needed to turn HTML into a PDF, you have stared at the same three names: **Dompdf**, **mPDF**, and **TCPDF**. For a decade the default answer was "just use TCPDF" — but in 2026 that answer is actively wrong: TCPDF's maintainer has officially deprecated it, mPDF's GPL license is a legal trap for commercial products, and Dompdf quietly became the safest default. This article gives you the current state of all three — real stars, real licenses, real code — plus the migration checklist TCPDF users now need.

## TL;DR — Quick Verdict

**Use Dompdf for new projects.** It is the most popular (11,177 stars), under LGPL-2.1 (compatible with proprietary software), actively maintained, and its CSS 2.1 engine covers the invoice/report use case better than anything else in pure PHP. **Use mPDF only when you need serious typography** — RTL text, CJK support, advanced CSS — and you either accept GPL-2.0 or buy a commercial license. **Do not start new projects with TCPDF.** It is officially deprecated and in maintenance-only mode; feature development moved to `tc-lib-pdf`, and the font system changed under everyone's feet.

## At a Glance — The Comparison Table

All stats fetched live from GitHub on 2026-08-26.

| Criterion | Dompdf | mPDF | TCPDF |
|---|---|---|---|
| GitHub stars | 11,177 | 4,700 | 4,537 |
| Last push | 2026-08-02 | 2026-06-11 | 2026-08-21 |
| License | LGPL-2.1 | GPL-2.0 (commercial license available) | GPL-2.0+ / commercial (no SPDX tag) |
| Status | ✅ Active | ✅ Active | ⚠️ **Deprecated, maintenance-only** |
| Input model | HTML + CSS 2.1 | HTML + CSS subset | Low-level drawing API + writeHTML |
| Unicode / CJK | DejaVu fonts bundled; CJK needs custom fonts | ✅ Excellent (UTF-8 native, CJK via fonts) | ✅ Good (Unicode core fonts) |
| RTL / Arabic / Hebrew | ⚠️ Limited | ✅ Strong | ✅ Strong |
| Page headers/footers | ✅ CSS `@page` | ✅ Headers/footers, paged CSS | ✅ Manual |
| Barcodes built-in | ❌ | ✅ (needs `bcmath`) | ✅ 40+ symbologies |
| Composer-friendly | ✅ `dompdf/dompdf` | ✅ `mpdf/mpdf` | ⚠️ Legacy layout; successor `tecnickcom/tc-lib-pdf` |
| Best for | HTML→PDF in proprietary apps | Typography-heavy PDFs, reports, RTL | Legacy systems already on TCPDF |

## Use-Case Decision Matrix

| Use case | Recommended tool | Why |
|---|---|---|
| Invoices, receipts, order confirmations from HTML templates | **Dompdf** | LGPL-2.1, zero license friction in commercial apps, `loadHtml` → `render` → `stream` in four lines |
| Large reports with complex CSS, RTL, or CJK content | **mPDF** | Best typography engine of the three; UTF-8 native; beware GPL for distribution |
| Closed-source SaaS embedding PDF generation | **Dompdf** (or mPDF with commercial license) | LGPL permits proprietary use without releasing source; GPL-2.0 does not |
| Barcode-bearing labels or tickets | **TCPDF (legacy)** or **mPDF** | TCPDF ships 40+ symbologies; mPDF generates barcodes with `bcmath` |
| Existing TCPDF codebase in production | **Keep TCPDF for now, plan migration** | Deprecated but maintained for critical fixes; migrate in phases to `tc-lib-pdf` |
| Modern, type-safe, Composer-first PDF stack | **tecnickcom/tc-lib-pdf** (TCPDF successor) | Modular architecture, better static-analysis fit — but a different API |

## Dompdf — The Safe Default for HTML to PDF

Dompdf is, at its heart, "a CSS 2.1 compliant HTML layout and rendering engine written in PHP." That sentence matters: it is not a drawing library — you hand it HTML and it lays it out. The Quick Start from the official README is the entire mental model:

```php
// reference the Dompdf namespace
use Dompdf\Dompdf;

// instantiate and use the dompdf class
$dompdf = new Dompdf();
$dompdf->loadHtml('hello world');

// (Optional) Setup the paper size and orientation
$dompdf->setPaper('A4', 'landscape');

// Render the HTML as PDF
$dompdf->render();

// Output the generated PDF to Browser
$dompdf->stream();
```

Options are set via a dedicated `Options` class — `$options->set('defaultFont', 'Courier')` — and external stylesheets, inline `style` tags, `@import`, `@media`, and `@page` rules are all respected. Fonts: Dompdf embeds any font referenced via CSS `@font-face` (pre-loaded or accessible), and ships DejaVu Sans/Serif/Mono out of the box for decent Unicode coverage.

**The licensing story is the reason Dompdf wins for business software.** LGPL-2.1 lets you link the library into proprietary applications without releasing your own source — you only have to make *changes to Dompdf itself* available. For a SaaS product or a closed-source internal tool, that is the difference between shipping and a legal review.

**Where Dompdf falls short**: CSS 2.1, not CSS3. No flexbox, no grid, limited `position` support. If your designers style for the browser first and the PDF second, expect layout drift — and budget for a "PDF stylesheet" early.

## mPDF — The Typography Powerhouse (License Caveat)

mPDF generates PDFs "from UTF-8 encoded HTML," and its real strength is text: full UTF-8 handling, strong RTL (Arabic, Hebrew) support, CJK with proper fonts, and a much larger CSS subset than Dompdf. Since version 7.0 the basic usage is deceptively simple:

```php
require_once __DIR__ . '/vendor/autoload.php';

$mpdf = new \Mpdf\Mpdf();
$mpdf->WriteHTML('<h1>Hello world!</h1>');
$mpdf->Output();
```

That outputs the PDF inline to the browser as `application/pdf`. For real documents you configure page size, margins, headers/footers, and fonts in the `Mpdf` constructor options array.

**The license trap is real and frequently discovered late.** mPDF is **GPL-2.0**. If you distribute a closed-source application that embeds mPDF — a desktop app, a commercial plugin, a proprietary SaaS deliverable shipped to customers — GPL obligations kick in. mPDF's maintainers offer a commercial license precisely for this; budget for it, or choose Dompdf. This is the same calculation Java teams face with iText's AGPL, which we cover in our [Java PDF library comparison](../2026-08-26-java-pdf-libraries-pdfbox-openpdf-itext-comparison/).

**Operational caveats from the official README**: mPDF needs optional PHP extensions for advanced features — `zlib` for compression of output and embedded fonts, `bcmath` for barcode generation, `xml` for character-set conversion and SVG. And it "has some problems with fetching external HTTP resources with single-threaded servers such as `php -S`" — the README explicitly recommends nginx (php-fpm) or Apache. If your dev environment is `php -S` and your PDFs reference remote images, they will silently break.

## TCPDF — Deprecated, and the Font System Just Moved

TCPDF's story changed permanently in 2026. The README now opens with a **Deprecation Notice**: *"TCPDF is deprecated and in maintenance-only mode. Active feature development has moved to tc-lib-pdf, the modern and modular successor. For new projects, use `tecnickcom/tc-lib-pdf`."* Legacy systems get critical compatibility fixes; nothing else.

If that were the whole story, the advice would be simple. It is not — because the TCPDF repository also shipped a **modern-engine rewrite** whose compatibility is documented with unusual honesty:

- **The public API is unchanged.** All 291 public method signatures remain; existing code keeps calling `new TCPDF(...)`, `AddPage()`, `SetFont()`, `Cell()`, `writeHTML()`, `Output()` exactly as before.
- **Rendering moved to the `tc-lib-*` libraries** (text layout, HTML/CSS, fonts, graphics, barcodes, encryption, signatures). A machine-verified `MAPPING.md` tracks every method's delegation status.
- **Output is structurally equivalent, not byte-identical.** Line-breaking and font metrics differ slightly; long documents may paginate one page earlier or later. Regression tests that diff PDFs byte-for-byte will break.
- **Legacy behaviors were dropped**: legacy font definitions, EPS vector import, always-on stream compression, policy-based local file access.

The font migration is the part that will bite existing users hardest. Repository-shipped `fonts/` assets are gone; fonts now resolve from `vendor/tecnickcom/tc-lib-pdf-font/target/fonts/`:

```php
require __DIR__.'/vendor/autoload.php';

// Optional: override only if you need a non-default path.
define('K_PATH_FONTS', __DIR__.'/vendor/tecnickcom/tc-lib-pdf-font/target/fonts/');

$pdf->SetFont('helvetica', '', 11);
```

Two breaking details from the official migration path: **legacy PHP font descriptors (`fontname.php` + `fontname.z`) are no longer supported** — convert the original TTF/OTF with the `tc-lib-pdf-font` importer instead — and any deployment that assumed a repository-relative `fonts/` folder (custom `K_PATH_FONTS` overrides) must repackage to ship `vendor/` assets in production.

## Pitfalls and Migration Notes

- **Design for PDF, not for the browser.** All three engines render a subset of CSS. Dompdf is CSS 2.1; mPDF supports more but not everything; TCPDF's HTML support is a table-based approximation. Maintain a separate PDF stylesheet and test every template — this advice is identical across languages, as our [Python PDF library comparison](../2026-07-01-python-pdf-libraries-reportlab-fpdf2-pikepdf-pdfplumber-pymupdf/) and [JavaScript PDF guide](../2026-07-21-javascript-pdf-generation-pdfkit-jspdf-pdfmake/) confirm.
- **CJK text requires fonts, everywhere.** Dompdf's DejaVu fonts do not cover CJK; mPDF needs you to register a CJK font; TCPDF's core fonts are Windows-ANSI only. Embedding a CJK font adds megabytes to the binary — test memory limits.
- **Memory and execution time limits.** Rendering a 500-page report in any of these libraries is CPU- and RAM-hungry. Run PDF generation in a queue worker, not in the request thread — or users will hit `memory_limit` and `max_execution_time` at the worst moment.
- **`php -S` breaks remote resources in mPDF.** Single-threaded dev server + external images/fonts = intermittent failures. Use nginx + php-fpm locally.
- **mPDF + GPL: decide before you build, not before you ship.** If the product is closed-source, Dompdf (LGPL) or an mPDF commercial license are the two clean paths.
- **TCPDF migrations: freeze your output tests first.** Because the modern engine's output is structurally equivalent but not byte-identical, your golden-file comparisons will need re-baselining. The README's safe-migration checklist: require `tecnickcom/tc-lib-pdf`, confirm font assets under `vendor/.../target/fonts/`, smoke-test headers/body/bold-italic/RTL/Unicode, remove stale `K_PATH_FONTS` overrides, then re-run regression comparisons.
- **Your PDF stack is part of your PHP toolchain.** Dompdf, mPDF, and even the new `tc-lib-pdf` all install cleanly via Composer. For the broader PHP ecosystem story — including how the language's mature libraries handle their own licensing — see our [PHP email library comparison](../2026-08-24-php-email-libraries-phpmailer-symfony-mailer-swiftmailer-comparison/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP PDF Generation in 2026: Dompdf vs mPDF vs TCPDF — Which One Should You Actually Use?",
  "description": "Current-state comparison of the three main PHP PDF libraries — Dompdf, mPDF, and TCPDF — covering the TCPDF deprecation, GPL vs LGPL licensing pitfalls, real code examples, live GitHub stats, and migration checklists.",
  "datePublished": "2026-08-26",
  "dateModified": "2026-08-26",
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

**Q: Is TCPDF still supported in 2026?**
A: Only in maintenance mode. The official README declares TCPDF deprecated, with active development moved to `tecnickcom/tc-lib-pdf`. Critical compatibility fixes still land (last push August 2026), but new projects should not start on TCPDF.

**Q: Dompdf vs mPDF — which license is safer for a commercial product?**
A: Dompdf (LGPL-2.1) is safer: you can use it in proprietary software without releasing your source as long as you do not modify Dompdf itself. mPDF is GPL-2.0 — distributing closed-source software that embeds it requires a commercial license from the maintainers.

**Q: Can Dompdf handle CJK or Arabic text?**
A: Dompdf bundles DejaVu fonts for broad Unicode coverage, but full CJK requires registering custom fonts via `@font-face`. For serious RTL/CJK typography, mPDF is the stronger engine.

**Q: What changed with TCPDF fonts after the rewrite?**
A: Repository-shipped `fonts/` assets were removed; fonts now resolve from `vendor/tecnickcom/tc-lib-pdf-font/target/fonts/`. Legacy PHP font descriptors (`fontname.php` + `fontname.z`) are no longer supported — convert TTFs with the `tc-lib-pdf-font` importer.

**Q: Which PHP PDF library has the most stars?**
A: Dompdf leads with 11,177 GitHub stars, followed by mPDF at 4,700 and TCPDF at 4,537 (as of 2026-08-26). Dompdf is also the most recently active of the two actively maintained options.

**Q: Do these libraries work with Composer?**
A: Yes. Dompdf (`dompdf/dompdf`) and mPDF (`mpdf/mpdf`) are standard Composer packages. TCPDF's legacy package still resolves, but the recommended Composer-first successor is `tecnickcom/tc-lib-pdf`, with font assets in `tecnickcom/tc-lib-pdf-font`.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
