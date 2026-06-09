---
title: "Self-Hosted IIIF Viewers: Mirador vs Universal Viewer vs Recogito for Digital Humanities"
date: "2026-06-09"
tags: ["digital-humanities", "iiif", "cultural-heritage", "image-viewer", "annotation", "libraries", "museum", "self-hosted"]
draft: false
---

## Introduction

The International Image Interoperability Framework (IIIF) has transformed how libraries, museums, and archives share digitized collections online. Rather than building siloed image viewers for each institution, IIIF provides a standardized protocol for serving and displaying high-resolution images, audio, video, and 3D content. This means any IIIF-compatible viewer can display content from any IIIF-compatible image server — unlocking a global ecosystem of interoperable cultural heritage resources.

Three leading open-source IIIF viewers have emerged as the go-to choices for institutions building self-hosted digital collections platforms: **Mirador**, **Universal Viewer**, and **Recogito**. While Mirador and Universal Viewer focus on image viewing and comparison, Recogito specializes in text annotation — together they form a comprehensive toolkit for digital humanities work.

## Comparison Table

| Feature | Mirador 3 | Universal Viewer | Recogito |
|---------|-----------|------------------|----------|
| **Primary Focus** | Deep zoom, annotation, comparison | Universal media viewer | Text annotation with linked open data |
| **Media Types** | Images (JPEG, TIFF, JP2) | Images, audio, video, 3D, PDF | Images, plain text, TEI/XML |
| **Multi-Up View** | Yes — side-by-side comparison | No — single item at a time | No |
| **Annotation** | W3C Web Annotation standard | Basic | Full semantic annotation with entity linking |
| **IIIF API Support** | Image API 2.x/3.0, Presentation API 3.0 | Image API, Presentation API, AV API | Image API 2.x, Presentation API |
| **Search** | Within-manifest search | Within-manifest search | Full-text search with semantic filters |
| **Authentication** | IIIF Auth API | IIIF Auth API | OAuth2 / OpenID Connect |
| **Deployment** | Static JS (drop-in) | Static JS (drop-in) | Java/Scala web application |
| **GitHub Stars** | 607+ | 559+ | 163+ |
| **Latest Release** | 3.3.0 (2026) | 4.1.1 (2026) | 3.3.0 (2024) |
| **Plugin System** | Yes — React component plugins | Yes — extensions framework | API-based integration |

## Mirador 3: The Scholar's Workbench

Mirador is the most feature-rich IIIF viewer available, designed with art historians, manuscript researchers, and digital humanities scholars in mind. Its standout feature is **multi-up viewing** — the ability to open multiple IIIF manifests side by side and compare them pixel by pixel.

### Key Features

Mirador 3 is a complete rewrite using React and Redux, making it highly extensible through a plugin architecture. Plugins can add new annotation tools, image manipulation features, or integration with external services. The workspace can be saved and shared via URL, enabling scholars to return to exactly the same comparison view.

```html
<!-- Deploy Mirador with a simple HTML page -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://unpkg.com/mirador@latest/dist/mirador.min.js"></script>
</head>
<body>
  <div id="mirador-viewer" style="width:100%; height:100vh;"></div>
  <script>
    Mirador.viewer({
      id: 'mirador-viewer',
      windows: [{
        manifestId: 'https://iiif.harvardartmuseums.org/manifests/object/299843',
      }],
      workspaceControlPanel: { enabled: true },
    });
  </script>
</body>
</html>
```

### Self-Hosted Deployment

Mirador is a client-side JavaScript application, making deployment extremely simple — serve the static files through any web server:

```nginx
# Nginx configuration for Mirador
server {
    listen 80;
    server_name viewer.example.org;
    root /var/www/mirador;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy IIIF image server (e.g., Cantaloupe)
    location /iiif/ {
        proxy_pass http://localhost:8182/iiif/;
        proxy_set_header Host $host;
        add_header Access-Control-Allow-Origin *;
    }
}
```

```yaml
# Docker Compose for Mirador + Cantaloupe IIIF image server
version: '3.8'
services:
  mirador:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./mirador-dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro

  cantaloupe:
    image: ghcr.io/uclalibrary/cantaloupe:latest
    ports:
      - "8182:8182"
    volumes:
      - ./images:/imageroot:ro
      - ./cantaloupe.properties:/etc/cantaloupe/cantaloupe.properties:ro
    environment:
      CANTALOUPE_SOURCE_STATIC: FilesystemSource
      CANTALOUPE_FILESYSTEMSOURCE_PATH_PREFIX: /imageroot/
```

Mirador stores annotations using the W3C Web Annotation Data Model, and can connect to annotation servers like SimpleAnnotationServer or Elasticsearch-backed endpoints for persistent storage.

## Universal Viewer: One Viewer for Everything

Universal Viewer (UV) lives up to its name by supporting the broadest range of media types — images, audio, video, 3D models, PDFs, and even born-digital content. It powers the viewing experience for institutions including the British Library, Wellcome Collection, and Europeana.

### Architecture

UV is built with TypeScript and supports IIIF APIs natively, with extensions for handling non-IIIF content. Its "extensions" framework allows institutions to customize the viewer for specific collection types. While it lacks Mirador's multi-up comparison, it excels at providing a polished, accessible viewing experience for individual items.

```html
<!-- Deploy Universal Viewer -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/universalviewer@4/dist/umd/uv.min.js"></script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/universalviewer@4/dist/uv.css">
</head>
<body>
  <div id="uv" style="width:100%; height:100vh;"></div>
  <script>
    const uv = new UV({
      target: '#uv',
      manifest: 'https://wellcomelibrary.org/iiif/b18035723/manifest',
    });
  </script>
</body>
</html>
```

UV includes built-in support for deep zoom (OpenSeadragon), audio/video playback, PDF rendering (via PDF.js), and even 3D model viewing (via Three.js). For libraries and archives with diverse collections spanning multiple media types, UV provides a consistent viewing experience across all formats.

## Recogito: Semantic Annotation Platform

Recogito takes a different approach from Mirador and UV — rather than being primarily a viewer, it's an **annotation platform** built on top of IIIF. Developed by Pelagios Commons, Recogito enables scholars to annotate text and images with linked open data entities.

### Semantic Annotation Workflow

Recogito's annotation model connects text and image annotations to authority files like Wikidata, GeoNames, and Pleiades. When a scholar annotates a place name in a historical map, Recogito can automatically suggest linked data entities for that location:

```yaml
# Recogito deployment with Docker
version: '3.8'
services:
  recogito-db:
    image: postgres:14
    environment:
      POSTGRES_DB: recogito
      POSTGRES_USER: recogito
      POSTGRES_PASSWORD: securepassword
    volumes:
      - pgdata:/var/lib/postgresql/data

  recogito:
    image: pelagios/recogito:latest
    ports:
      - "9000:9000"
    depends_on:
      - recogito-db
    environment:
      DATABASE_URL: jdbc:postgresql://recogito-db:5432/recogito
      DATABASE_USER: recogito
      DATABASE_PASSWORD: securepassword
      RECOGITO_ADMIN_EMAIL: admin@example.org
      RECOGITO_ADMIN_PASSWORD: secureadminpw
    volumes:
      - recogito-data:/opt/recogito/data

volumes:
  pgdata:
  recogito-data:
```

Recogito supports TEI/XML export for integration with digital scholarly editions, and its annotations follow the W3C Web Annotation standard for interoperability with Mirador and other annotation-consuming tools.

## Why Self-Host Your IIIF Infrastructure?

Running your own IIIF viewers and image servers gives institutions complete control over their digital collections. **Preservation** is the primary concern — cloud-hosted solutions can disappear or change pricing, but self-hosted infrastructure ensures your digitized collections remain accessible indefinitely. For smaller institutions concerned about long-term sustainability, self-hosted solutions avoid recurring SaaS fees.

**Accessibility and performance** improve when images are served from local infrastructure. IIIF's deep zoom protocol requires many small image tile requests — serving these from a local Cantaloupe or Loris server eliminates the latency of routing through cloud services. For researchers studying high-resolution manuscript images, smooth zoom performance directly impacts research productivity.

**Privacy and access control** matter for collections that include culturally sensitive materials. IIIF's Authentication API allows fine-grained access control — public collections can be freely accessible while restricted materials require institutional login. See our [guide to self-hosted library and digital collection platforms](../2026-05-02-koha-vs-omeka-vs-invenio-self-hosted-library-digital-collection-guide/) for a broader look at collection management infrastructure.

**Interoperability** is IIIF's greatest strength — self-hosting means your collections participate in the global IIIF ecosystem. Scholars can open your institution's manuscripts side-by-side with materials from the British Library or the Vatican using Mirador, without any special integration work. This cross-institutional interoperability is transforming digital humanities research. For institutions building complete digital collection platforms, our [comparison of DSpace, Fedora, and Invenio](../2026-05-02-koha-vs-omeka-vs-invenio-self-hosted-library-digital-collection-guide/) covers repository software for managing and preserving digital assets.

## Deployment Best Practices

When deploying IIIF infrastructure, separate concerns: use a dedicated IIIF image server (Cantaloupe or Loris) for image processing and tile delivery, while the viewer (Mirador or UV) is a lightweight static frontend. For production deployments, place a caching layer (Varnish or CloudFront) in front of the image server to accelerate repeated tile requests.

Annotation data should be stored in a persistent backend — Mirador can use Elasticsearch, SimpleAnnotationServer, or a custom W3C Web Annotation Protocol endpoint. Recogito uses PostgreSQL for annotation storage with Elasticsearch for full-text search.

## FAQ

### Do I need a IIIF image server to use these viewers?

For Mirador and Universal Viewer, yes — you need a IIIF-compatible image server (like Cantaloupe or Loris) to serve images in the IIIF Image API format. Recogito can work directly with uploaded images or connect to external IIIF image servers.

### Can I use Mirador and Recogito together?

Yes, this is a common workflow. Use Recogito for collaborative text annotation and entity linking, then export annotations in W3C Web Annotation format and load them into Mirador for visualization alongside the images. The annotation data model is interoperable between the two tools.

### What storage requirements should I plan for?

Image tile caches for IIIF can grow quickly — a single 100 MB TIFF can generate hundreds of MB of tiles at various zoom levels. Plan for 5-10x the original image size in storage for tile derivatives. Use SSD storage for the tile cache for fast access.

### How do these viewers handle very large images (gigapixel+)?

Mirador and UV both use OpenSeadragon for deep zoom, which handles gigapixel images efficiently by requesting only the visible tiles at the current zoom level. The bottleneck is typically the image server's ability to generate tiles on-the-fly — consider pre-generating tiles for heavily accessed images.

### Are these viewers accessible for users with disabilities?

Universal Viewer has the strongest accessibility support, including keyboard navigation, ARIA labels, and screen reader compatibility. Mirador 3 has made significant accessibility improvements with focus on keyboard navigation and semantic HTML. Recogito includes accessibility features for text annotation workflows.

### Can I customize the branding and UI?

All three viewers support customization. Mirador's plugin system allows complete UI customization through React components. UV provides a theming framework and the ability to hide/show panels. Recogito supports custom branding through CSS and configuration files.
---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IIIF Viewers: Mirador vs Universal Viewer vs Recogito for Digital Humanities",
  "description": "Compare Mirador, Universal Viewer, and Recogito for self-hosted IIIF viewing and annotation. Build interoperable digital collections for libraries, museums, and archives.",
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
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)