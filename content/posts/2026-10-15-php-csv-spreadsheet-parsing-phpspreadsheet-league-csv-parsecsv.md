---
title: "PhpSpreadsheet vs League CSV vs ParseCsv in 2026: PHP CSV Parsing at Scale"
date: "2026-10-15"
description: "Which PHP library should parse your CSV and XLSX imports in 2026? Real memory behaviour, streaming code, benchmarks and pitfalls for PhpSpreadsheet, League CSV, ParseCsv and OpenSpout."
tags: ["php", "csv", "spreadsheet", "data-processing", "developer-tools"]
cover: "/img/screenshots/phpspreadsheet-autofilter.jpg"
draft: false
---

Every PHP developer meets the same wall eventually: a customer uploads a 180 MB spreadsheet, your import job hits `Allowed memory size of 512M exhausted`, and the request dies halfway through a partially written database. The library you chose three years ago for its friendly array API is now the reason your nightly sync runs out of memory.

Four libraries cover PHP spreadsheet work in 2026, and they sit at genuinely different points on the streaming-versus-convenience curve: **PhpSpreadsheet**, **League CSV**, **ParseCsv**, and **OpenSpout**. This guide shows which one survives a 2-million-row file, which one you should never point at a large upload, and the exact code to switch between them.

## TL;DR — Quick Verdict

**CSV of any size: League CSV.** Its record iterator is a generator, so memory stays flat regardless of file size, and the API is expressive enough for header handling, filtering and streaming downloads.

**XLSX/ODS with styles, formulas or multiple sheets: PhpSpreadsheet.** Nothing else in PHP reads the format as completely — but it loads workbooks into memory, so configure cell caching and only use it on files you can afford to hold.

**Huge XLSX files (100 MB+, hundreds of thousands of rows): OpenSpout.** It streams XLSX row by row and is the maintained successor to the archived box/spout.

**ParseCsv: small files and legacy code.** It is a tidy little parser that loads everything into an array — perfect for a 5,000-row config dump, dangerous for anything larger.

## The 2026 Status Check

Live GitHub data, pulled 2026-10-15:

| | **PhpSpreadsheet** | **League CSV** | **ParseCsv** | **OpenSpout** |
|---|---|---|---|---|
| Repo | PHPOffice/PhpSpreadsheet | thephpleague/csv | parsecsv/php-parsecsv | openspout/openspout |
| Stars | 13,995 | 3,482 | 683 | 1,263 |
| Last commit | 2026-10-12 | 2026-10-13 | 2026-02-02 | 2026-10-13 |
| Latest release | 5.10.0 | 9.28.0 | 1.3.2 | actively released |
| Install | `composer require phpoffice/phpspreadsheet` | `composer require league/csv` | `composer require parsecsv/php-parsecsv` | `composer require openspout/openspout` |
| Formats read | XLSX, XLS, ODS, CSV, HTML | CSV (+ TSV, delimited) | CSV (+ TSV) | CSV, XLSX, ODS |
| Formats written | XLSX, XLS, ODS, CSV, PDF, HTML | CSV | CSV | CSV, XLSX, ODS |
| Memory model | Whole workbook in memory (cacheable) | Row streaming | All rows in an array | Row streaming |
| Reads 1 GB file safely | No | Yes | No | Yes (XLSX/CSV) |
| Extensions needed | zip, xml, gd, mbstring | mbstring | mbstring | zip, xml |

The two rows that decide your architecture are **memory model** and **formats read**. Streaming libraries keep memory flat; array-based ones scale with file size. And only PhpSpreadsheet and OpenSpout understand XLSX at all — if your uploads are `.xlsx`, a CSV parser cannot help you.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Use | Why |
|---|---|---|
| Nightly 1 GB CSV import | **League CSV** | Generator iteration, constant memory |
| User-uploaded XLSX, any size | **OpenSpout** | Streams rows instead of loading the workbook |
| Read one worksheet, then write styled XLSX | **PhpSpreadsheet** | Full format support: styles, formulas, charts |
| Small CSV in a legacy script | **ParseCsv** | Minimal API, already in your composer.json |
| CSV download generated on the fly | **League CSV** | Write straight to `php://output` |
| Semicolon-delimited European export | **League CSV** or **ParseCsv** | Explicit delimiter control, no sniffing guesswork |
| Complex type coercion into models | **League CSV** + your own mapper | Statement API plus property access |
| PDF export from a workbook | **PhpSpreadsheet** | Built-in writers for PDF and HTML | 

## League CSV — The Default for Anything Large

League CSV treats a CSV file as what it actually is: a stream of records. `getRecords()` returns a generator, so the file is read incrementally and memory stays flat whether it holds a thousand rows or ten million.

```php
<?php
require 'vendor/autoload.php';

use League\Csv\Reader;
use League\Csv\Writer;

// --- reading: constant memory, associative rows from the header ---
$csv = Reader::createFromPath('/data/orders.csv', 'r');
$csv->setHeaderOffset(0);         // first row provides column names
$csv->setDelimiter(',');          // use ';' for many European exports
$csv->skipEmptyRecords();

$batch = [];
foreach ($csv->getRecords() as $record) {
    // $record is keyed by header: ['id' => '1', 'email' => '...', ...]
    $batch[] = $record;
    if (count($batch) === 1000) {
        insert_batch($batch);     // one INSERT per 1000 rows, not per row
        $batch = [];
    }
}
if ($batch) {
    insert_batch($batch);
}

// --- writing: stream a download without buffering the whole export ---
$writer = Writer::createFromPath('php://output', 'w');
$writer->insertOne(['id', 'email', 'total']);
foreach ($rows as $row) {
    $writer->insertOne($row);
}
```

The install line documented in the project README is `composer require league/csv:^9.0`. One configuration note worth knowing: older PHP versions need `ini_set('auto_detect_line_endings', '1')` to handle Mac-style line endings, and the package's own README shows that guard for pre-8.1 installs.

Where League CSV wins beyond memory: header injection detection, duplicate-header handling, delimiter and escape configuration per instance, and the `Statement`/`ResultSet` layer for filtering and ordering without writing manual loops. It is the one library here you can point at an untrusted upload without adding a size gate first.

![League CSV logo, the streaming CSV reader and writer for PHP](/img/screenshots/league-csv-logo.jpg "League CSV PHP package logo")

## PhpSpreadsheet — Complete XLSX Support, Real Memory Cost

PhpSpreadsheet is the successor to PHPExcel and remains the most complete spreadsheet implementation in PHP: multiple sheets, formulas, styles, number formats, chart definitions, and readers for XLSX, XLS, ODS and HTML.

```php
<?php
require 'vendor/autoload.php';

use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Settings;
use Symfony\Component\Cache\Adapter\FilesystemAdapter;
use Symfony\Component\Cache\Psr16Cache;

// 1. back cell objects with a PSR-16 cache to cut peak memory
Settings::setCache(new Psr16Cache(new FilesystemAdapter()));

// 2. read values only — skipping styles and formulas saves a large amount of RAM
$reader = IOFactory::createReaderForFile('/data/report.xlsx');
$reader->setReadDataOnly(true);

// 3. optionally restrict to specific columns/rows via an IReadFilter
$spreadsheet = $reader->load('/data/report.xlsx');

$sheet = $spreadsheet->getActiveSheet();
foreach ($sheet->getRowIterator(2) as $row) {   // start at row 2, skip header
    $cells = [];
    foreach ($row->getCellIterator() as $cell) {
        $cells[] = $cell->getValue();
    }
    // process $cells
}

$spreadsheet->disconnectWorksheets();   // free memory promptly
unset($spreadsheet);
```

Three settings change the memory profile dramatically. `setReadDataOnly(true)` discards styling metadata. A PSR-16 cache (filesystem, APCu or Redis) stores cell objects outside PHP's memory. An `IReadFilter` limits which rows and columns are materialised at all — the single biggest lever when you only need two columns from a 40-column sheet.

Writing is where it is unmatched: styled multi-sheet workbooks, conditional formatting and PDF/HTML export all come from the same object graph. If your deliverable is a formatted report rather than a data dump, this is the library. For the wider landscape of generating spreadsheets from code, our [comparison of openpyxl, XlsxWriter, Excelize and PhpSpreadsheet](../2026-06-20-spreadsheet-generation-libraries-openpyxl-xlsxwriter-excelize-phpspreadsheet/) covers the generation side in depth.

![PhpSpreadsheet reading a worksheet with the autofilter UI, screenshot from the official project documentation](/img/screenshots/phpspreadsheet-autofilter.jpg "PhpSpreadsheet worksheet with autofilter")

## ParseCsv — Small, Friendly, Entirely In-Memory

ParseCsv is the library you reach for when the job is "read this 3,000-row CSV and give me an array". The API is a thin object with public properties, and that simplicity is the entire point.

```php
<?php
require_once __DIR__ . '/vendor/autoload.php';

$csv = new ParseCsv\Csv();
$csv->encoding('UTF-8', 'UTF-8');   // convert on read
$csv->delimiter = ';';              // explicit, no guessing
$csv->parse('/data/orders.csv');     // fills $csv->data with every row

foreach ($csv->data as $row) {
    // $row['email'], $row['total'], ...
}

// mutate and write back
$csv->addRow(['email' => 'new@example.com', 'total' => 0]);
$csv->save();
```

Install is a single line: `composer require parsecsv/php-parsecsv`. Configuration options cover delimiter, enclosure, encoding conversion, and whether to use the first row as keys.

The tradeoff is right there in `$csv->data`: every row is decoded into a PHP array before you touch it. For a 50 MB file that is typically several hundred megabytes of PHP memory, because each CSV line becomes an array of zvals plus a hash table for the keys. Use it for configuration files, small exports and admin tooling — not for user uploads.

## OpenSpout — Streaming XLSX When PhpSpreadsheet Is Too Heavy

OpenSpout exists because large XLSX files break array-based readers. It reads and writes CSV, XLSX and ODS with a row-oriented streaming API, and it is the actively maintained continuation of box/spout (which was archived in 2022 with 4,225 stars).

```php
<?php
require 'vendor/autoload.php';

use OpenSpout\Reader\XLSX\Reader;
use OpenSpout\Writer\XLSX\Writer;
use OpenSpout\Common\Entity\Row;

// streaming read: one row in memory at a time
$reader = new Reader();
$reader->open('/data/big-report.xlsx');

foreach ($reader->getSheetIterator() as $sheet) {
    foreach ($sheet->getRowIterator() as $row) {
        $values = $row->toArray();
        // process $values
    }
}
$reader->close();

// streaming write
$writer = new Writer();
$writer->openToFile('/data/out.xlsx');
$writer->addRow(Row::fromValues(['id', 'email']));
foreach ($rows as $row) {
    $writer->addRow(Row::fromValues($row));
}
$writer->close();
```

Pin the major version in `composer.json`. The 4.x line reorganised the API (readers and writers are constructed directly rather than through entity factories), so code copied from older Spout tutorials will not compile against it. Details like formatted cells, merged cells and sheet styling are also deliberately out of scope — OpenSpout moves data, PhpSpreadsheet renders documents.

## Memory and Throughput: What to Expect

The practical rule for PHP imports is that non-streaming readers cost roughly **10 to 30 times the file size** in peak memory once you account for decoded strings, arrays and per-row overhead. That is why a 40 MB XLSX can exhaust a 512 MB `memory_limit` while a 1 GB CSV streams comfortably through League CSV.

Three habits matter more than library choice:

- **Batch your database writes.** One `INSERT` per row turns a 60-second import into a 20-minute one. Collect 500–1000 rows and insert them together, as shown in the League CSV example.
- **Insert inside a transaction.** Thousands of autocommitted inserts each pay a WAL flush; a single transaction can cut wall-clock time several-fold.
- **Bound the input.** Check `$_FILES['file']['size']` before parsing, and reject or queue anything beyond what your worker can handle. A queue plus a CLI worker is far more robust than a web request that might time out mid-import.

If your import endpoint is a long-running PHP process, the runtime environment matters too — our [comparison of Swoole, RoadRunner and FrankenPHP application servers](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/) covers how each handles concurrent long tasks. And once the data is parsed, the persistence layer usually dominates: see our [PHP ORM comparison covering Laravel Eloquent, Doctrine and Propel](../2026-07-06-php-orm-libraries-laravel-eloquent-doctrine-propel/) for the bulk-insert patterns that pair well with these readers.

## Pitfalls and Migration Notes

**A UTF-8 BOM silently breaks your first header.** Files exported from Excel often start with `EF BB BF`, so the first column key becomes `"\u{FEFF}id"` and every `$row['id']` returns null. Strip the BOM before parsing, or use League CSV's header handling and normalise the first key.

**Never trust header names as-is.** Duplicate headers, trailing spaces and empty header cells produce confusing arrays. Normalise keys explicitly, and decide what to do when a header is missing rather than letting `null` keys collide.

**CSV injection is a real security bug when you write files.** A cell beginning with `=`, `+`, `-` or `@` is executed as a formula when opened in a spreadsheet application. If any field in your export comes from user input, prefix suspicious values with a single quote or a tab before writing.

**Date cells are numbers, not dates.** XLSX stores dates as serial numbers, so `getValue()` gives you `45210` rather than `2026-10-15`. Use PhpSpreadsheet's date conversion helpers or apply a number format; do not hand-roll the epoch offset.

**Check your extensions before deploying.** PhpSpreadsheet needs `zip`, `xml`, `gd` and `mbstring`; OpenSpout needs `zip` and `xml`. A missing `ext-zip` fails at runtime on the first XLSX read, not at install time — add all of them to your Dockerfile.

**Streaming output requires a clean buffer.** Writing a CSV download to `php://output` while output buffering is active sends your framework's HTML wrapper into the file. Call `ob_end_clean()` before streaming and set `Content-Type: text/csv` plus `Content-Disposition` explicitly.

**Do not stream your database cursor and your HTTP response at once.** Multiple nested streams make error handling and retries nearly impossible. Stream the input into a queue or a batch insert, then generate the response from finished data.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PhpSpreadsheet vs League CSV vs ParseCsv in 2026: PHP CSV Parsing at Scale",
  "description": "Which PHP library should parse CSV and XLSX imports in 2026? Memory behaviour, streaming code, benchmarks and pitfalls for PhpSpreadsheet, League CSV, ParseCsv and OpenSpout.",
  "datePublished": "2026-10-15",
  "dateModified": "2026-10-15",
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

**Which PHP library is fastest for reading a large CSV file?**
League CSV is the fastest practical choice because it iterates records as a generator, keeping memory flat while avoiding the per-array overhead of loading everything up front. For raw throughput on very simple files, PHP's native `fgetcsv()` in a loop is comparable, but you lose header handling, delimiter control and encoding support that League CSV provides.

**Can PhpSpreadsheet read a 100 MB XLSX file?**
Not comfortably with default settings. It materialises the workbook in memory, so a file that large typically needs several gigabytes of PHP memory. Reduce peak usage with `setReadDataOnly(true)`, a PSR-16 cell cache and an `IReadFilter`; if the file is still too large, read it with OpenSpout instead.

**Is box/spout still maintained?**
No. box/spout was archived in 2022 after reaching 4,225 stars. OpenSpout (openspout/openspout) is the maintained continuation with 1,263 stars and commits through October 2026. Migrating means updating the composer package and adapting to the 4.x API.

**How do I handle a semicolon-delimited CSV from Excel in a European locale?**
Set the delimiter explicitly instead of relying on detection. In League CSV call `$csv->setDelimiter(';')`, and in ParseCsv assign `$csv->delimiter = ';'`. Automatic delimiter detection misreads files containing text with commas or quotes, which is why both libraries favour explicit configuration.

**What is the best way to import a million CSV rows into MySQL from PHP?**
Stream the file with League CSV, accumulate 500–1000 rows, and insert each batch inside a single transaction, using `INSERT ... VALUES` with multiple tuples or `LOAD DATA LOCAL INFILE` for the fastest path. Commit in chunks of a few thousand rows to keep rollback and re-run costs reasonable.

**Do I need to worry about memory when writing CSV exports?**
Yes, if you build the whole export string in PHP first. Write directly to `php://output` with League CSV's writer so rows leave the process as they are produced, and remember to call `ob_end_clean()` first so no buffered HTML pollutes the file.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
