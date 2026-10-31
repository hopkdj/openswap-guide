---
title: "Prawn vs HexaPDF vs CombinePDF in 2026: Which Ruby PDF Library Should You Actually Use?"
date: "2026-11-01"
tags: ["ruby", "pdf", "libraries", "reporting", "backend"]
draft: false
description: "Prawn, HexaPDF and CombinePDF compared on real invoicing and reporting workloads: layout DSLs, AcroForm filling, encryption, digital signatures, memory behaviour and AGPL licensing risk, with working Ruby code."
---

A Ruby PDF bug rarely looks like a PDF bug. It looks like a Sidekiq worker that balloons to 1.8 GB of RSS on a 900-page statement run, or an invoice attachment that renders beautifully in Preview and as blank pages in a bank's document portal. Ruby has three mature ways to produce PDFs and they solve genuinely different problems: **Prawn** draws documents, **HexaPDF** reads and rewrites them, and **CombinePDF** stitches existing pages together.

Picking the wrong one is expensive in exactly the way that is hard to notice in development — everything works on your 3-page sample and falls over on the customer's 400-page appendix.

Here is the short answer, the code, and the licensing trap that has surprised more than one Rails team.

## TL;DR: The 10-Second Verdict

**Use Prawn for generated documents** — invoices, receipts, packing slips, anything where you control the layout from scratch. Its DSL is still the most ergonomic way to position text and tables in Ruby. **Use HexaPDF when you must open, fill, sign, encrypt or optimize an existing PDF** — it is a full object-model toolkit, not a drawing library. **Use CombinePDF when the job is literally "attach these pages together and stamp a footer"** — it is MIT licensed and does one thing without drama.

If your Rails app sends invoices: **Prawn to generate, CombinePDF to merge in the terms page.** If your app fills government or bank forms: **HexaPDF, and budget for its license.**

## How the Three Libraries Compare

| Dimension | Prawn 2.x | HexaPDF 0.9x | CombinePDF 1.x |
|---|---|---|---|
| GitHub stars | 4,825 | 1,382 | 784 |
| Last push | 2026-04-18 | 2026-10-18 | 2025-04-08 |
| License | Ruby License, GPL-2.0, GPL-3.0 | **AGPL-3.0** or commercial | MIT |
| Primary job | Generate documents via layout DSL | Read, write, modify, secure PDFs | Merge and stamp existing pages |
| Read existing PDFs | No | Yes, full object model | Yes, page level |
| AcroForm (fillable fields) | No | Yes, including appearance regeneration | No |
| Digital signatures | No | Yes (PKCS#7, timestamping hooks) | No |
| Encryption / permissions | No | Yes (AES-256, owner/user passwords) | Yes, via loaded document options |
| Compress / linearize | No | Yes (`optimize`, object streams) | No |
| Text layout DSL | Best in class | Manual canvas positioning | None (stamping only) |
| Table helper | Yes (`prawn-table`) | Manual | No |
| CJK / custom fonts | TTF/TTC embedding, AFM for core fonts | TTF/OTF/TTC, CID fonts | Stamping with built-in fonts |
| Streaming-friendly memory | Moderate (document in memory) | Good (lazy object loading) | Good for merges, whole doc in memory |
| Active maintenance | Steady, slower cadence | Very active | Low activity since 2025 |

The license row is the one that ends projects. Prawn's GPL option is easy to misread as viral for your whole app; in practice most teams rely on the Ruby License (non-copyleft) for the gem, but legal review on that is your call. HexaPDF is **AGPL-3.0**, which for a closed-source SaaS means buying a commercial license — gettalong sells one, and it is the correct route for commercial products. CombinePDF's MIT license is unambiguous.

## Decision Matrix: Pick by Use Case

| Your task | Recommended | Why |
|---|---|---|
| Monthly invoices with tables, headers, logos | **Prawn** | `table` and cursor model beat manual coordinates for structured layouts |
| Fill a bank or tax form with customer data | **HexaPDF** | Only one of the three with a real AcroForm API |
| Merge generated invoice + static terms page | **CombinePDF** | MIT, two lines of code, no layout work |
| Add page numbers or "CONFIDENTIAL" watermark to an existing PDF | **CombinePDF** | Stamping API is purpose-built |
| Digitally sign a contract PDF | **HexaPDF** | PKCS#7 signature support |
| Password-protect an export | **HexaPDF** | AES-256 encryption and permission flags |
| Shrink a 40 MB scanned PDF before emailing | **HexaPDF** | `optimize: true` plus object streams |
| Render a chart-heavy analytics report | **Prawn** (+ SVG or image embedding) | Drawing primitives, gradients, transparency groups |
| Parse text out of an inbound PDF | **HexaPDF** | Content-stream access; the others cannot read text |

## Prawn: The Layout DSL That Still Wins for Generated Documents

Prawn's model is a cursor on a page. You `text`, `move_down`, `bounding_box`, and it flows content for you. For invoices and statements, nothing in Ruby is faster to write.

```bash
gem install prawn
# prawn-table ships as a dependency of prawn, so tables work out of the box
```

```ruby
require 'prawn'
require 'prawn/table'

Prawn::Document.generate('invoice.pdf', page_size: 'A4', margin: 48) do
  text 'OpenSwap Consulting', size: 20, style: :bold
  text 'Invoice #2026-1147 — due 2026-12-01', size: 10, color: '555555'
  move_down 24

  table([['Description', 'Qty', 'Unit', 'Total'],
         ['Backend audit', '12', '$140.00', '$1,680.00'],
         ['Migration plan', '1', '$900.00', '$900.00']],
        header: true,
        width: bounds.width,
        column_widths: [260, 60, 90, 90],
        cell_style: { size: 10, padding: 8, border_color: 'DDDDDD' })

  move_down 16
  text 'Total due: $2,580.00', size: 14, style: :bold, align: :right

  number_pages 'Page <page> of <total>', at: [0, -20], size: 8, align: :right
end
```

Prawn's strengths are all layout-side: `bounding_box` for two-column sections, `repeat(:all)` for headers on every page, `group` to keep a table from splitting awkwardly, and `number_pages` for pagination. Font embedding is straightforward with `font_families.update` pointing at TTF files, which is how you ship a brand font without relying on the 14 core PDF fonts.

What Prawn cannot do is open an existing PDF and change it. It writes; it does not read. If your workflow says "take the customer's PO document and append our invoice", Prawn is the wrong first tool.

## HexaPDF: A Real PDF Object Model in Pure Ruby

HexaPDF is the closest thing Ruby has to a general PDF toolkit: a parser, a document object model, a canvas for drawing, and higher-level features — forms, signatures, encryption, optimization, PDF/A validation. It is pure Ruby with no native extensions, which makes it deployable anywhere Ruby runs.

```bash
gem install hexapdf
```

```ruby
require 'hexapdf'

doc  = HexaPDF::Document.new
page = doc.pages.add
canvas = page.canvas

canvas.font('Helvetica', size: 22, variant: :bold)
    .text('Statement — November 2026', at: [48, page.height - 60])

canvas.font('Helvetica', size: 10)
[['Backend audit', '$1,680.00'], ['Migration plan', '$900.00']].each_with_index do |(label, amount), i|
  y = page.height - 110 - (i * 18)
  canvas.text(label,  at: [48, y])
  canvas.text(amount, at: [420, y])
end

doc.write('statement.pdf', optimize: true)
```

The features that justify HexaPDF's AGPL price tag are the ones Prawn does not have at all:

```ruby
# Fill an AcroForm and flatten the result
doc  = HexaPDF::Document.open('tax-form.pdf')
form = doc.acro_form
form.field(:full_name).field_value = 'Ada Lovelace'
form.field(:tax_year).field_value = '2026'
doc.write('tax-form-filled.pdf', optimize: true)

# Encrypt with AES-256 and restrict permissions
pdf = HexaPDF::Document.open('contract.pdf')
pdf.encrypt(name: 'owner-secret', owner_password: 'owner-secret',
            user_password: 'reader-secret', algorithm: :aes, key_length: 256,
            permissions: [:print, :copy])
pdf.write('contract-protected.pdf')
```

HexaPDF also gives you `doc.pages.each` access to content streams, `doc.objects` for raw object inspection, and `HexaPDF::Document.open(...).pages[3].canvas` for appending content to an existing page — the "stamp a page I did not create" workflow that CombinePDF handles only at a coarser level.

The trade-offs: it is verbose for pure layout (you position everything by coordinate), the API surface is large enough that you will keep the documentation open for a week, and AGPL means a commercial license for closed-source distribution. For a Rails SaaS, that license is usually a few hundred dollars against weeks of engineering — cheap, but it must be a deliberate decision, not an accident discovered during due diligence.

## CombinePDF: The MIT Merge-and-Stamp Tool

CombinePDF does one job: load PDFs, concatenate their pages, optionally stamp text or images, save. It is MIT licensed, small, and depended on by countless Rails apps that needed "merge two PDFs" and did not want a toolkit.

```bash
gem install combine_pdf
```

```ruby
require 'combine_pdf'

pdf = CombinePDF.new
pdf << CombinePDF.load('invoice.pdf')
pdf << CombinePDF.load('terms-and-conditions.pdf')

# Stamp a footer on every page after merging
pdf.pages.each_with_index do |page, index|
  page.textbox "OpenSwap Ltd — page #{index + 1}",
               x: 48, y: 24, width: 400, height: 20, font_size: 8
end

# Watermark the first page only
pdf.pages.first.textbox 'PAID', x: 380, y: 420, width: 200, height: 80,
                        font_size: 48, text_align: :center, text_color: [0.75, 0, 0]

pdf.save 'invoice-with-terms.pdf'
```

CombinePDF also handles a common but awkward case well: taking pages from a scanned document and inserting an already-generated cover page, or rotating a landscape page that came out of a scanner sideways. Its `textbox` uses built-in fonts, so custom branding requires registering a TTF — check that before you promise a design team pixel-perfect stamps.

The caveat is maintenance cadence: last repository push was April 2025 and the gem's release rhythm is slow. It works, it is small, and the API is stable — but do not expect fixes for exotic malformed PDFs.

## Where Each Library Breaks: Pitfalls and Migration Traps

**Memory blowups on large batches.** All three build documents in memory. A 500-page statement with embedded images can exceed 1 GB RSS per worker. Cap batch size, process in background jobs, and stream the result to S3 rather than buffering in the controller. If you are already running Sidekiq, our [Ruby background job processor comparison](../2026-07-28-ruby-background-job-processors-sidekiq-shoryuken-faktory-sucker-punch-comparison/) covers worker memory limits in more depth.

**Missing or unembedded fonts.** The 14 core PDF fonts (Helvetica, Times, Courier and friends) are not embedded, so a document can look perfect locally and render with substituted glyphs on a customer's machine. Embed a TTF via `font_families.update` in Prawn, or register fonts in HexaPDF's `font` call. For CJK content this is mandatory, not cosmetic.

**Coordinate system confusion.** Prawn uses a top-left origin with a flowing cursor; raw PDF canvases (HexaPDF, CombinePDF textboxes) use bottom-left with absolute points. Porting layout code between them means flipping every Y value. Write a tiny helper that converts your intended top-down positions once.

**License drift in a monorepo.** HexaPDF being AGPL means a single `require 'hexapdf'` in a shared internal gem can pull the obligation into every product that depends on it. Keep PDF work in a dedicated service or gem with an explicit license note, and verify with your legal team before shipping.

**Signatures are not just "add a signature".** Signing requires a certificate chain, usually a timestamp authority, and a document byte range that must not change after signing. If your workflow signs and then appends a page, the signature invalidates. Sign last, always.

**Rebuilding instead of merging.** Teams often re-render a terms page in Prawn on every invoice just to combine it. Generating it once, storing it, and merging with CombinePDF cuts CPU dramatically at scale — and keeps the legal text byte-identical across invoices, which matters in disputes.

If you are wiring PDF generation into a larger Rails data layer, the [Ruby ORM comparison](../2026-07-30-ruby-orm-libraries-activerecord-sequel-rom-rb/) and the [Ruby JSON serialization guide](../2026-07-31-ruby-json-serialization-alba-blueprinter-ams/) cover the surrounding decisions.

## FAQ

**Can Prawn read or modify an existing PDF?**

No. Prawn is a writer only — it builds a document from scratch through its layout DSL. If you need to open a PDF, fill fields, stamp pages or extract text, use HexaPDF (full object model) or CombinePDF (page-level merge and stamp).

**Is HexaPDF's AGPL license a problem for a commercial SaaS?**

It is a problem only if you ignore it. AGPL-3.0 requires that users interacting with the software over a network can obtain the corresponding source, which for a closed-source product usually means purchasing the commercial license from the author. Many teams do exactly that; the cost is small relative to building a PDF form engine in-house. Budget for it during architecture review, not after launch.

**Which library is fastest for merging 50 PDFs?**

CombinePDF, in practice, because that is its single purpose and it does minimal object rewriting. HexaPDF can merge too (`doc.pages << other_doc.pages` semantics via imports) and will be slower but more correct on unusual files. Measure with your real documents — malformed scans are where libraries diverge.

**Can I fill an interactive form with CombinePDF?**

No. CombinePDF does not implement AcroForm field editing. Stamping text on top of a form visually "fills" it but leaves the underlying field empty, so the recipient's PDF reader will still show blank fields and validation rules will fail. Use HexaPDF's `acro_form` API when the form must remain machine-readable.

**How do I add page numbers to a document generated with Prawn?**

Use `number_pages 'Page <page> of <total>', at: [0, -20]` inside the document block; Prawn substitutes the placeholders per page. With CombinePDF, loop over `pdf.pages` after merging and call `textbox` with the index; with HexaPDF, draw on each page's canvas after the content is final.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Prawn vs HexaPDF vs CombinePDF in 2026: Which Ruby PDF Library Should You Actually Use?",
  "description": "Prawn, HexaPDF and CombinePDF compared on invoicing and reporting workloads: layout DSLs, AcroForm filling, encryption, signatures, memory behaviour and AGPL licensing risk.",
  "datePublished": "2026-11-01",
  "dateModified": "2026-11-01",
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
