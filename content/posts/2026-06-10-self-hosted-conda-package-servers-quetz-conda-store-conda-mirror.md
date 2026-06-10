---
title: "Self-Hosted Conda Package Servers: Quetz vs conda-store vs conda-mirror"
date: "2026-06-10"
tags: ["conda", "python", "package-management", "data-science", "scientific-computing", "devops"]
draft: false
---

## Introduction

Scientific computing teams, data science platforms, and enterprise machine learning groups face a critical dependency management challenge: how to provide reproducible, auditable, and internally curated Python and R package repositories. Public channels like conda-forge and Anaconda's defaults channel solve discovery, but they introduce external dependency risk, rate limiting, and lack of control over package provenance in regulated or air-gapped environments.

Three open-source tools enable organizations to self-host their conda package infrastructure: **Quetz**, developed by the makers of Mamba, provides a full-featured conda package server with user management, channels, and a web UI; **conda-store** focuses on collaborative data science environments with versioned, shareable conda environments; and **conda-mirror** offers a lightweight approach for creating local mirrors of upstream conda channels.

This guide compares these three self-hosted conda infrastructure tools, covering deployment, architecture, and use cases to help teams build reliable, reproducible package management pipelines.

## Why Self-Host Your Conda Package Infrastructure?

Data science and scientific computing teams have specific requirements that public conda channels cannot satisfy:

**Reproducibility at Scale**: When a Nature paper depends on a specific combination of numpy 1.24.3, scipy 1.10.1, and pandas 2.0.1, you need those exact versions available indefinitely. Public channels occasionally remove old package versions. Self-hosted mirrors freeze exact dependency graphs for permanent archival.

**Air-Gapped and Regulated Environments**: Pharmaceutical research, defense contractors, and financial institutions operate on networks with no internet access. A local conda mirror on an internal server enables package installation without ever touching the public internet — critical for security compliance.

**Internal Package Distribution**: Organizations developing proprietary Python libraries need to distribute them alongside open-source dependencies. Quetz and conda-store support private channels where teams publish internal packages with the same `conda install` workflow they use for public packages — no separate pip index or wheel server required.

For teams building end-to-end data science infrastructure, pair this with a [self-hosted notebook platform](../2026-05-18-apache-zeppelin-vs-polynote-vs-jupyterlab-self-hosted-notebooks-guide/) and our guide on [reactive notebooks](../2026-06-09-self-hosted-reactive-notebooks-marimo-livebook-jupyterlite-guide/).

## Comparison Table

| Feature | Quetz | conda-store | conda-mirror |
|---------|-------|-------------|--------------|
| **Primary Use Case** | Package server + private channels | Collaborative environments | Upstream channel mirroring |
| **Web UI** | Full dashboard | Environment management UI | None |
| **User Management** | OAuth2, GitHub, GitLab, LDAP | JupyterHub integration | N/A |
| **Private Channels** | Yes, with ACLs | Yes, per-environment | No |
| **Upstream Mirroring** | Via proxy | Via solver | Yes (primary function) |
| **Environment Versioning** | No | Yes (built-in) | No |
| **Docker Deployment** | Yes | Yes | CLI tool |
| **API** | REST API | REST API | CLI only |
| **Database Backend** | PostgreSQL | PostgreSQL | None (flat files) |
| **S3 Storage Support** | Yes | Yes | No |
| **License** | BSD-3 | BSD-3 | BSD-3 |
| **GitHub Stars** | 328+ | 155+ | 35+ |
| **Maturity** | Production (Quansight) | Active development | Stable utility |

## Quetz: The Full-Featured Conda Server

Quetz is the most comprehensive self-hosted conda package server, developed by Quansight (the company behind Mamba, the fast conda solver). It provides private channels, user management, and a web dashboard — essentially a self-hosted equivalent of Anaconda.org for enterprise teams.

**Key Capabilities:**
- **Private channels with access control** — create channels per team, project, or department with granular read/write permissions
- **OAuth2 authentication** — integrates with GitHub, GitLab, Google, and generic OAuth2 providers
- **Package proxy** — transparently cache packages from upstream channels (conda-forge, defaults) to reduce external bandwidth
- **S3-compatible storage** — store packages on MinIO, AWS S3, or any S3-compatible object store
- **Web UI** — browse channels, view package metadata, and manage users through a clean dashboard

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  quetz:
    image: ghcr.io/mamba-org/quetz:latest
    container_name: quetz
    ports:
      - "8000:8000"
    volumes:
      - ./quetz-config:/config
      - ./quetz-channels:/channels
    environment:
      - QUETZ_DATABASE_URL=postgresql://quetz:changeme@postgres:5432/quetz
      - QUETZ_SECRET_KEY=your-secret-key-here
      - QUETZ_SESSION_SECRET=another-secret
      - QUETZ_S3_ACCESS_KEY=minioadmin
      - QUETZ_S3_SECRET_KEY=minioadmin
      - QUETZ_S3_ENDPOINT=http://minio:9000
      - QUETZ_S3_BUCKET=quetz-packages
    depends_on:
      - postgres
      - minio

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=quetz
      - POSTGRES_USER=quetz
      - POSTGRES_PASSWORD=changeme
    volumes:
      - ./postgres-data:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ./minio-data:/data
```

**Initial Setup:**

```bash
# Initialize Quetz database
docker exec quetz quetz init-db

# Create a private channel
docker exec quetz quetz create-channel myteam-internal --private

# Upload a package
docker exec quetz quetz upload myteam-internal mypackage-1.0.0-py39_0.tar.bz2
```

Users then configure their conda to use the private server:

```bash
conda config --add channels https://quetz.example.com/channels/myteam-internal
conda config --add channels https://quetz.example.com/channels/conda-forge
conda install mypackage
```

## conda-store: Collaborative Environment Management

conda-store approaches the conda infrastructure problem from a different angle — rather than focusing on package distribution, it focuses on environment management for collaborative data science teams. It builds versioned, shareable conda environments that entire teams can use consistently.

**Key Capabilities:**
- **Versioned environments** — every environment build is immutable and versioned, with a complete history
- **Environment sharing** — team members can use the exact same environment via a simple URL or API call
- **JupyterHub integration** — environments appear automatically as kernel options in JupyterHub
- **Build queue** — asynchronous environment builds with status tracking
- **Garbage collection** — automatic cleanup of unused environment versions

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  conda-store-server:
    image: quansight/conda-store-server:latest
    container_name: conda-store-server
    ports:
      - "8080:8080"
    volumes:
      - ./conda-store-data:/var/lib/conda-store
    environment:
      - CONDA_STORE_DB_URL=postgresql+psycopg2://admin:changeme@postgres:5432/conda-store
      - CONDA_STORE_REDIS_URL=redis://redis:6379/0
      - CONDA_STORE_STORAGE=LocalStorage
      - CONDA_STORE_STORAGE_PATH=/var/lib/conda-store
    depends_on:
      - postgres
      - redis

  conda-store-worker:
    image: quansight/conda-store-server:latest
    command: conda-store-worker
    volumes:
      - ./conda-store-data:/var/lib/conda-store
    environment:
      - CONDA_STORE_DB_URL=postgresql+psycopg2://admin:changeme@postgres:5432/conda-store
      - CONDA_STORE_REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=conda-store
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=changeme
    volumes:
      - ./postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
```

**Creating an Environment:**

```bash
# Create a new environment via API
curl -X POST http://conda-store:8080/api/v1/environment/   -H "Content-Type: application/json"   -d '{
    "namespace": "team-ds",
    "specification": {
      "name": "ml-pipeline-v2",
      "channels": ["conda-forge"],
      "dependencies": [
        "python=3.11",
        "numpy=1.26",
        "pandas=2.1",
        "scikit-learn=1.3",
        "jupyterlab"
      ]
    }
  }'

# Activate the environment (any team member)
conda activate https://conda-store.example.com/conda-store/team-ds/ml-pipeline-v2
```

## conda-mirror: Lightweight Channel Mirroring

conda-mirror is the simplest tool in this comparison — a single-purpose utility for creating local mirrors of upstream conda channels. It downloads package metadata and binary packages, maintaining the channel structure for offline or internal use.

**Key Capabilities:**
- **Full channel mirroring** — replicate entire channels (conda-forge, defaults, bioconda) to local storage
- **Platform filtering** — mirror only linux-64 or osx-arm64 packages to save storage
- **Incremental updates** — only download new and changed packages on subsequent runs
- **No server required** — serves packages via any HTTP server (nginx, Apache, Python http.server)

**Basic Usage:**

```bash
# Install
pip install conda-mirror

# Mirror conda-forge for linux-64 only
conda-mirror   --upstream-channel https://conda.anaconda.org/conda-forge   --target-directory /data/conda-mirrors/conda-forge   --platform linux-64   --temp-directory /tmp/conda-mirror

# Serve the mirror
cd /data/conda-mirrors
python -m http.server 8000
```

For production use, pair conda-mirror with nginx for efficient static file serving:

```nginx
server {
    listen 80;
    server_name conda-mirror.internal;

    location / {
        root /data/conda-mirrors;
        autoindex on;
        add_header Cache-Control "public, max-age=86400";
    }
}
```

## Choosing the Right Conda Infrastructure Tool

| Organization Profile | Recommended Stack | Rationale |
|---------------------|-------------------|-----------|
| Small team needing private packages | Quetz | Full-featured with minimal setup |
| Data science platform with JupyterHub | conda-store | Native JupyterHub integration, environment versioning |
| Air-gapped environment needing full mirrors | conda-mirror + nginx | Simple, reliable, zero-moving-parts |
| Enterprise with multiple teams | Quetz + conda-mirror | Quetz for private channels, mirror for upstream caching |
| Research lab wanting reproducibility | conda-store | Versioned environments with complete history |

For most organizations, these tools work best in combination: use conda-mirror to create a local cache of conda-forge and bioconda, run Quetz for private team channels and package publishing, and deploy conda-store for data science teams that need versioned, shareable environments integrated with their JupyterHub infrastructure.

## Frequently Asked Questions

### How much storage does a conda-forge mirror require?

A full conda-forge mirror for linux-64 only requires approximately 150-200 GB. Adding osx-arm64 and linux-aarch64 can push this to 400-500 GB. Using conda-mirror's platform filtering (`--platform linux-64`) is essential for keeping storage manageable. Incremental daily updates typically add 1-5 GB per day.

### Can Quetz proxy packages without downloading them all?

Yes. Quetz's proxy mode downloads packages on-demand when a user requests them, caching them locally for subsequent requests. This avoids the upfront storage cost of a full mirror while still providing local access. However, the first user to request a package will experience download latency as Quetz fetches it from upstream.

### How does conda-store handle environment conflicts?

conda-store uses Mamba's solver (via the conda-libmamba-solver) to resolve environments. When a specification cannot be resolved, it returns detailed conflict analysis showing which packages conflict and why. This is significantly more helpful than the legacy conda solver's opaque error messages.

### Can I use these tools with Mamba instead of Conda?

Absolutely. All three tools are fully compatible with Mamba. In fact, Quetz is developed by the Mamba team (Quansight/mamba-org) and conda-store uses libmamba for environment resolution. Users can install packages from any of these servers using `mamba install`, which is typically 5-10x faster than the standard conda solver.

### What about pip packages — can these tools handle those?

Quetz can serve pip-installable packages alongside conda packages, making it a unified package server. conda-store environments can include pip dependencies, resolved alongside conda packages by the solver. conda-mirror is conda-specific and does not handle PyPI packages — for pip mirroring, consider devpi-server or a simple PyPI mirror.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Conda Package Servers: Quetz vs conda-store vs conda-mirror",
  "description": "Compare three open-source tools for self-hosting conda package infrastructure: Quetz (full-featured server), conda-store (collaborative environments), and conda-mirror (lightweight mirroring). Includes Docker Compose deployment, configuration examples, and storage estimates.",
  "datePublished": "2026-06-10",
  "dateModified": "2026-06-10",
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
