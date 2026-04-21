---
title: "Complete Guide to Firefly III: Self-Hosted Personal Finance 2026"
date: 2026-04-12
tags: ["guide", "self-hosted", "privacy", "finance"]
draft: false
description: "Take control of your financial data with Firefly III — a powerful self-hosted personal finance manager. Complete setup guide with Docker, import tools, and budgeting workflows."
---

## Why Self-Host Your Personal Finance Manager?

- **Total Privacy**: Your spending habits, income sources, and account balances stay on your hardware — never transmitted to a third-party cloud service.
- **Unlimited Accounts**: No tier restrictions. Track every bank account, credit card, crypto wallet, and cash stash.
- **Custom Rules**: Automate transaction categorization with powerful rule engines tailored to your spending patterns.
- **No Subscription Fees**: Most cloud budgeting apps charge $5–$15/month. Firefly III is free and open source (AGPL-3.0).
- **Data Portability**: Export everything to CSV or JSON at any time. No vendor lock-in.
- **Multi-User Support**: Share a single instance with family members, each with separate accounts and budgets.
- **Multi-Currency**: Track accounts in different currencies with automatic exchange rate updates.

Firefly III is a self-hosted personal finance manager that follows the envelope budgeting methodology. It was created by James Cole and has grown into one of the most capable open-source finance platforms available, supporting double-entry bookkeeping, automated imports from over 2,000 banks via CSV and API, and a robust rule-based transaction categorization engine.

## Core Features

| Feature | Details |
|---------|---------|
| **Account Types** | Asset, Expense, Revenue, Debt, Loan, Mortgage, Liability |
| **Budgeting** | Envelope-style with monthly/weekly caps per category |
| **Rules Engine** | Auto-categorize transactions by description, amount, or tags |
| **Recurring Transactions** | Set up bills, salary deposits, subscriptions |
| **Piggy Banks** | Savings goals with progress tracking |
| **Reports** | Income/expense charts, category breakdowns, net worth over time |
| **Multi-Currency** | Automatic rates via external APIs |
| **API** | Full REST API for third-party integrations |
| **Data Import** | CSV, Spectre API, Nordigen (formerly GoCardless) |
| **Two-Factor Auth** | TOTP-based 2FA for login security |
| **Webhooks** | Trigger external services on transaction events |

## System Requirements

Firefly III is a PHP/Laravel application backed by MySQL, MariaDB, or PostgreSQL. For a single-user household, minimal resources are needed:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 1 core | 2 cores |
| **RAM** | 512 MB | 1 GB |
| **Storage** | 2 GB | 5 GB (for transaction history) |
| **Database** | MariaDB 10.3+ / PostgreSQL 12+ | MariaDB 10.6+ / PostgreSQL 15+ |

A Raspberry Pi 4 or any small VPS with 1 GB of RAM handles Firefly III comfortably.

## [docker](https://www.docker.com/) Installation

The recommended deployment method is Docker Compose. This gives you Firefly III, a database, and a cron container for scheduled tasks in one stack.

### Step 1: Create the project directory

```bash
mkdir -p ~/firefly-iii
cd ~/firefly-iii
```

### Step 2: Write the docker-compose.yml

```yaml
version: "3.8"

services:
  fireflyiii:
    image: fireflyiii/core:latest
    container_name: fireflyiii
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - APP_KEY=${APP_KEY}
      - DB_CONNECTION=mysql
      - DB_HOST=fireflyiii_db
      - DB_PORT=3306
      - DB_DATABASE=firefly
      - DB_USERNAME=firefly
      - DB_PASSWORD=${DB_PASSWORD}
      - TRUSTED_PROXIES=**
    volumes:
      - firefly_upload:/var/www/html/storage/upload
    depends_on:
      - fireflyiii_db
    networks:
      - firefly_net

  fireflyiii_db:
    image: mariadb:lts
    container_name: fireflyiii_db
    restart: unless-stopped
    environment:
      - MYSQL_DATABASE=firefly
      - MYSQL_USER=firefly
      - MYSQL_PASSWORD=${DB_PASSWORD}
      - MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
    volumes:
      - firefly_db:/var/lib/mysql
    networks:
      - firefly_net

  fireflyiii_cron:
    image: alpine:latest
    container_name: fireflyiii_cron
    restart: unless-stopped
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache curl
        while true; do
          curl -fsS http://fireflyiii:8080/api/v1/cron/${CRON_TOKEN} > /dev/null 2>&1
          sleep 86400
        done
    depends_on:
      - fireflyiii
    networks:
      - firefly_net

volumes:
  firefly_upload:
  firefly_db:

networks:
  firefly_net:
    driver: bridge
```

### Step 3: Generate secrets and create .env

```bash
# Generate a random 32-character APP_KEY
APP_KEY=$(openssl rand -base64 32 | tr -d '=+/')
DB_PASSWORD=$(openssl rand -base64 24)
DB_ROOT_PASSWORD=$(openssl rand -base64 24)
CRON_TOKEN=$(openssl rand -hex 16)

cat > .env <<EOF
APP_KEY=${APP_KEY}
DB_PASSWORD=${DB_PASSWORD}
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
CRON_TOKEN=${CRON_TOKEN}
EOF
```

**Important**: Save the `.env` file somewhere safe. If you lose the `APP_KEY`, you cannot decrypt stored credentials.

### Step 4: Start the stack

```bash
docker compose up -d
```

Firefly III will initialize the database on first launch. This takes about 30–60 seconds. Check the logs:

```bash
docker compose logs -f fireflyiii
```

Look for the line indicating the database migration completed successfully, then navigate to `http://your-server-ip:8080` to create your admin account.

## Reverse Proxy Setup

Exposing Firefly III directly on port 8080 is not recommended for production. Place it behind a reverse proxy [caddy](https://caddyserver.com/)TLS termination.

### Caddy (simplest option)

```caddy
finance.yourdomain.com {
    reverse_proxy localhost:8080

    tls your@email.com

    header {
        -Server
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cros[nginx](https://nginx.org/)gin"
    }
}
```

### Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name finance.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/finance.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/finance.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Block access to sensitive paths
    location ~ /\. {
        deny all;
    }
}
```

## First-Time Configuration

After creating your admin account, configure these essential settings:

### 1. Set Your Preferences

Navigate to **Options → Preferences**:

- Set your **fiscal year start** (usually January 1)
- Choose your **default currency**
- Set **week start** to Monday or Sunday
- Enable **dark mode** if preferred

### 2. Create Asset Accounts

Go to **Accounts → Create new** and add your real-world accounts:

```
Account Type: Asset
Account Name: Checking - Chase
Currency: USD (default)

Account Type: Asset
Account Name: Savings - Ally
Currency: USD

Account Type: Asset
Account Name: Cash Wallet
Currency: USD
```

### 3. Set Up Expense Categories

Categories are the backbone of Firefly III's budgeting. Create categories that match your spending:

```
Housing
  ├─ Rent / Mortgage
  ├─ Utilities
  ├─ Internet
  └─ Insurance

Transportation
  ├─ Gas / Fuel
  ├─ Public Transit
  └─ Maintenance

Food
  ├─ Groceries
  └─ Restaurants

Personal
  ├─ Healthcare
  ├─ Entertainment
  └─ Subscriptions
```

### 4. Configure Budgets

Budgets cap spending per category per period:

```
Go to: Budgets → Create new budget
Name: "Monthly Budget - May 2026"

Category          | Monthly Limit
------------------|-------------
Groceries         | $600
Restaurants       | $150
Gas / Fuel        | $200
Entertainment     | $100
Subscriptions     | $75
Healthcare        | $150
```

## Automating Transaction Imports

Manually entering every transaction defeats the purpose of a finance manager. Firefly III supports multiple import methods.

### Option 1: CSV Import (works with every bank)

Most banks let you export transactions as CSV. Firefly III has an importer that maps CSV columns to its data model.

1. **Export CSV from your bank** — ensure it includes date, description, amount, and optionally category.
2. **Download the Firefly III Data Importer** — a separate Docker container:

```yaml
  firefly_importer:
    image: fireflyiii/data-importer:latest
    container_name: firefly_importer
    restart: unless-stopped
    ports:
      - "8081:8080"
    environment:
      - FIREFLY_III_URL=http://fireflyiii:8080
      - VANITY_URL=http://finance.yourdomain.com
    depends_on:
      - fireflyiii
    networks:
      - firefly_net
```

3. **Open the importer** at `http://your-server:8081` and follow the mapping wizard.
4. **Save import configurations** for reuse next month.

### Option 2: Nordigen (free, open-source bank API)

Nordinen (formerly GoCardless) provides free open banking access for 3,000+ banks across Europe and growing support elsewhere. It connects directly to your bank and pulls transactions automatically.

1. **Register at nordigen.com** and get your API credentials.
2. **Add to your Firefly III .env**:

```env
NORDIGEN_SECRET_ID=your_secret_id
NORDIGEN_SECRET_KEY=your_secret_key
```

3. **Restart Firefly III** and configure the connection in the admin panel under **Configuration → Provider Settings**.
4. **Link your accounts** — Firefly III will pull transaction history going back 90 days (or longer, depending on your bank).

### Option 3: Manual CSV mapping with jq

For banks with unusual CSV formats, pre-process the file before importing:

```bash
# Transform a bank's CSV to Firefly III import format
awk -F',' 'NR>1 {
    date=$1;
    desc=$2;
    amount=$3;
    sign = (amount < 0) ? "-" : "";
    gsub(/[$,]/, "", amount);
    printf "%s,%s,%.2f\n", date, desc, sign amount
}' bank_export.csv > firefly_import.csv
```

## Rules Engine: Auto-Categorize Transactions

The rules engine is Firefly III's most powerful feature. Create rules that automatically tag and categorize incoming transactions.

### Example Rules

**Rule: Identify grocery stores**

```
Trigger: On store of transaction
Conditions:
  - Description contains "WALMART"
  - OR Description contains "KROGER"
  - OR Description contains "WHOLE FOODS"
Actions:
  - Set category to "Groceries"
  - Set tag to "essential"
```

**Rule: Flag subscriptions**

```
Trigger: On store of transaction
Conditions:
  - Description contains "NETFLIX"
  - OR Description contains "SPOTIFY"
  - OR Description contains "GITHUB"
Actions:
  - Set category to "Subscriptions"
  - Set tag to "recurring"
```

**Rule: Split utility bills**

```
Trigger: On store of transaction
Conditions:
  - Description contains "ELECTRIC CO"
Actions:
  - Set category to "Utilities"
  - Set tag to "housing"
```

Rules can be configured through the web UI under **Rules → Create new rule**. For advanced users, rules can also be managed via the REST API.

## Piggy Banks: Track Savings Goals

Piggy banks let you set savings targets and monitor progress:

```
Name: Emergency Fund
Target: $10,000
Linked Account: Savings - Ally
Current: $3,200 (32%)
Start Date: 2026-01-01
Target Date: 2026-12-31
```

Every time you transfer money to the linked savings account, Firefly III updates the piggy bank progress automatically.

## Net Worth and Reports

Firefly III generates several built-in reports:

| Report | What It Shows |
|--------|--------------|
| **Net Worth** | Total assets minus liabilities over time |
| **Income vs Expenses** | Monthly comparison chart |
| **Budget Report** | Actual spending vs budgeted amount per category |
| **Category Report** | Spending breakdown by category with percentages |
| **Tag Report** | Spending filtered by tags |
| **Bill Report** | Upcoming and paid bills |
| **Piggy Bank Report** | Progress on all savings goals |

The **net worth report** is particularly valuable — it gives you a single number tracking your financial health over months and years.

## Advanced: Custom API Integrations

Firefly III has a comprehensive REST API documented at `/api/v1/about`. Here are practical uses:

### Check current balance via API

```bash
curl -s -H "Authorization: Bearer ${API_TOKEN}" \
  "http://localhost:8080/api/v1/accounts" | \
  jq '.data[] | select(.attributes.type == "asset") |
      {name: .attributes.name, balance: .attributes.current_balance}'
```

### Create a transaction via API

```bash
curl -X POST http://localhost:8080/api/v1/transactions \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apply_rules": true,
    "fire_webhooks": true,
    "transactions": [{
      "type": "withdrawal",
      "date": "2026-04-12",
      "amount": "45.50",
      "description": "Lunch at downtown cafe",
      "source_name": "Checking - Chase",
      "destination_name": "Restaurants",
      "category_name": "Food",
      "tags": ["dining-out"]
    }]
  }'
```

### Mobile access with 3rd-party apps

Several mobile apps connect to Firefly III via its API:

- **Firefly III Mobile** (unofficial, Android/iOS)
- **Popsicle** (iOS, open source)
- **Firefly Assistant** (Android, automates SMS-based transaction entry)

## Backup Strategy

Protect your financial data with regular backups:

```bash
#!/bin/bash
# backup_firefly.sh — run via cron weekly

BACKUP_DIR="/backups/firefly-iii"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Export Firefly III data via API
curl -s -H "Authorization: Bearer ${API_TOKEN}" \
  "http://localhost:8080/api/v1/export/accounts" \
  -o "$BACKUP_DIR/accounts_${TIMESTAMP}.json"

curl -s -H "Authorization: Bearer ${API_TOKEN}" \
  "http://localhost:8080/api/v1/export/transactions" \
  -o "$BACKUP_DIR/transactions_${TIMESTAMP}.json"

# Backup database
docker exec fireflyiii_db mysqldump \
  -u root -p"${DB_ROOT_PASSWORD}" firefly \
  > "$BACKUP_DIR/db_${TIMESTAMP}.sql"

# Compress
tar czf "$BACKUP_DIR/firefly_${TIMESTAMP}.tar.gz" \
  "$BACKUP_DIR"/*_${TIMESTAMP}.*

# Clean backups older than 90 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +90 -delete

echo "Backup complete: firefly_${TIMESTAMP}.tar.gz"
```

Add to crontab:

```cron
0 3 * * 0 /path/to/backup_firefly.sh >> /var/log/firefly-backup.log 2>&1
```

## Migration from Other Services

### From Mint (RIP) or Monarch Money

Most services let you export transaction history as CSV:

1. Export all transactions as CSV from your current service.
2. Map the columns using the Firefly III Data Importer.
3. Import accounts first, then transactions.
4. Recreate budgets and categories manually (these rarely export cleanly).

### From YNAB

YNAB uses a different data model but exports are possible:

1. Go to **Settings → Export Data** in YNAB.
2. Download the CSV files for transactions and budgets.
3. Use the importer to map YNAB's category format to Firefly III categories.
4. Note: YNAB's envelope budgeting maps well to Firefly III's budget system.

## Common Issues and Solutions

### "APP_KEY missing" error

The `APP_KEY` must be set before the first database migration. If you started without it:

```bash
# Stop the container, clear the database volume, add APP_KEY, restart
docker compose down -v
# Add APP_KEY to .env
docker compose up -d
```

### High memory usage on MariaDB

For small deployments, tune MariaDB to use less RAM:

```bash
docker exec fireflyiii_db bash -c 'cat > /etc/mysql/conf.d/custom.cnf <<EOF
[mysqld]
innodb_buffer_pool_size = 128M
max_connections = 10
performance_schema = OFF
EOF'
docker compose restart fireflyiii_db
```

### Missing transactions from bank import

Banks sometimes paginate or limit exports. If you're missing data:

1. Check the date range on the export — some banks only show 90 days by default.
2. Request a longer history in your bank's online portal.
3. For Nordigen, ensure the account consent hasn't expired (90-day default).
4. Re-run the import with a fresh CSV covering the missing date range.

## Getting Help

- **Official Documentation**: [docs.firefly-iii.org](https://docs.firefly-iii.org)
- **GitHub Repository**: [github.com/firefly-iii/firefly-iii](https://github.com/firefly-iii/firefly-iii)
- **Discord Community**: Active community for troubleshooting and feature discussions
- **Reddit**: r/FireflyIII for user tips and workflows

Firefly III turns personal finance management from a monthly chore into an automated, privacy-respecting system that gives you genuine insight into where your money goes — without selling your data to advertisers or charging subscription fees.

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
