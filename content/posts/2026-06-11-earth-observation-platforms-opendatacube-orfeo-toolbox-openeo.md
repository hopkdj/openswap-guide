---
title: "Self-Hosted Earth Observation Platforms: OpenDataCube vs Orfeo Toolbox vs openEO"
date: "2026-06-11"
tags: ["earth-observation", "geospatial", "satellite-imagery", "scientific-computing", "remote-sensing", "data-platform", "python"]
draft: false
---

## Introduction

Earth observation (EO) data is exploding. The Copernicus Sentinel satellites alone generate over 12 terabytes of imagery daily. Landsat, MODIS, and commercial constellations add petabytes more. Processing this data at scale — calibrating, compositing, analyzing time series, extracting insights — requires purpose-built platforms that go far beyond what desktop GIS tools can handle.

In this guide, we compare three leading open-source platforms for self-hosted earth observation data management and analysis: **OpenDataCube** (ODC), the Australian-born platform for continental-scale time-series analysis; **Orfeo Toolbox** (OTB), the French space agency's powerful image processing library; and **openEO**, the European Space Agency-backed federated API standard for EO processing. Each represents a different philosophy: full-stack platform, algorithm library, and API federation.

| Feature | OpenDataCube | Orfeo Toolbox | openEO |
|---------|-------------|---------------|--------|
| **GitHub Stars** | 580 | 388 | 207 (Python client) |
| **Primary Language** | Python | C++ | Python (client), various backends |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Latest Update** | June 2026 | May 2026 | June 2026 |
| **Processing Model** | Index + query + analyze | CLI/C++/Python library | API-driven, multi-backend |
| **Web Interface** | Yes (ODC Explorer, OWS) | No (CLI + API only) | Yes (Web Editor, QGIS plugin) |
| **Docker Support** | Excellent (10+ images, 7.8M pulls) | Yes (orfeotoolbox/otb) | Yes (docker-compose for backend) |
| **Jupyter Integration** | First-class (xarray, Dask) | Via Python bindings | Native Python client |
| **Time Series** | Core feature | Manual (batch processing) | Via user-defined functions (UDFs) |
| **Cloud Optimized** | COGs, STAC, OGC compliant | GDAL-based (all formats) | Cloud-native, federation model |
| **Best For** | Multi-year satellite data cubes | Advanced image processing algorithms | Multi-backend, federated EO workflows |

## OpenDataCube: The Time-Series Powerhouse

OpenDataCube (ODC) was developed by Geoscience Australia and has since been adopted by Digital Earth Africa, Digital Earth Australia, and similar programs worldwide. Its core insight is that satellite imagery is most valuable when organized as a "data cube" — a multi-dimensional array with spatial (x, y) and temporal (t) axes, enabling efficient time-series queries like "give me the NDVI for this pixel every month for the last 10 years."

### Key Features

- **Data Cube Model**: Imagery is ingested into a structured database (PostgreSQL) with a metadata index. Queries retrieve data by bounding box, time range, and product type — the engine handles tiling, reprojection, and mosaicking transparently.
- **Time-Series Analysis**: Because data is organized along a temporal axis, operations like "calculate the mean NDVI for each month across 5 years" run in seconds. This enables trend analysis, change detection, and phenology monitoring at continental scale.
- **Full Web Stack**: ODC Explorer provides a browser-based interface for discovering and visualizing data cubes. The `datacube-ows` component exposes data via OGC Web Map Service (WMS) and Web Coverage Service (WCS) standards.
- **xarray + Dask Integration**: Python access uses xarray DataArrays and Datasets, with optional Dask-backed lazy computation for out-of-core processing of datasets larger than RAM.

### Docker Deployment

```yaml
# docker-compose.yml for OpenDataCube
version: '3'
services:
  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: datacube
      POSTGRES_USER: datacube
      POSTGRES_PASSWORD: datacube_pass
    volumes:
      - pgdata:/var/lib/postgresql/data

  datacube:
    image: opendatacube/datacube:latest
    depends_on:
      - postgres
    environment:
      DATACUBE_DB_URL: postgresql://datacube:datacube_pass@postgres/datacube
    volumes:
      - ./data:/data
      - ./datacube.conf:/root/.datacube.conf
    command: datacube system init

  explorer:
    image: opendatacube/explorer:latest
    ports:
      - "8080:8080"
    environment:
      DATACUBE_DB_URL: postgresql://datacube:datacube_pass@postgres/datacube

  ows:
    image: opendatacube/ows:latest
    ports:
      - "8081:8080"
    environment:
      DATACUBE_DB_URL: postgresql://datacube:datacube_pass@postgres/datacube

volumes:
  pgdata:
```

```bash
# Initialize and index Sentinel-2 data
docker compose up -d
datacube product add /data/sentinel-2-product.yaml
datacube dataset add /data/sentinel-2-datasets.yaml

# Query via Python
python3 -c "
import datacube
dc = datacube.Datacube()
data = dc.load(product='s2_l2a', x=(-122.4, -122.3), y=(37.7, 37.8),
               time=('2024-01', '2024-12'), measurements=['red', 'nir'])
ndvi = (data.nir - data.red) / (data.nir + data.red)
print(ndvi.mean(dim=['x', 'y']))
"
```

## Orfeo Toolbox: The Algorithm Workhorse

Orfeo Toolbox (OTB) is developed by CNES (the French space agency) and is the go-to library when you need serious image processing algorithms. While ODC excels at data management and time series, OTB excels at what you actually do to each image: orthorectification, pansharpening, segmentation, classification, feature extraction, and change detection.

### Key Features

- **350+ Processing Functions**: Radiometric calibration, atmospheric correction, orthorectification, image registration, pansharpening, segmentation (mean-shift, watershed), classification (SVM, Random Forest, deep learning via TensorFlow integration), object-based image analysis, SAR processing, and more.
- **Streaming Architecture**: OTB processes images in tiles with a pipeline/streaming model. This means you can process a 500GB Sentinel-2 mosaic on a machine with 8GB RAM — the pipeline streams tiles through the processing chain without loading the entire image.
- **Python + CLI + C++**: Use OTB from the command line (`otbcli_OrthoRectification`), from Python (`otbApplication`), or from C++ for maximum performance. The Python bindings enable integration with NumPy, scikit-learn, and Jupyter notebooks.
- **SAR Expertise**: OTB has one of the best open-source SAR (Synthetic Aperture Radar) processing stacks available, including Sentinel-1 TOPSAR processing, speckle filtering, polarimetric decomposition, and interferometry.

### Docker Deployment

```bash
# Pull and run Orfeo Toolbox
docker pull orfeotoolbox/otb:latest

# Run a processing chain
docker run --rm -v $(pwd)/data:/data orfeotoolbox/otb:latest \
  otbcli_OrthoRectification \
  -io.in /data/raw_image.tif \
  -io.out /data/ortho_image.tif \
  -map utm -map.utm.zone 33

# Use Python API inside the container
docker run --rm -v $(pwd)/data:/data orfeotoolbox/otb:latest \
  python3 -c "
import otbApplication
app = otbApplication.Registry.CreateApplication('OrthoRectification')
app.SetParameterString('io.in', '/data/raw_image.tif')
app.SetParameterString('io.out', '/data/ortho_image.tif')
app.SetParameterString('map', 'utm')
app.SetParameterInt('map.utm.zone', 33)
app.ExecuteAndWriteOutput()
"
```

## openEO: The Federated API Standard

openEO takes a fundamentally different approach: instead of building another processing engine, it defines a standard API that sits on top of any EO processing backend. A user writes one analysis (in Python, R, or JavaScript) that runs unchanged on Google Earth Engine, Sentinel Hub, a self-hosted openEO backend, or any compliant platform.

### Key Features

- **Backend Federation**: Write once, run anywhere. The same openEO process graph executes on different backends without modification — the user selects which backend to target at runtime. This prevents vendor lock-in and enables seamless migration between platforms.
- **User-Defined Functions (UDFs)**: openEO provides a powerful UDF system where you can inject Python or R code directly into the processing pipeline. UDFs run close to the data (server-side), eliminating data transfer bottlenecks.
- **Web Editor + QGIS Plugin**: The openEO Web Editor provides a graphical process graph builder for designing EO workflows visually. The QGIS plugin brings openEO processing directly into the most popular desktop GIS.
- **Self-Hosted Backend**: The `openeo-geopyspark-driver` provides a complete self-hosted backend using GeoPySpark for distributed processing. Deploy it with Docker Compose and connect the Web Editor or Python client to your own infrastructure.

### Docker Deployment (Self-Hosted Backend)

```bash
# Clone the GeoPySpark driver with local backend setup
git clone https://github.com/Open-EO/openeo-geopyspark-driver.git
cd openeo-geopyspark-driver/docker/local_openeo_server

# Start the self-hosted backend
docker compose up -d

# Connect from Python
python3 -c "
import openeo
connection = openeo.connect('http://localhost:8080')
connection.authenticate_basic('user', 'password')

# Define a processing workflow
datacube = connection.load_collection(
    'SENTINEL2_L2A',
    spatial_extent={'west': 5.0, 'east': 5.5, 'south': 51.0, 'north': 51.5},
    temporal_extent=['2024-06-01', '2024-06-30'],
    bands=['B04', 'B08']
)
ndvi = (datacube.band('B08') - datacube.band('B04')) / (datacube.band('B08') + datacube.band('B04'))
result = ndvi.download('ndvi_result.tif')
"
```

## Why Self-Host Your Earth Observation Platform?

Earth observation data is inherently large and geographically specific. When you process satellite imagery on cloud platforms, you pay egress fees to move data out, compute fees to process it, and storage fees to keep it. A self-hosted EO platform on your own infrastructure eliminates all three — your data sits on your storage, your computation runs on your hardware, and your results stay local.

For organizations with continuous monitoring needs (agricultural monitoring, deforestation tracking, urban growth analysis), self-hosting enables persistent processing pipelines that run on schedule without per-job cloud costs. A single server with 32 cores and 128GB RAM can process years of Sentinel-2 data for a region the size of a small country, continuously, for the cost of electricity and hardware amortization.

Data sovereignty is another critical consideration. Many EO applications involve sensitive locations — military installations, critical infrastructure, natural resource deposits. Self-hosting ensures that both the imagery and the analysis results never leave your controlled environment.

For related geospatial infrastructure, see our guide on [self-hosted geospatial mapping servers](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/) covering Nominatim, tileserver-gl, and GeoServer. If you need to serve processed results as map tiles, our [vector tile servers comparison](../2026-05-19-self-hosted-vector-tile-servers-tegola-vs-tileserver-gl-vs-martin-guide/) covers Tegola, tileserver-gl, and Martin. For storing geospatial results, check our [geospatial database comparison](../2026-05-20-self-hosted-geospatial-database-tile38-postgis-redis-guide/).

## Choosing the Right EO Platform

**Choose OpenDataCube if** your primary need is time-series analysis of satellite data at regional to continental scales. ODC's data cube model is unmatched for questions like "how has vegetation changed in this watershed over the last decade?" The Docker ecosystem is mature, and the ODC Explorer provides an accessible web interface for non-programmers.

**Choose Orfeo Toolbox if** you need advanced image processing algorithms — orthorectification, pansharpening, SAR processing, segmentation, classification. OTB's streaming pipeline architecture handles massive images on modest hardware, and the Python bindings enable integration with the broader scientific Python ecosystem.

**Choose openEO if** you need backend flexibility — the ability to develop on a cloud platform and deploy on self-hosted infrastructure (or vice versa). openEO's federation model is the most future-proof approach, avoiding lock-in to any single processing engine. The trade-off is that you need to assemble more components to get a fully working system.

## FAQ

### Can OpenDataCube handle commercial satellite data (Planet, Maxar)?

Yes, but it requires custom product definitions and ingestion scripts. ODC's data model is generic — you define a product YAML file describing the measurements, coordinate reference system, and metadata schema, then write an ingestion pipeline that populates the database. The community maintains product definitions for Sentinel-2, Landsat, and MODIS; commercial data requires custom work.

### Is Orfeo Toolbox suitable for real-time processing?

OTB's streaming architecture is designed for batch processing of large images, not real-time streaming. However, it can be integrated into near-real-time pipelines where images arrive on a schedule (e.g., every 5 days for Sentinel-2). For true real-time EO processing, consider coupling OTB with a message queue (RabbitMQ/Kafka) and triggering processing chains when new imagery is detected.

### How does openEO compare to Google Earth Engine?

openEO was designed as an open, federated alternative to Google Earth Engine's proprietary API. Functionally, they're similar: both provide a high-level API for EO processing with UDF support. The key difference is that openEO lets you choose (or self-host) the backend, while Earth Engine locks you into Google's infrastructure. openEO's Python client can even target Earth Engine as a backend via community adapters.

### What hardware do I need to self-host these platforms?

For regional-scale analysis (a few thousand square kilometers), a server with 16 cores, 64GB RAM, and 4TB SSD storage is sufficient for OpenDataCube or openEO. Orfeo Toolbox can process larger areas on the same hardware thanks to its streaming architecture. For continental-scale ODC deployments (Digital Earth Africa scale), you'll need multiple servers with distributed storage (Ceph/MinIO) and parallel processing (Dask distributed).

### Can these platforms share data with QGIS and other GIS tools?

Yes. All three output standard GeoTIFF files that open in any GIS. OpenDataCube exposes OGC WMS/WCS services that QGIS can consume as live layers. Orfeo Toolbox has a QGIS plugin for GUI-driven processing. openEO has a QGIS plugin that lets you run openEO workflows directly within the QGIS interface. See our [geospatial catalog guide](../2026-06-09-self-hosted-geospatial-catalog-pygeoapi-pycsw-geonetwork-guide/) for metadata management across your EO and GIS stack.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Earth Observation Platforms: OpenDataCube vs Orfeo Toolbox vs openEO",
  "description": "Compare three open-source earth observation platforms for self-hosting: OpenDataCube (time-series data cubes), Orfeo Toolbox (advanced image processing), and openEO (federated API standard). Includes Docker deployment guides and satellite imagery workflow examples.",
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
