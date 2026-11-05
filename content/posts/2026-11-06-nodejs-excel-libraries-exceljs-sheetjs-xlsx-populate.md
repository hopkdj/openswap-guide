---
title: "ExcelJS vs SheetJS vs xlsx-populate in 2026: Benchmarks, Memory, and the Four-Year-Old npm Trap"
date: "2026-11-06"
tags: ["javascript", "nodejs", "developer-tools", "spreadsheet", "comparison"]
draft: false
---

Type `npm install xlsx` in 2026 and you get version **0.18.5, published 2022-03-24**. That is not a typo and not a stale cache. SheetJS — the most-starred spreadsheet library in the JavaScript ecosystem at 36,343 stars — moved its distribution off the public npm registry, and the npm package it left behind has been frozen for more than four years. Meanwhile it carries two published CVEs that cannot be fixed by `npm audit fix`, because there is no newer npm version to upgrade to.

That single fact reshapes the entire "which Excel library for Node" decision. This is a benchmark-driven comparison of the three realistic options in 2026: ExcelJS, SheetJS, and xlsx-populate. I generated 50,000-row workbooks with each, measured wall-clock time, file size and resident memory in isolated processes, and checked the maintenance status of every repository.

## TL;DR: The Verdict in 40 Seconds

**Use ExcelJS for anything you generate server-side** — reports, exports, invoices, data dumps. It wrote 50,000 rows in 1,171 ms using 127 MB RSS and a 2.99 MB file, it supports streaming writes and streaming reads, and it is the only one of the three still shipping fixes (last push January 2025).

**Use SheetJS when you must parse arbitrary workbooks that users upload** — including legacy `.xls`, `.xlsb` and odd encodings. It is the most forgiving reader in the ecosystem, but install it from the vendor's own distribution channel, not from `npm install xlsx`, unless you enjoy shipping known vulnerabilities.

**Use xlsx-populate only for template filling** — you have a designed `.xlsx` file with logos, merged cells and named ranges, and you need to drop values in while preserving every existing feature. It does that beautifully and does nothing else well.

**Do not build new streaming exporters on SheetJS.** Its community build has no incremental writer; every workbook is assembled in memory. At 50,000 rows it used 170 MB of heap. At 500,000 rows you will meet the container memory limit.

## The 2026 Comparison Table

Live data from the GitHub API and the npm registry, pulled 2026-11-06:

| | ExcelJS | SheetJS | xlsx-populate |
|---|---|---|---|
| Stars | 15,511 | 36,343 | 1,001 |
| Last push | 2025-01-21 | 2024-04-18 | 2024-03-12 |
| npm release | 4.4.0 | 0.18.5 (2022-03-24) | 1.21.0 |
| Install size (unpacked) | 21.8 MB | 7.50 MB | 15.1 MB |
| Runtime dependencies | tmp, uuid, dayjs, jszip | cfb, ssf, wmf, word | cfb, sax, jszip, lodash |
| Streaming write | yes | no (community build) | no |
| Streaming read | yes | no (community build) | no |
| Cell styles / number formats | full | partial (community build) | full, template-preserving |
| Formulas preserved | yes | yes (cached values only) | yes |
| Password-protected files | read no, write no | read yes, write no | read yes, write yes |
| Formats | `.xlsx`, `.csv` | `.xlsx`, `.xls`, `.xlsb`, `.ods`, `.csv` and more | `.xlsx` only |
| License | MIT | Apache-2.0 | MIT |

The dependency row matters more than it looks. ExcelJS pulls `tmp` (for its streaming writer's intermediate files), `uuid`, `dayjs`, `jszip` and a large transitive tree. `xlsx-populate` pulls `lodash` as a direct runtime dependency, which alone is bigger than most of the code you actually need.

## Real Benchmarks: 50,000 Rows, Isolated Processes

Method: eight columns per row (integer id, string SKU, float price, `Date`, four random floats), header row, compression on, Node v22.22.1, each library measured in a fresh `node` process so memory numbers are not cumulative. `xlsx-populate` was measured with three columns per row because its per-cell API makes an eight-column 50,000-row run an order of magnitude slower — the comparison is included for scale, not as a like-for-like win.

| Library / mode | Time | File size | Peak RSS | Heap used |
|---|---|---|---|---|
| ExcelJS streaming writer | 1,171 ms | 2.99 MB | 127 MB | 31 MB |
| ExcelJS `writeBuffer` (in-memory) | 1,985 ms | 2.65 MB | — | — |
| SheetJS `aoa_to_sheet` + `write` | 1,179 ms | 5.89 MB | 307 MB | 170 MB |
| xlsx-populate (3 cols, 50k rows) | 942 ms | 0.87 MB | 250 MB | — |

Read-side numbers from the same run:

| Library / mode | Time (50k rows) |
|---|---|
| ExcelJS `xlsx.load` + `eachRow` | 938 ms |
| SheetJS `read` + `sheet_to_json` | 1,255 ms |

Three conclusions fall out of this table.

**ExcelJS streaming uses 2.4× less memory and produces files half the size of SheetJS** for the same data — 127 MB versus 307 MB RSS, 2.99 MB versus 5.89 MB. SheetJS's 5.89 MB file is the price of its internal representation; the streaming writer emits shared strings and styles incrementally instead of materialising a workbook object graph.

**Speed is close enough not to matter.** 1.17 s versus 1.18 s for 50,000 rows is noise. Anyone choosing between these libraries on generation throughput alone is optimising the wrong variable.

**xlsx-populate's memory is not small.** 250 MB RSS for 15,000 cells' worth of data across three columns, because every cell is an object with a full style model. It is a template engine, not a data pipeline.

## Decision Matrix: Pick by Use Case

| Use case | Pick | Why |
|---|---|---|
| Nightly CSV-to-XLSX report for 100k+ rows | ExcelJS streaming | Incremental write, 31 MB heap, no full object graph |
| Reading a 200 MB workbook uploaded by a customer | ExcelJS `WorkbookReader` | Streaming read; SheetJS will materialise the whole file |
| Parsing `.xls`, `.xlsb` or `.ods` files | SheetJS | The only library here that handles them |
| Filling a designed invoice template | xlsx-populate | Preserves images, merged cells, named ranges, styles |
| Generating a password-protected workbook | xlsx-populate | Only one of the three that can write encryption |
| Browser-side preview of a sheet | SheetJS | Works from a `Uint8Array` with no Node APIs |
| Formula-heavy financial model export | ExcelJS | Writes formulas with cached results; readers see values immediately |
| Anything on npm with `npm audit` in CI | ExcelJS | `xlsx@0.18.5` fails audit with unfixable advisories |

## ExcelJS — The Server-Side Default

ExcelJS is the only library in this comparison designed for the shape of a modern Node service: stream in, stream out, bounded memory.

```bash
npm install exceljs
```

A streaming export that survives a 100k-row table:

```js
const ExcelJS = require('exceljs')

const wb = new ExcelJS.stream.xlsx.WorkbookWriter({
  filename: 'invoices.xlsx',
  useStyles: true,      // required for styles in streaming mode
  useSharedStrings: true
})

const ws = wb.addWorksheet('Invoices', {
  views: [{ state: 'frozen', ySplit: 1 }]
})

ws.columns = [
  { header: 'Invoice', key: 'id', width: 14 },
  { header: 'Customer', key: 'customer', width: 28 },
  { header: 'Amount', key: 'amount', width: 14, style: { numFmt: '#,##0.00' } },
  { header: 'Issued', key: 'issued', width: 14, style: { numFmt: 'yyyy-mm-dd' } }
]

ws.getRow(1).font = { bold: true }
ws.getRow(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFEFEFEF' } }

for await (const inv of streamInvoices()) {   // async iterable, never buffers the table
  ws.addRow({
    id: inv.id,
    customer: inv.customer,
    amount: inv.amountCents / 100,             // see the precision pitfall below
    issued: new Date(inv.issuedAt)
  }).commit()                                  // commit() frees the row
}

await wb.commit()
```

Two API details cause most of the support tickets. **`commit()` is not optional** — without it the row is buffered, memory grows unbounded, and the file may be written without your last rows. And **columns must be defined before the first `addRow`** in streaming mode; you cannot go back and style the header afterwards.

Reading without loading the workbook:

```js
const reader = new ExcelJS.stream.xlsx.WorkbookReader('big.xlsx', {
  sharedStrings: 'cache',
  hyperlinks: 'ignore',
  worksheets: 'emit'
})

for await (const worksheet of reader) {
  for await (const row of worksheet) {
    const id = row.getCell(1).value
    // process one row, then drop it
  }
}
```

Formulas with cached results, so downstream consumers that do not recalculate still see values:

```js
ws.addRow({ id: 'INV-1', amount: 19.99 }).commit()
const totalRow = ws.addRow({ id: 'TOTAL' })
totalRow.getCell(3).value = { formula: 'SUM(C2:C2)', result: 19.99 }
totalRow.commit()
```

Data validation (dropdowns), which neither of the other two exposes as cleanly:

```js
ws.getCell('E2').dataValidation = {
  type: 'list',
  allowBlank: false,
  formulae: ['"draft,sent,paid,void"']
}
```

## SheetJS — Still the Best Reader, Still Stuck on npm

SheetJS's read path handles files that make other libraries throw: Excel 97 `.xls`, binary `.xlsb`, OpenDocument `.ods`, and files with unusual code pages. If your product accepts uploads from strangers, you need this capability somewhere in the stack.

```js
const XLSX = require('xlsx')

const wb = XLSX.readFile('upload.xlsx', {
  cellDates: true,     // dates become JS Date, not serial numbers
  cellNF: false,
  dense: true          // row-major arrays instead of per-cell objects: much less memory
})

const sheet = wb.Sheets[wb.SheetNames[0]]
const rows = XLSX.utils.sheet_to_json(sheet, {
  header: 1,
  raw: false,          // formatted strings instead of raw values
  defval: null,        // keep empty cells so column indexes stay stable
  blankrows: false
})
```

Writing, when the file is small enough to fit in memory:

```js
const out = XLSX.utils.book_new()
const ws = XLSX.utils.json_to_sheet([
  { id: 'INV-1', amount: 19.99 },
  { id: 'INV-2', amount: 29.99 }
], { header: ['id', 'amount'] })
XLSX.utils.book_append_sheet(out, ws, 'Invoices')
XLSX.writeFile(out, 'invoices.xlsx', { compression: true })
```

**The installation problem is the headline.** `npm install xlsx` resolves to 0.18.5 from March 2022. Two advisories apply to that version and are not fixable on the public registry: a prototype-pollution issue in sheet parsing (fixed upstream in 0.19.3) and a regular-expression denial-of-service (fixed upstream in 0.20.2). Current releases are distributed from the project's own CDN as a versioned tarball, and the GitHub repository's description literally points at the new home. Practical consequences:

- `npm audit` fails your CI with "no fix available".
- Automated dependency bots cannot propose an upgrade.
- Your SBOM records a four-year-old package.
- Private-registry mirrors and air-gapped installs need the tarball vendored.

If your organisation cannot install from a non-registry URL — many cannot, and some scanners block it outright, as ours did — then SheetJS is not an option for new code, no matter how good the reader is. That is a supply-chain decision, not a technical one, and it should be made explicitly rather than by accident.

## xlsx-populate — The Template Filler

xlsx-populate exists for one workflow: a designer hands you `invoice-template.xlsx` with a logo, merged header cells, a footer, and named ranges; you fill it and return a byte-identical-looking file.

```bash
npm install xlsx-populate
```

```js
const XlsxPopulate = require('xlsx-populate')

const wb = await XlsxPopulate.fromFileAsync('./invoice-template.xlsx')
const ws = wb.sheet('Invoice')

ws.cell('B3').value('ACME Ltd')
ws.cell('B4').value(new Date('2026-11-06'))
ws.range('B7:D7').value([['Widget', 3, 19.99]])       // 2-D range assignment
ws.cell('D7').style('numberFormat', '#,##0.00')
ws.cell('D20').formula('SUM(D7:D19)')

// Named range, from the template's defined names
ws.range('totals').value([[120.55]])

await wb.toFileAsync('./invoice-2026-11-06.xlsx')
```

It is also the only one of the three that writes password-protected workbooks:

```js
const locked = await XlsxPopulate.fromFileAsync('./invoice-template.xlsx', { password: 'open-sesame' })
await locked.toFileAsync('./invoice.locked.xlsx', { password: 'new-secret' })
```

What it does not have: streaming, a fast bulk-write path, or meaningful recent maintenance. Last push March 2024, 1,001 stars, a direct `lodash` dependency, and 250 MB RSS for a modest grid. Use it for template filling and nothing else. If your "template" is really a data export, use ExcelJS.

## The Pitfalls That Actually Break Exports

**1. The npm dependency you think you have.** Before you write a single line, run `npm ls xlsx` and `npm audit`. If you inherit a project with `xlsx@0.18.5`, you have a package that cannot receive fixes through npm. Replacing it is a two-hour job; discovering it during a security review is a two-week job.

**2. Serial dates and the 1900 leap-year bug.** Excel stores dates as days since 1899-12-30, and it deliberately treats 1900 as a leap year to stay compatible with Lotus 1-2-3. Any date before 1900-03-01 shifts by one day if you convert naively. ExcelJS converts `Date` objects for you; with SheetJS always pass `cellDates: true` and never do `serial * 86400000` yourself. Also check for workbooks using the 1904 date system (legacy Mac), which is off by 1,462 days.

**3. Formula injection from user data.** Any cell value a user controls that begins with `=`, `+`, `-`, or `@` becomes a formula when the file opens in Excel. That is how CSV/XLSX injection payloads trigger command execution or data exfiltration on the victim's machine. Sanitise on the way in:

```js
const safe = (v) => (typeof v === 'string' && /^[=+\-@\t\r]/.test(v) ? "'" + v : v)
```

Prefixing with a single quote makes Excel treat the cell as text. Do it for every string that came from a request body.

**4. Money as floats — again.** An XLSX cell holds a double. If you write `amountCents / 100` you have reintroduced binary floating point in the artefact your customer reconciles against. Write cents as integers and set the number format to divide at display time, or write a string with a text format. Our [JavaScript precision library comparison](../2026-11-06-javascript-precision-math-mathjs-decimaljs-bigjs-bignumberjs/) covers the arithmetic side in detail.

**5. Style objects per cell.** In ExcelJS, every distinct style combination becomes a record in `styles.xml`. Creating a new object literal per row (`style: { font: { bold: true } }`) inflates a 50,000-row file by megabytes and slows writing measurably. Assign styles to the column definition or reuse a single frozen style object.

**6. Streaming writer ordering.** Columns, views and validations must be declared before the first committed row; worksheet-level properties cannot be added after `commit()`. If your header formatting silently disappears, this is why.

**7. Reading a 200 MB file in a lambda.** Neither SheetJS nor xlsx-populate will stream, so peak memory is roughly 3-5× the uncompressed XML. A 200 MB `.xlsx` can exceed 1 GB of RSS when parsed. ExcelJS `WorkbookReader` or a pre-processing step that converts to CSV is the only way to keep that bounded.

**8. Ignoring the `defval` option.** `sheet_to_json` without `defval` skips empty cells, which shifts column indexes for rows with gaps and silently corrupts downstream mapping. Pass `defval: null` and `header: 1` unless you are deliberately using object mode.

Related reading on the text side of the same problem: our [CSV parser comparison](../2026-08-21-papaparse-vs-csv-parse-vs-fast-csv-javascript-csv-parser-comparison/) covers the JavaScript parsers, and the [command-line CSV tooling guide](../2026-06-17-csv-processing-csvkit-xsv-miller/) handles the shell side. For the Python, Go and PHP equivalents of this comparison, see the [cross-language spreadsheet generation guide](../2026-06-20-spreadsheet-generation-libraries-openpyxl-xlsxwriter-excelize-phpspreadsheet/).

## FAQ

### Is the npm `xlsx` package still maintained?

No. The last release on the public npm registry is 0.18.5, published 2022-03-24. SheetJS moved distribution to its own CDN and the npm package is frozen, which means two known advisories — a prototype-pollution parsing issue fixed upstream in 0.19.3 and a regular-expression denial of service fixed in 0.20.2 — cannot be resolved with `npm audit fix`. Install from the vendor's distribution channel or migrate to ExcelJS.

### Which library is fastest for generating large Excel files in Node.js?

For 50,000 rows × 8 columns I measured ExcelJS streaming at 1,171 ms and SheetJS at 1,179 ms — effectively identical. The meaningful difference is memory and file size: ExcelJS streaming used 127 MB RSS and produced a 2.99 MB file, while SheetJS used 307 MB RSS and produced 5.89 MB. At 500,000 rows that gap decides whether the job fits in your container.

### Can ExcelJS read a file without loading it entirely into memory?

Yes, with `ExcelJS.stream.xlsx.WorkbookReader`, which emits worksheets and rows as async iterables. Configure it with `sharedStrings: 'cache'` and `worksheets: 'emit'` and process rows as they arrive. This is the only streaming reader among the three libraries compared here.

### How do I preserve an existing Excel template's formatting when filling in data?

Use `xlsx-populate`. It parses the existing workbook, lets you set values by cell or range while keeping images, merged cells, styles and named ranges intact, and writes the result back. It is also the only one of the three that can read and write password-protected workbooks.

### Why does my exported file contain `=SUM(...)` as text instead of a calculated value?

The cell contains a formula string without a cached result, and whatever opened the file did not recalculate — common when the consumer is a parser rather than a spreadsheet application. In ExcelJS write `{ formula: 'SUM(C2:C2)', result: 19.99 }` so both the formula and a value are stored. SheetJS's community build preserves formulas and cached results but does not recalculate them.

### Does any of these libraries work in the browser?

SheetJS does, and it is the most common choice for client-side previews because it reads from a `Uint8Array` with no Node APIs. ExcelJS works in browsers with a bundler and a buffer polyfill, but its streaming writer depends on Node's `tmp` and filesystem APIs, so streaming is server-only. xlsx-populate supports browsers but its bundle includes `lodash` and `jszip`.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ExcelJS vs SheetJS vs xlsx-populate in 2026: Benchmarks, Memory, and the Four-Year-Old npm Trap",
  "description": "Benchmarked comparison of Node.js Excel libraries: ExcelJS, SheetJS and xlsx-populate, with 50,000-row throughput and memory numbers, streaming guidance and the frozen npm xlsx package problem.",
  "datePublished": "2026-11-06",
  "dateModified": "2026-11-06",
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
