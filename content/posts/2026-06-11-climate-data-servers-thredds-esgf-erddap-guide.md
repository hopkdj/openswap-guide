---
title: "Self-Hosted Climate & Environmental Data Servers: THREDDS vs ESGF vs ERDDAP"
date: "2026-06-11"
tags: ["climate-data", "environmental-data", "thredds", "esgf", "erddap", "netcdf", "scientific-data", "open-science", "self-hosted", "data-server", "geoscience"]
draft: false
---

## Introduction

Climate science and environmental monitoring generate petabytes of data annually — from satellite observations and weather models to ocean buoy readings and ice core samples. Making this data accessible to researchers worldwide requires specialized data servers that understand scientific data formats like NetCDF, HDF5, and GRIB, provide efficient subsetting and aggregation, and expose standardized web service interfaces.

Unlike general-purpose file servers, climate data servers must handle multi-dimensional gridded data (time × latitude × longitude × variable), support on-the-fly subsetting and reprojection, and serve data through OGC-compliant protocols like WMS, WCS, and OPeNDAP. This article compares three leading open-source platforms for self-hosting climate and environmental data: **THREDDS Data Server (TDS)** from Unidata, the **Earth System Grid Federation (ESGF)** node software, and **ERDDAP** from NOAA.

## Comparison Table

| Feature | THREDDS Data Server | ESGF Node | ERDDAP |
|---------|---------------------|-----------|--------|
| **Primary Role** | Scientific data catalog and access server | Federated climate data node | Environmental data server with subsetting |
| **GitHub Stars** | 264+ (Unidata/thredds) | 20+ (ESGF/esgf-installer) | N/A (NOAA-hosted) |
| **Language** | Java (Spring) | Python + Bash | Java (Servlet) |
| **Maintainer** | Unidata / UCAR | ESGF Collaboration (multi-institutional) | NOAA / NMFS |
| **Docker Support** | Yes (community images) | Yes (Ansible-based deployment) | Yes (official Docker) |
| **Data Formats** | NetCDF, HDF5, GRIB, BUFR, NcML | NetCDF, CMIP-standard | NetCDF, HDF, CSV, JSON, XML |
| **Protocols** | OPeNDAP, WMS, WCS, WFS, HTTP, ncISO | ESGF Search API, Globus, HTTP | OPeNDAP, WMS, ERDDAP tabledap/griddap |
| **Federation** | THREDDS Catalogs (hierarchical) | ESGF Federation (P2P index) | Standalone (multi-server via EDAC) |
| **Subsetting** | Server-side (ncss) | Server-side (via ESGF Compute) | Server-side (full subsetting engine) |
| **Metadata Standards** | ISO 19115, ACDD, CF Conventions | CIM (Climate Model Metadata) | CF Conventions, ACDD, ISO 19115 |
| **User Base** | 500+ data servers worldwide | 50+ federation nodes globally | 100+ servers at research institutions |
| **Production Maturity** | 20+ years (mature) | 15+ years (mature but complex) | 15+ years (mature) |

## THREDDS Data Server (TDS): The Scientific Data Workhorse

The THREDDS Data Server is the most widely deployed scientific data server in the geoscience community, with over 500 installations serving everything from real-time weather radar data to climate model outputs. Developed and maintained by Unidata (UCAR), TDS provides a unified interface for discovering and accessing scientific datasets stored in self-describing formats.

### Key Features

- **OPeNDAP Protocol**: Industry-standard protocol for remote data access with subsetting — clients can request specific variable slices from massive datasets without downloading the entire file
- **NetCDF Subset Service (NCSS)**: Gridded data subsetting by spatial bounding box, time range, and variable selection — returns NetCDF, CSV, or XML
- **WMS/WCS Support**: OGC Web Map Service for generating map images from gridded data, and Web Coverage Service for data extraction
- **THREDDS Catalogs**: Hierarchical XML catalog system that can aggregate thousands of datasets across multiple servers into a single searchable catalog
- **ncISO Metadata**: Automatic generation of ISO 19115 metadata from NetCDF files, enabling discovery through geospatial search engines

### Docker Deployment

```yaml
version: "3.8"
services:
  thredds:
    image: unidata/thredds-docker:latest
    container_name: thredds
    ports:
      - "8443:8443"
      - "8080:8080"
    environment:
      - TDS_CONTENT_ROOT_PATH=/usr/local/tomcat/content/thredds
      - TDS_JVM_MAX_HEAP=4G
      - TDS_HOST=climate-data.example.edu
    volumes:
      - ./thredds-config:/usr/local/tomcat/content/thredds
      - /data/climate:/data/climate:ro
      - ./logs:/usr/local/tomcat/logs
    restart: unless-stopped
```

### Catalog Configuration

```xml
<?xml version="1.0" encoding="UTF-8"?>
<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
         xmlns:xlink="http://www.w3.org/1999/xlink"
         name="Climate Data Server" version="1.2">

  <service name="all" base="" serviceType="Compound">
    <service name="odap" serviceType="OPENDAP" base="/thredds/dodsC/"/>
    <service name="http" serviceType="HTTPServer" base="/thredds/fileServer/"/>
    <service name="wms" serviceType="WMS" base="/thredds/wms/"/>
    <service name="ncss" serviceType="NetcdfSubset" base="/thredds/ncss/"/>
  </service>

  <datasetScan name="CMIP6 Model Output" ID="cmip6"
               path="cmip6" location="/data/climate/cmip6">
    <metadata inherited="true">
      <serviceName>all</serviceName>
      <dataType>Grid</dataType>
    </metadata>
    <filter>
      <include wildcard="*.nc"/>
    </filter>
    <addDatasetSize/>
  </datasetScan>
</catalog>
```

### Accessing Data via OPeNDAP

```python
import xarray as xr

# Access a THREDDS-served dataset with subsetting
url = "http://climate-data.example.edu/thredds/dodsC/cmip6/tas_Amon_model1_historical.nc"
ds = xr.open_dataset(url)

# Subset by region and time before downloading
subset = ds.sel(lat=slice(30, 60), lon=slice(-130, -60),
                time=slice("2000-01-01", "2020-12-31"))
print(subset)
```

## ESGF Node: The Federated Climate Data Grid

The Earth System Grid Federation (ESGF) is a peer-to-peer network of data nodes that collectively serve the world's climate model data, most famously the Coupled Model Intercomparison Project (CMIP) datasets used by the IPCC. Running an ESGF node means joining a global federation where your institution's climate data becomes discoverable and accessible to thousands of researchers worldwide.

### Key Features

- **Federated Search**: Your node's data is indexed and searchable through the global ESGF search portal alongside data from 50+ other nodes
- **Globus Transfer**: High-performance, reliable data transfer using the Globus toolkit with automatic retry and checksumming
- **CMIP Standards**: Built-in support for CMIP5, CMIP6, CORDEX, and other climate model intercomparison project data structures
- **Replication**: Automatic data replication between nodes for load balancing and geographic distribution
- **Identity Federation**: Single sign-on across the federation using OpenID Connect and X.509 certificates

### Node Deployment Architecture

```yaml
version: "3.8"
services:
  esgf-index:
    image: esgf/esgf-index:latest
    container_name: esgf-index
    ports:
      - "8983:8983"
    environment:
      - SOLR_HEAP=4G
    volumes:
      - ./solr-data:/var/solr
      - ./index-config:/opt/solr/server/solr/configsets
    restart: unless-stopped

  esgf-idp:
    image: esgf/esgf-idp:latest
    container_name: esgf-idp
    ports:
      - "8443:8443"
    environment:
      - ESGF_HOSTNAME=esgf-node.example.edu
      - ESGF_ORGANIZATION=Example University
    volumes:
      - ./certs:/etc/grid-security
    restart: unless-stopped

  esgf-tds:
    image: esgf/esgf-thredds:latest
    container_name: esgf-tds
    ports:
      - "8080:8080"
    environment:
      - TDS_CONTENT_ROOT=/esg/content/thredds
    volumes:
      - /data/climate:/esg/content/thredds/data:ro
    restart: unless-stopped

  esgf-publisher:
    image: esgf/esgf-publisher:latest
    container_name: esgf-publisher
    environment:
      - ESGF_INDEX_HOST=esgf-index
      - ESGF_TDS_HOST=esgf-tds
    volumes:
      - /data/climate:/data/climate:ro
      - ./publisher-config:/etc/esg/publisher
    restart: unless-stopped
```

### Publishing Data to ESGF

```bash
# Map climate model files to the ESGF data model
esgmapfile --project cmip6 --map mapfile.txt \
  /data/climate/cmip6/tas_Amon_Model1_historical_r1i1p1f1_*.nc

# Publish to the local ESGF index
esgpublish --map mapfile.txt \
  --project cmip6 \
  --thredds-url http://esgf-node.example.edu:8080/thredds \
  --service fileservice \
  --noscan --commit

# Verify publication
esgsearch --project cmip6 --local-node-only \
  --query "variable:tas AND experiment:historical"
```

## ERDDAP: The Environmental Data Subsetter

ERDDAP (Environmental Research Division's Data Access Program), developed by NOAA's Southwest Fisheries Science Center, takes a user-friendly approach to scientific data serving. It excels at making heterogeneous datasets — from satellite imagery and model outputs to buoy observations and tabular data — accessible through a consistent RESTful API with powerful subsetting capabilities.

### Key Features

- **Unified Data Model**: ERDDAP treats all datasets (gridded or tabular) consistently, enabling users to request data in their preferred format regardless of the native storage format
- **Powerful Subsetting**: Users can subset by any dimension (time, space, variable) and request output in 30+ formats including NetCDF, CSV, JSON, MATLAB, and GeoJSON
- **Standardized URLs**: Every dataset has a predictable REST API URL pattern, making automated data access straightforward
- **Automatic Graphing**: Built-in visualization via the "Make A Graph" web interface with interactive time series and map plots
- **ISO 19115 Metadata**: Automatic generation of standards-compliant metadata for dataset discovery

### Docker Deployment

```yaml
version: "3.8"
services:
  erddap:
    image: axiom/docker-erddap:latest
    container_name: erddap
    ports:
      - "8080:8080"
    environment:
      - ERDDAP_MIN_MEMORY=2G
      - ERDDAP_MAX_MEMORY=4G
      - ERDDAP_baseUrl=http://climate-data.example.edu:8080
      - ERDDAP_baseHttpsUrl=https://climate-data.example.edu
      - ERDDAP_email=admin@example.edu
    volumes:
      - ./erddap-content:/usr/local/tomcat/content/erddap
      - /data/climate:/data/climate:ro
      - ./logs:/usr/local/tomcat/logs
      - ./erddap-bigParentDirectory:/erddapData
    restart: unless-stopped
```

### Dataset Configuration

```xml
<!-- datasets.xml fragment for ERDDAP -->
<dataset type="EDDGridFromNcFiles" datasetID="cmip6_tas_daily"
         active="true">
  <reloadEveryNMinutes>60</reloadEveryNMinutes>
  <updateEveryNMillis>10000</updateEveryNMillis>

  <fileDir>/data/climate/cmip6/tas/</fileDir>
  <fileNameRegex>tas_day_.*\.nc</fileNameRegex>

  <metadata>
    <att name="title">CMIP6 Daily Near-Surface Air Temperature</att>
    <att name="summary">Historical and scenario daily mean near-surface
      air temperature from CMIP6 models.</att>
    <att name="cdm_data_type">Grid</att>
    <att name="Conventions">CF-1.7, ACDD-1.3</att>
    <att name="creator_name">Example Climate Research Group</att>
    <att name="institution">Example University</att>
    <att name="license">CC-BY-4.0</att>
  </metadata>

  <addAttributes>
    <att name="time_units">days since 1850-01-01</att>
  </addAttributes>
</dataset>
```

### Accessing ERDDAP Data via REST API

```bash
# Get dataset metadata as JSON
curl "http://climate-data.example.edu:8080/erddap/info/cmip6_tas_daily/index.json"

# Subset data: specific time range, region, output as CSV
curl "http://climate-data.example.edu:8080/erddap/griddap/cmip6_tas_daily.csv?\
tas%5B(2020-01-01T00:00:00Z):1:(2020-12-31T00:00:00Z)%5D%5B(30):1:(60)%5D%5B(-130):1:(-60)%5D"

# Download as NetCDF
curl -O "http://climate-data.example.edu:8080/erddap/griddap/cmip6_tas_daily.nc?\
tas%5B(2020-01-01T00:00:00Z):1:(2020-12-31T00:00:00Z)%5D%5B(30):1:(60)%5D%5B(-130):1:(-60)%5D"
```

## Why Self-Host Climate Data Servers?

The climate science community has a long tradition of open data sharing, exemplified by the CMIP project where modeling centers worldwide contribute petabytes of simulation output to a shared pool. However, relying solely on centralized data portals creates bottlenecks: during IPCC assessment cycles, demand spikes can overwhelm download servers, and researchers in regions with limited international bandwidth face excessive wait times.

Self-hosting a climate data node addresses these challenges through **geographic distribution**. By replicating commonly requested datasets to your regional server, you reduce international bandwidth consumption, provide faster access to local researchers, and contribute to the resilience of the global climate data infrastructure. This model of federated data sharing is analogous to our [distributed tracing infrastructure guide](../2026-05-06-self-hosted-distributed-tracing-jaeger-grafana-tempo-signoz-guide/), where observability data is distributed across nodes for reliability and performance.

Additionally, self-hosting enables **custom data services** beyond what centralized portals offer. You can integrate real-time weather station feeds, run on-the-fly regridding or bias correction services, and combine climate model outputs with local observational data for customized regional climate services. Our [weather forecasting platform guide](../2026-06-08-weather-forecasting-wrf-vs-ufs-vs-wrf-hydro/) covers running your own weather models, which naturally pair with THREDDS or ERDDAP for data distribution. For institutions doing large-scale geospatial analysis, our [geospatial catalog server guide](../2026-06-09-self-hosted-geospatial-catalog-pygeoapi-pycsw-geonetwork-guide/) and [earth observation platform guide](../2026-06-11-earth-observation-platforms-opendatacube-orfeo-toolbox-openeo/) provide complementary tools for satellite data processing and serving.

**Scientific reproducibility** is another compelling reason. Climate research results depend on specific model versions and data subsets. By self-hosting exact versions of the datasets used in your published research, you ensure that future researchers can exactly reproduce your analysis — something that cannot be guaranteed when relying on external portals that may update or remove older data versions.

## Hardware and Storage Planning

Climate data is storage-intensive. A single CMIP6 model run can produce tens of terabytes. When planning your deployment, consider these guidelines:

| Deployment Scale | Storage | RAM | CPU | Use Case |
|-----------------|---------|-----|-----|----------|
| **Small (departmental)** | 10-50 TB | 16 GB | 8 cores | Serving selected regional datasets |
| **Medium (institutional)** | 50-200 TB | 32 GB | 16 cores | Complete CMIP6 for one domain |
| **Large (national node)** | 200+ TB | 64+ GB | 32+ cores | Full CMIP6 + CORDEX + reanalysis |

For storage, ZFS or Ceph provides the data integrity guarantees needed for long-term scientific data preservation. Consider using SSD-backed metadata storage (for catalog indexes and database) with HDD-backed bulk data storage.

## Choosing the Right Platform

**Choose THREDDS if:**
- You need OGC standards compliance (WMS, WCS, WFS)
- You are serving diverse data types (gridded, point, radial, trajectory)
- You want hierarchical catalog aggregation across multiple servers
- You are already part of the Unidata/UCAR ecosystem

**Choose ESGF if:**
- You are contributing to CMIP or other international climate model intercomparison projects
- You need federated search and discovery across a global network
- Your institution is a climate modeling center publishing model outputs
- You need Globus-based high-performance data transfer

**Choose ERDDAP if:**
- You need the easiest path to serving scientific data with a REST API
- Your users require subsetting and format conversion on-the-fly
- You are serving tabular data alongside gridded data from a single platform
- You want built-in visualization and graphing capabilities

## FAQ

### Can THREDDS and ERDDAP run on the same server?

Yes, and many institutions do exactly this. THREDDS serves as the primary OPeNDAP/WMS endpoint with catalog aggregation, while ERDDAP provides the user-friendly REST API and subsetting interface. Since both read the same NetCDF files directly from disk, there is no data duplication. Configure them to share read-only access to your data directories.

### How do I handle data that exceeds available disk space?

For large climate archives, implement a tiered storage strategy. Keep frequently accessed datasets (current year, popular CMIP6 experiments) on fast local storage, and use THREDDS aggregation to create virtual datasets that span local and remote data. ERDDAP supports cache directories where subset results can be served from a hot cache. For long-term archival, integrate with tape libraries or object storage systems.

### Is ESGF overkill for a single institution?

If you are not contributing data to CMIP or similar international projects, yes — ESGF's federation complexity is unnecessary. THREDDS or ERDDAP alone can serve your needs with much lower operational overhead. ESGF makes sense when your data needs to be discoverable through the global ESGF search portal and accessible to the international climate modeling community.

### What data formats should I standardize on?

NetCDF4 with CF (Climate and Forecast) Conventions is the gold standard for climate and environmental data. It is self-describing, supports compression, and is natively supported by all three platforms. GRIB (common in operational weather forecasting) is supported by THREDDS with the GRIB feature collection. HDF5 is supported but CF-compliant NetCDF4 is strongly preferred for interoperability.

### How do users discover datasets on my server?

THREDDS provides hierarchical catalog browsing at the base URL. ERDDAP offers a searchable dataset list with faceted filtering by category. For broader discovery, register your server with DataONE, the ESGF search portal (if you are a federation node), or Google Dataset Search by ensuring your datasets have schema.org/Dataset markup in their landing pages.

### Can I serve real-time streaming data?

ERDDAP supports the EDDTableFromAsciiFiles dataset type with near-real-time updates via file polling, making it suitable for environmental sensor networks and weather station data with 5-15 minute update intervals. For true streaming (sub-second latency), combine MQTT or Kafka ingestion with periodic NetCDF file generation that ERDDAP or THREDDS can serve.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Climate & Environmental Data Servers: THREDDS vs ESGF vs ERDDAP",
  "description": "Comprehensive comparison of three open-source platforms for serving climate and environmental data: THREDDS Data Server, ESGF Node, and ERDDAP. Includes Docker deployment, OPeNDAP/WMS configuration, and CMIP6 data serving best practices.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
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
