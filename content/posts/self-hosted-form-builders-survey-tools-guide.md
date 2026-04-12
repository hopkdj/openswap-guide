---
title: "Best Self-Hosted Form Builders & Survey Tools 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted form builders and survey tools — LimeSurvey, Formbricks, and OhMyForm compared. Own your data, protect respondent privacy."
---

If you run a business, manage a community, or simply want to collect feedback from users, forms and surveys are unavoidable. But every time you embed a Typeform widget or send out a Google Forms link, you're handing someone else your respondents' data — their answers, their email addresses, sometimes their IP addresses and behavioral patterns.

For organizations that take privacy seriously, or for anyone who wants full control over their data pipeline, self-hosted form builders are the only option that makes sense. This guide covers the three best open-source survey and form platforms you can run on your own server in 2026: **LimeSurvey**, **Formbricks**, and **OhMyForm**.

## Why Self-Host Your Forms and Surveys

The arguments for owning your form infrastructure are the same as for any self-hosted service, but they're especially strong when it comes to survey data:

**Data ownership and privacy.** Your respondents' answers never leave your server. No third-party analytics, no data mining, no surprise terms-of-service changes. You control retention, deletion, and access policies end to end.

**GDPR and compliance.** When you self-host, you define the data lifecycle. You can configure data anonymization, set automatic deletion schedules, and keep everything within your jurisdiction's legal boundaries without relying on a vendor's compliance promises.

**No rate limits or response caps.** Typeform limits free accounts to 10 responses per month. Google Forms stops you at a certain point too. Self-hosted tools have zero artificial limits — collect 50 responses or 500,000, it doesn't matter.

**Deep customization.** Want to white-label your surveys with your own branding? Add custom CSS, integrate with your internal authentication system, or pipe responses directly into your database? Self-hosted tools give you that flexibility.

**Long-term archival.** Survey data is often needed for years — academic research, compliance audits, trend analysis. When your data lives on your own infrastructure, you decide how long it stays and in what format.

## LimeSurvey: The Enterprise-Grade Survey Platform

[LimeSurvey](https://www.limesurvey.org/) is the most mature open-source survey platform available. It has been in active development since 2006 and powers surveys for universities, governments, and enterprises worldwide. If you need statistical rigor, complex branching logic, and multilingual support, this is the tool.

### Key Features

- **20+ question types** including array, multiple choice with comments, ranking, file upload, equation, and boilerplate text
- **Advanced branching and quotas** — build complex survey flows with skip logic, relevance equations, and response quotas
- **Multilingual surveys** — manage translations within the platform, switch languages per respondent
- **Statistical analysis** — built-in descriptive statistics, cross-tabulations, and export to SPSS, R, and CSV
- **Token management** — generate invitation tokens for controlled access surveys, track open/completion rates
- **REST API** — full JSON-RPC API for programmatic survey creation and response retrieval

### Docker Installation

```yaml
# docker-compose.yml for LimeSurvey
version: "3.8"

services:
  db:
    image: mariadb:10.11
    container_name: limesurvey-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: your-root-password
      MYSQL_DATABASE: limesurvey
      MYSQL_USER: limesurvey
      MYSQL_PASSWORD: your-db-password
    volumes:
      - limesurvey-db:/var/lib/mysql
    networks:
      - limesurvey-net

  limesurvey:
    image: acdsp/limesurvey:latest
    container_name: limesurvey
    restart: unless-stopped
    ports:
      - "8080:8082"
    environment:
      DB_TYPE: "mysql"
      DB_HOST: "db"
      DB_PORT: "3306"
      DB_NAME: "limesurvey"
      DB_USER: "limesurvey"
      DB_PASSWORD: "your-db-password"
      ADMIN_USER: "admin"
      ADMIN_PASSWORD: "your-admin-password"
      ADMIN_NAME: "Survey Admin"
      ADMIN_EMAIL: "admin@example.com"
    depends_on:
      - db
    volumes:
      - limesurvey-upload:/app/upload
    networks:
      - limesurvey-net

volumes:
  limesurvey-db:
  limesurvey-upload:

networks:
  limesurvey-net:
    driver: bridge
```

Start it up:

```bash
docker compose up -d
```

Then navigate to `http://your-server:8080` and log in with the admin credentials you configured.

### Creating Your First Survey

1. Go to **Surveys** → **Create survey**
2. Set a title, description, and welcome text
3. Choose your base language and optionally add translations
4. Under **Question themes**, pick a template or customize with your own CSS
5. Add question groups to organize sections (demographics, feedback, satisfaction, etc.)
6. Add questions to each group, configuring type, validation rules, and display options
7. Activate the survey and share the public link or generate invitation tokens

### When to Choose LimeSurvey

Pick LimeSurvey when you need enterprise-grade survey capabilities: academic research, customer satisfaction programs, employee engagement surveys, or anything requiring statistical analysis and complex question logic. It's overkill for a simple contact form, but unmatched for serious survey work.

## Formbricks: The Modern Experience Management Platform

[Formbricks](https://formbricks.com/) is a newer entrant that positions itself as an open-source alternative to Typeform and Hotjar combined. It's built with modern web technologies and excels at website surveys, in-app feedback, and multi-step form experiences. If you want beautiful, conversion-optimized forms that look great on any device, Formbricks is a strong choice.

### Key Features

- **Website surveys** — embed pop-up, slide-in, or full-page surveys directly on your site
- **In-app feedback widgets** — collect user feedback without leaving your application
- **Link surveys** — shareable multi-step forms (the Typeform alternative)
- **Targeting and triggers** — show surveys based on URL, user attributes, or custom events
- **Action classes** — connect surveys to user actions like page views, clicks, or custom JS triggers
- **Beautiful UI out of the box** — modern, responsive design that requires zero customization
- **Webhook integrations** — pipe responses to Slack, Discord, Zapier, or any endpoint
- **Self-hosted with a generous open-source core** — all core features are available in the CE edition

### Docker Installation

Formbricks requires a PostgreSQL database and optionally Redis for caching:

```yaml
# docker-compose.yml for Formbricks
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: formbricks-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: formbricks
      POSTGRES_PASSWORD: your-db-password
      POSTGRES_DB: formbricks
    volumes:
      - formbricks-db:/var/lib/postgresql/data
    networks:
      - formbricks-net

  redis:
    image: redis:7-alpine
    container_name: formbricks-redis
    restart: unless-stopped
    volumes:
      - formbricks-redis:/data
    networks:
      - formbricks-net

  formbricks:
    image: ghcr.io/formbricks/formbricks:latest
    container_name: formbricks
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      WEBAPP_URL: "http://your-server:3000"
      NEXTAUTH_URL: "http://your-server:3000"
      NEXTAUTH_SECRET: "generate-a-random-secret-here"
      DATABASE_URL: "postgresql://formbricks:your-db-password@postgres:5432/formbricks"
      REDIS_URL: "redis://redis:6379"
      ENCRYPTION_KEY: "generate-another-random-key"
      NEXT_PUBLIC_ENCRYPTION_KEY: "same-encryption-key-as-above"
      CRON_SECRET: "generate-a-cron-secret"
      EMAIL_FROM: "noreply@example.com"
      SMTP_HOST: "smtp.example.com"
      SMTP_PORT: "587"
      SMTP_USER: "your-smtp-user"
      SMTP_PASSWORD: "your-smtp-password"
    depends_on:
      - postgres
      - redis
    networks:
      - formbricks-net

volumes:
  formbricks-db:
  formbricks-redis:

networks:
  formbricks-net:
    driver: bridge
```

Generate the required secrets:

```bash
# Generate NEXTAUTH_SECRET
openssl rand -base64 32

# Generate ENCRYPTION_KEY
openssl rand -base64 32

# Generate CRON_SECRET
openssl rand -base64 32
```

Then start the stack:

```bash
docker compose up -d
```

### Embedding a Website Survey

Once Formbricks is running, create a survey in the dashboard and get the embed snippet:

```html
<!-- Add to your website's <head> -->
<script
  type="text/javascript"
  src="http://your-server:3000/js/formbricks.umd.cjs"
></script>
<script>
  formbricks.init({
    environmentId: "your-environment-id",
    apiHost: "http://your-server:3000",
    userId: "unique-user-id", // optional, for user identification
    attributes: {
      plan: "premium",
      language: "en"
    }
  });
</script>
```

This lets you trigger surveys based on user behavior, target specific audience segments, and collect responses without any page redirect.

### When to Choose Formbricks

Formbricks is ideal for product teams, SaaS companies, and website owners who want to collect user feedback in context. If you need in-app surveys, NPS widgets, or multi-step forms that feel native to your brand, this is the right tool. It's less suited for academic research or highly structured questionnaires with complex skip logic.

## OhMyForm: The Lightweight, Developer-Friendly Option

[OhMyForm](https://ohmyform.com/) takes a minimalist approach. It's a form builder that focuses on doing one thing well: creating forms and collecting responses. The interface is clean, the codebase is small, and it's easy to extend. If you want something that gets out of your way and just works, OhMyForm deserves a look.

### Key Features

- **Drag-and-drop form builder** — intuitive interface for assembling forms quickly
- **Multiple question types** — text, email, number, date, dropdown, radio, checkbox, file upload
- **Form theming** — customize colors, fonts, and layout to match your brand
- **Response management** — view, export, and manage submissions from the dashboard
- **REST API** — programmatic access for integrating forms into existing workflows
- **Lightweight footprint** — minimal resource requirements, runs easily on a small VPS
- **Multi-user support** — role-based access for teams managing multiple forms

### Docker Installation

```yaml
# docker-compose.yml for OhMyForm
version: "3.8"

services:
  db:
    image: postgres:16-alpine
    container_name: ohmyform-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ohmyform
      POSTGRES_PASSWORD: your-db-password
      POSTGRES_DB: ohmyform
    volumes:
      - ohmyform-db:/var/lib/postgresql/data
    networks:
      - ohmyform-net

  ohmyform:
    image: ohmyform/ohmyform:latest
    container_name: ohmyform
    restart: unless-stopped
    ports:
      - "3001:3000"
    environment:
      DATABASE_URL: "postgresql://ohmyform:your-db-password@db:5432/ohmyform"
      SECRET_KEY: "your-secret-key-change-this"
      ADMIN_EMAIL: "admin@example.com"
      ADMIN_PASSWORD: "your-admin-password"
      APP_URL: "http://your-server:3001"
      MAILER_URL: "smtp://smtp.example.com:587?user=your-smtp-user&password=your-smtp-password"
    depends_on:
      - db
    volumes:
      - ohmyform-uploads:/app/uploads
    networks:
      - ohmyform-net

volumes:
  ohmyform-db:
  ohmyform-uploads:

networks:
  ohmyform-net:
    driver: bridge
```

Launch it:

```bash
docker compose up -d
```

Access the admin panel at `http://your-server:3001/admin`.

### Creating a Simple Feedback Form

1. Log in and navigate to the **Forms** section
2. Click **Create Form** and set a title and description
3. Use the drag-and-drop builder to add questions — reorder by dragging
4. Configure each question's validation (required fields, email format, min/max length)
5. Set up email notifications for new submissions if needed
6. Publish the form and share the generated URL or embed it via iframe

### When to Choose OhMyForm

OhMyForm is perfect when you need straightforward forms without enterprise overhead. Internal feedback forms, event registration, contact forms, simple surveys — anything where you want to spin up a form in five minutes and forget about the infrastructure.

## Feature Comparison

| Feature | LimeSurvey | Formbricks | OhMyForm |
|---------|-----------|------------|----------|
| **Primary use case** | Academic & enterprise surveys | In-app & website feedback | Simple forms & surveys |
| **Question types** | 20+ | ~12 | ~8 |
| **Branching logic** | Advanced (equations, relevance) | Basic (conditional display) | Basic (skip logic) |
| **Multilingual** | Yes, built-in translation manager | Yes | No |
| **Self-hosted** | Yes (AGPL-3.0) | Yes (AGPL-3.0) | Yes (AGPL-3.0) |
| **Docker support** | Yes, official image | Yes, official image | Yes, official image |
| **API** | JSON-RPC REST API | REST API + SDK | REST API |
| **Webhooks** | Via plugin | Native | Via plugin |
| **Analytics** | Statistical analysis, crosstabs | Response dashboard, funnel view | Basic response list |
| **Team collaboration** | User roles, token management | Team workspaces | Multi-user with roles |
| **File uploads** | Yes, with size limits | Yes | Yes |
| **Custom themes** | Full CSS/HTML template system | Theme customizer | Color/font customization |
| **Resource usage** | Moderate (PHP + MySQL) | Higher (Node.js + PostgreSQL) | Light (Node.js + PostgreSQL) |
| **Learning curve** | Steep | Low | Very low |

## Reverse Proxy Setup

All three tools should sit behind a reverse proxy for TLS termination. Here's a Caddy configuration that handles all three on the same server:

```caddyfile
# Caddyfile

survey.example.com {
    reverse_proxy localhost:8080
    encode gzip
}

feedback.example.com {
    reverse_proxy localhost:3000
    encode gzip
}

forms.example.com {
    reverse_proxy localhost:3001
    encode gzip
}
```

Caddy automatically obtains and renews TLS certificates. No manual certificate management needed.

If you prefer Nginx:

```nginx
# /etc/nginx/sites-available/survey.example.com
server {
    listen 80;
    server_name survey.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then enable the site and get a certificate with Certbot:

```bash
sudo ln -s /etc/nginx/sites-available/survey.example.com /etc/nginx/sites-enabled/
sudo certbot --nginx -d survey.example.com
```

## Security Best Practices

**Enable HTTPS everywhere.** Use Caddy or Nginx with Certbot to serve all form endpoints over TLS. Never collect personal data over plain HTTP.

**Rate limit submissions.** Protect your forms from spam and abuse by adding rate limiting at the reverse proxy level:

```nginx
# Nginx rate limiting
limit_req_zone $binary_remote_addr zone=forms:10m rate=10r/m;

server {
    location / {
        limit_req zone=forms burst=5 nodelay;
        proxy_pass http://127.0.0.1:8080;
    }
}
```

**Regular backups.** Dump your databases on a schedule:

```bash
#!/bin/bash
# backup-forms.sh — add to cron for daily backups

BACKUP_DIR="/opt/backups/forms"
DATE=$(date +%Y-%m-%d)

# LimeSurvey (MySQL/MariaDB)
mysqldump -u limesurvey -p limesurvey | gzip > "$BACKUP_DIR/limesurvey-$DATE.sql.gz"

# Formbricks (PostgreSQL)
pg_dump -U formbricks formbricks | gzip > "$BACKUP_DIR/formbricks-$DATE.sql.gz"

# OhMyForm (PostgreSQL)
pg_dump -U ohmyform ohmyform | gzip > "$BACKUP_DIR/ohmyform-$DATE.sql.gz"

# Keep only 30 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

Add to crontab:

```bash
0 3 * * * /opt/scripts/backup-forms.sh
```

**Keep images updated.** Set up Watchtower or a similar tool to automatically pull new images:

```yaml
# Add to your docker-compose.yml
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --schedule "0 0 4 * * *" --cleanup
```

## Which Tool Should You Pick?

The answer depends entirely on your use case:

**Choose LimeSurvey** if you need rigorous survey methodology — complex skip logic, quota management, statistical analysis, multilingual support, or anything that resembles academic or enterprise research. It's the most powerful option but requires the most time to learn.

**Choose Formbricks** if you're a product team or website owner looking for beautiful, contextual feedback collection. The in-app survey capabilities, targeting system, and modern UI make it the best Typeform alternative for user experience research.

**Choose OhMyForm** if you need simple forms fast with minimal overhead. Internal feedback, event registration, contact forms — anything where a lightweight, no-nonsense tool is preferable to a feature-heavy platform.

All three are open-source, self-hostable, and give you complete ownership of your data. The best practice? Try each one in a Docker container for an afternoon. Build the same form in all three and see which workflow clicks with your team. You can't go wrong with any of them.
