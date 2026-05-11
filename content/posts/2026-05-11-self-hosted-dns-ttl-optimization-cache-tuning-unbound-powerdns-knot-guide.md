---
title: "Self-Hosted DNS TTL Optimization and Cache Tuning: Unbound vs PowerDNS vs Knot Resolver (2026)"
date: "2026-05-11"
tags: ["dns", "performance", "caching", "unbound", "powerdns", "knot-resolver"]
draft: false
---

DNS Time-To-Live (TTL) values determine how long recursive resolvers cache query results. Getting TTL values right is one of the most impactful yet overlooked aspects of DNS infrastructure optimization. Too short, and you generate excessive upstream queries; too long, and clients receive stale data when records change.

This guide covers DNS TTL optimization strategies across three popular self-hosted recursive resolvers: **Unbound**, **PowerDNS Recursor**, and **Knot Resolver**.

## Understanding DNS TTL

When an authoritative nameserver returns a DNS response, it includes a TTL value (in seconds) specifying how long the record may be cached. Recursive resolvers honor this TTL by storing the response and serving cached copies until it expires.

### TTL Trade-Offs

| TTL Value | Cached Duration | Upstream Queries | Record Freshness |
|-----------|----------------|------------------|------------------|
| 30s | 30 seconds | Very high | Excellent |
| 300s (5 min) | 5 minutes | High | Good |
| 3600s (1 hr) | 1 hour | Moderate | Acceptable |
| 86400s (24 hr) | 1 day | Low | Poor for dynamic records |

### Common TTL Recommendations

- **A/AAAA records**: 300-3600 seconds (5 min to 1 hour)
- **MX records**: 3600-86400 seconds (1 to 24 hours)
- **NS records**: 86400 seconds (24 hours)
- **TXT/SPF records**: 3600 seconds (1 hour)
- **CNAME records**: Match the TTL of the target record
- **SRV records**: 300-3600 seconds

## Unbound — DNSSEC-Validating Recursive Resolver

Unbound is a validating, recursive, and caching DNS resolver developed by NLnet Labs. It is widely deployed as a recursive resolver and supports extensive TTL customization.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  unbound:
    image: mvance/unbound:latest
    container_name: unbound-resolver
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf
      - ./unbound-cache:/opt/unbound/etc/unbound/cache
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8953:8953"
    restart: unless-stopped
    cap_add:
      - NET_BIND_SERVICE
```

### TTL Optimization Configuration

```conf
server:
    # Override minimum TTL (in seconds)
    cache-min-ttl: 60
    
    # Override maximum TTL (in seconds)
    cache-max-ttl: 86400
    
    # Serve expired records while refreshing (stale-cache)
    serve-expired: yes
    serve-expired-ttl: 86400
    serve-expired-ttl-reset: yes
    serve-expired-reply-ttl: 30
    
    # Prefetch records before they expire
    prefetch: yes
    prefetch-key: yes
    
    # Cache size (4 MB minimum)
    msg-cache-size: 256m
    rrset-cache-size: 512m
    
    # Number of queries to prefetch
    num-threads: 4
    
    # Log cache statistics
    statistics-interval: 0
    statistics-cumulative: yes
    extended-statistics: yes
```

The `serve-expired` feature is particularly powerful: when a cached record's TTL expires and the upstream nameserver is unreachable, Unbound continues serving the stale record for up to `serve-expired-ttl` seconds while simultaneously attempting to refresh it.

## PowerDNS Recursor

PowerDNS Recursor is a high-performance recursive DNS resolver designed for ISPs and large-scale deployments. It features a Lua scripting engine for advanced query processing and TTL manipulation.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  pdns-recursor:
    image: powerdns/pdns-recursor-49
    container_name: pdns-recursor
    environment:
      PDNS_rememberServerSettings: "yes"
    volumes:
      - ./recursor.conf:/etc/powerdns/recursor.conf
      - ./pdns-lua:/etc/powerdns/lua
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    restart: unless-stopped
```

### TTL Optimization Configuration

```conf
# recursor.conf

# Cache TTL bounds
max-cache-ttl=86400
max-negative-ttl=3600
min-cache-ttl=60

# Packet cache (faster than full record cache)
max-packetcache-ttl=3600
packetcache-ttl=1800

# Serve stale records
serve-stale-extensions=1
max-cache-entries=1000000

# Prefetch popular records
max-refresh-per-second=5

# Lua scripting for custom TTL rules
lua-dns-script=/etc/powerdns/lua/ttl-rules.lua
```

Lua TTL override script (`ttl-rules.lua`):

```lua
function preresolve(dq)
    -- Force minimum TTL of 5 minutes for A records
    if dq.qtype == pdns.A then
        local min_ttl = 300
        for k, rec in pairs(dq.records) do
            if rec.ttl < min_ttl then
                rec.ttl = min_ttl
            end
        end
    end
    return false
end

function postresolve(dq)
    -- Cap maximum TTL at 24 hours
    local max_ttl = 86400
    for k, rec in pairs(dq.records) do
        if rec.ttl > max_ttl then
            rec.ttl = max_ttl
        end
    end
    return false
end
```

## Knot Resolver

Knot Resolver is a modern caching DNS resolver developed by CZ.NIC. It features a modular architecture with Lua scripting, DNS-over-TLS, and DNS-over-HTTPS support built in.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  knot-resolver:
    image: cznic/knot-resolver:latest
    container_name: knot-resolver
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf
      - ./knot-cache:/var/cache/knot-resolver
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "853:853/tcp"
    restart: unless-stopped
```

### TTL Optimization Configuration

```lua
-- kresd.conf

-- Cache configuration
cache.size = 500 * MB

-- TTL bounds
policy.add(policy.ttl(policy.LIMIT_TTL, 60, 86400))

-- Stale cache serving
policy.add(policy.serve_stale(86400))

-- Prefetch records that will expire soon
policy.add(policy.prefetch(true))

-- Cache metrics
metrics.enabled = true

-- DNS-over-TLS
tls.listen('0.0.0.0', 853, tls.creds('/etc/knot-resolver/tls/server.pem'))
```

## Comparison Table

| Feature | Unbound | PowerDNS Recursor | Knot Resolver |
|---------|---------|-------------------|---------------|
| **TTL min/max override** | Yes | Yes | Yes (via policy) |
| **Serve stale/expired** | Yes | Yes | Yes |
| **Prefetch** | Yes | Partial (via Lua) | Yes |
| **Lua scripting** | No | Yes | Yes |
| **Per-query TTL rules** | No | Yes (Lua) | Yes (policy) |
| **DNSSEC validation** | Yes | Yes | Yes |
| **DNS-over-TLS** | Yes | Yes (4.7+) | Yes |
| **DNS-over-HTTPS** | No (needs proxy) | No (needs proxy) | Yes |
| **Cache size config** | msg-cache, rrset-cache | max-cache-entries | cache.size |
| **Prometheus metrics** | Via exporter | Built-in | Built-in |
| **GitHub Stars** | 4,523 | N/A (powerdns.com) | 437 |
| **Best For** | DNSSEC-first deployments | Large-scale / ISP | Modern features + DoH |

## Advanced TTL Optimization Strategies

### Aggressive TTL Capping

When authoritative servers set extremely low TTLs (e.g., 1 second for CDN failover), your resolver generates thousands of upstream queries. Implementing a minimum TTL floor (60-300 seconds) dramatically reduces upstream load while maintaining acceptable freshness.

```conf
# Unbound
cache-min-ttl: 60

# PowerDNS Recursor
min-cache-ttl=60

# Knot Resolver
policy.add(policy.ttl(policy.LIMIT_TTL, 60, 86400))
```

### Selective TTL Override

Different record types have different freshness requirements. Use PowerDNS Lua or Knot Resolver policies to apply TTL rules selectively:

```lua
-- PowerDNS Lua: longer TTL for MX records, shorter for A records
function postresolve(dq)
    for k, rec in pairs(dq.records) do
        if rec.qtype == pdns.MX and rec.ttl < 3600 then
            rec.ttl = 3600
        elseif rec.qtype == pdns.A and rec.ttl < 300 then
            rec.ttl = 300
        end
    end
    return false
end
```

### Stale Cache Serving

All three resolvers support serving expired records when upstream servers are unreachable. This is critical for resilience during network partitions or authoritative server outages:

- **Unbound**: `serve-expired: yes` with configurable TTL reset
- **PowerDNS Recursor**: `serve-stale-extensions=1`
- **Knot Resolver**: `policy.add(policy.serve_stale(86400))`

For a comprehensive DNS security hardening guide that complements TTL tuning, see our [DNS cache hardening comparison](../2026-04-26-dns-cache-hardening-unbound-vs-bind9-vs-knot-resolver-self-hosted-security-guide/). Organizations managing DNS firewall policies can also benefit from our [DNS firewall and RPZ solutions guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/).

## Why Optimize DNS TTL Settings?

**Reduced upstream query load** — By enforcing reasonable minimum TTLs, you can reduce upstream DNS queries by 40-80%, especially for domains with very low TTL values. This lowers bandwidth costs and reduces dependency on upstream resolver availability.

**Improved response latency** — Cached responses return in microseconds, while uncached queries require network round trips to authoritative servers. Aggressive caching with prefetch ensures that popular records are always available locally.

**Resilience during outages** — Stale cache serving ensures that DNS resolution continues even when authoritative nameservers are unreachable. Users experience no interruption while the resolver works to refresh expired records in the background.

**Better control over failover behavior** — DNS-based failover mechanisms rely on low TTLs to redirect traffic quickly. By setting appropriate TTL bounds on your recursive resolver, you can balance between fast failover and reasonable caching performance.

**Cost optimization** — For organizations using paid DNS services, reducing upstream query volume directly reduces costs. Many DNS providers charge per query, making TTL optimization a direct cost-saving measure.

## FAQ

### What is the ideal DNS TTL value?

There is no universal ideal TTL. For static infrastructure (mail servers, nameservers), use 86400 seconds (24 hours). For dynamic infrastructure (web servers, load balancers), use 300-3600 seconds (5-60 minutes). The key is matching the TTL to your infrastructure's change frequency.

### What happens if I set cache-min-ttl higher than the authoritative TTL?

Your resolver will honor the higher minimum TTL, serving cached results even after the authoritative TTL has expired. This means clients may receive slightly stale data but benefit from faster responses and reduced upstream load. The trade-off is between freshness and performance.

### Does serving stale DNS records cause security issues?

Serving stale records is generally safe for most use cases. The records were previously validated (if DNSSEC is enabled) and were considered authoritative at the time of caching. However, for time-sensitive records like CAA or TLSA, consider using shorter stale TTLs or disabling stale serving for specific zones.

### How do I monitor DNS cache hit rates?

Unbound: Use `unbound-control stats` to view cache hit rates. PowerDNS Recursor: Query the built-in HTTP metrics endpoint or use `rec_control get-all`. Knot Resolver: Enable metrics and query the HTTP endpoint. Look for cache hit rates above 70% as a healthy baseline.

### Can I override TTL for specific domains only?

PowerDNS Recursor and Knot Resolver support domain-specific TTL overrides via Lua scripting and policy rules respectively. Unbound does not support per-domain TTL overrides natively — you would need to use local-zone configurations or deploy multiple Unbound instances with different settings.

### How does prefetching affect cache performance?

Prefetching proactively refreshes records before their TTL expires, ensuring that popular records are always fresh in the cache. This increases background query volume slightly (typically 5-10% more queries) but eliminates cache miss latency for frequently accessed records. Enable prefetching for resolvers serving many clients.

### Should I disable DNS caching entirely for development environments?

For development and testing, you may want shorter TTLs to see DNS changes immediately. Rather than disabling caching entirely, set `cache-min-ttl: 0` and `cache-max-ttl: 60` to ensure records expire quickly while still providing some caching benefit.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS TTL Optimization and Cache Tuning: Unbound vs PowerDNS vs Knot Resolver (2026)",
  "description": "Optimize DNS TTL and cache settings across Unbound, PowerDNS Recursor, and Knot Resolver. Docker deployment guides and performance tuning configuration.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
