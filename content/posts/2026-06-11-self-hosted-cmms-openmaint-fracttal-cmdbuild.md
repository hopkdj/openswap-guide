---
title: "Self-Hosted Maintenance Management (CMMS): OpenMAINT vs Fracttal vs CMDBuild"
date: "2026-06-11"
tags: ["cmms", "maintenance-management", "facility-management", "open-source", "self-hosted"]
draft: false
---

Computerized Maintenance Management Systems (CMMS) help organizations track equipment, schedule preventive maintenance, manage work orders, and optimize asset lifecycles. While enterprise solutions like IBM Maximo dominate the market, open-source self-hosted alternatives provide compelling options for facilities teams on a budget. This guide compares three leading open-source CMMS platforms.

## Comparison at a Glance

| Feature | OpenMAINT | Fracttal | CMDBuild |
|---------|-----------|----------|----------|
| **Type** | Facility CMMS | Cloud CMMS | ITIL CMDB + Maintenance |
| **Language** | Java | Web-based | Java |
| **Database** | PostgreSQL | Proprietary | PostgreSQL |
| **License** | AGPLv3 | Proprietary | AGPLv3 |
| **Work Orders** | ✅ Full | ✅ Full | ✅ Full |
| **Preventive Maintenance** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Asset Registry** | ✅ Yes | ✅ Yes | ✅ Yes (CMDB) |
| **Mobile App** | ✅ Android | ✅ Native | ✅ Web responsive |
| **Docker Support** | ✅ Yes | ❌ Cloud only | ✅ Yes |
| **BIM Integration** | ✅ Yes | ❌ No | ✅ BIM viewer |
| **Inventory/Spare Parts** | ✅ Yes | ✅ Yes | ✅ Yes |

## OpenMAINT: Full-Featured Facility CMMS

OpenMAINT is an open-source CMMS for managing movable assets, facilities, and related maintenance activities. Built on the CMDBuild framework, it provides a comprehensive solution for facility managers.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  openmaint-db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=openmaint
      - POSTGRES_USER=openmaint
      - POSTGRES_PASSWORD=openmaint
    volumes:
      - om_db:/var/lib/postgresql/data
    restart: unless-stopped

  openmaint-app:
    image: itmicus/openmaint:latest
    ports:
      - "8080:8080"
    environment:
      - CMDBUILD_DATABASE_URL=jdbc:postgresql://openmaint-db:5432/openmaint
      - CMDBUILD_DATABASE_USER=openmaint
      - CMDBUILD_DATABASE_PASSWORD=openmaint
    depends_on:
      - openmaint-db
    restart: unless-stopped

volumes:
  om_db:
```

## Fracttal: Modern Maintenance Platform

Fracttal offers a modern web-based CMMS with IoT sensor integration for predictive maintenance. While its core is cloud-based, the self-hosted enterprise edition provides on-premises deployment with real-time equipment monitoring.

### Self-Hosted Configuration

```yaml
version: "3.8"
services:
  fracttal-api:
    image: fracttal/fracttal-enterprise:latest
    ports:
      - "3000:3000"
    environment:
      - DB_HOST=postgres
      - DB_NAME=fracttal
      - DB_USER=fracttal
      - DB_PASSWORD=secure-password
      - REDIS_URL=redis://redis:6379
      - IOT_MQTT_BROKER=mqtt://mosquitto:1883
    depends_on:
      - postgres
      - redis
      - mosquitto
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=fracttal
      - POSTGRES_USER=fracttal
      - POSTGRES_PASSWORD=secure-password
    volumes:
      - frac_db:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    restart: unless-stopped

volumes:
  frac_db:
```

## CMDBuild: ITIL CMDB with Maintenance Module

CMDBuild is an open-source configuration management database that includes robust maintenance management capabilities. It follows ITIL best practices and includes workflow automation for maintenance processes.

```yaml
version: "3.8"
services:
  cmdbuild-db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=cmdbuild
      - POSTGRES_USER=cmdbuild
      - POSTGRES_PASSWORD=cmdbuild
    volumes:
      - cmdb_db:/var/lib/postgresql/data
    restart: unless-stopped

  cmdbuild-app:
    image: itmicus/cmdbuild:latest
    ports:
      - "8080:8080"
    environment:
      - CMDBUILD_DATABASE_URL=jdbc:postgresql://cmdbuild-db:5432/cmdbuild
      - CMDBUILD_DATABASE_USER=cmdbuild
      - CMDBUILD_DATABASE_PASSWORD=cmdbuild
    depends_on:
      - cmdbuild-db
    restart: unless-stopped

volumes:
  cmdb_db:
```

## Choosing the Right CMMS

- **Choose OpenMAINT** for comprehensive facility maintenance management with BIM integration, space management, and preventive maintenance scheduling for large facilities.
- **Choose Fracttal** for IoT-enabled predictive maintenance with real-time sensor monitoring and a modern, user-friendly interface optimized for mobile technicians.
- **Choose CMDBuild** if you need ITIL-aligned asset and configuration management alongside maintenance workflows, particularly in IT-heavy environments.

## Why Self-Host Your CMMS?

Self-hosting your maintenance management system ensures sensitive facility data — equipment locations, maintenance histories, and vendor contracts — stays within your infrastructure. Cloud CMMS solutions charge per-asset or per-technician fees that scale rapidly with your operation. Open-source self-hosted alternatives cap costs at infrastructure spending while giving you complete control over data retention policies and system customization.

For related operational tools, see our [self-hosted IT asset management guide](../2026-04-28-snipe-it-vs-grocy-vs-inventree-self-hosted-asset-management-guide/) and [inventory management comparison](../snipe-it-vs-grocy-vs-partkeepr-self-hosted-inventory-management/).

## FAQ

### What's the difference between CMMS and EAM?

CMMS focuses on maintenance operations (work orders, preventive maintenance, spare parts). Enterprise Asset Management (EAM) covers the full asset lifecycle including procurement, depreciation, and disposal. OpenMAINT and Fracttal are CMMS-focused; CMDBuild leans toward EAM with its ITIL CMDB foundation.

### Can these systems integrate with building automation (BMS/BACnet)?

OpenMAINT and Fracttal support integration with BMS systems through REST APIs and MQTT for IoT sensor data. CMDBuild requires custom development for BMS integration but provides a flexible data model that can accommodate building automation data.

### How do mobile technicians access work orders?

OpenMAINT provides an Android app for offline work order management. Fracttal offers native iOS and Android apps with real-time synchronization. CMDBuild uses a responsive web interface that works on mobile browsers but lacks offline capabilities.

### What hardware do I need?

A basic CMMS deployment needs 4GB RAM and 2 CPU cores on a Linux server. For facilities with 1,000+ assets and 50+ technicians, increase to 8GB RAM and 4 CPU cores. PostgreSQL databases benefit significantly from SSD storage.

### How does preventive maintenance scheduling work?

All three platforms support calendar-based and meter-based preventive maintenance triggers. OpenMAINT offers the most sophisticated scheduling with seasonal adjustments and resource leveling. Fracttal adds IoT-based condition monitoring for predictive triggers. CMDBuild uses workflow-based scheduling with ITIL change management integration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Maintenance Management (CMMS): OpenMAINT vs Fracttal vs CMDBuild",
  "description": "Compare open-source self-hosted CMMS platforms for facility maintenance management with Docker Compose deployment guides, work order tracking, and preventive maintenance scheduling.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
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
