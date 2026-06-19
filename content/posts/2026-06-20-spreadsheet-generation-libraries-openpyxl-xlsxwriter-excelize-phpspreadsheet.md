---
title: "Programmatic Spreadsheet Generation Libraries: OpenPyXL vs XlsxWriter vs Excelize vs PhpSpreadsheet"
date: "2026-06-20"
tags: ["spreadsheet", "developer-tools", "data-processing", "python", "golang", "php", "excel", "libraries"]
draft: false
---

Modern applications frequently need to generate Excel and spreadsheet files programmatically — from financial reports and data exports to invoice generation and analytics dashboards. While self-hosted spreadsheet editors like EtherCalc and Collabora provide web-based interactive editing, sometimes you need to generate `.xlsx` files directly from your application code without user interaction.

This article compares four leading open-source spreadsheet generation libraries across different programming languages: **OpenPyXL** and **XlsxWriter** (Python), **Excelize** (Go), and **PhpSpreadsheet** (PHP). Each handles the complexities of the Office Open XML (OOXML) format so you don't have to.

## How Spreadsheet Generation Libraries Work

Unlike interactive spreadsheet editors that render a full GUI in the browser, spreadsheet generation libraries operate at the file format level. They construct valid `.xlsx` (or `.xls`, `.ods`) files by writing XML structures, shared strings, styles, and cell data according to the ECMA-376 Office Open XML specification.

The `.xlsx` format is essentially a ZIP archive containing XML files. A typical `.xlsx` file structure includes:

```
workbook.xlsx
├── [Content_Types].xml
├── _rels/
│   └── .rels
├── xl/
│   ├── workbook.xml
│   ├── styles.xml
│   ├── sharedStrings.xml
│   ├── worksheets/
│   │   └── sheet1.xml
│   └── _rels/
│       └── workbook.xml.rels
└── docProps/
    ├── app.xml
    └── core.xml
```

Each library abstracts this complexity, providing an API for creating worksheets, adding data, applying formatting, inserting charts, and setting formulas. The key difference between them lies in their design philosophy, performance characteristics, and language ecosystem.

## Library-by-Library Deep Dive

### OpenPyXL (Python) — 2,200+ Stars

OpenPyXL is the de facto standard for reading and writing Excel 2010+ xlsx/xlsm files in Python. It supports both reading existing files and creating new ones from scratch, making it ideal for template-based workflows where you need to modify an existing spreadsheet.

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
ws = wb.active
ws.title = "Quarterly Report"

# Headers with styling
headers = ["Product", "Q1", "Q2", "Q3", "Q4", "Total"]
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(color="FFFFFF", bold=True, size=12)

for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center")

# Data rows
data = [
    ["Widget A", 15000, 18200, 16400, 20100],
    ["Widget B", 8200, 9100, 7800, 9500],
    ["Service X", 32000, 28500, 31000, 34000],
]

for row_idx, row_data in enumerate(data, 2):
    for col_idx, value in enumerate(row_data, 1):
        ws.cell(row=row_idx, column=col_idx, value=value)
    # SUM formula
    ws.cell(row=row_idx, column=6, value=f"=SUM(B{row_idx}:E{row_idx})")

# Column widths
ws.column_dimensions['A'].width = 20
for col in ['B', 'C', 'D', 'E', 'F']:
    ws.column_dimensions[col].width = 14

wb.save("quarterly_report.xlsx")
```

**Strengths:** Read-write capability, extensive styling support, charts and images, data validation. **Weaknesses:** Can be slow with very large files (100K+ rows), higher memory usage compared to XlsxWriter.

### XlsxWriter (Python) — 3,900+ Stars

XlsxWriter is a write-only Python module for creating Excel XLSX files. Unlike OpenPyXL, it cannot read or modify existing files, but it excels at high-performance writing with a comprehensive feature set including charts, conditional formatting, data validation, and rich formatting.

```python
import xlsxwriter

workbook = xlsxwriter.Workbook("sales_report.xlsx")
worksheet = workbook.add_worksheet("Sales")

# Define formats
header_format = workbook.add_format({
    'bold': True,
    'bg_color': '#4472C4',
    'font_color': 'white',
    'border': 1,
    'align': 'center',
    'valign': 'vcenter',
})

currency_format = workbook.add_format({'num_format': '$#,##0'})
percent_format = workbook.add_format({'num_format': '0.0%'})

# Write headers
headers = ["Region", "Revenue", "Growth", "Notes"]
for col, header in enumerate(headers):
    worksheet.write(0, col, header, header_format)

# Write data
sales_data = [
    ["North America", 1250000, 0.15, "Strong Q4 performance"],
    ["Europe", 980000, 0.08, "Currency impact -2%"],
    ["Asia Pacific", 1450000, 0.22, "New market expansion"],
    ["Latin America", 420000, 0.12, "Steady growth"],
]

for row, data in enumerate(sales_data, 1):
    worksheet.write(row, 0, data[0])
    worksheet.write_number(row, 1, data[1], currency_format)
    worksheet.write_number(row, 2, data[2], percent_format)
    worksheet.write(row, 3, data[3])

# Add a chart
chart = workbook.add_chart({'type': 'column'})
chart.add_series({
    'name': 'Revenue',
    'categories': '=Sales!$A$2:$A$5',
    'values': '=Sales!$B$2:$B$5',
})
chart.set_title({'name': 'Revenue by Region'})
worksheet.insert_chart('D7', chart)

worksheet.set_column('A:D', 18)
workbook.close()
```

**Strengths:** High performance, excellent charting (60+ chart types), conditional formatting, rich string support. **Weaknesses:** Write-only (no reading), Python-only.

### Excelize (Go) — 20,700+ Stars

Excelize is the most starred spreadsheet library in this comparison, written in Go. It provides a complete API for reading and writing Microsoft Excel files with support for charts, images, conditional formatting, pivot tables, and sparklines. Its Go-native implementation makes it ideal for microservices and CLI tools.

```go
package main

import (
    "fmt"
    "github.com/xuri/excelize/v2"
)

func main() {
    f := excelize.NewFile()
    defer func() {
        if err := f.Close(); err != nil {
            fmt.Println(err)
        }
    }()

    // Create a new sheet
    index, _ := f.NewSheet("Inventory")
    f.SetActiveSheet(index)

    // Set headers
    headers := []string{"SKU", "Product Name", "Quantity", "Unit Price", "Total"}
    headerStyle, _ := f.NewStyle(&excelize.Style{
        Font: &excelize.Font{Bold: true, Size: 12, Color: "FFFFFF"},
        Fill: excelize.Fill{Type: "pattern", Color: []string{"4472C4"}, Pattern: 1},
        Alignment: &excelize.Alignment{Horizontal: "center"},
    })

    for i, h := range headers {
        cell, _ := excelize.CoordinatesToCellName(i+1, 1)
        f.SetCellValue("Inventory", cell, h)
    }
    f.SetRowStyle("Inventory", 1, 1, headerStyle)

    // Data rows
    inventory := [][]interface{}{
        {"SKU-001", "Widget Pro", 450, 29.99},
        {"SKU-002", "Gadget Mini", 1200, 12.50},
        {"SKU-003", "Sensor X1", 85, 199.00},
    }

    for rowIdx, row := range inventory {
        for colIdx, val := range row {
            cell, _ := excelize.CoordinatesToCellName(colIdx+1, rowIdx+2)
            f.SetCellValue("Inventory", cell, val)
        }
        totalCell, _ := excelize.CoordinatesToCellName(5, rowIdx+2)
        f.SetCellFormula("Inventory", totalCell,
            fmt.Sprintf("=C%d*D%d", rowIdx+2, rowIdx+2))
    }

    f.AutoFilter("Inventory", "A1:E4", []excelize.AutoFilterOptions{})
    f.SetColWidth("Inventory", "A", "E", 18)
    f.SaveAs("inventory_report.xlsx")
}
```

**Strengths:** Excellent performance, concurrency-safe, reads and writes, streaming writer for large files, rich feature set. **Weaknesses:** Requires Go runtime, steeper learning curve for non-Go developers.

### PhpSpreadsheet (PHP) — 13,900+ Stars

PhpSpreadsheet is the successor to PHPExcel, providing a pure PHP implementation for reading and writing spreadsheet files. It supports multiple formats including Xlsx, Xls, Ods, Csv, Html, and Pdf, making it the most format-flexible option.

```php
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Writer\Xlsx;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\Style\Alignment;
use PhpOffice\PhpSpreadsheet\Style\Border;

$spreadsheet = new Spreadsheet();
$sheet = $spreadsheet->getActiveSheet();
$sheet->setTitle('Employee Report');

$headerStyle = [
    'font' => ['bold' => true, 'color' => ['rgb' => 'FFFFFF'], 'size' => 12],
    'fill' => ['fillType' => Fill::FILL_SOLID, 'startColor' => ['rgb' => '4472C4']],
    'alignment' => ['horizontal' => Alignment::HORIZONTAL_CENTER],
];

$headers = ['Employee', 'Department', 'Salary', 'Start Date', 'Status'];
foreach ($headers as $col => $header) {
    $cell = $sheet->getCellByColumnAndRow($col + 1, 1);
    $cell->setValue($header);
    $sheet->getStyle($cell->getCoordinate())->applyFromArray($headerStyle);
}

$employees = [
    ['Alice Johnson', 'Engineering', 95000, '2024-03-15', 'Active'],
    ['Bob Smith', 'Marketing', 78000, '2024-01-10', 'Active'],
    ['Carol Davis', 'Engineering', 110000, '2023-06-01', 'Active'],
];

$row = 2;
foreach ($employees as $emp) {
    $col = 1;
    foreach ($emp as $value) {
        $sheet->getCellByColumnAndRow($col, $row)->setValue($value);
        $col++;
    }
    $row++;
}

foreach (range('A', 'E') as $col) {
    $sheet->getColumnDimension($col)->setAutoSize(true);
}

$writer = new Xlsx($spreadsheet);
$writer->save('employee_report.xlsx');
```

**Strengths:** Multi-format support, reads and writes, extensive styling, formula calculation engine, PDF export. **Weaknesses:** Higher memory usage than compiled alternatives, PHP runtime dependency.

## Feature Comparison Table

| Feature | OpenPyXL | XlsxWriter | Excelize | PhpSpreadsheet |
|---------|----------|------------|----------|----------------|
| **Language** | Python | Python | Go | PHP |
| **GitHub Stars** | 2,200+ | 3,900+ | 20,700+ | 13,900+ |
| **Read Support** | Yes | No | Yes | Yes |
| **Write Support** | Yes | Yes | Yes | Yes |
| **Output Formats** | XLSX, XLSM | XLSX | XLSX, XLAM, XLSM | XLSX, XLS, ODS, CSV, HTML, PDF |
| **Charts** | 20+ types | 60+ types | 30+ types | 30+ types |
| **Pivot Tables** | Limited | Full | Full | Full |
| **Streaming Write** | Memory-bound | Optimized | Streaming writer | Memory-bound |
| **Conditional Formatting** | Yes | Yes | Yes | Yes |
| **Data Validation** | Yes | Yes | Yes | Yes |
| **Image Insertion** | Yes | Yes | Yes | Yes |
| **License** | MIT | BSD-2 | BSD-3 | MIT |

## Performance and Scaling Considerations

When choosing a spreadsheet generation library, performance characteristics matter significantly depending on your use case. For generating reports with 10,000+ rows, XlsxWriter and Excelize significantly outperform their counterparts due to their optimized write paths. XlsxWriter's write-only design means it never loads the entire document into memory — it streams data directly to the output file using Python's tempfile module for temporary storage, keeping memory usage constant regardless of file size.

Excelize leverages Go's goroutines for concurrent cell operations and provides a streaming writer API (NewStreamWriter) that can handle millions of rows without exhausting memory. In benchmarks, Excelize generates 100,000-row files in approximately 2-3 seconds compared to 15-20 seconds for OpenPyXL.

For use cases involving template modification (reading an existing .xlsx, modifying specific cells, and saving), OpenPyXL and PhpSpreadsheet are the clear winners since XlsxWriter cannot read files at all. OpenPyXL handles template workflows efficiently with minimal code, while PhpSpreadsheet adds PDF export as a bonus for reporting pipelines that need both spreadsheet and document output.

## Deployment Integration Patterns

Integrating spreadsheet generation into containerized applications follows language-specific patterns. Here is a Docker Compose example for a Python report generation service using XlsxWriter:

```yaml
version: "3.8"
services:
  report-generator:
    image: python:3.12-slim
    volumes:
      - ./reports:/app/reports
      - ./templates:/app/templates
    environment:
      - OUTPUT_DIR=/app/reports
      - TEMPLATE_DIR=/app/templates
    command: >
      sh -c "pip install xlsxwriter openpyxl &&
             python /app/generate_reports.py"
```

For Go microservices with Excelize, a minimal multi-stage Dockerfile keeps the image size small:

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /excel-service

FROM alpine:3.20
COPY --from=builder /excel-service /usr/local/bin/excel-service
ENTRYPOINT ["/usr/local/bin/excel-service"]
```

## Why Generate Spreadsheets Programmatically?

Not every spreadsheet task requires a full web-based editor. Programmatic generation fills critical gaps in data pipelines and business automation. When you need to generate hundreds of customized invoices at month-end, export analytics from a data warehouse to Excel for business analysts, or produce regulatory compliance reports on a scheduled basis, a library integrated into your application code is far more efficient than automating a browser-based editor.

Data sovereignty is another key consideration. Using a self-hosted spreadsheet generation library means your sensitive financial data never leaves your infrastructure. Unlike SaaS spreadsheet APIs that process your data on external servers, OpenPyXL, XlsxWriter, Excelize, and PhpSpreadsheet all run entirely within your application's process — no network calls, no third-party access, complete control over data handling.

For interactive spreadsheet editing with a web interface, see our [self-hosted spreadsheet editors comparison](../ethercalc-vs-onlyoffice-calc-vs-collabora-calc-self-hosted-spreadsheets-guide-2026/). If you're working with CSV and tabular data processing, our [CSV processing tools guide](../2026-06-17-csv-processing-csvkit-xsv-miller/) covers command-line alternatives. For large-scale data pipeline orchestration, check our [data processing engines comparison](../2026-05-14-self-hosted-data-processing-engines-databend-vs-datafusion-vs-ballista-guide/).

## FAQ

### When should I use XlsxWriter over OpenPyXL?

Use XlsxWriter when you only need to create new Excel files from scratch and performance matters. It's faster, uses less memory, and has better chart support (60+ types vs 20+). Use OpenPyXL when you need to read existing Excel files, modify templates, or work with .xlsm (macro-enabled) files. Many projects use both: OpenPyXL for template reading and XlsxWriter for high-volume output generation.

### Can Excelize handle files larger than available RAM?

Yes. Excelize provides a streaming writer API (NewStreamWriter) that writes rows incrementally without holding the entire dataset in memory. This allows generating files with millions of rows on machines with modest RAM. The streaming mode does have limitations — it cannot modify previously written rows, and complex formatting like merged cells is restricted.

### Is PhpSpreadsheet compatible with PHPExcel?

PhpSpreadsheet is the official successor to PHPExcel, but it's not fully backward compatible. Namespaces changed and many method signatures were updated. A migration guide is available in the official documentation, and most projects can migrate within a few hours. PHPExcel itself is deprecated and no longer receives security updates.

### How do I protect generated spreadsheets with passwords?

All four libraries support Excel workbook and worksheet protection. With OpenPyXL: `ws.protection.sheet = True` and `ws.protection.password = 'secret'`. With XlsxWriter: `worksheet.protect('secret', {'insert_rows': True})`. With Excelize: `f.ProtectSheet("Sheet1", &excelize.SheetProtectionOptions{Password: "secret"})`. With PhpSpreadsheet: `$sheet->getProtection()->setPassword('secret')`. Note that Excel built-in password protection is not cryptographically secure — it deters casual users but should not be relied upon for sensitive data.

### Can these libraries handle non-English characters and Unicode?

Yes, all four libraries fully support Unicode. OpenPyXL and XlsxWriter use Python's native Unicode strings. Excelize uses Go's native UTF-8 encoding. PhpSpreadsheet handles UTF-8 through PHP's mbstring extension. For CJK characters, Arabic script, emoji, and right-to-left text, all libraries render correctly in Excel.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Programmatic Spreadsheet Generation Libraries: OpenPyXL vs XlsxWriter vs Excelize vs PhpSpreadsheet",
  "description": "Compare four leading open-source spreadsheet generation libraries across Python, Go, and PHP. Code examples, feature comparison, and deployment patterns for programmatic Excel file creation.",
  "datePublished": "2026-06-20",
  "dateModified": "2026-06-20",
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
