---
title: "Self-Hosted DNS Cache Statistics & Performance Monitoring: Unbound vs PowerDNS Recursor vs BIND 9"
date: "2026-05-20"
description: "Monitor DNS cache hit rates, query latency, and resolver performance with Unbound, PowerDNS Recursor, and BIND 9. Includes Prometheus exporters and dashboard configurations."
tags: ["dns", "cache-monitoring", "dns-performance", "resolver-monitoring", "prometheus"]
draft: false
---

DNS resolver performance directly impacts every application and user on your network. Cache hit rates, query latency, and upstream resolution times are critical metrics that determine whether users experience instant page loads or frustrating delays. This guide covers how to monitor DNS cache statistics and resolver performance using three widely-deployed open-source DNS resolvers: **Unbound**, **PowerDNS Recursor**, and **BIND 9**.

## Why Monitor DNS Cache Performance?

DNS resolution is the first step in nearly every network request. A slow or misconfigured DNS resolver cascades delays across your entire infrastructure:

- **Cache hit rate below 80%** means your resolver is performing excessive upstream queries, increasing latency and upstream DNS server load
- **High query latency** (above 100ms for cached queries) indicates resource constraints, disk I/O bottlenecks, or recursive resolver issues
- **NXDomain spikes** can indicate misconfigured applications, DNS-based attacks, or reconnaissance activity
- **Cache poisoning attempts** manifest as anomalous query patterns that monitoring can detect early

## 1. Unbound Cache Statistics

[Unbound](https://github.com/NLnetLabs/unbound) is a validating, recursive, and caching DNS resolver developed by NLnet Labs. It provides detailed cache statistics through its `unbound-control` command and Prometheus exporter.

### Key Metrics Available

- **Cache hit ratio**: Percentage of queries served from cache vs. upstream resolution
- **Query types**: Distribution of A, AAAA, MX, TXT, and other query types
- **Response codes**: NOERROR, NXDOMAIN, SERVFAIL breakdown
- **Memory usage**: Cache size, RRset count, and memory allocation
- **Upstream query time**: Average latency for recursive resolution

### Docker Compose Setup

```yaml
version: "3.8"
services:
  unbound:
    image: mvance/unbound:latest
    container_name: unbound
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "8953:8953"       # unbound-control
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf:ro
    restart: unless-stopped
    networks:
      - dns-monitoring

  unbound-exporter:
    image: kumina/unbound_exporter:latest
    container_name: unbound-exporter
    ports:
      - "9167:9167"
    command: ["--unbound.host=unbound", "--unbound.port=8953"]
    depends_on:
      - unbound
    restart: unless-stopped
    networks:
      - dns-monitoring

networks:
  dns-monitoring:
    driver: bridge
```

### Unbound Configuration (unbound.conf)

```yaml
server:
  # Cache settings
  cache-min-ttl: 300
  cache-max-ttl: 86400
  msg-cache-size: 128m
  rrset-cache-size: 256m

  # Statistics
  statistics-interval: 0
  extended-statistics: yes
  statistics-cumulative: no

  # Remote control for unbound-control
  remote-control:
    control-enable: yes
    control-interface: 0.0.0.0
    control-port: 8953
    server-key-file: /opt/unbound/etc/unbound/unbound_server.key
    server-cert-file: /opt/unbound/etc/unbound/unbound_server.pem
    control-key-file: /opt/unbound/etc/unbound/unbound_control.key
    control-cert-file: /opt/unbound/etc/unbound/unbound_control.pem

  # Logging
  log-queries: no
  log-replies: no
  log-tag-queryreply: no
  log-local-actions: no
  verbosity: 1
```

### Collect Cache Stats

```bash
# View cache statistics
docker exec unbound unbound-control stats

# Key metrics output example:
# total.num.queries=45230
# total.num.cachehits=38456
# total.num.cachemiss=6774
# total.num.recursivereplies=6774
# avg.num.querytype.A=32100
# avg.num.querytype.AAAA=8900
# avg.num.querytype.MX=1200

# Calculate cache hit ratio
HITS=$(docker exec unbound unbound-control stats | grep cachehits | cut -d= -f2)
MISSES=$(docker exec unbound unbound-control stats | grep cachemiss | cut -d= -f2)
RATIO=$(echo "scale=2; $HITS * 100 / ($HITS + $MISSES)" | bc)
echo "Cache hit ratio: $RATIO%"
```

## 2. PowerDNS Recursor Statistics

[PowerDNS Recursor](https://github.com/PowerDNS/pdns) is a high-performance, security-focused recursive DNS resolver. It provides statistics via HTTP API, SNMP, and built-in Prometheus metrics.

### Key Metrics Available

- **Question rate**: Queries per second
- **Cache size**: Number of entries in the packet cache and negative cache
- **CPU usage**: User and system time breakdown
- **Query distribution**: Per-query-type and per-qclass statistics
- **Slow query tracking**: Queries exceeding configurable latency thresholds
- **Throttled queries**: Rate-limited and blocked queries

### Docker Compose Setup

```yaml
version: "3.8"
services:
  pdns-recursor:
    image: powerdns/pdns-recursor:4.9
    container_name: pdns-recursor
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "8082:8082"       # Web API
    volumes:
      - ./recursor.conf:/etc/pdns-recursor/recursor.conf:ro
    environment:
      - PDNS_recurring=yes
    restart: unless-stopped
    networks:
      - dns-monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: pdns-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
    networks:
      - dns-monitoring

networks:
  dns-monitoring:
    driver: bridge
```

### PowerDNS Recursor Configuration (recursor.conf)

```ini
# Listen on all interfaces
local-address=0.0.0.0
local-port=53

# Web API for statistics
webserver=yes
webserver-address=0.0.0.0
webserver-port=8082
webserver-password=monitoring_secret
webserver-allow-from=0.0.0.0/0, ::/0

# Prometheus metrics
webserver-loglevel=normal

# Cache tuning
max-cache-entries=1000000
max-negative-ttl=3600
max-cache-ttl=86400
max-tmp-cache-entries=100000

# Query logging (disable in production for performance)
quiet=yes
log-common-errors=yes

# Security
dnssec=validate
serve-rfc1918=no
```

### Fetch Statistics via API

```bash
# Get all statistics
curl -s -H "X-API-Key: monitoring_secret"   http://localhost:8082/api/v1/servers/localhost/statistics | python3 -m json.tool

# Key metrics from API response:
# "all-outqueries": total upstream queries
# "cache-hits": cache hit count
# "cache-misses": cache miss count
# "answers-slow": queries taking > 1 second
# "sys-msec": system CPU time
# "user-msec": user CPU time
```

## 3. BIND 9 Statistics Channel

[BIND 9](https://github.com/isc-projects/bind9) is the most widely deployed DNS server, serving as both authoritative and recursive resolver. Its statistics channel provides detailed XML/JSON metrics.

### Key Metrics Available

- **Resolver statistics**: Queries received, resolved, cached
- **Cache database size**: RRset and message cache sizes
- **Client query statistics**: Per-view, per-client statistics
- **Memory management**: Heap, mmap, and context memory usage
- **TSIG and DNSSEC validation**: Signature validation rates

### Docker Compose Setup

```yaml
version: "3.8"
services:
  bind9:
    image: ubuntu/bind9:latest
    container_name: bind9
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "8053:8053"       # Statistics channel
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./named.conf.options:/etc/bind/named.conf.options:ro
      - ./bind9-data:/var/cache/bind
    environment:
      - BIND9_USER=root
    restart: unless-stopped
    networks:
      - dns-monitoring

  bind9-exporter:
    image: ghcr.io/prometheus-community/bind_exporter:latest
    container_name: bind9-exporter
    ports:
      - "9119:9119"
    command: ["--bind.stats-groups", "server,view,tasks"]
    environment:
      - BIND9_URL=http://bind9:8053
    restart: unless-stopped
    networks:
      - dns-monitoring

networks:
  dns-monitoring:
    driver: bridge
```

### BIND 9 Statistics Configuration (named.conf.options)

```
options {
    directory "/var/cache/bind";

    // Enable statistics channel
    statistics-channels {
        inet * port 8053 allow { any; };
    };

    // Cache tuning
    max-cache-size 256m;
    max-ncache-ttl 3600;
    max-cache-ttl 86400;

    // DNSSEC validation
    dnssec-validation auto;

    // Query logging
    querylog no;
};

logging {
    channel query_log {
        file "/var/log/bind9/query.log" versions 3 size 50m;
        severity info;
        print-time yes;
    };
    category queries { query_log; };
};
```

### Collect Statistics via rndc

```bash
# Dump statistics to file
docker exec bind9 rndc stats

# View cache statistics
docker exec bind9 cat /var/cache/bind/named_stats.txt

# Key sections in the stats file:
# +++ Statistics Dump +++
# ++ Incoming Requests ++
# ++ Outgoing Queries ++
# ++ Name Server Statistics ++
# ++ Resolver Statistics ++
# ++ Cache DB RRsets ++
# ++ Socket I/O Statistics ++
```

## Comparison Table

| Feature | Unbound | PowerDNS Recursor | BIND 9 |
|---------|---------|-------------------|--------|
| **Cache hit metrics** | Via unbound-control | HTTP API + Prometheus | Statistics channel + rndc |
| **Prometheus exporter** | kumina/unbound_exporter | Built-in | prometheus-community/bind_exporter |
| **Per-query logging** | Optional (verbosity) | Lua scripting | Query logging category |
| **DNSSEC validation stats** | Yes | Yes | Yes |
| **Cache size tuning** | msg-cache-size, rrset-cache-size | max-cache-entries | max-cache-size |
| **Slow query tracking** | Via response time histogram | answers-slow metric | Via query logging |
| **Negative cache stats** | Yes (NXDOMAIN) | max-negative-ttl | Via cache DB RRsets |
| **Resource usage** | Low (~100MB RAM) | Low (~150MB RAM) | Medium (~300MB RAM) |
| **Best for** | Simple, secure caching | High-performance with rich API | Enterprise, multi-view setups |

## Prometheus Dashboard Setup

```yaml
# prometheus.yml — scrape all DNS resolvers
scrape_configs:
  - job_name: unbound
    static_configs:
      - targets: ["unbound-exporter:9167"]

  - job_name: pdns-recursor
    static_configs:
      - targets: ["pdns-recursor:8082"]

  - job_name: bind9
    static_configs:
      - targets: ["bind9-exporter:9119"]
```

### Key Grafana Panels

- **Cache Hit Rate**: `rate(unbound_response_cache_hits[5m]) / rate(unbound_response_total[5m]) * 100`
- **Queries per Second**: `rate(unbound_queries_total[1m])`
- **Upstream Query Latency**: `histogram_quantile(0.95, rate(unbound_response_time_seconds_bucket[5m]))`
- **Cache Memory Usage**: `unbound_memory_cache_bytes`

## Why Monitor DNS Cache Performance?

Proactive DNS cache monitoring prevents performance degradation before users notice it:

- **Capacity planning**: Track cache utilization trends to predict when you need to increase cache size or add resolver instances
- **Anomaly detection**: Sudden drops in cache hit rate often indicate upstream DNS issues, cache poisoning attempts, or application misconfigurations
- **Cost optimization**: Higher cache hit rates reduce upstream DNS queries, lowering bandwidth costs and improving response times for users
- **SLA compliance**: DNS resolution time is part of most application performance SLAs. Monitoring cache performance ensures you meet these commitments
- **Security insights**: NXDomain spikes can reveal malware C2 communication, DGA-based domain generation, or DNS tunneling attempts
- **Cache tuning validation**: When you adjust TTL values or cache sizes, monitoring confirms whether the changes improve hit rates or waste memory

For DNS traffic analysis, see our [DNS traffic collector comparison](../2026-04-26-pktvisor-vs-dns-collector-vs-dsc-self-hosted-dns-traff/).
If you need authoritative DNS management, check our [DNS authoritative server comparison](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/).
For DNS-over-TLS setup, our [DNS-over-TLS guide](../self-hosted-dns-over-tls-resolver-stubby-unbound-knot-2026/) covers encrypted resolution.

## FAQ

### What is a good DNS cache hit rate?
For a typical internal DNS resolver serving a stable set of domains, a cache hit rate of **80-95%** is expected. Enterprise environments with diverse client applications may see 60-80%. Below 50% suggests the cache is too small, TTLs are very short, or the resolver is serving too many unique domains.

### How do I monitor DNS cache performance without a dashboard?
All three resolvers provide command-line tools for quick checks: `unbound-control stats`, `rec_control get-all`, and `rndc stats`. For automated monitoring, each has a Prometheus exporter that feeds into time-series databases for alerting.

### Why is my DNS cache hit rate dropping suddenly?
Common causes include: (1) A new application or service making queries for unique domains, (2) DNS TTL changes upstream reducing cache lifetime, (3) Cache eviction due to memory pressure, (4) A cache flush command was accidentally executed, or (5) DNS-based attacks generating random queries for non-existent domains.

### How much memory should I allocate for DNS cache?
For Unbound, start with 128MB message cache and 256MB RRset cache for up to 1000 clients. Scale to 512MB/1GB for 10,000+ clients. PowerDNS Recursor uses `max-cache-entries` (default 1M entries ≈ 200MB). BIND 9's `max-cache-size` defaults to 90% of available RAM but should be capped at 512MB-1GB for dedicated resolvers.

### Can I monitor DNS cache performance across multiple resolvers?
Yes. Deploy a Prometheus instance that scrapes each resolver's exporter, then use Grafana to aggregate and compare metrics. This is especially useful for anycast deployments where you want to compare cache hit rates across geographically distributed resolvers.

### Does DNS cache monitoring help with security?
Absolutely. Monitoring cache statistics reveals security-relevant patterns: sudden spikes in NXDomain responses may indicate malware using domain generation algorithms (DGAs), unusual TXT query volumes could signal DNS tunneling, and abnormal query patterns from single sources may reveal compromised hosts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Cache Statistics & Performance Monitoring: Unbound vs PowerDNS Recursor vs BIND 9",
  "description": "Monitor DNS cache hit rates, query latency, and resolver performance with Unbound, PowerDNS Recursor, and BIND 9. Includes Prometheus exporters and dashboard configurations.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
