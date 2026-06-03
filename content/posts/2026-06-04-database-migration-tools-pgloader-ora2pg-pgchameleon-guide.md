---
title: "Self-Hosted Database Migration Tools: pgloader vs ora2pg vs pg_chameleon"
date: "2026-06-04"
tags: ["postgresql", "database", "migration", "etl", "devops", "self-hosted"]
draft: false
---

## Introduction

Moving data between database systems is one of the most critical — and perilous — operations in infrastructure management. Whether you are migrating from Oracle to PostgreSQL to cut licensing costs, replicating MySQL data into a reporting database, or consolidating multiple data sources, the right migration tool can mean the difference between a weekend project and a months-long ordeal.

This guide compares three battle-tested open-source database migration tools — **pgloader**, **ora2pg**, and **pg_chameleon** — that handle complex schema conversions, data type mappings, and ongoing replication. Each tool serves a distinct migration scenario, and understanding their strengths will help you choose the right one for your project.

## Comparison Table

| Feature | pgloader | ora2pg | pg_chameleon |
|---------|----------|--------|--------------|
| **Target Database** | PostgreSQL, MySQL, SQLite | PostgreSQL | PostgreSQL |
| **Source Databases** | MySQL, SQLite, MS SQL, CSV, Fixed-width, DBF | Oracle, MySQL | MySQL/MariaDB |
| **Stars (GitHub)** | 6,400+ | 1,200+ | 430+ |
| **Language** | Common Lisp | Perl | Python |
| **Schema Conversion** | Automatic | Automatic + manual tuning | Automatic for MySQL |
| **Data Type Mapping** | Built-in, extensive | Highly configurable | Automatic |
| **Ongoing Replication** | No (one-shot) | No (one-shot) | Yes (CDC-based) |
| **Install Method** | apt, brew, source | apt, CPAN, source | pip |
| **License** | PostgreSQL | GPL-3.0 | BSD-2-Clause |
| **Docker Support** | Community images | Community images | Not official |

## pgloader: The Swiss Army Knife

pgloader is a data loading and migration utility written in Common Lisp. It supports an impressive range of source formats including MySQL, SQLite, MS SQL Server, CSV files, fixed-width files, and even legacy dBase (DBF) files. Its killer feature is automatic schema and data type conversion — it reads the source schema and automatically generates the appropriate PostgreSQL DDL.

### Installation

```bash
# Debian/Ubuntu
sudo apt-get install pgloader

# macOS
brew install pgloader

# From source
git clone https://github.com/dimitri/pgloader.git
cd pgloader
make
```

### Basic Usage

Migrate an entire MySQL database to PostgreSQL:

```bash
pgloader mysql://user:pass@source-host/source_db          pgsql://user:pass@target-host/target_db
```

For more complex migrations, pgloader uses a command file:

```lisp
LOAD DATABASE
     FROM mysql://user:password@source-host/source_db
     INTO pgsql://user:password@target-host/target_db

WITH include drop, create tables, create indexes,
     reset sequences,
     workers = 8, concurrency = 2,
     multiple readers per thread, rows per range = 50000

SET maintenance_work_mem to '1GB',
    work_mem to '64MB'

CAST type datetime to timestamptz
                drop default drop not null using zero-dates-to-null,
     type tinyint to boolean using tinyint-to-boolean;
```

pgloader excels at bulk one-shot migrations. It can handle terabyte-scale databases with parallel workers and configurable batch sizes. However, it does not support ongoing replication — once the migration completes, you need a separate solution for keeping data in sync during cutover.

## ora2pg: The Oracle Specialist

ora2pg is the de facto standard for Oracle-to-PostgreSQL migrations. Written in Perl, it provides incredibly detailed control over schema conversion, data export, and even PL/SQL-to-PL/pgSQL translation. It has been used in production migrations at organizations of all sizes, including major enterprises moving off Oracle.

### Installation

```bash
# Install DBI and Oracle dependencies first
sudo apt-get install libdbd-oracle-perl perl-doc

# Install ora2pg
sudo apt-get install ora2pg

# Or from CPAN
cpan install Ora2Pg
```

### Configuration

ora2pg uses a configuration file (`ora2pg.conf`) that controls every aspect of the migration:

```perl
ORACLE_HOME     /usr/lib/oracle/19.6/client64
ORACLE_DSN      dbi:Oracle:host=oracle-host;sid=ORCL;port=1521
ORACLE_USER     scott
ORACLE_PWD      tiger

PG_DSN          dbi:Pg:dbname=mydb;host=pg-host;port=5432
PG_USER         postgres
PG_PWD          secret

# Export type: TABLE, COPY, INSERT, PGBULKLOAD
EXPORT_TYPE     COPY

# Schema conversion options
REPLACE_TABLES  0
FILE_PER_TABLE  1
FILE_PER_FKEY   1

# Data type mapping customizations
DATA_TYPE       CLOB:text
DATA_TYPE       BLOB:bytea
DATA_TYPE       RAW:bytea
DATA_TYPE       BINARY_FLOAT:float4
DATA_TYPE       BINARY_DOUBLE:float8
```

### Migration Workflow

```bash
# 1. Export schema
ora2pg -c ora2pg.conf -t TABLE -b schema_output/

# 2. Review and adjust the exported SQL
# Edit schema_output/*.sql as needed

# 3. Apply schema to target PostgreSQL
psql -h pg-host -d mydb -f schema_output/schema.sql

# 4. Export data
ora2pg -c ora2pg.conf -t COPY -b data_output/

# 5. Load data into PostgreSQL
# (ora2pg generates scripts that use COPY commands)
```

ora2pg's strength lies in its configurability. You can fine-tune every type mapping, exclude specific tables or schemas, and generate reports that estimate migration effort based on your Oracle schema complexity. The migration cost assessment feature alone can save weeks of planning — it analyzes your Oracle schema and identifies objects that require manual intervention.

## pg_chameleon: The Replication Specialist

pg_chameleon takes a fundamentally different approach — it is designed for ongoing MySQL-to-PostgreSQL replication, not one-shot migration. Written in Python, it uses MySQL binary log replication to capture changes and apply them to PostgreSQL in near real-time. This makes it ideal for zero-downtime migrations where both systems need to run in parallel during a transition period.

### Installation

```bash
pip install pg_chameleon

# Create configuration directory
chameleon init_replica --config my_migration --source mysql
```

### Configuration

```ini
# ~/.pg_chameleon/config/my_migration.yml
[global]
pid_dir = ~/.pg_chameleon/pid/
log_dir = ~/.pg_chameleon/logs/
log_level = info

[source]
type = mysql
host = mysql-host
port = 3306
user = repl_user
password = repl_pass
# MySQL must have binary logging enabled and the repl user needs REPLICATION SLAVE

[destination]
type = postgresql
host = pg-host
port = 5432
user = postgres
password = pg_pass
database = target_db
```

### Replication Workflow

```bash
# 1. Create the replica schema in PostgreSQL
chameleon create_replica_schema --config my_migration

# 2. Add source tables to replicate
chameleon add_source --config my_migration --schema source_db --tables "*"

# 3. Initial data load
chameleon init_replica --config my_migration --source mysql

# 4. Start ongoing replication
chameleon start_replica --config my_migration

# 5. Monitor replication status
chameleon show_status --config my_migration
chameleon show_errors --config my_migration
```

pg_chameleon handles the most challenging part of database migration — the cutover. You can run it for days or weeks, keeping your PostgreSQL target in sync with the MySQL source, while testing your application against PostgreSQL. When ready, you stop writes to MySQL, let pg_chameleon catch up, and switch your application to PostgreSQL with minimal downtime.

## Deployment Architecture

For production database migrations, run the migration tools from a dedicated jump host or container that has network access to both source and target databases:

```bash
# Using a dedicated container for migrations
docker run -it --rm \
  --network migration-net \
  -v ./migration-configs:/configs \
  -v ./migration-data:/data \
  dimitri/pgloader:latest \
  pgloader /configs/my-migration.load
```

For pg_chameleon in replication mode, consider running it as a systemd service:

```ini
[Unit]
Description=pg_chameleon replication service
After=network.target

[Service]
Type=simple
User=postgres
ExecStart=/usr/local/bin/chameleon start_replica --config my_migration
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Choosing the Right Tool

Your choice depends primarily on the migration scenario:

- **Oracle to PostgreSQL**: ora2pg is the clear winner. Its deep Oracle-specific knowledge, cost assessment reports, and PL/SQL translation capabilities have no equal among open-source alternatives.

- **MySQL to PostgreSQL (one-shot)**: pgloader handles this elegantly with automatic schema conversion and parallel data loading. Use it for smaller databases or when you can afford a brief maintenance window.

- **MySQL to PostgreSQL (zero-downtime)**: pg_chameleon is the only open-source option that supports ongoing replication during the migration. Use it for large, high-traffic databases that cannot tolerate extended downtime.

- **SQLite or other sources to PostgreSQL**: pgloader supports the widest range of source formats and is the go-to choice.

## Why Self-Host Your Database Migration Tooling?

Running migration tools on your own infrastructure gives you complete control over the migration process. You are not sending your database credentials or data through third-party cloud services. Every byte of your sensitive business data stays within your network boundaries.

Database migrations are not one-time events — they recur as you upgrade systems, consolidate databases, or create development and testing environments from production data. Having migration tooling established and tested in your infrastructure pays dividends across multiple projects.

For organizations managing multiple database systems, see our [self-hosted database comparison guide](../2026-04-25-firebird-vs-postgresql-vs-mariadb-self-hosted-sql-database-guide-2026/). If you are working with PostgreSQL replication beyond migrations, our [logical replication guide](../2026-05-10-postgresql-logical-replication-pglogical-wal2json-pgoutput-guide/) covers pglogical, wal2json, and pgoutput.

Database migration tooling is a foundational part of any data engineering infrastructure. Combined with [data pipeline orchestration](../2026-04-24-apache-nifi-vs-streampipes-vs-kestra-self-hosted-data-pipeline-orchestration-guide-2026/), these tools form the backbone of a self-hosted data platform that keeps your organization's data portable and vendor-independent.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Migration Tools: pgloader vs ora2pg vs pg_chameleon",
  "description": "Compare pgloader, ora2pg, and pg_chameleon for PostgreSQL database migration. Covers Oracle-to-PostgreSQL, MySQL-to-PostgreSQL, schema conversion, and zero-downtime replication.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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

### How long does a database migration typically take?

Migration duration depends on database size, network bandwidth, and the tool's parallelism. pgloader can migrate ~100 GB/hour with 8 parallel workers on commodity hardware. ora2pg's COPY mode achieves similar speeds. pg_chameleon's initial load speed is comparable, but it adds near-zero ongoing overhead once replication is running.

### Can I migrate stored procedures and functions?

ora2pg provides the best support, capable of converting Oracle PL/SQL to PostgreSQL PL/pgSQL with approximately 80% success rate for common patterns. pgloader does not convert stored procedures. pg_chameleon focuses on data replication and does not handle schema objects beyond tables and basic indexes.

### What happens to data types that have no direct equivalent?

All three tools provide configurable type mappings. pgloader has sensible defaults (MySQL `TINYINT` → PostgreSQL `boolean`, MySQL `DATETIME` → PostgreSQL `timestamptz`). ora2pg lets you define custom mappings in its configuration file. pg_chameleon uses a mapping table that you can modify. For complex types (spatial, XML, JSON), manual review is always recommended.

### Do these tools work with cloud database services?

Yes, all three work with cloud-hosted databases (RDS, Cloud SQL, Aurora, etc.) as long as you have network connectivity and the necessary credentials. For pg_chameleon with MySQL on RDS, you need to enable binary logging and configure the replication user. ora2pg works with Oracle on RDS or on-premises equally well.

### Is there a way to validate data integrity after migration?

All three tools can generate row counts and checksums for validation. For pgloader, you run `pgloader --with "data only"` after schema migration and compare row counts. ora2pg generates validation SQL scripts. For pg_chameleon, the `show_status` command reports replication lag and error counts. For rigorous validation, complement these with dedicated data comparison tools like data-diff that perform row-level comparisons across databases.

### Can I pause and resume a pg_chameleon replication?

Yes, pg_chameleon supports graceful stop and restart. Use `chameleon stop_replica --config my_migration` to pause, and `chameleon start_replica --config my_migration` to resume. It tracks its position in MySQL binary logs and PostgreSQL, so replication picks up exactly where it left off.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
