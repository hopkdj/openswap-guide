---
title: "Self-Hosted DNS Cache Monitoring: Unbound vs PowerDNS Recursor vs BIND9 Stats Guide 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "dns", "monitoring", "prometheus"]
draft: false
description: "Compare built-in statistics, monitoring integrations, and Prometheus exporters for Unbound, PowerDNS Recursor, and BIND9 DNS cache resolvers."
---

If you run a self-hosted DNS resolver, knowing what's happening inside your cache is just as important as keeping it secure. Cache hit rates, query type distributions, upstream response times — these metrics tell you whether your DNS infrastructure is healthy, efficient, or about to fail.

This guide compares the **statistics and monitoring capabilities** of three widely-used self-hosted DNS resolvers: **Unbound**, **PowerDNS Recursor**, and **BIND 9**. We'll cover built-in stats, Prometheus exporters, and Grafana dashboard setups so you can build a complete observability stack for your DNS infrastructure.

For related reading, see our [authoritative DNS server comparison](../powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) and [complete DNS resolver setup guide](../self-hosted-dns-resolvers-unbound-dnsmasq-bind-coredns-guide/).

## Why Monitor Your DNS Cache?

A DNS resolver that isn't monitored is a resolver that's failing silently. Without statistics, you won't know:

- **Cache efficiency** — Are queries being served from cache or forwarded upstream? A low cache hit ratio means wasted bandwidth and slower responses.
- **Query distribution** — Which record types (A, AAAA, MX, TXT) dominate your traffic? This helps size your resolver and plan capacity.
- **Upstream health** — Are your upstream DNS servers responding quickly, or are some timing out and causing latency spikes?
- **Abuse detection** — Sudden spikes in NXDOMAIN responses can indicate misconfigured clients or reconnaissance activity.
- **Resource utilization** — Memory usage, thread load, and file descriptor counts help you plan scaling before outages occur.

Each of the three resolvers we compare has a different philosophy for exposing statistics. Understanding these differences helps you choose the right resolver for your monitoring stack.

## Quick Comparison Table

| Feature | Unbound | PowerDNS Recursor | BIND 9 |
|---------|---------|-------------------|--------|
| Stats Interface | `unbound-control stats` | `rec_control get-all` | `rndc stats` + statistics channel |
| Prometheus Exporter | `unbound_exporter` (Kumina) | Community exporters available | `bind_exporter` (DigitalOcean) |
| Stats Format | Key-value pairs | JSON, CSV | XML, JSON |
| Real-Time Metrics | Yes (control interface) | Yes (API + control) | Yes (statistics channel) |
| Per-Client Stats | Yes | Yes | Yes |
| Cache Size Metrics | Yes | Yes | Yes |
| Query Type Breakdown | Yes | Yes | Yes |
| Upstream Latency | Yes | Yes | Partial |
| Docker Image | `docker.io/unbound` | `docker.io/powerdns/pdns-recursor` | `docker.io/internetsystemsconsortium/bind9` |
| GitHub Stars | 4,475 | 4,352 (PowerDNS org) | 736 (mirror) |

## Unbound: Detailed Statistics via Control Interface

Unbound provides rich statistics through its `unbound-control` command-line tool. The stats are exposed as key-value pairs covering cache behavior, query processing, and memory usage.

### Enabling the Control Interface

Unbound's statistics require the remote-control interface to be enabled in your configuration:

```yaml
server:
  # Enable the control interface
  control-enable: yes
  control-interface: 127.0.0.1
  control-port: 8953

  # Collect extended statistics
  extended-statistics: yes
  statistics-cumulative: no
  statistics-interval: 0
```

### Reading Statistics

Once configured, you can query stats at any time:

```bash
# Full statistics dump
unbound-control stats

# Reset stats after reading
unbound-control stats_noreset

# Specific metric
unbound-control stats | grep cache
```

Key metrics include `total.num.cachehits`, `total.num.cachemiss`, `mem.cache.rrset`, and `time.now.elapsed`. The cache hit ratio can be calculated from these values.

### Docker Deployment with Monitoring

```yaml
services:
  unbound:
    image: docker.io/unbound:latest
    container_name: unbound
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8953:8953/tcp"
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf:ro
      - ./root.key:/opt/unbound/etc/unbound/root.key:ro
    cap_add:
      - NET_BIND_SERVICE
    networks:
      - dns-monitoring

  unbound-exporter:
    image: docker.io/kumina/unbound-exporter:latest
    container_name: unbound-exporter
    restart: unless-stopped
    ports:
      - "9167:9167/tcp"
    command:
      - "--unbound.host=unbound:8953"
      - "--unbound.key-file=/etc/unbound/unbound_control.key"
      - "--unbound.cert-file=/etc/unbound/unbound_control.pem"
    volumes:
      - ./unbound-keys:/etc/unbound:ro
    depends_on:
      - unbound
    networks:
      - dns-monitoring

networks:
  dns-monitoring:
    driver: bridge
```

The Kumina Unbound exporter scrapes metrics from the control interface and exposes them on port 9167 in Prometheus format. Key exported metrics include `unbound_cache_hits_total`, `unbound_cache_misses_total`, `unbound_queries_total`, and `unbound_memory_cache_bytes`.

## PowerDNS Recursor: JSON-RPC API for Statistics

PowerDNS Recursor takes a different approach — it exposes statistics through a JSON-RPC API that can be queried programmatically or consumed by monitoring tools.

### Enabling the API

Add these settings to your `recursor.conf`:

```ini
# Enable the web server and API
webserver=yes
webserver-address=127.0.0.1
webserver-port=8082
webserver-password=your-secure-password
api-key=your-api-key

# Enable detailed statistics
statistics-interval=1
```

### Reading Statistics via API

```bash
# Get all statistics as JSON
curl -s -H "X-API-Key: your-api-key" \
  http://127.0.0.1:8082/api/v1/servers/localhost/statistics

# Filter for specific metrics
curl -s -H "X-API-Key: your-api-key" \
  http://127.0.0.1:8082/api/v1/servers/localhost/statistics \
  | jq '.[] | select(.name | test("cache"))'

# Using rec_control CLI
rec_control get-all
```

The API returns a JSON array with entries for `cache-hits`, `cache-misses`, `queries`, `noerror-answers`, `nxdomain-answers`, and many more. The `rec_control` CLI provides a human-readable alternative.

### Docker Deployment with Monitoring

```yaml
services:
  pdns-recursor:
    image: docker.io/powerdns/pdns-recursor-49:latest
    container_name: pdns-recursor
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8082:8082/tcp"
    environment:
      - PDNS_webserver=yes
      - PDNS_webserver-address=0.0.0.0
      - PDNS_webserver-port=8082
      - PDNS_webserver-password=monitoring-password
      - PDNS_api=yes
      - PDNS_api-key=monitoring-api-key
    networks:
      - dns-monitoring

  pdns-recursor-exporter:
    image: docker.io/galexrt/pdns_recursor_exporter:latest
    container_name: pdns-recursor-exporter
    restart: unless-stopped
    ports:
      - "9199:9199/tcp"
    environment:
      - PDNS_URL=http://pdns-recursor:8082
      - PDNS_API_KEY=monitoring-api-key
    depends_on:
      - pdns-recursor
    networks:
      - dns-monitoring

networks:
  dns-monitoring:
    driver: bridge
```

The PowerDNS Recursor exporter converts API metrics into Prometheus format. Key metrics include `pdns_recursor_cache_hits_total`, `pdns_recursor_queries_total`, and `pdns_recursor_latency_seconds`.

## BIND 9: Statistics Channel and XML Output

BIND 9 provides statistics through two mechanisms: the `rndc stats` command (which writes XML to a file) and a built-in statistics channel (HTTP endpoint).

### Enabling the Statistics Channel

Add this to your `named.conf`:

```
options {
    // Enable the statistics channel
    statistics-channel {
        inet 127.0.0.1 port 8053 allow { 127.0.0.1; };
    };

    // Enable detailed query statistics
    querylog yes;
};
```

### Reading Statistics

```bash
# Dump stats to file (XML format)
rndc stats
cat /var/cache/bind/named_stats.txt

# Query the statistics channel (XML)
curl -s http://127.0.0.1:8053/

# Query specific statistics (JSON, BIND 9.16+)
curl -s http://127.0.0.1:8053/json/v1/server
```

The XML output includes `<counters>` elements for `Queryv4`, `Queryv6`, `RespNX`, `CacheDBHit`, and dozens of other metrics. The JSON endpoint (available in BIND 9.16+) provides a cleaner format for programmatic access.

### Docker Deployment with Monitoring

```yaml
services:
  bind9:
    image: docker.io/internetsystemsconsortium/bind9:9.18
    container_name: bind9
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8053:8053/tcp"
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./zones:/etc/bind/zones:ro
      - bind-cache:/var/cache/bind
    networks:
      - dns-monitoring

  bind-exporter:
    image: docker.io/prometheuscommunity/bind-exporter:latest
    container_name: bind-exporter
    restart: unless-stopped
    ports:
      - "9119:9119/tcp"
    command:
      - "--bind.stats-url=http://bind9:8053/json/v1/server"
      - "--bind.stats-version=2"
    depends_on:
      - bind9
    networks:
      - dns-monitoring

volumes:
  bind-cache:

networks:
  dns-monitoring:
    driver: bridge
```

The BIND exporter scrapes the statistics channel and exposes metrics on port 9119. Key metrics include `bind_resolver_cache_rrsets`, `bind_resolver_queries_total`, and `bind_resolver_response_errors_total`.

## Building a Unified Monitoring Dashboard

Once you have Prometheus exporters running for your DNS resolver, you can build a Grafana dashboard to visualize the data. Here's a recommended dashboard layout:

### Row 1: Cache Performance
- **Cache Hit Ratio** — `rate(cache_hits[5m]) / (rate(cache_hits[5m]) + rate(cache_misses[5m]))`
- **Cache Size** — `mem_cache_bytes` or equivalent
- **Cache Evictions** — Rate of cache entries being removed

### Row 2: Query Analysis
- **Queries per Second** — `rate(queries_total[5m])`
- **Query Type Distribution** — Breakdown by A, AAAA, MX, TXT, etc.
- **Response Code Distribution** — NOERROR, NXDOMAIN, SERVFAIL rates

### Row 3: Performance
- **Upstream Response Latency** — P50, P95, P99 percentiles
- **Thread Utilization** — Active threads vs total threads
- **Memory Usage** — Resident set size and cache memory

### Row 4: Health
- **Uptime** — Resolver uptime metric
- **File Descriptors** — Open FDs vs limit
- **Error Rate** — Rate of SERVFAIL and timeout responses

For alerting rules, consider these Prometheus alert definitions:

```yaml
groups:
  - name: dns-resolver-alerts
    rules:
      - alert: DNSCacheHitRatioLow
        expr: rate(dns_cache_hits_total[5m]) / (rate(dns_cache_hits_total[5m]) + rate(dns_cache_misses_total[5m])) < 0.3
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "DNS cache hit ratio below 30%"

      - alert: DNSHighErrorRate
        expr: rate(dns_servfail_total[5m]) / rate(dns_queries_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "DNS SERVFAIL rate above 5%"

      - alert: DNSHighLatency
        expr: histogram_quantile(0.95, rate(dns_upstream_latency_seconds_bucket[5m])) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "DNS upstream P95 latency above 500ms"
```

## Choosing the Right Resolver for Monitoring

Your choice depends on your existing infrastructure:

- **Unbound** — Best if you want simplicity. The `unbound-control` interface is straightforward, the Kumina exporter is well-maintained, and the metrics are comprehensive. Ideal for small to medium deployments.

- **PowerDNS Recursor** — Best if you need programmatic access. The JSON-RPC API is powerful and supports real-time statistics, per-client tracking, and dynamic configuration changes. The ecosystem of community exporters gives you flexibility.

- **BIND 9** — Best if you're already running BIND for authoritative DNS. The statistics channel provides XML and JSON output, and the DigitalOcean/Prometheus Community exporter integrates seamlessly with existing BIND monitoring setups.

All three resolvers integrate cleanly with Prometheus and Grafana, so your choice should be driven by your existing DNS infrastructure rather than monitoring capabilities alone.

## FAQ

### What is the best way to monitor DNS cache hit rates?

The most reliable approach is to use a Prometheus exporter specific to your DNS resolver (unbound_exporter, pdns_recursor_exporter, or bind_exporter) combined with a Grafana dashboard. Calculate the cache hit ratio as `cache_hits / (cache_hits + cache_misses)` over a 5-minute rate window. A healthy resolver should maintain a hit ratio above 60-70%.

### Can I monitor multiple DNS resolvers from a single Grafana dashboard?

Yes. Each Prometheus exporter exposes metrics on its own port. Configure your `prometheus.yml` to scrape all exporters, then use Grafana's datasource templating or panel variables to switch between resolvers in a single dashboard. Add a `resolver` label to each scrape job for easy filtering.

### How often should I poll DNS statistics?

For Prometheus scraping, a 15-second interval is recommended for real-time monitoring. For `unbound-control stats` or `rec_control get-all` manual checks, polling every 1-5 minutes is sufficient for trend analysis. Avoid polling faster than 5 seconds — the stats interfaces are not designed for high-frequency access.

### Does enabling statistics impact DNS resolver performance?

The performance overhead is negligible. Unbound's extended statistics add less than 1% CPU overhead. PowerDNS Recursor's API has minimal impact when queried at monitoring intervals (15-30 seconds). BIND 9's statistics channel runs in a separate thread. The main concern is disk I/O if you're writing stats to files (like BIND's `rndc stats` output) — use in-memory interfaces or exporters instead.

### How do I set up alerts for DNS resolver failures?

Use Prometheus alerting rules to monitor: (1) cache hit ratio dropping below 30%, (2) SERVFAIL rate exceeding 5%, (3) upstream latency P95 above 500ms, and (4) resolver process uptime resetting. Route alerts through Alertmanager to PagerDuty, Slack, or email. For self-hosted alerting, see our [Prometheus alerting comparison](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-self-hosted-alerting/).

### Can I use these exporters with VictoriaMetrics instead of Prometheus?

Yes. All three exporters expose metrics in the standard Prometheus text format, which VictoriaMetrics accepts natively. Point your VictoriaMetrics `scrape_configs` to the exporter endpoints (ports 9167, 9199, or 9119) and you'll get the same metrics without running a Prometheus server.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Cache Monitoring: Unbound vs PowerDNS Recursor vs BIND9 Stats Guide 2026",
  "description": "Compare built-in statistics, monitoring integrations, and Prometheus exporters for Unbound, PowerDNS Recursor, and BIND9 DNS cache resolvers.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
