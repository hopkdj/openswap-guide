---
title: "Restate vs Inngest vs Trigger.dev in 2026: Which Durable Execution Engine Should You Self-Host?"
date: "2026-09-21"
tags: ["workflow-orchestration", "background-jobs", "self-hosted", "distributed-systems", "docker"]
draft: false
cover: "/img/screenshots/inngest-dashboard.jpg"
description: "Hands-on comparison of Restate 1.7, Inngest 1.45 and Trigger.dev 4.6 for self-hosted durable execution: real docker-compose files, licensing traps, and a decision matrix."
---

Your worker dies at step 7 of 12. The payment went through, the receipt did not, and nobody can tell you which state the job is in. That is the exact failure mode durable execution engines were built to eliminate — and in 2026 there are three serious open-source options you can run on your own hardware: **Restate, Inngest, and Trigger.dev**.

This guide compares them with live repository data, the official docker-compose files (pulled from each repo, not from memory), and the licensing details that decide whether you are allowed to self-host them in production at all.

## TL;DR — Quick Verdict

- **Choose Restate** if you want a single Rust binary, polyglot SDKs (TypeScript, Java/Kotlin, Python, Go, Rust), and durable state inside your existing services. It is the least infrastructure to operate — but the license is Business Source License 1.1, so read the terms before you build a product on top of it.
- **Choose Inngest** if you are event-driven: you already run Postgres and Redis, and you want a dashboard plus step functions with sleeps, fan-out, and concurrency controls. Note that the server is **SSPL-licensed**, which is a hard blocker for many commercial hosting scenarios.
- **Choose Trigger.dev** if your stack is TypeScript and your jobs are long-running with real observability. It has the largest community (16k+ stars), the most permissive license of the three (**Apache-2.0**), and the heaviest self-hosted footprint — Postgres with logical replication, Redis, MinIO, and ClickHouse.

If you only take one sentence away: **Restate is the smallest thing to operate, Trigger.dev is the safest license, Inngest is the best event-driven UX.**

## Quick Comparison Table

All figures pulled from GitHub on 2026-09-21.

| Dimension | Restate | Inngest | Trigger.dev |
|---|---|---|---|
| Stars | **4,449** | 5,855 | **16,352** |
| Core language | Rust | Go | TypeScript |
| License | Business Source License 1.1 | SSPL 1.0 (Apache-2.0 future) | **Apache-2.0** |
| Latest release | v1.7.10 | v1.45.1 | v4.6.3 |
| Last push | 2026-09-18 | 2026-09-20 | 2026-09-20 |
| Deploy shape | 1 binary / 1 container | Server + Postgres + Redis | Webapp + worker + Postgres + Redis + MinIO + ClickHouse |
| Runtime deps | None (embedded storage or object store) | PostgreSQL 17, Redis 7 | PostgreSQL (logical WAL), Redis 7, S3-compatible store, ClickHouse |
| SDKs | TS, Java, Kotlin, Python, Go, Rust | TS, Python, Go | TypeScript only |
| Dashboard | Admin API + Grafana dashboards | Built-in web dashboard | Built-in web dashboard |
| Self-host effort | **Low** | Medium | **High** |

## Scenario Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Microservices in mixed languages, want durable RPC between them | **Restate** | Durable execution is a library-level primitive; no separate workflow DSL |
| Event fan-out, throttling, debouncing, scheduled steps | **Inngest** | Its queue is multi-tenant with flow control built in |
| Long-running TypeScript jobs, 30-minute timeouts, file uploads | **Trigger.dev** | Tasks run in your own TypeScript codebase with real run logs |
| You must ship a commercial SaaS product | **Trigger.dev** | Only Apache-2.0 option here |
| You have one small VM and 2 GB of RAM | **Restate** | Single process, no Postgres/Redis/ClickHouse chain |
| You already run Postgres 17 + Redis in production | **Inngest** | Reuses infrastructure you already pay for |

## Restate — Durable Execution as a Library

Restate (v1.7.10, 4,449 stars, actively developed) inverts the usual model. Instead of moving your code into a workflow engine, you keep writing normal service handlers and wrap side effects in `ctx.run()` calls. Restate journals every result, so a crash mid-handler replays the journal and resumes exactly where it stopped.

![Restate Grafana monitoring dashboards from the official repository](/img/screenshots/restate-grafana.jpg "Restate ships Grafana dashboards for invocation latency, failures and service health")

The server itself is a single Rust binary with no external database requirement:

```bash
docker run --rm -p 8080:8080 -p 9070:9070 -p 9071:9071 \
    --add-host=host.docker.internal:host-gateway \
    docker.restate.dev/restatedev/restate:latest
```

Port `8080` is ingress, `9070` is the admin/REST API, and `9071` exposes metrics for Prometheus. Registering a service is one command:

```bash
# Register a service listening on port 9080
restate deployments register http://localhost:9080
```

A durable handler looks like ordinary application code — the durability comes from the boundaries you declare:

```typescript
import * as restate from "@restatedev/restate-sdk";

const payments = restate.service({
  name: "Payments",
  handlers: {
    charge: async (ctx: restate.Context, req: { account: string; cents: number }) => {
      // Journaled: replayed from the journal instead of re-executing
      const idempotencyKey = await ctx.run(() => deriveIdempotencyKey(req));
      const result = await ctx.run(() => provider.charge(idempotencyKey, req.cents));
      return result;
    },
  },
});
```

**Why teams pick it:** the operational surface is genuinely small — one container, no Postgres, no Redis, no ClickHouse. Long-running handlers survive restarts, and the SDK exists for TypeScript, Java, Kotlin, Python, Go, and Rust, so polyglot shops do not need a second workflow language.

**Why teams hesitate:** the repository license is **Business Source License 1.1**, not OSI-approved open source. It is fine for internal use, but you must read the "Additional Use Grant" clause before shipping a competing hosted product.

## Inngest — Event-Driven Step Functions

Inngest (v1.45.1, 5,855 stars) is the "if you know Postgres and Redis, you already have a self-hosted Inngest" option. The server is a Go binary that runs as a single process, and its official docker-compose example from the docs is refreshingly short:

```yaml
services:
  inngest:
    image: inngest/inngest
    command: "inngest start"
    ports:
      - "8288:8288"   # APIs and Dashboard
      - "8289:8289"   # Connect WebSocket gateway
    environment:
      # Both keys must be hex strings with an even number of characters
      - INNGEST_EVENT_KEY=your_event_key_here
      - INNGEST_SIGNING_KEY=your_signing_key_here
      - INNGEST_POSTGRES_URI=postgres://inngest:password@postgres:5432/inngest
      - INNGEST_REDIS_URI=redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "inngest", "alpha", "doctor", "healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:17
    environment:
      - POSTGRES_DB=inngest
      - POSTGRES_USER=inngest
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Two operational details matter here. First, the `inngest alpha doctor healthcheck` subcommand only exists from **v1.19.3** onward — older images need `curl -f http://localhost:8288/health` instead. Second, the two secrets must be **hex strings of even length**; a normal passphrase will be rejected at boot, which is one of the most common self-hosting support questions.

Functions are declared as step functions, and every `step.run()` is individually retried and memoized:

```typescript
import { Inngest } from "inngest";
const inngest = new Inngest({ id: "shop" });

export const processOrder = inngest.createFunction(
  { id: "process-order", concurrency: { limit: 20 } },
  { event: "shop/order.created" },
  async ({ event, step }) => {
    const user = await step.run("load-user", () => loadUser(event.data.userId));
    await step.sleep("cool-off", "1h");
    await step.run("send-receipt", () => sendReceipt(user, event.data));
  }
);
```

**What you get that the others do not:** a multi-tenant queue with built-in throttling, debouncing, prioritisation, rate limiting, and batching — the happy path for high-volume event streams. There is also an official Helm chart for Kubernetes with KEDA-based autoscaling.

**The catch:** the server is licensed under the **Server Side Public License (SSPL) 1.0**, with an Apache-2.0 future license. If you intend to offer a hosted workflow service to third parties, that is a legal conversation, not a technical one.

## Trigger.dev — TypeScript-Native Long-Running Tasks

Trigger.dev v4.6.3 is the biggest project of the three at **16,352 stars**, and the only one under a plain **Apache-2.0** license. It is also the most demanding to self-host: the official stack includes Postgres configured for **logical replication**, Redis, a MinIO (S3-compatible) object store for large payloads, and ClickHouse for run logs.

The contributor compose file (`docker/docker-compose.yml`) shows how much the platform expects from Postgres:

```yaml
services:
  database:
    build:
      context: .
      dockerfile: Dockerfile.postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    command:
      - -c
      - listen_addresses=*
      - -c
      - wal_level=logical          # required for the realtime layer
      - -c
      - shared_preload_libraries=pg_partman_bgw
      - -c
      - max_connections=500        # default 100 is exhausted quickly
    ports:
      - "${POSTGRES_HOST_PORT:-5432}:5432"

  redis:
    image: redis:7
    volumes:
      - redis-data:/data

  minio:
    image: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
    command: server /data --console-address ":9001"

volumes:
  database-data:
  redis-data:
  minio-data:
  clickhouse-data:
```

**`wal_level=logical` is not optional.** It is what powers realtime run updates. Turning it off after the fact means restarting Postgres and rebuilding indexes — plan for it before your first production deploy, not after.

Tasks are just TypeScript functions with declared retry behaviour:

```typescript
import { task } from "@trigger.dev/sdk/v3";

export const syncCrm = task({
  id: "sync-crm",
  retry: { maxAttempts: 5 },
  run: async (payload: { accountId: string }) => {
    const rows = await fetchRows(payload.accountId);
    await pushToCrm(rows);
    return { pushed: rows.length };
  },
});
```

**Why it wins for TypeScript teams:** runs are visible in the dashboard with full logs, the object store handles multi-hundred-megabyte payloads without stuffing them into database rows, and ClickHouse keeps run history queryable far past the point where a Postgres table would need partitioning gymnastics.

**Why it costs you:** four stateful services plus a webapp and worker processes. Budget several gigabytes of RAM and a proper backup strategy for Postgres, MinIO, and ClickHouse independently.

## Avoid These Pitfalls

- **License first, architecture second.** SSPL (Inngest) and BUSL (Restate) both restrict offering the software as a competing hosted service. Trigger.dev's Apache-2.0 has no such trap. Decide this before you write a line of integration code.
- **Retries are at-least-once, not exactly-once.** All three engines retry steps. Wrap every external call in an idempotency key — a Stripe-style `idempotency-key` header, a unique constraint, or a deduplication table. Durable execution does not remove the need for idempotent effects.
- **Connection pool exhaustion.** Trigger.dev's compose explicitly raises `max_connections` to 500 because the webapp alone opens roughly 50 pooled connections and the realtime layer another 40. If you self-host on managed Postgres with a low connection cap, size the pool or add PgBouncer in transaction mode.
- **Deploys during in-flight work.** Restate pins invocations to registered service endpoints; if you deregister an old deployment before in-flight invocations drain, they fail. Use the admin API to drain rather than deleting the registration.
- **Unbounded state growth.** Sleep timers, journals, and run history all grow forever by default. Set retention windows early — ClickHouse keeps months of run data comfortably, and you will not notice the disk filling until it does.
- **Secret format requirements.** Inngest rejects non-hex keys at startup. Restate needs the admin port reachable for CLI registration. Check these before you write your first handler.

## Why Self-Host Durable Execution At All?

Managed workflow platforms price per step execution, and the bill scales with exactly the thing you want more of — throughput. Self-hosting inverts that: Restate, Inngest, and Trigger.dev all run on hardware you already own, and the marginal cost of an extra million steps is CPU time you are already paying for.

The second reason is data residency. Durable execution journals contain payloads: order details, customer identifiers, sometimes file contents. Keeping those in your own Postgres and object store removes an entire class of compliance questions.

Third, avoiding vendor lock-in matters more than usual here because workflow code is deeply intertwined with the runtime API. Migrating hundreds of `step.run()` calls off a hosted platform is a rewrite, not a configuration change. Running the server yourself means the API surface you build on is one you control the version of.

If you are still deciding whether you need a durable engine at all, compare this against classic orchestrators in our [saga orchestrator comparison](../2026-05-03-temporal-vs-camunda-vs-cadence-self-hosted-saga-orchestrators-guide/) and the broader [workflow orchestration roundup](../2026-04-24-dagu-vs-netflix-conductor-vs-airflow-self-hosted-workflow-orchestration-guide-2026/). If your use case is closer to business automation than engineering primitives, the [workflow automation platforms guide](../2026-04-29-automatisch-vs-n8n-vs-activepieces-self-hosted-workflow-automation-2026/) covers that space instead.

## FAQ

### Which durable execution engine is easiest to self-host?

**Restate.** It is a single container with no external database, no Redis, and no object store. You can be running durable handlers on a 1 GB VM in under five minutes. Inngest is second: it needs Postgres 17 and Redis 7, both of which are standard. Trigger.dev is the heaviest, requiring Postgres with logical replication, Redis, MinIO, and ClickHouse.

### Is Inngest really open source if I self-host it?

The server is licensed under the **SSPL 1.0**, which is source-available but not OSI-approved. It is generally fine for internal business use; the SSPL's obligations trigger when you offer the software itself as a service to third parties. If you need an unambiguously permissive license, Trigger.dev (Apache-2.0) is the safe pick, and Restate's BUSL 1.1 has its own restrictions worth reading.

### Do I still need idempotency if the engine retries my steps?

Yes. All three engines provide at-least-once execution of steps, which means a step can run twice — for example if the worker dies after the external call succeeds but before the result is journaled. Design side effects to be idempotent with a key derived from the run and step identity.

### Can these engines handle multi-hour or multi-day workflows?

Yes, and that is their main advantage over a cron runner or a job queue. Inngest has `step.sleep()`, Trigger.dev supports delayed and long-running tasks with checkpointed execution, and Restate journals timers durably so a `ctx.sleep()` inside a handler survives a full server restart. Multi-day workflows with human approval steps in the middle are a standard pattern in all three.

### What is the difference between durable execution and a normal job queue?

A job queue retries the whole job from the start. A durable execution engine records the result of every step, so on failure it resumes at the first unfinished step rather than re-running completed work. That difference is what makes long, expensive, multi-step workflows safe to retry.

### Which one should I pick if my team is polyglot?

Restate. It ships officially supported SDKs for TypeScript, Java, Kotlin, Python, Go, and Rust. Inngest covers TypeScript, Python, and Go. Trigger.dev is TypeScript-only by design, which is a strength for TS teams and a blocker for everyone else.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Restate vs Inngest vs Trigger.dev in 2026: Which Durable Execution Engine Should You Self-Host?",
  "description": "Comparison of Restate, Inngest and Trigger.dev for self-hosted durable execution, with official docker-compose files, licensing analysis and a decision matrix.",
  "datePublished": "2026-09-21",
  "dateModified": "2026-09-21",
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
