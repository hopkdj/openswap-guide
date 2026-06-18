---
title: "Self-Hosted Drone Photogrammetry: OpenDroneMap vs WebODM vs NodeODM — Complete Guide 2026"
date: "2026-06-18"
tags: ["drone", "photogrammetry", "gis", "mapping", "odm", "3d-modeling", "docker"]
draft: false
---

## Why Self-Host Your Drone Photogrammetry Pipeline?

Drone-based photogrammetry has revolutionized surveying, construction, agriculture, and environmental monitoring. Instead of relying on expensive cloud processing services like DroneDeploy or Pix4D Cloud, self-hosting your photogrammetry pipeline gives you complete control over your data, eliminates per-project processing fees, and lets you scale processing across your own hardware.

When you self-host, you own the entire workflow — from image upload to 3D model generation. Your survey data never leaves your infrastructure, which is critical for government contracts, defense projects, and any scenario where data sovereignty matters. Cloud services typically charge $100-500+ per project for processing, while a self-hosted setup on a capable workstation or server can process unlimited projects at zero marginal cost.

For aerial survey workflows, see our [drone ground control stations guide](../2026-06-05-self-hosted-drone-ground-control-stations-mission-planner-qgc-inav/). If you need 3D visualization for your outputs, check our [3D geospatial visualization comparison](../2026-06-15-self-hosted-3d-geospatial-visualization-cesiumjs-deck-gl-kepler/). For general photogrammetry without drone specialization, see our [photogrammetry tools guide](../2026-06-07-self-hosted-photogrammetry-3d-reconstruction-meshroom-colmap-openmvs-guide/).

The OpenDroneMap ecosystem is the leading open-source solution for drone photogrammetry, with over 6,000 GitHub stars and an active community of surveyors, researchers, and developers. In this guide, we compare the three core components: ODM CLI, WebODM, and NodeODM — helping you choose the right tool for your workflow.

## Comparison: OpenDroneMap vs WebODM vs NodeODM

| Feature | OpenDroneMap (ODM) | WebODM | NodeODM |
|---------|-------------------|--------|---------|
| **Type** | CLI processing engine | Full web UI platform | Lightweight REST API |
| **GitHub Stars** | 6,199+ | 3,986+ | 292+ |
| **Interface** | Command line | Web dashboard | REST API |
| **Multi-User** | No | Yes (with auth) | Via API tokens |
| **GPU Acceleration** | Yes (CUDA) | Yes (via ODM) | Yes (via ODM) |
| **Processing Nodes** | Single machine | Single + cluster | Single node |
| **Plugin System** | Python-based | Full plugin API | None |
| **Docker Support** | Native (Docker image) | Native (docker-compose) | Native (Docker image) |
| **Point Cloud Export** | Yes (LAS, LAZ, PLY) | Yes | Yes |
| **Orthophoto Generation** | Yes (GeoTIFF) | Yes | Yes |
| **3D Model Export** | Yes (OBJ, PLY, glTF) | Yes | Yes |
| **License** | AGPL v3 | AGPL v3 | AGPL v3 |
| **Last Updated** | June 2026 | June 2026 | April 2026 |

### OpenDroneMap (ODM CLI)

OpenDroneMap is the command-line engine that powers the entire ecosystem. It takes raw drone images and produces orthomosaics, point clouds, 3D models, and digital elevation models (DEMs). ODM is written in Python and C++, with heavy use of OpenCV, GDAL, and Ceres Solver for structure-from-motion processing.

ODM supports virtually all consumer and professional drones — any platform that captures geotagged images. It handles multispectral imagery (RedEdge, Sequoia), oblique imagery, and nadir captures. Processing is highly configurable through a YAML settings file or command-line flags.

### WebODM

WebODM provides a polished web interface on top of ODM. It adds user management, project organization, processing queues, and visualization tools. You can view 3D models, point clouds, and orthophotos directly in the browser — no desktop GIS software required. WebODM includes a measurement tool, annotation system, and export to common GIS formats.

For teams and organizations, WebODM adds user authentication, project sharing, and REST API access. It can connect to multiple NodeODM instances for distributed processing across a cluster of machines.

### NodeODM

NodeODM is a lightweight REST API wrapper around ODM, designed to run on individual processing nodes. It accepts images via HTTP, processes them with ODM, and returns the results. NodeODM is ideal for building custom processing pipelines, integrating photogrammetry into automated workflows, or scaling processing across multiple machines when used with WebODM's cluster mode.

## Deployment: Docker Compose for WebODM

WebODM provides an official docker-compose setup. Here\'s a production-ready configuration:

```yaml
version: \'3.8\'

services:
  webodm:
    image: opendronemap/webodm:latest
    container_name: webodm
    ports:
      - "8000:8000"
    volumes:
      - webodm_data:/webodm/app/media
      - ./data/projects:/webodm/app/media/project
    environment:
      - WO_SECRET_KEY=change-this-to-a-random-string
      - WO_BROKER_URL=redis://redis:6379
      - WO_DEBUG=false
    restart: unless-stopped
    depends_on:
      - redis
      - db

  redis:
    image: redis:7-alpine
    container_name: webodm-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data

  db:
    image: postgres:16-alpine
    container_name: webodm-db
    environment:
      - POSTGRES_USER=webodm
      - POSTGRES_PASSWORD=secure-password
      - POSTGRES_DB=webodm
    volumes:
      - db_data:/var/lib/postgresql/data
    restart: unless-stopped

  nodeodm:
    image: opendronemap/nodeodm:latest
    container_name: nodeodm
    ports:
      - "3000:3000"
    restart: unless-stopped
    environment:
      - NVIDIA_VISIBLE_DEVICES=all  # For GPU acceleration

volumes:
  webodm_data:
  redis_data:
  db_data:
```

For GPU acceleration with NVIDIA GPUs, install the NVIDIA Container Toolkit:

```bash
# Install NVIDIA Container Toolkit (Ubuntu/Debian)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed \'s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g\' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## Command-Line Processing with ODM

For advanced users who prefer the CLI, ODM provides a Docker-based workflow:

```bash
# Create a project directory with your drone images
mkdir -p ~/drone-projects/survey-01/images
cp /path/to/drone/images/*.JPG ~/drone-projects/survey-01/images/

# Run ODM processing
docker run -ti --rm \
  -v ~/drone-projects/survey-01:/datasets \
  opendronemap/odm:latest \
  --project-path /datasets \
  --orthophoto-resolution 2 \
  --dem-resolution 4 \
  --dsm \
  --dtm \
  --pc-quality high \
  --feature-quality ultra \
  --cog
```

Key parameters for production use:
- `--orthophoto-resolution`: Output resolution in cm/pixel (default: 5)
- `--pc-quality`: Point cloud density — low, medium, high, ultra
- `--feature-quality`: Feature extraction quality — affects processing speed
- `--dsm`: Generate Digital Surface Model (includes buildings/vegetation)
- `--dtm`: Generate Digital Terrain Model (bare earth)
- `--cog`: Output Cloud Optimized GeoTIFF format

## Cluster Processing Setup

For large surveys, distribute processing across multiple machines using NodeODM:

```bash
# On each processing node
docker run -d --restart unless-stopped \
  --name nodeodm-worker \
  -p 3000:3000 \
  opendronemap/nodeodm:latest

# In WebODM, add each node under Administration > Processing Nodes
# Nodes are auto-discovered and used for parallel task processing
```

## Choosing the Right Tool for Your Workflow

**Use ODM CLI when:**
- You need maximum control over processing parameters
- You\'re building automated CI/CD-style processing pipelines
- You have scripting experience and prefer terminal workflows
- You want to integrate with custom GIS tools or scripts

**Use WebODM when:**
- You need a user-friendly web interface for team collaboration
- Non-technical team members need to process drone imagery
- You want built-in visualization, measurement, and annotation tools
- You need project management and user authentication

**Use NodeODM when:**
- You\'re building a custom web application that needs photogrammetry
- You want to scale processing across a cluster of machines
- You need to integrate drone processing into an existing API workflow
- You prefer lightweight, single-purpose microservices

## FAQ

### How many images can ODM process?

ODM can handle datasets from 50 to 5,000+ images. For datasets beyond 2,000 images, 32GB+ RAM and GPU acceleration are recommended. Processing time scales roughly linearly with image count — a 500-image survey typically takes 2-4 hours on a modern workstation. You can split large surveys into sub-models using `--split` and `--split-overlap` parameters for faster processing.

### What drone hardware is compatible?

ODM works with any drone that captures geotagged images — DJI (Mavic, Phantom, Matrice), Autel, Parrot, SenseFly, Wingtra, and custom-built drones. The key requirement is that images contain GPS coordinates in EXIF data. RTK/PPK-corrected imagery produces the highest accuracy, but standard GPS-tagged images work well for most applications.

### Does ODM support multispectral and thermal imagery?

Yes. ODM supports multispectral cameras including MicaSense RedEdge, Parrot Sequoia, and DJI Multispectral. For thermal imagery, ODM can process radiometric JPEG and TIFF files. Use the `--radiometric-calibration` flag for calibrated thermal outputs. Multispectral outputs include reflectance maps, NDVI, and other vegetation indices.

### How accurate are the outputs compared to commercial software?

ODM produces results comparable to commercial photogrammetry software when properly configured. For RTK/PPK-corrected imagery, ODM achieves 2-5 cm horizontal accuracy and 5-10 cm vertical accuracy — matching Pix4D and Agisoft Metashape. Using GCPs (Ground Control Points) improves accuracy to 1-3 cm. The main difference is ODM\'s lack of advanced point cloud classification, though third-party tools can fill this gap.

### What are the hardware requirements for self-hosting?

Minimum: 16GB RAM, 4-core CPU, 50GB free disk space. Recommended: 32-64GB RAM, 8+ core CPU, NVIDIA GPU (8GB+ VRAM), 500GB+ SSD storage. GPU acceleration reduces processing time by 50-70%. For a production setup processing daily surveys, a dedicated workstation with 128GB RAM and an RTX 4090 or A-series GPU is ideal. Cloud VMs (AWS g5.xlarge or equivalent) work well for burst processing.

### Can I use WebODM commercially?

Yes. WebODM and ODM are licensed under AGPL v3, which permits commercial use. You can offer processing services to clients, integrate the API into commercial products, and provide managed hosting — as long as you make your source modifications available. For closed-source integration without AGPL obligations, OpenDroneMap offers a commercial license through their website.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Drone Photogrammetry: OpenDroneMap vs WebODM vs NodeODM — Complete Guide 2026",
  "description": "Compare OpenDroneMap, WebODM, and NodeODM for self-hosted drone photogrammetry. Docker Compose setup, cluster processing, GPU acceleration, and production deployment guide.",
  "datePublished": "2026-06-18",
  "dateModified": "2026-06-18",
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
