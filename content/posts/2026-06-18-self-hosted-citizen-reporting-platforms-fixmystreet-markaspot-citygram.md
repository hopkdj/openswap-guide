---
title: "Self-Hosted Citizen Reporting Platforms: FixMyStreet vs Mark-a-Spot vs CityGram"
date: "2026-06-18"
tags: ["self-hosted", "citizen-engagement", "civic-tech", "open-government", "community-tools", "gis", "municipal-software"]
draft: false
---

## Introduction

Citizen reporting platforms enable residents to report non-emergency issues directly to their local government—potholes, broken streetlights, graffiti, illegal dumping, and other infrastructure problems. These tools transform passive complaint systems into structured, trackable workflows that improve municipal responsiveness and build community trust.

In this guide, we compare three leading open-source citizen reporting platforms: **FixMyStreet** (by mySociety), **Mark-a-Spot** (Drupal-based), and **CityGram** (by Code for America). Each takes a different architectural approach, from the battle-tested Perl monolith to modern headless PWAs on Drupal to lightweight notification systems.

### What Makes a Good Citizen Reporting Platform?

Before diving into the comparison, here are the key features to evaluate:

- **Map-based reporting**: Users can drop a pin on a map to pinpoint the exact location of an issue
- **Category routing**: Reports are automatically categorized and routed to the correct department
- **Status tracking**: Residents can follow their report from submission to resolution
- **Open data integration**: Reports are published as open data for transparency and accountability
- **Multi-tenancy**: Support for multiple jurisdictions within a single deployment
- **Accessibility**: WCAG compliance for inclusive civic participation

## Comparison Table: FixMyStreet vs Mark-a-Spot vs CityGram

| Feature | FixMyStreet | Mark-a-Spot | CityGram |
|---------|------------|-------------|----------|
| **GitHub Stars** | 599 | 70 | 170 |
| **Primary Language** | Perl | TypeScript (Vue.js PWA) | Ruby |
| **Backend Framework** | Catalyst (Perl MVC) | Drupal 11 | Ruby on Rails / Sinatra |
| **Map Engine** | OpenStreetMap / Leaflet | OpenStreetMap / Leaflet | OpenStreetMap |
| **Docker Support** | Official Compose | Official Compose | Limited (Heroku-based) |
| **Multi-tenancy** | Yes (cobrand system) | Limited (Drupal multisite) | No (single city) |
| **Mobile App** | Progressive Web App | Progressive Web App (Vue.js) | Web-based only |
| **Open311 API** | Native (Open311 v2) | Planned / partial | Native |
| **License** | AGPLv3 | GPLv2 | MIT |
| **First Release** | 2010 | 2012 | 2014 |
| **Last Update** | June 2026 | June 2026 | June 2022 |
| **Active Maintainers** | mySociety team (UK) | Community + German civic tech | Inactive / Archived |

## Deep Dive: Each Platform in Detail

### FixMyStreet — The Industry Standard

FixMyStreet is the most mature citizen reporting platform, originally developed by UK-based nonprofit mySociety. It has been deployed in dozens of countries including the UK (fixmystreet.com), Uruguay (Por Mi Barrio), Malaysia (Aduan Rakyat), and Norway (FiksGataMi).

**Key Strengths:**
- **Proven at scale**: Handles millions of reports across multiple countries
- **Internationalization**: Full i18n support with translations for 30+ languages
- **Cobrand architecture**: Run multiple city-branded instances from one codebase
- **Open311 standard**: Fully implements the Open311 GeoReport v2 specification for interoperable civic data

**Deployment with Docker Compose:**

```yaml
# fixmystreet/docker-compose.yml
services:
  nginx:
    image: nginx:1.27.2
    depends_on:
      - fixmystreet
    ports:
      - "8000:80"
    volumes:
      - ./conf/nginx.conf-docker:/etc/nginx/conf.d/default.conf
    networks:
      default:
        aliases:
          - nginx.svc

  fixmystreet:
    image: fixmystreet/fixmystreet:stable
    tty: true
    depends_on:
      postgres:
        condition: service_healthy
      memcached:
        condition: service_started
    cgroup: host
    stop_signal: SIGRTMIN+3
    volumes:
      - ./conf/general.yml-docker:/var/www/fixmystreet/fixmystreet/conf/general.yml
      - fixmystreet_uploads:/var/www/fixmystreet/fixmystreet/web/photo
    environment:
      - DATABASE_URL=postgres://fixmystreet:password@postgres/fixmystreet
    networks:
      default:
        aliases:
          - fixmystreet.svc

  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: fixmystreet
      POSTGRES_PASSWORD: password
      POSTGRES_DB: fixmystreet
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fixmystreet"]
      interval: 5s
      timeout: 5s
      retries: 5
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      default:
        aliases:
          - postgres.svc

  memcached:
    image: memcached:1.6
    networks:
      default:
        aliases:
          - memcached.svc

volumes:
  postgres_data:
  fixmystreet_uploads:
```

FixMyStreet uses PostgreSQL with PostGIS for spatial queries—a critical requirement for map-based reporting. The `fixmystreet/fixmystreet:stable` Docker image is actively maintained and updated with each release.

### Mark-a-Spot — Modern Drupal Power

Mark-a-Spot takes a different approach by building on Drupal 11, one of the most powerful open-source content management systems. The frontend is a modern Vue.js Progressive Web App (PWA), providing a native-like experience on mobile devices.

**Key Strengths:**
- **Drupal ecosystem**: Leverages Drupal's extensive module library for workflows, taxonomy, and user management
- **Vue.js PWA frontend**: Fast, offline-capable mobile experience
- **Flexible configuration**: Drupal's Views, Rules, and Webform modules enable powerful customization without coding
- **German civic tech roots**: Built with European GDPR compliance from the start

**Deployment with Docker Compose:**

```yaml
# mark-a-spot/docker-compose.yml
services:
  web:
    image: nginx:stable-alpine
    container_name: web
    depends_on:
      - markaspot
    networks:
      - drupal
    volumes:
      - ./conf/nginx.conf:/etc/nginx/conf.d/default.conf
      - .:/app/data
    ports:
      - 80:80

  markaspot:
    image: markaspot/markaspot:latest
    container_name: markaspot
    environment:
      VIRTUAL_HOST: 'web'
      PHP_MEMORY_LIMIT: 1G
      XDEBUG_ENABLED: 0
      MARKASPOT_MARIADB_SERVICE_HOST: 'db'
      DRUPAL_DATABASE_PORT: '3306'
      DRUPAL_DATABASE_NAME: 'drupal'
      DRUPAL_DATABASE_USERNAME: 'drupal'
      DRUPAL_DATABASE_PASSWORD: 'drupal'
    volumes:
      - markaspot_data:/app/data
    networks:
      - drupal

  db:
    image: mariadb:10.11
    container_name: db
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: drupal
      MYSQL_USER: drupal
      MYSQL_PASSWORD: drupal
    volumes:
      - db_data:/var/lib/mysql
    networks:
      - drupal

volumes:
  markaspot_data:
  db_data:

networks:
  drupal:
    driver: bridge
```

The Mark-a-Spot Docker image bundles PHP 8.2, Apache/Nginx, and all required Drupal modules. The setup wizard handles Drupal installation and configuration after the containers start.

### CityGram — Lightweight City Notifications

CityGram, developed by Code for America, takes a fundamentally different approach. Rather than a full reporting workflow, it focuses on **subscription-based notifications**—residents subscribe to topics (e.g., "new building permits in my neighborhood") and receive notifications via SMS, email, or webhook when matching events occur.

**Key Strengths:**
- **Subscription model**: Push-based architecture keeps residents informed without checking a portal
- **Geo-subscriptions**: Subscribe to events within a geographic radius
- **SMS integration**: Uses Twilio for SMS notifications, critical for digital inclusion
- **Simple deployment**: Originally designed for Heroku; straightforward Ruby on Rails app

**Deployment (Manual Setup):**

CityGram doesn't have an official Docker image, but deployment on a Linux server is straightforward:

```bash
# Install dependencies
git clone https://github.com/codeforamerica/citygram.git
cd citygram
bundle install

# Configure environment
cp .env.sample .env
# Edit .env with your DATABASE_URL, Twilio credentials, etc.

# Setup database
bundle exec rake db:create db:migrate

# Start the server
bundle exec rails server -b 0.0.0.0 -p 3000
```

**Note:** CityGram's last update was in June 2022, and the project appears to be in maintenance mode. For new deployments, FixMyStreet or Mark-a-Spot are recommended unless the notification-centric model specifically matches your needs.

## Deployment Architecture

All three platforms share a similar deployment architecture but differ in operational complexity:

```
┌─────────────────────────────────────────────────┐
│                  Reverse Proxy                    │
│              (Nginx / Caddy / Traefik)            │
├──────────┬──────────────────┬────────────────────┤
│ FixMyStreet│   Mark-a-Spot   │     CityGram       │
│ (Perl)     │  (Drupal/PHP)   │   (Ruby/Rails)     │
├──────────┼──────────────────┼────────────────────┤
│ PostgreSQL │    MariaDB       │    PostgreSQL      │
│ + PostGIS  │                  │                    │
├──────────┼──────────────────┼────────────────────┤
│ Memcached  │    Redis (opt)   │    Redis (opt)      │
└──────────┴──────────────────┴────────────────────┘
```

For production deployments, always place these behind a reverse proxy with HTTPS termination:

```nginx
# Example Nginx reverse proxy configuration
server {
    listen 443 ssl http2;
    server_name reports.yourcity.gov;
    
    ssl_certificate /etc/letsencrypt/live/reports.yourcity.gov/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/reports.yourcity.gov/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Why Self-Host Your Citizen Reporting Platform?

Running your own citizen reporting platform gives your municipality complete control over citizen data, bypassing vendor lock-in from commercial SaaS solutions like SeeClickFix or CitizenConnect. Open-source platforms ensure that report data remains publicly accessible, supporting transparency mandates and open government initiatives.

Self-hosting also enables deep customization—integrate with your existing GIS infrastructure, connect to internal work order systems, or add custom report categories that reflect your community's specific needs. The cost savings are substantial: FixMyStreet is used by the UK government for over 400 local authorities at zero licensing cost, compared to commercial alternatives charging $5,000–$50,000 per year.

For broader civic engagement, see our [guide to citizen participation platforms](../2026-06-08-self-hosted-citizen-participation-e-democracy-decidim-consul-polis/). If your municipality also needs open data publishing, our [open data portals comparison](../2026-06-08-open-data-portals-ckan-vs-dkan-vs-dataverse/) covers CKAN, DKAN, and Dataverse. For collaborative decision-making, check our [group decision-making tools guide](../2026-06-11-self-hosted-group-decision-making-loomio-democracyos-considerit/).

## FAQ

### Can FixMyStreet handle multiple cities in one installation?

Yes, FixMyStreet's cobrand system supports multiple jurisdictions from a single codebase. Each city or region gets its own branded subdomain, report categories, and administrative dashboard while sharing the same backend infrastructure. This architecture has been proven across 400+ UK councils and international deployments.

### What's the minimum hardware requirement for self-hosting?

A VPS with 2 vCPUs, 4GB RAM, and 20GB SSD storage can comfortably run FixMyStreet or Mark-a-Spot for a small to medium city (up to 100,000 residents). FixMyStreet is particularly resource-efficient due to its Perl Catalyst architecture. Add more resources as report volume grows—PostGIS spatial queries become the primary bottleneck at scale.

### Does Mark-a-Spot support Open311?

Mark-a-Spot has partial Open311 support through community-contributed modules. Full Open311 GeoReport v2 compliance is under development. If Open311 integration with external systems is a hard requirement, FixMyStreet offers the most mature implementation.

### How do these platforms handle photo uploads?

All three platforms support photo attachments with reports. FixMyStreet stores photos on the server filesystem with configurable size limits (default 20MB). Mark-a-Spot integrates with Drupal's media management for automatic thumbnail generation and CDN integration. CityGram supports image attachments through Twilio MMS and can forward photos to city work order systems.

### Can I migrate from a commercial platform to an open-source one?

Yes, but it requires planning. FixMyStreet provides CSV import tools for bulk report migration from SeeClickFix and other platforms. The Open311 standard helps—if your current platform exports Open311 data, you can import it programmatically. Plan for a transition period where both systems run in parallel.

### Are these platforms accessible for users with disabilities?

FixMyStreet has undergone WCAG 2.1 AA audits and is used by the UK government, which has strict accessibility requirements. Mark-a-Spot benefits from Drupal's accessibility features and Vue.js ARIA support. CityGram's notification-based model is inherently more accessible as it works via SMS for users without smartphones.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Citizen Reporting Platforms: FixMyStreet vs Mark-a-Spot vs CityGram",
  "description": "Compare three open-source citizen reporting platforms: FixMyStreet (599 stars, Perl), Mark-a-Spot (70 stars, Drupal/PWA), and CityGram (170 stars, Ruby). Includes Docker Compose deployment configs, feature comparison table, and self-hosting guide for municipalities.",
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
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
