---
title: "Self-Hosted DKIM Proxy & Signing Gateway: dkimproxy vs OpenDKIM vs Rspamd"
date: "2026-05-14"
tags: ["email", "dkim", "security", "smtp", "self-hosted", "authentication"]
draft: false
---

DomainKeys Identified Mail (DKIM) signing is a critical component of modern email authentication. When your mail server sends outbound messages, each one must carry a cryptographic signature proving it originated from your domain. This guide compares three approaches to deploying DKIM signing as a self-hosted gateway or proxy: **dkimproxy**, **OpenDKIM**, and **Rspamd**. Each handles the signing workflow differently, offering trade-offs in complexity, performance, and integration depth.

## How DKIM Signing Works in a Mail Gateway

DKIM signing happens at a specific point in the outbound mail flow. After your Mail Transfer Agent (MTA) receives a message from a user or application, the DKIM gateway computes a cryptographic hash of selected message headers and body content, then signs that hash with your domain's private key. The signature is inserted as a `DKIM-Signature` header before the message is delivered to the recipient's mail server.

The signing gateway can sit in several positions within your mail infrastructure. It can operate as a transparent SMTP proxy that intercepts and rewrites messages in transit, as a milter (mail filter) plugin loaded directly into your MTA, or as a content filter that receives messages via LMTP or local delivery agent protocols. The architectural choice affects latency, reliability, and operational complexity.

Self-hosting your DKIM signing infrastructure gives you full control over key management, signing policies, and cryptographic parameters. You decide which headers to sign, how often to rotate keys, and what algorithm strength to use. This control is essential for organizations that cannot rely on third-party email services to handle their authentication correctly.

## dkimproxy

dkimproxy is a dedicated DKIM signing and verification proxy written in Perl. It operates as a standalone SMTP proxy that sits between your MTA and the external network, intercepting outbound messages, applying DKIM signatures, and forwarding them to their destination.

The tool separates signing and verification into two distinct processes: `dkimproxy_out` handles outbound signing while `dkimproxy_in` verifies inbound signatures. This separation means you can deploy only the signing component if your inbound verification is handled elsewhere. dkimproxy supports both DomainKeys and DKIM standards, making it compatible with older systems that still rely on the original DomainKeys protocol.

Configuration is file-based, with a signing table that maps sender addresses to signing domains and selector values. Each entry specifies the private key file location, the signing domain, and the selector name used in DNS lookups. The proxy reads these tables at startup and can be configured to reload them on signal.

```bash
# Install dkimproxy on Debian/Ubuntu
apt-get install dkimproxy

# Or from source
cd /opt
wget https://sourceforge.net/projects/dkimproxy/files/dkimproxy/1.4.1/dkimproxy-1.4.1.tar.gz
tar xzf dkimproxy-1.4.1.tar.gz
cd dkimproxy-1.4.1
./configure --prefix=/usr/local/dkimproxy
make && make install
```

The signing table format is straightforward:

```
# /etc/dkimproxy/dkimproxy_out.conf
# Map sender addresses to signing identities
*@example.com    dkim(c=relaxed, a=rsa-sha256, s=mail2026, d=example.com, i=@example.com, key=/etc/dkimproxy/keys/example.com/mail2026.private)
*@news.example.com    dkim(c=relaxed, a=rsa-sha256, s=news2026, d=news.example.com, i=@news.example.com, key=/etc/dkimproxy/keys/news.example.com/news2026.private)

# Listen on port 10027, submit signed mail to port 10028
listen    127.0.0.1:10027
relay     127.0.0.1:10028
```

dkimproxy runs as a lightweight daemon with minimal resource requirements. It handles connection pooling and can process hundreds of messages per second on modest hardware.

## OpenDKIM

OpenDKIM is the most widely deployed DKIM implementation, developed as part of the Trusted Domain Project. It operates primarily as a milter (mail filter) plugin, loading directly into Postfix, Sendmail, or other milter-compatible MTAs. This integration model eliminates the need for a separate proxy process and reduces mail flow latency.

As a milter, OpenDKIM intercepts messages at the SMTP protocol level within the MTA process itself. It can sign outbound messages, verify inbound signatures, and apply domain-level policies based on the results. The milter architecture means OpenDKIM has direct access to the SMTP envelope sender, authentication context, and connection metadata, enabling more sophisticated signing policies than a standalone proxy can offer.

Key management in OpenDKIM is handled through the `opendkim-genkey` utility, which generates key pairs and produces the corresponding DNS TXT record for publication. The KeyTable and SigningTable configuration files map domains to their signing keys, with support for wildcard selectors and per-user signing identities.

```bash
# Install OpenDKIM
apt-get install opendkim opendkim-tools

# Generate a DKIM key pair
opendkim-genkey -t -s mail2026 -d example.com
# Produces mail2026.private (signing key) and mail2026.txt (DNS record)
```

Docker Compose deployment requires running OpenDKIM alongside your MTA with shared key storage:

```yaml
version: '3.8'

services:
  postfix:
    image: linuxserver/mailserver:latest
    ports:
      - "25:25"
      - "587:587"
    volumes:
      - ./postfix-config:/config
      - ./dkim-keys:/etc/opendkim/keys
    environment:
      - TZ=UTC
    depends_on:
      - opendkim
    networks:
      - mail-net

  opendkim:
    image: tvial/docker-opendkim:latest
    volumes:
      - ./dkim-keys:/etc/opendkim/keys
      - ./opendkim.conf:/etc/opendkim.conf
    networks:
      - mail-net
    restart: unless-stopped

networks:
  mail-net:
    driver: bridge
```

OpenDKIM's configuration file controls signing behavior, key selection, and reporting:

```
# /etc/opendkim.conf
Syslog                  yes
SyslogSuccess           yes
LogWhy                  yes
Canonicalization        relaxed/simple
Mode                    sv
SubDomains              no
OversignHeaders         From
SigningTable            refile:/etc/opendkim/SigningTable
KeyTable                /etc/opendkim/KeyTable
InternalHosts           /etc/opendkim/TrustedHosts
Socket                  inet:8891@localhost
```

## Rspamd DKIM Signing

Rspamd is a high-performance spam filtering system that includes built-in DKIM signing capabilities. Unlike dkimproxy (dedicated proxy) and OpenDKIM (milter plugin), Rspamd handles DKIM signing as one feature within a broader email processing pipeline that also includes SPF checking, DMARC validation, Bayes filtering, and fuzzy hash matching.

Rspamd's DKIM signing is configured through its modular architecture. The `dkim_signing` module reads signing rules from the configuration and applies them to outbound messages based on authenticated user identity, envelope sender domain, or explicit header matching. Rspamd can sign messages with multiple keys simultaneously, supporting multi-domain deployments where a single mail server sends on behalf of several domains.

The signing configuration in Rspamd uses a Lua-based syntax that supports conditional logic, regular expression matching, and dynamic selector generation. This flexibility allows administrators to implement complex signing policies, such as using different selectors for marketing mail versus transactional mail from the same domain.

```lua
# /etc/rspamd/local.d/dkim_signing.conf
sign_networks = "/etc/rspamd/dkim/signing_networks.map";

domain {
    example.com {
        path = "/var/lib/rspamd/dkim/example.com.key";
        selector = "mail2026";
    }
    newsletter.example.com {
        path = "/var/lib/rspamd/dkim/newsletter.key";
        selector = "news2026";
        allow_hdrfrom_mismatch = true;
    }
}
```

Docker deployment of Rspamd with DKIM signing:

```yaml
version: '3.8'

services:
  rspamd:
    image: rspamd/rspamd:latest
    ports:
      - "11332:11332"
      - "11334:11334"
    volumes:
      - ./rspamd-config:/etc/rspamd
      - ./dkim-keys:/var/lib/rspamd/dkim
    environment:
      - TZ=UTC
    networks:
      - mail-net
    restart: unless-stopped

networks:
  mail-net:
    driver: bridge
```

## Comparison Table

| Feature | dkimproxy | OpenDKIM | Rspamd DKIM |
|---------|-----------|----------|-------------|
| Architecture | SMTP proxy | Milter plugin | Content filter module |
| Language | Perl | C | C/Lua |
| MTA Integration | SMTP relay port | milter socket | LMTP/SMTP filter |
| DKIM Verification | Yes (separate process) | Yes | Yes (built-in) |
| DomainKeys Support | Yes | No | No |
| Multi-domain Signing | Via signing table | Via KeyTable | Via Lua config |
| Key Rotation | Manual file swap | Manual + opendkim-genkey | Config reload |
| Performance | Moderate (~200 msg/s) | High (~500 msg/s) | Very high (~1000+ msg/s) |
| Resource Usage | Low (~50MB RAM) | Low (~30MB RAM) | Moderate (~200MB RAM) |
| Docker Support | Community images | Official image available | Official image |
| Active Development | Minimal | Active | Very active |
| GitHub Stars | N/A (SourceForge) | N/A | 2,400+ |

## Choosing the Right DKIM Signing Approach

For simple deployments with a single domain and straightforward signing requirements, **dkimproxy** offers the simplest setup. Its proxy architecture means it works with any MTA that can route mail through an SMTP relay, and the configuration format is easy to understand. The trade-off is that development has slowed, and it lacks some modern features like automatic key rotation.

**OpenDKIM** is the best choice when you need tight MTA integration and proven reliability. Its milter architecture eliminates an extra network hop, and it has been the default DKIM implementation for most Linux distributions for over a decade. If your MTA supports milter (Postfix, Sendmail), OpenDKIM is the most operationally mature option.

**Rspamd** is ideal when you want DKIM signing as part of a comprehensive email processing pipeline. If you are already deploying Rspamd for spam filtering, enabling DKIM signing adds minimal overhead while providing a unified configuration interface. Its Lua-based configuration offers the most flexibility for complex multi-domain environments.

## Why Self-Host DKIM Signing?

Running your own DKIM signing infrastructure ensures that every outbound message from your domain carries a valid cryptographic signature. Third-party email services may sign messages on your behalf, but relying on them introduces dependency risk. If the service experiences an outage, changes its signing policy, or discontinues support, your email deliverability suffers immediately.

Self-hosted DKIM signing also gives you complete control over cryptographic parameters. You choose the key size (2048-bit is recommended), the signing algorithm (rsa-sha256), the canonicalization mode, and which headers to include in the signature. This control matters when your organization has specific compliance requirements or when you need to coordinate DKIM key rotation across multiple sending domains.

The operational cost of self-hosted DKIM signing is minimal. All three tools discussed here run on modest hardware with negligible CPU and memory overhead. The primary investment is in initial setup and ongoing key management, tasks that are straightforward with the tools and automation scripts available in each project.

For organizations managing multiple mail servers or sending domains, centralized DKIM signing provides consistent authentication across your entire email infrastructure. Rather than configuring signing on each individual MTA, a dedicated signing gateway ensures uniform policy enforcement and simplifies key rotation procedures.

If you are building a complete self-hosted email server, our [Postfix, Dovecot, and Rspamd guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) covers the full stack configuration. For DKIM signing to work alongside broader email authentication, see our [OpenDKIM vs Rspamd vs OpenDMARC comparison](../2026-05-18-opendkim-vs-rspamd-vs-opendmarc-email-authentication-guide/). Understanding SMTP relay configuration is also important — our [Postal vs Stalwart vs Haraka guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/) covers outbound mail routing.

## FAQ

### What is the difference between a DKIM proxy and a DKIM milter?

A DKIM proxy operates as a separate SMTP server that receives messages, adds signatures, and forwards them on. A DKIM milter is a plugin loaded directly into the MTA process, signing messages without an additional network hop. Proxies work with any MTA but add latency; milters are faster but require MTA support for the milter protocol.

### How often should I rotate DKIM keys?

Best practice is to rotate DKIM keys every 6-12 months. Generate a new key pair, publish the new public key in DNS with a different selector, configure your signing tool to use the new key, and keep the old key in DNS for 30 days to allow in-flight messages to verify.

### Can I sign messages with multiple DKIM keys?

Yes. Rspamd natively supports multi-key signing where a single message carries multiple DKIM-Signature headers. OpenDKIM and dkimproxy sign with one key per message, but you can configure different keys for different sender domains or subdomains.

### What DKIM key size should I use?

2048-bit RSA keys are the current recommended minimum. 1024-bit keys are still functional but considered weak by modern standards. DNS TXT records have a 255-character per-string limit, so 2048-bit public keys must be split across multiple strings in the DNS record.

### Does DKIM signing affect message delivery speed?

The cryptographic signing operation adds minimal latency — typically under 10 milliseconds per message on modern hardware. The bigger performance factor is the architectural choice: milter plugins (OpenDKIM) are fastest, while proxy-based solutions (dkimproxy) add one additional SMTP transaction.

### What happens if my DKIM private key is compromised?

Immediately generate a new key pair and update your DNS records. Revoke the compromised key by removing its DNS TXT record. Messages signed with the compromised key will fail verification once the DNS record is removed. Investigate how the key was exposed and improve access controls.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DKIM Proxy & Signing Gateway: dkimproxy vs OpenDKIM vs Rspamd",
  "description": "Compare three approaches to self-hosted DKIM email signing: dkimproxy SMTP proxy, OpenDKIM milter, and Rspamd module. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
