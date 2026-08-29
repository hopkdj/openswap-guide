---
title: "C# PDF Libraries in 2026: QuestPDF vs PDFsharp vs PdfPig — Which One Should You Use?"
date: "2026-08-29"
tags: ["csharp", "dotnet", "pdf", "pdf-generation", "developer-tools"]
draft: false
cover: "/img/screenshots/questpdf-hello.jpg"
---

You finally got the client sign-off on the invoice layout, opened your C# project, and then the old question lands on your desk again: which PDF library do you build this on? Pick the wrong one and you will be fighting the library instead of shipping reports — either fighting a revenue-capped license, fighting a drawing API that makes tables painful, or discovering too late that the "PDF library" you chose cannot even read a PDF back. The .NET ecosystem has three mature, actively maintained options with completely different philosophies, and the choice is not about stars — it is about what your document pipeline actually does.

## TL;DR — Quick Verdict

If you are **generating** structured business documents — invoices, reports, contracts — and can live with a revenue-conditioned community license, **QuestPDF is the best developer experience in .NET right now**. If you need **battle-tested, MIT-licensed drawing primitives** with a document-model layer on top, or you cannot accept any usage restrictions, choose **PDFsharp + MigraDoc**. If your real job is **reading, extracting, and analyzing** existing PDFs — text, words, bounding boxes, reading order — the only serious choice is **PdfPig**, which is a parser first and a generator second. Do not use a writer library to parse, and do not use a parser library to generate complex layouts.

## Comparison at a Glance

| Criterion | QuestPDF | PDFsharp & MigraDoc | PdfPig |
|---|---|---|---|
| **Primary role** | Declarative PDF generation | Low-level drawing + document model | PDF parsing, extraction, layout analysis |
| **GitHub stars** | 14,169 | 978 | 2,552 |
| **License** | Community + commercial (free under $1M revenue) | MIT | Apache-2.0 |
| **Last push** | 2026-08-29 | 2026-05-05 | 2026-08-27 |
| **API style** | Fluent `Document.Create(...)` composition | `XGraphics` drawing + `MigraDoc` document tree | `PdfDocument.Open(...)` reader + `PdfDocumentBuilder` writer |
| **Can it read PDFs?** | No | Minimal | Yes — the core use case |
| **Can it generate PDFs?** | Yes, rich layouts | Yes, full control | Basic (Standard 14 / TrueType fonts only) |
| **Learning curve** | Low-medium | Medium-high | Medium (different skillset) |
| **Best for** | Business documents, invoices, reports | Precise graphics, forms, low-level control | Search, extraction, QA, document analysis |

## Decision Matrix: Use Case → Tool → Why

| Use case | Recommended tool | Why |
|---|---|---|
| Invoices, quotes, contracts, multi-page reports | **QuestPDF** | Fluent layout API makes repeating headers, footers, and page flow trivial |
| Pixel-precise graphics, charts, drawings, labels | **PDFsharp** | `XGraphics` gives you direct drawing primitives and full control |
| Formal long documents with headings and paragraphs | **MigraDoc** (PDFsharp's companion) | Document-object model with styles, like a mini word processor |
| Extract text, tables, or reading order from existing PDFs | **PdfPig** | Dedicated layout-analysis pipeline (`WordExtractor`, `PageSegmenter`, reading-order detection) |
| Build a PDF QA/regression tool that re-reads its own output | **PdfPig** (reader) + QuestPDF or PDFsharp (writer) | Pair a strong parser with a strong generator |
| A library you can ship inside a product with zero license anxiety | **PDFsharp** | Pure MIT — no revenue check, no license key, no telemetry question |

## QuestPDF — Design Documents Like Software

QuestPDF (14,169 stars, last push 2026-08-29) treats a document as a composition of components. Instead of positioning text at coordinates, you describe a page as a tree of layout elements — `Column`, `Row`, `Table`, `Text`, `Image` — and the library handles flow, pagination, and content breaking. The official quick-start from the repository shows the whole model:

```csharp
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

// set your license here:
// QuestPDF.Settings.License = LicenseType.Community;

Document.Create(container =>
{
    container.Page(page =>
    {
        page.Size(PageSizes.A4);
        page.Margin(2, Unit.Centimetre);
        page.PageColor(Colors.White);
        page.DefaultTextStyle(x => x.FontSize(20));

        page.Header()
            .Text("Hello PDF!")
            .SemiBold().FontSize(36).FontColor(Colors.Blue.Medium);

        page.Content()
            .PaddingVertical(1, Unit.Centimetre)
            .Column(x =>
            {
                x.Spacing(20);

                x.Item().Text(Placeholders.LoremIpsum());
                x.Item().Image(Placeholders.Image(200, 100));
            });

        page.Footer()
            .AlignCenter()
            .Text(x =>
            {
                x.Span("Page ");
                x.CurrentPageNumber();
            });
    });
})
.GeneratePdf("hello.pdf");
```

The `CurrentPageNumber()` span in the footer is the feature that wins people over: pagination and content flow are handled for you. Tables with repeating headers, cell spanning, and conditional styling are all declarative. The README makes the pitch explicit — "Stop fighting with HTML-to-PDF conversion. Build pixel-perfect reports, invoices, and exports using the language and tools you already love." The one thing you must internalize is the **license model**: the library is free for individuals, non-profits, open-source projects, and organizations under **$1 million in annual gross revenue**. Above that threshold you need a paid license, and the license type must be set in code (`LicenseType.Community` or `LicenseType.Professional`) before the first generation or the library throws.

## PDFsharp & MigraDoc — The Battle-Tested Classic

PDFsharp (978 stars, last push 2026-05-05) has been around since 2005 and is the conservative choice: pure MIT license, no revenue caps, no license keys, no runtime license checks. The core library gives you an `XGraphics` surface on a `PdfPage` — you draw lines, ellipses, text, and images with absolute control. The canonical Hello World from the official samples repository shows the drawing model:

```csharp
using PdfSharp.Pdf;
using PdfSharp.Drawing;
using PdfSharp.Fonts;

// Create a new PDF document.
var document = new PdfDocument();
document.Info.Title = "Created with PDFsharp";
document.Info.Subject = "Hello, World!";

// Create an empty page in this document.
var page = document.AddPage();

// Get an XGraphics object for drawing on this page.
var gfx = XGraphics.FromPdfPage(page);

var width = page.Width.Point;
var height = page.Height.Point;

// Draw two lines with a red default pen.
gfx.DrawLine(XPens.Red, 0, 0, width, height);
gfx.DrawLine(XPens.Red, width, 0, 0, height);

// Draw a circle with a red pen which is 1.5 point thick.
var r = width / 5;
gfx.DrawEllipse(new XPen(XColors.Red, 1.5), XBrushes.White,
    new XRect(width / 2 - r, height / 2 - r, 2 * r, 2 * r));

// Create a font and draw the text.
var font = new XFont("Times New Roman", 20, XFontStyleEx.BoldItalic);
gfx.DrawString("Hello, PDFsharp!", font, XBrushes.Black,
    new XRect(0, 0, width, height), XStringFormats.Center);

// Save the document.
document.Save("hello.pdf");
```

Low-level drawing is powerful but verbose, which is why the project ships **MigraDoc** — a separate document model where you build `Document` → `Section` → `Paragraph` / `Table` objects with styles, then render that tree to PDF via `MigraDoc.DocumentObjectModel` and `MigraDoc.Rendering`. MigraDoc is effectively a miniature word processor: define a style once, reuse it across headings and body text, and let the renderer flow content across pages. Version 7 is currently in preview (7.0.0 Preview 1, published 2026-03-24) with C# 12 support and targets .NET 8, 9, and 10 — production teams should pin the stable 6.x line unless they want to ride the preview.

## PdfPig — The Reader the Others Aren't

PdfPig (2,552 stars, last push 2026-08-27) is a C# port of Apache PDFBox, and it approaches the format from the opposite direction: it is a **parser first**. If your pipeline needs to extract text from uploaded PDFs, verify that generated documents contain the right content, or analyze document structure, PdfPig is the tool — the official README's extraction sample is the real deal:

```csharp
using UglyToad.PdfPig;
using UglyToad.PdfPig.DocumentLayoutAnalysis.TextExtractor;
using UglyToad.PdfPig.DocumentLayoutAnalysis.WordExtractor;

using (PdfDocument document = PdfDocument.Open("document.pdf"))
{
    foreach (Page page in document.GetPages())
    {
        string text = ContentOrderTextExtractor.GetText(page);
        IEnumerable<Word> words = page.GetWords(NearestNeighbourWordExtractor.Instance);
    }
}
```

The README warns about the classic trap: do **not** use `page.Text` directly, because the `Text` property preserves internal content order, which is rarely the order a human reads. The layout-analysis pipeline — `NearestNeighbourWordExtractor` for words, `DocstrumBoundingBoxes` for page segmentation, `UnsupervisedReadingOrderDetector` for reading order — is what makes extraction actually usable in production. On the generation side, `PdfDocumentBuilder` exists but is deliberately limited: it supports the Standard 14 fonts and TrueType fonts, and cannot edit forms, annotations, or existing font-based content. If you need a full round-trip (generate then re-read), the pragmatic stack is PdfPig for reading and QuestPDF or PDFsharp for writing.

## Pitfalls & Practical Advice

**The QuestPDF license trap.** The community license is generous but conditional — if your organization crosses $1M annual gross revenue, you must purchase a license. And the library enforces it at runtime: you must set `QuestPDF.Settings.License` explicitly, and the current versions throw on unset or misconfigured license types. Audit this before you commit to the API, not after your legal team finds the dependency.

**The `page.Text` ordering trap in PdfPig.** Extracting text with `page.Text` returns content in internal PDF order, which is frequently wrong for human reading (multi-column layouts, table cells, wrapped lines). Always use `ContentOrderTextExtractor.GetText(page)` or the word/segment pipeline. This single mistake produces "garbled" extraction bugs that look like library bugs but are usage errors.

**Preview-version discipline with PDFsharp 7.** The 7.0 line is a preview with new target frameworks and build-system changes (assets moved out of the repository, PowerShell-based asset downloads, central package management). If you are starting a production project today, evaluate the stable 6.x releases unless you specifically need .NET 10 support from the 7.0 preview.

**Don't use a writer to parse.** QuestPDF and PDFsharp have no meaningful PDF-reading capability. If your app ingests customer PDFs and extracts data, you need PdfPig (or a dedicated tool) regardless of which writer you pick. Conversely, PdfPig's builder is not a layout engine — generating a polished multi-page invoice with it means reimplementing text measurement and pagination by hand.

**Font availability differs.** QuestPDF bundles and embeds fonts cleanly for consistent rendering. PDFsharp depends on installed fonts (with a documented `GlobalFontSettings` mechanism for custom resolvers). PdfPig's builder only ships the Standard 14 fonts plus TrueType registration. If your documents use non-Latin scripts, verify font embedding behavior in your chosen library early — it is the most common cause of "the PDF looks different on the server".

For more on the PDF generation landscape across languages, see our [Java PDF library comparison](../2026-08-26-java-pdf-libraries-pdfbox-openpdf-itext-comparison/) and the [Rust PDF generation guide](../2026-08-26-rust-pdf-libraries-printpdf-lopdf-pdf-rs-comparison/). If your stack leans on HTML-to-PDF instead of a native library, our [HTML-to-PDF document generation comparison](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-pagedjs/) covers WeasyPrint, wkhtmltopdf, Typst, and Paged.js.

## FAQ

**Is QuestPDF really free?**
Yes for individuals, non-profits, open-source projects, and organizations under $1M annual gross revenue. Larger organizations must buy a commercial license, and the license type must be set explicitly in code before first use.

**Can I extract text from PDFs with QuestPDF or PDFsharp?**
No — both are generation-focused. For text extraction, layout analysis, or reading-order detection, use PdfPig, which is built for parsing and is a port of Apache PDFBox.

**Which library is best for invoices with repeating headers?**
QuestPDF. Its fluent API handles page flow, repeating table headers, and footer page numbers declaratively, which keeps invoice code small and maintainable.

**What is the difference between PDFsharp and MigraDoc?**
PDFsharp is the low-level drawing engine (`XGraphics` on a `PdfPage`). MigraDoc is a higher-level document-object model with styles and flowing paragraphs that renders through PDFsharp. Most business-document work uses MigraDoc on top of PDFsharp.

**Does PdfPig support creating PDFs?**
A basic `PdfDocumentBuilder` exists with Standard 14 and TrueType font support, but it cannot edit forms, annotations, or existing content. Treat PdfPig as a reader, and pair it with a writer library for round-trip pipelines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C# PDF Libraries in 2026: QuestPDF vs PDFsharp vs PdfPig — Which One Should You Use?",
  "description": "Compare the three leading C# PDF libraries in 2026: QuestPDF's declarative generation, PDFsharp's MIT-licensed drawing engine, and PdfPig's parsing and extraction pipeline. Includes code samples, license analysis, and decision matrix.",
  "datePublished": "2026-08-29",
  "dateModified": "2026-08-29",
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
