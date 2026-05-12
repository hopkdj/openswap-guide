---
title: "Self-Hosted DNS Rate Limiting: dnsdist vs BIND RRL vs Unbound Rate-Limit"
date: "2026-05-12"
tags: ["dns", "rate-limiting", "ddos-protection", "security", "networking"]
draft: false
---

DNS rate limiting is a critical defense layer for any self-hosted DNS infrastructure. Without it, your recursive or authoritative servers become amplification targets in distributed denial-of-service (DDoS) attacks. This guide compares three leading approaches to DNS rate limiting: **dnsdist** from PowerDNS, **BIND Response Rate Limiting (RRL)**, and **Unbound's built-in rate-limit** feature.

## Why DNS Rate Limiting Matters

DNS is inherently stateless — a small query can trigger a large response, making it one of the most effective amplification vectors for DDoS attacks. In 2023 and 2024, DNS amplification attacks consistently ranked among the top five attack vectors, with peak traffic exceeding 3 Tbps. A self-hosted DNS server without rate limiting is both a victim and an unwitting accomplice in these attacks.

Rate limiting works by tracking query patterns per source IP and dropping or truncating responses that exceed configured thresholds. This protects your server's resources and prevents it from being used as an amplification reflector. For organizations running their own authoritative or recursive DNS, implementing rate limiting is not optional — it's a fundamental security requirement.

For broader DNS infrastructure planning, see our [comprehensive DNS server comparison](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) and [DNS firewall with RPZ guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/).

## Comparison Overview

| Feature | dnsdist | BIND RRL | Unbound rate-limit |
|---------|---------|----------|---------------------|
| **Developer** | PowerDNS | ISC | NLnet Labs |
| **License** | GPL-2.0 | MPL-2.0 | BSD-3-Clause |
| **GitHub Stars** | Part of PowerDNS (4,361+) | Part of BIND (ISC) | Part of Unbound (NLnetLabs) |
| **Rate Limit Type** | Global + per-client rules | Per-zone, per-source IP | Per-source IP |
| **QPS Threshold** | Configurable per rule | qps-limit, slip | default 50 qps |
| **Slip Response** | Yes (TC=1) | Yes (slip parameter) | Yes (TC=1) |
| **IPv6 Support** | Yes | Yes | Yes |
| **Dynamic Rules** | Yes (Lua, API) | No (static config) | No (static config) |
| **Logging** | Extensible (Lua, stats) | Query log | Verbosity levels |
| **Docker Image** | Official (powerdns/dnsdist) | Official (isc/bind) | Official (nlnetlabs/unbound) |
| **Best For** | Advanced traffic shaping | BIND deployments | Recursive resolver protection |

## dnsdist (PowerDNS)

dnsdist is a highly configurable DNS load balancer and rate limiter. Unlike the other two options, it operates as a front-end proxy, sitting in front of your backend DNS servers and applying rate limiting rules before queries reach them.

### Key Features

- **Rule-based rate limiting**: Define granular rules based on source IP, query type, domain name, or any combination
- **Lua scripting**: Dynamic rule creation and real-time adjustments via embedded Lua
- **Multiple backends**: Distribute traffic across multiple DNS servers with health checking
- **DoH/DoT termination**: Handle encrypted DNS traffic and apply rate limits per-client
- **Real-time statistics**: Web-based dashboard and console for monitoring

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  dnsdist:
    image: powerdns/dnsdist:latest
    container_name: dnsdist
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8081:8081/tcp"  # Web dashboard
      - "5199:5199/tcp"  # Console
    volumes:
      - ./dnsdist.conf:/etc/dnsdist/dnsdist.conf:ro
    restart: unless-stopped
    networks:
      dns-net:
        ipv4_address: 172.20.0.10

networks:
  dns-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

### Rate Limiting Configuration

```lua
-- dnsdist.conf

-- Basic rate limiting: 100 queries/second per source IP
-- "Slip" mode sends TC=1 (truncated) instead of dropping
addAction(AllRule(),
  QPSAction(100, {pool="default"}, {slip=100})
)

-- Stricter limit for ANY queries (common amplification vector)
addAction(
  QTypeRule(DNSQType.ANY),
  QPSAction(10, {pool="default"}, {slip=10})
)

-- Whitelist trusted resolvers (no rate limit)
addAction(
  NetGroup("/etc/dnsdist/whitelist.txt"),
  AllowAction()
)

-- Log dropped queries
setQPSLogRate(10)

-- Web dashboard
webserver("0.0.0.0:8081", "your-dashboard-password")
controlSocket("127.0.0.1:5199")
setKey("your-console-key")
```

### Advanced: Per-Domain Rate Limiting

```lua
-- Rate limit specific domains more aggressively
addAction(
  AndRule({
    QTypeRule(DNSQType.ANY),
    orRule({
      QNameRule("example.com"),
      QNameRule("example.org")
    })
  }),
  QPSAction(5)
)
```

## BIND Response Rate Limiting (RRL)

BIND's Response Rate Limiting is a built-in feature that limits the rate at which the server sends responses to the same client for the same type of question. It has been part of BIND since version 9.9 and is considered the gold standard for authoritative server protection.

### Key Features

- **Slip mechanism**: Sends truncated responses (TC=1) at a configurable rate, allowing legitimate clients to retry over TCP
- **Per-source, per-zone tracking**: Tracks query rates independently for each source IP and zone combination
- **IPv6 prefix aggregation**: Uses /56 prefixes for IPv6 to prevent per-address evasion
- **Exempt lists**: Whitelist trusted resolvers that should not be rate-limited
- **Automatic tuning**: Adjusts behavior based on server load

### BIND Configuration

```bind
// named.conf

options {
    // Enable Response Rate Limiting
    rate-limit {
        // Maximum responses per second per source IP
        responses-per-second 50;

        // Send 1 in N responses as TC=1 (truncated)
        // instead of REFUSED. 2 means send 1 out of 2.
        slip 2;

        // Window size for tracking (seconds)
        window 15;

        // Minimum number of responses before limiting kicks in
        min-table-size 10;

        // Maximum entries in the rate-limit table
        max-table-size 100000;

        // Limit for wildcard responses
        responses-per-second 20;

        // Limit for NXDOMAIN responses
        nxdomains-per-second 10;
    };

    // Trusted resolvers exempt from rate limiting
    rate-limit {
        responses-per-second 0;
    };
    allow-recursion { trusted-resolvers; };
};

// Define trusted resolvers
acl trusted-resolvers {
    10.0.0.0/8;
    172.16.0.0/12;
    192.168.0.0/16;
    // Add your upstream resolver IPs
};
```

### Docker Compose for BIND with RRL

```yaml
version: "3.8"

services:
  bind9:
    image: isc/bind:9.18
    container_name: bind9-rrl
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./zones/:/etc/bind/zones/:ro
      - bind-data:/var/cache/bind
    restart: unless-stopped

volumes:
  bind-data:
```

## Unbound Rate Limiting

Unbound is a recursive DNS resolver with a built-in rate-limit feature designed to protect against cache poisoning and query floods. It operates at the recursive resolver level, limiting how many queries a single source can make.

### Key Features

- **Recursive-specific protection**: Designed for resolver protection, not authoritative
- **Simple configuration**: Single parameter controls the rate limit
- **IPv6 support**: Full IPv6 rate limiting with prefix aggregation
- **Low memory overhead**: Efficient tracking with minimal resource impact
- **TC=1 slip**: Sends truncated responses for legitimate clients to retry over TCP

### Unbound Configuration

```yaml
# unbound.conf

server:
  # Rate limit: maximum queries per second per source IP
  # Default is 50. Set to 0 to disable.
  ratelimit: 50

  # Rate limit below domain (per-domain tracking)
  # Limits responses for a specific domain name
  ratelimit-below-domain: 20

  # Number of milliseconds to keep rate limit entries
  ratelimit-factor: 10

  # Whitelist for trusted networks (no rate limiting)
  access-control: 10.0.0.0/8 allow
  access-control: 172.16.0.0/12 allow
  access-control: 192.168.0.0/16 allow
  access-control: 0.0.0.0/0 allow

  # Harden against various attacks
  harden-glue: yes
  harden-dnssec-stripped: yes
  harden-referral-path: yes
```

### Docker Compose for Unbound

```yaml
version: "3.8"

services:
  unbound:
    image: nlnetlabs/unbound:latest
    container_name: unbound-ratelimit
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf:ro
      - unbound-data:/opt/unbound/etc/unbound
    restart: unless-stopped

volumes:
  unbound-data:
```

## Choosing the Right DNS Rate Limiting Solution

The choice depends on your architecture:

- **Use dnsdist** when you need advanced traffic shaping, DoH/DoT termination, or want to rate-limit across multiple backend servers. Its Lua-based rules and API make it the most flexible option.
- **Use BIND RRL** when running BIND as an authoritative server. It's the most battle-tested rate limiting for authoritative DNS, with decades of production use.
- **Use Unbound rate-limit** when protecting a recursive resolver. It's simple, effective, and requires minimal configuration.

For comprehensive DNS management, check our [DNS management web UI guide](../2026-05-04-self-hosted-dns-management-web-ui-powerdns-admin-dnscontrol-technitium-guide/) and [DNS-over-QUIC setup guide](../2026-05-02-knot-dns-vs-dnsdist-vs-unbound-self-hosted-dns-over-quic-guide/).

## FAQ

### What is DNS rate limiting and why is it necessary?

DNS rate limiting controls how many queries a DNS server will respond to from a single source IP within a time window. It prevents DNS amplification attacks, where attackers send small spoofed queries that generate large responses directed at a victim. Without rate limiting, any open DNS resolver can be weaponized as a DDoS amplifier.

### What is the "slip" mechanism in DNS rate limiting?

The slip mechanism sends truncated responses (TC=1 flag) to rate-limited clients instead of dropping queries entirely. This tells legitimate clients to retry their query over TCP, which is harder to spoof. The slip ratio controls how often TC=1 responses are sent — a slip of 2 means every second limited query gets a truncated response instead of a refusal.

### Should I use rate limiting on both authoritative and recursive DNS servers?

Yes, but with different configurations. Authoritative servers should use response rate limiting (like BIND RRL) to prevent amplification. Recursive resolvers should use query rate limiting (like Unbound's ratelimit) to prevent cache flooding and query storms. dnsdist can protect both by sitting in front as a proxy.

### How do I whitelist trusted resolvers from rate limiting?

All three solutions support whitelisting. In dnsdist, use `NetGroup()` with an allowlist file. In BIND, define an ACL and set `responses-per-second 0` for that ACL. In Unbound, use `access-control` entries with `allow_snoop` or exempt specific subnets. Always whitelist your internal resolvers, monitoring systems, and any legitimate high-volume clients.

### What rate limit values should I start with?

For authoritative servers (BIND RRL): start with `responses-per-second 50` and `slip 2`. For recursive resolvers (Unbound): start with `ratelimit: 50`. For dnsdist: start with `QPSAction(100)` per source IP and adjust based on your traffic patterns. Monitor your logs and adjust thresholds — legitimate recursive resolvers may send hundreds of queries per second.

### Can rate limiting cause false positives for legitimate users?

Yes, if configured too aggressively. Large organizations with NAT may have many users sharing a single public IP. The slip mechanism mitigates this by allowing TCP retries. For dnsdist, you can use Lua scripting to implement adaptive rate limiting based on historical patterns. Always monitor dropped queries and adjust thresholds accordingly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Rate Limiting: dnsdist vs BIND RRL vs Unbound Rate-Limit",
  "description": "Compare DNS rate limiting solutions for self-hosted infrastructure: dnsdist (PowerDNS), BIND Response Rate Limiting (RRL), and Unbound rate-limit feature.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
