---
title: "Ghostfolio: Self-Hosted Portfolio Tracker & Wealth Management Guide 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "privacy", "finance"]
draft: false
description: "Complete guide to Ghostfolio, the open-source self-hosted portfolio tracker and wealth management platform. Docker setup, configuration, and alternatives compared."
---

Tracking your investments across multiple brokerages, crypto exchanges, and bank accounts usually means logging into five different dashboards — or handing that data to a proprietary portfolio app that monetizes your financial behavior. [ghost](https://ghost.org/)folio changes that equation entirely.

Ghostfolio is an open-source wealth management platform that aggregates your entire portfolio into a single self-hosted dashboard. With over 8,100 GitHub stars and active development (last update April 2026), it is the most popular open-source portfolio tracker available today. This guide covers what Ghostfolio does, how to deploy it with [docker](https://www.docker.com/), and how it compares to smaller open-source alternatives.

---

## Why Self-Host Your Portfolio Tracker

Financial data is among the most sensitive information you own. When you use a cloud-based portfolio tracker like Empower (Personal Capital), Sharesight, or Delta, you are granting a third-party company access to:

- Your complete asset allocation across every account
- Transaction history and trade patterns
- Net worth calculations and growth trends
- Account balances and cash flow data

Self-hosting a portfolio tracker like Ghostfolio keeps all of this data on your own infrastructure. There are no API keys shared with third-party analytics companies, no data mining for advertising purposes, and no risk of a startup shutting down and taking your historical data with it. For related reading on self-hosted personal finance, see our [Actual Budget vs Firefly III vs Beancount comparison](../actual-budget-vs-firefly-iii-vs-beancount-self-hosted-personal-finance-2026/) and our [complete Firefly III guide](../firefly-iii-self-hosted-finance-guide/).

---

## Ghostfolio at a Glance

| Metric | Value |
|--------|-------|
| **GitHub Stars** | 8,161+ |
| **Language** | TypeScript (Angular + NestJS) |
| **License** | AGPL-3.0 |
| **Database** | PostgreSQL |
| **Cache** | Redis |
| **Last Updated** | April 2026 |
| **API** | REST API available |
| **Multi-Currency** | Yes (automatic FX conversion) |
| **Crypto Support** | Yes (Bitcoin, Ethereum, and more) |
| **ETF Support** | Yes (global coverage via Yahoo Finance API) |
| **Mobile** | Progressive Web App (PWA) |

Ghostfolio's tech stack combines Angular for the frontend, NestJS for the backend API, Prisma as the ORM layer, and PostgreSQL for persistent storage. Redis provides caching for market data lookups. The application fetches pricing data from Yahoo Finance, which covers stocks, ETFs, bonds, and cryptocurrencies across global markets.

The project was created by Thomas Kaul and has grown into one of the most popular personal finance tools on GitHub. The AGPL-3.0 license ensures that any modifications you make to the code must also be open-sourced if you distribute them — but for self-hosting on your own server, you can freely customize the code without restrictions.

---

## Core Architecture and Data Flow

Understanding how Ghostfolio manages your data helps you troubleshoot issues and plan your deployment:

1. **Market Data Service** — Runs on a schedule, fetching current prices from Yahoo Finance for all tracked symbols. Results are cached in Redis to reduce API calls.
2. **Portfolio Calculator** — Computes time-weighted rate of return, asset allocation percentages, and geographic distribution from your transaction history.
3. **REST API** — Exposes portfolio data, holdings, and performance metrics via authenticated endpoints. You can use these endpoints to build custom dashboards or integrate with other services.
4. **PostgreSQL** — Stores all user accounts, transactions, holdings, and account configurations. This is the only data store that needs regular backups.
5. **Redis** — Caches market data, exchange rates, and session information. If Redis goes down, Ghostfolio will still function but will be slower as it queries Yahoo Finance directly.

This architecture is designed to run on a single server with minimal resource requirements. A $5/month VPS with 1 GB RAM is sufficient for personal use with a few hundred transactions.

---

## The Open-Source Portfolio Tracker Landscape in 2026

While Ghostfolio dominates this space, several smaller alternatives exist:

| Feature | **Ghostfolio** | **Invester** | **Wall Street Local** |
|---------|---------------|--------------|----------------------|
| **Stars** | 8,161+ | 37 | 470 |
| **Language** | TypeScript | TypeScript | JavaScript (SvelteKit) |
| **Last Updated** | April 2026 | April 2023 | March 2025 |
| **License** | AGPL-3.0 | MIT | MIT |
| **Database** | PostgreSQL + Redis | SQLite | Cloudflare D1 |
| **Docker Support** | Official compose | Manual | Manual |
| **Multi-Account** | Yes | Limited | No |
| **Crypto** | Yes | No | No |
| **Asset Classes** | Stocks, ETFs, Bonds, Crypto, Commodities | Stocks, ETFs | US institutional holdings (13F filings) |
| **Portfolio Analytics** | Allocation, performance, fees | Custom widgets | Congress trading tracker |
| **Best For** | Personal wealth management | Custom dashboards | Tracking politician trades |

**Ghostfolio** is the clear choice for personal portfolio management with its comprehensive asset class support, active development, and mature Docker deployment. **Invester** offers widget-based dashboards but has not been updated since 2023. **Wall Street Local** serves a different purpose entirely — tracking US money manager 13F filings and congressional stock trades — and is useful for market research rather than personal portfolio tracking.

---

## Installing Ghostfolio with Docker Compose

Ghostfolio provides an official Docker Compose configuration that deploys three services: the Ghostfolio application, PostgreSQL database, and Redis cache.

### Prerequisites

- Docker and Docker Compose installed
- At least 1 GB RAM (PostgreSQL + Redis + Ghostfolio)
- A domain name (optional, for HTTPS with reverse proxy)

### Step 1: Create the Project Directory

```bash
mkdir -p ~/ghostfolio && cd ~/ghostfolio
```

### Step 2: Create the Environment File

Create a `.env` file with your configuration:

```bash
cat > .env << 'ENVFILE'
COMPOSE_PROJECT_NAME=ghostfolio

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=change-me-to-a-secure-password

# PostgreSQL
POSTGRES_DB=ghostfolio-db
POSTGRES_USER=ghostfolio
POSTGRES_PASSWORD=change-me-to-a-secure-password

# Application
ACCESS_TOKEN_SALT=$(openssl rand -hex 16)
DATABASE_URL=postgresql://ghostfolio:change-me-to-a-secure-password@postgres:5432/ghostfolio-db?connect_timeout=300&sslmode=prefer
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENVFILE
```

Generate secure passwords before deployment:

```bash
# Generate a secure Redis password
openssl rand -hex 32

# Generate JWT secret
openssl rand -hex 32

# Generate access token salt
openssl rand -hex 16
```

### Step 3: Create the Docker Compose File

```bash
mkdir -p docker && cat > docker/docker-compose.yml << 'COMPOSEFILE'
name: ghostfolio
services:
  ghostfolio:
    image: docker.io/ghostfolio/ghostfolio:latest
    container_name: ghostfolio
    restart: unless-stopped
    init: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    env_file:
      - ../.env
    ports:
      - 3333:3333
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service healthy
    healthcheck:
      test: ['CMD-SHELL', 'curl -f http://localhost:3333/api/v1/health']
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: docker.io/library/postgres:15-alpine
    container_name: gf-postgres
    restart: unless-stopped
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_READ_SEARCH
      - FOWNER
      - SETGID
      - SETUID
    security_opt:
      - no-new-privileges:true
    env_file:
      - ../.env
    healthcheck:
      test:
        ['CMD-SHELL', 'pg_isready -d "$${POSTGRES_DB}" -U $${POSTGRES_USER}']
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - postgres:/var/lib/postgresql/data

  redis:
    image: docker.io/library/redis:alpine
    container_name: gf-redis
    restart: unless-stopped
    user: '999:1000'
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    env_file:
      - ../.env
    command:
      - /bin/sh
      - -c
      - redis-server --requirepass "$${REDIS_PASSWORD:?REDIS_PASSWORD variable is not set}"
    healthcheck:
      test:
        ['CMD-SHELL', 'redis-cli --pass "$${REDIS_PASSWORD}" ping | grep PONG']
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres:
COMPOSEFILE
```

### Step 4: Start the Services

```bash
cd ~/ghostfolio
docker compose -f docker/docker-compose.yml up -d
```

Verify all containers are running:

```bash
docker compose -f docker/docker-compose.yml ps
```

You should see three healthy containers:

```
NAME            IMAGE                          STATUS
ghostfolio      ghostfolio/ghostfolio:latest   Up (healthy)
gf-postgres     postgres:15-alpine             Up (healthy)
gf-redis        redis:alpine                   Up (healthy)
```

### Step 5: Access the Web Interface

Open your browser and navigate to `http://your-server-ip:3333`. The first screen prompts you to create an admin a[nginx](https://nginx.org/)t.

---

## Setting Up a Reverse Proxy with Nginx

For production use, you should place Ghostfolio behind a reverse proxy with HTTPS. Here is a minimal Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name portfolio.example.com;

    ssl_certificate     /etc/letsencrypt/live/portfolio.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portfolio.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3333;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Adding Assets and Tracking Your Portfolio

Once logged in, Ghostfolio lets you add holdings in several ways:

### Manual Entry

1. Click the **+** button to add a new holding
2. Search by ticker symbol (e.g., `AAPL`, `VOO`, `BTC-USD`)
3. Enter quantity, purchase price, and date
4. Select the account this holding belongs to

### CSV Import

Ghostfolio supports importing transaction history via CSV:

1. Navigate to **Portfolio > Import Activities**
2. Upload a CSV file with columns: `date`, `symbol`, `quantity`, `price`, `fee`, `currency`
3. Preview the import and confirm

This works well for exporting transaction history from most brokerages.

### Account Organization

Create separate accounts for different brokers, retirement accounts, or crypto wallets:

- **Brokerage Account** — Stocks and ETFs held at your main broker
- **Crypto Wallet** — Bitcoin, Ethereum, and other crypto holdings
- **Retirement Account** — 401(k) or IRA holdings
- **Cash Account** — Savings and checking account balances

Each account can be assigned a different currency, and Ghostfolio converts everything to your base currency for the total net worth view.

### Supported Asset Classes

Ghostfolio covers a wide range of investment types:

- **Stocks** — Individual company shares traded on any major exchange (NYSE, NASDAQ, LSE, TSE, etc.)
- **ETFs** — Exchange-traded funds including index funds, sector funds, and thematic ETFs
- **Bonds** — Government and corporate bonds with yield tracking
- **Cryptocurrency** — Bitcoin, Ethereum, and hundreds of altcoins with automatic price updates
- **Commodities** — Gold, silver, and other precious metals tracked via commodity symbols
- **Mutual Funds** — Traditional mutual fund holdings with NAV tracking
- **Cash** — Cash balances in any currency for a complete net worth picture

This breadth of support means most investors can track their entire portfolio in one place. You can add positions in US stocks, European ETFs, Japanese government bonds, and Bitcoin all within the same portfolio view.

---

## Key Features Deep Dive

### Portfolio Analytics

Ghostfolio calculates several metrics automatically:

- **Time-weighted rate of return (TWROR)** — Performance metric that eliminates the impact of cash flows, giving you a true picture of investment performance regardless of when you added or withdrew money
- **Investment by asset class** — Pie chart breakdown of stocks, bonds, crypto, cash, and other categories
- **Geographic allocation** — Country-level diversification view showing where your money is invested globally
- **Sector allocation** — Industry-level breakdown for equity holdings (technology, healthcare, financials, etc.)
- **Top holdings** — Largest positions by portfolio percentage, helping you identify concentration risk
- **Investment streak** — Tracks consecutive periods of investing, useful for dollar-cost averaging strategies

These analytics update automatically as market data refreshes. You don't need to run any manual calculations or import updated prices — Ghostfolio handles everything in the background.

### Multi-Currency Support

Ghostfolio fetches real-time exchange rates and converts all holdings to your base currency. This is essential for international investors who hold assets across USD, EUR, GBP, JPY, and other currencies. The exchange rate data comes from the same Yahoo Finance data source that provides stock prices, ensuring consistency.

When you add a holding denominated in a foreign currency, Ghostfolio automatically:
1. Looks up the current price in the original currency
2. Fetches the current exchange rate to your base currency
3. Calculates the position value and returns in your base currency
4. Updates the conversion rate each time market data refreshes

This means your portfolio dashboard always shows accurate totals regardless of currency fluctuations.

### Fire-and-Forget Market Data

Ghostfolio automatically refreshes market data from Yahoo Finance on a scheduled basis. You don't need to manually update prices or configure cron jobs — the built-in data service handles this. For cryptocurrency, it supports multiple data sources to ensure price availability even if one source is temporarily down.

### Tags and Filtering

Tag individual holdings (e.g., "dividend", "growth", "retirement") and filter your portfolio view by tag. This is useful for analyzing specific slices of your portfolio without creating separate accounts. Common tagging strategies include:

- **Investment strategy** — "value", "growth", "dividend", "index"
- **Risk level** — "conservative", "moderate", "aggressive"
- **Goal-based** — "retirement", "emergency", "education", "house"
- **Tax treatment** — "taxable", "tax-deferred", "tax-free"

### API Access

Ghostfolio exposes a REST API at `/api/v1/` that you can use for:

- Querying portfolio performance programmatically
- Building custom dashboards on top of your data (see our [self-hosted BI dashboard guide](../self-hosted-bi-dashboard-superset-metabase-lightdash-guide-2026/) for visualization ideas)
- Integrating with home automation or notification systems
- Exporting data for tax preparation or financial planning

Authentication is handled via API tokens generated from the admin panel. Each token can be scoped to specific accounts, allowing you to grant limited access to third-party tools.

---

## Maintenance and Backups

### Database Backup

```bash
# Backup the PostgreSQL database
docker exec gf-postgres pg_dump -U ghostfolio ghostfolio-db > ghostfolio-backup-$(date +%Y%m%d).sql

# Restore from backup
cat ghostfolio-backup-20260418.sql | docker exec -i gf-postgres psql -U ghostfolio ghostfolio-db
```

For automated backups, set up a cron job on your host server:

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * docker exec gf-postgres pg_dump -U ghostfolio ghostfolio-db > /backup/ghostfolio-$(date +\%Y\%m\%d).sql && find /backup -name "ghostfolio-*.sql" -mtime +30 -delete
```

This keeps 30 days of backups and automatically removes older ones. Store the backup directory on a separate volume or sync it to offsite storage for disaster recovery.

### Updating Ghostfolio

```bash
cd ~/ghostfolio
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up -d
```

The pull command fetches the latest image from Docker Hub. The up -d command restarts the container with the new image while preserving your database and Redis data through the volume mounts.

Before updating production instances, consider testing the new version on a staging server first. Ghostfolio's release notes on GitHub list any breaking changes or required migrations.

### Log Monitoring

```bash
# Check Ghostfolio logs
docker logs ghostfolio --tail 50

# Check PostgreSQL logs
docker logs gf-postgres --tail 50

# Follow Redis logs in real-time
docker logs -f gf-redis
```

Common issues to watch for:
- **Market data fetch failures** — Usually temporary Yahoo Finance rate limiting. Redis cache will serve stale data until the next successful fetch.
- **Database connection errors** — Check that the PostgreSQL container is healthy and the DATABASE_URL in your .env file matches the actual credentials.
- **High memory usage** — PostgreSQL can consume significant RAM with large portfolios. Monitor with `docker stats` and consider increasing your server's memory if needed.

### Resource Requirements

| Component | Minimum RAM | Recommended RAM |
|-----------|------------|-----------------|
| Ghostfolio app | 150 MB | 256 MB |
| PostgreSQL | 100 MB | 256 MB |
| Redis | 30 MB | 64 MB |
| **Total** | **280 MB** | **576 MB** |

A $5/month VPS (typically 1 GB RAM) handles personal portfolios with hundreds of transactions comfortably. If you run many other services on the same server, allocate at least 512 MB for the Ghostfolio stack.

---

## FAQ

### Is Ghostfolio free to use?

Yes. Ghostfolio is completely free and open-source under the AGPL-3.0 license. There are no premium tiers, no feature paywalls, and no telemetry. You host it yourself and own all your data.

### Can Ghostfolio track cryptocurrency?

Yes. Ghostfolio supports cryptocurrency holdings including Bitcoin, Ethereum, and many others. You can add crypto positions manually by searching for the ticker symbol (e.g., `BTC-USD`) or by importing transactions via CSV. Market data is refreshed automatically.

### Does Ghostfolio connect to my brokerage automatically?

Ghostfolio does not directly connect to brokerage APIs. You add transactions manually or import them via CSV file. This design choice is intentional — it means Ghostfolio never stores your brokerage login credentials or requires API access to your financial accounts, reducing your attack surface.

### What databases does Ghostfolio support?

Ghostfolio requires PostgreSQL (version 15 recommended) and Redis for caching. These are included in the official Docker Compose file. The PostgreSQL requirement means you cannot run Ghostfolio on SQLite alone — plan for the additional memory footprint (approximately 200-300 MB total for all three services).

### Can I run Ghostfolio on a Raspberry Pi?

Yes, but with caveats. The ARM64 Docker images for Ghostfolio, PostgreSQL, and Redis all work on Raspberry Pi 4 and newer. You will need at least 2 GB of RAM (4 GB recommended) since PostgreSQL and Redis run alongside the application. For larger portfolios with years of transaction history, a more powerful server is advisable.

### How do I back up my Ghostfolio data?

The primary data lives in the PostgreSQL volume. Run `docker exec gf-postgres pg_dump -U ghostfolio ghostfolio-db > backup.sql` to create a backup. Store this file on a separate drive or offsite location. The Redis cache does not need to be backed up — it is rebuilt from the database on restart.

### Can I import data from other portfolio trackers?

Ghostfolio supports CSV import with a defined column format. Most portfolio trackers and brokerages allow CSV export of transaction history, which you can then map to Ghostfolio's expected format. There is no direct import from specific platforms like Sharesight or Empower, but the CSV approach covers the vast majority of use cases.

---

## Final Thoughts: Is Ghostfolio Right for You?

Ghostfolio is the best self-hosted portfolio tracker for most individual investors in 2026. Its combination of comprehensive asset class support, active development, clean interface, and straightforward Docker deployment makes it the default choice for anyone who wants to track their wealth without relying on a proprietary SaaS platform.

The main trade-offs are worth understanding:

**Pros:**
- Completely free and open-source with no premium tiers
- Supports stocks, ETFs, bonds, crypto, commodities, and cash in one place
- Automatic market data updates via Yahoo Finance
- Multi-currency with real-time exchange rate conversion
- Clean, modern Angular-based interface with PWA support
- REST API for custom integrations
- Active development with regular releases
- Strong security defaults (hardened Docker containers with dropped capabilities)

**Cons:**
- No direct brokerage API connections — manual or CSV import only
- Requires PostgreSQL and Redis (not a single binary)
- AGPL-3.0 license may be restrictive for some commercial use cases
- Yahoo Finance data source can occasionally be rate-limited
- No built-in tax lot tracking or cost basis calculations

If you need direct brokerage connectivity, you will need to stick with a proprietary solution like Empower or Sharesight. But if you are comfortable adding transactions manually or importing CSV files, Ghostfolio gives you everything else a serious portfolio tracker needs — with the added benefit that your financial data never leaves your server.

For related personal finance tools, check out our [Actual Budget vs Firefly III vs Beancount guide](../actual-budget-vs-firefly-iii-vs-beancount-self-hosted-personal-finance-2026/) for expense tracking and budgeting, or our [Firefly III self-hosted finance guide](../firefly-iii-self-hosted-finance-guide/) for a deeper dive into transaction-based financial management.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ghostfolio: Self-Hosted Portfolio Tracker & Wealth Management Guide 2026",
  "description": "Complete guide to Ghostfolio, the open-source self-hosted portfolio tracker and wealth management platform. Docker setup, configuration, and alternatives compared.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
