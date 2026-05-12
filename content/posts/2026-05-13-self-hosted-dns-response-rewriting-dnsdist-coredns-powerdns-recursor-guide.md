---
title: "Self-Hosted DNS Response Rewriting: dnsdist vs CoreDNS vs PowerDNS Recursor"
date: "2026-05-13"
tags: ["dns", "networking", "security", "coredns", "powerdns"]
draft: false
---

DNS response rewriting is the practice of intercepting and modifying DNS query responses before they reach the client. This capability powers a wide range of self-hosted infrastructure use cases: blocking malicious domains, redirecting internal services, enforcing geo-based routing, implementing split-DNS policies, and testing production deployments with shadow traffic.

This guide compares three powerful open-source DNS engines — dnsdist, CoreDNS, and PowerDNS Recursor — for implementing self-hosted DNS response rewriting and query manipulation.

## What Is DNS Response Rewriting?

DNS response rewriting involves modifying DNS responses at the resolver level. When a client queries for a domain, the rewriter can:

- **Block** — Return NXDOMAIN or a sinkhole IP for blacklisted domains
- **Redirect** — Return a different IP address (e.g., internal service IPs)
- **Rewrite** — Change the response name, type, or TTL
- **Filter** — Strip or modify DNSSEC records, EDNS options
- **Log and Analyze** — Record query patterns for threat intelligence

Unlike simple hosts-file blocking, DNS rewriting operates at the protocol level, supporting wildcards, regular expressions, and conditional logic based on query source, time of day, or external data feeds.

## Comparison Table

| Feature | dnsdist | CoreDNS | PowerDNS Recursor |
|---------|---------|---------|-------------------|
| Primary Role | DNS load balancer | DNS server (plugin-based) | Recursive resolver |
| Language | C++ | Go | C++ |
| Configuration | Lua scripting | Corefile (declarative) | Lua + recursor.conf |
| Rewrite Rules | Lua + built-in actions | rewrite plugin | Lua scripting |
| Plugin Ecosystem | Moderate | Extensive (50+ plugins) | Moderate |
| DNSSEC | Full support | Full support | Full support |
| DoH/DoT | Native | Via plugins | Native |
| API | REST API | Prometheus metrics | REST API + protobuf |
| Docker Image | Official | Official | Official |
| License | BSD-3 | Apache-2.0 | GPL-2.0 |
| Performance | ~1M+ QPS | ~500K QPS | ~300K QPS |

## dnsdist

dnsdist is a DNS load balancer from the PowerDNS project, designed for high-performance DNS traffic management. Its Lua-based configuration language provides powerful response rewriting capabilities through programmable rules.

### dnsdist Docker Compose

```yaml
version: "3.8"
services:
  dnsdist:
    image: powerdns/dnsdist:1.9.x
    container_name: dnsdist-rewrite
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8053:8053"
    volumes:
      - ./dnsdist.conf:/etc/dnsdist/dnsdist.conf:ro
      - ./rules.lua:/etc/dnsdist/rules.lua:ro
    restart: unless-stopped
    cap_add:
      - NET_BIND_SERVICE
```

### dnsdist Response Rewriting Rules

```lua
-- /etc/dnsdist/dnsdist.conf
-- Load additional rules
dofile("/etc/dnsdist/rules.lua")

-- Block known malware domains
addAction("malware.example.com", RCodeAction(DNSRCode.NXDOMAIN))

-- Redirect internal services
addAction("db.internal.local", SpoofAction("10.0.1.50"))

-- Rate limit per source
addAction("any", DelayAction(100))

-- Log all queries to a specific domain
addAction("*.staging.example.com", LogAction("/var/log/dnsdist/staging.log", true, true))
```

```lua
-- /etc/dnsdist/rules.lua
-- Advanced: Block based on threat intelligence feed
function blockFromFeed(qname)
    local blocked = {
        "evil-domain.com",
        "phishing-site.net",
        "c2-server.org"
    }
    for _, domain in ipairs(blocked) do
        if qname:endsWith(domain) then
            return true
        end
    end
    return false
end

addRule(RegexRule(".*"), function(dq)
    if blockFromFeed(dq.qname:toString()) then
        dq.rcode = DNSRCode.NXDOMAIN
        return false
    end
    return true
end)
```

dnsdist excels at high-throughput DNS manipulation. Its Lua engine runs within the DNS processing pipeline, meaning rule evaluation adds minimal latency. The built-in web dashboard provides real-time query monitoring and rule statistics.

## CoreDNS

CoreDNS is a plugin-based DNS server written in Go, originally developed as the default DNS service in Kubernetes. Its modular architecture makes it easy to add response rewriting through the rewrite and host plugins.

### CoreDNS Docker Compose

```yaml
version: "3.8"
services:
  coredns:
    image: coredns/coredns:1.11.3
    container_name: coredns-rewrite
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "9153:9153"
    volumes:
      - ./Corefile:/etc/coredns/Corefile:ro
      - ./zones:/etc/coredns/zones:ro
    restart: unless-stopped
    user: "coredns"
```

### CoreDNS Corefile with Rewrite Rules

```
# /etc/coredns/Corefile
example.com:53 {
    # Rewrite internal service names
    rewrite name sub.internal.example.com 10.0.1.100

    # Redirect specific queries
    rewrite name regex dev\.(.*)\.example.com {1}.staging.example.com answer auto

    # Block ad domains
    hosts {
        0.0.0.0 ads.example.com
        0.0.0.0 tracker.example.com
        fallthrough
    }

    # Forward other queries
    forward . 8.8.8.8 1.1.1.1

    # Prometheus metrics
    prometheus :9153

    # Cache responses
    cache 300

    # Log queries
    log
    errors
}
```

```
# Advanced rewrite with response modification
.:53 {
    # Rewrite both query and response
    rewrite name exact api.prod.example.com api.internal.example.com
    rewrite type CNAME A

    # Load zone data from file
    file /etc/coredns/zones/db.internal internal

    forward . 1.1.1.1 8.8.8.8
    cache 300
    log
}
```

CoreDNS's declarative Corefile syntax makes configuration more readable than Lua scripting. The plugin ecosystem includes options for geo-based routing, health checking, and external data source integration.

## PowerDNS Recursor

PowerDNS Recursor is a high-performance recursive DNS resolver with built-in Lua scripting for response policy zones (RPZ), query rewriting, and custom resolution logic.

### PowerDNS Recursor Docker Compose

```yaml
version: "3.8"
services:
  pdns-recursor:
    image: powerdns/pdns-recursor:4.9.x
    container_name: pdns-recursor
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./recursor.conf:/etc/powerdns/recursor.conf:ro
      - ./lua-config.lua:/etc/powerdns/lua-config.lua:ro
    restart: unless-stopped
```

### PowerDNS Recursor Configuration

```ini
# /etc/powerdns/recursor.conf
local-address=0.0.0.0
local-port=53
allow-from=10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
lua-config-file=/etc/powerdns/lua-config.lua
webserver=yes
webserver-address=0.0.0.0
webserver-port=8082
api-key=changeme
```

```lua
-- /etc/powerdns/lua-config.lua
-- Block malicious domains via RPZ-like logic
prerpzfunction = function(dq)
    local blocked = {
        ["evil.com."] = true,
        ["malware.net."] = true,
    }
    if blocked[dq.qname:toString()] then
        dq.rcode = pdns.NXDOMAIN
        return true
    end
    return false
end

-- Redirect internal domains
preresolve = function(dq)
    local redirects = {
        ["db.internal.local."] = "10.0.1.50",
        ["cache.internal.local."] = "10.0.1.51",
    }
    local target = redirects[dq.qname:toString()]
    if target then
        dq:addRecord(pdns.newDNSRecord(pdns.A, dq.qname, target, 60))
        dq.rcode = pdns.NOERROR
        return true
    end
    return false
end

-- Rate limiting
nxdomain-ratelimit = 200
```

PowerDNS Recursor's Lua hooks (preresolve, prerpzfunction, postresolve) give you precise control over every stage of DNS resolution. Its RPZ-like capabilities make it suitable for enterprise-scale domain blocking and policy enforcement.

## Choosing the Right DNS Rewriting Engine

**Choose dnsdist if:** You need maximum performance and already use PowerDNS products. Its Lua API is the most flexible for complex rewriting logic and integrates seamlessly with existing PowerDNS deployments.

**Choose CoreDNS if:** You prefer declarative configuration and want a plugin ecosystem that handles everything from DNS rewriting to service discovery. It is the best choice for Kubernetes environments and teams that value readability over raw programmability.

**Choose PowerDNS Recursor if:** You need a full recursive resolver with deep Lua integration for response policy enforcement. Its Lua hooks provide the most granular control over the DNS resolution pipeline.

## Why Self-Host DNS Response Rewriting?

Self-hosted DNS rewriting gives your organization complete control over DNS traffic without relying on third-party services that may log, monetize, or mishandle your query data. When you manage your own DNS infrastructure, every query stays within your network boundary, maintaining compliance with data protection regulations and preventing DNS-based data exfiltration.

Internal service discovery is a primary use case. Self-hosted DNS rewriting lets you maintain different DNS views for different environments — developers get routed to staging services, production traffic goes to live endpoints, and QA teams see shadow deployments — all through a single DNS infrastructure with zero application changes required.

Security enforcement through DNS rewriting catches threats at the network layer before they reach endpoints. By integrating with threat intelligence feeds, you can automatically block queries to newly registered malicious domains, command-and-control servers, and phishing sites. DNS-level blocking is particularly effective because it requires no endpoint software installation and works for all devices on the network, including IoT devices that cannot run security agents.

Cost and performance are additional benefits. Commercial DNS filtering services typically charge $2-5 per user per month. Self-hosted DNS rewriting serves unlimited clients from a single server instance, with sub-millisecond query latency when properly configured.

For related reading, check our [dnsdist DoH/DoT guide](2026-05-02-knot-dns-vs-dnsdist-vs-unbound-self-hosted-dns-over-quic-guide/) for encrypting DNS traffic, the [DNS firewall and RPZ guide](2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide/) for policy-based domain blocking, and our [split-horizon DNS guide](2026-04-24-self-hosted-split-horizon-dns-pihole-dnsmasq-coredns-bind9-guide/) for serving different DNS responses based on client location.

For related reading, see our [dnsdist DoH/DoT guide](../2026-05-02-knot-dns-vs-dnsdist-vs-unbound-self-hosted-dns-over-quic-guide/) for encrypting DNS traffic, the [DNS firewall and RPZ guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide/) for policy-based domain blocking, and our [split-horizon DNS guide](../2026-04-24-self-hosted-split-horizon-dns-pihole-dnsmasq-coredns-bind9-guide/) for serving different DNS responses based on client location.

## FAQ

### What is the difference between DNS rewriting and DNS blocking?

DNS blocking is a specific form of rewriting where the response is changed to NXDOMAIN or a sinkhole IP address. DNS rewriting is the broader category that includes blocking, redirecting to different IPs, changing response types, modifying TTLs, and adding or removing DNS records. All blocking is rewriting, but not all rewriting is blocking.

### Can DNS rewriting bypass DNSSEC validation?

No — properly configured DNS rewriters must maintain DNSSEC validation. If a rewritten response breaks DNSSEC signatures, validating resolvers will reject the response and return SERVFAIL. dnsdist and PowerDNS Recursor both support DNSSEC-aware rewriting that preserves or revalidates signatures. CoreDNS handles DNSSEC through its dnssec plugin.

### How do I update DNS rewriting rules dynamically?

dnsdist supports reloading Lua configurations without restart via the REST API (`/api/v1/servers/localhost/config`). CoreDNS supports the reload plugin which watches the Corefile for changes and reloads automatically. PowerDNS Recursor can reload Lua scripts via `rec_control reload-lua`. For feed-driven updates, all three can read from external APIs or databases.

### Is DNS rewriting effective against encrypted DNS (DoH/DoT)?

Only if your DNS rewriter is the endpoint for encrypted DNS queries. If clients use DoH/DoT to external resolvers (like 1.1.1.1 or 8.8.8.8), your self-hosted rewriter never sees the traffic. To enforce DNS rewriting on your network, you must either configure clients to use your resolver or intercept and redirect DoH/DoT traffic at the firewall level.

### What performance impact does DNS rewriting add?

Minimal. dnsdist adds approximately 5-10 microseconds per rule evaluation. CoreDNS plugin chaining adds 10-20 microseconds. PowerDNS Recursor Lua hooks add 10-30 microseconds depending on script complexity. For comparison, typical DNS resolution latency is 1-10 milliseconds, so rewriting overhead is less than 1% of total query time.

### Can I use DNS rewriting for A/B testing?

Yes. DNS rewriting can route different clients to different service endpoints based on source IP, query name patterns, or external configuration. For example, you can configure rules that send 10% of traffic from a specific subnet to a new deployment while keeping 90% on the stable version. This is particularly useful for canary deployments and gradual rollouts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Response Rewriting: dnsdist vs CoreDNS vs PowerDNS Recursor",
  "description": "Compare dnsdist, CoreDNS, and PowerDNS Recursor for self-hosted DNS response rewriting, query manipulation, and policy-based domain blocking with Docker compose configs.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
