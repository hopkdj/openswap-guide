---
title: "Lago vs Kill Bill: Best Open-Source Billing Platforms 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "billing", "saas"]
draft: false
description: "Compare Lago and Kill Bill — the two leading open-source self-hosted billing and subscription management platforms. Docker setup, API examples, and migration guides included."
---

Running a SaaS business means your billing infrastructure is mission-critical. When Stripe Billing, Chargebee, or Recurly become too expensive or too restrictive, open-source self-hosted billing platforms offer full control over your pricing logic, customer data, and revenue analytics.

In this guide, we compare the two most mature open-source billing platforms available in 2026: **[Lago](https://github.com/getlago/lago)** and **[Kill Bill](https://github.com/killbill/killbill)**. Both are self-hosted, API-first, and designed for businesses that need usage-based billing, subscription management, and payment orchestration without vendor lock-in.

## Why Self-Host Your Billing Infrastructure?

Billing is the backbone of any subscription business. Relying on a third-party SaaS provider introduces several risks:

- **Vendor lock-in**: Migrating away from Stripe Billing or Chargebee means rebuilding your entire pricing logic, customer records, and invoicing pipeline.
- **Cost at scale**: SaaS billing platforms charge per invoice or as a percentage of revenue. At $50K+ MRR, those fees add up to thousands of dollars per month.
- **Data control**: Financial data lives on someone else's servers. Self-hosting keeps customer records, payment history, and revenue analytics within your infrastructure.
- **Custom pricing models**: SaaS platforms support standard subscription tiers but struggle with com[plex](https://www.plex.tv/) usage-based, tiered, or hybrid pricing. Open-source platforms let you implement any pricing logic.
- **Regulatory compliance**: GDPR, SOC 2, and PCI DSS requirements are easier to satisfy when you control the full data pipeline.

For these reasons, many growing SaaS companies evaluate open-source alternatives once they outgrow the free tiers of commercial billing providers.

## Lago — Modern Usage-Based Billing API

**Lago** (9,500+ GitHub stars, last updated April 2026) is an open-source metering and usage-based billing API written in Go and Ruby. It is designed from the ground up for modern SaaS products that charge based on consumption — think API calls, storage gigabytes, or compute hours.

Key features:

- **Usage-based metering**: Track and bill for any event type with real-time aggregation.
- **Subscription management**: Plans, trials, add-ons, and proration out of the box.
- **Payment orchestration**: Native integrations with Stripe, Gocardless, and Cashfree.
- **Revenue analytics**: Built-in dashboards for MRR, ARR, churn, and revenue attribution.
- **REST API**: Clean, well-documented API for creating customers, plans, invoices, and events.
- **Admin dashboard**: A self-hosted web UI for managing subscriptions and viewing analytics.

Lago's architecture uses PostgreSQL (with partitioning via `postgres-partman`) for data storage, Redis for caching and job queues, and a Ruby on Rails API backend. The frontend is a standalone React application serv[docker](https://www.docker.com/) Nginx.

### Lago Docker Compose Setup

Lago ships with a production-ready Docker Compose configuration. Here is a simplified version for a minimal self-hosted deployment:

```yaml
volumes:
  lago_postgres_data:
  lago_redis_data:
  lago_storage_data:

services:
  db:
    image: getlago/postgres-partman:15.0-alpine
    container_name: lago-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: lago
      POSTGRES_USER: lago
      POSTGRES_PASSWORD: changeme
      PGDATA: /data/postgres
    volumes:
      - lago_postgres_data:/data/postgres
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lago"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: lago-redis
    restart: unless-stopped
    volumes:
      - lago_redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  migrate:
    image: getlago/api:v1.45.1
    container_name: lago-migrate
    depends_on:
      db:
        condition: service_healthy
    command: ["./scripts/migrate.sh"]
    environment:
      DATABASE_URL: "postgresql://lago:changeme@db:5432/lago?search_path=public"
      REDIS_URL: "redis://redis:6379"
      SECRET_KEY_BASE: "your-secret-key-base-hex-64-characters-long-here"
      LAGO_ENCRYPTION_PRIMARY_KEY: "your-encryption-primary-key"
      LAGO_ENCRYPTION_DETERMINISTIC_KEY: "your-encryption-deterministic-key"
      LAGO_ENCRYPTION_KEY_DERIVATION_SALT: "your-encryption-derivation-salt"

  api:
    image: getlago/api:v1.45.1
    container_name: lago-api
    restart: unless-stopped
    depends_on:
      migrate:
        condition: service_completed_successfully
    command: ["./scripts/start.api.sh"]
    environment:
      DATABASE_URL: "postgresql://lago:changeme@db:5432/lago?search_path=public"
      REDIS_URL: "redis://redis:6379"
      SECRET_KEY_BASE: "your-secret-key-base-hex-64-characters-long-here"
      LAGO_ENCRYPTION_PRIMARY_KEY: "your-encryption-primary-key"
      LAGO_ENCRYPTION_DETERMINISTIC_KEY: "your-encryption-deterministic-key"
      LAGO_ENCRYPTION_KEY_DERIVATION_SALT: "your-encryption-derivation-salt"
      RAILS_ENV: production
      LAGO_API_URL: http://localhost:3000
      LAGO_FRONT_URL: http://localhost
      LAGO_PDF_URL: http://pdf:3000
    volumes:
      - lago_storage_data:/app/storage
    ports:
      - "3000:3000"

  front:
    image: getlago/front:v1.45.1
    container_name: lago-front
    restart: unless-stopped
    depends_on:
      - api
    environment:
      API_URL: http://localhost:3000
      APP_ENV: production
    ports:
      - "80:80"
```

Deploy with:

```bash
docker compose up -d
```

After deployment, the Lago admin dashboard is available at `http://localhost`, and the API runs on `http://localhost:3000`.

### Lago API — Creating a Customer and Plan

```bash
# Create a customer
curl -X POST http://localhost:3000/api/v1/customers \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {
      "external_id": "cust_001",
      "name": "Acme Corp",
      "currency": "USD",
      "email": "billing@acme.com"
    }
  }'

# Create a plan with usage-based pricing
curl -X POST http://localhost:3000/api/v1/plans \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": {
      "name": "Pro Plan",
      "code": "pro_plan",
      "interval": "monthly",
      "amount_cents": 4900,
      "currency": "USD",
      "charges": [
        {
          "billable_metric": {
            "name": "API Calls",
            "code": "api_calls",
            "aggregation_type": "sum_agg"
          },
          "charge_model": "graduated",
          "graduated_ranges": [
            {"from_value": 0, "to_value": 1000, "per_unit_amount": "0.01"},
            {"from_value": 1001, "to_value": null, "per_unit_amount": "0.005"}
          ]
        }
      ]
    }
  }'

# Record a usage event
curl -X POST http://localhost:3000/api/v1/events \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "external_customer_id": "cust_001",
      "transaction_id": "evt_abc123",
      "code": "api_calls",
      "properties": {
        "count": 150
      }
    }
  }'
```

## Kill Bill — Enterprise Subscription Billing Platform

**Kill Bill** (5,400+ GitHub stars, last updated April 2026) is the longest-running open-source subscription billing and payments platform. Written in Java, it has been in production use since 2010 and is designed for enterprises that need a highly modular, extensible billing system.

Key features:

- **10+ years of production use**: Battle-tested at companies handling millions of transactions.
- **Modular architecture**: Enable or disable modules (catalog, invoicing, payments, overdue) as needed.
- **Catalog system**: Flexible product catalog with plans, phases, price lists, and availability rules.
- **Payment plugin ecosystem**: Integrations with Stripe, Adyen, Braintree, PayPal, and more via a plugin architecture.
- **Multi-currency and multi-tenant**: Support for global businesses with complex pricing.
- **Kaui admin UI**: Kill Bill Admin UI (KAUI) provides a web interface for managing accounts and subscriptions.
- **REST API**: Comprehensive API for all billing operations.

Kill Bill runs on a Java servlet container (Tomcat by default) with MySQL or MariaDB as the backing store. Its plugin-based architecture allows deep customization of payment flows, tax calculations, and notification systems.

### Kill Bill Docker Compose Setup

Kill Bill does not ship an official Docker Compose file, but the community-standard deployment uses the `killbill/killbill` Docker image with a MySQL database:

```yaml
volumes:
  kb_mysql_data:

services:
  mysql:
    image: mysql:8.0
    container_name: kb-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: killbill
    volumes:
      - kb_mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  killbill:
    image: killbill/killbill:0.24.0
    container_name: kb-server
    restart: unless-stopped
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      KILLBILL_DAO_URL: jdbc:mysql://mysql:3306/killbill
      KILLBILL_DAO_USER: root
      KILLBILL_DAO_PASSWORD: root
      KILLBILL_SERVER_API_KEY: lazar
      KILLBILL_SERVER_API_SECRET: demo
    ports:
      - "8080:8080"

  kaui:
    image: killbill/kaui:3.0.7
    container_name: kaui-ui
    restart: unless-stopped
    depends_on:
      - killbill
    environment:
      KAUI_CONFIG_DAO_URL: jdbc:mysql://mysql:3306/kaui
      KAUI_CONFIG_DAO_USER: root
      KAUI_CONFIG_DAO_PASSWORD: root
      KAUI_KILLBILL_URL: http://killbill:8080
      KAUI_KILLBILL_API_KEY: lazar
      KAUI_KILLBILL_API_SECRET: demo
    ports:
      - "9090:8080"
```

Deploy with:

```bash
docker compose up -d
```

The Kill Bill API is available at `http://localhost:8080` and the KAUI admin dashboard at `http://localhost:9090`.

### Kill Bill API — Creating an Account and Subscription

```bash
# Create an account
curl -X POST http://localhost:8080/1.0/kb/accounts \
  -u "lazar:demo" \
  -H "Content-Type: application/json" \
  -H "X-Killbill-ApiKey: lazar" \
  -H "X-Killbill-ApiSecret: demo" \
  -H "X-Killbill-CreatedBy: admin" \
  -d '{
    "name": "Acme Corp",
    "email": "billing@acme.com",
    "currency": "USD",
    "externalKey": "cust_001"
  }'

# Create a subscription (requires a catalog to be uploaded first)
curl -X POST http://localhost:8080/1.0/kb/accounts/{accountId}/subscriptions \
  -u "lazar:demo" \
  -H "Content-Type: application/json" \
  -H "X-Killbill-ApiKey: lazar" \
  -H "X-Killbill-ApiSecret: demo" \
  -H "X-Killbill-CreatedBy: admin" \
  -d '{
    "productName": "Standard",
    "productCategory": "BASE",
    "billingPeriod": "MONTHLY",
    "priceList": "DEFAULT"
  }'
```

## Lago vs Kill Bill: Head-to-Head Comparison

| Feature | Lago | Kill Bill |
|---|---|---|
| **Language** | Go + Ruby on Rails | Java |
| **License** | MIT | Apache 2.0 |
| **GitHub Stars** | 9,500+ | 5,400+ |
| **Database** | PostgreSQL (with partitioning) | MySQL / MariaDB |
| **Usage-Based Billing** | Native, first-class support | Possible but requires custom plugin |
| **Subscription Management** | Yes — plans, trials, proration | Yes — catalog-driven, highly flexible |
| **Payment Integrations** | Stripe, Gocardless, Cashfree | Stripe, Adyen, Braintree, PayPal + plugins |
| **Admin Dashboard** | Built-in (React SPA) | KAUI (separate deployment) |
| **Multi-Tenancy** | Via organization API | Native multi-tenant support |
| **Docker Setup** | Official compose file | Community compose, no official file |
| **Learning Curve** | Moderate — REST-first, good docs | Steep — Java ecosystem, catalog XML |
| **Best For** | Modern SaaS, API-first products | Enterprise, complex billing logic |
| **Community** | Active, fast-growing (since 2022) | Mature, established (since 2010) |

## Which Should You Choose?

### Choose Lago if:

- Your product charges based on **usage** (API calls, storage, bandwidth, seats).
- You want a **modern developer experience** with clean REST APIs and a built-in admin UI.
- You prefer **PostgreSQL** and want built-in database partitioning for scaling event ingestion.
- You need **fast time-to-value** — Lago's Docker compose works out of the box with minimal configuration.
- You value a **modern tech stack** (Go + Ruby) and active community growth.

### Choose Kill Bill if:

- You need **enterprise-grade modularity** — the ability to swap out billing components.
- Your pricing logic involves **complex catalogs** with phases, price lists, and availability windows.
- You require **multi-tenant isolation** out of the box.
- You operate in a **Java-heavy infrastructure** and want native JVM integration.
- You value **battle-tested stability** — Kill Bill has been in production for over a decade.
- You need a **wider range of payment plugins** (Adyen, Braintree, PayPal).

## Reverse Proxy Configuration (Nginx)

Both platforms should sit behind a reverse proxy with TLS termination. Here is an Nginx configuration for Lago:

```nginx
server {
    listen 443 ssl http2;
    server_name billing.example.com;

    ssl_certificate /etc/letsencrypt/live/billing.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/billing.example.com/privkey.pem;

    # Lago Frontend
    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Lago API
    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }
}
```

For Kill Bill, point the proxy to port 8080:

```nginx
server {
    listen 443 ssl http2;
    server_name billing.example.com;

    ssl_certificate /etc/letsencrypt/live/billing.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/billing.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

## Backup and Disaster Recovery

For any billing platform, data integrity is non-negotiable. Here is a simple backup strategy using `pg_dump` for Lago:

```bash
# Daily backup cron job for Lago PostgreSQL
0 2 * * * pg_dump -U lago -h localhost lago | gzip > /backups/lago-$(date +\%Y\%m\%d).sql.gz

# Restore from backup
gunzip -c /backups/lago-20260420.sql.gz | psql -U lago -h localhost lago
```

For Kill Bill with MySQL:

```bash
# Daily backup cron job for Kill Bill MySQL
0 2 * * * mysqldump -u root -proot killbill | gzip > /backups/killbill-$(date +\%Y\%m\%d).sql.gz

# Restore from backup
gunzip -c /backups/killbill-20260420.sql.gz | mysql -u root -proot killbill
```

For related reading on self-hosted infrastructure management, see our [self-hosted invoicing guide](../invoice-ninja-akaunting-crater-self-hosted-invoicing-guide/) for complementary financial [n8n](https://n8n.io/)ls, and our [workflow automation comparison](../n8n-vs-nodered-vs-activepieces/) for building billing notification pipelines. If you are building a full SaaS stack, our [Backend-as-a-Service comparison](../appwrite-vs-supabase-vs-pocketbase-self-hosted-firebase-alternatives-2026/) covers the backend infrastructure layer that sits alongside billing.

## FAQ

### What is the difference between Lago and Kill Bill?

Lago is a modern, API-first billing platform focused on usage-based metering and subscription management. It uses Go and Ruby on Rails with PostgreSQL. Kill Bill is a mature Java-based billing platform with a modular plugin architecture, designed for complex enterprise billing scenarios. Lago is easier to set up and better suited for usage-based pricing, while Kill Bill offers deeper extensibility for complex catalog-driven billing.

### Can I migrate from Stripe Billing to Lago or Kill Bill?

Yes. Both platforms provide REST APIs for creating customers, plans, and subscriptions. You can export your Stripe customer data via the Stripe API and import it into either platform. Lago has a dedicated Stripe migration guide in its documentation. Kill Bill's payment plugin system also supports running both Stripe and Kill Bill in parallel during a gradual migration.

### Do Lago and Kill Bill support free trials and proration?

Both platforms support trial periods and proration. Lago handles proration automatically when customers upgrade or downgrade plans mid-cycle. Kill Bill supports trial periods through its catalog definition, where you can define trial phases with zero cost before transitioning to paid billing periods.

### How do I handle payment processing with open-source billing?

Neither Lago nor Kill Bill processes payments directly. Instead, they integrate with payment gateways like Stripe, Gocardless, or Adyen. The billing platform manages the subscription logic, invoice generation, and revenue recognition, while the payment gateway handles actual card charges and bank transfers. This separation means you can switch payment providers without changing your billing engine.

### Which platform is easier to self-host?

Lago is easier to self-host. It ships with an official Docker Compose file that includes all services (API, frontend, PostgreSQL, Redis) and works with a single `docker compose up -d` command. Kill Bill requires a MySQL database, a Kill Bill server container, and optionally a KAUI admin container — more moving parts to configure and maintain.

### Are there any costs associated with using Lago or Kill Bill?

Both platforms are free and open-source. Lago is licensed under MIT and Kill Bill under Apache 2.0. You only pay for your own infrastructure costs (server, database storage, bandwidth). Both platforms offer paid cloud-hosted options if you prefer not to self-host — Lago Cloud and Kill Bill Cloud — which include support and managed infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Lago vs Kill Bill: Best Open-Source Billing Platforms 2026",
  "description": "Compare Lago and Kill Bill — the two leading open-source self-hosted billing and subscription management platforms. Docker setup, API examples, and migration guides included.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
