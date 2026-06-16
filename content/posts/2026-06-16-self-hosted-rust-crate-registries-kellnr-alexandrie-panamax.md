---
title: "Self-Hosted Rust Crate Registries Compared: Kellnr vs Alexandrie vs Panamax (2026)"
date: "2026-06-16"
tags: ["rust", "crate-registry", "package-management", "devops", "self-hosted", "registry", "open-source"]
draft: false
---

The Rust ecosystem has exploded in recent years, with developers relying on [crates.io](https://crates.io) as the central registry for open-source libraries. But for enterprises, air-gapped environments, and teams that need private crate hosting, a self-hosted Rust crate registry is essential. Private registries give you control over access, audit trails, offline availability, and custom crate policies that the public registry cannot provide.

In this guide, we compare three leading open-source Rust crate registries — **Kellnr**, **Alexandrie**, and **Panamax** — that let you host your own crate storage, manage private packages, and mirror crates.io for offline or controlled environments.

## Why Self-Host Your Rust Crate Registry?

Running your own crate registry offers several advantages over relying solely on the public crates.io. First, you gain **complete control over access** — only authorized team members can publish or download crates, which is critical for proprietary code. Second, a local registry eliminates dependency on external network availability, making builds faster and more reliable.

For air-gapped or restricted-network environments (common in defense, finance, and healthcare), a self-hosted registry is the only way to distribute Rust dependencies. You can mirror the crates you need and serve them internally without any external connectivity.

Third, self-hosted registries provide **audit capabilities** — you can track who published what and when, enforce version policies, and integrate with your CI/CD pipeline for automated crate validation. For teams building safety-critical software, this traceability is non-negotiable.

Finally, as your organization grows, a self-hosted registry scales with you. Unlike crates.io's rate limits and availability constraints, your own registry infrastructure can be sized to match your build frequency and team size.

For similar self-hosted package management solutions, see our [binary repository guide](../2026-04-28-artifactory-oss-vs-nexus-vs-pulp-self-hosted-binary-repository-guide/) and [Debian package repository comparison](../2026-05-02-aptly-vs-reprepro-vs-apt-mirror-self-hosted-debian-package-repository-guide/). If you work across multiple languages, check our [Go module proxy guide](../2026-04-30-athens-vs-goproxy-self-hosted-go-module-proxy-guide-2026/).

## Comparison Table

| Feature | Kellnr | Alexandrie | Panamax |
|---------|--------|------------|---------|
| **Stars** | 1,016 | 516 | 560 |
| **Language** | Rust | Rust | Rust |
| **License** | MIT | MIT | MIT |
| **Private Crates** | Yes (built-in auth) | Yes (token-based) | Read-only mirror |
| **crates.io Mirror** | Yes (proxy mode) | Manual import | Full mirror |
| **Web UI** | Yes (clean dashboard) | Minimal | None (CLI only) |
| **API Compatibility** | Full cargo API | Full cargo API | cargo API (read-only) |
| **Docker Support** | Official image | Community image | Official image |
| **Authentication** | GitLab OAuth, local users | API tokens | N/A (read-only) |
| **Last Updated** | June 2026 | January 2024 | June 2024 |
| **Best For** | Teams needing private + mirror | Lightweight private registry | Offline/air-gapped mirroring |

## Kellnr: The Full-Featured Rust Crate Registry

[Kellnr](https://github.com/kellnr/kellnr) (1,016 stars) is the most actively maintained open-source Rust crate registry. Written in Rust itself, it provides a complete private registry with authentication, a web dashboard, and crates.io proxy capabilities.

Kellnr supports GitLab OAuth integration out of the box, making it easy to integrate with existing identity infrastructure. It also supports local user accounts for simpler deployments. The web UI provides a clean dashboard for browsing crates, managing access, and viewing crate documentation.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kellnr:
    image: ghcr.io/kellnr/kellnr:latest
    container_name: kellnr
    ports:
      - "8000:8000"
    volumes:
      - kellnr_data:/opt/kellnr/data
    environment:
      - KELLNR_ORIGIN=http://localhost:8000
      - KELLNR_REGISTRY_AUTH_REQUIRED=true
      - KELLNR_SESSION_EXPIRY=86400
    restart: unless-stopped

volumes:
  kellnr_data:
```

After starting, configure Cargo to use your local registry:

```toml
# ~/.cargo/config.toml
[registries]
kellnr = { index = "http://localhost:8000/git/index" }

[registry]
default = "kellnr"
```

Kellnr excels in team environments where you need both private crate hosting AND transparent crates.io proxying. Crates not found in your private registry are automatically fetched from crates.io and cached, giving you the best of both worlds.

## Alexandrie: Lightweight and Minimal

[Alexandrie](https://github.com/hirevo/alexandrie) (516 stars) is a lightweight alternative crate registry implemented in Rust. Unlike Kellnr's full dashboard, Alexandrie focuses on being a minimal, efficient registry that "just works" without unnecessary complexity.

Alexandrie uses token-based authentication — administrators generate API tokens for users, which are then used for `cargo publish` and `cargo yank` operations. This model is straightforward and works well for small teams that don't need OAuth integration.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  alexandrie:
    image: ghcr.io/hirevo/alexandrie:latest
    container_name: alexandrie
    ports:
      - "3000:3000"
    volumes:
      - alexandrie_data:/var/lib/alexandrie
      - ./alexandrie.toml:/etc/alexandrie.toml:ro
    environment:
      - RUST_LOG=info
    restart: unless-stopped

volumes:
  alexandrie_data:
```

Configuration via `alexandrie.toml`:

```toml
[general]
addr = "0.0.0.0"
port = 3000

[database]
url = "postgres://alexandrie:password@db/alexandrie"

[storage]
type = "disk"
path = "/var/lib/alexandrie/crates"
```

One notable limitation: Alexandrie's last update was in January 2024, making it the least actively maintained option in this comparison. It works reliably for existing use cases but lacks recent features and security updates that Kellnr benefits from. However, for teams that value simplicity and don't need a web UI, Alexandrie remains a solid choice.

## Panamax: Offline Mirror for Air-Gapped Environments

[Panamax](https://github.com/panamax-rs/panamax) (560 stars) takes a different approach — it is a **read-only mirror** of rustup and crates.io, designed specifically for offline and air-gapped environments. If you work in an environment with no internet access, Panamax lets you replicate the entire Rust ecosystem locally.

Panamax mirrors both the Rust toolchain (via rustup) and the crate registry (via crates.io), creating a fully self-contained Rust development environment. This is invaluable for defense contractors, financial institutions, and any organization with strict network isolation requirements.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  panamax:
    image: ghcr.io/panamax-rs/panamax:latest
    container_name: panamax
    ports:
      - "8080:8080"
    volumes:
      - panamax_data:/data
    command:
      - "mirror"
      - "--base-dir=/data"
      - "--listen=0.0.0.0:8080"

volumes:
  panamax_data:
```

Initial mirror synchronization (run once on a connected machine):

```bash
# Mirror crates.io (full sync — can take hours for complete mirror)
panamax mirror crates-io --base-dir=/data

# Mirror Rust toolchains
panamax mirror rustup --base-dir=/data

# Serve the mirror
panamax serve --base-dir=/data --listen=0.0.0.0:8080
```

Configure Cargo on air-gapped machines:

```toml
[source.crates-io]
replace-with = "panamax"

[source.panamax]
registry = "http://panamax-server:8080/crates.io"
```

Unlike Kellnr, Panamax does not support private crate uploads — it is purely a mirroring tool. But for its specific use case (offline Rust development), it is the gold standard. Pair it with Kellnr for a hybrid setup: Panamax mirrors crates.io into your network, and Kellnr hosts your private crates.

## Deployment Architecture and Network Considerations

When deploying a Rust crate registry in production, consider a reverse proxy in front for TLS termination and access control. Here is a minimal Nginx configuration for Kellnr:

```nginx
server {
    listen 443 ssl;
    server_name crates.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/crates.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crates.yourcompany.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

For high-availability deployments, consider running multiple Kellnr instances behind a load balancer with shared storage (NFS or object storage) for crate data. The PostgreSQL database used by both Kellnr and Alexandrie should also be configured with replication for production environments.

## Choosing the Right Crate Registry

Your choice depends primarily on your use case:

- **Kellnr** is the best all-around option for teams that need private crate hosting, a web UI, GitLab OAuth, AND transparent crates.io proxying. Its active development (updated June 2026) makes it the safest long-term investment.

- **Alexandrie** is ideal for small teams or individual developers who want a minimal, no-frills private registry. Its token-based auth is simple to set up, and the lightweight design means fewer resources consumed.

- **Panamax** is the only choice for air-gapped environments where you need a complete offline mirror of both rustup and crates.io. It pairs well with Kellnr for hybrid setups.

Consider combining tools: use Panamax to pull crates.io into your isolated network, and Kellnr to host your private crates alongside the mirrored public ones. This gives you the best of both worlds without sacrificing security or convenience.

## FAQ

### What is a Rust crate registry and why do I need one?

A Rust crate registry is a server that stores and distributes Rust packages (crates). The default public registry is crates.io. You need a self-hosted registry when you want to publish private/proprietary crates, work in air-gapped environments, mirror crates.io for faster builds, or enforce organization-specific policies on crate usage.

### Can I use Kellnr as a complete crates.io replacement?

Yes and no. Kellnr can proxy requests to crates.io, so crates not found locally are fetched from the public registry and cached. This means you can configure Cargo to only talk to Kellnr — it will serve your private crates directly and fetch public crates on demand. However, it does not mirror the entire crates.io index by itself (that is Panamax"s job).

### How do I migrate crates from crates.io to my private registry?

For Kellnr or Alexandrie, you download the crate from crates.io using `cargo download <crate-name>`, then republish it to your private registry using `cargo publish --registry <your-registry>`. For Panamax, the mirror command handles this automatically for all crates.

### What are the storage requirements for a crate registry?

A full crates.io mirror (Panamax) requires approximately 150-200 GB of storage and grows with each sync. A private registry (Kellnr or Alexandrie) starts small — typically under 1 GB for moderate usage — and grows based on how many private crates you publish. Both Kellnr and Alexandrie support PostgreSQL for metadata and disk storage for crate files, with configurable retention policies.

### Is there a performance impact compared to using crates.io directly?

A local registry is actually faster than crates.io for crate downloads because network latency is eliminated. Builds that previously took 30-60 seconds for dependency resolution can complete in under 5 seconds with a local registry. The initial crate download is also faster since it comes from your local network rather than the public internet.

### Can I run multiple registries on the same server?

Yes. Kellnr, Alexandrie, and Panamax all expose HTTP APIs on configurable ports. You can run Kellnr on port 8000 for private crates and Panamax on port 8080 for crates.io mirroring on the same machine. Configure Cargo with both registries in your `.cargo/config.toml` file.

### Do these registries support crate signing or verification?

Currently, none of the three tools natively support cryptographic crate signing (that feature is still evolving in the broader Rust ecosystem). However, you can implement verification at the CI/CD level — run `cargo audit`, `cargo deny`, and custom linting on all crates before allowing them into your registry. Kellnr's webhook support makes this integration straightforward.

### How do I handle registry backups?

All three tools store crate files on disk. Back up the data directory (`/opt/kellnr/data`, `/var/lib/alexandrie`, or Panamax's `/data`) along with the PostgreSQL database. A simple cron job with `rsync` or `restic` handles this. Since crate versions are immutable, incremental backups are efficient — only new crate versions consume storage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Rust Crate Registries Compared: Kellnr vs Alexandrie vs Panamax (2026)",
  "description": "Comprehensive comparison of self-hosted Rust crate registries: Kellnr, Alexandrie, and Panamax. Learn which open-source registry fits your team with Docker Compose examples, comparison tables, and deployment guides.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
