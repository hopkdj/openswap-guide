---
title: "Browser PDF in 2026: PDF.js vs react-pdf vs pdf-lib, the Full Stack Guide"
date: "2026-09-09"
tags: ["javascript", "pdf", "react", "frontend", "library"]
draft: false
cover: "/img/screenshots/pdfjs-browser-pdf-cover.jpg"
---

Your users do not want to download PDFs. They want to preview invoices, sign contracts and export reports without leaving the tab — and the moment you search "JavaScript PDF", you face a wall of libraries that all claim to do everything. Then you integrate one and discover it only renders, or only generates, or only works if your bundler cooperates.

The reality in 2026 is that browser PDF work is three different jobs — **rendering**, **React integration**, and **generation/editing** — and the three libraries that own those jobs are **PDF.js (53,848 stars)**, **react-pdf (11,166 stars)** and **pdf-lib (8,624 stars)**. They are not three rivals; they are three layers of one stack, and teams waste weeks by treating them as interchangeable.

## TL;DR: Quick Verdict

**Use PDF.js directly when you need a full viewer or are not on React.** **Use react-pdf when you are on React** — it is a thin, well-maintained wrapper over PDF.js that renders pages as components. **Use pdf-lib when you need to create, merge or fill PDFs in the browser or Node** — it is the dependency-free generation layer. The winning architecture is usually a combination: **generate documents with pdf-lib, display them with react-pdf (or PDF.js), and never let your backend touch a PDF library again.**

## Why PDF Work Is Three Problems, Not One

A shocking amount of JavaScript PDF confusion comes from the word "PDF" covering three unrelated capabilities. **Rendering** means parsing a binary PDF and drawing pages — a huge, security-sensitive task (parsing untrusted input is why this code runs in a Web Worker). **Generation** means building a valid PDF from scratch. **Editing** means loading an existing document and modifying pages, text or forms. PDF.js does the first supremely well and explicitly does not aim to be a generation toolkit. pdf-lib does the second and third and does not render at all. Libraries that promise "create and view PDFs" either bundle one of these two or are thin on one side — which is why comparing them head-to-head on features they were never built to share produces nonsense rankings.

## Feature Comparison at a Glance

| | **PDF.js** | **react-pdf** | **pdf-lib** |
|---|---|---|---|
| GitHub stars | 53,848 | 11,166 | 8,624 |
| Last push | 2026-09-08 | 2026-09-04 | 2024-07-17 |
| License | Apache-2.0 | MIT | MIT |
| Primary role | Rendering engine + full viewer | React wrapper over PDF.js | PDF creation and modification |
| Rendering | Canvas/SVG via display layer | Yes (delegates to PDF.js) | No |
| Generation | Not a goal | No | Yes (`PDFDocument.create()`) |
| Form filling | Via viewer scripting (AcroForm/XFA) | Through PDF.js document | Yes (text fields, radio groups, checkboxes) |
| Merge/split | No | No | Yes |
| Framework | Vanilla (any) | React | Vanilla (browser + Node) |
| Worker | Yes (pdf.worker) | Yes (configures PDF.js worker) | No (pure JS, synchronous) |
| Maintenance status | Mozilla, very active | Active | Stable but slowed since 2024 |

## Use Case → Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Full-featured viewer (search, thumbnails, printing) inside any app | **PDF.js viewer** | It is the engine behind Firefox's built-in PDF viewer; the display layer + viewer components are production-hardened |
| React app: render a few pages inline (previews, e-sign flows) | **react-pdf** | `<Document>`/`<Page>` components with loading states; worker setup is documented for every bundler |
| Client-side invoice/report generation, no server round-trip | **pdf-lib** | Pure JS, no native deps, runs in browser and Node with the same API |
| Fill and flatten a government or vendor PDF form | **pdf-lib** | Field APIs for text, dropdowns, radio groups; also signs via external libraries |
| Server-side HTML → PDF at scale | **Neither** — see server tools | Our [self-hosted PDF generation guide](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-pagedjs/) covers WeasyPrint/Typst-class engines that handle pagination properly |

## PDF.js: The Rendering Engine Mozilla Maintains

PDF.js is the PDF reader that ships inside Firefox, and it is structured in three layers that the official getting-started documentation spells out: **core** (parses the binary format — advanced use only), **display** (the public API for rendering and extracting data), and **viewer** (the full UI built on display — Firefox's own PDF viewer). For application developers, the display layer is the contract, and the API has been remarkably stable across major versions.

The official repository example (`examples/node/getinfo.mjs`) shows the loading and page-inspection pattern that every integration builds on:

```js
import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";

const loadingTask = getDocument({ url: pdfPath });
const pdfDoc = await loadingTask.promise;

const { numPages } = pdfDoc;
const pdfPage = await pdfDoc.getPage(1);
const viewport = pdfPage.getViewport({ scale: 1.0 });

// Render the page into a canvas context
const canvas = document.getElementById("the-canvas");
const context = canvas.getContext("2d");
canvas.width = viewport.width;
canvas.height = viewport.height;
await pdfPage.render({ canvasContext: context, viewport }).promise;

// Extract text layer content for selection/search
const { items } = await pdfPage.getTextContent();

pdfPage.cleanup();
await loadingTask.destroy();
```

Two operational realities matter. First, **the worker**: PDF.js ships `pdf.worker.mjs` and your app must point `GlobalWorkerOptions.workerSrc` at it, plus serve the `cmaps/` directory for correct rendering of non-Latin scripts — the official docs note the worker is not enabled for `file://` URLs, so you need a real server. Second, **module builds**: modern pdf.js ships ESM (`pdf.mjs`/`pdf.worker.mjs`) and legacy builds for older browsers; bundlers must treat the worker as a web worker asset, not a normal import. Those two setup steps cause the majority of "blank page" bug reports.

## react-pdf: The React Way to Render

react-pdf wraps PDF.js in idiomatic React components. `file` can be a URL, base64 string, `Uint8Array` or `ArrayBuffer`, and you nest `<Page>` components inside `<Document>` — the component handles loading, errors and re-renders. From the project README, the setup is two parts: configure the worker in the **same module** where you render the components (a documented footgun — the README warns that setting it in a separate file can be overwritten by module execution order), then render:

```ts
import { Document, Page } from 'react-pdf';
import { pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

function PdfPreview({ file }: { file: string }) {
  return (
    <Document file={file}>
      <Page pageNumber={1} />
    </Document>
  );
}
```

The README's compatibility notes are the real value: in **Next.js** you must skip SSR when importing the module (both Pages and App Router have documented patterns); in **Parcel** the worker URL needs the `npm:` prefix; under **pnpm** you may need `public-hoist-pattern[]=pdfjs-dist` so the worker resolves. react-pdf is MIT, actively maintained (last push September 2026), and its maintainer also publishes the widely used react-date-picker and react-calendar family — a single-maintainer dependency, so pin versions and watch the release cadence.

## pdf-lib: Generation and Editing Without the Bloat

pdf-lib is the inverse of PDF.js: **it never renders a page**, but it creates, merges, splits and modifies PDFs with zero native dependencies, in the browser or Node, with the identical API. The official README example is the canonical "hello world" of client-side generation:

```js
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'

const pdfDoc = await PDFDocument.create()
const timesRomanFont = await pdfDoc.embedFont(StandardFonts.TimesRoman)
const page = pdfDoc.addPage()
const { width, height } = page.getSize()

const fontSize = 30
page.drawText('Creating PDFs in JavaScript is awesome!', {
  x: 50,
  y: height - 4 * fontSize,
  size: fontSize,
  font: timesRomanFont,
  color: rgb(0, 0.53, 0.71),
})

const pdfBytes = await pdfDoc.save()
```

Editing existing documents is equally direct: `PDFDocument.load(existingPdfBytes)`, then `getPages()`, `drawText()` with rotation, and the form API (`createTextField`, `createRadioGroup`, `createCheckBox`, `addToPage`) for filling and flattening forms client-side — a genuinely useful trick for e-signature-style flows where the server should never handle the document. The honest caveat: the repository's last push was July 2024. The library is stable, widely deployed and still receives issue attention, but do not expect feature growth — treat it as mature-and-frozen, pin the version, and keep an eye on whether the ecosystem forks it.

## Pitfalls and Integration Gotchas

1. **The worker is the #1 cause of blank viewers.** Every PDF.js-based integration (including react-pdf) needs `workerSrc` pointed at a served copy of `pdf.worker(.min).mjs`. Same-origin serving avoids both CORS and CSP issues; self-hosting the worker file is worth the few kilobytes.
2. **Bundler-specific worker handling.** Next.js, Vite, Parcel and pnpm each resolve the worker differently — react-pdf's README documents all four. Test in the actual production build, not just dev mode, because dev servers forgive worker path mistakes that prod builds do not.
3. **pdf-lib cannot render.** If your "preview after generate" feature assumes one library does both, you will generate bytes you cannot display. Pair pdf-lib output with react-pdf/PDF.js (`file` accepts `Uint8Array`, so `pdfDoc.save()` feeds directly into `<Document file={bytes} />`).
4. **pdf-lib is maintenance-slowed.** Last upstream push July 2024. It is stable, but vet any security-sensitive PDF parsing use case against the commit history before betting a compliance feature on it.
5. **Server-side generation is a different product.** Client-side PDF.js/pdf-lib cannot replace WeasyPrint or Typst for paginated HTML reports — for that, see our [server-side document generation comparison](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-pagedjs/), and if you already generate PDFs server-side with the older JavaScript generation libraries, our [PDFKit vs jsPDF vs pdfmake guide](../2026-07-21-javascript-pdf-generation-pdfkit-jspdf-pdfmake/) covers the trade-offs there.
6. **CSP and blob URLs.** If your app runs a strict Content-Security-Policy, PDF.js rendering into `blob:` URLs and worker-src directives need explicit allowances. Budget time for a CSP audit before launch.
7. **Memory on long sessions.** Rendering many pages accumulates canvas memory; call `page.cleanup()` (display layer) or unmount off-screen `<Page>` components (react-pdf) to release resources.

## Building the Full Client-Side PDF Stack

A pattern worth stealing for document-heavy apps: keep the **whole lifecycle in the browser**. Generate or fetch bytes → store as `Uint8Array` → render with react-pdf → let the user edit/fill with pdf-lib → export. The server only stores bytes; no PDF library, no worker, no native dependencies in your backend. For teams comparing client and server approaches across the stack, our [open-source PDF processing survey](../2026-05-02-stirling-pdf-vs-gotenberg-vs-ocrmypdf-self-hosted-pdf-processing-guide/) shows what the self-hosted server tools do well (OCR, batch conversion) so you can decide which jobs belong server-side after all.

## FAQ

### What is the difference between PDF.js and react-pdf?

PDF.js is Mozilla's PDF rendering engine and viewer, usable from any JavaScript environment. react-pdf is a React wrapper around PDF.js that exposes `<Document>` and `<Page>` components. Use react-pdf in React apps; use PDF.js directly everywhere else or when you need the full viewer UI.

### Can pdf-lib render or display PDFs?

No. pdf-lib only creates, modifies, merges and fills PDFs — it has no rendering engine. To display pdf-lib output, pass the `Uint8Array` from `pdfDoc.save()` to PDF.js or react-pdf.

### Is pdf-lib still maintained?

The repository's last push was July 2024. The library is stable and widely used, but feature development has effectively stopped. Pin your version and treat it as mature-and-frozen rather than actively evolving.

### Do I need a web worker for client-side PDF rendering?

PDF.js-based rendering (including react-pdf) uses a worker by default to keep parsing off the main thread, and you must configure `GlobalWorkerOptions.workerSrc` to point at the worker file. pdf-lib does not use a worker — it is synchronous pure JavaScript.

### Can I fill in PDF forms in the browser?

Yes. pdf-lib has a full form API: `createTextField`, `createRadioGroup`, `createCheckBox`, dropdowns, and `form.flatten()` to burn values into the page so they are no longer editable. PDF.js also supports AcroForm and XFA through its viewer scripting, mainly for display and interaction.

### Why is my react-pdf page blank in production but fine in development?

Almost always a worker resolution problem: the `workerSrc` URL built at runtime differs between dev and the production bundle (Next.js, Parcel and pnpm each have documented quirks — see the README notes in this guide). Check the browser console for worker load errors, and verify the worker file is actually served at the URL your bundle computed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Browser PDF in 2026: PDF.js vs react-pdf vs pdf-lib, the Full Stack Guide",
  "description": "Compare PDF.js, react-pdf and pdf-lib for browser PDF work: rendering engine vs React wrapper vs generation library, worker setup, form filling, real code samples and a use-case decision matrix.",
  "datePublished": "2026-09-09",
  "dateModified": "2026-09-09",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
