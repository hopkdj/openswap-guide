---
title: "Athens vs GOPROXY: Self-Hosted Go Module Proxy Guide 2026"
date: 2026-04-30
tags: ["comparison", "guide", "self-hosted", "go", "devops", "package-management"]
draft: false
description: "Complete guide to self-hosted Go module proxies in 2026. Compare Athens and GOPROXY for caching Go modules, speeding up CI builds, and securing your Go dependency pipeline with Docker Compose setups."
---

Every Go project depends on external modules — from the standard library extensions to third-party packages pulled from proxy.golang.org. Relying entirely on public module proxies introduces real risks that compound as your team and codebase grow. Build pipelines break when upstream proxies go down, supply chain attacks slip through unchecked module downloads, and network egress costs spiral with every CI run pulling the same dependencies.

A self-hosted Go module proxy solves all three problems at once. It caches modules locally for faster builds, gives you control over which packages enter your supply chain, and eliminates repeated network calls to external services. In 2026, two open-source projects lead this space: **Athens** and **GOPROXY**. Each takes a fundamentally different approach to the same problem.

This guide compares both tools, provides production-ready Docker Compose configurations, and helps you choose the right proxy for your Go development workflow.

## Why Self-Host a Go Module Proxy?

Go modules changed how the language manages dependencies, but the default behavior — downloading directly from `proxy.golang.org` — isn't ideal for every organization. Here is why teams choose to run their own proxy:

- **Build speed** — cached modules serve from local storage, cutting CI build times by 40-70% for large projects with hundreds of dependencies
- **Supply chain security** — validate module checksums against your own `sum.golang.org` mirror and block unapproved packages before they reach your codebase
- **Offline builds** — once cached, modules are available even when the public proxy is unreachable or your network is isolated
- **Private modules** — host internal Go packages alongside public ones through a single `GOPROXY` endpoint, eliminating separate private registry tooling
- **Bandwidth savings** — a single cached module serves every developer and CI job, reducing egress costs for teams running many concurrent builds
- **Compliance and audit** — log every module download, track versions in use across your organization, and maintain an artifact trail for security reviews

For teams running Go at scale — whether that means a handful of microservices or a monorepo with thousands of packages — a self-hosted proxy pays for itself in saved build time alone.

## Athens: The Full-Featured Go Module Proxy

[Athens](https://github.com/gomods/athens) (4,740 stars, last updated April 2026) is the most widely deployed self-hosted Go module proxy. Originally created as an official Go community project, it provides a complete proxy server with pluggable storage backends, a web-based module browser, and support for private Go repositories.

### Key Features

- **Multiple storage backends** — MongoDB, MinIO/S3, Azure Blob Storage, Google Cloud Storage, and local disk
- **Web UI** — browse cached modules, view versions, and download packages through a built-in interface
- **Private module support** — configure wildcard patterns (`GOPRIVATE`) to proxy internal repositories alongside public ones
- **Module download filtering** — whitelist or block specific modules and version patterns
- **Distributed caching** — run multiple Athens instances behind a load balancer with shared storage
- **VCS integration** — pulls modules directly from GitHub, GitLab, Bitbucket, or any Git-compatible source
- **Go checksum database integration** — validates module integrity against `sum.golang.org` by default

### Docker Compose Deployment

Here is a production-ready Athens setup with MongoDB for module storage and local disk for configuration:

```yaml
version: '3.8'

services:
  athens:
    image: gomods/athens:latest
    container_name: athens-proxy
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - ATHENS_STORAGE_TYPE=mongo
      - ATHENS_MONGO_STORAGE_URL=mongodb://mongo:27017
      - ATHENS_GOGET_WORKERS=10
      - ATHENS_GOGET_MAX_TRIES=3
      - ATHENS_TIMEOUT=300
      - ATHENS_FILTER_FILE=/config/filter.json
      - ATHENS_BASIC_AUTH_USER=
      - ATHENS_BASIC_AUTH_PASS=
      - GONOSUMCHECK=github.com/my-org/*
      - GONOSUMDB=github.com/my-org/*
      - GOFLAGS=-insecure
    volumes:
      - ./config:/config:ro
    depends_on:
      - mongo
    networks:
      - athens-net

  mongo:
    image: mongo:7
    container_name: athens-mongo
    restart: unless-stopped
    volumes:
      - mongo-data:/data/db
    networks:
      - athens-net

networks:
  athens-net:
    driver: bridge

volumes:
  mongo-data:
```

### Athens Configuration File

Create `config/filter.json` to control which modules Athens will proxy:

```json
{
  "Exclude": [
    "github.com/untrusted-org/*",
    "github.com/deprecated-module/*"
  ],
  "Include": [
    "github.com/my-org/*"
  ]
}
```

Then configure your Go client to use the proxy:

```bash
# Point Go to your self-hosted proxy
export GOPROXY=http://localhost:3000

# Keep sum verification enabled for public modules
export GONOSUMCHECK=github.com/my-org/*

# Mark internal modules as private (bypasses proxy and checksum DB)
export GOPRIVATE=github.com/my-org/*

# Verify the proxy is working
go env GOPROXY
go list -m -json github.com/gin-gonic/gin
```

### S3 Storage Backend

For production deployments, swap MongoDB for S3-compatible storage to enable multi-region caching:

```yaml
  athens:
    image: gomods/athens:latest
    environment:
      - ATHENS_STORAGE_TYPE=s3
      - ATHENS_S3_REGION=us-east-1
      - ATHENS_S3_BUCKET=go-modules-cache
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - ATHENS_STORAGE_DOWNLOAD_URL=https://go-modules.example.com
```

This configuration is particularly useful for teams running CI across multiple geographic regions, where each region needs fast local access to the same module cache.

## GOPROXY: The Minimalist Alternative

[GOPROXY](https://github.com/goproxy/goproxy) (1,478 stars, last updated April 2026) takes a different approach. Rather than a full-featured server, it provides a lightweight Go module proxy **handler** — a library you embed into your own Go application. This gives you complete control over the proxy's behavior, storage, and integration with existing infrastructure.

### Key Features

- **Minimal footprint** — the core handler is under 1,000 lines of Go code
- **Embeddable** — integrate into existing Go services, reverse proxies, or CI pipelines
- **Custom storage** — implement your own `Cacher` interface to store modules anywhere
- **Protocol compliance** — fully implements the [GOPROXY protocol specification](https://go.dev/ref/mod#goproxy-protocol)
- **No external dependencies** — runs as a single Go binary with no database requirement
- **Hot module caching** — cache modules to disk with configurable TTL and eviction policies

### Self-Hosted Deployment

Because GOPROXY is a library, you wrap it in a minimal Go server. Here is a complete working example:

```go
package main

import (
    "log"
    "net/http"
    "os"

    "github.com/goproxy/goproxy"
    "github.com/goproxy/goproxy/cacher"
)

func main() {
    // Create a disk-based cacher that stores modules in /var/cache/go-modules
    cacheDir := os.Getenv("CACHE_DIR")
    if cacheDir == "" {
        cacheDir = "/var/cache/go-modules"
    }
    
    diskCache, err := cacher.NewDisk(cacheDir)
    if err != nil {
        log.Fatalf("Failed to create disk cache: %v", err)
    }

    // Create the GOPROXY handler with disk caching
    proxy := &goproxy.Goproxy{
        GoBinEnv: append(
            os.Environ(),
            "GOPROXY=https://proxy.golang.org,direct",
            "GONOSUMDB=*",
        ),
        ProxiedGoSumDBSum: []string{"GOPROXY.IO"},
        Cacher:            diskCache,
    }

    // Serve the proxy on port 8080
    log.Println("Go module proxy listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", proxy))
}
```

Build and run:

```bash
go mod init my-goproxy
go get github.com/goproxy/goproxy
go build -o goproxy-server .
./goproxy-server
```

### Docker Compose for GOPROXY

Package the self-hosted proxy in a lightweight container:

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY main.go .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /goproxy

FROM alpine:3.19
RUN apk add --no-cache go git
COPY --from=builder /goproxy /usr/local/bin/
RUN mkdir -p /var/cache/go-modules
VOLUME ["/var/cache/go-modules"]
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/goproxy"]
```

```yaml
version: '3.8'

services:
  goproxy:
    build: .
    container_name: goproxy-server
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - CACHE_DIR=/var/cache/go-modules
    volumes:
      - goproxy-cache:/var/cache/go-modules

volumes:
  goproxy-cache:
```

Build and start:

```bash
docker compose up -d --build

# Configure your Go client
export GOPROXY=http://localhost:8080
go get github.com/stretchr/testify
```

## Feature Comparison

| Feature | Athens | GOPROXY |
|---------|--------|---------|
| **Type** | Standalone server | Embeddable library |
| **Stars** | 4,740 | 1,478 |
| **Storage** | MongoDB, S3, Azure, GCS, disk | Disk (custom implementations possible) |
| **Web UI** | Built-in module browser | None |
| **Private modules** | Yes (filter config) | Yes (via `GoBinEnv`) |
| **Checksum verification** | Built-in `sum.golang.org` | Configurable |
| **Docker image** | Official (`gomods/athens`) | Build from source |
| **External dependencies** | MongoDB or object storage | None |
| **Multi-instance** | Shared storage backend | Each instance has own cache |
| **Download filtering** | JSON config file | Programmatic control |
| **Memory footprint** | ~50-100 MB with MongoDB | ~10-20 MB |
| **Best for** | Teams needing a ready-to-use proxy | Developers embedding proxy into existing systems |

## Choosing the Right Go Module Proxy

**Choose Athens when:**
- You need a production-ready proxy with zero custom code
- Multiple storage backend options matter for your infrastructure
- A web-based module browser would help your team audit dependencies
- You want built-in support for private Go repositories
- Your CI runs across multiple regions with shared object storage

**Choose GOPROXY when:**
- You want to embed proxy functionality into an existing Go service
- Minimal dependencies and small binary size are priorities
- You need custom caching logic (e.g., Redis-backed cache, custom eviction)
- Your team prefers programmatic control over configuration files
- You are building a custom developer platform with integrated module proxying

For most organizations, **Athens** is the right starting point. It deploys in minutes with Docker Compose, scales horizontally with shared storage, and requires no code to operate. GOPROXY shines in specialized scenarios where the proxy is one component of a larger internal platform.

## Production Best Practices

### 1. Configure Upstream Proxy Fallback

Always configure Athens or GOPROXY to fall back to the official Go proxy:

```bash
# In Athens config
ATHENS_GOGET_ROOT_URL=https://proxy.golang.org

# In GOPROXY handler
GoBinEnv: ["GOPROXY=https://proxy.golang.org,direct"]
```

This ensures your proxy can fetch modules it has not yet cached, while still serving cached copies for repeat requests.

### 2. Enable Module Checksum Verification

Keep the Go checksum database active to detect tampered modules:

```bash
# Athens enables this by default
# For GOPROXY, configure the sum DB:
ProxiedGoSumDBSum: []string{"sum.golang.org"}
```

### 3. Set Appropriate Timeouts

Large modules can take time to download. Configure generous timeouts to avoid partial downloads:

```yaml
environment:
  - ATHENS_TIMEOUT=300        # 5 minutes for large modules
  - ATHENS_GOGET_WORKERS=10   # Parallel download workers
  - ATHENS_GOGET_MAX_TRIES=3  # Retry failed downloads
```

### 4. Use Reverse Proxy for HTTPS

Terminate TLS with a reverse proxy (Nginx, Caddy, or Traefik) in front of Athens:

```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - athens
```

```nginx
server {
    listen 443 ssl;
    server_name go-proxy.example.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    location / {
        proxy_pass http://athens:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. Monitor Cache Hit Rates

Track how often your proxy serves cached modules versus fetching from upstream. Athens exposes Prometheus metrics on `/metrics` by default:

```bash
# Query cache hit rate
curl -s http://localhost:3000/metrics | grep athens_

# Key metrics:
# athens_module_get_total - total module fetch requests
# athens_module_get_from_storage_total - cache hits
# athens_module_get_from_upstream_total - upstream fetches
```

For related reading, see our guide on [self-hosted package registries with Nexus and Verdaccio](../self-hosted-package-registry-nexus-verdaccio-pulp-guide-2026/) for a broader view of artifact management, or our comparison of [self-hosted SBOM tracking tools](../self-hosted-sbom-dependency-tracking-dependency-track-syft-cyclonedx-guide-2026/) to complement your Go module proxy with software bill of materials generation. Teams managing CI/CD pipelines should also review our [dependency automation guide covering Renovate and Dependabot](../2026-04-19-renovate-vs-dependabot-vs-updatecli-self-hosted-dependency-automation-guide-2026/) for automated module update workflows.

## FAQ

### What is a Go module proxy and why do I need one?

A Go module proxy is a server that implements the GOPROXY protocol, caching Go module downloads and serving them to clients on request. Instead of every `go get` or `go build` fetching directly from `proxy.golang.org`, your proxy serves cached copies. This speeds up builds, reduces network dependency, and gives you control over which modules your team can use.

### Does Athens support private Go modules?

Yes. Athens can proxy private repositories hosted on GitHub, GitLab, or any Git-compatible service. Configure `GOPRIVATE` environment variables and authentication tokens (via `ATHENS_GITHUB_TOKEN`, `ATHENS_GITLAB_TOKEN`, or SSH keys) to enable access. You can also use the filter file to include or exclude specific module patterns.

### Can I run multiple Athens instances for high availability?

Yes. Athens is designed for horizontal scaling. Deploy multiple instances behind a load balancer and point them at a shared storage backend (MongoDB replica set, S3 bucket, or Azure Blob container). Each instance reads and writes to the same storage layer, so any cached module is available from any node.

### What is the difference between Athens and GOPROXY?

Athens is a complete, standalone Go module proxy server with built-in storage, web UI, and configuration. GOPROXY is a Go library (handler) that you embed into your own application. Think of Athens as a ready-to-deploy product and GOPROXY as a building block for custom solutions.

### How do I migrate from proxy.golang.org to a self-hosted proxy?

Point your `GOPROXY` environment variable to your proxy's URL: `export GOPROXY=http://your-proxy:3000`. Go will automatically start routing all module requests through your proxy. Existing builds will work immediately — the proxy fetches any uncached modules from upstream on first request, then serves them from cache on subsequent requests. No manual import or pre-warming is required.

### Does GOPROXY cache modules to disk?

Yes, when configured with a disk-based cacher. The `cacher.NewDisk(path)` function creates a local file system cache at the specified directory. You can also implement the `Cacher` interface to use Redis, etcd, or any other storage system.

### How do I secure my self-hosted Go module proxy?

Place the proxy behind HTTPS using a reverse proxy (Nginx, Caddy, or Traefik) with TLS certificates. For Athens, you can enable basic authentication with `ATHENS_BASIC_AUTH_USER` and `ATHENS_BASIC_AUTH_PASS`. For team environments, integrate with OAuth or SSO through your reverse proxy. Always keep module checksum verification enabled to detect tampered packages.

### Can I use Athens with Go workspaces (Go 1.18+)?

Yes. Athens works transparently with Go workspaces (`go.work` files). The proxy intercepts all module resolution requests regardless of whether they come from a single module or a workspace. No special configuration is needed — just set `GOPROXY` in your environment or `go.env` file.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Athens vs GOPROXY: Self-Hosted Go Module Proxy Guide 2026",
  "description": "Complete guide to self-hosted Go module proxies in 2026. Compare Athens and GOPROXY for caching Go modules, speeding up CI builds, and securing your Go dependency pipeline with Docker Compose setups.",
  "datePublished": "2026-04-30",
  "dateModified": "2026-04-30",
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
