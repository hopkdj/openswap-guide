---
title: "Self-Hosted DNS Firewall & RPZ Solutions: Unbound vs PowerDNS vs BIND 9 vs Knot Resolver 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "dns", "security", "firewall"]
draft: false
description: "Compare self-hosted DNS firewall solutions with RPZ (Response Policy Zone) support. Full guide covering Unbound, PowerDNS Recursor, BIND 9, and Knot Resolver with Docker deployment configs and threat intelligence integration."
---

A DNS firewall sits at the edge of your network, intercepting every DNS query and blocking requests to known-malicious domains before a connection is ever established. Unlike application-layer firewalls that inspect traffic after the handshake, DNS firewalls stop threats at the resolution stage — preventing malware C2 callbacks, phishing page loads, and cryptomining scripts from reaching your infrastructure.

Response Policy Zones (RPZ) is the IETF-standard mechanism that makes DNS firewalls possible. An RPZ zone acts like a DNS-level hosts file: when a query matches a domain listed in the policy zone, the resolver returns a controlled response (NXDOMAIN, a sinkhole IP, or a passthrough) instead of the real answer.

In this guide, we compare the four most widely used open-source DNS resolvers with RPZ support: **Unbound**, **PowerDNS Recursor**, **BIND 9**, and **Knot Resolver**. For related reading on DNS infrastructure, see our [DNS load balancing guide](../dnsdist-vs-powerdns-recursor-vs-unbound-self-hosted-dns-load-balancing-guide-2026/) and [DNS filtering and content blocking comparison](../self-hosted-dns-filtering-content-blocking-pihole-adguard-technitium-guide-2026/).

## Why Deploy a Self-Hosted DNS Firewall

Running your own DNS firewall instead of relying on cloud-based services like Cisco Umbrella or Cloudflare Gateway gives you full control over policy rules, zero egress fees for DNS queries, and the ability to enforce custom blocklists tailored to your environment. Self-hosted DNS firewalls also keep query data on-premises, which matters for compliance with GDPR, HIPAA, and internal data governance policies.

DNS firewalls are particularly effective against:

- **Malware command-and-control (C2)** — blocking domains used by botnets and RATs
- **Phishing and scam sites** — sinkholing known phishing URLs before users visit them
- **Cryptomining scripts** — blocking mining pool domains at the DNS level
- **Data exfiltration via DNS tunneling** — detecting and blocking anomalous DNS patterns
- **Ad and tracker blocking** — optional but widely used as a secondary benefit

For teams already running DNS-over-TLS resolvers, see our [DoT resolver guide](../self-hosted-dns-over-tls-resolver-stubby-unbound-knot-2026/) for hardening options that complement DNS firewalling.

## How RPZ (Response Policy Zone) Works

RPZ defines four policy record types that control how matched queries are handled:

| Record Type | Response | Use Case |
|---|---|---|
| `CNAME .` | NXDOMAIN | Block the domain entirely |
| `CNAME *.*` | Drop (no response) | Silent drop — client times out |
| `CNAME <IP>` | Redirect to sinkhole IP | Serve a warning page |
| `CNAME rpz-passthru.` | Allow passthrough | Whitelist an FP |

A typical RPZ zone file looks like this:

```zone
$TTL 3600
@       SOA     localhost. root.localhost. (
                2026042101 ; serial
                3600       ; refresh
                900        ; retry
                604800     ; expire
                86400 )    ; minimum TTL

        NS      localhost.

; Block malware domains
evil-malware.com      CNAME .
bad-phishing.net      CNAME .
cryptominer-pool.org  CNAME .

; Redirect to sinkhole
ads.example.com       CNAME 10.0.0.1
tracker.example.net   CNAME 10.0.0.1

; Whitelist (passthrough)
false-positive.com    CNAME rpz-passthru.
```

All four resolvers covered here support loading RPZ zones, but they differ significantly in configuration complexity, policy action flexibility, and integration with threat intelligence feeds.

## Unbound with RPZ

[Unbound](https://github.com/NLnetLabs/unbound) is a validating, recursive, and caching DNS resolver from NLnet Labs. With 4,450+ GitHub stars and active development (last updated April 2026), it is one of the most widely deployed DNS resolvers in the world.

### RPZ Configuration

Unbound added native RPZ support in version 1.13.0. Configuration is done through the `rpz` directive in `unbound.conf`:

```yaml
server:
    # Enable RPZ
    rpz:
        name: "rpz.local"
        zonefile: "/etc/unbound/rpz.zone"
        # Policy actions
        rpz-action-override: nxdomain
        # Log RPZ hits
        log-local-actions: yes

    # Optional: fetch RPZ zone from a URL
    # rpz:
    #     name: "threat-feed.rpz"
    #     url: "https://example.com/rpz.zone"
    #     rpz-action-override: drop
```

### Docker Deployment

Unbound does not ship an official Docker image, but the community-maintained `mvance/unbound` image is widely used:

```yaml
version: "3.8"
services:
  unbound-rpz:
    image: mvance/unbound:latest
    container_name: unbound-rpz
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf
      - ./rpz.zone:/opt/unbound/etc/unbound/rpz.zone
    cap_add:
      - NET_BIND_SERVICE
```

### Key Features

- DNSSEC validation built-in
- RPZ supports all four policy actions (NXDOMAIN, drop, redirect, passthru)
- Can load multiple RPZ zones from files and URLs
- Logging of RPZ-triggered queries for incident response
- Low memory footprint (~50MB for typical deployments)

## PowerDNS Recursor with RPZ

[PowerDNS Recursor](https://github.com/PowerDNS/pdns) is the recursive resolver component of the PowerDNS suite. The combined PowerDNS repository has 4,346+ stars and is actively maintained. The Recursor has enterprise-grade RPZ support that is among the most flexible in the industry.

### RPZ Configuration

PowerDNS Recursor uses Lua-based configuration in `recursor.conf`:

```lua
-- recursor.conf
rpzFile=/etc/powerdns/recursor.rpz

-- Advanced: multiple RPZ zones with different policies
rpzFile=/etc/powerdns/threat-feed.rpz {
    policyName=threat-feed
    policyAction=NXDOMAIN
}

rpzFile=/etc/powerdns/custom-blocks.rpz {
    policyName=custom
    policyAction=Custom
    customIP=10.0.0.1
}
```

For more granular control, PowerDNS Recursor supports Lua scripting to implement dynamic RPZ policies:

```lua
-- prerpz.lua — dynamic policy based on query source
function prerpz(dq)
    if dq.qname:isPartOf(PDNSName("suspicious.example.com")) then
        dq.variable = true
        return true
    end
    return false
end
```

### Docker Deployment

PowerDNS provides an official Docker Compose setup:

```yaml
version: "3.8"
services:
  pdns-recursor:
    image: powerdns/pdns-recursor-49
    container_name: pdns-recursor
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8082:8082"  # Web API
    environment:
      - PDNS_RECURSOR_API_KEY=your-secret-key
    volumes:
      - ./recursor.conf:/etc/pdns-recursor/recursor.conf
      - ./recursor.rpz:/etc/pdns-recursor/recursor.rpz
```

### Key Features

- Most flexible RPZ policy engine of any open-source resolver
- Supports per-zone policy configuration
- Built-in REST API for dynamic rule management
- Lua scripting for custom policy logic
- Metrics endpoint for Prometheus/Grafana integration
- RPZ hit logging with detailed query context

## BIND 9 with RPZ

[BIND 9](https://gitlab.isc.org/isc-projects/bind9) from ISC is the original DNS server that introduced the RPZ specification. It remains the reference implementation, though its GitHub mirror (738 stars) is archived — active development happens on GitLab.

### RPZ Configuration

BIND 9 uses `named.conf` with a `response-policy` block:

```namedconf
options {
    response-policy {
        zone "rpz-threats";
        zone "rpz-custom";
    };

    // RPZ policy overrides
    response-policy {
        zone "rpz-threats" policy nxdomain;
        zone "rpz-custom" policy drop;
    };
};

zone "rpz-threats" {
    type master;
    file "/etc/bind/rpz-threats.zone";
    allow-query { any; };
};

zone "rpz-custom" {
    type master;
    file "/etc/bind/rpz-custom.zone";
    allow-query { any; };
};
```

BIND 9 also supports NSD (Name Server Daemon) mode for zone transfers, enabling you to pull RPZ zones from external threat intelligence providers via AXFR/IXFR:

```namedconf
zone "external-threat-feed" {
    type slave;
    masters { 203.0.113.1; };
    file "/etc/bind/rpz-external.zone";
    allow-notify { 203.0.113.1; };
};
```

### Docker Deployment

ISC provides an official BIND 9 Docker image:

```yaml
version: "3.8"
services:
  bind9-rpz:
    image: iscorg/bind9:latest
    container_name: bind9-rpz
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./named.conf:/etc/bind/named.conf
      - ./named.conf.local:/etc/bind/named.conf.local
      - ./rpz-threats.zone:/etc/bind/rpz-threats.zone
      - ./rpz-custom.zone:/etc/bind/rpz-custom.zone
      - bind-data:/var/cache/bind
    cap_add:
      - NET_BIND_SERVICE
      - SYS_CHROOT

volumes:
  bind-data:
```

### Key Features

- Original RPZ specification reference implementation
- Supports AXFR/IXFR for automated threat feed updates
- DNSSEC validation with inline signing
- Views for split-horizon DNS (internal vs external policies)
- Mature and extensively documented

## Knot Resolver with RPZ

[Knot Resolver](https://github.com/CZ-NIC/knot) from CZ.NIC is a modern, lightweight recursive resolver written in C. It supports RPZ through its policy module and includes Lua scripting for advanced use cases.

### RPZ Configuration

Knot Resolver uses a Lua-based configuration in `kresd.conf`:

```lua
-- Load the policy module
policy = modules.load('policy')

-- RPZ zone file
policy.add(policy.rpzfile('/etc/knot-resolver/rpz.zone'))

-- Dynamic policy rules
policy.add(policy.suffix(policy.DROP, {todname('malware.example.com')}))
policy.add(policy.suffix(policy.NXDOMAIN, {todname('phishing.example.net')}))

-- Passthrough (whitelist)
policy.add(policy.suffix(policy.PASS, {todname('trusted.example.org')}))
```

Knot Resolver also supports loading RPZ zones from a running DNS server:

```lua
-- Pull RPZ zone from a remote nameserver
policy.add(policy.rpz('rpz-feed.local', {
    ip = '203.0.113.1',
    hostname = 'rpz.threatfeed.example',
}))
```

### Docker Deployment

Knot Resolver provides an official Docker image:

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
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf
      - ./rpz.zone:/etc/knot-resolver/rpz.zone
      - knot-data:/var/cache/knot-resolver
    cap_add:
      - NET_BIND_SERVICE

volumes:
  knot-data:
```

### Key Features

- Lightweight and fast — minimal memory overhead
- Lua scripting for custom policy logic
- Supports RPZ zone files and remote zone fetching
- Integrated with Knot DNS for authoritative/recursive split setups
- Prometheus metrics exporter built-in

## Comparison Table

| Feature | Unbound | PowerDNS Recursor | BIND 9 | Knot Resolver |
|---|---|---|---|---|
| RPZ Support | Yes (v1.13+) | Yes (advanced) | Yes (reference impl) | Yes (policy module) |
| Policy Actions | All 4 types | All 4 + custom IP | NXDOMAIN, drop, passthru | NXDOMAIN, drop, pass |
| Lua Scripting | No | Yes | No | Yes |
| REST API | No | Yes | No | No |
| Prometheus Metrics | Via exporter | Built-in | Via exporter | Built-in |
| DNSSEC Validation | Yes | Yes | Yes | Yes |
| AXFR/IXFR Zone Transfer | No | No | Yes | Yes |
| Docker Image | Community | Official | Official | Official |
| Memory Footprint | ~50 MB | ~100 MB | ~150 MB | ~40 MB |
| GitHub Stars | 4,450 | 4,346 | 738 (mirror) | 300 (mirror) |
| License | BSD | GPL-2.0 | MPL-2.0 | GPL-3.0 |

## Integrating Threat Intelligence Feeds

The real power of a DNS firewall comes from keeping RPZ zones updated with current threat intelligence. Several free and commercial feeds provide RPZ-formatted zone files:

### Free RPZ Feeds

- **Spamhaus RPZ** — Free for non-commercial use; covers malware, phishing, and spam domains
- **Abuse.ch URLhaus** — Malware URL database with RPZ export
- **PhishTank** — Community-driven phishing database

### Automated Zone Updates

For BIND 9 and Knot Resolver, you can configure zone transfers from threat intelligence providers:

```namedconf
# BIND 9 — AXFR from Spamhaus
zone "zen.spamhaus.org" {
    type slave;
    masters { 204.152.184.88; };  ; NS1 of Spamhaus
    file "/etc/bind/rpz-spamhaus.zone";
};
```

For Unbound and PowerDNS Recursor, which do not support AXFR natively, use a cron job to download zone files:

```bash
#!/bin/bash
# /etc/cron.daily/update-rpz.sh
curl -s -o /etc/unbound/rpz-threats.zone \
    "https://threatfeed.example.com/rpz-export.zone"

# Reload Unbound to pick up changes
unbound-control reload
```

For PowerDNS Recursor, use the REST API for dynamic updates without restart:

```bash
curl -X PATCH \
    -H "X-API-Key: your-secret-key" \
    "http://localhost:8082/api/v1/servers/localhost/rpzzones" \
    -d '{
        "name": "threat-feed",
        "kind": "RPZ",
        "masters": ["203.0.113.1"],
        "axfr_timeout": 30
    }'
```

## Choosing the Right DNS Firewall

**Choose Unbound** if you need a simple, reliable DNS firewall with DNSSEC validation and low resource usage. It is the best fit for small to medium deployments where ease of configuration matters more than advanced features.

**Choose PowerDNS Recursor** if you need the most flexible RPZ engine with Lua scripting, REST API, and built-in metrics. It is ideal for larger organizations that need dynamic policy management and integration with existing monitoring stacks.

**Choose BIND 9** if you need AXFR/IXFR zone transfers for automated threat feed integration, or if your team already has BIND expertise. Views make it easy to apply different policies to internal vs external clients.

**Choose Knot Resolver** if you need a lightweight resolver with good RPZ support and Prometheus metrics. It is a strong choice for containerized deployments where memory footprint matters.

For teams looking to combine DNS firewalling with DNS-over-TLS encryption, our [complete DNS privacy guide](../self-hosted-dns-privacy-doh-dot-dnscrypt-complete-guide-2026/) covers how to layer DoT/DoH on top of any of these resolvers.

## FAQ

### What is RPZ and how does it differ from standard DNS blocking?

RPZ (Response Policy Zone) is an IETF-standard mechanism for DNS-level policy enforcement. Unlike simple DNS blocking (like Pi-hole's blocklist), RPZ supports multiple policy actions: NXDOMAIN (domain not found), drop (no response), redirect (sinkhole IP), and passthru (whitelist). This flexibility allows administrators to serve custom block pages for phishing domains while silently dropping malware C2 callbacks.

### Can I use multiple RPZ zones at the same time?

Yes. All four resolvers support loading multiple RPZ zones simultaneously. You can combine a threat intelligence feed zone with a custom internal blocklist and a whitelist zone. The resolver evaluates zones in order, with the first matching rule taking precedence.

### How often should RPZ zones be updated?

Threat intelligence zones should be updated at least daily. BIND 9 supports AXFR/IXFR for automatic incremental transfers. For file-based RPZ (Unbound, PowerDNS Recursor, Knot Resolver), a daily cron job to download updated zones and reload the resolver is the standard approach.

### Does RPZ work with DNS-over-TLS and DNS-over-HTTPS?

Yes. RPZ operates at the resolution layer, so it works regardless of whether queries arrive via plaintext DNS, DoT, or DoH. You can deploy a DNS firewall resolver that also offers DoT/DoH upstream to upstream resolvers or root servers.

### Is a self-hosted DNS firewall enough for complete network security?

No. A DNS firewall is one layer of defense. It blocks known-bad domains but cannot detect threats accessed via direct IP connections, encrypted C2 channels that bypass DNS, or zero-day domains not yet in threat feeds. Combine DNS firewalling with network monitoring, endpoint protection, and egress filtering for a complete security posture.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Firewall & RPZ Solutions: Unbound vs PowerDNS vs BIND 9 vs Knot Resolver 2026",
  "description": "Compare self-hosted DNS firewall solutions with RPZ (Response Policy Zone) support. Full guide covering Unbound, PowerDNS Recursor, BIND 9, and Knot Resolver with Docker deployment configs and threat intelligence integration.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
