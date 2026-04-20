---
title: "SimpleLogin vs AnonAddy vs ForwardEmail: Best Self-Hosted Email Alias Services 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete comparison of self-hosted email alias services — SimpleLogin, AnonAddy (addy.io), and ForwardEmail. Docker setup guides, feature breakdowns, and how to protect your real inbox from spam and tracking."
---

Your real email address is the master key to your digital identity. Every time you sign up for a service, newsletter, or free trial, you hand it over — often to companies that sell it to data brokers, track your behavior across the web, or leave it exposed when they suffer a breach. The result: an inbox drowning in spam, targeted phishing attempts, and a permanent trail linking every account back to you.

Email aliasing solves this by creating disposable forwarding addresses that route to your real inbox. Instead of sharing `yourname@gmail.com`, you use `randomalias@yourdomain.com`. If an alias starts receiving spam, you disable it in one click — your real address stays clean and unknown. For a broader look at protecting your communications, see our [privacy stack guide](../privacy-stack-guide/) covering essential self-hosted privacy tools.

Three open-source projects dominate the self-hosted email alias space in 2026: **SimpleLogin**, **AnonAddy (addy.io)**, and **ForwardEmail**. Each takes a different architectural approach and offers distinct trade-offs in complexity, features, and operational overhead. This guide compares them head-to-head and walks you through deploying each one. For those also looking to run a complete self-hosted email server, check out our guide to [email archiving solutions](../self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/).

## Feature Comparison

| Feature | SimpleLogin | AnonAddy (addy.io) | ForwardEmail |
|---------|-------------|---------------------|--------------|
| **Language** | Python | PHP | Node.js (JavaScript) |
| **License** | MIT | MIT | Apache 2.0 |
| **GitHub Stars** | 6,614 | 4,586 | 1,562 |
| **Last Updated** | 2026-04-08 | 2026-04-10 | 2026-04-20 |
| **Best For** | Developer-friendly alias management | Privacy-first email forwarding | Full email service replacement |
| **Docker Support** | ✅ Official images | ✅ Community images | ✅ Official images |
| **Database** | PostgreSQL | MariaDB / MySQL | MongoDB (optional, can use memory) |
| **Catch-all Aliases** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Random Aliases** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Custom Domains** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Email Encryption** | ✅ PGP support | ✅ PGP support | ✅ End-to-end encrypted |
| **API** | ✅ REST API | ✅ REST API | ✅ API |
| **Browser Extension** | ✅ Chrome, Firefox, Safari | ✅ Chrome, Firefox | ❌ No |
| **Mobile App** | ✅ iOS + Android | ❌ Responsive web only | ❌ No |
| **Self-Hosted Difficulty** | Medium (multiple containers) | Medium (Postfix + PHP + DB) | Low (single container for basic use) |
| **SPF/DKIM/DMARC** | ✅ Built-in guidance | ✅ Comprehensive docs | ✅ Built-in |
| **Reply via Alias** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Open Source** | ✅ Yes | ✅ Yes | ✅ Yes |

## Why Self-Host Your Email Alias Service?

Cloud-based alias services exist — SimpleLogin itself was acquired by Proton in 2022 and offers a hosted tier, while AnonAddy runs the free/paid addy.io service. But self-hosting brings compelling advantages:

**Unlimited aliases without quotas.** Hosted services often cap the number of aliases on free or lower-tier plans. Self-hosting removes all limits — create as many aliases as you need for every newsletter, signup, and online purchase.

**Complete data ownership.** Your alias database, forwarding rules, and email metadata never leave your server. No third party can analyze which services you use, correlate your aliases, or hand data to law enforcement without your knowledge.

**Custom domain control.** Point your own domain to the alias service and create addresses like `shop@yourdomain.com`, `bank@yourdomain.com`, or `newsletter@yourdomain.com`. You control the domain lifetime — no dependency on a provider's infrastructure.

**No vendor lock-in.** If a hosted alias service shuts down or changes its pricing model, migrating all your aliases is painful. Self-hosting means you can update, migrate, or replace the software on your own schedule.

**Full email encryption support.** Self-hosted setups let you configure PGP encryption, custom DKIM signing, and TLS policies that hosted services may not support on their free tiers.

## SimpleLogin: The Developer-Friendly Option

[SimpleLogin](https://simplelogin.io) is the most popular open-source email alias service, now maintained by Proton. Written in Python, it provides a polished web interface, browser extensions for all major browsers, and native mobile apps. It is designed to be a drop-in replacement for the hosted SimpleLogin service.

### Architecture

SimpleLogin runs as a multi-container setup: the main Python web application, a PostgreSQL database, and a local Postfix instance for handling email delivery. The separation of concerns makes it horizontally scalable but adds operational complexity.

### Docker Deployment

```yaml
# docker-compose.yml for SimpleLogin
version: "3"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: simplelogin
      POSTGRES_PASSWORD: your-db-password
      POSTGRES_DB: simplelogin
    volumes:
      - sl-db:/var/lib/postgresql/data
    restart: unless-stopped

  app:
    image: simplelogin/app:latest
    environment:
      - DB_URI=postgresql://simplelogin:your-db-password@db:5432/simplelogin
      - FLASK_SECRET=your-secret-key-change-this
      - URL=http://localhost:7777
      - WELCOME_EMAIL=true
      - POSTMASTER=contact@yourdomain.com
      - SUPPORT_EMAIL=support@yourdomain.com
      - ADMIN_EMAIL=admin@yourdomain.com
      - SENDER_DOMAIN=yourdomain.com
    ports:
      - "7777:7777"
    depends_on:
      - db
    restart: unless-stopped

  postfix:
    image: simplelogin/postfix:latest
    environment:
      - RELAYHOST=your-smtp-relay:587
      - RELAYHOST_USERNAME=your-smtp-username
      - RELAYHOST_PASSWORD=your-smtp-password
    network_mode: host
    restart: unless-stopped

volumes:
  sl-db:
```

Key configuration steps after deployment:

1. Set up DNS MX records pointing to your server
2. Configure SPF, DKIM, and DMARC records for your domain
3. Generate DKIM keys using SimpleLogin's built-in commands
4. Set up your SMTP relay for sending emails through the aliases

### Key Strengths

- **Browser extensions** for automatic alias creation when filling signup forms
- **Mobile apps** (iOS and Android) for managing aliases on the go
- **PGP encryption** support for end-to-end encrypted forwarded emails
- **Mailbox feature** — send emails from your alias address (not just receive)
- **OAuth integration** — sign in with Google, Facebook, or Proton accounts

## AnonAddy (addy.io): The Privacy-Focused Option

[AnonAddy](https://anonaddy.com), also known as addy.io, is a PHP-based email alias service with a strong emphasis on privacy and email deliverability. The self-hosting guide is among the most detailed in the open-source alias space, covering everything from server hardening to DANE/DNSSEC configuration.

### Architecture

AnonAddy follows a traditional LAMP-style stack: PHP web application (Laravel framework), MariaDB/MySQL database, Postfix as the MTA, Redis for caching, Nginx as the reverse proxy, and Rspamd for spam filtering. The official self-hosting guide provides step-by-step instructions for each component.

### Server Deployment

AnonAddy's self-hosting is primarily a manual installation rather than Docker-based. Here is the core setup flow:

```bash
# 1. Install dependencies
sudo apt update
sudo apt install postfix nginx mariadb-server redis-server \
  php8.2 php8.2-fpm php8.2-mysql php8.2-redis php8.2-mbstring \
  php8.2-xml php8.2-curl php8.2-zip rspamd

# 2. Configure Postfix as "Internet Site"
sudo dpkg-reconfigure postfix
# System mail name: yourdomain.com

# 3. Clone and install the application
cd /var/www
git clone https://github.com/anonaddy/anonaddy.git
cd anonaddy
composer install --no-dev
cp .env.example .env

# 4. Configure .env with your database, mail, and app settings
# DB_CONNECTION=mysql, DB_HOST=127.0.0.1, DB_DATABASE=anonaddy
# MAIL_FROM_DOMAIN=yourdomain.com
# APP_URL=https://app.yourdomain.com

# 5. Run migrations and generate app key
php artisan key:generate
php artisan migrate --force

# 6. Set up supervisor for queue workers
sudo apt install supervisor
# Create /etc/supervisor/conf.d/anonaddy.conf
# [program:anonaddy-queue]
# command=php /var/www/anonaddy/artisan queue:work --sleep=3 --tries=3
# autostart=true
# autorestart=true
```

### Docker Alternative

While the official docs favor manual installation, community Docker images exist:

```yaml
# docker-compose.yml for AnonAddy (community setup)
version: "3"

services:
  db:
    image: mariadb:11
    environment:
      MYSQL_ROOT_PASSWORD: root-password
      MYSQL_DATABASE: anonaddy
      MYSQL_USER: anonaddy
      MYSQL_PASSWORD: your-db-password
    volumes:
      - aa-db:/var/lib/mysql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  app:
    image: anonaddy/anonaddy:latest
    environment:
      - DB_CONNECTION=mysql
      - DB_HOST=db
      - DB_DATABASE=anonaddy
      - DB_USERNAME=anonaddy
      - DB_PASSWORD=your-db-password
      - REDIS_HOST=redis
      - APP_URL=https://app.yourdomain.com
      - MAIL_FROM_DOMAIN=yourdomain.com
    ports:
      - "8080:80"
    depends_on:
      - db
      - redis
    restart: unless-stopped

volumes:
  aa-db:
```

Note: The Docker approach handles the web application and database, but you still need to configure Postfix and DNS records separately for actual email delivery.

### Key Strengths

- **Wildcard alias support** — any address at any subdomain routes to your inbox
- **Rspamd integration** for automatic spam filtering on forwarded emails
- **Comprehensive self-hosting documentation** covering security hardening
- **DANE/TLSA support** for encrypted email delivery verification
- **Recipient verification** — only forward to verified recipient addresses
- **Unlimited bandwidth** — no caps when self-hosted

## ForwardEmail: The Lightweight Option

[ForwardEmail](https://forwardemail.net) takes a different approach — it is a full-stack email service that includes alias management as one of its features. Built with Node.js, it prioritizes simplicity and can serve as both an alias forwarder and a complete email server replacement.

### Architecture

ForwardEmail is a single Node.js application that handles email reception, forwarding, web interface, and API. It is the most lightweight of the three options and can run with minimal resources.

### Docker Deployment

```yaml
# docker-compose.yml for ForwardEmail
version: "3"

services:
  forwardemail:
    image: forwardemail/forwardemail:latest
    environment:
      - SMTP_PORT=25
      - WEB_PORT=3000
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=your-jwt-secret-change-this
      - REDIS_PASSWORD=your-redis-password
    ports:
      - "25:25"
      - "3000:3000"
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass your-redis-password
    volumes:
      - fe-redis:/data
    restart: unless-stopped

volumes:
  fe-redis:
```

ForwardEmail also supports a simplified mode without Redis for basic setups:

```bash
# Quick start without Docker
npm install -g forward-email
forward-email --port 25 --web-port 3000
```

### Key Strengths

- **Smallest resource footprint** — runs on a $5/month VPS easily
- **Built-in encrypted email storage** — not just forwarding, but full email hosting
- **Simple API** for programmatic alias management
- **No database required** for basic configurations
- **Anti-spam and anti-phishing** filters built in
- **Catch-all forwarding** with regex pattern matching

## Choosing the Right Service

Your choice depends on your priorities:

**Choose SimpleLogin if:** You want the most polished user experience with browser extensions, mobile apps, and a mature ecosystem. The multi-container Docker setup is well-documented, and the Proton backing gives confidence in long-term maintenance. Ideal for users who want a hosted-service-quality experience on their own infrastructure.

**Choose AnonAddy if:** You prioritize privacy and email deliverability. The wildcard alias feature (any address at any subdomain) is unique and powerful. The comprehensive self-hosting guide makes it accessible despite the manual installation process. Best for privacy-conscious users willing to invest time in a thorough setup.

**Choose ForwardEmail if:** You need a lightweight, resource-efficient solution that can grow from simple alias forwarding to full email hosting. The single-container Docker setup is the easiest to deploy. Best for users with limited server resources or those who want both alias management and email storage in one package.

## DNS Configuration (Required for All Three)

Regardless of which service you choose, proper DNS configuration is critical for email delivery. Set up these records on your domain:

```
# MX record — directs incoming mail to your server
MX  @  mail.yourdomain.com  priority: 10

# A record — points mail subdomain to your server IP
A   mail  <your-server-ip>

# SPF record — authorizes your server to send mail
TXT @  "v=spf1 mx ip4:<your-server-ip> ~all"

# DKIM record — signs outgoing emails (service-specific key)
TXT  simplelogin._domainkey  "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ..."

# DMARC record — policy for handling failed authentication
TXT _dmarc  "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com"
```

## Security Best Practices

1. **Use a dedicated server or VPS** — do not run your email alias service on a shared host
2. **Enable TLS for all connections** — use Let's Encrypt certificates for the web interface
3. **Harden your Postfix configuration** — restrict relaying, enable TLS, set up rate limiting
4. **Monitor blacklists** — check your server IP regularly on [multirbl.valli.org](https://multirbl.valli.org/lookup/)
5. **Keep software updated** — email software is a frequent attack target; patch promptly
6. **Set up fail2ban** — protect SSH and web interfaces from brute force attacks
7. **Regular backups** — dump your database and back up DKIM keys to avoid losing access to your aliases

## FAQ

### What is an email alias and why should I use one?

An email alias is an alternative address that forwards emails to your real inbox. For example, `newsletter@yourdomain.com` could forward to `yourname@gmail.com`. Using aliases protects your real email address from spam, data breaches, and tracking. If an alias starts receiving unwanted mail, you can disable it without affecting your primary address.

### Can I reply to emails sent to my alias?

Yes. All three services — SimpleLogin, AnonAddy, and ForwardEmail — support reverse aliasing. When you receive an email at your alias and hit reply, the service rewrites the sender address so your reply appears to come from the alias, not your real email. The recipient never sees your actual address.

### Do I need a dedicated domain name for email aliasing?

Yes. You need a domain you control to set up MX records, SPF/DKIM/DMARC, and receive emails at custom addresses. You cannot use a generic Gmail or Yahoo address as the receiving domain. Domain names cost around $10–15/year from registrars like Namecheap or Cloudflare.

### How difficult is it to self-host an email alias service?

Self-hosting requires a VPS (at least $5/month), a domain name, and basic Linux administration skills. SimpleLogin and ForwardEmail offer Docker-based setups that are relatively straightforward. AnonAddy requires more manual configuration but provides the most comprehensive documentation. Expect 1–3 hours for initial setup depending on your experience level.

### What happens to my aliases if my server goes down?

While your server is offline, incoming emails will bounce or queue at the sending server (depending on their retry policy). Most mail servers retry for 3–5 days before giving up. Once your server is back online, normal forwarding resumes. This is why choosing a reliable VPS provider and setting up monitoring is important.

### Can I migrate from a hosted alias service to self-hosting?

SimpleLogin allows you to export your alias data from the hosted service and import it into your self-hosted instance. AnonAddy supports database-level migration if you export from the hosted addy.io service. ForwardEmail stores alias data in its database or Redis, which you can back up and restore. Migration typically takes 15–30 minutes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SimpleLogin vs AnonAddy vs ForwardEmail: Best Self-Hosted Email Alias Services 2026",
  "description": "Complete comparison of self-hosted email alias services — SimpleLogin, AnonAddy (addy.io), and ForwardEmail. Docker setup guides, feature breakdowns, and how to protect your real inbox from spam and tracking.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
