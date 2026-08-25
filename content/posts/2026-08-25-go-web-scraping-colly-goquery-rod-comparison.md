---
title: "Go Web Scraping in 2026: Colly vs goquery vs Rod — Which Should You Build On?"
date: "2026-08-25"
tags: ["golang", "web-scraping", "crawler", "automation", "developer-tools"]
draft: false
cover: "/img/screenshots/colly-cover.jpg"
---

Every Go developer hits the same wall the first time they need data that isn't in an API: "I'll just scrape it" turns into an afternoon of fighting selectors, redirects, and pages that render nothing until JavaScript runs. The ecosystem offers three serious answers — Colly (25,480 stars), goquery (14,982 stars), and Rod (7,074 stars) — and they are **not interchangeable**. One is a full crawler framework, one is a DOM querying library, and one is a headless-browser driver. Understanding which layer each tool occupies is the difference between a scraper that survives contact with the real web and one that dies on page two of a 10,000-item crawl.

## TL;DR: Which Go Scraping Tool Should You Pick?

If your target pages are **static HTML** and you need **robust crawling at scale** — pagination, rate limits, retries, parallelism — use **Colly** as the crawler and **goquery** for its jQuery-style selectors inside Colly's callbacks (they compose perfectly). If you only need to **parse a single page or an HTML fragment** you already fetched, use **goquery** alone — it is a pure DOM library with no crawler machinery. If your targets are **JavaScript-rendered SPAs, login walls, or anything that needs a real browser** — use **Rod**; it drives Chrome over the DevTools Protocol and is the only one of the three that sees what a human sees. The pragmatic default for most projects is Colly + goquery, with Rod reserved for the pages that defeat them.

## Comparison at a Glance

| | Colly | goquery | Rod |
|---|---|---|---|
| **Stars** | 25,480 | 14,982 | 7,074 |
| **Last push** | 2026-08-14 | 2026-08-17 | 2026-08-11 |
| **License** | Apache-2.0 | BSD-3-Clause | MIT |
| **What it is** | Crawler/scraper framework | DOM query & manipulation | Chrome DevTools Protocol driver |
| **Renders JavaScript** | No | No | Yes (full browser) |
| **Crawling machinery** | Built-in (robots.txt, limits, retries, cache) | None | Manual (via browser) |
| **Selector API** | `OnHTML` + goquery internals | jQuery-style `Find/Each/Attr` | CSS selectors via `MustElement` |
| **Parallel scraping** | Yes (`Async`, `Parallelism`) | N/A | Yes (per-page goroutines) |
| **Proxy / rotation** | Built-in (`SetProxyFunc`) | Via `net/http` | Via launch flags / custom |
| **Headless browser** | No | No | Yes (auto-downloads Chrome) |
| **Learning curve** | Medium | Low | Medium-high |

## Decision Matrix: Pick by Use Case

| Use Case | Recommendation | Why |
|---|---|---|
| Crawl a whole site (links, pagination, dedup) | **Colly** | Collector handles frontier, retries, and domain rules for you |
| Extract fields from one fetched page | **goquery** | `NewDocumentFromReader` + `Find` is all you need |
| Scrape a React/Vue SPA or canvas-rendered data | **Rod** | Only a real browser sees post-JS DOM |
| Logged-in scraping with sessions | **Rod** (or Colly cookie jar) | Rod keeps full browser storage; Colly works if it's cookie-only auth |
| High-volume crawl with polite rate limits | **Colly** | `LimiterRule` with delay + parallelism is built-in |
| Mixed pipeline: crawl + parse + render fallback | **Colly + goquery + Rod** | The trio composes: Colly for frontier, goquery for parsing, Rod only for JS pages |

## Colly: The Elegant Crawler Framework

Colly is the closest Go gets to Scrapy: you create a `Collector`, register callbacks for the events you care about, and set it loose. The framework handles the crawl frontier, request deduplication, retries, backoff, caching, robots.txt, and per-domain rate limits — the boring 80% of scraping that kills hand-rolled crawlers.

```go
c := colly.NewCollector()

// Find and visit all links
c.OnHTML("a[href]", func(e *colly.HTMLElement) {
    e.Request.Visit(e.Attr("href"))
})

c.OnRequest(func(r *colly.Request) {
    fmt.Println("Visiting", r.URL)
})

c.Visit("http://go-colly.org/")
```

One `go get github.com/gocolly/colly/v2` later, this crawls an entire domain, following links while the framework keeps track of visited URLs. For product-catalog style scraping, the `OnHTML` callback receives a parsed element whose `Request` carries context — so you can attach custom data per page and even chain requests (`e.Request.Post`, `e.Request.Abort`). Rate limiting is declarative:

```go
c.Limit(&colly.LimitRule{
    DomainGlob:  "*",
    Delay:       2 * time.Second,
    Parallelism: 4,
})
```

That single rule gives you polite, throttled, four-goroutine crawling with zero bookkeeping. Colly's `Async` mode plus `Parallelism` handles genuinely large crawls, and `SetProxyFunc` swaps in rotating proxies when anti-bot measures get serious. The caveat: Colly parses the raw HTTP response — if the page builds its content in JavaScript, you get the empty skeleton. That's exactly when Rod comes in. Colly is also Apache-2.0 licensed, so it drops into commercial pipelines without a second thought. For the full cross-ecosystem picture (Crawlee, Scrapy, Playwright), our [self-hosted web scraping comparison](../self-hosted-web-scraping-crawlee-scrapy-playwright-guide-2026/) maps the alternatives outside Go.

## goquery: The jQuery-Style DOM Library

goquery does one thing and does it beautifully: query a parsed HTML tree with jQuery-style selectors. It sits on top of `golang.org/x/net/html`, which Go's own tooling uses, so the parsing is battle-tested — and, crucially, lenient. Real-world pages are full of malformed markup, and `x/net/html` auto-corrects instead of panicking, which is exactly what a scraper needs.

```go
res, err := http.Get("http://metalsucks.net")
if err != nil {
    log.Fatal(err)
}
defer res.Body.Close()
if res.StatusCode != 200 {
    log.Fatalf("status code error: %d %s", res.StatusCode, res.Status)
}

doc, err := goquery.NewDocumentFromReader(res.Body)
if err != nil {
    log.Fatal(err)
}

// Find the review items
doc.Find(".reviewRows .reviewRow").Each(func(i int, s *goquery.Selection) {
    title := s.Find("h2").Text()
    // ...
})
```

`Find`, `Each`, `Attr`, `Text`, `AttrOr`, `Closest`, `ParentsFiltered` — the API reads like jQuery, which makes it the fastest way for web developers to get productive. Because it's a pure library rather than a framework, you pair it with whatever HTTP client you already use, and it composes directly inside Colly's `OnHTML` callback (`e.DOM` is a goquery selection). Two things goquery will not do: execute JavaScript, and manage crawling state. It's a parsing layer, not a crawler — and that clarity is its strength. On the data side, its BSD-3-Clause license is permissive enough for commercial scrapers. If you want the Python equivalent of this layer, our [BeautifulSoup vs lxml vs Selectolax comparison](../2026-07-04-python-html-parsing-libraries-beautifulsoup-lxml-selectolax-pyquery-html5lib/) covers the same problem in Python.

## Rod: The Chrome DevTools Protocol Driver

Rod is the Puppeteer of Go: a high-level driver for the Chrome DevTools Protocol that launches a real browser, waits for elements, and interacts with pages the way a human would. It's for the pages that defeat static scraping — SPAs, infinite scroll, canvas dashboards, login flows.

```go
browser := rod.New().MustConnect()
defer browser.MustClose()

// Create a new page
page := browser.MustPage("https://github.com").MustWaitStable()

// Trigger the search input with hotkey "/"
page.Keyboard.MustType(input.Slash)

// Use a CSS selector to get the search input and type "git"
page.MustElement("#query-builder-test").MustInput("git").MustType(input.Enter)
```

The `Must*` API is aggressively ergonomic: each call panics on failure, so happy-path code reads top-to-bottom, while production code can use the non-panicking variants with `errors.Is`. Rod's engineering highlights are genuinely unusual for the space: **leakless** subprocess management (no zombie browser processes after crashes), two-step `WaitEvent` so you never miss an event, `WaitStable` / `WaitRequestIdle` helpers that handle SPA hydration, `HijackRequests` for intercepting network traffic, and correct handling of nested iframes and shadow DOM. Every operation is thread-safe, so parallel page workers are straightforward, and the launcher auto-downloads a compatible Chrome build on first run — which is also its main gotcha: the browser download is large, so CI images need it cached.

Rod is the tool that makes scraping resilient when Colly + goquery come back empty — and the browser context means cookies, localStorage, and sessions survive across pages, which unlocks authenticated scraping without manual cookie plumbing. For Java teams comparing this space, our [jsoup vs HtmlUnit vs WebMagic guide](../2026-07-21-java-web-scraping-jsoup-htmlunit-webmagic/) shows the same three-layer pattern (parser / browserless crawler / browser driver) in a different ecosystem.

## Common Pitfalls and Migration Traps

**Assuming static HTML means no JavaScript.** Modern sites increasingly ship server-side rendered shells with client-side hydration. Always check `curl <url> | head` before architecting: if the data isn't in the raw HTML, Colly and goquery will silently give you nothing — that's the moment to bring in Rod, not to add more selector logic.

**Colly respects robots.txt by default — and that's a feature.** `colly.NewCollector()` consults robots.txt; if a site disallows your path, you'll wonder why a crawl returns nothing. Set `Collector{IgnoreRobotsTxt: true}` deliberately and ethically — this is a legal/compliance decision, not a debugging toggle.

**The default User-Agent is an anti-bot beacon.** Colly's default UA identifies the framework. For production scraping, set a real browser UA and rotate proxies via `SetProxyFunc`; otherwise expect 403s on any serious target.

**goquery loads the whole document into memory.** A 20 MB HTML page becomes a full DOM tree in RAM. For very large pages, filter at the HTTP layer (e.g., `io.LimitReader`) or chunk your parsing — goquery gives you no streaming mode.

**Rod's first run downloads a browser.** Plan for ~150 MB on first launch (or a shared cache in CI). Also: always `defer browser.MustClose()` — while Rod's leakless layer cleans up crashes, explicit close is the correct discipline in long-running services.

**Rate limiting is your first line of defense.** Whatever you build, put Colly-style delay/parallelism limits in front of it. Unthrottled crawls get you blocked, and more importantly they get the *site* degraded for everyone else. Two seconds between requests is not cowardice.

**Migrating from hand-rolled `net/http` scraping.** The cheapest migration path is goquery first (replace your regex/html tokenizer with `Find` — you will delete hundreds of lines), then Colly once you need retries and limits. Move to Rod last, only for the pages that require it; browser automation is an order of magnitude heavier on CPU and memory.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Web Scraping in 2026: Colly vs goquery vs Rod — Which Should You Build On?",
  "description": "Comparison of the three Go scraping tools: the Colly crawler framework, the goquery jQuery-style DOM library, and the Rod Chrome DevTools Protocol driver. Real GitHub stats, code examples, rate limiting, and use-case decision matrix.",
  "datePublished": "2026-08-25",
  "dateModified": "2026-08-25",
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

## FAQ

### What is the difference between Colly and goquery?

Colly is a full crawling framework: it manages the crawl frontier, deduplication, retries, rate limits, and robots.txt, and it invokes your callbacks as pages are fetched. goquery is a DOM querying library: it parses HTML and gives you jQuery-style selectors. They complement each other — Colly's `OnHTML` callback gives you a parsed element you can query with goquery's API directly.

### When do I need Rod instead of Colly?

Whenever the page content is produced by JavaScript. Colly and goquery only see the raw HTML response; if a React or Vue app fetches data and renders it client-side, static scraping returns an empty skeleton. Rod drives a real Chrome browser, waits for the DOM to settle, and sees exactly what a human sees.

### Can I use all three together?

Yes, and that's the recommended architecture: Colly manages the crawl and its politeness rules, goquery parses the static pages, and Rod handles the small subset of URLs that need a real browser. Each tool is a layer, and the layers compose cleanly in one Go binary.

### Is web scraping legal in 2026?

Scraping publicly accessible data is generally legal in many jurisdictions, but the answer depends on the site's terms of service, robots.txt, and local law (the EU Database Directive, CFAA interpretation in the US, and similar rules elsewhere). Respect rate limits, identify your crawler where appropriate, and avoid bypassing authentication or access controls — that's where liability concentrates.

### Does Rod work with headless Chrome in Docker?

Yes — Rod's launcher supports installing a headless Chromium in containers (`rod.New().MustConnect()` with the launcher configured for `HEADLESS_SHELL`), and its leakless management is specifically designed to avoid orphaned browser processes in long-running services. Cache the browser binary in your image to avoid a large download on every start.

### Which license is safest for a commercial scraper?

Colly (Apache-2.0), goquery (BSD-3-Clause), and Rod (MIT) are all permissive and safe for commercial use. None of them impose copyleft obligations, so the choice should be driven by architecture, not licensing — a rare luxury in this space.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
