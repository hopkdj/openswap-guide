---
title: "Self-Hosted Database Benchmarking: pgbench vs sysbench vs HammerDB 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "database", "benchmarking", "performance"]
draft: false
description: "Complete guide to self-hosted database benchmarking in 2026. Compare pgbench, sysbench, and HammerDB with Docker setup instructions, benchmark workflows, and performance testing strategies for PostgreSQL, MySQL, and MariaDB."
---

Before you put a database into production, you need to know how it behaves under load. How many queries per second can it sustain? What happens when 500 concurrent connections hit it simultaneously? Does your schema design cause lock contention under write-heavy workloads? Without answering these questions with real benchmark data, you are deploying blind.

Commercial database benchmarking services and cloud-managed testing tools charge premium prices for capabilities you can replicate on your own hardware. In 2026, the three most capable open-source database benchmarking tools — **pgbench**, **sysbench**, and **HammerDB** — give you enterprise-grade load testing without licensing fees, data exfiltration risks, or per-test quotas. This guide covers all three with complete Docker-based setup instructions and a practical comparison.

## Why Self-Host Your Database Benchmarking

Running database benchmarks on your own infrastructure, rather than relying on vendor-provided benchmarks or cloud testing services, gives you several decisive advantages:

**Hardware-realistic results.** Cloud provider benchmarks run on their optimized infrastructure with tuned kernels and fast NVMe storage — nothing like your actual production servers. Benchmarking on hardware that matches your deployment environment produces numbers you can actually trust for capacity planning.

**Unlimited testing without quotas.** Commercial benchmarking platforms limit the number of tests, concurrent connections, or data volume. Self-hosted tools have no such restrictions. Run a 72-hour endurance test with 1,000 concurrent clients if your scenario requires it.

**Custom workload modeling.** Pre-packaged benchmarks rarely match your actual query patterns. Self-hosted tools let you write custom scripts that replay your real application's read/write ratios, transaction sizes, and query complexity profiles.

**No data leakage.** Sending schema information and query patterns to a third-party testing platform reveals your data architecture. Keeping benchmarks on-premise means your database design stays private.

**Regression testing across upgrades.** Before upgrading PostgreSQL from 16 to 17, or migrating from MySQL to MariaDB, run identical benchmark suites against both versions on identical hardware. Quantify the performance impact before touching production.

**Cost-effective capacity planning.** Instead of over-provisioning "just to be safe," use benchmark data to right-size your servers. A $20/month VPS that runs your benchmark suite can save thousands in unnecessary cloud spend.

## pgbench: PostgreSQL's Built-In Benchmark

**pgbench** ships with every PostgreSQL installation. It implements a modified TPC-B workload — a standardized transaction processing benchmark — and measures transactions per second (TPS) under configurable concurrency levels. Because it is bundled with PostgreSQL, there is zero installation overhead and the tool is always compatible with your server version.

### How pgbench Works

pgbench runs a sequence of SQL operations that simulate a banking workload:

1. **SELECT** an account balance by account ID
2. **UPDATE** the account balance (add or subtract a value)
3. **UPDATE** a teller record
4. **UPDATE** a branch record
5. **INSERT** a transaction history record

Each of these operations runs inside a transaction. By default, pgbench runs these five steps repeatedly across a configurable number of concurrent client connections, measuring how many complete transactions the database can process per second.

### Docker Setup

Start a PostgreSQL instance and run pgbench inside it:

```yaml
# docker-compose.yml — PostgreSQL with pgbench
services:
  postgres:
    image: postgres:17-alpine
    container_name: pgbench-target
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: benchmark123
      POSTGRES_DB: benchdb
    ports:
      - "5432:5432"
    command: >
      postgres
        -c shared_buffers=256MB
        -c effective_cache_size=1GB
        -c work_mem=16MB
        -c max_connections=200
    shm_size: 1g
```

### Running a pgbench Test

First, initialize the test database with scale factor 100 (creates ~100,000 rows per table):

```bash
docker exec pgbench-target pgbench -i -s 100 \
  -U postgres -d benchdb
```

The `-i` flag initializes the schema and `-s 100` sets the scale factor. Higher scale factors simulate larger datasets that may not fit in RAM, forcing disk I/O.

Then run the benchmark with 20 concurrent clients for 120 seconds:

```bash
docker exec pgbench-target pgbench -c 20 -j 4 -T 120 \
  -U postgres -d benchdb
```

- `-c 20` — 20 concurrent client connections
- `-j 4` — use 4 worker threads to manage clients
- `-T 120` — run for 120 seconds

Sample output:

```
starting vacuum...end.
transaction type: <builtin: TPC-B (sort of)>
scaling factor: 100
query mode: simple
number of clients: 20
number of threads: 4
maximum number of tries: 1
number of transactions per client: 0
duration: 120 s
number of transactions actually processed: 84523
latency average = 28.394 ms
latency stddev = 12.451 ms
initial connection time = 245.123 ms
tps = 703.842156 (without initial connection time)
```

The **tps** line is your key metric — 704 transactions per second sustained over 120 seconds with 20 concurrent clients.

### Custom Script Mode

pgbench supports custom SQL scripts for testing your actual queries. Create a file called `my-workload.sql`:

```sql
\setrandom aid 1 :naccounts
\setrandom bid 1 :nbranches
\setrandom tid 1 :ntellers

BEGIN;
UPDATE accounts SET abalance = abalance + :delta WHERE aid = :aid;
SELECT abalance FROM accounts WHERE aid = :aid;
UPDATE tellers SET tbalance = tbalance + :delta WHERE tid = :tid;
UPDATE branches SET bbalance = bbalance + :delta WHERE bid = :bid;
INSERT INTO history (tid, bid, aid, delta, mtime) VALUES (:tid, :bid, :aid, :delta, CURRENT_TIMESTAMP);
END;
```

Run it with:

```bash
docker exec pgbench-target pgbench -f /path/to/my-workload.sql \
  -c 20 -j 4 -T 120 -n -U postgres -d benchdb
```

The `-f` flag loads your custom script and `-n` skips the vacuum step (useful for custom workloads that do not use pgbench's built-in tables).

### Best Practices for pgbench

- **Warm the cache first.** Run a short preliminary test before the measured run to load hot data into PostgreSQL's shared buffers.
- **Vary the scale factor.** Test with `-s 10` (fits in RAM) and `-s 1000` (forces disk I/O) to understand both in-memory and I/O-bound performance.
- **Test connection scaling.** Run at `-c 10`, `-c 50`, `-c 100`, and `-c 200` to find the concurrency level where throughput plateaus or degrades.
- **Enable statement-level logging** during tests to identify slow queries: add `-l` to pgbench and examine `pgbench_log.*` files.
- **Test with realistic `postgresql.conf` settings.** Default PostgreSQL settings are conservative. Benchmark with production-equivalent `shared_buffers`, `work_mem`, and `wal_buffers` values.

## sysbench: Multi-Purpose System and Database Benchmark

**sysbench** is a modular benchmarking framework that tests CPU, memory, file I/O, mutex performance, and — most relevant here — OLTP database workloads for both MySQL/MariaDB and PostgreSQL. Unlike pgbench, which is PostgreSQL-specific, sysbench provides a unified benchmarking interface across multiple database engines.

### How sysbench Works

sysbench uses a Lua-based scripting system. For database benchmarking, it includes a built-in OLTP test that simulates a realistic mix of read and write operations:

- **Point SELECT queries** — single-row lookups by primary key
- **Range SELECT queries** — multi-row scans within index ranges
- **UPDATE queries** — modify individual rows
- **INSERT queries** — add new rows
- **DELETE queries** — remove rows by primary key
- **Index scan queries** — ordered traversal of secondary indexes

The mix of operations can be configured to match your application's read/write ratio. sysbench reports queries per second (QPS), transactions per second (TPS), latency percentiles (p50, p95, p99), and thread fairness metrics.

### Docker Setup

```yaml
# docker-compose.yml — MySQL + sysbench
services:
  mysql:
    image: mysql:8.4
    container_name: sysbench-target
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: benchmark123
      MYSQL_DATABASE: sbtest
    ports:
      - "3306:3306"
    command: >
      mysqld
        --innodb-buffer-pool-size=512M
        --innodb-log-file-size=128M
        --max-connections=200
        --innodb-flush-log-at-trx-commit=1
    volumes:
      - mysql-data:/var/lib/mysql

  sysbench:
    image: severalnines/sysbench:latest
    container_name: sysbench-runner
    depends_on:
      - mysql
    entrypoint: ["tail", "-f", "/dev/null"]

volumes:
  mysql-data:
```

### Running a sysbench Test

sysbench operates in three phases: prepare, run, and cleanup.

**Phase 1: Prepare** — create the test database and populate it:

```bash
docker exec sysbench-runner sysbench \
  --db-driver=mysql \
  --mysql-host=sysbench-target \
  --mysql-user=root \
  --mysql-password=benchmark123 \
  --mysql-db=sbtest \
  --tables=10 \
  --table-size=1000000 \
  oltp_common prepare
```

This creates 10 tables with 1 million rows each (~10 million total rows), giving you a ~2-4 GB dataset depending on schema.

**Phase 2: Run** — execute the benchmark:

```bash
docker exec sysbench-runner sysbench \
  --db-driver=mysql \
  --mysql-host=sysbench-target \
  --mysql-user=root \
  --mysql-password=benchmark123 \
  --mysql-db=sbtest \
  --threads=16 \
  --time=120 \
  --report-interval=10 \
  --percentile=99 \
  oltp_read_write run
```

- `--threads=16` — 16 concurrent worker threads
- `--time=120` — 120-second test duration
- `--report-interval=10` — print intermediate results every 10 seconds
- `--percentile=99` — calculate p99 latency
- `oltp_read_write` — mixed read/write workload (70/30 split)

**Phase 3: Cleanup** — remove test data:

```bash
docker exec sysbench-runner sysbench \
  --db-driver=mysql \
  --mysql-host=sysbench-target \
  --mysql-user=root \
  --mysql-password=benchmark123 \
  --mysql-db=sbtest \
  oltp_common cleanup
```

### sysbench Test Modes

sysbench ships with several predefined OLTP test scripts:

| Test Mode | Description | Use Case |
|-----------|-------------|----------|
| `oltp_read_only` | 100% SELECT queries | Read-heavy workloads (content sites, analytics reads) |
| `oltp_read_write` | ~70% reads, ~30% writes | General application workloads |
| `oltp_write_only` | 100% INSERT/UPDATE/DELETE | Write-heavy workloads (logging, IoT ingestion) |
| `oltp_point_select` | Single-row PK lookups | Cache hit rate testing, key-value store comparison |
| `oltp_delete` | Range deletes | Cleanup job simulation |
| `oltp_insert` | Bulk inserts | Data pipeline and ETL benchmarking |
| `oltp_update_index` | Indexed column updates | Hot row contention testing |
| `oltp_update_non_index` | Non-indexed column updates | Full table scan simulation |

### Non-Database Benchmarks

sysbench also tests hardware performance, which helps you understand whether bottlenecks are database-specific or systemic:

```bash
# CPU benchmark — prime number computation
sysbench cpu --cpu-max-prime=20000 run

# Memory benchmark — sequential read/write
sysbench memory --memory-block-size=1M --memory-total-size=10G run

# File I/O benchmark — random read/write on test files
sysbench fileio --file-total-size=5G --file-test-mode=rndrw prepare
sysbench fileio --file-total-size=5G --file-test-mode=rndrw --threads=8 run
sysbench fileio --file-total-size=5G --file-test-mode=rndrw cleanup
```

Running these before and after a database benchmark helps you distinguish between database-level optimization opportunities and fundamental hardware limitations.

## HammerDB: Enterprise-Grade Multi-Database Benchmark

**HammerDB** is the most sophisticated open-source database benchmarking tool available. It implements official TPC-C and TPC-H benchmarks — the same standardized workloads used by vendors in published performance comparisons — and supports PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, and DB2.

HammerDB provides a graphical user interface (via Tcl/Tk) for building test scenarios, but also supports fully automated command-line execution, making it ideal for CI/CD pipeline integration and headless server testing.

### TPC-C vs TPC-H

HammerDB implements two distinct benchmark standards:

**TPC-C (Online Transaction Processing):** Simulates a wholesale supplier's order management system with concurrent users performing new orders, payment processing, order status checks, delivery scheduling, and stock level queries. Measures throughput in transactions per minute (tpmC) and price-performance ratio.

**TPC-H (Decision Support):** Simulates a data warehouse environment with complex analytical queries across large datasets. Measures query response times for business intelligence workloads including pricing reports, shipping patterns, and supplier analysis.

### Docker Setup

```yaml
# docker-compose.yml — HammerDB with PostgreSQL
services:
  postgres:
    image: postgres:17-alpine
    container_name: hammerdb-target
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: benchmark123
      POSTGRES_DB: hammerdb
    ports:
      - "5432:5432"
    shm_size: 2g

  hammerdb:
    image: hammerdb/hammerdb:latest
    container_name: hammerdb-runner
    depends_on:
      - postgres
    entrypoint: ["tail", "-f", "/dev/null"]
```

### Running a TPC-C Benchmark via CLI

HammerDB uses Tcl scripts for automation. Create a benchmark script:

```tcl
# tpcc-benchmark.tcl
#!/usr/bin/tclsh
load_libtclodbc

# Connect to PostgreSQL
dbset db pg
dbset bm TPC-C

# Server connection
set vu_total 50
set tpcc_user_dict "user:benchuser password:benchmark123"
set tpcc_server "hammerdb-target"
set tpcc_port "5432"
set tpcc_database "hammerdb"

# Schema configuration
set tpcc_warehouse_count 20
set tpcc_num_vu $vu_total

# Build the schema
puts "Building TPC-C schema..."
buildschema

# Wait for schema build to complete
waitforbuildcomplete

# Run the timed test
puts "Starting TPC-C benchmark..."
vuset vu_total $vu_total
vuset logtimer TRUE
vucreate
timerstart 300  ;# 5-minute timed test
vurun
waitforruncomplete
timerstop

# Print results
printResults
exit
```

Run it with:

```bash
docker exec hammerdb-runner hammerdbcli auto tpcc-benchmark.tcl
```

HammerDB outputs detailed results including:

- **tpmC** — transactions per minute (standardized TPC-C metric)
- **NOPM** — new orders per minute
- **Response time percentiles** — p50, p95, p99 for each transaction type
- **Virtual user efficiency** — how effectively each simulated user contributes to throughput

### TPC-H (Analytical) Benchmark

For data warehouse workloads, switch to TPC-H:

```tcl
# tpch-benchmark.tcl
dbset db pg
dbset bm TPC-H

set tpch_user_dict "user:benchuser password:benchmark123"
set tpch_server "hammerdb-target"
set tpch_port "5432"
set tpch_database "hammerdb"

set tpch_scale_factor 10   ;# 10 GB dataset
set tpch_update_set 1      ;# 1 refresh stream

buildschema
waitforbuildcomplete

vuset vu_total 4
vuset logtimer TRUE
vucreate
timerstart 600
vurun
waitforruncomplete
timerstop
printResults
exit
```

TPC-H runs 22 complex analytical queries involving multi-table joins, aggregations, subqueries, and window functions — the kinds of queries that differentiate a tuned data warehouse from a poorly configured one.

## Head-to-Head Comparison

| Feature | pgbench | sysbench | HammerDB |
|---------|---------|----------|----------|
| **License** | PostgreSQL (open-source) | GPL-2.0 | GPL-3.0 |
| **Database Support** | PostgreSQL only | MySQL, MariaDB, PostgreSQL | PostgreSQL, MySQL, Oracle, SQL Server, DB2, MariaDB |
| **Benchmark Standards** | Modified TPC-B | Custom OLTP scripts | TPC-C, TPC-H (official) |
| **Installation** | Bundled with PostgreSQL | Separate package | Separate package + optional GUI |
| **Custom Workloads** | SQL script files | Lua scripts | Tcl scripts |
| **GUI** | No | No | Yes (Tcl/Tk) |
| **CLI Automation** | Yes | Yes | Yes |
| **Metrics Reported** | TPS, latency | QPS, TPS, latency percentiles | tpmC, NOPM, latency percentiles |
| **Hardware Tests** | No | CPU, memory, file I/O, mutex | No |
| **Data Volume Control** | Scale factor (-s) | Tables × table-size | Scale factor (SF) |
| **CI/CD Friendly** | Excellent | Excellent | Good (CLI mode) |
| **Best For** | Quick PostgreSQL checks | Cross-engine comparison | Certified benchmark compliance |

## Choosing the Right Tool

### Use pgbench when:

- You run PostgreSQL exclusively and need a fast, zero-install benchmark
- You want to test PostgreSQL configuration changes (`shared_buffers`, `work_mem`, checkpoint settings)
- You need to benchmark custom SQL scripts against PostgreSQL-specific features (CTEs, window functions, JSONB operations)
- Quick sanity checks before and after a major version upgrade

### Use sysbench when:

- You need to compare PostgreSQL vs MySQL vs MariaDB on identical hardware
- You want to isolate database performance from hardware bottlenecks (run CPU/memory/fileio tests first)
- Your workload is heavily read-focused or write-focused and you need test modes that match
- You need latency percentile data (p95, p99) for SLA compliance planning

### Use HammerDB when:

- You need TPC-C or TPC-H certified benchmark results for vendor comparisons or procurement decisions
- You benchmark multiple database engines (Oracle, SQL Server, PostgreSQL) with a single tool
- You want OLAP (analytical) benchmarking alongside OLTP (transactional) testing
- Your team benefits from a visual test configuration interface

## Practical Benchmarking Workflow

Here is a recommended workflow for evaluating a new database deployment:

```bash
# Step 1: Baseline hardware performance
sysbench cpu --cpu-max-prime=20000 run
sysbench memory --memory-block-size=1M --memory-total-size=10G run
sysbench fileio --file-total-size=5G --file-test-mode=rndrw prepare
sysbench fileio --file-total-size=5G --file-test-mode=rndrw --threads=8 --time=60 run
sysbench fileio --file-total-size=5G --file-test-mode=rndrw cleanup

# Step 2: PostgreSQL-specific baseline
docker exec pgbench-target pgbench -i -s 50 -U postgres -d benchdb
docker exec pgbench-target pgbench -c 10 -j 2 -T 60 -U postgres -d benchdb

# Step 3: Connection scaling test
for clients in 10 25 50 100 200; do
  echo "=== $clients concurrent clients ==="
  docker exec pgbench-target pgbench -c $clients -j 4 -T 60 -U postgres -d benchdb
done

# Step 4: Cross-engine comparison (if applicable)
docker exec sysbench-runner sysbench --db-driver=mysql \
  --mysql-host=sysbench-target --mysql-user=root \
  --mysql-password=benchmark123 --mysql-db=sbtest \
  --tables=10 --table-size=1000000 --threads=16 --time=120 \
  oltp_read_write run
```

Plot the results from Step 3 to create a throughput-vs-concurrency curve. The point where the curve flattens or begins declining tells you the practical connection limit for your hardware and configuration — valuable information for configuring connection poolers like PgBouncer or ProxySQL.

## Interpreting Results Correctly

Benchmark numbers are only useful when interpreted correctly:

- **Single-run results are misleading.** Always run each test 3-5 times and report the median. The first run includes cache warming; the last runs may show thermal throttling on bare metal.
- **TPS is not QPS.** A single transaction may contain 5-10 SQL queries. pgbench reports TPS; sysbench reports both TPS and QPS. Make sure you compare like with like.
- **Latency percentiles matter more than averages.** A p99 latency of 500ms means 1 out of every 100 queries takes half a second — unacceptable for user-facing applications even if the average is 20ms.
- **Scale factor changes everything.** A benchmark with `-s 10` (dataset fits in RAM) measures CPU and memory performance. A benchmark with `-s 1000` (dataset exceeds RAM) measures I/O subsystem performance. Both are valid but answer different questions.
- **Benchmark your actual schema.** Synthetic benchmarks are a starting point. Always supplement with tests that use your real schema, indexes, and query patterns.

## Conclusion

Database performance is not a property of the database software alone — it is the result of the interaction between your queries, your schema, your configuration, and your hardware. The only way to understand this interaction is to measure it systematically. pgbench gives you instant PostgreSQL benchmarking with zero setup overhead. sysbench provides a unified testing framework across database engines and hardware subsystems. HammerDB delivers certified TPC benchmarks that let you compare apples to apples across entirely different database platforms.

All three tools are free, open-source, and Docker-ready. There is no reason to deploy a database into production without first answering the fundamental question: how does it perform under the load you expect it to carry?
