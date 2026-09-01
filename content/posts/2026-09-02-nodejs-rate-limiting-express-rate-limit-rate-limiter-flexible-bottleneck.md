---
title: "Node.js Rate Limiting in 2026: express-rate-limit vs rate-limiter-flexible vs bottleneck"
date: "2026-09-02"
tags: ["nodejs", "rate-limiting", "express", "libraries", "developer-tools"]
draft: false
---

Rate limiting is the difference between a Node.js API that survives a viral post and one that melts. Yet most Express apps ship with no limiter at all — or with one that resets on every restart, shares a single bucket across all users behind a proxy, or throttles the wrong direction entirely. In 2026 the three tools you will actually encounter are **express-rate-limit** (the Express middleware), **rate-limiter-flexible** (the framework-agnostic distributed limiter), and **bottleneck** (the client-side job scheduler). They are not interchangeable — each solves a different layer of the problem.

## TL;DR: Quick Verdict

If you run an **Express (or plain HTTP) API and want per-IP protection in five minutes**, use express-rate-limit — it is the drop-in default, with validation and store plug-ins. If you need **limits that survive restarts and span multiple instances — Redis, Postgres, or in-memory with atomic counters — or per-user keys with penalties and blocks**, use rate-limiter-flexible. If your problem is **outbound**: your service hammering a third-party API with rate limits of its own, use bottleneck. Protect the inbound path with the first two; throttle the outbound path with the third. Mixing them is normal and correct.

## Head-to-Head Comparison

| Dimension | express-rate-limit | rate-limiter-flexible | bottleneck |
|---|---|---|---|
| Primary role | Express middleware (inbound) | Framework-agnostic limiter (inbound, distributed) | Client-side job scheduler / throttler (outbound) |
| Storage backends | In-memory (default), Redis, Memcached, others | Memory, Redis, Memcached, MongoDB, Postgres, MySQL, Cluster | In-memory only |
| Distributed / multi-instance | With external store | Yes, atomic via store | No (per-process; cluster option for workers) |
| API style | Middleware `app.use(limiter)` | `consume` / `penalize` / `block` promise API | `schedule(fn)` with `maxConcurrent` / `minTime` |
| Per-user / per-key limits | Via `keyGenerator` | First-class (`consume(key)`) | Via separate limiter instances |
| Response headers | `RateLimit` (draft-6/7/8) + legacy `X-RateLimit-*` | Manual (`RateLimiterRes` fields) | N/A (client side) |
| Works in the browser | No | No | Yes |
| License | MIT | MIT | MIT |
| GitHub stars (2026-09) | 3,289 | 3,582 | 2,004 |
| Last push | 2026-08-31 | 2026-06-08 | 2024-01-23 |

## Use Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Protect a public Express API from floods | express-rate-limit | One middleware, sensible defaults, per-IP out of the box |
| Limits shared across multiple server instances | rate-limiter-flexible | Redis/Postgres/Mongo stores with atomic operations |
| Per-user quotas (auth tokens, free tiers) | rate-limiter-flexible | `consume(userId)` with penalties and blocks |
| Throttle outbound calls to a third-party API | bottleneck | `maxConcurrent` + `minTime` schedules requests smoothly |
| Fastify/Koa/plain `http` server | rate-limiter-flexible | Framework-agnostic; works anywhere |
| Web app calling your own API from the browser | bottleneck | Runs client-side, supports clustering and reservoir bursts |

## express-rate-limit: The Five-Minute Express Default

express-rate-limit (3,289 stars, actively maintained — last push August 2026) is the most common way Node.js APIs get protected, and for good reason: it is a middleware that works with sensible defaults and validates its own configuration. The official README example is the entire quick start:

```ts
import { rateLimit } from 'express-rate-limit'

const limiter = rateLimit({
	windowMs: 15 * 60 * 1000, // 15 minutes
	limit: 100, // Limit each IP to 100 requests per `window` (here, per 15 minutes).
	standardHeaders: 'draft-8', // draft-6: `RateLimit-*` headers; draft-7 & draft-8: combined `RateLimit` header
	legacyHeaders: false, // Disable the `X-RateLimit-*` headers.
	ipv6Subnet: 56, // Set to 60 or 64 to be less aggressive, or 52 or 48 to be more aggressive
	// store: ... , // Redis, Memcached, etc. See below.
})

// Apply the rate limiting middleware to all requests.
app.use(limiter)
```

The details that matter in production: `ipv6Subnet` handles the IPv6 prefix problem (without it, a /64 of addresses counts as one IP or many, depending on how you aggregate), `keyGenerator` lets you switch from per-IP to per-user, and the built-in memory store can be swapped for Redis or Memcached via the `store` option so limits survive restarts. Its scope is deliberately narrow: it guards inbound requests to Express. It will not help you throttle requests your server makes to anyone else. If you are still choosing your HTTP framework, our [Express vs Koa vs Fastify vs Hono comparison](../2026-07-28-nodejs-http-frameworks-express-koa-fastify-hono-comparison/) covers how each framework shapes middleware like this one.

## rate-limiter-flexible: Distributed Limits Without a Framework

rate-limiter-flexible (3,582 stars, updated June 2026) is the power tool: a framework-agnostic limiter built on atomic counters, with storage backends for Redis, Memcached, MongoDB, Postgres, MySQL, and in-process memory. The core concept is points per duration, consumed per key. The README's basic example:

```javascript
const opts = {
  points: 6, // 6 points
  duration: 1, // Per second
};

const rateLimiter = new RateLimiterMemory(opts);

rateLimiter.consume(remoteAddress, 2) // consume 2 points
    .then((rateLimiterRes) => {
      // 2 points consumed
    })
    .catch((rateLimiterRes) => {
      // Not enough points to consume
    });
```

For a multi-instance deployment the same API with a Redis store gives you atomic, cross-process limits — no `setTimeout` approximations, no race windows:

```javascript
import { RateLimiterRedis } from 'rate-limiter-flexible';
import redis from 'redis';

const redisClient = redis.createClient({ url: 'redis://localhost:6379' });
await redisClient.connect();

const rateLimiter = new RateLimiterRedis({
  storeClient: redisClient,
  points: 100,
  duration: 60,
});
```

The resolved or rejected `RateLimiterRes` object carries `remainingPoints` and `msBeforeNext`, so you can emit accurate `Retry-After` headers. `penalize()` and `block()` extend the state machine for abusive clients, and `RateLimiterQueue` adapts the same counters into a throttling queue for outbound work. This is the tool that grows with you: start with `RateLimiterMemory`, move to Redis when you scale out, keep the same `consume(key)` call sites.

## bottleneck: Smooth Outbound Throttling

bottleneck (2,004 stars, last push January 2024 — stable and finished) solves the opposite problem. It is a "job scheduler and rate limiter" that runs client-side: you hand it a function and it executes it at a controlled rate, queueing work instead of rejecting it. This is exactly what you want when calling APIs with their own rate limits. The README's core pattern:

```js
const limiter = new Bottleneck({
  maxConcurrent: 1,
  minTime: 333
});

limiter.schedule(() => myFunction(arg1, arg2))
.then((result) => {
  /* handle result */
});
```

`maxConcurrent: 1, minTime: 333` means "at most 3 requests per second, one at a time" — the classic 3 req/s API quota. Beyond that, bottleneck supports priority queues, weighted jobs, clustering across worker threads, and **reservoir intervals** for quota-based APIs that reset hourly or daily. Because it is pure JavaScript with no Node-specific dependencies, it also runs in the browser — useful when your frontend needs to pace requests to your own backend. Its last release was over two years ago, but the API is complete and it remains the standard answer for outbound throttling in the Node ecosystem.

## Pitfalls: Six Ways Node.js Rate Limiting Goes Wrong

1. **Behind a reverse proxy, everyone shares one IP.** Express sees the proxy's address unless you call `app.set('trust proxy', 1)` (or a more specific value). Without it, express-rate-limit buckets your entire user base into a single counter. With it, make sure your proxy actually sets `X-Forwarded-For` correctly.
2. **The default memory store resets on restart.** Every deploy empties the buckets — a scripted attacker can simply wait for your rolling deployment to reset limits. Use a Redis/Memcached store for anything that matters.
3. **In-memory limiters do not work across instances.** Two replicas, each with `RateLimiterMemory`, allow 2x the intended traffic. rate-limiter-flexible with Redis is the fix; there is no shortcut.
4. **Using bottleneck to protect your server is backwards.** bottleneck queues and waits — it never rejects. An attacker would just build a longer queue, and you'd burn memory. Inbound protection needs a rejecting limiter (express-rate-limit or rate-limiter-flexible); bottleneck is for the requests *you* make.
5. **Unbounded `keyGenerator` keys leak memory.** If you limit per-user with ever-growing user IDs and never clean up, every limiter map grows forever. Prefer fixed-cardinality keys (IP, tier, route), or use a store with its own expiry.
6. **Header drafts change under you.** `standardHeaders: 'draft-8'` emits the combined `RateLimit` header; older drafts emit separate `RateLimit-*` headers; `legacyHeaders` toggles `X-RateLimit-*`. Pick one and be consistent — monitoring systems that parse these headers will silently misreport otherwise.

The same architectural decisions repeat across ecosystems. The [Java rate limiter libraries guide](../2026-06-19-rate-limiter-libraries-bucket4j-resilience4j-governor-guava/) and the [Python rate limiting comparison](../2026-07-02-python-rate-limiting-limits-slowapi-flask-limiter-django-ratelimit/) cover Bucket4j, Resilience4j, Flask-Limiter and friends, and the [gateway-level rate limiting guide](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide-2026/) explains when to push limits down to nginx or Envoy instead of the app. For related queueing patterns, our [Node.js job queue comparison](../2026-07-24-nodejs-job-queue-libraries-bullmq-beequeue-pgboss/) shows how BullMQ and friends handle the scheduling side of the same problem.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js Rate Limiting in 2026: express-rate-limit vs rate-limiter-flexible vs bottleneck",
  "description": "Deep comparison of the three Node.js rate limiting tools: express-rate-limit (Express middleware), rate-limiter-flexible (distributed, framework-agnostic), and bottleneck (outbound job throttling). Real code, live stats, and a decision matrix.",
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

## FAQ

### Which Node.js rate limiter is best for Express?

For a plain Express API, express-rate-limit is the default choice: it is middleware, so it drops into `app.use()` with one call, and it ships with per-IP limits, IPv6 handling, and store plug-ins. If you need per-user quotas or distributed stores, pair it with — or replace it by — rate-limiter-flexible, which works with Express too.

### Can these rate limiters work across multiple server instances?

express-rate-limit and bottleneck are per-process by default. rate-limiter-flexible is the distributed option: its Redis, Postgres, MongoDB, and MySQL backends perform atomic counter operations, so N instances share one limit without race conditions.

### What is the difference between middleware rate limiting and client-side throttling?

Middleware rate limiting protects your server by rejecting excess inbound requests (returning 429). Client-side throttling paces requests your application sends to another API, queueing them so you stay under the remote quota. They are complementary: you rate-limit inbound with express-rate-limit or rate-limiter-flexible, and throttle outbound with bottleneck.

### Do I need Redis for rate-limiter-flexible?

No. `RateLimiterMemory` works in a single process with the same API. Move to `RateLimiterRedis` (or another store) only when you scale to multiple instances or need limits to survive restarts — the call sites stay identical.

### How do I rate-limit per user instead of per IP?

express-rate-limit: set a `keyGenerator` that returns the user ID (with a fallback for anonymous traffic). rate-limiter-flexible: `consume(userId)` directly. In both cases prefer fixed-cardinality keys and be careful with memory growth for unbounded user populations.

### Is bottleneck still maintained?

bottleneck's last release was January 2024, and the project is best described as stable and complete rather than actively developed. It remains the standard tool for outbound throttling — the API is small, well-tested, and has not needed changes. For the same job with newer maintenance, rate-limiter-flexible's `RateLimiterQueue` is a reasonable alternative.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
