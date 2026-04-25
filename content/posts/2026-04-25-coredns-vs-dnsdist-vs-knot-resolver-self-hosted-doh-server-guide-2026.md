---
title: "CoreDNS vs dnsdist vs Knot Resolver: Best Self-Hosted DoH Server 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "privacy", "dns"]
draft: false
description: "Compare the top open-source DNS-over-HTTPS server solutions for self-hosted deployments. Complete setup guides for CoreDNS, dnsdist, and Knot Resolver with Docker configurations."
---

Running your own DNS-over-HTTPS (DoH) server gives you full control over encrypted DNS resolution for your network, clients, or even as a public service. Unlike DoH forwarders — which act as clients sending queries upstream — a DoH **server** accepts HTTPS-encapsulated DNS queries from remote clients and resolves them locally or forwards them to your chosen upstream.

This guide compares three powerful open-source DNS servers that can serve DNS-over-HTTPS in 2026: **CoreDNS**, **dnsdist**, and **Knot Resolver**. Each takes a different architectural approach, making them suitable for different use cases.

| Feature | CoreDNS | dnsdist | Knot Resolver |
|---|---|---|---|
| **GitHub Stars** | 14,015 | 4,348 (PowerDNS org) | 860+ |
| **Language** | Go | C++ | C |
| **Last Updated** | 2026-04-22 | 2026-04-24 | Active |
| **DoH Support** | Plugin-based (forward + tls) | Native (since 1.5.0) | Native (since 4.0) |
| **Primary Use** | Kubernetes DNS, extensible DNS | Load balancing, DoH/DoT gateway | High-performance recursive resolver |
| **Config Format** | Corefile (declarative) | Lua scripting | KNOT configuration |
| **DNSSEC** | Via plugin | Pass-through / validation | Full validating resolver |
| **Caching** | Cache plugin | Via cache backend | Built-in aggressive caching |
| **Docker Image** | `coredns/coredns` | `powerdns/dnsdist` | `cznic/knot-resolver` |
| **Extensibility** | Plugin ecosystem (40+ plugins) | Lua scripts, Actions/Rules | Lua modules, policies |
| **Best For** | Kubernetes, custom DNS pipelines | DoH/DoT termination, load balancing | Recursive resolution with DoH |

## Why Run Your Own DoH Server

Most self-hosted DNS guides focus on the client side — configuring your resolver to use encrypted upstream servers. But running your own DoH server serves several important purposes:

**Private encrypted DNS for your organization**: Instead of relying on public DoH providers (Cloudflare, Google, Quad9), you can host your own DoH endpoint. Clients query your server over HTTPS, and you control the resolution chain, logging policy, and filtering rules.

**Multi-protocol DNS termination**: A DoH server like dnsdist can accept queries over DoH, DoT (DNS-over-TLS), and plain DNS simultaneously, routing them intelligently based on policy, source, or query type.

**Corporate compliance**: Organizations with strict data residency requirements can keep all DNS traffic within their infrastructure. Employees and devices use the corporate DoH endpoint instead of public resolvers.

**Public DoH service**: You can run a public DoH resolver for your community, offering an encrypted alternative to big-tech DNS providers with your own privacy policy and filtering rules.

**Defense in depth**: Even if you already run Pi-hole or AdGuard Home for filtering, placing a DoH server in front of them encrypts the entire query path from external clients to your filtering layer.

For related reading, see our [DoH forwarder comparison](../2026-04-22-cloudflared-vs-dnsproxy-vs-dnscrypt-proxy-doh-forwarder-guide-2026/) for the client-side perspective, and our [DNS-over-QUIC guide](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/) for the next-generation encrypted DNS protocol.

## CoreDNS: Plugin-Based DNS Server

CoreDNS is a DNS server written in Go that chains plugins together to build a DNS pipeline. Originally designed as the default Kubernetes DNS, it has grown into a general-purpose DNS server with excellent DoH support through its `forward` and `tls` plugins.

### How CoreDNS Handles DoH

CoreDNS serves DoH using the `dns` and `tls` plugins combined with HTTP/2 support. The configuration is declarative — you define a Corefile that specifies which plugins to load and in what order.

```dockerfile
# Dockerfile for CoreDNS with DoH
FROM coredns/coredns:latest

COPY Corefile /etc/coredns/Corefile
COPY server.crt /etc/coredns/server.crt
COPY server.key /etc/coredns/server.key

EXPOSE 443 53 53/udp 8053

CMD ["-conf", "/etc/coredns/Corefile"]
```

```yaml
# docker-compose.yml for CoreDNS DoH Server
services:
  coredns:
    image: coredns/coredns:latest
    container_name: coredns-doh
    ports:
      - "443:443/tcp"
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./Corefile:/etc/coredns/Corefile:ro
      - ./certs:/etc/coredns/certs:ro
    restart: unless-stopped
    cap_add:
      - NET_BIND_SERVICE
```

```corefile
# Corefile — CoreDNS DoH configuration
https://:443 {
    tls /etc/coredns/certs/server.crt /etc/coredns/certs/server.key

    # Forward all queries to upstream resolvers
    forward . 8.8.8.8 1.1.1.1 {
        health_check 5s
    }

    # Cache responses
    cache 300

    # Log all queries
    log

    # Prometheus metrics
    prometheus :9153

    # Health check endpoint
    health
    ready
}
```

### CoreDNS Strengths

- **Plugin ecosystem**: Over 40 plugins covering caching, forwarding, rewriting, Kubernetes service discovery, and more
- **Kubernetes native**: The default Kubernetes DNS — if you're running K8s, CoreDNS is already there
- **Simple configuration**: The Corefile format is easy to read and version-control
- **Multi-protocol**: Can serve DNS over UDP, TCP, TLS, gRPC, and HTTP/2 (DoH) simultaneously

### CoreDNS Limitations

- DoH support requires careful TLS configuration — it's not a single-flag setup
- Recursive resolution is delegated to upstream servers (it's primarily a forwarding server)
- Not designed as a high-performance recursive resolver on its own

## dnsdist: DNS Load Balancer with DoH Termination

dnsdist (DNS Distributor) is a highly flexible DNS load balancer from the PowerDNS project. It excels at accepting DNS traffic over multiple protocols (plain, DoT, DoH) and distributing it across backend resolvers. While it doesn't resolve queries itself, it's the most mature DoH termination layer available in open source.

### How dnsdist Handles DoH

dnsdist uses Lua scripting for configuration, giving you programmatic control over query routing, rate limiting, and response manipulation. Its DoH implementation is production-grade and used by many large DNS operators.

```yaml
# docker-compose.yml for dnsdist DoH Server
services:
  dnsdist:
    image: powerdns/dnsdist:1.9.0
    container_name: dnsdist-doh
    ports:
      - "443:443/tcp"
      - "8443:8443/tcp"   # web console
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./dnsdist.conf:/etc/dnsdist/dnsdist.conf:ro
      - ./certs:/etc/dnsdist/certs:ro
    restart: unless-stopped
    cap_add:
      - NET_BIND_SERVICE
```

```lua
-- dnsdist.conf — DoH server configuration

-- Define backend resolvers
newServer({address="8.8.8.8", name="google-dns"})
newServer({address="1.1.1.1", name="cloudflare-dns"})

-- DoH configuration with TLS
addDOHLocal("0.0.0.0:443", "/etc/dnsdist/certs/server.crt",
            "/etc/dnsdist/certs/server.key",
            "/dns-query",
            {customResponseHeaders={["Server"]="dnsdist-doh"}})

-- Rate limiting: 10 queries/second per source
addAction(MaxQPSIPAction(10, 60), DropAction())

-- Block specific domains
addAction(RegexRule("^(.*\\.)?malware\\.example\\.$"), DropAction())

-- Log queries
addLuaAction(AllRule(), function(dq)
    dq:setSkipCache(false)
    return DNSAction.None, ""
end)

-- Web console for monitoring
webserver("0.0.0.0:8443", "admin-password")
setAPIKey("api-secret-key")
```

### dnsdist Strengths

- **Production-grade DoH**: Used by real DNS operators at scale
- **Powerful Lua scripting**: Complex routing, filtering, and rate-limiting logic
- **Load balancing**: Distributes queries across multiple backend resolvers with health checks
- **Protocol bridging**: Accepts DoH/DoT and forwards to plain DNS backends (or vice versa)
- **Built-in web console**: Real-time query monitoring and statistics

### dnsdist Limitations

- Not a recursive resolver — you need backend resolvers (Unbound, Knot, PowerDNS Recursor)
- Lua configuration has a steeper learning curve than declarative formats
- Some advanced DoH features (HTTP/3 support) may require newer versions

## Knot Resolver: High-Performance Recursive Resolver with Native DoH

Knot Resolver, developed by CZ.NIC (the Czech national registry), is a high-performance caching DNS resolver with native DoH support. Unlike CoreDNS and dnsdist, it is a full recursive resolver — it doesn't need upstream servers to do the heavy lifting.

### How Knot Resolver Handles DoH

Knot Resolver includes built-in DoH support via its `http` module. Configuration uses a combination of declarative settings and Lua scripting for advanced policies.

```yaml
# docker-compose.yml for Knot Resolver DoH Server
services:
  knot-resolver:
    image: cznic/knot-resolver:latest
    container_name: knot-doh
    ports:
      - "443:443/tcp"
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf:ro
      - ./certs:/etc/knot-resolver/certs:ro
      - knot-data:/var/lib/knot-resolver
    restart: unless-stopped
    cap_add:
      - NET_BIND_SERVICE

volumes:
  knot-data:
```

```lua
-- kresd.conf — Knot Resolver DoH configuration

-- Listen on standard DNS ports
net.listen('0.0.0.0', 53, { kind = 'dns' })

-- Enable DoH on port 443
net.listen('0.0.0.0', 443, { kind = 'web' })

-- TLS configuration
tls.server('/etc/knot-resolver/certs/server.crt',
           '/etc/knot-resolver/certs/server.key')

-- Enable DNSSEC validation
policy.add(policy.all(policy.TLS_FORWARD({
    {'8.8.8.8', hostname='dns.google'},
    {'1.1.1.1', hostname='cloudflare-dns.com'},
})))

-- Cache configuration
cache.size = 500 * MB

-- Query logging
log.info('Knot Resolver started with DoH enabled')

-- Aggressive NSEC caching (reduces upstream queries)
aggressive.nsec = true
```

### Knot Resolver Strengths

- **Full recursive resolver**: Resolves queries from root servers, no upstream dependency
- **DNSSEC validation**: Built-in, always-on DNSSEC validation
- **Aggressive NSEC caching**: Caches negative responses aggressively, reducing upstream load by 20-30%
- **High performance**: Written in C, optimized for high-throughput resolution
- **Lua scripting**: Flexible policy engine for filtering and customization

### Knot Resolver Limitations

- Smaller community compared to CoreDNS
- Configuration combines declarative and Lua styles, which can be confusing
- DoH configuration requires manual TLS certificate management

## Choosing the Right DoH Server

Your choice depends on your primary use case:

**Choose CoreDNS if**:
- You're running Kubernetes and want a unified DNS solution
- You need a plugin-based architecture for custom DNS pipelines
- You prefer simple, declarative configuration

**Choose dnsdist if**:
- You need DoH termination with intelligent query routing
- You're running multiple backend resolvers and need load balancing
- You require advanced rate limiting and traffic policies

**Choose Knot Resolver if**:
- You want a standalone recursive resolver with DoH
- DNSSEC validation is a hard requirement
- You need maximum resolution performance for high-traffic deployments

For most self-hosted setups, a common pattern is **dnsdist in front + Knot Resolver behind**: dnsdist handles DoH termination, rate limiting, and load distribution, while Knot Resolver provides recursive resolution with DNSSEC validation.

```yaml
# docker-compose.yml — dnsdist + Knot Resolver architecture
services:
  dnsdist:
    image: powerdns/dnsdist:1.9.0
    container_name: dnsdist
    ports:
      - "443:443/tcp"
    volumes:
      - ./dnsdist.conf:/etc/dnsdist/dnsdist.conf:ro
      - ./certs:/etc/dnsdist/certs:ro
    depends_on:
      - knot-resolver
    restart: unless-stopped

  knot-resolver:
    image: cznic/knot-resolver:latest
    container_name: knot-resolver
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf:ro
      - knot-data:/var/lib/knot-resolver
    restart: unless-stopped

  # Optional: Add a second Knot Resolver for redundancy
  knot-resolver-2:
    image: cznic/knot-resolver:latest
    container_name: knot-resolver-2
    volumes:
      - ./kresd-2.conf:/etc/knot-resolver/kresd.conf:ro
      - knot-data-2:/var/lib/knot-resolver
    restart: unless-stopped

volumes:
  knot-data:
  knot-data-2:
```

## TLS Certificate Setup

All three servers require TLS certificates for DoH. Here's how to generate self-signed certificates for testing:

```bash
# Generate a self-signed certificate for DoH
openssl req -x509 -newkey rsa:2048 -keyout server.key \
  -out server.crt -days 365 -nodes \
  -subj "/CN=doh.example.com" \
  -addext "subjectAltName=DNS:doh.example.com,IP:192.168.1.100"

# Place in your certs directory
mkdir -p certs
cp server.key server.crt certs/
```

For production, use Let's Encrypt with cert-manager (Kubernetes) or certbot (standalone). See our [certificate management guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) for automated renewal options.

## FAQ

### What is the difference between a DoH server and a DoH forwarder?

A DoH **forwarder** (like cloudflared or dnsproxy) runs on the client side — it accepts plain DNS from your local devices and forwards those queries to an upstream DoH provider. A DoH **server** runs on the infrastructure side — it accepts encrypted DoH queries from remote clients and resolves them. Think of forwarders as DoH clients and servers as DoH endpoints.

### Can I use these tools with Pi-hole or AdGuard Home?

Yes. A common architecture is: DoH Server → Pi-hole/AdGuard Home → Upstream Resolver. The DoH server accepts encrypted queries from external clients, forwards them to Pi-hole for filtering, and Pi-hole forwards clean queries to upstream resolvers. This gives you encrypted external access with local ad-blocking.

### Do I need a public SSL certificate for my DoH server?

For external clients, yes — most DoH clients (browsers, OS resolvers) will reject self-signed certificates. Use Let's Encrypt or another trusted CA. For internal corporate use, you can deploy your own PKI and distribute the root CA certificate to all managed devices.

### Which tool has the best performance for high-traffic DoH?

Knot Resolver is optimized for high-throughput recursive resolution and typically handles the most queries per second. dnsdist adds minimal overhead as a load balancer (~1-2ms per query). CoreDNS is slightly slower due to its Go runtime and plugin chain, but performs well for most self-hosted workloads.

### Can I run all three in production together?

You can combine them in layers: dnsdist handles DoH termination and load balancing across multiple Knot Resolver instances, while CoreDNS serves internal Kubernetes DNS. This is actually a recommended pattern for large organizations that need both public DoH services and internal DNS infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CoreDNS vs dnsdist vs Knot Resolver: Best Self-Hosted DoH Server 2026",
  "description": "Compare the top open-source DNS-over-HTTPS server solutions for self-hosted deployments. Complete setup guides for CoreDNS, dnsdist, and Knot Resolver with Docker configurations.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
