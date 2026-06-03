---
title: "Self-Hosted Email Security Gateways: Proxmox Mail Gateway vs Scrollout F1 vs MailScanner"
date: "2026-06-03"
tags: ["email", "security", "spam", "antivirus", "mail-gateway", "postfix", "self-hosted"]
draft: false
---

## Introduction

Email remains the number one attack vector for organizations of all sizes. Phishing, malware attachments, spam, and business email compromise (BEC) attacks all enter through the same channel: inbound SMTP. Placing an email security gateway in front of your mail server adds a critical defense layer that inspects every message before it reaches user inboxes.

An email security gateway sits between the internet and your mail server (typically Postfix, Exim, or Exchange). It accepts all inbound mail, scans it with multiple engines (spam filtering, antivirus, policy checks), and only relays clean messages to your backend mail server. This architecture means malicious content never touches your primary mail infrastructure.

In this guide, we compare three self-hosted email security gateways: **Proxmox Mail Gateway (PMG)**, **Scrollout F1**, and **MailScanner**. Each offers a different balance of ease of deployment, feature depth, and integration flexibility.

## Comparison Table

| Feature | Proxmox Mail Gateway | Scrollout F1 | MailScanner |
|---------|---------------------|--------------|-------------|
| **License** | AGPLv3 | GPLv2 | GPLv2 |
| **Base OS** | Debian (appliance) | Debian/Ubuntu | Linux (Perl-based) |
| **Spam Engine** | SpamAssassin (tuned) | SpamAssassin + custom rules | SpamAssassin |
| **Antivirus** | ClamAV (with SaneSecurity sigs) | ClamAV + optional commercial | ClamAV + 20+ commercial AVs |
| **Web GUI** | Yes (modern, feature-rich) | Yes (lightweight) | Yes (MailWatch plugin) |
| **Rule System** | Full mail processing rules | Yes (What-You-See-Is-What-You-Get) | Custom rulesets (Perl) |
| **Quarantine UI** | Yes (user self-service) | Yes | Yes (MailWatch) |
| **LDAP/AD Integration** | Yes | Yes | Via MailWatch |
| **Clustering** | Yes (multi-node) | No | No |
| **DKIM/DMARC** | Verification built-in | Yes | Via modules |
| **Greylisting** | Yes (built-in) | Yes | Yes |
| **Bayesian Auto-Learning** | Yes | Yes | Yes |
| **GitHub Stars** | ~500+ (PMG code) | ~300+ | ~200+ (MailScanner) |
| **Deployment** | ISO/CT template | Scripted install | Package + manual config |
| **Active Development** | Active (2026) | Moderate (2026) | Low (community-maintained) |

## Proxmox Mail Gateway: Enterprise-Ready Email Security

Proxmox Mail Gateway (PMG) is a Debian-based email security appliance that provides a full-featured, web-managed email filtering solution. PMG is particularly appealing because it's available as an ISO installer, a Proxmox VE container template, or a package install on top of Debian — giving you flexibility in how you deploy it.

PMG's mail processing engine uses a rule-based system that's extremely flexible. Every message passes through a series of configurable "What" objects (matching criteria like sender domain, attachment type, spam score) and "Action" objects (accept, quarantine, block, BCC, notify). You compose these into processing rules that form your security policy.

### Deploying Proxmox Mail Gateway

```bash
# Install PMG on Debian 12
wget https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg -O /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg
echo "deb http://download.proxmox.com/debian/pmg bookworm pmg-no-subscription" > /etc/apt/sources.list.d/pmg.list
apt-get update
apt-get install -y proxmox-mailgateway

# Access web interface at https://<ip>:8006
# Default login: root / pam (configure during install)
```

### PMG Rule Configuration via API

```bash
# Get API ticket
curl -k -X POST https://pmg.local:8006/api2/json/access/ticket   -d 'username=root@pam&password=your_password'

# Create a quarantine rule for high-spam messages
curl -k -X POST https://pmg.local:8006/api2/json/config/ruledb/what   -H 'CSRFPreventionToken: YOUR_TOKEN'   -H 'Cookie: PMGAuthCookie=YOUR_COOKIE'   -d 'name=HighSpam&field=spamlevel&value=5'

# Create corresponding action
curl -k -X POST https://pmg.local:8006/api2/json/config/ruledb/action   -H 'CSRFPreventionToken: YOUR_TOKEN'   -d 'name=Quarantine&action=quarantine'
```

### Docker-Based PMG (Unofficial)

```yaml
version: '3.8'
services:
  pmg:
    image: proxmox-mailgateway:latest
    ports:
      - "25:25"      # SMTP inbound
      - "10025:26"   # SMTP internal
      - "8006:8006"  # Web UI
    environment:
      PMG_HOSTNAME: pmg.yourdomain.com
      PMG_RELAY_HOST: mail.yourdomain.com
      PMG_RELAY_PORT: 25
    volumes:
      - pmg_config:/etc/pmg
      - pmg_spam:/var/lib/pmg
      - pmg_queue:/var/spool/pmg

volumes:
  pmg_config:
  pmg_spam:
  pmg_queue:
```

## Scrollout F1: Lightweight All-in-One Gateway

Scrollout F1 takes a different approach from PMG. It's designed as a lightweight, quick-to-deploy email gateway that bundles everything into a single installation script. Scrollout F1 includes Postfix as its MTA, SpamAssassin for spam detection, ClamAV for antivirus, and a custom web interface for management — all pre-configured with sensible defaults.

What makes Scrollout F1 unique is its "What-You-See-Is-What-You-Get" (WYSIWYG) rule builder. Instead of writing complex SpamAssassin rules or PMG processing rules, you configure filtering policies through a simple web form. For small to medium organizations that don't need the full power of PMG's rule engine, Scrollout F1's simplicity is a major advantage.

### Installing Scrollout F1

```bash
# Download and run the installer
wget https://www.scrolloutf1.com/download/scrolloutf1.tar.gz
tar xzf scrolloutf1.tar.gz
cd scrolloutf1

# The installer will ask a few questions
sudo ./install.sh

# Web interface will be available at https://<ip>:8443
```

Scrollout F1 also supports optional integration with commercial spam and antivirus engines (like ESET, Bitdefender) for organizations that want defense-in-depth beyond open source tools.

## MailScanner: The Veteran Swiss Army Knife

MailScanner has been protecting email servers since 2001 — it's one of the oldest and most battle-tested email security solutions available. Unlike PMG and Scrollout F1, MailScanner is not a complete appliance but a powerful mail filtering framework that integrates with your existing MTA (Postfix, Exim, Sendmail).

MailScanner's standout feature is its support for 20+ commercial antivirus engines simultaneously. You can configure MailScanner to scan every message with ClamAV, Sophos, Bitdefender, Kaspersky, and McAfee — all at once, in sequence. This multi-engine approach catches threats that any single AV might miss. For organizations in regulated industries with strict email security requirements, this is a compelling capability.

### Installing MailScanner with Postfix

```bash
# Install prerequisites
apt-get install -y postfix perl unzip wget

# Download MailScanner
wget https://github.com/MailScanner/v5/releases/download/5.7.4-1/MailScanner-5.7.4-1.deb
dpkg -i MailScanner-5.7.4-1.deb

# Install MailWatch (web frontend)
wget https://github.com/mailwatch/MailWatch/releases/download/v1.2.23/MailWatch-1.2.23.tar.gz
tar xzf MailWatch-1.2.23.tar.gz -C /var/www/html/
cd /var/www/html/mailwatch

# Configure MailWatch
cp conf.php.example conf.php
# Edit conf.php to set database credentials and mail server details

# Configure Postfix to use MailScanner as a content filter
postconf -e "header_checks = regexp:/etc/postfix/header_checks"
echo "/^Received:/ HOLD" >> /etc/postfix/header_checks
postfix reload
```

MailScanner also integrates with the MailWatch web frontend, which provides quarantine management, message search, spam report viewing, and per-user release capabilities — features comparable to PMG's web interface.

## Choosing the Right Email Security Gateway

Your choice depends primarily on your organization's size, technical expertise, and security requirements:

- **Choose Proxmox Mail Gateway** if you want an enterprise-grade appliance with clustering, full API access, and a polished web interface. PMG is the best fit for organizations with dedicated IT staff who want powerful rule-based mail processing. Its clustering capability makes it suitable for multi-site deployments.

- **Choose Scrollout F1** if you need a quick, no-fuss deployment with a simple web interface. It's ideal for small organizations, MSPs managing multiple client domains, or anyone who wants email security without a steep learning curve.

- **Choose MailScanner** if you need multi-engine antivirus scanning (3+ commercial AV engines), are running a high-security environment, or have existing Perl expertise on your team. MailScanner's flexibility is unmatched, but it requires more hands-on configuration than the alternatives.

## Why Self-Host Your Email Security Gateway?

Self-hosting your email security gateway keeps your organization's email content within your control. Cloud-based email security services (Proofpoint, Mimecast, Barracuda ESS) route all your email through their infrastructure. Every message — including confidential business communications, legal documents, and HR correspondence — is processed by a third party. For organizations with data sovereignty requirements or strict compliance frameworks (HIPAA, GDPR, PCI DSS), self-hosting eliminates this concern.

Cost is another significant factor. Cloud email security typically costs $3-15 per user per month. An organization with 200 users pays $600-3,000 monthly — or $7,200-36,000 annually. A self-hosted PMG or Scrollout F1 deployment on a $40/month dedicated server provides equivalent protection for a fraction of the cost. You're trading operational overhead (managing the server) for cost savings and data control.

Self-hosting also allows custom security rules that cloud providers can't offer. You can write processing rules specific to your business — blocking emails with competitor domain names in headers, flagging messages that reference internal project code names, or applying different spam thresholds to different departments. For more on self-hosted email infrastructure, see our [Postfix + Dovecot complete guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/). For spam filtering best practices, check our [SpamAssassin vs Rspamd comparison](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/). For mail quarantine management, see our [email quarantine management guide](../2026-06-01-self-hosted-email-quarantine-management-mailwatch-mailzu-amavisd-guide/).

## FAQ

### Does an email security gateway replace my existing spam filter?

No — an email security gateway complements your existing spam filter by adding a pre-filtering layer. Most organizations run both: the gateway filters the worst threats before they touch the mail server, and the mail server's built-in spam filter (Rspamd, SpamAssassin) handles what remains. This defense-in-depth approach is recommended because no single filter catches everything.

### Can I run an email security gateway in front of Microsoft 365 or Google Workspace?

Yes. Configure your MX records to point to the gateway instead of Microsoft/Google. The gateway scans inbound mail and relays clean messages to your cloud email provider. For outbound mail, you can route through the gateway for DLP (Data Loss Prevention) scanning before delivery. Proxmox Mail Gateway supports this configuration natively with its relay domains feature.

### How much server resources does an email gateway need?

For most organizations: 2-4 vCPUs, 4-8 GB RAM, and 50+ GB storage. SpamAssassin and ClamAV are the primary resource consumers — ClamAV loads virus definitions into RAM (currently ~500 MB) and SpamAssassin's rule processing is CPU-intensive. For MailScanner running 3+ commercial AV engines simultaneously, budget 8-16 GB RAM and 4-8 vCPUs. The storage requirement depends on your quarantine retention policy (30 days is typical).

### What about encrypted email (TLS)?

All three gateways support TLS for both inbound and outbound mail. PMG and Scrollout F1 enable opportunistic TLS by default. You can enforce mandatory TLS for specific domains (e.g., business partners, financial institutions) to prevent downgrade attacks. MailScanner relies on the underlying MTA (Postfix/Exim) for TLS — ensure your MTA is configured with `smtp_tls_security_level = may` or `encrypt`.

### Can I add my own custom spam detection rules?

All three platforms support custom rules. PMG uses its What/Action rule system in the web GUI. Scrollout F1 has a WYSIWYG rule builder plus the ability to add custom SpamAssassin rules. MailScanner supports fully custom Perl-based rulesets, SpamAssassin custom rules, and integration with external scoring engines. For advanced users, MailScanner's Perl API provides the most flexibility — you can write rules that inspect message headers, body content, attachments, and even embedded URLs in real-time.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Security Gateways: Proxmox Mail Gateway vs Scrollout F1 vs MailScanner",
  "description": "Comprehensive comparison of self-hosted email security gateway solutions including Proxmox Mail Gateway, Scrollout F1, and MailScanner. Covers deployment, spam filtering, antivirus integration, and mail processing rule configuration for Postfix and Exim.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
