---
title: "PDFBox vs OpenPDF vs iText 7 in 2026: Which Java PDF Library Should You Actually Use?"
cover: "/img/screenshots/pdfbox-cover.jpg"
date: "2026-08-26"
tags: ["java", "pdf", "pdf-generation", "library-comparison", "java-libraries"]
draft: false
---

Generating PDFs in Java used to be a boring decision — until you read the fine print of your license agreement. One of the three major Java PDF libraries costs **€2,000+ per developer per year** if your product is closed-source, another is a fork that exists *because* of that pricing, and the third one has been quietly maintained by the Apache Foundation for 20 years. Pick wrong and you either pay a surprise bill or rewrite your entire document pipeline under deadline pressure. This guide compares **Apache PDFBox, LibrePDF OpenPDF, and iText 7** with live repository data and real code so you can decide in ten minutes instead of ten meetings.

## TL;DR / Quick Verdict

- **Open-source, no-strings-attached PDF generation** → **Apache PDFBox** (3,105 stars, Apache-2.0). Boring, reliable, zero legal risk, but verbose for complex layouts.
- **iText-compatible API with LGPL/MPL licensing** → **OpenPDF** (4,356 stars). The direct descendant of the old free iText, with a modern package rename in 3.0 and active maintenance.
- **Feature-complete enterprise PDFs (forms, signing, accessibility)** → **iText 7** (2,254 stars on the community mirror). Best-in-class features, but AGPL or a commercial license — there is no middle ground.
- **Budget reality check:** if you are building a commercial SaaS, iText's community edition forces AGPL obligations that most companies cannot accept. PDFBox or OpenPDF will cover 90% of typical needs for free.

## Quick Comparison Table

| Criterion | Apache PDFBox | LibrePDF OpenPDF | iText 7 (Community) |
|---|---|---|---|
| GitHub stars | 3,105 | 4,356 | 2,254 |
| License | Apache-2.0 | MPL-2.0 OR LGPL-2.1+ | AGPL-3.0 (commercial dual license) |
| Last push (2026) | 2026-08-25 | 2026-08-05 | 2026-08-25 |
| Default branch | trunk | master | develop |
| Java requirement | Java 11+ (3.0.x) | Java 11+ (1.4.x), Java 8 (1.3.x) | Java 8+ (7.x/8.x) |
| PDF creation | Yes | Yes | Yes |
| PDF editing/merging | Yes | Yes | Yes |
| Digital signatures | Yes (COSE + CMS) | Yes (via BouncyCastle) | Yes (via BouncyCastle adapter) |
| HTML → PDF | No (separate preflight tools) | Limited | Yes (pdfHTML module, commercial) |
| Forms (AcroForm) | Yes | Yes | Yes (advanced) |
| Maven coordinates | org.apache.pdfbox:pdfbox | com.github.librepdf:openpdf | com.itextpdf:itext-core (pom) |
| Commercial-friendly | ✅ Free forever | ✅ Free forever | ❌ AGPL or paid license |

## Use Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Internal tool, reports for your own team | **PDFBox** | Apache-2.0 means nobody in legal will ever ask questions |
| Commercial SaaS with customer-facing PDFs | **OpenPDF** | LGPL/MPL keeps you compliant without paying for a license |
| You are migrating from old iText 2.x/4.x code | **OpenPDF** | Same API lineage — most code ports with a package rename |
| Digital signatures, PDF/A, accessibility, complex forms | **iText 7 (paid)** | The feature gap is real and only the commercial tier unlocks everything |
| Generating invoices/barcodes on the fly | **PDFBox** | Fast enough, and the CLI tools help with debugging |
| You need HTML/CSS rendering into PDF | **None of these alone** | Pair a library with WeasyPrint/Typst (see our [document generation guide](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-pagedjs/)) |

## Apache PDFBox — The Safe Default

Apache PDFBox has been around since 2002 and is one of the few Java PDF libraries you can adopt with zero legal review. The Apache-2.0 license lets you embed it in anything, sell anything, and never think about it again. The project mirror on GitHub shows **3,105 stars** with active commits (last push 2026-08-25 on the `trunk` branch).

Its philosophy is "explicit over magical." You build a document by adding pages and drawing on a `PDPageContentStream` — it is more code than iText's layout engine, but every byte you write is understandable. The canonical Hello World from the official examples shows the pattern:

```java
// From the official PDFBox examples (examples/pdmodel/HelloWorld.java)
import java.io.IOException;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDFont;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts.FontName;

try (PDDocument doc = new PDDocument()) {
    PDPage page = new PDPage();
    doc.addPage(page);

    PDFont font = new PDType1Font(FontName.HELVETICA_BOLD);

    try (PDPageContentStream contents = new PDPageContentStream(doc, page)) {
        contents.beginText();
        contents.setFont(font, 12);
        contents.newLineAtOffset(100, 700);
        contents.showText(message);
        contents.endText();
    }
    doc.save(filename);
}
```

Maven setup is a single dependency:

```xml
<dependency>
  <groupId>org.apache.pdfbox</groupId>
  <artifactId>pdfbox</artifactId>
  <version>3.0.5</version>
</dependency>
```

The 3.x line brought a cleaner font API (`Standard14Fonts.FontName` instead of the old `PDType1Font.HELVETICA` constants), COSE and CMS signature support, and better performance on large documents. If you need to extract text, render pages to images, or fill AcroForms, PDFBox has first-class support for all of it. The main trade-off: **no automatic layout engine**. You position elements yourself, which means multi-column brochures or flowing text require real work. For that, iText's layout model is genuinely nicer.

## LibrePDF OpenPDF — The iText Successor That Stayed Free

OpenPDF is the community fork of iText 4 (the last AGPL-free version) and has grown into its own project. With **4,356 stars** and steady maintenance (last push 2026-08-05), it is the most star-popular of the three — and the licensing story is the reason why. OpenPDF is **dual-licensed MPL-2.0 OR LGPL-2.1+**, which means you can use it in commercial products as long as you comply with the (reasonable) terms of either license, and you never pay a fee.

Version 3.0 introduced a breaking change you must know about: **the package name moved from `com.lowagie` to `org.openpdf`**. Old code like `com.lowagie.text.Document` becomes `org.openpdf.text.Document`. The README documents this explicitly:

```xml
<dependency>
  <groupId>com.github.librepdf</groupId>
  <artifactId>openpdf</artifactId>
  <version>3.0.5</version>
</dependency>
```

The API itself will feel familiar to anyone who used iText 4/5-style workflows — `Document`, `PdfWriter`, `PdfReader`, `PdfStamper`. A minimal document looks like this (using the new package):

```java
import org.openpdf.text.Document;
import org.openpdf.text.Paragraph;
import org.openpdf.text.pdf.PdfWriter;

Document document = new Document();
PdfWriter.getInstance(document, new FileOutputStream("hello.pdf"));
document.open();
document.add(new Paragraph("Hello OpenPDF!"));
document.close();
```

A notable 3.x feature: **Brotli stream compression** (`PdfWriter.useBrotliCompression = true`), which shrinks content streams beyond the classic FlateDecode — handy if you generate many large PDFs. Font handling is solid, including a separate `openpdf-fonts-extra` artifact for UTF-8 Liberation fonts (CJK and Cyrillic support is far better than PDFBox's standard-14 fonts).

The catch: OpenPDF's layout engine is dated compared to iText 7's. Complex tables, accessibility tags, and PDF/A workflows require more manual work. And for **digital signatures**, you will wire up BouncyCastle yourself — the project recommends it but does not bundle a one-line solution like iText's adapter.

## iText 7 — The Most Powerful, and the Most Expensive

iText is the industry heavyweight. iText 7's community repository (2,254 stars, last push 2026-08-25) is only a mirror of the real development — the actual product includes a layout engine, pdfHTML, pdfCalligraph, pdfSweep, and best-in-class **digital signing, PDF/A, and accessibility** support. Nothing else in Java matches its form-flattening and tagged-PDF capabilities.

The licensing, though, is the sharpest edge in this comparison. The community edition is **AGPL-3.0**. That means: if you serve the PDF-generating code over a network and do not release your entire application's source under AGPL, you must buy a commercial license — priced per developer, typically in the thousands of euros per seat per year. The README is upfront about the model ("AGPL License" badge right at the top), and iText's own getting-started guide leans into the commercial tier.

When you do accept the license, the code is the cleanest of the three. The README's Hello PDF shows the high-level layout API:

```java
// From the official iText 7 README
import com.itextpdf.kernel.pdf.PdfDocument;
import com.itextpdf.kernel.pdf.PdfWriter;
import com.itextpdf.layout.Document;
import com.itextpdf.layout.element.Paragraph;

try (Document document = new Document(new PdfDocument(new PdfWriter("./hello-pdf.pdf")))) {
    document.add(new Paragraph("Hello PDF!"));
}
```

Maven requires the BOM-style `itext-core` pom plus the BouncyCastle adapter for crypto:

```xml
<properties>
  <itext.version>8.0.5</itext.version>
</properties>
<dependencies>
  <dependency>
    <groupId>com.itextpdf</groupId>
    <artifactId>itext-core</artifactId>
    <version>${itext.version}</version>
    <type>pom</type>
  </dependency>
  <dependency>
    <groupId>com.itextpdf</groupId>
    <artifactId>bouncy-castle-adapter</artifactId>
    <version>${itext.version}</version>
  </dependency>
</dependencies>
```

Version 8.0.3+ even supports **GraalVM native image** compilation — genuinely useful for serverless PDF generation. If your company already has an iText commercial subscription, this is the obvious choice and the debate ends there. If it does not, the decision is really about whether your feature list *requires* iText's advanced modules, because the AGPL clause is a deal-breaker for most proprietary products.

## Pitfalls and Migration Guide

1. **The AGPL trap is real and it bites at audit time.** A common failure: a team prototypes with iText community edition, the product ships, and legal discovers the AGPL obligation months later. The retrofit is painful — swapping iText for OpenPDF mid-project means renaming packages (`com.itextpdf.*` → `org.openpdf.*` is *not* automatic; the APIs differ enough that layout code needs rewriting). Decide licensing *before* you write your first `PdfWriter`.
2. **OpenPDF 3.0 package rename breaks old code silently.** `com.lowagie.*` imports fail to compile after upgrading from 1.x. Run a global find-and-replace for `com.lowagie.text` → `org.openpdf.text`, then fix the handful of classes that moved (`com.lowagie.text.pdf.PdfReader` → `org.openpdf.text.pdf.PdfReader`, etc.). Budget half a day for a large codebase.
3. **PDFBox 3.x font API changes.** The old `PDType1Font.HELVETICA` constants were replaced by `new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD)`. Upgrading from 2.x without reading the migration notes produces a wall of compiler errors.
4. **Non-Latin text needs embedded fonts.** PDFBox's standard 14 fonts render Latin only. For Chinese, Japanese, or Cyrillic output, embed a TTF (PDFBox: `PDType0Font.load`; OpenPDF: the `openpdf-fonts-extra` Liberation artifacts). Skipping this produces tofu boxes that look broken to exactly the users you care about.
5. **Memory blows up on big documents.** Streaming with `PDPageContentStream` and `PdfWriter` keeps memory flat; loading 10,000-page PDFs fully into memory (e.g. with `LoadAndSave` style code) will OOM your container. For batch generation, reuse a single `PDDocument`/`Document` instance and add pages incrementally.
6. **Signature features are not all equal.** If your roadmap includes PAdES or PDF/A-3 signing, iText 7 (commercial) and PDFBox 3.x both handle it, but OpenPDF requires manual BouncyCastle wiring — validate the exact signature standard your customer requires before committing.
7. **HTML-to-PDF is a separate problem.** None of these three renders arbitrary HTML/CSS well out of the box. If your input is HTML, look at the browser-based tools we covered in our [self-hosted document generation comparison](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-pagedjs/) instead of fighting a low-level PDF API.

## Why the Ecosystem Around These Libraries Matters

Choosing a PDF library is also choosing an ecosystem. PDFBox ships **command-line utilities** (`PDFBox.jar ExtractText`, `PDFBox.jar Decrypt`, `PDFBox.jar Merge`) that are invaluable in scripts — you can merge reports in a cron job without writing a line of Java. OpenPDF inherits iText's huge Stack Overflow corpus, so most questions you will ever ask have answered threads from the 2010s that still apply after the package rename. iText's advantage is the **commercial knowledge base and support SLAs** — for a regulated industry (banking, healthcare, government) where a broken signature pipeline costs real money, the paid tier's support may justify itself.

For adjacent needs — OCR and PDF processing servers, document digitization, or browser-side generation — we have dedicated guides: [Stirling PDF vs Gotenberg vs OCRmyPDF](../2026-05-02-stirling-pdf-vs-gotenberg-vs-ocrmypdf-self-hosted-pdf-processing-guide/) for server-side PDF toolkits, and [C++ PDF generation libraries](../2026-06-27-cpp-pdf-generation-libraries-libharu-podofo-pdfwriter-qpdf/) if you are outside the JVM.

## FAQ

### Is iText free for commercial use?

No. The community edition is AGPL-3.0 — if you do not open-source your entire application, you need a paid commercial license. There is no free tier for proprietary products, which is exactly why OpenPDF (LGPL/MPL) and PDFBox (Apache-2.0) exist.

### What is the difference between OpenPDF and iText?

OpenPDF is a community fork of iText 4, the last version that was free of the AGPL license. It keeps the classic iText-style API (now under the `org.openpdf` package since version 3.0) but is maintained independently and licensed MPL-2.0 OR LGPL-2.1+. iText 7 is a completely rewritten, far more feature-rich engine from the commercial iText Group.

### Can Apache PDFBox create fillable forms and digital signatures?

Yes. PDFBox supports AcroForm creation/filling and digital signing including CMS and COSE signature types. It is the most capable fully-Apache-licensed option for signing workflows. For advanced PDF/A and PAdES compliance, verify your exact requirements against the 3.x release notes.

### Which Java PDF library is fastest?

For typical report generation all three are fast enough — the bottleneck is almost always font embedding and image processing, not the library core. PDFBox 3.x and iText 7 both use streaming content; OpenPDF 3.x adds Brotli compression that can significantly reduce output size (and thus I/O time) for text-heavy PDFs. Benchmark with *your* document shape; generic "fastest library" claims rarely transfer.

### Does OpenPDF support Chinese, Japanese, and Korean text?

Yes, via embedded TTF fonts. OpenPDF's `openpdf-fonts-extra` module bundles UTF-8 Liberation fonts, and the project wiki documents multi-byte language support with custom TTFs. PDFBox also handles CJK when you embed a font with `PDType0Font.load()`. iText 7 handles it out of the box in the paid tier.

### How do I choose between PDFBox and OpenPDF?

If you want zero license complexity and don't mind manual layout code, choose PDFBox. If you want a higher-level document model (tables, paragraphs, headers/footers) and iText-style ergonomics without the AGPL, choose OpenPDF. Most teams switching away from iText for licensing reasons land on OpenPDF; teams starting fresh with simple needs usually prefer PDFBox.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PDFBox vs OpenPDF vs iText 7 in 2026: Which Java PDF Library Should You Actually Use?",
  "description": "Compare Apache PDFBox, LibrePDF OpenPDF, and iText 7 for Java PDF generation with live GitHub stats, licensing analysis, code examples, and migration pitfalls.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
