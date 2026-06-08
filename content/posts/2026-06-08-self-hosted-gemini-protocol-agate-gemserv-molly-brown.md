---
title: "Self-Hosted Gemini Protocol Ecosystem: Agate vs Gemserv vs Molly-Brown Server Comparison"
date: "2026-06-08"
tags: ["gemini-protocol", "lightweight-web", "smol-internet", "self-hosted-server", "alternative-protocols", "privacy"]
draft: false
---

## Introduction

The Gemini protocol is a lightweight, privacy-respecting alternative to HTTP and the modern web. Designed as part of the "smol internet" movement, Gemini intentionally omits client-side scripting, complex styling, and tracking mechanisms — delivering text-focused content over a simple request-response protocol with mandatory TLS encryption.

Since its introduction in 2019, a growing ecosystem of Gemini servers, clients, and tools has emerged. This article compares three popular self-hosted Gemini servers: **Agate** (a fast Rust implementation), **Gemserv** (a feature-rich Rust server), and **Molly-Brown** (a Go-based server with a focus on extensibility). Whether you're looking to host a personal capsule (Gemini's equivalent of a website) or run a community Gemini portal, this guide covers the options.

## Comparison Table

| Feature | Agate | Gemserv | Molly-Brown |
|---------|-------|---------|-------------|
| **Stars** | 741 | 90+ | 115+ |
| **Language** | Rust | Rust | Go |
| **Virtual Hosting** | Yes (vhosts) | Yes | Yes |
| **CGI Support** | No | Yes | Yes |
| **SCGI/FastCGI** | No | Yes | No |
| **User Directories** | Yes (~user) | Yes | Yes |
| **Directory Listing** | Yes | Yes | Yes |
| **MIME Type Config** | Yes | Yes | Yes |
| **Redirect Support** | Temporary only | Full (30/31) | Yes |
| **Reverse Proxy** | No | Yes | No |
| **Access Logging** | Yes | Yes | Yes |
| **Client Cert Auth** | Yes | Yes | Yes |
| **Docker Support** | Community images | Manual | Community images |
| **Last Updated** | 2026 (active) | 2025 | 2025 |

## Self-Hosted Gemini Servers

### 1. Agate

Agate is the most popular Gemini server, written in Rust with a focus on simplicity, security, and performance. It's designed to serve static files with minimal configuration — you can have a Gemini capsule running in under a minute.

Installation and deployment:

```bash
# Install via cargo
cargo install agate

# Or download pre-built binary from GitHub releases
# https://github.com/mbrubeck/agate/releases

# Generate TLS certificate (required for Gemini)
openssl req -x509 -newkey rsa:4096 -keyout key.rsa -out cert.pem \
  -days 3650 -nodes -subj "/CN=gemini.yourdomain.com"

# Run agate
agate --content /var/gemini/content \
      --cert cert.pem \
      --key key.rsa \
      --hostname gemini.yourdomain.com \
      --addr [::]:1965

# Docker deployment
docker run -d \
  --name agate \
  -v /var/gemini/content:/content \
  -v /var/gemini/certs:/certs \
  -p 1965:1965 \
  ghcr.io/mbrubeck/agate:latest \
  --content /content \
  --cert /certs/cert.pem \
  --key /certs/key.rsa
```

Content in Agate is simple — just create `.gmi` (Gemtext) files in the content directory:

```text
# Welcome to My Gemini Capsule

Hello, Gemini space! This is a lightweight hypertext page.

=> /about.gmi About Me
=> /projects/ My Projects
=> gemini://example.com/ A Fellow Capsule

* Bullet points
* Are easy

> Blockquotes work too

```preformatted code```
```

### 2. Gemserv

Gemserv offers more advanced features than Agate, including CGI and SCGI support for dynamic content generation. If you want to build interactive Gemini applications (like guestbooks, search engines, or simple web apps on Gemini), Gemserv's CGI capabilities make it the best choice.

```bash
# Install Gemserv
git clone https://git.sr.ht/~int80h/gemserv
cd gemserv
cargo build --release

# Configuration file (gemserv.toml)
cat > gemserv.toml << 'EOF'
host = "gemini.yourdomain.com"
port = 1965
cert_chain = "/etc/gemserv/cert.pem"
key_file = "/etc/gemserv/key.rsa"
root = "/var/gemini"

[users]
enabled = true

[cgi]
enabled = true
path = "/cgi-bin/"
EOF

# Run with config
./target/release/gemserv -c gemserv.toml
```

With CGI support, you can create dynamic Gemini pages:

```bash
#!/bin/bash
# /var/gemini/cgi-bin/time.sh — displays current time on Gemini
echo "20 text/gemini"
echo ""
echo "# Current Server Time"
echo ""
echo "The current time is: $(date)"
echo ""
echo "=> / Back to homepage"
```

### 3. Molly-Brown

Molly-Brown is a Go-based Gemini server with an emphasis on extensibility through its configuration file and support for custom access controls. It's a solid middle-ground between Agate's minimalism and Gemserv's feature set.

```bash
# Install Molly-Brown
go install tildegit.org/solderpunk/molly-brown@latest

# Configuration file (molly.conf)
cat > molly.conf << 'EOF'
Port = 1965
Hostname = "gemini.yourdomain.com"
CertPath = "/etc/molly/cert.pem"
KeyPath = "/etc/molly/key.rsa"
DocBase = "/var/gemini"
HomeDocBase = "users"
GeminiExt = "gmi"
DefaultLang = "en"
AccessLog = "/var/log/molly/access.log"
ErrorLog = "/var/log/molly/error.log"

[DirectoryListing]
Enabled = true
SortBy = "Name"

[CGIPaths]
"/cgi-bin/" = "/var/gemini/cgi-bin/"

[MimeOverrides]
"xml" = "text/xml"
"svg" = "image/svg+xml"
EOF

# Run Molly-Brown
molly-brown -c molly.conf
```

## Why Self-Host a Gemini Capsule?

**Take Back Your Web Presence.** The Gemini protocol strips away the surveillance capitalism that defines the modern web — no ad trackers, no cookie consent banners, no JavaScript bloat. Running your own Gemini server gives you a platform for publishing that respects both your readers' privacy and your own autonomy. For complementary content management options, see our [static site generator guide](../self-hosted-static-site-generators-hugo-jekyll-astro-eleventy-guide/).

**Negligible Resource Requirements.** A Gemini server typically uses less than 50MB of RAM and negligible CPU. You can run it alongside other services on a $5/month VPS without any performance impact — the protocol was designed to be lightweight by nature. Combined with [self-hosted DNS](../2026-04-10-self-hosted-dns-privacy-doh-dot-dnscrypt-guide/), you can build a completely independent publishing stack.

**Part of the Smol Internet Movement.** Hosting a Gemini capsule connects you to a growing community of creators who value simplicity over complexity. The protocol's constraints — no inlining of images, no client-side scripting, plain text with minimal formatting — encourage thoughtful writing and intentional design. For real-time communication alongside your capsule, consider a [self-hosted IRC server and bouncer](../self-hosted-irc-server-bouncer-web-client-the-lounge-znc-ergo-guide-2026/).

## Deployment Architecture and Production Considerations

When deploying a Gemini server for production use, several architectural decisions affect reliability and maintenance. Gemini's simplicity means most deployment concerns are about the surrounding infrastructure rather than the server itself.

**Reverse Proxy and TLS Termination.** While Gemini servers handle TLS natively, you may want a TCP-level load balancer like HAProxy in front of multiple Gemini backend instances for high availability. Gemini uses port 1965 by default, and most cloud load balancers can forward raw TCP traffic to this port. For those already running a reverse proxy for HTTP services, consider using a dedicated small instance for Gemini since the resource requirements are minimal.

**Content Generation Workflows.** Many Gemini capsule maintainers write content in Gemtext (`.gmi` files) directly, but you can automate content generation from Markdown using converters like `md2gemini` or `gmi-web`. Set up a Git-based workflow where pushing to your capsule's repository triggers a build step that converts Markdown to Gemtext and syncs it to your server. This mirrors the static site generator workflow many web developers already use.

**Certificate Management and TOFU.** Since Gemini relies on self-signed certificates with TOFU (Trust On First Use), changing your certificate breaks all existing client trust relationships. Plan your certificate lifecycle carefully — generate certificates with long validity periods (1-5 years), and if you must change certificates, announce the change in advance on your capsule so users expect the TOFU warning. Consider using a configuration management tool to rotate certificates gracefully.

**Monitoring and Analytics.** Gemini intentionally lacks request headers that enable traditional web analytics. You can track basic access patterns through server logs, but user-agent and referrer data is absent by design. Tools like `glog` and `geminispacemonitor` provide Gemini-specific analytics that respect the protocol's privacy constraints. Set up log rotation and basic alerting if your capsule serves as critical infrastructure.

**Content Discovery and Federation.** Getting discovered in Gemini space requires active participation. Register with Gemini search engines (GUS, Kennedy), submit to aggregators (CAPCOM, Antenna), and cross-link with other capsules. The Gemini community values reciprocal linking — when you link to someone's capsule, they often link back, creating a decentralized discovery network that replaces algorithmic recommendation systems.

## FAQ

### Why would anyone use Gemini instead of HTTP/HTTPS?

Gemini intentionally rejects the complexity of the modern web. There's no JavaScript, no CSS, no cookies, and no tracking. Every request is a simple URL fetch with mandatory TLS. This makes Gemini pages fast, secure, and privacy-respecting by design. It's ideal for text-focused content where formatting beyond basic typography isn't needed.

### Do I need a special browser to access Gemini content?

Yes. Standard web browsers don't speak the Gemini protocol. Popular Gemini clients include Lagrange (GUI, cross-platform), Amfora (terminal), Ariane (Android), and Elaho (iOS). Many Gemini servers also support optional HTTP proxies that make content accessible via web browsers for convenience.

### How does Gemini handle TLS certificates?

Gemini mandates TLS for all connections. Unlike HTTPS, Gemini uses TOFU (Trust On First Use) — clients accept the server's self-signed certificate on first connection and warn if it changes later. This eliminates the need for certificate authorities while providing encryption. Self-signed certificates are the norm in Gemini space.

### Can I host dynamic content on Gemini?

Yes, using CGI or SCGI. Gemserv fully supports CGI scripts, allowing you to build interactive applications like guestbooks, search tools, or simple forms. Gemserv's SCGI support enables persistent backend processes for higher-performance dynamic content.

### How do I get traffic to my Gemini capsule?

The Gemini community maintains several search engines and aggregators: GUS (Gemini Universal Search), Kennedy, and CAPCOM (a monthly capsule aggregator). Submit your capsule URL to these services, and share your content on Gemini-focused forums and mailing lists. Cross-posting links from your web presence also helps.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Gemini Protocol Ecosystem: Agate vs Gemserv vs Molly-Brown Server Comparison",
  "description": "Compare three self-hosted Gemini protocol servers — Agate, Gemserv, and Molly-Brown — for hosting lightweight, privacy-respecting capsules on the smol internet.",
  "datePublished": "2026-06-08",
  "dateModified": "2026-06-08",
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
