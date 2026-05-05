---
title: "Self-Hosted Data Contract Validation: Data Contract CLI vs Soda Core vs dbt Tests 2026"
date: 2026-05-09T09:30:00Z
tags: ["data-quality", "data-contracts", "data-engineering", "validation", "data-pipeline", "governance"]
draft: false
---

Data contracts define the schema, quality expectations, and SLAs between data producers and consumers. As organizations scale their data pipelines, informal agreements about data structure break down — column types change without notice, null values appear in non-nullable fields, and downstream dashboards silently return wrong results. This guide compares three self-hosted tools for defining, validating, and enforcing data contracts across your data infrastructure.

## What Are Data Contracts?

A data contract is a formal agreement between a data producer (e.g., an application team writing to a database) and data consumers (e.g., analytics teams building dashboards). It specifies:

- **Schema**: Column names, types, constraints, and allowed values
- **Quality rules**: Null thresholds, freshness requirements, uniqueness guarantees
- **Terms**: Ownership, update frequency, deprecation policies
- **SLAs**: Maximum acceptable downtime, data freshness targets

Without data contracts, a producer team changing a column type from `INT` to `VARCHAR` can break dozens of downstream pipelines before anyone notices.

## Comparison Overview

| Feature | Data Contract CLI | Soda Core | dbt Tests |
|---------|-------------------|-----------|-----------|
| Contract definition format | YAML | YAML + SodaCL | YAML (dbt schema.yml) |
| Schema validation | Yes (JSON Schema, SQL DDL) | Yes (via checks) | Yes (test macros) |
| Data quality checks | Built-in | Extensive (SodaCL) | Built-in + custom SQL |
| Freshness monitoring | Yes | Yes | Yes (source freshness) |
| CI/CD integration | GitHub Actions, GitLab CI | GitHub Actions, CI | Native (dbt Cloud/CI) |
| Alerting | CLI exit codes, webhooks | Soda Cloud, webhooks | dbt Slack/Discord hooks |
| Supported databases | PostgreSQL, MySQL, BigQuery, Snowflake, DuckDB | 15+ data platforms | Any dbt-supported adapter |
| Open source | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| GitHub Stars | 870+ | 2,300+ | 8,500+ (dbt-core) |

## Data Contract CLI: Contract-First Data Engineering

[Data Contract CLI](https://github.com/datacontract/datacontract-cli) (870+ GitHub stars) is a purpose-built tool for defining and validating data contracts. It uses a YAML-based contract format that describes schemas, quality rules, and service level agreements, then validates actual data against those contracts.

### Contract Definition

A data contract in YAML format:

```yaml
dataContractSpecification: 1.1.0
id: orders-data-contract
info:
  title: Orders Data Contract
  version: 1.0.0
  description: Contract for the orders table in the e-commerce database
  owner: ecommerce-team
  contact:
    name: Data Engineering Team
    email: data-team@company.com

servers:
  production:
    type: postgres
    host: db.production.internal
    port: 5432
    database: ecommerce
    schema: public

models:
  orders:
    description: Customer orders
    fields:
      order_id:
        type: varchar
        primaryKey: true
        required: true
        unique: true
        pattern: "ORD-[0-9]{8}"
      customer_id:
        type: varchar
        required: true
        references: customers.customer_id
      total_amount:
        type: decimal
        minimum: 0
        required: true
      status:
        type: varchar
        enum: [pending, processing, shipped, delivered, cancelled]
        required: true
      created_at:
        type: timestamp
        required: true
        description: Order creation timestamp

quality:
  type: SodaCL
  checks:
    - orders:
        row_count >= 1000
    - orders:
        missing_count(order_id) = 0
    - orders:
        duplicate_count(order_id) = 0
    - orders:
          freshness(created_at) < 24h
```

### Docker Compose for CI/CD Validation

```yaml
version: "3.8"

services:
  datacontract-validator:
    image: datacontract/cli:latest
    volumes:
      - ./contracts:/contracts
      - ./results:/results
    entrypoint: ["datacontract"]
    command: ["test", "/contracts/orders.yaml", "--format", "json", "--output", "/results/orders-result.json"]
    depends_on:
      - postgres

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=ecommerce
      - POSTGRES_USER=validator
      - POSTGRES_PASSWORD=validatorpass
    volumes:
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U validator"]
      interval: 5s
      timeout: 5s
      retries: 5
```

### CI/CD Pipeline Integration

```yaml
# .github/workflows/data-contract.yaml
name: Validate Data Contracts
on:
  push:
    paths:
      - "contracts/**/*.yaml"
  schedule:
    - cron: "0 */4 * * *"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run data contract tests
        run: |
          docker run --rm             -v ${{ github.workspace }}/contracts:/contracts             datacontract/cli:latest test /contracts/
      - name: Publish results
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }}             -H "Content-Type: application/json"             -d '{"text": "Data contract validation failed!"}'
```

## Soda Core: Comprehensive Data Quality Engine

[Soda Core](https://github.com/sodadata/soda-core) (2,300+ GitHub stars) is a data quality engine that scans datasets for anomalies, schema changes, and quality violations. While Soda started as a cloud service, Soda Core is fully open source and runs entirely self-hosted.

### SodaCL (Soda Checks Language)

SodaCL provides a declarative language for expressing data quality checks:

```yaml
checks for orders:
  - row_count > 1000
  - missing_count(order_id) = 0
  - duplicate_count(order_id) = 0
  - invalid_count(status) = 0:
      valid values: [pending, processing, shipped, delivered, cancelled]
  - freshness(created_at) < 24h
  - schema:
      name: orders
      must have:
        fields:
          order_id:
            type: character varying
            variable: true
          total_amount:
            type: numeric
            variable: true

checks for customers:
  - row_count > 500
  - missing_count(email) < row_count * 0.05  # < 5% missing emails
  - duplicate_count(customer_id) = 0
```

### Docker Compose for Soda Core

```yaml
version: "3.8"

services:
  soda-core:
    image: sodadata/soda-core:latest
    volumes:
      - ./soda:/soda
      - ./configuration:/config
    entrypoint: ["soda"]
    command: ["scan", "-d", "production", "-c", "/config/configuration.yml", "/soda/checks/"]
    environment:
      - SODA_LOG_LEVEL=info

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=analytics
      - POSTGRES_USER=soda
      - POSTGRES_PASSWORD=sodapass
    ports:
      - "5432:5432"
```

### Soda Configuration

```yaml
# configuration.yml
data_source production:
  type: postgres
  connection:
    host: db.production.internal
    port: 5432
    username: soda_reader
    password: ${SODA_PG_PASSWORD}
    database: analytics
    schema: public

soda_cloud:
  # Optional: connect to Soda Cloud for dashboards
  # Leave empty for fully self-hosted operation
```

### Running Soda Scans

```bash
# Run all checks
soda scan -d production -c configuration.yml checks/

# Run with JSON output for CI/CD
soda scan -d production -c configuration.yml   --format json --output scan-results.json checks/

# Check exit code (0 = pass, non-zero = fail)
echo $?
```

## dbt Tests: Transformation-Native Validation

dbt (data build tool) includes built-in testing capabilities that serve as lightweight data contracts. While dbt is primarily a transformation tool, its test framework validates data quality as part of the ELT pipeline.

### dbt Schema and Test Definitions

```yaml
# models/schema.yml
version: 2

models:
  - name: stg_orders
    description: Staged orders data from the raw source
    columns:
      - name: order_id
        data_type: varchar
        tests:
          - unique
          - not_null
      - name: customer_id
        data_type: varchar
        tests:
          - not_null
          - relationships:
              to: ref('stg_customers')
              field: customer_id
      - name: total_amount
        data_type: decimal
        tests:
          - not_null
          - accepted_values:
              values: ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
              quote: false
      - name: created_at
        data_type: timestamp
        tests:
          - not_null

sources:
  - name: ecommerce
    database: raw
    schema: public
    freshness:
      warn_after: {count: 12, period: hour}
      error_after: {count: 24, period: hour}
    loaded_at_field: created_at
    tables:
      - name: orders
      - name: customers
```

### Docker Compose for dbt

```yaml
version: "3.8"

services:
  dbt-runner:
    image: ghcr.io/dbt-labs/dbt-core:latest
    volumes:
      - ./dbt-project:/usr/app
    working_dir: /usr/app
    entrypoint: ["dbt"]
    command: ["run", "--profiles-dir", ".", "--project-dir", "."]
    depends_on:
      postgres

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=warehouse
      - POSTGRES_USER=dbt_user
      - POSTGRES_PASSWORD=dbt_pass
    ports:
      - "5432:5432"
```

### Running dbt Tests

```bash
# Run all tests
dbt test --profiles-dir .

# Run tests on specific models
dbt test --select stg_orders stg_customers

# Run with JSON output for CI/CD
dbt test --output json --profiles-dir .

# Combine run and test
dbt build --profiles-dir .  # runs models + tests
```

## When to Choose Each Tool

**Choose Data Contract CLI** when:
- You want contract-first data engineering with formal YAML specifications
- You need to share contracts between teams as version-controlled artifacts
- Your focus is on schema validation and freshness monitoring
- You want database-agnostic contracts that work across PostgreSQL, MySQL, and cloud warehouses

**Choose Soda Core** when:
- You need comprehensive data quality checks with a mature expression language
- Your priority is detecting data anomalies and quality regressions
- You want to scan data without transforming it (separate from dbt)
- You operate across 15+ data platforms and need a unified scanning layer

**Choose dbt Tests** when:
- You already use dbt for data transformations
- You want tests integrated into your transformation pipeline
- Your team prefers SQL-based test definitions
- You need source freshness monitoring as part of your ELT pipeline

For related data engineering topics, see our [data pipeline orchestration guide](../2026-04-24-apache-nifi-vs-streampipes-vs-kestra-self-hosted-data-pipeline-orchestration-guide-2026/), [data quality tools comparison](../self-hosted-data-quality-tools-great-expectations-soda-dbt-guide-2026/), and [data observability platforms](../elementary-vs-soda-vs-great-expectations-self-hosted-data-observability-guide-2026/).

## Why Self-Host Data Contract Validation?

Cloud-based data quality and contract platforms charge per scan, per user, or per data volume — costs that scale unfavorably as your data grows. Self-hosted data contract validation runs entirely within your infrastructure, processing unlimited scans at the cost of compute resources alone.

For organizations with strict data governance requirements (HIPAA, GDPR, SOC 2), self-hosted validation ensures contract definitions and quality results never leave your network. The YAML-based contract format serves as living documentation that version control systems track, enabling code review workflows for data schema changes.

The shift-left approach — validating data contracts in CI/CD before data reaches production — prevents quality issues from reaching downstream consumers. A single broken pipeline can affect dozens of dashboards, ML models, and business reports. Contract validation catches these issues at the source.

## FAQ

### What is the difference between data contracts and data quality checks?

Data contracts are formal agreements that define what data consumers can expect — schema, quality thresholds, freshness, and ownership terms. Data quality checks are the technical implementation that verifies whether data meets those expectations. A data contract specifies "order_id must be unique"; a quality check executes `SELECT COUNT(*) - COUNT(DISTINCT order_id)` to verify it.

### Can I use Data Contract CLI without a database connection?

Yes. Data Contract CLI supports linting and schema validation without connecting to a database. Run `datacontract lint contract.yaml` to validate the contract syntax and structure. You can also export contracts to SQL DDL, JSON Schema, or Avro format for offline use.

### How often should data contract validations run?

For production data pipelines, run validations on every pipeline execution (event-driven). For scheduled batch pipelines, run after each batch completes. Additionally, schedule periodic contract reviews (weekly or monthly) to catch drift between contract definitions and actual data evolution.

### Can Soda Core and dbt Tests be used together?

Yes, they complement each other well. dbt tests validate data as part of the transformation pipeline (testing output of transformations), while Soda Core scans source data independently of transformations. Together they provide end-to-end coverage: Soda validates raw source data quality, dbt tests validate transformed data correctness.

### How do I handle breaking changes to data contracts?

Version your contracts alongside your code. When a producer team needs to make a breaking change:
1. Create a new contract version (v2) alongside the existing one (v1)
2. Run both contracts in parallel during a transition period
3. Notify all consumers of the upcoming change
4. After consumers migrate, deprecate v1 and remove validation
5. Update the contract specification version in the YAML file

### What databases does Data Contract CLI support?

Data Contract CLI supports PostgreSQL, MySQL, BigQuery, Snowflake, DuckDB, and any database with a SQLAlchemy driver. It also supports file-based formats like Parquet, CSV, and JSON for local testing and development. The contract definition is database-agnostic — the same YAML contract works across different database backends.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Data Contract Validation: Data Contract CLI vs Soda Core vs dbt Tests 2026",
  "description": "Compare self-hosted data contract tools: Data Contract CLI for contract-first engineering, Soda Core for comprehensive quality checks, and dbt Tests for transformation-native validation.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
