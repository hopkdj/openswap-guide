---
title: "htmx vs Alpine.js vs Unpoly in 2026: Server-Rendered Interactivity Without the SPA"
date: "2026-08-10"
tags: ["javascript", "frontend", "web-development"]
draft: false
cover: "/img/screenshots/alpine-hero.jpg"
---

Remember when every web app had to be a single-page application with a 400 KB JavaScript bundle, a build pipeline with seventeen dependencies, and a backend that returns JSON instead of HTML? The industry spent a decade building that — and then a quiet counter-revolution started. Server-rendered interactivity libraries — **htmx** (48,921 stars), **Alpine.js** (31,850 stars), and **Unpoly** (2,769 stars) — let you build genuinely interactive interfaces by enhancing HTML directly, with a fraction of the JavaScript, no client-side rendering, and no API layer. In 2026 these three are the mainstream answer to "do I really need React for this?" and this guide will show you exactly which one matches your stack.

**TL;DR:** If your backend already renders HTML and you want interactivity driven by *server responses* (partial HTML swaps, server-side validation) — pick **htmx**. If you want to sprinkle client-side behavior (dropdowns, modals, toggles) into server-rendered pages with the least ceremony — pick **Alpine.js**. If you are on a mature server framework (especially Rails or a PHP MVC) and want progressive enhancement with graceful degradation — pick **Unpoly**. htmx and Alpine complement each other beautifully; Unpoly is the opinionated framework that does both.

## Quick Comparison: htmx vs Alpine.js vs Unpoly

| Dimension | htmx | Alpine.js | Unpoly |
|---|---|---|---|
| GitHub stars | 48,921 | 31,850 | 2,769 |
| License | BSD-2-Clause | MIT | MIT |
| Last push (2026) | Aug 05 | Aug 09 | Aug 08 |
| Size (minified+gzip) | ~14 KB | ~15 KB | ~30 KB |
| Version (2026) | 2.x | 3.15.x | 3.x |
| Core mechanism | Server-driven HTML swaps | Client-side reactive state | Progressive-enhancement navigation |
| Attributes | `hx-get`, `hx-post`, `hx-target`... | `x-data`, `x-show`, `x-on`... | `up-follow`, `up-target`... |
| Partial page updates | Yes (fragments) | No (DOM manipulation) | Yes (fragments + layers) |
| Form validation | Server-side via swap | Client-side via JS | `up-validate` server round-trip |
| Requires JS build step | No | No | No |
| Graceful degradation | Partial (needs JS for hx-*) | No (JS required) | Yes (best in class) |
| Server language fit | Any (HTML in, HTML out) | Any | Rails/PHP-first docs |

## Use Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Django/Rails/Laravel app, want dynamic pages without an API | htmx | Attribute-driven partial swaps fit server templates perfectly |
| Marketing site with a few interactive components | Alpine.js | One script tag, `x-data` islands, zero build tooling |
| Legacy server app you must not break | Unpoly | Best-in-class progressive enhancement; works without JS |
| Real-time features (chat, dashboards, notifications) | htmx + SSE/WebSocket | `hx-trigger="every 5s"` and SSE support built in |
| You already use both htmx and need UI state | htmx + Alpine | The officially blessed pairing — htmx for server, Alpine for client |

## htmx — The Hypermedia Workhorse

htmx is the largest and most influential of the three, and its pitch is disarmingly simple: *any HTML element can issue an HTTP request, and any HTML element can be replaced by the response*. Instead of building an API and a client-side state layer, you annotate your server-rendered markup with a handful of `hx-*` attributes and the server returns the HTML fragment that should replace part of the page. As of August 2026 it has **48,921 stars** (last push August 5) and its 2.x line is the default choice for the "hypermedia-driven applications" movement.

Installation is one script tag — no build step, no framework integration:

```html
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js"></script>
```

The core pattern is a request triggered by a UI event, targeted at a DOM element, swapping in the server's HTML response. This is the canonical example from the official docs:

```html
<button hx-post="/clicked"
    hx-trigger="click"
    hx-target="#parent-div"
    hx-swap="outerHTML">
    Click Me!
</button>
```

Click the button, htmx POSTs to `/clicked`, and the server's HTML response replaces the `#parent-div` element. No fetch, no JSON, no state synchronization — the server remains the single source of truth, and the response is markup any developer can read. Beyond the basics, htmx ships genuinely powerful features: `hx-trigger` supports debouncing, throttling, and polling (`every 5s`); `hx-boost` turns regular links and forms into AJAX requests transparently; and the `hx-sse` and `hx-ws` extensions give you Server-Sent Events and WebSocket updates for dashboards and chat without writing a line of client-side connection code. The official logo says it all — high power, low ceremony:

![htmx logo](/img/screenshots/htmx-logo.png "htmx - high power tools for HTML")

The cost is a mindset shift: you must be comfortable letting the server drive UI state, which means unlearning SPA habits like optimistic updates and client-side caches. And htmx is deliberately *not* a state-management tool — complex client-side state still needs Alpine or a dedicated solution.

## Alpine.js — Declarative Behavior in Your Markup

Alpine.js is best described as "Tailwind for JavaScript": a tiny, drop-in library that lets you write interactive behavior *inside your HTML* using `x-*` directives, without leaving your template. Created by Caleb Porzio (the Laravel Livewire author), it has **31,850 stars** (last push August 9, 2026) and is the natural companion to server-rendered apps that need client-side interactivity — the counter below is the canonical example straight from the official docs:

```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.12/dist/cdn.min.js"></script>

<div x-data="{ count: 0 }">
  <button x-on:click="count++">Increment</button>
  <span x-text="count"></span>
</div>
```

Everything starts with `x-data`, which declares a reactive state object scoped to the element. `x-on:click` listens for events (with modifiers like `.outside`, `.keydown.escape`), `x-text` and `x-html` bind content reactively, `x-show` toggles visibility, `x-model` two-way binds inputs, and `x-for` loops. It is essentially a declarative reactivity system with jQuery-scale ergonomics:

```html
<div x-data="{ open: false }">
  <button x-on:click="open = !open">Toggle</button>
  <div x-show="open" x-transition>
    Contents...
  </div>
</div>
```

Alpine shines for **UI islands**: dropdowns, modals, tabs, toasts, and infinite-scroll triggers — the 10% of a page that needs interactivity. The official plugin set (morph, persist, focus, intersect, mask, sort) extends it into a mini-framework: `x-persist` keeps state in localStorage, `x-intersect` triggers on scroll visibility, and `Alpine.store()` provides global state. Its weak spot is server-driven updates: Alpine cannot fetch and swap HTML fragments by itself, so dynamic data still needs fetch calls or a partner like htmx. The hero image from the official repository below captures the aesthetic — clean, minimal, markup-first:

![Alpine.js hero image](/img/screenshots/alpine-hero.jpg "Alpine.js - rugged minimal framework for composing JavaScript behavior in your markup")

## Unpoly — Progressive Enhancement, Perfected

Unpoly is the least famous and arguably the most mature of the three. Built by the German consultancy makandra to serve their Rails clients, it has a modest **2,769 stars** (last push August 8, 2026) but a fanatically consistent philosophy: **the server renders complete HTML, and JavaScript only makes navigation and forms faster**. Unpoly intercepts link clicks and form submissions, fetches the new page (or a fragment), and swaps the relevant parts — with the page still fully functional if JavaScript is disabled. That graceful degradation is the property none of the other two can match.

Installation follows the same no-build pattern:

```html
<script src="/assets/unpoly.js"></script>
```

The central attributes are `up-follow` (enhance a link) and `up-target` (where to render the response):

```html
<a href="/projects/42" up-follow up-target="main">Show project</a>

<form action="/projects" method="post" up-target="main">
  ...
</form>
```

Unpoly's standout feature is **`up-validate`**: on form input, it submits the form to the server in the background and re-renders *just the form* with fresh server-side validation errors — real-time inline validation with zero client-side validation logic:

```html
<form action="/signup" method="post" up-validate>
  <input name="email" type="email" placeholder="Email">
</form>
```

The framework also includes layered dialogs (`up-layer`), history/popstate management, and fragment caching, all with server-rendered responses. Where htmx is a toolkit and Alpine is a sprinkles library, Unpoly is a *framework* — it makes strong assumptions (full-page navigation model, server-rendered forms) and rewards you with the most consistent UX of the three. The trade-offs: a steeper attribute vocabulary (`up-*` has more surface area than `hx-*`), documentation oriented toward Rails, and a community small enough that Stack Overflow answers are thin. The logo from the official repository is understated, much like the project:

![Unpoly logo](/img/screenshots/unpoly-logo.svg "Unpoly - progressive enhancement for HTML")

## Pitfalls and Migration Notes

**htmx pitfalls.** (1) CSRF: because htmx sends partial-HTML requests, make sure your server middleware reads the token from headers or the swapped form — many htmx apps hit 403s on POST after enabling CSRF protection. (2) History: `hx-boost` and swaps need `hx-push-url` to keep back/forward sane; without it users get broken navigation state. (3) Swap modes: default `innerHTML` replaces children — use `outerHTML` or `hx-swap="morph"` (via the morph extension) when the target element itself must change; naive swaps break event listeners. (4) Do not return JSON from htmx endpoints — the whole model depends on HTML fragments; mixing JSON in is a common anti-pattern that leads to unreadable swap targets.

**Alpine.js pitfalls.** (1) CSP: inline expressions in `x-data` violate strict Content-Security-Policy without `unsafe-eval` — if you run a locked-down site, Alpine's CSP build or moving logic into `Alpine.data()` is required. (2) `x-show` vs `x-if`: `x-show` toggles display (element stays in DOM), `x-if` destroys/recreates the DOM node — using `x-if` in tight loops is slow. (3) Store initialization: `Alpine.store()` must be registered before Alpine starts, and reactive data inside stores needs plain objects, not class instances. (4) Nesting `x-data` components with the same property names shadow each other — name collisions are the most common debugging trap.

**Unpoly pitfalls.** (1) Because Unpoly rewrites navigation globally, third-party scripts that listen for full page loads (analytics, chat widgets) need the `up:event` hooks — remember to re-initialize them on fragment swaps. (2) `up-validate` requires the server to return the *same form markup* with errors; endpoints that redirect on validation failure break the flow. (3) The attribute vocabulary is large — budget real reading time before production use. (4) Most community answers assume Rails; on other stacks you will translate idioms yourself.

**Migration strategy.** All three coexist with existing server templates — there is no rewrite required to adopt them. The lowest-risk path: add Alpine to a server-rendered app for UI islands first, then introduce htmx for the most painful server round-trips, and only consider Unpoly if you want the full navigation model. Since none of the three touches your backend API, you can also run them alongside an existing SPA while you migrate page by page. If your templates live in a JVM stack, our [Java template engines guide](../2026-07-25-java-template-engines-thymeleaf-freemarker-jte-rocker/) shows the server side; for the Node.js perspective on server-rendered apps, see our [Express vs Koa vs Fastify vs Hono comparison](../2026-07-28-nodejs-http-frameworks-express-koa-fastify-hono-comparison/).

## Why the Server-Rendered Approach Wins in 2026

The SPA pendulum has swung far enough that even the biggest frameworks are rediscovering server rendering, and these three libraries are the pragmatic middle ground: interactive experiences without sacrificing the simplicity of HTML. htmx is the power tool for server-driven partial updates — the choice when your backend is the source of truth and you want real-time capabilities without a single line of WebSocket client code. Alpine is the ergonomic sprinkler for client-side behavior — the choice for UI islands and component-level state with a 15 KB footprint. Unpoly is the progressive-enhancement framework for teams that cannot afford to break older browsers or non-JS users — the choice for longevity over flash. If you are still managing global state with a full library, our [Redux vs Zustand vs Jotai comparison](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/) will look very different once your state lives in the DOM and the server. The common thread: less JavaScript shipped, less state to synchronize, and a page that still works when the network is slow — which, in 2026, is a competitive advantage, not a compromise.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "htmx vs Alpine.js vs Unpoly in 2026: Server-Rendered Interactivity Without the SPA",
  "description": "Compare htmx, Alpine.js, and Unpoly in 2026: real GitHub stats, official code examples, pitfalls, and a use-case decision matrix for server-rendered interactivity without SPAs.",
  "datePublished": "2026-08-10",
  "dateModified": "2026-08-10",
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

**Can I use htmx and Alpine.js together?**
Yes — this is the officially recommended pairing. htmx handles server-driven HTML swaps (`hx-get`, `hx-target`), and Alpine handles client-side state inside the swapped fragments (`x-data`, `x-show`). The two libraries are orthogonal and both are small enough to ship together comfortably.

**Does htmx require a backend framework?**
No — htmx is frontend-only. It sends standard HTTP requests and expects HTML fragments in response, so any server that renders HTML works: Django, Rails, Laravel, Spring, Express, or even a static site with serverless functions. Our [Node.js framework comparison](../2026-07-28-nodejs-http-frameworks-express-koa-fastify-hono-comparison/) covers the server side options.

**Is Alpine.js a replacement for React?**
For interactive *islands* in server-rendered pages, yes — but not for a full SPA. Alpine has no virtual DOM, no component tree beyond the DOM, and no server-side rendering story. If your app is a dense client-side application with complex state, React or a similar framework is still the right tool; if it is a website with interactive parts, Alpine is simpler and smaller.

**What does progressive enhancement mean for Unpoly?**
It means every enhanced link and form is a plain HTML link and form first. If JavaScript fails or is disabled, Unpoly pages still navigate and submit normally — just without the fast fragment swap. Neither htmx (swaps fail) nor Alpine (behavior absent) degrades this gracefully.

**Which is best for real-time dashboards?**
htmx, using the SSE extension (`hx-sse`) or WebSocket support, or simple polling via `hx-trigger="every 5s"`. Alpine has no native real-time story, and Unpoly's navigation model is not designed for it.

**Do these libraries work with server-side validation?**
Yes — this is one of their biggest advantages over SPAs. htmx swaps in the server-rendered error fragment, Unpoly's `up-validate` re-renders the form with server errors on every input, and Alpine can call any validation endpoint via fetch. Validation logic lives in one place: the server.

**How large are the bundle sizes?**
htmx is roughly 14 KB (minified+gzipped), Alpine about 15 KB, and Unpoly around 30 KB. All three ship as plain script tags with no build step, which is the entire point — there is no toolchain to maintain.

**Which should a Rails or Django team choose?**
Both ecosystems have strong examples of all three, but the conventional wisdom: Django teams gravitate to htmx (or Alpine + htmx), while Rails teams — especially those following the Hotwire-adjacent philosophy — find Unpoly's form handling and progressive enhancement model closest to their existing conventions.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
