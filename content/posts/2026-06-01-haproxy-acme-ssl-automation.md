---
title: "Self-Hosted HAProxy SSL/TLS Automation: haproxy-acme vs certbot-haproxy vs acme.sh Guide 2026"
date: "2026-06-01"
tags: ["haproxy", "ssl", "tls", "acme", "lets-encrypt", "reverse-proxy", "automation"]
draft: false
---

HAProxy is one of the most battle-tested reverse proxies and load balancers in the self-hosted world. But managing SSL/TLS certificates manually is a recipe for expired certs and midnight outages. The solution: automate certificate renewal directly with HAProxy. Three tools dominate this space — each with different integration approaches and trade-offs.

## Why Automate HAProxy SSL/TLS Certificates?

Every self-hosted service behind HAProxy needs valid TLS certificates. Without automation, you're stuck with manually renewing certificates every 90 days, restarting HAProxy after each renewal causing brief downtime, risking expired certificates taking your services offline, and having no visibility into certificate expiry status.

Automating this with ACME (Automatic Certificate Management Environment) clients that integrate natively with HAProxy eliminates all of these problems. You get zero-downtime renewals, automatic expiry monitoring, and integration with Let's Encrypt, ZeroSSL, or any ACME-compatible CA.

## Comparison: haproxy-acme vs certbot-haproxy vs acme.sh

| Feature | haproxy-acme | certbot-haproxy | acme.sh + HAProxy |
|---------|-------------|-----------------|-------------------|
| **Language** | Go (single binary) | Python (certbot plugin) | Shell script |
| **Zero-downtime reload** | Yes (hitless reload) | Yes (graceful reload) | Yes (via post-hook) |
| **ACME challenge type** | HTTP-01, TLS-ALPN-01 | HTTP-01, DNS-01 | HTTP-01, DNS-01, TLS-ALPN-01 |
| **Multi-domain certs** | Yes (SAN support) | Yes (SAN support) | Yes (SAN support) |
| **HAProxy integration** | Native (reads HAProxy config) | Plugin-based | External (script hooks) |
| **OCSP stapling** | Auto-configured | Manual config | Manual config |
| **Docker support** | Docker image available | Works in Docker | Works in Docker |
| **Wildcard certs** | Via DNS-01 only | Yes (DNS-01) | Yes (DNS-01) |
| **Stars** | 500+ | N/A (certbot ecosystem) | 10,000+ |

### haproxy-acme: Purpose-Built for HAProxy

haproxy-acme is a Go-based tool built specifically for HAProxy certificate automation. It reads your HAProxy configuration file directly, identifies which domains need certificates, and manages the entire lifecycle — from issuance to renewal to HAProxy reloads.

```bash
# Docker Compose for haproxy-acme
version: "3.8"
services:
  haproxy-acme:
    image: fromnibly/haproxy-acme:latest
    container_name: haproxy-acme
    volumes:
      - ./haproxy.cfg:/etc/haproxy/haproxy.cfg:ro
      - ./certs:/etc/haproxy/certs
      - ./acme:/etc/haproxy-acme
    environment:
      - ACME_EMAIL=admin@example.com
      - ACME_ACCEPT_TOS=true
      - HAPROXY_CONFIG=/etc/haproxy/haproxy.cfg
      - CERT_DIR=/etc/haproxy/certs
    restart: unless-stopped
```

The key advantage of haproxy-acme is its native understanding of HAProxy configuration syntax. It parses your haproxy.cfg, finds all crt directives, and manages certificates only for domains HAProxy actually serves. This eliminates the configuration mismatch that often plagues generic ACME clients.

### certbot-haproxy: The Certbot Plugin Approach

Certbot, the official EFF ACME client, offers a HAProxy plugin that integrates with certbot's standard workflow. It's the most mature option, backed by the Let's Encrypt ecosystem.

```bash
# Install certbot with HAProxy plugin
apt install certbot python3-certbot-haproxy

# Obtain certificate with automatic HAProxy integration
certbot --haproxy -d example.com -d www.example.com

# Auto-renewal with systemd timer (zero-downtime)
certbot renew --haproxy --deploy-hook "systemctl reload haproxy"
```

```yaml
# Docker Compose for certbot + HAProxy
version: "3.8"
services:
  certbot:
    image: certbot/certbot:latest
    container_name: certbot
    volumes:
      - ./certs:/etc/letsencrypt
      - ./haproxy.cfg:/etc/haproxy/haproxy.cfg:ro
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew --haproxy; sleep 12h; done'"
    restart: unless-stopped
```

Certbot's strength is its vast plugin ecosystem and DNS-01 challenge support, making wildcard certificates straightforward. However, the HAProxy plugin is community-maintained and sometimes lags behind HAProxy releases.

### acme.sh + HAProxy: The Scripting Approach

acme.sh is the most popular ACME client by star count. It doesn't have native HAProxy integration, but its flexible hook system makes HAProxy automation simple.

```bash
# Install acme.sh
curl https://get.acme.sh | sh

# Issue certificate with HAProxy deploy hook
acme.sh --issue -d example.com -d www.example.com \
  --webroot /var/www/html \
  --reloadcmd "cat /etc/acme/example.com/fullchain.cer /etc/acme/example.com/example.com.key > /etc/haproxy/certs/example.com.pem && systemctl reload haproxy"
```

```yaml
# Docker Compose with acme.sh and HAProxy
version: "3.8"
services:
  acme-sh:
    image: neilpang/acme.sh:latest
    container_name: acme-sh
    volumes:
      - ./acme:/acme.sh
      - ./certs:/certs
    environment:
      - DEPLOY_HAPROXY_HOT_UPDATE=yes
    command: daemon
    restart: unless-stopped

  haproxy:
    image: haproxy:lts-alpine
    container_name: haproxy
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/usr/local/etc/haproxy/certs
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
```

acme.sh supports 80+ DNS API providers out of the box, making it the best choice if you need wildcard certificates via DNS-01 challenges. The trade-off is that you need to write and maintain the HAProxy integration scripts yourself.

## Deployment Architecture

A typical production setup runs HAProxy as the edge proxy with one of these ACME tools as a sidecar container. HAProxy handles incoming TLS connections on port 443, while the ACME client manages certificate issuance and renewal in the background, communicating with Let's Encrypt or another ACME-compatible certificate authority.

All three tools can operate in Docker alongside HAProxy. The key architectural decision is whether you want the ACME client to parse HAProxy config directly (haproxy-acme), act as a certified plugin (certbot-haproxy), or run independently with hook scripts (acme.sh). Each approach has distinct advantages for different operational styles.

## Why Self-Host Your SSL/TLS Automation?

Running your own SSL/TLS automation gives you complete control over your certificate lifecycle. Unlike managed services such as Cloudflare or AWS ACM, self-hosted solutions let you use any ACME-compatible CA — not just the one your cloud provider supports. You keep private keys on your own infrastructure with no third-party access, and you can customize renewal intervals and notification policies to match your operational needs.

For broader HAProxy management capabilities beyond SSL, see our [HAProxy management APIs guide](../2026-04-24-haproxy-dataplane-api-vs-prometheus-exporter-vs-runtime-api-self-hosted-haproxy-management-guide-2026/). If you're evaluating reverse proxy solutions with built-in SSL management, check our [reverse proxy GUI comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/). And for general ACME client options beyond HAProxy, our [ACME DNS-01 challenge guide](../2026-04-27-certbot-vs-acme-sh-vs-lego-vs-dehydrated-self-hosted-acme-dns-challenge-guide-2026/) covers broader use cases.

In a production self-hosted environment, automated SSL/TLS certificate management is essential — not optional. Manual certificate renewal is error-prone and doesn't scale. With three or more services behind HAProxy, you might have a dozen certificates expiring at different times. Automated ACME integration eliminates certificate outages, reduces operational toil, and ensures your services remain accessible with valid TLS at all times. Combined with monitoring and alerting through Prometheus and Grafana, you get full visibility into certificate health without manual intervention.

## Security Considerations for Automated Certificate Management

When automating SSL/TLS certificates, security deserves careful attention. Your ACME client needs access to HAProxy's certificate directory and the ability to reload HAProxy — both sensitive operations. Follow these best practices to minimize risk.

Run your ACME client as a dedicated non-root user with write access only to the certificate directory, not the HAProxy configuration. Use filesystem permissions to enforce this — the ACME client should only write to /etc/haproxy/certs and never modify haproxy.cfg. For Docker deployments, mount the certs directory as writable but the config as read-only.

Store your ACME account private key securely. This key proves ownership of your domains to the certificate authority. If compromised, an attacker could issue certificates for your domains. Use encrypted volumes or Docker secrets to protect it.

Monitor certificate transparency logs for unexpected certificates issued for your domains. Tools like certspotter and crt.sh let you detect mis-issuance early. Set up alerting so you're notified within minutes of any unexpected certificate appearing for your domains.

## Monitoring SSL Certificate Health in Production

Once your ACME automation is running, the final piece is monitoring. Set up Prometheus metrics collection for certificate expiry dates and renewal success rates. Configure Grafana dashboards showing certificate status across all your domains with color-coded health indicators — green for valid, yellow for expiring within 14 days, red for expired. Add alerting rules that trigger notifications when a certificate is approaching expiry or a renewal attempt fails, giving you time to intervene before services go offline.

## FAQ

### Which ACME client should I choose for HAProxy?

haproxy-acme if you want a purpose-built tool that understands HAProxy config natively. certbot-haproxy if you're already in the certbot ecosystem and want the most battle-tested ACME client. acme.sh if you need the broadest DNS API support and maximum flexibility.

### Can these tools handle wildcard certificates?

Yes, all three support wildcard certificates via DNS-01 challenges. acme.sh has the broadest DNS provider support with 80+ integrations. certbot-haproxy supports DNS-01 via certbot's DNS plugins. haproxy-acme supports DNS-01 with external hook scripts.

### Do I need to restart HAProxy after certificate renewal?

No, all three tools support zero-downtime certificate reloads. HAProxy's hitless reload mechanism allows certificates to be updated without dropping active connections.

### How do I monitor certificate expiry?

All three tools provide expiry checking. haproxy-acme has built-in Prometheus metrics. certbot includes certbot certificates for manual checks and timer-based renewal. acme.sh has acme.sh --list and cron-based renewal notifications. Combine with your existing monitoring stack for alerting.

### What about OCSP stapling?

haproxy-acme auto-configures OCSP stapling in HAProxy. With certbot-haproxy and acme.sh, you'll need to manually add OCSP stapling directives to your HAProxy configuration.

### Can I run these in Docker alongside HAProxy?

Absolutely. All three tools have Docker images and work as sidecar containers. The Docker Compose examples above show production-ready configurations for each tool.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted HAProxy SSL/TLS Automation: haproxy-acme vs certbot-haproxy vs acme.sh Guide 2026",
  "description": "Compare haproxy-acme, certbot-haproxy, and acme.sh for automated SSL/TLS certificate management with HAProxy. Docker Compose examples, zero-downtime renewal, and production deployment patterns.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到加密货币监管，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测科技事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
