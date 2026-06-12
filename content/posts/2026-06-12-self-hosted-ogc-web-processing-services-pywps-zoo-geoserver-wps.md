---
title: "Self-Hosted OGC Web Processing Services: PyWPS vs ZOO-Project vs GeoServer WPS"
date: "2026-06-12"
tags: ["geospatial", "ogc", "data-processing", "gis", "wps", "geoserver", "scientific-computing"]
draft: false
---

## Introduction

Geospatial data processing — from satellite image analysis to hydrological modeling to spatial statistics — often requires significant computational resources. Rather than running these operations on individual workstations, the OGC **Web Processing Service (WPS)** standard enables you to deploy geoprocessing algorithms as network-accessible services that any OGC-compatible client can invoke.

This article compares three open-source WPS implementations: **PyWPS** (a Python-based WPS 2.0 server), **ZOO-Project** (a polyglot WPS platform supporting multiple languages), and **GeoServer WPS** (the built-in processing module of the popular GeoServer platform).

| Feature | PyWPS | ZOO-Project | GeoServer WPS |
|---------|:-----:|:-----------:|:-------------:|
| OGC Standard | WPS 2.0 | WPS 1.0 / 2.0 | WPS 1.0 |
| Language | Python | C, Python, Java, R, JS | Java |
| Process Hosting | Flask + Python functions | CGI/ZOO-Kernel + Services | Built-in GeoServer extension |
| Docker Support | ✓ (official image) | ✓ (community) | ✓ (via GeoServer image) |
| Async Execution | ✓ | ✓ | Limited |
| Results Storage | Local / S3 | Local / PostgreSQL | GeoServer data stores |
| Stars | 185+ | 37+ | 4,372+ (GeoServer) |
| License | MIT | MIT | GPL v2 |

## PyWPS: Python-Powered Geoprocessing

PyWPS is the most popular open-source WPS implementation for Python-based geoprocessing. It wraps any Python function as an OGC WPS 2.0 process, making it ideal for scientific computing, raster analysis, and integration with the Python geospatial ecosystem (GDAL, Rasterio, Shapely, NumPy, xarray).

Deploy PyWPS with Docker:

```yaml
version: "3.8"
services:
  pywps:
    image: geopython/pywps:latest
    ports:
      - "5000:5000"
    environment:
      - PYWPS_CFG=/etc/pywps/pywps.cfg
      - PYWPS_PROCESSES=/processes
    volumes:
      - ./pywps.cfg:/etc/pywps/pywps.cfg
      - ./processes:/processes
      - pywps_outputs:/tmp
    restart: unless-stopped

volumes:
  pywps_outputs:
```

Define a processing function:

```python
# processes/buffer_analysis.py
from pywps import Process, LiteralInput, ComplexInput, ComplexOutput
from pywps import Format
import geopandas as gpd
import tempfile
import json

class BufferAnalysis(Process):
    def __init__(self):
        inputs = [
            ComplexInput('input_geojson', 'Input GeoJSON',
                         supported_formats=[Format('application/json')]),
            LiteralInput('distance', 'Buffer distance (meters)',
                         data_type='float')
        ]
        outputs = [
            ComplexOutput('output_geojson', 'Buffered GeoJSON',
                          supported_formats=[Format('application/json')])
        ]
        super().__init__(
            self._handler, identifier='buffer_analysis',
            title='Buffer Analysis', version='1.0',
            inputs=inputs, outputs=outputs
        )

    def _handler(self, request, response):
        gdf = gpd.read_file(request.inputs['input_geojson'][0].file)
        distance = float(request.inputs['distance'][0].data)
        buffered = gdf.buffer(distance)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            buffered.to_file(f.name, driver='GeoJSON')
            response.outputs['output_geojson'].file = f.name
        return response
```

PyWPS excels at wrapping scientific Python workflows — climate model post-processing, hydrological analysis, vegetation index calculation — as standardized web services.

## ZOO-Project: Polyglot Processing Platform

ZOO-Project takes a unique approach by supporting processing algorithms written in **any** programming language. Its CGI-based architecture uses ZOO-Kernel to manage process execution, while individual services can be implemented in Python, R, Java, JavaScript, C, or even shell scripts.

```yaml
version: "3.8"
services:
  zoo:
    image: zoo-project/zoo-project:latest
    ports:
      - "8080:8080"
    volumes:
      - ./services/cgi-env:/usr/lib/cgi-bin
      - zoo_data:/var/www/html/data
    environment:
      - MAPFILE=/var/www/html/data/demo.map

volumes:
  zoo_data:
```

A ZOO service in Python:

```python
#!/usr/bin/env python3
# services/cgi-env/hello_world.py
import json

def hello_world(conf, inputs, outputs):
    name = inputs["name"]["value"]
    result = {"greeting": f"Hello, {name}! Processing complete."}
    outputs["Result"]["value"] = json.dumps(result)
    return 3  # SERVICE_SUCCEEDED
```

ZOO-Project is particularly useful when your organization has geoprocessing code scattered across multiple languages and you need a unified WPS interface without rewriting everything.

## GeoServer WPS: Built-In Processing Extension

GeoServer, the most popular open-source map server (4,372+ stars), includes a WPS module that exposes its internal rendering and analysis capabilities as standardized processes. Rather than writing custom processing code, you leverage GeoServer's existing operations — reprojection, raster-to-vector conversion, spatial queries, and more.

```yaml
version: "3.8"
services:
  geoserver:
    image: docker.osgeo.org/geoserver:2.26-latest
    ports:
      - "8080:8080"
    environment:
      - INSTALL_EXTENSIONS=true
      - STABLE_EXTENSIONS=wps
      - GEOSERVER_ADMIN_USER=admin
      - GEOSERVER_ADMIN_PASSWORD=geoserver
    volumes:
      - geoserver_data:/opt/geoserver_data

volumes:
  geoserver_data:
```

Invoke a WPS process through the GeoServer REST interface:

```bash
curl -X POST "http://localhost:8080/geoserver/wps" \
  -H "Content-Type: application/xml" \
  -d '<wps:Execute service="WPS" version="1.0.0"
  xmlns:wps="http://www.opengis.net/wps/1.0.0">
    <ows:Identifier>gs:Reproject</ows:Identifier>
    <wps:DataInputs>
      <wps:Input>
        <ows:Identifier>features</ows:Identifier>
        <wps:Reference xlink:href="http://localhost:8080/geoserver/topp/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=topp:states"/>
      </wps:Input>
      <wps:Input>
        <ows:Identifier>targetCRS</ows:Identifier>
        <wps:Data><wps:LiteralData>EPSG:4326</wps:LiteralData></wps:Data>
      </wps:Input>
    </wps:DataInputs>
    <wps:ResponseForm>
      <wps:RawDataOutput mimeType="application/json">
        <ows:Identifier>result</ows:Identifier>
      </wps:RawDataOutput>
    </wps:ResponseForm>
  </wps:Execute>'
```

GeoServer WPS is the lowest-friction option if you already run GeoServer — you get geoprocessing capabilities without deploying additional infrastructure.

## Choosing the Right WPS Engine

- **Choose PyWPS** for scientific Python workflows. If your team already uses Jupyter notebooks, GDAL, or scikit-learn for geospatial analysis, PyWPS wraps your existing code as web services with minimal overhead.
- **Choose ZOO-Project** for polyglot environments where geoprocessing code exists in multiple languages. Its CGI architecture lets you wrap R statistical models, C++ image processors, and Python scripts under a single WPS endpoint.
- **Choose GeoServer WPS** if GeoServer is already your mapping backbone. It provides immediate access to spatial processing without deploying new services.

## Why Self-Host Your Geoprocessing Infrastructure?

Cloud-based geoprocessing services (ArcGIS Online, Google Earth Engine) impose usage quotas, data egress fees, and vendor lock-in. Self-hosted WPS services eliminate ongoing per-computation costs and give you total control over algorithm versions, data residency, and processing throughput.

This is critical for reproducible science — when a published analysis depends on a specific version of a processing algorithm, you cannot afford to have that version changed or deprecated by a cloud vendor. Self-hosted WPS with version-controlled Docker images ensures your geoprocessing environment is permanently reproducible.

The OGC WPS standard also enables loose coupling between data servers and processing engines. For interactive map visualization, see our [self-hosted GIS web map viewers](../2026-06-09-self-hosted-gis-web-map-viewers-qgis-server-mapbender-lizmap/). For discovering datasets to feed into your WPS processes, check our [geospatial catalog services guide](../2026-06-09-self-hosted-geospatial-catalog-pygeoapi-pycsw-geonetwork-guide/). And for understanding the underlying map serving infrastructure, see our [geospatial mapping servers comparison](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/).

## Performance Optimization and Production Deployment

WPS services are inherently compute-intensive — unlike typical web applications that serve pre-computed responses, each WPS request triggers actual geoprocessing. This has significant implications for deployment architecture.

For PyWPS deployments, the standard approach uses Gunicorn with multiple worker processes behind an NGINX or Caddy reverse proxy. Each Gunicorn worker handles one request at a time, so size your worker count based on expected concurrent processing load. For CPU-bound raster operations (GDAL Warp, DEM processing), limit workers to the number of physical CPU cores. For I/O-bound operations (database queries, file format conversions), you can oversubscribe workers by 2–3x.

Process-level isolation is critical for production environments. Rather than running all WPS processes in a single Python interpreter (where a crash in one process kills everything), deploy PyWPS with separate Gunicorn instances for different process categories — one for quick statistical computations, another for long-running raster analysis. Configure request timeouts appropriately for each category.

For ZOO-Project, the CGI architecture naturally isolates each process execution, but this comes with process startup overhead. Mitigate this by using FastCGI instead of plain CGI for frequently invoked services, and pre-warm commonly used interpreters. For Java-based processes, use a persistent JVM application server (Tomcat) rather than spawning a new JVM per request — this can reduce cold-start latency from seconds to milliseconds.

Output caching dramatically improves response times for identical inputs. Both PyWPS and ZOO-Project support configuring result storage backends — use a shared Redis cache for frequently requested computations and S3-compatible object storage (MinIO) for large result files. Configure appropriate cache TTLs based on how often your input data changes: weather model outputs might have a 6-hour TTL, while static DEM analysis results can be cached indefinitely.

Monitoring WPS deployments requires both infrastructure metrics (CPU, memory, disk) and domain-specific metrics (job queue depth, average execution time per process type, cache hit rate). Prometheus with the Node Exporter and a custom WPS metrics exporter gives you full observability. Set up alerting for job queue backlogs exceeding 5 minutes and for individual process execution times that deviate significantly from historical baselines. For the underlying map server infrastructure, see our [geospatial mapping servers guide](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/).


## FAQ

### What is the OGC WPS standard?

The Web Processing Service (WPS) is an OGC standard that defines how geoprocessing algorithms can be invoked over HTTP. It specifies interfaces for describing processes (GetCapabilities), requesting process details (DescribeProcess), and executing computations (Execute). WPS 2.0 added RESTful bindings and improved asynchronous execution support.

### Can I run computationally intensive processes via WPS?

Yes. Both PyWPS and ZOO-Project support asynchronous execution — you submit a job, receive a status URL, and poll for completion. For heavy processing (climate model runs, multi-GB raster operations), deploy the WPS server on dedicated compute hardware and configure worker queues using Redis or Celery for PyWPS.

### How do I handle large input/output files?

WPS supports both inline data (included in the request body) and referenced data (URLs to external files). For large datasets, use referenced inputs pointing to files on your network storage or object store. Most WPS implementations also support streaming outputs to avoid buffering entire results in memory.

### Does GeoServer WPS support custom processing algorithms?

GeoServer WPS exposes built-in GeoServer operations as processes, but you can also register custom WPS processes via Java plugins implementing the `ProcessFactory` interface. However, for extensive custom processing, PyWPS or ZOO-Project provide more developer-friendly extension mechanisms.

### What's the recommended deployment for production WPS?

Deploy behind a reverse proxy (Caddy or NGINX) with TLS termination. For PyWPS, use Gunicorn as the WSGI server. For ZOO-Project, Apache with FastCGI is the standard setup. All three benefit from PostgreSQL/PostGIS for storing processing results and job metadata. Monitor with Prometheus + Grafana for visibility into job queues and execution times.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted OGC Web Processing Services: PyWPS vs ZOO-Project vs GeoServer WPS",
  "description": "Compare open-source OGC WPS engines — PyWPS, ZOO-Project, and GeoServer WPS — for self-hosting geoprocessing services. Includes Docker deployments, Python code examples, and REST API calls.",
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
