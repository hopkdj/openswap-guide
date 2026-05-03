---
title: "Self-Hosted DNS Logging and Analysis: dnstap, PowerDNS-Admin, and go-dnstap Comparison Guide"
date: 2026-05-03T17:00:00+00:00
draft: false
tags: ["dns", "logging", "monitoring", "self-hosted", "network-security", "dnstap"]
---

DNS logging and analysis is a critical component of network observability that many self-hosters overlook. While tools like Pi-hole and AdGuard Home focus on blocking and filtering, a dedicated DNS logging pipeline lets you capture every query, analyze traffic patterns, detect anomalies, and maintain audit trails for compliance. This guide compares three approaches to self-hosted DNS logging and analysis: **dnstap-based collectors**, **PowerDNS-Admin** for query logging, and **go-dnstap** for high-performance query capture.

## What Is DNS Logging and Why Does It Matter?

Every DNS query that passes through your recursive resolver reveals information about which devices on your network are communicating with which external services. DNS logging provides:

- **Security forensics** — trace which internal host queried a known malicious domain
- **Network troubleshooting** — identify slow resolutions, NXDOMAIN storms, or misconfigured clients
- **Compliance auditing** — maintain query logs for regulatory requirements (HIPAA, PCI-DSS, SOC 2)
- **Traffic analysis** — understand which services your infrastructure depends on
- **Anomaly detection** — spot DNS tunneling, data exfiltration, or C2 beacon patterns

Unlike basic query logs (text files written by your DNS resolver), structured logging formats like **dnstap** capture rich metadata: query type, response code, round-trip time, client IP, and response data. This structured data is what makes DNS analysis powerful.

## Comparison Table

| Feature | dnstap + go-dnstap | PowerDNS-Admin + pdns | Knot Resolver + log |
|---------|-------------------|----------------------|---------------------|
| Logging format | dnstap (binary protobuf) | pdns query log (JSON/text) | Knot query log (text) |
| Query detail | Full query/response pairs | Query + answer + timing | Query + response codes |
| Performance impact | Low (asynchronous) | Low (async via Lua) | Low (built-in) |
| Real-time streaming | Yes (via Unix socket) | Via PowerDNS API | Via file tailing |
| Storage backend | Flexible (any dnstap consumer) | MySQL/PostgreSQL | File-based |
| Web UI | Third-party (go-dnstap dashboard) | Built-in (PowerDNS-Admin) | None (CLI only) |
| Docker support | Yes | Yes | Yes |
| Active development | Yes (open-source) | Yes (open-source) | Yes (open-source) |
| Learning curve | Medium | Low | Low |
| Best for | High-volume logging & analysis | Full DNS management + logging | Simple query logging |

## dnstap: The Gold Standard for DNS Query Logging

**dnstap** is a flexible, structured logging format for DNS servers developed by ISC (the creators of BIND). It uses Protocol Buffers to encode rich query metadata into a compact binary format, making it ideal for high-throughput DNS logging.

### Supported DNS Servers

dnstap is natively supported by several popular DNS servers:

- **BIND 9** — via `dnstap` configuration directive
- **Unbound** — via `dnstap:` configuration block
- **Knot Resolver** — via the `dnstap` module
- **PowerDNS Recursor** — via `dnstap` support (4.4+)

### go-dnstap: High-Performance dnstap Collector

[go-dnstap](https://github.com/dnstap/golang-dnstap) and related tooling provide a fast, lightweight dnstap collector written in Go. It reads dnstap data from a Unix socket or file and can forward it to various backends.

#### Docker Compose for go-dnstap Collection

```yaml
version: "3.8"

services:
  dnstap-collector:
    image: ghcr.io/dnstap/dnstap:latest
    container_name: dnstap-collector
    restart: unless-stopped
    volumes:
      - dnstap-socket:/var/run/dnstap
      - dnstap-data:/data
    command: ["--socket", "/var/run/dnstap/dnstap.sock", "--output", "/data/dnstap.log"]
    ports:
      - "8080:8080"

  dnstap-viewer:
    image: ghcr.io/dnstap/dnstap-viewer:latest
    container_name: dnstap-viewer
    restart: unless-stopped
    depends_on:
      - dnstap-collector
    ports:
      - "3000:3000"
    volumes:
      - dnstap-data:/data:ro

volumes:
  dnstap-socket:
  dnstap-data:
```

#### Unbound Configuration for dnstap Output

```yaml
server:
    dnstap-enable: yes
    dnstap-socket-path: /var/run/dnstap/dnstap.sock
    dnstap-send-identity: yes
    dnstap-send-version: yes
    dnstap-log-resolve-query-messages: yes
    dnstap-log-resolve-response-messages: yes
    dnstap-log-forward-query-messages: yes
    dnstap-log-forward-response-messages: yes
```

### Installing and Configuring dnstap

To set up dnstap logging with Unbound:

```bash
# Install Unbound with dnstap support
sudo apt install unbound

# Create dnstap socket directory
sudo mkdir -p /var/run/dnstap
sudo chown unbound:unbound /var/run/dnstap

# Add dnstap config to unbound.conf (see above)
sudo systemctl restart unbound

# Verify dnstap socket is active
sudo ls -la /var/run/dnstap/dnstap.sock
```

### Parsing dnstap Data

The `dnstap` command-line tool can decode binary dnstap data into human-readable format:

```bash
# Decode dnstap data to text
dnstap -r /data/dnstap.log

# Filter for specific query types
dnstap -r /data/dnstap.log | grep "type: MX"

# Export to JSON for analysis
dnstap -r /data/dnstap.log -j > dnstap-data.json

# Count queries per domain
dnstap -r /data/dnstap.log | grep "query:" | awk '{print $3}' | sort | uniq -c | sort -rn | head -20
```

## PowerDNS-Admin with Query Logging

[PowerDNS-Admin](https://github.com/ngoduykhanh/PowerDNS-Admin) is a web-based management interface for PowerDNS that includes query logging and analytics capabilities. Combined with the PowerDNS Recursor's built-in logging, it provides a complete DNS logging and management solution.

### Docker Compose for PowerDNS-Admin

```yaml
version: "3.8"

services:
  pdns-recursor:
    image: powerdns/pdns-recursor-49:latest
    container_name: pdns-recursor
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    environment:
      - PDNS_recurson=yes
      - PDNS_allow_from=0.0.0.0/0
      - PDNS_webserver=yes
      - PDNS_webserver_address=0.0.0.0
      - PDNS_webserver_password=changeme
      - PDNS_query_logging=yes
      - PDNS_loglevel=9
    volumes:
      - pdns-recursor-data:/etc/powerdns

  powerdns-admin:
    image: psitrax/powerdns-admin:latest
    container_name: powerdns-admin
    restart: unless-stopped
    depends_on:
      - db
    ports:
      - "9191:80"
    environment:
      - SQLALCHEMY_DATABASE_URI=mysql://pdns:pdns@db/pdns
      - GUNICORN_TIMEOUT=60
      - GUNICORN_WORKERS=4
    volumes:
      - pdns-admin-data:/data

  db:
    image: mariadb:10.11
    container_name: pdns-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=pdns
      - MYSQL_USER=pdns
      - MYSQL_PASSWORD=pdns
    volumes:
      - pdns-db-data:/var/lib/mysql

volumes:
  pdns-recursor-data:
  pdns-admin-data:
  pdns-db-data:
```

### PowerDNS Recursor Query Logging Configuration

PowerDNS Recursor has built-in query logging that can be enabled with minimal configuration:

```lua
-- recursor.lua for advanced query logging
function preresolve(dq)
    -- Log every query to a file
    pdnslog("query: " .. dq.qname:toString() .. " type: " .. tostring(dq.qtype), pdns.loglevels.Info)
    return false
end

-- Enable query logging in pdns-recursor.conf
-- query-logging=yes
-- loglevel=9
```

### PowerDNS-Admin Web Interface

PowerDNS-Admin provides a comprehensive web dashboard for:

- Viewing and managing DNS zones and records
- Query logging with search and filtering
- Per-domain analytics and query statistics
- User management with role-based access control
- API integration for automation

## Knot Resolver Query Logging

[Knot Resolver](https://knot-resolver.readthedocs.io/) is a modern, high-performance DNS resolver from the CZ.NIC project. It includes built-in query logging capabilities through its Lua module system.

### Docker Compose for Knot Resolver with Logging

```yaml
version: "3.8"

services:
  knot-resolver:
    image: cznic/knot-resolver:latest
    container_name: knot-resolver
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8053:8053/tcp"
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf:ro
      - knot-log-data:/var/log/knot-resolver

volumes:
  knot-log-data:
```

### Knot Resolver Query Log Configuration

```lua
-- kresd.conf
-- Enable query logging
modules = {
    'policy',
    'hints',
    'view',
}

-- Log queries to file
log_query = function (state, req)
    local qname = pkt2str.name(req:question())
    local qtype = pkt2str.type(req:question())
    local client = net.ip(state:peer())
    local timestamp = os.date('%Y-%m-%d %H:%M:%S')
    
    log(string.format('[%s] %s %s %s', timestamp, client, qtype, qname))
    return state
end

policy.add(policy.all(policy.TURN))
```

## DNS Analysis Tools and Dashboards

Once you have DNS logs flowing, you'll want to analyze them. Here are several approaches:

### GoAccess for DNS Log Visualization

GoAccess can parse DNS query logs and generate real-time dashboards:

```bash
# Install goaccess
sudo apt install goaccess

# Parse DNS query logs
goaccess /var/log/dns-queries.log --log-format='%^ %h %t %^ %^ %s %^ %^' --date-format='%Y-%m-%d' --time-format='%H:%M:%S' -o /var/www/dns-dashboard.html
```

### ELK Stack for DNS Log Aggregation

For enterprise-scale DNS log analysis, the ELK stack (Elasticsearch, Logstash, Kibana) is the gold standard:

```yaml
# ELK Stack Docker Compose
version: "3.8"
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
    ports:
      - "5044:5044"
      - "5140:5140/udp"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### Loki + Grafana for Lightweight DNS Monitoring

For a lighter-weight alternative to ELK:

```yaml
version: "3.8"
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log/dns:/var/log/dns:ro
      - ./promtail-config.yaml:/etc/promtail/config.yaml:ro

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  loki-data:
  grafana-data:
```

## Self-Hosted DNS Privacy Considerations

When logging DNS queries, you are collecting sensitive data about user activity on your network. Consider these privacy implications:

- **Data retention policies** — define how long query logs are kept and automate deletion
- **Anonymization** — strip or hash client IP addresses to protect user privacy
- **Access controls** — restrict who can view DNS logs (especially in multi-tenant environments)
- **Encryption at rest** — encrypt log files to prevent unauthorized access
- **Compliance** — ensure logging practices meet regulatory requirements for your jurisdiction

For more on protecting DNS privacy at the protocol level, see our [complete DNS privacy guide](../self-hosted-dns-privacy-doh-dot-dnscrypt-guide/) covering DoH, DoT, and DNSCrypt implementations.

## FAQ

### What is dnstap and why is it better than text-based DNS logging?

dnstap is a structured, binary logging format for DNS servers that uses Protocol Buffers. Unlike text-based logs, dnstap captures complete query/response pairs with full metadata (query type, response code, round-trip time, EDNS options) in a compact format. This makes it ideal for high-throughput environments where text logs would be too large or slow to parse.

### Can I use dnstap with Pi-hole or AdGuard Home?

Pi-hole uses dnsmasq which does not natively support dnstap. AdGuard Home has its own query log format. However, you can run Unbound as a recursive resolver behind Pi-hole/AdGuard Home and enable dnstap on Unbound to capture the full resolution chain. See our [DNS filtering comparison](../self-hosted-dns-filtering-content-blocking-pihole-adguard-technitium-guide-2026/) for more on combining filtering with logging.

### How much disk space does DNS logging consume?

For a typical home network (50-100 devices), DNS logging generates approximately 100-500 MB per day in dnstap format (compressed). Text-based logs can be 2-5x larger. With compression (gzip/zstd) and log rotation, a week of logs typically fits in 1-3 GB. Enterprise environments with thousands of devices should plan for 10-50 GB per week.

### How do I detect DNS tunneling from query logs?

DNS tunneling manifests as: unusually long subdomain names (60+ characters), high query frequency to a single domain, TXT or NULL record queries, and base64-encoded data in domain labels. You can detect this by analyzing query entropy and length distributions using tools like `dnstap -r` with custom filters, or by importing logs into Elasticsearch/Kibana for real-time anomaly detection dashboards.

### Is PowerDNS-Admin suitable for small/home networks?

PowerDNS-Admin is designed for managing authoritative DNS zones at scale. While it can be used on small networks, it's overkill if you only need query logging. For home networks, Unbound with dnstap + go-dnstap is simpler and more lightweight. PowerDNS-Admin shines when you need zone management, per-user access control, and API integration alongside logging. For a broader look at DNS resolver options, see our [DNS resolver comparison](../self-hosted-dns-resolvers-unbound-dnsmasq-bind-coredns-guide-2026/).

### Can I forward DNS logs to a SIEM or security platform?

Yes. dnstap data can be forwarded to Security Information and Event Management (SIEM) platforms using collectors like Logstash, Fluent Bit, or Vector. Most SIEMs (Elastic Security, Splunk, Wazuh) have DNS parsing pipelines. You can also use the dnstap-to-Syslog bridge to forward logs to any syslog-compatible platform.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Logging and Analysis: dnstap, PowerDNS-Admin, and go-dnstap Comparison Guide",
  "description": "Compare self-hosted DNS logging solutions: dnstap-based collectors, PowerDNS-Admin, and Knot Resolver query logging. Includes Docker Compose configs, analysis tools, and privacy considerations.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
