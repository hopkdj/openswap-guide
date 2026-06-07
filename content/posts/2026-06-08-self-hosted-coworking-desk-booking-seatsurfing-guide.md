---
title: "Self-Hosted Coworking Space & Desk Booking: Seatsurfing vs MRBS Alternatives for Flexible Workspaces"
date: "2026-06-08"
tags: ["coworking", "desk-booking", "room-reservation", "workspace-management", "office-tools", "self-hosted"]
draft: false
---

## Introduction

The rise of hybrid work has made flexible workspace management essential. Whether you run a coworking space, manage a shared office, or simply want to coordinate hot-desking across your team, self-hosted desk booking systems give you full control over your workspace logistics without paying per-user SaaS fees. These platforms handle desk reservations, room bookings, seat assignments, and capacity tracking — all from a server you control.

In this guide, we compare the leading open-source workspace management tools that you can self-host with Docker, helping you choose the right solution for your flexible office environment.

## Comparison Table

| Feature | Seatsurfing | MRBS | Booked Scheduler |
|---------|------------|------|-----------------|
| GitHub Stars | 295+ | 190+ | 220+ |
| Primary Use | Desk/seat booking | Room booking | Resource scheduling |
| Docker Support | Yes (official) | Community images | Yes |
| Floor Plan View | Yes (SVG maps) | No | No |
| Mobile-Friendly | Yes | Basic | Yes |
| SSO/OIDC Support | Yes | LDAP | Yes |
| Multi-Location | Yes | Yes | Yes |
| API Available | Yes (REST) | Limited | Yes (REST) |
| License | AGPL-3.0 | GPL-2.0 | GPL-3.0 |
| Active Development | Active (2026) | Active | Moderate |

## Seatsurfing: Purpose-Built for Hot-Desking

[Seatsurfing](https://github.com/seatsurfing/seatsurfing) is a modern, Docker-native desk booking platform designed specifically for flexible workspaces. Unlike general-purpose room booking tools, Seatsurfing focuses on the hot-desking experience with interactive floor plan maps, seat-level reservations, and frictionless check-in flows.

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  seatsurfing:
    image: seatsurfing/backend:latest
    container_name: seatsurfing
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      SEATSURFING_DB_HOST: postgres
      SEATSURFING_DB_PORT: "5432"
      SEATSURFING_DB_NAME: seatsurfing
      SEATSURFING_DB_USER: seatsurfing
      SEATSURFING_DB_PASSWORD: changeme
      SEATSURFING_ADMIN_EMAIL: admin@example.com
      SEATSURFING_ADMIN_PASSWORD: admin123!
      SEATSURFING_PUBLIC_URL: https://desk.example.com
      SEATSURFING_OIDC_ENABLED: "false"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./data:/app/data

  postgres:
    image: postgres:16-alpine
    container_name: seatsurfing-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: seatsurfing
      POSTGRES_USER: seatsurfing
      POSTGRES_PASSWORD: changeme
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U seatsurfing"]
      interval: 5s
      timeout: 5s
      retries: 5
```

Key features include:
- **Interactive floor plans**: Upload SVG maps and place clickable desk markers
- **Self-service booking**: Users browse available desks and reserve directly
- **Check-in/check-out**: QR code and confirmation links for attendance tracking
- **OIDC integration**: Connect with Authentik, Keycloak, or any OIDC provider
- **Multi-tenant**: Support multiple locations and organizations from a single instance

## MRBS: The Battle-Tested Room Booker

[MRBS](https://mrbs.sourceforge.io/) (Meeting Room Booking System) has been around since the early 2000s and remains one of the most deployed open-source room booking systems. While originally focused on meeting rooms, MRBS can be adapted for desk booking with custom area configurations.

```php
// MRBS configuration excerpt (config.inc.php)
$auth["type"] = "db";       // Database authentication
$auth["session"] = "php";    // PHP session handling
$mail_settings['admin_email'] = 'admin@example.com';
$mail_settings['from'] = 'noreply@example.com';

// Enable periodic booking features
$periods_enabled = true;
$enable_periods = true;

// Set timezone and default view
$default_timezone = "America/New_York";
$default_view = "week";
$default_room = "Desk Area A";
```

MRBS strengths include:
- **Decades of stability**: Production-hardened across thousands of deployments
- **Recurring bookings**: Advanced repeating reservation patterns
- **LDAP authentication**: Native integration with enterprise directories
- **Email notifications**: Customizable templates for confirmations and reminders
- **Reporting**: Usage statistics and booking history exports

## Why Self-Host Your Workspace Management?

Running your own desk booking platform gives you several advantages over SaaS alternatives:

**Data sovereignty**: All booking data, user information, and usage patterns stay on your infrastructure. No third party has access to who sits where or when — important for companies with sensitive floor plans or security-conscious environments.

**Cost predictability**: SaaS desk booking tools typically charge $3-8 per user per month. For a 200-person office, that is $7,200-$19,200 annually. Self-hosting on a $20/month VPS costs $240/year regardless of user count. The savings compound as your team grows.

**Integration flexibility**: Self-hosted platforms let you connect directly to your existing identity provider (OIDC, LDAP, SAML), your internal calendar systems (CalDAV), and your office IoT sensors (occupancy detection). You are not limited to the integrations a SaaS vendor chooses to build.

**Customization control**: Need custom booking rules? Want to add QR-code door access integration? With self-hosted software, you own the codebase and can modify it to fit your exact workflow. For organizations with unique workspace policies, this flexibility is essential.

For team communication, see our [Matrix chat clients guide](../2026-05-07-matrix-chat-clients-element-cinny-fluffychat-guide/). For scheduling beyond desk booking, check our [self-hosted scheduling platforms comparison](../2026-05-13-calcom-vs-easyappointments-vs-rallly-self-hosted-scheduling-guide/). If you manage physical meeting spaces, our [room booking guide](../mrbs-vs-booked-vs-grr-self-hosted-room-booking-guide-2026/) covers traditional conference room scheduling.

## Deployment Architecture

A typical self-hosted workspace management deployment follows this architecture:

```
                  ┌─────────────┐
                  │   Reverse   │
    Internet ────▶│   Proxy     │────▶ seatsurfing:8080
                  │  (Caddy)    │
                  └─────────────┘────▶ postgres:5432
                         │
                         ▼
                  ┌─────────────┐
                  │ OIDC Provider│
                  │ (Authentik)  │
                  └─────────────┘
```

**Reverse proxy configuration** (Caddyfile):
```
desk.example.com {
    reverse_proxy seatsurfing:8080
    header Access-Control-Allow-Origin *
}
```

For high-availability setups, run PostgreSQL in replication mode and deploy multiple Seatsurfing instances behind a load balancer. Use the REST API to sync booking data across locations.


## Security and Access Control Considerations

When deploying a self-hosted workspace management platform that handles real-time occupancy data, security deserves careful attention. Here are key considerations for production deployments:

**Network segmentation**: Place your booking application on an isolated VLAN separate from guest Wi-Fi networks. Coworking spaces often have public networks that should never have direct access to the booking backend. Use your reverse proxy (Caddy, Nginx, or Traefik) as the sole entry point with TLS termination.

**Authentication hardening**: Enable OIDC with a dedicated identity provider like Authentik or Keycloak. Avoid the built-in local authentication for production use — centralized identity management means you can revoke access instantly when a membership ends, rather than managing accounts across multiple systems. Configure short session timeouts (2-4 hours) to minimize exposure from unattended kiosk devices.

**Data retention**: Booking records contain patterns of when specific people are in the office. Define a data retention policy — most privacy regulations require you to state how long occupancy data is stored. Seatsurfing supports automatic pruning of historical booking data beyond a configurable age, helping you comply with GDPR and similar regulations.

**Audit logging**: Enable detailed access logs in your reverse proxy and monitor for unusual patterns. A sudden spike in booking API calls from a single IP could indicate scraping or abuse. Forward logs to a centralized log management system for long-term retention and alerting.


## FAQ

### Can I use Seatsurfing for meeting room booking alongside desks?

Yes. Seatsurfing supports both desks and rooms as reservable resources. You can create an SVG floor plan with both desk icons and room icons, and define different booking rules for each type. For organizations that need primarily meeting room scheduling with advanced recurring booking patterns, MRBS may be a better fit.

### How does check-in enforcement work?

Seatsurfing supports QR code check-in, email link confirmation, and optional automatic release of unconfirmed bookings. When a user reserves a desk, they receive a confirmation email with a check-in link. If they do not check in within a configurable window (e.g., 30 minutes after the booking start), the desk is automatically released for others to book — preventing "ghost reservations" that waste capacity.

### Can I integrate desk booking with physical access control?

Yes, through Seatsurfing's REST API. The API exposes current bookings, user assignments, and check-in status. You can build middleware that queries `/api/bookings/current` and controls door strikes, desk power outlets, or monitor activation based on booking validity. This is commonly used in managed coworking spaces where desk access should be gated behind valid reservations.

### What hardware do I need to run a self-hosted desk booking system?

A basic VPS with 2 vCPUs, 2GB RAM, and 20GB SSD can comfortably serve 500+ users. PostgreSQL will consume about 256MB RAM under normal load. If you expect high concurrency (100+ simultaneous bookings), upgrade to 4GB RAM. The application itself is lightweight — most resource usage comes from the database.

### Does Seatsurfing support floor plan visualization on mobile?

The interactive SVG floor plans render responsively on mobile browsers. Users can pinch-zoom, tap desks to view details, and complete bookings from their phones. The mobile web interface is optimized for on-the-go booking, though there is no native mobile app — the PWA works well as a home screen shortcut.

### Can I restrict booking to specific user groups or departments?

Seatsurfing supports location-based and organization-based access control through its multi-tenant architecture. You can create separate organizations with their own floor plans and user pools. Within the OIDC integration, you can map group claims to restrict which users can book specific locations. MRBS offers area-level and room-level access controls through its permission system.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Coworking Space & Desk Booking: Seatsurfing vs MRBS Alternatives for Flexible Workspaces",
  "description": "Comprehensive comparison of self-hosted desk booking and coworking space management tools including Seatsurfing, MRBS, and Booked Scheduler with Docker Compose deployment guides.",
  "datePublished": "2026-06-08",
  "dateModified": "2026-06-08",
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
