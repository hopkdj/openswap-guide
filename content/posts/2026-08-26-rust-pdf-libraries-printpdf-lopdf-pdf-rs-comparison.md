---
title: "Rust PDF Libraries in 2026: printpdf vs lopdf vs pdf-rs — Which One Should You Actually Use?"
date: "2026-08-26"
tags: ["rust", "pdf", "pdf-generation", "library-comparison", "rust-libraries"]
draft: false
cover: "/img/screenshots/printpdf-cover.png"
---

Generating or manipulating PDFs from Rust has never been as comfortable as it is in Python or Java, and that gap costs teams real hours every month. The three libraries that actually matter — **printpdf**, **lopdf**, and **pdf-rs** — take completely different approaches to the same format, and picking the wrong one means fighting raw PDF operators or hitting experimental write paths at the worst moment. All three are MIT-licensed and actively maintained, so the decision comes down to one question: what do you want to do with the document?

## TL;DR — Quick Verdict

**If you are generating new documents** — invoices, reports, certificates — use **printpdf**; its op-based API is the closest Rust gets to a friendly document builder, and it even compiles to WASM. **If you are merging, splitting, or editing existing PDFs** — use **lopdf**; it is the most capable object-level manipulator and the only one with first-class support for encrypted files and object streams. **If you are parsing and inspecting PDFs** — use **pdf-rs**; its reader is battle-tested, but its write path is still marked experimental, so do not build a generator on it.

## At a Glance — The Comparison Table

All stats fetched live from GitHub on 2026-08-26.

| Criterion | printpdf | lopdf | pdf-rs |
|---|---|---|---|
| GitHub stars | 1,110 | 2,236 | 1,691 |
| Last push | 2026-08-17 | 2026-08-24 | 2026-07-18 |
| License | MIT | MIT | MIT |
| Abstraction level | High-level ops (lines, text, images) | Object/stream level (PDF spec terms) | Reader-first, low-level |
| Create new documents | ✅ Great | ✅ Possible, verbose | ⚠️ Experimental |
| Modify existing PDFs | ⚠️ Limited | ✅ Excellent (merge, decrypt, replace text) | ✅ Read/alter, write experimental |
| Text extraction | ⚠️ Experimental | ✅ Via content parsing | ✅ Via `text` example |
| Encryption support | ❌ Not supported | ✅ Decryption + object streams | ❌ |
| WASM support | ✅ Official demo (wasm32) | ✅ Feature flag (`wasm_js`) | ❌ |
| Rust edition requirement | Stable (1.60+) | Rust 1.85+ (2024 edition) | Stable |
| Best for | Generating new docs | Manipulating existing docs | Reading/inspecting docs |

## Use-Case Decision Matrix

| Use case | Recommended tool | Why |
|---|---|---|
| Generate invoices/reports from scratch in Rust | **printpdf** | Clean `Op`-based API, `Mm`/`Pt` units, font embedding, SVG support |
| Merge 20 PDFs into one deliverable | **lopdf** | Dedicated merge example, object-level control, no rendering needed |
| Replace a string in a legacy PDF (e.g., price updates) | **lopdf** | One call: `doc.replace_text(page, from, to, None)` |
| Extract text/metadata from PDFs at scale | **pdf-rs** | Reader is the most mature; `cargo run --example text` gives you a head start |
| Render PDF pages to images in a Rust web app | **printpdf** | PDF→SVG→`resvg` pipeline documented; WASM demo runs in the browser |
| Parse PDFs on embedded/no-std-ish targets | **pdf-rs** | Minimal dependency footprint for the read path |

## printpdf — The High-Level Document Builder

printpdf describes itself as "a Rust library for creating, reading, writing and rendering PDF documents," and the *creating* part is where it shines. Instead of manipulating PDF dictionaries, you build a document from `Op` values — draw lines, polygons, and bezier curves, set CMYK or RGB colors, embed TrueType fonts with Unicode support, and even embed SVG content via the `svg2pdf` crate. The official README's basic example shows how minimal a valid document can be:

```rust
use printpdf::*;

fn main() {
    let mut doc = PdfDocument::new("My first PDF");
    let page1_contents = vec![Op::Marker { id: "debugging-marker".to_string() }];
    let page1 = PdfPage::new(Mm(210.0), Mm(297.0), page1_contents);
    let mut warnings = Vec::new();
    let pdf_bytes: Vec<u8> = doc
        .with_pages(vec![page1])
        .save(&PdfSaveOptions::default(), &mut warnings);
}
```

Two details are worth noting. First, units are physical (`Mm`, `Pt`), so an A4 page is `Mm(210.0) x Mm(297.0)` and you never guess at pixel math. Second, printpdf auto-subsets embedded fonts to keep file sizes small — a feature you normally only get from commercial generators. The library also supports bookmarks, link annotations, layers, and advanced typography (character/word scaling, superscript, subscript).

The experimental features matter for one specific audience: **WASM**. The project ships a live wasm32 demo on its site, and if you want PDF generation in the browser without a server, printpdf is the only one of the three with a proven browser path. Experimental text extraction (page→SVG, then render via `resvg`) is a workable route for thumbnails.

**What printpdf will not do**: gradients, patterns, file attachments, embedded JavaScript, or PDF-standard conformance checking. And the `from_html`/`html` feature is explicitly "still evolving" — basic tables, page breaks, headers/footers work, but do not expect a full HTML engine.

## lopdf — The Object-Level Manipulator

lopdf ("A Rust library for PDF document manipulation") is the workhorse for anyone who needs to *change* existing PDFs. Its API is written in PDF-spec vocabulary — `Document`, `Object`, `Stream`, `dictionary!` — which makes it intimidating at first and extremely powerful once you accept the model. Under the hood everything stays in memory as high-level objects until you serialize, which is why operations like merge and decrypt are so straightforward.

The README's modify example is the one to memorize:

```rust
use lopdf::Document;

let mut doc = Document::load("assets/example.pdf").unwrap();
doc.version = "1.4".to_string();
doc.replace_text(1, "Hello World!", "Modified text!", None);
doc.save("modified.pdf").unwrap();
```

That is a real, common workflow — loading a template, swapping placeholder text, saving — in five lines. Beyond text replacement, lopdf can merge documents (there is a full worked merge example), decrypt encrypted PDFs, embed raster images (`embed_image` feature) and TrueType fonts (`font_embedding`, via `skrifa`), and save using modern object streams.

**The catch is the learning curve and the toolchain floor.** Creating a document from scratch means assembling dictionaries by hand and issuing raw content operators (`BT`, `Tf`, `Td`, `Tj`, `ET`) — the README's create example is ~80 lines for "Hello World!". And since the 2024-edition rewrite, **lopdf requires Rust 1.85 or newer**; older CI images will fail. One pleasant surprise: the crate's date handling is pluggable — `chrono` (default), `jiff`, `time`, or none at all — which keeps dependencies honest. Its FAQ even explains why the library keeps everything in memory: serialization is all-or-nothing by design.

## pdf-rs — The Reader-First Library

pdf-rs (the `pdf` crate, repo `pdf-rs/pdf`) describes itself simply: "Read, alter and write PDF files." The README is candid in a way that should shape your decision: **"Modifying and writing PDFs is still experimental."** For reading, parsing, and inspecting, pdf-rs is mature and widely used; for generating documents, it is not your tool.

The project is a Cargo workspace where the default member is the `pdf` library, and the companion crates are where the real value shows:

```bash
# Run the built-in examples against any PDF
cargo run --example content -- <file.pdf>   # dump content streams
cargo run --example text -- <file.pdf>      # extract text
cargo run --example metadata -- <file.pdf>  # inspect metadata
cargo run --example read -- <file.pdf>      # low-level object dump
```

The ecosystem around it is genuinely useful: `pdf_render` renders pages via Servo's Pathfinder renderer (with a minimal viewer), and `inspect-prim` visualizes a PDF as an interactive hierarchy of primitives — a debugging tool you will not find anywhere else. If your project is a PDF *parser* (compliance checks, redaction analysis, document intelligence), pdf-rs gives you the strongest read path of the three and a clean way to inspect what other tools produce.

**Where it hurts**: the write path. Because writing is still experimental, you should treat pdf-rs as read-only in production and re-verify any altered output in a viewer before shipping. There is also no high-level text-layout API — building a page from scratch means working close to the content-stream level, similar to lopdf but with fewer conveniences.

## Pitfalls and Migration Notes

- **printpdf's HTML-to-PDF is not a substitute for a layout engine.** The `html` feature handles basic tables and page breaks but will silently produce wrong output on complex CSS. For pixel-exact results, position elements manually with ops — the README says exactly this.
- **PDF coordinates have Y = 0 at the bottom.** Every new Rust PDF developer trips on this. In lopdf's create example, "600" places text near the top of the page precisely because of this inverted axis.
- **Unicode requires embedded fonts.** PDF core fonts (Helvetica, Times, Courier) only carry Windows-ANSI encoding. Any CJK or emoji content requires an embedded TrueType/OpenType font — printpdf does this automatically, lopdf needs the `font_embedding` feature, and pdf-rs does not help you here.
- **Check Rust version requirements before adopting lopdf.** Rust 1.85+ is a hard floor. If your deployment targets an older toolchain, printpdf or pdf-rs is the safer dependency.
- **Object streams change file sizes dramatically.** lopdf's modern-format saving reduces PDF size by keeping objects compressed in streams — great for storage, but some legacy consumers choke on PDF 1.5+ object streams. Test in the actual viewer your users open.
- **Don't mix abstraction levels in one codebase.** Teams that start with lopdf for "power" and printpdf for "speed" end up with two document models. Pick one primary library per service; the Java world learned this lesson the hard way, as our [Java PDF library comparison](../2026-08-26-java-pdf-libraries-pdfbox-openpdf-itext-comparison/) shows.
- **For web services, consider who renders.** If your API only needs to produce downloadable PDFs, any of the three works. If you also need server-side thumbnails, printpdf's PDF→SVG→`resvg` pipeline avoids adding a browser dependency — a decision we analyze in detail in our [self-hosted PDF generation tools comparison](../2026-06-25-self-hosted-pdf-document-generation-weasyprint-wkhtmltopdf-typst-pagedjs/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust PDF Libraries in 2026: printpdf vs lopdf vs pdf-rs — Which One Should You Actually Use?",
  "description": "Deep comparison of the three actively maintained Rust PDF libraries — printpdf, lopdf, and pdf-rs — covering abstraction levels, real code examples, GitHub stats, pitfalls, and a use-case decision matrix.",
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

**Q: Is there a pure-Rust way to convert HTML to PDF?**
A: printpdf's `html` feature (gated behind the `html` feature flag) converts basic HTML layouts — tables, page breaks, headers/footers — but it is explicitly experimental and not pixel-exact. For complex HTML-to-PDF, most Rust teams shell out to headless Chromium, Playwright, or WeasyPrint; see our [screenshot and PDF generation API comparison](../self-hosted-screenshot-pdf-generation-apis-gotenberg-playwright-puppeteer-guide-2026/) for the self-hosted options.

**Q: Which Rust PDF library has the most stars?**
A: lopdf leads with 2,236 GitHub stars, followed by pdf-rs at 1,691 and printpdf at 1,110 (all figures as of 2026-08-26). All three are actively maintained, with lopdf pushing most recently (2026-08-24).

**Q: Can I merge multiple PDFs with these libraries?**
A: Yes — lopdf has a dedicated, fully worked merge example in its README and is the strongest choice for merging, splitting, and page reordering. printpdf and pdf-rs focus on generation and parsing respectively and are not the right tools for document surgery.

**Q: Do these libraries support encrypted PDFs?**
A: lopdf supports decryption, including working with encrypted files via its `nom_parser`-based features, and its README contains an explicit example for encrypted documents. printpdf does not support encryption, and pdf-rs's README does not list it as a capability.

**Q: Can I generate PDFs in the browser with Rust (WASM)?**
A: printpdf has an official wasm32 demo and documented browser usage, making it the default choice for client-side generation. lopdf offers a `wasm_js` feature flag for encryption-related randomness on wasm targets, but it is not a browser-first workflow.

**Q: What is the minimum supported Rust version?**
A: lopdf requires Rust 1.85 or later (2024 edition, object-stream support). printpdf and pdf-rs work on stable toolchains without a hard floor — check their respective `rust-version` fields in Cargo.toml for your exact configuration.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
