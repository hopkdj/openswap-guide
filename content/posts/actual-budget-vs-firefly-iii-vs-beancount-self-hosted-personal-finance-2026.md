---
title: "Actual Budget vs Firefly III vs Beancount: Best Self-Hosted Personal Finance 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy", "finance", "budgeting"]
draft: false
description: "Compare Actual Budget, Firefly III, and Beancount as the best open-source self-hosted personal finance and budgeting tools in 2026. Docker setup, feature comparison, and practical guides."
---

## Why Self-Host Your Personal Finances?

Your financial data is among the most sensitive information you manage daily. Every budgeting app, from Mint to YNAB, requires you to upload bank statements, transaction histories, and spending habits to third-party servers. Even when companies promise encryption and privacy, you are trusting someone else with your most personal numbers.

Self-hosting your personal finance stack changes that equation entirely. By running budgeting software on your own hardware — a Raspberry Pi, a NAS, or a VPS — you retain full ownership of every transaction, every category, and every report. No telemetry, no data harvesting, no sudden service shutdowns that leave you without access to years of financial records.

The open-source ecosystem offers three fundamentally different approaches to personal finance: **envelope-based budgeting** (Actual Budget), **comprehensive expense tracking** (Firefly III), and **plain-text accounting** (Beancount). Each serves a different mindset and workflow. This guide compares all three, provides [docker](https://www.docker.com/) Compose deployment instructions, and helps you pick the right tool for your needs.

---

## What Is Envelope Budgeting?

Envelope budgeting is a time-tested method where you allocate every dollar of income into labeled "envelopes" representing spending categories — groceries, rent, entertainment, savings. When an envelope runs empty, you stop spending in that category or move money from another envelope.

This method forces conscious trade-offs. Instead of wondering where your money went at the end of the month, you decide where it goes at the beginning. The best self-hosted tools implement this philosophy with different interfaces and feature sets.

---

## Actual Budget: YNAB-Style Envelope Budgeting, Open Source

[Actual Budget](https://actualbudget.org/) is a free, open-source implementation of the envelope budgeting methodology. It closely mirrors the experience of YNAB (You Need A Budget) but runs entirely on your own infrastructure. The project gained massive popularity after YNAB moved to a subscription-only model, leaving privacy-conscious users searching for an alternative.

### Core Philosophy

Actual Budget treats every dollar as having a job. When income arrives, you assign it to categories. As you spend, balances decrease. Rollover rules automatically carry over unspent amounts or deficits to the next month. The interface is clean, fast, and works offline via a local-first architecture.

### Key Features

- **Envelope budgeting** with customizable categories and groups
- **Rules engine** for automatic transaction categorization
- **Bank sync** via GoCardless and SimpleFIN (bring-your-own API key)
- **Multi-device sync** through a self-hosted server
- **Reports** including net worth, spending by category, and cash flow
- **Offline-first** PWA that works without internet
- **Import** OFX, QIF, and CSV files
- **Split transactions** and transfers between accounts

### Docker Compose Deployment

Actual Budget consists of a server component and a web-based client. Here is a minimal Docker Compose setup:

```yaml
version: "3.8"

services:
  actual-server:
    image: docker.io/actualbudget/actual-server:latest
    container_name: actual-budget
    restart: unless-stopped
    ports:
      - "5006:5006"
    volumes:
      - ./actual-data:/data
    environment:
      - TZ=UTC
```

Start the server with:

```bash
docker compose up -d
```

Then open `http://localhost:5006` in your browser. The first visit walks you through creating an admin account and your first budget file. All data lives in the `./actual-data` directory, which you should include in your backup routine.

### Reverse Proxy with Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name budget.example.com;

    ssl_certificate /etc/letsencrypt/live/budget.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/budget.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for real-time sync
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Creating Your First Budget

After logging in, the setup flow is straightforward:

1. **Create a new budget file** — this is your financial database
2. **Add accounts** — checking, savings, credit cards, cash
3. **Import transactions** — upload CSV files or configure bank sync
4. **Set up categories** — group by needs (housing, food, transport) and wants (dining, entertainment)
5. **Fund envelopes** — assign available money to each category for the current month
6. **Create rules** — automate categorization for recurring merchants

The rules engine deserves special attention. You can define conditions like "if description contains 'Starbucks', set category to 'Dining Out'" and apply them retroactively to all existing transactions.

---

## Firefly III: Comprehensive Personal Finance Manager

[Firefly III](https://www.firefly-iii.org/) is a full-featured personal finance manager that goes beyond budgeting. It tracks income, expenses, assets, liabilities, and investments with double-entry accounting precision. Where Actual Budget focuses on forward-looking budget allocation, Firefly III excels at historical analysis and reporting.

### Core Philosophy

Firefly III believes you should record every financial event and then derive insights from that data. Every transaction is a movement between accounts with metadata — tags, categories, descriptions, and attachments. Over time, this creates a rich dataset for reports, budgets, and financial planning.

### Key Features

- **Double-entry accounting** — every transaction has a source and destination
- **Multi-currency support** — track accounts in different currencies with automatic conversion
- **Recurring transactions** — set up automatic entries for rent, subscriptions, salary
- **Piggy banks** — savings goals with progress tracking
- **Budgets** — monthly or custom-period spending limits per category
- **Rules and bills** — automate transaction processing
- **REST API** — full programmatic access for custom integrations
- **Import tools** — CSV importer, bank file imports, and third-party connectors
- **Reports and charts** — net worth, income vs. expense, budget performance, category breakdowns
- **Multi-user** — separate financial data per user on a single installation

### Docker Compose Deployment

Firefly III requires a database. Here is a production-ready setup with MariaDB:

```yaml
version: "3.8"

services:
  app:
    image: fireflyiii/core:latest
    container_name: firefly-iii
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - APP_KEY=base64:YOUR_32_CHAR_KEY_HERE
      - DB_CONNECTION=mysql
      - DB_HOST=db
      - DB_PORT=3306
      - DB_DATABASE=firefly
      - DB_USERNAME=firefly
      - DB_PASSWORD=firefly_secret
      - APP_ENV=local
      - APP_LOG_LEVEL=notice
      - TZ=UTC
    volumes:
      - firefly-upload:/var/www/html/storage/upload
    depends_on:
      db:
        condition: service_healthy

  db:
    image: mariadb:11
    container_name: firefly-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=root_secret
      - MYSQL_DATABASE=firefly
      - MYSQL_USER=firefly
      - MYSQL_PASSWORD=firefly_secret
    volumes:
      - firefly-db:/var/lib/mysql
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      start_period: 30s
      interval: 10s
      retries: 5

  cron:
    image: alpine:3
    container_name: firefly-cron
    restart: unless-stopped
    volumes:
      - ./cron.sh:/etc/cron.sh:ro
    entrypoint: ["/etc/cron.sh"]
    command: ["sh", "-c", "while true; do curl -s http://app:8080/api/v1/cron/YOUR_CRON_TOKEN; sleep 86400; done"]

volumes:
  firefly-upload:
  firefly-db:
```

Generate the APP_KEY before starting:

```bash
# Generate a secure 32-character base64 key
openssl rand -base64 32
# Output: abc123... (paste this into APP_KEY)
```

Initialize the database on first run:

```bash
docker compose exec app php artisan firefly-iii:upgrade-database
```

### Setting Up Recurring Transactions

Firefly III shines when you automate your financial tracking:

1. Navigate to **Options → Recurring**
2. Click **Create new recurring transaction**
3. Select type: withdrawal (expense), deposit (income), or transfer
4. Define the schedule: daily, weekly, monthly, or custom cron-like patterns
5. Set start date, end date (optional), and repetition pattern
6. Fill in transaction details: amount, source account, destination account, category

Once configured, the cron job (defined in the compose file above) automatically creates these transactions on schedule.

### Importing Bank Data

The Firefly III data importer runs as a separate container:

```yaml
  importer:
    image: fireflyiii/data-importer:latest
    container_name: firefly-importer
    restart: unless-stopped
    ports:
      - "8081:8080"
    environment:
      - FIREFLY_III_URL=http://app:8080
      - VANITY_URL=http://localhost:8080
    depends_on:
      - app
```

Access it at `http://localhost:8081`. The importer supports CSV files with automatic column mapping and can connect to GoCardless for automatic bank feeds in supported regions.

---

## Beancount: Plain-Text Double-Entry Accounting

[Beancount](https://beancount.github.io/) takes a radically different approach. Instead of a database and web interface, you write your financial records as plain text files using a simple, human-readable syntax. This approach — called **plain-text accounting** — has a devoted following among engineers, accountants, and anyone who values data portability and version control.

### Core Philosophy

Your financial data should be plain text. No proprietary formats, no vendor lock-in, no database migrations. Just files that you can diff, grep, back up with any tool, and store in Git. Beancount reads these files and produces reports, balance sheets, and visualizations through command-line tools.

### Key Features

- **Plain text files** — every transaction is readable and editable in any text editor
- **Double-entry accounting** — built into the syntax by design
- **Git version control** — full history, branching, and collaboration via pull requests
- **Powerful query language** — filter and aggregate transactions programmatically
- **Price tracking** — record commodity prices for investment valuation
- **Flexible reporting** — balance sheets, income statements, commodity reports
- **Third-party tools** — Fava (web UI), BeanHub, Emacs/VS Code integrations
- **No server required** — run reports on any machine with Python installed
- **Extensible** — plugins for custom logic, validation, and report generation

### Installation

Beancount runs on Python and installs via pip:

```bash
pip install beancount[fava]
```

The `[fava]` extra installs Fava, the official web interface for browsing Beancount files.

### Your First Beancount File

Create a file called `finances.bean`:

```text
; finances.bean — Personal finance ledger

; === Account Declarations ===
option "title" "My Personal Finances"
option "operating_currency" "USD"

2020-01-01 open Assets:Checking
2020-01-01 open Assets:Savings
2020-01-01 open Assets:Cash
2020-01-01 open Liabilities:CreditCard
2020-01-01 open Expenses:Groceries
2020-01-01 open Expenses:Rent
2020-01-01 open Expenses:Dining
2020-01-01 open Expenses:Utilities
2020-01-01 open Expenses:Entertainment
2020-01-01 open Expenses:Insurance
2020-01-01 open Income:Salary
2020-01-01 open Income:Interest

; === Opening Balances ===
2020-01-01 * "Opening balances"
  Assets:Checking         5000.00 USD
  Assets:Savings         10000.00 USD
  Equity:Opening-Balances

; === Transactions ===
2026-04-01 * "Monthly salary"
  Assets:Checking        4500.00 USD
  Income:Salary

2026-04-02 * "Rent payment"
  Expenses:Rent          1200.00 USD
  Assets:Checking

2026-04-03 * "Grocery store" #weekly
  Expenses:Groceries       87.43 USD
  Liabilities:CreditCard

2026-04-03 * "Coffee shop"
  Expenses:Dining           5.50 USD
  Liabilities:CreditCard

2026-04-05 * "Transfer to savings"
  Assets:Savings           500.00 USD
  Assets:Checking

2026-04-10 * "Electric bill"
  Expenses:Utilities       124.00 USD
  Liabilities:CreditCard

2026-04-12 * "Grocery store" #weekly
  Expenses:Groceries       92.17 USD
  Liabilities:CreditCard

2026-04-14 * "Movie tickets"
  Expenses:Entertainment    32.00 USD
  Assets:Cash
```

### Running Reports

Generate a balance sheet:

```bash
bean-report finances.bean balances
```

View all transactions in a specific account:

```bash
bean-report finances.bean register Assets:Checking
```

Get a monthly income statement:

```bash
bean-report finances.bean incomebalance
```

### Using Fava — The Web Interface

Fava provides a browser-based view of your Beancount data:

```bash
fava finances.bean
```

This starts a local web server at `http://localhost:5000`. The interface includes:

- **Income statement** with drill-down by account
- **Balance sheet** with asset and liability summaries
- **Journal** — chronological transaction list
- **Query editor** — run Beancount queries interactively
- **Charts** — visual spending breakdowns
- **Editor** — edit the source file directly in the browser

### Running Beancount + Fava with Docker

For a self-hosted setup with automatic Fava access:

```yaml
version: "3.8"

services:
  fava:
    image: python:3.12-slim
    container_name: beancount-fava
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./ledger:/ledger:ro
    working_dir: /ledger
    command: >
      sh -c "
        pip install beancount[fava] &&
        fava --host 0.0.0.0 finances.bean
      "
```

Mount your ledger files in the `./ledger` directory and access Fava at `http://localhost:5000`. For production, add a reverse proxy with authentication.

### Version Controlling Your Finances

The natural workflow for Beancount users is Git:

```bash
git init finances/
cd finances/
git add finances.bean
git commit -m "Initialize ledger with opening balances"

# After adding transactions:
git add finances.bean
git commit -m "Add April 2026 transactions"
```

You can view your financial history with standard Git tools:

```bash
git log --oneline          # See transaction commit history
git diff HEAD~1            # See what changed since last commit
git blame finances.bean    # See who added each transaction
```

This is particularly powerful for shared household finances — each person commits their own transactions, and the git history serves as an audit trail.

---

## Feature Comparison

| Feature | Actual Budget | Firefly III | Beancount + Fava |
|---|---|---|---|
| **Budgeting model** | Envelope-based | Category budgets + tracking | No built-in budgeting |
| **Accounting method** | Single-entry | Double-entry | Double-entry |
| **Data format** | SQLite database | MySQL/PostgreSQL | Plain text files |
| **Web interface** | Built-in PWA | Full web application | Fava (separate) |
| **Offline support** | Yes (offline-first) | No | Yes (local files) |
| **Bank sync** | GoCardless, SimpleFIN | GoCardless (via importer) | Manual or third-party |
| **Mobile app** | PWA (installable) | Responsive web | None (Fava is web) |
| **Multi-user** | No (single user) | Yes | Via Git collaboration |
| **Multi-currency** | Yes | Yes (native) | Yes |
| **Investment tracking** | Basic (net worth) | Yes (with prices) | Yes (price directives) |
| **Recurring transactions** | Via rules | Native support | Manual (or scripts) |
| **API** | Limited | Full REST API | None (CLI-based) |
| **Reports** | Spending, net worth, cash flow | 20+ report types | Balance, income, register, custom |
| **Learning curve** | Low | Medium | High |
| **Setup com[plex](https://www.plex.tv/)ity** | One container | Container + database | Python install or container |
| **Backup strategy** | Export files / copy data dir | Database dumps | Git push |
| **License** | MIT | GNU GPL v3 | Apache 2.0 |
| **Best for** | Monthly budgeting, YNAB refugees | Full financial tracking & analysis | Engineers, auditors, Git users |

---

## Which One Should You Choose?

### Choose Actual Budget If

You want to **control your monthly spending** with a proven envelope methodology. You liked YNAB but refuse to pay a subscription. You need a tool that works on your phone and laptop, syncs between devices, and makes budgeting feel intuitive rather than like accounting homework. The rules engine handles categorization automatically, and the offline-first design means your finances are always accessible.

### Choose Firefly III If

You want **comprehensive financial tracking** with rich reporting. You care about understanding where your money went over the past year, not just managing this month's budget. You want investment tracking, savings goals (piggy banks), recurring transactions, and multi-user support for family finances. The REST API means yo[grafana](https://grafana.com/)uild custom integrations — pull data into a Grafana dashboard, feed it into automation scripts, or connect it to your own applications.

### Choose Beancount If

You are a **developer, engineer, or data professional** who values transparency, portability, and version control. You want your financial data in a format that will still be readable in 30 years — no database migrations, no software upgrades, no vendor dependency. You are comfortable with command-line tools and appreciate the ability to query your finances with a dedicated language. You already use Git for everything and see no reason your financial records should be different.

---

## Running Multiple Tools Together

These tools are not mutually exclusive. A common pattern among self-hosting enthusiasts is running both Actual Budget and Firefly III:

- **Actual Budget** for day-to-day envelope budgeting and monthly planning
- **Firefly III** for long-term financial analysis, investment tracking, and detailed reporting
- **Beancount** as a permanent, version-controlled archive of all financial events

Data flows between them through CSV exports and imports. Firefly III's REST API makes automated synchronization possible, and Beancount's plain-text format is trivially generated from any source.

Here is a unified Docker Compose that runs both Actual Budget and Firefly III on the same host:

```yaml
version: "3.8"

services:
  # Envelope budgeting
  actual:
    image: docker.io/actualbudget/actual-server:latest
    container_name: actual-budget
    restart: unless-stopped
    ports:
      - "5006:5006"
    volumes:
      - ./actual-data:/data

  # Full finance manager
  firefly:
    image: fireflyiii/core:latest
    container_name: firefly-iii
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - APP_KEY=base64:YOUR_KEY_HERE
      - DB_CONNECTION=mysql
      - DB_HOST=firefly-db
      - DB_PORT=3306
      - DB_DATABASE=firefly
      - DB_USERNAME=firefly
      - DB_PASSWORD=firefly_secret
    volumes:
      - firefly-upload:/var/www/html/storage/upload
    depends_on:
      firefly-db:
        condition: service_healthy

  firefly-db:
    image: mariadb:11
    container_name: firefly-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=root_secret
      - MYSQL_DATABASE=firefly
      - MYSQL_USER=firefly
      - MYSQL_PASSWORD=firefly_secret
    volumes:
      - firefly-db:/var/lib/mysql
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      start_period: 30s
      interval: 10s
      retries: 5

volumes:
  firefly-upload:
  firefly-db:
```

Both services share the same Docker network and can be accessed through a single reverse proxy at different subdomains.

---

## Security Considerations

Regardless of which tool you choose, follow these security practices:

1. **Always use HTTPS** — put a reverse proxy with Let's Encrypt certificates in front of every service
2. **Strong passwords** — use a password manager to generate and store unique passwords
3. **Regular backups** — automate daily backups of databases and data directories to an off-site location
4. **Firewall rules** — expose services only through the reverse proxy, not directly to the internet
5. **Keep containers updated** — subscribe to release notifications and update regularly
6. **Network isolation** — run financial services on a separate Docker network or VLAN
7. **Two-factor authentication** — enable 2FA wherever supported (Authentik, Authelia, or built-in)
8. **Audit access logs** — review who accessed your financial data and when

For Beancount specifically, the security model shifts: your data is only as secure as your Git repository and file storage. Use encrypted disks, private repositories, and consider age or GPG encryption for backup archives.

---

## The Bottom Line

Self-hosting your personal finance is one of the highest-impact privacy decisions you can make. Whether you choose the intuitive envelope budgeting of Actual Budget, the comprehensive tracking of Firefly III, or the transparent plain-text approach of Beancount, you gain something that no commercial service can offer: **complete ownership of your financial data**.

The initial setup takes an evening. The payoff — years of private, portable, ad-free financial management — lasts indefinitely. Pick the tool that matches your workflow, deploy it with Docker, and take back control of your numbers.

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
