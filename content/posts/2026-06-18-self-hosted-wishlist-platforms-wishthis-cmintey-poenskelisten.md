---
title: "Self-Hosted Wishlist & Gift Registry Platforms: wishthis vs cmintey/wishlist vs Poenskelisten"
date: "2026-06-18"
tags: ["self-hosted", "wishlist", "gift-registry", "open-source", "personal-tools", "family-tools", "web-application", "php", "docker"]
draft: false
---

## Why Self-Host a Wishlist Platform?

Sharing gift wishlists with family and friends is a universal need, but most people rely on commercial platforms like Amazon Wish Lists — which track your browsing habits, restrict you to products sold on their marketplace, and hold your data hostage. Self-hosted wishlist platforms offer a private, flexible alternative where you control your data and can list items from any store, website, or even non-commercial desires.

The privacy argument is compelling. Commercial wishlist services build detailed profiles of your shopping preferences, income brackets, and relationships. When you add items to an Amazon wishlist, that data feeds their recommendation engine and advertising algorithms. A self-hosted wishlist keeps this personal information completely private — only the people you explicitly share your list with can see what you're wishing for.

Flexibility is another major advantage. Self-hosted wishlists let you add items from any retailer, custom handmade gifts, experiences (like concert tickets or cooking classes), or even charitable donations. You're not locked into a single marketplace's catalog. For families spread across different countries, this means each person can shop where it makes the most sense for them, not where the wishlist platform dictates.

Beyond individual use, self-hosted wishlists shine for group gifting scenarios — office Secret Santa exchanges, family holiday planning, wedding registries, and baby showers. You can create multiple lists for different occasions, set group gifting pools where multiple people contribute toward expensive items, and manage everything from one place without sharing data with third parties.

For broader gift management, check our [gift card and loyalty systems guide](../2026-06-04-gift-card-loyalty-systems-voucherify-open-loyalty-guide/).

## Feature Comparison

| Feature | wishthis | cmintey/wishlist | Poenskelisten |
|---------|----------|------------------|---------------|
| **GitHub Stars** | 305+ | 569+ | 192+ |
| **Language** | PHP | TypeScript (Next.js) | Python (Flask) |
| **Database** | MySQL/MariaDB | PostgreSQL | SQLite (default) |
| **Docker Support** | Yes | Yes | Yes |
| **Multiple Lists** | Yes | Yes | Yes |
| **Group Gifting** | No | No | Yes (reservation system) |
| **Item Reservations** | No | No | Yes |
| **External URLs** | Yes | Yes | Yes |
| **Custom Text Items** | Yes | Yes | Yes |
| **Password-Protected Lists** | Yes | Via invite system | Via link sharing |
| **Image Uploads** | Via URL only | Yes | Yes |
| **Public/Private Lists** | Yes | Yes | Yes |
| **REST API** | No | Yes (GraphQL) | Limited |
| **Admin Panel** | Yes | No | Yes (Flask-Admin) |
| **Authentication** | Built-in user accounts | NextAuth.js (GitHub, Google, Email) | Simple link-based with optional admin |

## Installation & Deployment

### wishthis Docker Setup

wishthis is a clean PHP-based platform that's easy to deploy:

```yaml
version: "3.8"

services:
  db:
    image: mariadb:10.11
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MARIADB_DATABASE: wishthis
      MARIADB_USER: wishthis
      MARIADB_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql

  wishthis:
    image: ghcr.io/wishthis/wishthis:latest
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      WISHTHIS_DB_HOST: db
      WISHTHIS_DB_NAME: wishthis
      WISHTHIS_DB_USER: wishthis
      WISHTHIS_DB_PASSWORD: ${DB_PASSWORD}
      WISHTHIS_SITE_URL: https://wishes.example.com
      WISHTHIS_TIMEZONE: America/New_York
    volumes:
      - wishthis_data:/var/www/html/upload
    depends_on:
      - db

volumes:
  db_data:
  wishthis_data:
```

### cmintey/wishlist with Docker

This Next.js-based wishlist offers a modern, responsive interface:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: wishlist
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: wishlist
    volumes:
      - pg_data:/var/lib/postgresql/data

  wishlist:
    image: ghcr.io/cmintey/wishlist:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://wishlist:${DB_PASSWORD}@postgres:5432/wishlist
      NEXTAUTH_URL: https://wishes.example.com
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
    depends_on:
      - postgres

volumes:
  pg_data:
```

### Poenskelisten with Docker

Poenskelisten uses Python Flask with a lightweight SQLite backend, making it perfect for Raspberry Pi:

```yaml
version: "3.8"

services:
  poenskelisten:
    image: ghcr.io/aunefyren/poenskelisten:latest
    restart: unless-stopped
    ports:
      - "8080:5000"
    environment:
      SECRET_KEY: ${SECRET_KEY}
      ADMIN_USERNAME: admin
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      TIMEZONE: Europe/Oslo
    volumes:
      - wishlist_data:/app/instance
      - wishlist_uploads:/app/static/uploads

volumes:
  wishlist_data:
  wishlist_uploads:
```

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name wishes.example.com;

    ssl_certificate /etc/letsencrypt/live/wishes.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wishes.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 10M;
    }
}
```

## Choosing the Right Wishlist Platform

**Choose wishthis** if you want a battle-tested, PHP-based solution with standard LAMP stack deployment. It has the simplest setup — just a web server, PHP, and MySQL — no Node.js or Python runtime required. The user interface is clean and intuitive, with drag-and-drop reordering and a responsive mobile design. Its administrative panel provides user management, system statistics, and configuration options.

**Choose cmintey/wishlist** if you prefer a modern JavaScript stack with OAuth authentication. Its Next.js frontend offers excellent performance with server-side rendering, and NextAuth.js integration lets users sign in with their existing GitHub or Google accounts — no separate registration needed. The GraphQL API makes it extensible for custom integrations. It's the best choice if you're already comfortable with Node.js/Next.js deployments.

**Choose Poenskelisten** if you want the simplest possible deployment. Using SQLite by default means no separate database container to manage. The Flask backend is lightweight and runs well on resource-constrained hardware like a Raspberry Pi. Its unique reservation system allows multiple people to claim items from a list without revealing who has purchased what — perfect for Secret Santa exchanges and group gift coordination.

## Security Considerations

All three platforms handle personal data, so secure deployment is critical. Always deploy behind HTTPS with valid TLS certificates from Let's Encrypt. For wishthis and cmintey/wishlist with user accounts, use strong password policies and consider rate limiting login attempts. Poenskelisten's link-based sharing means anyone with the link can view the list — use random, unguessable URLs and consider HTTP basic auth as an additional layer.

Regular backups of the database are essential — losing wishlist data means losing gift plans for multiple people. All three platforms store data in their respective databases, so standard database backup procedures apply. For Docker deployments, mount database volumes to persistent storage and include them in your backup rotation.

## FAQ

### Can I add items from any online store?

Yes. All three platforms support adding items with a title, description, and external URL. You can link to products on Amazon, Etsy, local retailers, or any website. For items without URLs (like "a handmade scarf" or "donation to charity"), you can enter custom text descriptions. cmintey/wishlist and Poenskelisten also support image uploads, so you can add photos of non-online items.

### Is there a way to prevent someone from seeing what others have reserved?

Poenskelisten is the best option for this — its reservation system hides who has claimed each item from other list viewers. This is ideal for surprise gifts and Secret Santa exchanges. wishthis and cmintey/wishlist show wishlists as-is without reservation privacy. For those, you can use separate lists per person as a workaround.

### How do I share my wishlist with family who aren't technical?

All three platforms provide simple sharing via URL. Once deployed at a domain like `wishes.yourdomain.com`, you can share a direct link to your wishlist via email, text, or messaging apps. cmintey/wishlist allows list owners to generate invite links with specific permissions. No apps to install — recipients just open the link in any web browser. For extra convenience, set up a short memorable domain or subdomain.

### Can I host multiple wishlists for different occasions?

Absolutely. All three platforms support creating multiple wishlists per user. You can have separate lists for birthdays, holidays, baby showers, and wedding registries — each with its own URL, items, and sharing settings. wishthis organizes lists under user accounts with easy switching. Poenskelisten creates each list with its own unique sharing link.

### How do these compare to Amazon Wish Lists?

Amazon Wish Lists limit you to Amazon's catalog, track your browsing for advertising, and require recipients to have Amazon accounts. Self-hosted wishlists let you add items from any source, keep your data private, and allow anyone to view your list without creating accounts. The trade-off is that Amazon handles fulfillment logistics natively — with self-hosted wishlists, the gift-giver purchases items manually from the linked stores. For most users, the privacy and flexibility benefits outweigh this minor inconvenience.

### Are there mobile-friendly interfaces?

Yes. All three platforms feature responsive designs that work well on mobile browsers. wishthis has a mobile-optimized layout with touch-friendly controls. cmintey/wishlist, built with Next.js and modern CSS, looks and feels like a native app on mobile. Poenskelisten uses Bootstrap for a clean responsive experience. While none have dedicated mobile apps, the web interfaces are fully functional on phones and tablets.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Wishlist & Gift Registry Platforms: wishthis vs cmintey/wishlist vs Poenskelisten",
  "description": "Complete comparison of open-source self-hosted wishlist and gift registry platforms. Covers wishthis, cmintey/wishlist, and Poenskelisten with Docker Compose deployment guides, feature comparison, and privacy advantages over commercial alternatives.",
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
