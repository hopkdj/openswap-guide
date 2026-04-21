---
title: "Sitespeed.io vs WebPageTest vs Lighthouse: Self-Hosted Web Performance Monitoring 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "monitoring", "web-performance"]
draft: false
description: "Compare three leading open-source web performance testing tools — Sitespeed.io, WebPageTest, and Google Lighthouse — with self-hosted Docker deployment guides, feature comparisons, and practical monitoring setups for 2026."
---

Web performance directly impacts user engagement, conversion rates, and search engine rankings. While hosted services like GTmetrix and Pingdom offer convenient testing, self-hosting your performance monitoring stack gives you unlimited tests, complete data ownership, and the ability to test internal or staging environments that aren't publicly accessible.

In this guide, we compare three leading open-source web performance tools — **Sitespeed.io**, **WebPageTest**, and **Google Lighthouse** — and show you how to deploy each one with Docker for continuous, self-hosted performance monitoring.

For related monitoring setups, see our [endpoint monitoring with Gatus vs Blackbox Exporter vs Smokeping](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/) and [load testing with k6 vs Locust vs Gatling](../k6-vs-locust-vs-gatling-self-hosted-load-testing-guide-2026/).

## Why Self-Host Web Performance Monitoring?

Public speed testing services are convenient but come with significant limitations:

- **Test quotas** — free tiers restrict you to a handful of tests per day
- **No historical tracking** — you can't see how performance trends over time
- **Limited locations** — you're stuck with the provider's test locations
- **Privacy concerns** — every URL you test is visible to the service operator
- **No internal testing** — staging environments behind authentication can't be tested
- **No CI/CD integration** — hard to automate performance regression detection

Self-hosting solves all of these problems. You get unlimited tests, full control over test locations and browsers, historical data you own, and the ability to integrate performance checks into your deployment pipeline.

## Sitespeed.io: Comprehensive Performance Analysis

**GitHub**: [sitespeedio/sitespeed.io](https://github.com/sitespeedio/sitespeed.io) — ⭐ 4,974 stars | Last updated: April 2026 | Language: JavaScript

Sitespeed.io is the most feature-complete open-source web performance tool available. It runs real browser tests using Chrome or Firefox, collects over 100 metrics per page load, and integrates seamlessly with Grafana and Graphite for long-term trend analysis.

### Key Features

- Real browser testing with Chrome or Firefox via Selenium/WebDriver
- Over 100 metrics collected per test (Core Web Vitals, resource timings, visual metrics)
- Built-in Grafana dashboards with pre-configured panels
- Video recording and filmstrip analysis of page loads
- Custom JavaScript execution during page load
- Budget file support for pass/fail performance gates
- Multi-page test scripts for user journey testing
- WebPageReplay support for consistent, repeatable testing

### Docker Deployment

Sitespeed.io provides an official Docker compose stack with Grafana and Graphite pre-configured. Clone the repository and start the monitoring stack:

```bash
git clone https://github.com/sitespeedio/sitespeed.io.git
cd sitespeed.io/docker/
docker compose up -d
```

The docker-compose.yml includes three services:

```yaml
version: '3'
services:
    grafana:
      image: grafana/grafana:12.2.0
      hostname: grafana
      depends_on:
        - graphite
      ports:
        - "3000:3000"
      environment:
        - GF_SECURITY_ADMIN_PASSWORD=your-secure-password
        - GF_SECURITY_ADMIN_USER=sitespeedio
        - GF_AUTH_ANONYMOUS_ENABLED=true
        - GF_USERS_ALLOW_SIGN_UP=false
        - GF_USERS_ALLOW_ORG_CREATE=false
        - GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/Welcome.json
      volumes:
        - grafana:/var/lib/grafana
        - ./grafana/provisioning/datasources:/etc/grafana/provisioning/datasources
        - ./grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards
      restart: always
    graphite:
      image: sitespeedio/graphite:1.1.10-3
      hostname: graphite
      ports:
        - "2003:2003"
        - "8080:80"
      restart: always
      volumes:
        - whisper:/opt/graphite/storage/whisper

volumes:
    grafana:
    whisper:
```

Run a single test against the Docker network:

```bash
docker run --rm -v "$(pwd)/sitespeed-result:/sitespeed.io/sitespeed-result" \
  sitespeedio/sitespeed.io:latest \
  --grafana.host grafana \
  --graphite.host graphite \
  https://www.yoursite.com
```

### Setting Up a Performance Budget

Create a `budget.json` file to enforce performance thresholds:

```json
{
  "budget": {
    "timings": {
      "backEndTime": 500,
      "frontEndTime": 2000,
      "pageLoadTime": 3000,
      "fullyLoaded": 5000
    },
    "transferSize": {
      "total": 2000000
    },
    "cumulativeLayoutShift": 0.1,
    "largestContentfulPaint": 2500
  }
}
```

Run with the budget to get pass/fail results:

```bash
docker run --rm sitespeedio/sitespeed.io:latest \
  --budget.config budget.json \
  https://www.yoursite.com
```

## WebPageTest: The Industry Standard

**GitHub**: [WPO-Foundation/webpagetest](https://github.com/WPO-Foundation/webpagetest) — ⭐ 3,244 stars | Last updated: September 2025 | Language: PHP

WebPageTest is the grandfather of web performance testing. Originally built at AOL and now maintained by the Web Performance Open Source Project, it provides the most detailed waterfall charts, connection diagrams, and filmstrip views available in any open-source tool.

### Key Features

- Multi-location testing with configurable test agents
- Detailed waterfall charts showing every resource request
- Connection view showing DNS, TCP, TLS, and TTFB breakdowns
- Filmstrip views at 100ms intervals with visual progress
- Video comparison between test runs
- Custom metrics via JavaScript injection
- API for automated testing and CI integration
- Mobile device emulation with real device agents
- Traffic shaping to simulate 3G, 4G, and custom connections
- Lighthouse integration built-in

### Docker Deployment

WebPageTest's Docker setup includes three components: a web front-end (Nginx + PHP), and a test agent that runs browser tests. Clone the repository and configure:

```bash
git clone https://github.com/WPO-Foundation/webpagetest.git
cd webpagetest
```

The official docker-compose.yml on the `master` branch orchestrates three services:

```yaml
version: '3.6'
services:
  web:
    build: 
      context: .
      dockerfile: docker/local/Dockerfile-nginx
    ports:
      - "80:80"
    volumes:
      - .:/var/www/webpagetest
    secrets:
      - source: wpt_settings_ini
        target: /var/www/webpagetest/settings/settings.ini
      - source: wpt_keys_ini
        target: /var/www/webpagetest/settings/keys.ini

  php:
    build: 
      context: .
      dockerfile: docker/local/Dockerfile-php
    expose:
      - "9000"
    volumes:
      - .:/var/www/webpagetest
    secrets:
      - source: wpt_settings_ini
        target: /var/www/webpagetest/www/settings/settings.ini
      - source: wpt_keys_ini
        target: /var/www/webpagetest/www/settings/keys.ini
      - source: wpt_locations_ini
        target: /var/www/webpagetest/www/settings/locations.ini

  agent:
    cap_add:
      - NET_ADMIN
    build:
      context: .
      dockerfile: docker/local/Dockerfile-wptagent
    environment:
      - SERVER_URL=http://web/work/
      - LOCATION=Test
      - KEY=123456789
    init: true

secrets:
  wpt_settings_ini:
    file: ./docker/local/wptconfig/settings.ini
  wpt_keys_ini:
    file: ./docker/local/wptconfig/keys.ini
  wpt_locations_ini:
    file: ./docker/local/wptconfig/locations.ini
```

Create the required configuration files:

```bash
mkdir -p docker/local/wptconfig
```

Create `docker/local/wptconfig/settings.ini`:
```ini
[settings]
locations=Test
```

Create `docker/local/wptconfig/keys.ini`:
```ini
[locations]
Test.key=123456789
```

Create `docker/local/wptconfig/locations.ini`:
```ini
[locations]
1=Test

[Test]
1=Test-Local
label="Test Location"
group=Desktop
```

Then start the stack:

```bash
docker compose up -d
```

Access the WebPageTest UI at `http://your-server/` and submit your first test.

### Using the WebPageTest API

For automated testing, use the REST API:

```bash
# Submit a test
curl -s "http://your-server/runtest.php?f=json&url=https://www.yoursite.com&location=Test"

# Check test status
curl -s "http://your-server/testStatus.php?f=json&test=TEST_ID"

# Get results
curl -s "http://your-server/xmlResult.php?test=TEST_ID"
```

## Google Lighthouse: The Baseline Auditor

**GitHub**: [GoogleChrome/lighthouse](https://github.com/GoogleChrome/lighthouse) — ⭐ 30,078 stars | Last updated: April 2026 | Language: JavaScript

Lighthouse is Google's open-source automated auditing tool. While it doesn't offer the same historical monitoring or multi-location testing as Sitespeed.io or WebPageTest, it provides the most authoritative audit of web best practices, accessibility, and SEO — directly from the company that builds Chrome and ranks websites.

### Key Features

- Five audit categories: Performance, Accessibility, Best Practices, SEO, and Progressive Web App
- Core Web Vitals scoring (LCP, FID/INP, CLS)
- Detailed opportunities list with estimated savings
- Accessibility audit with WCAG compliance checks
- SEO recommendations
- PWA compliance verification
- CI-friendly JSON output
- Puppeteer integration for custom flows

### Running Lighthouse

Lighthouse is typically installed via npm:

```bash
npm install -g lighthouse
```

Run an audit:

```bash
lighthouse https://www.yoursite.com --output html --output-path ./report.html
```

Generate a JSON report for CI integration:

```bash
lighthouse https://www.yoursite.com --output json --output-path ./report.json
```

### Docker Setup

Lighthouse doesn't ship an official Docker image, but you can create one easily:

```dockerfile
FROM node:20-slim

RUN apt-get update && apt-get install -y \
    chromium \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g lighthouse

ENTRYPOINT ["lighthouse"]
```

Build and run:

```bash
docker build -t lighthouse-selfhosted .

docker run --rm -v "$(pwd)/reports:/reports" \
  lighthouse-selfhosted \
  https://www.yoursite.com \
  --output html --output-path /reports/report.html \
  --chrome-flags="--no-sandbox --headless"
```

For production use, consider the community-maintained `patrickhulce/lighthouse` image or integrate Lighthouse into a Sitespeed.io pipeline (which includes it by default).

## Feature Comparison

| Feature | Sitespeed.io | WebPageTest | Lighthouse |
|---------|-------------|-------------|------------|
| **Stars** | 4,974 | 3,244 | 30,078 |
| **License** | MIT | BSD-2-Clause | Apache 2.0 |
| **Real browser testing** | ✅ Chrome, Firefox | ✅ Chrome, Edge, custom | ✅ Chrome only |
| **Core Web Vitals** | ✅ Full support | ✅ Full support | ✅ Full support |
| **Historical monitoring** | ✅ Grafana/Graphite | ✅ Via API + storage | ❌ Single runs only |
| **Multi-location testing** | ✅ Via Docker agents | ✅ Multiple test agents | ❌ Local only |
| **Waterfall charts** | ✅ Detailed | ✅ Industry best | ❌ No waterfall |
| **Filmstrip views** | ✅ 100ms intervals | ✅ 100ms intervals | ❌ Not available |
| **Video recording** | ✅ Built-in | ✅ Built-in | ❌ Not available |
| **CI/CD integration** | ✅ Budget files | ✅ REST API | ✅ JSON output |
| **Accessibility audit** | Via Lighthouse plugin | Limited | ✅ Full WCAG audit |
| **SEO audit** | Via Lighthouse plugin | ❌ | ✅ Full SEO audit |
| **Traffic shaping** | ✅ Via WebPageReplay | ✅ Built-in (3G/4G/custom) | ❌ Limited |
| **Custom metrics** | ✅ JavaScript | ✅ JavaScript | ✅ Via plugins |
| **Docker compose** | ✅ Full stack (Grafana+Graphite) | ✅ Full stack (web+agent) | ❌ DIY image |
| **Performance budgets** | ✅ Budget.json | ⚠️ Via API checks | ⚠️ Via score thresholds |
| **Multi-page scripts** | ✅ Scripted navigation | ✅ Test scripts | ❌ Single page |
| **Setup complexity** | Medium | High | Low |
| **Best for** | Continuous monitoring | Deep analysis per test | Quick audits & CI checks |

## Choosing the Right Tool

Your choice depends on your monitoring goals:

**Choose Sitespeed.io** if you want a complete, out-of-the-box monitoring stack. The Grafana integration gives you beautiful dashboards, historical trend analysis, and alerting capabilities. It's the best choice for teams that need to track performance over time and catch regressions early. Sitespeed.io can also include Lighthouse audits in its test runs, giving you the best of both worlds.

**Choose WebPageTest** if you need the deepest possible analysis of individual page loads. The waterfall charts, connection views, and filmstrip comparisons are unmatched. It's the tool of choice for performance engineers who need to diagnose specific bottlenecks — slow DNS lookups, render-blocking resources, or third-party script impact.

**Choose Lighthouse** if you need quick, lightweight audits focused on best practices, accessibility, and SEO compliance. It's ideal for CI pipelines where you want a pass/fail gate on every pull request. For full performance monitoring, consider wrapping Lighthouse in a Sitespeed.io pipeline rather than running it standalone.

## Integrating Performance Monitoring into Your Pipeline

For a comprehensive monitoring strategy, combine these tools:

1. **Lighthouse in CI** — Run on every pull request to catch performance regressions before merge
2. **Sitespeed.io for continuous monitoring** — Schedule hourly tests with Grafana dashboards and alerts
3. **WebPageTest for deep diagnostics** — Use when a regression is detected to identify the root cause

A typical setup uses Sitespeed.io as the primary monitoring engine (it includes Lighthouse by default) with Grafana dashboards for visualization. If you need to add more test locations, deploy additional Sitespeed.io agents and point them at the same Graphite backend.

For API-level monitoring that complements your page-level performance tests, consider pairing with an [endpoint monitoring solution like Gatus or Smokeping](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/). And if you're optimizing web performance, deploying a [self-hosted CDN with Varnish or Squid](../self-hosted-cdn-edge-caching-varnish-traffic-server-squid-nginx-guide/) can dramatically improve response times.

## FAQ

### Can I run Sitespeed.io, WebPageTest, and Lighthouse on the same server?

Yes, but resource requirements vary significantly. Sitespeed.io with Grafana and Graphite needs at least 4GB RAM. WebPageTest with a browser agent needs 2-4GB per agent. Lighthouse alone needs about 1GB. A single 8GB server can comfortably run Sitespeed.io's full stack plus a Lighthouse container, but adding WebPageTest agents may require 16GB or more depending on test frequency.

### Do I need to configure Grafana separately with Sitespeed.io?

No — the official Docker compose stack includes pre-provisioned Grafana dashboards. When you run `docker compose up`, Grafana starts with Sitespeed.io's dashboards already configured. You only need to customize them if you want to add custom panels or change thresholds.

### How often should I run performance tests?

For production monitoring, every 1-4 hours is typical. For staging environments tied to your CI/CD pipeline, run on every deployment. Sitespeed.io supports cron scheduling via its built-in scheduler, and WebPageTest can be triggered via API from any cron job or CI system.

### Can WebPageTest test pages behind authentication?

Yes — you can configure authentication cookies, HTTP headers, or custom scripts that log in before the test begins. WebPageTest's scripting API supports `navigate`, `setValue`, `click`, and `exec` commands to handle complex login flows. This makes it ideal for testing internal dashboards and admin panels.

### Does Lighthouse work on single-page applications (SPAs)?

Lighthouse works well with SPAs, but you need to ensure the page is fully loaded before the audit begins. Use the `--preset=full` flag for a more thorough audit that waits for network idle. For SPAs with client-side routing, Sitespeed.io's scripting support lets you navigate through multiple routes in a single test session.

### How do I alert on performance regressions?

Sitespeed.io's budget feature is the simplest approach: define thresholds in a `budget.json` file and the tool will exit with a non-zero code when thresholds are violated. In Grafana, you can set up alert rules on any metric panel to send notifications via Slack, email, or webhooks when performance degrades beyond acceptable limits.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Sitespeed.io vs WebPageTest vs Lighthouse: Self-Hosted Web Performance Monitoring 2026",
  "description": "Compare three leading open-source web performance testing tools — Sitespeed.io, WebPageTest, and Google Lighthouse — with self-hosted Docker deployment guides, feature comparisons, and practical monitoring setups.",
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
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
