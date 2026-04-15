---
title: "Buildah vs Kaniko vs Earthly: Self-Hosted Container Build Tools Guide 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "containers", "docker", "devops"]
draft: false
description: "Comprehensive comparison of Buildah, Kaniko, and Earthly for self-hosted container image building. Learn which tool fits your CI/CD pipeline, security requirements, and workflow."
---

Building container images has become a daily task for developers, DevOps engineers, and platform teams. While `docker build` is the most well-known approach, it requires a running Docker daemon and root-level privileges — both of which create security and architectural concerns in production CI/CD environments.

Enter a new generation of self-hosted container build tools that eliminate the daemon dependency, improve reproducibility, and integrate seamlessly into automated pipelines. In this guide, we'll compare three leading options: **Buildah**, **Kaniko**, and **Earthly** — examining their architectures, features, installation processes, and ideal use cases.

## Why Self-Host Your Container Build Pipeline?

Running container builds on your own infrastructure offers several advantages over managed or SaaS build services:

- **Security and Compliance**: Build artifacts never leave your network. For regulated industries (finance, healthcare, government), this is non-negotiable.
- **Cost Control**: SaaS build minutes add up quickly. A self-hosted build runner with caching costs a fraction of commercial alternatives.
- **No Daemon Dependency**: Traditional `docker build` requires the Docker daemon (root access, socket exposure). Modern tools use rootless builds or run containers-within-containers safely.
- **Full Pipeline Control**: Customize caching strategies, base image registries, build environments, and retention policies without vendor lock-in.
- **Air-Gapped Support**: Self-hosted tools work in offline environments where no internet access is available for pulling base images or pushing results.

Now let's examine each tool in depth.

## Buildah: The Daemonless Dockerfile Builder

Buildah is developed by Red Hat and forms the core of the Podman container ecosystem. It specializes in building OCI-compliant container images from Dockerfiles — without requiring a Docker daemon.

### Key Features

- **Daemonless architecture**: No background service required; each `buildah` invocation is independent
- **Rootless builds**: Full support for unprivileged users building images
- **Dockerfile compatibility**: Drop-in replacement for `docker build` in most cases
- **Multi-stage builds**: Full support for complex multi-stage Dockerfiles
- **Image manipulation**: Push, pull, mount, unmount, and modify images directly from the command line
- **OCI compliance**: Produces standard OCI images compatible with any runtime

### Installation

**Fedora / RHEL / CentOS:**

```bash
sudo dnf install -y buildah
```

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install -y buildah
```

**macOS (via Homebrew):**

```bash
brew install buildah
```

**From Source:**

```bash
git clone https://github.com/containers/buildah
cd buildah
make
sudo make install
```

### Building Your First Image

```bash
# Build from a Dockerfile (same syntax as docker build)
buildah build -t myapp:latest .

# Build with a specific containerfile
buildah build -f Containerfile.production -t myapp:prod .

# Build with build arguments
buildah build --build-arg NODE_ENV=production -t myapp:latest .
```

### Advanced: Scripting Image Creation

Buildah's unique strength is its ability to build images using shell scripts instead of Dockerfiles:

```bash
#!/bin/bash
container=$(buildah from ubuntu:24.04)

# Install packages
buildah run $container -- apt-get update
buildah run $container -- apt-get install -y nginx curl

# Copy application files
buildah copy $container ./app /var/www/html
buildah copy $container ./nginx.conf /etc/nginx/nginx.conf

# Set metadata
buildah config --port 80 $container
buildah config --entrypoint '["nginx", "-g", "daemon off;"]' $container
buildah config --label "maintainer=team@example.com" $container

# Commit the image
buildah commit $container myapp:custom-build
```

This scripting approach gives you full programmatic control — conditionals, loops, and external tool integration work naturally.

### Performance and Caching

Buildah uses the `containers/storage` backend with layer-level caching. Subsequent builds skip unchanged layers automatically:

```bash
# Configure storage location
export STORAGE_DRIVER=vfs
buildah build -t myapp:cached .

# Use overlayfs for better performance (recommended on Linux)
buildah --storage-driver overlay build -t myapp:fast .
```

---

## Kaniko: Build Images in Kubernetes, No Daemon Required

Kaniko, developed by Google, is designed specifically for building container images inside Kubernetes clusters — or any environment where running a Docker daemon is impractical or forbidden.

### Key Features

- **No Docker daemon**: Runs entirely in userspace; extracts the base filesystem and executes Dockerfile commands as a series of snapshots
- **Kubernetes-native**: Designed to run as a Kubernetes Job or Pod
- **Registry-agnostic**: Pushes to any OCI-compliant registry (Docker Hub, Harbor, ECR, GCR, GHCR)
- **Snapshot-based layering**: After each Dockerfile command, Kaniko snapshots the filesystem changes and creates a new layer
- **Warmer cache**: Pre-downloads base images to speed up builds in cluster environments
- **Security isolation**: Each build runs in its own Pod with configurable resource limits and network policies

### Installation

Kaniko doesn't require installation in the traditional sense — you run it as a container image. Here's how to use it in different contexts.

#### As a Kubernetes Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kaniko-build
spec:
  template:
    spec:
      containers:
      - name: kaniko
        image: gcr.io/kaniko-project/executor:latest
        args:
          - "--dockerfile=Dockerfile"
          - "--context=git://github.com/myorg/myapp.git#main"
          - "--destination=registry.example.com/myapp:latest"
          - "--cache=true"
          - "--cache-repo=registry.example.com/myapp/cache"
          - "--compressed-caching=false"
        volumeMounts:
          - name: kaniko-secret
            mountPath: /secret
        env:
          - name: GOOGLE_APPLICATION_CREDENTIALS
            value: /secret/kaniko-creds.json
      restartPolicy: Never
      volumes:
        - name: kaniko-secret
          secret:
            secretName: regcred
```

#### With Docker (for testing)

```bash
docker run -it \
  -v "$HOME/.docker/config.json":/kaniko/.docker/config.json \
  -v "$(pwd)":/workspace \
  gcr.io/kaniko-project/executor:latest \
  --dockerfile /workspace/Dockerfile \
  --destination myregistry.com/myapp:latest \
  --context dir:///workspace/ \
  --cache=true
```

#### Local Binary (Standalone)

```bash
# Download the latest release
wget https://github.com/GoogleContainerTools/kaniko/releases/latest/download/executor-linux-amd64
chmod +x executor-linux-amd64
sudo mv executor-linux-amd64 /usr/local/bin/kaniko

# Build an image
kaniko \
  --context /path/to/build/context \
  --dockerfile /path/to/Dockerfile \
  --destination registry.example.com/myapp:latest
```

### Build Contexts

Kaniko supports multiple context sources:

```bash
# Local directory
kaniko --context dir:///workspace --dockerfile Dockerfile

# Git repository
kaniko --context git://github.com/user/repo.git#refs/heads/main --dockerfile Dockerfile

# GCS bucket
kaniko --context gs://my-bucket/build-context --dockerfile Dockerfile

# S3 bucket
kaniko --context s3://my-bucket/build-context --dockerfile Dockerfile

# Azure Blob Storage
kaniko --context https://myaccount.blob.core.windows.net/container/build-context --dockerfile Dockerfile
```

### Performance Tuning

```bash
# Enable snapshot mode for faster builds
kaniko --snapshot-mode=redo \
  --context dir:///workspace \
  --destination registry.example.com/myapp:latest

# Use cache to speed up repeated builds
kaniko --cache=true \
  --cache-repo registry.example.com/cache \
  --compressed-caching=false \
  --context dir:///workspace \
  --destination registry.example.com/myapp:latest

# Run with multiple layers in parallel
kaniko --single-snapshot=false \
  --context dir:///workspace \
  --destination registry.example.com/myapp:latest
```

---

## Earthly: Reproducible Builds with Buildkit and Makefile-Like Syntax

Earthly takes a fundamentally different approach. Instead of simply building Dockerfiles, it provides a build automation system with its own syntax (`Earthfile`) inspired by Makefiles and Dockerfiles. It runs on top of BuildKit and is designed for reproducible, CI-friendly builds.

### Key Features

- **Earthfile syntax**: Combines the best of Makefiles and Dockerfiles — targets, dependencies, and artifact passing
- **Reproducible builds**: Same build, same result, every time — across machines and CI systems
- **CI/CD integration**: First-class support for GitHub Actions, GitLab CI, Jenkins, CircleCI, and more
- **Satellite builds (optional)**: Optional managed build runners for speed; self-hosted mode uses local BuildKit
- **Artifact sharing**: Easily pass build outputs between targets and save them to local files
- **Multi-platform builds**: Build for linux/amd64, linux/arm64, and other architectures simultaneously
- **Secret management**: Built-in SSH and secret passing without baking credentials into images

### Installation

**Linux (one-liner):**

```bash
sudo /bin/sh -c 'wget https://github.com/earthly/earthly/releases/latest/download/earthly-linux-amd64 -O /usr/local/bin/earthly && chmod +x /usr/local/bin/earthly && earthly bootstrap'
```

**macOS:**

```bash
brew install earthly
earthly bootstrap
```

**From Source:**

```bash
git clone https://github.com/earthly/earthly.git
cd earthly
go build -o earthly ./cmd/earthly
sudo mv earthly /usr/local/bin/
earthly bootstrap
```

### Writing Your First Earthfile

Create a file named `Earthfile` in your project root:

```dockerfile
VERSION 0.8
FROM golang:1.23-alpine3.20

WORKDIR /go/src/myapp

build:
    COPY go.mod go.sum ./
    RUN go mod download
    COPY . .
    RUN CGO_ENABLED=0 go build -o /bin/myapp ./cmd/server
    SAVE IMAGE --push myapp:latest

test:
    FROM +build
    RUN go test -v ./...

docker:
    FROM +build
    SAVE IMAGE --push registry.example.com/myapp:$VERSION
```

### Running Builds

```bash
# Build the default target
earthly +build

# Run tests
earthly +test

# Build and push with a version argument
earthly --push --arg VERSION=v2.1.0 +docker

# Build for multiple platforms
earthly --platform linux/amd64,linux/arm64 +docker

# Use CI mode (stricter caching, no local state)
earthly --ci +build
```

### Multi-Target Dependencies

Earthfile targets can depend on each other, creating a build graph:

```dockerfile
VERSION 0.8

deps:
    COPY package.json package-lock.json ./
    RUN npm ci
    SAVE ARTIFACT node_modules /node_modules AS LOCAL node_modules

lint:
    FROM node:20-alpine
    COPY --from+deps /node_modules ./node_modules
    COPY . .
    RUN npm run lint

build:
    FROM node:20-alpine
    COPY --from+deps /node_modules ./node_modules
    COPY . .
    RUN npm run build
    SAVE ARTIFACT dist /dist AS LOCAL dist

image:
    FROM node:20-alpine
    COPY --from+build /dist ./dist
    RUN npm ci --omit=dev
    CMD ["node", "dist/index.js"]
    SAVE IMAGE --push registry.example.com/webapp:latest
```

```bash
# Run the full pipeline — dependencies resolve automatically
earthly +image

# Just lint (lint will pull deps automatically)
earthly +lint
```

---

## Head-to-Head Comparison

| Feature | Buildah | Kaniko | Earthly |
|---|---|---|---|
| **Developer** | Red Hat | Google | Earthly Technologies |
| **Daemon Required** | No | No | No (uses BuildKit) |
| **Dockerfile Support** | Full | Full | Via `IMPORT` directive |
| **Own Build Syntax** | No (scripts or Dockerfile) | No (Dockerfile only) | Yes (Earthfile) |
| **Rootless Builds** | Yes | Yes | Yes |
| **Kubernetes Native** | No | Yes | Partial |
| **CI/CD Integration** | CLI-based | Job/Pod-based | First-class |
| **Caching** | Layer-level (containers/storage) | Snapshot-level (registry cache) | BuildKit cache + remote |
| **Multi-Platform** | Limited | No | Yes (buildx-compatible) |
| **Artifact Sharing** | Manual | No | Built-in (SAVE ARTIFACT) |
| **Secret Management** | Mount-based | Volume-based | Built-in (--secret flag) |
| **Language** | Go | Go | Go |
| **License** | Apache 2.0 | Apache 2.0 | Mozilla Public License 2.0 |
| **GitHub Stars** | ~8.6K | ~10.8K | ~14K+ |
| **Registry Push** | Yes | Yes | Yes |
| **Air-Gapped Builds** | Yes | Yes | Yes (with local cache) |

---

## Choosing the Right Tool

### Choose Buildah when:

- You want a **drop-in replacement for `docker build`** with minimal learning curve
- Your team works in a **Red Hat / Podman ecosystem**
- You need **scriptable image creation** using shell commands instead of Dockerfiles
- You want **rootless builds on a single host** without Kubernetes
- You need to **modify existing images** (mount, inspect, re-tag) without rebuilding from scratch

**Typical deployment**: Install on developer laptops and CI runners alongside Podman. Use Buildah in CI scripts as a direct substitute for `docker build`.

### Choose Kaniko when:

- You're building **inside Kubernetes clusters** (GitLab runners, Tekton pipelines, Argo Workflows)
- You **cannot run a Docker daemon** for security or policy reasons
- You need **cloud-storage context sources** (GCS, S3, Azure Blob)
- You want **per-Pod build isolation** with resource limits and network policies
- Your CI system is Kubernetes-native (no VM-based runners available)

**Typical deployment**: Deploy as a Kubernetes Job triggered by webhooks or CI pipeline steps. Each build runs in an isolated Pod with its own resource quota.

### Choose Earthly when:

- You need **complex, multi-stage builds** with dependencies between targets
- **Reproducibility** across developer machines and CI systems is critical
- You want **Makefile-like build orchestration** with Docker-compatible execution
- You build for **multiple architectures** (amd64, arm64) from a single command
- Your build process involves **compiling, testing, linting, and packaging** in a unified pipeline
- You need **artifact passing** between build stages without manual file copying

**Typical deployment**: Install `earthly` binary on CI runners. Commit `Earthfile` to the repository. Trigger builds via CI pipelines with `earthly --ci +target`.

---

## Production CI/CD Integration Examples

### GitHub Actions with Buildah

```yaml
name: Build with Buildah
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Buildah
        run: |
          sudo apt update
          sudo apt install -y buildah
      - name: Build image
        run: |
          buildah build --format docker -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
      - name: Push to GHCR
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | \
            buildah login --username "${{ github.actor }}" --password-stdin ghcr.io
          buildah push ghcr.io/${{ github.repository }}:${{ github.sha }}
```

### GitLab CI with Kaniko

```yaml
build:
  image:
    name: gcr.io/kaniko-project/executor:debug
    entrypoint: [""]
  script:
    - |
      /kaniko/executor \
        --context "${CI_PROJECT_DIR}" \
        --dockerfile "${CI_PROJECT_DIR}/Dockerfile" \
        --destination "${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHORT_SHA}" \
        --cache=true \
        --cache-repo "${CI_REGISTRY_IMAGE}/cache"
  rules:
    - when: always
```

### Jenkins with Earthly

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'earthly --ci --push +docker'
            }
        }
        stage('Test') {
            steps {
                sh 'earthly --ci +test'
            }
        }
    }
}
```

---

## Security Considerations

All three tools improve security over traditional `docker build` in different ways:

| Concern | Buildah | Kaniko | Earthly |
|---|---|---|---|
| Root daemon exposure | Eliminated | Eliminated | Eliminated |
| Socket mount required | No | No | No |
| Namespace isolation | Yes (Podman namespaces) | Yes (Pod isolation) | Yes (BuildKit sandboxes) |
| Build context tampering | Filesystem ACLs | Pod security policies | Read-only source mount |
| Credential leakage | BuildKit secret mount | Volume mount (scoped) | Built-in --secret |
| Supply chain attestations | Via cosign/sigstore | Via cosign/sigstore | Built-in provenance |

For maximum security, combine any of these tools with image signing (cosign), SBOM generation (syft), and vulnerability scanning (Trivy) in your pipeline.

---

## Final Verdict

Each tool excels in its own domain:

- **Buildah** is the pragmatic choice for teams already using Podman or who want a daemonless `docker build` replacement. Its scripting capabilities make it uniquely flexible for non-standard build workflows.

- **Kaniko** is the Kubernetes specialist. If your CI runs inside a cluster and you can't run Docker, Kaniko is purpose-built for exactly this scenario. Its snapshot-based approach is reliable and well-tested at Google-scale.

- **Earthly** is the build orchestration powerhouse. When your builds involve compilation, testing, linting, multi-platform targets, and artifact sharing, Earthfile's dependency graph and reproducible execution save hours of debugging broken CI pipelines.

The best approach for many organizations is not picking one but **combining them**: use Buildah on developer workstations, Kaniko for Kubernetes-native CI, and Earthly for complex multi-service builds. All three produce OCI-compliant images, so the outputs are interchangeable regardless of which tool created them.
