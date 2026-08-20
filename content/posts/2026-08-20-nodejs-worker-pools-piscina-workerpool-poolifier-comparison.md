---
title: "Piscina vs Workerpool vs Poolifier in 2026: Which Node.js Worker Pool Should You Use?"
date: "2026-08-20"
tags: ["nodejs", "javascript", "concurrency", "worker-threads", "performance"]
draft: false
cover: "/img/screenshots/piscina-cover.jpg"
---

A single JSON serialization pass over 100,000 records blocks your Node.js event loop for **300–800 milliseconds** — invisible in development, catastrophic at 5,000 requests per second. The standard fix is `worker_threads`, but raw threads are a footgun: you manage lifecycle, queueing, and backpressure yourself. Three mature pools wrap this for you: **Piscina**, **workerpool**, and **poolifier**. They look similar at a glance and differ sharply in API philosophy, runtime support, and deployment model. Here is what actually changes your choice in 2026.

## TL;DR

**Default to Piscina** for worker_threads-based CPU offload in Node — it is the fastest, simplest, and most actively maintained of the three (5,186 stars, commits August 2026). **Choose workerpool** when the same task code must run in the browser via Web Workers, or when you want to offload functions without writing a worker script. **Choose poolifier** when you need cluster-mode process pools, first-class TypeScript/ESM, or dynamic pool sizing, or when you deploy on Electron, Deno, or Bun. All three are free; two are MIT and workerpool is Apache-2.0.

## Quick Comparison Table

| Dimension | Piscina | workerpool | poolifier |
|---|---|---|---|
| GitHub repo | piscinajs/piscina | josdejong/workerpool | poolifier/poolifier |
| Stars | 5,186 | 2,307 | 453 |
| Last commit | 2026-08 | 2026-08 | 2026-08 |
| Worker type | worker_threads | worker_threads + Web Workers | worker_threads + cluster |
| Browser support | ❌ | ✅ | ❌ |
| TypeScript/ESM | ESM ✅, types bundled | CJS, limited types | TS-first, ESM ✅, JSR |
| Dynamic pool sizing | ❌ (fixed at init) | ❌ | ✅ (DynamicPool) |
| Pool events | limited | ❌ | ✅ (ready/busy/full) |
| Transferable objects | ✅ | ✅ | ✅ |
| License | MIT | Apache-2.0 | MIT |
| Runtime support | Node | Node + browser | Node, Electron, Deno, Bun |

## Decision Matrix

| Use case | Recommendation | Why |
|---|---|---|
| Default CPU offload in a Node service | **Piscina** | Smallest API surface, excellent throughput, ESM-native |
| Same code in browser and server | **workerpool** | The only one with Web Worker support in the browser |
| Process isolation for crash safety | **poolifier (cluster)** | Separate processes survive worker crashes and memory leaks |
| Heavy TypeScript monorepo | **poolifier** | Strict types, ESM, JSR distribution, `ThreadWorker` is fully typed |
| One-off background computation | **workerpool.exec()** | Offload a function directly — no worker file to write |
| Variable load (bursty queues) | **poolifier** | `DynamicThreadPool` scales between min and max workers at runtime |

## Piscina — The Fast, Minimal Worker Threads Pool

Piscina is the pool behind the Node.js ecosystem's heaviest users of threaded compute. Its philosophy is "one import, one class, run it" — you point it at a worker file and call `run()` with a payload, and the pool handles queueing, task distribution, and lifecycle. There is no separate worker registration API; your worker file simply exports a function (or named functions).

```js
// main.js
const path = require("path");
const Piscina = require("piscina");

const piscina = new Piscina({
  filename: path.resolve(__dirname, "worker.js"),
});

(async function () {
  const result = await piscina.run({ a: 4, b: 6 });
  console.log(result); // Prints 10
})();
```

```js
// worker.js — a plain exported function is the entire contract
module.exports = ({ a, b }) => {
  return a + b;
};
```

Workers may be async, and ESM is first-class — pass a `file://` URL as the filename and use `export default` in the worker:

```js
import { Piscina } from "piscina";

const piscina = new Piscina({
  filename: new URL("./worker.mjs", import.meta.url).href,
});

const result = await piscina.run({ a: 4, b: 6 });
console.log(result); // Prints 10
```

A single worker file can export multiple named handlers, and Piscina dispatches by task name — which makes it easy to model a pool of typed operations (image resize, hashing, PDF rendering) behind one worker file. The pool defaults to one worker per available CPU, uses the shared-array-buffer task queue, and is deliberately thin: no cluster mode, no browser target, no dynamic resizing. That focus is why it is the performance baseline other pools benchmark against.

## workerpool — The Cross-Runtime Offload Swiss Army Knife

workerpool is the oldest and most portable of the three. Its headline feature is that it runs in **both Node.js and the browser** (Web Workers), so you can share task code between your API server and client-side processing. It also supports two calling styles: offloading an existing function dynamically, and registering a dedicated worker script.

Dynamic offload — no worker file needed, but note the constraint that **function and arguments must be static and stringifiable**:

```js
const workerpool = require("workerpool");
const pool = workerpool.pool();

function add(a, b) {
  return a + b;
}

pool
  .exec(add, [3, 4])
  .then(function (result) {
    console.log("result", result); // outputs 7
  })
  .catch(function (err) {
    console.error(err);
  })
  .then(function () {
    pool.terminate(); // terminate all workers when done
  });
```

Dedicated worker scripts — the recommended pattern for anything non-trivial:

```js
// myWorker.js
const workerpool = require("workerpool");

// a deliberately inefficient implementation of the fibonacci sequence
function fibonacci(n) {
  if (n < 2) return n;
  return fibonacci(n - 2) + fibonacci(n - 1);
}

// create a worker and register public functions
workerpool.worker({
  fibonacci: fibonacci,
});
```

```js
// myApp.js
const workerpool = require("workerpool");

// create a worker pool using an external worker script
const pool = workerpool.pool(__dirname + "/myWorker.js");

pool
  .exec("fibonacci", [10])
  .then(function (result) {
    console.log("result", result);
  })
  .catch(function (err) {
    console.error(err);
  });
```

The browser story is the differentiator: `workerpool.js` loads via a plain `<script>` tag and you can drive the same `pool.exec()` API from a Web Worker context with `importScripts('workerpool.js')`. The trade-offs are a heavier callback-style API, CommonJS-first packaging, and no cluster mode — if your workload is "one web app doing CPU work on both sides of the wire", workerpool is the only pool that fits.

## poolifier — The TypeScript-First Pool With Cluster Mode

poolifier is the youngest of the three but the most feature-dense. It provides **worker_threads and cluster pools** under one API, fixed or **dynamic** sizing, an event emitter you can subscribe to, and first-class TypeScript/ESM (it is also published on JSR). It runs on Node, Electron, Deno, and Bun. Workers are defined by extending or instantiating `ThreadWorker`:

```js
import { ThreadWorker } from 'poolifier'

function yourFunction(data) {
  // this will be executed in the worker thread,
  // the data will be received by using the execute method
  return { ok: 1 }
}

export default new ThreadWorker(yourFunction, {
  maxInactiveTime: 60000,
})
```

Pools come in fixed and dynamic flavors, with lifecycle events you can hook:

```js
import { DynamicThreadPool, FixedThreadPool, PoolEvents, availableParallelism } from 'poolifier'

// a fixed worker_threads pool
const fixedPool = new FixedThreadPool(availableParallelism(), './yourWorker.js', {
  onlineHandler: () => console.info('worker is online'),
  errorHandler: e => console.error(e),
})

fixedPool.emitter?.on(PoolEvents.ready, () => console.info('Pool is ready'))
fixedPool.emitter?.on(PoolEvents.busy, () => console.info('Pool is busy'))

// or a dynamic pool: scales from floor to ceiling workers on demand
const dynamicPool = new DynamicThreadPool(
  Math.floor(availableParallelism() / 2),
  availableParallelism(),
  './yourWorker.js',
)
```

The same classes exist for cluster mode — `ClusterWorker`, `FixedClusterPool`, `DynamicClusterPool` — which swaps threads for full OS processes. That gives you crash isolation (a worker segfault kills only its process) and per-process memory limits, at the cost of higher memory use per worker. If your deployment is Electron or Bun, poolifier is effectively the only serious choice.

## Pitfalls and Traps When Using Worker Pools

1. **Serialization is the hidden tax.** Every task payload crosses the worker boundary via structured clone. Functions, class instances, and circular references either fail or serialize silently slowly. Keep payloads flat and small — if your "parallel" job spends more time cloning than computing, it is slower than the serial version. Use transferable objects (`ArrayBuffer`, `SharedArrayBuffer`) for large binary payloads.
2. **Only offload work above the crossover point.** IPC + scheduling overhead is roughly 10–50 microseconds per task. Offloading a 100-microsecond task is a net loss. A good rule: only pool tasks that take ≥ 1 ms of pure CPU per item, and amortize by batching items per task.
3. **workerpool's dynamic `exec()` needs static functions.** The function and its arguments are stringified and shipped to the worker — closures over main-thread state are silently lost. Long-lived state belongs in a dedicated worker script registered with `workerpool.worker()`, not in an offloaded closure.
4. **Threads share the process; cluster does not.** A native crash (segfault, OOM in a native addon) inside a worker_threads worker takes down the entire Node process, pool or no pool. If your workload uses native libraries, prefer poolifier's cluster mode for isolation.
5. **Pool size is not "more is faster".** Defaults (one per available CPU) are right for pure CPU work. On shared CI hosts or containers, oversubscription thrashes the machine — expose pool size via an environment variable and cap it (e.g. `MIN(4, os.availableParallelism())`) in CI.
6. **Error handling differs per API.** Piscina and poolifier reject the task promise; workerpool's `.exec()` also returns a promise but emits `'error'` on the pool for worker-level failures. Decide on one policy (reject-and-retry vs fail-fast) before you have 40 call sites.
7. **Worker memory is per-isolate.** Each thread carries its own heap. Ten workers on a 4 GB container can exhaust memory even when each task is tiny, if the workers import heavy libraries. Keep worker files dependency-light.

## Migration and Sizing Strategy

Moving from raw `worker_threads` to a pool is a two-step refactor: replace `new Worker(...)` + manual message passing with `pool.run(payload)`, then delete your hand-rolled queue (the pool's internal queue is usually better). The migration path that avoids regressions:

1. **Profile the serial path first.** Measure the actual per-item CPU time with `perf_hooks`. If the hot path is I/O-bound (network, disk), a worker pool is the wrong tool — a job queue with a bounded concurrency of promises is cheaper. For background work that must survive restarts, our [Node.js job queue comparison](../2026-07-24-nodejs-job-queue-libraries-bullmq-beequeue-pgboss/) covers BullMQ-style durable queues.
2. **Start with Piscina's defaults.** One worker per core, fixed pool, no tuning. Measure throughput and latency percentiles (p99 matters more than mean for event-loop health).
3. **Move the biggest cost items to transferables.** If you pass large buffers, switch to `ArrayBuffer` transfer so the data is moved by pointer, not copied.
4. **Cap it in production containers.** `Math.min(availableParallelism, 4)` for a typical web service — leave headroom for the event loop, GC, and the platform runtime. Our [process managers comparison](../2026-08-17-nodejs-process-managers-pm2-nodemon-forever-comparison/) shows how to keep the pool alive across deployments, and the [build tooling guide](../2026-06-21-javascript-build-bundlers-esbuild-rollup-parcel-swc-turbopack/) demonstrates the same "parallelize the hot path, not everything" thinking for build performance.
5. **Benchmark the pool boundary.** A simple A/B with `console.time` around a 1,000-task batch, serial vs pooled, tells you whether pooling is paying for itself in minutes — most teams are surprised how quickly IPC overhead eats small tasks.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Piscina vs Workerpool vs Poolifier in 2026: Which Node.js Worker Pool Should You Use?",
  "description": "Comparison of the three leading Node.js worker pools: Piscina, workerpool, and poolifier — worker_threads vs cluster, browser support, TypeScript support, and migration strategy.",
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

### What is the difference between worker_threads and cluster in Node.js?
`worker_threads` run JavaScript in parallel threads inside the same process — they share memory (via `SharedArrayBuffer`), start fast, and use little extra RAM, but a native crash in any thread kills the whole process. `cluster` spawns separate OS processes, each with its own V8 isolate and memory space — heavier, but isolated: a crash in one worker process does not take down the others. Piscina and workerpool are thread-based; poolifier supports both modes.

### When should I use a worker pool instead of a job queue?
A worker pool is for CPU-bound work that must complete promptly inside the same process lifecycle (image resizing, hashing, PDF rendering, data transformation). A job queue (BullMQ, Bee-Queue, pg-boss) is for durable, retryable background work that should survive restarts and scale across machines. The two compose well: enqueue the job, and process jobs in a worker pool so the queue consumer never blocks the event loop.

### Do these pools work in the browser?
Only workerpool does. It ships a browser build that runs on Web Workers via `importScripts('workerpool.js')` or a script tag, with the same `pool.exec()` API. Piscina and poolifier target Node.js runtimes only (poolifier additionally supports Electron's main process, Deno, and Bun).

### How many workers should I create?
Start with `os.availableParallelism()` (Piscina and poolifier default to this) and cap it in containers and CI where CPU limits are lower than the host's. For mixed workloads — a web server doing some offload — start at half the cores and measure latency percentiles; the event loop and GC need headroom too.

### Can workers share memory with the main thread?
Not directly. Each worker has its own isolate and heap; data crosses the boundary by structured clone (copy) or by transferring `ArrayBuffer`/`SharedArrayBuffer` objects (zero-copy ownership transfer, or shared mutable memory with `SharedArrayBuffer`). Plain JavaScript objects are always copied.

### Do worker pools work with ESM projects?
Yes. Piscina accepts `file://` URLs and `export default` workers, poolifier is ESM-first with JSR distribution, and workerpool supports ESM via its dedicated-worker script pattern (dynamic `exec` is CommonJS-oriented). All three run fine alongside `"type": "module"` projects.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
