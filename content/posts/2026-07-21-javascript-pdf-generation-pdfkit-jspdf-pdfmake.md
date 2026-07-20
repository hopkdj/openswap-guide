---
title: "JavaScript PDF Generation Libraries: PDFKit vs jsPDF vs pdfmake — Building Documents Programmatically"
date: "2026-07-21"
tags: ["javascript", "pdf", "nodejs", "pdfkit", "jspdf", "document-generation", "web-development", "libraries"]
draft: false
---

## Introduction

Generating PDF documents programmatically is a core requirement for countless applications — invoices, reports, certificates, tickets, and labels all need to end up as downloadable PDFs. The JavaScript ecosystem offers several mature libraries for this task, each with different design philosophies and use cases.

This article compares three leading JavaScript PDF generation libraries: **PDFKit**, **jsPDF**, and **pdfmake**. We'll examine their APIs, performance characteristics, and ideal use cases to help you pick the right tool for your next project.

## Quick Comparison

| Feature | PDFKit | jsPDF | pdfmake |
|---------|--------|-------|---------|
| GitHub Stars | ~10,000 | ~29,000 | ~12,000 |
| Environment | Node.js | Browser + Node.js | Both |
| Layout Model | Absolute positioning | Absolute positioning | Declarative document definition |
| Tables | Manual (via plugin) | Plugin required | Built-in |
| Unicode / CJK | Font embedding | Limited | Font embedding |
| Watermarks | Native | Manual | Native |
| Streaming Output | Yes (pipable) | No (in-memory) | No (in-memory) |
| Weekly npm Downloads | ~2M | ~3.5M | ~800K |
| License | MIT | MIT | MIT |

## PDFKit: Node.js Powerhouse

PDFKit is the go-to choice for server-side PDF generation in Node.js. It provides a low-level drawing API with precise control over every pixel, making it ideal for complex layouts, custom graphics, and high-volume server-side generation.

```javascript
const PDFDocument = require('pdfkit');
const fs = require('fs');

const doc = new PDFDocument({
  size: 'A4',
  margins: { top: 50, bottom: 50, left: 72, right: 72 },
  info: { Title: 'Invoice', Author: 'Example Corp' }
});

doc.pipe(fs.createWriteStream('invoice.pdf'));

// Header
doc.fontSize(24).font('Helvetica-Bold')
   .text('INVOICE', { align: 'center' });
doc.moveDown();

// Company info
doc.fontSize(12).font('Helvetica')
   .text('Example Corporation', 72, 120)
   .text('123 Business St, Suite 100', 72, 135)
   .text('invoice@example.com', 72, 150);

// Line items table
const tableTop = 200;
const items = [
  { description: 'Web Development', quantity: 40, rate: 150, amount: 6000 },
  { description: 'Server Setup', quantity: 8, rate: 200, amount: 1600 },
  { description: 'Maintenance', quantity: 1, rate: 500, amount: 500 }
];

doc.font('Helvetica-Bold');
doc.text('Description', 72, tableTop);
doc.text('Qty', 350, tableTop);
doc.text('Rate', 400, tableTop);
doc.text('Amount', 450, tableTop, { align: 'right' });

let y = tableTop + 20;
doc.font('Helvetica');
items.forEach(item => {
  doc.text(item.description, 72, y);
  doc.text(item.quantity.toString(), 350, y);
  doc.text(`$${item.rate}`, 400, y);
  doc.text(`$${item.amount}`, 450, y, { align: 'right' });
  y += 20;
});

// Total
doc.moveTo(300, y + 10).lineTo(520, y + 10).stroke();
doc.font('Helvetica-Bold').fontSize(14);
doc.text(`Total: $${items.reduce((s, i) => s + i.amount, 0)}`, 350, y + 15, { align: 'right' });

doc.end();
```

PDFKit's streaming architecture is a standout feature — documents are piped directly to HTTP responses or file streams, keeping memory usage low even for multi-page PDFs with embedded images. It supports TrueType and OpenType fonts with Unicode, making it suitable for international documents. For more complex PDF processing workflows, check our guide on [self-hosted PDF document generation tools](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-page/).

## jsPDF: Browser-First PDF Generation

jsPDF is the dominant choice for client-side PDF generation in the browser. With nearly 30,000 GitHub stars, it's the most popular JavaScript PDF library by a wide margin. jsPDF can also run in Node.js via the `jspdf` npm package, though its API feels more natural in browser contexts.

```javascript
import { jsPDF } from 'jspdf';

const doc = new jsPDF({
  orientation: 'portrait',
  unit: 'mm',
  format: 'a4'
});

// Add text with positioning
doc.setFontSize(22);
doc.text('Certificate of Completion', 105, 30, { align: 'center' });

doc.setFontSize(14);
doc.text('This certifies that', 105, 55, { align: 'center' });

doc.setFontSize(20);
doc.setTextColor(0, 51, 102);
doc.text('Jane Doe', 105, 70, { align: 'center' });
doc.setTextColor(0, 0, 0);

doc.setFontSize(12);
doc.text('has successfully completed the', 105, 82, { align: 'center' });
doc.text('Advanced JavaScript Course', 105, 92, { align: 'center' });

// Add a decorative line
doc.setDrawColor(0, 51, 102);
doc.setLineWidth(0.5);
doc.line(40, 105, 170, 105);

// Add an image (logo)
const logoBase64 = '...'; // Base64-encoded image
doc.addImage(logoBase64, 'PNG', 80, 120, 50, 20);

// Save automatically
doc.save('certificate.pdf');
```

jsPDF's biggest strength is **browser-side generation without a server round-trip**. Users fill out a form, click "Download," and the PDF is generated instantly in the browser using the Canvas API. This makes jsPDF perfect for client-side reports, receipts, and simple documents where sending data to a server for PDF rendering would add unnecessary latency.

The main limitation: jsPDF struggles with complex layouts and multi-page tables. Its positioning system is pixel-based and absolute — there's no automatic flow, pagination, or reflow. For server-side PDF generation with complex data, tools like [self-hosted PDF processing platforms](../2026-05-02-stirling-pdf-vs-gotenberg-vs-ocrmypdf-self-hosted-pdf-processing-guid/) offer more robust alternatives.

## pdfmake: Declarative Document Design

pdfmake takes a fundamentally different approach: instead of a drawing API, you define your document as a JavaScript object — paragraphs, tables, images, columns, headers, footers — and pdfmake handles layout, pagination, and text flow automatically.

```javascript
const pdfmake = require('pdfmake');

const fonts = {
  Roboto: {
    normal: 'fonts/Roboto-Regular.ttf',
    bold: 'fonts/Roboto-Medium.ttf',
    italics: 'fonts/Roboto-Italic.ttf',
    bolditalics: 'fonts/Roboto-MediumItalic.ttf'
  }
};

const printer = new pdfmake(fonts);

const docDefinition = {
  pageSize: 'A4',
  pageMargins: [40, 60, 40, 60],
  header: { text: 'Monthly Report', alignment: 'center', margin: [0, 20] },
  footer: (currentPage, pageCount) => ({
    text: `Page ${currentPage} of ${pageCount}`,
    alignment: 'center'
  }),
  content: [
    { text: 'Sales Performance Report', style: 'header' },
    { text: 'July 2026', style: 'subheader' },
    '
',
    {
      style: 'tableExample',
      table: {
        headerRows: 1,
        widths: ['*', 'auto', 'auto', 'auto'],
        body: [
          [{ text: 'Product', style: 'tableHeader' },
           { text: 'Units', style: 'tableHeader' },
           { text: 'Price', style: 'tableHeader' },
           { text: 'Revenue', style: 'tableHeader' }],
          ['Widget A', '1,240', '$12.99', '$16,107.60'],
          ['Widget B', '890', '$24.50', '$21,805.00'],
          ['Widget C', '2,100', '$8.75', '$18,375.00'],
          [{ text: 'Total', colSpan: 3, alignment: 'right', bold: true }, {}, {},
           { text: '$56,287.60', bold: true }]
        ]
      },
      layout: 'lightHorizontalLines'
    },
    '
',
    { text: 'Key Insights', style: 'subheader' },
    {
      ul: [
        'Widget A sales exceeded projections by 15% this quarter.',
        'Widget C continues to be the volume leader with 2,100 units sold.',
        'Overall revenue grew 12% compared to the previous quarter.'
      ]
    }
  ],
  styles: {
    header: { fontSize: 22, bold: true, margin: [0, 0, 0, 10] },
    subheader: { fontSize: 16, bold: true, margin: [0, 10, 0, 5] },
    tableExample: { margin: [0, 5, 0, 15] },
    tableHeader: { bold: true, fontSize: 13, color: 'black' }
  }
};

const pdfDoc = printer.createPdfKitDocument(docDefinition);
pdfDoc.pipe(fs.createWriteStream('report.pdf'));
pdfDoc.end();
```

pdfmake's declarative model is transformative for data-driven documents. You describe *what* you want (a table with these rows, a header with this text), and pdfmake handles *how* to lay it out — including pagination, column widths, and text wrapping. The table system is particularly powerful, with support for row spans, column spans, automatic width calculation, and multiple border styles.

The trade-off: pdfmake requires embedding font files (it doesn't use system fonts), which adds ~1-2MB to your project. It also has a steeper learning curve than jsPDF for simple documents, and the declarative model can feel constraining when you need pixel-level control.

## Choosing the Right Library

- **PDFKit** is the best choice for server-side Node.js applications generating complex, data-heavy PDFs. Its streaming architecture keeps memory usage low, and the low-level API gives you complete control over positioning, colors, and graphics.
- **jsPDF** wins for browser-side generation — forms, receipts, and one-page documents that users need to download immediately without a server round-trip. Its massive community and 29K stars mean you'll find answers to almost any question.
- **pdfmake** excels for report generation and data-driven documents where automatic layout, pagination, and table formatting save hours of manual positioning code. Its declarative document definition separates content structure from presentation logic.

## Advanced PDF Manipulation Techniques

Beyond basic generation, production PDF workflows often require operations that go beyond what a single library can handle:

**Watermarking and Overlays.** PDFKit supports native watermarking through its opacity and layering system — draw semi-transparent text or images before the main content, and they appear as watermarks on every page. pdfmake allows watermarks through its `background` page property, applying an image or text layer behind the document content. jsPDF requires manual drawing of watermark elements on each page, which becomes tedious for multi-page documents.

**PDF Merging and Splitting.** None of these three libraries handles merging multiple PDFs — for that, you'll need `pdf-lib` (pure JavaScript, works in browser and Node.js) or `qpdf` (command-line, very fast). A common workflow: generate individual sections with PDFKit or pdfmake, then merge them into a final document using pdf-lib. The [self-hosted PDF processing platform guide](../2026-05-02-stirling-pdf-vs-gotenberg-vs-ocrmypdf-self-hosted-pdf-processing-guid/) covers tools that handle merging, splitting, and OCR in production.

**Form-Fillable PDFs.** Creating PDFs with fillable form fields (AcroForms) requires the PDF specification's interactive form features, which go beyond basic content generation. PDFKit can set form field annotations through its low-level API, but the workflow is complex. For form-heavy PDFs, consider `pdf-lib` or server-side tools like Gotenberg, which can populate PDF form fields from JSON data.

**Server-Side Performance Optimization.** When generating PDFs on a server at scale, PDFKit's streaming model can be combined with Node.js streams and backpressure handling to prevent memory exhaustion. For pdfmake, generating multiple reports simultaneously requires careful worker pool management — each report builds entirely in memory before output. A common deployment pattern uses a dedicated PDF generation microservice with PDFKit behind an HTTP API, accepting JSON payloads and returning PDF streams.

## FAQ

### Can I use PDFKit in the browser?

PDFKit is primarily designed for Node.js and uses Node.js streams. It can be bundled for browser use via Webpack or Browserify with the `brfs` transform, but this approach is complex and not officially supported. For browser PDF generation, jsPDF or pdfmake are far better choices.

### How do I handle Chinese, Japanese, or Korean text in PDFs?

PDFKit supports CJK text through embedded TrueType fonts — just register a font that contains the required glyphs. jsPDF has limited CJK support and often requires the `jspdf-cjk` plugin or manual font embedding. pdfmake requires embedding CJK font files, which can significantly increase the output PDF size. For professional multi-language documents, PDFKit with embedded fonts is the most reliable approach.

### What's the memory usage like for large PDFs?

PDFKit has the lowest memory footprint because of its streaming architecture — pages are written to the output stream as they're generated, so a 500-page PDF uses roughly the same memory as a 5-page one. jsPDF and pdfmake build the entire document in memory before output, which can cause issues with documents beyond 100 pages. For high-volume server generation, PDFKit is the clear winner.

### Can I generate PDFs from HTML templates?

None of these three libraries directly render HTML to PDF — that requires a headless browser engine (like Puppeteer or Playwright) or an HTML-to-PDF converter (like wkhtmltopdf or WeasyPrint). However, both PDFKit and pdfmake can be used alongside HTML templating: generate JSON document definitions or layout coordinates from your template engine, then feed them to the PDF library. For more on this approach, see our [self-hosted document management comparison](../2026-04-27-mayan-edms-vs-teedy-vs-docspell-self-hosted-document-management-2026/).

### How do I add digital signatures to PDFs?

None of the three libraries support digital signatures natively. For PAdES (PDF Advanced Electronic Signatures), you need a dedicated PDF manipulation library like `node-signpdf` (which works with PDFKit outputs) or a specialized signing service. PDFKit can prepare PDFs for signing by creating a signature placeholder, while jsPDF and pdfmake have limited or no support for digital signature workflows.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript PDF Generation Libraries: PDFKit vs jsPDF vs pdfmake — Building Documents Programmatically",
  "description": "Compare PDFKit, jsPDF, and pdfmake for server-side and browser PDF generation. Streaming architecture vs declarative document definitions for invoices, reports, and certificates in JavaScript.",
  "datePublished": "2026-07-21",
  "dateModified": "2026-07-21",
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
