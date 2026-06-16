---
title: "Self-Hosted CSV Processing Tools: csvkit vs xsv vs Miller (mlr)"
date: "2026-06-17"
tags: ["data-processing", "csv", "cli-tools", "dev-tools", "data-wrangling", "python", "rust"]
draft: false
---

CSV (Comma-Separated Values) remains the universal interchange format for data — it's the lowest common denominator between spreadsheets, databases, APIs, and log files. Whether you're analyzing Apache access logs, transforming database exports, or cleaning up a messy spreadsheet, you need tools that can slice, filter, aggregate, and reshape tabular data efficiently.

This guide compares three powerful open-source CSV toolkits for the command line: **csvkit** (Python-based comprehensive toolkit, 6,390 GitHub stars), **xsv** (blazing-fast Rust toolkit, 10,750 stars), and **Miller** (awk/sed for structured data, 9,911 stars). Each takes a fundamentally different approach to tabular data processing, and choosing the right one depends on your performance requirements, data complexity, and workflow preferences.

## Why Process CSV on the Command Line?

Before reaching for Python pandas or loading data into a database, command-line CSV tools offer compelling advantages:

- **Speed**: Process multi-gigabyte files without loading everything into memory
- **Pipeline composability**: Chain operations with Unix pipes — `csvcut | csvgrep | csvsort | csvlook`
- **Scriptability**: Embed in shell scripts for automated ETL pipelines
- **Zero setup**: No database schema, no Python environment, no Jupyter notebook — just pip install and go
- **Deterministic**: Same input always produces the same output, making pipelines reproducible

A single well-crafted pipeline can replace hundreds of lines of Python and run an order of magnitude faster. For data engineers and system administrators who live on the command line, these tools are indispensable.
For related reading, see our [Data Processing Engines comparison](../2026-05-14-self-hosted-data-processing-engines-databend-vs-datafusion-vs-ballista-guide/) and our [JSON Schema Validation guide](../2026-06-08-self-hosted-json-schema-validation-ajv-prism-joi/). For text processing at scale, check our [CLI Fuzzy Finders comparison](../2026-06-16-self-hosted-cli-fuzzy-finders-fzf-skim-peco/).

## Tool Comparison

| Feature | csvkit | xsv | Miller (mlr) |
|---------|--------|-----|--------------|
| **Language** | Python | Rust | Go |
| **GitHub Stars** | 6,390 | 10,750 | 9,911 |
| **Last updated** | June 2026 | April 2025 | June 2026 |
| **Install** | `pip install csvkit` | `cargo install xsv` / binary | `apt install miller` / binary |
| **Speed** | Moderate (Python) | Blazing fast (Rust) | Fast (Go) |
| **Memory usage** | Streaming (low) | Indexed (low) | Streaming (low) |
| **Input formats** | CSV, TSV, Excel, JSON, SQL | CSV, TSV | CSV, TSV, JSON, JSON Lines, DKVP, NIDX, XTAB |
| **Output formats** | CSV, JSON, SQL, Excel, Markdown | CSV, TSV | CSV, TSV, JSON, JSON Lines, Markdown, DKVP, XTAB |
| **CSV dialect support** | Auto-detect + manual | Limited (delimiter only) | Extensive (CSV, TSV, ASV, USV, etc.) |
| **Statistics/aggregation** | `csvstat` (descriptive stats) | `xsv stats` + `xsv frequency` | `mlr stats1`, `mlr stats2`, `mlr top`, `mlr histogram` |
| **Joins** | `csvjoin` (single-key) | `xsv join` (single-key) | `mlr join` (multi-key, left/right/inner/full) |
| **SQL-like queries** | `csvsql` (SQLite-backed) | None (use `xsv search`) | `mlr filter` + `mlr put` (DSL) |
| **Streaming** | All commands are streaming | Index-based for joins | All commands are streaming |

## csvkit: The Python Powerhouse

csvkit is the Swiss Army knife of CSV processing — a comprehensive toolkit that covers everything from basic slicing to SQL-powered queries and Excel conversion. Written in Python, it's easy to install and extend, though not the fastest option for multi-gigabyte files.

**Installation:**

```bash
pip install csvkit

# Verify installation
csvstat --version
```

**Core workflow:**

```bash
# Inspect a CSV file
csvstat sales.csv    # Descriptive statistics for every column
csvlook sales.csv | head -20   # Pretty-print with aligned columns

# Slice and dice
csvcut -c name,revenue sales.csv        # Select specific columns
csvcut -C id,notes sales.csv            # Exclude columns
csvgrep -c category -m "Electronics" sales.csv  # Filter rows by value

# Sort and analyze
csvsort -c revenue -r sales.csv | head -10  # Sort by revenue descending

# Convert between formats
csvjson sales.csv > sales.json         # CSV to JSON
in2csv sales.xlsx > sales.csv          # Excel to CSV
csvsql --db sqlite:///sales.db --insert sales.csv  # CSV to SQLite
csvformat -T sales.csv > sales.tsv     # CSV to TSV

# SQL queries on CSV data
csvsql --query "SELECT category, SUM(revenue) as total FROM sales GROUP BY category ORDER BY total DESC" sales.csv
```

**Real-world pipeline — cleaning messy survey data:**

```bash
# 1. Extract relevant columns
csvcut -c "Timestamp,Department,Satisfaction,Comments" raw_survey.csv > step1.csv

# 2. Filter out empty responses
csvgrep -c Satisfaction -r "^(1|2|3|4|5)$" step1.csv > step2.csv

# 3. Aggregate by department
csvsql --query "
  SELECT Department,
         COUNT(*) as responses,
         ROUND(AVG(CAST(Satisfaction AS FLOAT)), 2) as avg_satisfaction
  FROM step2
  GROUP BY Department
  ORDER BY avg_satisfaction DESC
" step2.csv | csvlook

# 4. Output as Markdown for a report
csvlook --no-inference step2.csv
```

csvkit's killer feature is `csvsql` — it loads CSV data into an in-memory SQLite database and runs real SQL queries. This makes complex aggregations and joins trivially easy, especially for analysts who already know SQL. The Excel integration (`in2csv`) is another standout — it handles `.xlsx` files without requiring Excel itself.

## xsv: Blazing-Fast Rust CSV Toolkit

xsv is written in Rust by Andrew Gallant (BurntSushi, also the author of ripgrep), and it's designed for one thing: raw speed. If you regularly process CSV files with millions of rows, xsv is the tool you want. It uses memory-mapped I/O and heavily optimized parsing to achieve throughput that Python can't match.

**Installation:**

```bash
# Download prebuilt binary (Linux x86_64)
curl -L -o xsv.tar.gz https://github.com/BurntSushi/xsv/releases/download/0.13.0/xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
tar xzf xsv.tar.gz
sudo mv xsv /usr/local/bin/

# macOS
brew install xsv

# Via Cargo (Rust)
cargo install xsv
```

**Core operations:**

```bash
# Get basic statistics (blazing fast even on 10M+ rows)
xsv stats sales.csv

# Frequency tables
xsv frequency sales.csv --select category --limit 10

# Search (regex)
xsv search -s description "refund" sales.csv

# Select columns
xsv select name,revenue sales.csv

# Sort
xsv sort -s revenue -R sales.csv | xsv table | head

# Join two CSV files
xsv join id users.csv id orders.csv

# Split huge files into chunks
xsv split -s 1000000 huge.csv split_dir/

# Index a CSV for fast random access
xsv index sales.csv
```

**Performance comparison (10M row CSV, 1.2GB):**

```bash
# csvkit: ~45 seconds
time csvstat huge.csv

# xsv: ~2 seconds (22x faster)
time xsv stats huge.csv

# xsv search: near-instantaneous with index
xsv index huge.csv
time xsv search -s status "failed" huge.csv  # milliseconds
```

xsv's `stats` command is orders of magnitude faster than csvkit's `csvstat` for large files because it uses SIMD-accelerated parsing and streams data without materializing Python objects. The `index` command creates a lightweight index file that enables near-instant random access — essential for repeatedly querying large datasets.

**The `xsv table` formatter is excellent for quick previews:**

```bash
xsv table sales.csv | head -20
# Produces aligned columns without csvlook's Python overhead
```

## Miller (mlr): The awk/sed for Structured Data

Miller is unique among CSV tools — it has its own domain-specific language (DSL) for data transformation that feels like a cross between awk, SQL, and a functional programming language. If you need complex multi-step transformations that would require nested Python loops, Miller's `put` and `filter` verbs express them in a fraction of the code.

**Installation:**

```bash
# Ubuntu/Debian
apt install miller

# macOS
brew install miller

# Prebuilt binary
curl -L -o mlr https://github.com/johnkerl/miller/releases/latest/download/mlr.linux.amd64
chmod +x mlr && sudo mv mlr /usr/local/bin/
```

**Core verbs:**

```bash
# Filter rows (awk-like)
mlr --csv filter '$revenue > 10000 && $status == "active"' sales.csv

# Compute new columns
mlr --csv put '$margin = $revenue - $cost; $margin_pct = $margin / $revenue * 100' sales.csv

# Aggregate
mlr --csv stats1 -a sum,mean,count -f revenue -g category sales.csv

# Grouped statistics (multiple aggregations)
mlr --csv stats2 -a corr,linreg-ols -f revenue,marketing_spend -g region sales.csv

# Sort
mlr --csv sort -nr revenue sales.csv

# Join (multi-key, multi-type)
mlr --csv join -j "user_id,date" -f orders.csv users.csv

# Reshape
mlr --csv reshape -r status -o item,value sales.csv

# Top N
mlr --csv top -n 10 -f revenue sales.csv
```

**Miller's DSL for complex transformations:**

```bash
mlr --csv put '
  $total = $quantity * $unit_price;
  $discount_amount = $total * $discount_rate / 100;
  $final = $total - $discount_amount;
  if ($final > 1000) {
    $tier = "premium";
  } elif ($final > 100) {
    $tier = "standard";
  } else {
    $tier = "basic";
  }
  $order_month = substr($order_date, 0, 7);
' orders.csv
```

Miller's key differentiator is its expression language — `put` and `filter` accept a full programming language with arithmetic, string manipulation, conditionals, and built-in functions (math, string, type conversion). This allows complex multi-step transformations in a single Miller command, where csvkit would require multiple piped commands or full SQL queries.

**Format conversion:**

```bash
# CSV to JSON
mlr --c2j cat sales.csv

# JSON to CSV
mlr --j2c cat sales.json

# CSV to Markdown table
mlr --c2m cat sales.csv

# Pretty-print with bar charts
mlr --c2p bar -f revenue sales.csv

# Any format to any format
mlr --icsv --ojsonl cat sales.csv    # CSV to JSON Lines
mlr --icsv --odkvp cat sales.csv     # CSV to key-value pairs
mlr --icsv --oxtab cat sales.csv     # CSV to vertical tabular
```

## Choosing the Right CSV Toolkit

The three tools excel in different scenarios:

- **Start with csvkit** if you're new to command-line data processing or frequently work with Excel files. The `csvsql` command makes complex queries accessible, and the Excel conversion handles real-world data formats.
- **Reach for xsv** when speed matters — processing files with millions of rows, building data pipelines that run on cron, or repeatedly querying large datasets. The `index` command combined with `search` makes it the fastest tool for exploratory analysis of large CSVs.
- **Use Miller** for complex, multi-step transformations that would be awkward to express as a pipeline of simpler commands. Its DSL handles arithmetic, conditional logic, and multi-key joins that csvkit and xsv can't express without external scripts.

A typical data workflow might use all three: xsv for initial exploration (fast stats and previews), csvkit for Excel imports and SQL queries, and Miller for the final transformation and output formatting.

## FAQ

### How does Miller compare to using pandas in Python?

Miller runs as a streaming processor — it processes one record at a time, never loading the entire dataset into memory. For simple transformations, Miller is 5-10x faster than pandas. For complex group-by aggregations, pandas may be faster if the data fits in memory, but Miller handles out-of-core datasets that would crash pandas. Miller's command-line interface is also more composable than Python scripts for ad-hoc analysis.

### Can csvkit handle non-UTF-8 encodings?

Yes — csvkit uses Python's encoding detection and handles Latin-1, UTF-16, and other common encodings. Use `csvstat` to detect encoding issues: it reports character counts and flags non-ASCII values. For explicit encoding, pipe through `iconv` first: `iconv -f LATIN1 -t UTF-8 latin1.csv | csvstat`.

### Is xsv still maintained? The last release was April 2025.

xsv is feature-complete and stable — the core CSV parsing, stats, search, join, and indexing functionality has been battle-tested for years. Andrew Gallant focuses maintenance on critical bug fixes. For new CSV features, check Miller which is actively developed with bi-weekly releases through June 2026.

### What's the best tool for converting between CSV and JSON?

Miller has the most comprehensive format support — it handles CSV, TSV, JSON, JSON Lines, DKVP, NIDX, XTAB, and Markdown. For simple CSV-to-JSON conversion, csvkit's `csvjson` works well. Miller's `--j2c` and `--c2j` flags handle nested JSON structures that csvkit doesn't support.

### Can these tools handle CSV files with embedded newlines in quoted fields?

Yes — all three tools properly handle RFC 4180-compliant CSV with quoted fields containing newlines, commas, and escaped quotes. Miller and csvkit auto-detect quoting. xsv requires consistent quoting and may fail on malformed CSV that csvkit would handle gracefully.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CSV Processing Tools: csvkit vs xsv vs Miller (mlr)",
  "description": "Compare csvkit, xsv, and Miller for command-line CSV processing — speed benchmarks, SQL queries, multi-format conversion, and real-world data transformation pipelines.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
