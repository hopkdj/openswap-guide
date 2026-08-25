---
title: "Off the Main Thread in 2026: Comlink vs Partytown vs worker-dom for JavaScript Web Workers"
date: "2026-08-25"
tags: ["javascript", "web-workers", "performance", "frontend", "developer-tools"]
draft: false
cover: "/img/screenshots/partytown-cover.jpg"
---

Your page feels slow, and the culprit is almost never the network — it's the main thread. Every third-party script, every DOM mutation, every JSON parse runs on the one thread that also has to paint pixels and answer clicks, and browsers give you exactly one escape hatch: Web Workers. The problem is that Workers are hostile to work with — `postMessage` and structured cloning make even a counter tedious. Three open-source projects exist to fix this, and they fix *different* problems: Comlink (12,784 stars) removes the RPC boilerplate, Partytown (13,762 stars) moves third-party scripts wholesale, and worker-dom (3,263 stars) relocates DOM itself. Picking between them without knowing which layer each one owns is how teams end up with a worker architecture that's slower than the original.

## TL;DR: Which Web Worker Library Should You Use?

If you have **your own heavy code** (parsing, crypto, image processing, search) and just want it in a worker without `postMessage` ceremony, use **Comlink** — it turns a worker into a plain async object. If your problem is **third-party scripts** (analytics, chat widgets, marketing pixels) stealing main-thread time, use **Partytown** — it rewrites those scripts to run in a worker with zero changes to their calls. If you're building an **embeddable, content-heavy component** where DOM rendering itself is the bottleneck, evaluate **worker-dom** — it runs a real DOM API in a worker. These are not competitors: they compose. The common architecture is Comlink for your own modules, Partytown for the vendor junk, and worker-dom only when rendering work itself must leave the main thread.

## Comparison at a Glance

| | Comlink | Partytown | worker-dom |
|---|---|---|---|
| **Stars** | 12,784 | 13,762 | 3,263 |
| **Last push** | 2026-08-11 | 2026-08-25 | 2026-08-20 |
| **License** | Apache-2.0 | MIT | Apache-2.0 |
| **What it moves** | Your code (via RPC) | Third-party scripts | DOM operations |
| **API surface** | `wrap` / `expose` proxies | Script tag attribute + config | `upgradeElement` |
| **Vendor script support** | No | Yes (Google Analytics, GTM, etc.) | No |
| **Sync main-thread access** | No (async only) | Yes (Atomics-based) | Via DOM patches |
| **Bundle size** | ~1 KB | ~7 KB | ~40 KB (main) + worker |
| **Production status** | Stable, widely used | Beta (documented trade-offs) | Experimental (AMP lineage) |
| **Browser support** | All worker-capable browsers | Modern (needs service worker + Atomics) | Modern |

## Decision Matrix: Pick by Use Case

| Use Case | Recommendation | Why |
|---|---|---|
| Move your image/parsing/search code off main thread | **Comlink** | Wrap the worker once; call it like a local module |
| Kill the main-thread cost of analytics/tag managers | **Partytown** | Vendor scripts need zero code changes |
| Embed heavy third-party content in a sandboxed area | **worker-dom** | DOM work for that subtree happens in a worker |
| Multiple workers sharing typed APIs | **Comlink** | Proxies + transferables keep the plumbing invisible |
| E-commerce site drowning in marketing scripts | **Partytown** | It was built for exactly this (Builder.io, Qwik ecosystem) |
| Component that must stay responsive during render | **worker-dom** | Main thread keeps priority for interaction |

## Comlink: RPC for Workers Without the Boilerplate

Comlink is the smallest idea that changes everything: instead of `worker.postMessage()` and `onmessage` handlers on both sides, you get an async proxy. In the main thread you `wrap` the worker and call its methods like normal functions; inside the worker you `expose` an object. Comlink handles the message channel, serialization, errors, and even callbacks.

```js
import * as Comlink from "https://unpkg.com/comlink/dist/esm/comlink.mjs";

async function init() {
  const worker = new Worker("worker.js");
  // WebWorkers use postMessage and therefore work with Comlink.
  const obj = Comlink.wrap(worker);

  alert(`Counter: ${await obj.counter}`);
  await obj.inc();
  alert(`Counter: ${await obj.counter}`);
}
init();
```

```js
importScripts("https://unpkg.com/comlink/dist/umd/comlink.js");

const obj = {
  counter: 0,
  inc() {
    this.counter++;
  },
};
Comlink.expose(obj);
```

The rule of thumb Comlink's README hammers home: **if you're using the proxy, put `await` in front of it** — every property access and call is asynchronous, and exceptions are re-thrown on the caller side. Two primitives cover the edges: `Comlink.transfer(value, transferables)` hands ArrayBuffers to the worker without copying (zero-copy for large binary payloads), and `Comlink.proxy(fn)` passes a function reference so the worker can call *back* into the main thread. That combination — proxy in, transfer for bytes, proxy for callbacks — handles almost every real worker design, and it does it in about a kilobyte. It's Apache-2.0, Google-maintained, and stable enough that it's embedded in production tooling across the web. If your mental model of workers is the Node.js side of the same problem, our [Piscina vs workerpool vs poolifier comparison](../2026-08-20-nodejs-worker-pools-piscina-workerpool-poolifier-comparison/) covers the server-side equivalent.

## Partytown: Send Third-Party Scripts to the Worker

Partytown attacks a different enemy: the vendor scripts that *you* didn't write and can't refactor — analytics, tag managers, A/B testing, chat widgets. Their main-thread cost is real: each one parses, evaluates, and mutates the DOM, and they compete with your code for the same thread. Partytown's philosophy is blunt: **the main thread belongs to your code; everything else can wait in a worker.**

The integration is a script-tag attribute. You configure a forward list for the globals the vendor scripts will call, load Partytown, and mark the vendor scripts with `type="text/partytown"`:

```html
<script>
  partytown = {
    forward: ["dataLayer.push"],
  };
</script>
<script src="/~partytown/partytown.js"></script>
<script type="text/partytown" src="https://example.com/analytics.js"></script>
```

Partytown runs those scripts in a Web Worker backed by a service worker, and its sync-communication layer (Atomics + eval) lets the worker read and write the main thread's state — including `document`, `localStorage`, and cookies — with the same semantics the scripts expect. That's what makes it "drop-in": Google Analytics and tag-manager integrations work with their standard snippets. The trade-offs are documented honestly: some APIs can't be fully synchronized, it's labeled beta, and it only pays off when third-party script weight is actually significant. The picture below — from the project's own README — shows the difference: without Partytown, your code and third-party code fight for the main thread; with it, vendors are quarantined in the worker.

![Partytown moves third-party scripts off the main thread](/img/screenshots/partytown-inline.jpg "Partytown's architecture: third-party scripts relocated from the main thread into a web worker, freeing the main thread for your code")

The context matters: Partytown is built by Builder.io and is part of the Qwik ecosystem's performance story (their headline claim was cutting 99% of JavaScript with Qwik + Partytown). It's MIT-licensed, pushed within the last week, and the most directly actionable tool here if your performance budget is being eaten by vendor code. One caution: measure first — on a site with little third-party weight, Partytown's worker and service-worker overhead can exceed what it saves.

## worker-dom: The DOM API, Inside a Worker

worker-dom is the most ambitious of the three: an implementation of the DOM API that runs inside a Web Worker, sending only the *necessary* mutations to the foreground thread. Its stated purpose is to move "intermediate work related to DOM mutations" off the main thread — so a subtree of your page (typically embedded content from a third party) can be driven entirely from a worker, while the main thread stays free for high-priority interaction.

You upgrade a specific element to be worker-driven:

```html
<div src="hello-world.js" id="upgrade-me"></div>
```

```html
<script type="module">
  import { upgradeElement } from "./dist/main.mjs";
  upgradeElement(document.getElementById("upgrade-me"), "./dist/worker/worker.mjs");
</script>
```

With the module variant in place, the `div`'s entire subtree is rendered by the worker, and mutations are diffed and shipped to the main thread — the main thread only does the final paint work. It grew out of AMP (`amp-script` uses it to sandbox third-party content), which shows in its design: it's built for *embedded, quarantined* content rather than for relocating your whole app. That's also its limitation — it's an in-progress, experimental implementation, and the DOM surface is not 100% complete, so exotic APIs can trip it. But for the specific use case of "embed heavy third-party content without letting it jank my page," there is no other open-source option with this architecture. Apache-2.0, pushed recently, and worth a spike if you build embeds.

## Common Pitfalls and Migration Traps

**Workers are not free.** Spawning a worker has real startup cost (a new isolate, a fresh event loop, message channel setup). Moving a 5 ms task into a worker can make the total path *slower*. Profile first: Comlink's README and Partytown's docs both warn that off-threading only wins when the moved work is substantial or long-running.

**Structured cloning is the hidden tax.** Comlink's zero-copy `transfer` only applies to transferables (ArrayBuffers, MessagePorts, ImageBitmaps). Plain objects and typed arrays get cloned — and cloning a large object graph can take longer than the task itself. Design your worker payloads as flat buffers, not nested objects.

**Partytown's sync access has edges.** Some vendor patterns (synchronous `document.write`, certain `window` reads at load time) don't survive the relocation. The FAQ lists them; test your specific vendor scripts with the debug mode before trusting production numbers. And because it depends on a service worker plus Atomics, it's a modern-browser-only strategy.

**worker-dom is not a drop-in app framework.** You can't load React into a worker-dom worker and expect every React feature to work — the DOM subset is incomplete. It shines for sandboxed embedded content (its AMP lineage), not for re-architecting your application. Read the known-limitations list before committing.

**Cookie/localStorage semantics differ per tool.** Comlink gives you none (you design it), Partytown synchronizes them via its communication layer, and worker-dom doesn't solve them at all. If your worker code needs storage access, verify the behavior in each tool rather than assuming parity.

**Keep the main thread for interaction.** The entire point of this family of tools is that the main thread should never be blocked. A common anti-pattern: moving work to a worker, then `await`-ing it synchronously in a way that re-blocks rendering. Off-thread work should be fire-and-update — show a placeholder, update when the worker responds.

**Migrating a legacy main-thread codebase.** Start with Comlink on the single most expensive function (search, parse, transform). Keep the original synchronous path behind the same interface; flip the implementation to the worker behind a feature flag. Only reach for Partytown or worker-dom when vendor scripts or embedded content are the measured bottleneck — and measure before and after with real field data.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Off the Main Thread in 2026: Comlink vs Partytown vs worker-dom for JavaScript Web Workers",
  "description": "Comparison of the three JavaScript libraries for moving work off the main thread: Comlink RPC proxies, Partytown third-party script relocation, and worker-dom's DOM-in-worker implementation. Real GitHub stats, code examples, and decision matrix.",
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

### Are Comlink, Partytown, and worker-dom competitors?

Not really — they solve different layers of the same problem. Comlink removes RPC boilerplate for your own worker code, Partytown relocates third-party scripts into a worker without code changes, and worker-dom runs DOM operations for an embedded subtree inside a worker. Many sites use Comlink and Partytown together.

### What does Comlink actually do?

Comlink turns a Web Worker into an async object: `Comlink.wrap(worker)` returns a proxy whose methods you can call and await, and `Comlink.expose(obj)` in the worker makes that object available remotely. It replaces postMessage/onmessage plumbing, including error propagation and callback passing.

### Is Partytown production-ready?

Partytown is labeled beta but is widely deployed on high-traffic sites, especially in the Qwik ecosystem. The docs list explicit trade-offs (some sync APIs behave differently, modern browsers only). Test your specific vendor scripts with its debug tooling before trusting production metrics.

### When should I use worker-dom instead of Comlink?

When the DOM work itself is the bottleneck — for example, rendering a large embedded component or third-party content. worker-dom runs a DOM implementation inside the worker and ships only the necessary mutations to the main thread. For ordinary CPU work (parsing, computation), Comlink is simpler and sufficient.

### Do these libraries work with module workers and bundlers?

Comlink and worker-dom are ESM-friendly and bundle cleanly with Vite/webpack/Rollup; Comlink also ships UMD builds. Partytown is served as a static script with a service worker, so it integrates with any build system but has its own copying/placement steps. Check each project's docs for bundler-specific notes.

### What about WebAssembly and workers?

WebAssembly modules run natively inside workers, so the combination is powerful: a WASM module doing heavy work in a worker, exposed to the main thread through Comlink's proxy. For the server side of that story, see our [WASM runtime comparison](../2026-04-21-wasmedge-vs-wasmtime-vs-wasmer-self-hosted-webassembly-runtimes-guide-2026/). For reference, heavy browser tooling like code editors — covered in our [Monaco vs CodeMirror vs Ace guide](../2026-08-22-browser-code-editors-monaco-codemirror-ace-comparison/) — is exactly the kind of workload these off-threading patterns are built for.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
