---
title: "Self-Hosted Email Autoconfig: Stalwart vs Mail-in-a-Box vs Modoboa Auto-Discovery Guide"
date: "2026-05-10"
tags: ["email", "autoconfig", "autodiscover", "mail-server", "stalwart", "modoboa"]
draft: false
---

Setting up email clients manually is tedious. Users need server addresses, port numbers, security settings, and authentication methods — often making mistakes that result in connection failures. Email autoconfiguration solves this by letting clients like Thunderbird, Outlook, and Apple Mail discover the correct settings automatically.

Three open-source platforms provide built-in autoconfig and autodiscover support: **Stalwart Mail Server**, **Mail-in-a-Box**, and **Modoboa**. Each takes a different approach to automatic email client setup.

## Comparison Table

| Feature | Stalwart Mail Server | Mail-in-a-Box | Modoboa |
|---------|---------------------|---------------|---------|
| GitHub Stars | 12,706+ | 15,290+ | 3,483+ |
| Language | Rust | Python/Shell | Python |
| Thunderbird Autoconfig | ✅ Built-in (XML) | ✅ Built-in | ✅ Built-in |
| Outlook Autodiscover | ✅ Built-in (XML) | ✅ Built-in | ❌ Not supported |
| Apple Mail Config | ✅ Via SRV records | ✅ Via SRV records | ✅ Via SRV records |
| Protocols | IMAP, JMAP, SMTP, CalDAV, CardDAV | IMAP, SMTP, CardDAV, CalDAV | IMAP, SMTP, Webmail |
| MTA | Built-in (Rust) | Postfix | Postfix |
| Webmail | JMAP Web UI | Roundcube | Modoboa Webmail |
| Docker Support | ✅ Official image | ❌ Setup script only | ✅ Docker Compose |
| Multi-domain | ✅ Yes | ❌ Single domain | ✅ Yes |
| JMAP Support | ✅ Full implementation | ❌ No | ❌ No |
| Reverse Proxy | Built-in TLS | Nginx | Nginx |

## How Email Autoconfig Works

Autoconfiguration uses well-known URLs and DNS records to publish email server settings:

- **Thunderbird/Mozilla**: Fetches `autoconfig.yourdomain.com/mail/config-v1.1.xml`
- **Outlook**: Fetches `autodiscover.yourdomain.com/autodiscover/autodiscover.xml`
- **Apple Mail**: Uses DNS SRV records (`_imaps._tcp`, `_submission._tcp`)

All three platforms handle these mechanisms automatically once configured.

## Stalwart Mail Server

Stalwart is a modern, all-in-one mail server written in Rust. It supports the latest JMAP protocol alongside traditional IMAP and SMTP, with built-in autoconfig XML generation.

### Key Features
- **JMAP protocol** — modern JSON-based alternative to IMAP/SMTP
- **Built-in autoconfig** — serves `config-v1.1.xml` at the well-known path automatically
- **Full autodiscover** — Outlook-compatible autodiscover endpoint
- **Multi-tenant** — supports multiple domains with separate configurations

### Docker Compose

```yaml
version: '3.8'
services:
  stalwart:
    image: stalwartlabs/mail-server:latest
    container_name: stalwart-mail
    ports:
      - "25:25"
      - "143:143"
      - "993:993"
      - "587:587"
      - "443:443"
      - "80:80"
    volumes:
      - ./data:/opt/stalwart-mail/data
      - ./config:/opt/stalwart-mail/etc
    environment:
      - SERVER_HOSTNAME=mail.example.com
    restart: unless-stopped
```

Stalwart autoconfigures Thunderbird clients when they connect with an email address `@yourdomain.com` — the server responds with the correct IMAP/SMTP settings automatically.

## Mail-in-a-Box

Mail-in-a-Box is a turnkey mail server solution that configures Postfix, Dovecot, and related services through an automated setup script. It provides Thunderbird autoconfig and Outlook autodiscover out of the box.

### Key Features
- **One-click deployment** — single script sets up the complete mail stack
- **Built-in DNS** — includes NSD for authoritative DNS with SRV records
- **SPF/DKIM/DMARC** — automatic email authentication setup
- **Web admin panel** — manage domains, mailboxes, and aliases

### Installation

```bash
curl -s https://mailinabox.email/setup.sh | sudo bash
```

Mail-in-a-Box creates the necessary autoconfig DNS entries and serves the Thunderbird XML configuration from its built-in Nginx web server. The autodiscover endpoint is also pre-configured for Outlook clients.

## Modoboa

Modoboa is a Python-based mail hosting platform with a web admin panel. It provides Thunderbird autoconfig but lacks Outlook autodiscover support.

### Key Features
- **Web admin panel** — manage domains, accounts, and aliases via browser
- **Autoconfig plugin** — generates Thunderbird-compatible XML configurations
- **Amavis/Rspamd integration** — spam and virus filtering
- **Postfixadmin-compatible** — can replace or integrate with existing setups

### Docker Compose

```yaml
version: '3.8'
services:
  modoboa:
    image: modoboa/modoboa:latest
    container_name: modoboa
    ports:
      - "80:80"
      - "443:443"
      - "25:25"
      - "587:587"
      - "993:993"
    volumes:
      - ./data:/srv
      - ./modoboa:/etc/modoboa
    environment:
      - VIRTUAL_HOST=mail.example.com
    restart: unless-stopped
```

After installation, enable the autoconfig plugin in Modoboa's admin panel. It serves the Thunderbird `config-v1.1.xml` file at `autoconfig.yourdomain.com`.

## DNS Configuration for Autoconfig

For all platforms, configure these DNS records to enable automatic discovery:

```
; Thunderbird Autoconfig
autoconfig  IN  CNAME  mail.yourdomain.com

; Outlook Autodiscover (Stalwart and M-i-a-B only)
autodiscover  IN  CNAME  mail.yourdomain.com

; Apple Mail SRV Records
_imaps._tcp   IN  SRV  0 1 993 mail.yourdomain.com.
_submission._tcp  IN  SRV  0 1 587 mail.yourdomain.com.
```

## Choosing the Right Platform

- **Choose Stalwart** if you want the most modern mail server with JMAP support, built-in autoconfig AND autodiscover, multi-domain capability, and Docker deployment.
- **Choose Mail-in-a-Box** if you want a simple, one-click setup with both Thunderbird and Outlook autoconfiguration — ideal for single-domain personal use.
- **Choose Modoboa** if you need a traditional Postfix-based setup with a polished web admin panel and Thunderbird autoconfig, and don't need Outlook autodiscover support.

## Why Self-Host Email Autoconfig?

Using your own email autoconfig server instead of relying on third-party providers gives you complete control over the email experience. When you self-host, you define the autoconfig XML response — no intermediary can change settings, inject ads, or throttle connections. Users connecting Thunderbird or Outlook to your domain get the exact server parameters you specify, including custom ports, security settings, and authentication methods.

Self-hosting autoconfig also eliminates the risk of provider deprecation. Google, Microsoft, and Yahoo have all changed their autoconfig behavior over the years, sometimes breaking third-party clients. With a self-hosted solution, the configuration endpoint is under your control and won't change without your permission.

For organizations managing multiple domains, Stalwart's multi-tenant autoconfig is particularly valuable. Each domain gets its own autoconfig XML response, so users at `@company-a.com` and `@company-b.com` both get automatic discovery without any manual setup. This is impossible with shared hosting providers that only support a single mail server configuration.

If you're setting up a complete mail server, see our [Postfix vs Exim MTA comparison](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide/) and [SMTP relay guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide/) for transport layer options. For spam filtering, our [Rspamd vs SpamAssassin comparison](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide/) covers content filtering integration.


## Security Considerations for Email Autoconfig

When deploying email autoconfig, security must be a primary concern. The autoconfig XML files and autodiscover endpoints contain sensitive server information including hostnames, port numbers, and security requirements. Exposing these at predictable URLs means anyone who knows your domain can discover your email infrastructure details.

To mitigate this, always serve autoconfig over HTTPS with valid TLS certificates. This prevents network-level eavesdroppers from reading the XML configuration files. Additionally, configure your reverse proxy to only serve autoconfig responses when the `Host` header matches your autoconfig subdomain — this prevents the configuration from being served to requests for unrelated domains on the same server.

For Outlook autodiscover, the XML endpoint is particularly sensitive as it reveals your complete mail server topology. Consider implementing IP-based rate limiting on the autodiscover endpoint to prevent automated scanning. Both Stalwart and Mail-in-a-Box include basic rate limiting; for Modoboa, configure Nginx's `limit_req_zone` directive.

## FAQ

### What is email autoconfig?
Email autoconfig is a mechanism that allows email clients to automatically discover the correct server settings (IMAP/SMTP host, port, security) for a given email domain. Thunderbird uses an XML file served at `autoconfig.yourdomain.com`, while Outlook uses a separate autodiscover endpoint.

### Which email clients support autoconfig?
Mozilla Thunderbird, Outlook 2016+, Apple Mail (via DNS SRV records), and Evolution all support some form of automatic email configuration discovery. Thunderbird's autoconfig is the most widely implemented.

### Does Modoboa support Outlook autodiscover?
No, Modoboa only supports Thunderbird-style autoconfig (`config-v1.1.xml`). If you need Outlook autodiscover, consider Stalwart Mail Server or Mail-in-a-Box, both of which include autodiscover endpoints.

### Can I use autoconfig with custom ports?
Yes. The autoconfig XML file includes port numbers for IMAP and SMTP. You can specify any port (e.g., 993 for IMAPS, 587 for Submission) and the email client will use those values automatically.

### How do I test autoconfig for my domain?
Open `https://autoconfig.yourdomain.com/.well-known/autoconfig/v1.1/config.xml` in a browser, or run `dig autoconfig.yourdomain.com` to verify DNS. In Thunderbird, enter your email address and it should auto-detect the settings.

### Is Stalwart production-ready?
Yes, Stalwart Mail Server is actively maintained with over 12,700 GitHub stars. It supports JMAP, IMAP, SMTP, CalDAV, and CardDAV protocols with full autoconfig and autodiscover support. It's suitable for production use in small to medium deployments.
$jsonld_block


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Autoconfig: Stalwart vs Mail-in-a-Box vs Modoboa Auto-Discovery Guide",
  "description": "Compare Stalwart, Mail-in-a-Box, and Modoboa for self-hosted email autoconfiguration. Learn how each platform handles Thunderbird autoconfig and Outlook autodiscover for automatic email client setup.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
