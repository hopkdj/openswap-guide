---
title: "Self-Hosted Subscription & Recurring Payment Trackers: Wallos vs ihatemoney vs Spliit"
date: "2026-06-03"
tags: ["subscription-management", "finance", "self-hosted", "expense-tracking", "budgeting", "personal-finance"]
draft: false
---

## Why Self-Host Your Subscription Tracker?

Subscription services have quietly become one of the largest categories of personal spending. Between streaming services, cloud storage, software licenses, news subscriptions, and membership fees, the average household manages 12-15 recurring payments — often without a clear picture of the total monthly cost. Self-hosting a subscription tracker gives you complete visibility and control over your recurring expenses.

Commercial subscription management apps often require linking your bank account or credit card, creating a privacy risk. Self-hosted alternatives keep your financial data on your own server, accessible only to you. You can track subscriptions, split shared expenses with roommates or family members, and generate custom reports — all without sharing data with third parties.

For comprehensive personal finance management, see our [personal finance comparison](../2026-05-01-maybe-finance-vs-firefly-iii-vs-actual-budget-self-hosted-personal-finance/) and our [self-hosted billing platforms guide](../2026-05-03-fossbilling-vs-paymenter-vs-solidinvoice-self-hosted-billing-guide/). For payment processing, check our [self-hosted payment gateways guide](../2026-04-29-self-hosted-payment-gateways-hyperswitch-btcpay-server-guide/).

## Comparison Table

| Feature | Wallos | ihatemoney | Spliit |
|---------|--------|------------|--------|
| **Stars** | 2,500+ | 1,200+ | 900+ |
| **Language** | PHP | Python (Flask) | TypeScript (Next.js) |
| **Last Update** | Jun 2026 | May 2026 | May 2026 |
| **Focus** | Subscription tracking | Shared expense splitting | Group expense sharing |
| **Subscription Management** | Yes (renewal dates, costs, categories) | No (general expenses) | No (one-time splits) |
| **Recurring Payments** | Yes (monthly/yearly tracking) | No | Limited |
| **Multi-Currency** | Yes | No | Yes (automatic conversion) |
| **Group Splitting** | No | Yes (detailed balance) | Yes (simplified splits) |
| **Payment Reminders** | Yes (email notifications) | No | No |
| **API** | Yes (REST) | Yes (REST) | Yes (REST) |
| **Docker Support** | Yes | Yes | Yes |
| **Mobile Friendly** | Responsive | Responsive | Responsive (PWA) |

## Wallos: Dedicated Subscription Manager

Wallos is a PHP-based subscription tracking application designed specifically for managing recurring payments. It tracks subscription costs, renewal dates, payment methods, and categories — giving you a clear dashboard of your total monthly and yearly subscription spending.

```yaml
# docker-compose.yml for Wallos
version: '3'
services:
  wallos:
    image: bellamy/wallos:latest
    ports:
      - "8282:80"
    environment:
      - TZ=UTC
    volumes:
      - wallos_data:/var/www/html/db
      - wallos_logos:/var/www/html/images/uploads/logos
    restart: unless-stopped

volumes:
  wallos_data:
  wallos_logos:
```

Wallos includes email notifications for upcoming renewals, a visual calendar showing all subscription dates, and cost analysis by category. It supports multiple currencies and payment methods (credit card, PayPal, bank transfer), making it easy to see exactly where your money goes each month.

## ihatemoney: Shared Expense Settlement

ihatemoney (stylized as "I Hate Money") is a Python Flask application for tracking shared expenses between groups of people. It is the go-to choice for roommates splitting rent and utilities, friends sharing vacation costs, or couples managing joint expenses.

```yaml
# docker-compose.yml for ihatemoney
version: '3'
services:
  ihatemoney:
    image: ihatemoney/ihatemoney:latest
    ports:
      - "5000:5000"
    environment:
      - ACTIVATE_DEMO_PROJECT=false
      - ADMIN_PASSWORD=change-me
      - SECRET_KEY=change-me-to-random
      - SQLALCHEMY_DATABASE_URI=sqlite:////data/ihatemoney.db
    volumes:
      - ihatemoney_data:/data
    restart: unless-stopped

volumes:
  ihatemoney_data:
```

ihatemoney calculates who owes whom and simplifies debts between group members. It supports multiple projects (one per group), bill categorization, and settlement tracking. The interface is deliberately simple — create a project, invite members via a shared link, and start logging expenses.

## Spliit: Modern Group Expense Sharing

Spliit is a TypeScript/Next.js application that brings modern UX to group expense sharing. It handles multi-currency splits with automatic exchange rate conversion, making it ideal for international travel groups or distributed teams.

```yaml
# docker-compose.yml for Spliit
version: '3'
services:
  spliit:
    image: spliit/spliit:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://spliit:spliit_secret@db:5432/spliit
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=change-me-to-random-string
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=spliit
      - POSTGRES_USER=spliit
      - POSTGRES_PASSWORD=spliit_secret
    volumes:
      - spliit_db:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  spliit_db:
```

Spliit focuses on one-time expense splits rather than recurring subscriptions. Its strength is the polished interface and multi-currency support — group members can log expenses in their local currency, and Spliit automatically converts everything to a base currency for settlement calculations.

## Choosing the Right Tool

The three platforms serve distinct but complementary use cases. Wallos is the dedicated subscription tracker — use it to monitor your Netflix, Spotify, cloud hosting, and software license costs in one dashboard. ihatemoney is the classic shared expense manager for roommates and travel groups who need detailed balance tracking over time. Spliit is the modern alternative for one-time expense splits with multi-currency requirements.

For complete financial tracking, you might run both Wallos (for subscription monitoring) and ihatemoney or Spliit (for shared expenses). All three are open-source, Docker-deployable, and store data on your own infrastructure — no third-party access to your financial information.

## Security Best Practices for Financial Data

When self-hosting tools that handle financial information, security is paramount. All three platforms store financial data on your own server, but implementing proper security measures is your responsibility.

For Wallos and ihatemoney, placing them behind a reverse proxy (nginx, Caddy, or Traefik) with HTTPS is the minimum requirement. Both support HTTP Basic Auth out of the box, but for stronger security, configure OAuth2 or OpenID Connect authentication through your reverse proxy. This adds a second authentication layer and enables features like two-factor authentication through your identity provider.

Spliit uses NextAuth.js, which supports multiple authentication providers including GitHub, Google, and custom OIDC providers. Take advantage of this by configuring a self-hosted identity provider like Authentik or Keycloak, then connecting Spliit to it for unified authentication across all your self-hosted services. This also enables single sign-on — log in once to access your subscription tracker, expense splitter, and other tools.

Database encryption is another consideration. All three platforms store data in unencrypted databases by default (SQLite or PostgreSQL). For sensitive financial data, consider enabling filesystem-level encryption (LUKS, dm-crypt), using encrypted database volumes, or placing database files on encrypted storage. Regular encrypted backups to off-site locations ensure you never lose your financial records.

Network isolation is the final layer. Run these applications on a dedicated Docker network that is isolated from public-facing services. Use firewall rules to restrict database access to only the application container. For Wallos specifically, which sends email reminders, use an SMTP relay service rather than exposing your mail server directly to the application container.

## Building a Complete Self-Hosted Finance Stack

A subscription tracker is one piece of a broader personal finance management stack. Many self-hosted users combine multiple tools: Wallos for subscription monitoring, Firefly III or Actual Budget for overall budgeting, ihatemoney or Spliit for shared expenses, and Invoice Ninja or Crater for invoicing and billing. Each tool excels at its specific function, and together they provide comprehensive financial visibility without relying on any commercial service.

The API-driven architecture of these tools enables integration possibilities. Wallos provides REST endpoints for querying subscription data — you could build a Grafana dashboard showing your monthly subscription costs trended over time. ihatemoney's API enables automated expense logging via webhooks or cron jobs. Spliit's modern TypeScript codebase and REST API make it the most developer-friendly option for custom integrations and automation.

## FAQ

### Can Wallos automatically detect subscriptions from my bank?

No. Wallos requires manual entry of subscription details. It is designed for privacy-conscious users who prefer not to link banking credentials to third-party services. You enter subscription name, cost, billing cycle, and payment method once, and Wallos handles the ongoing tracking and reminders.

### How does ihatemoney simplify debts between multiple people?

ihatemoney uses a debt simplification algorithm that minimizes the number of transactions needed to settle up. For example, if Alice owes Bob $20, Bob owes Carol $15, and Carol owes Alice $10, ihatemoney calculates that Alice can pay Bob $10 and Carol $0, reducing three transactions to one. This is especially useful for large groups where pairwise debts become complicated.

### Does Spliit support recurring expenses like monthly rent?

Spliit is primarily designed for one-time expense splits. While you can create recurring groups and manually add repeating expenses, it does not have built-in recurring expense automation like Wallos. For ongoing shared expenses like rent and utilities, ihatemoney is a better fit due to its long-running project model.

### Are there mobile apps for these platforms?

All three offer responsive web interfaces that work on mobile browsers. Spliit provides the best mobile experience with its PWA support and modern Next.js interface. Wallos and ihatemoney work well on mobile screens but don't have dedicated native apps. All three expose REST APIs if you want to build custom mobile clients.

### How do these compare to Firefly III or Actual Budget?

Firefly III and Actual Budget are comprehensive personal finance managers that handle all income, expenses, budgets, and reports. Wallos is specialized for subscription tracking — it is simpler and more focused. ihatemoney and Spliit are for shared expense splitting between people, which is a different use case from personal budgeting. You might use Wallos alongside Firefly III: Wallos for subscription monitoring and Firefly III for overall budgeting.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Subscription & Recurring Payment Trackers: Wallos vs ihatemoney vs Spliit",
  "description": "Compare open-source self-hosted platforms for subscription management, recurring payment tracking, and shared expense splitting. Wallos, ihatemoney, and Spliit compared with Docker deployment guides.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
