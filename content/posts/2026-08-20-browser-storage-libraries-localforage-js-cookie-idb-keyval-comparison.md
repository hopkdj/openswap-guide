---
title: "Browser Storage in 2026: localForage vs js-cookie vs idb-keyval — Stop Losing User Data to the Wrong API"
date: "2026-08-20"
tags: ["javascript", "browser-storage", "indexeddb", "localstorage", "cookies", "frontend", "pwa"]
draft: false
cover: "/img/screenshots/localforage-cover.png"
---

Your user spends forty minutes building something in your web app, the browser tab crashes, and everything is gone. That is the silent failure mode of web storage: it is not a server outage, not a network issue — the data was sitting in a JavaScript variable the whole time because nobody shipped it to the right storage API. The average web developer now has **three mainstream browser storage mechanisms** — cookies, localStorage, and IndexedDB — plus a pile of wrapper libraries that make the choice even more confusing. And the stakes are higher than they look: cookies ride along with every HTTP request, localStorage is synchronous and capped at about 5 MB, and IndexedDB is asynchronous, powerful, and famously painful to use directly.

The three libraries that fix this mess are **localForage (25,803 stars), js-cookie (22,593 stars), and idb-keyval (3,229 stars)**. Each one exists because a native API is awkward: localForage wraps IndexedDB/WebSQL/localStorage behind a simple promise API, js-cookie makes cookies tolerable, and idb-keyval compresses IndexedDB down to a five-function key-value store. This guide tells you which one belongs in which part of your app — and, just as importantly, which native API each one is hiding from you.

## TL;DR — Quick Verdict

Use **js-cookie** for anything the server needs on every request — session IDs, preferences, A/B variants — where a 4 KB cookie with an `expires` date is the right tool. Use **localForage** for general application data (form drafts, cached responses, user settings) when you want a simple `getItem`/`setItem` API and browser fallbacks without thinking about IndexedDB at all. Use **idb-keyval** when you are already building on IndexedDB — large blobs, images, offline-first data — and want a tiny, typed, dependency-free promise wrapper instead of localForage's driver abstraction. If you need to *query* data (indexes, ranges, filters), skip all three and use the `idb` library or raw IndexedDB — key-value wrappers cannot do relational queries.

## Quick Comparison Table

| Feature | localForage | js-cookie | idb-keyval |
|---|---|---|---|
| What it wraps | IndexedDB / WebSQL / localStorage | `document.cookie` | IndexedDB |
| Primary use | App data storage with simple API | Small server-bound values | Large/structured data on IndexedDB |
| GitHub stars | 25,803 | 22,593 | 3,229 |
| License | Apache-2.0 | MIT | NOASSERTION (ISC-style) |
| Last push | 2024-07-30 (stable, maintenance) | 2026-08-10 | 2026-07-08 |
| API style | `getItem`/`setItem` (localStorage-like) | `Cookies.set/get/remove` | `get`/`set`/`del` promises |
| Async | Yes (promises + callbacks) | No (synchronous) | Yes (promises) |
| Size limit | IndexedDB (practically unlimited) | 4 KB per cookie | IndexedDB (practically unlimited) |
| Bundled size | ~29 KB min+gzip | ~1 KB | ~600 B |
| Query/index support | No | No | No |
| Fallback drivers | IndexedDB → WebSQL → localStorage | N/A | N/A |

## Use Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Session token, language, or A/B variant the server must see | **js-cookie** | Cookies are the only storage that travels with every request automatically |
| Form drafts, cached API responses, user preferences (5 MB+ data) | **localForage** | localStorage-like API, no size anxiety, works on every browser |
| Offline-first app storing blobs, images, or large structured data | **idb-keyval** | Direct IndexedDB access, tiny bundle, promise-based |
| You need indexes, ranges, or queries over stored records | **raw IndexedDB / idb** | Key-value wrappers cannot filter or query — this is beyond all three |
| App must work in old browsers (IE11-era) | **localForage** | Its driver fallback chain exists precisely for this |
| Settings object that changes frequently and must persist | **localForage or idb-keyval** | Async storage keeps writes off the main thread; localStorage would block |
| PWA offline caching of UI state | **idb-keyval** | Works inside service workers, tiny, no DOM dependency |
| "Just remember the user's name and theme" | **localStorage directly** | Don't add a dependency for two strings — but use async storage once data grows |

## localForage — The Simple API over the Powerful Engine

localForage's pitch is one sentence: "Offline storage, improved — wraps IndexedDB, WebSQL, or localStorage using a simple but powerful API." It gives you the exact `getItem`/`setItem`/`removeItem` API you already know from localStorage, but backed by IndexedDB — so the 5 MB localStorage ceiling disappears and writes become asynchronous. It automatically picks the best available driver at runtime: IndexedDB first, WebSQL as a fallback, localStorage as the last resort.

```js
import localforage from 'localforage';

// Optional: name your database and store
localforage.config({
  name: 'my-app',
  storeName: 'keyvaluepairs',
});

// Promise-based API
await localforage.setItem('userProfile', { name: 'Ada', theme: 'dark' });
const profile = await localforage.getItem('userProfile');
await localforage.removeItem('userProfile');

// Callback API also supported
localforage.setItem('key', 'value', function (err) { /* ... */ });
```

Because the API is identical to localStorage, migrating an existing localStorage-based app is a find-and-replace: swap `window.localStorage.getItem` for `await localforage.getItem` and you gain async writes and effectively unlimited space. The `localforage.iterate()` helper streams through every entry (handy for export/backup features), and you can force a driver with `localforage.setDriver(localforage.INDEXEDDB)`.

The honest caveat: **localForage is in maintenance mode** — its last push was July 2024, and the project's own stance is that it is feature-complete. That is fine for a stable wrapper (the underlying APIs it targets are frozen), but teams should know there will be no new driver support. WebSQL, one of its fallback drivers, has been deprecated for years (Safari shipped its removal in 2024, Firefox never had it), which leaves IndexedDB and localStorage as the real fallback chain in practice. For most applications this changes nothing: IndexedDB is supported everywhere modern, and that is where localForage ends up anyway.

## js-cookie — Cookies Done Right

Cookies are the storage mechanism the server actually sees, and js-cookie exists because `document.cookie` is one of the worst APIs in the platform — a single string you parse with `; ` splits, with no escaping, no JSON, and no per-property management. js-cookie gives you a sane, tiny (~1 KB) wrapper with three functions and attribute handling:

```js
import Cookies from 'js-cookie';

// Basic
Cookies.set('name', 'value');
Cookies.get('name');        // => 'value'
Cookies.remove('name');

// With attributes
Cookies.set('name', 'value', { expires: 7, path: '' });   // 7 days, site-wide
Cookies.set('prefs', { theme: 'dark' });                   // JSON serialized
Cookies.set('session', 'abc123', { secure: true, sameSite: 'strict' });

// Read everything
Cookies.get();   // => { name: 'value', prefs: '{"theme":"dark"}' }
```

Plain objects passed to `set` are JSON-serialized automatically and parsed on `get` — the most common cookie pain point solved. The `expires` attribute takes days (or a `Date`), and `sameSite`, `secure`, `domain`, and `path` are all first-class. This library is actively maintained (last push August 2026), works in browsers and Node, and has no dependencies.

The real pitfalls live in the *semantics* of cookies, not in js-cookie itself. The README documents the two that bite everyone. First, `Cookies.remove('name')` only works if you pass the same `path`/`domain` the cookie was set with — `Cookies.set('name', 'value', { path: '' })` followed by a bare `Cookies.remove('name')` silently fails, leaving a zombie cookie. Second, `domain` only matters for cross-subdomain reads: `Cookies.get('foo', { domain: 'sub.example.com' })` does not filter anything — the domain attribute is *write-time only*. And the hard platform limit: 4 KB per cookie and ~50-100 cookies per domain. Every byte you store in a cookie is re-sent with every request to that domain, so bloating cookies with app state is a performance tax you pay on every page load.

## idb-keyval — The 600-Byte IndexedDB Key-Value Store

idb-keyval, by Jake Archibald (ex-Google Chrome, the person behind service workers), is the minimal viable wrapper: a promise-based key-value store on IndexedDB in about 600 bytes, with zero dependencies and TypeScript types built in. There is no driver abstraction, no config layer — just functions:

```js
import { get, set, del, setMany, getMany, entries, clear } from 'idb-keyval';

// Default store (database 'keyval-store')
await set('hello', 'world');
await get('hello');   // => 'world'
await del('hello');

// Custom store for separating concerns
import { createStore } from 'idb-keyval';
const store = createStore('my-db', 'my-store');
await set('profile', profile, store);
await get('profile', store);

// Batch operations — the big IndexedDB performance win
await setMany([['a', 1], ['b', 2]], store);
await getMany(['a', 'b'], store);   // => [1, 2]
```

The batch helpers (`setMany`/`getMany`/`delMany`) are worth the download alone: IndexedDB transactions are expensive to open, and batching keys into one transaction is dramatically faster than a loop of individual `set` calls. `entries()`, `keys()`, and `values()` round out the API, and everything returns promises, so it slots into service workers and async modules without ceremony.

Because it is a straight key-value store, idb-keyval inherits IndexedDB's capabilities — essentially unlimited storage, structured-clone serialization (objects, blobs, `ArrayBuffer`s, `File`s), and async, off-main-thread writes — while hiding the verbosity. The trade-off versus localForage is purely ergonomic: no fallback chain and no legacy-browser support, which matters exactly never for modern apps and always for IE-era targets. And like every key-value wrapper, queries are out of scope: if you need to find "all orders where total > 100," you need real IndexedDB with indexes (the `idb` library by the same author is the recommended stepping stone).

## Pitfalls and Gotchas — What Nobody Tells You

**1. localStorage is synchronous and blocks the main thread.** Every `getItem` on localStorage runs the storage engine synchronously on the UI thread. A few hundred KB of cached data, read on startup, adds visible jank on low-end devices. Anything beyond a few strings belongs in async storage (localForage or idb-keyval). This is also why localStorage is a bad home for data that grows.

**2. Cookies are not free storage — they are request baggage.** The 4 KB limit per cookie is real, but the silent cost is bandwidth: every cookie is sent with every request to its domain, including images, scripts, and API calls. A 3 KB cookie on a page with 100 requests is 300 KB of overhead. Keep cookies for server-bound identity/preferences; keep app data out of them.

**3. The `path` attribute is a footgun in every cookie library.** Setting `Cookies.set('name', 'value', { path: '' })` then calling `Cookies.remove('name')` without the same path leaves the cookie in place. Establish one convention (always pass `path` explicitly, or always use the default) and never mix.

**4. "Works in private browsing" is not guaranteed.** Safari's private mode historically evicts or refuses persistent storage; browsers under storage pressure evict data; and the Storage Partitioning changes (Chrome 108+) isolate third-party storage. Design for data loss — flush important state to a server, and treat client storage as a cache, not a source of truth.

**5. WebSQL is gone; do not let a fallback chain fool you.** localForage's WebSQL fallback is dead weight in every modern browser (Safari removed WebSQL support in 2024). The effective chain is IndexedDB → localStorage. If you use localForage, verify with `localforage.driver()` at runtime which driver actually loaded instead of assuming.

**6. Key-value stores cannot query — plan for that before you need it.** The moment your stored records need indexes, ranges, or filtered reads, localForage and idb-keyval both force you to load everything and filter in JavaScript, which is O(n) and slow at scale. If queries are on the roadmap, start with real IndexedDB indexes or a document store early; retrofitting is painful. The [web spreadsheet libraries guide](../2026-08-14-web-spreadsheet-libraries-univer-handsontable-luckysheet-guide/) shows how serious persistence needs (document cells, undo history) force exactly this kind of storage engineering.

**7. Versioned schemas for IndexedDB are your job.** Raw IndexedDB and wrappers like idb-keyval do not migrate your data when you change the shape of what you store. You must version your store (`createStore('my-db', 'my-store-v2')`) or write a migration step; localForage's `storeName` plays the same role. Bump it when shapes change, or old data corrupts the new code paths.

For the broader frontend architecture, our [state management comparison](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/) covers where persisted state fits in your store layer, and the [data fetching guide](../2026-08-11-tanstack-query-vs-swr-vs-rtk-query-react-data-fetching-comparison/) shows cache-and-persist patterns that pair naturally with client-side storage for offline-first experiences.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Browser Storage in 2026: localForage vs js-cookie vs idb-keyval — Stop Losing User Data to the Wrong API",
  "description": "Deep comparison of localForage, js-cookie, and idb-keyval for browser storage in 2026: features, GitHub stats, API examples, size limits, pitfalls, and a decision matrix for cookies, localStorage, and IndexedDB.",
  "datePublished": "2026-08-20",
  "dateModified": "2026-08-20",
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

### What is the difference between localStorage, sessionStorage, cookies, and IndexedDB?

localStorage and sessionStorage are synchronous string stores (5-10 MB, per-origin); sessionStorage clears when the tab closes. Cookies are small (4 KB each), sent automatically with every request to the domain. IndexedDB is an asynchronous, transactional, schema-free database with practically unlimited storage and structured-clone support for objects, blobs, and files. Wrapper libraries hide the complexity of the last three.

### Is localForage still maintained in 2026?

localForage is in maintenance mode — its last push was July 2024, and the project considers itself feature-complete. It remains stable and widely used (25,803 stars) because the browser APIs it wraps are frozen. Teams wanting an actively-developed wrapper should look at idb-keyval (last push July 2026) or raw IndexedDB with the `idb` helper.

### When should I use cookies instead of localStorage or IndexedDB?

When the server needs the value on every request: session identifiers, language selection, consent flags, A/B test assignments. Cookies are the only storage automatically attached to HTTP requests. For anything the server does not need on every request, prefer async client storage — cookies waste bandwidth and have a hard 4 KB size limit.

### Can I store objects in cookies?

Yes, with js-cookie: `Cookies.set('prefs', { theme: 'dark' })` serializes the object to JSON automatically and parses it back on `get`. Raw `document.cookie` does no such thing — you would handle JSON serialization and escaping yourself. Even with JSON, remember the 4 KB cookie cap and the per-request bandwidth cost.

### How much data can I store with localForage or idb-keyval?

Effectively as much as the browser allows, because both wrap IndexedDB — no fixed 5 MB localStorage cap. Practical limits are set by the browser's storage quota, which is shared with Cache Storage and other origin data (Chrome typically allows a large fraction of free disk space per origin). Browsers can evict data under storage pressure, so treat large client stores as a cache layer, not a backup.

### Is localStorage synchronous a real problem?

Yes, for non-trivial data. localStorage reads and writes execute synchronously on the main thread, so a large cached payload read at startup blocks rendering and interaction. Async storage (IndexedDB via localForage or idb-keyval) performs reads and writes without blocking the UI, which matters on mobile devices and for growing datasets.

### Which library should I use for an offline-first PWA?

idb-keyval is the strongest fit: it works inside service workers, has no DOM or window dependency, is ~600 bytes, and its batch helpers (`setMany`/`getMany`) make the frequent multi-key writes of offline sync fast. Pair it with the Cache Storage API for network responses; use idb-keyval for app state and user-generated data.

### Do I need a library at all, or can I use native APIs directly?

For two or three small strings, use localStorage directly — a dependency is overkill. For real application data, the native APIs are where the bugs live: `document.cookie` parsing/escaping, localStorage's sync blocking and 5 MB cap, and IndexedDB's verbosity. Wrapper libraries exist precisely because these three APIs are error-prone at the edges; the 600-byte cost of idb-keyval buys you correct transaction handling and structured clones.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
