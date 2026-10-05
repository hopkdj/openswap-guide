---
title: "Spreadsheet Formula Engines in 2026: HyperFormula vs Formulajs vs IronCalc vs Python formulas"
date: "2026-10-05"
tags: ["developer-tools", "libraries", "spreadsheet", "javascript", "rust", "python"]
draft: false
cover: "/img/screenshots/hyperformula-logo.jpg"
---

Every product that lets a user type `=SUM(A1:A10)` eventually hits the same wall: **you now have to evaluate arbitrary formulas correctly, and you cannot ship your own half-baked parser.** Excel-compatible formula evaluation means 400+ functions, operator precedence, relative and absolute references, cross-sheet ranges, circular-reference detection, and locale-aware number parsing. That is a multi-year project — unless you embed an engine.

This guide compares the four formula engines that are genuinely maintained in 2026, with live GitHub data and API examples taken directly from their official repositories.

## Quick Verdict

Pick **HyperFormula** if you are building a browser or Node.js product and want the closest thing to Excel semantics with a commercial-friendly license path. Pick **Formulajs** if you only need a function library — a stateless `SUM`, `PMT`, or `VLOOKUP` — and not a dependency graph. Pick **IronCalc** if you want a native Rust engine with a real calculation model, or you need it embedded in a Rust service. Pick **Python `formulas`** when your source of truth is an actual `.xlsx` workbook and you want to compute its output cells without opening a spreadsheet application.

## The Four Engines Compared

| Engine | Language | Stars | Last Push | Evaluation model | License | Excel file I/O | Best for |
|---|---|---|---|---|---|---|---|
| [HyperFormula](https://github.com/handsontable/hyperformula) | TypeScript | 2,798 | active 2026 | Full dependency graph | GPL-3 or commercial | Import/export via wrappers | In-browser spreadsheet products |
| [Formulajs](https://github.com/formulajs/formulajs) | JavaScript | 821 | active 2026 | Stateless function calls | MIT | None | Quick calculations, no cell graph |
| [IronCalc](https://github.com/ironcalc/IronCalc) | Rust | 4,184 | 2026-10-04 | Full workbook model | Open source | Native `.xlsx` read/write | Embedded engines, Rust services |
| [python `formulas`](https://github.com/vinci1it2000/formulas) | Python | 500 | active 2026 | On-demand graph over workbook | EUPL-1.2 | Loads real `.xlsx` | Auditing and automating workbooks |

Star counts are pulled live from the GitHub API. A note on **HyperFormula's license**: the open-source tier is GPL-3, and the project expects a commercial license key for closed-source use — read that carefully before you embed it in a proprietary product.

## Use-Case Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Editable grid in a web app where users type formulas | **HyperFormula** | It maintains a dependency graph, so a single edit recalculates only affected cells |
| You just need `PMT`, `NPV` or `SUM` inside a calculation form | **Formulajs** | Function-level API, no engine instance, no memory graph to manage |
| Rust service that must parse and recalculate a workbook | **IronCalc** | Native model with `xlsx` import/export and no JavaScript runtime |
| Automated reporting off a finance team's `.xlsx` model | **Python `formulas`** | Loads the actual workbook, calculates it, and can write results back |
| You need circular-reference tolerance | **python `formulas`** | `finish(circular=True)` explicitly models circular dependencies |

## HyperFormula — The Full Engine for Web Products

Install:

```bash
npm install hyperformula
```

HyperFormula builds a dependency graph and recalculates affected cells when inputs change. The example below, adapted from the project README, creates a mortgage payment calculator:

```js
import { HyperFormula } from 'hyperformula';

// Create a HyperFormula instance
const hf = HyperFormula.buildEmpty({ licenseKey: 'gpl-v3' });

// Add an empty sheet
const sheetName = hf.addSheet('Mortgage Calculator');
const sheetId = hf.getSheetId(sheetName);

// Populate inputs
hf.setCellContents({ sheet: sheetId, col: 0, row: 0 }, [['Principal', 300000]]);
hf.setCellContents({ sheet: sheetId, col: 0, row: 1 }, [['Rate', 0.045]]);
hf.setCellContents({ sheet: sheetId, col: 0, row: 2 }, [['Term (months)', 360]]);

// A real Excel formula, evaluated by the engine
hf.setCellContents(
  { sheet: sheetId, col: 0, row: 3 },
  [['Monthly payment', '=PMT(B2/12, B4, -B1)']]
);

console.log(hf.getCellValue({ sheet: sheetId, col: 1, row: 3 }));
```

The important architectural detail is that `hf.setCellContents` is a **mutation**, not an evaluation. The engine recomputes the dependency subgraph in the background, which is why HyperFormula can drive a 100,000-cell grid without freezing the UI. It also exposes undo/redo stacks, named expressions, and clipboard semantics — the parts of "spreadsheet-ness" you would otherwise rebuild by hand.

## Formulajs — Functions Without the Engine

Install:

```bash
npm install @formulajs/formulajs
```

Formulajs is deliberately *not* an engine. It is a library of Excel-compatible functions that you call directly, which makes it far lighter than a graph-based system when you only need math:

```js
import * as formulajs from '@formulajs/formulajs';

formulajs.SUM([1, 2, 3]);              // 6
formulajs.DATE(2008, 7, 8);
formulajs.PMT(0.045 / 12, 360, -300000);
```

You can also import individual functions to keep your bundle small:

```js
import { SUM } from '@formulajs/formulajs';

SUM([1, 2, 3]); // 6
```

Use Formulajs when the *user* is not writing formulas. If your UI is "pick a loan amount, pick a rate, we show the payment", Formulajs is the right size of tool. The moment users need cell references and cross-references, you have outgrown it.

## IronCalc — A Native Rust Engine

Install:

```bash
cargo add ironcalc
```

IronCalc implements a workbook model — sheets, cells, styles — and writes real `.xlsx` files without a JavaScript or Java dependency. This example from the repository README fills a 99×99 multiplication square and exports it:

```rust
use ironcalc::{
    base::{expressions::utils::number_to_column, Model},
    export::save_to_xlsx,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut model = Model::new_empty("hello-calc.xlsx", "en", "UTC", "en")?;

    // Adds a square of numbers in the first sheet
    for row in 1..100 {
        for column in 1..100 {
            let value = row * column;
            model.set_user_input(0, row, column, format!("{}", value));
        }
    }

    save_to_xlsx(&model, "hello-calc.xlsx")?;
    Ok(())
}
```

`Model::new_empty` takes a filename plus locale, timezone and language tags — a detail that matters, because it is the mechanism by which IronCalc avoids the classic comma-versus-decimal-point disaster when parsing user input.

## Python `formulas` — Calculate the Workbook Itself

Install:

```bash
pip install formulas
```

This library takes a different approach: instead of asking you to build a model, it parses an existing `.xlsx` file into a calculation graph and evaluates the output cells. From the official documentation:

```python
import formulas

fpath = "financial_model.xlsx"
xl_model = formulas.ExcelModel().loads(fpath).finish()

solution = xl_model.calculate()
xl_model.write(dirpath="./output")
```

Two behaviours are worth memorising. First, `finish(circular=True)` allows circular references, which is essential if your workbook contains the interest-calculations-on-interest patterns common in finance. Second, `from_ranges()` lets you load only the part of the workbook you care about:

```python
xl_model = formulas.ExcelModel().from_ranges("'[model.xlsx]DATA'!C2:D2")
```

That partial-load path is the difference between a 40-second full-workbook evaluation and a sub-second one when you only need two output cells.

## Common Pitfalls

**1. Locale decimal separators will corrupt your inputs.** `1,5` means one-and-a-half in Germany and fifteen in the United States. Engines that accept a locale at construction time (IronCalc's `Model::new_empty`) handle this properly; engines that do not (Formulajs) will silently mis-parse strings. Normalise to a canonical numeric type *before* the engine sees it.

**2. Volatile functions break naive caching.** `NOW()`, `TODAY()` and `RAND()` change on every evaluation. If you memoise results, a `NOW()` cell will freeze at its first value. Either mark volatile functions explicitly or exclude them from your cache.

**3. Cross-sheet references are where ports fail.** `Sheet2!A1` and `'My Sheet'!A1` (note the mandatory quotes around names with spaces) are parsed differently by every engine. When migrating from one engine to another, diff the *evaluated* result of every output cell, not the formula text.

**4. Unbounded ranges are a performance trap.** `SUM(A:A)` over a million-row sheet costs real memory in graph-based engines. Prefer bounded ranges (`A1:A1000`) unless your engine implements lazy evaluation.

**5. License keys are a real deployment concern.** HyperFormula's open-source build requires `licenseKey: 'gpl-v3'` and expects a paid key for proprietary use. Baking in the wrong key is a compliance bug, not a runtime one — put it in configuration, not in code.

## FAQ

**What is the difference between a formula engine and a spreadsheet library?**
A spreadsheet library writes or reads `.xlsx` files; a formula engine *evaluates* the formulas inside them. HyperFormula and IronCalc are engines, Formulajs is a function library, and Python `formulas` is an engine that starts from an existing workbook.

**Can I use HyperFormula in a commercial product?**
Only under the terms you comply with. HyperFormula is GPL-3 without a commercial key, which is incompatible with closed-source distribution. For proprietary products you need a commercial license — plan for that before you build on it.

**How do I evaluate Excel formulas without JavaScript?**
Use **IronCalc** (Rust) or **Python `formulas`**. Both parse and evaluate workbook content natively, and both can write results back to real `.xlsx` files.

**Which engine handles circular references?**
Python `formulas` supports them explicitly through `finish(circular=True)`. Most engines reject circular references outright, which is correct behaviour for a normal spreadsheet but inconvenient when you inherit a finance model that relies on iterative calculation.

**Do formula engines support every Excel function?**
No. Coverage is the single biggest differentiator between engines. HyperFormula and IronCalc cover the widely used function set and a large portion of the specialist functions; Formulajs implements a broad library of individual functions. Always test your specific function list against the engine before committing.

**How do I migrate formulas between engines?**
Do not migrate formula text — migrate *results*. Run both engines over the same workbook, compare the evaluated value of every output cell, and only then investigate the formulas that disagree.

For the companion problem of *producing* spreadsheets rather than evaluating them, see our [spreadsheet generation libraries comparison](../2026-06-20-spreadsheet-generation-libraries-openpyxl-xlsxwriter-excelize-phpspreadsheet/). If your formulas are driven by validated JSON input, our [JSON schema validation guide](../2026-06-08-self-hosted-json-schema-validation-ajv-prism-joi/) covers the boundary, and the [Python CSV libraries roundup](../2026-07-04-python-csv-libraries-csv-pandas-csvkit-unicodecsv/) handles the tabular data feeding into it.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Spreadsheet Formula Engines in 2026: HyperFormula vs Formulajs vs IronCalc vs Python formulas",
  "description": "A practical 2026 comparison of spreadsheet formula engines for JavaScript, Rust and Python, covering dependency graphs, Excel function coverage, licensing and real API examples.",
  "datePublished": "2026-10-05",
  "dateModified": "2026-10-05",
  "author": { "@type": "Organization", "name": "OpenSwap Guide" },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": { "@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png" }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
