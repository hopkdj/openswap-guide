---
title: "Self-Hosted SSL/TLS Proxy Comparison: stunnel vs sslh vs hitch (2026)"
date: "2026-05-07"
draft: false
tags: ["ssl", "tls", "proxy", "security", "stunnel", "sslh", "hitch", "self-hosted"]
---

SSL/TLS proxy software sits between clients and backend services, handling encryption termination, protocol multiplexing, and secure traffic forwarding. Whether you need to expose a single service over HTTPS, multiplex multiple protocols on one port, or handle thousands of TLS connections at scale, the right proxy makes all the difference.

This guide compares three mature open-source SSL/TLS proxy solutions: **stunnel**, **sslh**, and **hitch**. Each takes a fundamentally different approach to TLS proxying, and understanding their strengths will help you pick the right tool for your infrastructure.

## What Is an SSL/TLS Proxy?

An SSL/TLS proxy terminates encrypted connections from clients and forwards decrypted traffic to backend servers — or conversely, encrypts outgoing traffic before it reaches the internet. Unlike full reverse proxies like Nginx or Traefik, dedicated TLS proxies focus on a single job: handling the TLS layer efficiently.

Key use cases include:

- **TLS termination** for legacy services that lack native HTTPS support
- **Protocol multiplexing** — running SSH, HTTPS, and OpenVPN on the same port
- **High-performance TLS offloading** for load balancers and CDN edge nodes
- **mTLS (mutual TLS)** enforcement for zero-trust service meshes

## stunnel: The Universal TLS Tunnel

[stunnel](https://www.stunnel.org/) is the oldest and most widely deployed TLS proxy. Created in 1998, it wraps arbitrary TCP connections in TLS/SSL encryption. It is available in every major Linux distribution's package repository.

### Key Features

- Wraps any TCP service in TLS (SMTP, IMAP, POP3, databases, custom protocols)
- Client and server mode
- Certificate-based authentication and client certificate verification
- Stunnel can chain proxies for multi-hop encryption
- Simple INI-style configuration

### Docker Deployment

stunnel is distributed as a lightweight Docker image. A typical setup:

```yaml
version: "3.8"
services:
  stunnel:
    image: vimagick/stunnel:latest
    container_name: stunnel
    ports:
      - "443:443"
    volumes:
      - ./stunnel.conf:/etc/stunnel/stunnel.conf:ro
      - ./certs:/etc/stunnel/certs:ro
    restart: unless-stopped
    networks:
      - backend
```

Sample `stunnel.conf` for HTTPS termination:

```ini
[https]
accept = 0.0.0.0:443
connect = 127.0.0.1:8080
cert = /etc/stunnel/certs/server.pem
CAfile = /etc/stunnel/certs/ca.pem
verify = 2
```

### When to Use stunnel

- You need to add TLS to legacy protocols (IMAP, POP3, IRC, database connections)
- Simple point-to-point TLS tunneling
- Client certificate authentication for internal services
- Quick setup with minimal configuration overhead

## sslh: The Protocol Multiplexer

[sslh](https://github.com/yrutschle/sslh) (5,062 stars on GitHub) is a protocol demultiplexer that listens on a single port and routes incoming connections based on the protocol detected in the first bytes. It can share port 443 between HTTPS, SSH, OpenVPN, and more.

### Key Features

- Protocol detection: HTTPS, SSH, OpenVPN, XMPP, any custom protocol
- Transparent proxy mode — backend sees the original client IP
- Forking and threading modes for different load profiles
- Support for SNI-based routing (different backends based on hostname)
- Lightweight: single binary, minimal dependencies

### Docker Deployment

```yaml
version: "3.8"
services:
  sslh:
    image: ghcr.io/yrutschle/sslh:latest
    container_name: sslh
    network_mode: host
    environment:
      - DAEMON_OPTS="--user sslh --listen 0.0.0.0:443 --ssh 127.0.0.1:22 --ssl 127.0.0.1:443 --openvpn 127.0.0.1:1194 --anyprot 127.0.0.1:80 --pidfile /var/run/sslh/sslh.pid"
    restart: unless-stopped
```

Command-line configuration:

```bash
sslh --listen 0.0.0.0:443 \
     --ssh 127.0.0.1:22 \
     --ssl 127.0.0.1:8443 \
     --openvpn 127.0.0.1:1194 \
     --anyprot 127.0.0.1:80 \
     --transparent \
     --user sslh \
     --pidfile /var/run/sslh/sslh.pid
```

### When to Use sslh

- You are behind a restrictive firewall that only allows port 443
- You need SSH and HTTPS on the same port
- Running OpenVPN and a web server on port 443 simultaneously
- SNI-based virtual hosting without a full reverse proxy

## hitch: High-Performance TLS Termination

[hitch](https://github.com/varnish/hitch) (1,942 stars) is a scalable TLS proxy built by Varnish Software. It is designed for high-throughput environments where TLS termination is the bottleneck. Hitch integrates natively with Varnish Cache and HAProxy via the PROXY protocol.

### Key Features

- Multi-process architecture for CPU core utilization
- OCSP stapling for faster TLS handshakes
- ALPN (Application-Layer Protocol Negotiation) support for HTTP/2
- PROXY protocol v1/v2 for passing client IPs to backends
- TLS 1.2 and 1.3 support with modern cipher suites
- Designed to handle tens of thousands of concurrent connections

### Docker Deployment

```yaml
version: "3.8"
services:
  hitch:
    image: varnish/hitch:latest
    container_name: hitch
    ports:
      - "443:443"
    volumes:
      - ./hitch.conf:/etc/hitch/hitch.conf:ro
      - ./certs:/etc/hitch/certs:ro
    restart: unless-stopped
    networks:
      - backend
```

Sample `hitch.conf`:

```ini
frontend = "[*]:443"
backend = "[127.0.0.1]:8443"

pem-file = "/etc/hitch/certs/server.pem"

ciphersuites = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256"
ciphers = "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"

prefer-server-ciphers = on
ocsp-dir = "/var/lib/hitch/ocsp"

write-proxy-v2 = on
```

### When to Use hitch

- High-traffic websites needing TLS offloading
- Deployments paired with Varnish Cache or HAProxy
- Environments requiring OCSP stapling and ALPN
- Edge nodes and CDN origin shields

## Comparison Table

| Feature | stunnel | sslh | hitch |
|---|---|---|---|
| **Primary Purpose** | TLS tunnel for any TCP | Protocol multiplexer | High-performance TLS termination |
| **GitHub Stars** | N/A (sourceforge) | 5,062 | 1,942 |
| **Protocol Detection** | No | Yes (SSH, HTTPS, OpenVPN, etc.) | No |
| **SNI Routing** | No | Yes | No |
| **OCSP Stapling** | No | No | Yes |
| **ALPN Support** | Partial | No | Yes |
| **PROXY Protocol** | No | Transparent mode | v1/v2 |
| **Multi-process** | No | No | Yes |
| **mTLS / Client Certs** | Yes | No | No |
| **Docker Image** | vimagick/stunnel | ghcr.io/yrutschle/sslh | varnish/hitch |
| **Package Managers** | apt, yum, apk | apt, yum | apt, yum |
| **Best For** | Legacy TLS wrapping | Port sharing | High-scale TLS offload |

## Installation Guide

### Install stunnel (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install stunnel4 -y
sudo systemctl enable stunnel4
sudo systemctl start stunnel4
```

### Install sslh (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install sslh -y
sudo systemctl enable sslh
sudo systemctl start sslh
```

### Install hitch (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install hitch -y
sudo systemctl enable hitch
sudo systemctl start hitch
```

## Why Self-Host Your TLS Proxy?

Running your own SSL/TLS proxy gives you full control over encryption parameters, certificate management, and traffic routing. Cloud-managed TLS termination services lock you into specific vendors, limit cipher suite choices, and add latency through additional network hops.

With a self-hosted TLS proxy, you can implement mutual TLS for internal services, enforce specific TLS versions and cipher suites for compliance (PCI DSS, HIPAA), and multiplex protocols on restricted ports without depending on third-party infrastructure. For organizations running services across multiple data centers, self-hosted TLS proxies provide a consistent encryption layer that travels with your infrastructure.

For certificate automation, see our [TLS certificate automation guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/). If you need SSL/TLS scanning and auditing capabilities, check our [SSL scanning tools comparison](../2026-04-22-testssl-vs-sslyze-vs-sslscan-self-hosted-ssl-tls-scanning-guide-2026/). For full reverse proxy solutions, our [reverse proxy comparison](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/) covers Docker registry proxies in depth.


Organizations running microservices architectures benefit particularly from self-hosted TLS proxies. Service-to-service communication in Kubernetes clusters often relies on mTLS for authentication, and running dedicated TLS proxies as sidecars provides a consistent security layer without modifying application code. This approach is especially valuable for legacy applications that cannot be easily updated to support modern TLS versions.

Hardware security modules (HSMs) can be integrated with self-hosted TLS proxies for organizations with strict key management requirements. While cloud TLS termination stores private keys in the provider's infrastructure, self-hosted proxies keep keys on-premises, satisfying regulatory requirements in finance, healthcare, and government sectors.

For teams managing TLS across dozens of services, automation tools become essential. Certificate rotation, revocation checking, and compliance auditing are all manageable within a self-hosted TLS proxy infrastructure — something that cloud-managed services either do not offer or charge premium rates for.

## FAQ

### What is the difference between stunnel and a reverse proxy?

stunnel is a dedicated TLS tunnel that wraps TCP connections in encryption. It does not handle HTTP routing, load balancing, or content-based decisions. A reverse proxy like Nginx or Traefik operates at the HTTP layer, supporting virtual hosts, path-based routing, and caching. Use stunnel when you need TLS for non-HTTP protocols or simple point-to-point encryption.

### Can sslh share port 443 with both HTTPS and SSH?

Yes. sslh detects the protocol from the first bytes of each incoming connection. HTTPS connections (starting with a TLS ClientHello) are forwarded to your web server, while SSH connections (starting with `SSH-`) are forwarded to your SSH daemon. This is particularly useful when you are behind a corporate firewall that only allows outbound traffic on port 443.

### Does hitch support HTTP/2?

hitch supports ALPN (Application-Layer Protocol Negotiation), which enables HTTP/2 negotiation during the TLS handshake. However, hitch itself does not speak HTTP/2 — it passes the negotiated protocol to the backend (e.g., Varnish or HAProxy), which handles the HTTP/2 framing.

### Is stunnel still maintained?

Yes. stunnel receives regular security updates and is included in all major Linux distributions. Development is stable rather than rapid, as the codebase is mature and focused. The project maintains its own release cycle at stunnel.org.

### Which TLS proxy should I choose for a high-traffic website?

For high-traffic deployments, hitch is the best choice. Its multi-process architecture, OCSP stapling, ALPN support, and PROXY protocol integration make it ideal for pairing with Varnish Cache or HAProxy at the edge. stunnel and sslh are better suited for internal services, protocol multiplexing, and legacy protocol encryption.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SSL/TLS Proxy Comparison: stunnel vs sslh vs hitch (2026)",
  "description": "Compare three open-source SSL/TLS proxy solutions: stunnel for TLS tunneling, sslh for protocol multiplexing, and hitch for high-performance TLS termination. Includes Docker configs and deployment guides.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
