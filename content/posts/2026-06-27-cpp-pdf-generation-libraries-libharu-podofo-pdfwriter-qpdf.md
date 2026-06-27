---
title: "C++ PDF Generation Libraries: libHaru vs PoDoFo vs PDF-Writer vs QPDF"
date: "2026-06-27"
tags: ["c++", "pdf", "document-generation", "libharu", "developer-libraries"]
draft: false
---

## Introduction

Generating and manipulating PDF documents from C++ applications is a common requirement across enterprise reporting, invoicing systems, and document automation workflows. Unlike higher-level HTML-to-PDF tools, native C++ PDF libraries offer direct control over every element on the page — text positioning, vector graphics, embedded fonts, and metadata — without the overhead of a browser rendering engine. This guide compares four mature C++ PDF libraries that cover the spectrum from lightweight generation to industrial-grade document transformation.

## Comparison Table

| Feature | libHaru | PoDoFo | PDF-Writer | QPDF |
|---------|---------|--------|------------|------|
| **Stars** | 1,979 | 585 | 1,014 | 5,181 |
| **License** | ZLIB/Libpng | LGPL 2.1 | Apache 2.0 | Apache 2.0 |
| **Primary use** | PDF creation | PDF creation & editing | PDF creation & parsing | PDF transformation |
| **C++ Standard** | C89 (C library) | C++17 | C++11 | C++17 |
| **Unicode support** | Yes (CID fonts) | Yes | Yes (full UTF-8) | Yes |
| **Encryption** | RC4, AES-128 | RC4, AES | AES-128/256 | AES-256 |
| **Font embedding** | Type1, TrueType | TrueType, Type1 | TrueType, OpenType | Preserves existing |
| **Linearization** | No | No | No | Yes (web optimization) |
| **Build system** | CMake / Autotools | CMake | Makefile | CMake |
| **Header-only** | No | No | No | No |
| **Best for** | Simple PDF generation | Document editing workflows | High-performance PDF creation | PDF repair, optimization, splitting |

## libHaru — Lightweight PDF Generation

libHaru is a mature C library (with a clean C API callable from C++) focused exclusively on creating PDF documents from scratch. It supports compressed object streams, embedded Type1 and TrueType fonts, CID fonts for Unicode text, JPEG and PNG image embedding, and both RC4 and AES-128 encryption. With over 1,900 stars and two decades of history, libHaru is battle-tested in production environments ranging from ERP systems to scientific publishing tools.

libHaru's API is procedural and straightforward — you create a document, add pages, set fonts, and draw text or graphics using coordinate-based positioning. The library handles internal PDF structure (cross-reference tables, object numbering, compression) transparently, making it ideal for report generation where you control the exact layout.

### Building and Using libHaru

```bash
# Build from source
git clone https://github.com/libharu/libharu.git
cd libharu
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
sudo cmake --install build
```

```cpp
#include <hpdf.h>
#include <cstdio>

int main() {
    HPDF_Doc pdf = HPDF_New(nullptr, nullptr);
    HPDF_Page page = HPDF_AddPage(pdf);
    HPDF_Page_SetSize(page, HPDF_PAGE_SIZE_A4, HPDF_PAGE_PORTRAIT);

    HPDF_Font font = HPDF_GetFont(pdf, "Helvetica", nullptr);
    HPDF_Page_BeginText(page);
    HPDF_Page_SetFontAndSize(page, font, 24);
    HPDF_Page_TextOut(page, 50, 750, "Invoice Report");
    HPDF_Page_EndText(page);

    HPDF_SaveToFile(pdf, "output.pdf");
    HPDF_Free(pdf);
    return 0;
}
```

## PoDoFo — Document Manipulation Powerhouse

PoDoFo (PDF Document Format) is a C++17 library designed for both creating and modifying existing PDF documents. Unlike libHaru's create-only approach, PoDoFo can parse, inspect, and edit PDF files — reordering pages, extracting text, modifying annotations, and rebuilding internal structures while preserving the original document's integrity.

PoDoFo's object model directly mirrors the PDF specification (pages, resources, contents, annotations) making it an excellent choice for developers who need to understand and manipulate PDF internals directly. Version 0.10+ brought a fully refactored C++17 API with improved memory safety and modern CMake integration.

```bash
# Build PoDoFo with all features
git clone https://github.com/podofo/podofo.git
cd podofo
cmake -B build -DCMAKE_BUILD_TYPE=Release       -DPODOFO_BUILD_STATIC=OFF       -DWANT_FONTMANAGER=ON
cmake --build build
sudo cmake --install build
```

```cpp
#include <podofo/podofo.h>
using namespace PoDoFo;

int main() {
    PdfMemDocument doc;
    auto& page = doc.GetPages().CreatePage(PdfPageSize::A4);

    PdfPainter painter;
    painter.SetCanvas(page);
    painter.TextState.SetFont(
        doc.GetFonts().SearchFont("Arial"), 18);
    painter.DrawText("Modified Document", 50, 750);
    painter.FinishDrawing();

    doc.Save("modified.pdf");
    return 0;
}
```

## PDF-Writer — High-Performance Creation

PDF-Writer (formerly Hummus PDF) is a performance-focused C++ library optimized for high-throughput PDF generation. It's used in production by financial institutions generating millions of statements daily, printing systems, and document management platforms. The library excels at creating complex documents with embedded fonts, JPEG2000 images, form XObjects for reusable content, and AES-256 encryption.

PDF-Writer's architecture separates content description from serialization, enabling streaming output that minimizes memory usage even for multi-gigabyte documents. Its API is lower-level than libHaru's, giving you precise control over PDF operators, graphics state, and content streams — but requiring deeper PDF specification knowledge.

```cpp
#include "PDFWriter/PDFWriter.h"
#include "PDFWriter/PDFPage.h"
#include "PDFWriter/PageContentContext.h"

int main() {
    PDFWriter pdf;
    pdf.StartPDF("output.pdf", ePDFVersion14);

    PDFPage page;
    page.SetMediaBox(PDFRectangle(0, 0, 595, 842));
    PageContentContext* ctx = pdf.StartPageContentContext(&page);

    ctx->BT();
    ctx->Tf(pdf.GetFontForFile("Helvetica"), 18);
    ctx->Tm(1, 0, 0, 1, 50, 780);
    ctx->Tj("Professional PDF Generation");
    ctx->ET();

    pdf.EndPageContentContext(ctx);
    pdf.WritePageAndRelease(&page);
    pdf.EndPDF();
    return 0;
}
```

## QPDF — The PDF Swiss Army Knife

QPDF is a command-line tool and C++ library specializing in structural PDF transformations rather than content creation. With over 5,000 stars, it is the de facto standard for PDF optimization, repair, and manipulation in server environments. QPDF can linearize PDFs for web-optimized streaming, split and merge documents, rotate pages, encrypt and decrypt, and — most importantly — preserve all content intact during transformations.

QPDF's content-preserving architecture makes it uniquely suited for workflows where you cannot afford to re-render or lose fidelity: adding watermarks without disturbing vector graphics, removing pages without breaking cross-references, and optimizing PDF structure without touching rendered content. It supports JSON output mode for programmatic document inspection.

```bash
# Install via package manager or build
sudo apt install libqpdf-dev

# Command-line examples
qpdf --linearize input.pdf optimized.pdf          # Web-optimize
qpdf --pages a.pdf 1-5 b.pdf 3-8 -- merged.pdf   # Merge pages
qpdf --encrypt user123 owner456 256 -- input.pdf encrypted.pdf  # Encrypt
```

```cpp
#include <qpdf/QPDF.hh>
#include <qpdf/QPDFWriter.hh>
#include <iostream>

int main() {
    QPDF qpdf;
    qpdf.processFile("input.pdf");

    auto pages = qpdf.getAllPages();
    qpdf.removePage(pages.back());

    QPDFWriter w(qpdf, "output.pdf");
    w.setLinearization(true);
    w.setQDFMode(true);
    w.write();
    return 0;
}
```

## Deployment and Build Integration

All four libraries integrate well with CMake-based C++ projects. For enterprise deployments, the pattern depends on your needs:

- **PDF-only generation**: libHaru or PDF-Writer, depending on performance requirements
- **Document editing pipelines**: PoDoFo for creation + modification
- **Server-side processing**: QPDF for transformation, paired with a generator for creation
- **High-throughput reporting**: PDF-Writer for streaming output, QPDF for post-processing

For broader document management context, see our [self-hosted PDF processing guide](../2026-05-02-stirling-pdf-vs-gotenberg-vs-ocrmypdf-self-hosted-pdf-processing-guide/) and [document automation platform comparison](../2026-05-03-docassemble-vs-docxtemplater-vs-pandoc-self-hosted-document-automation-guide/). If you need a complete document management system, our [EDMS comparison](../2026-04-27-mayan-edms-vs-teedy-vs-docspell-self-hosted-document-management-2026/) covers the server-side options.

## Performance Characteristics and Scaling

When choosing a PDF library for production workloads, understanding performance characteristics at scale is essential. libHaru generates a 100-page text report in approximately 30-50ms on modern hardware, with memory usage scaling linearly with page count. PDF-Writer's streaming architecture reduces peak memory by 40-60% compared to in-memory approaches — critical for generating 10,000+ page documents without hitting memory limits.

QPDF's linearization (web optimization) adds roughly 15-20% overhead but enables progressive rendering where the first page displays before the entire document downloads. For server-side PDF processing, PoDoFo's incremental save feature modifies only changed objects, reducing I/O by up to 90% when adding watermarks or annotations to existing documents. Benchmark your specific workload — a simple text report and a graphics-heavy catalog have dramatically different performance profiles across these libraries.


## FAQ

### Can I use these libraries for commercial closed-source software?

Yes, all four libraries have permissive licenses suitable for commercial use. libHaru uses the ZLIB/Libpng license, PDF-Writer and QPDF use Apache 2.0, and PoDoFo uses LGPL 2.1 (which requires dynamic linking for closed-source distribution). Check each license for specific attribution and distribution requirements.

### Which library handles complex Unicode text best?

PDF-Writer has the most comprehensive Unicode support, including full UTF-8 text handling, bidirectional text, and OpenType font embedding. libHaru supports CID fonts for CJK text. PoDoFo's font handling has improved significantly in 0.10+. For multilingual documents, test with your target character sets before committing.

### How do these compare to HTML-to-PDF tools like wkhtmltopdf?

HTML-to-PDF converters render through a browser engine, giving you CSS-based layout. Native C++ PDF libraries give you pixel-precise control over every element at the cost of manual layout. Use native libraries when layout precision and performance matter (financial statements, archival documents); use HTML converters when design flexibility and rapid iteration are priorities.

### Can QPDF modify existing PDF content like text or images?

No — QPDF is a content-preserving transformer. It can reorganize, encrypt, optimize, and inspect PDF documents, but it does not modify rendered page content. To change text, images, or graphics inside a PDF, use PoDoFo or regenerate the document with libHaru or PDF-Writer.

### Which library is the easiest to get started with?

libHaru has the simplest API and the shortest time-to-first-PDF. Its procedural interface, minimal boilerplate, and clear documentation make it ideal for developers who need to add PDF output to an existing C++ project quickly. PDF-Writer requires more PDF specification knowledge but offers substantially better performance at scale.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ PDF Generation Libraries: libHaru vs PoDoFo vs PDF-Writer vs QPDF",
  "description": "In-depth comparison of four C++ libraries for PDF generation and manipulation, covering creation, editing, optimization, and enterprise deployment patterns.",
  "datePublished": "2026-06-27",
  "dateModified": "2026-06-27",
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
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://hopkdj.github.io/openswap-guide/posts/2026-06-27-cpp-pdf-generation-libraries-libharu-podofo-pdfwriter-qpdf/"
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
