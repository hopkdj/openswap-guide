---
title: "Aptly vs Reprepro vs Apt-mirror: Self-Hosted Debian Package Repository Management 2026"
date: 2026-05-02T11:00:00+00:00
draft: false
tags: ["debian", "ubuntu", "package-manager", "apt", "self-hosted", "repository"]
---

Managing Debian and Ubuntu packages across multiple servers requires a reliable, self-hosted package repository. Whether you need to distribute custom-built `.deb` files, mirror upstream repositories for offline access, or maintain a stable snapshot of package versions for reproducible deployments, a self-hosted apt repository gives you full control over your software supply chain.

In this guide, we compare three established tools for managing Debian package repositories: **Aptly**, **Reprepro**, and **Apt-mirror**. Each serves a different use case — from full-featured repository publishing to simple upstream mirroring.

## Why Self-Host a Package Repository?

Organizations running Debian or Ubuntu systems benefit from a local package repository for several reasons:

- **Bandwidth savings** — download packages once from upstream, serve locally to hundreds of servers
- **Air-gapped deployments** — maintain package access for systems without internet connectivity
- **Version pinning** — freeze package versions for compliance and reproducibility requirements
- **Custom packages** — distribute internally-built `.deb` packages alongside upstream software
- **Security** — verify and sign packages before distribution, controlling exactly what reaches your servers
- **Snapshot capability** — roll back to a known-good repository state after a bad update

For teams managing infrastructure at scale, a local repository is not a luxury — it's a necessity. The question is which tool best fits your workflow.

## Quick Comparison Table

| Feature | Aptly | Reprepro | Apt-mirror |
|---|---|---|---|
| **Type** | Full repository manager | Repository publisher | Upstream mirror |
| **Language** | Go | C | Perl |
| **Web UI** | No (REST API) | No | No |
| **Custom packages** | Yes | Yes | No (mirror only) |
| **Snapshot support** | Yes (point-in-time) | No | No |
| **Mirror upstream** | Yes | Partial | Yes (primary use case) |
| **GPG signing** | Yes | Yes | No |
| **Docker image** | Official | Community | Community |
| **Best For** | Full lifecycle management | Simple publishing | Bandwidth-saving mirrors |

## Aptly — Full Repository Lifecycle Management

**Aptly** is the most feature-complete Debian repository manager available. Written in Go, it handles the entire package repository lifecycle: mirroring upstream repos, importing custom packages, creating snapshots, and publishing signed repositories.

### Key Features

- **Snapshot management** — create point-in-time snapshots of any repository state and publish them independently
- **Flexible filtering** — create filtered repository views by package name, version, architecture, or dependency constraints
- **Multi-architecture support** — manage amd64, arm64, armhf, and other architectures from a single repository
- **GPG signing** — sign published repositories for client verification
- **REST API** — automate all operations through a JSON API
- **S3 and filesystem publishing** — publish repositories to local filesystem, Amazon S3, or Swift object storage
- **Incremental updates** — efficiently sync mirrors by downloading only changed packages

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  aptly:
    image: aptly/aptly:latest
    container_name: aptly
    volumes:
      - ./data:/srv/aptly
      - ./gpg:/root/.gnupg
    ports:
      - 8080:8080
    command: ["serve", "-listen=:8080", "-rootPath=/srv/aptly"]
    restart: unless-stopped
```

### Typical Workflow

```bash
# 1. Create a mirror of Debian stable
aptly mirror create -architectures=amd64,arm64 \
  -filter='Priority (required,important)' \
  debian-stable http://deb.debian.org/debian bookworm main

# 2. Update the mirror
aptly mirror update debian-stable

# 3. Create a local repository for custom packages
aptly repo create -distribution=internal -component=main my-packages

# 4. Import custom .deb files
aptly repo add my-packages /tmp/custom-package_1.0_amd64.deb

# 5. Create a snapshot
aptly snapshot create stable-snap-$(date +%Y%m%d) from mirror debian-stable

# 6. Merge snapshots with custom packages
aptly snapshot merge combined stable-snap-20260502 my-packages

# 7. Publish the merged snapshot
aptly publish snapshot -gpg-sign=YOUR_KEY_ID \
  -distribution=bookworm \
  combined filesystem:public:debian
```

The snapshot workflow is Aptly's killer feature. You can publish a snapshot, continue updating mirrors, and switch clients to a new snapshot at your convenience — enabling zero-downtime repository updates and instant rollback capability.

## Reprepro — Simple and Reliable Repository Publisher

**Reprepro** is the traditional Debian repository management tool, written in C and maintained by Debian developers. It focuses on one thing: creating and maintaining apt repository directories from a set of `.deb` packages.

### Key Features

- **Battle-tested** — used by Debian and Ubuntu infrastructure teams for years
- **Simple data model** — manages distributions, components, and packages with straightforward commands
- **Built-in GPG support** — signs Releases files automatically
- **Pull-based updates** — automatically resolve and include dependencies when adding packages
- **Multiple distribution support** — manage stable, testing, and unstable branches simultaneously
- **Efficient storage** — uses hard links to avoid duplicating package files across distributions

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  reprepro:
    image: debian:bookworm-slim
    container_name: reprepro
    volumes:
      - ./repo:/repo
      - ./gpg:/root/.gnupg
      - ./packages:/incoming
    command: ["bash", "-c", "apt-get update && apt-get install -y reprepro && sleep infinity"]
    restart: unless-stopped
```

### Configuration and Usage

Reprepro uses a `conf/distributions` file to define repository structure:

```
Origin: MyRepo
Label: My Internal Repository
Codename: bookworm
Architectures: amd64 arm64
Components: main contrib
Description: Internal package repository
SignWith: YOUR_KEY_ID
```

```bash
# Add a package (auto-resolves dependencies)
reprepro -b /repo includedeb bookworm /incoming/my-package_1.0_amd64.deb

# List all packages in a distribution
reprepro -b /repo list bookworm

# Remove a package
reprepro -b /repo remove bookworm my-package

# Export the repository (regenerates Packages and Release files)
reprepro -b /repo export
```

Serve the `/repo` directory with Nginx:

```nginx
server {
    listen 80;
    server_name repo.internal;
    root /repo;

    location / {
        autoindex on;
        types {
            application/octet-stream deb;
            application/octet-stream udeb;
            application/octet-stream dsc;
            application/octet-stream tar.gz;
        }
    }
}
```

Reprepro does not mirror upstream repositories — it only manages packages you explicitly add. For mirroring, pair it with Apt-mirror or use Aptly instead.

## Apt-mirror — Upstream Repository Mirroring

**Apt-mirror** is a specialized tool for creating exact local copies of upstream Debian and Ubuntu repositories. It downloads all packages, metadata, and indexes from the source repository, making them available locally.

### Key Features

- **Exact mirroring** — creates a byte-for-byte local copy of upstream repositories
- **Incremental sync** — only downloads new or changed packages on subsequent runs
- **Multiple architectures** — mirror packages for different CPU architectures
- **Multiple releases** — mirror multiple Debian/Ubuntu versions simultaneously
- **Automated via cron** — designed to run on a schedule for continuous synchronization
- **Low overhead** — uses rsync-like efficiency for incremental updates

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  apt-mirror:
    image: ubuntu:24.04
    container_name: apt-mirror
    volumes:
      - ./mirror:/mirror
      - ./mirror.list:/etc/apt/mirror.list:ro
      - ./cron:/etc/cron.d
    command: ["bash", "-c", "apt-get update && apt-get install -y apt-mirror && sleep infinity"]
    restart: unless-stopped
```

### Configuration

Configure `/etc/apt/mirror.list`:

```
set base_path    /mirror
set mirror_path  $base_path/mirror
set skel_path    $base_path/skel
set var_path     $base_path/var
set defaultarch  amd64

# Debian Bookworm
deb http://deb.debian.org/debian bookworm main contrib non-free
deb http://deb.debian.org/debian bookworm-updates main contrib non-free
deb http://security.debian.org bookworm-security main contrib non-free

# Ubuntu Noble
deb http://archive.ubuntu.com/ubuntu noble main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu noble-security main restricted universe multiverse

clean http://deb.debian.org/debian
clean http://archive.ubuntu.com/ubuntu
```

Run the mirror:

```bash
# Initial full mirror (downloads everything)
apt-mirror /etc/apt/mirror.list

# Subsequent runs only download changes
apt-mirror /etc/apt/mirror.list

# Clean up obsolete packages
apt-mirror --clean /etc/apt/mirror.list
```

Apt-mirror creates a directory structure that can be served directly via HTTP:

```bash
# Nginx configuration
server {
    listen 80;
    server_name mirror.internal;
    root /mirror/mirror;

    location / {
        autoindex on;
    }
}
```

Clients then point to `http://mirror.internal/debian` or `http://mirror.internal/archive.ubuntu.com/ubuntu` in their `/etc/apt/sources.list`.

## Performance and Storage Comparison

| Metric | Aptly | Reprepro | Apt-mirror |
|---|---|---|---|
| **Initial mirror (full Debian stable)** | ~50 GB | N/A (no mirroring) | ~50 GB |
| **Storage efficiency** | Good (dedup via snapshots) | Excellent (hard links) | Fair (full mirror) |
| **Sync speed (incremental)** | Fast (API-driven) | N/A | Fast (rsync-based) |
| **Memory usage** | ~200 MB | ~50 MB | ~100 MB |
| **Setup complexity** | Moderate | Low | Low |
| **Maintenance effort** | Low | Low | Low |

For pure mirroring, Apt-mirror and Aptly are comparable in storage requirements. Aptly's snapshot feature adds ~10-20% overhead per snapshot but provides rollback capability that the other tools lack.

## Combining Tools in Production

In real-world deployments, organizations often combine these tools:

1. **Apt-mirror** syncs upstream repositories to a local mirror for bandwidth savings
2. **Aptly** imports the mirrored packages, adds custom `.deb` files, and creates snapshots
3. **Reprepro** publishes the final repository to internal servers (optional, if you prefer its simpler model)

A common pattern is to use Aptly for everything — it mirrors, manages custom packages, snapshots, and publishes in a single tool. This reduces operational complexity compared to maintaining multiple tools.

## Why Self-Host Your Package Repository?

Running your own package repository is foundational infrastructure for any organization using Debian or Ubuntu at scale. It eliminates dependency on external mirrors that can be slow, unreliable, or blocked by network policies. For compliance-driven environments, it provides an auditable, version-controlled software supply chain.

A local repository pairs naturally with other self-hosted infrastructure tools. If you manage binary artifacts beyond Debian packages, our [binary repository comparison](../2026-04-28-artifactory-oss-vs-nexus-vs-pulp-self-hosted-binary-repository-guide/) covers Nexus, Artifactory OSS, and Pulp. For Python-specific needs, our [PyPI mirror guide](../pypiserver-vs-devpi-vs-bandersnatch-self-hosted-pypi-mirror-guide-2026/) covers self-hosted Python package management. And for broader package ecosystem coverage, our [general package registry guide](../self-hosted-package-registry-nexus-verdaccio-pulp-guide-2026/) includes npm, Maven, and Docker registries.

## FAQ

### What is the difference between Aptly, Reprepro, and Apt-mirror?

Aptly is a full repository lifecycle manager that mirrors, manages custom packages, creates snapshots, and publishes repositories. Reprepro is a repository publisher that creates apt repository directories from packages you explicitly add — it does not mirror upstream repos. Apt-mirror is a dedicated upstream mirroring tool that creates local copies of Debian/Ubuntu repositories but cannot manage custom packages.

### Can I use these tools with Ubuntu repositories?

Yes. All three tools support Ubuntu repositories alongside Debian. Configure the appropriate Ubuntu mirror URLs (archive.ubuntu.com or security.ubuntu.com) and the tools handle the repository format identically.

### How much storage do I need for a full Debian mirror?

A full Debian stable mirror with main, contrib, and non-free components for amd64 requires approximately 50-60 GB. Adding arm64 and other architectures increases this proportionally. Using Apt-mirror's clean feature removes obsolete packages automatically.

### Can Aptly replace both Reprepro and Apt-mirror?

Yes. Aptly can mirror upstream repositories (replacing Apt-mirror) and publish custom package repositories (replacing Reprepro). Its snapshot feature adds capabilities neither of the other tools provides.

### How do I serve the repository to client machines?

Serve the published directory via any HTTP server (Nginx, Apache, Caddy). Clients add the repository to `/etc/apt/sources.list` pointing to your server URL. For HTTPS, place a reverse proxy with TLS termination in front of the HTTP server.

### Is GPG signing required?

GPG signing is not strictly required but strongly recommended. Clients can be configured to accept unsigned repositories, but signing provides verification that packages haven't been tampered with during transit or storage.

### How often should I update my mirror?

For security updates, daily synchronization is recommended. For full repository mirrors, weekly updates are sufficient. Configure a cron job to run `apt-mirror` or `aptly mirror update` on your preferred schedule.

### Can I mirror only specific packages, not the entire repository?

Aptly supports filtering during mirror creation (by priority, section, architecture, or package name). Apt-mirror mirrors entire suites — you cannot filter individual packages. Reprepro only manages packages you explicitly add, so it is inherently filtered.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Aptly vs Reprepro vs Apt-mirror: Self-Hosted Debian Package Repository Management 2026",
  "description": "Compare Aptly, Reprepro, and Apt-mirror for managing self-hosted Debian and Ubuntu package repositories. Includes Docker Compose configs, workflow examples, and production deployment patterns.",
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
