---
title: "Self-Hosted Point Cloud Web Servers: Potree vs Entwine vs PDAL"
date: "2026-06-09"
tags: ["self-hosted", "point-cloud", "lidar", "geospatial", "3d-visualization", "data-processing", "webgl", "engineering"]
draft: false
---

## Introduction

Point cloud data — dense 3D coordinate collections from LIDAR scanners, photogrammetry, and depth cameras — powers everything from autonomous vehicle perception to construction site monitoring and cultural heritage preservation. As point cloud datasets grow to billions of points, efficient web-based access becomes critical for sharing, analyzing, and visualizing this data across teams. In this guide, we compare three open-source tools for building self-hosted point cloud web servers: **Potree** for WebGL visualization, **Entwine** for data organization and streaming, and **PDAL** for processing pipelines.

## Why Self-Host Point Cloud Infrastructure?

Commercial point cloud platforms charge per gigabyte stored and per user seat, making them prohibitively expensive for organizations handling terabytes of survey data. A self-hosted solution running on your own storage infrastructure eliminates these recurring costs entirely. For a survey company processing 50GB of new LIDAR data weekly, self-hosting can save $20,000-50,000 annually compared to cloud-based point cloud platforms.

Beyond cost, self-hosting provides **control over data residency and access latency**. Point cloud data from infrastructure surveys, mining operations, and defense applications often cannot leave the organization's network due to security requirements. Running Potree, Entwine, and PDAL on local servers keeps all data on-premises while still providing web-based access to field teams via VPN. For related geospatial processing workflows, see our [point cloud processing guide](../2026-06-08-self-hosted-point-cloud-processing-pcl-open3d-pdal/). If you're working with photogrammetry data, our [3D reconstruction guide](../2026-06-07-self-hosted-photogrammetry-3d-reconstruction-meshroom-colmap-openmvs-guide/) covers image-based point cloud generation. For broader GIS visualization needs, check our [GIS web map viewers comparison](../2026-06-09-self-hosted-gis-web-map-viewers-qgis-server-mapbender-lizmap/).

## Platform Comparison

| Feature | Potree | Entwine | PDAL |
|---------|--------|---------|------|
| **GitHub Stars** | 5,495+ | 517+ | 1,378+ |
| **Primary Function** | WebGL visualization | Point cloud organization | Data processing pipeline |
| **Web Server** | Built-in (Node.js/Express) | Greyhound/EPT protocol | N/A (CLI/library) |
| **Streaming Format** | Potree Converter octree | Entwine Point Tile (EPT) | Output to various formats |
| **Max Dataset Size** | 100B+ points (tiled) | 1T+ points | Unlimited (streaming) |
| **Coordinate Systems** | EPSG/Proj4 | EPSG/WKT | Full PROJ/GDAL support |
| **Filter Pipeline** | Limited (clipping) | Basic (bounds, srs) | 70+ filter stages |
| **License** | BSD-2-Clause | LGPL-2.1 | BSD-3-Clause |
| **Language** | JavaScript | C++ | C++/Python bindings |
| **Last Updated** | January 2026 | June 2026 | June 2026 |

## Setting Up Potree for WebGL Visualization

Potree converts point cloud files (LAS, LAZ, PLY, PTX) into an optimized octree format and serves them through a browser-based WebGL viewer:

```bash
# Install Node.js and dependencies
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Clone Potree and PotreeConverter
git clone https://github.com/potree/potree.git
git clone https://github.com/potree/PotreeConverter.git

# Build PotreeConverter
cd PotreeConverter
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install

# Convert a LAS file to Potree format
PotreeConverter input_scan.las -o /var/www/pointclouds/my_dataset   --generate-page --overwrite

# Serve with Potree viewer
cd ../../potree
python3 -m http.server 8080
# Access at http://your-server:8080/examples/viewer.html
```

For production deployments, serve Potree through nginx with CORS headers and SSL:

```nginx
server {
    listen 443 ssl;
    server_name pointcloud.yourdomain.com;
    ssl_certificate /etc/letsencrypt/live/pointcloud.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pointcloud.yourdomain.com/privkey.pem;

    root /var/www/potree;
    index examples/viewer.html;

    location /pointclouds/ {
        alias /var/www/pointclouds/;
        add_header Access-Control-Allow-Origin *;
        add_header Cache-Control "public, max-age=31536000";
    }

    location / {
        try_files $uri $uri/ =404;
    }
}
```

## Deploying Entwine for Massive Dataset Streaming

Entwine organizes point clouds into the Entwine Point Tile (EPT) format, enabling efficient spatial queries and progressive loading of massive datasets:

```bash
# Install Entwine via Conda (recommended for server deployment)
conda create -n entwine -c conda-forge entwine
conda activate entwine

# Build an EPT dataset from LAS/LAZ files
entwine build   -i /data/raw_scans/   -o /data/ept/city_survey   --srs "EPSG:26910"   --threads 16

# Serve EPT data via HTTP with Greyhound protocol
npm install -g greyhound-server
greyhound-server --port 8080   --ept /data/ept/city_survey   --cache-size 4096

# Access via Potree viewer connected to Greyhound endpoint
# URL: http://your-server:8080/
```

Entwine's EPT format supports range queries that only load points visible in the current viewport, making it practical to serve trillion-point datasets to web browsers. The Greyhound server protocol is supported by Potree, QGIS, and PDAL, giving you flexibility in visualization frontends.

## Building PDAL Processing Pipelines

PDAL (Point Data Abstraction Library) provides a comprehensive pipeline framework for point cloud processing. While PDAL itself isn't a web server, it generates the optimized datasets that Potree and Entwine serve:

```bash
# Install PDAL
sudo apt install -y pdal

# Define a processing pipeline (pipeline.json)
cat > pipeline.json << 'EOF'
{
  "pipeline": [
    {
      "type": "readers.las",
      "filename": "/data/scans/*.las"
    },
    {
      "type": "filters.reprojection",
      "out_srs": "EPSG:3857"
    },
    {
      "type": "filters.outlier",
      "method": "statistical",
      "mean_k": 8,
      "multiplier": 3.0
    },
    {
      "type": "filters.decimation",
      "step": 10
    },
    {
      "type": "writers.copc",
      "filename": "/data/output/cleaned_scan.copc"
    }
  ]
}
EOF

# Run the pipeline
pdal pipeline pipeline.json

# Verify output statistics
pdal info /data/output/cleaned_scan.copc --summary
```

PDAL's 70+ filter stages handle everything from coordinate reprojection and noise removal to classification, colorization, and format conversion. For automated workflows, wrap PDAL pipelines in shell scripts triggered by inotify on incoming scan directories.

## Recommended Architecture

For a production point cloud server, combine all three tools in a layered architecture. **Ingest layer** — PDAL watches for new scan files and automatically runs cleaning, reprojection, and classification pipelines. **Organization layer** — Entwine builds and continuously updates EPT datasets from PDAL's output. **Serving layer** — Greyhound streams Entwine data, and Potree provides the WebGL viewer frontend. This architecture scales from small survey datasets to terabyte-scale municipal LIDAR collections.

For high-availability deployments, run multiple Greyhound instances behind a load balancer. Entwine datasets are static files, so they can be replicated across servers using rsync or distributed filesystems like Ceph. Potree's static HTML/CSS/JS viewer can be served from any CDN or edge cache.

## Scaling Point Cloud Infrastructure for Enterprise Deployments

When your point cloud library grows beyond a few hundred gigabytes, the simple single-server architecture described above needs hardening for production use. Here's how to scale each layer of the point cloud serving pipeline.

**Storage layer.** EPT datasets and Potree octrees are essentially collections of small static files (typically 50KB-500KB per tile) organized in a deep directory hierarchy. This access pattern benefits enormously from NVMe storage with high IOPS for random reads. For datasets exceeding 10TB, consider CephFS or MinIO object storage with SSD-backed pools. Configure your storage backend to use erasure coding (rather than replication) for point cloud data — the cost savings are significant, and the read-heavy workload doesn't require the write performance of replicated storage.

**Compute layer.** PDAL pipelines can be computationally intensive, especially when running statistical outlier removal, ground classification, or ICP registration on billion-point datasets. Offload PDAL processing to dedicated worker nodes using a job queue like Celery or Slurm. A typical pipeline configuration: an NFS-mounted hot directory receives new scans, an inotify watcher submits a PDAL job to the queue, workers process the scan and write the output to the EPT build directory, and finally an Entwine `build` update command reindexes the dataset to include the new data.

**Caching layer.** Potree viewers request hundreds of small tile files when a user navigates to a new area of a point cloud. Without caching, each request hits the storage backend, adding latency. Deploy Varnish Cache or nginx's proxy_cache in front of your Greyhound server with a 24-hour TTL on tile requests. For globally distributed teams, replicate EPT datasets to regional object storage buckets and use GeoDNS to route users to the nearest Greyhound instance. CloudFront or Cloudflare R2 can serve as edge caches if your data can leave the corporate network.

**Monitoring and health checks.** Monitor Greyhound server health with Prometheus metrics exposed on a `/metrics` endpoint (requires a small sidecar process). Track tile request latency (p50/p95/p99), cache hit ratios, and dataset build freshness. Set up synthetic checks that request a known tile URL every 5 minutes and alert if it returns 404 or takes longer than 2 seconds. For Entwine, monitor the `entwine info` output to verify dataset integrity after each build update.

**Security considerations.** Point cloud data often contains sensitive information — building interiors from indoor mobile mapping, infrastructure vulnerabilities from bridge inspections, or classified terrain from defense surveys. Implement IP allowlisting for Greyhound endpoints, require mutual TLS for PDAL pipeline workers communicating with storage, and audit all access via nginx access logs shipped to a SIEM. For multi-tenant deployments, use Entwine's `--subset` option to create filtered views of datasets restricted to specific bounding boxes or classification codes.


## FAQ

### What's the difference between LAS, LAZ, EPT, and COPC?

LAS is the uncompressed industry standard for point cloud storage. LAZ is LAS with lossless compression (typically 7-20x smaller). EPT (Entwine Point Tile) is a directory-based streaming format that enables partial loading of massive datasets. COPC (Cloud Optimized Point Cloud) is a LAZ file with an internal spatial index supporting HTTP range requests — it's simpler than EPT for datasets under 500GB.

### Can I serve point clouds from object storage like MinIO?

Yes. Potree's octree format and Entwine's EPT format consist of many small static files accessed via HTTP range requests, making them compatible with S3-compatible object storage. Use CORS configuration to allow browser access. For PDAL, use the `readers.ept` stage to read directly from object storage.

### How much storage do I need for a city-scale LIDAR dataset?

A typical municipal LIDAR survey with 50-100 points per square meter over 500 km² generates 500GB-1TB of raw LAS data. After LAZ compression and EPT conversion, expect 50-200GB. PDAL's decimation filters can reduce this further for web visualization while preserving full-resolution data for analysis.

### Does Potree work on mobile devices?

Potree uses WebGL 2.0 and works on modern mobile browsers (iOS Safari 15+, Chrome for Android). Performance depends on the device's GPU — expect 15-30 FPS for datasets under 10M visible points on recent phones. Use PDAL's decimation filter to create lower-resolution versions specifically for mobile access.

### How do I add measurement tools to Potree?

Potree includes built-in measurement tools (distance, area, height profile, volume calculation) accessible from the toolbar. For custom measurement workflows, use Potree's JavaScript API to add annotation overlays and export measurements as GeoJSON. The API is documented in the Potree GitHub repository under `docs/`.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Point Cloud Web Servers: Potree vs Entwine vs PDAL",
  "description": "Compare open-source point cloud web servers Potree, Entwine, and PDAL for self-hosted LIDAR data visualization. Includes setup guides for WebGL streaming, EPT datasets, and automated processing pipelines.",
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
