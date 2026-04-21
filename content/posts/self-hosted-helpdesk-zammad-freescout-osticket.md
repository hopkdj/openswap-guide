---
title: "Best Self-Hosted Help Desk Software in 2026: Zammad vs FreeScout vs osTicket"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted help desk and customer support platforms. Compare Zammad, FreeScout, and osTicket with Docker installation, configuration, and feature breakdown."
---

Running a customer support operation on SaaS platforms like Zendesk, Freshdesk, or Intercom means handing over every customer conversation, complaint, and internal note to a third party. For businesses that value data sovereignty, privacy compliance, or simply want to eliminate per-agent subscription costs, self-hosted help desk software is the logical answer.

In 2026, the self-hosted help desk landscape is stronger than ever. Three platforms stand out: **Zammad**, **FreeScout**, and **osTicket**. Each takes a different approach to ticketing, and each excels in different scenarios. This guide breaks down the strengths, weaknesses, and deployment details so you can choose the right platform and get it running in under an hour.

## Why Self-Host Your Help Desk

The case for owning your support infrastructure is compelling:

- **Full data ownership.** Every ticket, attachment, and audit log stays on your servers. No vendor lock-in, no surprise data retention policy changes, and no cross-border data transfer concerns under GDPR or similar regulations.
- **Unlimited agents, no per-seat pricing.** SaaS help desks typically charge $25–$150 per agent per month. Self-hosted solutions are free and open-source, so scaling your support team costs nothing beyond your server.
- **Deep customization.** Access to the full codebase and database means you can build custom workflows, integrate with any internal tool, and modify the UI to match your brand — things that are impossible or heavily restricted on SaaS platforms.
- **Offline resilience.** Your support system stays available even when a SaaS provider experiences an outage. You control the uptime SLA.
- **Unified communications.** Self-hosted platforms can integrate directly with your self-hosted email server (Postfix/Dovecot, [mailcow](https://mailcow.email/)), matrix channels, or internal wiki without relying on fragile API webhooks through multiple SaaS layers.

The trade-off is operational responsibility — you manage backups, updates, and server resources. With [docker](https://www.docker.com/) and modern orchestration tools, this overhead is minimal and well worth the benefits.

## Zammad: The Modern All-in-One Help Desk

Zammad is a Ruby-on-Rails-based help desk that has gained significant traction since its initial release. It offers a polished, modern web interface with real-time updates via WebSocket, built-in live chat, and support for multiple communication channels including email, Twitter/X, Telegram, and Facebook.

### Key Features

- **Multi-channel inbox** — Email, Twitter, Telegram, Facebook, web chat, and phone all funnel into a single ticket queue
- **Real-time UI** — WebSocket-based interface means agents see new tickets and updates instantly without refreshing
- **Built-in knowledge base** — Create and manage internal and external help articles natively
- **Time accounting** — Track time spent on each ticket for billing or SLA reporting
- **Text modules and macros** — Pre-built responses and bulk actions for high-volume teams
- **Elasticsearch integration** — Full-text search across all tickets, notes, and attachments
- **Over 200 API endpoints** — RESTful API for deep integrations

### Docker Installation

Zammad provides an official Docker Compose setup. Here is a production-ready confi[nginx](https://nginx.org/)ion:

```yaml
version: "3.8"
services:
  zammad-nginx:
    image: zammad/zammad-docker-compose:zammad-postgresql-latest
    ports:
      - "8080:8080"
    environment:
      - NGINX_SERVER_SCHEME=https
      - POSTGRESQL_DB=zammad
      - POSTGRESQL_USER=zammad
      - POSTGRESQL_PASS=zammad_secure_password
      - POSTGRESQL_HOST=zammad-postgresql
    depends_on:
      - zammad-postgresql
      - zammad-elasticsearch
    restart: unless-stopped
    volumes:
      - zammad-data:/opt/zammad

  zammad-postgresql:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=zammad
      - POSTGRES_USER=zammad
      - POSTGRES_PASSWORD=zammad_secure_password
    restart: unless-stopped
    volumes:
      - postgresql-data:/var/lib/postgresql/data

  zammad-elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    restart: unless-stopped
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data

volumes:
  zammad-data:
  postgresql-data:
  elasticsearch-data:
```

Save this as `docker-compose.yml` and launch:

```bash
mkdir zammad && cd zammad
# Create the docker-compose.yml file above
docker compose up -d
```

After containers start, access Zammad at `http://your-server-ip:8080`. The first visit launches the setup wizard where you configure the admin account, email channel, and organization details.

### Resource Requirements

Zammad is the most resource-intensive of the three options due to its Rails stack and Elasticsearch dependency:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB | 50 GB+ SSD |
| Services | 3 containers | 4+ containers |

Elasticsearch alone requires at least 2 GB of heap for production use. If you are running on a budget VPS, consider FreeScout or osTicket instead.

## FreeScout: The Lightweight Help Scout Alternative

FreeScout positions itself as a free, open-source clone of Help Scout. Written in PHP with a Laravel foundation, it is significantly lighter than Zammad and focuses on shared inbox functionality with a clean, minimal interface.

### Key Features

- **Shared inbox** — Multiple agents manage a single inbox without duplicate responses
- **Collision detection** — Real-time awareness when another agent is replying to the same conversation
- **Conversations, not tickets** — Thread-based model that feels like email, not a traditional ticketing system
- **Modular architecture** — Official and community modules extend functionality (KB, reports, canned responses, auto-assignments)
- **Email piping and IMAP** — Connect multiple email accounts seamlessly
- **Customer portal** — Self-service portal where customers can view their conversation history
- **Lightweight** — Runs comfortably on a $5/month VPS with MySQL/MariaDB

### Docker Installation

FreeScout has excellent community Docker support. Here is a clean production setup:

```yaml
version: "3.8"
services:
  freescout:
    image: linuxserver/freescout:latest
    container_name: freescout
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - DB_HOST=freescout-db
      - DB_NAME=freescout
      - DB_USER=freescout
      - DB_PASS=freescout_password
      - APP_URL=https://support.example.com
      - ADMIN_EMAIL=admin@example.com
      - ADMIN_PASS=StrongAdminPass123!
    volumes:
      - freescout-config:/config
      - freescout-data:/data
    ports:
      - "8080:80"
      - "8443:443"
    depends_on:
      - freescout-db
    restart: unless-stopped

  freescout-db:
    image: mariadb:11
    container_name: freescout-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_password_here
      - MYSQL_DATABASE=freescout
      - MYSQL_USER=freescout
      - MYSQL_PASSWORD=freescout_password
    volumes:
      - freescout-mysql-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  freescout-config:
  freescout-data:
  freescout-mysql-data:
```

Launch with:

```bash
mkdir freescout && cd freescout
docker compose up -d
```

Once running, visit `http://your-server-ip:8080`. The LinuxServer.io image handles initial database setup automatically. Log in with the admin credentials from the environment variables.

### Configuring Email Channels

FreeScout connects to email via IMAP fetching or email piping. For IMAP:

1. Navigate to **Manage → Email** in the admin panel
2. Add an IMAP account with your mail server credentials
3. Set the fetch frequency (default is every 5 minutes)
4. Configure SMTP for outbound replies

For lower latency, set up email piping directly to the FreeScout script:

```bash
# In your mail server's aliases or .forward file:
# |/opt/freescout/artisan freescout:parse
```

This delivers incoming emails to FreeScout instantly rather than polling on a schedule.

### Resource Requirements

FreeScout is dramatically lighter than Zammad:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2 cores |
| RAM | 512 MB | 1 GB |
| Disk | 5 GB | 20 GB |
| Services | 2 containers | 2 containers |

This makes it ideal for small teams, solo operators, or budget-conscious deployments.

## osTicket: The Battle-Tested Enterprise Ticketing System

osTicket is the oldest and most widely deployed open-source help desk system, with a history stretching back to 2006. It is a traditional ticketing system with a focus on flexibility, custom fields, and SLA management. While the interface is less modern than Zammad or FreeScout, its depth of features and maturity make it the go-to choice for IT departments and enterprises.

### Key Features

- **Advanced ticket filtering** — Sophisticated rules engine for auto-assignment, escalation, and routing based on any field
- **Custom fields and forms** — Build custom ticket forms with dropdowns, dates, file uploads, and calculated fields
- **SLA plans** — Define service-level agreements with escalation rules and notification thresholds
- **Help topics and departments** — Hierarchical organization of tickets by subject area and team
- **Agent collaboration** — Internal notes, thread splitting, and ticket merging
- **Extensive plugin ecosystem** — Community plugins for LDAP auth, SSO, reporting, and more
- **API** — REST API for integrations, though less comprehensive than Zammad's

### Docker Installation

osTicket can run with a simple Apache + MySQL stack:

```yaml
version: "3.8"
services:
  osticket:
    image: osticket/osticket:latest
    container_name: osticket
    environment:
      - ADMIN_FIRSTNAME=Admin
      - ADMIN_LASTNAME=User
      - ADMIN_EMAIL=admin@example.com
      - ADMIN_PASSWORD=StrongPass123!
      - ADMIN_USERNAME=admin
      - MYSQL_HOST=osticket-db
      - MYSQL_DATABASE=osticket
      - MYSQL_USER=osticket
      - MYSQL_PASSWORD=osticket_password
      - SITE_URL=https://support.example.com
    ports:
      - "8080:80"
    depends_on:
      - osticket-db
    restart: unless-stopped
    volumes:
      - osticket-data:/var/www/html/upload

  osticket-db:
    image: mariadb:11
    container_name: osticket-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=osticket
      - MYSQL_USER=osticket
      - MYSQL_PASSWORD=osticket_password
    volumes:
      - osticket-mysql-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  osticket-data:
  osticket-mysql-data:
```

Deploy with:

```bash
mkdir osticket && cd osticket
docker compose up -d
```

The official image runs an initial setup script on first boot. Visit `http://your-server-ip:8080/scp` to access the staff control panel.

### Creating Custom Ticket Forms

One of osTicket's standout features is its custom form builder. Here is how to create a specialized IT support form:

1. Go to **Admin Panel → Forms**
2. Click **Add New Form** and name it "IT Support Request"
3. Add fields:
   - **Affected System** — Dropdown: Email, Network, Server, Workstation, Other
   - **Priority** — Dropdown: Low, Medium, High, Critical
   - **Asset Tag** — Text field for hardware identification
   - **Screenshot** — File upload for error messages
4. Attach the form to a **Help Topic** (e.g., "IT Support") so it appears when customers select that topic

This level of customization is osTicket's primary advantage over lighter alternatives.

### Resource Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2 cores |
| RAM | 512 MB | 1–2 GB |
| Disk | 5 GB | 20 GB |
| Services | 2 containers | 2–3 containers |

osTicket sits between FreeScout and Zammad in terms of resource needs.

## Feature Comparison

| Feature | Zammad | FreeScout | osTicket |
|---------|--------|-----------|----------|
| **Primary Model** | Multi-channel ticketing | Shared inbox | Traditional ticketing |
| **Tech Stack** | Ruby on Rails, PostgreSQL | PHP/Laravel, MySQL | PHP, MySQL |
| **Real-time UI** | Yes (WebSocket) | Partial (AJAX) | No (page refresh) |
| **Live Chat** | Built-in | Via module | Via plugin |
| **Knowledge Base** | Built-in | Via module | Via plugin |
| **Multi-channel** | Email, Twitter, Telegram, Facebook, Chat, Phone | Email only | Email, Web form, API |
| **Custom Fields** | Yes | Limited | Excellent |
| **SLA Management** | Yes | Via module | Excellent (native) |
| **Time Tracking** | Built-in | Via module | Via plugin |
| **API** | RESTful, 200+ endpoints | REST, limited | REST, basic |
| **Elasticsearch** | Native (required) | No | No |
| **Minimum RAM** | 4 GB | 512 MB | 512 MB |
| **Best For** | Medium-large teams, multi-channel support | Small teams, email-focused support | IT departments, enterprise |
| **License** | GPL-3.0 | AGPL-3.0 (free), commercial modules | GPL-2.0 |

## Reverse Proxy Setup with HTTPS

All three platforms should sit behind a reverse proxy for production use. Here is a Caddy configuration that works for any of them:

```caddy
support.example.com {
    reverse_proxy localhost:8080

    encode gzip
    tls admin@example.com

    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

For Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name support.example.com;

    ssl_certificate /etc/letsencrypt/live/support.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/support.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

The WebSocket upgrade headers are essential for Zammad's real-time functionality.

## Backup Strategy

Protect your help desk data with automated backups. Here is a simple script that backs up all three platform types:

```bash
#!/bin/bash
# backup-helpdesk.sh
BACKUP_DIR="/opt/backups/helpdesk"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Database backup
docker compose exec -T freescout-db mysqldump -u freescout -pfreescout_password freescout \
    | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Application data backup
docker compose cp freescout:/data "$BACKUP_DIR/app_data_$DATE"
docker compose cp freescout:/config "$BACKUP_DIR/app_config_$DATE"

# Compress everything
tar czf "$BACKUP_DIR/backup_$DATE.tar.gz" \
    "$BACKUP_DIR/db_$DATE.sql.gz" \
    "$BACKUP_DIR/app_data_$DATE" \
    "$BACKUP_DIR/app_config_$DATE"

# Clean up raw files
rm -rf "$BACKUP_DIR/db_$DATE.sql.gz" \
       "$BACKUP_DIR/app_data_$DATE" \
       "$BACKUP_DIR/app_config_$DATE"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: backup_$DATE.tar.gz"
```

Add to cron for daily execution:

```bash
0 2 * * * /opt/scripts/backup-helpdesk.sh >> /var/log/helpdesk-backup.log 2>&1
```

## Which Should You Choose?

The decision comes down to your team size, communication channels, and technical resources:

**Choose Zammad if** you need a modern, multi-channel support platform with live chat, social media integration, and real-time collaboration. It is ideal for customer-facing teams of 5+ agents who handle support across email, chat, and social channels. The resource requirements are higher, but the feature set justifies the investment.

**Choose FreeScout if** you want a lightweight, email-focused shared inbox that feels like a team email client rather than a traditional ticketing system. It is perfect for small teams (1–5 agents) who primarily handle email support and want something that runs on minimal hardware. The modular architecture lets you add features as needed.

**Choose osTicket if** you are an IT department or enterprise that needs deep customization, custom ticket forms, SLA management, and a proven platform with nearly two decades of development. The interface is dated, but the functionality is comprehensive, and the low resource requirements make it accessible for any budget.

All three platforms are actively maintained, fully open-source, and can be deployed in production within an hour using Docker. The best choice depends entirely on your workflow, team structure, and the channels your customers use to reach you.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
