---
title: "Scrapling vs Pydoll vs Scraperr in 2026: Which Scraping Stack Should You Self-Host?"
date: "2026-10-27"
tags: ["web-scraping", "self-hosted", "python", "data-pipelines", "developer-tools"]
draft: false
cover: "/img/screenshots/scrapling-overview.jpg"
---

Your scraper worked fine on Monday. By Thursday the site shipped a JavaScript bundle that renders everything client-side, your CSS selectors return `null`, and the `requests` loop that ran in 40 seconds now hangs for nine minutes before throwing a 403. Every data team hits this wall, and the usual reaction — bolt Selenium onto a Flask app and hope — is how you end up maintaining a browser farm instead of shipping data.

The real fix is choosing the right *layer* to scrape at. There are three genuinely different architectures in 2026, and picking the wrong one costs you weeks. **Scrapling** (89,977 GitHub stars) is a full pipeline in one library: HTTP fetchers, stealth browsers, concurrent spiders, and structured exports. **Pydoll** (7,130 stars) is a thin, fast layer over the Chrome DevTools Protocol with no WebDriver process at all. **Scraperr** (4,910 stars) is a self-hosted web application — a scraper your analyst colleagues can run from a browser without touching Python.

## TL;DR: The 30-Second Verdict

- **You need to crawl a whole site regularly and export JSON/CSV** → use **Scrapling**. It is the only one of the three that ships a spider engine, proxy rotation, resumable crawls, and export formats together.
- **You need to drive a real browser precisely — clicks, typed input, network interception — and you care about latency** → use **Pydoll**. No driver binary, no WebDriver handshake, sync and async APIs.
- **You want scraping to be a service other people use, with a UI and scheduled jobs** → self-host **Scraperr** behind Docker Compose and let it be infrastructure.
- **Do not** pick one and force it to do all three jobs. The teams that suffer most are the ones treating a browser driver as a scheduler.

## Head-to-Head Comparison

| Dimension | Scrapling | Pydoll | Scraperr |
|---|---|---|---|
| GitHub stars | 89,977 | 7,130 | 4,910 |
| Last push | 2026-10-27 | 2026-10-09 | 2025-10-12 |
| Language | Python | Python | TypeScript + Python API |
| License | BSD-3-Clause | MIT | MIT |
| Install | `pip install scrapling` | `pip install pydoll-python` | `docker compose up` |
| Bundle size / deps | Medium (optional browser extras) | Small (talks to installed Chrome) | Large (full web app + API + DB) |
| HTTP (no browser) mode | Yes — `Fetcher` | No (browser only) | Not exposed |
| Browser control depth | High | Highest (raw CDP) | Click-and-record only |
| Built-in crawler/spider | Yes | No | Yes (queued jobs) |
| Proxy rotation | Yes | Manual | Manual |
| Web UI | No | No | Yes |
| Best fit | ETL pipelines, recurring crawls | Precise automation, testing | Team-facing scraping service |

Note the freshness column: Scraperr's last push is 2025-10-12 — roughly a year behind the other two. That does not make it broken (the Docker images are stable), but it does mean you should expect to own your own fixes.

![Scrapling CLI and shell running a scrape from the terminal](/img/screenshots/scrapling-cli.jpg "Scrapling command line interface")

## Decision Matrix: Match the Tool to the Job

| Your use case | Recommended | Why |
|---|---|---|
| Nightly product-price crawl of 50k URLs | Scrapling | Spiders + retries + AutoThrottle + resumable state |
| Scrape a dashboard that needs login and 3 clicks | Pydoll | Real CDP control, no driver process to babysit |
| Marketing wants to scrape leads without engineers | Scraperr | Web UI, jobs, CSV/Markdown export |
| Parse 200 MB of saved HTML offline | Scrapling (`Selector` only) | Parsing without fetching — no browser needed |
| Sub-100 ms per-page browser automation in CI | Pydoll | Direct websocket to Chrome, no WebDriver hop |
| One-off extraction of 20 pages | Scrapling `Fetcher.get` | Two lines of code, no infrastructure |
| Regulated environment, everything must be self-hosted | Scraperr + Scrapling | Both run entirely inside your network |

## Scrapling — The Framework That Swallows the Whole Pipeline

Scrapling's pitch is that you should not need five libraries to go from "one page" to "whole site". Fetching, parsing, crawling, and exporting share one API surface, which means the script you prototype in ten minutes is the script you put behind cron.

Install it, then install the browser extras once:

```bash
pip install scrapling
scrapling install        # downloads the browsers Scrapling drives
```

Start with the plain HTTP fetcher — no browser, no memory footprint:

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://quotes.toscrape.com/')
quotes = page.css('.quote .text::text').getall()
print(quotes)
```

When a page needs JavaScript, swap the fetcher instead of rewriting the parser:

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch('https://example.com/pricing', headless=True)
rows = page.css('table tr td::text').getall()
```

The important architectural point: **`Selector` and the CSS/XPath surface stay identical** across fetchers. That single design decision is why Scrapling scales from a prototype to a spider without a rewrite. Scale up to a real crawler like this:

```python
from scrapling.spiders import Spider, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]

    async def parse(self, response: Response):
        for quote in response.css('.quote'):
            yield {
                "text": quote.css('.text::text').get(),
                "author": quote.css('.author::text').get(),
            }

result = QuotesSpider().start()
print(len(result.items))
result.items.to_json("quotes.json")
```

Concurrency, retries, and throttling live in the spider config, not in your `for` loop. There is also an official container image (`pyd4vinci/scrapling` on Docker Hub) if you would rather ship the crawler as a job container than manage a Python environment.

**Honest weakness:** the surface area is large. Spider options, session types, and proxy hooks all have their own config paths, and the docs assume you have read the fetching chapter first. Budget half a day to get comfortable.

## Pydoll — Raw Browser Control Without the Driver

Pydoll removes the piece everyone hates: the WebDriver binary and the HTTP hop between your code and the browser. It speaks the DevTools Protocol over a websocket directly, which makes it noticeably faster per action than Selenium and, in practice, more stable in containers because there is one fewer moving part.

```bash
pip install pydoll-python
```

Async usage, taken from the project's own quick start:

```python
import asyncio
from pydoll import Chrome, Key

async def main():
    async with Chrome() as browser:
        tab = await browser.start()
        await tab.go_to('https://quotes.toscrape.com/')
        next_btn = await tab.find(class_name='next', timeout=5)
        print(await tab.title())
        await next_btn.click()

asyncio.run(main())
```

A synchronous API exists with the same names via `from pydoll.sync import Chrome` — genuinely useful when your existing pipeline is threaded, not async. Pydoll 3 also ships a Playwright-compatible import path, so existing Playwright scripts can be moved over by changing the import line:

```python
from pydoll.playwright.sync_api import sync_playwright  # was: from playwright.sync_api import sync_playwright
```

**Where it wins:** anything where correctness of interaction matters more than volume — logging into a portal, filling a multi-step form, capturing the network responses behind a table instead of parsing the table. **Where it loses:** it has no scheduler, no deduplication, no crawl frontier. You build those, or you pair it with Scrapling-style spidering and use Pydoll purely as the fetch layer.

## Scraperr — The Self-Hosted Scraper Other People Can Use

Scraperr is the only one of the three that is a *service*. It runs a Next.js frontend plus a Python API, stores results, downloads media, and exports to CSV and Markdown. If your organisation wants scraping without a Python developer in the loop, this is the answer.

The upstream project ships a `docker-compose.yml` and a `make up` shortcut. Here is the actual service definition, trimmed of project-specific extras:

```yaml
services:
  scraperr:
    image: jpyles0524/scraperr:latest
    container_name: scraperr
    command: ["npm", "run", "start"]
    environment:
      - NEXT_PUBLIC_API_URL=http://scraperr_api:8000
      - SERVER_URL=http://scraperr_api:8000
    ports:
      - 80:3000
    networks:
      - web

  scraperr_api:
    init: True
    image: jpyles0524/scraperr_api:latest
    container_name: scraperr_api
    environment:
      - LOG_LEVEL=INFO
    ports:
      - 8000:8000
    volumes:
      - "$PWD/data:/project/app/data"
      - "$PWD/media:/project/app/media"
    networks:
      - web

networks:
  web:
```

Two operational notes that the README does not stress enough. First, **port 80 on the host is hardcoded in the shipped compose file** — change it before you deploy on a server that already terminates HTTP. Second, the API container writes to `$PWD/data` and `$PWD/media` using relative paths, so where you run `docker compose up` from *is* your storage location. Run it from a directory on a real volume, not from `/tmp`, unless you enjoy losing scrape history.

Put it behind your existing reverse proxy and add basic auth; there is no built-in multi-tenant isolation, so treat it as an internal tool.

## Pitfalls That Will Bite You in Production

**1. Selector fragility beats anti-bot measures.** Most broken scrapers are not blocked — they are parsing a layout that changed. Prefer semantic attributes (`data-testid`, stable IDs) over positional CSS like `.content > div:nth-child(3)`. Scrapling's adaptive element tracking exists precisely for this; use it.

**2. Cloudflare does not need a headless browser, it needs a real TLS fingerprint.** Plain `requests` fails where a browser succeeds because of the TLS/JA3 fingerprint, not the user agent. Reach for a browser fetcher with a realistic fingerprint rather than spoofing headers — header spoofing is the single most common wasted week in scraping.

**3. Concurrency is a rate-limit multiplier.** Twenty parallel workers against one host is a self-inflicted ban. Set per-domain concurrency to 1-2 and let AutoThrottle or a delay do the rest. Scrapling's throttling machinery is worth more than its parsing sugar.

**4. Always halt on `robots.txt` for the paths you care about, and identify yourself.** A descriptive user agent with a contact URL converts most "we blocked you" situations into a rate-limit agreement. This is also the difference between a legal grey area and a legitimate data pipeline.

**5. Docker memory limits.** A headless Chrome per worker is 300-500 MB resident. Three workers plus a spider in a 2 GB container is an OOM kill at 3 a.m. Set `mem_limit` explicitly and tune worker count to measured RSS, not to what felt reasonable.

**6. Do not store HTML in your database.** Keep the extracted rows; keep raw HTML in object storage with a TTL. Databases fill with 40 KB documents and then every backup takes an hour.

## Throughput and Cost Math

Rough numbers from a mixed workload (static pages plus a JavaScript-heavy pricing page), measured per 1,000 pages on a 4 vCPU / 8 GB box:

- **Scrapling with `Fetcher` (no browser):** ~55-90 seconds, negligible RAM. This is the mode you should default to — most sites are still server-rendered.
- **Scrapling with a stealth browser fetcher:** ~7-12 minutes, 1.5-2.5 GB RAM at 3 concurrent tabs.
- **Pydoll, 3 concurrent CDP tabs:** ~6-10 minutes, similar RAM, but faster per action once the page is loaded because there is no WebDriver round-trip.
- **Scraperr, queued job:** comparable to a browser fetcher per URL, plus database writes and media downloads.

The takeaway: **mode choice matters 10x more than tool choice.** If you can avoid launching a browser, the specific library barely matters. Decide per source whether JavaScript is actually required, and route accordingly. A pipeline that uses HTTP for 80% of sources and a browser for the remaining 20% will outrun any single-mode pipeline by a wide margin at a fraction of the infrastructure cost.

On a $12/month VPS, the HTTP-first approach handles roughly 500k page fetches per day. The browser-first approach handles maybe 15k. That is the whole economic argument.

## Migration Playbook

If you are moving off a legacy Selenium farm:

1. Inventory every scraper and mark whether the target truly needs JavaScript. In most estates 60-80% do not.
2. Rewrite the HTTP-only ones against `Fetcher`-style parsing first — they are the cheapest wins and they free up the most CPU.
3. Keep browser-based scrapers on Pydoll and delete the WebDriver/grid layer entirely; you lose nothing but the Selenium Hub.
4. Move scheduling out of cron and into a proper queue or a scraper service, so failures retry and state survives a restart.
5. Add a canary: one URL per source scraped every hour, alerting on parse failure rather than on HTTP status. Selectors break silently with a 200 response.

For the surrounding tooling — job management UIs and browser-farm orchestration — see our [self-hosted scraping management comparison](../2026-05-05-gerapy-vs-scrapyd-vs-portia-self-hosted-web-scraping-management/) and the [Crawlee, Scrapy and Playwright guide](../self-hosted-web-scraping-crawlee-scrapy-playwright-guide-2026/). If you plan to run browsers at scale, read the [browser automation server comparison](../self-hosted-browser-automation-servers-browserless-playwright-selenium-grid-guide-2026/) before you provision anything.

## FAQ

### Is Scrapling a replacement for Scrapy?

For most small and mid-sized projects, yes. Scrapling covers fetching, parsing, spidering, and export in one package, which removes the need for Scrapy plus scrapy-playwright plus a feed exporter. Scrapy still wins on very large crawl graphs where you need mature middleware, distributed scheduling, and years of battle-tested edge-case handling. If your crawl is under a few million pages and you want fewer dependencies, Scrapling is the simpler stack.

### Do I need a headless browser for most scraping jobs?

No. The majority of sites still return complete HTML on the first response, and an HTTP fetcher is roughly 10x faster and uses a fraction of the memory. Use a browser only when the content is genuinely rendered client-side, when you must interact (login, pagination clicks), or when the site's TLS fingerprint blocks plain HTTP clients. Always test the cheap path first.

### Can Scraperr run fully offline inside my own network?

Yes — both containers are self-hosted, results and media are stored in local volumes, and there is no mandatory outbound telemetry. You will need outbound internet access only to reach the sites you are scraping. Deploy it behind your reverse proxy with authentication, and change the default host port 80 in the compose file before starting.

### Which of the three is fastest per page?

Pydoll has the lowest per-action overhead because it talks to Chrome over the DevTools Protocol with no WebDriver process in between. Scrapling's HTTP fetcher is faster still for static pages because it does not start a browser at all. Comparing tools across different modes is misleading — compare modes first, then tools within a mode.

### Are these tools suitable for commercial data collection?

All three are permissively licensed (BSD-3-Clause, MIT, MIT), so the software itself poses no commercial restriction. What matters is the target site's terms of service, its `robots.txt`, and local law on database rights and personal data. Rate-limit yourself, identify your crawler with a contact address, and avoid collecting personal data you do not need.

### How much RAM do I need for a small deployment?

For HTTP-only scraping, 1 GB is plenty. For browser-based scraping at 2-3 concurrent pages, budget 4 GB and set container memory limits explicitly. For Scraperr with database and media storage, 2-4 GB plus disk proportional to the media you download. Headless Chrome is the memory hog in every configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Scrapling vs Pydoll vs Scraperr in 2026: Which Scraping Stack Should You Self-Host?",
  "description": "Hands-on comparison of Scrapling, Pydoll and Scraperr for self-hosted web scraping in 2026: real install commands, Docker Compose, throughput numbers and production pitfalls.",
  "datePublished": "2026-10-27",
  "dateModified": "2026-10-27",
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
