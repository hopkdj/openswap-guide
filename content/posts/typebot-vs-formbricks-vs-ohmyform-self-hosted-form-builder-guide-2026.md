---
title: "Typebot vs Formbricks vs OhMyForm: Best Self-Hosted Form Builders 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare three self-hosted form builders — Typebot, Formbricks, and OhMyForm. Docker deployment guides, feature comparison, and when to choose each platform in 2026."
---

Collecting data through forms is essential for every business, team, and developer. Whether you are running customer feedback surveys, building lead capture funnels, creating interactive quizzes, or gathering user research, the form tool you choose shapes the entire experience. Cloud services like Typeform, SurveyMonkey, and Google Forms dominate the market — but they come with per-response pricing, data privacy concerns, and limited customization.

Self-hosted form builders change that equation entirely. You own the infrastructure, control every byte of data, and pay no per-response fees. In this guide, we compare three mature open-source platforms — [Typebot](https://typebot.io), [Formbricks](https://formbricks.com), and [OhMyForm](https://ohmyform.com) — and walk through complete Docker deployment for each.

For a broader overview of form-building tools and Typeform alternatives, see our [best self-hosted form builders guide](../best-self-hosted-form-builders-survey-tools-typeform-alternatives-2026/).

## Why Self-Host Your Form Builder

**Data privacy and compliance.** Every form response contains personal data — email addresses, opinions, sometimes sensitive business information. With self-hosting, responses never leave your servers. This matters enormously for GDPR, HIPAA, and enterprise compliance requirements. You decide retention policies, encryption standards, and access controls.

**Unlimited responses, zero per-submission fees.** Typeform charges based on response volume. A popular survey with 10,000 responses can cost hundreds of dollars per month on enterprise plans. A self-hosted instance on a $10/month VPS handles unlimited responses. The cost scales with your infrastructure, not your data volume.

**Full customization.** Self-hosted tools let you modify branding, email templates, form logic, and integrations. Embed forms directly into your application using native SDKs or webhooks. No third-party logos, no rate limits, no feature gates on enterprise plans.

**Deep integrations on your terms.** Connect forms to your existing CRM, database, or data pipeline without relying on Zapier or paid connectors. Webhooks, REST APIs, and direct database access mean your form data flows exactly where you need it. For workflow automation ideas, check our [n8n vs Huginn vs Activepieces guide](../huginn-vs-n8n-vs-activepieces-self-hosted-ifttt-alternatives-2026/).

## Typebot

Typebot is a conversational form builder that presents questions in a chat-style interface. Instead of static forms, users interact with your questionnaire through a flowing conversation that feels more natural and typically achieves higher completion rates.

**GitHub stats:** 9,881 stars · Last updated: April 21, 2026 · Language: TypeScript

### Key Features

- **Conversational interface** — chat-style form flow with typing indicators and animated bubbles
- **Visual drag-and-drop builder** — no code required to design complex form flows
- **Rich input types** — text, email, phone, date picker, file upload, payment buttons, image selection, buttons, and more
- **Advanced logic** — conditional branching, variable storage, skip logic, and calculator blocks
- **Webhook and API integrations** — send responses to any endpoint, Google Sheets, Zapier, Make, and n8n
- **Embed options** — embed as a bubble widget, full-page form, or inline component
- **Multi-language support** — build forms in multiple languages with automatic detection
- **Analytics dashboard** — view completion rates, drop-off points, and response statistics

### Docker Compose Deployment

Typebot requires PostgreSQL and Redis alongside the main application:

```yaml
services:
  typebot-db:
    image: postgres:16-alpine
    restart: always
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: typebot
      POSTGRES_PASSWORD: changeme_db_pass
      POSTGRES_DB: typebot
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U typebot"]
      interval: 10s
      timeout: 5s
      retries: 5

  typebot-redis:
    image: redis:7-alpine
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  typebot-builder:
    image: baptisteArno/typebot-builder:latest
    restart: always
    depends_on:
      typebot-db:
        condition: service_healthy
      typebot-redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://typebot:changeme_db_pass@typebot-db:5432/typebot
      REDIS_URL: redis://typebot-redis:6379
      ENCRYPTION_SECRET: changeme_secret_key_32chars
      NEXTAUTH_URL: http://localhost:3001
      NEXT_PUBLIC_VIEWER_URL: http://localhost:3000
    ports:
      - "3001:3000"

  typebot-viewer:
    image: baptisteArno/typebot-viewer:latest
    restart: always
    depends_on:
      typebot-db:
        condition: service_healthy
      typebot-redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://typebot:changeme_db_pass@typebot-db:5432/typebot
      REDIS_URL: redis://typebot-redis:6479
      ENCRYPTION_SECRET: changeme_secret_key_32chars
    ports:
      - "3000:3000"

volumes:
  db_data:
```

Deploy with `docker compose up -d`. The builder runs on port 3001 (admin panel) and the viewer serves published forms on port 3000.

### Best Use Cases

- Interactive customer onboarding flows
- Lead qualification chatbots
- Quizzes and assessments with conditional logic
- Multi-step surveys where engagement matters

## Formbricks

Formbricks positions itself as an open-source survey and experience management platform. It combines traditional forms with in-app survey widgets, website popups, and link-based surveys. The platform is designed for product teams who need to collect feedback at multiple touchpoints.

**GitHub stats:** 12,120 stars · Last updated: April 22, 2026 · Language: TypeScript

### Key Features

- **Multiple survey types** — link surveys, in-app widgets, website popups, and email surveys
- **Targeting and triggers** — show surveys based on user actions, page visits, or time on page
- **Survey templates** — pre-built templates for NPS, CSAT, product-market fit, feature requests, and more
- **Advanced question types** — multiple choice, rating scales, open text, ranking, file upload, CTA, consent
- **SDK integrations** — JavaScript SDK for web, React Native SDK for mobile apps
- **Team collaboration** — workspace sharing, role-based access control
- **Webhook and API** — real-time response forwarding to any endpoint
- **Self-hosted or cloud** — official Docker deployment for full data control

### Docker Compose Deployment

Formbricks requires PostgreSQL and optional RustFS for file storage:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: always
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: changeme_pg_pass
      POSTGRES_DB: formbricks
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  formbricks:
    image: ghcr.io/formbricks/formbricks:latest
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "3000:3000"
    environment:
      WEBAPP_URL: http://localhost:3000
      NEXTAUTH_URL: http://localhost:3000
      NEXTAUTH_SECRET: changeme_nextauth_secret_64chars
      DATABASE_URL: postgresql://postgres:changeme_pg_pass@postgres:5432/formbricks?schema=public
      ENCRYPTION_KEY: changeme_encryption_key_32chars
      CRON_SECRET: changeme_cron_secret
      SHORT_URL_BASE: http://localhost:3000
      ASSET_PREFIX_URL: http://localhost:3000
      ENTERPRISE_LICENSE_KEY: ""

volumes:
  pg_data:
```

Run `docker compose up -d` and access the admin panel at `http://localhost:3000`. Generate secure secrets using `openssl rand -hex 32` for `NEXTAUTH_SECRET` and `openssl rand -hex 16` for `ENCRYPTION_KEY`.

### Best Use Cases

- In-app user feedback collection
- NPS and CSAT surveys embedded in web applications
- Product research with targeted survey triggers
- Website visitor feedback popups
- Email-based survey campaigns

## OhMyForm

OhMyForm is a straightforward open-source form builder focused on creating traditional, field-based forms. It is the simplest of the three options, making it a good choice for teams that need basic form functionality without conversational interfaces or in-app widgets.

**GitHub stats:** 2,885 stars · Last updated: October 31, 2024 · Language: TypeScript

> **Note:** OhMyForm development has slowed significantly. The last update was in October 2024. For active development and regular feature updates, consider Typebot or Formbricks instead. OhMyForm is included here for completeness and for teams that prefer its minimal approach.

### Key Features

- **Simple form builder** — drag-and-drop interface for creating standard forms
- **Multiple field types** — text, textarea, email, number, date, dropdown, radio, checkbox, file upload
- **Custom themes** — basic theming support for form appearance
- **Response export** — download responses as CSV or JSON
- **Public form links** — share forms via unique URLs
- **Self-hosted deployment** — Docker Compose with PostgreSQL and Redis

### Docker Compose Deployment

OhMyForm uses a simpler stack with PostgreSQL and Redis:

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  ohmyform:
    image: ohmyform/ohmyform:latest
    restart: always
    depends_on:
      redis:
        condition: service_healthy
    ports:
      - "3000:3000"
    environment:
      CREATE_ADMIN: "TRUE"
      DATABASE_DRIVER: pg
      DATABASE_HOST: postgres
      DATABASE_PORT: 5432
      DATABASE_NAME: ohmyform
      DATABASE_USER: ohmyform
      DATABASE_PASSWORD: changeme_db_pass
      REDIS_URL: redis://redis:6379
      MAILER_URI: smtp://mail.example.com:587

  postgres:
    image: postgres:16-alpine
    restart: always
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: ohmyform
      POSTGRES_PASSWORD: changeme_db_pass
      POSTGRES_DB: ohmyform

volumes:
  db_data:
```

### Best Use Cases

- Simple contact forms and registration forms
- Internal data collection for small teams
- Scenarios where a conversational interface is unnecessary
- Projects prioritizing simplicity over advanced features

## Feature Comparison

| Feature | Typebot | Formbricks | OhMyForm |
|---|---|---|---|
| **Form Style** | Conversational chat | Multi-type (link, in-app, popup) | Traditional static forms |
| **Visual Builder** | Drag-and-drop flow | Drag-and-drop editor | Drag-and-drop editor |
| **Conditional Logic** | Advanced branching | Basic skip logic | Limited |
| **In-App Embedding** | Bubble widget | Native SDK (JS, React Native) | iframe embed only |
| **Question Types** | 20+ input types | 12+ question types | 10 field types |
| **Multi-Language** | Yes | Yes | No |
| **Analytics** | Built-in dashboard | Built-in dashboard | Response export only |
| **Webhooks** | Yes | Yes | Limited |
| **Team Collaboration** | Yes | Yes (role-based) | No |
| **API Access** | REST API | REST API | REST API |
| **Database** | PostgreSQL | PostgreSQL | PostgreSQL |
| **Cache/Queue** | Redis | None required | Redis |
| **Last Active Dev** | April 2026 | April 2026 | October 2024 |
| **GitHub Stars** | 9,881 | 12,120 | 2,885 |
| **Best For** | Interactive flows | Product feedback | Simple forms |

## How to Choose

**Choose Typebot if:** You need high-engagement conversational forms. The chat-style interface consistently outperforms traditional forms in completion rates. It is ideal for lead capture, onboarding flows, quizzes, and any scenario where you want the form to feel like a conversation rather than a questionnaire.

**Choose Formbricks if:** You need versatile survey distribution across multiple channels — in-app widgets, website popups, email links, and standalone survey pages. It is the best choice for product teams running NPS surveys, user research, and feature feedback campaigns. The targeting engine lets you show the right survey to the right user at the right moment.

**Choose OhMyForm if:** You need simple, traditional forms without complexity. If you just want to create a contact form, registration form, or basic data collection tool and do not need conversational flows or in-app embedding, OhMyForm provides the minimum viable solution. However, be aware that development has slowed — for long-term projects, prefer Typebot or Formbricks.

For teams also collecting user feedback through feature requests, see our [Fider vs LogChimp feedback platform comparison](../fider-vs-logchimp-self-hosted-feedback-feature-request-guide-2026/) for complementary tools.

## Deployment Checklist

Before going live with any self-hosted form builder:

1. **Set up HTTPS** — all form responses should be encrypted in transit. Use a reverse proxy (Caddy, Traefik, or Nginx) with Let's Encrypt certificates.
2. **Generate secure secrets** — never use placeholder values for `ENCRYPTION_SECRET`, `NEXTAUTH_SECRET`, or `DATABASE_PASSWORD`. Use `openssl rand -hex 32` for all secrets.
3. **Configure SMTP** — set up email delivery for form notifications, user invitations, and response confirmations.
4. **Set up backups** — PostgreSQL data should be backed up daily. Use `pg_dump` or a tool like Restic for automated backups.
5. **Configure CORS** — if embedding forms on external domains, set appropriate CORS headers in your reverse proxy.
6. **Monitor resources** — form builders with high traffic can consume significant database connections. Monitor PostgreSQL connection pools and Redis memory usage.

## FAQ

### What is the main difference between Typebot and Formbricks?

Typebot focuses on conversational, chat-style forms that feel like talking to a chatbot. Formbricks focuses on traditional surveys with multiple distribution methods — in-app widgets, website popups, email links, and standalone pages. Typebot excels at engagement and completion rates; Formbricks excels at versatile survey placement and targeting.

### Can I migrate from Typeform to a self-hosted form builder?

Yes. Typebot and Formbricks both support importing from Typeform's export format. You can export your existing forms from Typeform (Settings > Export), then recreate them in your self-hosted platform. The question types map closely, though conversational-style Typeform forms translate most naturally to Typebot.

### How much does it cost to self-host a form builder?

The infrastructure cost is typically $5–$20 per month for a small VPS (1–2 vCPUs, 2–4 GB RAM). All three platforms run comfortably on modest hardware for most use cases. PostgreSQL and Redis (required by Typebot and OhMyForm) add minimal overhead. This is dramatically cheaper than Typeform or SurveyMonkey, which charge $25–$300+ per month depending on response volume.

### Do these form builders support GDPR compliance?

Self-hosting inherently gives you GDPR compliance advantages because you control the data. All three platforms store responses in your own PostgreSQL database, and you control retention, deletion, and access policies. Typebot and Formbricks also include cookie consent options and data export features to support subject access requests.

### Can I embed these forms on my existing website?

Yes. Typebot offers embed as a floating bubble, inline component, or full-page link. Formbricks provides a JavaScript SDK for in-app widgets and website popups. OhMyForm supports iframe embedding. All three also generate shareable public URLs for direct linking.

### Which platform has the most active development?

Formbricks (12,120 stars, updated April 2026) and Typebot (9,881 stars, updated April 2026) are both actively maintained with regular releases. OhMyForm's last update was in October 2024, making it the least actively developed of the three. For production deployments, Typebot or Formbricks are the safer long-term choices.

### Can I use these form builders without Docker?

Yes. All three platforms are Node.js/Next.js applications that can be deployed directly on a server using PM2 or systemd. However, Docker Compose is the officially supported and recommended deployment method for all three, as it handles database setup, migrations, and dependency management automatically.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Typebot vs Formbricks vs OhMyForm: Best Self-Hosted Form Builders 2026",
  "description": "Compare three self-hosted form builders — Typebot, Formbricks, and OhMyForm. Docker deployment guides, feature comparison, and when to choose each platform in 2026.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
