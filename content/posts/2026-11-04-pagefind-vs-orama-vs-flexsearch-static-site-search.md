---
title: "Pagefind vs Orama vs FlexSearch in 2026: Site Search That Still Works at 10,000 Pages"
date: "2026-11-04"
tags: ["search", "static-site", "hugo", "javascript", "performance", "libraries"]
draft: false
description: "Pagefind, Orama and FlexSearch compared for static sites in 2026: build-time vs runtime indexes, real code, bundle weight, Hugo and GitHub Pages deployment, subpath pitfalls and a decision matrix."
---

A Hugo site is a pleasure to build and a nuisance to search. Everything is static, there is no server to query, and the moment the archive passes a few thousand pages the naive answer — ship every post as JSON and filter it in the browser — turns your homepage into a 12 MB download. The site this article lives on is past eleven thousand pages; that is not a hypothetical.

Three libraries dominate the static-site search problem in 2026: **Pagefind**, **Orama** and **FlexSearch**. They are often listed together as "client-side search", which hides the fact that they solve three different problems. One builds an index at deploy time and streams fragments on demand. One is a full search engine that runs in memory wherever JavaScript runs. One is a fast indexing primitive you assemble yourself.

## TL;DR / Quick Verdict

- **Choose Pagefind** for a content site — blog, docs, marketing — especially a large one. It indexes your built HTML as a deploy step, splits the index into per-page fragments, and downloads only the fragments a query needs. MIT licensed, actively developed, zero infrastructure, and it is the only one of the three that gives you a usable search UI out of the box.
- **Choose Orama** when search is part of the product rather than a page feature: you need structured filters, facets, typo tolerance, vector or hybrid ranking, and you want the same engine to run in a browser, on an edge worker or on a Node server.
- **Choose FlexSearch** when you are building search into an application you control, need raw indexing throughput and a small payload, and are willing to write the persistence, tokenization configuration and UI yourself.

The one-line rule: **Pagefind indexes your site, Orama is a search engine, FlexSearch is a search data structure with an API.**

## Side-by-Side Comparison

| Dimension | Pagefind | Orama | FlexSearch |
|---|---|---|---|
| GitHub stars | 5,544 | 10,596 | **13,819** |
| Last push | 2026-11-03 | 2026-10-18 | 2026-06-28 |
| License | MIT | Apache-2.0 | Apache-2.0 |
| Index built | At deploy time, by a CLI over built HTML | At runtime, in memory | At runtime, in memory |
| Index delivered | Per-page fragments, fetched on demand | Whole serialized index (you persist it) | Whole serialized index (you persist it) |
| Runtime engine | Rust compiled to WebAssembly | JavaScript | JavaScript |
| Search UI included | **Yes** (`PagefindUI`) | No | No |
| Structured filters / facets | Basic metadata filters | **Yes** (schema-driven) | Yes, via Document API |
| Typo tolerance | Prefix/wildcard oriented | **Yes**, configurable tolerance | Via encoder/resolver config |
| Vector / hybrid ranking | No | **Yes** (vector fields, hybrid) | No |
| Server-side use | Not applicable (static output) | Yes (Node, workers, edge) | Yes (Node) |
| CJK / custom tokenization | Language-specific stemmers, `--force-language` | Custom tokenizer | Custom encoder + charset |
| Best fit | Content sites at 1k–100k+ pages | Product search, apps | Embedded search you control |

The star ranking is misleading in a useful way: **FlexSearch has the most stars and the least built-in product**, because it is a low-level library people embed. Pagefind has fewer stars and the shortest path to a working search box on a static site.

## Decision Matrix: Pick by Situation

| Your situation | Recommended | Why |
|---|---|---|
| Hugo/Jekyll/Eleventy blog with a search box | Pagefind | One CLI step after the build, UI included |
| Documentation site with versioned sections | Pagefind | Filters by metadata, fragment loading keeps it light |
| Site hosted on GitHub Pages under a subpath | Pagefind | `bundlePath` handles the prefix |
| Search inside a React app with facets and sorting | Orama | Schema, filters, facets, hybrid ranking |
| Offline-first desktop or Electron app | FlexSearch or Orama | Persist the index, no network needed |
| 50,000-page archive on cheap hosting | Pagefind | Index is generated and served as static files |
| You need vector similarity | Orama | Vector fields in the schema |
| You want to own every byte of the pipeline | FlexSearch | Lowest-level control, no opinions |

## Pagefind: Index the Site, Not the Browser

Pagefind's premise is that a static site already knows all of its content at deploy time, so the browser should never download an index of the whole site. The CLI walks your built HTML, extracts content, and writes a directory of index fragments. At query time the WASM runtime fetches only the fragments a query touches.

The build step is one command after Hugo finishes:

```bash
hugo --minify
npx pagefind --site public
```

For local testing, `--serve` starts a preview server so you can try queries against the generated index:

```bash
npx pagefind --site public --serve
```

That command is the whole integration. No Node server, no API key, no index hosting — `public/pagefind/` is deployed with the rest of the site. If you prefer a native binary over npm, `cargo install pagefind` builds the same CLI from source.

Wiring the UI is two tags and one constructor:

```html
<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<script src="/pagefind/pagefind-ui.js"></script>

<div id="search"></div>
<script>
  new PagefindUI({ element: "#search" });
</script>
```

`element` is the only required option — everything else has defaults, including the placeholder text, result rendering and keyboard handling.

**The subpath trap deserves its own paragraph.** If the site is served from `https://user.github.io/repo/`, the defaults look for `/pagefind/`, which does not exist at the domain root. Set `bundlePath` explicitly:

```html
<script>
  new PagefindUI({
    element: "#search",
    bundlePath: "/repo/pagefind/",
    showSubResults: true
  });
</script>
```

This one option is the cause of most "Pagefind returns nothing" reports on GitHub Pages and Netlify preview deployments.

Scoping what gets indexed is handled with data attributes in your templates. Put `data-pagefind-body` on the article container so navigation, sidebars and footers are not indexed as content, and `data-pagefind-ignore` on elements you want excluded even inside the body:

```html
<article data-pagefind-body>
  <h1 data-pagefind-meta="title">{{ .Title }}</h1>
  <div class="content">{{ .Content }}</div>
  <aside data-pagefind-ignore>Related posts…</aside>
</article>
```

Metadata declared with `data-pagefind-meta` becomes filterable, which is how you implement "search only posts tagged postgres" without writing a query language.

Where Pagefind stops: there is nothing to query at runtime. If your content changes without a rebuild — user comments, a database-backed catalogue — Pagefind cannot see it. It is a build artifact, and that is the point.

## Orama: A Search Engine That Happens to Fit in a Browser

Orama is a different category of tool. It defines a schema, indexes documents in memory, and answers queries with ranking, filters, facets and vector similarity. The same package runs in a browser tab, a Cloudflare Worker and a Node process.

```bash
npm i @orama/orama
```

The schema is explicit, which is the feature that separates it from every "just index the text" library:

```javascript
import { create, insert, search } from '@orama/orama'

const db = create({
  schema: {
    name: 'string',
    description: 'string',
    price: 'number',
    embedding: 'vector[1536]',
    meta: {
      rating: 'number'
    }
  }
})

insert(db, {
  name: 'Noise cancelling headphones',
  description: 'Best noise cancelling headphones on the market',
  price: 99.99,
  embedding: [0.2432, 0.9431, 0.5322, 0.4234 /* ... */],
  meta: { rating: 4.5 }
})

const results = await search(db, {
  term: 'noise cancelling',
  properties: ['name', 'description']
})
```

Because the schema declares types, Orama can filter on `price` and `meta.rating`, facet on them, and rank with typo tolerance — without you writing a parser. Vector fields put similarity search in the same query path, which is why teams building "find similar documents" features reach for it instead of a search server.

The tradeoff is that **you own the index lifecycle**. There is no CLI walking your site; you decide what to insert, when, and how to persist it. Orama's ecosystem provides a persistence plugin for serializing an index, but the deployment question is yours: build the index at startup, ship a prebuilt blob, or rebuild it in a worker. On a 10,000-page archive, a full in-memory index is a real download and a real memory footprint, and no amount of clever ranking fixes that.

For a product catalogue, an internal dashboard, or a documentation site with a handful of structured facets, that trade is excellent. For a blog with 10,000 posts, it is the wrong shape.

## FlexSearch: The Fastest Primitive, Assembled by You

FlexSearch is the library that benchmarks well and asks you to make every decision. The core API is deliberately small:

```javascript
import { Index } from 'flexsearch'

const index = new Index()
index.add(0, 'John Doe')
index.add(1, 'Jane Doe')

const results = index.search('John', 10)
```

For structured documents there is a `Document` wrapper that indexes named fields and returns the original objects:

```javascript
import { Document } from 'flexsearch'

const docs = new Document({
  document: {
    id: 'id',
    index: ['title', 'body'],
    store: true
  }
})

docs.add({ id: 1, title: 'Postgres tuning', body: 'Work memory and checkpoints…' })

const hits = docs.search('checkpoints')
```

What you get beyond the API: worker support for keeping indexing off the main thread, IndexedDB export/import for persistence, configurable encoders and character sets for languages that do not tokenize on spaces, and a `fastupdate` mode for indexes that change constantly (at the cost of leaving empty slots behind, reclaimable with `index.cleanup()`).

What you do not get: a UI, a build step, a schema, ranking explanations, or a persistence policy. On a content site you would end up rebuilding Pagefind's feature set, badly, on top of FlexSearch. On an application where search is one feature among many and you already have a data layer, that control is exactly what you want.

## Index Size and Build Time: What to Actually Measure

Every comparison of these libraries eventually argues about speed, usually with numbers from different machines and different corpora. The measurements that matter for a static site are narrower:

1. **Bytes transferred on first search.** Pagefind wins structurally: the initial payload is the runtime plus one fragment, not the corpus. If you ship an Orama or FlexSearch index, measure the gzipped size of the serialized index — that number is on your users' data plans.
2. **Build-step duration.** Pagefind adds a pass over `public/` after `hugo`. On a 10,000-page site that is minutes, not seconds, and it belongs in CI after the build, before deploy — never in a pre-commit hook.
3. **Time to first result on a cold cache.** This is where WASM plus fragment fetching beats parsing a multi-megabyte JSON blob, even though the raw query engine in FlexSearch is faster in isolation.
4. **Index freshness.** Pagefind's index is exactly as fresh as the last deploy. In-memory indexes are as fresh as your insert logic. Pick the failure mode you can live with.

If you benchmark, benchmark your own corpus, gzip the payload, and measure on a throttled connection. A "fast" search that downloads 8 MB first is not fast.

## Deployment Recipes

**Hugo on GitHub Pages (subpath):** run `hugo --minify`, then `npx pagefind --site public`. Commit the generated `public/` according to your deploy strategy, and remember the `bundlePath` option described above. The index must be regenerated on every content change — a stale `pagefind/` directory silently serves yesterday's results.

**CI ordering that works:** build → run Pagefind → deploy the artifact. If Pagefind runs before Hugo, it indexes the previous build; if it runs after deploy, the first visitors hit a 404 for the index.

**Orama or FlexSearch in an app:** build the index at build time, serialize it, and load it lazily — ideally only when the search box receives focus. A 2 MB index loaded on page load costs every visitor, including the majority who never search.

**Caching:** serve index files with long cache headers and content-hashed filenames. Both Pagefind fragments and serialized indexes are immutable per deploy, so there is no reason to re-download them.

## Common Traps

- **Indexing the chrome instead of the content.** Without `data-pagefind-body`, navigation and footer text pollute results. Every page then matches "Home About Contact".
- **Forgetting the subpath.** `/pagefind/` at the domain root on a project-pages deployment returns 404s. Set `bundlePath`.
- **Running the indexer before the site build.** The index silently reflects the previous deploy; queries return pages that no longer exist.
- **Committing a stale index.** Generated search artifacts belong to the deploy pipeline, not to source control, unless your host serves straight from the repo.
- **Assuming CJK works out of the box.** Pagefind ships language support and a `--force-language` override; FlexSearch needs an appropriate encoder and charset. Test with real queries in the target language.
- **Loading the whole index eagerly.** Defer Orama/FlexSearch initialization until the user interacts with search; for Pagefind, keep the default lazy fragment loading.
- **Ignoring typo tolerance expectations.** Users type "postgress". Orama handles tolerance configuration natively; Pagefind's model is prefix-oriented; FlexSearch needs encoder tuning. Choose based on your audience, not benchmarks.

## FAQ

**Is Pagefind free for commercial sites?**
Yes. Pagefind is MIT licensed and runs entirely in your build pipeline and the visitor's browser. There is no hosted service and no per-query cost.

**Can Pagefind work on GitHub Pages under a project subpath?**
Yes, but you must set `bundlePath` to the subpath, for example `/repo/pagefind/`. Without it the UI requests `/pagefind/` at the domain root and receives 404 responses.

**Does Orama need a server?**
No. Orama runs in the browser, in a worker, on an edge runtime or in Node. A server is optional and only useful when the index is too large to ship to clients.

**Which is faster, FlexSearch or Pagefind?**
They are not directly comparable. FlexSearch's in-memory query engine is extremely fast once the index is loaded; Pagefind transfers far less data on a cold visit because it fetches fragments on demand. For a content site the cold-visit experience usually decides the outcome.

**Can I use these with Hugo's multilingual sites?**
Yes. Pagefind detects language per page and can be forced with `--force-language`; Orama and FlexSearch require you to route queries to the right index and tokenizer configuration.

**Do I still need Meilisearch or Typesense?**
Only if you need server-side features: typo-tolerant search across millions of records, synonyms managed centrally, analytics, or instant indexing of content that is not in your build. For a static blog, a static index removes an entire service from your stack.

If you are still choosing the publishing stack itself, our [static site generator comparison](../self-hosted-static-site-generators-hugo-jekyll-astro-eleventy-guide/) covers Hugo against Jekyll, Astro and Eleventy. For the client-side library tier below Pagefind — fuzzy matching rather than index building — see the [Fuse.js vs MiniSearch vs Lunr.js comparison](../2026-08-18-fusejs-vs-minisearch-vs-lunrjs-client-side-fuzzy-search-comparison/). And if you eventually outgrow static search, the [Meilisearch vs Typesense vs SearXNG guide](../meilisearch-vs-typesense-vs-searxng/) covers the self-hosted server tier.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Pagefind vs Orama vs FlexSearch in 2026: Site Search That Still Works at 10,000 Pages",
  "description": "Pagefind, Orama and FlexSearch compared for static sites: build-time vs runtime indexes, real code, bundle weight, Hugo and GitHub Pages deployment, and subpath pitfalls.",
  "datePublished": "2026-11-04",
  "dateModified": "2026-11-04",
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
