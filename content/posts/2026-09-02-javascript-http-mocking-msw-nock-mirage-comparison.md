---
title: "JavaScript HTTP Mocking in 2026: MSW vs Nock vs Mirage JS — Which API Mocking Library Should You Use?"
date: "2026-09-02"
tags: ["javascript", "testing", "mocking", "msw", "nock", "miragejs", "developer-tools"]
draft: false
cover: "/img/screenshots/msw-dashboard.jpg"
---

Every frontend team hits the same wall: your components, hooks and end-to-end flows depend on APIs that are slow, flaky, rate-limited or not even built yet. Stubbing fetch manually works for two endpoints and collapses at fifty. That is why HTTP mocking libraries exist — and in 2026 the JavaScript ecosystem has three serious contenders: **MSW** (Mock Service Worker), **Nock**, and **Mirage JS**. They look interchangeable at a glance, but they intercept requests at completely different layers of the stack, which means the choice determines everything from whether your mocks work in the browser to whether they survive a refactor from fetch to axios.

**TL;DR:** Pick **MSW** for anything that runs in a browser or mixes browser + Node tests — it mocks at the network level via a real Service Worker, so your code, your HTTP client and your devtools all see genuine network traffic. Pick **Nock** if you only test Node.js server code or CLI tools and want the fastest, most battle-tested interceptor with zero browser baggage. Pick **Mirage JS** if you want an in-memory fake API server with models, factories and relationships for rapid UI prototyping — but be aware its browser approach is an XHR/fetch shim, not a network-level mock. For new component and integration test suites in 2026, MSW is the default answer; Nock remains the champion for pure backend tests.

## Quick Comparison: MSW vs Nock vs Mirage JS

| Dimension | MSW | Nock | Mirage JS |
|---|---|---|---|
| GitHub stars | **18,180** | 13,122 | 5,529 |
| Last push (checked 2026-09-02) | 2026-07-24 | **2026-08-05** | 2025-08-11 |
| License | MIT | MIT | MIT |
| Interception layer | **Service Worker (browser) / HTTP interceptor (Node)** | Node `http`/`https` module patch | XHR/fetch shim + Pretender |
| Works in browser | ✅ native SW | ❌ Node only | ✅ via shim |
| Works in Node | ✅ (node interceptor) | ✅ | ⚠️ via jsdom XHR |
| Request matching | Path, method, headers, body | Path, method, headers, body, query | Routes + serializers |
| Response mocking | `HttpResponse` factory | `.reply()` chains | Factories + serializers |
| Models/factories/relationships | ❌ (bring your own) | ❌ | ✅ built-in |
| Delay/network error simulation | ✅ | ✅ | ✅ (timing) |
| Record & replay real traffic | ⚠️ via third-party | ✅ (`.log()` + recorder) | ❌ |
| Devtools network tab visibility | ✅ shows real requests | ❌ (patched layer) | ⚠️ partial |
| Test runner support | Vitest, Jest, Playwright, Storybook, Cypress | Mocha, Jest, Vitest, tap | Jest, QUnit, Cypress |
| TypeScript types | First-party, excellent | @types/nock | First-party |

## Decision Matrix: Pick Your Mocking Tool in 10 Seconds

| Use Case | Recommended | Why |
|---|---|---|
| React/Vue component tests with Vitest or Jest | **MSW** | Network-level mocks via Node interceptor; same handler code works in Storybook and Playwright |
| Browser dev + tests share the same mocks | **MSW** | Service Worker approach means dev mode and test mode run identical handlers |
| Pure backend/CLI Node.js unit tests | **Nock** | Minimal overhead, precise matching, no browser concepts involved |
| Prototyping UI against a fake data API with relations | **Mirage JS** | Models + factories + serializers give you a real fake backend in minutes |
| End-to-end tests with Playwright/Cypress | **MSW** | Intercept at network level so the browser app cannot tell mocks from real API |
| Testing axios/fetch timeouts, retries, 5xx storms | **Nock** | `.replyWithError()`, delays and sequence replies are first-class |
| You already use [WireMock/MockServer as a shared service](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mockserver-guide-2026/) | Keep it, add MSW locally | Shared mock servers stay for integration envs; MSW covers per-test isolation |

## MSW — Mock at the Network Level, in Any Environment

MSW's insight is elegant: instead of patching `fetch` or `XMLHttpRequest`, it registers a **Service Worker** in the browser that intercepts real network requests and returns crafted responses. Your application code, your HTTP client, your browser devtools Network tab and your error handling all see completely normal traffic — because from the page's perspective it *is* normal traffic, just answered locally.

The same handlers run in Node.js via the `setupServer` interceptor, which makes MSW the rare tool that unifies browser and unit-test mocking behind one API:

```js
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

const server = setupServer(
  http.get('https://api.example.com/users/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Ada Lovelace',
      role: 'admin',
    })
  }),

  http.post('https://api.example.com/users', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...body, id: 'usr_42' }, { status: 201 })
  }),
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

Error scenarios are just handlers too — no mocking-library-specific error syntax:

```js
http.get('https://api.example.com/status', () => {
  return HttpResponse.json({ message: 'Service unavailable' }, { status: 503 })
})
```

MSW is also the mocking layer used by Storybook's built-in mocking and by Playwright recipes, so handler code you write for Vitest can be reused verbatim in component stories and e2e tests. The trade-offs: you must run the Service Worker registration in browser contexts (`worker.start()` with the `mockServiceWorker.js` file served statically), and response latency simulation is manual rather than turnkey. Its growth (18k+ stars, releases through July 2026) makes it the safest long-term bet.

## Nock — The Node-Native Workhorse

Nock predates the modern test stack by years and remains the most precise HTTP interceptor for Node.js. It patches the `http` and `https` modules themselves, so anything built on them — axios, got, node-fetch, the AWS SDK — is intercepted without touching your application code. For server-side tests this is a feature: no Service Worker, no DOM, no browser concepts.

```js
const nock = require('nock')

nock('https://api.stripe.com')
  .get('/v1/customers/cus_123')
  .reply(200, { id: 'cus_123', email: 'ada@example.com' })

// Sequence replies: first call 500, then 200
nock('https://api.example.com')
  .post('/webhooks')
  .times(2)
  .reply(500, { error: 'boom' })
  .post('/webhooks')
  .reply(200, { ok: true })

// Simulate connection failure to test retry logic
nock('https://api.example.com')
  .get('/flaky')
  .replyWithError({ code: 'ECONNRESET', message: 'socket hang up' })
```

Nock's matcher is strict and explicit — query strings, headers and request bodies can all be pinned, which makes tests precise and, occasionally, brittle. It also ships a recorder (`nock.recorder.rec()`) that captures real traffic into reusable fixtures — genuinely useful for building regression suites against a staging environment.

```js
nock.recorder.rec({ output_objects: true, dont_print: true })
// ... run your code against the real API ...
const fixtures = nock.recorder.play()
```

Limitations: browser tests are out of scope by design, and because Nock patches the socket layer, it cannot simulate what a browser network stack would do (Service Worker caching, redirects, CORS preflight). Its active maintenance (August 2026 push, 13k stars) and zero-dependency philosophy keep it the right answer for backend and CLI testing.

## Mirage JS — A Fake API Server for UI Development

Mirage JS takes yet another approach: it runs an **in-memory API server inside your app** with a database layer, models, factories, serializers and route handlers — closer to a fake backend than a request interceptor. It was designed around Ember's ecosystem and later generalized to React and Vue.

```js
import { createServer, Model, Factory } from 'miragejs'

createServer({
  models: {
    user: Model,
    post: Model,
  },

  factories: {
    user: Factory.extend({
      name(i) { return `User ${i}` },
      admin: false,
    }),
  },

  routes() {
    this.namespace = 'api'
    this.get('/users', (schema) => schema.all('user'))
    this.get('/users/:id', (schema, request) => schema.find('user', request.params.id))
    this.post('/users', (schema, request) => {
      const attrs = JSON.parse(request.requestBody)
      return schema.create('user', attrs)
    })
  },

  seeds(server) {
    server.createList('user', 25)
  },
})
```

The killer feature is **relationships and serializers**: `schema.find('post', id).user` resolves nested resources the way a real REST API would, and serializers shape payloads (including JSON:API) without hand-writing responses. For rapid UI prototyping — "give me a fake users list with 25 records, pagination and a detail view" — Mirage is still the fastest tool in this comparison.

The caveats matter in 2026: Mirage intercepts via an XHR/fetch shim (Pretender), so it does not play perfectly with native `fetch` streams, and the project's release cadence has slowed (last push August 2025). It remains excellent for throwaway prototypes and Storybook-style demos, but teams standardizing on one mocking strategy for both unit and e2e tests increasingly pick MSW.

## Pitfalls and Migration Notes

1. **Mocking layer must match your runtime.** Nock cannot intercept browser requests; MSW's Service Worker does nothing in plain Node without `setupServer`; Mirage needs a DOM-ish environment. Pick by where your code actually runs, not by team familiarity.
2. **fetch streams break naive interceptors.** Mirage's XHR shim and older fetch patches struggle with `request.body` streams. MSW's `request.json()` and Nock's body matchers handle modern usage cleanly.
3. **One interceptor per test process.** Mixing Nock and MSW in the same suite causes double interception or "no match" errors. Standardize per test file or per project.
4. **Never let mocks leak into production builds.** MSW's `worker.start()` should be gated by an env flag; a misconfigured build ships a mock API to real users. Use `import.meta.env.DEV` or `NODE_ENV` checks.
5. **Reset state between tests.** Nock persists mocks until removed (`nock.cleanAll()`), MSW accumulates handlers (`server.resetHandlers()`), Mirage keeps its database. Forgetting teardown is the #1 source of order-dependent test failures.
6. **Record-then-edit beats hand-writing for legacy APIs.** If you are adding tests to an existing codebase with a sprawling API, record real traffic first (Nock recorder or MSW's third-party recording tools), then trim and harden the fixtures — hand-writing hundreds of handlers is where teams give up.
7. **Mock the contract, not the implementation.** Match on URL/method/status, not on "whatever axios sends." Tests that assert on axios internals break the day you migrate to fetch — our [HTTP client ecosystem guide](../2026-08-28-nodejs-vs-bun-vs-deno-javascript-runtimes-comparison/) shows how much churn that ecosystem has had.

## Why Bother Mocking HTTP at the Network Level?

The alternative — mocking your HTTP client module with a generic stubbing library — couples every test to the client's API surface. Upgrade axios, and hundreds of tests silently change meaning. Network-level mocking inverts that: your code under test executes exactly as it does in production, issuing real requests that are answered at the transport boundary. Tests then survive client migrations, which matters in an ecosystem where teams rotate between fetch, axios and undici as quickly as they rotate frameworks. If you are evaluating test runners to pair with your mocking choice, our [JavaScript testing frameworks guide](../2026-07-21-javascript-testing-frameworks-vitest-jest-playwright/) compares Vitest, Jest and Playwright, and the [cross-language unit mocking comparison](../2026-06-20-unit-test-mocking-libraries-mockito-sinonjs-gomock-testdoublejs/) shows where HTTP mocking ends and plain spies/stubs begin.

## FAQ

### What is the difference between MSW and Nock?
MSW intercepts at the Service Worker level in browsers and via a dedicated interceptor in Node, so browser tests see genuine network traffic; Nock patches Node's `http`/`https` modules directly and only works in Node.js. For browser component tests choose MSW; for pure Node.js backend tests either works, with Nock being lighter-weight.

### Can MSW mock axios requests?
Yes. MSW intercepts at the network layer, below axios, so axios, fetch, got and the browser's native fetch all pass through the same handlers. You never mock axios itself.

### Is Mirage JS still maintained?
The project is in slow-maintenance mode — its last push was August 2025 — but it remains stable and is still the fastest way to stand up a fake data API with models, factories and serializers for UI prototyping. For long-lived test infrastructure, MSW is the safer investment.

### Does Nock work with Vitest?
Yes. Nock works with any Node.js test runner, including Vitest, Jest, Mocha and node:test. Remember to call `nock.cleanAll()` and `nock.enableNetConnect()` in teardown to avoid mocks leaking between test files.

### Do these libraries support TypeScript?
MSW ships first-party types for its handler and response APIs; Nock relies on the community `@types/nock` package; Mirage JS includes first-party types but some serializer/relationship edge cases require `any` assertions.

### Can I use MSW in production builds by accident?
Only if you explicitly import and start the worker. Guard `worker.start()` behind an environment check (for example `if (import.meta.env.DEV)`), and verify your bundler strips test-only imports in production builds.

### Which tool should I use for Playwright e2e tests?
MSW, via its Node interceptor configured in Playwright's webServer or as a route fallback — it lets the browser app run against consistent mock data while keeping the network layer intact. Mirage and Nock are not designed for that workflow.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript HTTP Mocking in 2026: MSW vs Nock vs Mirage JS — Which API Mocking Library Should You Use?",
  "description": "Compare MSW, Nock and Mirage JS for JavaScript API mocking: interception layers, browser vs Node support, code examples, decision matrix and migration pitfalls for 2026.",
  "datePublished": "2026-09-02",
  "dateModified": "2026-09-02",
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
