---
title: "Self-Hosted Resumable File Upload Servers 2026: tusd vs tus-node-server vs tusdotnet (TUS Protocol)"
date: 2026-05-02T20:30:00+00:00
tags: ["file-upload", "tus-protocol", "file-sharing", "resumable-upload", "self-hosted", "web-server"]
draft: false
---

Large file uploads are notoriously fragile. A dropped Wi-Fi connection, a server timeout, or a browser crash can wipe out a 10 GB upload mid-transfer, forcing users to start from scratch. The **TUS protocol** solves this problem with resumable, chunked file uploads that survive network interruptions.

In this guide, we compare the three leading open-source TUS server implementations — **tusd**, **tus-node-server**, and **tusdotnet** — to help you choose the right self-hosted upload server for your infrastructure.

## What Is the TUS Protocol?

TUS is an open-source protocol (RFC 8188) for resumable file uploads over HTTP. It standardizes how clients and servers negotiate upload sessions, handle chunked transfers, and resume interrupted uploads. The protocol defines a set of HTTP methods and headers:

- **POST** — Create a new upload session
- **HEAD** — Query the current offset of an upload
- **PATCH** — Upload a chunk of data at a specific offset
- **DELETE** — Cancel an upload session

Key benefits of TUS:

| Feature | Benefit |
|---------|---------|
| Resumable uploads | Interrupted transfers resume from last chunk, not from zero |
| Parallel uploads | Multiple chunks can be uploaded simultaneously for large files |
| Server-agnostic | Works with any storage backend (disk, S3, Azure, GCS) |
| Client ecosystem | Official clients for JavaScript, Go, Python, iOS, Android, Java, and more |
| No vendor lock-in | Open standard, supported by multiple independent implementations |

The TUS ecosystem includes official client libraries across every major platform, making it easy to integrate resumable uploads into any application.

## TUS Server Implementations Compared

Three server implementations dominate the TUS ecosystem. Each targets a different technology stack and deployment scenario.

| Feature | **tusd** | **tus-node-server** | **tusdotnet** |
|---------|----------|---------------------|---------------|
| Language | Go | TypeScript (Node.js) | C# (.NET) |
| GitHub Stars | ⭐ 3,778 | ⭐ 1,078 | ⭐ 600+ |
| Last Updated | May 2026 | May 2026 | Active |
| License | MIT | MIT | MIT |
| Storage Backends | Local disk, AWS S3, Azure Blob, GCS | Local disk, AWS S3, Azure, GCS | Local disk, Azure Blob |
| Standalone Server | ✅ Yes (CLI binary) | ✅ Yes (npm) | ✅ Yes (NuGet) |
| Embeddable | ✅ Go library | ✅ Express/Koa/Fastify middleware | ✅ ASP.NET Core middleware |
| Concurrent Uploads | ✅ Native goroutines | ✅ Async Node.js | ✅ Async/await |
| Docker Image | ✅ `tusproject/tusd` | ✅ Community images | ✅ Community images |
| Expiry/Cleanup | ✅ Built-in | ✅ Via plugin | ✅ Via configuration |
| Web UI | ❌ No | ❌ No | ❌ No |

### tusd — The Reference Implementation

**tusd** is the official reference implementation of the TUS protocol, written in Go. It's the most feature-complete and battle-tested option, used in production by companies worldwide.

**Strengths:**
- Official reference implementation — sets the standard for protocol compliance
- Native Go performance — handles thousands of concurrent uploads with minimal memory
- Built-in storage backends for disk, S3, Azure, and Google Cloud Storage
- Standalone binary with no runtime dependencies
- Hook system for custom authentication, validation, and post-processing

**Weaknesses:**
- No native middleware integration (must run as a separate process or use hooks)
- Configuration via CLI flags and environment variables only
- No built-in web UI for monitoring uploads

### tus-node-server — The Developer-Friendly Option

**tus-node-server** brings TUS to the Node.js ecosystem. It's designed to be embedded directly into Express, Koa, Fastify, or any Node.js web framework.

**Strengths:**
- Seamless integration with existing Node.js applications
- First-class TypeScript support
- Plugin architecture for custom storage backends
- Works alongside your existing Express/Fastify middleware (auth, rate limiting, CORS)
- Active community with regular releases

**Weaknesses:**
- Requires Node.js runtime — more dependencies than a standalone Go binary
- Smaller ecosystem than tusd
- Slightly higher memory usage under heavy concurrent load

### tusdotnet — The .NET Choice

**tusdotnet** is the TUS server implementation for the .NET ecosystem. It integrates as middleware in ASP.NET Core applications.

**Strengths:**
- Native .NET integration — perfect for C# / ASP.NET Core projects
- Configurable via ASP.NET Core's dependency injection system
- Supports local disk and Azure Blob Storage out of the box
- Active maintenance with regular security updates

**Weaknesses:**
- Smallest community of the three implementations
- Fewer storage backend options
- Primarily used in .NET shops — less cross-platform flexibility

## Docker Compose Deployment

### tusd with S3 Backend

```yaml
services:
  tusd:
    image: tusproject/tusd:latest
    container_name: tusd
    ports:
      - "1080:1080"
    environment:
      - AWS_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - TUSD_S3_BUCKET=my-upload-bucket
      - TUSD_S3_ENDPOINT=https://s3.us-east-1.amazonaws.com
      - TUSD_HOOKS_DIR=/etc/tusd/hooks
    volumes:
      - ./hooks:/etc/tusd/hooks:ro
      - /tmp/tus-data:/tmp/tus-data
    restart: unless-stopped
    command: >
      -s3-bucket=my-upload-bucket
      -s3-endpoint=https://s3.us-east-1.amazonaws.com
      -base-path=/files/
      -max-size=10737418240
      -hooks-dir=/etc/tusd/hooks
    networks:
      - upload-net

networks:
  upload-net:
    driver: bridge
```

### tus-node-server with Express

Create a `Dockerfile`:

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY server.js ./
EXPOSE 1080
CMD ["node", "server.js"]
```

And `docker-compose.yml`:

```yaml
services:
  upload-server:
    build: .
    container_name: tus-node-server
    ports:
      - "1080:1080"
    environment:
      - STORAGE_TYPE=s3
      - S3_BUCKET=my-upload-bucket
      - S3_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - MAX_FILE_SIZE=10737418240
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    networks:
      - upload-net

networks:
  upload-net:
    driver: bridge
```

### Reverse Proxy with Caddy

For production deployments, put your TUS server behind a reverse proxy to handle TLS termination, rate limiting, and request routing. Here's a Caddy configuration:

```caddyfile
uploads.example.com {
    reverse_proxy /files/* tusd:1080

    # Increase timeouts for large uploads
    @upload path /files/*
    handle @upload {
        reverse_proxy tusd:1080 {
            flush_interval -1
        }
    }

    # Rate limit uploads
    rate_limit {
        distributed
        zone uploads {
            key {remote_host}
            events 100
            window 1m
        }
    }

    encode gzip
    log {
        output file /var/log/caddy/uploads.log
    }
}
```

## Nginx Configuration for TUS

If you prefer Nginx, configure it to properly handle the long-running PATCH requests that TUS uses:

```nginx
server {
    listen 80;
    server_name uploads.example.com;

    client_max_body_size 0;  # Disable body size limit — TUS handles chunking
    proxy_request_buffering off;  # Stream request body to upstream
    proxy_buffering off;  # Disable response buffering

    location /files/ {
        proxy_pass http://tusd:1080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # TUS uses PATCH for chunk uploads — ensure these are forwarded
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        # Timeout settings for large uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

## Why Self-Host Your Upload Server?

Running your own TUS upload server gives you complete control over how files are stored, processed, and accessed. Instead of relying on third-party upload services that may have data residency requirements, rate limits, or unpredictable pricing, you own the entire pipeline.

**Data sovereignty** is the primary driver. When you host the upload server yourself, files never leave your infrastructure. This is critical for organizations subject to GDPR, HIPAA, or other data protection regulations. You decide where data is stored (local disk, S3-compatible storage, or a specific cloud region), who can access it, and how long it's retained.

**Cost predictability** matters too. Third-party file upload APIs often charge per GB transferred or per API call. At scale, these costs compound quickly. A self-hosted TUS server has a fixed infrastructure cost — the only variable is your storage, which you already budget for.

**Performance and reliability** improve when you eliminate the external dependency. Your TUS server lives on your network, reducing latency for both upload and download. If your application server goes down, uploads can continue independently and be processed when the server recovers.

**Custom processing pipelines** become possible. With tusd's hook system or tus-node-server's middleware, you can trigger virus scanning, thumbnail generation, metadata extraction, or content indexing immediately after each upload completes — all within your own infrastructure.

For organizations managing large file transfers at scale, a self-hosted TUS server is a foundational piece of infrastructure that pays for itself in control and cost savings. For related server infrastructure topics, see our [complete email server setup guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) and [best self-hosted reverse proxy comparison](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/).

## FAQ

### What is the TUS protocol and why should I use it?

TUS is an open-source HTTP-based protocol (RFC 8188) for resumable file uploads. Unlike standard file uploads that must restart from zero if interrupted, TUS uploads are chunked and can resume from the last successfully transferred chunk. This is essential for large file uploads over unreliable networks, mobile connections, or when users need to pause and resume uploads.

### Is the TUS protocol free to use?

Yes, the TUS protocol is completely open-source and free. All official server and client implementations use permissive licenses (MIT, Apache 2.0). There are no licensing fees, usage limits, or vendor lock-in.

### Which TUS server should I choose?

Choose **tusd** if you need a standalone, high-performance server with the most features and storage backends. Choose **tus-node-server** if you're building a Node.js application and want tight integration with your existing Express or Fastify app. Choose **tusdotnet** if your infrastructure is built on .NET / ASP.NET Core.

### Can I use TUS with object storage like S3?

Yes. Both tusd and tus-node-server have native support for AWS S3, Google Cloud Storage, and Azure Blob Storage. You can configure the server to stream uploaded chunks directly to your object storage bucket, eliminating the need for local disk space.

### How do I secure a TUS upload server?

Secure your TUS server with: (1) TLS/HTTPS termination via a reverse proxy (Caddy, Nginx), (2) authentication via tusd hooks or Express middleware, (3) file size limits to prevent abuse, (4) upload expiry to automatically clean up abandoned uploads, and (5) rate limiting at the reverse proxy level. For additional protection, consider adding a WAF layer — see our [WAF comparison guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) for options.

### Does TUS support parallel chunk uploads?

Yes, the TUS protocol supports concurrent uploads. Multiple chunks of the same file can be uploaded simultaneously using the `Upload-Concat` header, significantly speeding up large file transfers on high-bandwidth connections.

### Can TUS handle files larger than 10 GB?

Yes. TUS has no inherent file size limit. The only constraints are your storage backend's limits and your server's disk space. With S3-backed storage, you can handle files of any size supported by S3 (up to 5 TB per object).

### How do I monitor TUS upload progress?

TUS servers expose the current upload offset via HEAD requests. You can poll this endpoint from your frontend to show a progress bar. tusd also supports hook scripts that fire on upload completion, allowing you to trigger notifications, logging, or post-processing pipelines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Resumable File Upload Servers 2026: tusd vs tus-node-server vs tusdotnet (TUS Protocol)",
  "description": "Compare open-source TUS protocol server implementations — tusd, tus-node-server, and tusdotnet — for self-hosted resumable file uploads with Docker deployment guides.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
