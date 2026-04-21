---
title: "Self-Hosted Geospatial & Mapping Servers: Nominatim, TileServer GL & GeoServer Guide 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "geospatial", "maps"]
draft: false
description: "Complete guide to self-hosted geospatial servers — Nominatim for geocoding, TileServer GL for map tiles, and GeoServer for full GIS infrastructure. Docker deployment and configuration."
---

Building location-aware applications means relying on maps, geocoding, and spatial data. The default path for most developers is Google Maps Platform — geocoding APIs, tile servers, routing engines, all billed per request. But when your application scales, those costs multiply fast. More importantly, you hand over your entire location data pipeline to a single vendor.

Self-hosted geospatial infrastructure changes that equation. The open-source mapping ecosystem in 2026 is mature enough to replace every major Google Maps API component: geocoding, tile serving, spatial queries, and map rendering. This guide covers the three pillars of a self-hosted geospatial stack — Nominatim, TileServer GL, and GeoServer — with [docker](https://www.docker.com/) deployment instructions, configuration examples, and a comparison to help you pick the right tool for each layer.

## Why Self-Host Your Mapping Infrastructure

Running your own geospatial servers addresses real problems that cloud APIs create:

**Cost control at scale.** Google's Geocoding API costs $5 per 1,000 requests. Their Maps JavaScript API runs $7 per 1,000 loads. For an application serving 100,000 users with map views and address lookups, that's thousands of dollars per month. Self-hosted servers run on a single $40/month VPS with unlimited requests.

**Data privacy.** Every geocoding request sent to a cloud API reveals your users' locations, search patterns, and behavior. If you build a healthcare app, a logistics platform, or any service where location data is sensitive, sending coordinates to third-party servers creates compliance risks under GDPR, HIPAA, and state privacy laws. Self-hosted geocoding keeps all queries inside your infrastructure.

**Offline and air-gapped operation.** Applications in defense, maritime, mining, and remote field operations often need map data without internet connectivity. Self-hosted tile servers and geocoders run entirely on local networks with pre-loaded map data.

**No rate limits or vendor lock-in.** Cloud geocoding APIs enforce strict request quotas, and routing APIs throttle concurrent requests. Self-hosted solutions scale with your hardware. There are no sudden policy changes, no deprecated API versions, and no account suspensions that break your production service overnight.

**Custom data layers.** Self-hosted GIS servers let you overlay proprietary datasets — property boundaries, utility networks, environmental data — on top of standard map tiles without sharing those layers with any external service.

## Nominatim — Self-Hosted Geocoding

[Nominatim](https://nominatim.org/) is the geocoding engine that powers OpenStreetMap's search. It converts street addresses into latitude/longitude coordinates (forward geocoding) and performs the reverse operation (reverse geocoding). Unlike Google's Geocoding API, Nominatim is fully open-source under the GPL and runs entirely on your own hardware.

### How It Works

Nominatim imports OpenStreetMap data into a PostgreSQL database with the PostGIS extension. When you send a search query, it matches against indexed address components — street names, house numbers, postal codes, city names — and returns ranked results with precise coordinates. The import process is thorough: a full planet import indexes every mapped address on Earth.

### Hardware Requirements

Nominatim is resource-intensive during import but modest during runtime:

| Dataset | RAM (import) | RAM (runtime) | Disk Space | Import Time |
|---------|-------------|---------------|------------|-------------|
| Full planet | 64 GB+ | 8 GB | ~900 GB SSD | 24-48 hours |
| Europe extract | 32 GB | 4 GB | ~200 GB SSD | 4-8 hours |
| Single country | 8 GB | 2 GB | ~20-50 GB SSD | 30-90 minutes |
| City/region | 4 GB | 1 GB | ~2-10 GB SSD | 5-15 minutes |

### Docker Deployment

```yaml
# docker-compose.yml for Nominatim
version: "3.8"

services:
  nominatim:
    image: mediagis/nominatim:4.4
    container_name: nominatim
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      # Adjust based on your dataset and server RAM
      - PBF_URL=https://download.geofabrik.de/north-america/us-california-latest.osm.pbf
      - REPLICATION_URL=https://download.geofabrik.de/north-america/us-california-updates/
      - NOMINATIM_THREADS=4
    volumes:
      - nominatim-data:/var/lib/postgresql/14/main
    shm_size: "2g"

volumes:
  nominatim-data:
    driver: local
```

For a full planet import on a dedicated server:

```yaml
# docker-compose.yml for full planet Nominatim
version: "3.8"

services:
  nominatim:
    image: mediagis/nominatim:4.4
    container_name: nominatim-full-planet
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - PBF_URL=https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf
      - NOMINATIM_THREADS=8
      # Pre-allocated shared memory for large imports
    volumes:
      - /data/nominatim:/var/lib/postgresql/14/main
      - /data/imports:/nominatim/data
    shm_size: "32g"
    deploy:
      resources:
        limits:
          memory: 64G
```

### Usage Examples

Once running, the API is available at `http://localhost:8080`:

```bash
# Forward geocoding — find coordinates for an address
curl "http://localhost:8080/search?q=1600+Pennsylvania+Ave+Washington+DC&format=json&limit=1"

# Response:
# [{"place_id": 289873411, "lat": "38.8976763", "lon": "-77.0365298",
#   "display_name": "The White House, 1600, Pennsylvania Avenue NW, Washington, DC 20500, United States",
#   "type": "building", "importance": 0.9756}]

# Reverse geocoding — find address for coordinates
curl "http://localhost:8080/reverse?lat=38.8977&lon=-77.0365&format=json"

# Search with structured query
curl "http://localhost:8080/search?street=Market+Street&city=San+Francisco&state=California&country=US&format=json"

# Search within a bounding box (San Francisco area)
curl "http://localhost:8080/search?q=coffee&format=json&viewbox=-122.52,37.82,-122.35,37.70&bounded=1"
```

### Updating Data

Nominatim supports incremental updates from OpenStreetMap's change feeds:

```bash
# Configure the replication URL during setup, then run updates:
docker exec nominatim nominatim replication --project-dir /nominatim

# Or set up a cron job for hourly updates:
# 0 * * * * docker exec nominatim nominatim replication --project-dir /nominatim
```

### Performance Tuning

```bash
# Increase PostgreSQL shared buffers for better query performance
# Add to postgresql.conf inside the container:
# shared_buffers = 4GB
# work_mem = 256MB
# effective_cache_size = 16GB

# Nominatim also supports flatnode files for faster lookups on large datasets:
# Add to your docker-compose environment:
# - FLATNODE_FILE=/nominatim/flatnode/flatfile
# Then mount a volume for the flatnode directory
```

## TileServer GL — Self-Hosted Map Tile Serving

[TileServer GL](https://tileserver.readthedocs.io/) serves map tiles from pre-rendered raster data or generates them on-the-fly using vector tile styles. It replaces Google's Maps JavaScript API and Static Maps API with a self-hosted solution that serves tiles in any style you define.

### How It Works

TileServer GL can operate in two modes:

- **Raster mode**: Serves pre-rendered PNG/JPG tiles generated by tools like Tilemaker or Planetiler. Simple and fast, but requires significant disk space for all zoom levels.
- **Vector mode**: Serves compact Protocol Buffer (PBF) vector tiles and renders them client-side using MapLibre GL JS. The style (colors, fonts, layers) is defined in a JSON style file and can be changed without regenerating tiles.

Vector mode is the recommended approach — a single vector tile dataset for the entire planet is roughly 80 GB, compared to terabytes for pre-rendered raster tiles.

### Docker Deployment

```yaml
# docker-compose.yml for TileServer GL
version: "3.8"

services:
  tileserver:
    image: maptiler/tileserver-gl:latest
    container_name: tileserver-gl
    restart: unless-stopped
    ports:
      - "8081:8080"
    volumes:
      # Vector tiles (generated by Planetiler or Tilemaker)
      - ./data/planet.mbtiles:/data/planet.mbtiles
      # Custom style JSON and font files
      - ./styles:/data/styles
      - ./fonts:/data/fonts
    command:
      - "planet.mbtiles"
      - "--config"
      - "/data/styles/config.json"
```

To download a regional MBTiles file and serve it:

```bash
# Download vector tiles for a region (example: Europe)
# Planetiler is the fastest tool for generating planet-scale vector tiles
docker run -v $(pwd)/data:/data ghcr.io/onthegomap/planetiler:latest \
  --download --area=france --output=/data/france.mbtiles

# Serve with TileServer GL
docker run -d --name tileserver-gl \
  -p 8081:8080 \
  -v $(pwd)/data/france.mbtiles:/data/france.mbtiles \
  maptiler/tileserver-gl:latest
```

### Custom Map Style

Create a custom style to control exactly how your maps look:

```json
// styles/custom-style.json
{
  "version": 8,
  "name": "Custom Dark Style",
  "sources": {
    "openmaptiles": {
      "type": "vector",
      "url": "mbtiles://planet.mbtiles"
    }
  },
  "sprite": "sprites/custom",
  "glyphs": "fonts/{fontstack}/{range}.pbf",
  "layers": [
    {
      "id": "background",
      "type": "background",
      "paint": {"background-color": "#1a1a2e"}
    },
    {
      "id": "water",
      "type": "fill",
      "source": "openmaptiles",
      "source-layer": "water",
      "paint": {"fill-color": "#16213e"}
    },
    {
      "id": "roads",
      "type": "line",
      "source": "openmaptiles",
      "source-layer": "transportation",
      "paint": {
        "line-color": "#4a4e69",
        "line-width": {"base": 1.2, "stops": [[6, 0.5], [14, 4]]}
      }
    },
    {
      "id": "place-labels",
      "type": "symbol",
      "source": "openmaptiles",
      "source-layer": "place",
      "layout": {
        "text-field": ["get", "name"],
        "text-size": 12
      },
      "paint": {"text-color": "#c9d1d9"}
    }
  ]
}
```

### Client-Side Integration

Use MapLibre GL JS (the open-source fork of Mapbox GL JS) to display tiles:

```html
<!DOCTYPE html>
<html>
<head>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <style>
    #map { width: 100%; height: 600px; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = new maplibregl.Map({
      container: 'map',
      style: {
        version: 8,
        sources: {
          selfhosted: {
            type: 'raster',
            tiles: ['http://your-server:8081/styles/osm-bright/{z}/{x}/{y}.png'],
            tileSize: 256
          }
        },
        layers: [{
          id: 'tiles',
          type: 'raster',
          source: 'selfhosted'
        }]
      },
      center: [-122.4194, 37.7749], // San Francisco
      zoom: 12
    });
    map.addControl(new maplibregl.NavigationControl());
  </script>
</body>
</html>
```

## GeoServer — Full GIS Server

[GeoServer](https://geoserver.org/) is a full-featured geographic information system server that serves geospatial data using open standards. It is the most powerful option in this guide, supporting OGC-compliant WMS (Web Map Service), WFS (Web Feature Service), and WCS (Web Coverage Service) protocols.

### When to Use GeoServer

Choose GeoServer when you need:

- **Multi-format data serving**: Shapefiles, PostGIS, GeoTIFF, GeoJSON, and dozens of other data sources
- **Standards compliance**: OGC WMS, WFS, WCS, and WMTS for interoperability with any GIS client
- **Layer styling**: SLD (Styled Layer Descriptor) for professional cartographic rendering
- **Data editing**: WFS-T for transactional editing of vector features
- **Com[plex](https://www.plex.tv/) spatial queries**: Filter expressions, coordinate transformations, and projections

If you just need map tiles and address search, Nominatim + TileServer GL are simpler. If you need enterprise GIS capabilities, GeoServer is the answer.

### Docker Deployment

```yaml
# docker-compose.yml for GeoServer
version: "3.8"

services:
  geoserver:
    image: kartoza/geoserver:2.25.2
    container_name: geoserver
    restart: unless-stopped
    ports:
      - "8082:8080"
    environment:
      - GEOSERVER_ADMIN_USER=admin
      - GEOSERVER_ADMIN_PASSWORD=your_secure_password
      - INITIAL_MEMORY=2G
      - MAXIMUM_MEMORY=8G
      - GEOSERVER_DATA_DIR=/opt/geoserver/data_dir
      - STABLE_EXTENSIONS=wps-plugin,control-flow-plugin
      - ENABLE_CORS=true
    volumes:
      - geoserver-data:/opt/geoserver/data_dir
      # Mount your own data directory for persistence
      - ./geoserver_data:/geoserver_data
      # Mount shapefiles, GeoTIFFs, etc.
      - ./data:/data
    depends_on:
      - postgis

  postgis:
    image: postgis/postgis:16-3.4
    container_name: geoserver-postgis
    restart: unless-stopped
    environment:
      - POSTGRES_USER=geoserver
      - POSTGRES_PASS=secure_db_password
      - POSTGRES_DB=gis_data
    volumes:
      - postgis-data:/var/lib/postgresql
    command: >
      postgres
      -c shared_preload_libraries='pg_stat_statements'
      -c max_connections=100

volumes:
  geoserver-data:
  postgis-data:
```

### Loading Data via the REST API

GeoServer includes a comprehensive REST API for managing workspaces, datastores, and layers programmatically:

```bash
# Create a new workspace
curl -u admin:your_secure_password \
  -X POST -H "Content-Type: text/xml" \
  -d "<workspace><name>my_project</name></workspace>" \
  http://localhost:8082/geoserver/rest/workspaces

# Add a PostGIS datastore
curl -u admin:your_secure_password \
  -X POST -H "Content-Type: text/xml" \
  -d '
  <dataStore>
    <name>gis_database</name>
    <connectionParameters>
      <entry key="host">postgis</entry>
      <entry key="port">5432</entry>
      <entry key="database">gis_data</entry>
      <entry key="user">geoserver</entry>
      <entry key="passwd">secure_db_password</entry>
      <entry key="dbtype">postgis</entry>
    </connectionParameters>
  </dataStore>' \
  http://localhost:8082/geoserver/rest/workspaces/my_project/datastores

# Publish a layer from an existing table
curl -u admin:your_secure_password \
  -X POST -H "Content-Type: text/xml" \
  -d "<featureType><name>city_boundaries</name></featureType>" \
  "http://localhost:8082/geoserver/rest/workspaces/my_project/datastores/gis_database/featuretypes"
```

### Serving Map Layers

Once your data is loaded, GeoServer serves it via standard OGC protocols:

```bash
# WMS GetMap — get a rendered map image
curl "http://localhost:8082/geoserver/wms?service=WMS&version=1.1.1&request=GetMap\
  &layers=my_project:city_boundaries\
  &bbox=-122.52,37.70,-122.35,37.82\
  &width=800&height=600\
  &srs=EPSG:4326\
  &format=image/png" \
  -o map_output.png

# WFS GetFeature — get vector data as GeoJSON
curl "http://localhost:8082/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature\
  &typeName=my_project:city_boundaries\
  &outputFormat=application/json\
  &srsName=EPSG:4326" \
  -o boundaries.geojson

# WMTS — get map tiles (compatible with Leaflet and OpenLayers)
curl "http://localhost:8082/geoserver/gwc/service/wmts\
  ?layer=my_project:city_boundaries\
  &style=&tilematrixset=EPSG:900913\
  &Service=WMTS&Request=GetTile&Version=1.0.0\
  &Format=image/png&TileMatrix=EPSG:900913:12\
  &TileCol=655&TileRow=1583" \
  -o tile.png
```

### Integration with OpenLayers

```html
<!DOCTYPE html>
<html>
<head>
  <link href="https://cdn.jsdelivr.net/npm/ol@9.2.4/ol.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/ol@9.2.4/dist/ol.js"></script>
  <style>#map { width: 100%; height: 500px; }</style>
</head>
<body>
  <div id="map"></div>
  <script>
    const wmsSource = new ol.source.TileWMS({
      url: 'http://your-server:8082/geoserver/wms',
      params: {
        'LAYERS': 'my_project:city_boundaries',
        'TILED': true,
        'VERSION': '1.1.1'
      },
      serverType: 'geoserver',
      crossOrigin: 'anonymous'
    });

    const map = new ol.Map({
      target: 'map',
      layers: [
        new ol.layer.Tile({
          source: new ol.source.OSM()  // Base layer
        }),
        new ol.layer.Tile({
          source: wmsSource,  // Your GeoServer layer
          opacity: 0.7
        })
      ],
      view: new ol.View({
        center: ol.proj.fromLonLat([-122.4194, 37.7749]),
        zoom: 12
      })
    });
  </script>
</body>
</html>
```

## Putting It All Together: Complete Self-Hosted Stack

A production-ready self-hosted mapping stack combines all three components:

```yaml
# docker-compose.yml — Complete geospatial stack
version: "3.8"

services:
  # Geocoding: address → coordinates
  nominatim:
    image: mediagis/nominatim:4.4
    container_name: nominatim
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - PBF_URL=https://download.geofabrik.de/north-america/us-california-latest.osm.pbf
      - NOMINATIM_THREADS=4
    volumes:
      - nominatim-data:/var/lib/postgresql/14/main
    shm_size: "2g"

  # Tile serving: map visualization
  tileserver:
    image: maptiler/tileserver-gl:latest
    container_name: tileserver-gl
    restart: unless-stopped
    ports:
      - "8081:8080"
    volumes:
      - ./data/california.mbtiles:/data/california.mbtiles

  # GIS server: spatial data management
  geoserver:
    image: kartoza/geoserver:2.25.2
    container_name: geoserver
    restart: unless-stopped
    ports:
      - "8082:8080"
    environment:
      - GEOSERVER_ADMIN_USER=admin
      - GEOSERVER_ADMIN_PASSWORD=your_secure_password
      - INITIAL_MEMORY=2G
      - MAXIMUM_MEMORY=4G
    volumes:
      - geoserver-data:/opt/geoserver/data_dir

  # Spatial database (shared by GeoServer)
  postgis:
    image: postgis/postgis:16-3.4
    container_name: postgis
    restart: unless-stopped
    environment:
      - POSTGRES_USER=gis
      - POSTGRES_PASS=gis_password
      - POSTGRES_DB=spatial_db
    volumes:
      - postgis-data:/var/lib/postgresql
    ports:
      - "[caddy](https://caddyserver.com/)5432"

  # Reverse proxy for unified access
  caddy:
    image: caddy:2.8
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config

volumes:
  nominatim-data:
  geoserver-data:
  postgis-data:
  caddy-data:
  caddy-config:
```

```
# Caddyfile — reverse proxy configuration
maps.yourdomain.com {
    handle /search* {
        reverse_proxy nominatim:8080
    }
    handle /reverse* {
        reverse_proxy nominatim:8080
    }
    handle /tiles* {
        reverse_proxy tileserver:8080
    }
    handle /geoserver* {
        reverse_proxy geoserver:8080
    }
    handle {
        respond "Geospatial Stack" 200
    }
}
```

## Feature Comparison

| Feature | Nominatim | TileServer GL | GeoServer |
|---------|-----------|---------------|-----------|
| **Primary purpose** | Geocoding | Tile serving | Full GIS server |
| **Geocoding** | ✅ Full-featured | ❌ No | ⚠️ Limited plugin |
| **Raster tiles** | ❌ No | ✅ Yes | ✅ WMS |
| **Vector tiles** | ❌ No | ✅ Yes | ✅ with extensions |
| **WFS/WMS/WCS** | ❌ No | ❌ No | ✅ All OGC standards |
| **Data editing** | ❌ No | ❌ No | ✅ WFS-T |
| **Custom styling** | ❌ No | ✅ JSON styles | ✅ SLD/CSS |
| **Spatial queries** | ❌ No | ❌ No | ✅ Filter expressions |
| **License** | GPL | BSD | Apache 2.0 |
| **RAM (runtime)** | 2-8 GB | 512 MB-2 GB | 2-8 GB |
| **Setup complexity** | Medium | Low | High |
| **Best for** | Address search | Map display | Enterprise GIS |

## Choosing the Right Tool

**Use Nominatim when** you need forward and reverse geocoding for addresses and place names. It is the gold standard for open-source geocoding and handles everything from "1600 Pennsylvania Avenue" to "coffee shops near me" queries.

**Use TileServer GL when** you need to serve map tiles for web or mobile applications. It is lightweight, supports both raster and vector modes, and lets you define custom map styles with JSON configuration files.

**Use GeoServer when** you need enterprise-grade GIS capabilities: multi-format data publishing, OGC standard compliance, spatial data editing, complex layer styling, and integration with enterprise spatial databases like PostGIS.

**Use all three together** for a complete replacement of Google Maps Platform. Nominatim handles address search, TileServer GL serves your base map tiles, and GeoServer manages your custom spatial data layers.

The open-source geospatial ecosystem is mature, well-documented, and production-ready. With a single server and a weekend of setup time, you can replace every paid mapping API in your stack while keeping your data private, your costs predictable, and your infrastructure entirely under your control.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
