---
title: "opossum vs cockatiel vs p-retry in 2026: Stop Letting One Slow Upstream Take Down Your Node.js API"
date: "2026-11-06"
tags: ["nodejs", "reliability", "circuit-breaker", "javascript", "backend"]
draft: false
---

One upstream provider goes from 80 ms to 30 seconds. Your Node.js service keeps accepting requests, keeps opening new sockets to it, and burns its entire connection pool in ninety seconds. Now every endpoint that touches that provider is slow — including the health check your load balancer uses. One degraded dependency became a total outage, and no amount of horizontal scaling helps, because you are simply launching more processes that will also block.

This is the failure mode that retries, timeouts and circuit breakers exist to prevent. In Node.js, three libraries cover the space and they overlap just enough to confuse everyone: **opossum** (circuit breaker), **cockatiel** (full policy toolkit) and **p-retry** (retry only). Choosing the wrong one is usually not a bug — it is a slow-motion outage waiting for its first bad Tuesday.

## TL;DR — the 30-second verdict

- **You want one thing and one thing only: retries with backoff.** Use **p-retry**. It is 1,041 stars of focused, well-tested behavior with an `AbortError` escape hatch.
- **You need circuit breaking plus timeouts plus fallbacks, in one coherent API.** Use **cockatiel** or **opossum**. cockatiel gives you composable policies (retry + breaker + timeout + bulkhead); opossum gives you the most battle-tested single-purpose breaker in the ecosystem.
- **My recommendation for new services:** **cockatiel** for anything with more than one failure mode, **p-retry** for scripts and workers, and **opossum** when a team already runs it and the breaker is the only pattern needed.
- **A retry without a timeout is a load amplifier**, not a resilience mechanism. Fix the timeout first.

## Side-by-side comparison (GitHub data pulled 2026-11-06)

| | **opossum** | **cockatiel** | **p-retry** |
|---|---|---|---|
| GitHub stars | **1,695** | **1,833** | **1,041** |
| Last push | 2026-08-21 | 2026-10-29 | 2026-11-02 |
| License | Apache-2.0 | MIT | MIT |
| Core abstraction | `CircuitBreaker` wrapping a function | Composable **policies** | Retry wrapper for async functions |
| Circuit breaker | Yes (primary feature) | Yes (`ConsecutiveBreaker`, `SamplingBreaker`) | No |
| Retry | No (manual) | Yes, with pluggable backoffs | Yes (primary feature) |
| Timeout | Yes (per-call, triggers failure) | Yes (`timeout()` policy) | No |
| Bulkhead isolation | No | Yes (`bulkhead()`) | No |
| Fallback | Yes (`fallback` option) | Yes (`fallback()` policy) | No |
| Events / metrics | Rich event emitter (`success`, `timeout`, `open`, `halfOpen`, `failure`) | Events (`onRetry`, `onSuccess`, `onFailure`, `onGiveUp`) | Minimal |
| TypeScript | Types via DefinitelyTyped | **Written in TypeScript** | Written in TypeScript |
| Runtime requirement | Node.js **>= 22** | Node.js (modern LTS) | Node.js (modern LTS) |
| Best fit | Existing breaker-centric codebases | Greenfield services with several failure modes | Workers, scripts, single-call retries |

## Decision matrix: pick in ten seconds

| Your situation | Pick | Why |
|---|---|---|
| Calling a flaky third-party API from an HTTP handler | **cockatiel** | Retry + breaker + timeout composed in one policy |
| Only need "try 5 times with backoff" | **p-retry** | Zero ceremony, `AbortError` stops pointless retries |
| Legacy service already using opossum | **opossum** | Do not migrate for its own sake; add timeouts |
| Protecting a database from a thundering herd | **opossum** or **cockatiel** breaker | Fails fast when the dependency is clearly down |
| Limiting concurrency to a slow upstream | **cockatiel** (`bulkhead`) | Neither of the others does concurrency limits |
| Cron job or queue worker hitting an unstable endpoint | **p-retry** | Simplest correct tool; no state to maintain |

## opossum: the breaker that made the pattern mainstream

opossum is 1,695 stars, Apache-2.0, last pushed 2026-08-21, and it requires **Node.js 22 or newer** — check that before you adopt it. Its model is a single wrapper: you hand it an async function, it decides whether to call it.

From the official README:

```javascript
const CircuitBreaker = require('opossum');

function asyncFunctionThatCouldFail(x, y) {
  return new Promise((resolve, reject) => {
    // Do something, maybe on the network or a disk
  });
}

const options = {
  timeout: 3000,                  // >3s counts as a failure
  errorThresholdPercentage: 50,   // 50% failures trips the circuit
  resetTimeout: 30000,            // try again after 30s
};

const breaker = new CircuitBreaker(asyncFunctionThatCouldFail, options);

breaker.fire(x, y)
  .then(console.log)
  .catch(console.error);
```

What makes opossum genuinely useful in production is the event surface and the fallback path. You can wire the breaker into your metrics without touching the call site:

```javascript
const breaker = new CircuitBreaker(callPaymentProvider, {
  timeout: 2500,
  errorThresholdPercentage: 40,
  resetTimeout: 20000,
  volumeThreshold: 10,           // do not trip on 1 failure out of 2 calls
  fallback: () => ({ queued: true, reason: "provider_unavailable" }),
});

breaker.on("open",     () => metrics.increment("payments.breaker.open"));
breaker.on("halfOpen", () => metrics.increment("payments.breaker.half_open"));
breaker.on("timeout",  () => metrics.increment("payments.breaker.timeout"));
breaker.on("fallback", () => metrics.increment("payments.breaker.fallback"));

const result = await breaker.fire(order);
```

Two details that are easy to get wrong: `volumeThreshold` defaults mean a breaker can trip on a tiny sample in low-traffic services (set it explicitly), and the `fallback` return value is indistinguishable from success at the call site — log it, or you will ship silent data loss.

The `timeout` option is also doing double duty as a cancellation signal through `AbortController` support. That matters: without it, the underlying socket keeps working after you have given up on the answer, and your "fast fail" still consumes connections.

## cockatiel: policies you can compose

cockatiel has 1,833 stars, an MIT license, a push on 2026-10-29, and it is written in TypeScript. Instead of one wrapper, it gives you policy objects that you can nest — retry inside breaker inside timeout, in an order you control. The project's own README example shows the composition directly:

```typescript
import {
  retry, circuitBreaker, handleAll, wrap,
  ExponentialBackoff, ConsecutiveBreaker,
} from 'cockatiel';

// Retry 3 times with exponential backoff
const retryPolicy = retry(handleAll, {
  maxAttempts: 3,
  backoff: new ExponentialBackoff(),
});

// Stop calling for 10s if it fails 5 times in a row
const circuitBreakerPolicy = circuitBreaker(handleAll, {
  halfOpenAfter: 10 * 1000,
  breaker: new ConsecutiveBreaker(5),
});

// Retry 3 times, each attempt going through the breaker
const retryWithBreaker = wrap(retryPolicy, circuitBreakerPolicy);

export const handleRequest = async (req, res) => {
  const data = await retryWithBreaker.execute(() => callUpstream(req.body));
  res.json(data);
};
```

The policy ordering is the whole point, and it is where teams get it wrong. `wrap(retryPolicy, circuitBreakerPolicy)` means **each retry passes through the breaker**, so the breaker sees individual attempts. If you inverted it, the breaker would see one logical operation made of three attempts, and it would take three times as long to trip — usually not what you want.

Add a timeout and a bulkhead and you have protected the whole failure surface:

```typescript
import { timeout, BulkheadRejectionError, bulkhead } from 'cockatiel';

const timeoutPolicy = timeout(4000, AbortSignal.timeout);  // per-attempt ceiling
const bulkheadPolicy = bulkhead(20, 50);                   // 20 concurrent, 50 queued

const safeUpstream = wrap(
  bulkheadPolicy,
  circuitBreakerPolicy,
  timeoutPolicy,
  retryPolicy,
);

try {
  await safeUpstream.execute(() => fetchQuote(id));
} catch (err) {
  if (err instanceof BulkheadRejectionError) {
    return res.status(429).json({ error: "too_many_requests" });
  }
  throw err;
}
```

That is four distinct resilience patterns in about ten lines. For a service with a database, two third-party APIs and an internal RPC, that compactness is worth the extra API surface — and the TypeScript types keep the policy composition honest at compile time.

The cost: cockatiel is a policy engine, so debugging requires understanding ordering and predicate semantics. `handleAll` catches everything including your own programming errors, which will retry a `TypeError` three times before failing. Use narrower predicates (`handleType(NetworkError)`, `handleWhen(...)`) in anything user-facing.

## p-retry: retries, done properly, and nothing else

p-retry is 1,041 stars, MIT, pushed 2026-11-02, and it retries exactly what you give it. The `AbortError` is the feature that makes it safe in practice — it distinguishes "this will never succeed" from "this might succeed later":

```javascript
import pRetry, { AbortError } from 'p-retry';

const run = async () => {
  const response = await fetch('https://sindresorhus.com/unicorn');

  // Abort retrying if the resource doesn't exist
  if (response.status === 404) {
    throw new AbortError(response.statusText);
  }

  return response.blob();
};

console.log(await pRetry(run, { retries: 5 }));
```

Retrying a 404 is not resilience, it is noise. Retrying a 500, a socket hang-up or a 429 with `Retry-After` is resilience. The most common real-world elaboration is honoring the server's own backoff hint:

```javascript
import pRetry, { AbortError } from 'p-retry';

const fetchWithRetry = (url) => pRetry(
  async () => {
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });

    if (res.status === 429) {
      const retryAfter = Number(res.headers.get('retry-after') ?? 1);
      throw new Error(`rate limited, retry after ${retryAfter}s`);
    }
    if (res.status >= 400 && res.status < 500) {
      throw new AbortError(`client error ${res.status}`);
    }
    if (!res.ok) throw new Error(`server error ${res.status}`);

    return res.json();
  },
  {
    retries: 4,
    factor: 2,          // exponential
    minTimeout: 300,
    maxTimeout: 8000,
    randomize: true,    // jitter — essential with many clients
    onFailedAttempt: (err) => {
      log.warn({ attempt: err.attemptNumber, left: err.retriesLeft }, err.message);
    },
  },
);
```

`randomize: true` deserves emphasis. Without jitter, 200 workers that fail at the same moment retry at the same moment, and you have built a synchronized load generator pointed at a service that is already struggling.

p-retry has no breaker and no timeout of its own. That is fine — `AbortSignal.timeout()` handles the timeout, and if you need a breaker you need cockatiel or opossum. Layering p-retry on top of a broken dependency without a breaker is the classic anti-pattern: retries multiply load exactly when the dependency can least afford it.

## Throughput and blast radius: the math that decides your architecture

| Pattern | Effect during an outage | Cost when healthy |
|---|---|---|
| No timeout, no retry | Requests pile up until the process dies | None |
| Timeout only | Fails fast, user sees an error | Negligible |
| Timeout + retry | **Multiplies load** by attempt count | Extra calls on transient failures |
| Timeout + retry + jitter | Multiplies load, but spread over time | Negligible |
| Timeout + retry + breaker | Load drops to zero once tripped | Small state machine overhead |
| Above + bulkhead | Bounded concurrency per dependency | Queueing latency at saturation |

Three retries against a dependency already at capacity means **three times the traffic** from the same user base. A breaker exists to convert that multiplier back to zero. That is why the pattern ordering matters more than the library choice: timeout, then breaker, then retry through the breaker, then bulkhead around everything.

If you have implemented these patterns in other runtimes, the semantics are identical — see the [Java, Go and .NET circuit breaker comparison](../2026-06-21-circuit-breaker-libraries-resilience4j-hystrix-failsafe-go-polly/) and the [retry and backoff library comparison](../2026-06-21-retry-backoff-libraries-tenacity-polly-spring-retry-retry-go/). Rate limiting is the natural companion: our [Node.js rate limiting comparison](../2026-09-02-nodejs-rate-limiting-express-rate-limit-rate-limiter-flexible-bottleneck/) covers the inbound side of the same problem.

## Pitfalls that turn resilience code into an outage

**1. Retrying non-idempotent operations.** A retried `POST /charge` can double-charge a customer. Either make the operation idempotent with a client-generated idempotency key, or do not retry it. This is the single most expensive mistake in this entire article.

**2. No timeout on the underlying call.** A breaker with `timeout: 3000` still leaves a live socket behind unless the call honors an abort signal. Pass `AbortSignal.timeout()` into `fetch`, and configure your HTTP client's own timeout as well.

**3. Retry storms.** Without jitter and without a breaker, retries synchronize. Add `randomize: true`, cap `maxTimeout`, and always pair retries with a breaker on shared dependencies.

**4. Breaker thresholds copied from a blog post.** `errorThresholdPercentage: 50` on a service doing three calls per minute will trip on two failures and then stay open. Set `volumeThreshold` (opossum) or use `SamplingBreaker`/`ConsecutiveBreaker` (cockatiel) based on your actual request rate.

**5. Counting expected errors as failures.** A 404 from a lookup endpoint is a normal answer, not a dependency failure. Feed only genuine transport/5xx failures into the breaker, or you will open it during ordinary traffic.

**6. Swallowing the fallback.** `fallback: () => ({})` returns a truthy object that looks like a success. Downstream code writes empty records and nobody notices for a week. Make fallbacks explicit (`{ degraded: true }`) and log every invocation.

**7. Sharing one breaker across unrelated endpoints.** A slow `/reports` endpoint can trip the breaker protecting `/auth`. One breaker per dependency (or per critical operation), never per HTTP client instance.

**8. Testing only the happy path.** Inject failures deliberately: point the client at a local server that returns 500s, or use your library's test hooks (`opossum` allows `breaker.open()`; cockatiel policies can be executed against a stub). A breaker you have never seen open is a breaker you do not understand.

**9. Node.js 22+ requirement.** opossum's current release targets Node.js 22 and later. If you are pinned to an older LTS for compliance reasons, verify before committing — cockatiel and p-retry have far looser constraints.

## FAQ

### Which Node.js circuit breaker library should I use in 2026?

Use **cockatiel** if you need more than one pattern (retry, timeout, bulkhead, fallback) and want them composable; use **opossum** if circuit breaking is your only requirement and you want the most widely deployed breaker in the ecosystem. Both are actively maintained and Apache-2.0/MIT licensed respectively.

### Do I need a circuit breaker if I already have retries?

Yes, if the dependency is shared. Retries multiply load during an outage — the exact moment the dependency cannot absorb it. A breaker converts that multiplier to zero once the failure rate crosses a threshold, giving the dependency room to recover.

### Does p-retry include a circuit breaker?

No. p-retry is deliberately scoped to retrying async functions, with `AbortError` to stop retries that cannot succeed. Pair it with `AbortSignal.timeout()` for timeouts and with cockatiel or opossum when you need circuit breaking.

### What is the correct order for retry, timeout and circuit breaker policies?

Timeout innermost (each attempt gets a ceiling), circuit breaker around it (so it observes individual attempts), retry outermost (so retries pass through the breaker), and bulkhead around everything to cap concurrency. `wrap(bulkhead, breaker, timeout, retry)` with cockatiel expresses exactly that.

### How many retries should an HTTP client do?

Two to four, with exponential backoff, jitter and a hard timeout per attempt. Beyond four attempts you are usually retrying a problem that will not resolve in seconds. Always stop immediately on 4xx responses that indicate a permanent error.

### Is it safe to retry POST requests?

Only if the operation is idempotent. Use an idempotency key generated by the client and honored by the server, or restrict retries to `GET`, `HEAD`, `PUT` and `DELETE`. Retrying a payment capture without an idempotency key is how duplicate charges happen.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "opossum vs cockatiel vs p-retry in 2026: Stop Letting One Slow Upstream Take Down Your Node.js API",
  "description": "A production comparison of Node.js resilience libraries: opossum circuit breakers, cockatiel composed policies and p-retry, with real code, policy ordering rules and outage-prevention pitfalls.",
  "datePublished": "2026-11-06",
  "dateModified": "2026-11-06",
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
