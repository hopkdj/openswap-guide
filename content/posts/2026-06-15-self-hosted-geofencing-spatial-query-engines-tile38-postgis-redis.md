---
title: "Self-Hosted Geofencing & Spatial Query Engines: Tile38 vs PostGIS vs Redis Geospatial"
date: "2026-06-15"
tags: ["geofencing", "spatial", "location-services", "geospatial", "gis", "postgis", "redis", "self-hosted"]
draft: false
---

## Why Self-Host Your Location Infrastructure?

Location-aware applications—ride-sharing, delivery tracking, store locators, asset tracking—depend on fast spatial queries. Every "find drivers within 5km" or "show restaurants near me" query requires a spatial database that can efficiently search millions of geographic points. Commercial location APIs charge per request and introduce latency; self-hosting gives you sub-millisecond query performance at fixed infrastructure cost.

Self-hosted spatial databases and geofencing engines let you build real-time location features without vendor lock-in. You control the data, the query patterns, and the indexing strategy. For delivery apps processing 100,000+ location queries per minute during peak hours, self-hosting can reduce costs by 80-90% compared to managed location services.

For address-level geocoding, see our [address verification and geocoding guide](../2026-06-15-self-hosted-address-verification-geocoding-libpostal-pelias-photon-addok/). For broader geospatial database comparisons, our [spatial database comparison](../2026-05-20-self-hosted-geospatial-database-tile38-postgis-redis-guide/) covers Tile38, PostGIS, and Redis. For mapping and visualization, check our [self-hosted mapping servers guide](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/).

## Comparison Table

| Feature | Tile38 | PostGIS | Redis Geospatial |
|---------|--------|---------|------------------|
| **GitHub Stars** | 9,200+ | N/A (PostgreSQL extension) | N/A (Redis module) |
| **Primary Use Case** | Real-time geofencing & spatial pub/sub | Full spatial SQL database | Lightweight spatial indexing |
| **Query Type** | Geofencing, nearby, intersects | Full OGC spatial SQL | Radius queries, geo-hash |
| **Real-time Updates** | Yes (native pub/sub) | Via LISTEN/NOTIFY | Via Pub/Sub |
| **Geofence Webhooks** | Yes (built-in) | No (needs application logic) | No (needs application logic) |
| **Spatial Index** | R-tree (in-memory) | GiST, SP-GiST, BRIN | Geohash + Sorted Set |
| **Memory Model** | In-memory (persisted to disk) | Disk-based (with memory cache) | In-memory (persisted to disk) |
| **Precision** | Meter-level | Sub-meter | Meter-level |
| **Complex Spatial Ops** | Basic (within, nearby, intersects) | Full (buffer, union, intersects, ST_DWithin) | Basic (GEORADIUS, GEOSEARCH) |
| **Docker Support** | Yes | Yes | Yes |
| **Scaling** | Single-node (AOF replication) | Read replicas, sharding | Cluster mode |
| **Best For** | Real-time geofencing, fleet tracking | Spatial analytics, GIS applications | Simple radius queries, caching |

## Tool Deep-Dive

### Tile38 — Real-Time Geofencing Engine

Tile38 is a purpose-built, in-memory geospatial database designed for real-time geofencing. It supports WebSocket connections for live location updates and built-in webhooks that fire when objects enter or leave geographic regions.

```yaml
# docker-compose.yml for Tile38
version: '3'
services:
  tile38:
    image: tile38/tile38:latest
    ports:
      - "9851:9851"
    volumes:
      - tile38_data:/data
    command: tile38-server /data

volumes:
  tile38_data:
```

```bash
# Set moving objects with real-time updates
tile38-cli
> SET fleet driver:1 POINT 40.7484 -73.9857
> SET fleet driver:2 POINT 40.7589 -73.9851
> SET fleet driver:3 POINT 40.7128 -74.0060

# Create a geofence around Times Square (500m radius)
> SETHOOK delivery-zone http://webhook.example.com/delivery NEARBY fleet FENCE POINT 40.7580 -73.9855 500

# Webhook fires when driver:1 enters the zone
# POST http://webhook.example.com/delivery
# {"hook":"delivery-zone","id":"driver:1","detect":"inside","key":"fleet",...}

# Find all drivers within 3km of a location
> NEARBY fleet POINT 40.7580 -73.9855 3000
```

Tile38's killer feature is its native geofencing pub/sub system. Set up a fence once, and Tile38 automatically notifies your application whenever objects cross the boundary. This eliminates the need for periodic polling—critical for fleet tracking applications where you need real-time zone entry/exit events.

### PostGIS — Full Spatial SQL Powerhouse

PostGIS extends PostgreSQL with comprehensive spatial capabilities following OGC standards. It's the go-to choice when you need both spatial queries and standard relational data in the same database.

```yaml
# docker-compose.yml for PostGIS
version: '3'
services:
  postgis:
    image: postgis/postgis:15-3.4
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: geospatial
      POSTGRES_USER: geo
      POSTGRES_PASSWORD: changeme
    volumes:
      - pg_data:/var/lib/postgresql/data
    command: >
      -c shared_buffers=1GB
      -c effective_cache_size=3GB
      -c maintenance_work_mem=256MB
      -c wal_buffers=16MB

volumes:
  pg_data:
```

```sql
-- Enable PostGIS
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

-- Create a spatial table for store locations
CREATE TABLE stores (
    id SERIAL PRIMARY KEY,
    name TEXT,
    location GEOGRAPHY(POINT, 4326)
);

-- Create spatial index
CREATE INDEX stores_location_idx ON stores USING GIST (location);

-- Insert store locations
INSERT INTO stores (name, location) VALUES
    ('Downtown Store', ST_SetSRID(ST_MakePoint(-73.9857, 40.7484), 4326)),
    ('Midtown Store', ST_SetSRID(ST_MakePoint(-73.9851, 40.7589), 4326)),
    ('Upper East Store', ST_SetSRID(ST_MakePoint(-73.9554, 40.7749), 4326));

-- Find all stores within 2km of a user location
SELECT name, ST_Distance(location, 
    ST_SetSRID(ST_MakePoint(-73.9855, 40.7580), 4326)
) AS distance_meters
FROM stores
WHERE ST_DWithin(location,
    ST_SetSRID(ST_MakePoint(-73.9855, 40.7580), 4326),
    2000
)
ORDER BY distance_meters;

-- Create a custom geofence polygon
SELECT name
FROM stores
WHERE ST_Within(location,
    ST_GeomFromText('POLYGON((-74.0 40.75, -73.97 40.75, -73.97 40.77, -74.0 40.77, -74.0 40.75))', 4326)
);
```

PostGIS excels at complex spatial analytics: catchment area analysis, drive-time isochrones, demographic clustering. Its SQL interface integrates naturally with existing application stacks using ORMs or raw SQL.

### Redis Geospatial — Lightweight Spatial Indexing

Redis includes built-in geospatial commands using sorted sets with geohash encoding. It's ideal for caching geocoding results, powering simple "near me" queries, or adding location awareness to existing Redis-based applications.

```yaml
# docker-compose.yml for Redis with geospatial
version: '3'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

```bash
# Add locations to a geospatial index
redis-cli
> GEOADD drivers -73.9857 40.7484 "driver:1"
> GEOADD drivers -73.9851 40.7589 "driver:2"
> GEOADD drivers -74.0060 40.7128 "driver:3"

# Find drivers within 3km
> GEORADIUS drivers -73.9855 40.7580 3 km WITHDIST WITHCOORD
1) 1) "driver:2"
   2) "0.1035"
   3) 1) "-73.98509997129440308"
      2) "40.75889866982482244"
2) 1) "driver:1"
   2) "1.0670"
   3) 1) "-73.98570001125335693"
      2) "40.74839866341054442"

# Calculate distance between two points
> GEODIST drivers "driver:1" "driver:2" km
"1.1733"
```

Redis geospatial is intentionally simple—it supports radius queries and distance calculations but not polygon intersections or complex spatial predicates. Use it when you need sub-millisecond spatial lookups and already run Redis in your stack.

## Deployment Architecture for Location Services

A production location stack typically layers these tools:

```
┌──────────────────────┐
│   Mobile App / Web   │
└──────────┬───────────┘
           │ Location updates (WebSocket)
┌──────────▼───────────┐
│       Tile38         │ ← Real-time geofencing & pub/sub
└──────────┬───────────┘
           │ Webhook triggers
┌──────────▼───────────┐
│   Application Logic  │ ← Business rules, notifications
└──────────┬───────────┘
           │ Persisted location data
┌──────────▼───────────┐
│      PostGIS         │ ← Spatial analytics, historical queries
└──────────┬───────────┘
           │ Cached geocoding results
┌──────────▼───────────┐
│   Redis Geospatial    │ ← Hot cache for nearby queries
└──────────────────────┘
```

```python
# Integration example: Fleet tracking with Tile38 + PostGIS
import asyncio
import aiohttp
import asyncpg

async def handle_driver_update(driver_id, lat, lon):
    # 1. Update real-time position in Tile38 (WebSocket)
    async with aiohttp.ClientSession() as session:
        await session.post(f"http://tile38:9851/SET fleet {driver_id} POINT {lat} {lon}")
    
    # 2. Persist to PostGIS for historical analysis
    conn = await asyncpg.connect("postgresql://geo:pass@postgis/geospatial")
    await conn.execute("""
        INSERT INTO driver_positions (driver_id, location, timestamp)
        VALUES ($1, ST_SetSRID(ST_MakePoint($2, $3), 4326), NOW())
    """, driver_id, lon, lat)
    await conn.close()

# Tile38 webhook handler (called when driver enters/exits geofence)
async def handle_geofence_event(hook, driver_id, detect):
    if detect == "inside":
        # Driver entered delivery zone - trigger assignment logic
        await assign_delivery(driver_id)
    elif detect == "outside":
        # Driver left zone - update ETA
        await update_delivery_status(driver_id, "en_route")
```

## Choosing the Right Tool

**Choose Tile38** when real-time geofencing is your core requirement. Its native pub/sub and webhook system eliminates polling overhead and provides sub-millisecond fence detection. Ideal for fleet tracking, delivery zone management, and proximity marketing.

**Choose PostGIS** when you need complex spatial analytics alongside your business data. Join spatial queries with customer tables, run catchment area analysis, or build GIS dashboards. The trade-off is slower real-time performance compared to Tile38.

**Choose Redis Geospatial** as a lightweight spatial cache layer. It's perfect for "restaurants near me" queries where you've already geocoded addresses and need fast radius lookups. Don't use it for complex spatial operations.

## FAQ

### What's the difference between geocoding and geofencing?

Geocoding converts addresses to coordinates. Geofencing monitors whether objects (drivers, devices, assets) are inside or outside geographic boundaries. Tile38 handles geofencing natively, while PostGIS can implement it through spatial queries and application-level polling.

### How many objects can Tile38 handle?

Tile38 can manage millions of moving objects on a single node with 8-16GB RAM. Each object is a small key-value pair with coordinates. For fleet tracking at scale, one Tile38 instance comfortably handles 100,000+ active drivers updating positions every few seconds.

### Can I combine PostGIS and Tile38?

Yes—this is a common production pattern. Use Tile38 for real-time position tracking and geofencing (WebSocket/webhook-based), and sync position updates to PostGIS for historical analysis, dashboards, and complex spatial queries. Tile38 handles the "now," PostGIS handles the "what happened."

### Do I need PostGIS if I already use PostgreSQL?

PostGIS is an extension to PostgreSQL that adds spatial types and functions. If you already run PostgreSQL, enabling PostGIS adds spatial capabilities with zero additional infrastructure. It's the simplest path to spatial SQL for existing PostgreSQL deployments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Geofencing & Spatial Query Engines: Tile38 vs PostGIS vs Redis Geospatial",
  "description": "Compare self-hosted geofencing and spatial query engines: Tile38 (real-time geofencing), PostGIS (full spatial SQL), and Redis Geospatial (lightweight spatial indexing). Docker Compose deployment, webhook integration, and fleet tracking architecture.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
