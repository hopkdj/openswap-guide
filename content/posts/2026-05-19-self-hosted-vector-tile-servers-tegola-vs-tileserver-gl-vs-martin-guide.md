---
title: "Self-Hosted Vector Tile Servers: Tegola vs TileServer-GL vs Martin"
date: "2026-05-19"
tags: ["gis", "tile-server", "openstreetmap", "maptiler", "vector-tiles", "postgis", "self-hosted", "mapping"]
draft: false
---

Vector tile servers transform raw geospatial data into Mapbox Vector Tiles (MVT), the standard format for interactive web maps. Instead of serving pre-rendered raster images, vector tile servers generate tiles dynamically from databases like PostGIS, enabling client-side styling, rotation, and 3D rendering. We compare the three leading open-source vector tile servers.

## Why Self-Host Vector Tile Servers?

Commercial tile services charge per request, limit styling customization, and can disappear overnight. Self-hosting gives you full control over tile generation, styling, and caching. For high-traffic applications, a self-hosted tile server eliminates per-request costs entirely.

Vector tiles offer three advantages over traditional raster tiles: smaller file sizes (typically 30-50% smaller), client-side rendering with dynamic styling, and smooth zoom transitions without quality loss. Modern web mapping frameworks like MapLibre GL JS and OpenLayers require vector tile backends.

For broader geospatial infrastructure, see our [geospatial mapping servers guide](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/) and [network topology mapping comparison](../2026-05-02-self-hosted-network-topology-mapping-netbox-librenms-auto-discovery/).

## Tegola: High-Performance PostGIS Tile Server

[Tegola](https://github.com/go-spatial/tegola) is a Mapbox Vector Tile server written in Go, designed for high-performance tile generation directly from PostGIS databases. It is the most widely adopted dedicated vector tile server in the open-source ecosystem.

**Key Features:**

- Direct PostGIS data source — no intermediate file formats needed
- Mapbox Vector Tile (MVT) format with efficient caching
- Configurable via TOML with layer definitions and SQL queries
- HTTP/2 support for faster tile delivery
- Built-in tile seeding for pre-generation and CDN caching
- Support for multiple coordinate reference systems
- Prometheus metrics export for monitoring

**GitHub Stats:** 1,487 stars, actively maintained with regular releases.

### Tegola Docker Compose Deployment

```yaml
version: '3.8'
services:
  postgis:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: tegola
      POSTGRES_PASSWORD: tegola_pass
      POSTGRES_DB: gis_data
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  tegola:
    image: gospatial/tegola:latest
    ports:
      - "8080:8080"
    volumes:
      - ./tegola.toml:/etc/tegola/tegola.toml
    depends_on:
      - postgis
    command: ["serve", "--config", "/etc/tegola/tegola.toml"]

volumes:
  pg_data:
```

**tegola.toml configuration:**

```toml
[webserver]
port = ":8080"

[[providers]]
name = "postgis_provider"
type = "postgis"
host = "postgis:5432"
database = "gis_data"
user = "tegola"
password = "tegola_pass"

  [[providers.layers]]
  name = "roads"
  geometry_fieldname = "geom"
  id_fieldname = "gid"
  sql = "SELECT gid, ST_AsBinary(geom) AS geom, name, highway FROM roads WHERE geom && !BBOX!"

  [[providers.layers]]
  name = "buildings"
  geometry_fieldname = "geom"
  id_fieldname = "ogc_fid"
  sql = "SELECT ogc_fid, ST_AsBinary(geom) AS geom, name, type FROM buildings WHERE geom && !BBOX!"

[[maps]]
name = "osm_map"
attribution = "OpenStreetMap contributors"

  [[maps.layers]]
  name = "roads"
  provider_layer = "postgis_provider.roads"
  min_zoom = 0
  max_zoom = 17

  [[maps.layers]]
  name = "buildings"
  provider_layer = "postgis_provider.buildings"
  min_zoom = 12
  max_zoom = 17
```

## TileServer-GL: Vector and Raster Tile Rendering

[TileServer-GL](https://github.com/maptiler/tileserver-gl) by MapTiler provides both vector and raster tile serving with GL-style rendering. It uses MapLibre GL Native for server-side raster rendering and serves vector tiles directly from MBTiles or PMTiles files.

**Key Features:**

- Dual vector/raster tile serving from a single platform
- Server-side raster rendering with GL-style themes
- MBTiles and PMTiles file support
- Style editor and preview interface
- WMTS protocol support for GIS software integration
- Light footprint with Node.js-based architecture
- Supports multiple map styles simultaneously

**GitHub Stats:** 2,805 stars, maintained by MapTiler (commercial company with strong open-source commitment).

### TileServer-GL Docker Compose Deployment

```yaml
version: '3.8'
services:
  tileserver:
    image: maptiler/tileserver-gl:latest
    ports:
      - "8080:80"
    volumes:
      - ./data:/data
      - ./config.json:/usr/src/app/config.json
    command: ["--config", "/usr/src/app/config.json"]
```

**config.json configuration:**

```json
{
  "options": {
    "paths": {
      "root": "/data",
      "fonts": "/data/fonts",
      "styles": "/data/styles",
      "mbtiles": "/data"
    }
  },
  "services": {
    "preview": {
      "type": "static",
      "path": "/preview/"
    }
  },
  "data": {
    "osm-map": {
      "mbtiles": "/data/osm-tiles.mbtiles"
    }
  }
}
```

## Martin: High-Performance PostGIS and PMTiles Tile Server

[Martin](https://github.com/urbica/martin) is a blazing-fast tile server written in Rust, supporting PostGIS, MBTiles, and PMTiles sources. It auto-discovers tile sources from PostGIS tables with geometry columns, eliminating manual layer configuration.

**Key Features:**

- Written in Rust for maximum performance and memory efficiency
- Auto-discovery of PostGIS tile sources — zero configuration needed
- PMTiles support for serverless tile serving from object storage
- MBTiles file support with automatic introspection
- Built-in tile server with HTTP/2 support
- Configurable via environment variables or YAML
- Sub-millisecond tile generation for simple geometries

**GitHub Stats:** 3,642 stars, one of the fastest-growing tile server projects.

### Martin Docker Compose Deployment

```yaml
version: '3.8'
services:
  postgis:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: martin
      POSTGRES_PASSWORD: martin_pass
      POSTGRES_DB: geo
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  martin:
    image: urbica/martin:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://martin:martin_pass@postgis:5432/geo
      - KEEP_ALIVE=75
      - WORKER_THREADS=4
    depends_on:
      - postgis

  # PMTiles from object storage (optional)
  martin-pmtiles:
    image: urbica/martin:latest
    ports:
      - "3001:3000"
    volumes:
      - ./pmtiles:/data
    environment:
      - PMTILES_PATH=/data

volumes:
  pg_data:
```

## Feature Comparison

| Feature | Tegola | TileServer-GL | Martin |
|---------|--------|---------------|--------|
| **Language** | Go | Node.js | Rust |
| **Primary Data Source** | PostGIS | MBTiles/PMTiles | PostGIS/PMTiles |
| **Auto-Discovery** | Manual layer config | Manual | Automatic from PostGIS |
| **Vector Tiles** | Yes (MVT) | Yes (MVT) | Yes (MVT) |
| **Raster Tiles** | No | Yes (server-side GL) | No |
| **PMTiles** | No | Yes | Yes |
| **MBTiles** | No | Yes | Yes |
| **Tile Seeding** | Built-in | Via external tools | Via external tools |
| **WMTS Support** | No | Yes | No |
| **Prometheus Metrics** | Yes | No | Yes |
| **Configuration** | TOML | JSON | Env vars/YAML |
| **GitHub Stars** | 1,487 | 2,805 | 3,642 |
| **Best For** | PostGIS-first workflows | Styled raster + vector | Zero-config PostGIS |

## Choosing the Right Vector Tile Server

**Choose Tegola** if your data lives in PostGIS and you need fine-grained control over tile layer definitions. Its SQL-based layer configuration gives you precise control over what data appears at each zoom level, and its tile seeding capability integrates well with CDN workflows.

**Choose TileServer-GL** if you need both vector and raster tiles from the same platform, or if you work with MBTiles/PMTiles files rather than live database connections. Its server-side GL rendering produces high-quality raster tiles for legacy mapping clients that do not support vector rendering.

**Choose Martin** if you want zero-configuration tile serving from PostGIS. Martin auto-discovers geometry columns and serves tiles immediately, making it ideal for rapid prototyping and development. Its Rust-based architecture delivers the best raw performance for high-traffic deployments.

For data versioning workflows, see our [data versioning guide](../dvc-lakefs-pachyderm-self-hosted-data-versioning-guide-2026/).

## FAQ

### Can vector tile servers replace raster tile caches?
Yes, vector tiles offer smaller file sizes and client-side styling flexibility. However, raster tiles remain necessary for legacy GIS software and print workflows where client-side rendering is not available. TileServer-GL bridges both worlds by serving vector and raster tiles.

### How do I convert OpenStreetMap data to vector tiles?
Use tools like `osm2pgsql` to load OSM data into PostGIS, then configure your tile server to query the resulting tables. Alternatively, use `tippecanoe` to convert GeoJSON directly to MBTiles, which TileServer-GL and Martin can serve.

### What is the performance difference between Tegola and Martin?
Martin, being written in Rust, typically delivers lower latency for simple tile queries (sub-millisecond vs 5-10ms for Tegola). For complex queries with heavy PostGIS processing, the difference is minimal since PostGIS dominates the processing time. Martin's auto-discovery also eliminates configuration overhead.

### Can I use PMTiles with self-hosted tile servers?
Yes. Both TileServer-GL and Martin support PMTiles, a single-file archive format for tile data. PMTiles can be served from any HTTP server or object storage (S3, Cloudflare R2) without a dedicated tile server process, making it the most cost-effective option for static tile sets.

### How do I add custom styling to vector tiles?
Vector tiles contain raw geometry and attributes — styling is applied on the client side using MapLibre GL JS, OpenLayers, or Leaflet with a vector tile plugin. Define a JSON style document specifying colors, line widths, and label rules for each layer.

### Does Tegola support real-time data updates?
Tegola reads directly from PostGIS, so any data changes in the database are immediately reflected in served tiles. There is no caching layer that needs invalidation — each tile request queries the current database state.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Vector Tile Servers: Tegola vs TileServer-GL vs Martin",
  "description": "Compare Tegola, TileServer-GL, and Martin for serving Mapbox Vector Tiles from PostGIS and MBTiles in self-hosted mapping deployments.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
