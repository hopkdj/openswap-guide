---
title: "Fuse.js vs MiniSearch vs Lunr.js in 2026: Which Client-Side Search Library Should You Use?"
date: "2026-08-18"
tags: ["javascript", "search", "frontend", "developer-tools"]
draft: false
cover: "/img/screenshots/fuse-cover.jpg"
---

You have 20,000 product docs sitting in your React app, and your users keep typing "settngs" instead of "settings". Every keystroke fires a request to your search server, your API bill climbs, and the response still feels sluggish. Client-side search libraries solve this by moving the index into the browser — but choosing the wrong one means either typo-blind results or a bundle that chokes mobile users.

Three libraries dominate this space: **Fuse.js (20,447 stars)**, **MiniSearch (6,095 stars)**, and **Lunr.js (9,199 stars)**. All three run entirely in the browser, all three are MIT-licensed and dependency-free, and all three will happily index your documents in memory. They differ drastically in *what kind of search* they perform, and that difference decides which one you should ship.

## TL;DR / Quick Verdict

**If your core problem is typos and fuzzy autocomplete** (typeahead over names, tags, command palettes), pick **Fuse.js** — it is the strongest approximate-matching engine here and its new token search handles multi-word queries well. **If you need real full-text search** — tokenization, prefix matching, field boosting, ranking of 10,000+ documents — pick **MiniSearch**; it is the best-engineered full-text library in this trio and stays under ~4 kB gzipped. **If you need a proven, boring, maintenance-mode library** on a static site with a pre-built index, **Lunr.js** still works — just know it hasn't had a meaningful release in years. Choose based on search *semantics*, not star count.

## Quick Comparison Table

| Feature | Fuse.js | MiniSearch | Lunr.js |
|---|---|---|---|
| **Approach** | Approximate (fuzzy) string matching | Full-text inverted index + BM25-style ranking | Full-text inverted index + tf-idf ranking |
| **GitHub stars** | 20,447 | 6,095 | 9,199 |
| **Last push** | 2026-08-09 | 2025-09-16 | 2024-07-31 |
| **Typo tolerance** | ✅ Core feature (Bitap algorithm) | ✅ Via `fuzzy` option (edit distance) | ⚠️ Basic (wildcards / edit distance) |
| **Multi-word query ranking** | ✅ Token Search (BM25 IDF) | ✅ Built-in | ⚠️ OR-by-default, no smart ranking |
| **Prefix search** | ✅ Extended search | ✅ `prefix: true` | ✅ `*` wildcards |
| **Field boosting** | ✅ Weighted keys | ✅ `boost` option | ✅ Boost at index or query time |
| **Auto-suggestions** | ❌ | ✅ Built-in | ❌ |
| **Dynamic index (add/remove)** | ✅ `add()` / `remove()` | ✅ `add()` / `remove()` | ❌ Rebuild required |
| **Language support** | Unicode-aware, CJK via `Intl.Segmenter` | English + stemming, configurable | 14 languages built-in |
| **Bundle (min+gzip)** | ~6.8 kB basic / ~8.6 kB full | ~4 kB | ~28 kB |
| **Maintenance status** | Active | Active | Maintenance mode |
| **License** | Apache-2.0 | MIT | MIT |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Command palette / typeahead with typos | **Fuse.js** | Bitap fuzzy matching is purpose-built for "I typed it wrong" search over names and tags |
| Docs site or knowledge base search | **MiniSearch** | Real tokenization + ranking gives the best relevance for multi-paragraph content |
| Offline-first mobile app search | **MiniSearch** | Smallest memory footprint, built for resource-constrained browsers |
| Static site with pre-built index | **Lunr.js** | Classic build-time index workflow; zero JS framework needed |
| Search across 100K+ documents in the browser | **Fuse.js + FuseWorker** | Web Worker parallel search is ~5x faster on large corpora |
| You need CJK / Thai word segmentation | **Fuse.js** | `Intl.Segmenter`-based tokenizer handles languages without spaces |

## Fuse.js — The Fuzzy Match Specialist

Fuse.js is a lightweight, zero-dependency fuzzy-search library written in TypeScript. It uses the **Bitap algorithm** for approximate string matching, which means it shines exactly where users are sloppy: typos, misspellings, and partial matches are handled out of the box.

```js
import Fuse from 'fuse.js'

const books = [
  { title: "Old Man's War", author: 'John Scalzi' },
  { title: 'The Lock Artist', author: 'Steve Hamilton' },
  { title: 'HTML5', author: 'Remy Sharp' },
  { title: 'JavaScript: The Good Parts', author: 'Douglas Crockford' }
]

const fuse = new Fuse(books, {
  keys: ['title', 'author']
})

fuse.search('javscript')
// → [{ item: { title: 'JavaScript: The Good Parts', ... }, ... }]
```

The `keys` array maps which fields to search, and you can assign weights so a title match outranks a description match: `[{ name: 'title', weight: 2 }, { name: 'description', weight: 1 }]`. For precise control, extended search adds operators (`=term` exact, `^term` prefix, `!term` exclusion) via `useExtendedSearch: true`, and the object query syntax expresses the same operators without magic characters:

```js
const fuse = new Fuse(list, { keys: ['title', 'author'] })
fuse.search({ title: { $startsWith: 'old' }, author: { $eq: 'Kay' } })
```

The two features that keep Fuse.js ahead of its rivals in 2026 are **Token Search** and **FuseWorker**. Token Search (`useTokenSearch: true`) splits multi-word queries into independent terms, fuzzy-matches each, and ranks results with BM25-style IDF weighting — type `"express midleware rout"` and it finds "Express Middleware" and "Express Routing Guide" despite typos in every word. FuseWorker splits large datasets across Web Workers and searches in parallel, claiming roughly 5x faster search on 100K documents without freezing the UI. Dynamic collections (`fuse.add()` / `fuse.remove()`) round out the package.

One honest caveat: Fuse.js is a *matcher*, not a full-text engine. It won't stem words ("running" vs "run") or understand synonyms, and its default single-field scoring is simpler than MiniSearch's. For plain fuzzy search you only need the ~6.8 kB basic build; the full build (~8.6 kB) adds extended, logical, and token search.

## MiniSearch — The Tiny Full-Text Engine

MiniSearch is a "tiny but powerful in-memory full-text search engine" with a proper inverted index and modern BM25-style ranking. Where Fuse.js optimizes for *approximate* matching, MiniSearch optimizes for *relevance*: tokenize the corpus, build a real index, rank results, boost fields — all in a package designed for memory-constrained environments like mobile browsers.

```javascript
let miniSearch = new MiniSearch({
  fields: ['title', 'text'],        // fields to index for full-text search
  storeFields: ['title', 'category'] // fields to return with search results
})

miniSearch.addAll(documents)

let results = miniSearch.search('zen art motorcycle')
// => [
//   { id: 2, title: 'Zen and the Art of Motorcycle Maintenance', category: 'fiction', score: 2.77, ... },
//   { id: 4, title: 'Zen and the Art of Archery', category: 'non-fiction', score: 1.39, ... }
// ]
```

Search options cover the full spectrum: field-scoped search, field boosting (`boost: { title: 2 }`), prefix search (`prefix: true`), fuzzy matching with a max edit distance proportional to term length (`fuzzy: 0.2`), and even a `filter` callback for faceted results:

```javascript
// The misspelled 'ismael' matches 'ishmael' at fuzzy: 0.2
miniSearch.search('ismael', { fuzzy: 0.2 })

// Default options can be baked into the constructor
miniSearch = new MiniSearch({
  fields: ['title', 'text'],
  searchOptions: { boost: { title: 2 }, fuzzy: 0.2 }
})
```

MiniSearch also ships an **auto-suggestion engine** for query autocompletion — something neither competitor offers — and documents can be added or removed from the live index at any time. It has zero external dependencies and follows semantic versioning with a proper changelog. Its trade-off is the reverse of Fuse.js's: fuzzy matching is a configurable option rather than the core identity, so heavy typo tolerance costs you a bit of tuning effort. The project's cadence is slower (last push September 2025), but it is stable, complete software — not abandoned.

## Lunr.js — The Granddaddy, Still in Maintenance Mode

Lunr.js has been around since 2013, and its tagline says it all: *"A bit like Solr, but much smaller and not as bright."* It was the default client-side search for Jekyll, GitBook, and a generation of static sites. Its builder-style API is instantly recognizable:

```javascript
var idx = lunr(function () {
  this.field('title')
  this.field('body')

  this.add({
    "title": "Twelfth-Night",
    "body": "If music be the food of love, play on: Give me excess of it…",
    "author": "William Shakespeare",
    "id": "1"
  })
})

idx.search("love")
// → [{ ref: "1", score: 0.354, matchData: { ... } }]
```

Lunr supports full-text search in 14 languages, term boosting at query or index time, field-scoped searches, and fuzzy matching via wildcards or edit distance. The killer workflow for static sites is **pre-building the index at build time** (the `lunr` npm package runs in Node), serializing it as JSON, and loading it into the browser — no client-side indexing cost at all.

The bad news is that Lunr.js is effectively in **maintenance mode**: the last real release was years ago and the last repo push was July 2024. There are no security concerns (it has zero dependencies and runs entirely client-side), but you should treat it as frozen software — new language features, modern bundler ergonomics, and bug fixes are not coming. If you need a stable index format for a docs site and don't care about new features, it still works fine. If you're starting a new project today, MiniSearch is the modern replacement with the same build-time-index workflow and better ranking.

## Common Pitfalls and Migration Gotchas

1. **Choosing by stars instead of semantics.** Fuse.js has 3x MiniSearch's stars, but for a 50,000-document docs corpus, full-text ranking beats fuzzy matching. Stars measure popularity, not fit.
2. **Forgetting `useExtendedSearch`.** In Fuse.js, operator characters like `=term` and `^term` are treated as literal text unless you enable extended search. Use the object query syntax — it needs no flag and validates strictly.
3. **Unbounded `fuzzy` in MiniSearch.** `fuzzy: 0.2` means max edit distance = 20% of the term length. Values above ~0.3 produce noise on short queries like "cat".
4. **Lunr.js has no incremental updates.** Documents added after index creation require a full rebuild. For chatty, frequently-changing datasets this is a dealbreaker.
5. **Client-side search has a ceiling.** All three keep the index in memory. Beyond roughly 100K documents you should move to a server-side engine — the Web Worker trick only pushes the limit, it doesn't remove it.
6. **Highlighting is DIY.** None of these ship a ready-made highlighter UI. Fuse.js gives you `includeMatches` with character indices, MiniSearch returns match metadata — you still have to render it yourself (a good companion to our [syntax highlighting libraries comparison](../2026-08-12-highlightjs-vs-prism-vs-shiki-syntax-highlighting-comparison/)).
7. **CJK and Thai text.** Word-based indexing breaks on languages without spaces. Fuse.js handles them via `Intl.Segmenter` tokenization; verify MiniSearch's tokenizer config before committing to a multilingual corpus.
8. **Bundle-size creep.** Mixing a fuzzy library *and* a full-text engine in one app doubles your search payload. Pick one primary engine and keep the other out.

## Migration Guide: Fuse.js → MiniSearch (or Vice Versa)

Migrating between these libraries is more about semantics than syntax. If you're moving Fuse.js fuzzy search to MiniSearch full-text, wrap your query pipeline: keep `fuzzy: 0.2` and `prefix: true` as default search options so existing users keep their typo tolerance, then re-map your highlighting code from Fuse's `includeMatches` indices to MiniSearch's `match` metadata. Moving MiniSearch to Fuse.js for a typeahead-heavy UI is easier: Fuse's weighted `keys` and object query syntax map naturally onto the autocomplete pattern, and `Fuse.match()` covers single-string comparisons without building an index at all. In both directions, snapshot your top-100 queries before and after the migration and compare result relevance — ranking changes are the one thing unit tests never catch.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Fuse.js vs MiniSearch vs Lunr.js in 2026: Which Client-Side Search Library Should You Use?",
  "description": "Compare Fuse.js, MiniSearch, and Lunr.js for client-side search in 2026: fuzzy matching vs full-text ranking, bundle sizes, GitHub stats, decision matrix, and migration tips.",
  "datePublished": "2026-08-18",
  "dateModified": "2026-08-18",
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

### Which client-side search library is best for a React app?

For React typeahead and fuzzy search, Fuse.js integrates cleanly and its weighted keys fit component-driven UIs. For full-text search over a large content corpus, MiniSearch is the better engine — pair it with your existing data-fetching layer (see our [TanStack Query vs SWR vs RTK Query comparison](../2026-08-11-tanstack-query-vs-swr-vs-rtk-query-react-data-fetching-comparison/) for the data side).

### Is Lunr.js still maintained in 2026?

Effectively no — the last push was July 2024 and there have been no meaningful releases in years. It remains usable for static-site search with a pre-built index, but new projects should prefer MiniSearch (same workflow, modern ranking).

### Can Fuse.js handle multi-word queries?

Yes, since the addition of Token Search (`useTokenSearch: true`), which fuzzy-matches each word independently and ranks results with BM25-style IDF weighting. Without it, multi-word queries degrade to looser single-pattern matching.

### What is the largest dataset these libraries can handle in the browser?

A practical ceiling is roughly 100K documents. Fuse.js's FuseWorker pushes this via parallel Web Worker search (~5x faster on 100K documents), but beyond that, an in-memory index in the browser becomes the wrong architecture — move to a server-side search engine.

### Do these libraries work offline?

Yes — the index lives entirely in memory or in a serialized blob you load at runtime, so search works without a network connection. That is the main reason to choose client-side search over an API-backed search box. The terminal-world equivalent is explored in our [fzf vs skim vs peco fuzzy finder guide](../2026-06-16-self-hosted-cli-fuzzy-finders-fzf-skim-peco/).

### Are there server-side alternatives if my corpus outgrows the browser?

Yes — Meilisearch, Typesense, and Sonic are self-hosted engines with similar typo tolerance and far larger capacity. If your dataset is already server-side, you can also run Lunr.js's index build in Node during CI and serve the serialized index as a static asset, as many docs sites do.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
