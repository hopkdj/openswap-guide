---
title: ".NET Excel Libraries in 2026: ClosedXML vs NPOI vs EPPlus"
date: "2026-09-09"
tags: ["dotnet", "csharp", "excel", "spreadsheet", "library"]
draft: false
cover: "/img/screenshots/closedxml-excel-cover.jpg"
---

Nothing kills a .NET backend project faster than discovering, three sprints in, that your "free forever" Excel library is neither free for your business nor capable of the pivot table your customer just asked for. Excel automation looks like a solved problem — until legal review reads your dependencies and finance needs a formula engine.

Three libraries dominate the .NET ecosystem in 2026: **ClosedXML (5,704 stars)**, **NPOI (6,199 stars)** and **EPPlus (2,035 stars)**. All three write real `.xlsx` files, and all three have a licensing story you must understand before you write a single `using` statement — two of them changed their terms in ways that still surprise teams today.

## TL;DR: Quick Verdict

**If you are a business writing modern `.xlsx` files and want the least code, MIT licensing and zero legal review, choose ClosedXML.** **If you must read legacy `.xls` files, need POI-compatible APIs, or want streaming writes for huge exports, choose NPOI** — and read its revenue-based fee EULA first. **If you need serious Excel machinery — formula calculation, pivot tables, charts, VBA — EPPlus is the most capable library, but the free tier is strictly non-commercial**; budget for a commercial license or pick ClosedXML plus a separate calculation strategy.

## Why Excel Libraries Are a Legal Minefield in 2026

The .NET Excel space went through a licensing upheaval starting in 2020 that many tutorials still ignore. EPPlus, once LGPL, moved to the **Polyform Noncommercial license** at version 5 — free for personal and non-commercial use, paid for commercial use. Then, in 2025, NPOI introduced an **EULA on binary releases since 2.8.0** requiring a monthly maintenance fee from organizations that generate revenue from the library, while remaining free for startups, freelancers and hobbyists under the project's published thresholds. Only ClosedXML has stayed plain MIT. This means "which library is best" is now inseparable from "who is paying for it" — the exact scenario that makes procurement reject a pull request months after the prototype.

## Feature Comparison at a Glance

| | **ClosedXML** | **NPOI** | **EPPlus** |
|---|---|---|---|
| GitHub stars | 5,704 | 6,199 | 2,035 |
| Last push | 2026-09-04 | 2026-09-01 | 2026-09-08 |
| License | MIT | Apache-2.0 + fee EULA (since 2.8.0) | Polyform Noncommercial / commercial |
| File formats | .xlsx, .xlsm | .xls (HSSF), .xlsx (XSSF), streaming (SXSSF) | .xlsx, .xlsm |
| API style | High-level, Excel-object model (`XLWorkbook`) | Apache POI port (`IWorkbook`/`ISheet`/`IRow`) | High-level (`ExcelPackage`) |
| Formula calculation | No (Excel computes on open) | Formula evaluator available | Full calculation engine (`Calculate()`) |
| Pivot tables | Yes | Partial | Yes |
| Charts | Yes | Basic | Yes (rich) |
| VBA / macros | Read-only | Limited | Yes (add/read) |
| NuGet downloads | Very high | Very high | High |

## Use Case → Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Business app writing modern .xlsx, want clean code + no license review | **ClosedXML** | MIT, intuitive API, active development; just don't expect server-side formula calculation |
| Legacy .xls (Excel 97-2003) ingestion | **NPOI** | HSSF is the only serious .xls reader in .NET; the wiki's format table makes the limits explicit |
| Exporting 500k rows without OOM | **NPOI (SXSSF)** | Streaming workbook keeps memory flat; ClosedXML and EPPlus load documents into memory |
| Server-side formulas, pivot-heavy financial reports | **EPPlus (commercial license)** | The calc engine and pivot/chart depth have no free equivalent |
| Hobby, OSS or internal non-commercial tooling | **EPPlus free tier** or ClosedXML | Polyform non-commercial covers non-commercial use; ClosedXML is MIT for everything |

## ClosedXML: The MIT Workhorse

ClosedXML wraps the Open XML SDK behind an object model that reads like the Excel UI: `XLWorkbook`, `Worksheets`, `Cell`, `Range`, with fluent styling and a genuinely pleasant API. It is `.xlsx`/`.xlsm` only — there is no legacy `.xls` support by design. The repository's own examples show how compact real work is; this sparkline snippet from the official sample suite demonstrates both the API style and a feature many teams do not expect from a free library:

```csharp
using ClosedXML.Excel;

var workbook = new XLWorkbook();
var ws1 = workbook.AddWorksheet("Linear");

ws1.Range("A2:A4").Merge().SetValue("Linear, Colorful 1, All markers, SameForAll scale");
ws1.SparklineGroups.Add("B2:B4", "C2:P4")
    .SetStyle(XLSparklineTheme.Colorful1)
    .SetShowMarkers(XLSparklineMarkers.All).VerticalAxis
    .SetMaxAxisType(XLSparklineAxisMinMax.SameForAll)
    .SetMinAxisType(XLSparklineAxisMinMax.SameForAll);

ws1.Range("A5:A7").Merge().SetValue("Linear, Colorful 2, First+Last+High+Low, Automatic scale");
ws1.SparklineGroups.Add("B5:B7", "C5:P7")
    .SetStyle(XLSparklineTheme.Colorful2)
    .SetShowMarkers(XLSparklineMarkers.FirstPoint | XLSparklineMarkers.LastPoint
        | XLSparklineMarkers.HighPoint | XLSparklineMarkers.LowPoint);
```

The team is active (last push September 2026) and the issue tracker moves fast. The price you pay: **ClosedXML has no calculation engine**. It writes formulas and cached values into the file, but it does not compute results — Excel or LibreOffice calculates them when the file is opened. If your pipeline needs to generate a file and immediately read back computed totals without Excel in between, ClosedXML alone will not do it.

## NPOI: The POI Port That Refuses to Die

NPOI is the .NET port of Apache POI, and it brings POI's entire mental model: a `Workbook` (or the interfaces `IWorkbook`/`ISheet`/`IRow`/`ICell`) with three concrete implementations that the official getting-started wiki contrasts directly:

| | HSSFWorkbook | XSSFWorkbook | SXSSFWorkbook |
|---|---|---|---|
| File format | .xls (Excel 97-2003) | .xlsx (Excel 2007+) | .xlsx (Excel 2007+) |
| Format type | BIFF8 binary | OpenXML | OpenXML |
| Max rows per sheet | 65,536 | 1,048,576 | 1,048,576 |
| Max columns per sheet | 256 | 16,384 | 16,384 |
| Streaming workbook | No | No | Yes |
| Memory usage | High | High | Low |

The official "create a simple Excel" tutorial from the project's tutorial repository shows the API — verbose by design, but explicit and portable from Java POI knowledge:

```csharp
#r "nuget:NPOI"

using NPOI.XSSF.UserModel;
using System.IO;

var workbook = new XSSFWorkbook();
var sheet = workbook.CreateSheet("Sheet1");

sheet.CreateRow(0).CreateCell(0).SetCellValue("This is a test");

for (int i = 1; i <= 15; i++)
{
    sheet.CreateRow(i).CreateCell(0).SetCellValue(i);
}

using (var file = File.Create("sample.xlsx"))
{
    workbook.Write(file);
}
```

Two realities dominate NPOI in 2026. First, it is the only serious option for **`.xls` ingestion** and the only one with a **streaming writer** (SXSSF) for row counts that would exhaust memory in DOM-based libraries. Second, its funding model changed: since version 2.8.0 the binary releases carry an EULA that requires a **monthly maintenance fee from organizations using it commercially**, while startups, freelancers and hobbyists below the published revenue thresholds remain free. The README is explicit about this. Teams on the Apache-2.0 assumption from older versions should re-read the terms before upgrading.

## EPPlus: The Most Capable — With the Most Expensive Free Tier

EPPlus was the default "free Excel library" for a decade until its 2020 license change, and the confusion from that era still surfaces in code reviews. Version 5+ is **Polyform Noncommercial**: free for personal and non-commercial use, commercial use requires a paid license from EPPlus Software AB. The license header on every official sample file says it plainly. What you get for that is the deepest feature set of the three: a real **calculation engine** (`worksheet.Calculate()`), pivot tables, rich charts, conditional formatting, tables, and VBA support.

The official "getting started" sample shows both the mandatory license configuration and how straightforward the API is:

```csharp
using OfficeOpenXml;

// If you are a commercial business and have purchased a commercial license:
ExcelPackage.License.SetCommercial("<Your License Key here>");

// If you use EPPlus in a noncommercial context according to the Polyform Noncommercial license:
ExcelPackage.License.SetNonCommercialPersonal("<Your Name>");
// or...
ExcelPackage.License.SetNonCommercialOrganization("<Your Noncommercial Organization>");

using (var package = new ExcelPackage())
{
    // Add a new worksheet to the empty workbook
    var worksheet = package.Workbook.Worksheets.Add("Inventory");
    worksheet.Cells["A1"].Value = "ID";
    worksheet.Cells["B1"].Value = "Product";
    worksheet.Cells["C1"].Value = "Quantity";
    worksheet.Cells["D1"].Value = "Price";

    // Add a formula — EPPlus can calculate it for you
    worksheet.Cells["E2:E4"].Formula = "C2 * D2";
    worksheet.Calculate();

    package.SaveAs(new System.IO.FileInfo("Inventory.xlsx"));
}
```

The `SetCommercial`/`SetNonCommercialPersonal` call is mandatory — forget it and EPPlus throws a license exception at runtime, which is how many teams discover the licensing model in production. Version 8 development is active (last push September 2026), and the samples repository covers everything from async usage to complex pivot and chart scenarios.

## Pitfalls and Migration Gotchas

1. **EPPlus throws at runtime without a license context.** Since v5, every process must call `ExcelPackage.License.SetCommercial(...)` or the non-commercial equivalents before touching a package. Wrap it in startup code, not per-request — and make procurement sign off on the commercial tier before you build on the free one.
2. **NPOI's fee EULA is new since 2.8.0.** The Apache-2.0 license header is still in the repo, but the binary releases add an EULA with a revenue-based maintenance fee. Read `OSMFEULA.txt` in the repository before upgrading a commercial deployment.
3. **ClosedXML does not calculate formulas.** If your tests assert values right after writing formulas with ClosedXML, they will read empty or cached results. Compute server-side yourself, or open the file in Excel first.
4. **`.xls` limits are real.** HSSF caps at 65,536 rows and 256 columns per sheet. A report that fits in XSSF can silently fail or corrupt when a legacy consumer forces the older format.
5. **Memory scales with document size.** ClosedXML and EPPlus are DOM-based: a 200 MB workbook means hundreds of MB of managed objects. For bulk exports use NPOI's SXSSF streaming or restructure the export into multiple workbooks.
6. **Watch culture and number formats.** `SetCellValue(3.99)` with the wrong culture or cell format produces "3,99" strings in some locales — always set explicit number formats for money and dates, and test the file in both Excel and LibreOffice, because their rendering of edge cases differs (the same cross-application quirk we flag in our [web spreadsheet library guide](../2026-08-14-web-spreadsheet-libraries-univer-handsontable-luckysheet-guide/)).
7. **File locks and streams.** All three libraries keep the `FileStream` semantics you give them — use `using` blocks, and if you write to a memory stream for download, reset the position before handing it to the response.

## Choosing Between the Java and .NET Ecosystems

If your stack is polyglot, note that the Java side has its own equivalents — our [Apache POI vs EasyExcel vs FastExcel comparison](../2026-08-28-java-excel-libraries-apache-poi-easyexcel-fastexcel-comparison/) covers the same decisions for JVM teams, and NPOI's API deliberately mirrors Apache POI, so knowledge transfers directly. For .NET services that already make heavy outbound calls, the library patterns here fit alongside the clients covered in our [C# HTTP client comparison](../2026-08-02-csharp-http-client-libraries-restsharp-refit-httpclientfactory/). Whichever library you pick, write a thin repository wrapper around it: Excel requirements change faster than any library vendor's roadmap, and the wrapper is what lets you swap ClosedXML for EPPlus when finance eventually demands the calc engine.

## FAQ

### Which .NET Excel library is completely free for commercial use?

ClosedXML is MIT licensed with no commercial restrictions. NPOI is Apache-2.0 with an additional EULA since version 2.8.0 that requires a monthly maintenance fee from revenue-generating organizations. EPPlus is Polyform Noncommercial — free only for non-commercial use.

### Can ClosedXML read .xls files?

No. ClosedXML supports Excel 2007+ formats (.xlsx, .xlsm) only. For legacy Excel 97-2003 (.xls) files you need NPOI's HSSF implementation or a conversion step first.

### Does EPPlus require a license key in code?

Yes, since version 5. You must call `ExcelPackage.License.SetCommercial("<key>")` for commercial use or the non-commercial setters (`SetNonCommercialPersonal`/`SetNonCommercialOrganization`) otherwise, or EPPlus throws a license exception at runtime.

### Which library can calculate formulas on the server?

EPPlus has a full calculation engine (`worksheet.Calculate()`). NPOI provides a formula evaluator. ClosedXML writes formulas but does not calculate them — results appear when the file is opened in a spreadsheet application.

### How do I export very large datasets without running out of memory?

Use NPOI's SXSSFWorkbook, which streams rows to disk instead of keeping the whole sheet in memory. ClosedXML and EPPlus are DOM-based and load the full document, so multi-hundred-thousand-row exports will consume large amounts of RAM.

### Why does my EPPlus code throw a LicenseException on the server?

The license context must be configured before any EPPlus API is used — typically once at application startup. A common cause is setting it per-request or only in development configuration, so the first production request throws. Set it in `Program.cs`/startup and verify with a license smoke test in CI.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": ".NET Excel Libraries in 2026: ClosedXML vs NPOI vs EPPlus",
  "description": "Compare ClosedXML, NPOI and EPPlus for .NET Excel automation: licensing (MIT vs fee EULA vs Polyform), .xls/.xlsx support, streaming, formula calculation, real code samples and a use-case decision matrix.",
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
