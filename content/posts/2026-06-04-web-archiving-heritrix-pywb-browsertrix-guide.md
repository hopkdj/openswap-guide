---
title: "Self-Hosted Web Archiving at Scale: Heritrix vs pywb vs Browsertrix"
date: "2026-06-04"
tags: ["web-archiving", "digital-preservation", "crawler", "replay", "heritrix", "pywb", "browsertrix"]
draft: false
---

## Introduction

The web is the primary medium of human communication in the 21st century — and it is vanishing at an alarming rate. Studies by the Pew Research Center found that 38% of webpages from 2013 were inaccessible by 2023. Government documents, news articles, research data, and cultural heritage all live on URLs that may 404 tomorrow. Web archiving — systematically capturing, storing, and replaying web content — is the digital equivalent of library preservation, and it requires specialized infrastructure.

Heritrix, pywb, and Browsertrix form a complete open-source web archiving stack developed by the Internet Archive and Webrecorder communities. Heritrix is the battle-tested crawler that has archived billions of pages for the Internet Archive's Wayback Machine. pywb is the Python-based replay engine that powers Wayback Machine-compatible archives. Browsertrix represents the next generation, handling the modern JavaScript-heavy web that traditional crawlers struggle with. This guide covers deploying each tool as part of a self-hosted web archiving pipeline.

## Project Overview

| Feature | Heritrix | pywb | Browsertrix |
|---------|----------|------|-------------|
| **Role** | Web Crawler | Web Archive Replay | Browser-Based Crawler |
| **Language** | Java | Python (JavaScript frontend) | TypeScript (Node.js) |
| **Stars** | 3,227 | 1,664 | 1,046 |
| **License** | Apache 2.0 | AGPL v3 | AGPL v3 |
| **Container** | Docker image available | Docker Compose support | Native Docker Compose |
| **WARC Format** | Produces WARC | Reads/serves WARC | Produces WARC |
| **JavaScript Support** | Basic (headless browser) | N/A (replay only) | Full (browser-based capture) |
| **Wayback Compatible** | No (requires replay engine) | Yes (full Wayback Machine API) | Yes (via pywb integration) |
| **Scale Target** | Enterprise/bulk crawls | Archive access & replay | High-fidelity single-site crawls |
| **Authentication** | Basic HTTP/FTP/HTTPS | N/A | Browser-based login capture |

## Architecture Deep-Dive

### Heritrix: The Enterprise Web Crawler

Heritrix is the Internet Archive's production crawler, having archived hundreds of billions of web pages since its initial release in 2004. It is designed for breadth-first crawling at enormous scale — a single Heritrix instance can crawl millions of URLs across thousands of domains while respecting robots.txt directives and crawl delays.

Heritrix operates through a modular, extensible architecture built around "processor chains." A crawl job consists of chained modules: a `Frontier` manages the URL queue with politeness scheduling, `Fetcher` modules handle HTTP/HTTPS/DNS requests, `Extractor` modules parse HTML for new links (including JavaScript-rendered links via a headless browser extractor), and `Writer` modules serialize captured resources to WARC (Web ARChive) format files.

The key operational concept in Heritrix is the "crawl scope" — rules that define which URLs should be captured and which should be excluded. Scope can be defined by domain, URL path regex, surt prefixes, or custom decision modules. This prevents crawls from spiraling into the entire web and ensures you capture only the content you intend to preserve.

### pywb: The Wayback Machine in Python

pywb (Python Wayback) is the reference implementation of the Wayback Machine's replay functionality. While Heritrix captures the raw web content, pywb provides the user-facing interface for browsing archived web pages exactly as they appeared at the time of capture. It supports the full WARC format specification and implements the Memento protocol for time-based content negotiation.

pywb's architecture includes a CDX index server that maps URLs to their capture timestamps and WARC file offsets. When a user requests an archived URL with a specific timestamp, pywb consults the CDX index, locates the appropriate WARC record, and serves a rewritten version of the page. The rewriting process modifies embedded resource URLs (images, CSS, JavaScript) to point back through the archive, ensuring the page renders correctly while remaining within the archived context.

A standout feature of pywb is its support for "live-archive hybrid" mode, where missing resources can be fetched from the live web and archived on-the-fly. This enables "record-on-demand" workflows where browsing generates new archival captures transparently.

### Browsertrix: High-Fidelity Browser-Based Archiving

Browsertrix represents the state of the art in web archiving, addressing the fundamental limitation of traditional crawlers: they cannot faithfully capture pages that depend on client-side JavaScript execution, WebSockets, and complex single-page application (SPA) architectures. Browsertrix runs a real Chromium browser to render each page fully before capturing, ensuring that dynamically loaded content, WebGL visualizations, and interactive maps are preserved.

Browsertrix operates on a "crawl workflow" model. Users define a crawl configuration specifying seed URLs, scope rules, page limits, and behaviors (such as scrolling to trigger lazy-loaded content or clicking "load more" buttons). The browser-based crawler then visits each page, interacts with it as configured, and captures the complete rendered page as WARC records.

Browsertrix integrates with pywb for replay, creating a complete capture-to-access pipeline. It also includes a web-based management UI for creating, monitoring, and reviewing crawls. For institutional archiving programs, Browsertrix Cloud provides a managed SaaS platform, but the open-source Browsertrix Crawler can be fully self-hosted.

## Deployment

### Heritrix with Docker

```yaml
version: "3.8"
services:
  heritrix:
    image: internetarchive/heritrix3:latest
    ports:
      - "8443:8443"
    environment:
      - HERITRIX_USER=admin
      - HERITRIX_PASSWORD=changeme
    volumes:
      - heritrix-data:/opt/heritrix/jobs
      - heritrix-config:/opt/heritrix/config

volumes:
  heritrix-data:
  heritrix-config:
```

Access the Heritrix web UI at `https://your-server:8443` and log in with the configured credentials. The web console provides crawl job creation, monitoring, and WARC management.

### pywb with Docker Compose

```yaml
version: "3.8"
services:
  pywb:
    image: webrecorder/pywb:latest
    ports:
      - "8080:8080"
    volumes:
      - ./webarchive:/webarchive
      - ./config.yaml:/webarchive/config.yaml
    command: wayback --proxy /webarchive/archive/

volumes:
  webarchive-data:
```

A minimal pywb `config.yaml`:

```yaml
collections:
  my-archive:
    index_paths: /webarchive/archive/cdx/
    archive_paths: /webarchive/archive/warcs/
    default_timestamp: "20260101000000"

enable_auto_fetch: true
proxy:
  coll: my-archive
  recording: true
```

### Browsertrix with Docker Compose

```yaml
version: "3.8"
services:
  browsertrix-crawler:
    image: webrecorder/browsertrix-crawler:latest
    ports:
      - "9037:9037"
    volumes:
      - ./crawls:/crawls
      - ./config.yaml:/app/config.yaml
    environment:
      - CRAWL_ID=my-crawl
      - CRAWL_DIR=/crawls

  browsertrix-backend:
    image: webrecorder/browsertrix-backend:latest
    depends_on:
      - redis
      - mongo
    environment:
      - MONGO_URL=mongodb://mongo:27017
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./crawls:/crawls

  redis:
    image: redis:7-alpine
  mongo:
    image: mongo:7
    volumes:
      - mongo-data:/data/db

volumes:
  mongo-data:
```

## Building a Complete Archiving Pipeline

These three tools work best as complementary components in a unified archiving pipeline:

1. **Browsertrix** handles the initial capture of JavaScript-heavy sites, ensuring high-fidelity preservation of modern web applications.
2. **Heritrix** performs bulk, large-scale crawls of simpler sites and provides the infrastructure for domain-wide preservation projects.
3. **pywb** serves as the unified access layer, providing Wayback Machine-compatible replay of WARC files produced by both Heritrix and Browsertrix.

For ongoing preservation, set up cron-based recrawl schedules. Browsertrix and Heritrix both support configurable crawl frequencies, allowing you to capture news sites daily, blogs weekly, and static reference pages monthly. pywb's live-archive hybrid mode fills gaps by archiving pages on-demand when users browse your archive.

## Why Self-Host Your Web Archiving Infrastructure?

Commercial web archiving services like Archive-It charge substantial annual fees based on data volume and crawl frequency. For institutions with modest archiving needs — a university archiving faculty websites, a journalism organization preserving news coverage, or a research group capturing dataset documentation — self-hosting provides equivalent functionality at a fraction of the cost. A modest VPS with 500GB storage can archive thousands of pages over years of operation.

Self-hosting also ensures that your archived content remains under your control. When using commercial services, your organization's web archives are subject to the provider's terms of service, pricing changes, and business continuity. Self-hosted WARC files are an open standard readable by any conforming tool, meaning your archives are truly portable and independent of any single vendor.

Legal compliance is another factor. Web archiving intersects with copyright law, data protection regulations (GDPR), and institutional records policies. Self-hosting allows you to implement access controls — restricting certain archives to on-campus access, implementing takedown procedures when requested, and maintaining audit trails of who accessed what archival content.

For related digital preservation workflows, see our [digital archive platform comparison](../2026-04-23-archivematica-vs-omeka-s-vs-dspace-self-hosted-digital-archive-guide-2026/) and [backup verification guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/). For managing the research data that web archives often complement, our [encrypted backup comparison](../2026-04-22-duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) covers reliable storage strategies.

## FAQ

### How much storage do I need for web archiving?

Storage requirements vary dramatically based on crawl scope and media content. As a rough estimate: archiving a single news website's front page daily generates about 50-100MB per month. A full crawl of a medium-sized domain (10,000 pages) might produce 5-20GB of WARC files. Video content dramatically increases storage requirements. Plan for at least 100GB for a small institutional archive and 1TB+ for domain-scale preservation projects. WARC files compress well — gzip compression typically reduces size by 60-70%.

### Can I archive websites that require login?

Browsertrix supports browser-based login capture. You can configure a crawl to navigate to a login page, enter credentials, and then proceed to capture authenticated content. Heritrix supports basic HTTP authentication and cookie-based sessions configured through the crawl settings. pywb does not handle authentication — it replays already-captured content regardless of whether it was originally behind a login. Be aware that archiving authenticated content may have legal and terms-of-service implications.

### How do these tools handle robots.txt?

Heritrix respects robots.txt by default and enforces crawl delays specified in the file. You can configure crawl-specific robots policy — for example, ignoring robots.txt for your own domains while respecting it for external domains. Browsertrix also respects robots.txt by default. Institutions archiving their own websites for preservation purposes typically configure crawls to ignore robots.txt for their own domains. The Internet Archive's official policy on robots.txt is nuanced — their Heritrix configuration is publicly documented.

### Can I make my archive publicly accessible like the Wayback Machine?

Yes. Deploy pywb with a public-facing web server (Nginx reverse proxy recommended) and DNS configuration. pywb provides the full Wayback Machine API, meaning tools that work with the Internet Archive's Wayback Machine — browser extensions, citation tools, and academic research software — will work with your self-hosted archive. Add HTTPS via Let's Encrypt and implement rate limiting to prevent abuse of your archiving infrastructure.

### What's the difference between WARC and WACZ formats?

WARC (Web ARChive) is the ISO standard (ISO 28500) for web archiving, storing individual HTTP request/response records with metadata. WACZ (Web Archive Collection Zipped) is a newer format that packages a complete web archive — multiple WARC records, CDX indexes, and metadata — into a single ZIP file. WACZ is designed for easy sharing and verification (it includes cryptographic signatures). pywb supports both formats. Most production archiving pipelines use WARC for storage and WACZ for distribution or submission to aggregators.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Web Archiving at Scale: Heritrix vs pywb vs Browsertrix",
  "description": "Complete guide to self-hosting web archiving infrastructure with Heritrix (crawler), pywb (Wayback Machine replay), and Browsertrix (browser-based capture). Covers Docker deployment, WARC formats, and building a complete digital preservation pipeline.",
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
