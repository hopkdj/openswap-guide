---
title: "Dive vs SlimToolkit vs Hadolint: Container Image Optimization Guide 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "docker", "containers", "optimization"]
draft: false
description: "Compare Dive, SlimToolkit, and Hadolint for self-hosted container image optimization. Learn how to analyze layers, reduce image size by up to 30x, and write efficient Dockerfiles."
---

Every Docker image you build carries hidden costs. Bloated layers slow down CI/CD pipelines, waste registry storage, increase attack surfaces, and bloat deployment times. For teams running hundreds of microservices, a poorly optimized image can add gigabytes of unnecessary data to every deployment.

This guide compares three essential self-hosted tools that address container image optimization from different angles: [Dive](https://github.com/wagoodman/dive) for layer-by-layer analysis, [SlimToolkit](https://github.com/slimtoolkit/slim) for automated image minification, and [Hadolint](https://github.com/hadolint/hadolint) for Dockerfile best practices. Together, they form a complete optimization pipeline you can run entirely on your own infrastructure.

## Why Optimize Container Images

Before diving into the tools, it's worth understanding what's at stake. An unoptimized Docker image typically suffers from several problems:

- **Excessive size**: Development dependencies, build artifacts, and cached package manager files inflate images to 2-5 GB when 200 MB would suffice
- **Security vulnerabilities**: Every binary in your image is a potential attack vector. Minimizing the image surface reduces exploitable code
- **Slow deployments**: Larger images mean longer pull times, slower rollouts, and higher bandwidth costs
- **CI/CD bottlenecks**: Image build and push times directly impact developer feedback loops
- **Registry storage costs**: Storing dozens of large image tags adds up, especially with private registries

The goal isn't just to make images smaller — it's to make them faster to build, safer to run, and cheaper to store.

## Dive: Container Image Layer Analysis

**GitHub**: [wagoodman/dive](https://github.com/wagoodman/dive) · 53,845 stars · Updated December 2025

Dive is a command-line tool for exploring each layer in a Docker image. It provides an interactive TUI (terminal user interface) that lets you inspect what's happening at every step of your Dockerfile, identify wasted space, and understand layer efficiency.

### What Dive Does

Dive mounts the container image filesystem and lets you navigate layers visually. For each layer, you can see:

- Files added, modified, or deleted
- Size contribution of each layer
- Files that are duplicated across layers (indicating wasted space)
- Layer efficiency score based on content changes

This makes it an indispensable **diagnostic** tool — it doesn't modify images, but it tells you exactly where the bloat is hiding.

### Installing Dive

```bash
# Using Go
go install github.com/wagoodman/dive@latest

# Using Homebrew (macOS/Linux)
brew install dive

# Using Debian/Ubuntu
wget https://github.com/wagoodman/dive/releases/download/v0.12.0/dive_0.12.0_linux_amd64.deb
sudo dpkg -i dive_0.12.0_linux_amd64.deb
```

### Running Dive with Docker

```bash
# Analyze an image directly from a registry
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest \
  nginx:latest

# Analyze a locally built image
docker build -t myapp:latest .
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest myapp:latest
```

### Dive Configuration

Create `~/.dive.yaml` to set efficiency thresholds:

```yaml
# Dive configuration file
log-level: info
layer-change:
  show-aggregated-changes: true
efficiency:
  threshold: 90
  mismatch-severity: warning
low-efficiency-severity: critical
```

### Interpreting Dive Results

Dive provides two key metrics:

- **Image Efficiency Score**: Percentage of image bytes that aren't duplicated in later layers. A score above 90% is generally good.
- **Wasted Bytes**: Total bytes of files that were added in one layer but modified or deleted in a later layer. This directly indicates opportunities for Dockerfile improvement.

## SlimToolkit: Automated Image Minification

**GitHub**: [slimtoolkit/slim](https://github.com/slimtoolkit/slim) · 23,167 stars · Updated April 2026

SlimToolkit (formerly DockerSlim) is a powerful tool that automatically analyzes and optimizes Docker images. Unlike Dive, which diagnoses problems, SlimToolkit actively **fixes** them by creating minimal, secure versions of your images — sometimes reducing size by 30x or more.

### How SlimToolkit Works

SlimToolkit uses dynamic analysis to determine exactly which files your application needs at runtime:

1. It runs your container and monitors all file system access
2. It identifies the minimal set of binaries, libraries, and data files actually used
3. It creates a new image containing only those files
4. The resulting image is dramatically smaller while preserving full functionality

### Installing SlimToolkit

```bash
# Using the install script
curl -sL https://raw.githubusercontent.com/slimtoolkit/slim/master/scripts/install-slim.sh | bash

# Using Go
go install github.com/slimtoolkit/slim@latest

# Using Homebrew
brew install slimtoolkit/tap/slim
```

### Using SlimToolkit with Docker

```bash
# Basic optimization
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  slimtoolkit/slim:latest \
  build myapp:latest

# Optimization with HTTP probing (for web services)
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  slimtoolkit/slim:latest \
  build --http-probe myapp:latest

# Optimization with custom probe commands
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  slimtoolkit/slim:latest \
  build --exec "curl -s http://localhost:8080/health" myapp:latest
```

### Advanced SlimToolkit Configuration

For complex applications, use a configuration file:

```yaml
# slim.yaml
http-probe:
  cmd: "start"
  start-cmd: "curl -s http://localhost:3000/health || exit 1"
  ports:
    - port: 3000
      protocol: tcp
  continue-after: 5s

keep-perms:
  paths:
    - "/app/data"
    - "/app/config"
```

```bash
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/slim.yaml:/etc/slim.yml \
  slimtoolkit/slim:latest \
  build --config-path /etc/slim.yml myapp:latest
```

### Real-World Size Reductions

| Base Image | Original Size | After SlimToolkit | Reduction |
|---|---|---|---|
| node:18 (full) | ~1.0 GB | ~45 MB | 22x |
| python:3.11 | ~900 MB | ~80 MB | 11x |
| golang:1.21 | ~800 MB | ~25 MB | 32x |
| ubuntu:22.04 + Nginx | ~200 MB | ~8 MB | 25x |

These are typical results for compiled languages and minimal services. Interpreted languages like Python see less dramatic reductions because the runtime itself is substantial.

## Hadolint: Dockerfile Linting and Best Practices

**GitHub**: [hadolint/hadolint](https://github.com/hadolint/hadolint) · 12,086 stars · Updated April 2026

Hadolint is a Dockerfile linter that validates your Dockerfiles against best practices. It catches common mistakes, security issues, and anti-patterns before they become bloated or vulnerable images. While Dive and SlimToolkit work on built images, Hadolint works on the **source** — your Dockerfile.

### What Hadolint Checks

Hadolint enforces dozens of rules including:

- **DL3006**: Always tag images in `FROM` instructions
- **DL3008**: Pin versions in `apt-get install`
- **DL3013**: Pin versions in `pip install`
- **DL3018**: Pin versions in `apk add`
- **DL3025**: Use absolute paths for `WORKDIR`
- **DL4006**: Set the `SHELL` option for pipefail
- **SC2086**: Quote variables in shell commands

Many of these rules directly impact image size. For example, not pinning package versions means your build pulls the latest (potentially larger) packages each time. Not cleaning up package manager caches leaves temporary files in the final image.

### Installing Hadolint

```bash
# Using Homebrew
brew install hadolint

# Using Docker (no installation needed)
alias hadolint='docker run --rm -i hadolint/hadolint hadolint -'

# Using Go
go install github.com/hadolint/hadolint/v2/cmd/hadolint@latest
```

### Running Hadolint

```bash
# Lint a Dockerfile
hadolint Dockerfile

# Lint with custom configuration
hadolint --config .hadolint.yaml Dockerfile

# Lint a Dockerfile from stdin
cat Dockerfile | hadolint -

# JSON output for CI/CD integration
hadolint --format json Dockerfile
```

### Hadolint Configuration

Create `.hadolint.yaml` in your project root:

```yaml
# .hadolint.yaml
ignored:
  - DL3008
  - DL3013

trustedRegistries:
  - docker.io
  - ghcr.io
  - gcr.io
```

## Comparison Table

| Feature | Dive | SlimToolkit | Hadolint |
|---|---|---|---|
| **Primary Purpose** | Layer analysis | Image minification | Dockerfile linting |
| **Input** | Built image | Built image | Dockerfile source |
| **Output** | Analysis report | Optimized image | Lint report |
| **Modifies Images** | No | Yes | No |
| **Docker Socket Required** | Yes | Yes | No |
| **CI/CD Integration** | Yes (exit codes) | Yes (exit codes) | Yes (exit codes, SARIF) |
| **Languages** | Go | Go | Haskell |
| **Stars (GitHub)** | 53,845 | 23,167 | 12,086 |
| **Last Updated** | Dec 2025 | Apr 2026 | Apr 2026 |
| **Docker Image Available** | Yes | Yes | Yes |
| **License** | Apache 2.0 | Apache 2.0 | BSD-3-Clause |

## Building an Optimization Pipeline

The three tools work best together in sequence. Here's a complete CI/CD pipeline that integrates all three:

### Step 1: Lint the Dockerfile (Hadolint)

```bash
#!/bin/bash
# 1. Validate Dockerfile before building
echo "=== Step 1: Linting Dockerfile ==="
docker run --rm -i hadolint/hadolint hadolint - < Dockerfile
if [ $? -ne 0 ]; then
  echo "Hadolint found issues. Fix before proceeding."
  exit 1
fi
```

### Step 2: Build the Image

```bash
# 2. Build the original image
echo "=== Step 2: Building image ==="
docker build -t myapp:original .

# Check original size
docker images myapp:original --format "{{.Size}}"
```

### Step 3: Analyze the Layers (Dive)

```bash
# 3. Analyze layer efficiency
echo "=== Step 3: Analyzing layers ==="
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest \
  --ci myapp:original
```

### Step 4: Optimize the Image (SlimToolkit)

```bash
# 4. Create optimized image
echo "=== Step 4: Optimizing ==="
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  slimtoolkit/slim:latest \
  build --http-probe-cmd 'curl -s http://localhost:8080/health' \
  --target myapp:original \
  --tag myapp:optimized
```

### Step 5: Compare Results

```bash
# 5. Compare sizes
echo "=== Step 5: Results ==="
echo "Original: $(docker images myapp:original --format '{{.Size}}')"
echo "Optimized: $(docker images myapp:optimized --format '{{.Size}}')"

# 6. Analyze the optimized image
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest \
  --ci myapp:optimized
```

### Full Docker Compose for Local Optimization Lab

Set up a local optimization environment with all three tools:

```yaml
version: "3.8"

services:
  hadolint:
    image: hadolint/hadolint:latest-debian
    command: hadolint Dockerfile
    volumes:
      - ./Dockerfile:/Dockerfile:ro

  dive:
    image: wagoodman/dive:latest
    command: dive --ci myapp:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  slimtoolkit:
    image: slimtoolkit/slim:latest
    command: slim build myapp:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  registry:
    image: registry:2
    ports:
      - "5000:5000"
    volumes:
      - registry-data:/var/lib/registry

volumes:
  registry-data:
```

## Best Practices for Container Image Optimization

### Use Multi-Stage Builds

Combine multi-stage builds with these tools for maximum effect:

```dockerfile
# Stage 1: Build
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /myapp

# Stage 2: Runtime
FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /myapp .
EXPOSE 8080
CMD ["./myapp"]
```

### Clean Up Package Caches

Always remove package manager caches in the same `RUN` layer:

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx && \
    rm -rf /var/lib/apt/lists/*
```

### Use Distroless or Alpine Base Images

For Go and Rust binaries, consider distroless images:

```dockerfile
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/myapp /myapp
ENTRYPOINT ["/myapp"]
```

### Set a CI Efficiency Threshold

Use Dive's CI mode to enforce quality gates:

```yaml
# .dive.yaml for CI
layer-change:
  show-aggregated-changes: true
efficiency:
  threshold: 90
  mismatch-severity: warning
low-efficiency-severity: critical
```

```bash
# Fail CI if efficiency is below threshold
dive --ci myapp:latest
```

## When to Use Each Tool

| Scenario | Best Tool |
|---|---|
| Understanding why an image is large | Dive |
| Reducing image size automatically | SlimToolkit |
| Catching Dockerfile anti-patterns early | Hadolint |
| CI/CD quality gate for image builds | Dive + Hadolint |
| Pre-production image hardening | SlimToolkit |
| Investigating layer duplication | Dive |
| Dockerfile code review | Hadolint |
| Complete optimization workflow | All three |

For production deployments, we recommend running all three tools in sequence: Hadolint catches source-level issues during development, Dive identifies layer-level waste after building, and SlimToolkit produces the final optimized image for deployment.

For related reading, see our [container security hardening guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/) for securing your optimized images, the [container build tools comparison](../buildah-vs-kaniko-vs-earthly-self-hosted-container-build-tools-guide-2026/) for rootless image building in CI/CD, and the [container registry guide](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/) for storing optimized images efficiently.

## FAQ

### What is the best tool for reducing Docker image size?

SlimToolkit (formerly DockerSlim) is the most effective tool for automated image size reduction. It uses dynamic analysis to identify only the files your application actually needs at runtime, often achieving 10-30x size reductions. For compiled languages like Go and Rust, reductions of 30x are common.

### Does SlimToolkit break my container's functionality?

SlimToolkit is designed to preserve full functionality. It monitors your application during a probe phase (default 5 seconds) to catalog all file access patterns. The optimized image includes everything your app touched during probing. For complex applications, you can extend the probe duration or specify custom commands to ensure all code paths are exercised.

### Can I use these tools in CI/CD pipelines?

Yes, all three tools support CI/CD integration. Hadolint can output in JSON, JUnit, or SARIF formats for CI integration. Dive has a `--ci` flag that exits with non-zero status if efficiency thresholds aren't met. SlimToolkit can be run as a build step with `--tag` to produce optimized images ready for pushing to your registry.

### Is Dive only useful for debugging large images?

While Dive excels at identifying wasted space in large images, it's equally valuable for understanding layer caching behavior. By analyzing which layers change most frequently between builds, you can reorganize your Dockerfile to maximize Docker's build cache effectiveness — speeding up rebuilds even for small images.

### Does Hadolint catch security issues in Dockerfiles?

Yes. Hadolint includes rules that catch security-relevant patterns like running containers as root (DL3002), using ADD instead of COPY (DL3010, which can extract untrusted tarballs), and not pinning package versions (DL3008, DL3013). While it's not a full security scanner, it catches many common Dockerfile security mistakes.

### How do I combine multi-stage builds with SlimToolkit?

SlimToolkit works best on the final stage image. Build your multi-stage Dockerfile normally, then run SlimToolkit on the resulting image. The multi-stage build already removes build-time dependencies, and SlimToolkit further removes unused runtime files. The combination typically produces the smallest possible image.

### What Dockerfile rules should I never ignore in Hadolint?

Never ignore DL3006 (always tag FROM images), DL3008/DL3013/DL3018 (pin package versions), and DL3025 (use absolute WORKDIR paths). Pinning versions ensures reproducible builds, while absolute WORKDIR paths prevent subtle path resolution issues across different Docker versions.

### Can SlimToolkit optimize images for multiple architectures?

SlimToolkit operates on the architecture of the host where it runs. For multi-arch images, run SlimToolkit separately on each target architecture (e.g., amd64 and arm64) and then use `docker manifest create` to combine the optimized images into a multi-arch manifest.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dive vs SlimToolkit vs Hadolint: Container Image Optimization Guide 2026",
  "description": "Compare Dive, SlimToolkit, and Hadolint for self-hosted container image optimization. Learn how to analyze layers, reduce image size by up to 30x, and write efficient Dockerfiles.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
