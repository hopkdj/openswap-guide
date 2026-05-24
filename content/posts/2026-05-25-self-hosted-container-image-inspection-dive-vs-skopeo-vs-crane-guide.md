---
title: "Self-Hosted Container Image Inspection Tools: Dive vs Skopeo vs crane"
date: "2026-05-25"
tags: ["docker", "container-infrastructure", "image-management", "container-registry"]
draft: false
---

Container images are the fundamental building blocks of self-hosted infrastructure. Every Dockerfile produces an image composed of layered filesystems, metadata, and configuration. As teams build and maintain dozens or hundreds of container images, questions arise: How large is this image? Which layers consume the most space? Does this image contain the expected base layer? Can we verify the image signature before deploying it to production?

Three specialized tools address these questions from different angles: **Dive** for layer-by-layer exploration and size optimization, **Skopeo** for remote image inspection without pulling, and **crane** (go-containerregistry) for programmatic registry operations. Unlike vulnerability scanners that analyze image contents for security issues, these tools focus on image structure, provenance, and registry management.

This guide compares Dive, Skopeo, and crane across their capabilities, workflows, and integration patterns — helping you build a comprehensive container image inspection pipeline for your self-hosted environment.

## Overview of Container Image Inspection Tools

### Dive — Layer Explorer and Optimizer

**Dive** is an interactive tool that explores each layer of a Docker image, showing exactly what files were added, modified, or removed at each step. It identifies wasted space (files duplicated across layers), calculates an efficiency score, and provides a terminal-based UI for navigating the layer filesystem. Dive is primarily used during image development to optimize Dockerfiles and reduce image sizes.

| Attribute | Value |
|-----------|-------|
| GitHub | [wagoodman/dive](https://github.com/wagoodman/dive) |
| Stars | 53,000+ |
| License | MIT |
| Primary use | Image layer exploration, size optimization |
| Interface | Terminal UI (TUI) |
| Requires Docker daemon | No (can analyze local tarballs) |

### Skopeo — Remote Inspection and Copying

**Skopeo** inspects container images on remote registries without downloading them. It can display image metadata, layer digests, operating system information, and architecture compatibility. Beyond inspection, Skopeo copies images between registries, signs and verifies image content, and converts between image formats (Docker, OCI). It is the Swiss Army knife for image management operations.

| Attribute | Value |
|-----------|-------|
| GitHub | [containers/skopeo](https://github.com/containers/skopeo) |
| Stars | 10,800+ |
| License | Apache 2.0 |
| Primary use | Remote inspection, image copying, signature verification |
| Interface | CLI |
| Requires Docker daemon | No |

### crane — Registry Operations Library and CLI

**crane** (part of the go-containerregistry project by Google) provides both a Go library and a CLI for interacting with container registries. It supports pulling, pushing, copying, tagging, and cataloging images. crane is designed for programmatic access — CI/CD pipelines, registry synchronization tools, and custom image management scripts use it as a lightweight alternative to the Docker CLI for registry operations.

| Attribute | Value |
|-----------|-------|
| GitHub | [google/go-containerregistry](https://github.com/google/go-containerregistry) |
| Stars | 3,800+ |
| License | Apache 2.0 |
| Primary use | Registry operations, programmatic image management |
| Interface | CLI + Go library |
| Requires Docker daemon | No |

## Comparison Table

| Feature | Dive | Skopeo | crane |
|---------|------|--------|-------|
| **Layer inspection** | Full (interactive TUI) | Yes (layer list + digests) | No |
| **Wasted space detection** | Yes (efficiency score) | No | No |
| **Remote inspection** | No (requires local image) | Yes (registry-native) | Yes (registry-native) |
| **Image copying** | No | Yes (registry to registry) | Yes (registry to registry) |
| **Signature verification** | No | Yes (cosign, mechanical) | Yes (cosign, simple signing) |
| **Format conversion** | No | Yes (Docker <-> OCI) | Yes (Docker <-> OCI) |
| **Registry catalog** | No | Limited | Yes (full catalog) |
| **Image tagging** | No | No | Yes |
| **Manifest inspection** | Basic | Full (schema v1/v2, OCI) | Full (schema v1/v2, OCI) |
| **Go library API** | No | No | Yes (first-class) |
| **CI/CD integration** | Via CLI exit codes | Via CLI exit codes | Via CLI + Go library |
| **Multi-arch support** | Yes (select platform) | Yes (inspect all platforms) | Yes |
| **Private registry auth** | Yes (Docker config) | Yes (auth files) | Yes (keychain) |
| **Tarball analysis** | Yes | Yes | Yes |
| **Image diff** | No | Yes (compare two images) | No |

## Configuration and Usage Examples

### Dive — Analyzing Image Layers

Dive can analyze images from the Docker daemon or from saved tarballs:

```bash
# Analyze a local Docker image
dive nginx:alpine

# Analyze from a registry (pulls image first)
dive ghcr.io/nginx/nginx:alpine

# Analyze a saved tarball (no Docker daemon needed)
docker save nginx:alpine -o nginx.tar
dive nginx.tar

# CI mode: output efficiency metrics as JSON
dive nginx:alpine --json > dive-report.json
```

Dive TUI navigation:
- **Arrow keys**: Navigate layers
- **Tab**: Switch between layer files and image details
- **Ctrl+F**: Filter files
- **Space**: Toggle file visibility (added/removed/modified)
- **Ctrl+O**: Show/hide file details panel

Dive CI integration with efficiency thresholds:

```bash
# Fail CI if image efficiency is below 80%
dive nginx:alpine --ci --lowestEfficiency 0.80

# Output JSON report for dashboard integration
dive myapp:latest --ci --json > /tmp/dive-results.json
```

### Skopeo — Remote Inspection Without Pulling

Skopeo inspects images directly on registries, avoiding the bandwidth cost of downloading:

```bash
# Inspect image metadata without downloading
skopeo inspect docker://nginx:alpine

# Output as formatted JSON
skopeo inspect docker://nginx:alpine --format '{{.Architecture}} {{.Os}}'

# List all tags in a repository
skopeo list-tags docker://ghcr.io/nginx/nginx

# Compare two images to see differences
skopeo inspect docker://nginx:1.25-alpine --raw > img1.json
skopeo inspect docker://nginx:1.26-alpine --raw > img2.json
diff img1.json img2.json

# Copy image between registries
skopeo copy docker://nginx:alpine docker://myregistry.internal/nginx:alpine

# Sign an image with cosign
skopeo sign --sign-by mykey@myregistry.com docker://myregistry.internal/nginx:alpine
```

### crane — Programmatic Registry Operations

crane provides both CLI and Go library access:

```bash
# List all repositories in a registry
crane catalog registry.internal:5000

# Pull an image to a tarball (no Docker daemon)
crane pull registry.internal:5000/myapp:v1 myapp.tar

# Push an image from tarball
crane push myapp.tar registry.internal:5000/myapp:v2

# Tag an existing image
crane tag registry.internal:5000/myapp:v1 latest

# Get image digest
crane digest registry.internal:5000/myapp:v1

# Export filesystem to a tarball
crane export registry.internal:5000/myapp:v1 filesystem.tar
```

Go library usage for CI/CD integration:

```go
package main

import (
    "fmt"
    "github.com/google/go-containerregistry/pkg/crane"
)

func main() {
    // List tags
    tags, err := crane.ListTags("registry.internal:5000/myapp")
    if err != nil {
        panic(err)
    }
    fmt.Println("Tags:", tags)

    // Copy image
    err = crane.Copy("registry.internal:5000/myapp:v1",
        "registry.internal:5000/myapp:stable")
    if err != nil {
        panic(err)
    }
}
```

## Docker Compose Integration

These tools integrate into containerized CI/CD and image management pipelines:

```yaml
# Docker Compose: Image inspection pipeline
version: "3.8"
services:
  image-inspector:
    image: wagoodman/dive:latest
    container_name: dive-inspector
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./dive-config.yaml:/root/.dive.yaml
    command: >
      sh -c "
        dive --ci --json /reports/dive-report.json myapp:latest
      "
    restart: "no"

  registry-sync:
    image: ghcr.io/google/go-containerregistry/crane:latest
    container_name: crane-sync
    volumes:
      - ./auth:/root/.docker/config.json:ro
    command: >
      sh -c "
        crane copy registry.internal:5000/myapp:v1
        registry.backup.internal:5000/myapp:v1
      "
    restart: "no"

  skopeo-inspector:
    image: quay.io/skopeo/stable:latest
    container_name: skopeo-checker
    volumes:
      - ./inspect-results:/results
    command: >
      sh -c "
        skopeo inspect docker://registry.internal:5000/myapp:v1
        --format json > /results/inspect.json
      "
    restart: "no"
```

## When to Use Each Tool

### Use Dive When:
- Optimizing Dockerfile layer ordering to reduce image size
- Identifying wasted space from files added and then deleted in the same build stage
- Reviewing what each layer contributes to the final image
- Setting up CI quality gates for image efficiency scores
- Debugging unexpectedly large container images

### Use Skopeo When:
- Verifying image metadata before pulling (architecture, OS, labels)
- Copying images between registries without a Docker daemon
- Verifying image signatures for supply chain security
- Comparing images across different tags or registries
- Converting images between Docker and OCI formats

### Use crane When:
- Building custom registry synchronization tools
- Implementing automated image promotion pipelines (dev -> staging -> production)
- Programmatically listing repository catalogs and tag inventories
- Integrating registry operations into Go applications
- Performing bulk image operations (retagging, mirroring) in CI/CD

## Why Self-Host Image Inspection Infrastructure?

Self-hosted image inspection tools provide visibility into your container supply chain without depending on external SaaS scanning services. When building images for self-hosted applications, understanding image composition, layer efficiency, and registry state is critical for:

- **Cost optimization**: Smaller images mean faster deployments, less storage consumption, and reduced network bandwidth for registry replication. Dive's efficiency scoring identifies optimization opportunities that can reduce image sizes by 30-50%.

- **Supply chain integrity**: Skopeo's signature verification ensures that images deployed to production match exactly what was built and signed in CI. Without remote attestation, there is no guarantee that a pulled image is the one you built.

- **Registry governance**: crane enables automated inventory management — tracking which images exist, which tags are in use, and synchronizing registries across environments. This prevents registry sprawl and orphaned image accumulation.

For container registry management, see our [Distribution vs Harbor vs Zot guide](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/).
For container security hardening, check our [Docker Bench vs Trivy vs Checkov comparison](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide/).
For container build pipelines, our [Buildpacks vs Tilt vs Skaffold guide](../2026-04-28-buildpacks-vs-tilt-vs-skaffold-self-hosted-container-build-guide/) covers it.

## FAQ

### Can Dive analyze images without installing Docker?

Yes. Dive can analyze images from saved tarballs (`docker save` output) without a running Docker daemon. Run `docker save image:tag -o image.tar` on any machine with Docker, transfer the tarball to your analysis machine, and run `dive image.tar`. This is useful for CI environments where running a Docker daemon inside containers is impractical.

### Does Skopeo require credentials to inspect public registry images?

No. Skopeo can inspect public images on Docker Hub, GitHub Container Registry, and other public registries without authentication. For private registries, provide credentials via `--authfile`, `--src-creds`, or the standard Docker config file at `~/.docker/config.json`. Skopeo also supports credential helpers and Kubernetes service account tokens.

### Is crane a replacement for the Docker CLI?

No. crane focuses exclusively on registry operations — it does not build images, run containers, or manage Docker volumes. It is complementary to the Docker CLI, providing a lighter-weight option for registry-specific tasks (push, pull, copy, tag, catalog) without requiring the Docker daemon. For CI/CD pipelines that only need to move images between registries, crane is often faster and more resource-efficient than `docker push`/`docker pull`.

### How do I verify image signatures with Skopeo?

Skopeo supports two signature formats: mechanical signing (GPG-based) and cosign (Sigstore). For cosign verification:
```bash
skopeo copy --src-tls-verify=true --dest-tls-verify=true
docker://registry.example.com/myapp:v1
docker://registry.example.com/myapp:v1
```
For more comprehensive signature verification, combine Skopeo with the `cosign` CLI:
```bash
cosign verify --key cosign.pub registry.example.com/myapp:v1
```

### Can these tools work with air-gapped registries?

Yes. All three tools work with self-hosted registries (Harbor, Distribution, Zot) that are not connected to the public internet. Skopeo and crane support TLS verification bypass (`--tls-verify=false` for Skopeo, `crane --insecure` for crane) for registries with self-signed certificates. Dive works with any image accessible to the Docker daemon, regardless of registry connectivity.

### Which tool should I use for automated image size monitoring in CI?

Dive is the best fit. It provides a `--ci` mode that outputs JSON reports with efficiency scores, wasted bytes, and layer-by-layer breakdowns. You can set threshold-based exit codes (`--lowestEfficiency 0.80`) to fail builds that do not meet size targets. Skopeo and crane do not provide size analysis or efficiency scoring — they focus on metadata inspection and registry operations rather than image optimization.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Inspection Tools: Dive vs Skopeo vs crane",
  "description": "Compare Dive, Skopeo, and crane for container image inspection, layer analysis, and registry operations. Configuration examples and Docker Compose deployment guides.",
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
