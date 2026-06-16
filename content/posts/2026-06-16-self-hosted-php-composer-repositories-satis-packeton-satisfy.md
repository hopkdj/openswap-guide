---
title: "Self-Hosted PHP Composer Repositories: Satis vs Packeton vs Satisfy Compared (2026)"
date: "2026-06-16"
tags: ["php", "composer", "package-management", "devops", "self-hosted", "repository", "open-source"]
draft: false
---

The PHP ecosystem relies on [Packagist](https://packagist.org) as its central package repository, but organizations handling proprietary code need private Composer repositories for internal distribution. Whether you are shipping internal libraries across teams, managing licensed dependencies, or working in environments with restricted internet access, a self-hosted Composer repository gives you control over package availability, access, and versioning.

This guide compares three self-hosted PHP Composer repository solutions — **Satis**, **Packeton**, and **Satisfy** — covering their architectures, deployment methods, and ideal use cases.

## Why Self-Host Your Composer Repository?

Self-hosting your Composer repository brings several concrete benefits. First, **private package hosting** lets you distribute internal PHP libraries to your team without exposing them on Packagist. Your proprietary authentication middleware, database abstractions, or framework components stay within your network while remaining installable via standard `composer require` commands.

Second, a local repository **improves build reliability**. CI/CD pipelines that depend on Packagist are vulnerable to rate limiting, network outages, and upstream repository changes. A local mirror eliminates these external dependencies, ensuring consistent builds even during Packagist downtime.

Third, you gain **version control and audit capabilities**. Track which packages are available, enforce semantic versioning policies, and maintain a history of what was installed when. For regulated industries (finance, healthcare, government), this audit trail is essential for compliance.

For related package management infrastructure, see our [binary repository guide](../2026-04-28-artifactory-oss-vs-nexus-vs-pulp-self-hosted-binary-repository-guide/) and [PHP application server comparison](../2026-06-04-php-application-servers-swoole-roadrunner-frankenphp-guide/). For language-agnostic dependency management, our [Debian package repository guide](../2026-05-02-aptly-vs-reprepro-vs-apt-mirror-self-hosted-debian-package-repository-guide/) covers similar concepts.

## Comparison Table

| Feature | Satis | Packeton | Satisfy |
|---------|-------|----------|---------|
| **Stars** | 3,279 | 531 | 547 |
| **Language** | PHP | PHP | PHP |
| **License** | MIT | MIT | MIT |
| **Web UI** | None (CLI only) | Full admin dashboard | Configuration UI for Satis |
| **Private Packages** | Yes (static config) | Yes (unlimited repos) | Yes (via Satis) |
| **User Management** | None | Built-in (roles, teams) | None |
| **API** | N/A | Composer API + REST | N/A (wraps Satis) |
| **Docker Support** | Community images | Official Docker image | Official Docker image |
| **Mirroring** | Manual config per package | Full Packagist proxy | Via Satis config |
| **Last Updated** | June 2026 | April 2026 | May 2025 |
| **Best For** | Simple static hosting | Enterprise team management | Satis with a friendly UI |

## Satis: The Foundation — Simple Static Composer Repository

[Satis](https://github.com/composer/satis) (3,279 stars) is the official static Composer repository generator from the Composer team. It is the most widely used solution and forms the foundation that both Packeton and Satisfy build upon.

Satis reads a JSON configuration file listing your packages (from VCS repositories, archives, or Packagist), downloads them, and generates a static HTML/JSON website that Composer can consume. The result is a directory of static files that you serve with any web server — Nginx, Apache, or even S3.

### Satis Configuration and Deployment

Create a `satis.json` configuration:

```json
{
    "name": "acme/private-repository",
    "homepage": "https://packages.acme.com",
    "repositories": [
        {"type": "vcs", "url": "https://github.com/acme/internal-lib"},
        {"type": "vcs", "url": "https://github.com/acme/auth-package"},
        {"type": "composer", "url": "https://packagist.org"}
    ],
    "require": {
        "acme/internal-lib": "*",
        "acme/auth-package": "*"
    },
    "require-dependencies": true,
    "archive": {
        "directory": "dist",
        "format": "zip"
    }
}
```

Run Satis to build the repository:

```bash
# Using Docker
docker run --rm -v $(pwd):/build composer/satis build satis.json /build/output

# Or using Composer directly
php bin/satis build satis.json output/
```

Serve with Nginx:

```nginx
server {
    listen 443 ssl;
    server_name packages.acme.com;
    root /var/www/composer-repo/output;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
}
```

Satis is ideal for teams that want a simple, reliable, zero-maintenance solution. However, it has no web UI — every package change requires editing `satis.json`, rebuilding, and redeploying. For teams that manage packages frequently, this becomes tedious.

## Packeton: Enterprise-Grade Private Packagist

[Packeton](https://github.com/vtsykun/packeton) (531 stars) is a full-featured private Packagist alternative with a web dashboard, user management, and unlimited private repositories. It is the closest self-hosted equivalent to Private Packagist (the commercial SaaS offering).

Unlike Satis's static approach, Packeton runs as a persistent web application with a database backend. It provides a Packagist-compatible API, meaning any tool that works with Packagist (Composer itself, CI plugins) works seamlessly with Packeton.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  packeton:
    image: vtsykun/packeton:latest
    container_name: packeton
    ports:
      - "8080:80"
    volumes:
      - packeton_data:/var/www/packeton/data
    environment:
      - DATABASE_URL=postgres://packeton:password@db/packeton
      - PACKETON_ADMIN_USER=admin
      - PACKETON_ADMIN_PASSWORD=changeme
      - PACKETON_BASE_URL=https://packages.acme.com
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    container_name: packeton_db
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=packeton
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=packeton
    restart: unless-stopped

volumes:
  packeton_data:
  pg_data:
```

Packeton supports multiple organization types — you can have VCS-triggered updates (GitHub, GitLab, Bitbucket webhooks), custom package types, and per-user API tokens. The dashboard shows download statistics, package health, and dependency graphs. For teams that manage dozens of internal packages across multiple projects, this level of visibility is invaluable.

## Satisfy: Satis with a Smile

[Satisfy](https://github.com/project-satisfy/satisfy) (547 stars) fills the gap between Satis's simplicity and Packeton's complexity. It is essentially a web-based configuration UI for Satis — you manage your `satis.json` through a browser instead of editing files manually.

Satisfy does not replace Satis; it wraps around it and provides a friendly way to add, remove, and configure packages. When you save changes in the Satisfy UI, it generates a new `satis.json`, triggers a Satis rebuild, and serves the results. This makes it dramatically easier to use than raw Satis for teams that don't need Packeton's full enterprise features.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  satisfy:
    image: ghcr.io/project-satisfy/satisfy:latest
    container_name: satisfy
    ports:
      - "8081:80"
    volumes:
      - satisfy_config:/var/www/satisfy/config
      - satisfy_output:/var/www/satisfy/web
    environment:
      - SATISFY_ADMIN_PASSWORD=changeme
      - SATISFY_HOMEPAGE=https://packages.acme.com
    restart: unless-stopped

volumes:
  satisfy_config:
  satisfy_output:
```

Satisfy's main advantage is reducing the friction of managing a static Satis repository. Instead of SSH-ing into a server to edit JSON files, team members can self-serve package additions through the web UI. For small to medium teams that want Satis's simplicity without the manual editing, Satisfy is the sweet spot.

## Choosing the Right Composer Repository

Your choice depends on your team's scale and workflow complexity:

- **Satis** is perfect for small teams (1-5 developers) who publish packages infrequently. The static approach means near-zero runtime complexity — you can even host the output on S3 or GitHub Pages. If you publish a new package version once a week, editing `satis.json` is not a burden.

- **Packeton** is the right choice for medium to large organizations that need a Packagist-like experience with user management, access control, and an API. Its webhook integration with GitHub/GitLab means new package versions are automatically detected and indexed. For teams shipping 10+ internal packages, the time saved on administration alone justifies Packeton's additional complexity.

- **Satisfy** is the "Goldilocks" option — more convenient than raw Satis but simpler than Packeton. If you have 5-15 team members who occasionally need to add packages but don't need full enterprise features, Satisfy provides the web UI convenience without the operational overhead of Packeton's database and authentication systems.

## Security Best Practices for Composer Repositories

Regardless of which tool you choose, implement these security measures:

```bash
# 1. Require HTTPS for all Composer traffic
# Composer 2.x enforces HTTPS by default, but verify:
composer config --global repo.packagist false
composer config --global secure-http true

# 2. Sign your packages (using GPG with Satis)
gpg --detach-sign --armor package.zip
# Verify on install:
gpg --verify package.zip.asc

# 3. Scan dependencies for vulnerabilities
composer audit
# Or use a dedicated tool:
docker run --rm -v $(pwd):/app php:cli composer audit
```

For production deployments, always place your Composer repository behind a reverse proxy with rate limiting to prevent abuse. Packeton includes built-in rate limiting; for Satis and Satisfy, configure it at the Nginx level:

```nginx
limit_req_zone $binary_remote_addr zone=composer:10m rate=30r/m;

server {
    location / {
        limit_req zone=composer burst=10 nodelay;
    }
}
```

## FAQ

### What is the difference between Satis and Packagist?

Packagist (packagist.org) is the public, centralized Composer repository that hosts all open-source PHP packages. Satis is a tool that generates a static, private Composer repository from a configuration file — you specify which packages to include, and it downloads them for local hosting. Think of Packagist as "npm for PHP" and Satis as "host your own npm registry on a static file server."

### Can I use Satis to mirror all of Packagist?

Theoretically yes, but practically no. Mirroring all of Packagist requires downloading every PHP package ever published (hundreds of GB). Satis is designed for selective mirroring — you specify exactly which packages and versions you need. For a broader mirror, Packeton's proxy mode is more efficient.

### How many packages can Packeton handle?

Packeton has been tested with thousands of packages and millions of download events. Its database-backed architecture scales linearly with PostgreSQL. For very large deployments (10,000+ packages), ensure your PostgreSQL instance has sufficient memory (2 GB minimum recommended) and use connection pooling with PgBouncer.

### Do these tools work with Composer 2.x?

Yes. All three tools — Satis, Packeton, and Satisfy — are fully compatible with Composer 2.x. Composer 2 brought significant performance improvements (lazy loading, parallel downloads) and all these repository tools support the updated API format.

### Can I restrict access to specific packages per user?

Only Packeton supports per-user and per-team access control. Satis and Satisfy serve static files — access control must be implemented at the web server level (HTTP Basic Auth, IP whitelisting, or OAuth proxy). If you need granular "Alice can see package X but not package Y" controls, Packeton is your only option among these three.

### How do I migrate from Packagist to a self-hosted solution?

Start by setting up Packeton (or Satis) and configuring your private packages first. Then, gradually add the public packages your projects depend on to your Satis configuration. Update your projects" `composer.json` to point to your private repository instead of Packagist. For a gradual migration, you can configure Composer to use both repositories, with your private one taking priority.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PHP Composer Repositories: Satis vs Packeton vs Satisfy Compared (2026)",
  "description": "Complete comparison of self-hosted PHP Composer repository solutions: Satis, Packeton, and Satisfy. Includes Docker Compose deployment examples, security best practices, and selection guide.",
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
