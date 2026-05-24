---
title: "Self-Hosted Database Audit & Activity Monitoring: pgAudit vs MySQL Audit Plugin vs Auditbeat (2026)"
date: "2026-05-25"
tags: ["database-security", "audit", "postgresql", "mysql", "compliance"]
draft: false
---

Database audit trails are essential for compliance frameworks like PCI DSS, HIPAA, SOC 2, and GDPR. They answer the critical question: who accessed what data, when, and how? Without audit logging, you cannot detect unauthorized data access, prove compliance during audits, or investigate security incidents after the fact.

This guide compares three leading self-hosted database audit solutions: **pgAudit** for PostgreSQL, the **MySQL Audit Plugin** (formerly McAfee), and **Auditbeat** for infrastructure-wide audit collection. We'll examine deployment, audit policies, performance impact, and compliance coverage.

## Comparison Overview

| Feature | pgAudit | MySQL Audit Plugin | Auditbeat |
|---------|---------|-------------------|-----------|
| Database | PostgreSQL | MySQL / MariaDB | All (via modules) |
| License | PostgreSQL License | GPL v2 | Elastic License 2.0 |
| Audit Granularity | Session, Object, DDL, DML | All queries, connections | File, process, network, socket |
| Output Format | PostgreSQL log | JSON, syslog | JSON, Elasticsearch |
| Performance Impact | Low (~2-5%) | Low (~1-3%) | Very low |
| Compliance | PCI DSS, SOC 2, HIPAA | PCI DSS, SOC 2 | PCI DSS, HIPAA, SOC 2 |
| Installation | PostgreSQL extension | Plugin installation | Binary package |
| GitHub Stars | 1,640+ | 1,550+ | 12,600+ |

## pgAudit for PostgreSQL

pgAudit is the de facto PostgreSQL audit extension, maintained by the PostgreSQL community and included in many managed PostgreSQL distributions. It provides session-level and object-level audit logging with fine-grained control over which events are captured.

### Key Features

- **Session Auditing**: Logs all queries executed within a database session
- **Object Auditing**: Tracks access to specific tables, columns, or functions
- **DDL Logging**: Captures schema changes including CREATE, ALTER, DROP, and GRANT statements
- **Role Filtering**: Exclude trusted roles from audit trails to reduce noise
- **Log Tagging**: Each audit entry includes a structured `AUDIT` prefix for easy parsing

### Installation and Configuration

```sql
-- Install the extension
CREATE EXTENSION pgaudit;

-- Configure in postgresql.conf
ALTER SYSTEM SET shared_preload_libraries = 'pgaudit';
ALTER SYSTEM SET pgaudit.log = 'read, write, ddl';
ALTER SYSTEM SET pgaudit.log_catalog = 'off';
ALTER SYSTEM SET pgaudit.log_level = 'log';
ALTER SYSTEM SET pgaudit.log_parameter = 'off';

-- Restart PostgreSQL
SELECT pg_reload_conf();
```

For object-level auditing on specific tables:

```sql
-- Audit all SELECT and INSERT on the users table
ALTER ROLE app_user SET pgaudit.log = 'read, write';

-- Or use GRANT for role-based audit
GRANT SELECT, INSERT ON sensitive_data TO audit_role;
ALTER SYSTEM SET pgaudit.role = 'audit_role';
```

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    container_name: postgres-audit
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: securepassword
      POSTGRES_DB: audited_db
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres
      -c shared_preload_libraries=pgaudit
      -c pgaudit.log=read,write,ddl
      -c pgaudit.log_catalog=off
      -c log_destination=csvlog
      -c logging_collector=on
      -c log_directory=/var/log/postgresql

volumes:
  pg-data:
```

The `init.sql` file installs the extension:

```sql
CREATE EXTENSION IF NOT EXISTS pgaudit;
```

### When to Choose pgAudit

- You run PostgreSQL and need compliance-grade audit logging
- You require object-level auditing for sensitive tables
- You want minimal performance overhead with native PostgreSQL integration
- Your compliance framework mandates DDL and DML audit trails

## MySQL Audit Plugin

The MySQL Audit Plugin (originally developed by McAfee, now maintained by the MySQL community) provides comprehensive audit logging for MySQL and MariaDB servers.

### Key Features

- **Full Query Logging**: Captures every SQL statement with user, host, and timestamp
- **Connection Tracking**: Logs successful and failed login attempts
- **JSON Output**: Structured JSON format for easy parsing and SIEM integration
- **Table Filtering**: Audit specific tables or exclude system databases
- **Syslog Integration**: Forward audit events to syslog for centralized collection

### Installation

```bash
# Download the plugin
wget https://github.com/mcafee/mysql-audit/releases/download/v1.2.10/audit-plugin-mysql-8.0-1.2.10-801-linux-x86_64.zip
unzip audit-plugin-mysql-8.0-1.2.10-801-linux-x86_64.zip

# Install the plugin
cp audit-plugin-mysql-8.0-1.2.10-801-linux-x86_64/lib/libaudit_plugin.so /usr/lib/mysql/plugin/

# Enable in my.cnf
cat >> /etc/mysql/my.cnf << 'EOF'
[mysqld]
plugin-load-add=libaudit_plugin.so
audit_json_file=1
audit_json_log_file=/var/log/mysql/audit.log
audit_record_cmds=select,insert,update,delete,create,drop,alter,grant,revoke
audit_whitelist_users=root,monitor
EOF

# Restart MySQL
systemctl restart mysql
```

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  mysql:
    image: mysql:8.0
    container_name: mysql-audit
    restart: unless-stopped
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
    volumes:
      - mysql-data:/var/lib/mysql
      - ./audit.cnf:/etc/mysql/conf.d/audit.cnf
      - ./libaudit_plugin.so:/usr/lib/mysql/plugin/libaudit_plugin.so:ro
      - audit-logs:/var/log/mysql

volumes:
  mysql-data:
  audit-logs:
```

### When to Choose MySQL Audit Plugin

- You run MySQL or MariaDB and need comprehensive query-level auditing
- JSON-formatted audit logs are required for SIEM integration
- You need to track both successful and failed authentication attempts
- Your compliance mandate covers database access logging

## Auditbeat for Infrastructure-Wide Audit Collection

Auditbeat is part of the Elastic Beats family and collects audit data at the operating system level — file integrity monitoring, process execution tracking, network connection logging, and user login events. While not database-specific, it provides a broader security posture view that complements database-level audit tools.

### Key Features

- **File Integrity Monitoring**: Detects unauthorized changes to configuration files and binaries
- **Process Execution Logging**: Tracks all process launches with command-line arguments
- **Network Connection Tracking**: Logs inbound and outbound connections
- **User Login Events**: Captures SSH logins, sudo usage, and session events
- **Elasticsearch Integration**: Ships directly to Elasticsearch for centralized analysis

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  auditbeat:
    image: docker.elastic.co/beats/auditbeat:8.12.0
    container_name: auditbeat
    restart: unless-stopped
    user: root
    pid: host
    cap_add:
      - AUDIT_CONTROL
      - AUDIT_READ
    volumes:
      - ./auditbeat.yml:/usr/share/auditbeat/auditbeat.yml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc:/host/proc:ro
      - /etc:/host/etc:ro
    command:
      - "--strict.perms=false"
      - "-e"

volumes:
  auditbeat-data:
    driver: local
```

`auditbeat.yml` configuration:

```yaml
auditbeat.modules:
  - module: file_integrity
    paths:
      - /etc/mysql
      - /var/lib/mysql
      - /etc/postgresql

  - module: system
    datasets:
      - host
      - login
      - process
      - socket
      - user

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "auditbeat-%{+yyyy.MM.dd}"
```

### When to Choose Auditbeat

- You need host-level audit coverage across your entire infrastructure
- File integrity monitoring is a compliance requirement
- You already use the Elastic Stack for log aggregation
- You want to correlate database events with OS-level security events

## Why Self-Host Your Database Audit Tools?

Database audit logs contain sensitive information about who accessed what data and when. Sending these logs to a third-party SaaS platform introduces privacy and compliance risks. Self-hosted audit tools keep all audit trails within your infrastructure boundary, satisfying data residency requirements under GDPR, HIPAA, and financial regulations.

Self-hosted audit solutions also give you complete control over log retention policies. Instead of being limited by a vendor's retention window, you define how long audit records are kept — critical for compliance frameworks that mandate multi-year retention. The cost savings are significant too: audit log volumes can be massive, and per-gigabyte SaaS pricing becomes prohibitive at scale.

For organizations managing multiple database engines, combining pgAudit (PostgreSQL) with the MySQL Audit Plugin (MySQL) and Auditbeat (infrastructure) creates a comprehensive audit posture that covers every layer of your data stack.

For related reading, see our [log integrity and tamper-evident audit logging guide](../2026-04-25-self-hosted-log-integrity-tamper-evident-audit-logging-guide-2026/) and our [Kubernetes security auditing tools comparison](../2026-05-10-self-hosted-kubernetes-security-auditing-kube-hunter-kubeaudit-peirates-guide/). If you need broader server security auditing, our [Lynis vs OpenSCAP vs Goss comparison](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide-2026/) covers host-level compliance scanning.

## Choosing the Right Database Audit Tool

For PostgreSQL environments, pgAudit is the clear choice — it is native, well-maintained, and provides the granular object-level auditing that compliance auditors expect. For MySQL deployments, the MySQL Audit Plugin delivers comparable coverage with JSON-formatted output ready for SIEM ingestion.

If your compliance requirements extend beyond the database layer to include file integrity, process execution, and network connection tracking, Auditbeat complements database-specific tools by providing the infrastructure-level context that security teams need for incident investigation.

## FAQ

### What is the difference between pgAudit session and object auditing?

Session auditing logs all queries executed by a database session, regardless of which tables are accessed. Object auditing is more targeted — it only logs access to specific tables, columns, or functions that you explicitly configure. Use session auditing for broad compliance coverage and object auditing for focused monitoring of sensitive data.

### Does pgAudit impact PostgreSQL performance?

Yes, but the impact is minimal. pgAudit adds approximately 2-5% overhead on write-heavy workloads and less than 1% on read-heavy workloads. The actual impact depends on your audit policy — logging every SELECT on every table will have higher overhead than logging only DDL statements.

### Can the MySQL Audit Plugin filter out specific users?

Yes. The `audit_whitelist_users` configuration parameter lets you exclude trusted accounts (like monitoring or backup users) from audit logging. This reduces log volume and focuses audit records on actual application and administrative activity.

### Does Auditbeat replace database-specific audit tools?

No. Auditbeat provides infrastructure-level audit coverage (file changes, process execution, network connections) but does not capture SQL query content or database-level access patterns. Use Auditbeat alongside pgAudit or the MySQL Audit Plugin for comprehensive coverage.

### How do I forward audit logs to a SIEM?

pgAudit writes to PostgreSQL's standard log output, which can be shipped via Fluent Bit, Filebeat, or rsyslog. The MySQL Audit Plugin supports direct JSON file output and syslog forwarding. Auditbeat ships natively to Elasticsearch and Logstash. All three integrate with major SIEM platforms.

### What compliance frameworks require database audit logging?

PCI DSS (Requirement 10), HIPAA (Security Rule §164.312(b)), SOC 2 (CC6.1, CC7.2), and GDPR (Article 30) all require audit trails for data access. Financial regulations like SOX and Basel III also mandate comprehensive audit logging for database systems handling regulated data.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Audit & Activity Monitoring: pgAudit vs MySQL Audit Plugin vs Auditbeat (2026)",
  "description": "Compare self-hosted database audit solutions: pgAudit for PostgreSQL, MySQL Audit Plugin, and Auditbeat for infrastructure-wide audit collection. Includes Docker Compose configs and compliance coverage analysis.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
