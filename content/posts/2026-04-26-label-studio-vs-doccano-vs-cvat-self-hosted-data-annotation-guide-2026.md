---
title: "Label Studio vs Doccano vs CVAT: Best Self-Hosted Data Annotation Tools 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "data-annotation", "machine-learning"]
draft: false
description: "Compare the top three open-source, self-hosted data annotation tools — Label Studio, Doccano, and CVAT. Includes Docker deployment guides, feature comparisons, and pricing analysis for building your own labeling platform."
---

When building datasets for machine learning models, the quality of your labeled data directly determines model performance. Commercial annotation platforms charge per task or per seat, and at scale those costs add up quickly. Self-hosted open-source annotation tools give you full control over your data, unlimited labeling capacity, and zero per-item fees.

In this guide, we compare the three most popular self-hosted data annotation platforms — **Label Studio**, **Doccano**, and **CVAT** — and help you pick the right one for your use case.

## Why Self-Host Your Data Annotation Platform

Running your own annotation server offers several advantages over SaaS platforms:

- **Data privacy**: Your raw data and labels never leave your infrastructure — critical for healthcare, finance, and proprietary datasets.
- **Unlimited scale**: No per-task pricing, no monthly quotas. Label as much data as your hardware can handle.
- **Custom integrations**: Connect directly to your internal databases, object storage, and model training pipelines via APIs.
- **No vendor lock-in**: Export formats are standardized (JSON, COCO, YOLO, VOC), so you're never trapped in a proprietary ecosystem.
- **Cost savings**: For teams labeling tens of thousands of items, self-hosting eliminates recurring SaaS fees entirely.

All three tools covered here are open-source, actively maintained, and deployable via Docker with a web-based interface accessible to distributed labeling teams.

## Quick Comparison Table

| Feature | Label Studio | Doccano | CVAT |
|---------|-------------|---------|------|
| **GitHub Stars** | 27,138 | 10,635 | 15,711 |
| **Language** | TypeScript (Django) | Python (Django) | Python (Django) |
| **License** | Apache-2.0 | MIT | MIT |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Text Annotation** | ✅ NER, classification, summarization | ✅ NER, classification, relation | ❌ Not supported |
| **Image Annotation** | ✅ Bounding boxes, polygons, keypoints | ❌ Not supported | ✅ Bounding boxes, polygons, skeletons, tags |
| **Video Annotation** | ✅ Frame-by-frame tracking | ❌ Not supported | ✅ Interpolation, tracking, skeletons |
| **Audio Annotation** | ✅ Transcription, classification | ❌ Not supported | ❌ Not supported |
| **Auto-Labeling** | ✅ ML backend integration | ❌ Not supported | ✅ Semi-automatic interpolation |
| **Team Collaboration** | ✅ Roles, review, rejection | ✅ Role-based access | ✅ Jobs, tasks, assignments |
| **Export Formats** | JSON, COCO, YOLO, VOC, CSV | JSON, JSONL, CoNLL | COCO, YOLO, CVAT, MOT, Pascal VOC |
| **Database** | SQLite, PostgreSQL | PostgreSQL | PostgreSQL, ClickHouse, Redis |
| **API** | Full REST API | Full REST API | Full REST API |
| **Docker Deploy** | ✅ Single container or multi-service | ✅ Docker Compose (multi-service) | ✅ Docker Compose (multi-service) |

## Label Studio: The Multi-Modal All-Rounder

[Label Studio](https://github.com/HumanSignal/label-studio) (maintained by HumanSignal, formerly Heartex) is the most versatile open-source annotation platform. It supports text, image, audio, video, and time series data in a single interface, making it ideal for teams working across multiple data types.

With over 27,000 GitHub stars and an Apache 2.0 license, Label Studio has the largest community of the three tools. Its configuration-driven UI lets you define custom labeling interfaces using XML-like tags, giving you flexibility for virtually any annotation workflow.

### Key Features

- **Multi-modal support**: Label text, images, audio, video, HTML, and time series data in one platform.
- **Configurable UI**: Define labeling interfaces with XML-like configuration templates.
- **ML backend**: Connect trained models for pre-labeling and active learning loops.
- **Review workflow**: Built-in task review, acceptance, and rejection pipeline.
- **Extensible**: Plugin architecture for custom storage backends, ML models, and export formats.

### Docker Deployment

Label Studio's simplest deployment uses a single container with SQLite:

```yaml
services:
  label-studio:
    image: heartexlabs/label-studio:latest
    container_name: label-studio
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./mydata:/label-studio/data:rw
    environment:
      - LABEL_STUDIO_HOST=${LABEL_STUDIO_HOST:-}
```

For production workloads with PostgreSQL:

```yaml
services:
  label-studio:
    image: heartexlabs/label-studio:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - DJANGO_DB=default
      - POSTGRE_NAME=postgres
      - POSTGRE_USER=postgres
      - POSTGRE_PASSWORD=postgres
      - POSTGRE_HOST=db
      - POSTGRE_PORT=5432
    volumes:
      - ./mydata:/label-studio/data:rw
    depends_on:
      - db

  db:
    image: pgautoupgrade/pgautoupgrade:17-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=postgres
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Start the service with `docker compose up -d` and access the web UI at `http://localhost:8080`. The default installation includes SQLite; switch to PostgreSQL by setting the database environment variables.

### Best For

- Teams annotating **multiple data types** (text + images + audio).
- Projects requiring **custom labeling interfaces** via configuration templates.
- Workflows using **pre-labeling with ML models** for faster annotation cycles.
- Organizations needing an **Apache 2.0 license** for commercial use.

## Doccano: The Text Annotation Specialist

[Doccano](https://github.com/doccano/doccano) is a focused, text-only annotation tool built with Python and Django. It supports named entity recognition (NER), sentiment analysis, text classification, sequence-to-sequence tasks, and relation extraction.

With over 10,600 stars and an MIT license, Doccano is the most lightweight option. Its clean, minimal interface makes it easy for non-technical annotators to get started quickly — no configuration files or XML templates required.

### Key Features

- **Text-focused**: NER, text classification, sentiment analysis, relation extraction, and seq2seq annotation.
- **Simple interface**: No configuration needed — select a task type and start labeling immediately.
- **Role-based access**: Admin, annotator, and annotation approval roles.
- **Async processing**: Celery worker for handling large import/export operations.
- **REST API**: Full API for programmatic project and annotation management.

### Docker Deployment

Doccano requires multiple services — a backend, PostgreSQL database, RabbitMQ message broker, and a Celery worker:

```yaml
services:
  backend:
    image: doccano/doccano:backend
    volumes:
      - static_volume:/backend/staticfiles
      - media:/backend/media
    environment:
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "changeme"
      ADMIN_EMAIL: "admin@example.com"
      CELERY_BROKER_URL: "amqp://guest:guest@rabbitmq"
      DATABASE_URL: "postgres://postgres:postgres@postgres:5432/doccano?sslmode=disable"
      ALLOW_SIGNUP: "False"
      DEBUG: "False"
      DJANGO_SETTINGS_MODULE: "config.settings.production"
    depends_on:
      - postgres
    networks:
      - doccano-net

  celery:
    image: doccano/doccano:backend
    entrypoint: ["/opt/bin/prod-celery.sh"]
    environment:
      CELERY_BROKER_URL: "amqp://guest:guest@rabbitmq"
      DATABASE_URL: "postgres://postgres:postgres@postgres:5432/doccano?sslmode=disable"
      DJANGO_SETTINGS_MODULE: "config.settings.production"
    depends_on:
      - postgres
      - rabbitmq
    networks:
      - doccano-net

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: doccano
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - doccano-net

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    networks:
      - doccano-net

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "8080:80"
    volumes:
      - static_volume:/backend/staticfiles
      - media:/backend/media
    depends_on:
      - backend
    networks:
      - doccano-net

volumes:
  pgdata:
  static_volume:
  media:

networks:
  doccano-net:
    driver: bridge
```

After `docker compose up -d`, access the UI at `http://localhost:8080` and log in with the admin credentials defined in the environment variables.

### Best For

- **Text-only** annotation projects (NER, classification, relation extraction).
- Teams that want a **zero-configuration** labeling experience.
- Organizations preferring the **permissive MIT license**.
- Projects with **high-throughput text labeling** where Celery async processing matters.

## CVAT: The Computer Vision Powerhouse

CVAT (Computer Vision Annotation Tool) is the industry-standard open-source platform for image and video annotation. Originally developed by Intel, it supports over 15,700 GitHub stars and is used by teams of all sizes.

CVAT's standout feature is its **video interpolation** capability — draw bounding boxes or polygons on key frames, and CVAT automatically interpolates labels for intermediate frames. This dramatically reduces labeling time for video datasets.

### Key Features

- **Computer vision focus**: Images, video, and 3D point clouds — no text or audio support.
- **Video interpolation**: Automatic label propagation between key frames using tracking algorithms.
- **Skeleton annotation**: Define custom skeleton templates for pose estimation datasets.
- **Semi-automatic labeling**: Integrated model inference for pre-labeling images.
- **Analytics dashboard**: Built-in charts for annotation speed, quality metrics, and team performance.
- **Multi-format export**: COCO, YOLO, Pascal VOC, MOT, TFRecord, and 20+ additional formats.

### Docker Deployment

CVAT has the most complex deployment of the three, requiring PostgreSQL, Redis (two instances), ClickHouse for analytics, and a Vector log collector:

```yaml
name: cvat

services:
  cvat_db:
    container_name: cvat_db
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: root
      POSTGRES_DB: cvat
      POSTGRES_HOST_AUTH_METHOD: trust
    volumes:
      - cvat_db:/var/lib/postgresql/data
    networks:
      - cvat

  cvat_redis_inmem:
    container_name: cvat_redis_inmem
    image: redis:7-alpine
    restart: always
    volumes:
      - cvat_redis_inmem:/data
    networks:
      - cvat

  cvat_redis_ondisk:
    container_name: cvat_redis_ondisk
    image: redis:7-alpine
    restart: always
    command: ["--port", "6666"]
    volumes:
      - cvat_redis_ondisk:/data
    networks:
      - cvat

  cvat_clickhouse:
    container_name: cvat_clickhouse
    image: clickhouse/clickhouse-server:23.9-alpine
    restart: always
    volumes:
      - cvat_clickhouse:/var/lib/clickhouse
    networks:
      - cvat

  cvat:
    container_name: cvat
    image: opencv/cvat:latest
    restart: always
    ports:
      - "8080:8080"
    environment:
      CVAT_POSTGRES_HOST: cvat_db
      CVAT_REDIS_INMEM_HOST: cvat_redis_inmem
      CVAT_REDIS_INMEM_PORT: 6379
      CVAT_REDIS_ONDISK_HOST: cvat_redis_ondisk
      CVAT_REDIS_ONDISK_PORT: 6666
      CVAT_LOG_IMPORT_ERRORS: "true"
    volumes:
      - cvat_data:/home/django/data
      - cvat_keys:/home/django/keys
    depends_on:
      - cvat_db
      - cvat_redis_inmem
      - cvat_redis_ondisk
      - cvat_clickhouse
    networks:
      - cvat

volumes:
  cvat_db:
  cvat_redis_inmem:
  cvat_redis_ondisk:
  cvat_clickhouse:
  cvat_data:
  cvat_keys:

networks:
  cvat:
    driver: bridge
```

CVAT also requires the Docker Compose V2 plugin (the `name: cvat` field). After running `docker compose up -d`, create the superuser account:

```bash
docker exec -it cvat python manage.py createsuperuser
```

Then access the UI at `http://localhost:8080`.

### Best For

- **Computer vision** projects: object detection, segmentation, pose estimation.
- **Video datasets** where interpolation saves hours of manual frame-by-frame labeling.
- Teams needing **skeleton/keypoint annotation** for human pose or object part detection.
- Projects requiring **analytics dashboards** to track labeling progress and annotator performance.

## Choosing the Right Tool

Your choice depends primarily on **data type** and **team requirements**:

| Decision Factor | Recommended Tool |
|----------------|-----------------|
| Text annotation (NER, classification) | Doccano or Label Studio |
| Image annotation (detection, segmentation) | CVAT or Label Studio |
| Video annotation with interpolation | CVAT (only option) |
| Audio annotation | Label Studio (only option) |
| Multiple data types in one platform | Label Studio |
| Simplest deployment | Label Studio (single container) |
| Minimal hardware requirements | Doccano or Label Studio |
| Enterprise analytics dashboard | CVAT |
| Pre-labeling with ML models | Label Studio or CVAT |
| Apache 2.0 license required | Label Studio |
| MIT license required | Doccano or CVAT |

## Pricing and Licensing

All three tools are free and open-source:

- **Label Studio**: Apache 2.0 license. The open-source version includes core annotation features. HumanSignal offers a paid Enterprise edition with additional features (SSO, advanced analytics, dedicated support).
- **Doccano**: MIT license — fully permissive, no paid tier. The entire feature set is available in the open-source version.
- **CVAT**: MIT license. The CVAT cloud service offers a managed version with free tier limits and paid plans. The self-hosted version is fully featured with no artificial restrictions.

For organizations that need complete control and unlimited usage, all three self-hosted options eliminate recurring costs. The only expense is your server infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Label Studio vs Doccano vs CVAT: Best Self-Hosted Data Annotation Tools 2026",
  "description": "Compare the top three open-source, self-hosted data annotation tools — Label Studio, Doccano, and CVAT. Includes Docker deployment guides, feature comparisons, and pricing analysis for building your own labeling platform.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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

## FAQ

### What is the best open-source data annotation tool?

The best tool depends on your data type. For **text-only** annotation (NER, classification), Doccano is the simplest and most lightweight option. For **computer vision** (images, video, pose estimation), CVAT is the industry standard with video interpolation and skeleton support. For **multi-modal** projects spanning text, images, audio, and video, Label Studio is the most versatile all-in-one platform.

### Can I use Label Studio for free in production?

Yes. Label Studio is released under the Apache 2.0 license, which allows free commercial use. The open-source Community Edition includes all core annotation features, project management, and export capabilities. HumanSignal offers a paid Enterprise edition with additional features like SSO and advanced analytics, but the free version is production-ready.

### How do I deploy these tools with a reverse proxy?

All three tools run on a configurable port and can sit behind Nginx, Caddy, or Traefik. For Nginx, configure a `proxy_pass` to the container port (default 8080). With Caddy, use a simple `reverse_proxy localhost:8080` directive. For production, always enable HTTPS termination at the reverse proxy layer and configure the tool's `HOST` environment variable to match your public URL.

### Which tool supports team collaboration and review workflows?

All three support multi-user workflows. Label Studio has built-in review and rejection states with configurable reviewer roles. Doccano supports admin, annotator, and approval roles with task assignment. CVAT has the most granular system with jobs, tasks, and assignments, plus an analytics dashboard showing per-annotator speed and quality metrics — making it ideal for large labeling teams.

### Can these tools connect to external storage like S3 or GCS?

Yes. Label Studio supports cloud storage (S3, GCS, Azure Blob) as both input and output targets through its storage connector. CVAT can import data from cloud buckets and export results back to them. Doccano requires data to be uploaded through the web UI or API — direct cloud storage integration is not built in, though you can automate uploads via the REST API.

### How do these tools compare to commercial platforms like Scale or Labelbox?

Self-hosted open-source tools eliminate per-item pricing and keep your data on your own infrastructure. Commercial platforms offer managed services with support SLAs and sometimes higher-quality auto-labeling models, but at significant cost for large datasets. For teams with technical capacity to manage their own infrastructure, Label Studio, Doccano, and CVAT provide comparable core annotation features at zero licensing cost.

For related reading, see our [self-hosted ML experiment tracking guide](../self-hosted-ml-experiment-tracking-mlflow-clearml-aim-guide-2026/) for managing model training runs alongside your labeled datasets, the [data versioning comparison](../dvc-lakefs-pachyderm-self-hosted-data-versioning-guide-2026/) for tracking dataset changes over time, and the [ML feature store guide](../feast-vs-featureform-vs-hopsworks-self-hosted-ml-feature-store-2026/) for serving features built from annotated data.
