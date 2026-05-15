---
title: "Self-Hosted DNS Zone Backup and Recovery: BIND vs PowerDNS vs NSD"
date: "2026-05-15"
tags: ["dns", "backup", "disaster-recovery", "infrastructure"]
draft: false
---

DNS zones contain the authoritative mapping between domain names and IP addresses for your infrastructure. Losing zone data means your domains become unreachable — email bounces, websites go offline, and API endpoints fail. While DNS zone transfers (AXFR/IXFR) provide replication between servers, they do not constitute a backup strategy. This guide covers DNS zone backup and recovery approaches for three authoritative DNS servers: **BIND 9**, **PowerDNS Authoritative**, and **NSD**.

We will explore native backup mechanisms, automated export tools, disaster recovery procedures, and Docker Compose deployments for each platform.

## BIND 9: Native Zone File Backup

BIND 9 stores zone data in plain-text zone files on disk. This makes backup straightforward — you can copy the files directly or use standard backup tools.

### Zone File Storage

BIND 9 zone files are typically stored in `/etc/bind/zones/` or `/var/named/`. Each zone has its own file in standard RFC 1035 format. BIND automatically updates these files when you make changes via `nsupdate` (dynamic DNS) if the `update-policy` and `masterfile-format` are configured correctly.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  bind9:
    image: ubuntu/bind9:9.18
    environment:
      BIND9_USER: root
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "953:953/tcp"
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./zones:/etc/bind/zones
      - bind9-backup:/backup
    command: >
      -4 -u root -c /etc/bind/named.conf
      -f /etc/bind/zones

  zone-backup:
    image: ubuntu/bind9:9.18
    entrypoint: ["bash", "-c"]
    command: >
      "cp -r /etc/bind/zones /backup/zones-$(date +%Y%m%d) &&
      echo 'Zone backup completed' &&
      ls -la /backup/"
    volumes:
      - ./zones:/etc/bind/zones:ro
      - bind9-backup:/backup
    depends_on:
      - bind9

volumes:
  bind9-backup:
```

### Manual Backup Commands

```bash
# Use rndc to freeze zones before copying
docker compose exec bind9 rndc freeze example.com

# Copy zone files
docker compose exec bind9 cp -r /etc/bind/zones /backup/zones-backup

# Thaw zones after backup
docker compose exec bind9 rndc thaw example.com

# Export zone via AXFR (alternative approach)
dig @localhost example.com AXFR > /backup/example.com.zone
```

### Automated Backup Script

```bash
#!/bin/bash
# bind-zone-backup.sh - Automated BIND zone backup
BACKUP_DIR="/backup/bind-zones"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR/$DATE"

# Freeze all zones, copy, then thaw
rndc freeze -all
cp -r /etc/bind/zones/* "$BACKUP_DIR/$DATE/"
rndc thaw -all

# Create compressed archive
tar -czf "$BACKUP_DIR/zones-$DATE.tar.gz" -C "$BACKUP_DIR" "$DATE"
rm -rf "$BACKUP_DIR/$DATE"

# Retention: keep last 30 days
find "$BACKUP_DIR" -name "zones-*.tar.gz" -mtime +30 -delete
echo "BIND zone backup completed: zones-$DATE.tar.gz"
```

## PowerDNS Authoritative: Database-Backed Backup

PowerDNS Authoritative stores zone data in a database backend (MySQL, PostgreSQL, SQLite). Backing up zones means backing up the database, which provides consistent snapshots without freezing zones.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  pdns-auth:
    image: powerdns/pdns-auth-49:latest
    environment:
      - PDNS_gmysql_host=pdns-db
      - PDNS_gmysql_port=3306
      - PDNS_gmysql_user=pdns
      - PDNS_gmysql_password=pdns-secret-pass
      - PDNS_gmysql_dbname=pdns
      - PDNS_master=yes
      - PDNS_api=yes
      - PDNS_api-key=pdns-api-key-12345
      - PDNS_webserver=yes
      - PDNS_webserver-address=0.0.0.0
      - PDNS_webserver-password=webpass
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8081:8081"
    depends_on:
      - pdns-db

  pdns-db:
    image: mariadb:11
    environment:
      MARIADB_ROOT_PASSWORD: root-secret
      MARIADB_DATABASE: pdns
      MARIADB_USER: pdns
      MARIADB_PASSWORD: pdns-secret-pass
    volumes:
      - pdns-db-data:/var/lib/mysql
      - ./init-pdns.sql:/docker-entrypoint-initdb.d/init.sql:ro

  pdns-backup:
    image: mariadb:11
    entrypoint: ["bash", "-c"]
    command: >
      "mysqldump -h pdns-db -u pdns -ppdns-secret-pass pdns
      | gzip > /backup/pdns-backup-$(date +%Y%m%d_%H%M%S).sql.gz &&
      echo 'PowerDNS database backup completed'"
    volumes:
      - pdns-backup-data:/backup
    depends_on:
      - pdns-db

volumes:
  pdns-db-data:
  pdns-backup-data:
```

Database initialization script (`init-pdns.sql`):

```sql
CREATE DATABASE IF NOT EXISTS pdns;
USE pdns;

CREATE TABLE domains (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  master VARCHAR(128) DEFAULT NULL,
  last_check INT DEFAULT NULL,
  type VARCHAR(6) NOT NULL,
  notified_serial INT UNSIGNED DEFAULT NULL,
  account VARCHAR(40) DEFAULT NULL,
  options VARCHAR(64000) DEFAULT NULL,
  catalog VARCHAR(255) DEFAULT NULL
);

CREATE TABLE records (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  domain_id INT DEFAULT NULL,
  name VARCHAR(255) DEFAULT NULL,
  type VARCHAR(10) DEFAULT NULL,
  content VARCHAR(64000) DEFAULT NULL,
  ttl INT DEFAULT NULL,
  prio INT DEFAULT NULL,
  disabled TINYINT(1) DEFAULT 0,
  ordername VARCHAR(255) BINARY DEFAULT NULL,
  auth TINYINT(1) DEFAULT 1
);
```

### API-Based Zone Export

PowerDNS provides a REST API for zone export, which is useful for backup without database access:

```bash
# Export a zone via API
curl -s -H "X-API-Key: pdns-api-key-12345"   http://localhost:8081/api/v1/servers/localhost/zones/example.com   | jq '.resourceRecords[] | "\(.name) \(.type) \(.content)"'   > /backup/example.com-export.txt

# List all zones
curl -s -H "X-API-Key: pdns-api-key-12345"   http://localhost:8081/api/v1/servers/localhost/zones   | jq '.[].name'
```

### Database Backup with mysqldump

```bash
# Full database backup
mysqldump -u pdns -p pdns | gzip > pdns-full-backup.sql.gz

# Restore from backup
gunzip < pdns-full-backup.sql.gz | mysql -u pdns -p pdns

# Incremental backup via binary logs (if enabled)
mysqlbinlog --start-datetime="2026-05-15 00:00:00"   /var/lib/mysql/mariadb-bin.000001 > incremental-backup.sql
```

## NSD: Minimalist Zone Backup

NSD (Name Server Daemon) is a lightweight authoritative-only DNS server. Like BIND, it stores zones in plain-text files, making backup simple. NSD focuses on being a fast, secure, and easy-to-manage authoritative server without recursive resolution capabilities.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  nsd:
    image: nlnetlabs/nsd:latest
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8952:8952/tcp"
    volumes:
      - ./nsd.conf:/etc/nsd/nsd.conf:ro
      - ./zones:/etc/nsd/zones
      - nsd-backup:/backup
    command: ["-d", "-v"]

  nsd-backup:
    image: alpine:latest
    entrypoint: ["sh", "-c"]
    command: >
      "cp /etc/nsd/zones/* /backup/ &&
      echo 'NSD zone backup completed' &&
      ls -la /backup/"
    volumes:
      - ./zones:/etc/nsd/zones:ro
      - nsd-backup:/backup
    depends_on:
      - nsd

volumes:
  nsd-backup:
```

NSD configuration (`nsd.conf`):

```
server:
  port: 53
  ip-address: 0.0.0.0
  hide-version: yes
  database: ""

zone:
  name: "example.com"
  zonefile: "/etc/nsd/zones/example.com.zone"

zone:
  name: "example.org"
  zonefile: "/etc/nsd/zones/example.org.zone"
```

### Zone File Backup

```bash
# NSD stores zones in plain text files - direct copy works
cp /etc/nsd/zones/*.zone /backup/zones-$(date +%Y%m%d)/

# Use nsd-checkzone to validate before backup
nsd-checkzone example.com /etc/nsd/zones/example.com.zone

# AXFR export from running NSD instance
dig @localhost example.com AXFR > /backup/example.com-axfr.zone
```

### NSD Zone Signing Backup

If you use DNSSEC with NSD, you also need to back up the signed zone files and key material:

```bash
# Backup zones + DNSSEC keys
tar -czf /backup/nsd-dnssec-backup-$(date +%Y%m%d).tar.gz   /etc/nsd/zones/   /etc/nsd/keys/
```

## Comparison: BIND vs PowerDNS vs NSD Backup

| Feature | BIND 9 | PowerDNS Authoritative | NSD |
|---------|--------|----------------------|-----|
| **Storage backend** | Plain-text zone files | Database (MySQL, PG, SQLite) | Plain-text zone files |
| **Backup method** | File copy, AXFR export | Database dump, API export | File copy, AXFR export |
| **Consistency during backup** | Requires `rndc freeze` | Database transaction consistency | File copy (live) |
| **Incremental backup** | No (full zone files) | Database binary logs | No (full zone files) |
| **Zone export format** | RFC 1035 zone file | JSON via API, SQL dump | RFC 1035 zone file |
| **API access** | No (control via rndc) | Full REST API | No (control via nsd-control) |
| **DNSSEC key backup** | Manual (key files) | In database (if stored) | Manual (key files) |
| **Catalog zones** | Yes (RFC 7494) | Yes | No |
| **Docker image** | ubuntu/bind9:9.18 | powerdns/pdns-auth-49 | nlnetlabs/nsd:latest |
| **GitHub / project** | ISC (isc.org) | PowerDNS (pdns.nl) | NLnet Labs (nlnetlabs.nl) |
| **License** | MPL 2.0 | GPL 2.0 | BSD 2-Clause |
| **Best for** | Traditional zone file workflows | Database-backed, API-driven deployments | Minimalist authoritative-only setups |

## Why Self-Host Your DNS Zone Backups?

DNS zone data is the foundation of your network infrastructure. Losing it means every domain you manage stops resolving — websites, email, APIs, and internal services all become unreachable. Self-hosted zone backups ensure:

- **Immediate recovery capability** — restore zones on your own servers without waiting for a managed DNS provider
- **Historical versioning** — keep historical zone snapshots for auditing and rollback after accidental changes
- **Regulatory compliance** — maintain backup copies in specific geographic locations to meet data residency requirements
- **Cost control** — avoid per-zone backup fees charged by managed DNS providers
- **Disaster recovery independence** — if your primary DNS provider experiences an outage, you can quickly deploy a backup instance

For comprehensive DNS health validation to ensure your backed-up zones are syntactically correct before deploying them, see our [DNSViz vs Zonemaster guide](../2026-04-25-dnsviz-vs-zonemaster-self-hosted-dns-health-validation-guide-2026/). If you manage zone provisioning across multiple DNS providers, our [DNSControl vs OctoDNS vs Lexicon comparison](../2026-05-13-self-hosted-dns-zone-provisioning-dnscontrol-octodns-lexicon-guide/) covers infrastructure-as-code approaches. For DNSSEC validation of your restored zones, our [Unbound vs Knot Resolver vs PowerDNS DNSSEC guide](../2026-05-14-self-hosted-dnssec-validation-unbound-knot-resolver-powerdns-guide/) covers validation strategies.

## FAQ

### How often should I back up DNS zones?

Back up zones after every change and at least daily for static zones. Use `rndc notify` (BIND) or PowerDNS API webhooks to trigger backups immediately after zone modifications. For high-churn environments (dynamic DNS), consider hourly backups or continuous database replication.

### Can I restore a BIND zone backup to PowerDNS?

Yes. BIND zone files are in standard RFC 1035 format, which PowerDNS can import using `pdnsutil load-zone` or the PowerDNS API. The reverse (PowerDNS database to BIND) requires exporting zones via the API or a database query and formatting as zone files.

### Does NSD support zone transfers as a backup method?

NSD supports outgoing AXFR (zone transfers) to secondary servers. You can configure a secondary NSD or BIND instance to pull zones via AXFR, effectively creating a live backup. However, this is replication, not a point-in-time backup — if a zone is corrupted on the primary, the corruption propagates to the secondary.

### What is the difference between a zone file backup and an AXFR export?

A zone file backup copies the raw file from disk, including comments, formatting, and any non-standard directives. An AXFR export queries the running DNS server and receives only the standardized resource records. For restoration purposes, both are functionally equivalent, but zone files may contain additional metadata (SOA serial comments, TTL overrides) that AXFR does not preserve.

### How do I verify a DNS zone backup before deploying it?

Use `named-checkzone` (BIND), `nsd-checkzone` (NSD), or the PowerDNS API to validate the zone syntax before deployment. Check that the SOA serial is correct, all required record types are present (A, AAAA, MX, NS), and DNSSEC signatures (if applicable) are valid. Tools like DNSViz and Zonemaster provide comprehensive validation.

### Can I use rsync for BIND zone file backups?

Yes. rsync is an excellent tool for BIND zone file backups because it only transfers changed files. For large zone directories with hundreds of zones, rsync is significantly faster than full copies. Combine with `--backup` and `--backup-dir` to maintain versioned copies of changed files.

```bash
rsync -avz --backup --backup-dir=/backup/bind-incremental/$(date +%Y%m%d)   /etc/bind/zones/ backup-server:/backup/bind-zones/
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Zone Backup and Recovery: BIND vs PowerDNS vs NSD",
  "description": "Compare DNS zone backup and recovery strategies for BIND 9, PowerDNS Authoritative, and NSD. Includes Docker Compose configs, automated backup scripts, and disaster recovery procedures.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
