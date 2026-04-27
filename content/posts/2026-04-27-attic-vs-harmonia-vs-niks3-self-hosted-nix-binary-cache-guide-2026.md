---
title: "Attic vs Harmonia vs niks3: Best Self-Hosted Nix Binary Cache 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "nix", "cache", "devops"]
draft: false
description: "Compare Attic, Harmonia, and niks3 for self-hosted Nix binary cache servers. Complete deployment guide with Docker configs, S3 integration, and garbage collection setup."
---

If you are using the Nix package manager across multiple machines, a local binary cache eliminates redundant builds and dramatically speeds up deployments. Instead of every machine compiling the same package from source, you build once, push to your cache server, and all other machines download the pre-built binary.

This guide compares three self-hosted Nix binary cache servers: **Attic**, **Harmonia**, and **niks3**. All three are open-source, actively maintained, and can be deployed on your own infrastructure. We cover installation, configuration, S3 backend integration, and garbage collection to help you choose the right solution for your team.

## Why Self-Host a Nix Binary Cache

The public `cache.nixos.org` serves pre-built binaries for the official Nixpkgs channel, but it has limitations:

- **Custom overlays**: Packages from your own overlays or flake inputs are not available on the public cache. Every machine must build them from scratch.
- **Bandwidth**: Large organizations with dozens of servers downloading the same derivations waste bandwidth and time.
- **Privacy**: Every derivation your machines request is visible to the public cache operator.
- **Availability**: During Nixpkgs channel transitions or CI surges, the public cache can be slow or rate-limited.
- **CI acceleration**: Self-hosted caches let CI pipelines push build artifacts immediately after completion, so subsequent jobs can fetch instead of rebuild.

A self-hosted binary cache solves all of these problems. You control the data, the signing keys, and the storage backend.

## Comparison Overview

| Feature | Attic | Harmonia | niks3 |
|---|---|---|---|
| **GitHub Stars** | 1,842 | 483 | 184 |
| **Last Updated** | Apr 2026 | Apr 2026 | Apr 2026 |
| **Language** | Rust | Rust | Go |
| **License** | Apache 2.0 | Apache 2.0 | MIT |
| **Multi-Tenant** | Yes | No | No |
| **S3 Backend** | Native (required) | Optional | Native (required) |
| **Garbage Collection** | LRU-based | Manual | SQL-based GC |
| **Global Deduplication** | Yes (NAR + chunk) | No | No |
| **Managed Signing** | Server-side | Client-side | Client-side |
| **Docker Image** | Available (NixOS) | Available (NixOS) | Official (ghcr.io) |
| **NixOS Module** | Yes | Yes | No |
| **HTTP API** | REST + gRPC | Nix HTTP Protocol | REST |
| **Upstream Caching** | Yes (configurable) | Yes | No |

## Attic: Multi-Tenant S3-Backed Cache

[Attic](https://github.com/zhaofengli/attic) is the most feature-complete self-hosted Nix binary cache. It stores NARs (Nix Archive files) in S3-compatible storage and provides multi-tenancy with per-cache access control. Its standout features are global deduplication across tenants and server-side key management.

### Key Features

- **Multi-tenancy**: Create isolated caches for different teams or projects. Tenants cannot see each other's paths.
- **Global deduplication**: When the same NAR is uploaded to multiple caches, Attic stores it once and creates view mappings.
- **Managed signing**: The server holds the signing key. Users pushing paths never see the private key.
- **Upstream passthrough**: Configure Attic to proxy requests to `cache.nixos.org` for official packages while serving local builds from your own cache.
- **Garbage collection**: LRU-based cleanup removes the least-recently-used store paths when storage limits are reached.

### Deployment with Docker

Attic ships as a NixOS module but can run in any Docker environment. The server requires PostgreSQL for metadata and an S3-compatible backend (MinIO, AWS S3, Cloudflare R2).

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: attic
      POSTGRES_PASSWORD: attic-secret
      POSTGRES_DB: attic
    volumes:
      - pgdata:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    command: server /data
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minio-secret
    volumes:
      - s3data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  attic-server:
    image: ghcr.io/zhaofengli/attic-server:latest
    depends_on:
      - postgres
      - minio
    ports:
      - "8080:8080"
    environment:
      ATTIC_SERVER_DATABASE_URL: postgresql://attic:attic-secret@postgres/attic
      ATTIC_SERVER_STORAGE_S3_ENDPOINT: http://minio:9000
      ATTIC_SERVER_STORAGE_S3_ACCESS_KEY: minioadmin
      ATTIC_SERVER_STORAGE_S3_SECRET_KEY: minio-secret
      ATTIC_SERVER_STORAGE_S3_BUCKET: attic-nar
      ATTIC_SERVER_JWT_SECRET: "your-jwt-secret-here"
      ATTIC_SERVER_PUBLIC_URL: http://localhost:8080

volumes:
  pgdata:
  s3data:
```

### Pushing Paths to Attic

```bash
# Login to your Attic server
attic login local http://localhost:8080 your-token

# Create a cache
attic cache create my-cache --public

# Build and push a package
nix build nixpkgs#hello
attic push local:my-cache ./result
```

## Harmonia: High-Performance Rust Binary Cache

[Harmonia](https://github.com/nix-community/harmonia) is a Nix binary cache server written in Rust, maintained under the nix-community organization. It implements the standard Nix HTTP binary cache protocol and can serve as a drop-in replacement for `cache.nixos.org`.

### Key Features

- **Nix protocol native**: Harmonia speaks the exact same HTTP protocol as the official Nix cache, so no client-side changes are needed.
- **Rust performance**: Written in Rust with async I/O for high-throughput serving of NAR files.
- **Pluggable storage**: Supports local filesystem, S3, and SSH-backed stores.
- **Upstream mirroring**: Can be configured as a mirror of `cache.nixos.org`, caching paths on first request.
- **Simple architecture**: No database required for basic operation. The store metadata lives alongside the NAR files.

### Deployment

Harmonia uses a TOML configuration file and can run as a standalone binary or in a NixOS container.

```toml
# harmonia.toml
[server]
listen = "[::]:8080"
base-url = "http://localhost:8080"

[store]
type = "local"
path = "/var/lib/harmonia/store"

[upstream]
url = "https://cache.nixos.org"
enabled = true
```

### Docker Compose Setup

```yaml
version: "3.8"

services:
  harmonia:
    image: ghcr.io/nix-community/harmonia:latest
    ports:
      - "8080:8080"
    volumes:
      - ./harmonia.toml:/etc/harmonia/harmonia.toml:ro
      - harmonia-store:/var/lib/harmonia/store
    command: ["harmonia-cache", "-c", "/etc/harmonia/harmonia.toml"]

volumes:
  harmonia-store:
```

### Configuring Nix to Use Harmonia

Add the following to your `nix.conf` on client machines:

```ini
extra-substituters = http://your-server:8080
extra-trusted-public-keys = harmonia:your-public-key-here
```

## niks3: S3-Backed Cache with Garbage Collection

[niks3](https://github.com/Mic92/niks3) is a Go-based Nix binary cache server that stores NARs in S3-compatible storage. It includes built-in garbage collection, SQL-based metadata, and a simple REST API for path management.

### Key Features

- **S3-native**: Designed from the ground up for S3-compatible backends. Works with AWS S3, MinIO, and any S3-compatible service.
- **Garbage collection**: SQL-based GC identifies and removes orphaned NARs that are no longer referenced by any cache entry.
- **SQLite metadata**: Uses SQLite for lightweight metadata storage, avoiding the need for a separate PostgreSQL instance.
- **Go simplicity**: Single binary deployment with minimal dependencies.
- **Rate limiting**: Built-in request rate limiting to protect against abuse.

### Docker Compose Deployment

niks3 publishes official Docker images to `ghcr.io/Mic92/niks3`.

```yaml
version: "3.8"

services:
  niks3:
    image: ghcr.io/mic92/niks3:latest
    ports:
      - "8080:8080"
    environment:
      NIKS3_S3_ENDPOINT: http://minio:9000
      NIKS3_S3_BUCKET: nix-cache
      NIKS3_S3_ACCESS_KEY: minioadmin
      NIKS3_S3_SECRET_KEY: minio-secret
      NIKS3_S3_REGION: us-east-1
      NIKS3_SIGNING_KEY_PATH: /etc/niks3/signing-key.sec
      NIKS3_CACHE_NAME: "my-nix-cache"
    volumes:
      - ./signing-key.sec:/etc/niks3/signing-key.sec:ro
      - niks3-db:/var/lib/niks3
    depends_on:
      - minio

  minio:
    image: minio/minio:latest
    command: server /data
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minio-secret
    volumes:
      - s3data:/data
    ports:
      - "9000:9000"

volumes:
  niks3-db:
  s3data:
```

### Uploading to niks3

Use `nix copy` to push store paths:

```bash
# Generate a signing key if you don't have one
nix store generate-binary-cache-key my-cache my-cache.sec my-cache.pub

# Upload a derivation
nix copy --to http://localhost:8080 nixpkgs#hello

# Verify the cache
curl http://localhost:8080/my-cache/nix-cache-info
```

## Performance Considerations

Each tool has different performance characteristics based on its architecture:

| Metric | Attic | Harmonia | niks3 |
|---|---|---|---|
| **Cold Start** | ~2s (DB + S3 init) | ~0.5s (single binary) | ~0.3s (single binary) |
| **Throughput** | High (chunked uploads) | High (async Rust) | Medium (Go net/http) |
| **Storage Efficiency** | Excellent (global dedup) | Good (NAR-level) | Good (NAR-level) |
| **Memory Usage** | ~200MB (server + DB) | ~50MB | ~80MB |
| **Disk I/O** | Low (S3-first) | Medium (local store) | Low (S3-first) |

For small teams (under 10 machines), any of the three will perform well. For larger organizations with hundreds of machines and thousands of unique derivations, Attic's global deduplication and Harmonia's async I/O provide the best scaling characteristics.

## Choosing the Right Cache

**Choose Attic if:**
- You need multi-tenancy for multiple teams
- You want server-side key management
- Global deduplication matters for your storage budget
- You are already running PostgreSQL and S3/MinIO

**Choose Harmonia if:**
- You want the simplest setup (no database required)
- You need protocol-level compatibility with `cache.nixos.org`
- You prefer upstream mirroring over push-based caching
- Your team values the nix-community ecosystem

**Choose niks3 if:**
- You want a Go single binary with minimal dependencies
- SQLite is preferred over PostgreSQL for metadata
- Built-in rate limiting is important
- You want S3 storage with SQL-based garbage collection

For related reading, see our [build cache comparison covering sccache, ccache, and Icecream](../2026-04-23-sccache-vs-ccache-vs-icecream-self-hosted-build-cache-2026/), the [package registry guide for Nexus, Verdaccio, and Pulp](../self-hosted-package-registry-nexus-verdaccio-pulp-guide-2026/), and [container registry solutions including Harbor, Distribution, and Zot](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/).

## FAQ

### What is a Nix binary cache and why do I need one?

A Nix binary cache stores pre-built package outputs (NAR files) so that machines can download them instead of compiling from source. If you use Nix across multiple servers or a CI pipeline, a self-hosted cache prevents redundant builds, saves CPU time, and ensures consistent binary artifacts across your infrastructure.

### Do I need S3-compatible storage for these tools?

Attic and niks3 require S3-compatible storage (MinIO, AWS S3, Cloudflare R2, etc.) as their backend. Harmonia supports local filesystem storage as its default, making it the simplest option if you do not want to manage an S3 backend. You can also add S3 support to Harmonia as an optional configuration.

### How do I configure Nix clients to use my self-hosted cache?

Add your cache URL and public key to the Nix configuration on each client machine. Edit `/etc/nix/nix.conf` or `~/.config/nix/nix.conf`:

```ini
extra-substituters = http://your-cache-server:8080
extra-trusted-public-keys = your-cache-name:base64-public-key
```

Then run `nix build` as usual. Nix will query your cache before falling back to `cache.nixos.org`.

### Can I use these caches with Nix Flakes?

Yes. All three tools serve the standard Nix binary cache protocol, which is fully compatible with Nix Flakes. Flakes use the same substituter mechanism as traditional Nix expressions. Add your cache to `nixConfig.extra-substituters` in your `flake.nix` or to the system-wide `nix.conf`.

### How does garbage collection work?

Attic uses LRU-based garbage collection, automatically removing the least-recently-accessed store paths when your cache reaches its storage limit. Harmonia requires manual cleanup since it has no built-in GC daemon. niks3 includes SQL-based garbage collection that identifies orphaned NARs (no longer referenced by any cache entry) and removes them from S3.

### Is it safe to self-host the signing key?

The signing key ensures clients can verify that downloaded binaries came from your trusted cache. You should protect the private key file and never expose it publicly. Attic manages the key server-side, so only the Attic process has access. Harmonia and niks3 require you to manage the key file on disk. In all cases, distribute only the public key to client machines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Attic vs Harmonia vs niks3: Best Self-Hosted Nix Binary Cache 2026",
  "description": "Compare Attic, Harmonia, and niks3 for self-hosted Nix binary cache servers. Complete deployment guide with Docker configs, S3 integration, and garbage collection setup.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
