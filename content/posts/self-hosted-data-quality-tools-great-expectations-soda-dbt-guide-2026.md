---
title: "Self-Hosted Data Quality Tools: Great Expectations vs Soda Core vs dbt Tests 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "data-engineering"]
draft: false
description: "Complete guide to self-hosted data quality tools in 2026. Compare Great Expectations, Soda Core, and dbt tests for validating data pipelines. Installation, configuration, and real-world examples."
---

Data pipelines break silently. A column changes type upstream, a date field gets corrupted, or a critical lookup table goes empty. Without automated data quality checks, these issues cascade into dashboards, reports, and machine learning models before anyone notices. By the time someone flags bad numbers, the damage is already done.

This is where data quality frameworks come in. Tools like **Great Expectations**, **Soda Core**, and **dbt tests** let you define expectations about your data, run validations automatically, and get alerted when something goes wrong. All three are open-source, can be fully self-hosted, and integrate into existing CI/CD pipelines.

In this guide, we will compare these three tools head-to-head, show you how to install and configure each one, and help you pick the right fit for your data stack.

## Why Self-Host Your Data Quality Framework

Data quality is fundamentally about trust. When you send your data profiles, validation results, and schema information to a third-party cloud service, you are creating several problems:

**Sensitive data exposure.** Data quality tools need to read your actual data to validate it. That means column distributions, value ranges, null rates, and sometimes even sample records are transmitted to an external service. For healthcare, finance, or any regulated industry, this is a non-starter.

**Latency and coupling.** Cloud-based validation introduces network round-trips for every check. In a high-throughput pipeline processing millions of rows, this adds up. Self-hosted validation runs directly against your database or data lake with zero network overhead.

**Cost at scale.** SaaS data quality platforms charge by volume — rows scanned, checks run, or storage used. A busy pipeline can generate thousands of validation runs per day. Self-hosted tools have no per-row fees.

**Integration depth.** When the tool runs on your infrastructure, it can connect to your internal databases, message queues, and alerting systems without requiring public endpoints, VPN tunnels, or firewall exceptions.

**Full audit trail.** Validation results stay in your control. You can log them to your own monitoring stack, archive them for compliance, and correlate them with your deployment history.

## Great Expectations: The Most Mature Framework

Great Expectations (GX) is the most widely adopted open-source data quality framework. Developed by Superconductive Health and now maintained as an independent open-source project, it introduced the concept of "expectations" — declarative assertions about what your data should look like.

### Core Concepts

An **expectation** is a single validation rule. Examples:

- `expect_column_values_to_not_be_null` — checks that a column has no missing values
- `expect_column_values_to_be_between` — validates numeric ranges
- `expect_table_row_count_to_be_between` — ensures a table is not empty or unexpectedly large
- `expect_column_values_to_match_regex` — validates string patterns

Expectations are grouped into **Expectation Suites**, which represent the full set of rules for a particular dataset. A **Validation** is the act of running a suite against actual data and producing a **Validation Result** — a detailed JSON report of what passed, what failed, and why.

### Installation and Setup

Great Expectations is a Python package. The simplest way to get started is with pip:

```bash
pip install great_expectations
```

Initialize a new GX project:

```bash
great_expectations init
```

This creates a `great_expectations/` directory with the standard project structure:

```
great_expectations/
├── expectations/          # JSON expectation suite files
├── checkpoints/           # Checkpoint configurations
├── plugins/               # Custom expectation implementations
├── uncommitted/           # Git-ignored (data_docs, credentials)
│   ├── data_docs/         # HTML validation reports
│   └── config_variables.yml
└── great_expectations.yml # Main configuration
```

### Docker Compose Setup

For production deployments, run Great Expectations as part of your pipeline infrastructure:

```yaml
version: "3.8"
services:
  gx-runner:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./great_expectations:/app/great_expectations
      - ./pipelines:/app/pipelines
    environment:
      - GX_HOME=/app/great_expectations
    command: >
      bash -c "
        pip install great_expectations[sqlalchemy] pandas &&
        python /app/pipelines/validate.py
      "
    networks:
      - data-network

networks:
  data-network:
    driver: bridge
```

### Writing Your First Expectation Suite

Create a suite programmatically:

```python
import great_expectations as gx

# Connect to a context
context = gx.get_context()

# Create a new expectation suite
suite = context.add_or_update_expectation_suite("sales_data")

# Add expectations
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id")
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="total_amount", min_value=0, max_value=100000
    )
)
suite.add_expectation(
    gx.expectations.ExpectColumnDistinctValuesToContainSet(
        column="status", value_set=["pending", "shipped", "delivered", "cancelled"]
    )
)
suite.add_expectation(
    gx.expectations.ExpectTableRowCountToBeBetween(min_value=1, max_value=None)
)

context.save_expectation_suite(suite)
```

Run validation against a Pandas DataFrame or SQL database:

```python
import great_expectations as gx

context = gx.get_context()
validator = context.get_validator(
    batch_definition_name="daily_sales",
    expectation_suite_name="sales_data",
    # For SQL:
    # datasource_name="postgres",
    # data_asset_name="public.sales",
)

results = validator.validate()
print(f"Success: {results.success}")
print(f"Passed: {results.result.success_count}")
print(f"Failed: {results.result.unexpected_count}")

# Save results as checkpoint
context.build_data_docs()
```

### Built-in Data Docs

Great Expectations generates beautiful HTML reports automatically:

```bash
great_expectations docs build
```

These reports show every expectation, its result, unexpected values, and a pass/fail summary. You can host them on any static file server, internal wiki, or S3 bucket with static website hosting.

## Soda Core: YAML-First Data Quality

Soda Core takes a different approach. Instead of Python code, you define checks in YAML files called **SodaCL** (Soda Checks Language). This makes it accessible to data analysts who may not be comfortable writing Python, while still being powerful enough for engineers.

### Core Concepts

A **check** in SodaCL is a single assertion. Checks are organized in YAML files that reference a data source. Soda Core runs checks against the actual database by generating and executing SQL queries — it does not pull data into memory.

Key check types:

- `missing_count(column) = 0` — no null values allowed
- `values in (column) must be ['active', 'inactive']` — enum validation
- `row_count > 1000` — minimum table size
- `freshness(column) < 1h` — data recency check
- `schema changes` — detect unexpected column additions or removals

### Installation

```bash
pip install soda-core-postgres
# Or for other databases:
# pip install soda-core-snowflake
# pip install soda-core-bigquery
# pip install soda-core-spark
# pip install soda-core-duckdb
```

### Configuration File

Create a `configuration.yml` that defines your data sources:

```yaml
data_source my_postgres:
  type: postgres
  connection:
    host: localhost
    port: 5432
    username: ${POSTGRES_USER}
    password: ${POSTGRES_PASSWORD}
    database: analytics
    schema: public
```

Note that credentials are referenced as environment variables — never hardcode them in the YAML file.

### Writing Checks

Create a `checks/sales_checks.yml`:

```yaml
checks for sales_orders:
  - row_count > 1000
  - missing_count(order_id) = 0
  - duplicate_count(order_id) = 0
  - min(total_amount) >= 0
  - max(total_amount) <= 100000
  - values in (status) must be ['pending', 'shipped', 'delivered', 'cancelled']
  - freshness(created_at) < 24h

checks for customers:
  - schema changes:
      warn:
        when adds:
          - email
        when deletes:
          - customer_id
          - name
  - row_count > 500
  - missing_count(email) < 5
```

### Running Checks

```bash
soda scan -d configuration.yml -c checks/sales_checks.yml
```

Soda Core connects to the database, translates each check into SQL, executes the queries, and returns a summary:

```
Scan summary:
5/6 checks PASSED:
  sales_orders in my_postgres
    ✓ row_count > 1000
    ✓ missing_count(order_id) = 0
    ✓ duplicate_count(order_id) = 0
    ✓ min(total_amount) >= 0
    ✓ values in (status) must be [...]
1/6 checks FAILED:
  sales_orders in my_postgres
    ✗ freshness(created_at) < 24h
      freshness = 36h (last refresh: 2026-04-14 08:00:00)
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  soda-scanner:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./soda:/app/soda
    environment:
      - POSTGRES_USER=analytics
      - POSTGRES_PASSWORD=${PG_PASSWORD}
    command: >
      bash -c "
        pip install soda-core-postgres &&
        soda scan -d /app/soda/configuration.yml /app/soda/checks/
      "
    networks:
      - data-network
```

Soda also offers **Soda Cloud**, a hosted dashboard for monitoring results. But the core scanning engine is fully open-source and self-hosted. For a self-hosted dashboard, you can parse the JSON scan output and feed it into Grafana, Prometheus, or any monitoring system.

## dbt Tests: Quality Checks Inside Your Transformation Layer

dbt (data build tool) is primarily a SQL transformation framework, but its built-in testing capabilities make it a powerful data quality tool for teams already using dbt for their ELT pipelines.

### Core Concepts

dbt tests are defined in YAML files alongside your models. They run as SQL queries against your warehouse and are executed as part of the `dbt test` command. Tests can be **generic** (built-in, parameterized) or **singular** (custom SQL queries).

Built-in generic tests:

- `not_null` — column has no nulls
- `unique` — all values in a column are distinct
- `accepted_values` — values must be from a specified list
- `relationships` — foreign key integrity check

### Installation

```bash
pip install dbt-postgres
# Or: dbt-snowflake, dbt-bigquery, dbt-duckdb, dbt-redshift
```

Initialize a project:

```bash
dbt init data_quality_project
cd data_quality_project
```

### Writing Tests

In your `models/schema.yml`:

```yaml
version: 2

models:
  - name: stg_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: status
        tests:
          - accepted_values:
              values: ['pending', 'shipped', 'delivered', 'cancelled']
      - name: total_amount
        tests:
          - not_null
      - name: customer_id
        tests:
          - relationships:
              to: ref('stg_customers')
              field: customer_id

  - name: stg_customers
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
      - name: email
        tests:
          - not_null
```

### Custom SQL Tests

For checks that go beyond the built-in tests, create singular tests in `tests/`:

```sql
-- tests/assert_no_negative_refunds.sql
select order_id, refund_amount
from {{ ref('fct_refunds') }}
where refund_amount < 0
```

dbt treats any SQL file in the `tests/` directory that returns zero rows as a passing test. If rows are returned, the test fails and those rows are shown in the output.

### Running Tests

```bash
dbt test --select stg_orders
```

Output:

```
1 of 6 START test not_null_stg_orders_order_id ...................... [PASS]
2 of 6 START test unique_stg_orders_order_id ........................ [PASS]
3 of 6 START test accepted_values_stg_orders_status ................. [PASS]
4 of 6 START test not_null_stg_orders_total_amount .................. [PASS]
5 of 6 START test relationships_stg_orders_customer_id .............. [PASS]
6 of 6 START test custom_no_negative_refunds ........................ [PASS]

Finished running 6 tests in 12.3s.
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  dbt-runner:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./dbt_project:/app
    environment:
      - DBT_PROFILES_DIR=/app
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=analytics
      - POSTGRES_USER=analytics
      - POSTGRES_PASSWORD=${PG_PASSWORD}
    command: >
      bash -c "
        pip install dbt-postgres &&
        dbt deps &&
        dbt run &&
        dbt test
      "
    networks:
      - data-network
```

### dbt Package for Advanced Tests

The `dbt_expectations` package extends dbt with Great Expectations-style tests:

```yaml
# packages.yml
packages:
  - package: calogica/dbt_expectations
    version: [">=0.10.0"]
```

After running `dbt deps`, you can use tests like:

```yaml
- name: stg_orders
  columns:
    - name: created_at
      tests:
        - dbt_expectations.expect_column_values_to_be_of_type:
            column_type: timestamp
        - dbt_expectations.expect_row_value_to_have_recent_data:
            datepart: day
            interval: 1
        - dbt_expectations.expect_column_distinct_count_to_be_greater_than:
            value: 100
```

## Head-to-Head Comparison

| Feature | Great Expectations | Soda Core | dbt Tests |
|---------|-------------------|-----------|-----------|
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Definition format** | Python API | YAML (SodaCL) | YAML + SQL |
| **Execution engine** | Python (reads data into memory or uses SQLAlchemy) | SQL (generates queries, runs on database) | SQL (runs as warehouse queries) |
| **Built-in checks** | 90+ expectation types | 30+ check types | 4 generic tests (extensible via packages) |
| **Schema validation** | Yes (expect_column_to_exist) | Yes (schema changes check) | Limited (via dbt_expectations) |
| **Freshness checks** | Custom expectation | Built-in freshness check | Via dbt_expectations package |
| **Data profiling** | Full profiling (distributions, histograms) | Limited (via metrics) | No built-in profiling |
| **CI/CD integration** | Checkpoints + CLI | CLI + scan JSON output | `dbt test` + CI plugins |
| **Reporting** | HTML Data Docs (built-in) | CLI output + JSON | CLI output + docs (dbt docs) |
| **Learning curve** | Moderate (Python knowledge needed) | Low (YAML only) | Low (if already using dbt) |
| **Best for** | Data engineers who want programmatic control | Analysts who prefer declarative YAML | Teams already using dbt for transformations |

## Choosing the Right Tool

**Pick Great Expectations if:** You need the most comprehensive framework with the deepest feature set. Its Python API gives you unlimited flexibility — you can write custom expectations that check anything expressible in code. The Data Docs feature provides excellent out-of-the-box reporting. It is the best choice when you have dedicated data engineers and complex validation requirements.

**Pick Soda Core if:** You want a low-barrier entry point. The YAML-based SodaCL is easy to read and write, and the fact that it generates SQL rather than pulling data into memory makes it efficient for large datasets. It is ideal for teams where analysts need to write and maintain checks without Python expertise.

**Pick dbt tests if:** You are already running dbt for your transformations. Adding tests to your existing models requires zero additional infrastructure. The `dbt_expectations` package bridges the gap to more advanced checks. This is the path of least resistance for dbt-centric stacks.

## Real-World Pipeline Integration

Here is how you would wire data quality checks into a production pipeline that runs daily:

```yaml
# pipeline.yml - Airflow or cron-triggered
version: "3.8"
services:
  data-quality:
    image: python:3.11-slim
    volumes:
      - ./checks:/app/checks
      - ./great_expectations:/app/great_expectations
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/analytics
    command: >
      bash -c "
        pip install great_expectations[sqlalchemy] soda-core-postgres &&
        echo 'Running GX validations...' &&
        python /app/great_expectations/validate.py &&
        echo 'Running Soda checks...' &&
        soda scan -d /app/checks/configuration.yml /app/checks/ &&
        echo 'All quality checks complete'
      "
```

For alerting, parse the validation results and send notifications:

```python
import json, smtplib, requests

def alert_on_failures(results):
    failures = [r for r in results if not r['success']]
    if not failures:
        return

    message = f"Data quality alert: {len(failures)} checks failed\n\n"
    for f in failures:
        message += f"- {f['expectation_type']} on {f['column']}\n"

    # Send to Slack
    requests.post(SLACK_WEBHOOK, json={"text": message})

    # Or send email
    # send_email("data-quality@company.com", "DQ Alert", message)
```

## Conclusion

Data quality is not optional. Every pipeline that moves, transforms, or stores data needs automated validation. The question is not whether to implement data quality checks, but which tool fits your team's skills and existing infrastructure.

Great Expectations offers the most comprehensive feature set and is the industry standard for programmatic data validation. Soda Core provides the simplest entry point with its YAML-based check language. dbt tests integrate seamlessly into existing dbt workflows with minimal overhead.

All three are open-source, self-hostable, and free to run at any scale. The best choice depends on whether your team writes more Python, more YAML, or more SQL — and whether you want a standalone validation layer or something embedded in your transformation pipeline.
