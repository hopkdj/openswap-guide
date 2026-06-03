---
title: "Self-Hosted PHP E-Commerce Platforms: Sylius vs Bagisto vs Spree Commerce in 2026"
date: "2026-06-04"
tags: ["ecommerce", "php", "sylius", "bagisto", "spree", "online-store", "open-source", "self-hosted", "shopping-cart", "headless-commerce", "laravel", "symfony"]
draft: false
---

## Introduction

The open-source e-commerce landscape has evolved dramatically. While platforms like WooCommerce (WordPress) and Magento dominate market share, a new generation of headless, API-first e-commerce platforms has emerged — built on modern PHP frameworks with clean architectures designed for developers who need flexibility beyond what traditional monolithic platforms offer.

This guide compares three leading PHP-based e-commerce platforms: **Sylius** — a Symfony-based headless commerce framework, **Bagisto** — a Laravel-powered e-commerce platform with a rich admin panel, and **Spree Commerce** — a Ruby on Rails headless commerce platform reborn with modern API capabilities. Each takes a distinct approach to solving the online store challenge.

## Comparison Table

| Feature | Sylius | Bagisto | Spree Commerce |
|---------|--------|---------|----------------|
| **Stars** | 8,483 | 26,974 | 15,455 |
| **Language** | PHP (Symfony) | PHP (Laravel) | Ruby (Rails) |
| **License** | MIT | MIT (OSL 3.0 for enterprise) | BSD |
| **Architecture** | Headless, API-first | Full-stack with REST API | Headless, API-first |
| **Admin Panel** | Yes (Sylius Admin) | Yes (built-in) | Yes (Spree Admin) |
| **Multi-Store** | Yes (channels) | Yes (multi-store) | Via extensions |
| **Multi-Currency** | Native | Native | Via extensions |
| **Headless Frontend** | Next.js Storefront | Bagisto GraphQL API | Next.js Storefront |
| **Docker Support** | Official Docker | Official Docker | Official Docker |
| **Database** | MySQL/PostgreSQL | MySQL/PostgreSQL | PostgreSQL/MySQL |
| **Plugin/Marketplace** | 200+ plugins | 50+ extensions | 500+ extensions |
| **Best For** | Custom commerce solutions, B2B | Laravel shops, marketplaces | Headless storefronts, API-driven |

## Sylius: The Symfony Commerce Framework

Sylius is not just an e-commerce application — it's a **commerce framework** built on top of Symfony, one of PHP's most respected frameworks. This architectural choice means Sylius provides building blocks (product catalog, cart, checkout, orders, payments, shipping) that developers compose into custom commerce solutions rather than configuring a monolithic application.

Key strengths:
- **Component-based architecture**: Each commerce domain (taxation, shipping, promotions) is a standalone Symfony bundle
- **Plugin system**: 200+ community plugins for payment gateways, shipping carriers, and CRM integrations
- **Headless by design**: Full REST and GraphQL API with a separate admin panel (Sylius Admin)
- **B2B features**: Customer groups, corporate accounts, quote management, and tiered pricing
- **Testing culture**: Comprehensive Behat test suite, making behavior-driven development part of the platform

Sylius is the go-to choice for agencies and enterprises building custom commerce experiences. Rather than fighting against a platform's assumptions, you build exactly what you need using Sylius's components.

## Bagisto: The Laravel E-Commerce Powerhouse

Bagisto has rapidly become the most popular open-source e-commerce platform on GitHub, with over 26,000 stars. Built on Laravel — PHP's most popular framework — Bagisto provides a polished, full-featured e-commerce experience out of the box while maintaining Laravel's developer-friendly philosophy.

Notable features:
- **Complete admin panel**: Product management, order processing, customer management, and analytics — all in a clean Laravel admin interface
- **Multi-vendor marketplace**: Built-in marketplace functionality allowing multiple sellers on a single platform
- **GraphQL API**: Full GraphQL support for headless frontend development
- **Theme system**: Customizable storefront themes with a dedicated theme marketplace
- **Localization**: Built-in multi-language and multi-currency support with RTL compatibility
- **Booking/product types**: Supports virtual products, downloadable products, bookings, and subscriptions

Bagisto is ideal for businesses that want a complete e-commerce solution quickly — especially those already invested in the Laravel ecosystem or looking for a Mage

nto-style experience without the complexity.

## Spree Commerce: The API-First Storefront Platform

Spree Commerce is a veteran in the open-source e-commerce space, with over a decade of history. Originally a monolithic Rails application, Spree has reinvented itself as a **headless commerce platform** with a modern API layer, TypeScript SDK, and Next.js storefront reference implementation.

Current architecture:
- **Spree API**: RESTful and GraphQL APIs for the complete commerce lifecycle
- **Spree Admin**: Modern admin panel for managing products, orders, and customers
- **Storefront SDK**: TypeScript/JavaScript SDK for building custom storefronts
- **Next.js Commerce**: Official Next.js storefront with full commerce functionality
- **Extensible**: 500+ community extensions covering payments, shipping, taxes, and integrations

Spree's Ruby on Rails foundation means it inherits Rails' conventions and ecosystem. For teams familiar with Rails or looking for a battle-tested commerce backend to pair with a modern JavaScript frontend, Spree offers a compelling combination of maturity and modernity.

## Docker Compose Deployment

### Sylius Development Docker Compose

```yaml
version: '3.8'
services:
  php:
    image: php:8.2-fpm
    volumes:
      - ./sylius:/var/www/sylius
    working_dir: /var/www/sylius
  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./sylius/public:/var/www/sylius/public:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root
      - MYSQL_DATABASE=sylius
      - MYSQL_USER=sylius
      - MYSQL_PASSWORD=sylius
    ports:
      - "3306:3306"
    volumes:
      - db_data:/var/lib/mysql
volumes:
  db_data:
```

### Bagisto Docker Compose

```yaml
version: '3.8'
services:
  bagisto:
    image: bagisto/bagisto:latest
    ports:
      - "8080:80"
    environment:
      - APP_URL=http://localhost:8080
      - DB_CONNECTION=mysql
      - DB_HOST=db
      - DB_PORT=3306
      - DB_DATABASE=bagisto
      - DB_USERNAME=bagisto
      - DB_PASSWORD=bagistopass
    volumes:
      - bagisto_storage:/var/www/html/storage
    depends_on:
      - db
  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root
      - MYSQL_DATABASE=bagisto
      - MYSQL_USER=bagisto
      - MYSQL_PASSWORD=bagistopass
    volumes:
      - db_data:/var/lib/mysql
volumes:
  bagisto_storage:
  db_data:
```

### Spree Commerce Docker Compose

```yaml
version: '3.8'
services:
  spree:
    image: spree/spree:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://spree:spree@db:5432/spree
      - RAILS_ENV=production
      - SECRET_KEY_BASE=your-secret-key-base
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=spree
      - POSTGRES_USER=spree
      - POSTGRES_PASSWORD=spree
    volumes:
      - db_data:/var/lib/postgresql/data
volumes:
  db_data:
```

## Why Self-Host Your E-Commerce Platform?

Running your own e-commerce platform gives you control that SaaS solutions simply cannot match:

**Complete Customization**: Every aspect of the shopping experience — from product pages to checkout flow to post-purchase emails — is under your control. With headless platforms like Sylius and Spree, you can build custom storefronts using any frontend technology (React, Vue, Next.js) while the commerce backend handles the complex business logic.

**Transaction Fee Elimination**: Most SaaS e-commerce platforms charge per-transaction fees (typically 1-3% on top of payment processing). On $100,000 in monthly revenue, that's $12,000-$36,000 per year in platform fees alone — money that stays in your business with a self-hosted solution.

**Data Ownership and Analytics**: Your customer data, purchase history, and browsing behavior remain on your servers. You can run any analytics, build custom recommendation engines, and integrate with any marketing tool without API rate limits or data export restrictions.

**Scalability on Your Terms**: As your store grows, you scale your infrastructure — not your per-transaction fees. A $10 million/year store pays the same platform cost as a $100,000/year store when self-hosted.

For securing customer data, see our [SSL/TLS termination proxy guide](../self-hosted-tls-termination-proxy-traefik-caddy-haproxy-guide-2026/). For high-performance product search, check our [search engine comparison](../self-hosted-search-engines-meilisearch-typesense-algolia-alternatives-guide/). For payment processing without platform lock-in, see our [payment gateway guide](../2026-04-29-self-hosted-payment-gateways-hyperswitch-btcpay-server-guide/).

## FAQ

### Which platform is easiest to set up for a small online store?

Bagisto offers the fastest path to a working store. Its Laravel-based admin panel provides a complete store management experience out of the box — you can add products, configure shipping, set up payment gateways, and launch within hours. Sylius and Spree are more developer-oriented and require building or configuring a separate frontend.

### Can these platforms handle B2B e-commerce requirements?

Yes, all three support B2B features, but Sylius excels here. Its component architecture includes dedicated B2B suites with customer groups, corporate account management, quote-to-order workflows, purchase approval chains, and tiered pricing. Spree has B2B extensions, and Bagisto supports customer groups and custom pricing rules.

### How do these compare to Magento or WooCommerce?

WooCommerce is ideal for content-heavy stores where WordPress is already your CMS — it's simpler but less flexible for custom commerce logic. Magento (Adobe Commerce) is the enterprise heavyweight but comes with significant hosting costs and complexity. Sylius and Bagisto offer a middle ground: modern PHP architecture with less overhead than Magento but more commerce-specific features than building from scratch with Laravel or Symfony.

### Is Spree still actively maintained?

Yes. After going through several ownership changes, Spree Commerce is actively maintained with regular releases. The project has embraced a headless architecture with a Next.js storefront reference implementation. The 15,000+ stars and active contributor community indicate continued developer interest, though the pace of development is slower than Bagisto's rapid iteration.

### What about performance at scale?

All three platforms can scale to handle enterprise traffic with proper infrastructure. Sylius has been deployed in stores processing millions of orders. Bagisto's Laravel foundation supports horizontal scaling with load-balanced web servers and dedicated database/cache layers. Spree, as a Rails application, benefits from Ruby's mature ecosystem for scaling via background job processing (Sidekiq) and caching (Redis).

### Can I run a multi-vendor marketplace?

Bagisto has the strongest built-in marketplace support with its multi-vendor extension that allows multiple sellers to list products, manage their own inventory, and receive commission-based payouts. Sylius can achieve marketplace functionality through custom channel configurations and vendor plugins. Spree requires extensions for marketplace functionality but has several mature options available.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PHP E-Commerce Platforms: Sylius vs Bagisto vs Spree Commerce in 2026",
  "description": "Compare leading open-source e-commerce platforms: Sylius (Symfony headless), Bagisto (Laravel full-stack), and Spree Commerce (Rails headless). Includes Docker Compose deployment configs.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
