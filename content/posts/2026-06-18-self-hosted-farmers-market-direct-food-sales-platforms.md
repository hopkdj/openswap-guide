---
title: "Self-Hosted Farmers Market & Direct Food Sales Platforms: Local Food Nodes vs Open Food Network vs FoodHub"
date: "2026-06-18"
tags: ["farmers-market", "direct-sales", "local-food", "self-hosted", "csa", "food-hub"]
draft: false
---

## Introduction

Farmers markets and direct-to-consumer food sales have exploded in popularity as consumers seek fresh, local produce and want to support regional agriculture. Managing a farmers market — coordinating vendors, processing orders, handling payments, and organizing pickup logistics — requires specialized software. While platforms like Farmigo and Harvie offer managed solutions, self-hosted open-source alternatives give market organizers full control and eliminate recurring platform fees.

This article compares three approaches to self-hosting farmers market and direct food sales infrastructure: **Open Food Network's farmers market mode**, **Local Food Nodes** (a community-driven marketplace), and a **custom FoodHub stack** built from open-source components.

## Comparison Table

| Feature | Open Food Network (Market Mode) | Local Food Nodes | Custom FoodHub Stack |
|---------|-------------------------------|------------------|---------------------|
| **Architecture** | Ruby on Rails monolith | Node.js + MongoDB | Modular (WordPress + plugins) |
| **Primary Use Case** | Multi-vendor farmers markets | Community food marketplaces | Small-scale direct sales |
| **Stars (GitHub)** | 1,200+⭐ | 480+⭐ | N/A (composable) |
| **Vendor Management** | ✅ Enterprise profiles | ✅ Storefronts per vendor | ✅ Via WooCommerce |
| **Order Cycles** | ✅ Flexible scheduling | ✅ Real-time ordering | ✅ Manual cycles |
| **Payment Processing** | ✅ Stripe, PayPal | ✅ Stripe, bank transfer | ✅ WooCommerce gateways |
| **Pickup Logistics** | ✅ Hub locations | ✅ Map integration | ✅ Shipping plugins |
| **Inventory Tracking** | ✅ Per-vendor stock | ✅ Real-time inventory | ✅ Stock management |
| **Customer Accounts** | ✅ Full profiles | ✅ Social login | ✅ WordPress accounts |
| **Multi-Market** | ✅ Separate instances | ✅ Multi-community | ✅ Multi-site |
| **Docker Support** | ✅ Official Compose | ✅ Community images | ✅ Standard WP Docker |
| **Mobile Experience** | ✅ Responsive web | ✅ PWA support | ✅ Theme-dependent |
| **Multi-Language** | ✅ 15+ languages | ✅ 🇸🇪🇬🇧 primary | ✅ Plugin-based |
| **Tax Handling** | ✅ Configurable | ✅ Swedish tax system | ✅ WooCommerce tax |

## Open Food Network: The Full-Featured Marketplace

[Open Food Network](https://github.com/openfoodfoundation/openfoodnetwork) in "farmers market mode" is the most mature option for running a multi-vendor farmers market online. Each farmer gets their own enterprise profile with product listings, while market organizers manage order cycles and coordinate distribution.

### Key Features

- **Multi-Enterprise Model**: Each vendor (farm, bakery, rancher) has an independent profile with their own products, pricing, and availability. The market administrator controls which enterprises appear in each order cycle.
- **Flexible Order Cycles**: Run weekly markets, bi-weekly, or one-time special events. Customers see only products available in the current cycle.
- **Hub Logistics**: Designate pickup locations (the market itself, satellite pickup points) and allow customers to choose their preferred pickup during checkout.
- **Transparency**: Every product shows its producer — customers can click through to learn about the farm, their practices, and see a map of their location.

### Docker Compose for Farmers Market

```yaml
version: "3.8"
services:
  ofn:
    image: openfoodfoundation/openfoodnetwork:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgres://ofn:password@db/ofn
      REDIS_URL: redis://redis:6379/0
      RAILS_ENV: production
      SECRET_KEY_BASE: generate-a-long-random-string
      OFN_URL: https://market.yourdomain.com
      MAIL_HOST: smtp.yourmail.com
      MAIL_PORT: "587"
      STRIPE_PUBLISHABLE_KEY: pk_live_xxx
      STRIPE_SECRET_KEY: sk_live_xxx
    depends_on:
      - db
      - redis
    volumes:
      - ofn_uploads:/app/public/uploads
      - ofn_spree:/app/public/spree

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ofn
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ofn
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes

volumes:
  ofn_uploads:
  ofn_spree:
  pgdata:
```

After deployment, configure your market through the admin panel: set up shipping categories for pickup locations, configure payment methods, and invite your first farmers as enterprise users.

## Local Food Nodes: The Community-First Alternative

[Local Food Nodes](https://github.com/localfoodnodes/localfoodnodes) is a Swedish-origin platform designed specifically for community-driven food marketplaces. Built with Node.js and MongoDB, it offers a simpler architecture than OFN and emphasizes local community governance.

### Key Features

- **Community Ownership**: Each "node" is an independent marketplace run by local organizers. The platform is designed for federation — nodes can optionally connect and share products.
- **Producer Storefronts**: Each producer gets a customizable storefront with images, descriptions, and product listings. Customers can follow their favorite producers.
- **Real-Time Ordering**: Unlike OFN's order cycle model, Local Food Nodes supports continuous ordering with real-time inventory updates.
- **Built-in Messaging**: Customers and producers can communicate directly through the platform for custom orders or pickup arrangements.

### Docker Deployment

```yaml
version: "3.8"
services:
  lfn:
    image: localfoodnodes/app:latest
    ports:
      - "8080:8080"
    environment:
      MONGODB_URI: mongodb://mongo:27017/localfoodnodes
      JWT_SECRET: your-jwt-secret
      BASE_URL: https://market.yourdomain.com
      STRIPE_SECRET_KEY: sk_live_xxx
      MAIL_HOST: smtp.example.com
      MAIL_USER: user@example.com
      MAIL_PASS: password
    depends_on:
      - mongo
    volumes:
      - lfn_uploads:/app/uploads

  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db

volumes:
  lfn_uploads:
  mongo_data:
```

## Custom FoodHub Stack: Composable Direct Sales

For small-scale operations — a single farm selling directly to customers or a micro-market with 3-5 vendors — a custom WordPress + WooCommerce stack can be the most practical solution. This approach trades specialized food marketplace features for flexibility and a massive plugin ecosystem.

### Building Your Stack

```yaml
version: "3.8"
services:
  wordpress:
    image: wordpress:6-php8.2-apache
    ports:
      - "8080:80"
    environment:
      WORDPRESS_DB_HOST: db
      WORDPRESS_DB_USER: wordpress
      WORDPRESS_DB_PASSWORD: password
      WORDPRESS_DB_NAME: wordpress
    volumes:
      - wp_content:/var/www/html/wp-content

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_USER: wordpress
      MYSQL_PASSWORD: password
      MYSQL_DATABASE: wordpress
    volumes:
      - wp_db:/var/lib/mysql

volumes:
  wp_content:
  wp_db:
```

Once WordPress is running, install these plugins to create your food marketplace:

- **WooCommerce**: The core e-commerce engine for product listings, cart, and checkout
- **WooCommerce Product Vendors** or **Dokan**: Multi-vendor marketplace functionality, allowing each farmer to manage their own products
- **WooCommerce Local Pickup**: Configure pickup locations and time slots
- **WooCommerce Subscriptions**: For CSA (Community Supported Agriculture) weekly box subscriptions
- **WooCommerce Product Add-ons**: For customizing orders (e.g., "add a dozen eggs" or "substitute kale for spinach")

## Use Case Matching

### For Multi-Vendor Farmers Markets (20+ vendors)

**Use Open Food Network.** Its enterprise model and order cycle system are purpose-built for coordinating many producers through a central hub. The platform handles the complexity of per-vendor inventory, flexible pickup scheduling, and transparent supply chain information that customers at farmers markets expect.

### For Community Food Cooperatives

**Use Local Food Nodes.** Its community-governance model and simpler tech stack (Node.js + MongoDB vs Ruby on Rails + PostgreSQL + Redis) make it more accessible for volunteer-run organizations. The Swedish roots mean excellent documentation for cooperative structures.

### For Single-Farm Direct Sales or Micro-Markets

**Use the Custom WooCommerce Stack.** When you have 1-5 vendors and want maximum flexibility without learning a specialized platform, WordPress + WooCommerce gives you thousands of themes, plugins, and community resources. The trade-off is that you'll need to manually manage some food-specific workflows (order cycles, pickup logistics) that OFN handles automatically.

## Why Self-Host Your Farmers Market Platform?

Farmers markets operate on thin margins — typically 5-10% of gross sales go to market administration. Paying a SaaS platform 3-5% of transaction volume plus a monthly fee can consume half of that margin. Self-hosting eliminates platform fees entirely; your only ongoing costs are server hosting (15-30/month for a reliable VPS) and payment processing (typically 1.5-2.9% + 0.30 per transaction through Stripe).

Beyond cost savings, self-hosting preserves the community-focused ethos of farmers markets. Your market's data — customer preferences, vendor sales history, product seasonality — stays within the community rather than being monetized by a third-party platform. If your market's needs change, you can modify the software or hire a developer to add custom features.

For broader farm management, see our [farm management systems guide](../2026-04-29-farmos-vs-ekylibre-open-source-farm-management-systems-guide-2026/) comparing FarmOS and Ekylibre. For food cooperative ordering without the marketplace features, check our [food cooperative platforms guide](../2026-06-18-self-hosted-food-cooperative-management-foodsoft-ofn/).

## FAQ

### What's the difference between a farmers market platform and a CSA management tool?

A farmers market platform coordinates multiple vendors selling individual products to customers who browse and choose. A CSA (Community Supported Agriculture) tool typically manages subscription boxes — customers pay upfront for a season of weekly produce boxes, and the farm decides what goes in each box. OFN handles farmers markets well; WooCommerce Subscriptions works for CSA models. Some farms use both: OFN for market sales and a separate CSA system.

### How do I handle SNAP/EBT payments at my farmers market?

SNAP/EBT processing requires specialized hardware and certification. None of the open-source platforms natively process SNAP — you'll typically use a separate SNAP terminal (like those from FIS or Conduent) alongside the online platform. Some markets process SNAP at a central tent and issue wooden tokens that vendors accept, then the platform tracks only the non-SNAP portion.

### Can customers pre-order for pickup at specific times?

Yes, all three platforms support scheduled pickup. OFN's order cycle model is especially good for this — you set an ordering window (e.g., Monday-Thursday) and pickup windows (e.g., Saturday 9am-1pm). WooCommerce with the Local Pickup plugin can restrict pickup time slots. Local Food Nodes uses a continuous model but can be configured with delivery windows.

### What about integration with local delivery services?

OFN has an API that can integrate with delivery logistics platforms. The WooCommerce stack has plugins for delivery services like Shippo and ShipStation. For local bicycle delivery co-ops or volunteer delivery networks, custom API integration is usually needed — the open-source nature of these platforms makes this feasible with modest development effort.

### How do I handle product seasonality — when certain items are only available part of the year?

OFN handles seasonality through order cycles — you only make products available in cycles when they're in season. In the WooCommerce stack, you can use product visibility scheduling or simply toggle product status. Local Food Nodes supports marking products as "seasonal" with availability dates.

### Is there a self-hosted alternative to Farmigo for full-featured CSA management?

While no exact open-source Farmigo clone exists, you can combine tools: OFN or WooCommerce for ordering/sales, a spreadsheet or Airtable for box planning, and Mailchimp's free tier for member communications. For farms running 100+ CSA shares, the custom WooCommerce stack with Subscriptions and Product Add-ons provides the closest experience — though setup time is 10-20 hours versus Farmigo's managed onboarding.

### How do these platforms handle weight-based pricing (per-pound items)?

WooCommerce supports weight-based pricing natively with the "Measurement Price Calculator" extension. OFN supports variant pricing where you can set price per unit (kg, lb, bunch). Local Food Nodes has basic weight support. For farmers markets where many items are sold by weight, WooCommerce offers the most flexible pricing options.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Farmers Market & Direct Food Sales Platforms: Local Food Nodes vs Open Food Network vs FoodHub",
  "description": "Compare self-hosted farmers market and direct food sales platforms including Open Food Network, Local Food Nodes, and custom FoodHub stacks. Docker deployment and multi-vendor marketplace setup.",
  "datePublished": "2026-06-18",
  "dateModified": "2026-06-18",
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
