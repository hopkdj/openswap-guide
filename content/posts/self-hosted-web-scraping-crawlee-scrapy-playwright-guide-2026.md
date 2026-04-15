---
title: "Complete Guide to Self-Hosted Web Scraping: Crawlee vs Scrapy vs Playwright 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "automation"]
draft: false
description: "Build your own web scraping infrastructure in 2026. Compare Crawlee, Scrapy, and Playwright for self-hosted data extraction with Docker setup, proxy rotation, and ethical scraping practices."
---

Every organization needs data. Some of it lives behind public websites that do not offer APIs. Web scraping is the practice of programmatically extracting information from web pages — prices, product listings, news articles, job postings, real estate data, or any structured content published on the internet. While cloud scraping services exist, they are expensive, impose usage limits, and send your requests through shared infrastructure where your scraping patterns may be fingerprinted and blocked. Running your own scraping stack gives you full control over scheduling, data storage, proxy rotation, and request patterns.

In this guide, we will explore the three most powerful open-source frameworks for building self-hosted web scraping pipelines in 2026: **Crawlee**, **Scrapy**, and **Playwright**. Each takes a fundamentally different approach, and understanding their strengths will help you pick the right tool for your specific use case.

## Why Build Your Own Scraping Infrastructure

Running web scraping on your own infrastructure offers advantages that cloud services simply cannot match.

**Cost savings at scale.** Cloud scraping platforms charge per page or per gigabyte of data extracted. A project that crawls fifty thousand pages per month can easily cost hundreds of dollars on a managed platform. Self-hosted scraping runs on a single VPS or home server, with the primary cost being your proxy subscription — typically ten to twenty dollars per month for a residential proxy pool.

**Full control over data.** When you scrape through a third-party service, the extracted data passes through their servers. If you are collecting anything sensitive — competitive intelligence, proprietary market data, or personal information that falls under privacy regulations — keeping the entire pipeline in your own environment eliminates that exposure.

**Custom logic and integrations.** Managed scraping services offer generic extraction. A self-hosted pipeline can integrate directly with your databases, trigger webhooks on specific conditions, apply custom parsing logic, and feed data straight into your analytics stack. You are not limited by what the platform supports.

**Reliable scheduling.** Cloud services often queue your requests behind other users. A self-hosted scraper runs on your schedule — every hour, every day at midnight, or triggered by events. No waiting, no rate sharing, no unexpected downtime from the provider's side.

**Stealth and fingerprinting control.** Shared scraping platforms use common browser fingerprints and IP ranges that target websites actively block. When you control your own infrastructure, you manage the user agent rotation, browser fingerprint, request headers, and timing patterns that determine whether your requests look like a real user or a bot.

**Offline data processing.** Extracted data can be processed, cleaned, and stored entirely within your network. This is essential for compliance with data residency requirements and for building pipelines where raw HTML, screenshots, and parsed data all need to be retained for auditing.

## Crawlee: The Modern JavaScript Scraping Framework

**Best for**: JavaScript-heavy sites, Node.js developers, production-grade crawlers

Crawlee is an open-source web scraping and crawling framework built in TypeScript and JavaScript. It was originally developed by the Apify team as the engine behind their cloud platform and was later released as a standalone library. In 2026, Crawlee has become one of the most popular choices for developers who need to scrape modern JavaScript-rendered websites.

### Key Features

- **Automatic browser management** — Crawlee handles headless browser instances, pooling, and cleanup automatically
- **Built-in anti-blocking** — Session rotation, user agent management, and fingerprint spoofing are built in
- **Multiple crawlers** — Choose between CheerioCrawler (fast HTML parsing), PuppeteerCrawler (Chrome), and PlaywrightCrawler (multi-browser)
- **Automatic retries** — Failed requests are retried with exponential backoff
- **Request queue and deduplication** — Manages URLs to visit and prevents duplicate crawling
- **Persistent state** — Can pause and resume crawls, storing progress to disk
- **Storage abstractions** — Built-in datasets, key-value stores, and request queue persistence
- **Scaling support** — Can scale horizontally across multiple machines with the same request queue backend

### Installation and Quick Start

```bash
# Install Crawlee with Playwright support
npm init crawlee my-scraper
cd my-scraper
npm install

# Run the boilerplate crawler
npm start
```

### Basic Crawler Example

```typescript
// src/main.ts
import { PlaywrightCrawler, Dataset } from 'crawlee';

const crawler = new PlaywrightCrawler({
  // Maximum concurrent browser tabs
  maxConcurrency: 10,

  // Respect robots.txt
  respectRobotsTxtFile: true,

  async requestHandler({ page, request, enqueueLinks, log }) {
    const title = await page.title();
    log.info(`Scraping: ${title} (${request.url})`);

    // Extract data from the page
    const data = await page.evaluate(() => {
      const items = document.querySelectorAll('.product-card');
      return Array.from(items).map(item => ({
        name: item.querySelector('.product-name')?.textContent?.trim(),
        price: item.querySelector('.price')?.textContent?.trim(),
        url: item.querySelector('a')?.href,
      }));
    });

    // Save to dataset (JSON file by default)
    await Dataset.pushData(...data);

    // Follow pagination
    await enqueueLinks({
      selector: 'a.pagination-next',
      label: 'next-page',
    });
  },
});

await crawler.run(['https://example-shop.com/products']);
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM apify/actor-node-playwright-chrome:latest

COPY package*.json ./
RUN npm install --omit=dev

COPY . ./
CMD ["npm", "start"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  scraper:
    build: .
    restart: unless-stopped
    volumes:
      - ./data:/home/node/app/storage
    environment:
      - CRAWLEE_MAX_CONCURRENCY=5
      - CRAWLEE_AUTOSCALED_MIN_CONCURRENCY=1
      - CRAWLEE_AUTOSCALED_MAX_CONCURRENCY=10
```

## Scrapy: The Battle-Tested Python Framework

**Best for**: High-throughput crawling, data pipelines, Python developers, large-scale extraction

Scrapy has been the dominant Python web scraping framework since 2008. It is fast, highly extensible, and has a massive ecosystem of plugins. If you need to crawl hundreds of thousands of pages and process the results through a data pipeline, Scrapy is the proven choice.

### Key Features

- **Asynchronous architecture** — Built on Twisted, handles hundreds of concurrent requests efficiently
- **Item pipelines** — Process extracted data through validation, deduplication, and storage stages
- **Middleware system** — Insert custom logic at any point in the request/response cycle
- **Built-in caching** — HTTP caching avoids re-downloading unchanged pages during development
- **Selectors** — XPath and CSS selectors via the parsel library
- **Extensive settings** — Fine-grained control over concurrency, delays, retries, and more
- **Rich ecosystem** — Scrapy-Playwright, Scrapy-Splash, Scrapy-Redis for distributed crawling

### Installation and Quick Start

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install Scrapy
pip install scrapy

# Create a new project
scrapy startproject myscraper
cd myscraper

# Generate a spider
scrapy genspider products example-shop.com

# Run the spider
scrapy crawl products -o output.json
```

### Spider Example

```python
# myscraper/spiders/products.py
import scrapy
from myscraper.items import ProductItem

class ProductSpider(scrapy.Spider):
    name = 'products'
    allowed_domains = ['example-shop.com']
    start_urls = ['https://example-shop.com/products']

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
    }

    def parse(self, response):
        for card in response.css('.product-card'):
            yield ProductItem(
                name=card.css('.product-name::text').get(),
                price=card.css('.price::text').get(),
                url=card.css('a::attr(href)').get(),
            )

        # Follow pagination
        next_page = response.css('a.pagination-next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  scrapy:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
      - ./data:/app/data
    command: >
      bash -c "
        pip install scrapy scrapy-playwright &&
        playwright install chromium &&
        scrapy crawl products -o /app/data/output.json
      "
    environment:
      - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
```

## Playwright: Browser Automation for Complex Pages

**Best for**: Sites requiring complex interaction, login workflows, dynamic content, screenshot capture

Playwright is a browser automation library developed by Microsoft. While not a scraping framework per se, it is the go-to tool when pages require JavaScript interaction — clicking buttons, filling forms, waiting for dynamic content, or bypassing complex anti-bot measures that simpler tools cannot handle.

### Key Features

- **Multi-browser support** — Chromium, Firefox, and WebKit with a single API
- **Auto-waiting** — Automatically waits for elements to be actionable before interacting
- **Network interception** — Modify requests and responses, block resources, capture API traffic
- **Multi-page handling** — Manage tabs, popups, and frames seamlessly
- **Tracing and debugging** — Built-in trace viewer for recording and replaying browser sessions
- **Mobile emulation** — Test and scrape mobile versions of websites
- **Authentication state** — Save and reuse login sessions across runs

### Installation

```bash
# Python version
pip install playwright
playwright install

# Node.js version
npm init playwright@latest
```

### Scraping Example with Python

```python
from playwright.sync_api import sync_playwright
import json

def scrape_dynamic_site():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
        )

        # Optional: load saved authentication state
        # context = browser.new_context(storage_state='auth.json')

        page = context.new_page()

        # Block images and fonts to speed up scraping
        page.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}', 
                   lambda route: route.abort())

        page.goto('https://example-shop.com/products', wait_until='networkidle')

        # Wait for dynamic content to load
        page.wait_for_selector('.product-card', timeout=10000)

        # Handle pagination through clicking
        products = []
        while True:
            cards = page.query_selector_all('.product-card')
            for card in cards:
                products.append({
                    'name': card.query_selector('.product-name').inner_text(),
                    'price': card.query_selector('.price').inner_text(),
                })

            # Try to click next page
            next_btn = page.query_selector('a.pagination-next')
            if not next_btn:
                break
            next_btn.click()
            page.wait_for_load_state('networkidle')

        browser.close()

        with open('products.json', 'w') as f:
            json.dump(products, f, indent=2)

        print(f'Extracted {len(products)} products')

scrape_dynamic_site()
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  playwright-scraper:
    image: mcr.microsoft.com/playwright/python:v1.50.0-jammy
    volumes:
      - .:/app
      - ./data:/app/data
    working_dir: /app
    command: python scraper.py
    shm_size: '1gb'
    deploy:
      resources:
        limits:
          memory: 2G
```

## Head-to-Head Comparison

| Feature | Crawlee | Scrapy | Playwright |
|---------|---------|--------|------------|
| **Language** | TypeScript/JS | Python | JS / Python |
| **Rendering** | Cheerio + Browser | HTTP only (+ Playwright plugin) | Full browser |
| **Speed (static pages)** | Very fast | Fastest | Slowest |
| **Speed (JS pages)** | Fast | Medium | Fast |
| **Auto-retry** | ✅ Built-in | ✅ Middleware | ❌ Manual |
| **Request queue** | ✅ Built-in | ✅ Scheduler | ❌ Manual |
| **Anti-blocking** | ✅ Session management | ⚠️ Plugins needed | ❌ Manual |
| **Scaling** | ✅ Horizontal | ✅ Scrapy-Redis | ❌ Manual |
| **Learning curve** | Low | Medium | Medium |
| **Best for** | JS sites, production crawlers | High-throughput, data pipelines | Complex interaction, screenshots |
| **Memory usage** | Medium (browser pool) | Low (async HTTP) | High (full browser) |
| **Storage** | Built-in datasets | Pipelines to any backend | Manual |
| **Robots.txt** | ✅ Respect | ⚠️ Middleware needed | ❌ Manual |

## Choosing the Right Tool

**Use Crawlee when** you need a production-ready scraping pipeline with minimal boilerplate. Its built-in request queue, automatic retries, session rotation, and storage make it the fastest path from zero to a reliable crawler. If your target sites use JavaScript rendering, Crawlee's Playwright and Puppeteer integrations handle them seamlessly.

**Use Scrapy when** you are processing large volumes of pages and need maximum throughput on static HTML. Scrapy's asynchronous architecture handles thousands of concurrent requests with minimal memory. Its pipeline system is ideal for multi-stage data processing — extract, validate, transform, and load in a single framework. For JavaScript-rendered pages, add the `scrapy-playwright` plugin.

**Use Playwright when** the target site requires complex browser interaction — logging in, filling multi-step forms, clicking through dynamic menus, or capturing screenshots of rendered pages. Playwright gives you pixel-level control over the browser, which is invaluable for sites that detect and block automated requests based on browser behavior patterns.

## Practical Scraping Architecture

A production-grade self-hosted scraping stack typically combines multiple tools. Here is a proven architecture:

```yaml
# docker-compose.yml — Full scraping stack
version: '3.8'
services:
  # Message queue for distributed scraping
  redis:
    image: redis:7-alpine
    ports:
      - '6379:6379'
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # Database for storing results
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: scraper
      POSTGRES_USER: scraper
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - '5432:5432'

  # Scraping workers
  crawler:
    build: ./crawlers
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://scraper:${DB_PASSWORD}@postgres:5432/scraper
      - PROXY_URL=http://proxy-user:${PROXY_PASS}@proxy.example.com:8080
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 3
    restart: unless-stopped

  # Dashboard for monitoring
  flower:
    image: mher/flower
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    ports:
      - '5555:5555'

volumes:
  redis_data:
  pg_data:
```

## Ethical Scraping Practices

Running your own scraping infrastructure comes with responsibility. Follow these practices to be a good citizen on the web:

**Respect robots.txt.** Both Crawlee and Scrapy can be configured to honor robots.txt directives. Crawlee does this by default. Enable it in Scrapy with `ROBOTSTXT_OBEY = True`.

**Set appropriate delays.** Do not hammer servers with hundreds of requests per second. Use `DOWNLOAD_DELAY` in Scrapy or configure `minConcurrency` and request delays in Crawlee. A two-to-five second delay between requests is usually reasonable.

**Identify yourself.** Include a descriptive User-Agent header with contact information. Site administrators are far more likely to tolerate scraping from an identifiable source than from a generic bot.

```python
# Scrapy settings.py
USER_AGENT = 'MyResearchBot/1.0 (+https://example.com/bot-info)'
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 3
CONCURRENT_REQUESTS_PER_DOMAIN = 2
```

**Cache aggressively.** If you need to re-process data, do not re-download pages you already have. Scrapy's HTTP cache middleware stores responses locally. Crawlee's storage persists crawled pages.

**Do not scrape personal data without consent.** Collecting and storing personally identifiable information may violate privacy laws in your jurisdiction. Consult legal guidance before building pipelines that process user data.

## Proxy Rotation and Anti-Detection

Even the best scraping framework will get blocked if every request comes from the same IP address. Proxy rotation is essential for production scraping.

```yaml
# Caddy reverse proxy for rotating outbound requests
# /etc/caddy/Caddyfile
:8080 {
    reverse_proxy {
        to proxy1.example.com:3128
        to proxy2.example.com:3128
        to proxy3.example.com:3128
        lb_policy random
    }
}
```

Use residential proxy providers for sites with aggressive anti-bot measures, and datacenter proxies for less restrictive targets. Most providers offer APIs to rotate IPs programmatically.

## Conclusion

Self-hosted web scraping gives you complete control over your data pipeline. Crawlee excels at modern JavaScript-heavy sites with minimal setup. Scrapy dominates when raw throughput and data processing pipelines are the priority. Playwright is indispensable for pages that require full browser interaction. In practice, many production stacks combine all three — Scrapy for high-volume static page crawling, Crawlee for JavaScript-rendered content, and Playwright for edge cases requiring complex browser automation. With Docker, Redis, and a PostgreSQL database, you can run a scraping operation that handles millions of pages per month for a fraction of the cost of any managed service.
