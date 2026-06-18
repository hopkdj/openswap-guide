---
title: "Self-Hosted Event Ticketing & Registration: Attendize vs eventyay vs alf.io Compared 2026"
date: "2026-06-19"
tags: ["self-hosted", "event-ticketing", "event-management", "open-source", "attendize", "eventyay", "alfio", "registration", "conference"]
draft: false
---

Whether you're organizing a community meetup, a multi-track conference, or a music festival, selling tickets and managing registrations is the operational backbone of your event. Self-hosted ticketing platforms let you avoid per-ticket fees while maintaining full control over attendee data and the purchase experience.

## Why Self-Host Your Event Ticketing?

Commercial ticketing platforms charge fees that compound quickly. At 5-7% per ticket plus fixed fees, a conference selling 500 tickets at $100 each loses $2,500-$3,500 to the platform — before payment processing fees. Self-hosted alternatives eliminate these platform fees entirely. You pay only payment processor fees (typically 2.9% + $0.30), saving thousands per event.

Data ownership is equally important. When you use Eventbrite or Ticketmaster, attendee email addresses, purchase history, and demographic data live on their platform. You can export it, but you can't build long-term relationships directly. Self-hosting means every attendee interaction enriches your own database, enabling personalized follow-ups and targeted marketing for future events.

For organizations running recurring events — monthly meetups, quarterly workshops, annual conferences — the savings compound. A single self-hosted instance can manage dozens of events across years. If you also manage conference programs and speaker submissions, check out our [self-hosted conference CFP management guide](../2026-06-15-self-hosted-academic-conference-cfp-management-open-event-indico-pretalx/).

For organizations that need to manage both memberships AND events, see our comparison of [self-hosted association management platforms](../2026-06-19-self-hosted-association-membership-admidio-galette-tendenci/). And if you need collaborative planning tools, our [content calendar and editorial planning guide](../2026-05-04-self-hosted-content-calendar-editorial-planning-focalboard-leantime-vikunja-guide/) covers task management for event teams.

## Comparison: Attendize vs eventyay vs alf.io

| Feature | Attendize | eventyay | alf.io |
|---------|-----------|----------|--------|
| **GitHub Stars** | 4,262 | 1,628 | 1,588 |
| **Primary Language** | PHP (Laravel) | Python/Flutter | Java (Spring Boot) |
| **Database** | MySQL | PostgreSQL | PostgreSQL |
| **Free Tickets** | Yes | Yes | Yes |
| **Paid Tickets** | Stripe, PayPal | Stripe, PayPal, Omise | Stripe, PayPal, Mollie |
| **Seat Maps** | No | No | Yes (interactive) |
| **Discount Codes** | Yes | Yes | Yes |
| **Check-in App** | Web-based | Mobile app (Flutter) | Mobile app + Web |
| **Multi-Language** | 10+ languages | 5+ languages | 30+ languages |
| **Ticket PDF** | Yes | Yes | Yes (customizable) |
| **API** | REST API | GraphQL + REST | REST API |
| **Multi-Event** | Yes | Yes | Yes |
| **Waitlist** | No | Yes | Yes |
| **Docker Support** | Docker Compose | Manual setup | Docker Compose |
| **Last Updated** | Aug 2024 | June 2026 | June 2026 |

### Attendize — Polished Laravel Platform

Attendize is an open-source event management and ticket selling platform built on Laravel (PHP). It was once a commercial product and retains a polished admin interface that feels professional. The organizer dashboard provides clear revenue tracking, attendee lists, and order management.

Attendize supports multiple ticket tiers per event with early-bird pricing, discount codes, and custom questions during checkout. Its strength is the attendee management workflow: create an event, set up ticket types, collect orders, and check in attendees — all from a clean admin panel.

```yaml
# docker-compose.yml for Attendize
version: '3.8'
services:
  attendize:
    image: attendize/attendize:latest
    container_name: attendize
    ports:
      - "8081:80"
    environment:
      - DB_HOST=db
      - DB_DATABASE=attendize
      - DB_USERNAME=attendize
      - DB_PASSWORD=changeme
      - APP_URL=https://tickets.yourdomain.com
    volumes:
      - attendize_storage:/var/www/attendize/storage
    depends_on:
      - db
  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=attendize
      - MYSQL_USER=attendize
      - MYSQL_PASSWORD=changeme
    volumes:
      - mysql_data:/var/lib/mysql
volumes:
  attendize_storage:
  mysql_data:
```

**Note:** Attendize's last commit was August 2024. The project is stable and feature-complete for basic ticketing needs, but it is not receiving active feature development. For organizations that need a stable, proven platform without cutting-edge features, this is acceptable. For those who need ongoing development, eventyay or alf.io are better choices.

### eventyay — FOSSASIA's Modern Platform

eventyay is developed by FOSSASIA, the organization behind the annual FOSSASIA Summit. It is a modern, actively maintained platform with a Flutter-based mobile app for organizers and a responsive web frontend. It is the newest of the three platforms and benefits from lessons learned from earlier ticketing projects.

eventyay supports both free and paid tickets with Stripe, PayPal, and Omise payment gateways. Its GraphQL API makes it easy to build custom integrations, and the Flutter check-in app (available on both iOS and Android) provides a native scanning experience for event staff.

The platform excels at the complete event lifecycle: call for papers/speakers, schedule builder, ticket sales, and on-site check-in. For conferences that need an integrated solution rather than separate CFP and ticketing tools, eventyay is the most comprehensive option.

### alf.io — Enterprise-Grade with Seat Maps

alf.io is a Java-based (Spring Boot) ticketing platform that stands out with its interactive seat map feature — the only platform in this comparison that supports reserved seating. For theater performances, gala dinners, or any event with assigned seats, alf.io is the clear choice.

alf.io supports 30+ languages, making it the most internationally accessible option. Its payment gateway support is equally broad: Stripe, PayPal, Mollie, Saferpay, and several European-specific gateways. The platform also handles VAT/tax calculations automatically based on event location — essential for European event organizers.

```yaml
# docker-compose.yml for alf.io
version: '3.8'
services:
  alfio:
    image: alfio/alf.io:latest
    container_name: alfio
    ports:
      - "8082:8080"
    environment:
      - JAVA_OPTS=-Xmx512m
      - SPRING_PROFILES_ACTIVE=jdbc-session
      - DATABASE_URL=jdbc:postgresql://db:5432/alfio
      - DATABASE_USERNAME=alfio
      - DATABASE_PASSWORD=changeme
      - ALFIO_BASE_URL=https://tickets.yourdomain.com
    volumes:
      - alfio_data:/root/alfio-data
    depends_on:
      - db
  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=alfio
      - POSTGRES_USER=alfio
      - POSTGRES_PASSWORD=changeme
    volumes:
      - pg_data:/var/lib/postgresql/data
volumes:
  alfio_data:
  pg_data:
```

## Performance and Scaling Considerations

Event ticketing platforms face unique scaling challenges: traffic spikes during ticket sales, concurrent seat reservations, and payment processing under time pressure. The right database and caching strategy makes the difference between a smooth on-sale and frustrated attendees.

**Concurrency Control**: alf.io uses PostgreSQL's row-level locking for seat reservations, ensuring two attendees can't purchase the same seat simultaneously. Attendize uses MySQL's transactional model with pessimistic locking on ticket inventory. eventyay handles concurrency through PostgreSQL's `SELECT FOR UPDATE` — all three approaches work, but they need to be paired with connection pooling (PgBouncer for PostgreSQL) under high load.

**Caching**: For events expecting thousands of simultaneous visitors during ticket sales, add Redis caching in front of the application. alf.io has built-in caching support. For Attendize and eventyay, a Redis container and application-level caching configuration provide significant performance improvements.

**CDN for Static Assets**: Ticket images, event banners, and venue maps should be served through a CDN. This reduces load on your application server and improves page load times for attendees worldwide. Cloudflare's free tier works well for this purpose.

## Choosing the Right Platform

For **occasional community events** with free or donation-based tickets, Attendize provides the simplest setup and cleanest interface. Its Laravel base means PHP developers can easily customize it, and the admin panel requires minimal training for volunteer organizers. The main concern is the project's inactive development — if you need new features, you'll need to build them yourself.

For **tech conferences and events with CFPs**, eventyay is the strongest choice. Its integrated call-for-papers, schedule builder, and native mobile check-in app create a seamless experience from proposal submission to on-site attendance tracking. The active FOSSASIA community provides ongoing development and support.

For **seated events, performances, and international audiences**, alf.io is the best option. Seat maps, 30+ language support, and automatic VAT handling make it the only viable choice for European theaters, gala dinners, and events with assigned seating. Its enterprise-grade architecture handles the complexity that simpler platforms avoid.

## FAQ

### Can I integrate these with my existing website or CMS?

Yes. All three platforms can be embedded or linked from existing websites. alf.io provides a JavaScript widget for embedding the ticket purchase flow directly into any page. Attendize and eventyay can be iframed or linked as standalone pages styled to match your brand. For WordPress sites, you can point a subdomain (tickets.yourdomain.com) to the ticketing platform and link from your main site.

### How do I handle refunds and cancellations?

alf.io has the most complete refund workflow: organizers can issue full or partial refunds from the admin panel, and the platform tracks refund status against the original order. Attendize supports full order cancellation with optional refund processing. eventyay handles refunds through the payment gateway's admin interface. For all three, refund policies should be clearly communicated on the event page before purchase.

### What payment processing fees should I expect?

With self-hosted ticketing, you pay only payment processor fees: Stripe charges 2.9% + $0.30 per transaction, PayPal ranges from 2.59% to 3.49%, and Mollie (Europe) charges 1.2% + €0.25 for major European payment methods. alf.io's Mollie integration is particularly cost-effective for European events, with fees significantly lower than US-based processors.

### How does check-in work on the day of the event?

eventyay provides a Flutter-based mobile app for ticket scanning — download it from the app stores, log in with organizer credentials, and scan QR codes from attendees' tickets. alf.io has both a mobile app and a progressive web app for scanning. Attendize provides web-based check-in that works in any browser. For high-volume check-in, eventyay and alf.io's native scanning is notably faster than web-based solutions.

### Can I sell tickets in multiple currencies?

alf.io supports multi-currency events with automatic conversion. eventyay handles multi-currency through its payment gateway configuration — Stripe handles the conversion. Attendize supports the currency set at the application level, so each installation is single-currency. For international events with attendees from multiple countries, alf.io's multi-currency support is the most flexible.

### Is there ticket transfer functionality?

alf.io supports ticket reassignment through its admin panel — an organizer can transfer a ticket from one attendee to another. eventyay includes a self-service ticket transfer feature where attendees can reassign tickets themselves. Attendize requires manual order editing by the organizer for ticket transfers. For events where attendees frequently need to transfer tickets (corporate events, team registrations), eventyay's self-service transfer is the most convenient.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Event Ticketing & Registration: Attendize vs eventyay vs alf.io Compared 2026",
  "description": "Comprehensive comparison of open-source self-hosted event ticketing platforms: Attendize, eventyay, and alf.io. Includes Docker Compose deployment configs, feature comparison table, performance guidance, and FAQ for conference and event organizers.",
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
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
