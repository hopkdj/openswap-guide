---
title: "Self-Hosted S3 Proxy Gateways: S3Proxy vs Rclone Serve vs MinIO Gateway (2026)"
date: "2026-05-15"
tags: ["s3", "object-storage", "gateway", "proxy", "cloud-storage", "self-hosted"]
draft: false
---

When you need to expose non-S3 storage backends through the Amazon S3 API, or unify multiple cloud storage providers behind a single S3-compatible endpoint, a self-hosted S3 proxy gateway becomes essential. Whether you are migrating from Azure Blob to S3, serving local filesystem storage to S3-only applications, or building a multi-cloud storage abstraction layer, the right proxy tool saves weeks of application refactoring.

This guide compares three leading open-source S3 proxy solutions: **S3Proxy**, **Rclone Serve**, and **MinIO Gateway Mode**. Each offers a different approach to S3 API translation, with distinct tradeoffs in performance, feature coverage, and operational complexity.

## What Is an S3 Proxy Gateway?

An S3 proxy gateway sits between your applications and your actual storage backend. It translates incoming S3 API requests (GetObject, PutObject, ListBucket, etc.) into the native API calls of the underlying storage system — whether that is Azure Blob Storage, Google Cloud Storage, a local filesystem, FTP/SFTP, WebDAV, or another object store.

The primary use cases include:

- **Cloud migration**: Keep applications using S3 SDKs while the backend storage changes from AWS to Azure, GCS, or on-premises systems
- **Multi-cloud abstraction**: Present a unified S3 interface across multiple storage providers
- **Local development**: Use the S3 API against local filesystem storage for testing without AWS credentials
- **Legacy application support**: Give S3-compatible access to storage systems that only support FTP, WebDAV, or other protocols
- **Cost optimization**: Route cold data to cheaper backends (Backblaze B2, Wasabi) while keeping hot data on faster storage

## S3Proxy: Dedicated S3 Translation Layer

[S3Proxy](https://github.com/andrewgaul/s3proxy) is a purpose-built S3 API proxy that translates S3 requests to a wide range of backend storage providers. It supports Azure Blob, Google Cloud Storage, OpenStack Swift, filesystem, local memory, and S3-compatible backends.

**GitHub:** [andrewgaul/s3proxy](https://github.com/andrewgaul/s3proxy) — 2,250+ stars, actively maintained

### Key Features

- Full S3 API compatibility (v2 and v4 authentication signatures)
- Supports 10+ backend storage providers including Azure, GCS, Swift, filesystem, and S3
- CORS configuration and bucket lifecycle policies
- Identity-based access control with configurable credentials
- Path-style and virtual-hosted-style URL formats
- Multipart upload passthrough

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  s3proxy:
    image: andrewgaul/s3proxy:latest
    container_name: s3proxy
    ports:
      - "8080:80"
    environment:
      S3PROXY_AUTHORIZATION: aws-v2
      S3PROXY_IDENTITY: my-identity
      S3PROXY_CREDENTIAL: my-credential
      JCLOUDS_PROVIDER: filesystem
      JCLOUDS_ENDPOINT: http://localhost:8080
      JCLOUDS_REGION: us-east-1
      JCLOUDS_REGIONS: us-east-1
      JCLOUDS_IDENTITY: my-identity
      JCLOUDS_CREDENTIAL: my-credential
    volumes:
      - s3proxy-data:/data
    restart: unless-stopped

volumes:
  s3proxy-data:
```

### Azure Blob Backend Example

```yaml
services:
  s3proxy-azure:
    image: andrewgaul/s3proxy:latest
    environment:
      S3PROXY_AUTHORIZATION: aws-v4
      S3PROXY_IDENTITY: azure-identity
      S3PROXY_CREDENTIAL: azure-credential
      JCLOUDS_PROVIDER: azureblob
      JCLOUDS_IDENTITY: "your-storage-account"
      JCLOUDS_CREDENTIAL: "your-access-key"
    ports:
      - "8080:80"
```

## Rclone Serve: Multi-Protocol Storage Server

[Rclone](https://github.com/rclone/rclone) is best known as "rsync for cloud storage," but its `rclone serve` subcommand includes a full S3-compatible server mode. With support for over 70 storage backends, Rclone Serve offers the broadest backend coverage of any tool in this comparison.

**GitHub:** [rclone/rclone](https://github.com/rclone/rclone) — 57,000+ stars, extremely active development

### Key Features

- 70+ cloud and local storage backends
- S3, WebDAV, HTTP, FTP, and DLNA serve modes
- Built-in caching layer with disk and memory options
- VFS (Virtual File System) with directory caching
- Read/write bandwidth limits and rate limiting
- Encryption layer (crypt remote) for server-side encryption
- Union remote for combining multiple backends

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  rclone-s3:
    image: rclone/rclone:latest
    container_name: rclone-s3
    command: >
      serve s3 /data
      --addr :8080
      --s3-acl private
      --user admin
      --pass encrypted-password-here
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
      - ./rclone.conf:/config/rclone/rclone.conf
    environment:
      - TZ=UTC
    restart: unless-stopped
```

### Serve Google Drive as S3

```yaml
services:
  rclone-gdrive-s3:
    image: rclone/rclone:latest
    command: >
      serve s3 gdrive-remote:
      --addr :8080
      --user s3-user
      --pass s3-pass
      --s3-acl bucket-owner-full-control
    volumes:
      - ./rclone.conf:/config/rclone/rclone.conf
    ports:
      - "8080:8080"
```

## MinIO Gateway Mode: Enterprise S3 Frontend

[MinIO](https://github.com/minio/minio) is a high-performance, S3-compatible object store. Its gateway mode (available in earlier versions; the functionality is now integrated into MinIO's tiering and ILM features) provides an S3-compatible frontend for NAS, HDFS, Azure Blob, and GCS backends.

**GitHub:** [minio/minio](https://github.com/minio/minio) — 60,900+ stars, enterprise-grade project

### Key Features

- High-performance S3-compatible API with full feature parity
- Erasure coding and bitrot protection
- Server-side encryption (SSE-S3, SSE-KMS, SSE-C)
- Bucket lifecycle management and object versioning
- Built-in Prometheus metrics endpoint
- Console UI for management and monitoring
- Active-Active replication (site replication)

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  minio-gateway:
    image: minio/minio:latest
    container_name: minio-gateway
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin-secret
      MINIO_STORAGE_CLASS_STANDARD: EC:2
    volumes:
      - minio-data:/data
      - minio-config:/root/.minio
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  minio-data:
  minio-config:
```

### NAS Gateway (Local Filesystem as S3)

```yaml
services:
  minio-nas:
    image: minio/minio:latest
    command: server /mnt/nas --console-address ":9001"
    environment:
      MINIO_ROOT_USER: nas-admin
      MINIO_ROOT_PASSWORD: secure-nas-password
    volumes:
      - /mnt/nas-storage:/mnt/nas
    ports:
      - "9000:9000"
      - "9001:9001"
```

## Comparison Table

| Feature | S3Proxy | Rclone Serve | MinIO |
|---|---|---|---|
| **GitHub Stars** | 2,250+ | 57,000+ | 60,900+ |
| **Primary Focus** | S3 API translation | Multi-protocol storage | S3-compatible object store |
| **Backend Count** | 10+ | 70+ | Native + gateway modes |
| **S3 API Coverage** | Full (v2 + v4) | Good | Full |
| **Azure Blob** | Yes | Yes | Yes (gateway) |
| **Google Cloud Storage** | Yes | Yes | Yes (gateway) |
| **Local Filesystem** | Yes | Yes | Yes (NAS mode) |
| **Multipart Upload** | Passthrough | Supported | Native |
| **CORS Support** | Yes | Limited | Yes |
| **Server-Side Encryption** | No | Yes (crypt remote) | Yes (SSE-S3/KMS/C) |
| **Versioning** | No | No | Yes |
| **Erasure Coding** | No | No | Yes |
| **Web Console** | No | No | Yes |
| **Prometheus Metrics** | No | No | Yes |
| **License** | Apache 2.0 | MIT | GNU AGPLv3 |

## Choosing the Right S3 Proxy

**Use S3Proxy when:** You need a lightweight, dedicated S3 translation layer with minimal resource overhead. It is ideal for simple use cases like exposing Azure Blob Storage to S3-only applications, or running a local S3-compatible endpoint for development testing.

**Use Rclone Serve when:** You need the widest possible backend coverage and already use Rclone for storage management. The 70+ backend support, combined with encryption, caching, and union features, makes it the most versatile option for complex multi-cloud storage scenarios.

**Use MinIO when:** You need enterprise-grade S3 compatibility with full feature parity, including versioning, erasure coding, encryption, and a management console. MinIO is the best choice when the proxy itself needs to provide production-grade object storage capabilities beyond simple API translation.

## Performance Considerations

S3Proxy adds minimal latency because it translates requests directly without additional caching layers. For high-throughput scenarios with large objects, this direct passthrough approach is efficient. However, it does not provide caching, so every request hits the backend storage.

Rclone Serve includes a VFS layer with configurable caching (directory cache, read-ahead buffers), which can significantly improve performance for frequently accessed objects. The tradeoff is higher memory usage, especially with the VFS enabled.

MinIO provides the best raw performance of the three, with its native object store optimized for high-throughput S3 operations. When used in gateway mode, there is some translation overhead, but the built-in caching, read-ahead, and parallel upload mechanisms typically outperform the other two options.

## Security Best Practices

1. **Always use TLS termination** — Place a reverse proxy (Nginx, Caddy, Traefik) in front of the S3 proxy to encrypt all traffic in transit
2. **Use S3 v4 authentication** — Avoid v2 signatures when possible; v4 provides region-scoped request signing
3. **Isolate credentials** — Store backend storage credentials in environment variables or a secrets manager, never in Docker Compose files checked into version control
4. **Limit bucket permissions** — Use IAM policies or bucket policies to restrict access to specific buckets and operations
5. **Monitor access logs** — Enable request logging and forward to a centralized log management system for audit trail

## Deployment Architecture

For production deployments, consider this architecture:

```
                    ┌─────────────┐
    Applications ──▶│  Nginx/TLS  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  S3 Proxy   │
                    │  (cluster)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Azure   │ │  GCS     │ │  Local   │
        │  Blob    │ │          │ │  NAS     │
        └──────────┘ └──────────┘ └──────────┘
```

Multiple S3 proxy instances can be placed behind a load balancer for high availability. Stateless proxy instances mean horizontal scaling is straightforward — just add more containers.

## Why Self-Host Your S3 Gateway?

Running your own S3 proxy gateway gives you complete control over the storage abstraction layer that sits between your applications and your data. When you depend on cloud storage APIs but want to avoid vendor lock-in, a self-hosted gateway provides the flexibility to switch backends without modifying application code.

The cost benefits can be significant. Instead of paying premium rates for AWS S3, you can route data through your gateway to cheaper alternatives like Backblaze B2, Wasabi, or on-premises storage — all while your applications continue using familiar S3 SDKs and tools. This approach is especially valuable for organizations with large datasets where storage costs represent a major operational expense.

Data sovereignty requirements also drive the need for self-hosted S3 gateways. When regulations require data to remain within specific geographic boundaries, a gateway lets you route requests to compliant backends while maintaining the S3 API that your development team expects.

For development and testing environments, a self-hosted S3 proxy eliminates the need for AWS credentials entirely. Developers can work against a local S3-compatible endpoint, reducing cloud costs during development and ensuring that CI/CD pipelines are not blocked by external service dependencies.

If you are evaluating object storage backends, see our [S3 object storage comparison](../2026-05-14-self-hosted-s3-object-storage-garage-vs-seaweedfs-vs-ceph-rgw-guide/) for a detailed look at MinIO, SeaweedFS, and Garage. For file synchronization workflows that complement S3 proxy setups, our [rclone comparison guide](../2026-04-26-rsync-vs-rclone-vs-lsyncd-self-hosted-file-sync-tools-guide-2026/) covers the broader storage tooling ecosystem. And for cold storage strategies that pair well with S3 proxy tiering, the [cold storage solutions guide](../2026-05-10-self-hosted-cold-storage-solutions-minio-ceph-seaweedfs-guide/) provides additional context.

## FAQ

### What is the difference between S3Proxy and MinIO?

S3Proxy is a translation layer that converts S3 API calls into the native APIs of other storage providers (Azure, GCS, filesystem). MinIO is a full S3-compatible object store that stores data natively. MinIO Gateway mode adds translation capabilities, but the core project is designed as a primary storage system, not just a proxy.

### Can Rclone Serve replace an S3-compatible object store?

Rclone Serve provides an S3-compatible API but is not a replacement for a full object store. It lacks features like versioning, erasure coding, and bucket lifecycle policies. It is best suited for serving existing storage backends through the S3 API, not for primary object storage.

### Does S3Proxy support S3 Select or S3 Batch Operations?

No. S3Proxy focuses on core S3 API operations (GET, PUT, LIST, DELETE) and does not implement advanced features like S3 Select, Batch Operations, or Glacier retrieval. For these features, you would need a full S3-compatible store like MinIO or direct access to AWS S3.

### How do I migrate from AWS S3 to a self-hosted gateway?

Configure your chosen proxy (S3Proxy, Rclone Serve, or MinIO Gateway) with AWS S3 as the backend, then gradually update application endpoint URLs to point to your proxy. Once all traffic flows through the proxy, you can change the backend to a different provider without touching application code.

### Is MinIO Gateway mode still available in current versions?

MinIO has evolved its gateway functionality. In recent versions, the standalone gateway mode has been integrated into MinIO's tiered storage and ILM (Information Lifecycle Management) features. For pure proxy use cases, S3Proxy or Rclone Serve may be simpler options.

### Which S3 proxy supports the most storage backends?

Rclone Serve supports 70+ backends, far more than S3Proxy (10+) or MinIO Gateway (5+). If you need to expose an unusual storage protocol (Yandex Disk, Mega, Box) through the S3 API, Rclone is the most likely to support it.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted S3 Proxy Gateways: S3Proxy vs Rclone Serve vs MinIO Gateway (2026)",
  "description": "Compare S3Proxy, Rclone Serve, and MinIO Gateway Mode for self-hosted S3-compatible API proxying. Docker Compose configs, feature comparison, and deployment guide.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
