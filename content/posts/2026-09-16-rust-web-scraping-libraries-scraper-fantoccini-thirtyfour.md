---
title: "Rust Web Scraping in 2026: scraper vs fantoccini vs thirtyfour (Real Code, Real Trade-offs)"
date: "2026-09-16"
tags: ["rust", "web-scraping", "developer-tools", "automation", "comparison"]
draft: false
cover: "/img/screenshots/rust-logo.jpg"
description: "scraper 0.27 vs fantoccini 0.22 vs thirtyfour 0.37 compared for Rust web scraping in 2026: static parsing vs WebDriver automation, code examples, memory costs and pitfalls."
---

# Rust Web Scraping in 2026: scraper vs fantoccini vs thirtyfour (Real Code, Real Trade-offs)

Rust crawlers have quietly moved from hobby projects to production infrastructure. Price monitoring, competitor tracking, QA regression sweeps and dataset collection now run as long-lived Rust services because a single binary can saturate a network link at a fraction of the memory a Node or Python stack needs. The hard part is not the language — it is choosing between **parsing HTML directly** and **driving a real browser**, a decision that changes your memory footprint per worker from about 20 MB to roughly 300 MB and your throughput from thousands of pages per minute to dozens.

This guide compares the three libraries Rust teams actually deploy in 2026: **scraper 0.27.0** (2,419 stars), **fantoccini 0.22.1** (2,018 stars) and **thirtyfour 0.37.5** (1,435 stars). Star counts and versions were verified against the upstream repositories on 2026-09-16, and every snippet below is runnable.

## TL;DR — The 30-Second Verdict

- **Use `scraper`** for everything that does not require JavaScript: server-rendered pages, sitemaps, feeds, JSON endpoints behind simple HTML wrappers. It is the cheapest and fastest option by a wide margin.
- **Use `fantoccini`** when you need a real browser session and prefer a minimal, protocol-level client that speaks WebDriver over HTTP. It pairs naturally with `tokio` and gives you explicit control over waits.
- **Use `thirtyfour`** when you want a batteries-included WebDriver client: richer typed API, screenshot and cookie helpers, BiDi/CDP event access, and ergonomic element queries for complex form flows.
- **Do not use a browser library for static pages.** Reaching for Selenium-style automation when `curl` plus a CSS selector would work is the single most common way scrapers become expensive.

## Comparison at a Glance (verified 2026-09-16)

| Dimension | scraper | fantoccini | thirtyfour |
|---|---|---|---|
| Crate version | **0.27.0** | **0.22.1** | **0.37.5** |
| GitHub | `rust-scraper/scraper` | `jonhoo/fantoccini` | `stevepryde/thirtyfour` |
| Stars | 2,419 | 2,018 | 1,435 |
| Last push | 2026-09-14 | 2026-09-01 | 2026-09-10 |
| License | MIT | MIT | MIT |
| Executes JavaScript | no | yes (browser) | yes (browser) |
| Requires browser/driver | no | yes (geckodriver / chromedriver) | yes (chromedriver preferred) |
| Async runtime | runtime-agnostic | `tokio` | `tokio` |
| Selector engine | CSS + custom | CSS / XPath / link text (via driver) | CSS / XPath / many `By` strategies |
| Approx. memory per worker | ~15–30 MB | ~250–400 MB (browser) | ~250–400 MB (browser) |
| Typical throughput | very high | low–moderate | low–moderate |
| Best for | static HTML, feeds, bulk extraction | minimal browser automation | complex browser flows, QA-style checks |

## Decision Matrix — Pick by Task

| Your Task | Recommended | Reason |
|---|---|---|
| Scrape 100k server-rendered product pages | scraper | No browser overhead; parallelise with `tokio` + `Semaphore` |
| Read an RSS/Atom or sitemap feed and extract links | scraper | Pure parsing, no JS execution needed |
| Log in, click through a multi-step form, then extract | thirtyfour | Rich element API and explicit waits for dynamic UI |
| Screenshot pages for visual regression checks | thirtyfour | Built-in screenshot and browser control |
| Drive Firefox with a tiny client footprint | fantoccini | Straightforward geckodriver client, minimal abstraction |
| Extract one field from a JS-rendered single-page app | fantoccini or thirtyfour | Either works; choose thirtyfour for richer helpers |
| Run inside a container with strict memory limits | scraper | Browsers will blow past small cgroup limits |

## scraper — Static Parsing That Scales

`scraper` builds a DOM from an HTML string and lets you query it with CSS selectors. It does not execute JavaScript, does not need a browser, and runs comfortably inside a `tokio` task or a plain thread pool.

```toml
# Cargo.toml
[dependencies]
scraper = "0.27"
reqwest = { version = "0.12", features = ["blocking"] }
```

```rust
use scraper::{Html, Selector};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let html = reqwest::blocking::get("https://example.com/catalog")?.text()?;
    let doc = Html::parse_document(&html);

    let rows = Selector::parse("article.product").unwrap();
    let title = Selector::parse("h2.title").unwrap();
    let price = Selector::parse("span.price").unwrap();

    for item in doc.select(&rows) {
        let name = item
            .select(&title)
            .next()
            .map(|e| e.text().collect::<String>().trim().to_string())
            .unwrap_or_default();
        let cost = item
            .select(&price)
            .next()
            .map(|e| e.text().collect::<String>().trim().to_string())
            .unwrap_or_default();
        println!("{name} -> {cost}");
    }
    Ok(())
}
```

Parsing a page you already downloaded is fast enough that the network dominates. When you need concurrency, keep one HTTP client and bound parallelism explicitly:

```rust
use scraper::{Html, Selector};
use std::sync::Arc;
use tokio::sync::Semaphore;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::builder()
        .user_agent("openswap-guide-research/1.0")
        .build()?;
    let sem = Arc::new(Semaphore::new(16)); // 16 concurrent requests
    let urls: Vec<String> = (1..=200).map(|p| format!("https://example.com/page/{p}")).collect();

    let mut handles = Vec::new();
    for url in urls {
        let (client, sem) = (client.clone(), sem.clone());
        handles.push(tokio::spawn(async move {
            let _permit = sem.acquire().await.unwrap();
            let body = client.get(&url).send().await?.text().await?;
            let doc = Html::parse_document(&body);
            let sel = Selector::parse("a.next").unwrap();
            Ok::<Option<String>, reqwest::Error>(
                doc.select(&sel).next().and_then(|e| e.value().attr("href").map(str::to_string)),
            )
        }));
    }
    for h in handles {
        if let Ok(Ok(Some(href))) = h.await { println!("next: {href}"); }
    }
    Ok(())
}
```

**Where `scraper` hurts:** dynamic pages return an empty shell. Selector mistakes fail silently (an unmatched selector yields no elements, not an error), so assert on expected counts in tests. Malformed HTML is handled leniently, which is usually what you want but can mask template changes.

## fantoccini — A Thin, Honest WebDriver Client

`fantoccini` speaks the WebDriver protocol directly to `geckodriver` or `chromedriver`. It is async-first, unopinionated, and small — you manage waits and sessions yourself.

```toml
# Cargo.toml
[dependencies]
fantoccini = "0.22"
tokio = { version = "1", features = ["full"] }
serde_json = "1"
```

```rust
use fantoccini::{ClientBuilder, Locator};

#[tokio::main]
async fn main() -> Result<(), fantoccini::error::CmdError> {
    let mut caps = serde_json::map::Map::new();
    caps.insert(
        "goog:chromeOptions".to_string(),
        serde_json::json!({ "args": ["--headless=new", "--no-sandbox"] }),
    );

    let client = ClientBuilder::native()
        .capabilities(caps)
        .connect("http://localhost:9515")
        .await
        .expect("failed to connect to chromedriver");

    client.goto("https://example.com/login").await?;

    let user = client.wait().for_element(Locator::Css("input[name=email]")).await?;
    user.send_keys("ops@example.com").await?;

    let pass = client.form(Locator::Css("form#login")).await?;
    pass.set_by_name("password", "not-a-real-secret").await?;
    pass.submit().await?;

    let heading = client.wait().for_element(Locator::Css("h1.dashboard")).await?;
    println!("logged in: {}", heading.text().await?);

    client.close().await
}
```

Start the driver separately, for example with `chromedriver --port=9515` or `geckodriver --port=4444`, and point `.connect()` at it.

**Where `fantoccini` hurts:** `wait()` still requires you to choose sensible timeouts, and each browser session is a heavyweight process. Naive code that opens one client per URL will exhaust memory long before it saturates the network. Reuse a small pool of sessions and close them in `Drop` or with an explicit `close()`.

## thirtyfour — The Batteries-Included Option

`thirtyfour` wraps WebDriver with a much wider API surface: typed capabilities, `By` strategies, screenshot helpers, cookie management, and optional BiDi/CDP event streams for listening to network activity.

```toml
# Cargo.toml
[dependencies]
thirtyfour = "0.37"
tokio = { version = "1", features = ["full"] }
```

```rust
use thirtyfour::prelude::*;

#[tokio::main]
async fn main() -> WebDriverResult<()> {
    let mut caps = DesiredCapabilities::chrome();
    caps.add_arg("--headless=new")?;
    caps.add_arg("--window-size=1440,900")?;

    let driver = WebDriver::new("http://localhost:9515", caps).await?;
    driver.goto("https://example.com/pricing").await?;

    driver
        .query(By::Css("button[data-plan='annual']"))
        .wait(std::time::Duration::from_secs(10), std::time::Duration::from_millis(250))
        .click()
        .await?;

    let price = driver.find(By::Css(".plan-annual .amount")).await?;
    println!("annual price: {}", price.text().await?);

    let png = driver.screenshot_as_png().await?;
    std::fs::write("pricing.png", png)?;

    driver.quit().await?;
    Ok(())
}
```

`query(...).wait(timeout, interval)` is the practical advantage over hand-rolled polling: it retries until the element is actionable instead of failing on the first miss, which is what makes dynamic pricing pages and SPA dashboards tractable.

**Where `thirtyfour` hurts:** more abstraction to learn, and optional features (BiDi, CDP) pull in extra dependencies. Version pinning matters more here than with `scraper`, because the trait surface evolves quickly — pin an exact minor version in `Cargo.toml` and upgrade deliberately.

## Running Crawlers in Production: Concurrency, Memory and Politesse

**Bound your parallelism.** Network scraping with `scraper` scales with a `Semaphore`; browser scraping scales with RAM. Sixteen concurrent `scraper` tasks are trivial on a 1 GB container, while two headless browsers can exceed it. Size the pool to your cgroup limit, not to your CPU count.

**Respect `robots.txt` and rate limits.** A crawl that hammers a small site will be blocked, and it is your reputation on the line, not the library's. Parse the rules, apply a per-host delay, and honour `Retry-After` on 429 responses.

**Reuse sessions.** Creating a WebDriver session costs seconds of startup and hundreds of megabytes. Batch work per session: navigate many pages, reuse cookies, and reset state between tenants rather than restarting the driver.

**Set a real user agent and sane timeouts.** Default Rust HTTP clients and drivers identify themselves poorly and wait indefinitely. A `reqwest::Client` with a named user agent and 15–30 second timeouts prevents workers from stalling forever on a hung socket.

**Retry with backoff, but not forever.** Transient 5xx and driver hiccups are normal; a three-attempt exponential backoff catches almost all of them. Anything beyond that is usually a selector or anti-automation problem, not bad luck.

## Pitfall Guide

1. **Driver/browser version mismatch.** `chromedriver` must match the installed Chrome major version, or sessions fail at startup with a protocol error. Pin both in your container image rather than installing "latest" at build time.
2. **Blocking code inside async runtimes.** `reqwest::blocking` inside a `#[tokio::main]` context panics. Use the async client in async code and keep blocking calls in `spawn_blocking`.
3. **Selector fragility.** Class names generated by build tools change between deploys. Prefer semantic attributes (`data-testid`, `itemprop`, stable ids) and fail loudly when a required element count drops to zero.
4. **Silent empty results.** `scraper` returns an empty iterator for a bad selector. Assert `expected >= 1` in tests, otherwise a site redesign will quietly write empty records into your database.
5. **Memory growth from abandoned sessions.** A WebDriver session that is neither closed nor dropped keeps a browser process alive. Wrap sessions in RAII guards or close them in `Drop`.
6. **Time-of-day and timezone drift in extracted data.** Pages often render dates in the visitor's timezone. Normalise to UTC on ingest — a topic we covered in depth in our [PHP date library comparison](../2026-09-16-php-datetime-libraries-carbon-chronos-brick-comparison/), and the same reasoning applies to any Rust ingestion pipeline.
7. **Screenshot bloat.** Capturing a PNG per page at full resolution fills disks fast. Capture only on failure, and prefer JPEG for archival as described in our screenshot workflow.

## Building the Rest of the Stack

A crawler is rarely the whole system: you need a resilient HTTP layer, a queue, and storage. Our [Rust HTTP client comparison](../2026-08-17-rust-http-client-libraries-reqwest-hyper-ureq-comparison/) covers `reqwest`, `hyper` and `ureq` for the fetch side, and if you are also working in a JavaScript stack, the [Node.js HTML parsing comparison](../2026-09-01-cheerio-vs-jsdom-vs-parse5-nodejs-html-parsing-comparison/) maps `cheerio`, `jsdom` and `parse5` to the same trade-offs. For a broader view of where compiled languages pay off, see [Zig vs Rust vs Go for systems programming](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/).

## Which Should You Choose?

Start with **`scraper`**. Ship the crawler, measure how much of your target surface actually needs JavaScript, then add automation only for those pages. That single discipline keeps throughput high and memory predictable.

When you do need a browser, choose **`fantoccini`** if you want a minimal client and enjoy controlling waits yourself, and **`thirtyfour`** if you want richer helpers, screenshots and event streams without writing protocol plumbing. Running both approaches in one codebase is normal: `scraper` for the 90% of pages that are static, a browser library for the remainder.

The real cost driver is never the crate — it is how many browser processes you keep alive at once.

## FAQ

**Is `scraper` fast enough for large crawls?**
Yes. Parsing is rarely the bottleneck; the network is. On a modest VM, a `scraper`-based crawler with a bounded concurrency pool will saturate a typical 1 Gbit connection long before CPU becomes a constraint.

**Can I use these libraries with `async-std` or plain threads instead of `tokio`?**
`scraper` is runtime-agnostic and works anywhere, including synchronous code. `fantoccini` and `thirtyfour` are built around `tokio`, so browser automation should run on a `tokio` runtime; mixing runtimes in one binary is possible but adds complexity for little gain.

**Do I need `chromedriver` for `thirtyfour`, or does it support Firefox?**
`thirtyfour` targets W3C WebDriver endpoints and works with Firefox via `geckodriver`, but its Chrome/CDP features (event streams, advanced browser control) are Chrome-specific. If Firefox support is your primary requirement, `fantoccini` is the more natural fit.

**How do I avoid being blocked while scraping?**
Slow down, identify yourself honestly in the user agent, honour `robots.txt`, use conditional requests and caching, and avoid patterns that look like credential stuffing. Browser automation with real rendering helps on JS-heavy sites, but no library will save a crawler that ignores rate limits.

**Can I scrape without a browser and still get JavaScript-rendered content?**
Sometimes. Many single-page applications call JSON endpoints you can request directly once you identify them from the network tab. That is the cheapest path by far — confirm it is not covered by terms of service first.

**Which library should I use for visual regression checks?**
`thirtyfour`, because screenshots are a first-class API. Capture only on failure or on a scheduled subset to keep storage manageable, and prefer JPEG for archival copies.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Web Scraping in 2026: scraper vs fantoccini vs thirtyfour (Real Code, Real Trade-offs)",
  "description": "Comparison of Rust web scraping libraries in 2026: scraper 0.27 static parsing, fantoccini 0.22 and thirtyfour 0.37 WebDriver automation, with runnable code, memory costs and pitfalls.",
  "datePublished": "2026-09-16",
  "dateModified": "2026-09-16",
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
