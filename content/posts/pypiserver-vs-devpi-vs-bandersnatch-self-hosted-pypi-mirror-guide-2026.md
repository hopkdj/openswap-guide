---
title: "pypiserver vs devpi vs Bandersnatch: Self-Hosted PyPI Mirror Guide 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "python", "package-management"]
draft: false
description: "Compare pypiserver, devpi, and Bandersnatch for self-hosting a PyPI mirror or private Python package registry. Docker configs, caching strategies, and deployment guides."
---

If your team depends on Python packages from PyPI, running a self-hosted mirror gives you faster installs, offline resilience, and full control over which versions enter your environment. Whether you need a lightweight private registry for internal wheels, a caching proxy to speed up CI pipelines, or a full PyPI mirror for air-gapped networks, the right tool makes a big difference.

In this guide, we compare three popular open-source solutions — **pypiserver** (2,024 stars), **devpi** (1,163 stars), and **Bandersnatch** (535 stars) — to help you choose the best self-hosted PyPI mirror for your use case.

## Why Self-Host a PyPI Mirror

Running your own PyPI mirror solves several common problems:

- **Faster CI/CD builds**: Caching packages locally eliminates repeated downloads from PyPI, cutting build times from minutes to seconds.
- **Offline and air-gapped environments**: Teams working in restricted networks need local access to packages without internet connectivity.
- **Version pinning and reproducibility**: A private registry ensures your deployments always use the exact package versions you tested, immune to upstream deletions or changes.
- **Bandwidth savings**: A single cached copy serves all developers and CI agents, reducing external bandwidth usage.
- **Security and compliance**: Internal mirrors let you audit packages before they reach production and block known-vulnerable versions.

## Tool Overview

| Feature | pypiserver | devpi | Bandersnatch |
|---|---|---|---|
| GitHub Stars | 2,024 | 1,163 | 535 |
| Primary Use | Private package server | PyPI proxy + staging + testing | Full PyPI mirror client |
| PEP 503 Simple API | Yes | Yes | Yes |
| PEP 691 JSON API | Yes | Yes | Yes |
| Package Caching | No (manual upload) | Yes (transparent proxy cache) | Yes (full mirror sync) |
| Authentication | htpasswd | Built-in user system | No (read-only mirror) |
| Web UI | Minimal | Full web interface | No |
| Upload Support | Yes (pip twine) | Yes (with ACLs) | No |
| Index Replication | No | Yes (master/slave) | Yes (full PyPI mirror) |
| Last Updated | April 2026 | April 2026 | April 2026 |
| Language | Python | Python | Python |

## pypiserver: Minimal Private Package Server

pypiserver is the simplest option for hosting a private collection of Python packages. It serves `.tar.gz` and `.whl` files from a directory and presents them through the standard PyPI simple API.

**Best for**: Small teams uploading internal wheels, development environments, lightweight deployments.

### Installation

```bash
pip install pypiserver
```

### Running with [docker](https://www.docker.com/)

The official image makes it trivial to deploy:

```yaml
version: "3.3"
services:
  pypiserver:
    image: pypiserver/pypiserver:latest
    volumes:
      - ./packages:/data/packages
      - ./auth:/data/auth
    command: run -P /data/auth/.htpasswd -a update,download,list /data/packages
    ports:
      - "8080:8080"
    restart: unless-stopped
```

### Basic Usage

```bash
# Start without authentication (read-only access)
pypi-server run -p 8080 ~/packages

# Upload a package with twine
twine upload --repository-url http://localhost:8080 mypackage-1.0.0-py3-none-any.whl

# Install from your private server
pip install --index-url http://localhost:8080/simple/ mypackage
```

pypiserver does **not** cache packages from the public PyPI. You must manually upload every package you want to serve. This keeps the footprint small but means it is not suitable as a transparent proxy.

## devpi: Full-Featured PyPI Proxy and Staging Server

devpi is the most feature-rich option. It operates as a caching PyPI proxy, a private package index, and a staging/release tool — all in one. It supports index inheritance, allowing you to create isolated environments for testing packages before promoting them to production.

**Best for**: Enterprise teams, CI/CD pipelines, package staging and testing workflows.

### Key Features

- **Transparent caching**: First request to a package fetches from PyPI, then caches locally for all subsequent requests.
- **Index inheritance**: Create a `dev` index that inherits from `stable`, test new versions, then promote them.
- **Replication**: Set up master/slave configurations for high availability.
- **Search**: Full-text search across cached packages.

### Installation

```bash
pip install devpi-server devpi-web
```

### Running with Docker

```yaml
version: "3.8"
services:
  devpi:
    image: devpi/devpi:latest
    environment:
      - DEVPI_INIT=1
    volumes:
      - devpi_data:/data
    ports:
      - "3141:3141"
    restart: unless-stopped

volumes:
  devpi_data:
```

### Basic Usage

```bash
# Initialize and start devpi-server
devpi-init
devpi-server --start --port 3141

# Create a user and login
devpi use http://localhost:3141
devpi user -c myuser password=mypassword
devpi login myuser --password=mypassword

# Create an index that inherits from root/pypi (the PyPI cache)
devpi index -c dev bases=root/pypi

# Use the cached index
pip install --index-url http://localhost:3141/myuser/dev/+simple/ requests

# Upload your own package
twine upload --repository-url http://localhost:3141/myuser/dev/ mypackage-1.0.0.tar.gz
```

The caching proxy mode is the killer feature: after the first install of any package from PyPI, it is served locally at disk speed. Your CI agents never hit PyPI again for cached packages.

## Bandersnatch: Full PyPI Mirror Client

Bandersnatch (maintained by the Python Packaging Authority) mirrors the entire PyPI repository to local storage. It follows PEP 381, PEP 503, and PEP 691 to provide a complete, standards-compliant mirror.

**Best for**: Air-gapped networks, ISPs or universities providing mirrors to their users, organizations that need full offline access to all PyPI packages.

### How It Works

Bandersnatch is a **synchronization tool**, not a server. It downloads the PyPI package index and files to a local directory. You then serve that direc[nginx](https://nginx.org/)with any HTTP server (nginx, Apache, Caddy).

### Installation

```bash
pip install bandersnatch
```

### Configuration

Create a `bandersnatch.conf`:

```ini
[mirror]
directory = /srv/pypi
json = true
master = https://pypi.org
timeout = 10
global-timeout = 1800
workers = 3
hash-index = false
stop-on-error = false
storage-backend = filesystem
```

### Running the Mirror Sync

```bash
# Initialize the mirror (creates directory structure)
bandersnatch -c bandersnatch.conf mirror

# Run as a cron job to keep it updated
# Add to crontab: */30 * * * * bandersnatch -c /etc/bandersnatch.conf mirror
```

### Serving with nginx

```nginx
server {
    listen 80;
    server_name pypi.internal;

    root /srv/pypi/web;

    location / {
        autoindex off;
        try_files $uri $uri/ /simple/$uri/index.html;
    }

    location /simple/ {
        autoindex on;
        autoindex_format html;
    }
}
```

### Using the Mirror

```bash
pip install --index-url http://pypi.internal/simple/ requests
```

A full PyPI mirror requires significant storage (over 1 TB as of 2026). Bandersnatch supports plugins to filter by package na[actual](https://actualbudget.org/)lowing you to mirror only the packages you actually need.

## Comparison: When to Use Each Tool

| Scenario | Recommended Tool | Why |
|---|---|---|
| Small team, internal packages only | **pypiserver** | Lightweight, no caching overhead, simple setup |
| CI/CD pipeline speed improvement | **devpi** | Transparent caching eliminates repeated PyPI downloads |
| Air-gapped network, offline access | **Bandersnatch** | Full PyPI mirror with no internet dependency |
| Package staging and promotion workflow | **devpi** | Index inheritance, ACLs, and replication support |
| University or ISP public mirror | **Bandersnatch** | Standards-compliant full mirror for external users |
| Quick development server | **pypiserver** | `pip install pypiserver && pypi-server run` in 30 seconds |

## Deployment Comparison: Resource Requirements

| Metric | pypiserver | devpi | Bandersnatch |
|---|---|---|---|
| RAM | ~50 MB | ~200-500 MB | ~100 MB (sync process) |
| Disk (minimal) | Depends on uploaded packages | ~5-50 GB (cached packages) | 1+ TB (full mirror) |
| Disk (filtered) | N/A | ~5-50 GB | 10-100 GB (selective packages) |
| CPU | Minimal | Moderate (indexing) | Moderate (sync) |
| Network | None after upload | Low (cache miss only) | High (initial sync: 100+ GB) |
| Sync Time | N/A | Instant (on-demand cache) | Hours to days (initial full mirror) |

## FAQ

### Can I use pip with any of these servers without configuration changes?

Yes, all three tools implement the PyPI Simple API (PEP 503 and PEP 691). You point pip to your server with `--index-url http://your-server/simple/` and it works exactly like the public PyPI. For permanent configuration, add the index URL to `~/.pip/pip.conf`.

### How much disk space does a full PyPI mirror require?

As of 2026, the complete PyPI repository exceeds 1 terabyte. Bandersnatch supports filtering plugins (`[filter_project]`) to mirror only specific packages, reducing storage to gigabytes instead of terabytes. If you only need your team's dependencies, devpi's caching approach is more storage-efficient since it only stores what you actually use.

### Can these tools host private packages alongside public ones?

pypiserver only serves packages you upload manually. devpi supports this natively — its index inheritance lets you create a private index that falls back to the public PyPI cache for packages you have not uploaded. Bandersnatch mirrors public PyPI only; you would need a separate solution for private packages.

### How do I keep a Bandersnatch mirror up to date?

Bandersnatch includes a `mirror` command that syncs incremental changes from PyPI. Running it every 30 minutes via cron keeps your mirror current. The sync process only downloads new and updated packages, so subsequent runs are fast and bandwidth-efficient compared to the initial full mirror.

### Is it safe to expose a private package server to the internet?

pypiserver supports htpasswd-based authentication for upload access. devpi has a comprehensive user and permission system with per-index ACLs. Bandersnatch has no built-in authentication since it is designed as a read-only mirror — you should put it behind a reverse proxy (nginx, Caddy) with TLS and optional authentication if exposing it externally.

### Which tool is best for a CI/CD pipeline?

devpi is the strongest choice for CI/CD. Its transparent caching proxy means the first build for any package fetches from PyPI, and all subsequent builds hit the local cache. This dramatically reduces build times and eliminates failures caused by PyPI rate limiting or downtime. The index inheritance feature also supports promotion workflows: test packages in a `dev` index, then promote to `stable` for production builds.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "pypiserver vs devpi vs Bandersnatch: Self-Hosted PyPI Mirror Guide 2026",
  "description": "Compare pypiserver, devpi, and Bandersnatch for self-hosting a PyPI mirror or private Python package registry. Docker configs, caching strategies, and deployment guides.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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

For related reading, see our [package registry comparison (Nexus vs Verdaccio vs Pulp)](../self-hosted-package-registry-nexus-verdaccio-pulp-guide-2026/) and the complete [Docker Compose guide](../docker-compose-guide/) for containerizing these services. If you manage Python dependencies at scale, our [dependency automation guide (Renovate vs Dependabot)](../2026-04-19-renovate-vs-dependabot-vs-updatecli-self-hosted-dependency-automation-guide-2026/) covers automated version bumping workflows.
