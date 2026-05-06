---
title: "Self-Hosted Data Profiling & Quality: Great Expectations vs Soda Core vs Deequ (2026)"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "data-engineering", "data-quality", "testing"]
draft: false
description: "Compare Great Expectations, Soda Core, and Deequ for self-hosted data profiling and quality testing. Complete setup guides, pipeline integration, and quality check strategies."
---

As data pipelines grow in complexity, ensuring data quality becomes a critical operational requirement. Broken schemas, missing values, and unexpected distributions can silently corrupt downstream dashboards, models, and reports. Self-hosted data profiling tools let you define, test, and monitor data quality checks entirely within your own infrastructure — without sending sensitive data to external SaaS platforms.

This guide compares three leading open-source data profiling and quality frameworks: **Great Expectations**, **Soda Core**, and **Deequ**. We cover architecture, configuration patterns, CI/CD integration, and real-world use cases so you can build robust data quality gates into your pipelines.

## What Is Data Profiling?

Data profiling is the process of examining data sources to understand their structure, content, and quality. It answers questions like:

- What columns exist and what data types do they contain?
- How many null or empty values are in each column?
- What are the min, max, mean, and standard deviation for numeric columns?
- Are there duplicate rows or unexpected value distributions?
- Does the data match expected business rules (e.g., "age must be between 0 and 150")?

Automated data profiling tools take these manual checks and codify them into repeatable tests that run every time new data arrives in your pipeline.

## Architecture Overview

### Great Expectations

Great Expectations is a Python-based data validation framework that uses a declarative "expectation" syntax to define data quality rules. It supports pandas DataFrames, Spark DataFrames, and SQL databases (PostgreSQL, MySQL, BigQuery, Redshift, Snowflake, and more).

Key characteristics:
- Python-first with a rich expectation library (50+ built-in checks)
- Supports batch processing via Data Docs (HTML reports)
- Integrates with Airflow, dbt, Prefect, and Dagster
- Data Docs provide shareable, versioned quality reports
- Open-source core with optional cloud features

### Soda Core

Soda Core is the open-source engine behind Soda's data quality platform. It uses a YAML-based configuration format called "Soda Checks Language" (SCL) to define quality rules. It connects to various data sources via Soda Cloud connectors or direct JDBC/ODBC connections.

Key characteristics:
- YAML-based check definitions (simple, readable syntax)
- Supports 15+ data sources including Spark, DuckDB, and Athena
- Produces machine-readable scan results (JSON) for CI/CD integration
- Lightweight CLI tool, easy to embed in pipelines
- Open-source core with optional Soda Cloud dashboard

### Deequ

Deequ is a Scala library built on Apache Spark, developed by Amazon Web Services. It defines "unit tests for data" using a fluent API and computes data quality metrics at Spark-scale. It is designed for large datasets that require distributed processing.

Key characteristics:
- Built on Apache Spark for distributed data processing
- Fluent Scala/Java/Python API for defining checks
- Computes metrics (completeness, uniqueness, compliance) at scale
- VerificationSuite runs multiple checks in a single Spark job
- Best suited for teams already running Spark infrastructure

## Feature Comparison

| Feature | Great Expectations | Soda Core | Deequ |
|---------|--------------------|-----------|-------|
| **Language** | Python | Python / CLI | Scala / Java / Python |
| **Processing Engine** | Pandas / Spark / SQL | Native connectors | Apache Spark |
| **Check Syntax** | Python DSL | YAML (SCL) | Fluent API (Scala/Java) |
| **Built-in Checks** | 50+ | 30+ | 20+ |
| **Data Sources** | 15+ | 15+ | Spark-only (any Spark source) |
| **CI/CD Integration** | CLI + Data Docs | CLI + JSON output | Spark job output |
| **Visual Reports** | HTML Data Docs | Soda Cloud (paid) | Custom (via Spark UI) |
| **Data Profiling** | Auto-profile + manual | Auto-profile + manual | Metric computation |
| **Anomaly Detection** | No (rule-based only) | Yes (with Soda Cloud) | No (rule-based only) |
| **Max Dataset Size** | RAM-limited (pandas) / Spark-scale | Source-dependent | Spark-scale (unlimited) |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Stars (GitHub)** | 11,460+ | 2,340+ | 3,610+ |
| **Last Active** | May 2026 | May 2026 | May 2026 |

## Configuration Examples

### Great Expectations

Install and initialize:

```bash
pip install great_expectations
great_expectations init
```

Define expectations in Python:

```python
import great_expectations as gx
from great_expectations.core import ExpectationSuite

# Connect to your data source
context = gx.get_context()
validator = context.sources.pandas_default.read_csv("data/customers.csv")

# Define quality checks
validator.expect_column_values_to_not_be_null("customer_id")
validator.expect_column_values_to_be_unique("customer_id")
validator.expect_column_values_to_be_between("age", min_value=0, max_value=150)
validator.expect_column_values_to_match_regex("email", r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
validator.expect_table_row_count_to_be_between(min_value=100, max_value=1000000)

# Run validation
results = validator.validate()
print(results.success)  # True if all checks pass
```

Generate shareable Data Docs:

```bash
great_expectations docs build
```

This produces a static HTML site with colored pass/fail indicators, histograms, and value distributions — perfect for sharing with stakeholders.

### Soda Core

Install and create a checks file:

```bash
pip install soda-core-postgres
```

Create `checks/customers.yml`:

```yaml
checks for customers:
  - row_count > 100
  - missing_count(customer_id) = 0
  - duplicate_count(customer_id) = 0
  - invalid_count(email) = 0:
      valid format: email
  - avg(age) between 18 and 80
  - min(revenue) >= 0
```

Run the scan:

```bash
soda scan -d postgres_datasource checks/customers.yml
```

Output includes a summary with pass/fail status per check and a JSON file for CI/CD integration:

```bash
soda scan -d postgres_datasource checks/customers.yml --variable FILENAME=scan_output.json
```

### Deequ

Add Deequ to your Spark project (Maven):

```xml
<dependency>
    <groupId>com.amazon.deequ</groupId>
    <artifactId>deequ</artifactId>
    <version>2.0.7-spark-3.5</version>
</dependency>
```

Define checks in Scala:

```scala
import com.amazon.deequ.VerificationSuite
import com.amazon.deequ.checks.{Check, CheckLevel}

val verificationResult = VerificationSuite()
  .onData(df)
  .addCheck(
    Check(CheckLevel.Error, "Customer Data Quality")
      .hasSize(_ >= 100)
      .isComplete("customer_id")
      .isUnique("customer_id")
      .isContainedIn("status", Seq("active", "inactive", "suspended"))
      .isNonNegative("revenue")
      .satisfies("email LIKE '%@%.%'", "valid_email_format")
  )
  .run()

println(verificationResult.status) // Success or Error
```

For Python users, Deequ provides a PySpark wrapper:

```bash
pip install pydeequ
```

```python
from pydeequ.verification import VerificationSuite, Analysis
from pydeequ.checks import Check, CheckLevel

check = Check(spark, CheckLevel.Error, "Customer Validation")
check_result = (check
    .hasSize(lambda x: x >= 100)
    .isComplete("customer_id")
    .isUnique("customer_id")
    .isContainedIn("status", ["active", "inactive", "suspended"])
    .run()
)

print(check_result.status)
```

## Integration with Data Pipelines

### Airflow + Great Expectations

```python
from airflow import DAG
from great_expectations_provider.operators.great_expectations import GreatExpectationsOperator
from datetime import datetime

with DAG("data_quality_checks", start_date=datetime(2026, 1, 1), schedule="@daily") as dag:
    validate_customers = GreatExpectationsOperator(
        task_id="validate_customers",
        data_context_root_dir="great_expectations",
        checkpoint_name="customers_checkpoint",
        fail_task_on_validation_failure=True,
    )

    validate_orders = GreatExpectationsOperator(
        task_id="validate_orders",
        data_context_root_dir="great_expectations",
        checkpoint_name="orders_checkpoint",
        fail_task_on_validation_failure=True,
    )

    validate_customers >> validate_orders
```

### dbt + Soda Core

Soda Core integrates directly with dbt projects using the same connection:

```bash
# Install Soda Core with dbt support
pip install soda-core-dbt

# Run Soda checks against dbt models
soda scan -d dbt_datasource -V DBT_PROJECT_DIR=./my_dbt_project checks/models.yml
```

### Spark + Deequ in EMR/Databricks

```python
# In a Databricks notebook or EMR step
from pydeequ.analyzers import Analysis

analysis_result = (Analysis()
    .onData(df)
    .addAnalyzer(Size())
    .addAnalyzer(Completeness("customer_id"))
    .addAnalyzer(Uniqueness("customer_id"))
    .run()
)

metrics = AnalysisRunner(spark).onData(df).addAnalyzers([...]).run()
```

## Why Self-Host Your Data Profiling?

Data quality tools that run in the cloud require sending your data or at least metadata about your data to external servers. For organizations handling regulated data (GDPR, HIPAA, PCI-DSS), this creates compliance risk and audit complexity. Self-hosted data profiling keeps everything in your own infrastructure:

- **Full data sovereignty** — raw data, metrics, and quality reports never leave your network
- **No per-row or per-scan pricing** — run unlimited quality checks without metering costs
- **Custom quality rules** — encode business-specific validation logic that SaaS platforms do not support
- **Pipeline-native execution** — run quality checks as pipeline steps, not as separate SaaS API calls
- **Audit trail retention** — keep historical quality reports indefinitely for compliance audits
- **Integration with existing tools** — connect directly to your [data pipeline](../meltano-vs-airbyte-vs-singer-self-hosted-data-pipeline-guide-2026/) and [data warehouse](../2026-04-25-duckdb-vs-apache-doris-vs-apache-pinot-self-hosted-ola/) without network hops to external platforms

For teams already running self-hosted [data catalog](../amundsen-vs-datahub-vs-openmetadata-self-hosted-data-catalog-guide/) solutions, adding data profiling creates a complete in-house data governance stack.

## FAQ

### Which tool is easiest to get started with?

Great Expectations has the most approachable learning curve. The `great_expectations init` command scaffolds a project, and the Python DSL reads like natural language ("expect column values to be between 0 and 150"). Soda Core's YAML syntax is even simpler but requires understanding the SCL check language. Deequ requires Spark infrastructure, making it the most complex to set up.

### Can these tools handle real-time data streams?

None of the three tools are designed for real-time stream processing. Great Expectations and Soda Core run as batch checks against static datasets or database snapshots. Deequ runs on Spark batches. For real-time data quality monitoring, consider combining these with streaming tools like Apache Flink or Kafka Streams.

### How do I handle schema evolution in my quality checks?

Great Expectations supports "expectation suites" that you version alongside your code. When a schema changes, you create a new suite version and migrate existing checks. Soda Core checks reference columns by name, so they automatically fail when columns are missing — alerting you to schema changes. Deequ checks are defined in code and must be updated when schemas change.

### Can I use Great Expectations without a database connection?

Yes. Great Expectations works with pandas DataFrames in memory, CSV files, Parquet files, and Spark DataFrames. You do not need a database connection to run checks on flat files. This is ideal for profiling data during the ingestion phase before it lands in a database.

### Does Soda Core require Soda Cloud?

No. Soda Core is fully functional as a standalone CLI tool. Soda Cloud provides a web dashboard for visualizing scan results, setting up alerts, and managing checks across teams — but all quality checks run locally. The cloud component is optional.

### How does Deequ compare to Great Expectations for large datasets?

Deequ runs on Apache Spark and can process petabyte-scale datasets by distributing computation across a cluster. Great Expectations can also use Spark as an execution engine, but its primary interface is designed for pandas (in-memory) and SQL databases. For teams already running Spark, Deequ offers a more natural integration. For teams using Python and SQL databases, Great Expectations is more versatile.

### Can I schedule quality checks automatically?

Yes. All three tools run as CLI commands or library calls, making them easy to schedule with cron, Airflow, Prefect, or Dagster. Great Expectations has a built-in checkpoint system that can run on a schedule. Soda Core scans can be triggered via CI/CD pipelines. Deequ runs as a Spark job, which can be scheduled via Oozie, Airflow, or cloud schedulers.

### What happens when a quality check fails?

All three tools return a pass/fail status. Great Expectations produces a validation result object with per-expectation details and generates HTML Data Docs. Soda Core outputs a JSON scan result file and can be configured to exit with a non-zero code on failure (blocking CI/CD pipelines). Deequ returns a VerificationResult with Error or Warning level per check.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Data Profiling & Quality: Great Expectations vs Soda Core vs Deequ (2026)",
  "description": "Compare Great Expectations, Soda Core, and Deequ for self-hosted data profiling and quality testing. Complete setup guides, pipeline integration, and quality check strategies.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
