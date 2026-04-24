
---
title: "mitmproxy vs sslsplit vs bettercap: Self-Hosted TLS Interception Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "security", "networking", "proxy"]
draft: false
description: "Compare mitmproxy, sslsplit, and bettercap for self-hosted TLS interception and network traffic analysis. Complete setup guide with Docker configs and iptables rules for security testing."
---

## Why You Need Self-Hosted TLS Interception

TLS (Transport Layer Security) encrypts the vast majority of internet traffic today. While this protects user privacy, it also means security teams, penetration testers, and network administrators cannot inspect traffic for threats, policy violations, or debugging purposes. Self-hosted TLS interception tools solve this problem by acting as a man-in-the-middle proxy — decrypting, inspecting, and re-encrypting traffic between clients and servers.

Whether you're debugging API calls, testing security controls, auditing network traffic, or training a security team, having your own TLS interception tool under your control is essential. This guide compares three powerful open-source options: **mitmproxy**, **sslsplit**, and **bettercap**, each with distinct strengths and ideal use cases.

## Overview of the Three Tools

| Feature | mitmproxy | sslsplit | bettercap |
|---|---|---|---|
| **Language** | Python | C | Go |
| **GitHub Stars** | 43,259 | 1,862 | 19,113 |
| **Last Updated** | April 2026 | October 2025 | April 2026 |
| **License** | MIT | BSD-2-Clause | GPL v3 |
| **Primary Use** | HTTP/HTTPS proxy, API debugging | Transparent TLS interception | Network reconnaissance & MITM attacks |
| **Protocol Support** | HTTP/1, HTTP/2, WebSocket, gRPC | TCP, SSL/TLS, STARTTLS | HTTP, HTTPS, TCP, UDP, BLE, WiFi |
| **Interface** | Terminal UI, Web UI, CLI, API | CLI only | CLI, Web UI |
| **Transparent Mode** | Yes (with iptables) | Yes (native) | Yes (with iptables) |
| **Scripting** | Python addons | No | JavaScript (caplets) |
| **Certificate Generation** | Automatic CA | Manual CA setup | Automatic CA |
| **Docker Support** | Official image | Community images | Official image |

## mitmproxy: The Developer-Friendly TLS Proxy

[mitmproxy](https://mitmproxy.org/) is the most popular TLS interception tool, maintained by a large community and trusted by developers and security professionals alike. It provides three interfaces: a terminal-based interactive console (`mitmproxy`), a command-line dump tool (`mitmdump`), and a full web interface (`mitmweb`).

### Key Features

- **HTTP/2 and WebSocket support** — inspects modern web protocols, not just HTTP/1.1
- **Python addon system** — write custom scripts to modify traffic, log requests, or inject responses
- **Flow recording and replay** — save captured sessions as HAR files and replay them later
- **SSL/TLS passthrough** — selectively bypass interception for specific hosts (banking apps, pinning-heavy services)
- **Reverse proxy mode** — acts as a gateway to a specific backend server

### Installation

**Using pip:**
```bash
pip3 install mitmproxy
```

**Using Docker:**
```yaml
# docker-compose.yml
version: "3.8"
services:
  mitmproxy:
    image: mitmproxy/mitmproxy:latest
    container_name: mitmproxy
    ports:
      - "8080:8080"    # HTTP proxy
      - "8081:8081"    # Web interface
    volumes:
      - ./mitmproxy-data:/home/mitmproxy/.mitmproxy
    command: >
      mitmweb --web-host 0.0.0.0 --listen-host 0.0.0.0
    restart: unless-stopped
```

### Transparent Proxy Setup

To intercept traffic without configuring clients manually, set up iptables rules on a Linux gateway:

```bash
# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Redirect HTTP traffic to mitmproxy
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080

# Redirect HTTPS traffic to mitmproxy
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080
```

Then start mitmproxy in transparent mode:

```bash
mitmproxy --mode transparent --set confdir=~/.mitmproxy
```

### Custom Addon Example

One of mitmproxy's greatest strengths is its Python addon API. Here's a simple addon that logs all requests to a specific domain:

```python
# log_requests.py
from mitmproxy import http

class RequestLogger:
    def response(self, flow: http.HTTPFlow):
        if "api.example.com" in flow.request.host:
            print(f"[{flow.request.method}] {flow.request.url}")
            print(f"  Status: {flow.response.status_code}")
            print(f"  Content-Type: {flow.response.headers.get('Content-Type', 'unknown')}")

addons = [RequestLogger()]
```

Run it with:
```bash
mitmproxy --mode transparent --scripts log_requests.py
```

## sslsplit: Lightweight Transparent TLS Interceptor

[sslsplit](https://www.roe.ch/SSLsplit) is a C-based tool designed specifically for transparent SSL/TLS interception at the network level. Unlike mitmproxy, it operates below the HTTP layer, making it protocol-agnostic — it can intercept any TCP-based TLS connection, including SMTP, IMAP, FTP, and custom protocols.

### Key Features

- **Protocol-agnostic** — intercepts any TLS/TCP connection, not just HTTP
- **SNI-based routing** — uses Server Name Indication to determine target certificates
- **Minimal resource usage** — C binary with very low memory footprint, ideal for embedded systems
- **STARTTLS support** — handles protocols that upgrade to TLS mid-connection (SMTP, IMAP, XMPP)
- **OCSP stapling** — can serve cached OCSP responses to avoid detection

### Installation

sslsplit must be compiled from source:

```bash
# Install build dependencies
apt-get update && apt-get install -y \
    build-essential gcc make \
    libssl-dev libevent-dev

# Clone and build
git clone https://github.com/droe/sslsplit.git
cd sslsplit
make
sudo make install
```

### Docker Deployment (Community Image)

```yaml
# docker-compose.yml
version: "3.8"
services:
  sslsplit:
    image: ghcr.io/community/sslsplit:latest
    container_name: sslsplit
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./certs:/etc/sslsplit/certs
      - ./logs:/var/log/sslsplit
    command: >
      sslsplit -D -k /etc/sslsplit/certs/ca.key
      -c /etc/sslsplit/certs/ca.crt
      -l /var/log/sslsplit/connections.log
      ssl 0.0.0.0 8443
      tcp 0.0.0.0 8080
    restart: unless-stopped
```

### Transparent Interception Setup

sslsplit requires iptables rules to redirect traffic, plus a generated CA certificate:

```bash
# Generate CA key and certificate
openssl genrsa -out ca.key 4096
openssl req -new -x509 -key ca.key -out ca.crt -days 3650 \
    -subj "/CN=Interception CA"

# Redirect traffic
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to 8443
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to 8080

# Start sslsplit
sslsplit -D -k ca.key -c ca.crt \
    -l /var/log/sslsplit/connections.log \
    ssl 0.0.0.0 8443 \
    tcp 0.0.0.0 8080
```

### When to Choose sslsplit

sslsplit excels when you need to inspect non-HTTP protocols. If you're auditing email server traffic (SMTP/IMAP over TLS), testing custom binary protocols, or working in resource-constrained environments where a Python runtime isn't available, sslsplit is the right choice. Its minimal footprint makes it ideal for deployment on routers, Raspberry Pis, or network taps.

## bettercap: The Swiss Army Knife of Network Attacks

[bettercap](https://www.bettercap.org/) is a comprehensive network reconnaissance and attack framework written in Go. While it includes TLS interception capabilities, it goes far beyond that — supporting WiFi attacks, Bluetooth LE reconnaissance, HID device injection, and CAN-bus analysis. Its caplet scripting system (JavaScript-based) allows complex automated attack chains.

### Key Features

- **Multi-protocol** — WiFi, BLE, IPv4, IPv6, CAN-bus, HID
- **Caplet scripting** — JavaScript-based automation for complex attack scenarios
- **Built-in API server** — REST API for remote control and integration
- **Web UI** — Modern browser-based interface (`webui`)
- **Module system** — pluggable architecture with modules for ARP spoofing, DNS spoofing, HTTP proxy, and more
- **Packet crafting** — forge custom packets for testing network defenses

### Installation

**Using Go:**
```bash
go install github.com/bettercap/bettercap/v2@latest
```

**Using pre-built binaries:**
```bash
wget https://github.com/bettercap/bettercap/releases/latest/download/bettercap_linux_amd64.tar.gz
tar xzf bettercap_linux_amd64.tar.gz
sudo cp bettercap /usr/local/bin/
```

**Using Docker:**
```yaml
# docker-compose.yml
version: "3.8"
services:
  bettercap:
    image: bettercap/bettercap:latest
    container_name: bettercap
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./caplets:/usr/share/bettercap/caplets
      - ./logs:/var/log/bettercap
    command: >
      bettercap -caplet https-proxy \
        -eval "set http.proxy.sslstrip true; set http.proxy.script /usr/share/bettercap/caplets/inspect.js"
    restart: unless-stopped
```

### HTTPS Proxy Setup

bettercap's `https-proxy` module handles TLS interception with automatic certificate generation:

```bash
# Start the interactive session
sudo bettercap

# Inside bettercap:
> net.recon on
> set https.proxy.sslstrip true
> set http.proxy.port 8080
> http.proxy on
> https.proxy on
```

### Caplet Automation

Create a caplet file for automated interception:

```javascript
# intercept.caplet
# Enable network discovery
net.recon on

# Configure HTTPS proxy with SSL stripping
set https.proxy.sslstrip true
set http.proxy.port 8080

# Log all intercepted requests
set http.proxy.script log_intercept.js

# Start the proxy
http.proxy on
https.proxy on

# Save session to file
events.stream off
events.stream /var/log/bettercap/session.log
```

Run with:
```bash
sudo bettercap -caplet intercept.caplet
```

## Comparison: Which Tool for Which Scenario?

| Scenario | Recommended Tool | Why |
|---|---|---|
| API debugging and development | mitmproxy | Best HTTP/2 support, Python addons, web UI |
| Intercepting non-HTTP TLS protocols | sslsplit | Protocol-agnostic, works at TCP level |
| Network security assessment | bettercap | Full attack framework, ARP/DNS spoofing built-in |
| Automated testing pipelines | mitmproxy | Scriptable with Python, can run headless |
| Resource-constrained environments | sslsplit | Minimal C binary, no runtime dependencies |
| WiFi/BLE reconnaissance + TLS | bettercap | Multi-protocol support in one tool |
| Traffic replay and analysis | mitmproxy | HAR export/import, flow recording |
| Training and education | bettercap | Visual web UI, guided caplet workflows |

For related reading, see our [Suricata vs Snort vs Zeek IDS/IPS guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) for network-level threat detection, the [BunkerWeb vs ModSecurity vs CrowdSec WAF guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) for web application firewalls, and the [Fail2ban vs SSHGuard vs CrowdSec intrusion prevention guide](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/) for host-level security.

## Installation Comparison Summary

| Method | mitmproxy | sslsplit | bettercap |
|---|---|---|---|
| **Package Manager** | `pip install mitmproxy` | Build from source | Pre-built binary or `go install` |
| **Docker Image** | `mitmproxy/mitmproxy` (official) | Community images only | `bettercap/bettercap` (official) |
| **Network Mode** | Standard port mapping | `host` mode required | `host` mode required |
| **Special Permissions** | None (proxy mode) | `NET_ADMIN` for transparent | `NET_ADMIN`, `NET_RAW` |
| **Cross-Platform** | Linux, macOS, Windows | Linux, BSD | Linux, macOS, Windows |

## Security Considerations

Running a TLS interception tool introduces significant security and legal considerations:

1. **Certificate trust** — The generated CA certificate must be installed on client devices. Anyone with access to this CA key can impersonate any website. Store it securely and restrict access.

2. **Legal compliance** — Intercepting TLS traffic without authorization may violate wiretapping laws in many jurisdictions. Only intercept traffic on networks you own or have explicit permission to test.

3. **Certificate pinning** — Many modern apps (banking, social media) use certificate pinning to detect MITM attacks. These will fail when intercepted unless you bypass the pinning mechanism, which may itself be illegal.

4. **Data handling** — Intercepted traffic may contain sensitive credentials, tokens, and personal data. Ensure captured data is encrypted at rest and deleted when no longer needed.

5. **Network segmentation** — Run interception tools on isolated network segments. Do not place them on production networks where accidental misconfiguration could disrupt legitimate traffic.

## FAQ

### What is the difference between a proxy and transparent interception?

A proxy requires clients to be explicitly configured to route traffic through it (proxy settings in browser or OS). Transparent interception uses network-level redirects (iptables NAT rules) to route traffic through the interception tool without any client configuration. Transparent mode is harder to detect but requires control over the network gateway.

### Can mitmproxy intercept non-HTTP traffic?

mitmproxy is primarily designed for HTTP/HTTPS traffic. It supports HTTP/1, HTTP/2, WebSockets, and gRPC (which runs over HTTP/2). For non-HTTP TLS protocols like SMTP, IMAP, or FTP over TLS, use sslsplit which operates at the raw TCP/TLS layer.

### Is TLS interception legal?

TLS interception is legal only on networks you own or have explicit written authorization to monitor. In most jurisdictions, intercepting communications without consent violates wiretapping and privacy laws. Corporate environments typically have acceptable use policies that cover monitoring — ensure compliance before deploying any interception tool.

### Which tool is best for beginners?

mitmproxy is the most beginner-friendly option. Its web interface (`mitmweb`) provides a visual overview of all intercepted traffic, and the interactive terminal UI (`mitmproxy`) allows step-by-step inspection of requests and responses. The extensive documentation and large community also make it easier to find help.

### Can these tools bypass certificate pinning?

Certificate pinning is specifically designed to prevent MITM attacks, including the interception these tools perform. Some advanced mitmproxy scripts can bypass pinning for mobile apps by hooking into the SSL verification process, but this is technically complex and may have legal implications. sslsplit and bettercap do not have built-in pinning bypass capabilities.

### Do I need to recompile sslsplit for each project?

No. Once compiled, sslsplit is a standalone binary that does not need recompilation. However, you will need to recompile it if you want to update to a newer version or if you're deploying to a different architecture. The compilation process only requires standard C build tools (gcc, make) and OpenSSL development headers.

### How do I install the generated CA certificate on clients?

For **Linux**: Copy the CA cert to `/usr/local/share/ca-certificates/` and run `update-ca-certificates`. For **macOS**: Add the certificate to Keychain Access and set it to "Always Trust" for SSL. For **Windows**: Double-click the certificate file and install it to "Trusted Root Certification Authorities." For **Android/iOS**: Install via a mobile device management (MDM) profile or manually through the device settings.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "mitmproxy vs sslsplit vs bettercap: Self-Hosted TLS Interception Guide 2026",
  "description": "Compare mitmproxy, sslsplit, and bettercap for self-hosted TLS interception and network traffic analysis. Complete setup guide with Docker configs and iptables rules for security testing.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
