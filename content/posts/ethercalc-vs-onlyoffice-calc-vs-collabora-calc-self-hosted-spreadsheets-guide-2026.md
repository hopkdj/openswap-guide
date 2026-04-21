---
title: "EtherCalc vs OnlyOffice Calc vs Collabora Calc: Best Self-Hosted Google Sheets Alternative 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted spreadsheet alternatives in 2026. Compare EtherCalc, OnlyOffice Calc, and Collabora Calc — with Docker deployment guides, feature comparisons, and migration tips to replace Google Sheets."
---

If your team or personal workflow depends on spreadsheets for budgeting, project tracking, data analysis, or inventory management, you are almost certainly using Google Sheets or Microsoft Excel Online. Both are polished, collaborative, and free at low usage tiers — but they come with a hidden cost: every formula, every data point, and every business insight you create lives on someone else's server.

In 2026, self-hosted spreadsheet tools have matured to the point where giving up cloud convenience is no longer necessary. You can run a fully collaborative, formula-rich, real-time spreadsheet server on a $5 VPS and retain complete ownership of your data. This guide compares the three strongest open-source options — **EtherCalc**, **OnlyOffice Calc**, and **Collabora Calc** — and shows you exactly how to deploy each one with [docker](https://www.docker.com/).

## Why Self-Host Your Spreadsheets

The argument for moving spreadsheets off Google and Microsoft servers is stronger than ever:

**Full data ownership.** Google Sheets terms of service grant Google broad licenses to process your content for service improvement, analytics, and advertising purposes. Even with enterprise agreements, you are trusting a third party with financial records, customer data, and internal metrics. A self-hosted spreadsheet server means your data never leaves your infrastructure.

**Unlimited rows and users.** Google Sheets caps at 10 million cells per spreadsheet and limits simultaneous editors. Free Google accounts cap storage at 15 GB shared across Gmail, Drive, and Photos. Self-hosted, the only limits are your disk space and CPU. A team of 50 sharing dozens of heavy spreadsheets costs the same as a team of 5.

**Offline access and reliability.** Cloud spreadsheets are unusable during internet outages. A self-hosted instance on your local network or a nearby VPS keeps working even when your ISP goes down. For businesses that depend on spreadsheets for daily operations — inventory counts, POS reconciliations, shift scheduling — this reliability is critical.

**No format lock-in.** Google Sheets uses its own proprietary format under the hood. Export to .xlsx works most of the time, but com[plex](https://www.plex.tv/) formulas, conditional formatting, and script macros often break on import or export. Self-hosted tools based on LibreOffice (Collabora Calc) or with native .xlsx support (OnlyOffice Calc) maintain faithful round-trip compatibility.

**Auditability and compliance.** If your organization falls under GDPR, HIPAA, SOC 2, or industry-specific data regulations, proving where your data lives and who can access it is a legal requirement. Self-hosted spreadsheets give you a single, auditable server with logs you control.

## The Contenders at a Glance

### EtherCalc

EtherCalc is a lightweight, real-time collaborative spreadsheet built specifically for the web. It was created by Audrey Tang and is written in Node.js with SocialCalc as its calculation engine. The entire application — rendering, formula evaluation, and collaboration — happens in the browser and on the server with zero dependencies beyond Node.js and optional Redis for persistence.

EtherCalc is designed for one thing and one thing only: being a spreadsheet. It does not include document editing, presentations, or email. Its interface is a clean, familiar grid with a toolbar for common operations. It supports multiple tabs per spreadsheet, real-time multi-user editing with colored cursors showing who is editing which cell, and a formula language compatible with Google Sheets and Excel for common operations (SUM, AVERAGE, IF, VLOOKUP, and more).

The project is open-source under the Common Public Attribution License (CPAL) and has been actively maintained with regular releases. Its small footprint makes it ideal for lightweight deployments on low-resource servers or Raspberry Pi instances.

### OnlyOffice Calc

OnlyOffice Calc is the spreadsheet component of ONLYOFFICE Docs, a comprehensive open-source office suite developed by Ascensio System SIA. OnlyOffice uses the OOXML (Office Open XML) format — the same .xlsx format used by Microsoft Excel — as its native file format. This gives it an inherent advantage in compatibility: complex Excel workbooks with pivot tables, advanced charting, conditional formatting, and macro-enabled features tend to render more faithfully in OnlyOffice than in other open-source alternatives.

OnlyOffice Calc supports real-time collaborative editing with change tracking, comment threads, and review modes. It integrates with cloud storage platforms ([nextcloud](https://nextcloud.com/), ownCloud, Seafile, SharePoint) and can be embedded into existing web applications via its JavaScript API. The full ONLYOFFICE Docs package includes document, spreadsheet, and presentation editors in a single deployment.

The community edition is available under the GNU AGPL v3 license. The enterprise edition adds additional features like advanced security controls and priority support.

### Collabora Calc

Collabora Calc is the spreadsheet component of Collabora Online, which is built on the LibreOffice codebase. Collabora Productivity — the company behind the project — employs many of the core LibreOffice developers, meaning Collabora Calc benefits from decades of spreadsheet engineering.

Because it shares its engine with LibreOffice Calc, Collabora Calc supports the ODF (Open Document Format) .ods format natively and provides strong compatibility with .xlsx files. It handles complex spreadsheets with advanced formulas, pivot tables, data pilots, and chart types that other open-source tools struggle with. The rendering fidelity is exceptional — what you see in Collabora Calc is what you would see in LibreOffice desktop.

Collabora Online is designed primarily as a backend service that integrates with file management platforms like Nextcloud and ownCloud. It can also run standalone with its built-in WOPI (Web Application Open Platform Interface) server. The project is available under the Mozilla Public License 2.0.

## Feature Comparison

| Feature | EtherCalc | OnlyOffice Calc | Collabora Calc |
|---------|-----------|-----------------|----------------|
| **Native format** | SocialCalc (.socialcalc) | OOXML (.xlsx) | ODF (.ods) |
| **.xlsx import/export** | No | Yes (native) | Yes (strong) |
| **Real-time collaboration** | Yes | Yes | Yes |
| **Multi-user editing** | Unlimited | 20+ concurrent | 20+ concurrent |
| **Formula support** | Basic (SUM, IF, VLOOKUP, etc.) | Extensive (Excel-compatible) | Extensive (LibreOffice-compatible) |
| **Pivot tables** | No | Yes | Yes |
| **Chart types** | Basic | 15+ types | 20+ types |
| **Conditional formatting** | No | Yes | Yes |
| **Macros / scripting** | No | JavaScript macros | LibreOffice Basic / Python |
| **Data validation** | No | Yes | Yes |
| **Freeze panes** | No | Yes | Yes |
| **Comments / notes** | No | Yes | Yes |
| **Change tracking** | No | Yes | Yes |
| **Docker image size** | ~150 MB | ~1.2 GB | ~1.5 GB |
| **Minimum RAM** | 256 MB | 2 GB | 2 GB |
| **Mobile responsive** | Partial | Yes | Yes |
| **License** | CPAL 1.0 | AGPL v3 | MPL 2.0 |

## Choosing the Right Tool

The decision comes down to your specific needs:

**Choose EtherCalc if** you need a lightweight, no-frills spreadsheet for quick collaborative work — shared budgets, simple trackers, ad-hoc data entry. Its tiny footprint means you can run it on a $5/month VPS alongside other services. The tradeoff is limited formula support and no .xlsx compatibility.

**Choose OnlyOffice Calc if** your team works primarily with Excel files and needs high-fidelity compatibility. If you are migrating from Google Sheets or Excel Online and want the least disruption, OnlyOffice Calc's native .xlsx support and familiar ribbon-style interface make the transition smooth. The moderate resource requirements (2 GB RAM minimum) are reasonable for a small team server.

**Choose Collabora Calc if** you need the most powerful spreadsheet engine available in open source. Complex financial models, data analysis with pivot tables, advanced charting, and macro automation all work well in Collabora Calc. It is the best choice if your organization already uses Nextcloud, as the integration is seamless.

## Deploying EtherCalc with Docker

EtherCalc is the simplest to deploy. A single Docker Compose file gets you a fully functional collaborative spreadsheet server:

```yaml
version: '3.8'

services:
  ethercalc:
    image: audreyt/ethercalc:latest
    container_name: ethercalc
    restart: unless-stopped
    ports:
      - "8080:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    container_name: ethercalc-redis
    restart: unless-stopped
    volumes:
      - ethercalc-data:/data

volumes:
  ethercalc-data:
```

Save this as `docker-compose.yml` and run:

```bash
docker compose up -d
```

Your EtherCalc instance will be available at `http://your-server:8080`. Create a new spreadsheet by clicking the "New Spreadsheet" button — each spreadsheet gets its own URL that you can share with collaborators.

For production use, add a reverse proxy with HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name sheets.example.com;

    ssl_certificate /etc/letsencrypt/live/sheets.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sheets.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Deploying OnlyOffice Docs with Docker

OnlyOffice requires a bit more setup but delivers a much richer feature set:

```yaml
version: '3.8'

services:
  onlyoffice:
    image: onlyoffice/documentserver:latest
    container_name: onlyoffice
    restart: unless-stopped
    ports:
      - "8080:80"
      - "443:443"
    environment:
      - JWT_ENABLED=true
      - JWT_SECRET=your-secret-key-here-change-in-production
    volumes:
      - onlyoffice-data:/var/www/onlyoffice/Data
      - onlyoffice-logs:/var/log/onlyoffice
      - onlyoffice-certs:/var/www/onlyoffice/Data/certs

volumes:
  onlyoffice-data:
  onlyoffice-logs:
  onlyoffice-certs:
```

```bash
docker compose up -d
```

OnlyOffice Docs exposes a document server that can work standalone or integrate with Nextcloud, ownCloud, or other platforms. To use it standalone, access the built-in test example at `http://your-server:8080/web-apps/apps/api/documents/api` — but for real usage, you will want to connect it to a file storage backend.

**Integration with Nextcloud:**

Install the ONLYOFFICE connector app in Nextcloud, then configure it to point to your document server URL (`http://your-server:8080`). Set the JWT secret to match the one in your Docker Compose file. Once connected, every .xlsx file in your Nextcloud opens in OnlyOffice Calc with full real-time collaboration.

**Security hardening:**

```bash
# Enable JWT authentication (already done via environment variable above)
# Restrict access to your internal network
# Set up SSL certificates inside the container:
docker exec onlyoffice bash -c "cp /etc/onlyoffice/documentserver/certs/your-cert.pem /var/www/onlyoffice/Data/certs/"
docker exec onlyoffice bash -c "cp /etc/onlyoffice/documentserver/certs/your-key.pem /var/www/onlyoffice/Data/certs/"
docker restart onlyoffice
```

## Deploying Collabora Online with Docker

Collabora Online deployment is similar to OnlyOffice but uses a different base image and integration model:

```yaml
version: '3.8'

services:
  collabora:
    image: collabora/code:latest
    container_name: collabora
    restart: unless-stopped
    ports:
      - "9980:9980"
    environment:
      - domain=nextcloud\.example\.com
      - username=admin
      - password=your-admin-password
      - extra_params=--o:ssl.enable=false --o:ssl.termination=true
    cap_add:
      - MKNOD
    volumes:
      - collabora-data:/cool/userassets

volumes:
  collabora-data:
```

```bash
docker compose up -d
```

The `domain` parameter is critical — it tells Collabora which Nextcloud (or other WOPI host) is allowed to connect. Use a regex pattern if you have multiple subdomains. The `ssl.termination=true` flag assumes you are running a reverse proxy that handles HTTPS.

**Nginx reverse proxy for Collabora:**

```nginx
server {
    listen 443 ssl http2;
    server_name collabora.example.com;

    ssl_certificate /etc/letsencrypt/live/collabora.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/collabora.example.com/privkey.pem;

    # static files
    location ^~ /browser {
        proxy_pass http://localhost:9980;
        proxy_set_header Host $http_host;
    }

    # WOPI discovery URL
    location ^~ /hosting/discovery {
        proxy_pass http://localhost:9980;
        proxy_set_header Host $http_host;
    }

    # main websocket
    location ~ ^/cool/(.*)/ws$ {
        proxy_pass http://localhost:9980;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $http_host;
        proxy_read_timeout 36000s;
    }

    # download, presentation and image upload
    location ~ ^/(c|l)ool {
        proxy_pass http://localhost:9980;
        proxy_set_header Host $http_host;
    }

    # Admin Console
    location ~ ^/admin {
        proxy_pass http://localhost:9980;
        proxy_set_header Host $http_host;
    }
}
```

## Migrating from Google Sheets

Moving your existing Google Sheets data to a self-hosted solution requires a few steps:

**Step 1: Export your Google Sheets data.**
Open each spreadsheet in Google Sheets, go to File > Download, and select Microsoft Excel (.xlsx). For large organizations with dozens of spreadsheets, use Google Takeout to bulk export all Google Drive files.

**Step 2: Test compatibility.**
Open the exported .xlsx files in your chosen self-hosted tool. EtherCalc will not support .xlsx natively — you will need to recreate the spreadsheet structure manually or use a conversion tool. OnlyOffice Calc and Collabora Calc both handle .xlsx import well, but complex features like Google Apps Script macros, connected charts, and IMPORTRANGE functions will not transfer and need manual recreation.

**Step 3: Set up access control.**
Configure user authentication on your self-hosted instance. EtherCalc does not include built-in authentication — you will need to put it behind a reverse proxy with basic auth or integrate it with an auth provider. OnlyOffice and Collabora both support integration with SSO, LDAP, and OAuth through their host platforms (Nextcloud, ownCloud).

**Step 4: Train your team.**
If moving to OnlyOffice Calc, the ribbon interface will feel familiar to Excel users. Collabora Calc's interface mirrors LibreOffice, which has a slightly different layout. EtherCalc is minimal and requires almost no training — the grid and toolbar are self-explanatory.

## Performance and Scaling

**EtherCalc** is exceptionally lightweight. A single VPS with 1 CPU and 512 MB RAM can comfortably serve 20+ simultaneous users editing different spreadsheets. Redis handles persistence, and the Node.js server process uses minimal memory. The bottleneck is not compute but browser performance — very large spreadsheets with thousands of formulas will slow down the client-side rendering.

**OnlyOffice Docs** is more resource-intensive. The document server runs multiple Node.js processes and a document converter service. Minimum recommended specs are 2 CPU cores and 2 GB RAM for up to 20 concurrent editors. For larger teams, scale horizontally by running multiple document server instances behind a load balancer.

**Collabora Online** has similar requirements to OnlyOffice. Each collaborative session spawns a separate LibreOffice process (called a "kit"), which consumes roughly 150-300 MB RAM each. For 20 concurrent sessions, plan for 4-6 GB RAM. Collabora supports coolwsd (the Collabora Online WebSocket Daemon) clustering for horizontal scaling, where multiple CODE instances share a common storage backend.

## Backup and Disaster Recovery

Regardless of which tool you choose, implement regular backups:

```bash
#!/bin/bash
# Backup script for EtherCalc (Redis data)
BACKUP_DIR="/opt/backups/ethercalc"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Dump Redis database
docker exec ethercalc-redis redis-cli SAVE
docker cp ethercalc-redis:/data/dump.rdb "$BACKUP_DIR/redis_$TIMESTAMP.rdb"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/redis_$TIMESTAMP.rdb"
```

For OnlyOffice and Collabora, back up the Docker volumes and any connected file storage (Nextcloud data directory, database). A simple cron job running `docker compose exec` or volume-level `rsync` to an offsite location provides adequate protection for most use cases.

## Final Verdict

There is no single "best" self-hosted spreadsheet — the right choice depends on what you need:

- **EtherCalc** is the quickest to deploy and lightest to run. Perfect for individuals and small teams who need basic collaborative spreadsheets without the overhead of a full office suite.

- **OnlyOffice Calc** delivers the best Excel compatibility and a polished interface. If your workflow revolves around .xlsx files and you want the closest experience to Google Sheets, this is your tool.

- **Collabora Calc** offers the most powerful calculation engine and advanced features. For data analysts, financial planners, and organizations already invested in the LibreOffice ecosystem, it is the clear winner.

All three are open-source, free to self-host, and give you something Google Sheets never will: complete ownership of your data. Pick the one that matches your complexity needs, deploy it with Docker, and start reclaiming your spreadsheets.

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
