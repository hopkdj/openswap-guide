---
title: "Self-Hosted Payment Gateways: Hyperswitch vs BTCPay Server (2026)"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "payments", "fintech"]
draft: false
description: "Compare the best self-hosted payment gateway solutions in 2026. Hyperswitch for multi-provider payment orchestration and BTCPay Server for Bitcoin processing — with Docker deployment guides."
---

Running your own payment processing infrastructure means complete control over transaction routing, zero vendor lock-in, and no surprise fee increases from third-party providers. Whether you need to orchestrate payments across Stripe, PayPal, and Adyen — or process Bitcoin directly without intermediaries — self-hosted payment gateways give you the independence to manage your money on your own terms.

## Why Self-Host Your Payment Gateway?

Third-party payment processors like Stripe and PayPal are convenient, but they come with significant trade-offs:

- **Fee volatility** — providers can raise processing rates without notice
- **Account freezes** — funds can be held or accounts suspended based on automated risk algorithms
- **Limited routing control** — you cannot optimize which processor handles each transaction
- **Data lock-in** — customer payment data lives on someone else's servers
- **Geographic restrictions** — many providers block entire countries or regions

Self-hosted payment infrastructure addresses these concerns. You control the routing logic, own the transaction data, and can switch providers without rebuilding your integration. Two projects lead the self-hosted payment space in 2026, each solving a different problem.

## Hyperswitch: Open-Source Payment Orchestration

[Hyperswitch](https://github.com/juspay/hyperswitch) is an open-source payment switch written in Rust that lets you route transactions across multiple payment providers from a single integration. Built by Juspay, it processes billions in transactions and is designed for companies that need redundancy, cost optimization, and geographic flexibility in their payment stack.

**Key features:**

- Connect to 140+ payment processors through a unified API
- Smart routing rules based on cost, success rate, geography, and currency
- Real-time payment analytics and failure analytics
- No-code connector configuration through the HyperSwitch dashboard
- PCI-DSS compliant architecture

With over **42,500 GitHub stars** and active daily commits, Hyperswitch is one of the most popular open-source fintech projects. The Rust codebase delivers sub-millisecond latency for payment routing decisions.

### Hyperswitch Docker Deployment

Hyperswitch ships with a production-ready Docker Compose configuration that includes PostgreSQL, Redis, and ClickHouse for analytics.

```yaml
# hyperswitch-docker-compose.yml
volumes:
  pg_data:
  redisinsight_store:
  ckh_data:

networks:
  router_net:

services:
  pg:
    image: docker.io/postgres:latest
    ports:
      - "5432:5432"
    networks:
      - router_net
    volumes:
      - pg_data:/var/lib/postgresql
    environment:
      - POSTGRES_USER=db_user
      - POSTGRES_PASSWORD=StrongPassword123
      - POSTGRES_DB=hyperswitch_db
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d hyperswitch_db -U db_user"]
      interval: 5s
      retries: 3
      start_period: 5s
      timeout: 5s

  redis-standalone:
    image: docker.io/redis:7
    networks:
      - router_net
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD-SHELL", "redis-cli ping | grep PONG"]
      interval: 5s
      retries: 3
      start_period: 5s
      timeout: 5s

  hyperswitch-server:
    image: juspay/hyperswitch:latest
    ports:
      - "8080:8080"
    networks:
      - router_net
    depends_on:
      pg:
        condition: service_healthy
      redis-standalone:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://db_user:StrongPassword123@pg:5432/hyperswitch_db
      - REDIS_URL=redis://redis-standalone:6379
      - SERVER_PORT=8080
      - ADMIN_API_KEY=your-admin-api-key
      - JWT_SECRET=your-jwt-secret-key-minimum-32-chars
```

Start the stack:

```bash
docker compose -f hyperswitch-docker-compose.yml up -d
```

Once running, access the dashboard at `http://localhost:8080` and the REST API at `http://localhost:8080/api`. Configure your first payment connector through the dashboard or API:

```bash
# Create a payment connector (example: Stripe)
curl -X POST http://localhost:8080/v1/account/merchant_1/connectors \
  -H "api-key: your-admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "connector_name": "stripe",
    "connector_account_details": {
      "auth_type": "BodyKey",
      "api_key": "sk_test_your_stripe_key",
      "key1": "pk_test_your_publishable_key"
    },
    "business_country": "US",
    "business_label": "default"
  }'
```

### Payment Routing Configuration

One of Hyperswitch's most powerful features is its routing engine. You can define rules to route transactions based on multiple criteria:

```json
{
  "routing_algorithm": {
    "type": "advanced",
    "rules": [
      {
        "condition": {
          "connector": ["stripe"],
          "currency": ["USD"],
          "payment_method": ["card"]
        },
        "priority": 1
      },
      {
        "condition": {
          "connector": ["adyen"],
          "currency": ["EUR"],
          "amount": { "gte": 10000 }
        },
        "priority": 2
      }
    ]
  }
}
```

This routes USD card payments through Stripe and EUR payments above €100 through Adyen, optimizing for regional success rates and processing costs.

## BTCPay Server: Self-Hosted Bitcoin Payment Processor

[BTCPay Server](https://github.com/btcpayserver/btcpayserver) is a free, open-source, self-hosted Bitcoin payment processor. It lets you accept Bitcoin payments directly — without a middleman, without fees, and without censorship. Your keys, your coins, your customers.

**Key features:**

- Zero transaction fees (only Bitcoin network fees apply)
- No third-party involvement — payments go directly to your wallet
- Built-in invoicing system with automatic exchange rate conversion
- Supports Lightning Network for instant, low-fee micropayments
- Point-of-sale app for in-person payments
- Crowdfunding and donation page tools

With over **7,500 GitHub stars** and a passionate community, BTCPay Server has become the standard for self-hosted cryptocurrency payments. The C# application runs on .NET and supports full Bitcoin node integration through NBXplorer.

### BTCPay Server Docker Deployment

BTCPay Server provides official Docker deployment scripts through its `btcpayserver-docker` repository. The production configuration includes Nginx reverse proxy, Let's Encrypt SSL, PostgreSQL, and a Bitcoin node.

```yaml
# btcpay-docker-compose.yml (simplified BTC-only configuration)
services:
  nginx:
    restart: unless-stopped
    image: nginx:stable
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "nginx_conf:/etc/nginx/conf.d"
      - "nginx_vhost:/etc/nginx/vhost.d"
      - "nginx_html:/usr/share/nginx/html"
      - "nginx_certs:/etc/nginx/certs:ro"
    networks:
      - btcpay_net

  btcpayserver:
    restart: unless-stopped
    image: nicolasdorier/btcpayserver:latest
    expose:
      - "49392"
    environment:
      BTCPAY_POSTGRES: "User ID=postgres;Host=postgres;Port=5432;Database=btcpayserver"
      BTCPAY_NETWORK: mainnet
      BTCPAY_BIND: 0.0.0.0:49392
      BTCPAY_EXTERNALURL: https://pay.yourdomain.com/
      BTCPAY_CHAINS: "btc"
      BTCPAY_BTCEXPLORERURL: http://nbxplorer:32838/
    volumes:
      - "btcpay_datadir:/datadir"
    networks:
      - btcpay_net

  nbxplorer:
    restart: unless-stopped
    image: nicolasdorier/nbxplorer:latest
    expose:
      - "32838"
    environment:
      NBXPLORER_NETWORK: mainnet
      NBXPLORER_CHAINS: "btc"
      NBXPLORER_BTCRPCURL: http://bitcoind:43782
      NBXPLORER_POSTGRES: "User ID=postgres;Host=postgres;Port=5432;Database=nbxplorer"
    volumes:
      - "nbxplorer_datadir:/datadir"
    networks:
      - btcpay_net

  postgres:
    restart: unless-stopped
    image: postgres:15
    environment:
      POSTGRES_HOST_AUTH_METHOD: trust
    volumes:
      - "postgres_data:/var/lib/postgresql/data"
    networks:
      - btcpay_net

volumes:
  nginx_conf:
  nginx_vhost:
  nginx_html:
  nginx_certs:
  btcpay_datadir:
  nbxplorer_datadir:
  postgres_data:

networks:
  btcpay_net:
```

For a quick production deployment, use the official setup script:

```bash
# Clone the official Docker deployment repo
git clone https://github.com/btcpayserver/btcpayserver-docker.git
cd btcpayserver-docker

# Run the setup script
./btcpay-setup.sh -i

# The interactive installer will prompt for:
# - Your domain name
# - Bitcoin node settings
# - Lightning Network configuration (optional)
```

### Creating Your First Invoice

Once BTCPay Server is running, create an invoice through the web dashboard or API:

```bash
# Create a payment request via API
curl -X POST "https://pay.yourdomain.com/api/v1/stores/YOUR_STORE_ID/payment-requests" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 99.99,
    "currency": "USD",
    "title": "Premium Subscription",
    "description": "Annual premium plan",
    "expiryDate": "2026-05-29T00:00:00Z"
  }'
```

Customers receive a payment page with a Bitcoin address (or Lightning invoice) and a countdown timer. Payments are detected automatically through NBXplorer's blockchain monitoring.

## Head-to-Head Comparison

| Feature | Hyperswitch | BTCPay Server |
|---------|-------------|---------------|
| **Primary purpose** | Payment orchestration across providers | Direct Bitcoin/Lightning payments |
| **Language** | Rust | C# (.NET) |
| **GitHub stars** | 42,500+ | 7,500+ |
| **Payment methods** | Cards, wallets, bank transfers (via connectors) | Bitcoin on-chain, Lightning Network |
| **Transaction fees** | Per-connector fees (pass-through) | Zero platform fees (only BTC network fees) |
| **Payment processors** | 140+ (Stripe, PayPal, Adyen, etc.) | N/A — direct blockchain settlement |
| **Multi-currency** | Yes — automatic conversion | Yes — fiat pricing, BTC settlement |
| **Dashboard** | Yes — analytics, routing rules, connectors | Yes — invoices, stores, reports |
| **API** | RESTful API with SDKs | RESTful API |
| **Lightning Network** | Via connector | Native support |
| **Database** | PostgreSQL + Redis + ClickHouse | PostgreSQL |
| **Docker support** | Official docker-compose.yml | Official btcpayserver-docker repo |
| **License** | Apache 2.0 | MIT |

## Which One Should You Choose?

**Choose Hyperswitch if:**

- You need to accept traditional payment methods (credit cards, debit cards, digital wallets)
- You want to route transactions across multiple providers for redundancy
- You operate in multiple countries and need region-specific payment methods
- You want to optimize processing costs by dynamically selecting the cheapest connector
- You need detailed payment analytics and failure tracking

**Choose BTCPay Server if:**

- You want to accept Bitcoin payments without any intermediary
- You value financial sovereignty and censorship resistance
- You want zero platform fees on transactions
- You need Lightning Network support for instant micropayments
- You run an online store and want a self-hosted checkout experience

**Use both** if you want a complete payment stack: Hyperswitch handles fiat payment orchestration while BTCPay Server processes Bitcoin payments. Many merchants integrate both to offer customers maximum payment flexibility.

## FAQ

### Is Hyperswitch production-ready?

Yes. Hyperswitch is used in production by Juspay to process billions of dollars in transactions. The open-source version includes the core routing engine, connector framework, and dashboard. Enterprise features like advanced analytics and dedicated support are available through Juspay's commercial offering.

### Can BTCPay Server process cryptocurrencies other than Bitcoin?

BTCPay Server primarily supports Bitcoin on-chain and Lightning Network payments. It also supports a limited number of altcoins through community plugins, including Litecoin, Monero, and Ethereum (via third-party integrations). For multi-crypto support, BTCPay Server's architecture allows community-developed coin plugins.

### Do I need a Bitcoin node to run BTCPay Server?

No. BTCPay Server uses NBXplorer as a lightweight blockchain indexer, which connects to a Bitcoin node (either local or remote). The official Docker deployment includes everything you need — NBXplorer handles the blockchain indexing so you do not need to run a full Bitcoin node yourself. However, running your own node improves privacy and removes reliance on external services.

### How does Hyperswitch handle PCI compliance?

Hyperswitch is designed with a PCI-DSS compliant architecture. Payment card data never touches your servers — it flows directly from the customer's browser to the payment processor via Hyperswitch's redirect or hosted payment page. Your Hyperswitch instance only stores tokenized references, not raw card data.

### Can I migrate from Stripe to Hyperswitch?

Yes. Hyperswitch supports Stripe as a connector, so you can gradually migrate by routing a percentage of traffic through Hyperswitch while keeping Stripe as a direct integration. Once confident in Hyperswitch's reliability, you can add additional connectors and eventually remove the direct Stripe integration.

### What happens if my BTCPay Server goes offline during a payment?

Bitcoin payments are recorded on the blockchain, not on your server. If BTCPay Server goes offline after a customer sends payment, the transaction is still confirmed on the blockchain. When your server comes back online, NBXplorer will detect the confirmed payment and update the invoice status accordingly. Funds are never lost.

### Is there a cost to running these payment gateways?

Both Hyperswitch and BTCPay Server are free and open-source. Infrastructure costs depend on your deployment:
- **Hyperswitch**: Requires PostgreSQL, Redis, and optionally ClickHouse. A modest VPS (4 CPU, 8 GB RAM) handles moderate traffic.
- **BTCPay Server**: Requires PostgreSQL and optionally a Bitcoin node. Without a local node, 2 CPU / 4 GB RAM is sufficient. With a local Bitcoin node, plan for 500 GB+ storage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Payment Gateways: Hyperswitch vs BTCPay Server (2026)",
  "description": "Compare the best self-hosted payment gateway solutions in 2026. Hyperswitch for multi-provider payment orchestration and BTCPay Server for Bitcoin processing — with Docker deployment guides.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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

For more on self-hosted commerce platforms, see our [Medusa vs Saleor vs Vendure e-commerce guide](../best-self-hosted-ecommerce-platforms-medusa-saleor-vendure-2026/) and [Lago vs Kill Bill billing platforms comparison](../2026-04-21-lago-vs-killbill-open-source-billing-platforms-guide/). If you handle client invoicing, our [Invoice Ninja vs Akaunting vs Crater guide](../invoice-ninja-akaunting-crater-self-hosted-invoicing-guide/) covers the best self-hosted invoicing solutions.
