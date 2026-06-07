---
title: "Self-Hosted Elevation Data APIs: Open-Elevation vs OpenTopoData vs SRTM Tile Server"
date: "2026-06-08"
tags: ["elevation-data", "geospatial-tools", "openstreetmap", "mapping-apis", "self-hosted-apis"]
draft: false
---

## Introduction

Elevation data underpins a surprising number of modern applications — from hiking and cycling route planners that calculate cumulative elevation gain to drone flight path planning, solar panel placement optimization, flood risk modeling, and telecommunications line-of-sight analysis. The Google Elevation API has long been the default choice, but with its pay-per-request pricing and dependency on a cloud provider, many developers are turning to self-hosted alternatives.

In this article, we compare three open-source elevation data services that you can deploy on your own hardware: **Open-Elevation**, **OpenTopoData**, and a **self-hosted SRTM Tile Server**. Each takes a different approach to storing, querying, and serving elevation data.

## Comparison Table

| Feature | Open-Elevation | OpenTopoData | SRTM Tile Server |
|---------|---------------|--------------|------------------|
| GitHub Stars | 780+ | 400+ | N/A (DIY) |
| Language | Python | Python | Various (Python/Go) |
| Data Source | SRTM, CGIAR | SRTM, ETOPO1, GEBCO, EMODnet, Mapzen | SRTM GL1/GL3 |
| API Protocol | REST (GET /lookup) | REST (GET /v1/{dataset}) | Custom / XYZ Tiles |
| Docker Support | ✅ docker-compose.yml | ❌ (Python package) | ❌ (DIY) |
| Dataset Management | Pre-packaged TIFFs | Auto-download on first use | Manual tile management |
| Multi-Dataset | No (single dataset) | Yes (5+ datasets) | Depends on setup |
| Format Support | JSON response | JSON response | GeoTIFF, JSON, raw |
| Query Methods | Single point, line | Single point, multi-point | Tile-based, point query |
| CORS Support | Built-in | Manual configuration | Manual configuration |
| Last Updated | April 2024 | February 2026 | Ongoing (SRTM data static) |

## Open-Elevation — The Simple, Battle-Tested Option

[Open-Elevation](https://open-elevation.com) is the most straightforward self-hosted elevation API. Built in Python and backed by a Docker Compose deployment, it provides a drop-in replacement for the Google Elevation API's single-point and multi-point lookup endpoints.

### Key Features

- **Drop-in Google Elevation API Compatible**: The API endpoints closely mirror the Google Elevation API, making migration straightforward. The response format is nearly identical — just change the base URL
- **Docker Compose Ready**: Open-Elevation is one of the few elevation services with a production-ready `docker-compose.yml` in its repository. Deployment takes minutes
- **SRTM + CGIAR Data**: Ships with pre-processed SRTM elevation data covering the entire globe at 90m resolution
- **Single-Point and Multi-Point Queries**: Query one location or batch-query hundreds at once via the `/lookup` POST endpoint

### Deployment

```yaml
# docker-compose.yml — from open-elevation repository
version: "3.8"
services:
  open-elevation:
    image: open-elevation:latest
    build: .
    container_name: open-elevation
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    environment:
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8080
```

The initial setup downloads elevation TIFF files into the `./data` directory. The full SRTM dataset is approximately 25 GB — you can also download specific regions to save disk space.

```bash
# Clone and deploy
git clone https://github.com/Jorl17/open-elevation.git
cd open-elevation

# Download global elevation data (25 GB)
wget https://s3.amazonaws.com/open-elevation-assets/SRTM_90m_DEM_Global_Tiff.zip
unzip SRTM_90m_DEM_Global_Tiff.zip -d data/

# Start
docker-compose up -d

# Query a point (latitude, longitude)
curl "http://localhost:8080/api/v1/lookup?locations=47.3769,8.5417"
# Returns: {"results": [{"latitude": 47.3769, "longitude": 8.5417, "elevation": 408.0}]}
```

## OpenTopoData — Multi-Dataset Elevation Hub

[OpenTopoData](https://www.opentopodata.org) takes a more ambitious approach by supporting multiple elevation datasets behind a unified API. Where Open-Elevation gives you one dataset, OpenTopoData lets you choose from five different elevation sources depending on your use case.

### Key Features

- **Multiple Datasets**: SRTM 30m (higher resolution than Open-Elevation's 90m), SRTM 90m, ETOPO1 (global bathymetry + topography), GEBCO 2020 (ocean floor mapping), EMODnet (European marine data), and Mapzen Terrain Tiles
- **Dataset Selection via URL**: Switch between datasets simply by changing the URL path — `/v1/srtm30m`, `/v1/etopo1`, `/v1/gebco2020`, etc.
- **Auto-Download**: OpenTopoData downloads elevation tiles on first request and caches them. No need to pre-load 25 GB of data — it grows organically with usage
- **Self-Hosting Documentation**: Comprehensive self-hosting guide with instructions for both Docker and bare-metal Python deployment

### Deployment

OpenTopoData doesn't ship a `docker-compose.yml` in its repository, but you can easily create one:

```yaml
# docker-compose.yml
version: "3.8"
services:
  opentopodata:
    image: python:3.12-slim
    container_name: opentopodata
    working_dir: /app
    volumes:
      - ./data:/app/data
    ports:
      - "5000:5000"
    command: >
      sh -c "pip install opentopodata &&
             mkdir -p /app/data &&
             python -m opentopodata --port 5000 --data-dir /app/data"
    restart: unless-stopped
```

The config file controls which datasets are enabled:

```yaml
# config.yaml
datasets:
  srtm30m:
    type: raster
    path: data/srtm_30m/
    description: "SRTM 30m resolution global elevation"
  etopo1:
    type: raster
    path: data/etopo1/
    description: "ETOPO1 global relief model (1 arc-minute)"
  gebco2020:
    type: raster
    path: data/gebco_2020/
    description: "GEBCO 2020 bathymetry and topography"
```

Querying is dataset-aware:

```bash
# SRTM 30m resolution (land)
curl "http://localhost:5000/v1/srtm30m?locations=47.3769,8.5417"

# GEBCO 2020 (includes ocean floor depth — negative values for underwater)
curl "http://localhost:5000/v1/gebco2020?locations=21.3156,-157.8581"
# Returns elevation of Mauna Kea including its underwater base (~-5000m at nearby ocean floor)
```

The multi-dataset approach is invaluable for applications that need both land elevation (hiking apps) and ocean depth (marine navigation). For related geospatial infrastructure, see our [self-hosted geospatial mapping servers guide](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/).

## SRTM Tile Server — Maximum Control, Maximum Effort

For organizations that need complete control over their elevation data pipeline, building a custom SRTM Tile Server from raw SRTM data provides unlimited flexibility. This approach involves hosting SRTM GeoTIFF files and serving them through a standard tile server or a custom API.

### Architecture Overview

The SRTM (Shuttle Radar Topography Mission) dataset provides near-global elevation data at 30m (SRTM GL1) or 90m (SRTM GL3) resolution. The data is organized in 1° × 1° tiles — roughly 14,000 tiles cover the Earth's land surface.

A typical self-hosted stack includes:

1. **Data Storage**: SRTM GeoTIFF files stored on local disk or object storage
2. **Tile Server**: A service that reads GeoTIFF files and serves elevation values for specific coordinates
3. **Caching Layer**: Nginx or Varnish to cache frequent queries
4. **API Layer**: A thin REST wrapper around the tile server

### Building a Custom SRTM Server

```python
# srtm_server.py — Minimal SRTM elevation server
import rasterio
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
SRTM_DIR = "/data/srtm"

# Open all SRTM tiles into memory (or use lazy loading)
tile_cache = {}

def get_tile_filename(lat, lon):
    """Convert lat/lon to SRTM tile filename (e.g., N47E008.hgt)"""
    ns = 'N' if lat >= 0 else 'S'
    ew = 'E' if lon >= 0 else 'W'
    return f"{ns}{int(abs(lat)):02d}{ew}{int(abs(lon)):03d}.hgt"

def get_elevation(lat, lon):
    """Read elevation at (lat, lon) from SRTM tile"""
    tile_name = get_tile_filename(lat, lon)
    tile_path = os.path.join(SRTM_DIR, tile_name)
    
    if tile_path not in tile_cache:
        if not os.path.exists(tile_path):
            # Try 1-arcsecond (30m) and 3-arcsecond (90m) variants
            for ext in ['.hgt', '.tif', '.SRTMGL1.hgt.zip']:
                alt_path = os.path.join(SRTM_DIR, tile_name + ext)
                if os.path.exists(alt_path):
                    tile_path = alt_path
                    break
            else:
                return None
        tile_cache[tile_path] = rasterio.open(tile_path)
    
    dataset = tile_cache[tile_path]
    row, col = dataset.index(lon, lat)
    try:
        elevation = float(dataset.read(1)[row, col])
        return elevation if elevation != dataset.nodata else None
    except IndexError:
        return None

@app.route('/elevation')
def elevation():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    elev = get_elevation(lat, lon)
    if elev is None:
        return jsonify({"error": "no data"}), 404
    return jsonify({"latitude": lat, "longitude": lon, "elevation": elev})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  srtm-server:
    image: python:3.12-slim
    container_name: srtm-server
    working_dir: /app
    volumes:
      - ./srtm_server.py:/app/server.py
      - ./srtm_data:/data/srtm
    ports:
      - "5001:5001"
    command: >
      sh -c "pip install flask rasterio &&
             python server.py"
    restart: unless-stopped
```

Downloading the SRTM data can be done from NASA Earthdata or USGS EarthExplorer:

```bash
# Download all SRTM GL1 30m tiles for Europe region
# Requires NASA Earthdata account (free registration)
mkdir -p srtm_data
cd srtm_data

# Example: download using Earthdata API
for lat in $(seq 35 70); do
  for lon in $(seq -10 40); do
    tile=$(printf "N%02dE%03d" $lat $lon)
    wget --user=YOUR_USERNAME --password=YOUR_PASSWORD       "https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/${tile}.SRTMGL1.hgt.zip"
  done
done
```

## Why Self-Host Your Elevation API?

The economic case for self-hosting elevation data becomes compelling at scale. Google's Elevation API costs $5 per 1,000 requests. An application that calculates elevation profiles for 10,000 hiking routes per day — each requiring 100 elevation points along the path — would generate 1 million requests daily. At Google's pricing, that's $5,000 per day or $1.8 million per year. A self-hosted server with 50 GB of storage and a modest CPU costs perhaps $50-100 per month.

Privacy and data sovereignty are equally important for many use cases. Construction companies doing site surveys, government agencies planning infrastructure, and defense contractors analyzing terrain all prefer to keep their location queries on-premises rather than sending them to a cloud provider. Every query to the Google Elevation API reveals your location of interest — and location data patterns can be highly sensitive.

Offline capability is the third major advantage. Field operations — geological surveys, disaster response teams, military units — often operate in areas with limited or no internet connectivity. A self-hosted elevation server running on a ruggedized laptop or a Raspberry Pi can provide full elevation query capabilities without any network dependency. For mobile field applications, see our [self-hosted routing engines guide](../2026-04-25-graphhopper-vs-osrm-vs-valhalla-self-hosted-routing-engines-guide-2026/).

For developers building mapping stacks from scratch, our [vector tile servers comparison](../2026-05-19-self-hosted-vector-tile-servers-tegola-vs-tileserver-gl-vs-martin-guide/) covers the complementary technology for serving map tiles alongside elevation data.

## FAQ

### What's the difference between 30m and 90m elevation resolution?

SRTM data comes in two resolutions: SRTM GL1 at 30 meters (1 arc-second) and SRTM GL3 at 90 meters (3 arc-seconds). The 30m version provides roughly 9x more elevation points per square kilometer, making it better for detailed terrain analysis, hiking trail profiles, and drone flight planning. The 90m version is sufficient for regional-scale analysis, telecommunications tower placement, and weather modeling.

### Can I use these services for ocean depth (bathymetry)?

Yes — but only OpenTopoData with the GEBCO 2020 or ETOPO1 datasets. These include ocean floor elevation data, which returns negative elevation values (depth below sea level). Open-Elevation and basic SRTM servers only cover land surfaces. If your application needs both land and sea elevation — for example, a sailing navigation app — OpenTopoData's multi-dataset model is the clear choice.

### How much storage do I need?

Open-Elevation requires about 25 GB for the full global SRTM dataset. OpenTopoData downloads tiles on demand, so storage grows with usage — typically 5-20 GB for most use cases. A custom SRTM tile server with 30m resolution global coverage needs about 60 GB (including the higher-resolution tiles). You can dramatically reduce storage by downloading only the regions you need — Europe at 30m resolution is about 8 GB, North America about 12 GB.

### How do these services perform under load?

Elevation queries are inherently fast because they're simple array lookups — given a lat/lon coordinate, the server calculates which tile to open and which pixel to read. A single Python process can handle 500-1,000 requests per second on modest hardware. The bottleneck is usually disk I/O for uncached tiles. With an Nginx caching layer (cache hot tiles in memory), throughput can exceed 10,000 requests per second.

### Which service should I use for drone flight planning?

For drone flight planning, you need the highest resolution elevation data available. OpenTopoData with the SRTM 30m dataset is the best self-hosted option. The 30m resolution is sufficient for most consumer and commercial drone operations. If you need higher resolution (10m or better), you'll need to integrate national LiDAR datasets, which are beyond the scope of these open-source elevation servers but can be added to a custom SRTM tile server architecture.

---

**💰 Test your market judgment with real stakes? I use [Polymarket](https://polymarket.com/?r=fc8a0) — the world's largest prediction market platform. From election results to tech regulation timelines, you can bet on anything. Unlike gambling, this is a genuine information market: the more you know, the higher your win rate. I've profited handsomely by predicting tech-related event outcomes. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Elevation Data APIs: Open-Elevation vs OpenTopoData vs SRTM Tile Server",
  "description": "Compare three approaches to self-hosting elevation data APIs — Open-Elevation, OpenTopoData, and custom SRTM tile servers — with Docker Compose deployment, performance benchmarks, and use case analysis.",
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
