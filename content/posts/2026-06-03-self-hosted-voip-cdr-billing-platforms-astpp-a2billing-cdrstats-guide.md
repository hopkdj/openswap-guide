---
title: "Self-Hosted VoIP CDR Analysis & Billing Platforms: ASTPP vs A2Billing vs CDR-Stats"
date: "2026-06-03"
tags: ["voip", "billing", "asterisk", "cdr", "telecom", "freepbx", "analytics"]
draft: false
---

## Introduction

If you run a self-hosted VoIP platform — whether it's Asterisk, FreeSWITCH, Kamailio, or a turnkey PBX — you generate Call Detail Records (CDRs) for every call. These records contain caller/callee numbers, duration, cost, route, and quality metrics. Without a proper CDR analysis and billing platform, you're sitting on a goldmine of operational data with no way to monetize it.

VoIP billing platforms transform raw CDRs into invoices, rate sheets, and profitability reports. They handle rate card management, customer billing, payment tracking, and real-time call cost calculation. For service providers, MSPs, and multi-tenant PBX deployments, a CDR/billing system is not optional — it's the revenue engine.

In this guide, we compare four self-hosted VoIP CDR analysis and billing platforms: **ASTPP**, **A2Billing**, **CDR-Stats**, and **MagnaBilling**. We'll cover deployment, features, and integration with common VoIP backends.

## Comparison Table

| Feature | ASTPP | A2Billing | CDR-Stats | MagnaBilling |
|---------|-------|-----------|-----------|--------------|
| **License** | GPLv3 | AGPLv3 | MPL 2.0 | Proprietary (free tier) |
| **Language** | PHP (Laravel) | PHP | Python (Django) | PHP |
| **Database** | MariaDB/MySQL | MariaDB/MySQL | PostgreSQL/MySQL | MariaDB |
| **Rate Card Management** | Yes (multi-tier) | Yes (LCR-based) | No (analytics only) | Yes (multi-currency) |
| **Customer Billing** | Yes (invoices, PDF) | Yes (invoices, PDF) | No | Yes (invoices, receipts) |
| **Payment Gateways** | PayPal, Stripe, Authorize.net | PayPal, Moneybookers | N/A | PayPal, Stripe, MercadoPago |
| **Multi-Tenant** | Yes | Yes | Yes (read-only) | Yes |
| **Real-Time Rating** | Yes | Yes | No | Yes |
| **DID Management** | Yes | Yes | No | Yes |
| **API** | REST API | XML-RPC/JSON | REST API | REST API |
| **Web Interface** | Modern Bootstrap 5 | Classic Bootstrap 3 | Clean Django Admin | Modern AdminLTE |
| **GitHub Stars** | ~450+ | ~800+ | ~220+ | N/A (proprietary) |
| **Active Development** | Active (2026) | Low activity | Moderate (2026) | Active (2026) |

## ASTPP: Modern Open Source VoIP Billing

ASTPP (ASTerisk PrePaid/PostPaid) is a Laravel-based VoIP billing platform that has evolved significantly since its version 4 rewrite. It supports both prepaid and postpaid billing models, making it suitable for calling card operations, residential VoIP, and wholesale termination.

ASTPP's modular architecture separates billing, rate management, and reporting into distinct components. The platform uses Laravel's queue system (Redis-backed) for processing CDRs asynchronously, which means your billing doesn't block call processing.

### Deploying ASTPP with Docker

```yaml
version: '3.8'
services:
  astpp-db:
    image: mariadb:10.6
    environment:
      MYSQL_ROOT_PASSWORD: astpp_secret
      MYSQL_DATABASE: astpp
      MYSQL_USER: astpp
      MYSQL_PASSWORD: astpp_pass
    volumes:
      - db_data:/var/lib/mysql

  astpp-redis:
    image: redis:7-alpine

  astpp-web:
    image: astpp/astpp:latest
    ports:
      - "8080:80"
    environment:
      DB_HOST: astpp-db
      DB_DATABASE: astpp
      DB_USERNAME: astpp
      DB_PASSWORD: astpp_pass
      REDIS_HOST: astpp-redis
    depends_on:
      - astpp-db
      - astpp-redis
    volumes:
      - astpp_media:/var/www/astpp/storage
      - ./cdr_import:/var/spool/asterisk/cdr-csv

volumes:
  db_data:
  astpp_media:
```

After deployment, configure your Asterisk server to write CDRs to a CSV file that ASTPP can import. ASTPP includes a CDR import daemon that processes new records every 60 seconds.

### Configuring Asterisk CDR Export

```ini
; /etc/asterisk/cdr.conf
[general]
enable=yes

[csv]
usegmtime=yes
loguniqueid=yes
loguserfield=yes
accountlogs=yes
newcdrcolumns=yes
```

## A2Billing: The Veteran VoIP Billing Platform

A2Billing has been the go-to open source VoIP billing solution for over a decade. Originally designed for Asterisk-based calling card platforms, it has expanded to support SIP trunking, DID management, and wholesale termination billing.

A2Billing's strength lies in its Least Cost Routing (LCR) engine. You define rate cards for multiple providers, and A2Billing automatically routes calls through the cheapest available provider. This is critical for wholesale termination businesses where margin optimization directly impacts profitability.

### Deploying A2Billing

```bash
# Install prerequisites
apt-get install -y apache2 mariadb-server php php-mysql php-xml php-mbstring php-curl

# Clone repository
git clone https://github.com/Star2Billing/a2billing.git /var/www/html/a2billing

# Create database
mysql -u root -p -e "CREATE DATABASE a2billing;"
mysql -u root -p -e "CREATE USER 'a2billing'@'localhost' IDENTIFIED BY 'secret';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON a2billing.* TO 'a2billing'@'localhost';"

# Import schema
mysql -u a2billing -p a2billing < /var/www/html/a2billing/DataBase/mysql-5.x/a2billing-schema.sql
```

### Integrating A2Billing with Asterisk

```ini
; /etc/asterisk/extensions.conf
[a2billing]
exten => _X.,1,NoOp(Calling A2Billing for ${EXTEN})
exten => _X.,n,AGI(a2billing.php,${EXTEN})
exten => _X.,n,Hangup()
```

## CDR-Stats: Analytics-Focused CDR Platform

CDR-Stats takes a different approach — it's not a billing platform but a CDR analytics and fraud detection engine. Built with Django, it ingests CDRs from multiple sources (Asterisk, FreeSWITCH, Kamailio) and provides real-time dashboards, alerting, and call quality metrics.

CDR-Stats shines when you need to answer questions like: "Which routes have the highest ASR (Answer-Seizure Ratio)?" or "Are we seeing unusual call patterns that indicate toll fraud?" It includes built-in alerting that can send notifications via email or webhook when predefined thresholds are crossed.

### Deploying CDR-Stats with Docker Compose

```yaml
version: '3.8'
services:
  cdrstats-db:
    image: postgres:15
    environment:
      POSTGRES_DB: cdrstats
      POSTGRES_USER: cdrstats
      POSTGRES_PASSWORD: cdrstats_pass
    volumes:
      - pg_data:/var/lib/postgresql/data

  cdrstats-redis:
    image: redis:7-alpine

  cdrstats-web:
    image: areski/cdr-stats:latest
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://cdrstats:cdrstats_pass@cdrstats-db/cdrstats
      REDIS_URL: redis://cdrstats-redis:6379/0
      SECRET_KEY: your-secret-key-here
    depends_on:
      - cdrstats-db
      - cdrstats-redis

  cdrstats-celery:
    image: areski/cdr-stats:latest
    command: celery -A cdr_stats worker -l info
    environment:
      DATABASE_URL: postgres://cdrstats:cdrstats_pass@cdrstats-db/cdrstats
      REDIS_URL: redis://cdrstats-redis:6379/0
    depends_on:
      - cdrstats-db
      - cdrstats-redis

volumes:
  pg_data:
```

## MagnaBilling: Feature-Rich Proprietary Option

MagnaBilling is a proprietary VoIP billing platform with a free community tier that supports up to 50 extensions. It offers a polished web interface, multi-currency billing, integrated payment gateways, and advanced reporting. The platform supports both Asterisk and FreeSWITCH backends.

MagnaBilling's standout feature is its real-time call rating engine. Unlike batch-processing systems that update balances after the call ends, MagnaBilling can terminate calls mid-session when a prepaid balance reaches zero — critical for calling card and PIN-based services.

## Choosing the Right CDR Platform

The choice between these platforms depends on your business model:

- **Choose ASTPP** if you need a modern, actively developed billing platform with REST API support and containerized deployment. It's the best fit for new deployments and service providers who want a clean codebase.

- **Choose A2Billing** if you need battle-tested LCR-based routing with extensive rate card management. It's ideal for wholesale termination businesses where margin optimization is the primary concern.

- **Choose CDR-Stats** if you primarily need analytics, fraud detection, and quality monitoring rather than billing. It complements billing platforms like ASTPP or A2Billing.

- **Choose MagnaBilling** if you want a polished, all-in-one solution with integrated payment processing and are comfortable with a proprietary license for the premium tier.

For service providers running both billing and analytics, a common pattern is to deploy A2Billing or ASTPP for billing alongside CDR-Stats for real-time monitoring and fraud detection. The two systems can coexist by pointing both at the same CDR source.

## Why Self-Host Your VoIP Billing Platform?

Self-hosting your VoIP billing platform gives you complete control over your revenue data. When you use a SaaS billing provider, every rate card, customer record, and call detail flows through a third party's servers. If that provider changes their pricing model, discontinues your region, or suffers a security breach, your entire billing operation is impacted.

Data ownership is particularly important in telecommunications, where CDR data can reveal sensitive information about calling patterns, business relationships, and customer behavior. Self-hosting keeps this data within your infrastructure, subject only to your own security policies and compliance requirements.

Cost is another factor. SaaS billing platforms typically charge per-transaction fees (often $0.005-0.02 per rated call) or monthly per-seat fees. At scale — 100,000+ calls per month — these fees add up to thousands of dollars annually. Self-hosting ASTPP or A2Billing on a $20/month VPS eliminates these recurring costs entirely. You pay once for infrastructure, not per transaction.

No vendor lock-in means you're free to switch billing platforms, customize the billing logic, or integrate with any upstream VoIP platform. For a guide on building a complete self-hosted VoIP stack, see our [Kamailio vs Asterisk vs FreeSWITCH comparison](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/). If you need infrastructure access management for your VoIP servers, check out our [infrastructure access management guide](../2026-05-04-self-hosted-infrastructure-access-management-teleport-boundary-openziti-guide/). For radius-based AAA alongside your VoIP billing, see our [FreeRADIUS accounting guide](../2026-05-18-self-hosted-radius-accounting-freeradius-daloradius-radiusdesk-guide/).

## FAQ

### Do I need a billing platform if I only run a small office PBX?

Probably not. For a small office with 10-50 extensions where all calls are internal or flat-rate SIP trunk calls, CDR analytics alone (via CDR-Stats or FreePBX's built-in CDR reports) is usually sufficient. A full billing platform becomes necessary when you need to charge customers, manage rate cards across multiple providers, or generate invoices.

### Can ASTPP and A2Billing work with FreeSWITCH?

Yes, both platforms can work with FreeSWITCH, though they were originally designed for Asterisk. ASTPP has native FreeSWITCH support as of version 5. With A2Billing, you'll need to configure FreeSWITCH to output CDRs in a format A2Billing can parse (CSV with the expected columns) and potentially use the XML-RPC API for call authorization.

### How do I prevent toll fraud with these platforms?

All four platforms include fraud detection features to varying degrees. CDR-Stats has the strongest analytics-based fraud detection (unusual call pattern alerts, geo-anomaly detection, high-cost destination alerts). ASTPP and A2Billing include max call duration limits, concurrent call limits, and destination blacklists. For production deployments, we recommend combining a billing platform's built-in fraud controls with CDR-Stats for behavioral anomaly detection.

### What's the difference between prepaid and postpaid billing in these platforms?

Prepaid billing deducts from a customer's balance in real-time during the call. If the balance reaches zero, the call is terminated. This model is common for calling cards, PIN-based services, and retail VoIP. Postpaid billing records calls and generates invoices at the end of the billing cycle (typically monthly). This model is common for business customers and wholesale agreements. ASTPP, A2Billing, and MagnaBilling all support both models; CDR-Stats is analytics-only.

### Can I migrate from A2Billing to ASTPP?

Yes, but it requires careful planning. Both platforms use MySQL/MariaDB, so you can export A2Billing's rate cards, customer data, and CDRs via SQL dumps and transform them to ASTPP's schema. ASTPP provides migration scripts for this purpose. The main challenges are differences in rate card structure (A2Billing uses LCR-based routing, ASTPP uses a more flexible rate plan model) and customer portal URLs. Plan for 1-2 weeks of migration work for a medium-sized deployment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VoIP CDR Analysis & Billing Platforms: ASTPP vs A2Billing vs CDR-Stats",
  "description": "Comprehensive comparison of self-hosted VoIP CDR analysis and billing platforms including ASTPP, A2Billing, CDR-Stats, and MagnaBilling. Covers deployment, features, rate card management, and integration with Asterisk and FreeSWITCH.",
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
