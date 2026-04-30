---
title: "Peppermint vs Znuny vs Hesk — Self-Hosted Help Desk & Ticketing (2026)"
date: 2026-05-01T02:40:00Z
tags: ["helpdesk", "ticketing", "self-hosted", "customer-support", "docker"]
draft: false
---

Running a support operation should not require paying per-agent SaaS fees. Self-hosted help desk tools give you full control over your customer support workflow, no per-seat licensing, and complete data privacy. This guide compares **Peppermint** (modern and lightweight), **Znuny** (enterprise-grade ITSM), and **Hesk** (simple and free) to help you choose the right platform for your team.

Peppermint ([github.com/Peppermint-Lab/peppermint](https://github.com/Peppermint-Lab/peppermint)) has **3,100+ GitHub stars** and positions itself as a Zendesk and Jira alternative with a focus on simplicity.

---

## What Is a Self-Hosted Help Desk?

A self-hosted help desk is a ticketing and customer support platform you run on your own infrastructure. It handles incoming support requests (email, web forms, chat), organizes them into tickets, tracks resolution, and provides reporting. Unlike Zendesk, Freshdesk, or Jira Service Management, self-hosted tools have no per-agent costs and keep all customer data on your servers.

## Quick Comparison Table

| Feature | Peppermint | Znuny (OTRS fork) | Hesk |
|---------|------------|-------------------|------|
| **GitHub Stars** | 3,100+ | 600+ | N/A (SourceForge) |
| **License** | AGPL-3.0 | GPL-3.0 | Proprietary (free tier) |
| **Language** | TypeScript/Node.js | Perl | PHP |
| **Database** | PostgreSQL | MySQL/PostgreSQL | MySQL/SQLite |
| **Email Integration** | Yes | Yes (extensive) | Yes |
| **Multi-Channel** | Email, web, API | Email, phone, web, API | Email, web |
| **SLA Management** | Basic | Advanced | No |
| **Knowledge Base** | Yes | Yes | Yes |
| **Custom Fields** | Yes | Extensive | Basic |
| **REST API** | Yes | Yes | Limited |
| **Docker Support** | Official compose | Community | Community |
| **User Interface** | Modern SPA | Traditional web UI | Simple web UI |
| **Team Collaboration** | Yes | Yes | Basic |

## Peppermint — Modern and Lightweight

Peppermint is a newer help desk that aims to provide the core ticketing experience without the bloat of enterprise tools. It is designed for small to medium teams that need a clean, modern interface.

### Key Features

- **Ticket management** — create, assign, prioritize, and track support tickets
- **Email integration** — connect mailboxes to auto-create tickets from incoming emails
- **Knowledge base** — build a self-service help center for common issues
- **Team collaboration** — assign tickets, add internal notes, @mention teammates
- **REST API** — integrate with other tools and build custom workflows
- **Custom fields** — extend ticket data with your own fields
- **Clean, modern UI** — single-page application built with Next.js

### Docker Compose Setup

```yaml
services:
  peppermint_postgres:
    container_name: peppermint_postgres
    image: postgres:latest
    restart: always
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: peppermint
      POSTGRES_PASSWORD: ${DB_PASSWORD:-strong_password_here}
      POSTGRES_DB: peppermint

  peppermint:
    container_name: peppermint
    image: pepperlabs/peppermint:latest
    ports:
      - 1000:3000
      - 1001:5003
    restart: always
    depends_on:
      - peppermint_postgres
    environment:
      DB_USERNAME: "peppermint"
      DB_PASSWORD: ${DB_PASSWORD:-strong_password_here}
      DB_HOST: "peppermint_postgres"
      SECRET: ${SECRET:-your-secret-key-here}

volumes:
  pgdata:
```

**Important:** Replace the default passwords and secret key before deploying to production. Use environment variables or a `.env` file to keep credentials out of the compose file.

### When to Choose Peppermint

- You want a modern, clean UI without enterprise complexity
- Your team is small to medium-sized (under 50 agents)
- You value simplicity and ease of deployment

## Znuny — Enterprise-Grade ITSM (OTRS Fork)

Znuny is a fork of the well-known OTRS help desk, which was one of the most popular open-source ticketing systems before its commercial pivot. Znuny continues the open-source tradition with enterprise-grade features.

### Key Features

- **ITSM module** — ITIL-aligned service management with change, problem, and incident management
- **Advanced SLA management** — define response and resolution time targets with escalation
- **Process management** — build multi-step workflows with conditional logic
- **Dynamic fields** — extensive custom field system
- **PostMaster filters** — powerful email preprocessing and routing
- **Reporting** — comprehensive reporting and statistics
- **LDAP/Active Directory** — enterprise authentication integration
- **Ticket acceleration** — optimized for high-volume ticket queues

### Docker Compose Setup

```yaml
services:
  znuny:
    image: znuny/znuny:latest
    restart: unless-stopped
    ports:
      - 8080:80
    environment:
      ZNUNY_DB_HOST: db
      ZNUNY_DB_NAME: znuny
      ZNUNY_DB_USER: znuny
      ZNUNY_DB_PASSWORD: ${DB_PASSWORD:-znuny_secret}
    depends_on:
      - db
    volumes:
      - znuny-data:/opt/otrs

  db:
    image: mysql:8
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD:-znuny_secret}
      MYSQL_DATABASE: znuny
      MYSQL_USER: znuny
      MYSQL_PASSWORD: ${DB_PASSWORD:-znuny_secret}
    volumes:
      - znuny-db:/var/lib/mysql

volumes:
  znuny-data:
  znuny-db:
```

### When to Choose Znuny

- You need ITIL-aligned IT service management
- SLA management and escalation are critical
- You have a large support team (50+ agents)
- You need deep customization and process workflows

## Hesk — Simple and Free

Hesk has been around since 2006 and is one of the longest-running help desk tools. It is simple, fast, and does the basics well without unnecessary complexity.

### Key Features

- **Ticket tracking** — email-based and web form ticket submission
- **Knowledge base** — built-in FAQ system
- **Custom categories** — organize tickets by department and category
- **Auto-responder** — automatic email replies for new tickets
- **Simple UI** — lightweight, fast-loading interface
- **Low resource usage** — runs on minimal server resources
- **Free version** — fully functional free tier available

### Docker Compose Setup

```yaml
services:
  hesk:
    image: linuxserver/hesk:latest
    restart: unless-stopped
    ports:
      - 8080:80
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - hesk-config:/config

volumes:
  hesk-config:
```

Hesk uses the LinuxServer.io community image with standard volume mounts.

### When to Choose Hesk

- You need the simplest possible ticketing system
- Resource constraints are tight
- You do not need advanced features like SLAs or team workflows
- You are comfortable with a dated but functional interface

## Advanced: Setting Up Email Piping

For automatic ticket creation from incoming emails, configure your mail server to pipe messages to the help desk. Here is a Postfix configuration example for Peppermint:

```bash
# /etc/postfix/virtual
support@yourdomain.com   peppermint-pipe

# /etc/postfix/master.cf (add at end)
peppermint-pipe   unix  -       n       n       -       -       pipe
  flags=Rq user=www-data argv=/usr/bin/curl -X POST http://localhost:1000/api/tickets/email -d @-
```

For a complete email server setup including spam filtering and DKIM, see our [Postfix vs OpenSMTPD vs Maddy guide](../2026-04-18-maddy-vs-chasquid-vs-opensmtpd-lightweight-smtp-servers-2026/).

## Why Self-Host Your Help Desk?

Cloud help desks like Zendesk, Freshdesk, and Jira Service Management charge per agent per month. For a 10-person support team, Zendesk costs upwards of $500/month. Self-hosted alternatives eliminate these costs entirely:

- **No per-agent pricing** — add unlimited agents without paying extra
- **Full data control** — customer conversations and ticket data stay on your infrastructure
- **Custom workflows** — build ticket routing, escalation, and automation that matches your process
- **No vendor lock-in** — migrate or modify your setup without data export restrictions

For teams that also need a CRM alongside ticketing, see our [Twenty vs Monica vs EspoCRM guide](../twenty-vs-monica-vs-espocrm-self-hosted-crm-guide-2026/). If you need enterprise IT service management with change and incident workflows, our [Zammad vs FreeScout vs osTicket comparison](../self-hosted-helpdesk-zammad-freescout-osticket/) covers established alternatives.

## FAQ

### Q: Is Peppermint suitable for production use with a live support team?

A: Peppermint is stable enough for small team production use. However, it is younger than Znuny and Hesk, so it has fewer integrations and less battle-testing at scale. For enterprise deployments, Znuny is the safer choice.

### Q: Can these tools handle email-based ticket creation?

A: Yes, all three support email-to-ticket conversion. Peppermint and Znuny use API-based email piping. Hesk has a built-in POP3/IMAP email fetcher that periodically checks a mailbox.

### Q: Do any of these support live chat?

A: Peppermint focuses on email and web form ticketing. For live chat, you would need to integrate a separate tool like [Chatwoot or Tiledesk](../self-hosted-live-chat-chatwoot-papercups-tiledesk-guide/). Znuny can integrate with third-party chat tools via its API.

### Q: Which help desk is easiest to set up?

A: Hesk is the simplest — a single container with SQLite. Peppermint requires PostgreSQL but is straightforward. Znuny has the most complex setup due to its enterprise feature set and dependencies.

### Q: Can I migrate from Zendesk or Freshdesk?

A: Znuny has the most mature migration tools, including CSV and XML importers. Peppermint supports CSV import. Hesk has a basic CSV importer. None offer direct API migration from Zendesk, but you can export from Zendesk to CSV and import.

### Q: How do these compare to the help desks in your other guide?

A: This guide focuses on newer or alternative options. For a comparison of Zammad, FreeScout, and osTicket, see our [complete self-hosted help desk guide](../self-hosted-helpdesk-zammad-freescout-osticket/). Znuny fills the enterprise ITSM niche, while Peppermint targets the lightweight modern segment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Peppermint vs Znuny vs Hesk — Self-Hosted Help Desk & Ticketing (2026)",
  "description": "Compare Peppermint, Znuny, and Hesk for self-hosted help desk and ticketing. Docker Compose configs, feature comparison, and setup guides.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
