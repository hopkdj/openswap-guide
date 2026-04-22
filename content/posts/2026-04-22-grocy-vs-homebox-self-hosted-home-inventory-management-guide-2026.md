---
title: "Grocy vs Homebox: Best Self-Hosted Home Inventory Management 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "inventory", "home-management"]
draft: false
description: "Compare Grocy and Homebox for self-hosted home inventory management in 2026. Complete setup guides with Docker Compose, feature comparisons, and recommendations for organizing your household."
---

If you have ever wondered where that spare HDMI cable ended up, how many cans of tomatoes are left in the pantry, or whether the warranty on your laptop is still valid, you already understand the problem that self-hosted home inventory tools solve. This guide compares the two leading open-source solutions — **Grocy** and **Homebox** — and walks you through deploying each with Docker.

## Why Self-Host Your Home Inventory System

Running an inventory or household management system on your own server offers advantages that cloud-based alternatives cannot match:

- **Full data ownership**: Every photo, label, and note stays on your hardware. No third-party analytics, no data mining, no surprise policy changes.
- **No subscription fees**: Both Grocy and Homebox are completely free and open-source. You pay only for the electricity to run your server.
- **Offline access**: Your inventory data is available as long as your local network is up, even during internet outages.
- **Unlimited entries**: No artificial caps on how many items you can track. Catalog your entire home without hitting a paywall.
- **Custom integrations**: Connect to Home Assistant, notification services, or custom scripts through REST APIs.

For related reading on self-hosted personal finance, see our [personal finance management guide](../actual-budget-vs-firefly-iii-vs-beancount-self-hosted-personal-finance-2026/) and for meal planning, check our [recipe manager comparison](../tandoor-vs-mealie-self-hosted-recipe-manager/).

## Quick Comparison Table

| Feature | Grocy | Homebox |
|---------|-------|---------|
| **Primary Focus** | Groceries, chores, household management | Physical asset inventory |
| **Language** | JavaScript / PHP | Go |
| **Database** | SQLite | SQLite |
| **GitHub Stars** | 8,973 | 5,811 |
| **Latest Release** | v4.6.0 | v0.25.0 |
| **Docker Image** | `linuxserver/grocy` | `ghcr.io/sysadminsmedia/homebox:latest` |
| **Barcode Scanning** | Yes (built-in) | No |
| **Multi-User Support** | Yes (role-based) | Yes (family sharing) |
| **REST API** | Yes | Yes |
| **Chore Tracking** | Yes | No |
| **Battery Management** | Yes | No |
| **Meal Planning** | Yes | No |
| **Shopping Lists** | Yes | No |
| **Asset Locations** | Yes (via custom fields) | Yes (native, hierarchical) |
| **Label System** | Yes | Yes |
| **Warranty Tracking** | Via custom fields | Yes (native) |
| **Mobile Responsive** | Yes | Yes |
| **Resource Usage** | Moderate (PHP runtime) | Low (single Go binary) |

## Grocy — ERP Beyond Your Fridge

[Grocy](https://grocy.info/) bills itself as "ERP beyond your fridge" and takes that seriously. It is the most feature-rich self-hosted home management platform available, covering groceries, household chores, battery tracking, and meal planning in a single application.

The project was created by Bernd Bestel and has grown to nearly **9,000 stars** on GitHub. It is written in PHP with a JavaScript frontend and uses SQLite for storage. The latest version (v4.6.0) was released in early 2026, and the project sees multiple commits per week.

### Key Features

- **Stock management**: Track products with quantity, location, and expiration dates. Barcode scanning makes adding items painless.
- **Shopping lists**: Automatically generated from recipes, manually added, or triggered when stock falls below a minimum threshold.
- **Recipes and meal planning**: Build a recipe database with nutritional information. Plan meals for the week and generate shopping lists automatically.
- **Chore tracking**: Schedule and log household chores (cleaning, maintenance, laundry) with recurring intervals.
- **Battery management**: Track rechargeable batteries, their charge cycles, and replacement schedules.
- **Tasks**: General-purpose todo lists with categories and due dates.
- **Stock overview**: See what you have, what is expiring soon, and what needs to be reordered at a glance.

### Docker Compose Deployment

The easiest way to run Grocy is via the LinuxServer.io Docker image, which packages the application with all dependencies:

```yaml
services:
  grocy:
    image: lscr.io/linuxserver/grocy:latest
    container_name: grocy
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - ./grocy-config:/config
    ports:
      - 9283:80
    restart: unless-stopped
```

Save this as `docker-compose.yml` and run:

```bash
docker compose up -d
```

Grocy will be available at `http://<your-server-ip>:9283`. The default login requires setting an API key in the configuration. Create a `grocy.env` file in your config directory:

```bash
# grocy.env
GROCY_API_KEY=your-secret-api-key-here
GROCY_CULTURE=en
```

After the initial setup, access the web interface and navigate to **Manage data** to start adding products, locations, and recipes. The first-run wizard walks you through defining your storage locations (pantry, fridge, freezer, etc.) and product groups.

### Grocy Strengths

Grocy shines when you need a **complete household management system**. The barcode scanning feature is particularly useful — point your phone camera at a product barcode, and Grocy fetches product information from its built-in database. The chore and battery tracking features have no real competitor in the open-source space.

### Grocy Weaknesses

The PHP stack is heavier than Homebox's Go binary, consuming more RAM (roughly 150-250 MB idle vs. 20-40 MB for Homebox). The interface, while functional, is dense — the sidebar alone has 12 top-level navigation items. If you only need to track physical items, Grocy offers far more features than necessary.

## Homebox — Inventory Built for the Home User

[Homebox](https://homebox.software/) is a focused inventory management system designed specifically for home users. Originally created by hay-kot, it is now actively maintained by the **Sysadmins Media** community fork with over 5,800 GitHub stars. Written in Go with a Vue.js frontend, it ships as a single binary with minimal resource requirements.

The original hay-kot/homebox repository was archived in June 2024. The active continuation at sysadminsmedia/homebox receives regular updates — the latest release (v0.25.0) shipped in April 2026 with improved labeling, custom field support, and a refreshed UI.

### Key Features

- **Item cataloging**: Add items with photos, serial numbers, purchase prices, and detailed descriptions.
- **Hierarchical locations**: Organize items by room, shelf, drawer, or any custom hierarchy you define.
- **Labels and tags**: Categorize items with a flexible labeling system. Create labels like "Electronics," "Tools," "Warranty," or "Fragile."
- **Warranty and maintenance tracking**: Native support for warranty expiration dates, purchase receipts, and maintenance logs.
- **Asset QR codes**: Generate and print QR codes for each item. Scan them to quickly look up details.
- **Import/Export**: CSV import and export for bulk operations and backups.
- **Search**: Fast full-text search across all item fields.
- **Multi-user families**: Share your inventory with family members through built-in user management.

### Docker Compose Deployment

Homebox is even simpler to deploy than Grocy. Here is a production-ready Docker Compose configuration:

```yaml
services:
  homebox:
    image: ghcr.io/sysadminsmedia/homebox:latest
    container_name: homebox
    environment:
      - HBOX_LOG_LEVEL=info
      - HBOX_LOG_FORMAT=text
      - HBOX_WEB_MAX_UPLOAD_SIZE=50
    volumes:
      - ./homebox-data:/data
    ports:
      - 7745:7745
    restart: unless-stopped
```

Deploy with:

```bash
docker compose up -d
```

Homebox starts immediately on `http://<your-server-ip>:7745`. The first visit prompts you to create an admin account. There is no separate configuration file needed — all settings are managed through the web interface.

### Securing with a Reverse Proxy

For either tool, placing a reverse proxy in front provides HTTPS and centralizes authentication. Here is an example for Homebox with Caddy:

```yaml
services:
  homebox:
    image: ghcr.io/sysadminsmedia/homebox:latest
    container_name: homebox
    volumes:
      - ./homebox-data:/data
    restart: unless-stopped
    networks:
      - proxy

  caddy:
    image: caddy:2
    container_name: caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - proxy
    restart: unless-stopped

networks:
  proxy:
    external: true

volumes:
  caddy-data:
  caddy-config:
```

With this `Caddyfile`:

```
homebox.example.com {
    reverse_proxy homebox:7745
}
```

### Homebox Strengths

Homebox excels at **physical inventory management**. If your goal is to catalog everything you own — tools, electronics, furniture, collectibles — Homebox provides a cleaner, more focused experience than Grocy. The hierarchical location system is intuitive, and the Go backend is lightweight enough to run on a Raspberry Pi Zero alongside other services.

The QR code generation feature is particularly practical: print labels for storage bins, scan them with your phone, and instantly see the contents without opening the box.

### Homebox Weaknesses

Homebox does not handle groceries, meal planning, chores, or batteries. It is purely an inventory tool. If you want a single application to manage your entire household, Homebox will need to be paired with other tools (like Mealie for recipes or a separate chore tracker).

## Which Should You Choose?

The decision comes down to **scope**:

| Scenario | Recommendation |
|----------|---------------|
| Track groceries, plan meals, manage chores | **Grocy** — no other tool covers all three |
| Catalog physical possessions (tools, electronics, furniture) | **Homebox** — cleaner, more focused |
| Run both groceries and physical inventory | **Grocy + Homebox** side by side — they complement each other |
| Minimal resource usage (Raspberry Pi, low-power server) | **Homebox** — single Go binary, ~20 MB RAM |
| Barcode-driven inventory (retail-style tracking) | **Grocy** — built-in barcode scanning |
| Warranty and receipt management | **Homebox** — native support with photo attachments |
| Family sharing with multiple users | **Both support multi-user**, but Homebox has simpler family setup |

### Using Both Together

There is no conflict in running both applications. They serve different purposes:

- **Grocy** handles consumables (food, cleaning supplies, batteries) and recurring tasks.
- **Homebox** handles durable goods (electronics, tools, furniture, collectibles).

A typical self-hosted household setup might look like this:

```
┌──────────────────────────────────────────────┐
│              Your Home Server                │
├─────────────────┬────────────────────────────┤
│     Grocy       │        Homebox             │
│  :9283          │        :7745               │
├─────────────────┼────────────────────────────┤
│ • Groceries     │ • Electronics              │
│ • Recipes       │ • Tools                    │
│ • Chores        │ • Furniture                │
│ • Batteries     │ • Collectibles             │
│ • Shopping Lists│ • Warranty Documents       │
└─────────────────┴────────────────────────────┘
```

Both can sit behind the same reverse proxy with different subdomains or path-based routing.

For readers interested in broader IT asset management approaches, our [Snipe-IT vs InvenTree comparison](../snipe-it-vs-inventree-vs-partkeepr-self-hosted-inventory-guide-2026/) covers enterprise-grade inventory tools that can also be adapted for home use.

## FAQ

### Can Grocy and Homebox share the same database?

No. Grocy and Homebox use separate SQLite databases with completely different schemas. They are independent applications that can run side by side on the same server. If you want a unified view, you would need to build a custom dashboard that queries both APIs.

### Is Homebox actively maintained?

Yes. The original `hay-kot/homebox` repository was archived in June 2024, but the project continues under the `sysadminsmedia/homebox` fork, which receives regular updates. As of April 2026, the fork has over 5,800 stars and the latest release is v0.25.0.

### Does Grocy work without a barcode scanner?

Absolutely. While Grocy supports barcode scanning for quick product lookup, you can add products entirely manually through the web interface. The barcode feature is an enhancement, not a requirement. Many users manage their entire inventory without ever scanning a barcode.

### Can I access Homebox or Grocy from my phone?

Both applications are mobile-responsive and work well on smartphone browsers. Grocy also has an official Android companion app (`patzly/grocy-android` with over 1,100 stars on GitHub) that provides a native experience for shopping lists and stock checking on the go.

### How do I back up my Grocy or Homebox data?

Both tools store data in SQLite database files within their respective volumes. To back up, simply copy the database file:

```bash
# Grocy backup
docker exec grocy sqlite3 /config/data/grocy.db ".backup '/config/data/grocy-backup.db'"
cp ./grocy-config/data/grocy.db /backup/grocy-$(date +%F).db

# Homebox backup
cp ./homebox-data/homebox.db /backup/homebox-$(date +%F).db
```

Schedule this as a daily cron job and copy backups to a separate storage location.

### Can I import an existing spreadsheet into either tool?

Homebox supports CSV import natively — navigate to the Import section in settings and upload your file with columns for name, description, location, and labels. Grocy does not have a built-in CSV importer, but its REST API allows programmatic bulk import via scripts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Grocy vs Homebox: Best Self-Hosted Home Inventory Management 2026",
  "description": "Compare Grocy and Homebox for self-hosted home inventory management in 2026. Complete setup guides with Docker Compose, feature comparisons, and recommendations for organizing your household.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
