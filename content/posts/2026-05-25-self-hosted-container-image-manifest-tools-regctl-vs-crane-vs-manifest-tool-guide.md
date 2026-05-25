---
title: "Self-Hosted Container Image Manifest Tools: regctl vs crane vs manifest-tool"
date: "2026-05-25"
tags: ["containers", "docker", "registry", "devops", "multiarch", "image-management"]
draft: false
---

Container image manifests define the metadata, layers, and platform compatibility of OCI container images. When working with multi-architecture images, custom registries, or supply chain security, you need tools that can inspect, manipulate, and copy image manifests across registries. This guide compares three leading open-source tools: **regctl**, **crane**, and **manifest-tool**.

## Understanding Container Image Manifests

An OCI image manifest is a JSON document that describes a container image's layers, configuration blob, media types, and platform metadata. Modern registries support **manifest lists** (also called image indexes), which allow a single image tag to resolve to different manifests based on the pulling platform's architecture (amd64, arm64, arm/v7, etc.).

Key operations you need manifest tools for:

1. **Multi-architecture builds** — Create and manage manifest lists for cross-platform images
2. **Image copying** — Transfer images between registries without pulling to local disk
3. **Manifest inspection** — View and validate manifest content, digests, and layer metadata
4. **Tag manipulation** — Copy, retag, and manage image references across registries

For registry hosting, see our [Docker registry proxy comparison](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/) and [container registry garbage collection guide](../2026-05-22-container-registry-garbage-collection-harbor-distribution-zot-guide/).

## regctl: Comprehensive OCI Registry Client

[**regctl**](https://github.com/regclient/regclient) (1,842+ stars) is a full-featured OCI registry client written in Go, providing both a CLI tool (`regctl`) and a Go library (`regclient`) for programmatic registry operations.

### Key Features

- **Complete OCI spec support** — Full implementation of the OCI Distribution and Image specs
- **Manifest list manipulation** — Create, inspect, and modify image indexes for multi-arch images
- **Registry-to-registry copy** — Transfer images directly between registries without local storage
- **Blob-level operations** — Inspect, delete, and manage individual image layers
- **Authentication flexibility** — Supports Docker config, OAuth2, token auth, and basic auth
- **Go library** — Embed registry operations in your own Go applications

### Installation

```bash
# Via Go install
go install github.com/regclient/regclient/cmd/regctl@latest

# Download binary
curl -sSLO https://github.com/regclient/regclient/releases/latest/download/regctl-linux-amd64
chmod +x regctl-linux-amd64
sudo mv regctl-linux-amd64 /usr/local/bin/regctl

# Docker
docker run --rm ghcr.io/regclient/regctl:latest --help
```

### Common Operations

```bash
# Inspect an image manifest
regctl image manifest registry.example.com/myapp:v1.0

# Inspect as pretty JSON
regctl image manifest registry.example.com/myapp:v1.0 --format body

# Copy image between registries
regctl image copy docker.io/library/nginx:latest registry.example.com/nginx:latest

# Create a multi-arch manifest list
regctl image create registry.example.com/myapp:latest \
  --ref registry.example.com/myapp:linux-amd64 \
  --ref registry.example.com/myapp:linux-arm64

# Annotate a manifest list with platform info
regctl image mod registry.example.com/myapp:latest \
  --to-oci --annotate "org.opencontainers.image.arch=amd64"
```

### Docker Compose for Registry Operations

```yaml
version: "3.8"
services:
  regctl-copy:
    image: ghcr.io/regclient/regctl:latest
    environment:
      - REGCTL_USER=${SRC_USER}
      - REGCTL_PASS=${SRC_PASS}
    volumes:
      - ${HOME}/.docker/config.json:/root/.docker/config.json:ro
    entrypoint: ["/regctl"]
    command:
      - "image"
      - "copy"
      - "docker.io/library/nginx:latest"
      - "registry.example.com/nginx:latest"

  regctl-inspect:
    image: ghcr.io/regclient/regctl:latest
    entrypoint: ["/regctl"]
    command:
      - "image"
      - "manifest"
      - "registry.example.com/myapp:v1.0"
      - "--format"
      - "body"
```

### When to Use regctl

- **Full OCI registry operations** — Most comprehensive tool for registry management
- **Programmatic integration** — Go library for embedding in custom tooling
- **Multi-arch manifest creation** — Native support for creating and modifying manifest lists
- **Blob-level control** — Inspect and manage individual image layers

## crane: Fast Container Registry Operations

[**crane**](https://github.com/google/go-containerregistry) (3,880+ stars, part of go-containerregistry) is a fast, focused CLI tool for container image operations. It provides a subset of go-containerregistry's capabilities as a user-friendly CLI.

### Key Features

- **Speed optimized** — Written in Go with parallel layer transfers for maximum throughput
- **Simple CLI interface** — Clean, intuitive commands for common registry operations
- **OCI and Docker v2 support** — Works with both OCI and Docker manifest formats
- **Digest-based operations** — Reference images by SHA256 digest for immutability
- **Authentication via Docker config** — Reuses existing Docker credentials seamlessly
- **Go library ecosystem** — Part of the broader go-containerregistry library used by many projects

### Installation

```bash
# Via Go install
go install github.com/google/go-containerregistry/cmd/crane@latest

# Download binary
curl -sSLO https://github.com/google/go-containerregistry/releases/latest/download/go-containerregistry_Linux_x86_64.tar.gz
tar xf go-containerregistry_Linux_x86_64.tar.gz crane
sudo mv crane /usr/local/bin/

# Docker
docker run --rm gcr.io/go-containerregistry/crane --help
```

### Common Operations

```bash
# Pull and inspect manifest
crane manifest docker.io/library/nginx:latest

# Get image digest
crane digest docker.io/library/nginx:latest

# Copy between registries
crane cp docker.io/library/nginx:latest registry.example.com/nginx:latest

# List tags in a repository
crane ls registry.example.com/myapp

# Export image to tar
crane export docker.io/library/nginx:latest nginx.tar

# Flatten an image (combine layers)
crane flatten registry.example.com/myapp:latest
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  crane-copy:
    image: gcr.io/go-containerregistry/crane:latest
    volumes:
      - ${HOME}/.docker/config.json:/root/.docker/config.json:ro
    command: ["cp", "docker.io/library/nginx:latest", "registry.example.com/nginx:latest"]

  crane-inspect:
    image: gcr.io/go-containerregistry/crane:latest
    command: ["manifest", "registry.example.com/myapp:v1.0"]

  crane-tag-list:
    image: gcr.io/go-containerregistry/crane:latest
    command: ["ls", "registry.example.com/myapp"]
```

### When to Use crane

- **Fast registry transfers** — Optimized parallel transfers for large images
- **Simple CLI workflows** — Clean, minimal interface for common operations
- **Digest pinning** — Easy digest retrieval for supply chain security
- **Integration with Google Cloud** — Native GCR and Artifact Registry support

## manifest-tool: Dedicated Multi-Arch Manifest Management

[**manifest-tool**](https://github.com/estesp/manifest-tool) (836+ stars) is a specialized CLI tool focused exclusively on creating and querying container image manifest lists. Created by Phil Estes (estesp), a Docker/Moby maintainer, it fills a specific gap in multi-architecture image management.

### Key Features

- **Manifest list creation** — Build image indexes from individual platform-specific images
- **YAML push manifests** — Define multi-arch images declaratively in YAML files
- **OCI index conversion** — Convert Docker manifest lists to OCI image indexes
- **Query operations** — Inspect manifest list contents and individual platform manifests
- **Minimal footprint** — Single-purpose tool with no extra dependencies
- **Docker Hub integration** — Works seamlessly with Docker Hub's multi-arch image support

### Installation

```bash
# Download binary
curl -sSLO https://github.com/estesp/manifest-tool/releases/latest/download/manifest-tool-linux-amd64
chmod +x manifest-tool-linux-amd64
sudo mv manifest-tool-linux-amd64 /usr/local/bin/manifest-tool

# Go install
go install github.com/estesp/manifest-tool/v2/cmd/manifest-tool@latest
```

### YAML Push Manifest

```yaml
# manifest.yaml
image: registry.example.com/myapp:latest
manifests:
  - image: registry.example.com/myapp:linux-amd64
    platform:
      architecture: amd64
      os: linux
  - image: registry.example.com/myapp:linux-arm64
    platform:
      architecture: arm64
      os: linux
  - image: registry.example.com/myapp:linux-arm
    platform:
      architecture: arm
      os: linux
      variant: v7
```

```bash
# Push manifest list from YAML
manifest-tool push from-spec manifest.yaml

# Inspect a manifest list
manifest-tool inspect registry.example.com/myapp:latest

# Convert to OCI format
manifest-tool push from-spec --to-oci manifest.yaml
```

### Docker Compose for Multi-Arch Builds

```yaml
version: "3.8"
services:
  manifest-create:
    image: alpine:latest
    volumes:
      - ./manifest.yaml:/manifest.yaml:ro
      - ${HOME}/.docker/config.json:/root/.docker/config.json:ro
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache curl
        curl -sSLO https://github.com/estesp/manifest-tool/releases/latest/download/manifest-tool-linux-amd64
        chmod +x manifest-tool-linux-amd64
        ./manifest-tool-linux-amd64 push from-spec /manifest.yaml

  manifest-inspect:
    image: alpine:latest
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache curl
        curl -sSLO https://github.com/estesp/manifest-tool/releases/latest/download/manifest-tool-linux-amd64
        chmod +x manifest-tool-linux-amd64
        ./manifest-tool-linux-amd64 inspect registry.example.com/myapp:latest
```

### When to Use manifest-tool

- **Declarative multi-arch builds** — YAML-defined manifest lists are version-controllable
- **Docker Hub multi-arch images** — Purpose-built for Docker Hub's manifest format
- **Minimal toolchain** — Single binary focused on one job, done well
- **CI/CD manifest generation** — YAML specs integrate with build pipelines

## Comparison Table

| Feature | regctl | crane | manifest-tool |
|---------|--------|-------|---------------|
| **Primary Focus** | Full OCI registry client | Fast image operations | Manifest list management |
| **Manifest Creation** | Yes (image create) | Limited (no native) | Yes (push from-spec) |
| **Registry Copy** | Yes | Yes (optimized) | No |
| **YAML Manifest Spec** | No | No | Yes |
| **OCI Index Conversion** | Yes | Limited | Yes |
| **Blob Operations** | Yes | Yes (export/flatten) | No |
| **Go Library** | Yes (regclient) | Yes (go-containerregistry) | No |
| **Tag Listing** | Yes | Yes | No |
| **Stars** | 1,842+ | 3,880+ | 836+ |
| **Best For** | Comprehensive registry ops | Speed and simplicity | Multi-arch manifest creation |

## Choosing the Right Tool

### For Registry Administrators

Use **regctl** for comprehensive registry management. Its complete OCI spec support, blob-level operations, and Go library make it the most versatile tool for registry operations.

### For CI/CD Pipelines

Use **crane** for fast, reliable image transfers. Its parallel transfer optimization and clean CLI make it ideal for automated pipelines that need to copy and verify images quickly.

### For Multi-Architecture Publishing

Use **manifest-tool** when your primary need is creating and managing multi-architecture manifest lists. The YAML push spec format is declarative and version-controllable, making it ideal for build pipelines.

### Recommended Multi-Arch Workflow

```
Build per-arch images → Push individual tags → manifest-tool push from-spec → Verify with regctl inspect
```

## Why Self-Host Manifest Management Tools?

Running manifest tools on your own infrastructure ensures full control over image transfer pipelines, avoids rate limits on public registries, and keeps internal image metadata within your network. For organizations with private registries and air-gapped environments, self-hosted manifest tools are essential for multi-architecture image distribution.

For container image optimization strategies, our [image optimization guide](../2026-04-28-dive-vs-slimtoolkit-vs-hadolint-container-image-optimization-guide-2026/) covers reducing image size before manifest creation. Teams managing container supply chains should also review our [container image inspection comparison](../2026-05-25-self-hosted-container-image-inspection-dive-vs-skopeo-vs-crane-guide/) for verifying image contents after manifest operations.

## FAQ

### What is the difference between a Docker manifest list and an OCI image index?

They serve the same purpose — mapping a single image tag to multiple platform-specific manifests — but use different JSON schemas. Docker manifest lists use `application/vnd.docker.distribution.manifest.list.v2+json`, while OCI image indexes use `application/vnd.oci.image.index.v1+json`. Most modern tools support both formats.

### Can crane create multi-architecture manifest lists?

crane does not have native manifest list creation capabilities. It can inspect existing manifests and copy images, but for creating manifest lists, use regctl (`regctl image create`) or manifest-tool (`manifest-tool push from-spec`).

### How do I authenticate manifest tools with private registries?

All three tools support Docker's standard authentication via `~/.docker/config.json`. Additionally, regctl supports environment variables (`REGCTL_USER`, `REGCTL_PASS`) and direct credential flags. For CI environments, mounting the Docker config as a volume is the most reliable approach.

### Is manifest-tool still maintained?

manifest-tool is maintained by Phil Estes, a Docker/Moby maintainer. While it receives fewer updates than regctl or crane, it is stable and focused — the tool's narrow scope means it doesn't need frequent feature additions. For active development on new OCI features, regctl is the more current choice.

### How do I verify a multi-arch image was created correctly?

Use `regctl image manifest` or `manifest-tool inspect` to view the manifest list contents. You should see entries for each platform (linux/amd64, linux/arm64, etc.) with correct digests. Then test by pulling the image on different architectures to confirm resolution works.

### Can these tools work with Harbor, Zot, or Distribution registries?

Yes — all three tools communicate via the standard OCI Distribution API, which is implemented by Harbor, Zot, Distribution (Docker Registry), and most other OCI-compliant registries. Authentication may require additional configuration for Harbor's RBAC system.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Manifest Tools: regctl vs crane vs manifest-tool",
  "description": "Compare regctl, crane, and manifest-tool for OCI container image manifest management — multi-arch builds, registry copy, manifest inspection, and tag operations.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
