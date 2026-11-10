---
title: "Self-Hosted Cloudflare Workers in 2026: open-compute vs workerd vs WinterJS"
date: "2026-11-10"
tags: ["self-hosted", "edge-computing", "serverless", "wasm", "javascript"]
description: "open-compute, workerd and WinterJS compared: install commands, capnp config, memory footprint, Workers API coverage and which one to run on your own hardware in 2026."
cover: "/img/screenshots/open-compute-dashboard.jpg"
draft: false
---

# Self-Hosted Cloudflare Workers in 2026: open-compute vs workerd vs WinterJS

You wrote a Worker, it ran at 12 ms p99 on Cloudflare's edge, and then finance asked why the invoice went from $5 to $340 after a traffic spike. The obvious fix is to run the same code on a box you already pay for. The non-obvious part is that "run Workers yourself" hides three very different products: a full platform, a bare runtime, and a runtime that quietly died eight months ago.

This guide installs all three, shows the real config files from each project, and tells you which one to actually put in production in November 2026.

## TL;DR: The 60-Second Verdict

- **You want Workers on one machine with a dashboard, routing, KV, D1, Queues and a deploy command:** use **open-compute**. It is the only project in this comparison that is a platform rather than a runtime, it ships as one binary, and v0.4.0 is actively developed (last push 2026-11-08).
- **You are embedding a runtime inside your own Go/Rust/C++ service, or you need the exact same `workerd` binary Cloudflare runs:** use **workerd** directly. It is the reference implementation, it is Apache-2.0, and it is the safest thing to debug against.
- **You found WinterJS in a 2024 blog post and thought it was the easy path:** do not deploy it. The README now opens with a deprecation notice pointing at Edge.js, the last commit was 2026-03-17, and there is no GitHub release to pin. It is fine for a weekend experiment, not for anything with a pager.

Everything else in this article is the detail behind those three sentences.

## Three Platforms at a Glance

Star counts and update dates were pulled from GitHub on 2026-11-10, not from memory.

| | **open-compute** | **workerd** | **WinterJS** |
|---|---|---|---|
| GitHub | elliothux/open-compute | cloudflare/workerd | wasmerio/winterjs |
| Stars | **3,538** | **9,154** | **3,183** |
| Last push | 2026-11-08 | 2026-11-10 | 2026-03-17 |
| Latest release | v0.4.0 | v1.20261110.1 | no GitHub releases |
| License | Apache-2.0 | Apache-2.0 | MIT |
| Written in | Rust | C++ | Rust (SpiderMonkey) |
| What it is | platform (runtime + control plane + storage) | runtime only | Service Worker HTTP server |
| Multi-tenant routing | yes, per instance | no | no |
| Durable state | SQLite + local/S3 objects | none | none |
| KV / R2 / D1 bindings | yes | only what your config wires | not applicable |
| Deploy lifecycle (rollback, promote) | yes, content-addressed | no | no |
| Status | active | active | **deprecated** |

The star gap is misleading. `workerd` has more stars because every Workers developer has read its source, not because more people run it in production standalone. `open-compute` is the newer project and the one that solves the boring problems.

## Decision Matrix: Pick by Situation

| Your situation | Recommended | Why |
|---|---|---|
| Migrating off Cloudflare to cut a bill | open-compute | wrangler-compatible config, `/client/v4` API, so existing tooling keeps working |
| Single-node internal API, one team | open-compute | one binary, no Kubernetes, no Redis, no Postgres sidecar |
| You need Workers inside an existing Rust or Go daemon | workerd as a library/binary | it is the runtime, intended to be embedded |
| You want the exact semantics Cloudflare has | workerd | same code path, same compatibility dates |
| You need a 5-line Service Worker HTTP server now | WinterJS (test only) | `winterjs tests/simple.js` and you are done |
| You need multi-region failover | none of these | all three are single-node; go back to a managed edge |
| You need a stable 1.0 API surface | none of these | open-compute is v0.4, workerd versions by date, WinterJS is deprecated |

That last row matters. Nothing here is a drop-in replacement for a global anycast network, and pretending otherwise is how teams end up with a 40-minute outage during a regional failover drill.

## open-compute — The Platform Layer workerd Deliberately Isn't

The project's own framing is the clearest thing about it: *workerd is a runtime, not a platform*. Somebody has to own ingress, routing, deployment state, scheduling, and storage. open-compute is that layer, packaged as a single `ocd` binary plus a supervised workerd child process.

The architecture is unusually boring on purpose — SQLite for platform metadata, local filesystem or S3 for object bytes, and a loopback-only channel between the control plane and the runtime. No external database, no cache tier, no operator to install:

| Component | Role |
|---|---|
| `ocd` | ingress, control API, scheduler, supervisor, deployment authority |
| `workerd` (pinned fork) | executes Workers, checksum-verified at startup |
| SQLite | authoritative platform state, embedded via `rusqlite` |
| local / S3 object authority | bundles, static assets, R2 bytes, snapshots, cache bodies |

The claim that got my attention is the compatibility table: Workers standard limits, KV, R2, D1, Durable Objects with alarms, Queues, Cron, Workflows, static assets, service bindings, cache, images, Vectorize, plus a `/client/v4` API that the official `wrangler`/`cf` CLI can talk to. The repo says the test suite tracks 2,256 stable API members and compares ten products request-by-request against real Cloudflare.

### Install and first start

The documented path installs a user-scoped binary, creates an instance, and starts a login-scoped service:

```sh
curl -fsSL https://open-compute.dev/install.sh | sh
ocd setup --yes
ocd status
ocd dashboard
```

For a host-wide service that survives logout, you explicitly opt into system scope:

```sh
curl -fsSL https://open-compute.dev/install.sh | sudo sh
sudo ocd setup --system --yes
```

That `--system` flag being explicit rather than inferred is a good sign. So is `ocd capabilities --json`, which makes the daemon report its own supported surface instead of making you trust a README table.

### Deploy a Worker

It expects the standard `cloudflare.config.ts` plus Vite plugin workflow rather than a proprietary format:

```sh
npm install --save-dev cf@1.0.0-beta.21 @cloudflare/vite-plugin@beta vite typescript
npm run dev
npm run build
ocd cf deploy --prebuilt --mode production
```

Deployments are immutable and content-addressed, so a rollback moves a pointer instead of rebuilding. In practice this is the difference between "roll back in 3 seconds" and "roll back in 8 minutes while the error rate climbs."

![open-compute dashboard showing instances, deployments and storage](/img/screenshots/open-compute-dashboard.jpg "open-compute operator dashboard, dark and light mode")

### Where it hurts

It is **v0.4.0**. The compatibility table has a long "Not yet" column — Hyperdrive, rate limiting, mTLS certificates, Tail Workers, Logpush, Pipelines. Requests that need those capabilities are rejected rather than silently degraded, which is the right behavior but still means a migration plan needs an audit pass. And it is explicitly *not* a multi-replica HA cluster: one daemon, one machine. If that machine dies, so does your edge.

For a related look at sandboxing trade-offs, our [WebAssembly runtime comparison](../2026-04-21-wasmedge-vs-wasmtime-vs-wasmer-self-hosted-webassembly-runtimes-guide-2026/) covers the isolation models underneath these platforms.

## workerd — The Reference Runtime, and Why You Might Want It Bare

`workerd` is the JavaScript/Wasm runtime that actually powers Cloudflare Workers. Running it yourself gives you identical isolate semantics, identical compatibility dates, and identical bugs — which is exactly what you want when you are debugging a production-only failure.

Install it from npm (the platform-specific package pulls the binary), or build it from source:

```sh
npm install -g workerd
workerd --version
```

A minimal config is a Cap'n Proto file. This is the real `samples/helloworld/config.capnp` shape, not a paraphrase:

```capnp
using Workerd = import "/workerd/workerd.capnp";

const helloWorldExample :Workerd.Config = (
  services = [ (name = "main", worker = .helloWorld) ],
  sockets = [ ( name = "http", address = "*:8080", http = (), service = "main" ) ]
);

const helloWorld :Workerd.Worker = (
  serviceWorkerScript = embed "worker.js",
  compatibilityDate = "2023-02-28",
);
```

Then:

```sh
workerd serve my-config.capnp
```

Newer builds also accept a Wrangler config directly for simple projects — `workerd serve wrangler.jsonc` — which is the pragmatic middle ground between a full platform and hand-written capnp.

For production, the README documents a systemd unit using socket activation rather than letting the runtime bind privileged ports itself:

```ini
[Service]
ExecStart=/usr/bin/workerd serve /etc/workerd/config.capnp --socket-fd http=3 --socket-fd https=4
```

That is the whole deployment story. There is no deploy API, no rollback, no per-tenant routing, no KV. You get a process that executes isolates very well and nothing else. If you have one Worker and one config file, that is a feature. If you have twelve Workers and three environments, you will rebuild open-compute's control plane badly.

## WinterJS — The Third Slot Is a Warning, Not a Recommendation

WinterJS deserves its 3,183 stars: it is a JavaScript server that runs Service Worker scripts per the WinterCG specification, built on SpiderMonkey and hyper, and its benchmark claims up to 100,000 requests per second on a single laptop.

Running it is genuinely two commands:

```sh
wasmer run wasmer/winterjs --net --mapdir=tests:tests tests/simple.js
```

with a worker like:

```js
addEventListener('fetch', (req) => {
  req.respondWith(new Response('hello'));
});
```

Or natively, after `cargo install --git https://github.com/wasmerio/winterjs winterjs`, just `winterjs tests/simple.js` and curl port 8080.

Here is the problem, and it is the first line of the README:

> This project is now deprecated in favor of the Edge.js JS runtime, which can run any Node.js apps sandboxed with Wasmer.

Last commit 2026-03-17. No GitHub releases, so there is no version to pin and no changelog to diff. The successor, Edge.js, is a different product category — a Node.js-compatible sandboxed runtime (844 stars, last push 2026-11-07) rather than a Workers platform. Migration is not a rename; it is a rewrite of your fetch handler into `node:http`.

So why include it at all? Because most "self-host Workers" articles written in 2024 and 2025 still recommend it, and readers keep landing on those posts. If you are choosing today, the honest answer is: use open-compute for platform semantics, workerd for runtime fidelity, and treat WinterJS as a historical artifact.

If your actual goal is edge placement rather than Workers compatibility, [KubeEdge vs OpenYurt vs SuperEdge](../2026-04-23-kubeedge-vs-openyurt-vs-superedge-self-hosted-edge-computing-guide-2026/) is the more relevant comparison, and container-based isolation is covered in [Wasm container runtimes](../2026-05-24-webassembly-container-runtimes-crun-wasm-vs-spin-vs-wasmcloud-guide/).

## Where Each One Breaks: The Pitfall List

**1. Compatibility dates are not optional cosmetics.** `workerd` requires `compatibilityDate`. Pin it deliberately and bump it on a schedule — the same date that makes one Worker behave correctly can change another's semantics.

**2. "Workers-compatible" never means 100%.** open-compute publishes a partial/not-yet table; workerd only supports what your capnp wires up. Audit your bindings list before committing to a migration, and use `ocd capabilities --json` as the source of truth instead of documentation.

**3. Single node means single point of failure.** All three are one process on one machine. If you need five nines, none of these are your answer, and adding a load balancer in front does not fix state.

**4. Local storage is not a backup.** open-compute keeps object bytes on the local filesystem by default (S3 optional) and metadata in SQLite. Snapshot the data directory on a schedule you have actually tested restoring.

**5. Memory ceilings are per-isolate, not per-host.** A Worker that allocates aggressively will hit the isolate limit and throw, not gracefully degrade. Test with your worst payload, not your average one.

**6. Do not build on a deprecated runtime.** WinterJS has no releases and no forward path to the Workers programming model. The successor runs Node.js code, which is a different deployment contract entirely.

**7. Wrangler version drift bites.** open-compute CI pins `cf` 1.0.0-beta.21 and only warns on other 1.0.x versions. Freeze the CLI version in your repo or your builds will change under you.

## FAQ

### Can I run Cloudflare Workers on my own server in 2026?

Yes, and there are three levels of it. `workerd` is the official runtime and runs Workers exactly as Cloudflare does, but gives you no routing, storage, or deploy lifecycle. `open-compute` wraps a pinned workerd fork with a control plane, SQLite state, KV/R2/D1 bindings, and a `wrangler`-compatible deploy flow. WinterJS runs Service Worker scripts too, but it is deprecated as of 2026.

### Is open-compute a drop-in replacement for Cloudflare Workers?

No. It targets the Workers programming model and exposes a `/client/v4` API that official tooling can call, but it is a single-node platform. There is no anycast, no cross-region replication, and a documented list of unsupported features including Hyperdrive, rate limiting, and Logpush. Treat it as a migration target with an audit step, not a like-for-like swap.

### How much memory does each runtime need?

`workerd` and `open-compute` are both small: the binaries are static and measured in tens of megabytes, with SQLite embedded in the latter. Real memory use is dominated by your Workers themselves and by isolate count, not by the host process. WinterJS is heavier to build (it compiles SpiderMonkey) but ships as a prebuilt Wasmer package, so build cost only applies if you compile it yourself.

### Do I need Kubernetes to self-host Workers?

No, and that is the point of open-compute: one binary, one daemon, SQLite and a directory. Kubernetes only enters the picture if you already run it for other workloads. If you are comparing container orchestrators for this job, our [Quadlet vs Docker Compose comparison](../2026-11-08-podman-quadlet-vs-docker-compose-systemd-containers/) covers the systemd-native alternative.

### Which one should I pick for a production internal API?

`open-compute` if you want deploy commands, rollback, and bindings without assembling them yourself. `workerd` if you already have a service that should embed a JavaScript sandbox and you want zero platform code. Do not pick WinterJS for anything new.

### What happened to WinterJS?

It was deprecated in favor of Edge.js, Wasmer's Node.js-compatible sandboxed runtime. The WinterJS repository has had no commits since 2026-03-17 and publishes no GitHub releases. Edge.js is a different product — it runs Node.js applications, not Workers fetch handlers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Cloudflare Workers in 2026: open-compute vs workerd vs WinterJS",
  "description": "open-compute, workerd and WinterJS compared: install commands, capnp config, Workers API coverage and which one to run on your own hardware in 2026.",
  "datePublished": "2026-11-10",
  "dateModified": "2026-11-10",
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
