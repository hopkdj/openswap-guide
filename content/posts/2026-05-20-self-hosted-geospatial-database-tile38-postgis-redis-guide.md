---
title: "Self-Hosted Geo-Spatial Database — Tile38 vs PostGIS vs Redis Geo"
date: "2026-05-20"
tags: ["database", "geospatial", "location", "mapping", "self-hosted"]
draft: false
---

Location-aware applications — from fleet tracking and geofencing to proximity search and mapping — require databases that understand geographic coordinates, spatial relationships, and real-time position updates. Three open-source solutions serve this need: **Tile38**, **PostGIS**, and **Redis Geo**. Each brings a different philosophy to geospatial data management.

This guide compares all three across query capabilities, real-time features, Docker deployment, and integration patterns to help you choose the right geospatial database for your self-hosted infrastructure.

## Understanding Geospatial Database Requirements

Geospatial applications have unique requirements that standard databases struggle with:

- **Proximity queries**: Find all points within N meters of a location
- **Geofencing**: Detect when objects enter or leave defined boundaries
- **Real-time tracking**: Process continuous position updates at high throughput
- **Spatial indexing**: Efficiently store and query complex polygon data
- **Distance calculations**: Compute distances across the Earth's curved surface

Not all geospatial databases handle these equally well. Tile38 was built from the ground up for real-time geospatial operations. PostGIS extends PostgreSQL with comprehensive spatial analysis capabilities. Redis Geo adds basic geospatial operations to Redis's in-memory data store.

## Tool Comparison

| Feature | Tile38 | PostGIS | Redis Geo |
|---|---|---|---|
| GitHub Stars | 9,632 | 2,123 | Part of Redis (68,000+) |
| Language | Go | C | C |
| Storage Model | In-memory + disk | Disk (PostgreSQL) | In-memory (Redis) |
| Query Types | Proximity, geofence, radius, polygon | Full spatial SQL (OGC) | Radius only |
| Real-Time Webhooks | Yes (native) | Via triggers/extensions | Via Redis Streams |
| Geofencing | Native (with alerts) | Via ST_Contains/ST_Within | Manual implementation |
| Coordinate Systems | WGS84 (EPSG:4326) | Any (100+ projections) | WGS84 only |
| Complex Geometries | Polygon, MultiPolygon | Full OGC standard | Points only |
| Clustering | Built-in | Via PostgreSQL replication | Via Redis Cluster |
| Docker Support | Official image | Official image | Official image |
| License | MIT | GPL v2 | BSD 3-Clause |
| Best For | Real-time tracking | Complex spatial analysis | Simple proximity lookups |

## Tile38: The Real-Time Geospatial Engine

Tile38 is a real-time geospatial database and geofencing server built in Go. It was designed specifically for location-based services that need to track moving objects and detect spatial events.

**Strengths:**
- Native real-time geofencing with webhook notifications
- Excellent for fleet tracking, IoT location monitoring, and proximity alerts
- Built-in pub/sub for live position updates
- Supports points, polygons, and bounding boxes
- Lightweight — single binary, easy to deploy

**Weaknesses:**
- Limited to WGS84 coordinate system
- No complex spatial analysis (no spatial joins, buffers, etc.)
- Smaller community compared to PostGIS
- Not suitable for heavy analytical workloads

**Installation:**

```bash
# Download binary
wget https://github.com/tidwall/tile38/releases/latest/download/tile38-server-linux-amd64.tar.gz
tar xzf tile38-server-linux-amd64.tar.gz
./tile38-server

# Or via package manager
go install github.com/tidwall/tile38/cmd/tile38-server@latest
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  tile38:
    image: tile38/tile38:latest
    container_name: tile38
    ports:
      - "9851:9851"
    volumes:
      - tile38-data:/var/lib/tile38
    command: >
      tile38-server
      -d /var/lib/tile38
      -listen :9851
    restart: unless-stopped

  tile38-cli:
    image: tile38/tile38:latest
    container_name: tile38-cli
    depends_on:
      - tile38
    command: tile38-cli -h tile38 -p 9851
    stdin_open: true
    tty: true

volumes:
  tile38-data:
```

**Sample geofence query:**

```
# Set a delivery zone polygon
SETPROP delivery_zone OBJECT '{
  "type": "Polygon",
  "coordinates": [[
    [-122.4194, 37.7749],
    [-122.4094, 37.7749],
    [-122.4094, 37.7849],
    [-122.4194, 37.7849],
    [-122.4194, 37.7749]
  ]]
}'

# Set up a webhook for geofence alerts
SETCHAN delivery_alerts NEARBY delivery_zone OBJECT
  WEBHOOK https://your-app.example.com/alerts

# Track a vehicle
SET vehicle_1 POINT 37.7749 -122.4194
```

## PostGIS: The Full-Featured Spatial Extension

PostGIS extends PostgreSQL with comprehensive spatial data types and functions following OGC (Open Geospatial Consortium) standards. It is the most powerful open-source geospatial solution available.

**Strengths:**
- Full OGC spatial SQL compliance — hundreds of spatial functions
- Supports 100+ coordinate reference systems (CRS/projections)
- Complex spatial analysis: joins, buffers, intersections, topology
- Mature ecosystem with QGIS, GDAL, and MapServer integration
- ACID transactions and full PostgreSQL reliability
- Handles both vector and raster spatial data

**Weaknesses:**
- Heavier resource footprint than Tile38 or Redis Geo
- Steeper learning curve — requires PostgreSQL and SQL knowledge
- Not designed for high-frequency real-time tracking
- Complex setup for spatial indexing optimization

**Installation:**

```bash
# Ubuntu/Debian
apt-get update && apt-get install -y postgresql-16-postgis-3

# Enable PostGIS in a database
psql -d mydb -c "CREATE EXTENSION postgis;"
psql -d mydb -c "CREATE EXTENSION postgis_topology;"
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  postgis:
    image: postgis/postgis:16-3.4
    container_name: postgis
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: geodb
      POSTGRES_USER: geo_admin
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgis-data:/var/lib/postgresql/data
      - ./init-postgis.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=512MB
      -c effective_cache_size=1536MB
    restart: unless-stopped

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    ports:
      - "5050:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin_password
    depends_on:
      - postgis
    restart: unless-stopped

volumes:
  postgis-data:
```

**Sample spatial query:**

```sql
-- Find all restaurants within 500m of a point
SELECT name, address,
  ST_Distance(
    location::geography,
    ST_SetSRID(ST_MakePoint(-122.4194, 37.7749), 4326)::geography
  ) AS distance_meters
FROM restaurants
WHERE ST_DWithin(
  location::geography,
  ST_SetSRID(ST_MakePoint(-122.4194, 37.7749), 4326)::geography,
  500
)
ORDER BY distance_meters;

-- Spatial join: count parks per city district
SELECT district.name, COUNT(parks.id) AS park_count
FROM districts
LEFT JOIN parks ON ST_Contains(districts.boundary, parks.location)
GROUP BY district.name;
```

## Redis Geo: The Simple In-Memory Option

Redis Geo adds geospatial operations to Redis using sorted sets (ZSET) with geohash encoding. It provides basic proximity search but is limited compared to dedicated geospatial databases.

**Strengths:**
- Extremely fast — in-memory operations with microsecond latency
- Simple API — just 5 commands (GEOADD, GEOPOS, GEODIST, GEORADIUS, GEOSEARCH)
- Integrates seamlessly with existing Redis infrastructure
- Supports Redis Cluster for horizontal scaling
- Minimal operational overhead

**Weaknesses:**
- Only supports points — no polygons, lines, or complex geometries
- Limited to radius/proximity queries — no spatial joins or analysis
- WGS84 only — no coordinate system transformations
- Memory-constrained — large datasets require significant RAM
- No native geofencing or webhook support

**Installation:**

```bash
# Redis Geo is included in Redis 3.2+
apt-get update && apt-get install -y redis-server

# Verify Geo commands are available
redis-cli GEOADD test 37.7749 -122.4194 "San Francisco"
redis-cli GEODIST test "San Francisco" "Los Angeles" km
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  redis-geo:
    image: redis/redis-stack-server:latest
    container_name: redis-geo
    ports:
      - "6379:6379"
    volumes:
      - redis-geo-data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
    restart: unless-stopped

volumes:
  redis-geo-data:
```

**Sample proximity query:**

```
# Add locations
GEOADD locations -122.4194 37.7749 "San Francisco"
GEOADD locations -118.2437 34.0522 "Los Angeles"
GEOADD locations -121.8863 36.6002 "Monterey"

# Find all within 200km of a point
GEORADIUS locations -122.4194 37.7749 200 km WITHDIST WITHCOORD

# Using GEOSEARCH (Redis 6.2+)
GEOSEARCH locations FROMLONLAT -122.4194 37.7749 BYRADIUS 200 km
  WITHCOORD WITHDIST COUNT 10
```

## Architecture Comparison

| Aspect | Tile38 | PostGIS | Redis Geo |
|---|---|---|---|
| Data Persistence | Disk + AOF | Full WAL (ACID) | AOF/RDB snapshots |
| Horizontal Scaling | Built-in clustering | Read replicas, Citus | Redis Cluster |
| Query Language | Redis-like protocol | SQL (PostgreSQL) | Redis commands |
| Indexing | R-Tree / Quadtree | GiST / SP-GiST | GeoHash (ZSET) |
| Max Dataset Size | Limited by RAM+disk | Unlimited (disk-based) | Limited by RAM |

## When to Choose Each Tool

**Choose Tile38 when:**
- You need real-time geofencing with automatic webhook notifications
- Building fleet tracking, IoT monitoring, or location alert systems
- Working with WGS84 coordinates and simple point/polygon data
- You want a lightweight, purpose-built geospatial server

**Choose PostGIS when:**
- You need comprehensive spatial analysis and complex geometry operations
- Working with multiple coordinate reference systems
- Building mapping, GIS, or spatial analytics applications
- You already use PostgreSQL and want seamless integration

**Choose Redis Geo when:**
- You need ultra-fast proximity lookups (microsecond latency)
- Your use case only requires point-based radius queries
- You already run Redis and want to add location features without new infrastructure
- Your dataset fits comfortably in memory

## Why Self-Host Your Geospatial Database?

Running your own geospatial database means complete control over location data — which is increasingly sensitive from a privacy perspective. When you self-host, all GPS coordinates, movement patterns, and geofence events stay within your infrastructure rather than flowing through third-party APIs.

Self-hosted geospatial databases integrate naturally with other self-hosted mapping infrastructure. Pair Tile38 or PostGIS with Nominatim for geocoding, TileServer GL for map rendering, or GeoServer for spatial data publishing. For a comprehensive guide to self-hosted mapping servers, see our [Nominatim vs TileServer GL vs GeoServer comparison](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide/).

Cost savings become significant at scale. Commercial geospatial APIs charge per request for geocoding, reverse geocoding, and proximity queries. A self-hosted PostGIS instance processes millions of queries for the fixed cost of your server. For high-volume location services — delivery tracking, ride-sharing, logistics — this difference can amount to thousands of dollars per month.

Self-hosted geospatial databases also offer customization that cloud services cannot match. PostGIS supports custom projections, user-defined spatial functions, and integration with any PostgreSQL extension. Tile38 allows custom webhook payloads and event filtering. Redis Geo integrates with your existing Redis monitoring and alerting stack. For organizations building location-based products, this flexibility is essential.

If you are also working with GeoIP data for location-based routing or access control, our [GeoIP database comparison](../2026-04-23-self-hosted-geoip-databases-maxmind-ip2location-dbip-guide/) covers the complementary tools needed for IP-to-location lookups.

## FAQ

### Can Tile38 store complex geometries like PostGIS?

Tile38 supports points, bounding boxes, and polygons, but lacks the full OGC geometry support of PostGIS. Tile38 cannot perform spatial joins, create buffers, or analyze topological relationships. For complex spatial analysis, use PostGIS.

### Does Redis Geo support polygons or geofencing?

No. Redis Geo only supports point locations (latitude/longitude pairs). It can perform radius-based proximity searches but cannot define polygon boundaries or detect when points enter/leave areas. For geofencing, use Tile38 or PostGIS.

### Which geospatial database is fastest for proximity queries?

Redis Geo is the fastest for simple radius queries due to its in-memory architecture, typically responding in microseconds. Tile38 is close behind with sub-millisecond responses. PostGIS is slower (milliseconds) but offers far more query capabilities.

### Can I migrate data between these three databases?

Yes. GeoJSON is a common interchange format. Export from PostGIS using `ST_AsGeoJSON()`, import into Tile38 using `SET` with GeoJSON objects, and load into Redis Geo using `GEOADD` with extracted coordinates. Tools like ogr2ogr can convert between formats.

### Do these databases support real-time position tracking?

Tile38 has native real-time support with pub/sub channels and webhook notifications for position changes. PostGIS can achieve real-time tracking using logical replication or trigger-based notifications. Redis Geo requires polling or Redis Streams for real-time updates.

### Which database should I use for a delivery tracking application?

Tile38 is purpose-built for this use case. Its native geofencing, real-time webhooks, and efficient point/polygon storage make it ideal for tracking delivery vehicles, detecting zone entries/exits, and sending customer notifications.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Geo-Spatial Database — Tile38 vs PostGIS vs Redis Geo",
  "description": "Compare three open-source geospatial databases for self-hosted location services: Tile38 for real-time geofencing, PostGIS for comprehensive spatial analysis, and Redis Geo for fast proximity lookups.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
