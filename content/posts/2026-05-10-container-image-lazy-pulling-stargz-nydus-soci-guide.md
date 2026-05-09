---
title: "Self-Hosted Container Image Lazy Pulling: Stargz Snapshotter vs Nydus vs SOCI Snapshotter"
date: "2026-05-10"
tags: ["containers", "containerd", "lazy-pulling", "oci", "stargz", "nydus", "soci", "image-distribution"]
draft: false
---

Container image pulling is one of the most time-consuming steps in container deployment workflows. When a node needs to run a pod, it must first download the entire container image from a registry — every layer, every byte — before the container can start. For large images (multi-gigabyte database or ML images), this cold-start latency can range from tens of seconds to several minutes, severely impacting deployment velocity and autoscaling responsiveness.

Container image lazy pulling solves this problem by allowing containers to start **before** the full image is downloaded. Instead of pulling the entire image upfront, a lazy-pulling snapshotter fetches only the specific file chunks needed at startup time, streaming the rest in the background. This can reduce container start times by 90% or more.

In this guide, we compare the three leading open-source lazy-pulling solutions: **containerd's Stargz Snapshotter**, **Dragonfly's Nydus**, and **Amazon's SOCI Snapshotter**.

## How Lazy Pulling Works

Traditional container image pulling follows a sequential process: the container runtime contacts the registry, downloads every layer, decompresses them, and assembles the root filesystem. Only then can the container start. For a 2 GB image on a 100 Mbps connection, that's a minimum of ~160 seconds — and that's before decompression overhead.

Lazy pulling changes this paradigm:

1. **Image preparation**: The container image is converted into a format that supports random access. Layers are reorganized so individual files or chunks can be fetched independently.
2. **On-demand fetching**: When the container starts, the snapshotter intercepts file read requests. If a file isn't locally cached, it fetches just that file (or chunk) from the registry.
3. **Background prefetch**: While the container runs, remaining files are streamed in the background based on access patterns.
4. **Local caching**: Fetched content is cached on the node, so subsequent container starts are even faster.

The key difference between the three solutions lies in **how they restructure the image format** and **how they decide what to prefetch**.

## Comparison Table

| Feature | Stargz Snapshotter | Nydus | SOCI Snapshotter |
|---------|-------------------|-------|------------------|
| **Organization** | containerd (CNCF) | Ant Group / Dragonfly (CNCF) | AWS (AWS Labs) |
| **Image Format** | eStargz (gzip-compatible) | Nydus (binary blob + bootstrap) | SOCI (gzip-compatible) |
| **Registry Compatibility** | Standard OCI registries | Requires Nydus-compatible registry or converter | Standard OCI registries |
| **Build-time Conversion** | Required (estargz converter) | Required (nydus-image converter) | Required (soci-snapshotter CLI) |
| **Chunk Size** | File-level | Chunk-level (configurable, default ~128KB) | Chunk-level (~4MB) |
| **Prefetch Strategy** | Configurable priorities | Configurable (file/chunk level) | Access-pattern-based |
| **FUSE-based** | Yes | Yes | Yes |
| **Rootless Support** | Yes | Yes | Yes |
| **Kubernetes Integration** | containerd config | containerd + CRI | containerd config |
| **GitHub Stars** | ~1,534 | ~1,576 | ~727 |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **OCI Compliance** | Fully compliant | Partially compliant | Fully compliant |

## Stargz Snapshotter

Stargz Snapshotter is the reference implementation of eStargz (externally-addressable stargz), a lazy-pulling format developed by NTT and donated to the containerd project. It extends the standard gzip format with an index at the end of each layer, enabling random-access reads without full decompression.

### Architecture

Stargz uses a two-layer architecture:

- **Stargz TOC (Table of Contents)**: An index appended to the end of each gzip-compressed layer, mapping file paths to their byte offsets within the compressed stream.
- **FUSE filesystem driver**: Intercepts file system calls from the container and fetches only the needed chunks from the registry.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  containerd:
    image: ghcr.io/containerd/containerd:latest
    restart: always
    network_mode: host
    privileged: true
    volumes:
      - /etc/containerd:/etc/containerd
      - /var/lib/containerd:/var/lib/containerd
      - /run/containerd:/run/containerd
    command: ["containerd", "--config", "/etc/containerd/config.toml"]

  stargz-snapshotter:
    image: ghcr.io/containerd/stargz-snapshotter:latest
    restart: always
    network_mode: host
    privileged: true
    volumes:
      - /etc/containerd-stargz-grpc:/etc/containerd-stargz-grpc
      - /var/lib/containerd-stargz-grpc:/var/lib/containerd-stargz-grpc
      - /run/containerd-stargz-grpc:/run/containerd-stargz-grpc
    command: ["containerd-stargz-grpc", "--address", "/run/containerd-stargz-grpc/containerd-stargz-grpc.sock"]
    depends_on:
      - containerd
```

### containerd Configuration

```toml
# /etc/containerd/config.toml
[proxy_plugins]
  [proxy_plugins.stargz]
    type = "snapshot"
    address = "/run/containerd-stargz-grpc/containerd-stargz-grpc.sock"

[plugins."io.containerd.grpc.v1.cri".containerd]
  snapshotter = "stargz"
  disable_snapshot_annotations = false
```

### Converting Images to eStargz

```bash
# Install the estargz converter
go install github.com/containerd/stargz-snapshotter/cmd/ctr-remote@latest

# Convert an existing image to eStargz format
ctr-remote image optimize docker.io/library/nginx:latest   --oci   --prefetch   --mount-type=stargz

# Push the optimized image
ctr-remote images push --tls --plain-http registry.example.com/nginx:estargz
```

Stargz's key advantage is **OCI registry compatibility**. The eStargz format is fully backward-compatible with standard OCI registries — you can push eStargz images to Docker Hub, GitHub Container Registry, or any OCI-compliant registry without modifications.

## Nydus

Nydus is the image service developed by Ant Group as part of the Dragonfly project (now a CNCF graduated project). Unlike Stargz, Nydus uses a proprietary binary format optimized for chunk-level random access, providing faster lazy-pulling performance at the cost of requiring a conversion step and a compatible registry.

### Architecture

Nydus restructures container images into two components:

- **Bootstrap**: A small metadata file (typically a few KB) containing the filesystem tree layout, file attributes, and chunk locations. This is the only file needed to start a container.
- **Blob**: The actual file data, split into fixed-size chunks (default 128KB, configurable). Chunks are individually addressable and can be fetched on demand.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  nydus-snapshotter:
    image: ghcr.io/dragonflyoss/image-service/nydus-snapshotter:latest
    restart: always
    network_mode: host
    privileged: true
    volumes:
      - /etc/nydus-snapshotter:/etc/nydus-snapshotter
      - /var/lib/nydus-snapshotter:/var/lib/nydus-snapshotter
      - /run/nydus-snapshotter:/run/nydus-snapshotter
      - /var/run/containerd/containerd.sock:/var/run/containerd/containerd.sock
    command: ["containerd-nydus-grpc", "--address", "/run/nydus-snapshotter/containerd-nydus-grpc.sock"]

  nydusify:
    image: ghcr.io/dragonflyoss/image-service/nydusify:latest
    restart: "no"
    volumes:
      - /etc/nydus-snapshotter:/etc/nydus-snapshotter
    command: ["nydusify", "convert", "--source", "docker.io/library/nginx:latest", "--target", "registry.example.com/nginx:nydus"]
```

### Converting Images with Nydusify

```bash
# Install nydusify
go install github.com/dragonflyoss/image-service/cmd/nydusify@latest

# Convert and push in one command
nydusify convert   --source docker.io/library/nginx:latest   --target registry.example.com/nginx:nydus   --fs-type bootstrap

# Verify the converted image
nydusify check --target registry.example.com/nginx:nydus
```

### containerd Configuration

```toml
# /etc/containerd/config.toml
[proxy_plugins.nydus]
  type = "snapshot"
  address = "/run/nydus-snapshotter/containerd-nydus-grpc.sock"

[plugins."io.containerd.grpc.v1.cri".containerd]
  snapshotter = "nydus"
```

Nydus's chunk-level granularity means it can fetch only the exact bytes needed, making it particularly efficient for large images where only a small fraction of files are accessed at startup. The tradeoff is that the Nydus format is not OCI-compliant — images must be stored in a Nydus-compatible registry or converted back to OCI format for cross-registry portability.

## SOCI Snapshotter

SOCI (Seekable OCI) Snapshotter is Amazon's contribution to the lazy-pulling ecosystem. Like Stargz, it maintains OCI registry compatibility but uses a different approach: it creates a separate zTOC (zstd Table of Contents) index as a separate manifest layer, rather than appending metadata to the existing gzip stream.

### Architecture

SOCI separates the index from the image layers:

- **zTOC layer**: A standalone manifest containing file offsets and chunk metadata for each OCI layer, pushed as an additional layer in the image manifest.
- **FUSE driver**: Fetches individual chunks from the registry using HTTP Range requests, guided by the zTOC index.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  soci-snapshotter:
    image: public.ecr.aws/soci-workspace/soci-snapshotter:latest
    restart: always
    network_mode: host
    privileged: true
    volumes:
      - /etc/soci-snapshotter:/etc/soci-snapshotter
      - /var/lib/soci-snapshotter:/var/lib/soci-snapshotter
      - /run/soci-snapshotter:/run/soci-snapshotter
      - /var/run/containerd/containerd.sock:/var/run/containerd/containerd.sock
    command: ["soci-snapshotter-grpc", "--address", "/run/soci-snapshotter/soci-snapshotter-grpc.sock"]
```

### Converting Images with SOCI

```bash
# Install SOCI CLI
go install github.com/awslabs/soci-snapshotter/cmd/soci@latest

# Create SOCI indices for an image
soci create docker.io/library/nginx:latest --min-layer-size 10000000

# Push indices to the registry (alongside the original image)
soci push --auth docker.io/library/nginx:latest

# Pull with SOCI lazy loading
soci pull --auth docker.io/library/nginx:latest
```

### containerd Configuration

```toml
# /etc/containerd/config.toml
[proxy_plugins.soci]
  type = "snapshot"
  address = "/run/soci-snapshotter/soci-snapshotter-grpc.sock"

[plugins."io.containerd.grpc.v1.cri".containerd]
  snapshotter = "soci"
  disable_snapshot_annotations = false
```

SOCI's approach of keeping the index as a separate layer means the original OCI layers remain completely untouched. This provides the strongest OCI compliance of the three solutions, making it ideal for environments where image portability across registries is critical.

## Performance Comparison

Based on published benchmarks from each project:

| Metric | Standard Pull | Stargz | Nydus | SOCI |
|--------|--------------|--------|-------|------|
| **Cold start time (500MB image)** | ~45s | ~3s | ~2s | ~4s |
| **Cold start time (2GB image)** | ~180s | ~5s | ~3s | ~6s |
| **Index size overhead** | N/A | ~5% | ~2% | ~3% |
| **Registry bandwidth (first pull)** | 100% | ~15% | ~10% | ~12% |
| **Subsequent start (cached)** | 100% | ~5% | ~3% | ~5% |

Nydus generally achieves the fastest start times due to its smaller chunk size (128KB vs SOCI's 4MB), allowing more precise fetching. However, Stargz and SOCI offer easier integration since they work with standard OCI registries out of the box.

## Choosing the Right Solution

**Choose Stargz Snapshotter if:**
- You are already using containerd and want native integration
- OCI registry compatibility is critical (Docker Hub, GHCR)
- You prefer a CNCF-graduated project with strong community backing
- Your images are moderate size (< 1GB) and file-level granularity is sufficient

**Choose Nydus if:**
- You need the fastest possible cold start times
- You are running large images (multi-GB databases, ML models)
- You can manage a Nydus-compatible registry or conversion pipeline
- Chunk-level granularity matters for your workload

**Choose SOCI Snapshotter if:**
- You run on AWS or use Amazon ECR
- You need strong OCI compliance with zero image format changes
- Your workloads benefit from the zTOC index approach
- You want a solution backed by a major cloud provider

For related reading, see our [P2P Container Image Distribution guide](../2026-04-28-spegel-vs-kraken-vs-dragonfly-self-hosted-p2p-container-image-distribution-guide-2026/) and [OCI Container Runtimes comparison](../2026-05-09-oci-container-runtimes-crun-runc-youki-guide/).

## Why Self-Host Your Image Distribution Infrastructure?

When running containers at scale, how you distribute images directly impacts deployment velocity, infrastructure costs, and operational reliability. Lazy pulling solutions like Stargz, Nydus, and SOCI address several critical challenges that cloud-based registries alone cannot solve.

**Reduced cold-start latency** is the most immediate benefit. In autoscaling scenarios, a node must pull and start containers within seconds to handle traffic spikes. Traditional pulling from a remote registry can take minutes for large images, causing dropped requests during scaling events. Lazy pulling reduces this to single-digit seconds, making horizontal pod autoscaling (HPA) actually responsive to real-time traffic changes.

**Bandwidth cost savings** accumulate quickly. When deploying the same 2 GB image across 100 nodes, a full pull consumes 200 GB of egress bandwidth. With lazy pulling, each node downloads only 10-15% of the image at startup, reducing total bandwidth by 170-180 GB. For organizations paying $0.05-0.12/GB for egress, this translates to $8-22 per deployment cycle — multiplied by dozens or hundreds of daily deployments, the savings are substantial.

**Registry availability independence** is critical for production systems. If your registry experiences an outage, containers that use lazy pulling can still start from locally cached content. The snapshotter's FUSE-based architecture means that once a file chunk is cached, it never needs to be re-fetched from the registry.

**Faster CI/CD pipelines** benefit from lazy pulling as well. Build agents that need to pull base images for testing can start containers immediately rather than waiting for full downloads. This is especially valuable for parallel test suites that spin up dozens of ephemeral containers.

**Storage efficiency** improves because lazy-pulling snapshots share common content across containers at the block level. Unlike traditional overlay filesystems that duplicate layers, lazy-pulling snapshots reference the same cached chunks, reducing disk usage on worker nodes.

## FAQ

### What is container image lazy pulling?

Container image lazy pulling is a technique where only the specific files or data chunks needed to start a container are downloaded from the registry, rather than the entire image. The remaining data streams in the background while the container is already running. This can reduce container start times by 90% or more.

### Do lazy-pulled images work with standard Docker registries?

Stargz and SOCI maintain full OCI registry compatibility, meaning eStargz and SOCI-optimized images can be pushed to Docker Hub, GitHub Container Registry, Amazon ECR, or any OCI-compliant registry. Nydus requires a Nydus-compatible registry or a conversion step to translate back to OCI format.

### Can I use lazy pulling with Kubernetes?

Yes. All three solutions integrate with Kubernetes through containerd's proxy plugin interface. You configure the snapshotter in containerd's config.toml, then set the snapshotter name in your containerd CRI plugin configuration. Pods will automatically use lazy pulling when the snapshotter is set as the default.

### Is there a performance penalty for on-demand fetching?

During initial startup, the first few file reads may experience slightly higher latency (typically a few milliseconds) as the snapshotter fetches the required chunk from the registry. Once cached, subsequent reads are local-disk speed. For most workloads, this is negligible — the overall container start time is dramatically reduced because the container doesn't wait for the full image download.

### Which solution should I choose for my cluster?

If you prioritize OCI compatibility and ease of integration, choose Stargz or SOCI. If you need maximum performance and can manage a custom image format, choose Nydus. For AWS users, SOCI has native integration with Amazon ECR. For multi-cloud deployments, Stargz's broad registry support makes it the safest choice.

### Does lazy pulling work with all container images?

Yes, but the image must first be converted to the target format (eStargz, Nydus, or SOCI). The conversion process is a one-time build step — you convert the image once and push it to your registry. Subsequent deployments use the converted image directly. Most CI/CD pipelines can incorporate this conversion as a post-build step.

### How does lazy pulling affect image security and signing?

The conversion process preserves image integrity. Both Stargz and SOCI maintain the original layer digests, so image verification and signing (e.g., with Cosign or Notation) continue to work. Nydus creates new blob digests, so signature verification requires re-signing the converted image.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Lazy Pulling: Stargz Snapshotter vs Nydus vs SOCI Snapshotter",
  "description": "Compare the three leading open-source container image lazy pulling solutions: Stargz Snapshotter, Nydus, and SOCI Snapshotter. Learn about architecture, performance, Docker Compose deployment, and which to choose.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
