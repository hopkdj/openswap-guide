---
title: "Self-Hosted Git LFS Storage: Gitea vs Forgejo vs GitLab CE — Complete Guide 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "git", "storage", "devops"]
draft: false
description: "Compare self-hosted Git LFS storage solutions — Gitea, Forgejo, and GitLab CE. Complete guide with Docker Compose configs, S3 backend setup, migration strategies, and best practices for managing large files in Git repositories."
---

Git was designed for source code — small text files that compress well and diff cleanly. But modern development involves binary artifacts: compiled binaries, machine learning models, design assets, video files, and datasets. Committing these directly to Git bloats your repository and degrades performance.

[Git Large File Storage (LFS)](https://git-lfs.com/) solves this by replacing large files with lightweight pointer files in your repository while storing the actual content on a separate server. The challenge: **where do you host that LFS server?** Public services like GitHub impose storage limits and bandwidth quotas. For teams with large binary assets, self-hosting your LFS server is the most cost-effective and privacy-preserving option.

This guide compares three leading open-source platforms with built-in Git LFS support: **[gitea](https://gitea.io/)**, **Forgejo**, and **GitLab CE**. We cover installation, storage backends, [docker](https://www.docker.com/) Compose configurations, and migration strategies so you can choose the right LFS solution for your infrastructure.

## Why Self-Host Git LFS?

Running your own LFS server instead of relying on GitHub or GitLab.com offers several advantages:

- **No storage limits.** GitHub's free tier caps LFS at 1 GB. Self-hosted storage is limited only by your disk space.
- **No bandwidth charges.** Every `git lfs pull` and `git lfs push` consumes bandwidth. On self-hosted infrastructure, this traffic stays on your network.
- **Data sovereignty.** Binary assets — proprietary datasets, compiled firmware, design files — never leave your infrastructure.
- **Cost predictability.** GitHub charges $5/month per 50 GB of LFS storage and $5/month per 50 GB of bandwidth. Self-hosting on a single server with a 2 TB drive costs a fraction of that.
- **Faster clones.** When the LFS server is on the same network as your CI runners and developer workstations, large file downloads are significantly faster.
- **Custom retention policies.** Set your own rules for how long LFS objects are kept, when unused files are pruned, and who can access them.

For teams working with game assets, ML models, CAD files, or any binary-heavy project, self-hosted LFS pays for itself quickly.

## Project Overview and Live Stats

Here's how the three platforms compare as of April 2026, based on live GitHub data:

| Feature | Gitea | Forgejo | GitLab CE |
|---------|-------|---------|-----------|
| **GitHub Stars** | 54,998 | N/A (Codeberg-hosted) | 24,311 |
| **Last Updated** | 2026-04-20 | Active (Codeberg) | 2026-04-20 |
| **Language** | Go | Go | Ruby |
| **LFS Protocol** | Native LFS API | Native LFS API | Native LFS API |
| **Storag[minio](https://min.io/)kends** | Local disk, MinIO/S3 | Local disk, MinIO/S3 | Local disk, S3, GCS |
| **LFS Locking** | Yes | Yes | Yes |
| **LFS Object Pruning** | Manual (admin API) | Manual (admin API) | Built-in admin UI |
| **Docker Image** | `gitea/gitea` | `codeberg/forgejo` | `gitlab/gitlab-ce` |
| **RAM (minimum)** | 512 MB | 512 MB | 4 GB |
| **Best For** | Small teams, homelabs | Community-driven projects | Enterprise, large teams |

Gitea and Forgejo share a common codebase (Forgejo is a hard fork of Gitea created in 2022), so their LFS implementations are nearly identical. GitLab CE takes a different architectural approach with a more comprehensive — but heavier — LFS system.

## Option 1: Gitea — Lightweight Git LFS Server

[Gitea](https://gitea.io) is the most popular lightweight self-hosted Git platform. Its LFS implementation is straightforward: configure a storage backend, enable LFS in the config, and it works.

### Architecture

Gitea stores LFS objects in one of two ways:

- **Local filesystem** — objects stored under `[LFS].PATH` in a directory structure organized by OID
- **S3-compatible storage** — MinIO, AWS S3, Cloudflare R2, or any S3-compatible endpoint

Pointer files (`.gitattributes` entries) reference LFS objects by their SHA-256 hash (OID). When a developer pushes, Gitea receives the LFS objects, validates the OID, and stores them in the configured backend. On clone or pull, Gitea serves the objects back via its built-in LFS HTTP API.

### Docker Compose Setup

This configuration deploys Gitea with PostgreSQL and MinIO as the LFS storage backend:

```yaml
# docker-compose.yml — Gitea with S3-backed LFS
version: "3.8"

services:
  gitea:
    image: gitea/gitea:1.23
    container_name: gitea
    restart: unless-stopped
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=db:5432
      - GITEA__database__NAME=gitea
      - GITEA__database__USER=gitea
      - GITEA__database__PASSWD=gitea_password
      - GITEA__server__DOMAIN=lfs.example.com
      - GITEA__server__ROOT_URL=https://lfs.example.com
      - GITEA__lfs__ENABLED=true
      - GITEA__lfs__STORAGE_TYPE=minio
      - GITEA__lfs__MINIO_ENDPOINT=minio:9000
      - GITEA__lfs__MINIO_BUCKET=gitea-lfs
      - GITEA__lfs__MINIO_ACCESS_KEY_ID=minioadmin
      - GITEA__lfs__MINIO_SECRET_ACCESS_KEY=minioadmin
      - GITEA__lfs__MINIO_USE_SSL=false
      - GITEA__lfs__SERVE_DIRECT=true
    ports:
      - "3000:3000"
      - "2222:22"
    volumes:
      - gitea-data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    depends_on:
      - db
      - minio

  db:
    image: postgres:16-alpine
    container_name: gitea-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=gitea
      - POSTGRES_PASSWORD=gitea_password
      - POSTGRES_DB=gitea
    volumes:
      - gitea-db:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    container_name: gitea-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

volumes:
  gitea-data:
  gitea-db:
  minio-data:
```

Key configuration notes:

- `GITEA__lfs__SERVE_DIRECT=true` tells Gitea to generate pre-signed S3 URLs so clients download LFS objects directly from MinIO, bypassing the Gitea proxy. This is essential for performance with large files.
- `GITEA__lfs__MINIO_USE_SSL=false` is correct for internal Docker networks. Set to `true` if MinIO is behind TLS termination.
- The MinIO bucket `gitea-lfs` is created automatically on first use.

### Enabling LFS on a Repository

After deployment, LFS is enabled globally in Gitea's admin settings. Individual repositories must also opt in:

```bash
# In your local repository
git lfs install
git lfs track "*.bin" "*.zip" "*.png" "*.psd" "*.mlmodel"
git add .gitattributes
git commit -m "Add LFS tracking for binary files"
git push origin main
```

## Option 2: Forgejo — Community-Driven LFS Fork

[Forgejo](https://forgejo.org) is a community-driven hard fork of Gitea, created in response to Gitea Ltd's commercialization decisions. Since LFS is a core Git feature rather than a commercial add-on, Forgejo's LFS implementation closely mirrors Gitea's — with a few enhancements.

### Forgejo-Specific LFS Enhancements

- **Active community governance.** Forgejo's development is steered by a community assembly, not a single company. LFS feature requests are prioritized based on community voting.
- **Compatibility guarantees.** Forgejo maintains API compatibility with Gitea, so existing Gitea LFS clients work without modification.
- **Faster release cadence.** Forgejo has maintained a consistent release schedule with security patches and feature updates.

### Docker Compose Setup

Forgejo's deployment is nearly identical to Gitea — just swap the image and adjust the domain:

```yaml
# docker-compose.yml — Forgejo with MinIO-backed LFS
version: "3.8"

services:
  forgejo:
    image: codeberg/forgejo:10
    container_name: forgejo
    restart: unless-stopped
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - FORGEJO__database__DB_TYPE=postgres
      - FORGEJO__database__HOST=db:5432
      - FORGEJO__database__NAME=forgejo
      - FORGEJO__database__USER=forgejo
      - FORGEJO__database__PASSWD=forgejo_password
      - FORGEJO__server__DOMAIN=lfs.forgejo.local
      - FORGEJO__server__ROOT_URL=https://lfs.forgejo.local
      - FORGEJO__lfs__ENABLED=true
      - FORGEJO__lfs__STORAGE_TYPE=minio
      - FORGEJO__lfs__MINIO_ENDPOINT=minio:9000
      - FORGEJO__lfs__MINIO_BUCKET=forgejo-lfs
      - FORGEJO__lfs__MINIO_ACCESS_KEY_ID=minioadmin
      - FORGEJO__lfs__MINIO_SECRET_ACCESS_KEY=minioadmin
      - FORGEJO__lfs__SERVE_DIRECT=true
    ports:
      - "3000:3000"
      - "2222:22"
    volumes:
      - forgejo-data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    depends_on:
      - db
      - minio

  db:
    image: postgres:16-alpine
    container_name: forgejo-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=forgejo
      - POSTGRES_PASSWORD=forgejo_password
      - POSTGRES_DB=forgejo
    volumes:
      - forgejo-db:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    container_name: forgejo-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio-data:/data

volumes:
  forgejo-data:
  forgejo-db:
  minio-data:
```

The environment variable prefix changes from `GITEA__` to `FORGEJO__`, but the LFS-specific keys remain identical. This makes migration between Gitea and Forgejo straightforward.

## Option 3: GitLab CE — Enterprise-Grade LFS

[GitLab Community Edition](https://about.gitlab.com/install/) offers the most feature-complete LFS implementation of the three. Its LFS system integrates with GitLab's CI/CD, package registry, and object storage framework.

### GitLab LFS Architecture

GitLab's LFS system stores objects in configurable object storage and tracks metadata in PostgreSQL. Key features that distinguish it from Gitea/Forgejo:

- **LFS object storage per-project.** LFS objects can be routed to different storage backends based on project settings.
- **Built-in LFS object administration.** The admin UI shows LFS object counts, storage usage per-project, and provides cleanup tools.
- **LFS batch API.** GitLab's LFS server supports the batch transfer API, allowing clients to request multiple objects in a single HTTP call.
- **CI/CD LFS integration.** GitLab CI runners automatically handle LFS objects during pipeline execution without additional configuration.
- **LFS file locking.** Developers can lock LFS-tracked files to prevent merge conflicts on binary assets.

### Docker Compose Setup (Omnibus)

GitLab CE uses the Omnibus package, which bundles all components into a single container. The official Docker image handles LFS configuration through `gitlab.rb`:

```yaml
# docker-compose.yml — GitLab CE with external S3 LFS storage
version: "3.8"

services:
  gitlab:
    image: gitlab/gitlab-ce:17.10
    container_name: gitlab
    restart: unless-stopped
    hostname: gitlab.example.com
    environment:
      - GITLAB_OMNIBUS_CONFIG=|
        external_url 'https://gitlab.example.com'
        gitlab_rails['lfs_enabled'] = true
        gitlab_rails['lfs_object_store_enabled'] = true
        gitlab_rails['lfs_object_store_remote_directory'] = "gitlab-lfs"
        gitlab_rails['lfs_object_store_connection'] = {
          'provider' => 'AWS',
          'region' => 'us-east-1',
          'aws_access_key_id' => 'minioadmin',
          'aws_secret_access_key' => 'minioadmin',
          'endpoint' => 'http://minio:9000',
          'path_style' => true
        }
        gitlab_rails['lfs_object_store_proxy_download'] = false
        postgresql['enable'] = true
        redis['enable'] = true
    ports:
      - "80:80"
      - "443:443"
      - "2222:22"
    volumes:
      - gitlab-config:/etc/gitlab
      - gitlab-logs:/var/log/gitlab
      - gitlab-data:/var/opt/gitlab
    shm_size: '256m'

  minio:
    image: minio/minio:latest
    container_name: gitlab-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"

volumes:
  gitlab-config:
  gitlab-logs:
  gitlab-data:
  minio-data:
```

Important notes:

- `path_style: true` is required for MinIO (S3 path-style addressing vs virtual-hosted style).
- `lfs_object_store_proxy_download: false` means LFS objects are served directly from S3. Set to `true` if GitLab should proxy downloads (useful when S3 is not publicly accessible).
- GitLab CE requires at least 4 GB RAM and benefits from 8 GB+. The Omnibus package bundles PostgreSQL, Redis, Puma, Sidekiq, and other services.

## Comparison: LFS Capabilities Side by Side

| Capability | Gitea | Forgejo | GitLab CE |
|------------|-------|---------|-----------|
| **LFS enabled by default** | Yes (config flag) | Yes (config flag) | Yes |
| **S3/MinIO backend** | Yes | Yes | Yes |
| **Direct S3 downloads** | Yes (`SERVE_DIRECT`) | Yes (`SERVE_DIRECT`) | Yes (`proxy_download: false`) |
| **LFS file locking** | Yes | Yes | Yes |
| **LFS object admin UI** | Basic (admin panel) | Basic (admin panel) | Full (storage analytics) |
| **LFS object pruning** | Admin API only | Admin API only | Admin UI + scheduled jobs |
| **LFS batch API** | Yes | Yes | Yes |
| **LFS transfer quota** | No | No | Per-group limits |
| **LFS audit logging** | Basic | Basic | Comprehensive |
| **LFS migration tool** | Manual | Manual | Built-in (import from GitHub) |
| **Resource requirements** | Low (512 MB) | Low (512 MB) | High (4 GB+) |

## LFS Storage Backend Comparison: Local vs S3

Regardless of which platform you choose, you need to decide where LFS objects are stored:

### Local Filesystem

- **Pros:** Simple setup, no additional infrastructure, fastest for small deployments
- **Cons:** No horizontal scaling, harder to back up, single point of failure
- **Best for:** Homelabs, single-server deployments, teams under 10 users

```ini
# Gitea/Forgejo: local LFS storage (in app.ini)
[lfs]
ENABLED = true
PATH   = /data/git/lfs
```

### S3-Compatible Object Storage (MinIO, R2, S3)

- **Pros:** Horizontally scalable, built-in redundancy, easy backup/replication, works with CDN
- **Cons:** Additional infrastructure to manage, network latency for small files
- **Best for:** Production deployments, teams with large binary assets, multi-server setups

## Migrating LFS Objects Between Platforms

If you're moving from GitHub or between self-hosted platforms, here's the migration workflow:

### Step 1: Clone with LFS objects

```bash
# Clone the repository including all LFS objects
git lfs install
git clone --mirror git@github.com:org/repo.git
cd repo.git
git lfs fetch --all
```

### Step 2: Push to the new server

```bash
# Push the mirror to your self-hosted platform
git push --mirror https://lfs.example.com/org/repo.git

# The LFS objects are pushed automatically during the mirror push
# Verify with:
git lfs ls-files --all | wc -l
```

### Step 3: Verify LFS integrity

```bash
# On the new server, verify all LFS objects are accessible
git lfs fsck --all

# Check storage usage on the server
# For Gitea/Forgejo: check the LFS directory or MinIO bucket
# For GitLab CE: Admin Area → Monitoring → Storage
```

## Performance Tuning for Large LFS Repositories

For repositories with thousands of LFS objects or multi-gigabyte files:

1. **Use direct S3 serving.** Both `SERVE_DIRECT=true` (Gitea/Forgejo) and `proxy_download: false` (GitLab) bypass the application server for downloads, dramatically improving throughput.

2. **Configure connection pooling.** PostgreSQL connection limits should be set to accommodate concurrent LFS transfers:
   ```ini
   # Gitea/Forgejo app.ini
   [database]
   MAX_OPEN_CONNS = 100
   ```

3. **Set appropriate timeouts.** Large file uploads can take minutes. Configure your reverse proxy accordingly:
   ```nginx
   # Nginx configuration for LFS uploads
   client_max_body_size 0;  # unlimited
   proxy_read_timeout 600s;
   proxy_send_timeout 600s;
   ```

4. **Enable LFS object caching.** Place a CDN or reverse proxy cache in front of your LFS endpoint for frequently-downloaded objects.

5. **Regular cleanup.** Prune unreachable LFS objects periodically:
   ```bash
   # In your repository
   git lfs prune --verbose
   ```

## Which Should You Choose?

**Choose Gitea if:** You want a lightweight, battle-tested platform with minimal resource requirements. Gitea's LFS implementation is simple, reliable, and well-documented. It runs comfortably on a Raspberry Pi 4 and handles thousands of repositories without issue. For related CI/CD setup, see our [Woodpecker CI vs Drone CI vs Gitea Actions guide](../woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/) which covers integrating pipelines with Gitea.

**Choose Forgejo if:** You want Gitea's functionality but prefer community governance over corporate control. Forgejo's LFS is API-compatible with Gitea, making it a drop-in replacement for existing deployments. If you're also managing GitOps workflows, our [ArgoCD vs Flux guide](../argocd-vs-flux-self-hosted-gitops-guide/) covers deployment strategies that complement your version control infrastructure.

**Choose GitLab CE if:** You need enterprise features like per-project LFS quotas, comprehensive audit logging, built-in migration tools, and tight CI/CD integration. The trade-off is significantly higher resource consumption — plan for at least 4 GB RAM and a multi-core CPU.

For teams concerned about keeping binary secrets out of version control, our [secrets scanning guide](../self-hosted-secrets-scanning-gitleaks-trufflehog-detect-secrets-guide-2026/) covers complementary tools to ensure LFS-stacked binaries don't accidentally contain credentials.

## FAQ

### What is Git LFS and why can't I just commit large files directly to Git?

Git LFS (Large File Storage) replaces large files in your repository with lightweight text pointers. The actual file content is stored on a separate LFS server and downloaded on demand. Committing large binary files directly to Git causes your repository to grow unboundedly — every clone downloads the entire history of every binary file. LFS keeps repository clones fast while still versioning your binary assets.

### How much disk space do I need for a self-hosted LFS server?

It depends on your project. A single ML model can be 1-10 GB. Game asset repositories often exceed 50 GB. As a rule of thumb, plan for 3x your current binary asset size: 1x for the current objects, 1x for historical versions (LFS keeps old objects even after `git lfs prune` on the client), and 1x for growth buffer. Start with a 500 GB drive and expand as needed.

### Can I use Cloudflare R2 instead of MinIO for LFS storage?

Yes. R2 is S3-compatible and works as an LFS backend for all three platforms. For Gitea and Forgejo, set `STORAGE_TYPE=minio` and point `MINIO_ENDPOINT` to your R2 endpoint URL. For GitLab CE, use the same S3 connection configuration with R2's endpoint. R2 offers free egress bandwidth, making it cost-effective for teams with frequent LFS downloads.

### How do I restrict who can push LFS objects?

All three platforms tie LFS push permissions to repository access controls. If a user can push to a repository, they can push LFS objects to it. For finer-grained control:

- **Gitea/Forgejo:** Use branch protection rules and team permissions to limit who can push to specific branches.
- **GitLab CE:** Use Protected Branches and Protected Tags settings, or configure LFS transfer quotas per-group.
- **All platforms:** Set up pre-receive hooks or webhooks to validate LFS uploads (e.g., reject files over a certain size or of certain MIME types).

### Can I migrate from GitHub LFS to a self-hosted server without losing history?

Yes. The `git clone --mirror` approach followed by `git push --mirror` transfers both Git objects and LFS objects. The key step is running `git lfs fetch --all` on the cloned mirror before pushing, which downloads all historical LFS objects from GitHub. Then `git push --mirror` uploads them to your new server. Verify with `git lfs fsck --all` after migration.

### Do I need a separate server for the LFS storage backend?

No. For small to medium deployments, running MinIO on the same server as Gitea, Forgejo, or GitLab works fine. For production environments with heavy LFS traffic, separating the object storage onto dedicated hardware (or a separate VM/container) improves performance and makes backup strategies simpler.

### What happens if the LFS server goes down?

Developers can still clone repositories (the pointer files are in Git), but they won't be able to check out the actual large files — `git lfs smudge` will fail. Existing clones with cached LFS objects continue to work. This is why running the LFS server on reliable hardware with proper monitoring is important.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Git LFS Storage: Gitea vs Forgejo vs GitLab CE — Complete Guide 2026",
  "description": "Compare self-hosted Git LFS storage solutions — Gitea, Forgejo, and GitLab CE. Complete guide with Docker Compose configs, S3 backend setup, migration strategies, and best practices for managing large files in Git repositories.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
