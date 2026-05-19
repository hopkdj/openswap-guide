---
title: "Self-Hosted S3 Mount Tools — s3fs vs goofys vs rclone mount"
date: "2026-05-20"
tags: ["storage", "s3", "cloud-storage", "file-system", "self-hosted"]
draft: false
---

Amazon S3-compatible object storage has become the de facto standard for cloud storage, but mounting an S3 bucket as a local filesystem unlocks powerful workflows — from legacy application compatibility to seamless backup pipelines. Three open-source tools dominate this space: **s3fs**, **goofys**, and **rclone mount**. Each takes a fundamentally different approach to bridging the gap between POSIX filesystem semantics and S3's object storage API.

In this guide, we compare all three tools across performance, caching, POSIX compliance, Docker deployment, and real-world use cases to help you pick the right S3 mount solution for your infrastructure.

## How S3-to-POSIX Mounting Works

Object storage APIs like S3 are fundamentally different from POSIX filesystems. S3 operations are stateless and eventual-consistency, while POSIX expects immediate consistency, file locking, and random write support. S3 mount tools solve this mismatch using different strategies:

- **s3fs** translates POSIX calls to S3 API requests, downloading and uploading entire objects for each operation
- **goofys** uses a high-performance "faking" approach, caching metadata and streaming data on-demand
- **rclone mount** leverages rclone's virtual filesystem layer with aggressive caching and VFS (Virtual File System) options

Understanding these architectural differences is key to choosing the right tool. s3fs prioritizes POSIX compliance, goofys prioritizes performance, and rclone mount sits in the middle with configurable behavior.

## Tool Comparison

| Feature | s3fs-fuse | goofys | rclone mount |
|---|---|---|---|
| GitHub Stars | 9,856 | 5,542 | 44,000+ |
| Language | C++ | Go | Go |
| POSIX Compliance | High (full FUSE) | Low (best effort) | Medium (configurable VFS) |
| Write Support | Full read/write | Full read/write | Full read/write |
| Caching | Local disk cache | In-memory metadata | VFS + disk cache |
| Performance | Slower (full object fetch) | Fast (streaming) | Fast (chunked) |
| Multipart Upload | Yes | Yes | Yes |
| Server-Side Encryption | Yes | Yes | Yes |
| IAM Role Support | Yes | Yes | Yes |
| Docker Friendly | Yes | Yes | Yes |
| Active Development | Yes | Sporadic | Very Active |
| License | GPL v2 | Apache 2.0 | MIT |

## s3fs-fuse: The POSIX-Compliant Choice

s3fs-fuse is the most mature and POSIX-compliant S3 mount tool. It uses FUSE (Filesystem in Userspace) to provide a full POSIX interface over S3.

**Strengths:**
- Best POSIX compatibility — supports hard links, symlinks, permissions
- Works with legacy applications that expect traditional filesystem behavior
- Supports S3-compatible backends (MinIO, Ceph RGW, SeaweedFS)
- Configurable multipart upload thresholds and cache directory

**Weaknesses:**
- Performance overhead — every file read/write involves full object transfer
- High latency for random I/O patterns
- Cache management requires manual tuning

**Installation:**

```bash
# Ubuntu/Debian
apt-get update && apt-get install -y s3fs

# Build from source for latest features
git clone https://github.com/s3fs-fuse/s3fs-fuse.git
cd s3fs-fuse
./autogen.sh
./configure
make -j$(nproc)
make install
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  s3fs-mount:
    image: ubuntu:24.04
    container_name: s3fs-mount
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/fuse
    security_opt:
      - apparmor:unconfined
    volumes:
      - ./s3fs-credentials:/etc/s3fs:ro
      - ./s3fs-cache:/tmp/s3fs-cache
      - s3-mount:/mnt/s3:shared
    environment:
      - AWS_ACCESS_KEY_ID=your-access-key
      - AWS_SECRET_ACCESS_KEY=your-secret-key
      - S3_BUCKET=my-bucket
      - S3_URL=https://s3.example.com
    command: >
      bash -c "
        s3fs $$S3_BUCKET /mnt/s3
        -o url=$$S3_URL
        -o use_path_request_style
        -o use_cache=/tmp/s3fs-cache
        -o multipart_size=64
        -o allow_other
        -o umask=002
        && tail -f /dev/null
      "
    restart: unless-stopped

volumes:
  s3-mount:
```

## goofys: The High-Performance Option

goofys (GO of Your S3) is a high-performance, POSIX-ish S3 filesystem written in Go. It sacrifices strict POSIX compliance for dramatically better throughput.

**Strengths:**
- Much faster than s3fs — streams data on-demand instead of fetching full objects
- Low memory footprint — metadata-only caching
- Handles large directories better than s3fs
- Single binary with no FUSE library dependency (uses its own FUSE implementation)

**Weaknesses:**
- Not POSIX compliant — no hard links, limited permission support
- Some applications may fail due to missing POSIX features
- Less active development (last major update in 2024)
- No support for file renaming (copy + delete)

**Installation:**

```bash
# Download latest binary
wget https://github.com/kahing/goofys/releases/latest/download/goofys
chmod +x goofys
sudo mv goofys /usr/local/bin/

# Mount a bucket
goofys --endpoint https://s3.example.com my-bucket /mnt/s3
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  goofys-mount:
    image: golang:1.23-alpine
    container_name: goofys-mount
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/fuse
    security_opt:
      - apparmor:unconfined
    volumes:
      - goofys-mount:/mnt/s3:shared
      - ./aws-credentials:/root/.aws:ro
    environment:
      - AWS_ACCESS_KEY_ID=your-access-key
      - AWS_SECRET_ACCESS_KEY=your-secret-key
      - ENDPOINT_URL=https://s3.example.com
      - BUCKET=my-bucket
    command: >
      sh -c "
        go install github.com/kahing/goofys@latest
        goofys
        --endpoint $$ENDPOINT_URL
        --dir-mode 0777
        --file-mode 0666
        $$BUCKET /mnt/s3
        && tail -f /dev/null
      "
    restart: unless-stopped

volumes:
  goofys-mount:
```

## rclone mount: The Configurable Swiss Army Knife

rclone mount uses rclone's Virtual File System (VFS) layer to provide a configurable S3 mount experience. It sits between s3fs's strict compliance and goofys's performance-first approach.

**Strengths:**
- Extremely configurable — VFS cache modes (off, minimal, writes, full)
- Built-in encryption, compression, and chunking
- Supports 70+ cloud storage providers, not just S3
- Active development with frequent releases
- Excellent documentation and community

**Weaknesses:**
- Slightly more complex configuration
- VFS cache requires disk space management
- Full POSIX mode adds latency

**Installation:**

```bash
# Official install script
curl https://rclone.org/install.sh | sudo bash

# Or via package manager
apt-get install -y rclone

# Configure remote
rclone config
# Follow prompts to set up S3 remote with name "mys3"
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  rclone-mount:
    image: rclone/rclone:latest
    container_name: rclone-mount
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/fuse
    security_opt:
      - apparmor:unconfined
    volumes:
      - rclone-mount:/data:shared
      - ./rclone.conf:/config/rclone/rclone.conf:ro
      - ./rclone-cache:/cache
    command: >
      mount mys3:my-bucket /data
      --allow-other
      --vfs-cache-mode full
      --vfs-cache-max-size 10G
      --vfs-cache-max-age 24h
      --cache-dir /cache
      --dir-cache-time 5m
      --buffer-size 32M
      --log-level INFO
    restart: unless-stopped

volumes:
  rclone-mount:
```

## Performance Comparison

Benchmark results will vary based on network latency, object size, and workload patterns. Here are typical performance characteristics:

| Workload | s3fs | goofys | rclone mount |
|---|---|---|---|
| Sequential read (1MB files) | 15-30 MB/s | 80-150 MB/s | 60-120 MB/s |
| Sequential write (1MB files) | 10-20 MB/s | 70-130 MB/s | 50-100 MB/s |
| Random read (small files) | Very slow | Fast | Medium-Fast |
| Random write | Very slow | Medium | Medium |
| Directory listing (10K files) | 5-15s | 1-3s | 2-5s |
| First file open latency | High | Low | Low-Medium |

## When to Choose Each Tool

**Choose s3fs when:**
- You need strict POSIX compatibility (file locks, permissions, hard links)
- Running legacy applications that expect traditional filesystem semantics
- Working with small-scale, low-throughput workloads
- Your S3-compatible backend supports all required features

**Choose goofys when:**
- Performance is your top priority
- You can tolerate reduced POSIX compliance
- Working with large files and sequential I/O patterns
- Your application doesn't need hard links or complex permissions

**Choose rclone mount when:**
- You need a balance between performance and compatibility
- You want configurable caching behavior
- You need to work with multiple cloud providers beyond S3
- You want encryption, compression, or chunking features

## Why Self-Host Your S3 Mount Layer?

Managing your own S3 mount infrastructure gives you complete control over how object storage integrates with your existing systems. When you self-host the mount layer, you decide the caching strategy, the credential management approach, and the security posture — rather than relying on a third-party service's default behavior.

Self-hosted mount tools work seamlessly with self-hosted S3-compatible backends like MinIO, SeaweedFS, Garage, and Ceph RGW. For a deeper dive into S3 object storage options, see our [MinIO vs SeaweedFS vs Garage comparison](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/) and [cold storage solutions guide](../2026-05-10-self-hosted-cold-storage-solutions-minio-ceph-seaweedfs-guide/).

Running the mount layer locally eliminates egress charges when accessing your own S3-compatible storage over the local network. This is particularly important for large-scale data processing pipelines, where network costs can exceed storage costs. You also gain full visibility into mount operations, cache hit rates, and API call patterns — essential for capacity planning and performance tuning.

Self-hosting also means your credentials never leave your infrastructure. With s3fs, goofys, and rclone mount, you manage IAM policies, access keys, and encryption settings entirely within your control. For organizations handling sensitive data or operating under regulatory requirements, this control is non-negotiable.

If you're also looking at cloud storage aggregation tools, our [rclone vs Alist vs Filestash guide](../2026-04-30-alist-vs-rclone-vs-filestash-self-hosted-cloud-storage-aggregator-guide/) covers complementary approaches to unified cloud storage access.

## FAQ

### What is the difference between s3fs, goofys, and rclone mount?

s3fs provides the highest POSIX compliance by translating filesystem calls directly to S3 API requests. goofys prioritizes performance by streaming data on-demand and caching metadata in memory. rclone mount offers configurable behavior through its VFS layer, letting you tune the balance between performance and compliance.

### Can I use these tools with MinIO?

Yes. All three tools support any S3-compatible backend. For MinIO, use the `--endpoint` flag (goofys) or `--url` option (s3fs) pointed at your MinIO server URL. rclone supports MinIO through its S3 remote configuration.

### Which tool has the best write performance?

goofys generally offers the best write performance due to its streaming architecture and minimal caching overhead. rclone mount with `--vfs-cache-mode writes` is a close second. s3fs is the slowest for writes since it uploads entire objects on every modification.

### Do these tools support S3 server-side encryption?

Yes. All three support SSE-S3 (Amazon-managed keys) and SSE-KMS (customer-managed keys). Configure encryption through the appropriate flags or configuration options for each tool.

### Can I run these tools in Docker containers?

Yes. All three require `SYS_ADMIN` capability and `/dev/fuse` device access. The Docker Compose examples above show the required security settings and volume mounts.

### What happens to cached data when the container restarts?

s3fs and rclone mount persist cache to disk — configure a Docker volume for the cache directory to preserve it across restarts. goofys caches metadata in memory, so the cache is rebuilt on restart. For goofys, this is fast since only metadata (not file content) is cached.

### Is goofys still actively maintained?

goofys's development has slowed since 2024, but the tool is stable and widely used. For active development, rclone mount receives frequent updates and new features. s3fs also sees regular maintenance updates.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted S3 Mount Tools — s3fs vs goofys vs rclone mount",
  "description": "Compare three open-source tools for mounting S3-compatible object storage as a local filesystem: s3fs-fuse, goofys, and rclone mount. Covers performance, POSIX compliance, Docker deployment, and when to choose each tool.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
