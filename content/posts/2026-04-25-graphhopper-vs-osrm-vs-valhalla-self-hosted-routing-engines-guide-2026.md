---
title: "GraphHopper vs OSRM vs Valhalla: Self-Hosted Routing Engines Compared 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "routing", "openstreetmap", "maps"]
draft: false
description: "Compare the top 3 self-hosted routing engines — OSRM, GraphHopper, and Valhalla — for building your own route planning, isochrone, and matrix API server using OpenStreetMap data."
---

If you have ever looked into building your own route planning service, you quickly discover that OpenStreetMap (OSM) is the backbone of most open-source mapping projects. But raw OSM data alone does not give you routing — you need a routing engine to build a navigable graph from the map data and expose it through APIs.

This guide compares the three most popular open-source routing engines you can deploy on your own infrastructure: **OSRM**, **GraphHopper**, and **Valhalla**. Each handles turn-by-turn navigation, fastest/shortest-path calculation, and matrix distance queries, but they differ significantly in language, performance characteristics, and API capabilities.

For related background, see our [self-hosted geospatial mapping servers guide](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/) for the broader mapping stack, and our [complete Google Maps alternatives guide](../self-hosted-maps-geocoding-openstreetmap-alternatives-google-maps-guide/) for the geocoding layer that often pairs with routing engines.

## Why Self-Host a Routing Engine?

Public routing APIs — Google Directions, Mapbox Directions, HERE Routing — are convenient but come with well-known trade-offs:

- **Rate limits**: Free tiers cap at 2,500–10,000 requests per day. Production usage at scale costs hundreds or thousands of dollars monthly.
- **Data lock-in**: Your routing logic, custom road weights, and proprietary road closures live in someone else's infrastructure.
- **Latency**: Every API call traverses the public internet, adding 50–200ms of round-trip time compared to local queries.
- **Privacy**: Every route query reveals user movement patterns to the API provider.

A self-hosted routing engine runs entirely on your servers. You control the data, the compute, the uptime, and the privacy. All three engines covered here accept OpenStreetMap `.osm.pbf` extracts (freely available from [Geofabrik](https://download.geofabrik.de/) or [BBBike](https://extract.bbbike.org/)) and produce a complete route planning API with zero external dependencies.

## OSRM — Open Source Routing Machine

**OSRM** ([github.com/Project-OSRM/osrm-backend](https://github.com/Project-OSRM/osrm-backend)) is written in C++ and focuses on raw performance. With **7,665 stars** and active maintenance (last pushed April 2026), it remains one of the most widely deployed open-source routing engines.

### Key Characteristics

| Feature | Detail |
|---|---|
| Language | C++ |
| Graph building | Edge contraction (Contraction Hierarchies) |
| Algorithms | CH (default), MLD (Multi-Level Dijkstra) |
| Protocols | HTTP REST API, C++ library |
| Profile customization | Lua scripts |
| Memory footprint | Medium (full planet ~55 GB RAM) |

### Strengths

OSRM is the **fastest** of the three engines for basic route queries, typically returning a route in under 10ms for medium-distance queries on a standard server. Its Contraction Hierarchies algorithm pre-computes shortcuts during the graph building phase, making queries extremely fast.

OSRM's Lua-based profile system lets you customize how roads are weighted. The default profiles cover car, bike, and foot routing. You can edit the Lua scripts to avoid toll roads, prefer highways, or penalize specific road types.

### Limitations

OSRM supports **three core endpoints**: `/route` (turn-by-turn navigation), `/table` (distance/duration matrix), and `/nearest` (snapping a coordinate to the road network). It does **not** natively support isochrones (reachability polygons), elevation data, or multi-modal transit routing.

The MLD algorithm adds dynamic traffic support and more flexible weighting than CH, but it still cannot match Valhalla's extensive costing flexibility or GraphHopper's wider endpoint variety.

### Quick Start with Docker

```bash
# Create data directory
mkdir -p /opt/osrm && cd /opt/osrm

# Download a city extract (Berlin example)
wget https://download.geofabrik.de/europe/germany/berlin-latest.osm.pbf

# Step 1: Extract the graph from OSM data
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-extract -p /opt/car.lua /data/berlin-latest.osm.pbf

# Step 2: Partition the graph (for MLD algorithm)
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-partition /data/berlin-latest.osrm

# Step 3: Customize edge weights
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-customize /data/berlin-latest.osrm

# Step 4: Start the routing API on port 5000
docker run -t -i -p 5000:5000 -v "${PWD}:/data" \
  ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/berlin-latest.osrm
```

### Sample API Query

```bash
curl "http://localhost:5000/route/v1/driving/13.388860,52.517037;13.397634,52.529407?overview=full&geometries=geojson"
```

Response includes a GeoJSON geometry, turn-by-turn instructions, distance, and duration.

## GraphHopper

**GraphHopper** ([github.com/graphhopper/graphhopper](https://github.com/graphhopper/graphhopper)) is written in Java and takes a different architectural approach. With **6,416 stars** and daily updates, it offers the most diverse set of API endpoints.

### Key Characteristics

| Feature | Detail |
|---|---|
| Language | Java |
| Graph building | Core-CH, LM (Landmark), Hybrid |
| Algorithms | Dijkstra, A*, Contraction Hierarchies |
| Protocols | HTTP REST API, Java library, JavaScript client |
| Profile customization | Java profiles + custom encoding (no Lua) |
| Memory footprint | Higher (Java VM overhead, full planet ~40–60 GB) |

### Strengths

GraphHopper stands out for **API breadth**. Beyond basic routing, it provides:

- **Isochrone API**: Generate polygons showing reachable areas within a time/distance budget
- **Matrix API**: Distance/duration tables between multiple origins and destinations
- **SRTM Elevation**: Integrated elevation data for gradient-aware routing
- **Turn Restrictions**: Full support for OSM turn restrictions (no-left-turn, no-u-turn)
- **Public Transit**: GTFS-based transit routing with departure/arrival times

GraphHopper can also run **embedded** as a Java library inside your application, eliminating the HTTP layer entirely. This makes it popular for mobile and desktop routing apps.

The web interface is clean and production-ready out of the box, with a map display that shows the route, elevation profile, and step-by-step instructions.

### Limitations

Java's memory footprint is higher than C++. Running GraphHopper with a full planet extract requires 8–16 GB of heap space. The first graph build is also slower than OSRM due to Java JVM startup overhead.

Profile customization requires writing Java code rather than editing a Lua script, which is more involved for simple adjustments like avoiding toll roads.

### Quick Start with Docker

The community-maintained Docker image from IsraelHikingMap is the easiest way to run GraphHopper:

```bash
# Create directories
mkdir -p /opt/graphhopper/data /opt/graphhopper/maps
cd /opt/graphhopper

# Download config template
wget -O config.yml https://raw.githubusercontent.com/graphhopper/graphhopper/master/config-example.yml

# Download an OSM extract
wget -O data/berlin-latest.osm.pbf https://download.geofabrik.de/europe/germany/berlin-latest.osm.pbf

# Run GraphHopper
docker run -d \
  --name graphhopper \
  -p 8989:8989 \
  -v /opt/graphhopper/data:/data \
  -v /opt/graphhopper/maps:/maps \
  -v /opt/graphhopper/config.yml:/config.yml \
  israelhikingmap/graphhopper:latest \
  java -jar /app/graphhopper.jar web /config.yml
```

Configuration can be customized via `config.yml`:

```yaml
graphhopper:
  datareader.file: /data/berlin-latest.osm.pbf
  graph.location: /maps/berlin-gh
  profiles:
    - name: car
      vehicle: car
      weighting: fastest
    - name: bike
      vehicle: bike
      weighting: fastest
    - name: foot
      vehicle: foot
      weighting: shortest
  server:
    port: 8989
```

### Sample API Query

```bash
# Route request
curl "http://localhost:8989/route?point=52.517037,13.388860&point=52.529407,13.397634&profile=car&type=json"

# Isochrone request
curl "http://localhost:8989/isochrone?point=52.517037,13.388860&profile=car&time_limit=600&type=json"
```

## Valhalla

**Valhalla** ([github.com/valhalla/valhalla](https://github.com/valhalla/valhalla)) is written in C++ and was originally developed by MapQuest before being open-sourced. With **5,647 stars**, it is the most feature-rich engine for multi-modal routing.

### Key Characteristics

| Feature | Detail |
|---|---|
| Language | C++ |
| Graph building | Tile-based, hierarchical |
| Algorithms | A*, bidirectional Dijkstra |
| Protocols | HTTP REST API (JSON), C++ library, Python bindings |
| Profile customization | JSON costing models |
| Memory footprint | Medium (tile-based, full planet ~100 GB disk) |

### Strengths

Valhalla's standout feature is **multi-modal costing**. A single routing query can combine driving, cycling, walking, and public transit into one route. Its JSON-based costing model is far more flexible than OSRM's Lua profiles:

```json
{
  "costing": "auto",
  "costing_options": {
    "auto": {
      "use_tolls": 0.0,
      "use_highways": 0.5,
      "use_ferry": 0.3,
      "use_living_streets": 0.1,
      "service_penalty": 15,
      "maneuver_penalty": 5
    }
  }
}
```

Beyond routing, Valhalla provides:

- **Isochrone API**: Reachability polygons with configurable time/distance limits
- **Matrix API**: Origin-destination distance and duration tables
- **Elevation**: Integrated elevation profiles from SRTM data
- **Transit**: GTFS-based public transit routing with real-time feeds
- **Optimized Route**: Traveling Salesman Problem (TSP) solver
- **Trace Attributes**: Speed-limit lookup and matched-route data
- **Turn-by-turn**: Localized instructions in 30+ languages

### Limitations

The tile-based architecture means initial graph builds are slower than OSRM, and the full-planet disk footprint (~100 GB) is larger. The API response format differs from OSRM, so migration requires client-side changes.

Valhalla's documentation, while comprehensive, is spread across multiple repositories and the official GitHub wiki, which can make initial setup more confusing.

### Quick Start with Docker

Valhalla offers an official "scripted" Docker image that automates the entire build process:

```bash
# Create data directory
mkdir -p /opt/valhalla/custom_files
cd /opt/valhalla

# Option A: Let the container download OSM data automatically
docker run -dt \
  --name valhalla \
  -p 8002:8002 \
  -v $PWD/custom_files:/custom_files \
  -e tile_urls=https://download.geofabrik.de/europe/germany/berlin-latest.osm.pbf \
  ghcr.io/valhalla/valhalla-scripted:latest

# Option B: Pre-download the data yourself
wget -O custom_files/berlin-latest.osm.pbf \
  https://download.geofabrik.de/europe/germany/berlin-latest.osm.pbf

docker run -dt \
  --name valhalla \
  -p 8002:8002 \
  -v $PWD/custom_files:/custom_files \
  ghcr.io/valhalla/valhalla-scripted:latest
```

You can also compose the full setup in a `docker-compose.yml`:

```yaml
version: "3.8"

services:
  valhalla:
    image: ghcr.io/valhalla/valhalla-scripted:latest
    container_name: valhalla
    ports:
      - "8002:8002"
    volumes:
      - ./custom_files:/custom_files
    environment:
      - tile_urls=https://download.geofabrik.de/europe/germany/berlin-latest.osm.pbf
      - server_workers=4
      - use_tiles_ignore_pbf=True
    restart: unless-stopped
```

### Sample API Query

```bash
# Route request with costing options
curl -X POST http://localhost:8002/route \
  -H "Content-Type: application/json" \
  -d '{
    "locations": [
      {"lat": 52.517037, "lon": 13.388860},
      {"lat": 52.529407, "lon": 13.397634}
    ],
    "costing": "auto",
    "costing_options": {
      "auto": {"use_tolls": 0.0}
    },
    "directions_options": {"units": "kilometers"}
  }'
```

## Comprehensive Comparison

| Feature | OSRM | GraphHopper | Valhalla |
|---|---|---|---|
| **Language** | C++ | Java | C++ |
| **License** | BSD-2 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 7,665 | 6,416 | 5,647 |
| **Last Active** | Apr 2026 | Apr 2026 | Apr 2026 |
| **Route API** | Yes | Yes | Yes |
| **Matrix API** | Yes | Yes | Yes |
| **Isochrone API** | No | Yes | Yes |
| **Elevation Data** | No | Yes (SRTM) | Yes (SRTM) |
| **Transit Routing** | No | Yes (GTFS) | Yes (GTFS) |
| **TSP / Optimized Route** | No | No | Yes |
| **Turn-by-turn** | Yes | Yes | Yes |
| **Multi-modal Costing** | No | Limited | Yes |
| **Localized Instructions** | Yes | Yes | Yes (30+ langs) |
| **Custom Profiles** | Lua scripts | Java code | JSON costing |
| **Embedded Mode** | C++ lib | Java lib | C++ lib |
| **Full Planet RAM** | ~55 GB | ~40–60 GB | Tile-based (disk) |
| **Full Planet Disk** | ~50 GB | ~40 GB | ~100 GB |
| **Docker Image** | Official (GHCR) | Community | Official (GHCR) |

## Performance Benchmarks (General Guidelines)

Performance depends heavily on hardware, OSM extract size, and query complexity. General observations from community benchmarks:

- **Route query latency**: OSRM is fastest at ~5–10ms for medium routes. Valhalla and GraphHopper typically return results in 10–30ms.
- **Graph build time**: For a country-sized extract (e.g., Germany ~300 MB OSM), OSRM takes ~5 minutes, GraphHopper ~8–12 minutes, and Valhalla ~15–20 minutes.
- **Throughput**: OSRM can handle ~5,000–10,000 queries/second on a single 8-core server. Valhalla achieves ~2,000–4,000 queries/second. GraphHopper's throughput depends heavily on JVM tuning but typically reaches ~1,000–3,000 queries/second.

## Which Should You Choose?

**Choose OSRM if:**
- You need maximum query throughput and minimum latency
- Your use case is simple: route + matrix + nearest, no isochrones
- You want the smallest memory footprint for a given region size
- Lua-based profile customization is sufficient

**Choose GraphHopper if:**
- You need isochrones, elevation, or transit routing
- You want to embed the engine directly in a Java application
- You prefer a polished web interface out of the box
- Your infrastructure can accommodate Java's memory requirements

**Choose Valhalla if:**
- You need multi-modal routing (combining car, bike, walk, transit)
- You want fine-grained costing control via JSON parameters
- You need TSP/optimized route or trace matching
- You value the most comprehensive API surface area

For most self-hosted mapping stacks, the routing engine sits alongside a geocoding server and a tile server. See our guides on [self-hosted geospatial mapping servers](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/) and [Google Maps alternatives](../self-hosted-maps-geocoding-openstreetmap-alternatives-google-maps-guide/) for the complete picture.

## FAQ

### Can I run a full-planet routing server on a single machine?

Yes. All three engines can process the full OpenStreetMap planet extract on a single server. OSRM requires ~55 GB of RAM and ~50 GB of disk. Valhalla uses a tile-based architecture that stores more on disk (~100 GB) with moderate RAM requirements. GraphHopper needs 40–60 GB of JVM heap space for the full planet. For a production full-planet server, plan for 64–128 GB RAM.

### How often should I update the OSM data?

OpenStreetMap data changes constantly. For most use cases, updating weekly or monthly from Geofabrik is sufficient. OSRM and Valhalla can be updated incrementally using OSM change files (`.osc`), though a full rebuild is simpler and often faster for extracts smaller than a continent.

### Can I add custom road restrictions or speed limits?

All three engines support this. OSRM uses Lua profiles to define road class penalties and speed multipliers. GraphHopper requires Java code changes for custom weighting. Valhalla accepts JSON costing options at query time, allowing per-request adjustments without rebuilding the graph.

### Do these engines support real-time traffic data?

OSRM's MLD (Multi-Level Dijkstra) algorithm supports dynamic traffic updates via edge weight modifications without a full rebuild. GraphHopper and Valhalla require data ingestion into their costing models, which typically involves custom development. None of the three engines have built-in traffic data feeds — you need to provide the traffic data yourself.

### Which engine is best for bicycle or pedestrian routing?

All three include default bike and foot profiles. GraphHopper and Valhalla are generally preferred for active-transport routing because they support elevation data, allowing routes that avoid steep hills. Valhalla's `bicycle` costing model includes additional parameters for cycleway preference and hill avoidance.

### Can I use these engines with commercial applications?

Yes. All three are permissively licensed: OSRM uses BSD-2-Clause, while GraphHopper and Valhalla use Apache 2.0. You can embed them in commercial products, modify the source code, and distribute derivative works without paying licensing fees. The only cost is your server infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GraphHopper vs OSRM vs Valhalla: Self-Hosted Routing Engines Compared 2026",
  "description": "Compare the top 3 self-hosted routing engines — OSRM, GraphHopper, and Valhalla — for building your own route planning, isochrone, and matrix API server using OpenStreetMap data.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
