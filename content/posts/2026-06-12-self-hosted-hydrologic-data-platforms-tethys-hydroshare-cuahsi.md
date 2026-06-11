---
title: "Self-Hosted Hydrologic Data Platforms: Tethys Platform vs HydroShare vs CUAHSI HydroClient"
date: "2026-06-12"
tags: ["self-hosted", "comparison", "guide", "hydrology", "water-science", "environmental-data", "data-platform", "django", "docker", "python", "gis"]
draft: false
---

## Why Self-Host Hydrologic Data Management?

Water resource management depends on integrating diverse datasets — stream gauge readings, groundwater well logs, satellite precipitation estimates, climate model outputs, and water quality samples — into coherent analysis workflows. Historically, hydrologists spent more time locating and formatting data than actually analyzing it. Purpose-built hydrologic data platforms address this fragmentation by providing centralized catalogs, standardized metadata, and web-based visualization tools.

Self-hosting a hydrologic data platform ensures data sovereignty for water management agencies, research institutions, and environmental consultancies. Regulatory requirements around water rights data, drought monitoring, and flood forecasting increasingly demand auditable data provenance. A self-hosted platform provides full control over access policies, version history, and backup procedures — capabilities not guaranteed with public cloud services.

The three leading open-source platforms for hydrologic data management — Tethys Platform, HydroShare, and the CUAHSI HydroClient ecosystem — serve complementary roles in the water science data lifecycle. Tethys Platform provides a framework for building custom web applications on top of hydrologic models. HydroShare offers a collaborative repository for sharing and publishing water science data. The CUAHSI HydroClient provides discovery and access to federated water data services.

For the modeling side of hydrology, see our [hydrological modeling guide](../2026-06-10-self-hosted-hydrological-modeling-modflow-lisflood-wflow-guide/). For spatial data infrastructure, our [geospatial mapping servers comparison](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-ge/) covers complementary tools.

## Platform Comparison

| Feature | Tethys Platform | HydroShare | CUAHSI HydroClient |
|---------|----------------|------------|-------------------|
| Primary Role | Application development framework | Collaborative data repository | Federated data discovery |
| Architecture | Django + PostgreSQL + GeoServer | Django + Mezzanine CMS + iRODS | Desktop + web service client |
| Stars | 110 | 198 | N/A (ecosystem component) |
| Last Updated | May 2026 | June 2026 | Active ecosystem |
| Web Interface | Full (app builder + admin) | Full (resource landing pages) | Desktop GUI + JupyterHub |
| Data Storage | PostgreSQL/PostGIS | iRODS (federated storage) | Connects to remote services |
| API Support | REST API + app SDK | REST API (HS REST) | WaterOneFlow / WSDL |
| Docker Ready | Yes (Dockerfile) | Yes (Dockerfile) | Containerized JupyterHub |
| Authentication | Local + OAuth + LDAP | OAuth (HydroShare, Google, ORCID) | HydroShare OAuth |
| Best For | Building water data web apps | Publishing and sharing datasets | Discovering data from 100+ sources |

## Deployment Guide

### Tethys Platform Setup

Tethys Platform is designed around a "portal" concept where each installation hosts multiple hydrologic web apps. The recommended deployment uses Docker:

```bash
# Clone the repository
git clone https://github.com/tethysplatform/tethys.git
cd tethys

# Build and start with Docker
docker build -t tethys .
docker run -d --name tethys \
    -p 8000:8000 \
    -e DB_HOST=postgres \
    -e DB_PORT=5432 \
    -e DB_NAME=tethys \
    -e DB_USER=tethys_admin \
    --link postgres:postgres \
    tethys
```

For production, deploy with Docker Compose alongside PostgreSQL and GeoServer:

```yaml
# docker-compose.yml — Tethys Platform production stack
version: '3.8'
services:
  postgres:
    image: postgis/postgis:15-3.4
    environment:
      POSTGRES_DB: tethys
      POSTGRES_USER: tethys_admin
      POSTGRES_PASSWORD: secure_password
    volumes:
      - pgdata:/var/lib/postgresql/data

  tethys:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      DB_HOST: postgres
      DB_NAME: tethys
      DB_USER: tethys_admin
      DB_PASSWORD: secure_password
      SECRET_KEY: your_django_secret
    volumes:
      - ./workspaces:/var/lib/tethys/workspaces
      - ./static:/var/lib/tethys/static

  geoserver:
    image: kartoza/geoserver:2.24
    ports:
      - "8080:8080"
    volumes:
      - geoserver_data:/opt/geoserver/data_dir

volumes:
  pgdata:
  geoserver_data:
```

### HydroShare Installation

HydroShare uses a Django/Mezzanine CMS stack with iRODS for distributed storage:

```bash
# Clone and configure
git clone https://github.com/hydroshare/hydroshare.git
cd hydroshare

# Copy the local settings template
cp hydroshare/local_settings.py.example hydroshare/local_settings.py

# Edit key settings
# Set DATABASES to your PostgreSQL instance
# Set IRODS settings for storage backend
# Configure OAuth for ORCID, Google authentication

# Docker build
docker build -t hydroshare .
docker run -d --name hydroshare \
    -p 8000:8000 \
    -v /data/hydroshare:/hydroshare/data \
    hydroshare
```

### CUAHSI HydroClient Access

The HydroClient is primarily a desktop application for Windows, macOS, and Linux that connects to the CUAHSI Water Data Center catalog:

```bash
# Access via JupyterHub (Python API approach)
import hspy
from hs_restclient import HydroShare

# Connect to HydroShare
hs = HydroShare(host='www.hydroshare.org', auth=auth)

# Search for water quality data
results = hs.search(categories=['water quality'], 
                     bbox=[-105.0, 39.0, -104.0, 40.0])
for r in results:
    print(f"{r['title']}: {r['creator']}")

# Download resource files
hs.getResourceFile(resource_id, 'data/streamflow_2019_2024.csv',
                   destination='./local_data/')
```

## Building a Custom Water Quality Dashboard

One of Tethys Platform's strengths is its app SDK for building domain-specific dashboards. Here is a minimal example of a water quality monitoring app:

```python
# app.py — Tethys app for displaying water quality data
from tethys_sdk.base import TethysAppBase
from tethys_sdk.permissions import PermissionRequired

class WaterQualityMonitor(TethysAppBase):
    name = 'Water Quality Monitor'
    description = 'Real-time water quality parameter visualization'
    package = 'water_quality_monitor'
    
    def register_url_maps(self):
        return [
            ('home', 'water_quality_monitor', 'home'),
            ('station_detail', 'water_quality_monitor/{station_id}', 'station')
        ]
```

```python
# controllers.py — Fetch and display water quality data
import requests
from django.shortcuts import render
from tethys_sdk.gizmos import TimeSeries, MapView

def home(request):
    # Fetch data from CUAHSI WaterOneFlow service
    wof_url = "https://hydroportal.cuahsi.org/nwisuv/cuahsi_1_1.asmx"
    params = {
        'site': 'NWIS:01646500',
        'variable': 'NWIS:00060',  # Discharge
        'startDate': '2024-01-01',
        'endDate': '2024-12-31'
    }
    
    # Create time series plot
    ts_plot = TimeSeries(
        engine='highcharts',
        title='Potomac River Discharge at Little Falls',
        y_axis_label='Discharge (cfs)',
        series=[{
            'name': 'Observed',
            'data': fetch_waterml(wof_url, params)
        }]
    )
    
    context = {'ts_plot': ts_plot}
    return render(request, 'water_quality_monitor/home.html', context)
```

## Choosing Between Data Platforms and Modeling Frameworks

A common question in water science computing is whether you need a data platform or a modeling framework. The distinction matters:

- **Data Platforms** (Tethys, HydroShare): Store, catalog, discover, and share datasets. They provide web interfaces for browsing time series, spatial data, and documents. Use these when your primary need is organizing observational data from multiple sources for team access.

- **Modeling Frameworks** (MODFLOW, LISFLOOD, Wflow): Execute hydrologic simulations — groundwater flow, flood inundation, rainfall-runoff. They produce predictions from input parameters. Use these when your primary need is running simulations.

In practice, the two integrate: Tethys Platform apps commonly wrap MODFLOW models behind web interfaces, and model outputs are published to HydroShare as citable resources with DOIs.

## Data Standards and Interoperability

Hydrologic data platforms gain their power from adherence to open standards that enable cross-system data exchange. The WaterML 2.0 standard, developed by the Open Geospatial Consortium (OGC), defines an XML schema for water observations — including time series of discharge, stage, groundwater levels, and water quality parameters — that all three platforms support natively.

HydroShare assigns Digital Object Identifiers (DOIs) to published datasets through its DataCite integration, making water science data formally citable in academic publications. Each resource receives a landing page with structured metadata conforming to the Dublin Core and ISO 19115 geographic metadata standards. This means a researcher publishing streamflow data on HydroShare can include the DOI in a journal article, and readers can directly access the underlying data with full version history.

Tethys Platform apps commonly consume WaterML services from USGS and CUAHSI endpoints while publishing results through OGC Web Map Service (WMS) and Web Feature Service (WFS) standards via the bundled GeoServer instance. This standards-based architecture enables a Tethys dashboard displaying real-time reservoir levels to composite data from three different agencies, each exposing their data through slightly different web services, without custom ETL code for each source.

For organizations operating across institutional boundaries — a state water board coordinating with federal agencies, university researchers, and municipal utilities — this standards compliance is not optional. It is the difference between a platform that integrates into existing workflows and one that becomes another isolated data silo.


## FAQ

### What hardware requirements should I plan for?

A Tethys Platform deployment with PostgreSQL, GeoServer, and 3-4 custom apps runs comfortably on 8 GB RAM and 4 CPU cores. HydroShare requires additional storage orchestrated through iRODS — budget 16 GB RAM minimum for a production instance serving 50+ users. The HydroClient software runs on any modern laptop (4 GB RAM).

### How does HydroShare handle large datasets?

HydroShare uses iRODS (integrated Rule-Oriented Data System) as its storage backend, which supports federated storage across multiple physical locations. Individual resources can be up to 64 GB by default, with larger allocations available through the CUAHSI consortium. Data is stored with checksums, replicated across iRODS zones, and versioned automatically. For datasets exceeding 1 TB, HydroShare supports linking to external storage systems via the iRODS federation protocol.

### Can I federate my Tethys Portal with CUAHSI WaterOneFlow?

Yes. Tethys apps can publish data as WaterOneFlow (WaterML) web services, making your local data discoverable through the CUAHSI catalog. Configure the Tethys WaterML app from the Tethys App Library and register your service endpoint with the CUAHSI HIS Central catalog. Once registered, your data appears alongside USGS, EPA, and NOAA datasets in the HydroClient search interface.

### Is OAuth integration required, or can I use local authentication?

Both Tethys and HydroShare support local username/password authentication out of the box. OAuth providers (ORCID, Google, GitHub) simplify user management for multi-institutional collaborations but are optional. For air-gapped deployments in secure facilities, local Django authentication with Tethys's LDAP backend integration provides domain-joined access without external OAuth dependencies.

### How do these platforms compare to commercial LIMS for water quality labs?

Commercial LIMS (Laboratory Information Management Systems) focus on sample tracking, chain of custody, and regulatory compliance reporting for individual labs. Tethys and HydroShare serve the broader data lifecycle — from field sensor telemetry to published datasets with DOIs. Many water quality labs run both: a LIMS for internal sample management and HydroShare for publishing finalized datasets for public access and research collaboration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Hydrologic Data Platforms: Tethys Platform vs HydroShare vs CUAHSI HydroClient",
  "description": "Comprehensive comparison of open-source hydrologic data management platforms: Tethys Platform for building water data web apps, HydroShare for collaborative dataset publishing, and CUAHSI HydroClient for federated water data discovery. Includes Docker Compose deployment, WaterML integration, and custom dashboard development guide.",
  "datePublished": "2026-06-12",
  "dateModified": "2026-06-12",
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
