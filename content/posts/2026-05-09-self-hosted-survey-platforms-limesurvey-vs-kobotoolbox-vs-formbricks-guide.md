---
title: "Self-Hosted Survey Platforms: LimeSurvey vs KoboToolbox vs Formbricks (2026)"
date: "2026-05-09"
tags: ["comparison", "guide", "self-hosted", "survey", "data-collection"]
draft: false
description: "Compare LimeSurvey, KoboToolbox, and Formbricks for self-hosted surveys. Docker Compose setups, feature comparison, and deployment guide."
---

Self-hosted survey platforms give organizations full control over respondent data, survey logic, and customization — without sending sensitive feedback to third-party SaaS providers. Whether you are running academic research, customer satisfaction surveys, or internal employee feedback, having your own survey server means complete data ownership and no per-response pricing tiers.

In this guide, we compare three leading open-source survey platforms: **LimeSurvey**, **KoboToolbox**, and **Formbricks**. Each offers a different approach to survey design, deployment complexity, and target audience.

## Platform Overview

| Feature | LimeSurvey | KoboToolbox | Formbricks |
|---------|-----------|-------------|------------|
| GitHub Stars | 3,590+ | 170+ (KPI) | 5,000+ |
| Language | PHP / MySQL | Python / PostgreSQL | TypeScript / PostgreSQL |
| Primary Use | Enterprise surveys | Field data collection | Product feedback |
| Docker Support | Official image | Docker Compose | Official image |
| Mobile Offline | No | Yes (ODK Collect) | No |
| Survey Logic | Advanced skip/branch | Skip logic, validation | Basic logic |
| Multi-language | Yes (80+ languages) | Yes | Yes |
| API | REST API | REST API | REST API |
| License | GPL-2.0 | Apache 2.0 | AGPL-3.0 |
| Best For | Large organizations | NGOs, field research | SaaS product teams |

**LimeSurvey** is the most mature and feature-rich option, supporting complex survey logic, 80+ languages, and enterprise-scale deployments. It has been around since 2005 and is used by universities, governments, and corporations worldwide.

**KoboToolbox** is designed for field data collection in challenging environments. It supports offline data capture through ODK Collect on Android devices, making it ideal for NGOs and humanitarian organizations working in areas with limited connectivity.

**Formbricks** is the newest entrant, focusing on product experience surveys and in-app feedback. It is built with modern TypeScript and integrates well with developer workflows.

## Installation with Docker Compose

### LimeSurvey

LimeSurvey requires a MySQL/MariaDB database and a web server. The official Docker image handles the PHP application layer:

```yaml
version: '3.8'

services:
  limesurvey-db:
    image: mariadb:11
    environment:
      MYSQL_ROOT_PASSWORD: limesurvey_root
      MYSQL_DATABASE: limesurvey
      MYSQL_USER: limesurvey
      MYSQL_PASSWORD: limesurvey_pass
    volumes:
      - limesurvey_db:/var/lib/mysql
    restart: unless-stopped

  limesurvey:
    image: limesurvey/limesurvey:6-apache
    ports:
      - "8080:80"
    environment:
      LIMESURVEY_DB_HOST: limesurvey-db
      LIMESURVEY_DB_NAME: limesurvey
      LIMESURVEY_DB_USER: limesurvey
      LIMESURVEY_DB_PASSWORD: limesurvey_pass
      ADMIN_USER: admin
      ADMIN_PASSWORD: admin123
      ADMIN_EMAIL: admin@example.com
    depends_on:
      - limesurvey-db
    restart: unless-stopped

volumes:
  limesurvey_db:
```

Start with `docker compose up -d` and access the admin panel at `http://localhost:8080/admin`. The first login uses the credentials set in the environment variables.

### KoboToolbox

KoboToolbox provides an official Docker Compose setup through the `kobo-install` script, which orchestrates multiple services:

```bash
# Clone the official installer
git clone https://github.com/kobotoolbox/kobo-install.git
cd kobo-install

# Run the interactive setup (configures all services)
python3 run.py --setup
```

The full deployment includes PostgreSQL, MongoDB, Redis, Nginx, and the KPI/KoBoCAT application servers. For a manual Docker Compose approach:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: koboform
      POSTGRES_USER: kobo
      POSTGRES_PASSWORD: kobo_password
    volumes:
      - kobo_pg:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  kobocat:
    image: kobotoolbox/kobocat
    environment:
      DATABASE_URL: postgresql://kobo:kobo_password@postgres:5432/koboform
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8081:80"
    depends_on:
      - postgres
      - redis

volumes:
  kobo_pg:
```

### Formbricks

Formbricks has the simplest Docker deployment of the three:

```yaml
version: '3.8'

services:
  formbricks-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: formbricks
      POSTGRES_USER: formbricks
      POSTGRES_PASSWORD: formbricks_secret
    volumes:
      - formbricks_db:/var/lib/postgresql/data

  formbricks:
    image: ghcr.io/formbricks/formbricks:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://formbricks:formbricks_secret@formbricks-db:5432/formbricks
      NEXTAUTH_SECRET: your-nextauth-secret-key
      NEXTAUTH_URL: http://localhost:3000
      ENCRYPTION_KEY: your-encryption-key
    depends_on:
      - formbricks-db
    restart: unless-stopped

volumes:
  formbricks_db:
```

Run `docker compose up -d` and open `http://localhost:3000` to create your account. Formbricks handles database migrations automatically on first startup.

## Survey Design Capabilities

### Question Types

**LimeSurvey** supports the most extensive question type library: single choice, multiple choice, array questions, ranking, file upload, equation, and text display. It also supports custom question attributes and conditional display logic.

**KoboToolbox** uses the ODK XForms standard, supporting all standard ODK question types including GPS coordinates, barcode scanning, audio recording, and photo capture. This makes it uniquely suited for field data collection where multimedia evidence is needed.

**Formbricks** focuses on survey types relevant to product teams: multiple choice, open text, rating scales, NPS (Net Promoter Score), and CTA (Call to Action) buttons. The question set is smaller but covers the most common product feedback scenarios.

### Logic and Branching

LimeSurvey offers the most sophisticated logic engine with relevance equations, quota management, and answer piping. KoboToolbox supports skip logic and form validation through the XForms standard. Formbricks provides basic display conditions based on previous answers.

## Data Export and Analysis

All three platforms support CSV and Excel export. LimeSurvey additionally supports SPSS, R, and PDF output formats. KoboToolbox exports include GPS data in GeoJSON format and supports attachment downloads. Formbricks offers webhooks for real-time data forwarding to external systems.

## Scaling and Performance

LimeSurvey handles thousands of concurrent respondents with proper database tuning and horizontal scaling through load balancers. KoboToolbox scales to handle massive humanitarian deployments with millions of submissions. Formbricks is designed for high-velocity product feedback with low-latency survey rendering.

## Security Considerations

For survey platforms handling sensitive respondent data, consider these security measures:

- **TLS termination**: Always place a reverse proxy (Nginx, Traefik, or Caddy) in front of the survey application to enforce HTTPS
- **Database encryption**: Enable encryption at rest for stored survey responses, especially for PII data
- **Access controls**: Implement role-based access with separate accounts for survey designers, analysts, and administrators
- **Audit logging**: Enable access logging to track who views or exports survey data
- **Regular backups**: Schedule automated database backups with tested restore procedures

For detailed reverse proxy configuration, see our [Traefik vs Nginx comparison](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide/) for deployment patterns.

## Choosing the Right Survey Platform

| Scenario | Recommended Tool |
|----------|-----------------|
| Enterprise with complex survey logic | LimeSurvey |
| Field data collection in remote areas | KoboToolbox |
| Product feedback and in-app surveys | Formbricks |
| Academic research with multi-language needs | LimeSurvey |
| Humanitarian data collection with offline support | KoboToolbox |
| Developer-friendly API-first approach | Formbricks |

## Why Self-Host Your Survey Platform?

Running your own survey server provides several advantages over SaaS alternatives like SurveyMonkey or Google Forms:

**Data Ownership and Privacy**: When you self-host, respondent data never leaves your infrastructure. This is critical for organizations handling sensitive information — healthcare surveys, employee feedback, government research, or academic studies with IRB requirements. GDPR and HIPAA compliance become straightforward when data stays within your controlled environment.

**No Response Limits or Per-User Pricing**: SaaS survey tools typically charge per response or per active user. Self-hosted platforms eliminate these constraints entirely. You can collect unlimited responses from unlimited participants without worrying about escalating costs as your survey program grows.

**Complete Customization**: Open-source survey platforms allow you to modify the UI, add custom question types, integrate with internal authentication systems (LDAP, SAML, OAuth), and embed surveys into your own applications. SaaS tools limit you to their predefined feature set.

**Branding Control**: Self-hosted surveys carry your own branding, not a third-party company's logo. This is important for maintaining professional credibility and respondent trust, especially in academic and corporate environments.

**Integration with Existing Infrastructure**: Connect your survey data directly to internal databases, BI tools, and analytics pipelines. For organizations already running self-hosted data infrastructure — such as [self-hosted log management stacks](../self-hosted-log-management-loki-graylog-opensearch/) or [database management platforms](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide/) — adding a survey platform integrates naturally into your existing ecosystem.

## FAQ

### Which survey platform is easiest to deploy?

Formbricks has the simplest Docker setup with just two services (application + PostgreSQL). LimeSurvey requires MySQL/MariaDB plus the PHP application. KoboToolbox is the most complex, requiring PostgreSQL, MongoDB, Redis, and multiple application servers — though the official `kobo-install` script handles most of the configuration automatically.

### Can KoboToolbox surveys work offline?

Yes. KoboToolbox supports offline data collection through ODK Collect on Android devices. Surveyors download forms while connected, collect data offline (including photos, GPS coordinates, and audio), and sync submissions when connectivity is restored. This is its key differentiator from LimeSurvey and Formbricks.

### Does LimeSurvey support anonymous surveys?

Yes. LimeSurvey can be configured to collect responses without requiring respondent authentication. You can also enable token-based access for controlled surveys where only invited participants can respond, while still keeping individual responses anonymous.

### How do I add custom branding to survey forms?

LimeSurvey supports custom themes through its template system — you can modify HTML, CSS, and JavaScript. Formbricks allows theme customization through its admin interface and supports custom CSS injection. KoboToolbox supports custom branding through its server configuration and form design settings.

### Can I embed surveys on my website?

Formbricks is specifically designed for this use case — it provides JavaScript snippets to embed surveys directly into web applications. LimeSurvey supports iframe embedding and public survey links. KoboToolbox provides web form links but is primarily designed for standalone survey deployment rather than embedding.

### How do I migrate survey data between platforms?

All three platforms support CSV/Excel export and import. For complex migrations involving survey logic and question types, you will need to manually recreate the survey structure and import response data. LimeSurvey's LSS export format is proprietary, while KoboToolbox uses the open XForms standard.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Survey Platforms: LimeSurvey vs KoboToolbox vs Formbricks (2026)",
  "description": "Compare LimeSurvey, KoboToolbox, and Formbricks for self-hosted surveys. Docker Compose setups, feature comparison, and deployment guide.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
