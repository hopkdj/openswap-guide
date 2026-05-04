---
title: "Gerapy vs Scrapyd vs Portia: Self-Hosted Web Scraping Management Platforms 2026"
date: 2026-05-05
tags: ["comparison", "guide", "self-hosted", "web-scraping", "scrapy", "data-collection", "crawler"]
draft: false
description: "Compare self-hosted web scraping management platforms — Gerapy, Scrapyd, and Portia — for deploying, monitoring, and managing Scrapy spiders at scale."
---

Web scraping at a single-project scale is straightforward: write a Scrapy spider, run it from the command line, collect the results. But when you need to manage dozens of spiders across multiple projects, schedule recurring crawls, monitor execution status, and scale across distributed workers, a management platform becomes essential. Self-hosted scraping management gives you full control over crawl schedules, data storage, proxy rotation, and rate limiting — without depending on expensive cloud scraping services.

In this guide, we compare three open-source web scraping management solutions: **Gerapy** (a distributed crawler management framework built on Scrapy, Scrapyd, Django, and Vue.js), **Scrapyd** (the official Scrapy daemon for deploying and controlling spiders), and **Portia** (a visual scraping tool by Scrapinghub that lets you build spiders without writing code). Each serves different technical skill levels and operational requirements.

## Quick Comparison

| Feature | Gerapy | Scrapyd | Portia |
|---------|--------|---------|--------|
| **Language** | Python (Django + Vue.js) | Python | Python |
| **GitHub Stars** | 3,500+ | 3,000+ | 9,400+ |
| **Web UI** | ✅ Full dashboard | ❌ API only | ✅ Visual builder |
| **Spider Builder** | ❌ Code only | ❌ Code only | ✅ Point-and-click |
| **Deployment** | ✅ One-click deploy | ✅ Via scrapyd-deploy | ✅ Via UI |
| **Scheduling** | ✅ Built-in cron | Via scrapyd-schedule | ❌ |
| **Monitoring** | ✅ Dashboard with logs | API endpoints | ✅ UI with live preview |
| **Multi-Project** | ✅ Project management | ✅ Multiple eggs | ✅ Project workspaces |
| **Distributed Crawling** | ✅ Multiple workers | ✅ Multiple Scrapyd instances | ❌ Single instance |
| **Data Export** | ✅ Built-in viewer | Raw JSON/CSV | ✅ Export to CSV/JSON |
| **Last Updated** | Oct 2024 | Apr 2026 | Jun 2024 |

## Gerapy — Distributed Crawler Management Framework

Gerapy is a comprehensive web scraping management platform built on Scrapy, Scrapyd, Django, and Vue.js. It provides a full web dashboard for managing spider projects, deploying to distributed workers, scheduling recurring crawls, and monitoring execution results — all from a single interface.

**Key strengths:**

- **Complete management stack** — project creation, code editing, deployment, scheduling, and monitoring in one platform
- **Distributed architecture** — manage multiple Scrapyd worker nodes from a central dashboard, distributing crawls across servers
- **Built-in scheduling** — cron-like scheduling interface for recurring spider execution without external tools
- **Code editor** — web-based code editor for modifying spider source code directly in the browser
- **Result visualization** — view scraped data in the browser with filtering and export capabilities
- **Project templates** — starter templates for common scraping patterns

**Limitations:**

- Requires Scrapyd workers — Gerapy is the management layer; actual crawling happens on Scrapyd nodes
- Less active development — last significant update was in late 2024
- Resource-heavy — Django + Vue.js stack needs more memory than Scrapyd alone

### Install Gerapy

```bash
# pip
pip3 install gerapy

# Initialize and start
gerapy init
cd gerapy
gerapy migrate
gerapy runserver 0.0.0.0:8000

# Create a Scrapyd worker
pip3 install scrapyd
scrapyd
```

### Docker Compose for Gerapy

```yaml
version: "3.8"
services:
  gerapy:
    image: gerapy/gerapy:latest
    ports:
      - "8000:8000"
    volumes:
      - ./gerapy:/app/gerapy
      - ./projects:/app/projects
    environment:
      - GERAPY_DATABASE_URL=sqlite:////app/gerapy/db.sqlite3
  scrapyd-worker1:
    image: vimagick/scrapyd:latest
    ports:
      - "6800:6800"
    volumes:
      - scrapyd-data1:/data
  scrapyd-worker2:
    image: vimagick/scrapyd:latest
    ports:
      - "6801:6800"
    volumes:
      - scrapyd-data2:/data
volumes:
  scrapyd-data1:
  scrapyd-data2:
```

### Example: Deploy a spider via Gerapy API

```bash
# After setting up Gerapy, use the API to manage workers
# Add a Scrapyd worker to Gerapy
curl -X POST http://localhost:8000/api/worker \
  -H "Content-Type: application/json" \
  -d '{"name": "worker1", "ip": "scrapyd-worker1", "port": 6800}'

# Deploy a spider project
curl -X POST http://localhost:8000/api/project/deploy \
  -H "Content-Type: application/json" \
  -d '{"project": "my-spider", "worker_id": 1}'

# Schedule a recurring crawl
curl -X POST http://localhost:8000/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"project": "my-spider", "spider": "main", "cron": "0 2 * * *"}'
```

## Scrapyd — Official Scrapy Daemon

Scrapyd is the official daemon service for deploying and running Scrapy spiders. It provides a JSON API for deploying spider packages (eggs), scheduling crawls, monitoring status, and canceling jobs. While it lacks a web UI by default, its lightweight design and official Scrapy integration make it the foundation for many custom scraping platforms.

**Key strengths:**

- **Official Scrapy integration** — maintained by the Scrapy team, guaranteed compatibility with Scrapy features
- **Lightweight** — minimal resource footprint, runs comfortably on a 512 MB VM
- **JSON API** — full programmatic control over deployment, scheduling, and monitoring
- **Spider versioning** — deploys spiders as versioned eggs, enabling rollback to previous versions
- **Multiple instances** — run multiple Scrapyd daemons across servers and manage them centrally
- **Simple setup** — single command to start, no database or framework dependencies

**Limitations:**

- No built-in web UI — terminal and API only (third-party dashboards exist)
- No built-in scheduling — requires external cron or scrapyd-schedule
- No data visualization — results are stored as files on disk
- Manual deployment — requires `scrapyd-deploy` command-line tool

### Install Scrapyd

```bash
# pip
pip3 install scrapyd scrapyd-client

# Start the daemon
scrapyd --logfile /var/log/scrapyd.log &

# Deploy a spider
cd my-spider-project
scrapyd-deploy -p my-spider
```

### Docker Compose for Scrapyd

```yaml
version: "3.8"
services:
  scrapyd:
    image: vimagick/scrapyd:latest
    ports:
      - "6800:6800"
    volumes:
      - scrapyd-eggs:/eggs
      - scrapyd-logs:/logs
      - ./scrapyd.conf:/etc/scrapyd/scrapyd.conf:ro
    environment:
      - SCRAPYD_BIND_ADDRESS=0.0.0.0
volumes:
  scrapyd-eggs:
  scrapyd-logs:
```

### scrapyd.conf configuration

```ini
[scrapyd]
eggs_dir    = /eggs
logs_dir    = /logs
items_dir   = /items
jobs_to_keep = 50
max_proc    = 10
max_proc_per_cpu = 4
finish_to_keep = 100
poll_interval = 5
bind_address = 0.0.0.0
http_port   = 6800
```

### Example: Manage spiders via API

```bash
# List deployed projects
curl http://localhost:6800/listprojects.json

# List spiders in a project
curl http://localhost:6800/listspiders.json?project=my-spider

# Schedule a crawl
curl http://localhost:6800/schedule.json \
  -d project=my-spider -d spider=main

# Check job status
curl http://localhost:6800/listjobs.json?project=my-spider

# Cancel a running job
curl http://localhost:6800/cancel.json \
  -d project=my-spider -d job=<job-id>

# Delete a project version
curl http://localhost:6800/delversion.json \
  -d project=my-spider -d version=r1
```

## Portia — Visual Web Scraping Tool

Portia is a visual web scraping platform by Scrapinghub (now Zyte) that lets you build Scrapy spiders without writing code. Using a point-and-click interface, you annotate web pages to define what data to extract, and Portia generates the corresponding Scrapy spider automatically.

**Key strengths:**

- **No-code spider builder** — visually annotate pages to define extraction rules, no Python required
- **Live preview** — see extracted data in real-time as you configure selectors
- **Automatic spider generation** — exports standard Scrapy spiders you can run independently
- **Template-based** — handles pagination, item lists, and nested data through visual templates
- **Slybot engine** — built on Scrapy's Slybot, supporting JavaScript-rendered pages via Splash
- **Lower technical barrier** — non-developers can build and maintain scrapers

**Limitations:**

- Less flexible than hand-written spiders — complex logic requires code
- Single-instance architecture — no built-in distributed crawling
- Less active development — last major update in 2024
- Requires Splash for JavaScript pages — additional service dependency

### Install Portia

```bash
# Docker (recommended)
docker run -d -p 9001:9001 scrapinghub/portia

# From source
git clone https://github.com/scrapinghub/portia.git
cd portia
docker compose up
```

### Docker Compose for Portia

```yaml
version: "3.8"
services:
  portia:
    image: scrapinghub/portia:latest
    ports:
      - "9001:9001"
    volumes:
      - portia-projects:/app/data/projects
  splash:
    image: scrapinghub/splash:latest
    ports:
      - "8050:8050"
    command: --max-timeout 300
volumes:
  portia-projects:
```

### Example: Using Portia

1. Open `http://localhost:9001` in your browser
2. Create a new project and enter the target URL
3. Portia loads the page in its built-in browser
4. Click on elements you want to extract — Portia generates CSS selectors automatically
5. Configure pagination by clicking the "next" button link
6. Save the project — Portia generates a Scrapy spider you can export and run independently

## Choosing the Right Scraping Platform

| Use Case | Recommended Tool | Why |
|----------|-----------------|-----|
| **Distributed crawling at scale** | Gerapy | Multi-worker management, scheduling dashboard |
| **Lightweight spider deployment** | Scrapyd | Minimal footprint, official Scrapy integration |
| **Non-technical team members** | Portia | Visual builder, no coding required |
| **Recurring scheduled crawls** | Gerapy | Built-in cron scheduling interface |
| **API-driven automation** | Scrapyd | Clean JSON API, easy to integrate |
| **Quick prototyping** | Portia | Visual annotation, instant spider generation |
| **Custom scraping platform** | Scrapyd + custom UI | Scrapyd as the engine, build your own dashboard |

## Why Self-Host Your Scraping Infrastructure?

Running your own scraping management platform offers significant advantages over cloud scraping services:

**Data ownership:** Scraped data stays on your infrastructure. For competitive intelligence, market research, or compliance-sensitive data collection, keeping everything in-house eliminates third-party data exposure.

**Cost control:** Cloud scraping services charge per-page or per-GB of extracted data. At scale, these costs exceed the price of a small VM running Scrapyd or Gerapy. Self-hosting gives you unlimited crawls for a fixed infrastructure cost.

**Proxy flexibility:** Self-hosted platforms let you integrate your own proxy rotation strategy — residential proxies, datacenter proxies, or Tor — without being locked into a provider's proxy network.

**Custom rate limiting:** Control exactly how fast you crawl each target domain. Respect `robots.txt`, implement polite delays, and avoid getting blocked by overly aggressive scraping.

For teams that also run [web performance monitoring](../2026-04-21-sitespeedio-vs-webpagetest-vs-lighthouse-self-hosted-web-performance-monitoring-2026/), combining scraping with performance testing gives you a complete picture of how your competitors' sites are performing — both in content and speed. And when you need to [monitor your own site's link health](../2026-05-05-lychee-vs-muffet-vs-linkchecker-self-hosted-broken-link-checkers-guide/), the same crawling infrastructure can serve dual purposes.

## FAQ

### What is the difference between Gerapy, Scrapyd, and Portia?

Gerapy is a full management platform with a web dashboard, distributed worker management, and built-in scheduling — it uses Scrapyd as its crawling engine. Scrapyd is the lightweight daemon that runs Scrapy spiders and provides a JSON API for deployment and control, but has no web UI. Portia is a visual spider builder that generates Scrapy spiders through point-and-click page annotation, requiring no coding.

### Can I run these tools without Scrapy knowledge?

Portia is designed for users without Scrapy or Python experience — its visual builder generates spiders automatically. Scrapyd and Gerapy require you to write Scrapy spiders in Python, though Gerapy provides code templates and a web editor to simplify development.

### How do I scale scraping across multiple servers?

Gerapy natively supports multiple Scrapyd worker nodes — add workers through the dashboard and distribute crawls across them. With standalone Scrapyd, run multiple instances on different servers and use a load balancer or custom orchestrator to distribute `schedule.json` requests. Portia does not support distributed crawling.

### Can I scrape JavaScript-rendered pages?

Scrapyd runs Scrapy spiders, which by default only handle static HTML. For JavaScript-rendered pages, integrate Splash (a JavaScript rendering service) or use Scrapy-Playwright. Portia supports JavaScript pages when paired with a Splash instance. Gerapy inherits the capabilities of its underlying Scrapyd workers.

### How do I schedule recurring crawls?

Gerapy has built-in cron scheduling through its web interface. For Scrapyd, use `scrapyd-schedule` or a system cron job that calls the `schedule.json` API endpoint. Portia does not have built-in scheduling — export the generated spider and schedule it externally.

### Is self-hosted scraping legal?

Scraping publicly available web data is generally legal in most jurisdictions, but you must respect `robots.txt`, avoid overloading target servers, and comply with data protection regulations (GDPR, CCPA) for personal data. Always review the target site's terms of service and consult legal counsel for commercial scraping operations.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Gerapy vs Scrapyd vs Portia: Self-Hosted Web Scraping Management Platforms 2026",
  "description": "Compare self-hosted web scraping management platforms — Gerapy, Scrapyd, and Portia — for deploying, monitoring, and managing Scrapy spiders at scale.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
