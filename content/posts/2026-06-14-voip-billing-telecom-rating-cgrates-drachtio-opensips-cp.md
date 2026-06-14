---
title: "Self-Hosted VoIP Billing & Telecom Rating Platforms: CGRateS vs Drachtio vs OpenSIPS CP"
date: "2026-06-14"
tags: ["voip", "telecom", "billing", "sip", "opensips", "kamailio", "rating-engine", "isp"]
draft: false
---

## Introduction

For telecom operators, Internet Service Providers (ISPs), and VoIP service providers, accurate real-time billing and rating are critical infrastructure components. Every call, SMS, and data session must be tracked, rated against complex tariff plans, and billed correctly — often in real time to prevent fraud and revenue leakage.

Open source telecom rating and billing platforms give operators full control over their charging logic, avoid vendor lock-in, and can scale from small SIP trunking operations to carrier-grade deployments handling millions of transactions per day. This guide compares three prominent open source VoIP billing and telecom rating platforms: **CGRateS**, **Drachtio**, and the **OpenSIPS Control Panel (CP)** billing modules — each taking a fundamentally different architectural approach to the same problem.

## Comparison Table

| Feature | CGRateS | Drachtio | OpenSIPS CP |
|---------|---------|----------|-------------|
| **Architecture** | Standalone real-time charging system | SIP application server (Node.js controlled) | Web UI for OpenSIPS configuration |
| **Rating Engine** | Built-in, event-based | Via external application logic | Leverages OpenSIPS dialog/accounting |
| **Real-time Authorization** | Yes (prepaid, postpaid, pseudoprepaid) | Yes (via Node.js app logic) | Yes (via OpenSIPS ACC/CDR modules) |
| **Protocol Support** | Diameter, RADIUS, HTTP, SM-KPI | SIP only (Drachtio mediates) | SIP (via OpenSIPS core) |
| **Database Backend** | MySQL, PostgreSQL, MongoDB, Redis | N/A (stateless, app-managed) | MySQL, PostgreSQL (via OpenSIPS) |
| **Web Dashboard** | Built-in ERP-style admin panel | None (build your own) | Full web-based CP interface |
| **Multi-Tenant** | Yes, native | Via application logic | Via OpenSIPS multi-domain |
| **GitHub Stars** | 501+ | 326+ | 130+ |
| **Language** | Go | C++ (server), Node.js (apps) | PHP (CP), C (OpenSIPS) |
| **License** | AGPLv3 | MIT | GPLv2 |

## CGRateS: Carrier-Grade Real-Time Charging

[CGRateS](https://github.com/cgrates/cgrates) is a battle-tested, carrier-grade real-time charging system written in Go. Originally designed for telecom environments, it has evolved into a general-purpose event-based rating and billing engine that can handle virtually any metered service — from VoIP minutes to cloud infrastructure usage.

### Key Features

- **Real-time session control**: CGRateS can authorize, rate, and disconnect sessions mid-call when a prepaid balance runs out
- **Flexible rating**: Supports destination-based, time-based, volume-based, and custom rating profiles with complex tariff plans including peak/off-peak, tiered pricing, and bundled allowances
- **Multi-protocol**: Native Diameter (Ro/Rf/Gy), RADIUS accounting, and HTTP/JSON APIs make it compatible with virtually any network element
- **Built-in CDR mediation**: Normalizes call detail records from disparate sources into a unified format before rating

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  cgrates:
    image: cgrates/cgrates:latest
    container_name: cgrates
    ports:
      - "2012:2012"   # JSON-RPC
      - "2080:2080"   # HTTP API
      - "3868:3868"   # Diameter
      - "1812:1812/udp"  # RADIUS
    environment:
      - CGRATES_DB_HOST=mysql
      - CGRATES_DB_USER=cgrates
      - CGRATES_DB_PASSWORD=cgrates_pass
    depends_on:
      - mysql
    volumes:
      - ./cgrates_config:/etc/cgrates
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: cgrates
      MYSQL_USER: cgrates
      MYSQL_PASSWORD: cgrates_pass
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

### Rating a VoIP Call via API

```bash
# Authorize a call (check balance, return max duration)
curl -X POST http://localhost:2080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "SessionSv1.InitiateSession",
    "params": [{
      "OriginID": "call-001",
      "OriginHost": "sip-server-1",
      "RequestType": "*prepaid",
      "Tenant": "cgrates.org",
      "Account": "subscriber-1001",
      "Destination": "49123456789",
      "SetupTime": "2026-06-14T10:00:00Z",
      "Usage": "1800s"
    }]
  }'
```

CGRateS excels in environments requiring true carrier-grade features: prepaid/postpaid convergence, complex rating trees, and multi-vendor mediation. Its mature Diameter stack makes it the go-to choice for LTE/5G core integration. However, its learning curve is steep — expect several weeks to fully model your tariff structures.

## Drachtio: Programmable SIP Application Server

[Drachtio](https://github.com/drachtio/drachtio-server) takes a fundamentally different approach. Rather than being a billing system, it is a **programmable SIP application server** — a SIP proxy that you control via Node.js applications. For billing use cases, you write the billing logic yourself in JavaScript/Node.js, giving you unlimited flexibility but requiring significant development effort.

### Architecture

Drachtio sits between your SIP endpoints and your upstream carriers or PBXs. Your Node.js application receives events for every SIP message (INVITE, BYE, REGISTER, etc.) and can make real-time routing and authorization decisions.

```javascript
// Simple prepaid billing logic with Drachtio
const drachtio = require('drachtio');
const app = drachtio();

app.invite(async (req, res) => {
  const caller = req.get('From');
  const destination = req.getParsedHeader('To').uri;

  // Check balance from your billing database
  const balance = await getBalance(caller);
  const rate = await getRate(caller, destination);

  if (balance <= 0) {
    return res.send(402, 'Insufficient credit');
  }

  const maxDuration = Math.floor(balance / rate);
  req.set('Session-Expires', maxDuration);
  // Proxy the call to upstream carrier
  req.proxy({ destination: `sip:${destination}@upstream-carrier.com` });
});

app.bye(async (req, res) => {
  // Calculate actual call duration and deduct from balance
  const duration = calculateDuration(req);
  await deductBalance(req.source, duration);
  res.send(200);
});

app.listen({ port: 9022, secret: 'change-me' });
```

### Docker Deployment

```yaml
version: "3.8"
services:
  drachtio:
    image: drachtio/drachtio-server:latest
    container_name: drachtio
    ports:
      - "5060:5060/udp"   # SIP
      - "5060:5060/tcp"   # SIP/TCP
      - "9022:9022"       # Node.js control API
    environment:
      - DRACHTIO_SECRET=your-secret-here
      - DRACHTIO_SIP_IP=your-public-ip
    restart: unless-stopped

  billing-app:
    build: ./billing-app
    container_name: drachtio-billing
    depends_on:
      - drachtio
    environment:
      - DRACHTIO_HOST=drachtio
      - DRACHTIO_PORT=9022
      - DRACHTIO_SECRET=your-secret-here
    restart: unless-stopped
```

Drachtio is ideal for teams that need **complete control** over their SIP routing and billing logic, have Node.js expertise, and are building a custom VoIP platform from scratch. It is NOT a turnkey billing solution — you must build the rating engine, database schema, and web dashboard yourself.

## OpenSIPS Control Panel: Configuration-Driven Billing

The [OpenSIPS Control Panel (CP)](https://github.com/OpenSIPS/opensips-cp) is a web-based management interface for the OpenSIPS SIP server. While OpenSIPS itself is a high-performance SIP proxy/router (not a billing engine), the CP provides tools for managing subscribers, viewing CDRs (Call Detail Records), and configuring per-user billing profiles through a clean web interface.

### Billing-Relevant CP Modules

- **CDR Viewer**: Browse, search, and export call detail records with filtering by date, caller, destination, and call status
- **Subscriber Management**: Provision SIP accounts with per-user rate plans, credit limits, and calling permissions
- **Dialplan Editor**: Configure routing rules visually — essential for LCR (Least Cost Routing) across multiple carriers
- **Accounting Integration**: CP leverages OpenSIPS's `acc` (accounting) module to capture CDRs; pair with an external rating engine for full billing

### Nginx Reverse Proxy Configuration

```nginx
server {
    listen 443 ssl;
    server_name opensips-cp.example.com;

    ssl_certificate /etc/letsencrypt/live/opensips-cp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/opensips-cp.example.com/privkey.pem;

    root /var/www/opensips-cp/web;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.2-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

### LCR with OpenSIPS

The CP's dialplan module enables Least Cost Routing — directing outbound calls to the cheapest available carrier:

```opensips
# OpenSIPS LCR configuration (managed via CP)
loadmodule "drouting.so"
modparam("drouting", "db_url", "mysql://opensips:pass@localhost/opensips")

# Route based on least-cost prefix match
if (!do_routing("GW_CARRIER")) {
    t_reply(503, "No route found");
    exit;
}
```

OpenSIPS CP is best suited for operators already using OpenSIPS who need subscriber management and CDR visibility without deploying a separate billing stack. For full rating/billing, it's commonly paired with CGRateS or a custom billing backend.

## Deployment Architecture Comparison

When choosing a VoIP billing stack, consider these three deployment patterns:

**Pattern 1 — CGRateS Standalone**: Deploy CGRateS as the central rating/billing engine. All SIP proxies (OpenSIPS, Kamailio, FreeSWITCH) send accounting events to CGRateS via RADIUS or HTTP. CGRateS handles rating, balance management, and CDR generation in one system. Best for: carriers needing Diameter/RADIUS compliance and prepaid/postpaid convergence.

**Pattern 2 — Drachtio + Custom Stack**: Deploy Drachtio as the SIP frontend, write your billing logic in Node.js, and store balances/CDRs in your own database. This gives unlimited flexibility but requires building the entire billing infrastructure. Best for: startups building a custom VoIP platform with unique pricing models.

**Pattern 3 — OpenSIPS + CP + External Rating**: Use OpenSIPS for SIP routing and the CP for subscriber/CDR management, then export CDRs to an external rating engine (CGRateS, custom Python script, or a commercial billing system). Best for: established OpenSIPS deployments adding billing incrementally.

## Why Self-Host Your VoIP Billing Platform?

Running your own telecom billing infrastructure is a strategic decision that directly impacts your bottom line. Every percentage point of billing accuracy translates to real revenue — and every hour of billing system downtime means lost revenue that cannot be recovered retroactively.

Self-hosting gives you complete visibility into your rating logic. When a customer disputes a charge, you can trace the exact rating decision through your tariff trees and CDR records. With cloud-hosted billing SaaS platforms, you often receive a black-box "trust us" response. For telecom operators handling millions of minutes per month, this transparency is non-negotiable.

Cost control is another critical factor. Commercial telecom billing platforms typically charge per-transaction fees or revenue-share models that eat into margins as you scale. Open source solutions like CGRateS have zero per-transaction costs — your only expenses are the servers they run on. At 10 million CDRs per month, this can mean the difference between profitability and loss.

Data sovereignty matters enormously in telecom. Call detail records contain sensitive metadata about who calls whom, when, and for how long. Many jurisdictions have strict data localization requirements for telecommunications data. Self-hosting ensures your CDRs never leave your infrastructure — see our [self-hosted DNS privacy guide](../2026-04-10-self-hosted-dns-privacy-doh-dot-dnscrypt-guide/) for related data sovereignty considerations.

The open source telecom ecosystem is mature and well-supported. Communities around OpenSIPS, Kamailio, and FreeSWITCH have decades of production deployment experience. When you encounter an edge case — and in telecom, every case is an edge case — you have access to the source code, community forums, and commercial support vendors who can resolve issues quickly. For related infrastructure monitoring, our [self-hosted firewall log analysis guide](../2026-06-01-self-hosted-bandwidth-monitoring-darkstat-vnstat-php-bandwidthd-guide/) covers traffic visibility for VoIP networks.

## FAQ

### Do I need a dedicated billing server, or can it run on my existing SIP server?

For small deployments (< 100 concurrent calls), CGRateS or OpenSIPS CP can co-reside with your SIP proxy on the same server (4GB RAM, 2 vCPUs minimum). For production carrier environments, separate the billing server to avoid resource contention — a billing outage should never block call routing. CGRateS is particularly efficient in Go and typically uses < 500MB RAM even under load.

### Can CGRateS handle non-telecom billing, like IoT data or API usage?

Yes. CGRateS is fundamentally an event-based rating engine — it doesn't care whether the "event" is a phone call, an API request, or an IoT sensor reading. You define the rating parameters (destination, volume, time, custom fields) and CGRateS applies your tariff logic. Several cloud providers use CGRateS internally for metered API billing.

### How does prepaid balance enforcement work in real-time?

CGRateS supports "session debit reservation" — when a call starts, it reserves the maximum possible cost based on the rate, then periodically deducts actual usage. If the balance hits zero mid-call, CGRateS sends a disconnect signal. Drachtio achieves this by having your Node.js app calculate max duration at call setup and terminate via SIP BYE when the limit is reached. OpenSIPS can enforce session limits via the `dialog` module's `timeout` parameter.

### What database should I use for storing CDRs at scale?

Start with PostgreSQL — all three platforms support it, and it handles millions of CDR rows comfortably with proper indexing. For carrier-scale deployments (> 100M CDRs/month), consider partitioning CDR tables by date and archiving old records to object storage. CGRateS also supports MongoDB for CDR storage, which can simplify horizontal scaling.

### Can I integrate these with an existing FreeSWITCH or Asterisk deployment?

Absolutely. Both FreeSWITCH and Asterisk can generate RADIUS accounting packets (via the `mod_rad_auth` or `cdr_radius` modules) that CGRateS consumes natively. For Drachtio, you'd route SIP traffic through Drachtio as a proxy in front of your media servers. OpenSIPS CP works with any SIP infrastructure that OpenSIPS can proxy to.

### Is there a fully open source, all-in-one VoIP billing + PBX solution?

There is no single project that combines full PBX functionality with carrier-grade billing. The closest is FusionPBX (based on FreeSWITCH) with its built-in billing module, which handles basic prepaid and postpaid scenarios. For carrier-grade needs, the industry-standard pattern is OpenSIPS/Kamailio (SIP routing) + CGRateS (rating/billing) + FreeSWITCH (media handling).

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VoIP Billing & Telecom Rating Platforms: CGRateS vs Drachtio vs OpenSIPS CP",
  "description": "Compare open source VoIP billing and telecom rating platforms: CGRateS for carrier-grade real-time charging, Drachtio for programmable SIP billing, and OpenSIPS CP for configuration-driven subscriber management and CDR visibility.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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
