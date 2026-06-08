---
title: "Self-Hosted GIS Web Map Viewers: QGIS Server vs Mapbender vs Lizmap"
date: "2026-06-09"
tags: ["gis", "geospatial", "web-mapping", "open-source-gis", "map-viewer", "self-hosted"]
draft: false
---

## Introduction

Geographic Information Systems (GIS) have moved far beyond desktop-only workflows. Modern organizations need web-based map viewers that let teams, stakeholders, and the public explore spatial data without installing specialized software. Whether you manage municipal infrastructure, environmental monitoring data, or field survey results, a self-hosted web map viewer turns raw geospatial data into an accessible, interactive experience.

In this guide, we compare three open-source GIS web map viewers that you can self-host: **QGIS Server**, **Mapbender**, and **Lizmap**. Each takes a different architectural approach to serving maps over the web — from protocol-level WMS/WFS rendering to full-featured web mapping frameworks to QGIS-project-native publishing.

## QGIS Server: Protocol-Native Map Rendering

QGIS Server is the web-serving component of the QGIS project, one of the world's most popular open-source GIS platforms with over 13,800 GitHub stars. It provides OGC-compliant Web Map Service (WMS), Web Feature Service (WFS), and Web Coverage Service (WCS) endpoints directly from QGIS project files.

**Key strengths:**
- Native OGC protocol support (WMS 1.3, WFS 1.1/2.0, WCS)
- Renders directly from `.qgs` / `.qgz` project files — no conversion needed
- Full QGIS symbology, labeling, and print composer support
- WMTS (tile caching) for high-performance tile delivery
- Extensible via Python server plugins (filtering, access control, custom outputs)

**Deployment with Docker:**

```yaml
# docker-compose.yml for QGIS Server with Nginx
version: "3.8"
services:
  qgis-server:
    image: camptocamp/qgis-server:latest
    environment:
      - QGIS_PROJECT_FILE=/data/project.qgs
      - QGIS_SERVER_LOG_LEVEL=0
      - PGSERVICEFILE=/data/pg_service.conf
    volumes:
      - ./data:/data:ro
      - ./logs:/var/log/qgis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - qgis-server
```

**Nginx reverse proxy configuration:**

```nginx
server {
    listen 80;
    server_name maps.example.com;

    location /qgis/ {
        proxy_pass http://qgis-server:80/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

QGIS Server excels when you already use QGIS Desktop for map authoring and need a direct, no-friction path from project file to web service. It is purely a backend rendering engine — you pair it with a frontend map library (Leaflet, OpenLayers) for the user interface.

## Mapbender: Full-Stack Web Mapping Framework

Mapbender is a comprehensive web mapping framework built in PHP that provides both backend administration and a JavaScript-based frontend viewer. With 104 GitHub stars and active development through 2026, it targets organizations that need a complete, out-of-the-box web GIS portal.

**Key strengths:**
- Built-in user and group management with granular access control
- Visual map application designer — configure maps through a web UI, no coding required
- Catalog service for searching and discovering OGC services
- Integrated WMS, WFS, and WMTS client support
- Digitizing and redlining tools for collaborative map editing
- Multi-language interface (German, English, Italian, Spanish, Russian)

**Deployment with Docker:**

```yaml
# docker-compose.yml for Mapbender
version: "3.8"
services:
  mapbender:
    image: mapbender/mapbender-starter:latest
    ports:
      - "8080:80"
    environment:
      - DATABASE_URL=postgresql://mapbender:password@db:5432/mapbender
      - APP_SECRET=change-this-to-a-random-string
    volumes:
      - ./uploads:/var/www/mapbender/uploads
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgis/postgis:16-3.4
    environment:
      - POSTGRES_DB=mapbender
      - POSTGRES_USER=mapbender
      - POSTGRES_PASSWORD=password
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    restart: unless-stopped
```

Mapbender's killer feature is the **application designer** — admin users can drag-and-drop to create custom map interfaces with layer trees, legend panels, measurement tools, and search capabilities. This makes it ideal for city governments, utility companies, and regional planning agencies that need non-developers to build map applications.

## Lizmap: QGIS-Project-to-Web Publishing

Lizmap bridges QGIS Desktop and web publishing with an elegant approach: upload your QGIS project file, and Lizmap automatically generates a responsive web map interface. With 328 GitHub stars and strong European adoption (particularly in French local government), it has become the go-to solution for organizations that want to publish QGIS projects as web applications without writing JavaScript.

**Key strengths:**
- Direct QGIS project publishing — QGIS Server renders; Lizmap provides the web UI layer
- Responsive, mobile-friendly map interface out of the box
- Form-based attribute editing via WFS-T
- Layer filtering by user, group, or spatial extent
- Integrated print/atlas generation using QGIS layouts
- Custom popup configurations using QGIS expression syntax
- Plugin ecosystem for extensions (address search, cadastre, dataviz)

**Deployment with the official docker-compose:**

```yaml
# docker-compose.yml for Lizmap
version: "3.8"
services:
  lizmap:
    image: 3liz/lizmap-web-client:latest
    ports:
      - "8080:80"
    environment:
      - LIZMAP_WMSSERVERURL=http://qgis-server/cgi-bin/qgis_mapserv.fcgi
      - LIZMAP_CACHEREDIS_HOST=redis
      - LIZMAP_CACHESTORAGETYPE=redis
    volumes:
      - ./projects:/srv/projects
      - ./lizmap-config:/www/lizmap/var/config
      - ./lizmap-themes:/www/lizmap/www/themes
    depends_on:
      - qgis-server
      - redis
    restart: unless-stopped

  qgis-server:
    image: camptocamp/qgis-server:latest
    volumes:
      - ./projects:/srv/projects:ro
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
```

Lizmap's sweet spot is QGIS-heavy organizations that already invest in QGIS project authoring and want the fastest path from desktop project to production web map. The form-based editing capabilities make it particularly strong for field data collection workflows where mobile users need to update attributes in the field.

## Comparison Table

| Feature | QGIS Server | Mapbender | Lizmap |
|---------|------------|-----------|--------|
| **Architecture** | OGC protocol rendering engine | Full-stack PHP framework | QGIS project publishing platform |
| **Frontend** | None (API only — pair with OpenLayers/Leaflet) | Built-in JavaScript viewer + admin UI | Built-in responsive web UI |
| **OGC Standards** | WMS 1.3, WFS 1.1/2.0, WCS, WMTS | WMS/WFS client + WMS server (via Mapbender) | WMS/WFS (via QGIS Server) |
| **User Management** | Via proxy/server plugins | Built-in (groups, roles, ACLs) | Via Lizmap admin panel |
| **Map Authoring** | QGIS Desktop → project file | Web-based application designer | QGIS Desktop → upload project |
| **Editing** | WFS-T (configured per layer) | Digitizing + redlining tools | Form-based WFS-T editing |
| **Mobile Support** | Depends on frontend choice | Responsive interface | Native responsive design |
| **GitHub Stars** | 13,891 (QGIS project) | 104 | 328 |
| **Best For** | Backend rendering for custom frontends | Complete web GIS portal with admin tools | QGIS-centric organizations |
| **Language** | C++/Python | PHP/JavaScript | PHP/JavaScript |

## Choosing the Right GIS Web Viewer

Your choice depends on your organization's GIS maturity and workflow:

**Choose QGIS Server if:**
- You already have a custom web frontend built with OpenLayers, Leaflet, or MapLibre
- You need pure OGC protocol compliance for interoperability with third-party clients
- Your team has Python/plugin development skills for extending server behavior

**Choose Mapbender if:**
- You need non-developers to create and manage web map applications
- You want a complete portal with user management, catalogs, and access control built in
- Your organization serves multiple departments with different map requirements

**Choose Lizmap if:**
- QGIS Desktop is your organization's primary GIS authoring tool
- You want the fastest QGIS-project-to-web publishing workflow
- Field data collection and mobile editing are key requirements

## Security Hardening for Public Map Servers

When exposing GIS web viewers to the internet:

1. **Rate-limit OGC requests** to prevent denial-of-service attacks on WMS GetMap endpoints — use Nginx `limit_req_zone` with token bucket configuration
2. **Restrict WFS-T to authenticated users only** — unauthenticated write access can corrupt spatial data
3. **Use HTTPS exclusively** — browsers block geolocation APIs on HTTP origins
4. **Set appropriate CORS headers** for cross-origin tile requests from separate frontend domains
5. **Monitor tile cache hit ratios** — low ratios indicate configuration issues or attack patterns
6. **Restrict QGIS Server project file access** — project files contain database credentials

## Why Self-Host Your GIS Web Viewer?

Running your own GIS web viewer gives you complete control over your spatial data infrastructure. Cloud-based mapping services charge by tile request, map load, or stored feature — costs that scale unpredictably as usage grows. Self-hosting eliminates these variable costs while keeping sensitive spatial data (property boundaries, infrastructure locations, environmental monitoring sites) within your network perimeter.

Many organizations — particularly in government, utilities, and environmental science — have regulatory requirements that prohibit storing certain spatial datasets on third-party servers. Self-hosted GIS viewers satisfy these compliance requirements without sacrificing functionality. Modern container-based deployment means you can spin up a QGIS Server, Mapbender, or Lizmap instance in minutes with Docker Compose, matching the deployment speed of SaaS alternatives while retaining full data sovereignty.

For broader geospatial infrastructure, see our [self-hosted mapping server guide](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/). If you need high-performance tile delivery, check out our [vector tile server comparison](../2026-05-19-self-hosted-vector-tile-servers-tegola-vs-tileserver-gl-vs-martin-guide/). For IP geolocation data that enriches your maps, our [GeoIP database guide](../2026-04-23-self-hosted-geoip-databases-maxmind-ip2location-dbip-guide-2026/) covers the major providers.

## FAQ

### What's the difference between a GIS server and a GIS web viewer?

A GIS server (like GeoServer or QGIS Server) renders spatial data as standardized OGC web services (WMS, WFS). A GIS web viewer provides the browser-based user interface that consumes those services — displaying the rendered map tiles, handling user interactions like pan/zoom/click, and providing tools for searching, measuring, and editing. QGIS Server is purely a backend; Mapbender and Lizmap are viewers that sit on top of backends.

### Can I use QGIS Server without QGIS Desktop?

Technically yes — you can prepare QGIS project files (`.qgs`/`.qgz`) programmatically or use pre-configured projects. However, QGIS Desktop is the primary authoring tool for creating project files with symbology, labeling, and layer configurations. Without it, you would need to construct QGIS project XML manually, which is impractical for most users. Lizmap leverages this by making the QGIS Desktop → Web Server pipeline seamless.

### How do these compare to GeoServer?

GeoServer is a Java-based OGC server that publishes data from various sources (PostGIS, Shapefiles, GeoTIFF) as WMS/WFS/WCS. QGIS Server serves a similar backend role but renders from QGIS project files rather than managing data stores directly. Mapbender and Lizmap are web viewers that can consume services from either QGIS Server or GeoServer — they're not competitors to GeoServer, they complement it by providing the user-facing web interface.

### What hardware do I need to self-host a GIS web viewer?

For small to medium deployments (up to 50 concurrent users), a server with 4 GB RAM and 2 CPU cores is sufficient for all three options. The primary resource consumers are: tile rendering (CPU-bound, mitigated by tile caching), spatial database queries (benefit from SSD storage), and concurrent WMS requests. For production, allocate at least 8 GB RAM and enable WMTS tile caching (QGIS Server) or use a dedicated tile cache like MapProxy in front of your viewer.

### Can I restrict which layers different users see?

Yes, all three support access control at some level. Mapbender has the most comprehensive built-in system with user groups, role-based access, and per-application permission sets. Lizmap provides layer-level filtering by user group and spatial extent through its admin panel. QGIS Server supports access control through server plugins or by placing an authenticating reverse proxy (Nginx with auth_request, OAuth2 Proxy) in front of the WMS/WFS endpoints.

### Do these integrate with PostGIS databases?

Absolutely. All three connect to PostGIS as a primary spatial data source. QGIS Server reads layers defined in the QGIS project file — those layers can point to PostGIS connections. Mapbender consumes WMS/WFS services that may be backed by PostGIS through GeoServer or QGIS Server. Lizmap inherits whatever data sources are configured in the QGIS project file, including native PostGIS connections. For best performance, enable PostgreSQL connection pooling and use materialized views for complex spatial queries.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted GIS Web Map Viewers: QGIS Server vs Mapbender vs Lizmap",
  "description": "Compare three open-source self-hosted GIS web map viewers — QGIS Server for OGC protocol rendering, Mapbender for full-stack web mapping framework, and Lizmap for QGIS-project-to-web publishing. Includes Docker Compose deployment configs and comparison table.",
  "datePublished": "2026-06-09",
  "dateModified": "2026-06-09",
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
