---
title: "Cheerio vs jsdom vs parse5 in 2026: Which Node.js HTML Parser Should You Use?"
date: "2026-09-01"
tags: ["comparison", "guide", "developer-tools", "nodejs", "web-scraping", "html"]
draft: false
description: "Compare Cheerio, jsdom, and parse5 — the three dominant HTML parsing libraries in the Node.js ecosystem — across API style, spec compliance, script execution, memory usage, and real-world use cases like scraping and testing. Includes real code examples and a decision matrix for 2026."
---

Every web scraper, test runner, and static analyzer in the Node.js ecosystem eventually has to turn raw HTML into something you can query — and the library you pick changes your throughput by an order of magnitude. The three contenders in 2026 are **Cheerio (30,475 GitHub stars), jsdom (21,664), and parse5 (3,928)** — all MIT-licensed, all actively maintained with commits this week. They look interchangeable from the outside, but they are built for completely different jobs: one is a fast jQuery-style scraper, one is a full browser DOM, and one is the low-level spec parser hiding underneath both of the others. Pick the wrong one and you either execute untrusted code you should not, or ship a scraper that is ten times slower than it needs to be.

## TL;DR — Quick Verdict

- **Use Cheerio** for 95% of scraping and HTML extraction — jQuery-style selectors, no script execution, and the best speed-to-usefulness ratio in the ecosystem.
- **Use jsdom** only when you genuinely need a browser-like DOM — testing client-side code in Node, or scraping pages whose content is rendered by JavaScript.
- **Use parse5** when you are building a tool that needs the WHATWG spec exactly — sanitizers, converters, custom tree traversals — and you do not need CSS selectors.

## Comparison at a Glance

| Dimension | Cheerio | jsdom | parse5 |
|---|---|---|---|
| License | MIT | MIT | MIT |
| GitHub stars (Sep 2026) | **30,475** | **21,664** | **3,928** |
| Last commit | **Sep 2026** | **Sep 2026** | **Aug 2026** |
| What it is | jQuery-style parser + selector engine | Full DOM implementation (WHATWG) | Spec-compliant parser + serializer |
| API style | `$(selector)` jQuery API | `window.document` DOM API | Tree adapter / callback API |
| CSS selectors | Yes (sizzle-style, built-in) | Yes (querySelectorAll) | **No** — manual traversal |
| Executes JavaScript | **No** | Yes (opt-in, `runScripts`) | No |
| Renders layout / computes styles | No | Partially (no layout engine) | No |
| Relative speed (parse + query) | **Fastest** | Slow (10x+ overhead) | Fast (raw parsing) |
| Memory footprint | Low | High (window + document) | Lowest |
| Uses parse5 internally | Yes (parser backend) | Yes (parser backend) | — (it is the backend) |
| Best for | Scraping, extraction, SSR string manipulation | Testing client code, JS-rendered scraping | Sanitizers, converters, custom tooling |

## Decision Matrix

| Use case | Recommended library | Why |
|---|---|---|
| Scrape static pages: links, meta tags, tables, product data | **Cheerio** | jQuery selectors + speed; no browser overhead |
| Unit-test React/Vue/DOM code in Node | **jsdom** | Real `window`, `document`, events, and localStorage |
| Scrape a page that renders content with JavaScript | **jsdom** (or a real browser) | Cheerio sees the empty pre-render HTML; jsdom can run the scripts |
| Build an HTML sanitizer or markdown-to-HTML converter | **parse5** | Exact spec parsing, streaming support, tree adapter control |
| Parse a huge file without loading it all into memory | **parse5** (SAX-like) | Streaming parser API keeps memory flat |
| Extract data from an email or an RSS/Atom feed | **Cheerio** | Same selector API, tiny footprint |
| End-to-end crawling with JS execution and real browsing | Neither — use a browser automation tool | See the note below on Playwright/Crawlee workflows |

## Cheerio — The Scraper's Workhorse (30,475★, last commit Sep 2026)

Cheerio gives you a jQuery-like API over a fast parser backend (since 1.0 it uses parse5 under the hood), without any of the browser baggage — no window, no layout, no script execution. That combination is exactly right for the dominant job: pull HTML from the network, query it, extract what you need, move on.

```js
import * as cheerio from "cheerio";

const $ = cheerio.load(htmlString);

// Grab all product links and prices from a listing page
const items = $("article.product").map((_, el) => ({
  name: $(el).find("h2 a").text().trim(),
  href: $(el).find("h2 a").attr("href"),
  price: $(el).find(".price").text().replace(/[^\d.]/g, ""),
})).get();

// Meta tags for SEO tooling
const description = $('meta[name="description"]').attr("content");

// Remove ads and boilerplate before text extraction
$("script, style, .ad-banner").remove();
const cleanText = $("main").text().replace(/\s+/g, " ").trim();
```

The API is synchronous and forgiving: `$()` works on the whole document, `.find()`, `.closest()`, `.each()`, `.map()`, `.attr()`, `.text()`, `.html()` cover nearly everything a scraper does, and malformed HTML that would crash a strict parser is handled gracefully. It is also framework-agnostic — the same `load()` call works in Node and in the browser (for client-side preview tools), and the `cheerio.load` result is a plain function, so it composes with any async fetching layer you already have.

**The honest trade-offs:** Cheerio does not execute JavaScript. A single-page app served with an empty `<div id="root">` yields an empty query result — no amount of selector cleverness fixes that. And because it is not a full DOM, code that expects `window`, `document`, or event behavior will not run. For static HTML extraction it is the right tool, full stop.

## jsdom — A Browser DOM Without the Browser (21,664★, last commit Sep 2026)

jsdom implements the WHATWG DOM and HTML standards in pure JavaScript: real `window` and `document` objects, events, `localStorage`, `fetch` (behind a flag), and the ability to execute the scripts a page contains. It is the standard `testEnvironment` for Jest and Vitest because it lets Node code exercise real DOM behavior — clicking buttons, dispatching events, reading rendered text — without installing a browser.

```js
import { JSDOM } from "jsdom";

const dom = new JSDOM(`<!DOCTYPE html><div id="app"></div>`, {
  url: "https://example.com/",
  runScripts: "dangerously",
  resources: "usable",
  pretendToBeVisual: true,
});

const { window } = dom;
window.eval(`document.getElementById("app").innerHTML = "<h1>loaded</h1>"`);

console.log(window.document.querySelector("#app h1").textContent); // loaded
dom.window.close(); // free the resources
```

For scraping JavaScript-rendered content, jsdom is the pragmatic middle ground between Cheerio (too weak) and a headless browser (too heavy): it executes the page's own scripts, and if the page relies only on DOM APIs rather than layout, you get the rendered DOM in-process.

**The honest trade-offs:** the `runScripts: "dangerously"` flag is named accurately — executing a page's scripts in your process is running arbitrary code, so only do it with HTML you trust. Resource loading (`resources: "usable"`) can trigger network requests to third-party hosts, so keep it off unless the page needs external assets, and be careful about where those requests point. And it is slow and memory-hungry compared to Cheerio — a single `JSDOM` instance can consume tens of megabytes, so always call `dom.window.close()` and never accumulate instances in a long-running worker.

## parse5 — The Spec Engine Underneath (3,928★, last commit Aug 2026)

parse5 is the reference-grade HTML parsing and serialization toolset for Node.js, implementing the WHATWG HTML parsing algorithm — including all the error recovery that makes real-world HTML work. It does not give you selectors or a DOM; it gives you a parse tree you navigate with a tree-adapter API, plus streaming (SAX-like) parsing and serialization. If you have used Cheerio or jsdom, you have already used parse5 — both build on it.

```js
import { parse, serialize } from "parse5";

const document = parse(`<!DOCTYPE html><html><body><p>Hello</p></body></html>`);

// Walk the tree manually with the default tree adapter
function walk(node, depth = 0) {
  if (node.nodeName === "#text" && node.value.trim()) {
    console.log(" ".repeat(depth) + node.value.trim());
  }
  for (const child of node.childNodes || []) walk(child, depth + 1);
}
walk(document);

// Serialize back to HTML
const html = serialize(document);

// Streaming parse for huge documents
import { parseFragment } from "parse5";
const fragment = parseFragment(`<table><tr><td>A</td></tr></table>`);
```

Because parse5 models the spec exactly, it is the foundation of serious HTML tooling: sanitizers that must not leak dangerous markup, converters that round-trip HTML losslessly, and linters that report parse errors with source locations. The cost is ergonomics — there are no selectors, so anything beyond a shallow walk means writing traversal code, and most teams should reach for Cheerio on top of parse5 instead of using it directly.

## Pitfalls: What Actually Goes Wrong

1. **Never parse HTML with regex.** If you are writing `/<a href="([^"]*)"/g` to extract links, stop — malformed tags, attributes in different orders, and nested quotes will break it, and you will be debugging entity-encoded edge cases forever. All three libraries exist precisely because HTML cannot be regexed reliably.
2. **Cheerio + JavaScript-rendered pages = empty results.** Check what the server actually returns before blaming your selectors. `curl -s <url> | head` shows the raw HTML; if your target content is not there, you need jsdom or a real browser, not a better selector.
3. **jsdom `runScripts: "dangerously"` is arbitrary code execution.** The flag name is not a joke. Run scripts only on HTML you control. For scraping third-party pages with JS rendering, prefer a sandboxed browser tool instead.
4. **jsdom resource loading can be an SSRF vector.** Loading `resources: "usable"` makes the page fetch images/scripts from URLs it references — if you parse attacker-influenced HTML, those requests can hit internal network addresses. Keep resource loading disabled unless the page genuinely needs it.
5. **Memory leaks in long-running scrapers.** jsdom windows and Cheerio documents both hold large trees. Close jsdom windows explicitly, and in worker loops, null out references so the garbage collector can reclaim them. A scraper that runs for hours will OOM otherwise.
6. **Encoding headaches.** Pages declaring `charset=windows-1252` (or no charset at all) can produce mojibake. Cheerio handles the common cases, but for non-UTF-8 sources, decode the buffer explicitly (e.g., with `iconv-lite`) before calling `load()`.
7. **Respect the site you are scraping.** Rate-limit your requests, honor `robots.txt`, and check the site's terms and jurisdiction — the libraries are legal; the scraping pattern you deploy them in may not be. For large-scale crawling, our [web scraping framework comparison (Crawlee, Scrapy, Playwright)](../self-hosted-web-scraping-crawlee-scrapy-playwright-guide-2026/) covers managed pipelines with built-in politeness controls.
8. **Cross-language lessons.** If you maintain scrapers in multiple languages, the same selection logic applies everywhere: Python's [BeautifulSoup vs lxml vs selectolax comparison](../2026-07-04-python-html-parsing-libraries-beautifulsoup-lxml-selectolax-pyquery-html5lib/) and [Go's colly vs goquery vs rod comparison](../2026-08-25-go-web-scraping-colly-goquery-rod-comparison/) map one-to-one onto the Cheerio/jsdom/browser spectrum, and [Ruby's Nokogiri-based ecosystem](../2026-07-21-ruby-web-scraping-nokogiri-mechanize-kimurarails/) mirrors the same trade-offs.

## Choosing Between Cheerio and jsdom in One Decision

The boundary is simpler than it looks: **ask whether the data you need exists in the raw HTML the server sends.** If yes — static pages, meta tags, most product catalogs, emails, feeds — Cheerio. If no — the page renders its content with client-side code — you need script execution, which means jsdom at minimum, and realistically a real headless browser for anything with layout-dependent rendering or complex timing. In production scrapers, the common architecture is Cheerio for the extraction layer and a browser pool (Playwright) for the pages Cheerio cannot handle, so you never pay jsdom's cost for pages that do not need it.

## FAQ

**Is Cheerio a full DOM implementation?**
No. Cheerio parses HTML and provides a jQuery-like query and manipulation API, but it has no `window`, no layout, and no script execution. For testing code that touches the DOM, or scraping JavaScript-rendered content, you need jsdom or a headless browser.

**Does jsdom actually execute JavaScript?**
Only when you pass `runScripts: "dangerously"` (or `"outside-only"`). By default jsdom parses the DOM without running any scripts, which makes it safe for static parsing. When enabled, it executes the page's scripts inside your Node process — treat that as running arbitrary code.

**What is parse5 used for?**
parse5 is the WHATWG-compliant HTML parser and serializer that Cheerio and jsdom build on. It is used directly in tools that need exact spec behavior: HTML sanitizers, format converters, linters that report parse errors, and streaming parsers for very large documents.

**Which library is fastest for scraping?**
Cheerio is the fastest of the three for typical extract-and-move-on workloads — often 5–10x faster than jsdom, which pays for full DOM construction. parse5's raw parsing is also fast, but you then write your own traversal because it has no selectors.

**Can I use Cheerio with async/await and streams?**
Cheerio's API is synchronous; you fetch asynchronously (with `fetch`, axios, or whatever you use) and then call `cheerio.load(html)`. For parsing very large documents with bounded memory, parse5's streaming parser is the better fit than loading the whole string.

**Are these libraries free for commercial scraping?**
All three are MIT-licensed and free for any use. The legal constraints on scraping come from the sites you target (terms of service, robots.txt, applicable law), not from the libraries.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Cheerio vs jsdom vs parse5 in 2026: Which Node.js HTML Parser Should You Use?",
  "description": "Compare Cheerio, jsdom, and parse5 — the three dominant HTML parsing libraries in the Node.js ecosystem — across API style, spec compliance, script execution, memory usage, and real-world use cases like scraping and testing. Includes real code examples and a decision matrix for 2026.",
  "datePublished": "2026-09-01",
  "dateModified": "2026-09-01",
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
