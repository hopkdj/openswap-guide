---
title: "Self-Hosted Digital Menu & QR Ordering Systems for Restaurants 2026"
date: "2026-06-19"
tags: ["restaurant", "digital-menu", "qr-code", "self-hosted", "food-service", "hospitality"]
draft: false
---

## Why Self-Host Your Restaurant's Digital Menu?

The restaurant industry has undergone a massive digital transformation. QR code menus, online ordering, and contactless payments are no longer optional — they're expected by customers. But relying on SaaS platforms means paying monthly subscription fees, surrendering customer data to third parties, and risking service outages during peak hours.

Self-hosting your digital menu and ordering system puts you back in control. You own your customer data, eliminate recurring SaaS costs, and can customize the experience to match your brand. Plus, with modern open-source tools, you can deploy a production-ready system on a $5/month VPS that handles hundreds of orders per day.

In this guide, we compare the most practical open-source solutions for self-hosting restaurant digital menus and QR ordering: **Restaurant Menu Manager**, **Gastrofy**, and building a custom solution with **Directus** or **Strapi** as a headless CMS backend.

## Comparison Table

| Feature | Restaurant Menu Mgr | Gastrofy | Custom CMS (Directus) |
|---------|-------------------|----------|----------------------|
| **Stars** | 500+ | 300+ | 29,000+ (Directus) |
| **Language** | PHP/Laravel | Python/Django | Node.js/Vue |
| **QR Code Generation** | Built-in | Built-in | Manual / Plugin |
| **Online Ordering** | Yes | Yes | Custom build |
| **Multi-language** | Limited | Full i18n | Built-in (Directus) |
| **Payment Integration** | Stripe | Stripe, PayPal | API-based |
| **Menu Categories** | Yes | Yes | Fully customizable |
| **Docker Support** | Yes | Yes | Official image |
| **Admin Dashboard** | Web UI | Web UI | Full admin panel |
| **Mobile PWA** | Yes | Yes | Build separately |
| **Best For** | Quick setup | Multi-location | Customizability |

## 1. Restaurant Menu Manager: Full-Featured PHP Solution

Restaurant Menu Manager is a PHP/Laravel-based platform that provides everything a restaurant needs: digital menu display, QR code generation for tables, online ordering, and an admin dashboard for managing items, categories, and orders.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  app:
    image: restaurant-menu-manager:latest
    container_name: restaurant-menu
    ports:
      - "8000:80"
    environment:
      - APP_URL=https://menu.yourrestaurant.com
      - DB_CONNECTION=mysql
      - DB_HOST=db
      - DB_DATABASE=restaurant
      - DB_USERNAME=menu_user
      - DB_PASSWORD=secure_password
    volumes:
      - menu_uploads:/var/www/html/storage
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mysql:8.0
    container_name: menu-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=restaurant
      - MYSQL_USER=menu_user
      - MYSQL_PASSWORD=secure_password
    volumes:
      - menu_db:/var/lib/mysql
    restart: unless-stopped

volumes:
  menu_uploads:
  menu_db:
```

### Key Features

The platform automatically generates unique QR codes for each table. When a customer scans the QR code at their table, they're taken to a mobile-optimized menu where they can browse items, customize orders, and submit them directly to the kitchen. The admin dashboard provides real-time order tracking.

For Nginx reverse proxy setup:

```nginx
server {
    listen 443 ssl http2;
    server_name menu.yourrestaurant.com;

    ssl_certificate /etc/letsencrypt/live/menu.yourrestaurant.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/menu.yourrestaurant.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 2. Gastrofy: Python-Powered Multi-Location Solution

Gastrofy is a Python/Django-based restaurant management platform designed for chains and multi-location restaurants. It supports centralized menu management with per-location pricing and availability.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  web:
    image: gastrofy/gastrofy:latest
    container_name: gastrofy-web
    ports:
      - "8001:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=gastrofy.settings.production
      - SECRET_KEY=your-secret-key-here
      - DATABASE_URL=postgres://gastrofy:password@db:5432/gastrofy
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    container_name: gastrofy-db
    environment:
      - POSTGRES_DB=gastrofy
      - POSTGRES_USER=gastrofy
      - POSTGRES_PASSWORD=password
    volumes:
      - gastrofy_db:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: gastrofy-redis
    restart: unless-stopped

volumes:
  gastrofy_db:
```

### Multi-Location Management

Gastrofy's strongest feature is its location management system. You define a master menu with all items, then create per-location variants with different pricing, availability, and tax rates. This is ideal for restaurant chains where the flagship location has different pricing than suburban outlets.

```python
# Example: Define location-specific pricing via the Django admin
# Each Location has a ManyToMany relationship with MenuItem
# through a LocationMenuItem model that stores location_price

class LocationMenuItem(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    location_price = models.DecimalField(max_digits=8, decimal_places=2)
    available = models.BooleanField(default=True)
```

## 3. Build Your Own with Directus: Maximum Flexibility

For restaurants with unique requirements, building a custom digital menu on top of [Directus](https://github.com/directus/directus) (29,000+ stars) gives you complete control. Directus is a headless CMS that wraps your database with a REST and GraphQL API, an admin panel, and granular permissions.

### Directus Docker Compose

```yaml
version: "3.8"
services:
  directus:
    image: directus/directus:latest
    container_name: directus-menu
    ports:
      - "8055:8055"
    environment:
      - KEY=your-random-key
      - SECRET=your-random-secret
      - DB_CLIENT=pg
      - DB_HOST=db
      - DB_PORT=5432
      - DB_DATABASE=directus
      - DB_USER=directus
      - DB_PASSWORD=password
      - ADMIN_EMAIL=admin@yourrestaurant.com
      - ADMIN_PASSWORD=secure_admin_password
    volumes:
      - directus_uploads:/directus/uploads
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=directus
      - POSTGRES_USER=directus
      - POSTGRES_PASSWORD=password
    volumes:
      - directus_db:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  directus_uploads:
  directus_db:
```

### Building Your Menu API

Once Directus is running, you create collections for Menu Categories, Menu Items (with fields for name, description, price, image, dietary labels), and Orders. Directus automatically generates REST and GraphQL APIs:

```javascript
// Fetch menu from your custom Directus API
const response = await fetch('https://menu.yourrestaurant.com/items/menu_items?filter[category][_eq]=starters');
const starters = await response.json();

// Render items in your frontend
starters.data.forEach(item => {
    renderMenuItem(item.name, item.description, item.price, item.image);
});
```

You can build your frontend with any framework (React, Vue, Svelte) and deploy it as a static site or PWA. This approach requires more initial work but gives you unlimited flexibility.

## Deployment Architecture for Restaurants

A typical self-hosted restaurant menu deployment looks like this:

```
Internet → Cloudflare (CDN + DDoS) → Nginx Reverse Proxy
  ├── menu.yourrestaurant.com → Digital Menu App (port 8000)
  ├── admin.yourrestaurant.com → Admin Panel (port 8055 or 8001)
  └── api.yourrestaurant.com → API Backend
       ├── PostgreSQL (menu data)
       ├── Redis (session cache)
       └── S3-compatible storage (menu images)
```

For high availability during peak hours (Friday/Saturday dinner), deploy on a VPS with at least 2GB RAM and enable Cloudflare caching for static menu assets. The menu itself can be cached aggressively — it changes infrequently — while orders require real-time processing.

For related restaurant technology, see our [self-hosted restaurant POS comparison](../2026-06-18-self-hosted-restaurant-pos-ospos-floreant-unicenta/). If you're running a food cooperative or community food project, check our [food coop platform guide](../2026-06-05-self-hosted-food-coop-platforms-openfoodnetwork-foodcoopshop-guide/). For customer retention, see our [gift card and loyalty systems guide](../2026-06-04-gift-card-loyalty-systems-voucherify-open-loyalty-guide/).

## Hardware Requirements and Cost Analysis

One of the strongest arguments for self-hosting your restaurant's digital menu is cost. Let us break down the numbers. A typical SaaS digital menu platform charges $30-100 per month per location, plus transaction fees of 1.5-3% on orders. For a restaurant processing $20,000 in monthly orders, that is $300-600 in platform fees alone.

Self-hosting on a $6/month Hetzner CX22 VPS (2 vCPU, 4GB RAM, 40GB SSD) comfortably runs all three solutions we compared. Add $12/year for a domain name, and your total annual infrastructure cost is under $85. Even with an hour of monthly maintenance, the savings are substantial — $3,500+ per year for a single location.

Hardware requirements are modest. A Raspberry Pi 4 (4GB) can run Restaurant Menu Manager or a Directus-based setup for a small restaurant handling under 100 orders per day. For multi-location chains, we recommend a VPS with at least 2GB RAM per 5 locations. Database storage grows slowly — menu items, categories, and order records for a busy restaurant typically consume under 500MB per year.

For redundancy, deploy two instances behind a load balancer. During peak dinner hours (6-9 PM Friday and Saturday), a single instance handles the load, but having a hot standby ensures zero downtime if the primary node fails. Use Docker Swarm or a simple Nginx upstream configuration to manage failover.


## FAQ

### Do I need internet at my restaurant for a self-hosted digital menu?

You need internet for customers to access the menu via QR codes, but you can run the server on your local network if internet is unreliable. Use a local server (Raspberry Pi or mini PC) and have customers connect to your WiFi to access the menu. Many restaurants use this approach in areas with spotty connectivity.

### How do customers pay through a self-hosted ordering system?

Most self-hosted systems integrate with payment processors like Stripe or PayPal. The payment happens on the customer's device through the payment processor's secure iframe or redirect — your server never handles raw credit card data. For in-person payments, integrate with a POS system that supports card terminals.

### Can I print QR codes for my tables?

Yes. Most digital menu platforms generate QR codes automatically for each table. You can print them on sticker paper or order professional table stands with embedded QR codes. Each QR code encodes the URL with a table identifier (e.g., `https://menu.yourrestaurant.com/table/12`), so orders are automatically associated with the correct table.

### What if I want to update my menu during service?

All three solutions support real-time menu updates. Changes made in the admin panel are reflected immediately on the customer-facing menu. This is a key advantage over printed menus — you can mark items as "sold out" or adjust prices instantly without reprinting anything.

### Is a self-hosted system PCI compliant?

The system itself doesn't handle payment data if you use Stripe or PayPal's hosted checkout. Since card data never touches your server, PCI compliance requirements are minimal (SAQ A). However, you must ensure your server is properly secured (HTTPS, firewalls, regular updates) to protect customer data like names and order history.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Digital Menu & QR Ordering Systems for Restaurants 2026",
  "description": "Compare self-hosted solutions for restaurant digital menus and QR code ordering: Restaurant Menu Manager, Gastrofy multi-location platform, and custom builds with Directus headless CMS. Includes Docker Compose configurations and deployment architecture.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
