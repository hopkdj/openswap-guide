---
title: "Self-Hosted 3D CAD Web Viewers: Online 3D Viewer vs OpenSCAD vs FreeCAD"
date: "2026-06-09"
tags: ["cad", "3d-viewer", "web-based-cad", "stl-viewer", "step-viewer", "openscad", "freecad", "self-hosted"]
draft: false
---

Sharing 3D CAD models with team members, clients, or the public shouldn't require everyone to install specialized software. Self-hosted 3D CAD web viewers let you serve interactive 3D models directly in the browser — no downloads, no licenses, instant access. In this guide, we compare three leading approaches: **Online 3D Viewer** (a dedicated web-based model viewer), **OpenSCAD** (programmatic CAD with web capabilities), and **FreeCAD** (full-featured parametric CAD with web export).

## Why Self-Host a 3D CAD Viewer?

Engineering teams share CAD models constantly — with manufacturing partners, quality assurance, clients, and cross-functional team members. Email attachments and file shares create version chaos. Cloud platforms like Onshape or Autodesk Viewer charge per-seat fees and store your intellectual property on their servers.

A self-hosted 3D viewer on your infrastructure keeps designs under your control. Team members access the latest version through a URL. External partners get view-only access without installing software. Version control integrates with your existing Git or PLM workflow.

For teams already running 3D printer farms, our [OctoPrint self-hosted 3D printer server guide](../2026-04-20-octoprint-vs-mainsail-vs-fluidd-self-hosted-3d-printer-server-guide-2026/) covers the manufacturing side. CAD viewing complements your existing maker infrastructure by making designs accessible before they reach the printer. For broader self-hosted geospatial work, our [GIS raster processing guide](../2026-06-09-self-hosted-gis-raster-processing-gdal-grass-whitebox-otb/) covers 2D spatial data pipelines.

A self-hosted viewer removes barriers to design review. Stakeholders who wouldn't install Fusion 360 or SolidWorks can review a 3D model in their browser in seconds. This accelerates feedback cycles and reduces the "I can't open this file" bottleneck that plagues hardware teams.

## Platform Comparison

| Feature | Online 3D Viewer | OpenSCAD | FreeCAD |
|---------|-----------------|----------|---------|
| **Primary Role** | Web-based 3D model viewer | Script-based 3D CAD modeler | Full parametric CAD suite |
| **GitHub Stars** | 3,540 | 9,537 | 31,405 |
| **Language** | JavaScript/TypeScript | C++ with custom language | C++/Python |
| **Web Interface** | Built-in (core feature) | Via OpenSCAD Web / openscad.cloud | Via FreeCAD Web export |
| **Docker Support** | Official Docker image | Third-party containers | Official Docker images |
| **Supported Formats** | STL, OBJ, 3DS, PLY, glTF, STEP, IGES, FBX, 3DM, OFF | SCAD, STL, OFF, AMF, 3MF, DXF, SVG, CSG | STEP, IGES, STL, OBJ, DXF, SVG, IFC, BREP, and 20+ more |
| **Measurement Tools** | Yes (distance, angle, area) | Via script | Yes (full measurement workbench) |
| **Cross-Section** | Yes (clipping planes) | Via script (projection) | Yes (cross-section workbench) |
| **Annotations** | No | No | Yes (TechDraw workbench) |
| **Collaboration** | Share via URL | Share script files | Share FreeCAD files |
| **Rendering** | WebGL-based | OpenCSG / WebGL | Coin3D / WebGL export |
| **API/Automation** | JavaScript API | Command-line + Python | Full Python API |
| **Last Updated** | February 2026 | June 2026 | June 2026 |
| **Best For** | Embedding 3D views in websites | Programmatic parametric modeling | Complete CAD design + viewing |

## Getting Started with Docker

### Online 3D Viewer

```yaml
# docker-compose.yml
version: "3.8"
services:
  ov:
    image: kovacsv/online3dviewer:latest
    container_name: online3dviewer
    ports:
      - "8080:8080"
    volumes:
      - ./models:/app/models
      - ./config:/app/config
    environment:
      - MODELS_DIR=/app/models
    restart: unless-stopped
```

Online 3D Viewer is the most web-native of the three. Drop 3D files in the models directory and they're instantly viewable:

```bash
# Serve all models in the directory
curl http://localhost:8080/?model=sample.stl
```

### OpenSCAD

```yaml
# docker-compose.yml
version: "3.8"
services:
  openscad:
    image: openscad/openscad:latest
    container_name: openscad
    ports:
      - "8080:8080"
    volumes:
      - ./scad:/scad
      - ./output:/output
    command: >
      sh -c "cd /scad && python3 -m http.server 8080"
    restart: unless-stopped
```

OpenSCAD's strength is parametric modeling through code. A simple part definition:

```scad
// bracket.scad
module bracket(width=50, height=30, thickness=5) {
    difference() {
        cube([width, height, thickness]);
        translate([width/2, height/2, 0])
            cylinder(h=thickness+1, r=3);
    }
}
bracket();
```

Generate STL for web viewing:

```bash
docker exec openscad openscad -o /output/bracket.stl /scad/bracket.scad
```

### FreeCAD

```yaml
# docker-compose.yml
version: "3.8"
services:
  freecad:
    image: freecad/freecad:latest
    container_name: freecad
    ports:
      - "8080:8080"
    volumes:
      - ./models:/models
      - ./output:/output
    command: python3 -m freecad.web_server --port 8080
    restart: unless-stopped
```

FreeCAD provides the most complete CAD-to-web pipeline. Export models for web viewing with Python:

```python
# export_for_web.py
import FreeCAD
import Part
import Mesh
import Web

# Load a FreeCAD document
doc = FreeCAD.open("/models/assembly.FCStd")

# Export to various web-friendly formats
for obj in doc.Objects:
    if obj.isDerivedFrom("Part::Feature"):
        # Export STEP for engineering review
        Part.export([obj], "/output/" + obj.Name + ".step")
        # Export STL for lightweight web viewing
        Mesh.export([obj], "/output/" + obj.Name + ".stl")

# Generate glTF for modern web viewers
import importGLTF
importGLTF.export(doc.Objects, "/output/model.glb")
```

## Choosing the Right Platform

**Choose Online 3D Viewer** when your primary need is displaying existing 3D models on the web. It supports the widest range of input formats (30+ including proprietary formats like 3DM and FBX), provides measurement and cross-section tools without CAD expertise, and embeds cleanly into any website. Engineering teams sharing design reviews with non-technical stakeholders will appreciate its zero-learning-curve interface.

**Choose OpenSCAD** when your designs are defined programmatically. OpenSCAD's script-based approach makes version control natural (diff SCAD files in Git), enables parametric design families (change one variable to generate variants), and produces mathematically precise models. It's ideal for engineering teams that think in code and want reproducible, auditable design pipelines.

**Choose FreeCAD** when you need a complete CAD environment that also serves as a viewer. Its Python API allows automated export pipelines — check a STEP file into Git, trigger a CI pipeline that runs FreeCAD's Python script, and deploy updated glTF files to your web viewer automatically. For organizations that already use FreeCAD for design work, adding web viewing is a natural extension of existing infrastructure.


## Deployment Architecture and Integration

A production CAD viewer deployment typically follows a three-tier pattern: the viewer frontend (served as static HTML/JS), a conversion backend (handling STEP-to-STL/glTF conversion), and file storage (network share or object storage).

Online 3D Viewer operates purely as a frontend — point it at static 3D files served by Nginx or an S3-compatible bucket. For automated pipelines, add a conversion layer using FreeCAD's Python API in a Docker container triggered by Git hooks or CI/CD pipelines. When a designer pushes a STEP file to the repository, FreeCAD auto-converts it to glTF, and Online 3D Viewer immediately serves the updated version.

For enterprise deployments, integrate with your existing SSO provider through a reverse proxy. Nginx with OAuth2 Proxy or Caddy with forward auth ensures only authenticated users access your design repository. Cache commonly viewed models with standard HTTP caching headers — glTF files compress well (typically 5-10x with gzip) and rarely change.

OpenSCAD's script-based approach fits naturally into GitOps workflows. Store SCAD files in Git, use CI to generate STL/glTF artifacts, and deploy them to your web viewer. Parameterized designs become simple: change a dimension variable in Git, CI regenerates all dependent models, and stakeholders see the updated version at a stable URL.


## FAQ

### Can these tools handle large assemblies?

Online 3D Viewer handles files up to several hundred megabytes in browser memory — beyond that, performance depends on client hardware. FreeCAD processes large assemblies natively but web export should use decimated meshes for viewing. OpenSCAD can generate arbitrarily complex models but rendering time increases with complexity. For assemblies with thousands of parts, consider using a level-of-detail approach: export simplified representations for web viewing while keeping detailed models in your PLM system.

### Do I need a GPU on the server?

No. These tools render on the client side using WebGL. The server only needs to serve static files (STL, glTF, OBJ) — no server-side rendering required. A basic VPS with 1GB RAM handles model serving. File conversion (STEP to STL, SCAD to STL) uses CPU on the server, but this is typically done offline or on-demand with reasonable processing times.

### How do I protect proprietary designs?

All three solutions let you deploy behind authentication. Use a reverse proxy like Nginx or Caddy with basic auth, OAuth2, or SSO to restrict access. Online 3D Viewer and FreeCAD's web export generate client-side rendered models — the 3D data is downloaded to the browser, so consider whether view-only access is sufficient for your security requirements. For sensitive designs, add watermark overlays or use simplified representations.

### Can I embed the viewer in an existing website?

Yes. Online 3D Viewer provides an `<iframe>` embed and a JavaScript API for custom integration. FreeCAD's web export generates standalone HTML files that can be iframed. OpenSCAD models require conversion to a web-viewable format first (STL or glTF), then can be displayed with any WebGL viewer. For a polished integration, use Online 3D Viewer's API with custom branding and measurement tools.

### What formats work best for web viewing?

glTF (GL Transmission Format) is the modern standard — it's compact, supports PBR materials, and loads quickly. STL is universally supported but lacks color and material data. STEP/IGES provide engineering precision but are larger files. A practical workflow: store STEP for engineering, auto-convert to glTF for web viewing, and serve both from your self-hosted platform.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted 3D CAD Web Viewers: Online 3D Viewer vs OpenSCAD vs FreeCAD",
  "description": "Compare self-hosted 3D CAD web viewing solutions: Online 3D Viewer for format support, OpenSCAD for parametric modeling, and FreeCAD for complete CAD-to-web pipelines.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
