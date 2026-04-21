---
title: "Self-Hosted Screenshot & PDF Generation APIs: Gotenberg vs Playwright vs Puppeteer 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted screenshot and PDF generation APIs. Compare Gotenberg, Playwright, and Puppeteer for automated document rendering, invoice generation, and visual testing — with Docker setup instructions and performance benchmarks."
---

Automated PDF generation and website screenshots are core building blocks for countless applications. Invoices, reports, receipts, social media previews, and compliance documentation all depend on rendering HTML into pixel-perfect documents. The problem is that most teams rely on third-party SaaS APIs for this — services that charge per render, impose rate limits, and process your documents on servers you don't control.

Running your own screenshot and PDF generation stack gives you unlimited renders at zero marginal cost, full data privacy, and the ability to customize every aspect of the rendering pipeline. In 2026, the best tools for this job are open-source and ready to self-host.

## Why Self-Host Your Rendering Infrastructure

There are several compelling reasons to move PDF and screenshot generation in-house:

**Cost at scale.** Commercial rendering APIs typically charge $0.01–$0.05 per render. That's manageable for a few hundred documents, but a business generating 50,000 invoices per month pays $500–$2,500 for something that costs nothing to run locally. A single $10/month VPS with Gotenberg handles thousands of renders daily with room to spare.

**Data privacy.** Invoices, legal documents, financial reports, and health records flow through your rendering pipeline. Third-party services see every document you generate. Self-hosting keeps sensitive content within your infrastructure boundary — critical for GDPR, HIPAA, and SOC 2 compliance.

**No rate limits.** SaaS APIs throttle concurrent requests and impose daily quotas. When your batch job needs to generate 10,000 end-of-month reports, rate limits become a bottleneck. Self-hosted infrastructure scales with your hardware — add more containers, add more throughput.

**Customization.** Self-hosted solutions let you inject custom fonts, configure rendering parameters, modify page layouts, and integrate directly with your existing services. You control the Chromium version, the sandbox settings, and the network stack.

**Reliability.** External APIs go down. When your payment provider's receipt generation depends on a third-party service and that service has an outage, your business stops. Self-hosted rendering eliminates this single point of failure.

## What These Tools Actually Do

Before comparing options, it helps to understand the landscape. There are three categories of self-hosted rendering tools:

**Dedicated rendering APIs** wrap headless Chromium in a REST API. You send HTML or a URL, and get back a PDF or screenshot. Gotenberg is the standout here — it's purpose-built for this exact workflow, with a clean API, [docker](https://www.docker.com/)-native deployment, and features like PDF merging, form filling, and office document conversion.

**Browser automation frameworks** give you programmatic control over a headless browser. Playwright and Puppeteer let you write scripts that navigate pages, fill forms, take screenshots, and export PDFs. They're more flexible but require more code to achieve the same result as a dedicated API.

**Hybrid solutions** combine both approaches — tools like Browserless provide a REST API layer on top of Puppeteer/Playwright, giving you the convenience of an API with the flexibility of a browser automation framework.

## Gotenberg: The Dedicated Rendering API

Gotenberg is a stateless, Docker-first API for PDF generation. It wraps Chromium and LibreOffice, exposing a clean REST endpoint that accepts HTML, Markdown, URLs, and even Office documents. It's the simplest option to deploy and the most feature-complete for common use cases.

### Docker Setup

The fastest way to get started is a single Docker Compose file:

```yaml
version: "3.8"

services:
  gotenberg:
    image: gotenberg/gotenberg:8
    ports:
      - "3000:3000"
    restart: unless-stopped
    environment:
      - GOTENBERG_API_TIMEOUT=30s
      - GOTENBERG_CHROMIUM_RESTART_AFTER=100
      - GOTENBERG_CHROMIUM_AUTO_FILTER=true
```

Start it with `docker compose up -d`. The API is immediately available at `http://localhost:3000`.

### Generate a PDF from HTML

```bash
curl --request POST 'http://localhost:3000/forms/html' \
  --form 'files=@"/path/to/invoice.html"' \
  --form 'footer.html=@"/path/to/footer.html"' \
  --form 'nativePageRanges="1-3"' \
  --form 'pageSize="A4"' \
  --form 'preferCssPageSize=true' \
  --output invoice.pdf
```

### Generate a PDF from a URL

```bash
curl --request POST 'http://localhost:3000/forms/url' \
  --form 'url="https://example.com/report"' \
  --form 'waitForTimeout=2000' \
  --form 'emulatedMediaType="screen"' \
  --output report.pdf
```

### Take a Screenshot

```bash
curl --request POST 'http://localhost:3000/forms/url' \
  --form 'url="https://example.com"' \
  --form 'screenshots=true' \
  --form 'screenshotsFormat="jpeg"' \
  --form 'screenshotsQuality=90' \
  --form 'singlePage=true' \
  --output screenshot.jpg
```

### Merge Multiple PDFs

Gotenberg can combine existing PDFs into a single document — useful for assembling reports from multiple sources:

```bash
curl --request POST 'http://localhost:3000/forms/merge' \
  --form 'files=@"/path/to/report-part1.pdf"' \
  --form 'files=@"/path/to/report-part2.pdf"' \
  --form 'files=@"/path/to/report-part3.pdf"' \
  --output full-report.pdf
```

### Production Hardening

For production deployments, add these configurations:

```yaml
version: "3.8"

services:
  gotenberg:
    image: gotenberg/gotenberg:8
    ports:
      - "3000:3000"
    restart: unless-stopped
    environment:
      - GOTENBERG_API_TIMEOUT=60s
      - GOTENBERG_CHROMIUM_RESTART_AFTER=100
      - GOTENBERG_CHROMIUM_AUTO_FILTER=true
      - GOTENBERG_CHROMIUM_INCognito=true
      - GOTENBERG_DISABLE_ROUTER=true
      - GOTENBERG_API_DISABLE_HEALTH_CHECK_LOGGING=true
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

The `CHROMIUM_RESTART_AFTER` setting prevents memory leaks by recycling Chromium instances. The `INCOGNITO` flag ensures no data persists between requests. Resource limits prevent runaway processes from consuming the entire host.

## Playwright: The Browser Automation Powerhouse

Playwright is a cross-browser automation library developed by Microsoft. It supports Chromium, Firefox, and WebKit through a single API. While it requires writing code rather than making HTTP requests, it offers unmatched control over the rendering process.

### Installation

```bash
# Install Playwright for Node.js
npm init -y
npm install playwright
npx playwright install --with-deps chromium

# Or for Python
pip install playwright
playwright install --with-deps chromium
```

### Docker Deployment

```yaml
version: "3.8"

services:
  playwright-screenshot:
    image: mcr.microsoft.com/playwright:v1.49.0-jammy
    ports:
      - "3000:3000"
    working_dir: /app
    volumes:
      - ./app:/app
    command: ["node", "server.js"]
    restart: unless-stopped
    environment:
      - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
```

### Screenshot Server with Playwright

Create `server.js` to expose a simple screenshot API:

```javascript
const http = require("http");
const { chromium } = require("playwright");

const PORT = 3000;

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
    ],
  });

  const server = http.createServer(async (req, res) => {
    if (req.method !== "GET" || !req.url.startsWith("/screenshot")) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    const url = new URL(req.url, `http://localhost:${PORT}`);
    const targetUrl = url.searchParams.get("url");

    if (!targetUrl) {
      res.writeHead(400);
      res.end("Missing url parameter");
      return;
    }

    try {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 720 },
        deviceScaleFactor: 1,
      });

      const page = await context.newPage();
      await page.goto(targetUrl, {
        waitUntil: "networkidle",
        timeout: 15000,
      });

      // Wait for any lazy-loaded content
      await page.waitForTimeout(1000);

      const screenshot = await page.screenshot({
        fullPage: true,
        type: "jpeg",
        quality: 85,
      });

      await context.close();

      res.writeHead(200, {
        "Content-Type": "image/jpeg",
        "Content-Length": screenshot.length,
      });
      res.end(screenshot);
    } catch (err) {
      res.writeHead(500);
      res.end(`Error: ${err.message}`);
    }
  });

  server.listen(PORT, () => {
    console.log(`Screenshot server running on port ${PORT}`);
  });
})();
```

Use it with:
```bash
curl "http://localhost:3000/screenshot?url=https://example.com" -o example.jpg
```

### PDF Generation with Playwright

```javascript
const page = await browser.newPage();
await page.goto("https://example.com/invoice", {
  waitUntil: "networkidle",
});

const pdf = await page.pdf({
  format: "A4",
  printBackground: true,
  margin: { top: "20mm", bottom: "20mm", left: "15mm", right: "15mm" },
  displayHeaderFooter: true,
  headerTemplate: '<div style="font-size:10px;margin-left:20px;">CONFIDENTIAL</div>',
  footerTemplate:
    '<div style="font-size:10px;width:100%;text-align:center;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
});

require("fs").writeFileSync("invoice.pdf", pdf);
```

Playwright's strength is in com[plex](https://www.plex.tv/) workflows — logging into a dashboard, navigating to a report page, waiting for charts to render, then capturing a screenshot. It handles authentication, JavaScript execution, and dynamic content far better than simple HTML-to-PDF converters.

## Puppeteer: The Original Headless Chrome API

Puppeteer is Google's official Node.js library for controlling headless Chrome. It predates Playwright and remains widely used, though Playwright has surpassed it in feature parity and cross-browser support.

### Installation and Setup

```bash
npm install puppeteer
# Or puppeteer-core with a separate browser installation
npm install puppeteer-core
```

### Docker Deployment

```yaml
version: "3.8"

services:
  puppeteer-renderer:
    image: ghcr.io/browserless/chromium:latest
    ports:
      - "3000:3000"
    restart: unless-stopped
    environment:
      - CONCURRENT=5
      - MAX_QUEUE_LENGTH=10
      - TIMEOUT=30000
      - PRE_REQUEST_HEALTH_CHECK=true
      - EXIT_ON_HEALTH_CHECK_FAILURE=true
```

The Browserless image wraps Puppeteer with a REST API and connection management, making it production-ready out of the box.

### Generate PDF with Puppeteer

```javascript
const puppeteer = require("puppeteer");

async function generatePDF(url, outputPath) {
  const browser = await puppeteer.launch({
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(url, { waitUntil: "networkidle2" });

  await page.pdf({
    path: outputPath,
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
  });

  await browser.close();
}

generatePDF("https://example.com/report", "report.pdf");
```

### Screenshot with Puppeteer

```javascript
const page = await browser.newPage();
await page.goto("https://example.com", {
  waitUntil: "networkidle2",
});

// Full page screenshot
await page.screenshot({
  path: "fullpage.png",
  fullPage: true,
});

// Element-specific screenshot
const element = await page.$(".dashboard-card");
await element.screenshot({ path: "card.png" });
```

### HTML String to PDF (No URL Needed)

Puppeteer can render raw HTML strings directly, which is ideal for generating invoices from templates:

```javascript
const page = await browser.newPage();

const html = `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; padding: 40px; }
    .invoice-header { border-bottom: 2px solid #333; padding-bottom: 20px; }
    .line-item { display: flex; justify-content: space-between; padding: 8px 0; }
    .total { font-weight: bold; font-size: 1.2em; border-top: 2px solid #333; padding-top: 10px; }
    @media print { .no-print { display: none; } }
  </style>
</head>
<body>
  <div class="invoice-header">
    <h1>Invoice #2026-0042</h1>
    <p>Date: April 17, 2026</p>
  </div>
  <div class="line-item"><span>Web hosting (annual)</span><span>$120.00</span></div>
  <div class="line-item"><span>SSL certificate</span><span>$25.00</span></div>
  <div class="line-item"><span>CDN bandwidth (500GB)</span><span>$45.00</span></div>
  <div class="total"><span>Total</span><span>$190.00</span></div>
</body>
</html>
`;

await page.setContent(html, { waitUntil: "networkidle2" });
await page.pdf({ path: "invoice.pdf", format: "A4" });
```

## Feature Comparison

| Feature | Gotenberg | Playwright | Puppeteer + Browserless |
|---------|-----------|------------|------------------------|
| **Primary purpose** | PDF/screenshot API | Browser automation | Browser automation |
| **Deployment** | Single container | Code + container | Pre-built container |
| **API interface** | REST (HTTP forms) | Programmatic (Node.js/Python/Java/C#) | REST + programmatic |
| **HTML to PDF** | Yes | Yes | Yes |
| **URL to PDF** | Yes | Yes | Yes |
| **Screenshots** | JPEG/PNG | JPEG/PNG/WebP | JPEG/PNG/WebP |
| **PDF merging** | Built-in | Manual | Manual |
| **Office to PDF** | Yes (LibreOffice) | No | No |
| **Form filling (PDF)** | Built-in | Manual | Manual |
| **Markdown to PDF** | Yes | No | No |
| **PDF/A compliance** | Yes (PDF/A-1b, 2b, 3b) | No | No |
| **Multi-browser** | Chromium only | Chromium, Firefox, WebKit | Chromium only |
| **Concurrent requests** | Configurable pool | Manual management | Connection queue built-in |
| **Custom fonts** | Mount volume | Programmatic injection | Programmatic injection |
| **Authentication handling** | Cookie injection | Full login automation | Full login automation |
| **Memory management** | Auto-restart instances | Manual cleanup | Pool management |
| **Learning curve** | Low (curl commands) | Medium (API knowledge) | Medium (API knowledge) |
| **Best for** | Document pipelines | Complex workflows | Chrome-specific tasks |

## Performance Considerations

Rendering performance depends heavily on page complexity, but here are baseline measurements from a 2 vCPU / 4GB RAM server:

**Gotenberg:** Handles 5–10 concurrent PDF generations. Each render takes 1–3 seconds for typical pages. The auto-restart feature keeps memory usage stable even under sustained load. For high-throughput scenarios, run multiple Gotenberg instances behind a reverse proxy with round-robin load balancing.

**Playwright:** Browser startup adds 2–3 seconds on first request, but browser reuse cuts subsequent renders to under 1 second. The key optimization is keeping a single browser instance alive and creating new contexts per request — contexts are lightweight and isolated.

**Puppeteer with Browserless:** The built-in connection pool handles up to `CONCURRENT` simultaneous sessions. Queue length limits prevent memory exhaustion. The health check[kubernetes](https://kubernetes.io/)integrates cleanly with Docker Swarm and Kubernetes for automatic scaling.

### Scaling with Traefik

For production-scale rendering, deploy multiple Gotenberg containers behind Traefik:

```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v3.2
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
    ports:
      - "80:80"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"

  gotenberg-1:
    image: gotenberg/gotenberg:8
    labels:
      - "traefik.http.routers.gotenberg.rule=Host(`render.internal`)"
      - "traefik.http.services.gotenberg.loadbalancer.server.port=3000"
    environment:
      - GOTENBERG_CHROMIUM_RESTART_AFTER=100
    deploy:
      replicas: 4
      resources:
        limits:
          memory: 2G
          cpus: "1"
```

This setup distributes requests across 4 Gotenberg instances, each limited to 2GB memory and 1 CPU. Traefik handles health checking and failover automatically.

## Real-World Use Cases

### Invoice Generation Pipeline

```bash
#!/bin/bash
# Generate monthly invoices from HTML templates

TEMPLATE_DIR="/opt/invoices/templates"
OUTPUT_DIR="/opt/invoices/output"
GOTENBERG_URL="http://localhost:3000"

for client in $(ls "$TEMPLATE_DIR"); do
  curl --silent --request POST "${GOTENBERG_URL}/forms/html" \
    --form "files=@${TEMPLATE_DIR}/${client}/invoice.html" \
    --form "files=@${TEMPLATE_DIR}/${client}/header.html" \
    --form "pdfFormat=PDF/A-3b" \
    --form "nativePageRanges=1" \
    --output "${OUTPUT_DIR}/${client}-invoice-$(date +%Y-%m).pdf"
done
```

### Automated Visual Regression Testing

```javascript
const { chromium } = require("playwright");
const pixelmatch = require("pixelmatch");
const { PNG } = require("pngjs");
const fs = require("fs");

async function visualDiff(url, baselinePath, diffPath) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  await page.goto(url, { waitUntil: "networkidle" });
  await page.screenshot({ path: "current.png" });
  await browser.close();

  const baseline = PNG.sync.read(fs.readFileSync(baselinePath));
  const current = PNG.sync.read(fs.readFileSync("current.png"));
  const { width, height } = baseline;
  const diff = new PNG({ width, height });

  const mismatches = pixelmatch(
    baseline.data,
    current.data,
    diff.data,
    width,
    height,
    { threshold: 0.1 }
  );

  if (mismatches > 0) {
    fs.writeFileSync(diffPath, PNG.sync.write(diff));
    console.log(`Visual differences detected: ${mismatches} pixels`);
  } else {
    console.log("Screenshots match exactly");
  }

  return mismatches;
}

visualDiff(
  "https://app.example.com/dashboard",
  "baselines/dashboard.png",
  "diffs/dashboard.png"
);
```

### Social Media Preview Generator

```bash
# Generate Open Graph preview images from web pages
# Useful for CMS platforms that need automatic social media thumbnails

generate_og_image() {
  local url="$1"
  local output="$2"

  curl --silent --request POST "http://localhost:3000/forms/url" \
    --form "url=${url}" \
    --form "screenshots=true" \
    --form "screenshotsFormat=jpeg" \
    --form "screenshotsQuality=85" \
    --form "singlePage=true" \
    --form "viewport.width=1200" \
    --form "viewport.height=630" \
    --output "${output}"
}

generate_og_image "https://blog.example.com/latest-post" "/var/www/og-preview.jpg"
```

## Security Best Practices

When running a rendering service, you're essentially running a web browser that visits arbitrary URLs. This carries real security risks:

**Network isolation.** Run Gotenberg or Puppeteer in a Docker network with no outbound access to internal services. Use Docker user-defined networks and firewall rules to restrict what the rendering container can reach.

```yaml
services:
  gotenberg:
    image: gotenberg/gotenberg:8
    networks:
      - render-net
    # Block access to internal networks
    environment:
      - GOTENBERG_CHROMIUM_ALLOWED_ENDPOINTS=*.example.com,*.cdn.example.net

networks:
  render-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

**Request filtering.** Enable `CHROMIUM_AUTO_FILTER` in Gotenberg to block requests to private IP ranges. In Playwright, use route interception to filter outbound requests:

```javascript
await page.route("**/*", async (route) => {
  const url = route.request().url();
  const blocked = ["localhost", "127.0.0.1", "10.", "172.16.", "192.168."];

  if (blocked.some((prefix) => url.includes(prefix))) {
    route.abort();
  } else {
    route.continue();
  }
});
```

**Resource limits.** Always set Docker memory and CPU limits. A malicious or buggy page can consume unbounded resources through infinite loops, large allocations, or rendering explosions.

**Input validation.** Validate URLs before passing them to the rendering engine. Reject `file://`, `ftp://`, and `data:` URIs. Enforce HTTPS for external URLs.

## Monitoring and Observability

Add health checks and metrics to track rendering performance:

```yaml
services:
  gotenberg:
    image: gotenberg/gotenberg:8
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    environment:
      - GOTENBERG_API_DISABLE_HEALTH_CHECK_LOGGING=true
```

For Prometheus metrics, the Browserless image exposes `/metrics` endpoint. For Gotenberg, parse access logs to track request counts, error rates, and p99 latency.

## Choosing the Right Tool

The decision comes down to your use case complexity:

**Use Gotenberg** if you need a straightforward PDF or screenshot API. It requires zero code, deploys as a single container, and covers 90% of rendering needs — HTML to PDF, URL to PDF, screenshots, PDF merging, and office document conversion. It's the best choice for invoice generation, report pipelines, and document workflows.

**Use Playwright** if you need to interact with pages before capturing them — logging into dashboards, filling forms, waiting for JavaScript to render charts, or running visual regression tests. Its multi-browser support (Chromium, Firefox, WebKit) is unmatched, making it essential for cross-browser testing.

**Use Puppeteer with Browserless** if you're already invested in the Puppeteer ecosystem or need the specific features of the Browserless platform — connection pooling, session management, and the built-in REST API. It's a solid middle ground between Gotenberg's simplicity and Playwright's flexibility.

All three are open-source, self-hostable, and eliminate the need to send your documents through third-party APIs. The rendering infrastructure you run yourself will always be cheaper at scale, more private by default, and more reliable because you control the entire stack.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
