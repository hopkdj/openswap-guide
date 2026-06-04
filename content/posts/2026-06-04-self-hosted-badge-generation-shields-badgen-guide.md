---
title: "Self-Hosted Badge Generators for Open Source Projects: Shields vs Badgen"
date: "2026-06-04"
tags: ["badges", "developer-tools", "self-hosted", "open-source", "ci-cd", "documentation"]
draft: false
---

## Introduction

Every open-source project's README, documentation site, and landing page benefits from status badges — those small, colorful SVG images that display build status, test coverage, latest version, license, and download counts at a glance. Badges are the universal visual language of open-source health, converting complex CI/CD pipeline states into instantly recognizable signals.

While most projects use hosted badge services like shields.io or img.shields.io, self-hosting your badge generator gives you complete control over uptime, custom badge designs, private repository integration, and data sources that a public service cannot access. Two leading open-source badge generators — **Shields** (the engine behind shields.io) and **Badgen** — let you run your own badge service on your infrastructure.

Shields powers one of the most visited badge services on the internet with 26,700+ GitHub stars and support for hundreds of services. Badgen takes a different approach, focusing on speed, simplicity, and a clean API design with 1,500+ stars and a growing ecosystem. In this guide, we compare both for self-hosted badge generation, covering deployment, customization, and service integration.

## Feature Comparison

| Feature | Shields | Badgen |
|---------|---------|--------|
| **GitHub Stars** | 26,700+ | 1,540+ |
| **Last Updated** | June 2026 | June 2026 |
| **Language** | JavaScript (Node.js) | TypeScript / JavaScript |
| **Service Integrations** | 300+ services | 100+ services |
| **Custom Endpoint** | JSON endpoint + dynamic badges | URL-based templates |
| **Static Badges** | Yes (via URL parameters) | Yes (native) |
| **Dynamic Badges** | Yes (JSON/XML/API data sources) | Yes (live URL fetching) |
| **Self-Hosted Mode** | Full standalone server | Standalone + serverless |
| **Docker Support** | Official image (ghcr.io) | Official image (ghcr.io) |
| **Caching** | Configurable (Redis/Memcached) | Built-in LRU cache |
| **Custom Templates** | SVG template engine | Style presets ("flat", "classic") |
| **Rate Limiting** | Configurable via server | Built-in throttling |
| **License** | CC0 1.0 Universal | MIT |

## Docker Compose Deployment

### Shields (Self-Hosted)

```yaml
version: "3.8"
services:
  shields:
    image: ghcr.io/badges/shields:latest
    container_name: shields-server
    ports:
      - "8080:80"
    environment:
      - SHIELDS_ANALYTICS=false
      - WHEELMAP_TOKEN=
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:80"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Once running, generate badges by hitting your self-hosted endpoint:

```bash
# Build status badge
curl "http://localhost:8080/github/checks/nodejs/node.svg"

# Version badge
curl "http://localhost:8080/npm/v/express.svg"

# Custom static badge
curl "http://localhost:8080/badge/coverage-85%25-brightgreen.svg"
```

### Badgen (Self-Hosted)

```yaml
version: "3.8"
services:
  badgen:
    image: ghcr.io/badgen/badgen:latest
    container_name: badgen-server
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - CACHE_MAX_AGE=3600
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Badgen uses a simple URL scheme:

```bash
# npm version badge
curl "http://localhost:3000/npm/v/express"

# GitHub stars badge
curl "http://localhost:3000/github/stars/nodejs/node"

# Custom badge with label
curl "http://localhost:3000/badge/build/passing/green"
```

### Reverse Proxy Integration (Caddy)

For production use, place either service behind a reverse proxy with HTTPS:

```caddyfile
badges.example.com {
    reverse_proxy localhost:8080
    encode gzip
    header Cache-Control "public, max-age=300"
}
```

## API and Customization Deep-Dive

### Shields Custom Endpoints

Shields supports a **JSON endpoint** that lets you create badges from any data source:

```json
{
  "schemaVersion": 1,
  "label": "coverage",
  "message": "92%",
  "color": "brightgreen",
  "cacheSeconds": 300
}
```

Serve this JSON from any HTTP endpoint and reference it as:

```
http://localhost:8080/endpoint?url=https://your-server.com/badge-data.json
```

This pattern is particularly powerful for private repositories — you can host a small JSON endpoint behind your firewall that exposes internal metrics, and Shields generates the badge without needing direct access to your source code.

### Badgen URL Templates

Badgen shines with its **concise URL syntax** — every badge is a single URL with no external dependencies:

```
/badge/:label/:value/:color
/badge/:label/:value/:color?icon=github
/github/stars/:owner/:repo
/npm/v/:package
/docker/pulls/:owner/:image
```

The `?icon=` parameter supports 1,500+ icons from Simple Icons and iconify, making it easy to create professional-looking badges with brand logos.

## Performance and Caching Strategy

Badge services are read-heavy workloads — a single README badge can generate thousands of requests per day if your project has active traffic. Understanding caching is essential for keeping your service responsive under load.

### Browser-Side Caching

Both Shields and Badgen support HTTP `Cache-Control` headers. Set `max-age=300` (5 minutes) for badges that change infrequently (license, version) and `max-age=60` for real-time badges (build status, coverage). Browsers and CDNs respect these headers, dramatically reducing origin server load. For the most visited projects, a single badge request at the CDN edge can serve thousands of users.

### Server-Side Caching

Shields supports Redis and Memcached as shared cache backends for multi-instance deployments. Configure the `SHIELDS_REDIS_URL` environment variable to point to your Redis instance. Badgen uses an in-memory LRU cache by default with a configurable `CACHE_MAX_AGE` in seconds — for single-instance deployments, this is simpler and sufficient.

### Scaling Horizontally

Both services are stateless — you can run multiple container replicas behind a load balancer. For Shields, use Redis as the shared cache to avoid duplicate upstream API calls across replicas. For Badgen, each instance maintains its own cache, which is acceptable for deployments under 10 million requests per day. Use Docker Compose with `deploy.replicas: 3` or Kubernetes with a HorizontalPodAutoscaler targeting CPU usage above 70%.

### Upstream API Rate Limiting

Many badge data sources (GitHub API, npm registry, Docker Hub) enforce rate limits. Shields implements configurable rate limiting to avoid hitting these limits — set `SHIELDS_REQUEST_TIMEOUT_SECONDS=10` and configure the `rateLimit` option in your server config. Badgen uses a simpler approach: it caches upstream responses and serves stale data when rate limits are hit, ensuring badges never go blank even during API outages.

## Why Self-Host Your Badge Service?

Relying on a public badge service like img.shields.io means every visitor to your project's README or documentation triggers an external HTTP request to a third-party server. If that service is down, rate-limited, or deprecated, your project pages show broken images — an unprofessional look that undermines trust in your software. Self-hosting eliminates this dependency entirely.

For private repositories and internal tools, self-hosting is not optional — it is required. Public badge services cannot access your private GitLab instance, internal Jenkins server, or on-premises SonarQube deployment. A self-hosted badge service running inside your network can query all of these data sources and generate badges that reflect your actual pipeline state. For CI/CD integration patterns, see our [self-hosted CI/CD pipeline guide](../2026-04-19-woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/).

Branding and customization are additional benefits. With a self-hosted badge service, you can enforce consistent colors, fonts, and styling across all your organization's projects — no more mismatched badge aesthetics from different services. If your team maintains internal documentation sites, check out our [self-hosted static site generator comparison](../self-hosted-static-site-generators-hugo-jekyll-astro-eleventy-guide/) for integrating badges into your documentation pipeline.

For code review workflows where badges communicate pipeline status to reviewers, pair your badge service with a [self-hosted code review platform](../gerrit-vs-review-board-vs-phorge-self-hosted-code-review-guide/).

## Custom Badge Templates and Advanced Styling

Beyond the standard static and dynamic badges, both platforms support advanced customization for organizations that need branded badge styling.

### Shields Template Engine

Shields uses a custom SVG template engine that supports arbitrary colors, logos, and label text. The template format is documented in the Shields GitHub repository. You can create organization-specific badge templates that enforce your brand colors, font family, and corner radius across all projects. Mount custom templates into the Docker container:

```yaml
volumes:
  - ./custom-templates:/app/templates
```

This is particularly useful for large organizations that want every repository badge to match their design system — consistent label widths, corporate color palette, and custom icon sets.

### Badgen Style Presets

Badgen offers several built-in style presets via the `?style=` parameter: `flat` (default, clean modern look), `classic` (rounded corners, shadow effect), and `flat-square` (sharp corners). Combine with the `?icon=` parameter for brand-specific logos. For completely custom styling, Badgen supports SVG output that you can post-process with any SVG manipulation tool.

### Performance Comparison

In benchmark testing, Badgen typically serves badges 2-3x faster than Shields for simple static badges because its template engine is lighter weight. Shields excels at complex dynamic badges that query upstream APIs — its built-in caching layer prevents redundant API calls during traffic spikes. For high-traffic open-source projects, the difference is negligible because browser and CDN caching absorbs most requests.

## FAQ

### Why would I self-host a badge service instead of using shields.io?

Three reasons: reliability (no external dependency for your README badges), private data sources (your self-hosted service can access internal CI/CD, private registries, and on-premises tools), and customization (full control over caching, rate limiting, and badge styling). If your project is public and uses only public data sources, shields.io works fine — but for organizations running private infrastructure, self-hosting is essential.

### Can I use both Shields and Badgen on the same project?

Absolutely. Many projects use Shields for standard service badges (GitHub Actions, npm, Docker) and Badgen for custom, project-specific badges where the URL-template syntax is more convenient. Both generate standard SVG images, so they render identically in README files and documentation.

### How much traffic can a self-hosted badge service handle?

A single Node.js instance of either Shields or Badgen can serve thousands of badge requests per second on modest hardware (2 vCPU, 1GB RAM). Both services generate SVG badges that are typically 1-3KB in size. With proper caching headers (set `Cache-Control: public, max-age=300`), most requests are served from the browser cache or CDN edge, not your origin server.

### Do these badge services collect any analytics or user data?

The self-hosted versions do not collect analytics by default. Shields has an optional analytics module (disabled in the Docker Compose config above) that tracks service-level metrics. Badgen has no analytics features. Since you control the server, no data leaves your infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Badge Generators for Open Source Projects: Shields vs Badgen",
  "description": "Compare Shields and Badgen for self-hosted SVG badge generation. Covers Docker Compose deployment, API customization, reverse proxy setup, and integration with CI/CD pipelines.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
