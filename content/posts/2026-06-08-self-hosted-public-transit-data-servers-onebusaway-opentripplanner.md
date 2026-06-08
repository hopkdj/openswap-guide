---
title: "Self-Hosted Public Transit Data Servers: OneBusAway vs OpenTripPlanner vs TheTransitClock"
date: "2026-06-08"
tags: ["public-transit", "gtfs", "transportation", "open-data", "mapping", "self-hosted"]
draft: false
---

Public transit agencies around the world publish their schedule and real-time data using the General Transit Feed Specification (GTFS). But serving that data to riders — powering trip planners, arrival predictions, and service alerts — requires dedicated transit data server software. Rather than relying on Google Maps or Apple Maps alone, many agencies and enthusiasts self-host their own transit information systems to maintain data sovereignty, reduce costs, and offer customized rider experiences.

In this guide, we compare three leading open-source transit data servers that you can deploy on your own infrastructure: **OneBusAway**, **OpenTripPlanner**, and **TheTransitClock**. Each serves a distinct role in the transit data ecosystem — from real-time arrival displays to multimodal trip planning.

## Feature Comparison

| Feature | OneBusAway | OpenTripPlanner | TheTransitClock |
|---------|-----------|-----------------|-----------------|
| Primary Use Case | Real-time bus tracking & arrival predictions | Multimodal trip planning (transit + bike + walk) | Real-time transit vehicle tracking |
| GTFS Static | Yes | Yes | Yes |
| GTFS Realtime | Yes (full support) | Yes | Yes |
| REST API | Yes | Yes (GraphQL + REST) | Yes |
| Web Frontend | Yes (built-in) | Yes (debug UI) | Yes (admin + public) |
| Docker Support | Yes | Yes (community images) | Yes |
| License | Apache 2.0 | LGPL-3.0 | MIT |
| Stars | 236 | 2,655 | 86 |
| Last Updated | 2026-02 | 2026-06 | 2024-07 |

## OneBusAway

OneBusAway started at the University of Washington and has grown into a mature platform for delivering real-time bus arrival predictions. It ingests GTFS static schedule data along with GTFS Realtime vehicle positions and trip updates, then exposes a REST API and mobile-friendly web interface for riders.

**Key strengths:**
- Battle-tested in production at major transit agencies across North America
- Built-in web application with stop search, route maps, and arrival countdowns
- Modular architecture separating transit data, vehicle tracking, and web interface
- Active community with deployment guides and documentation

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  oba-db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: oba-root-password
      MYSQL_DATABASE: onebusaway
      MYSQL_USER: oba
      MYSQL_PASSWORD: oba-password
    volumes:
      - oba-db-data:/var/lib/mysql

  oba-app:
    image: onebusaway/onebusaway-application-modules:latest
    ports:
      - "8080:8080"
    environment:
      JDBC_URL: jdbc:mysql://oba-db:3306/onebusaway
      JDBC_USER: oba
      JDBC_PASSWORD: oba-password
      GTFS_URL: https://example.com/gtfs.zip
    depends_on:
      - oba-db

volumes:
  oba-db-data:
```

## OpenTripPlanner

OpenTripPlanner (OTP) is the most popular open-source multimodal trip planner, used by transit agencies worldwide including national journey planners in Finland, Norway, and the Netherlands. Unlike OneBusAway's focus on real-time arrivals, OTP excels at computing optimal routes that combine public transit with walking, cycling, and other modes.

**Key strengths:**
- Multimodal routing combining transit, walking, biking, and car
- Built-in elevation-aware routing for cyclists
- GraphQL API for flexible client integration
- Extensive international deployment base with 2,600+ stars on GitHub
- Support for GTFS, OpenStreetMap, and elevation data

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  otp:
    image: opentripplanner/opentripplanner:latest
    ports:
      - "8080:8080"
      - "8081:8081"
    volumes:
      - ./graphs:/var/otp/graphs
      - ./data:/var/otp/data
    command: --load --serve
    environment:
      JAVA_OPTS: "-Xmx4G"
```

This configuration mounts local directories for graph storage and input data. You build your transit graph once (a process that takes a few minutes for a medium-sized city) and then OTP serves routing requests at sub-second speeds.

## TheTransitClock

TheTransitClock takes a complementary approach: it specializes in predicting when the next bus will arrive by analyzing historical and real-time vehicle movement data. It processes GTFS Realtime feeds to track vehicle positions against schedule data and delivers accurate arrival predictions through its API and map interface.

**Key strengths:**
- Purpose-built for arrival time prediction using Kalman filtering
- Map-based admin interface for monitoring vehicle positions
- Lightweight deployment focused on real-time prediction, not trip planning
- MIT-licensed for maximum flexibility

**Simple deployment using Docker:**

```yaml
version: "3.8"
services:
  transitime-db:
    image: postgres:16
    environment:
      POSTGRES_DB: transitime
      POSTGRES_USER: transitime
      POSTGRES_PASSWORD: transit-password
    volumes:
      - transit-db:/var/lib/postgresql/data

  transitime-core:
    image: thetransitclock/transitime:latest
    ports:
      - "8080:8080"
    environment:
      TRANSITCLOCK_DB_HOST: transitime-db
      TRANSITCLOCK_DB_NAME: transitime
      TRANSITCLOCK_DB_USER: transitime
      TRANSITCLOCK_DB_PASSWORD: transit-password
    depends_on:
      - transitime-db

volumes:
  transit-db:
```

## Which Transit Server Should You Choose?

The choice depends on your primary use case. If you run a bus-only agency that needs real-time arrival signage and rider-facing stop predictions, OneBusAway is the battle-tested choice. If you need a comprehensive trip planner that handles walking, biking, and transit connections across a region, OpenTripPlanner is the gold standard with the largest community. If your focus is exclusively on improving arrival time accuracy using vehicle tracking data, TheTransitClock delivers specialized prediction capabilities that complement either of the other two.

For a complete rider information system, many agencies run OpenTripPlanner for trip planning alongside OneBusAway or TheTransitClock for real-time arrival screens — they serve different parts of the rider experience.

## Why Self-Host Your Transit Data Platform?

Running your own transit data server gives you complete control over the rider experience. When you rely on third-party platforms like Google Maps, you are constrained by their display choices, branding limitations, and data update schedules. A self-hosted solution lets you customize the rider interface, integrate directly with your agency's website and mobile apps, and control exactly when schedule updates go live.

Data sovereignty is another critical factor. Transit agencies collect enormous amounts of operational data — vehicle positions, ridership counts, on-time performance metrics — and keeping that data on your own infrastructure ensures it remains under your control. This matters for privacy compliance, particularly in regions with strict data residency requirements like the European Union.

Cost is the third pillar. While cloud-hosted transit information services charge per API call or per vehicle tracked, self-hosted solutions run on your own hardware with predictable costs. A single server can serve thousands of riders per hour for a fraction of the API billing costs. For smaller agencies with tight budgets, this can mean the difference between offering real-time information or sticking with printed schedules.

For more on serving geospatial data on your own infrastructure, see our guide to [self-hosted routing engines](../2026-04-25-graphhopper-vs-osrm-vs-valhalla-self-hosted-routing-engines-guide-2026/). If you are working with broader geospatial mapping, our [self-hosted mapping servers guide](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/) covers tile serving and geocoding. For maritime navigation systems, check out our [marine navigation platforms comparison](../2026-06-05-self-hosted-marine-navigation-opencpn-signalk-avnav-guide/).


## Deployment Considerations

When deploying a public transit data server, plan for three key operational concerns. First, GTFS data refresh — static schedules change with service updates, so schedule a cron job to download and reload GTFS feeds weekly. Both OneBusAway and OpenTripPlanner require a rebuild (graph build for OTP, bundle build for OBA) after downloading new GTFS data. Second, database sizing — a medium-sized transit agency with 5,000 stops and 200 vehicles generates modest database requirements (under 5 GB), but the graph-building process for OpenTripPlanner can temporarily consume 4-8 GB of RAM for a regional network. Third, public API rate limiting — when exposing your transit API to third-party apps, implement a reverse proxy with rate limiting to prevent a single misbehaving client from overwhelming your server. Nginx or Caddy with simple IP-based rate limiting handles this effectively.

## FAQ

### What is GTFS and why do I need it?

GTFS (General Transit Feed Specification) is the standard format for public transit data — it defines how schedules, routes, stops, and real-time vehicle positions are structured. Every transit data server in this comparison requires GTFS feeds as input. Most transit agencies publish their GTFS data publicly, and you can find feeds for your region at the [Transitland Feed Registry](https://www.transit.land/feeds) or [Mobility Database](https://database.mobilitydata.org/).

### Can I run these on a Raspberry Pi or low-power server?

OpenTripPlanner requires significant memory (2-4 GB minimum) for graph building and routing, so a Raspberry Pi 4 with 8 GB RAM is the bare minimum for a small city. OneBusAway and TheTransitClock are lighter — they can run comfortably on a 2 GB VPS or Raspberry Pi for a small to medium-sized transit system. The database (MySQL or PostgreSQL) is typically the biggest resource consumer across all three.

### Do I need real-time vehicle GPS data to use these?

For OneBusAway and TheTransitClock, real-time data is their primary value proposition — without GTFS Realtime vehicle positions, they fall back to static schedule data. OpenTripPlanner can function with only static GTFS schedules, providing schedule-based trip planning without any real-time feeds. Adding real-time data to OTP improves accuracy but is optional.

### How often should I update GTFS data?

Static GTFS schedules should be updated whenever the transit agency publishes changes — typically weekly or monthly. GTFS Realtime data for vehicle positions updates every 10-30 seconds in production systems. OneBusAway and TheTransitClock are designed to process this streaming data continuously.

### Are there hosting requirements or can these be fully offline?

All three servers can operate entirely offline once you have loaded the GTFS data. This makes them suitable for air-gapped environments, disaster recovery scenarios, or remote locations without reliable internet access. The only external dependency is the initial GTFS data download — after that, the servers run independently.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Public Transit Data Servers: OneBusAway vs OpenTripPlanner vs TheTransitClock",
  "description": "Compare three open-source self-hosted transit data servers — OneBusAway for real-time arrival predictions, OpenTripPlanner for multimodal trip planning, and TheTransitClock for vehicle tracking — with Docker Compose deployment examples.",
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
