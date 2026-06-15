---
title: "Self-Hosted Address Verification & Geocoding: libpostal vs Pelias vs Photon vs addok"
date: "2026-06-15"
tags: ["geocoding", "address-verification", "location-services", "openstreetmap", "self-hosted", "gis", "devops"]
draft: false
---

## Why Self-Host Your Address Verification?

Address data is the lifeblood of logistics, e-commerce, delivery services, and any application that needs to know where things are. When your application processes thousands of addresses daily—shipping labels, customer profiles, store locators—relying on Google Maps or Mapbox APIs introduces latency, per-request costs, and data privacy concerns. Every address you send to a third-party geocoding service potentially leaks business intelligence about your customer base and operations.

Self-hosting address verification and geocoding gives you complete control over your data pipeline. You can run batch processing jobs overnight without worrying about API rate limits. You maintain full data sovereignty—critical for GDPR compliance, healthcare applications, or any business handling sensitive location data. With the OpenStreetMap ecosystem powering modern open-source geocoders, the accuracy gap between self-hosted and commercial solutions has narrowed dramatically.

For broader geospatial infrastructure, see our [self-hosted mapping and geocoding guide](../self-hosted-maps-geocoding-openstreetmap-alternatives-google-maps-guide/). If you need spatial database capabilities, our [geospatial database comparison](../2026-05-20-self-hosted-geospatial-database-tile38-postgis-redis-guide/) covers Tile38, PostGIS, and Redis. For catalogue-level geospatial data discovery, see our [geospatial catalog platforms guide](../2026-06-09-self-hosted-geospatial-catalog-pygeoapi-pycsw-geonetwork-guide/).

## Address Verification Pipeline Architecture

A production address verification pipeline typically involves three stages:

1. **Parsing & Normalization** — breaking raw address strings into structured components (street number, street name, city, state, postal code, country)
2. **Geocoding** — converting structured addresses into geographic coordinates (latitude/longitude)
3. **Reverse Geocoding** — converting coordinates back into human-readable addresses

Different tools excel at different stages. libpostal dominates the parsing stage with its statistical NLP approach, while Pelias and Photon provide full-stack geocoding with autocomplete capabilities. Understanding the pipeline is key to choosing the right tool combination.

## Comparison Table

| Feature | libpostal | Pelias | Photon | addok |
|---------|-----------|--------|--------|-------|
| **Primary Function** | Address parsing & normalization | Full-stack geocoder | Search-as-you-type geocoder | Lightweight geocoder |
| **GitHub Stars** | 4,818 | 3,530 | 2,880 | 378 |
| **Language** | C (with bindings) | Node.js | Java | Python |
| **Storage Backend** | N/A (stateless) | Elasticsearch | Elasticsearch | Redis |
| **Autocomplete** | No | Yes (via API) | Yes (native) | Via plugin |
| **Reverse Geocoding** | No | Yes | Yes | Yes |
| **Batch Processing** | Yes (library) | Yes (import pipeline) | Yes (bulk import) | Limited |
| **Docker Support** | Community images | Official Docker Compose | Docker image | Docker image |
| **i18n Support** | 200+ countries | Global OSM data | Global OSM data | Primarily French OSM |
| **Data Source** | Statistical model (trained) | OpenStreetMap + Who's on First + GeoNames | OpenStreetMap (via Nominatim data) | OpenStreetMap (via custom index) |
| **Memory Footprint** | ~2GB (model data) | 8-16GB (with ES) | 4-8GB (with ES) | ~1GB (with Redis) |
| **Last Updated** | 2026-05-13 | 2026-03-20 | 2026-06-11 | 2025-12-23 |

## Tool Deep-Dive

### libpostal — The Address Parsing Foundation

libpostal is not a geocoder—it's a statistical natural language processing library trained on OpenStreetMap and OpenAddresses data covering over 200 countries and 60 languages. It normalizes messy address strings into structured components with remarkable accuracy.

```bash
# Install libpostal
git clone https://github.com/openvenues/libpostal
cd libpostal
./bootstrap.sh
./configure --datadir=/var/lib/libpostal/data
make -j$(nproc)
sudo make install
sudo ldconfig

# Download the statistical model data (~2GB)
sudo libpostal_data download all /var/lib/libpostal/data
```

Python integration via the `pypostal` binding:

```python
import postal.parser
import postal.expand

# Parse an address into components
parsed = postal.parser.parse_address(
    "781 Franklin Ave Crown Heights Brooklyn NYC NY 11216 USA"
)
# Output: [('781', 'house_number'), ('franklin ave', 'road'), ...]

# Normalize and expand abbreviations
expanded = postal.expand.expand_address("781 Franklin Ave Brooklyn NY")
# Returns: ["781 franklin avenue brooklyn new york", ...]
```

libpostal excels at handling international address formats and messy user input. However, it only normalizes text—it won't give you coordinates. Pair it with a geocoder like Pelias or Photon for a complete pipeline.

### Pelias — Full-Stack Geocoder with Elasticsearch

Pelias is a modular, full-featured geocoder built by the Mapzen team (now community-maintained). It powers geocode.earth's commercial API and can be self-hosted with Docker Compose.

```yaml
# docker-compose.yml for Pelias
version: '3'
services:
  elasticsearch:
    image: pelias/elasticsearch:7.17
    volumes:
      - es_data:/usr/share/elasticsearch/data
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms4g -Xmx4g"
    ports:
      - "9200:9200"

  api:
    image: pelias/api:latest
    ports:
      - "4000:4000"
    environment:
      - PORT=4000
    volumes:
      - ./pelias.json:/code/pelias.json

  placeholder:
    image: pelias/placeholder:latest
    environment:
      - PORT=4100

  pip-service:
    image: pelias/pip-service:latest
    environment:
      - PORT=4200

  whosonfirst:
    image: pelias/whosonfirst:latest
    volumes:
      - ./data/whosonfirst:/data

  openstreetmap:
    image: pelias/openstreetmap:latest
    volumes:
      - ./data/openstreetmap:/data

volumes:
  es_data:
```

The import pipeline processes multiple data sources (OpenStreetMap, Who's on First, GeoNames, OpenAddresses) into Elasticsearch. Pelias supports forward geocoding, reverse geocoding, autocomplete, and structured search—making it the most feature-complete self-hosted option.

```bash
# Test geocoding
curl "http://localhost:4000/v1/search?text=781+Franklin+Ave+Brooklyn"
```

### Photon — Search-as-You-Type Geocoder

Photon is a Java-based geocoder built on Apache Lucene/Elasticsearch that specializes in lightning-fast autocomplete. It ingests Nominatim data exports and provides sub-50ms response times for typeahead queries—ideal for address form autocomplete widgets.

```yaml
# Docker Compose for Photon
version: '3'
services:
  photon:
    image: komoot/photon:latest
    ports:
      - "2322:2322"
    volumes:
      - photon_data:/photon/photon_data
    command: -cors-any -enable-update-api
    environment:
      - JAVA_OPTS=-Xmx4g

volumes:
  photon_data:
```

```bash
# Import Nominatim data into Photon
wget https://download1.graphhopper.com/public/photon-db-latest.tar.bz2
java -jar photon.jar -data-dir ./photon_data

# Start the server
java -jar photon.jar -data-dir ./photon_data -listen-port 2322

# Autocomplete query
curl "http://localhost:2322/api?q=781+franklin+ave+brooklyn&limit=5"
```

Photon's key advantage is its instant search-as-you-type experience. It's simpler to deploy than Pelias (fewer services, no import pipeline to manage) but lacks Pelias's structured search capabilities and multi-source data richness.

### addok — Lightweight Python Geocoder

addok is a lightweight geocoder written in Python that stores data in Redis. It's designed for simplicity: import OpenStreetMap data with a single command and start serving geocoding requests immediately.

```bash
# Install addok
pip install addok

# Configure
addok config

# Import OSM data (region-specific extract)
addok import france-latest.osm.pbf

# Start the server
addok serve
# API available at http://localhost:7878

# Search
curl "http://localhost:7878/search?q=champs+elysees+paris"

# Reverse geocode  
curl "http://localhost:7878/reverse?lat=48.8584&lon=2.2945"
```

addok is ideal for regional deployments where you only need to geocode addresses within a specific country or region. Its Redis backend keeps memory usage low (~1GB for country-scale data) and deployment is trivial compared to the Elasticsearch-based alternatives.

## Deployment Architecture

For production deployments, a layered approach works best:

```
                  ┌─────────────┐
                  │  User Input  │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │  libpostal  │ ← Address parsing & normalization
                  └──────┬──────┘
                         │
               ┌─────────▼─────────┐
               │  Photon/Pelias    │ ← Geocoding & autocomplete
               └─────────┬─────────┘
                         │
               ┌─────────▼─────────┐
               │  Application     │ ← Store coordinates in PostGIS
               └──────────────────┘
```

```yaml
# nginx reverse proxy for geocoding services
server {
    listen 443 ssl;
    server_name geocode.example.com;

    location /photon/ {
        proxy_pass http://127.0.0.1:2322/;
        proxy_set_header Host $host;
    }

    location /pelias/ {
        proxy_pass http://127.0.0.1:4000/;
        proxy_set_header Host $host;
    }

    location /addok/ {
        proxy_pass http://127.0.0.1:7878/;
        proxy_set_header Host $host;
    }
}
```

## Choosing the Right Tool

**Choose libpostal** if you need world-class address parsing that handles messy international addresses. It's a library, not a web service—pair it with a geocoder of your choice.

**Choose Pelias** if you need a full-featured geocoder with structured search, multiple data sources, and reverse geocoding. Its modular architecture supports customization but requires more operational overhead (Elasticsearch cluster, multiple import services).

**Choose Photon** if autocomplete is your primary use case. It delivers sub-50ms search-as-you-type responses and is simpler to operate than Pelias. The trade-off is less data richness and fewer search capabilities.

**Choose addok** if you're deploying regionally (single country) and want the simplest possible setup. It runs on Redis with minimal memory and deployment complexity.

## Performance Benchmarks and Scaling Considerations

When benchmarking self-hosted geocoders, three metrics matter most: query latency, throughput under load, and index build time. libpostal's parsing is the fastest component—it processes addresses at ~10,000/second on modern hardware with no network overhead. Pelias typically serves search queries in 20-80ms at moderate load, but response times can spike to 200ms+ under concurrent query pressure due to Elasticsearch's internal queue management.

Photon's autocomplete performance is exceptional, with P95 latencies under 30ms for typeahead queries across global OSM datasets. This is achieved through Lucene's native fuzzy matching and Photon's optimized index structure. addok's Redis-backed architecture delivers consistent 10-30ms responses for simple searches but degrades on complex multi-token queries where fuzzy matching overhead accumulates.

For scaling beyond single-node deployments, Pelias benefits most from an Elasticsearch cluster with dedicated master and data nodes. Photon can scale horizontally by sharding its index across multiple Elasticsearch nodes. addok's Redis dependency limits it to vertical scaling—allocate more RAM for larger geographic coverage. At global scale (full planet OSM data), plan for 32-64GB RAM for Pelias, 16-32GB for Photon, and 8-16GB for addok with Redis.

Index build time varies dramatically: Photon's full planet import takes 4-8 hours on a 16-core machine; Pelias's multi-source import pipeline runs 12-24 hours for full planet coverage; addok's single-country import completes in 30-60 minutes. For production deployments, schedule weekly incremental updates using OSM diff files to keep indices current without full rebuilds.

## FAQ

### What's the difference between address verification and geocoding?

Address verification (or validation) confirms that an address exists and is deliverable, typically by checking against postal authority databases. Geocoding converts text addresses into geographic coordinates. Self-hosted tools like libpostal handle the parsing step, while Pelias/Photon/addok perform the geocoding. True address verification (confirming deliverability) is difficult without postal authority data, but normalization + geocoding provides a strong approximation.

### Can I geocode millions of addresses with these tools?

Yes, but the approach differs by tool. libpostal is designed for batch processing—it's a C library with no network overhead, making it ideal for processing large datasets. Pelias and Photon support bulk imports via their respective import pipelines. For million-scale batch geocoding, the recommended pipeline is: (1) use libpostal for parsing, (2) use Pelias or Photon's bulk import API, (3) store results in PostGIS for querying.

### How accurate are these compared to Google Maps?

OpenStreetMap-based geocoders achieve 85-95% accuracy compared to Google Maps in well-mapped urban areas. Rural coverage and address-level precision vary by region. For critical delivery applications, consider supplementing OSM data with local open data sources (government address databases, postal code files) that Pelias can ingest via custom importers.

### Do I need all four tools?

No. The most common production setup is libpostal (parsing) + either Pelias or Photon (geocoding). libpostal handles the dirty work of normalizing user-entered addresses, while Pelias/Photon provide the search and lookup capabilities. addok is an alternative to Pelias/Photon if you prefer Python and Redis over Java and Elasticsearch.

### How much does self-hosting save compared to Google Maps API?

Google Maps Geocoding API charges $5 per 1,000 requests. At 100,000 requests/month, that's $500/month—or $6,000/year. A self-hosted solution on a $200/month dedicated server (32GB RAM, 8 cores) costs $2,400/year, saving ~$3,600 annually. The break-even point is roughly 40,000 requests/month. Beyond cost, the primary value is data sovereignty and unlimited throughput.

### Can these tools handle non-Latin scripts (CJK, Arabic, Cyrillic)?

libpostal has trained models for 60+ languages including CJK, Arabic, and Cyrillic scripts. Pelias and Photon rely on OpenStreetMap's multilingual name tags—coverage for non-Latin scripts varies by region. For addresses in Chinese, Japanese, or Arabic, libpostal's normalization is the strongest component; autocomplete quality depends on OSM's local tag coverage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Address Verification & Geocoding: libpostal vs Pelias vs Photon vs addok",
  "description": "Comprehensive comparison of self-hosted address verification and geocoding tools. Compare libpostal (address parsing), Pelias (full-stack geocoder), Photon (autocomplete geocoder), and addok (lightweight Python geocoder) with Docker Compose deployment guides, performance benchmarks, and cost analysis.",
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
