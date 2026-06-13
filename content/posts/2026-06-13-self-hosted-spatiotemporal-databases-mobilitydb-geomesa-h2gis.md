---
title: "Self-Hosted Spatiotemporal Databases Beyond PostGIS: MobilityDB vs GeoMesa vs H2GIS"
date: "2026-06-13"
tags: ["spatial-database", "geospatial", "trajectory-analysis", "gis", "self-hosted", "mobility-data"]
draft: false
---

## The Rise of Spatiotemporal Data

Traditional geospatial databases like PostGIS excel at static geometries — points, lines, and polygons representing roads, buildings, and boundaries. But the modern world generates movement data: GPS traces from vehicles, vessel AIS positions, flight telemetry, wildlife tracking collars, and smartphone location pings. These spatiotemporal datasets require specialized capabilities that go beyond what standard spatial extensions provide.

Spatiotemporal databases add the temporal dimension to spatial queries. They can answer questions like "which taxis were within 500 meters of the airport between 2 PM and 3 PM last Tuesday?" or "what was the average speed of cargo ships through the Panama Canal in March?" These queries combine range searches, temporal filtering, trajectory simplification, and temporal aggregation — operations that conventional spatial databases handle inefficiently or not at all.

## Why Self-Host Spatiotemporal Analysis?

Data volume is the primary challenge. A fleet of 10,000 vehicles reporting GPS every 10 seconds generates over 86 million position records per day. Transmitting this data to cloud-based geospatial APIs incurs prohibitive bandwidth costs, while processing it on-premise with dedicated spatiotemporal databases costs only electricity and hardware.

Data sovereignty concerns apply strongly to location data. Movement patterns reveal sensitive information — where people live, work, and travel. Regulations like GDPR classify location data as personal data requiring explicit consent and localized processing. Self-hosting keeps movement data within your jurisdictional boundaries, simplifying compliance.

Performance requirements also favor self-hosting. Spatiotemporal queries are computationally intensive — they involve spatial indexing, temporal partitioning, and often trajectory reconstruction. Network latency to cloud services adds 50-200ms per query, which accumulates rapidly in interactive mapping applications. Local deployment cuts this to sub-millisecond latency for pre-warmed indexes.

For related geospatial infrastructure, see our [self-hosted geospatial mapping servers guide](../2026-06-12-self-hosted-ogc-web-processing-services-pywps-zoo-geoserver-wps/). For broader database optimization, check our [database query profiling guide](../2026-04-23-self-hosted-database-query-profiling-optimization-tools-guide-2026/).

## Comparing Spatiotemporal Database Solutions

| Feature | MobilityDB | GeoMesa | H2GIS |
|---------|-----------|---------|-------|
| **Base Platform** | PostgreSQL extension | Distributed (HBase, Accumulo, Kafka) | H2 (embedded Java) |
| **Spatial Types** | tgeompoint, tgeogpoint | Point, LineString, Polygon | All OGC types |
| **Temporal Support** | Native (moving objects) | Filter-based | Filter-based |
| **Trajectory Functions** | speed(), azimuth(), cumulativeLength() | Via CQL temporal filters | ST_ functions |
| **Indexing** | GiST (spatial) + Temporal | Z3/XZ3 (spatiotemporal) | R-tree (spatial) |
| **Scale** | Single node | Horizontally scalable | Embedded/single node |
| **Query Language** | SQL (PostgreSQL) | CQL (GeoServer compatible) | SQL (H2 dialect) |
| **License** | PostgreSQL license | Apache 2.0 | LGPL |
| **Stars** | 613+ | 1,488+ | 220+ |
| **Last Update** | 2026-06 | 2026-06 | 2026-05 |

### MobilityDB

MobilityDB is a PostgreSQL extension that adds native support for moving object data types. Unlike traditional spatial databases that treat time as an attribute column, MobilityDB integrates temporal semantics directly into its type system. A taxi's route becomes a single `tgeompoint` (temporal geometry point) value that captures position as a continuous function of time.

**Docker Compose deployment:**

```yaml
# docker-compose.yml for MobilityDB with PostGIS
version: "3.8"
services:
  mobilitydb:
    image: mobilitydb/mobilitydb:16-3.5
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: mobility
      POSTGRES_USER: analyst
      POSTGRES_PASSWORD: secure_password
    volumes:
      - mobility-data:/var/lib/postgresql/data
    command: >
      postgres -c shared_preload_libraries='postgis-3,libMobilityDB'
      -c max_connections=50

volumes:
  mobility-data:
```

**Loading and querying trajectory data:**

```sql
-- Load AIS vessel tracking data into MobilityDB
CREATE TABLE vessel_trips (
    mmsi integer,
    trip tgeompoint  -- Temporal geometry: position evolving over time
);

-- Insert a vessel trajectory
INSERT INTO vessel_trips VALUES (
    123456789,
    tgeompoint_seq(ARRAY[
        tgeompoint_inst('POINT(-122.4 37.8)'::geometry, timestamptz '2026-06-13 08:00:00'),
        tgeompoint_inst('POINT(-122.5 37.9)'::geometry, timestamptz '2026-06-13 09:00:00'),
        tgeompoint_inst('POINT(-122.6 38.0)'::geometry, timestamptz '2026-06-13 10:00:00')
    ])
);

-- Find vessels that entered San Francisco Bay area today
SELECT mmsi
FROM vessel_trips
WHERE trip && stbox(
    st_makeenvelope(-122.6, 37.7, -122.3, 37.9, 4326),
    tstzspan '[2026-06-13 00:00:00, 2026-06-13 23:59:59]'
);

-- Calculate average speed for each vessel (knots)
SELECT mmsi, speed(trip) * 1.94384 AS avg_speed_knots
FROM vessel_trips
WHERE speed(trip) IS NOT NULL;

-- Find vessels that came within 100 meters of each other
SELECT a.mmsi, b.mmsi, a.trip
FROM vessel_trips a, vessel_trips b
WHERE a.mmsi < b.mmsi
  AND tintersects(
      a.trip,
      tgeompoint_inst(b.trip::geometry, b.trip::timestamptz)
  );
```

MobilityDB's key advantage is its SQL-native approach. Analysts familiar with PostgreSQL can use standard SQL syntax enhanced with spatiotemporal functions. The GiST index over temporal geometries enables sub-second queries on billion-record tables. For organizations already running PostgreSQL, adding MobilityDB is a matter of loading an extension — no data migration or architecture change needed.

### GeoMesa

GeoMesa is a distributed spatiotemporal database built on top of NoSQL data stores including Apache Accumulo, HBase, and Apache Kafka. It is designed for massive-scale geospatial data — billions of records — where horizontal scalability is essential. GeoMesa implements the GeoTools API, making it compatible with GeoServer for OGC-standard WMS/WFS services.

```yaml
# docker-compose.yml for GeoMesa with Accumulo (single-node dev)
version: "3.8"
services:
  accumulo:
    image: apache/accumulo:2.1
    ports:
      - "9997:9997"
    environment:
      - ACCUMULO_INSTANCE=geomesa
      - ACCUMULO_PASSWORD=secret

  geoserver:
    image: geonode/geoserver:2.25
    ports:
      - "8080:8080"
    volumes:
      - ./geomesa-gs-plugin:/opt/geoserver/webapps/geoserver/WEB-INF/lib
    environment:
      - GEOMESA_ACCUMULO_INSTANCE=geomesa
      - GEOMESA_ACCUMULO_ZOOKEEPERS=zookeeper:2181

  zookeeper:
    image: zookeeper:3.8
    ports:
      - "2181:2181"
```

```bash
# Install GeoMesa command-line tools
wget https://github.com/locationtech/geomesa/releases/download/geomesa-5.1.0/geomesa-accumulo_2.12-5.1.0-bin.tar.gz
tar xzf geomesa-accumulo_2.12-5.1.0-bin.tar.gz

# Ingest GPS data with spatiotemporal indexing
geomesa-accumulo ingest \
  -C example-csv.conf \
  -c my_catalog \
  -i geomesa \
  -z zookeeper:2181 \
  --input-format CSV \
  gps_tracks.csv

# Query using CQL (Common Query Language)
geomesa-accumulo export \
  -c my_catalog \
  -i geomesa \
  -z zookeeper:2181 \
  -q "bbox(geom, -122.6, 37.7, -122.3, 37.9) AND dtg BETWEEN '2026-06-13T08:00:00Z' AND '2026-06-13T10:00:00Z'"
```

GeoMesa's distributed architecture is its defining strength. The Z3 and XZ3 indexes partition data across spatial and temporal dimensions simultaneously, enabling near-constant query latency regardless of dataset size. For organizations already running Hadoop or Accumulo clusters, GeoMesa integrates natively without additional infrastructure.

### H2GIS

H2GIS is a spatial extension for the H2 embedded Java database. While H2 is typically used as an embedded database in Java applications, H2GIS adds full OGC spatial type support, making it a lightweight alternative for spatiotemporal applications where a full PostgreSQL deployment would be overkill. It is ideal for edge computing scenarios or development environments.

```yaml
# docker-compose.yml for H2GIS web console
version: "3.8"
services:
  h2gis:
    image: openjdk:17-slim
    command: >
      sh -c "wget https://github.com/orbisgis/h2gis/releases/download/v2.2.1/h2gis-dist-2.2.1.jar &&
             java -cp h2gis-dist-2.2.1.jar org.h2.tools.Server -web -webAllowOthers -tcp -tcpAllowOthers"
    ports:
      - "8082:8082"
      - "9092:9092"
    volumes:
      - h2gis-data:/data
    working_dir: /data

volumes:
  h2gis-data:
```

```sql
-- H2GIS spatial queries (SQL with H2 extensions)
-- Create spatial table with trajectory data
CREATE TABLE taxi_trips (
    id INT PRIMARY KEY,
    trip_id VARCHAR,
    geom GEOMETRY,        -- Start point
    end_geom GEOMETRY,    -- End point
    start_time TIMESTAMP,
    end_time TIMESTAMP
);

-- Spatial index
CREATE SPATIAL INDEX ON taxi_trips(geom);

-- Find trips starting near downtown
SELECT trip_id, ST_Distance(geom, 'POINT(-73.98 40.75)') AS dist
FROM taxi_trips
WHERE geom && ST_Expand('POINT(-73.98 40.75)', 0.01)
  AND start_time BETWEEN '2026-06-13 08:00:00' AND '2026-06-13 10:00:00'
ORDER BY dist;
```

H2GIS shines in embedded and edge scenarios where deploying a full PostgreSQL server is impractical. Applications on IoT gateways, vehicle onboard computers, or mobile survey devices can use H2GIS for local spatial processing and sync results to central databases. Its compatibility with H2's server mode also makes it viable for small-team deployments accessed via JDBC.

## Choosing the Right Solution

The choice depends on your scale and existing infrastructure. MobilityDB is the right choice if you already use PostgreSQL — it adds spatiotemporal capabilities without changing your database architecture. Its SQL-native approach means your team's existing PostgreSQL skills transfer directly.

GeoMesa is the answer when scale demands distributed processing. If you are tracking millions of devices generating billions of position records, GeoMesa's horizontal scalability on Accumulo or HBase provides the throughput that single-node PostgreSQL cannot match. Its GeoServer integration enables OGC-compliant map services out of the box.

H2GIS is ideal for edge deployments or embedded analytics. If your use case involves processing location data on vehicles, drones, or remote sensors before transmitting reduced results, H2GIS provides a lightweight spatial engine that fits in constrained environments. It also serves as an excellent development and testing environment for spatial applications before deploying to production PostgreSQL or distributed clusters.

## FAQ

### How does MobilityDB differ from PostGIS with a timestamp column?

PostGIS with timestamps treats time as a filter attribute — you query "points WHERE time BETWEEN X AND Y" — but each point is independent. MobilityDB treats movement as a continuous function, enabling queries like "what was the position at exactly 9:23:45 AM?" (linear interpolation between known points). It also enables operations like speed(), azimuth(), and temporal intersection that would require complex window functions in vanilla PostGIS.

### Can GeoMesa handle real-time streaming data?

Yes. GeoMesa's Kafka integration ingests streaming location data through Kafka topics. Records are indexed in near-real-time and become queryable within seconds. This enables live dashboards showing current vehicle positions while maintaining historical query capabilities on the same data store. Configure Kafka topic partitioning by spatial region for optimal query performance.

### Is H2GIS suitable for production workloads?

H2GIS in server mode can handle production workloads for datasets up to tens of millions of records with moderate query concurrency (10-20 simultaneous users). Beyond that scale, migrate to MobilityDB or GeoMesa. H2GIS's primary strength is embedded deployment and development — use it as a stepping stone, not a permanent replacement for production-scale spatial databases.

### How do I migrate from PostGIS to MobilityDB?

MobilityDB is a PostgreSQL extension, so migrating involves installing the extension on your existing PostgreSQL instance and converting relevant tables. Existing PostGIS geometry columns remain fully functional — you add new tgeompoint columns for temporal data alongside them. No data migration or server change is needed.

### What are the hardware requirements for billion-record spatiotemporal datasets?

For MobilityDB on PostgreSQL: 64GB+ RAM for index caching, NVMe storage for random I/O during spatial index scans, and 16+ CPU cores for parallel query execution. For GeoMesa on Accumulo: a 5-node cluster with 32GB RAM each can handle 10+ billion records with sub-second query latency. The Z3 index's space-filling curve partitioning ensures even data distribution across cluster nodes.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Spatiotemporal Databases Beyond PostGIS: MobilityDB vs GeoMesa vs H2GIS",
  "description": "Comprehensive comparison of self-hosted spatiotemporal databases including MobilityDB for PostgreSQL, GeoMesa for distributed scale, and H2GIS for embedded deployment. Covers trajectory analysis, GPS data processing, and spatial indexing strategies.",
  "datePublished": "2026-06-13",
  "dateModified": "2026-06-13",
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
