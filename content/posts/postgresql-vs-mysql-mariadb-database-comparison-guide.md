---
title: "PostgreSQL vs MySQL vs MariaDB: Best Self-Hosted Database 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "database", "infrastructure"]
draft: false
description: "Compare PostgreSQL, MySQL, and MariaDB as self-hosted databases. Complete Docker setup guides, feature comparison, performance benchmarks, and migration strategies for 2026."
---

## Why Self-Host Your Database?

Running your own database server is the backbone of any self-hosted infrastructure. Whether you are powering a home lab, running a small business application, or building a multi-service architecture, the database choice defines your scalability ceiling, data integrity guarantees, and operational complexity.

Cloud database services like Amazon RDS, Google Cloud SQL, and Azure Database offer convenience at a steep premium. They charge for storage, compute, IOPS, backups, and data transfer — often running into hundreds of dollars per month for modest workloads. Self-hosting flips the economics: you pay for the hardware once, and the software is free.

Beyond cost, self-hosting your database gives you:

- **Full data sovereignty**. Your data stays on your hardware, in your jurisdiction, under your control. No vendor lock-in, no surprise policy changes, no forced migrations.
- **Unlimited connections and queries**. Cloud providers throttle connections, charge per query, or impose rate limits. Self-hosted databases scale with your hardware, not your budget tier.
- **Custom configuration**. Tune every parameter — from shared buffers to WAL settings, from query planner costs to replication lag thresholds. Cloud databases lock these behind "recommended defaults."
- **Extensibility**. Install extensions, write stored procedures in multiple languages, create custom index types, and build domain-specific functionality that cloud providers would never support.
- **Predictable performance**. No noisy neighbors. No shared infrastructure spikes. Your queries run on dedicated resources.
- **Complete backup control**. Schedule, encrypt, compress, and store backups exactly where you want them — on-premises NAS, offsite S3-compatible storage, or both.

The trade-off is operational responsibility: you manage updates, backups, replication, and disaster recovery. With modern containerization and automation tools, this overhead has shrunk dramatically.

## PostgreSQL vs MySQL vs MariaDB: Quick Comparison

| Feature | PostgreSQL 17 | MySQL 8.0/9.0 | MariaDB 11.x |
|---------|--------------|---------------|--------------|
| **License** | PostgreSQL License (BSD-like) | GPL (Oracle) | GPL (independent) |
| **SQL Compliance** | Excellent (near-full) | Good | Good |
| **JSON Support** | JSONB (binary, indexed) | JSON (text-based) | JSON (text-based) |
| **Full-Text Search** | Built-in, powerful | Built-in, basic | Built-in, basic |
| **GIS/Spatial** | PostGIS (industry standard) | Spatial extensions | Spatial extensions |
| **Replication** | Logical + Streaming | Group Replication, GTID | Galera Cluster, GTID |
| **Partitioning** | Declarative, advanced | Range/List/Hash | Range/List/Hash |
| **Stored Procedures** | PL/pgSQL, Python, Perl, etc. | SQL, limited languages | SQL, limited languages |
| **Window Functions** | Full support | Full support | Full support |
| **CTEs & Recursive Queries** | Full support | Full support (8.0+) | Full support |
| **MVCC** | Yes (multi-version) | Yes (InnoDB) | Yes (InnoDB/XtraDB) |
| **Connection Pooling** | PgBouncer, Pgpool-II | Proxy, Router | MaxScale |
| **High Availability** | Patroni, repmgr, Stolon | InnoDB Cluster, Orchestrator | Galera Cluster, MaxScale |
| **Max DB Size** | Unlimited (filesystem-limited) | 256 TB (InnoDB) | 256 TB (InnoDB/XtraDB) |
| **Learning Curve** | Medium | Low | Low |
| **Best For** | Complex queries, data integrity, extensibility | Web apps, CMS, general purpose | MySQL-compatible with open-source governance |

## PostgreSQL: The Advanced Open-Source Database

PostgreSQL is widely regarded as the most advanced open-source relational database. Originating from UC Berkeley research in 1986, it has evolved into an enterprise-grade system that rivals proprietary databases like Oracle in features and capabilities.

### Key Strengths

- **SQL Standards Compliance**. PostgreSQL implements more of the SQL standard than any other open-source database. CTEs, window functions, lateral joins, and recursive queries all work exactly as specified.
- **Extensibility Architecture**. The extension system is unmatched. PostGIS adds world-class spatial analysis. TimescaleDB transforms PostgreSQL into a time-series database. pgvector enables similarity search for embeddings. Each extension integrates natively — no separate server to manage.
- **Data Integrity**. PostgreSQL enforces constraints rigorously. Check constraints, exclusion constraints, deferred constraints, and partial indexes give you fine-grained control over data validity.
- **JSONB Performance**. Unlike MySQL's text-based JSON type, PostgreSQL's JSONB stores data in a decomposed binary format. You can index JSON fields with GIN indexes, query nested structures, and get sub-millisecond lookups on JSON documents.
- **Concurrency Control**. PostgreSQL's MVCC implementation avoids read locks entirely. Readers never block writers, and writers never block readers. Combined with advisory locks and SKIP LOCKED, it handles complex concurrent workloads gracefully.
- **Parallel Query Execution**. Complex analytical queries can be parallelized across multiple CPU cores automatically. Sequential scans, joins, aggregations, and sorts all benefit from parallel execution.

### PostgreSQL Docker Setup

A production-ready PostgreSQL deployment with persistent storage, custom configuration, and health checks:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:17-alpine
    container_name: postgres-primary
    restart: unless-stopped
    environment:
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme_secure_password}
      POSTGRES_DB: app_database
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app_user -d app_database"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    command: >
      postgres
        -c max_connections=200
        -c shared_buffers=256MB
        -c effective_cache_size=768MB
        -c maintenance_work_mem=64MB
        -c checkpoint_completion_target=0.9
        -c wal_buffers=16MB
        -c default_statistics_target=100
        -c random_page_cost=1.1
        -c effective_io_concurrency=200
        -c work_mem=4MB
        -c min_wal_size=1GB
        -c max_wal_size=4GB
        -c max_worker_processes=4
        -c max_parallel_workers_per_gather=2
        -c max_parallel_workers=4
        -c max_parallel_maintenance_workers=2
    networks:
      - db_network
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    restart: unless-stopped
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD:-admin}
      PGADMIN_CONFIG_SERVER_MODE: "False"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    ports:
      - "5050:80"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - db_network

volumes:
  postgres_data:
    driver: local
  pgadmin_data:
    driver: local

networks:
  db_network:
    driver: bridge
```

### PostgreSQL Streaming Replication

For high availability, PostgreSQL supports built-in streaming replication. Here is a minimal primary-replica setup:

**Primary node** (`postgresql.conf` additions):
```conf
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
hot_standby = on
```

**Replica node** — create a base backup and start as a standby:
```bash
# On the replica server
pg_basebackup -h primary_host -U replicator -D /var/lib/postgresql/data -P -R

# This creates standby.signal and sets primary_conninfo automatically
# Start PostgreSQL — it will connect as a read-only replica
```

### Essential PostgreSQL Extensions

PostgreSQL's extension ecosystem is one of its biggest advantages. Install the most useful ones:

```sql
-- Enable commonly used extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- Trigram full-text search
CREATE EXTENSION IF NOT EXISTS uuid-ossp;     -- UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS btree_gin;     -- GIN index on standard types
CREATE EXTENSION IF NOT EXISTS tablefunc;     -- Crosstab and pivot functions
CREATE EXTENSION IF NOT EXISTS hstore;        -- Key-value store type

-- For time-series data
-- CREATE EXTENSION timescaledb;

-- For geospatial data
-- CREATE EXTENSION postgis;
-- CREATE EXTENSION postgis_topology;

-- For vector similarity search (AI/ML applications)
-- CREATE EXTENSION vector;
```

### PostgreSQL Performance Tuning

PostgreSQL ships with conservative defaults designed to run on minimal hardware. For production, tune these key parameters:

```conf
# Memory settings (adjust based on available RAM)
shared_buffers = 25% of total RAM        # Up to 8GB typically
effective_cache_size = 75% of total RAM  # Estimate of OS cache available
work_mem = 4-64MB per operation          # Beware: per-operation, not per-connection
maintenance_work_mem = 256MB-2GB         # For VACUUM, CREATE INDEX, etc.
huge_pages = try                         # Use if shared_buffers > 32GB

# WAL and durability
wal_buffers = 16MB                       # Auto-tuned if set to -1
checkpoint_completion_target = 0.9       # Spread checkpoint I/O over time
wal_compression = on                     # Compress WAL records
synchronous_commit = on                  # Change to 'off' for bulk loads

# Query planner
random_page_cost = 1.1                   # Lower for SSDs (default 4.0 for HDDs)
effective_io_concurrency = 200           # Higher for SSDs (default 1)
default_statistics_target = 100          # Increase for complex queries (up to 10000)

# Connections
max_connections = 200                    # Use PgBouncer if you need more
```

## MySQL: The Web's Default Database

MySQL has powered the web since 1995. It is the database behind WordPress, Drupal, Joomla, and countless web applications. Now owned by Oracle, MySQL 8.0 and 9.0 have added significant features including window functions, CTEs, and improved JSON handling.

### Key Strengths

- **Ubiquity and Ecosystem**. MySQL is the most widely deployed open-source database. Every hosting provider supports it, every ORM supports it, and every developer has worked with it at some point.
- **Read Performance**. For read-heavy workloads with simple queries, MySQL's InnoDB engine delivers excellent throughput. The query optimizer is highly tuned for common web application patterns.
- **Replication Simplicity**. MySQL's binary log-based replication is straightforward to set up. Group Replication (8.0+) adds multi-primary support with automatic conflict detection.
- **Resource Efficiency**. MySQL generally uses less memory than PostgreSQL for equivalent workloads, making it a good choice for resource-constrained environments like small VPS instances or Raspberry Pi deployments.
- **Mature Tooling**. The ecosystem of backup tools (Percona XtraBackup), monitoring (Percona Monitoring and Management), and management utilities (MySQL Shell, MySQL Workbench) is extensive.

### MySQL Docker Setup

```yaml
version: "3.9"

services:
  mysql:
    image: mysql:8.0
    container_name: mysql-primary
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root_secure_password}
      MYSQL_DATABASE: app_database
      MYSQL_USER: app_user
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-changeme_secure}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./my.cnf:/etc/mysql/conf.d/custom.cnf:ro
      - ./init-scripts:/docker-entrypoint-initdb.d:ro
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD:-root_secure_password}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - db_network
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 256M

  phpmyadmin:
    image: phpmyadmin:latest
    container_name: phpmyadmin
    restart: unless-stopped
    environment:
      PMA_HOST: mysql
      PMA_PORT: 3306
      PMA_USER: root
      PMA_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root_secure_password}
    ports:
      - "8080:80"
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - db_network

volumes:
  mysql_data:
    driver: local

networks:
  db_network:
    driver: bridge
```

### MySQL Custom Configuration

Create `my.cnf` for production tuning:

```ini
[mysqld]
# InnoDB settings
innodb_buffer_pool_size = 512M           # 50-70% of available RAM
innodb_log_file_size = 128M
innodb_flush_log_at_trx_commit = 1       # 2 for less strict durability
innodb_flush_method = O_DIRECT
innodb_io_capacity = 2000                # Adjust for SSD (default 200)
innodb_io_capacity_max = 4000

# Connection settings
max_connections = 200
max_connect_errors = 1000000
wait_timeout = 600
interactive_timeout = 600

# Query cache (disabled in 8.0+, use application-level caching)
# query_cache_type = 0

# Binary logging for replication
server_id = 1
log_bin = mysql-bin
binlog_format = ROW
expire_logs_days = 7
sync_binlog = 1

# Character set
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# Slow query log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
```

## MariaDB: The Independent MySQL Fork

MariaDB was created by MySQL's original developers as a community-driven fork after Oracle's acquisition of MySQL. It maintains full MySQL compatibility while adding features that Oracle has not merged into MySQL.

### Key Strengths

- **True Open-Source Governance**. MariaDB is governed by the MariaDB Foundation, a non-profit organization. No single company controls its development roadmap. This independence matters for organizations concerned about Oracle's licensing direction.
- **Galera Cluster**. MariaDB's synchronous multi-primary replication is production-ready and easier to set up than MySQL Group Replication. All nodes are writable, and the cluster provides automatic failover with zero data loss.
- **Performance Optimizations**. MariaDB includes the Aria storage engine, thread pool (free, unlike MySQL Enterprise), and optimizer improvements that can outperform MySQL on certain workloads.
- **MySQL Compatibility**. Drop-in replacement for MySQL in most cases. Same client libraries, same SQL syntax, same ecosystem tools. Migration from MySQL to MariaDB is typically straightforward.
- **Additional Features**. Sequence tables, virtual columns, temporal tables, and the CONNECT storage engine (for federated queries to external data sources) are available without enterprise licensing.

### MariaDB Docker Setup with Galera Cluster

A three-node Galera Cluster provides high availability with automatic failover:

```yaml
version: "3.9"

services:
  mariadb-1:
    image: mariadb:11
    container_name: mariadb-node1
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD:-root_secure}
      MARIADB_DATABASE: app_database
      MARIADB_USER: app_user
      MARIADB_PASSWORD: ${MARIADB_PASSWORD:-changeme_secure}
      MARIADB_GALERA_CLUSTER_NAME: galera_cluster
      MARIADB_GALERA_CLUSTER_ADDRESS: "gcomm://"
      MARIADB_GALERA_MARIABACKUP_USER: sst_user
      MARIADB_GALERA_MARIABACKUP_PASSWORD: ${SST_PASSWORD:-sst_secure}
    volumes:
      - mariadb1_data:/var/lib/mysql
      - ./galera.cnf:/etc/mysql/conf.d/galera.cnf:ro
    ports:
      - "3306:3306"
      - "4567:4567"
      - "4568:4568"
      - "4444:4444"
    networks:
      galera_net:
        ipv4_address: 172.20.0.10

  mariadb-2:
    image: mariadb:11
    container_name: mariadb-node2
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD:-root_secure}
      MARIADB_GALERA_CLUSTER_NAME: galera_cluster
      MARIADB_GALERA_CLUSTER_ADDRESS: "gcomm://mariadb-1,mariadb-3"
      MARIADB_GALERA_MARIABACKUP_USER: sst_user
      MARIADB_GALERA_MARIABACKUP_PASSWORD: ${SST_PASSWORD:-sst_secure}
    volumes:
      - mariadb2_data:/var/lib/mysql
      - ./galera.cnf:/etc/mysql/conf.d/galera.cnf:ro
    ports:
      - "3307:3306"
      - "4567"
      - "4568"
      - "4444"
    networks:
      galera_net:
        ipv4_address: 172.20.0.11

  mariadb-3:
    image: mariadb:11
    container_name: mariadb-node3
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD:-root_secure}
      MARIADB_GALERA_CLUSTER_NAME: galera_cluster
      MARIADB_GALERA_CLUSTER_ADDRESS: "gcomm://mariadb-1,mariadb-2"
      MARIADB_GALERA_MARIABACKUP_USER: sst_user
      MARIADB_GALERA_MARIABACKUP_PASSWORD: ${SST_PASSWORD:-sst_secure}
    volumes:
      - mariadb3_data:/var/lib/mysql
      - ./galera.cnf:/etc/mysql/conf.d/galera.cnf:ro
    ports:
      - "3308:3306"
      - "4567"
      - "4568"
      - "4444"
    networks:
      galera_net:
        ipv4_address: 172.20.0.12

volumes:
  mariadb1_data:
    driver: local
  mariadb2_data:
    driver: local
  mariadb3_data:
    driver: local

networks:
  galera_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

Galera configuration (`galera.cnf`):

```ini
[mysqld]
binlog_format=ROW
default-storage-engine=innodb
innodb_autoinc_lock_mode=2

# Galera Provider Configuration
wspec_on=ON
wspec_provider=/usr/lib/galera/libgalera_smm.so
wspec_cluster_address=gcomm://
wspec_node_name=mariadb-1
wspec_sst_method=mariabackup

# Node-specific settings (override per node)
wspec_node_address=172.20.0.10
wspec_provider_options="gcache.size=1G"

# Cluster settings
wspec_slave_threads=4
wspec_certify_nonPK=ON
wspec_max_ws_size=2147483647
```

## Choosing the Right Database for Your Workload

### When to Choose PostgreSQL

- **Complex analytical queries**. PostgreSQL's query planner, parallel execution, and advanced indexing (GIN, GiST, BRIN, SP-GiST) make it superior for data-heavy operations.
- **Geospatial applications**. PostGIS is the industry standard for spatial data. No other open-source database comes close.
- **JSON document storage with relational queries**. JSONB with GIN indexes gives you document-database flexibility with SQL query power.
- **Data integrity requirements**. If your application requires strict constraints, deferred constraint checking, or exclusion constraints, PostgreSQL is the right choice.
- **Extensibility needs**. If you anticipate needing custom data types, procedural languages, or specialized indexes, PostgreSQL's extension architecture is unmatched.
- **Time-series data**. TimescaleDB turns PostgreSQL into a competitive time-series database with automatic partitioning and continuous aggregates.

### When to Choose MySQL

- **Existing ecosystem compatibility**. If your application framework (WordPress, Drupal, Django with MySQL backend) assumes MySQL, stick with it.
- **Simple read-heavy workloads**. MySQL excels at straightforward SELECT queries on well-indexed tables — the pattern behind most content-driven websites.
- **Resource-constrained environments**. MySQL typically consumes less memory than PostgreSQL, making it suitable for small VPS instances or edge deployments.
- **Familiar tooling**. If your team already knows MySQL administration, the operational learning curve is lower.

### When to Choose MariaDB

- **MySQL compatibility with open governance**. You want MySQL compatibility but prefer a database controlled by a non-profit foundation rather than a corporation.
- **Galera Cluster requirements**. You need synchronous multi-primary replication with automatic failover and zero data loss.
- **Thread pool at no cost**. MySQL's thread pool is an enterprise-only feature; MariaDB includes it in the free version.
- **Migration from MySQL**. You want to move away from Oracle-controlled MySQL with minimal application changes.

## Backup and Recovery Strategies

Regardless of which database you choose, backups are non-negotiable. Here are proven strategies for each:

### PostgreSQL Backup with pg_dump and WAL Archiving

```bash
# Logical backup (single database)
pg_dump -U app_user -d app_database -Fc -f /backups/app_$(date +%Y%m%d).dump

# Restore
pg_restore -U app_user -d app_database /backups/app_20260415.dump

# Physical backup with continuous WAL archiving
# Enable in postgresql.conf:
# archive_mode = on
# archive_command = 'cp %p /wal_archive/%f'

# Base backup
pg_basebackup -D /backups/base_$(date +%Y%m%d) -Ft -z -P

# Point-in-time recovery:
# 1. Restore base backup to data directory
# 2. Create recovery.signal
# 3. Set restore_command in postgresql.conf
# 4. Set recovery_target_time = '2026-04-15 14:30:00'
# 5. Start PostgreSQL
```

### MySQL/MariaDB Backup with mysqldump and Binary Logs

```bash
# Logical backup with binary log position
mysqldump -u root -p --all-databases --single-transaction \
  --flush-logs --master-data=2 > /backups/full_$(date +%Y%m%d).sql

# Restore
mysql -u root -p < /backups/full_20260415.sql

# Incremental backup from binary logs
mysqlbinlog --start-datetime="2026-04-15 00:00:00" \
  --stop-datetime="2026-04-15 14:30:00" \
  /var/lib/mysql/mysql-bin.* > /backups/incremental.sql

# MariaDB backup with mariabackup (hot backup)
mariabackup --backup --target-dir=/backups/hot_$(date +%Y%m%d) \
  --user=root --password=your_password

# Prepare backup for restore
mariabackup --prepare --target-dir=/backups/hot_20260415

# Restore (stop MariaDB first, clear data dir)
mariabackup --copy-back --target-dir=/backups/hot_20260415
chown -R mysql:mysql /var/lib/mysql
```

### Automated Backup Script

A universal backup script that works with any database type:

```bash
#!/bin/bash
# automated-db-backup.sh
# Usage: ./automated-db-backup.sh [postgres|mysql|mariadb]

set -euo pipefail

DB_TYPE="${1:-postgres}"
BACKUP_DIR="/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

case "$DB_TYPE" in
  postgres)
    pg_dump -U app_user -d app_database -Fc \
      -f "$BACKUP_DIR/pg_${TIMESTAMP}.dump"
    ;;
  mysql)
    mysqldump -u root --all-databases --single-transaction \
      --routines --triggers \
      | gzip > "$BACKUP_DIR/mysql_${TIMESTAMP}.sql.gz"
    ;;
  mariadb)
    mariabackup --backup --target-dir="$BACKUP_DIR/mariadb_${TIMESTAMP}" \
      --user=root --password="${MARIADB_ROOT_PASSWORD}"
    ;;
  *)
    echo "Unknown database type: $DB_TYPE"
    exit 1
    ;;
esac

# Compress uncompressed backups
find "$BACKUP_DIR" -name "*.dump" -not -name "*.gz" -exec gzip {} \;

# Remove backups older than retention period
find "$BACKUP_DIR" -type f -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup completed: $DB_TYPE ($TIMESTAMP)"
```

Add to cron for automated daily backups:

```bash
# Daily backup at 2:00 AM
0 2 * * * /usr/local/bin/automated-db-backup.sh postgres >> /var/log/db-backup.log 2>&1
```

## Migration Between Databases

Migrating between PostgreSQL, MySQL, and MariaDB requires careful planning. Here is a general migration workflow:

1. **Schema conversion**. Use `pgloader` for MySQL/PostgreSQL migration, or `mysql-workbench` for reverse engineering and schema generation.
2. **Data type mapping**. Review incompatible types: PostgreSQL's `SERIAL` maps to MySQL `AUTO_INCREMENT`, `BOOLEAN` maps to `TINYINT(1)`, `JSONB` maps to `JSON`.
3. **Syntax adjustments**. Update queries that use database-specific functions: `NOW()` works everywhere, but `CURRENT_TIMESTAMP` behavior differs, string concatenation uses `||` in PostgreSQL and `CONCAT()` in MySQL.
4. **Test thoroughly**. Run your application test suite against the target database before cutting over.
5. **Dual-write period**. For zero-downtime migration, configure your application to write to both databases temporarily, then switch reads.

### pgloader Example: MySQL to PostgreSQL

```bash
# Install pgloader
apt install pgloader

# Create a load file (mysql_to_pg.load)
LOAD DATABASE
  FROM mysql://root:password@mysql_host/app_database
  INTO postgresql://app_user:password@pg_host/app_database

  WITH include drop, create tables, create indexes, reset sequences
  SET maintenance_work_mem to '128MB',
      work_mem to '16MB'

  CAST type datetime to timestamptz
               drop default,
       type tinyint to boolean using tinyint-to-boolean,
       type bigint when (= precision 20) to bigint drop typemod
;

# Run migration
pgloader mysql_to_pg.load
```

## Monitoring Your Self-Hosted Database

A database without monitoring is a liability. Set up basic health checks:

```sql
-- PostgreSQL: check database size
SELECT pg_size_pretty(pg_database_size('app_database'));

-- PostgreSQL: find slow queries
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- MySQL/MariaDB: check slow queries
SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;

-- MySQL/MariaDB: show process list
SHOW FULL PROCESSLIST;
```

For comprehensive monitoring, deploy **pgwatch2** for PostgreSQL or **Percona Monitoring and Management (PMM)** for MySQL/MariaDB alongside your database. Both provide Docker-based deployment with Grafana dashboards out of the box.

## Final Recommendation

For most new self-hosted projects in 2026, **PostgreSQL** is the default choice. Its combination of SQL compliance, extensibility, JSONB performance, and the PostGIS ecosystem make it the most versatile option. The learning curve is slightly steeper, but the return on investment in developer productivity and query correctness is significant.

**MySQL** remains the right choice when ecosystem compatibility matters most — WordPress, legacy applications, or teams with deep MySQL expertise. It is reliable, well-understood, and performs excellently for its intended workloads.

**MariaDB** shines when you need MySQL compatibility with open-source governance, or when Galera Cluster's synchronous multi-primary replication fits your high-availability requirements. The Thread Pool inclusion at no cost is a genuine differentiator.

Whichever you choose, self-hosting your database puts you in control of your most valuable asset — your data. With Docker Compose, automated backups, and proper monitoring, the operational overhead is manageable even for small teams and home lab enthusiasts.
