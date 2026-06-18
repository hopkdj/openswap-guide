---
title: "Self-Hosted Gopher Protocol Servers: Gophernicus vs PyGopherd vs Spacecookie 2026"
date: "2026-06-18"
tags: ["gopher", "retro-computing", "protocol-server", "self-hosted", "gophernicus", "pygopherd", "spacecookie", "smolweb"]
draft: false
---

## Introduction

Before the World Wide Web became ubiquitous, the Gopher protocol was the primary way people navigated and discovered information across the internet. Released in 1991 at the University of Minnesota, Gopher provided a hierarchical, menu-driven interface that was simpler and faster than the early Web. While Gopher's popularity faded as HTTP and HTML took over, a dedicated community of enthusiasts has kept the protocol alive — and a new generation of "smolweb" and "small internet" advocates has embraced Gopher as a lightweight, privacy-respecting alternative to the modern bloated web.

Today, self-hosted Gopher servers let you serve documents, directories, and even dynamic content through a protocol that consumes minimal resources and works beautifully on vintage hardware. This guide compares three actively maintained Gopher server implementations — Gophernicus, PyGopherd, and Spacecookie — covering their features, deployment, and the unique appeal of running your own Gopher hole.

## What Is the Gopher Protocol?

Gopher is a TCP/IP application layer protocol (RFC 1436) designed for distributing, searching, and retrieving documents over the internet. Unlike HTTP, which serves rich, styled web pages, Gopher serves plain text and directory listings through a simple menu system. A Gopher client connects to port 70, sends a selector string, and receives either a directory listing or a document.

Key characteristics of Gopher:
- **Stateless and simple**: Each request is a single line of text followed by a CRLF, and the server closes the connection after responding
- **Hierarchical navigation**: Content is organized in nested menus, similar to a file system browser
- **Minimal bandwidth**: Directory listings and documents are plain text, typically under 1KB per page
- **No tracking, no cookies, no JavaScript**: Complete privacy by design — there's nothing to fingerprint

Modern Gopher servers extend the original protocol with support for virtual hosting (selectors based on hostname), CAPS files (server capability advertisement), and even Gopher+ extensions for richer metadata.

## Comparison Table: Gopher Server Implementations

| Feature | Gophernicus | PyGopherd | Spacecookie |
|---------|------------|-----------|-------------|
| **Language** | C | Python 3 | Haskell |
| **Stars** | 318 | 53 | 46 |
| **Last Updated** | Dec 2025 | Oct 2025 | Apr 2026 |
| **Virtual Hosting** | Yes (hostname-based) | Yes (multi-protocol) | Yes |
| **Gopher+ Support** | Yes | Partial | No |
| **CGI/Dynamic Content** | Yes (native CGI) | Yes (UMI handler) | Yes (Gophermap) |
| **CAPS Support** | Yes | Yes | Yes |
| **Web Proxy** | Built-in HTTP→Gopher | Built-in HTTP/Gopher | None (separate) |
| **IPv6** | Yes | Yes | Yes |
| **Configuration** | /etc/gophernicus/ | Python config file | Haskell config file |
| **Memory Footprint** | ~2MB | ~15MB | ~8MB |

## Gophernicus: The Production-Ready Workhorse

Gophernicus is the most mature and widely deployed Gopher server, written in C for maximum performance and minimal resource usage. Originally developed by Kim Holviala and now maintained as an open-source project, Gophernicus powers many of the active Gopher holes on the internet.

### Key Features

- **Virtual hosting**: Serve multiple Gopher domains from a single IP address, each with its own document root
- **CGI/1.1 support**: Run dynamic Gopher content through standard CGI scripts in any language
- **Built-in HTTP gateway**: Automatically converts Gopher content to HTML for web browsers
- **Access control**: IP-based allow/deny lists, per-directory access controls
- **Gophermap files**: Custom directory listings using gophermap format, supporting inline text and custom selectors
- **Security hardening**: chroot support, privilege dropping, and SELinux policy awareness

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gophernicus:
    image: gophernicus/gophernicus:latest
    container_name: gophernicus
    ports:
      - "70:70"
    volumes:
      - ./gopher-data:/var/gopher
      - ./gophernicus.conf:/etc/gophernicus/gophernicus.conf:ro
    environment:
      - GOPHER_HOSTNAME=gopher.yourdomain.com
      - GOPHER_ADMIN=admin@yourdomain.com
    restart: unless-stopped
```

Basic configuration (`gophernicus.conf`):

```
# Primary gopher hostname
hostname = gopher.yourdomain.com

# Document root
root = /var/gopher

# Enable virtual hosting
vhost = true

# Enable CGI scripts
cgi = true
cgidir = /var/gopher/cgi-bin

# Access control
filter = /var/gopher/gopher.filter

# HTTP gateway
http = true
httpport = 8070
```

## PyGopherd: The Multi-Protocol Python Server

PyGopherd is a Python-based server that speaks multiple protocols including Gopher, Gopher+, HTTP, and WAP (Wireless Application Protocol). It's ideal for hobbyists who want a single server process handling multiple retro and modern protocols simultaneously.

### Key Features

- **Multi-protocol**: Simultaneously serves Gopher, Gopher+, HTTP, and WAP from the same document tree
- **UMI (Universal Molecule Interface) handlers**: Extensible handler system for dynamic content generation — write Python modules that respond to Gopher selectors
- **Buck-tooth compatibility**: Full compatibility with the Buck-tooth gopher server ecosystem
- **Virtual folders**: Create logical directory structures that don't exist on the filesystem
- **Python extensibility**: Easily add custom handlers, filters, and authentication hooks

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  pygopherd:
    image: python:3.11-slim
    container_name: pygopherd
    ports:
      - "70:70"
      - "8070:8070"
    volumes:
      - ./gopher-data:/var/gopher
      - ./pygopherd.conf:/etc/pygopherd.conf:ro
    command: >
      sh -c "pip install pygopherd && pygopherd /etc/pygopherd.conf"
    restart: unless-stopped
```

Example `pygopherd.conf`:

```ini
[server]
protocols = gopher, gopherplus, http
port = 70
httpport = 8070
root = /var/gopher
hostname = gopher.yourdomain.com
pidfile = /var/run/pygopherd.pid

[gopherplus]
enabled = true

[http]
enabled = true
```

## Spacecookie: The Modern Haskell Gopher Server

Spacecookie is a modern Gopher server written in Haskell that emphasizes correctness, type safety, and a clean configuration model. It's the newest of the three and brings functional programming rigor to the Gopher ecosystem.

### Key Features

- **Type-safe configuration**: Haskell's type system catches configuration errors at compile time
- **Gophermap support**: Full-featured gophermap parser with support for dynamic menus
- **Systemd integration**: Native socket activation and journal logging
- **Reloadable configuration**: Change settings without restarting the server
- **Clean codebase**: Under 2000 lines of well-documented Haskell, making it ideal for customization

### Nix/Docker Deployment

Spacecookie is available via Nix packages, but can also be run in Docker:

```yaml
version: "3.8"
services:
  spacecookie:
    image: haskell:9.4-slim
    container_name: spacecookie
    ports:
      - "70:70"
    volumes:
      - ./gopher-data:/var/gopher
      - ./spacecookie.json:/etc/spacecookie.json:ro
    command: >
      sh -c "cabal update && cabal install spacecookie && spacecookie /etc/spacecookie.json"
    restart: unless-stopped
```

Configuration (`spacecookie.json`):

```json
{
  "serverName": "gopher.yourdomain.com",
  "serverPort": 70,
  "runUserName": "nobody",
  "rootDirectory": "/var/gopher",
  "logConfig": {
    "enable": true,
    "logDir": "/var/log/spacecookie"
  }
}
```

## Setting Up Your First Gopher Hole

Creating Gopher content is refreshingly simple — no HTML, CSS, or JavaScript required. Directory listings and documents are plain text formatted as Gophermaps:

```
Welcome to my Gopher hole!
1About This Server    /about.txt    gopher.yourdomain.com    70
1My Projects          /projects     gopher.yourdomain.com    70
1Daily Log            /phlog        gopher.yourdomain.com    70
1Links & Resources    /links.txt    gopher.yourdomain.com    70
.

iThis is an informational line (not a link)   null.host    1
i============================================   null.host    1
iLast updated: June 2026   null.host    1
.
```

Each line follows the format: `TypeDescription[TAB]Selector[TAB]Host[TAB]Port` where:
- Type `1` = Directory, `0` = Text file, `i` = Informational (non-link)
- The period (`.`) on a line by itself marks the end of the menu

## Why Self-Host a Gopher Server?

**Preserving Internet History**: Running a Gopher server is like operating a living museum of internet technology. You're keeping an important protocol alive and accessible for future generations to study and enjoy. The Gopher protocol represents a design philosophy of simplicity and accessibility that's increasingly relevant as the modern web grows ever more complex.

**Privacy by Design**: Gopher has no mechanism for cookies, tracking scripts, browser fingerprinting, or user analytics. Every visitor to your Gopher hole is completely anonymous. In an era of pervasive surveillance capitalism, serving content through a protocol that literally cannot track users is a powerful statement. See our guide on [privacy-focused DNS alternatives](../2026-04-10-self-hosted-dns-privacy-doh-dot-dnscrypt-guide/) for complementary privacy infrastructure.

**Minimal System Requirements**: A Gopher server serving thousands of documents can run comfortably on a Raspberry Pi Zero with 512MB of RAM. Gophernicus uses approximately 2MB of memory at idle — compare that to a typical Apache or Nginx instance serving similar content at 50-100MB. For resource-constrained environments or homelab setups, Gopher is the ultimate lightweight content server. Our [lightweight web server comparison](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/) explores similar efficiency-focused alternatives.

**Creative Expression**: The constraints of the Gopher format — plain text, no images, no styling — force content creators to focus on substance over style. The "phlog" (Gopher blog) community has produced some of the most thoughtful long-form writing on the internet precisely because there's nothing to distract from the words. If you enjoy our [self-hosted blogging platform comparison](../writefreely-self-hosted-blogging-platform-guide/), you'll appreciate the creative discipline Gopher imposes.

## FAQ

### What client do I need to access Gopher sites?

You have several options. **Command-line**: `lynx gopher://gopher.yourdomain.com` (Lynx has native Gopher support). **Desktop**: Lagrange (a beautiful GUI Gemini/Gopher browser available on all platforms). **Mobile**: Buran (Android) and Elaho (iOS). **Web proxy**: Many Gopher servers include built-in HTTP gateways, and public proxies like Floodgap (gopher.floodgap.com) let you browse Gopherspace through any web browser.

### Can Gopher servers handle modern traffic loads?

Yes — more easily than HTTP servers, in fact. Because Gopher serves plain text and uses a simple request-response model with no persistent connections, a single Gophernicus instance on modest hardware can handle thousands of concurrent requests. The protocol overhead is approximately 50 bytes per request, compared to HTTP/1.1's typical 500-800 bytes of headers alone.

### Is Gopher secure for serving content?

Gopher has no built-in encryption (TLS was added to HTTP years after Gopher's peak). However, you can run Gopher through an TLS-terminating proxy like stunnel or HAProxy for transport security. Many modern Gopher clients support "Gophers" (Gopher over TLS) on port 7444, though this is not standardized. For sensitive content, consider serving it over our recommended [TLS termination proxy setup](../self-hosted-tls-termination-proxy-traefik-caddy-haproxy-guide-2026/).

### How do I make my Gopher hole discoverable?

Register with **Veronica-2** (the Gopherspace search engine at gopher.floodgap.com) and submit your hole to the **Gopher Lawn** directory. Add a `CAPS.txt` file at your server root describing your hole's capabilities and topics. Many Gopher users also cross-post phlog entries to the Gopher subreddit and the #gopher channel on Libera.Chat IRC.

### What's the difference between Gopher and Gemini?

Gemini is a newer protocol (launched 2019) inspired by Gopher but with mandatory TLS, a richer text format (gemtext), and explicit status codes. Gopher is simpler, has a larger existing ecosystem, and works with any text-mode client. Gemini adds security and formatting at the cost of some of Gopher's elegant simplicity. Many servers now support both protocols.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Gopher Protocol Servers: Gophernicus vs PyGopherd vs Spacecookie 2026",
  "description": "Comprehensive comparison of self-hosted Gopher protocol servers — Gophernicus (C), PyGopherd (Python), and Spacecookie (Haskell). Includes Docker Compose deployment configs, gophermap examples, and setup guide for running your own Gopher hole on minimal hardware.",
  "datePublished": "2026-06-18",
  "dateModified": "2026-06-18",
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
