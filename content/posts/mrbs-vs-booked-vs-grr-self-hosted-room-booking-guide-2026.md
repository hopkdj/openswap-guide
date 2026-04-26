---
title: "MRBS vs Booked vs GRR: Best Self-Hosted Room Booking Systems 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "scheduling"]
draft: false
description: "Compare MRBS, Booked, and GRR — the top open-source self-hosted room booking and resource scheduling platforms for 2026. Complete Docker setup guides included."
---

Managing room bookings, equipment reservations, and shared resource schedules is a universal organizational challenge. Most teams default to Google Calendar, Outlook Room Finder, or paid SaaS booking platforms — but these tools collect scheduling data, impose per-user licensing costs, and often lack the granular resource management that offices, labs, and shared workspaces actually need.

Self-hosting a room booking system gives you full control over your scheduling data, eliminates recurring per-seat fees, and provides dedicated resource management features (equipment checkout, approval workflows, capacity limits) that general-purpose calendar tools simply don't offer. In this guide, we compare three mature open-source booking platforms — **MRBS**, **Booked**, and **GRR** — with complete Docker deployment instructions to help you pick the right tool for your organization.

## Why Self-Host Your Room Booking System

General-purpose calendar tools like Google Calendar and Outlook treat rooms as just another calendar resource. They lack features essential for facility management:

- **Equipment tracking** — projector checkout, laptop reservations, lab instrument scheduling
- **Approval workflows** — manager sign-off for conference rooms or high-value resources
- **Capacity and policy enforcement** — preventing overbooking, enforcing minimum lead times
- **Reporting and utilization analytics** — understanding which rooms are underused
- **Data sovereignty** — your booking patterns and resource usage data stays on your infrastructure

Self-hosted booking platforms are purpose-built for these scenarios. They model resources hierarchically (buildings → rooms → equipment), support approval chains, and provide utilization reports that help facility managers optimize space allocation.

## The Landscape: MRBS vs Booked vs GRR

| Feature | MRBS | Booked (phpScheduleIt) | GRR |
|---|---|---|---|
| **License** | GPL v2+ | GPL v3 | GPL v2 |
| **Stack** | PHP + MySQL/PostgreSQL | PHP + MySQL | PHP + MySQL |
| **Docker Support** | Community images | Official compose | Community images |
| **Resource Hierarchy** | Areas → Rooms | Schedules → Resources | Rooms → Resources |
| **Recurring Bookings** | Yes | Yes | Yes |
| **Approval Workflows** | Configurable per-room | Advanced multi-level | Per-resource admin |
| **Equipment Checkout** | Via custom attributes | Native tracking | Via resource types |
| **LDAP/AD Auth** | Yes | Yes | Yes |
| **iCal Export** | Yes | Yes | Yes |
| **Email Notifications** | Yes | Yes (advanced) | Yes |
| **REST API** | Limited | Yes | Limited |
| **Mobile Responsive** | Basic | Yes | Basic |
| **Multi-language** | 30+ | 20+ | 10+ |
| **GitHub Stars** | ~400 | ~600 | ~100 |
| **Last Updated** | Active | Active | Active |

## MRBS (Meeting Room Booking System)

[MRBS](https://mrbs.sourceforge.io/) is one of the oldest and most widely deployed open-source room booking systems. It's used by universities, government agencies, and enterprises worldwide. Its strength lies in simplicity and reliability — it does one thing well.

### Key Features

- Area and room hierarchy with customizable fields
- Custom booking types (e.g., training, meeting, private)
- Per-room access control (who can book, who approves)
- Recurring booking patterns (daily, weekly, monthly)
- CSV and iCal export for reporting
- LDAP, SAML, and local authentication

### Docker Deployment

MRBS doesn't have an official Docker image, but the community-maintained image works well:

```yaml
version: "3.8"

services:
  mrbs:
    image: linuxserver/mrbs:latest
    container_name: mrbs
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    ports:
      - "8080:80"
    volumes:
      - ./mrbs-config:/config
    restart: unless-stopped

  mrbs-db:
    image: mariadb:11
    container_name: mrbs-db
    environment:
      - MYSQL_ROOT_PASSWORD=mrbs-root-pass
      - MYSQL_DATABASE=mrbs
      - MYSQL_USER=mrbs
      - MYSQL_PASSWORD=mrbs-secret
    volumes:
      - mrbs-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  mrbs-data:
```

Save this as `docker-compose.yml` and run:

```bash
docker compose up -d
```

Access MRBS at `http://localhost:8080`. The default admin credentials are `administrator` / `password` — change these immediately after first login.

### Configuration Tips

After initial setup, configure the following in `config.inc.php`:

```php
$auth["type"] = "ldap";
$ldap_host = "ldap.your-org.com";
$ldap_base_dn = "ou=users,dc=your-org,dc=com";
$ldap_user_attrib = "uid";

// Require approval for specific room types
$approval_enabled = true;
$min_bdays_ahead = 1;
$max_bdays_ahead = 90;
```

## Booked (formerly phpScheduleIt)

[Booked](https://www.bookedscheduler.com/) is the most feature-rich of the three platforms. It evolved from phpScheduleIt and has been actively developed for over a decade. Its strength is comprehensive resource management with advanced workflow capabilities.

### Key Features

- Unlimited resource types and schedules
- Advanced approval workflows (multi-level)
- Equipment checkout with quantity tracking
- Quotas and limits (max bookings per user, per day)
- Credits-based booking system (charge departments for room use)
- REST API for integration
- Custom attributes per resource
- Waitlist functionality for fully booked resources
- Blackout periods for maintenance or holidays

### Docker Deployment

Booked provides official Docker compose support:

```yaml
version: "3.8"

services:
  booked:
    image: linuxserver/booked:latest
    container_name: booked
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    ports:
      - "8081:80"
    volumes:
      - ./booked-config:/config
    depends_on:
      - booked-db
    restart: unless-stopped

  booked-db:
    image: mariadb:11
    container_name: booked-db
    environment:
      - MYSQL_ROOT_PASSWORD=booked-root-pass
      - MYSQL_DATABASE=booked
      - MYSQL_USER=booked
      - MYSQL_PASSWORD=booked-secret
    volumes:
      - booked-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  booked-data:
```

```bash
docker compose up -d
```

Access Booked at `http://localhost:8081`. Log in as admin and run the installer wizard to configure the database connection.

### Advanced Configuration

Booked's configuration is managed through the web admin panel, but key settings in `config/config.php`:

```php
$conf['settings']['auth']['allow.self.registration'] = 'false';
$conf['settings']['authorization']['allow.guest.login'] = 'false';
$conf['settings']['uploads']['enable.reservation.attachments'] = 'true';
$conf['settings']['reports']['allow.reports'] = 'true';
// Enable credits system
$conf['settings']['credits']['enabled'] = 'true';
$conf['settings']['credits']['allow.purchase'] = 'false';
```

## GRR (Gestion de Ressources et Réservations)

[GRR](https://grr.devome.com/) is a French-developed booking system that has gained international adoption. It's lightweight and focused on simplicity, making it ideal for schools, small offices, and community organizations.

### Key Features

- Room and resource reservation with type categorization
- Per-area access control (administrators, users, visitors)
- Recurring reservations with exception handling
- Email notifications for new bookings and modifications
- Statistics and usage reports per room and per user
- LDAP authentication support
- iCal subscription for personal calendars
- Custom fields for resources

### Docker Deployment

```yaml
version: "3.8"

services:
  grr:
    image: jcdemaison/grr:latest
    container_name: grr
    environment:
      - GRR_DB_HOST=grr-db
      - GRR_DB_NAME=grr
      - GRR_DB_USER=grr
      - GRR_DB_PASSWORD=grr-secret
      - TZ=UTC
    ports:
      - "8082:80"
    depends_on:
      - grr-db
    restart: unless-stopped

  grr-db:
    image: mariadb:11
    container_name: grr-db
    environment:
      - MYSQL_ROOT_PASSWORD=grr-root-pass
      - MYSQL_DATABASE=grr
      - MYSQL_USER=grr
      - MYSQL_PASSWORD=grr-secret
    volumes:
      - grr-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  grr-data:
```

```bash
docker compose up -d
```

Access GRR at `http://localhost:8082`. The installer will guide you through database initialization.

## Choosing the Right Platform

| Scenario | Recommended Tool |
|---|---|
| **Simple room booking, minimal setup** | MRBS |
| **Enterprise with approval workflows, credits, equipment tracking** | Booked |
| **Small team, lightweight, easy to manage** | GRR |
| **University with many buildings and rooms** | MRBS or Booked |
| **Need REST API for integrations** | Booked |
| **Need waitlist and quota management** | Booked |
| **Budget-conscious, low maintenance** | GRR |

## Related Reading

For broader scheduling and calendar management, see our [self-hosted scheduling platforms guide](../self-hosted-scheduling-booking-platforms-cal-com-easy-appointments-2026/) and [self-hosted calendar servers comparison](../radicale-vs-baikal-vs-xandikos-self-hosted-calendar-contacts/).

## FAQ

### Can these tools handle equipment booking in addition to rooms?

Yes. All three platforms support resource booking beyond rooms. Booked has the most mature equipment tracking with quantity management and checkout workflows. MRBS handles equipment through custom attributes, while GRR uses resource type categorization to differentiate between rooms and movable equipment.

### Do these platforms support integration with existing calendar systems?

All three support iCal export, allowing users to subscribe to room schedules from Google Calendar, Outlook, or Thunderbird. Booked also offers a REST API for deeper integration with custom applications and existing booking portals.

### Can I restrict booking permissions to specific users or groups?

Yes. All three platforms provide granular access control. You can configure who can view, book, or approve reservations per room or per resource group. LDAP/Active Directory integration allows you to map organizational groups to booking permissions.

### How do I handle recurring bookings like weekly team meetings?

All three platforms support recurring booking patterns — daily, weekly, biweekly, monthly, and custom intervals. You can set an end date or a maximum number of occurrences. Booked additionally supports exception handling for individual instances within a recurring series.

### What happens when a room needs maintenance or is temporarily unavailable?

Booked has a dedicated blackout period feature that blocks all bookings for specified date ranges. MRBS and GRR handle this by creating blocking reservations (e.g., "Maintenance" bookings that prevent other reservations during those periods).

### Can I generate utilization reports to see which rooms are underused?

All three platforms provide usage statistics. MRBS offers CSV export for spreadsheet analysis. Booked has built-in reports with charts and filtering by date range, user, and resource. GRR includes per-room and per-user statistics dashboards.

### Is LDAP/Active Directory authentication supported?

Yes, all three platforms support LDAP authentication. Booked additionally supports SAML 2.0 and OAuth2 for modern identity provider integration. This allows users to log in with their existing corporate credentials.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MRBS vs Booked vs GRR: Best Self-Hosted Room Booking Systems 2026",
  "description": "Compare MRBS, Booked, and GRR — the top open-source self-hosted room booking and resource scheduling platforms for 2026. Complete Docker setup guides included.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
