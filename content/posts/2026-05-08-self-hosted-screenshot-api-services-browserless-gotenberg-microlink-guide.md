---
title: "Self-Hosted Screenshot API Services: browserless vs Gotenberg vs Microlink"
date: "2026-05-08"
draft: false
tags: ["screenshot", "browser-automation", "headless-chrome", "api", "docker"]
---

Screenshot APIs let you capture web pages, generate PDFs, and extract content programmatically. Instead of paying for commercial services like ScreenshotAPI or Urlbox, you can self-host powerful alternatives that give you full control over pricing, data privacy, and scaling.

In this guide, we compare three popular self-hosted screenshot and document conversion platforms: **browserless**, **Gotenberg**, and **Microlink browserless**. Each offers a REST API for headless browser operations, but they differ significantly in features, performance, and deployment complexity.

## What Is a Self-Hosted Screenshot API?

A screenshot API runs a headless browser (typically Chromium) behind a REST endpoint. You send a URL or HTML payload, and the service returns a screenshot (PNG/JPEG), PDF, or extracted data. Self-hosting gives you:

- **No per-request fees** — commercial screenshot APIs charge $0.001–$0.01 per capture; self-hosted runs on your infrastructure cost
- **Full data privacy** — URLs and page content never leave your servers
- **Custom configurations** — set viewport sizes, cookies, authentication headers, wait conditions, and ad blockers
- **Unlimited throughput** — scale horizontally with Docker containers or Kubernetes pods

Common use cases include automated visual testing, link preview generation, web archiving, compliance monitoring, and competitive analysis.

## Comparison Overview

| Feature | browserless | Gotenberg | Microlink browserless |
|---------|-------------|-----------|----------------------|
| **GitHub Stars** | 13,100+ | 12,000+ | 1,800+ |
| **Language** | Node.js/TypeScript | Go | Node.js/TypeScript |
| **Browser Engine** | Chrome/Chromium | Chrome (via Chromium) | Chromium (via Puppeteer) |
| **Primary Focus** | Headless browser automation | Document conversion | Screenshot & metadata extraction |
| **Screenshot Formats** | PNG, JPEG, WebP | PDF, HTML | PNG, JPEG, PDF |
| **PDF Generation** | Yes | Yes (primary feature) | Yes |
| **REST API** | Yes (extensive) | Yes | Yes |
| **WebSocket Support** | Yes | No | No |
| **Queue/Concurrency** | Built-in queue manager | Concurrency limits via env | Puppeteer pool |
| **Docker Image** | `browserless/chrome` | `gotenberg/gotenberg` | `microlinkhq/browserless` |
| **Kubernetes Ready** | Yes (Helm chart) | Yes | Yes |
| **License** | SSPL (free non-commercial) | MIT | MIT |
| **Active Development** | Yes (2026) | Yes (2026) | Yes (2026) |

## browserless

**browserless** is the most popular self-hosted headless browser service. It wraps Chrome in a production-ready Docker container with a comprehensive REST API, WebSocket support, and built-in concurrency management.

### Key Features

- **Multi-session support** — run multiple browser contexts concurrently
- **Built-in queue** — manages browser session allocation automatically
- **Puppeteer/Playwright compatible** — connect via CDP (Chrome DevTools Protocol)
- **Pre-installed extensions** — uBlock Origin, ad blockers ready
- **Health check endpoints** — `/metrics`, `/active`, `/concurrent` for monitoring
- **Session recording** — debug and replay browser sessions

### Docker Compose Configuration

```yaml
services:
  browserless:
    image: browserless/chrome:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - TOKEN=your-secret-api-token
      - CONCURRENCY=10
      - QUEUE_SIZE=20
      - TIMEOUT=30000
      - EXIT_ON_HEALTH_FAILURE=true
      - PREBOOT_QUANTITY=2
    volumes:
      - ./data:/tmp/browserless
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### API Usage Examples

```bash
# Capture a screenshot
curl -X POST http://localhost:3000/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "options": {"fullPage": true}}' \
  -o screenshot.png

# Generate PDF
curl -X POST http://localhost:3000/pdf \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o output.pdf

# Connect via Puppeteer
const puppeteer = require('puppeteer');
const browser = await puppeteer.connect({
  browserWSEndpoint: 'ws://localhost:3000?token=your-secret-api-token'
});
```

### When to Choose browserless

Choose browserless when you need a **full headless browser service** with session management, concurrent automation, and Puppeteer/Playwright compatibility. It's the best option for web scraping, automated testing pipelines, and any workflow that requires interactive browser control beyond simple screenshots.

## Gotenberg

**Gotenberg** is a Docker-powered document conversion API built on top of Chromium and LibreOffice. While it supports screenshots, its primary strength is converting a wide range of document formats to PDF.

### Key Features

- **Wide format support** — HTML, Markdown, DOCX, XLSX, PPTX, CSV, images to PDF
- **Merge PDFs** — combine multiple documents into a single PDF
- **Custom headers/footers** — inject page numbers, logos, dates
- **Webhook support** — async processing with callback URLs
- **No browser session overhead** — stateless, conversion-focused
- **Excellent documentation** — clear OpenAPI spec and examples

### Docker Compose Configuration

```yaml
services:
  gotenberg:
    image: gotenberg/gotenberg:8
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GOTENBERG_API_ENABLE_WEBHOOK=true
      - CHROME_RESTART_ATTEMPTS=3
      - CHROME_RESTART_DELAY=2s
      - API_TIMEOUT=30s
      - API_DISABLE_HEALTH_CHECK_LOGGING=true
    volumes:
      - ./tmp:/tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### API Usage Examples

```bash
# Convert URL to PDF
curl --request POST http://localhost:3000/forms/chromium/convert/url \
  --form 'url="https://example.com"' \
  --form 'output.pdf' > output.pdf

# Convert HTML to PDF with custom options
curl --request POST http://localhost:3000/forms/chromium/convert/html \
  --form 'file=@page.html' \
  --form 'pageSize="A4"' \
  --form 'marginTop="0.5in"' \
  --form 'marginBottom="0.5in"' \
  -o document.pdf

# Screenshot via Chromium endpoint
curl --request POST http://localhost:3000/forms/chromium/screenshot/url \
  --form 'url="https://example.com"' \
  --form 'format="jpeg"' \
  --form 'quality=90' \
  -o screenshot.jpg
```

### When to Choose Gotenberg

Choose Gotenberg when your primary need is **document conversion** — especially converting office documents (DOCX, XLSX, PPTX) to PDF. It's also ideal for generating invoices, reports, and archival PDFs from HTML templates. The stateless architecture makes it easier to scale horizontally than session-based browsers.

## Microlink browserless

**Microlink browserless** is a Puppeteer-based headless browser API focused on screenshot capture, PDF generation, and metadata extraction. It's the lightweight, MIT-licensed alternative to the commercial browserless service.

### Key Features

- **Simple REST API** — clean endpoints for screenshot, PDF, and HTML extraction
- **Metadata extraction** — auto-detect Open Graph, Twitter Cards, structured data
- **Optimization pipeline** — built-in image compression and format conversion
- **Puppeteer under the hood** — full Chromium capabilities
- **MIT licensed** — no SSPL restrictions, free for commercial use
- **Lightweight** — smaller footprint than full browserless

### Docker Compose Configuration

```yaml
services:
  browserless:
    image: microlinkhq/browserless:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - API_TOKEN=your-secret-token
      - CONCURRENCY=5
      - TIMEOUT=30000
      - CHROME_REFRESH_TIME=600000
      - PUPPETEER_CHROMIUM_FLAGS=--no-sandbox,--disable-setuid-sandbox
    volumes:
      - ./data:/tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### API Usage Examples

```bash
# Screenshot a URL
curl "http://localhost:3000/screenshot?url=https://example.com&fullPage=true&adblock=true" \
  -o screenshot.png

# Extract metadata
curl "http://localhost:3000/html?url=https://example.com"

# Generate PDF with options
curl "http://localhost:3000/pdf?url=https://example.com&pdf.printBackground=true" \
  -o document.pdf
```

### When to Choose Microlink browserless

Choose Microlink when you need an **MIT-licensed**, lightweight screenshot API without the SSPL restrictions of the main browserless project. It's well-suited for link preview generation, social media card creation, and simple web capture workflows where you don't need the full session management features of browserless.

## Choosing the Right Screenshot API

| Use Case | Best Choice | Why |
|----------|-------------|-----|
| Web scraping & automation | browserless | Full Puppeteer/Playwright support, session management |
| Document-to-PDF conversion | Gotenberg | Native LibreOffice integration, wide format support |
| Link previews & social cards | Microlink | Metadata extraction, lightweight, MIT licensed |
| High-concurrency screenshots | browserless | Built-in queue, pre-booted browsers, session pooling |
| Invoice/report generation | Gotenberg | HTML-to-PDF with headers, footers, and page numbers |
| Commercial use without SSPL | Microlink | Pure MIT license, no usage restrictions |

## Why Self-Host Your Screenshot API?

Running your own screenshot API service gives you significant advantages over commercial alternatives:

**Cost savings at scale.** Commercial screenshot APIs typically charge $0.001–$0.01 per request. At 100,000 captures per month, that's $100–$1,000. A self-hosted instance on a $20/month VPS with 4 CPU cores can handle 500–1,000 requests per hour, costing pennies per thousand captures. The breakeven point is typically around 10,000–20,000 requests per month.

**Data sovereignty and privacy.** When you send URLs to a commercial screenshot service, you're sharing your browsing patterns, internal application URLs, and potentially sensitive content. Self-hosting ensures that no third party sees what pages you're capturing, what cookies you're using, or what data you're extracting. This is critical for compliance with GDPR, HIPAA, and SOC 2 requirements.

**Custom configuration and control.** Self-hosted services let you configure exact viewport sizes, install custom browser extensions, set up authentication proxies, block specific domains or ads, and tune timeout thresholds for your specific use case. Commercial APIs offer limited customization and charge premium tiers for advanced features.

**Reliability and uptime.** Commercial APIs experience outages, rate limit changes, and API deprecations. With a self-hosted service, you control the availability. Run multiple instances behind a load balancer, and you eliminate single points of failure.

**No vendor lock-in.** All three services in this comparison use standard Chromium/Puppeteer APIs. If you need to switch providers or upgrade, your code changes are minimal. Compare that to proprietary screenshot APIs where migration requires rewriting integration code.

For more on self-hosted web services, see our [headless CMS comparison](../2026-05-04-payload-cms-vs-strapi-vs-directus-self-hosted-headless-cms/) and [file upload and screenshot server guide](../2026-04-25-zipline-vs-sharex-upload-server-vs-flowinity-self-hosted-file-upload-screenshot-server-guide-2026/). If you're building automated testing pipelines, our [container image scanning guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/) covers the testing infrastructure side.

## FAQ

### Can I run these screenshot APIs behind a reverse proxy?

Yes. All three services expose a standard HTTP API that works behind Nginx, Caddy, or Traefik. Add TLS termination, rate limiting, and authentication at the reverse proxy layer. For browserless, also proxy the WebSocket endpoint (`/session`) if you need CDP connections.

### How many concurrent screenshots can a single instance handle?

It depends on your CPU and memory. A typical 4-core, 8 GB server can handle 5–10 concurrent Chromium instances. browserless has the best built-in concurrency management with its queue system. Gotenberg uses semaphore-based concurrency limits. Microlink relies on Puppeteer's connection pool.

### Do these services support authentication and cookies?

Yes. All three support sending cookies, custom headers, and authentication credentials. browserless lets you set cookies via its API endpoint before taking screenshots. Gotenberg supports HTTP authentication via form fields. Microlink accepts cookies as URL parameters.

### What is the difference between SSPL and MIT licensing?

The SSPL (Server Side Public License) used by browserless requires that if you offer the service to others as a hosted product, you must open-source your entire service stack. For internal use or non-commercial purposes, it's free. The MIT license used by Gotenberg and Microlink has no such restrictions — you can use them commercially without additional obligations.

### Can I scale these services with Kubernetes?

Yes. All three provide Docker images that work in Kubernetes. browserless offers an official Helm chart. For Gotenberg and Microlink, create a Deployment with Horizontal Pod Autoscaler based on CPU/memory utilization. Add a Service and Ingress for external access.

### How do I monitor the health of a screenshot API service?

Each service provides a `/health` endpoint. browserless additionally exposes `/metrics` (Prometheus format), `/active` (current sessions), and `/concurrent` (queue depth). Set up alerting on health check failures and queue depth thresholds. For Gotenberg, monitor the `gotenberg_chromium_restarts_total` metric.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Screenshot API Services: browserless vs Gotenberg vs Microlink",
  "description": "Compare three self-hosted screenshot API services — browserless, Gotenberg, and Microlink browserless. Includes Docker Compose configs, API examples, and licensing comparison.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
