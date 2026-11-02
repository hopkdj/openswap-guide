---
title: "Stop Running Redis Just for Background Jobs: Graphile Worker vs pgmq vs River in 2026"
date: "2026-11-03"
tags: ["postgresql", "job-queues", "background-jobs", "self-hosted", "distributed-systems"]
draft: false
description: "You already run Postgres. Here is how Graphile Worker, pgmq, River and pgqueuer compare for background jobs in 2026 — with real schemas, real code and the failure modes that bite at scale."
---

Every architecture diagram starts the same way: one Postgres box and good intentions. Then somebody needs a nightly invoice run, and suddenly there is a Redis instance, a Celery worker pool, a Flower dashboard, and a second on-call rotation for a cache server that is now load-bearing.

The uncomfortable question most teams never ask: **if you already operate Postgres with point-in-time recovery, why is your job queue living somewhere else?** Postgres has had `SELECT ... FOR UPDATE SKIP LOCKED` since version 9.5, and a queue built on it inherits the transactional guarantees you already pay for — a job is enqueued in the same transaction as the row that caused it, or neither happens.

This article compares the four serious Postgres-native options in 2026: **Graphile Worker**, **pgmq**, **River**, and **pgqueuer**. Star counts and last-commit dates are pulled live from GitHub, and every code snippet comes from the projects' own documentation patterns rather than memory.

## TL;DR: The Short Verdict

- **Graphile Worker** (2,434 stars) if you are on Node and want a queue running in ten minutes with zero schema design.
- **pgmq** (5,370 stars) if you want queue *primitives* — send, read, archive — and intend to build your own worker semantics on top, in any language.
- **River** (5,850 stars) if you are on Go and want the most complete client: typed job args, uniqueness constraints, periodic jobs, a UI, and transactional enqueue.
- **pgqueuer** (1,548 stars) if you are on Python and specifically want async-first, `LISTEN/NOTIFY`-driven dispatch instead of polling.

None of these require Redis, RabbitMQ or a separate broker. All four require you to understand one thing: **your queue is now part of your database's write path**, and that changes how you tune and monitor it.

## The 2026 Comparison Table

| Dimension | Graphile Worker | pgmq | River | pgqueuer |
|---|---|---|---|---|
| Stars | 2,434 | 5,370 | 5,850 | 1,548 |
| Last push | 2026-10-20 | 2026-10-20 | 2026-11-02 | 2026-10-29 |
| Primary language | Node.js / TypeScript | SQL + any client | Go (also Java, JS, Ruby, Rust bindings) | Python (asyncio) |
| Install model | `npm i graphile-worker` | `CREATE EXTENSION pgmq` or SQL-only | Go module + migration | `pip install pgqueuer` |
| Dispatch | Polling with `LISTEN/NOTIFY` wakeup | Explicit `read()` polling | Polling, configurable interval | `LISTEN/NOTIFY` + polling |
| Job uniqueness | Task identifiers + job keys | Message dedupe via headers | First-class unique jobs | Limited |
| Cron / periodic | Built in (`crontab` file) | Not provided | Built in (`PeriodicJob`) | Not provided |
| Web UI | Graphile Worker UI (community) | None | River UI (official) | CLI only |
| Transactional enqueue | Yes | Yes (SQL call) | Yes (same tx as business write) | Yes |
| Throughput ceiling | Thousands/sec (batched) | Highest of the four | High | Moderate |
| Best fit | Node SaaS backends | Polyglot event plumbing | Go services needing full features | Python async services |

## Decision Matrix: Match the Tool to the Job

| Your situation | Pick | Why |
|---|---|---|
| Node/TypeScript app, one queue, ship this week | Graphile Worker | Zero SQL, task files are just modules |
| Multiple services in different languages sharing queues | pgmq | The API is SQL; every language can call it |
| Go service where a job must commit with the business row | River | Same-transaction insert with typed args |
| Python asyncio app with low-latency dispatch needs | pgqueuer | Notification-driven, no polling latency |
| You need scheduled/cron jobs in the same system | Graphile Worker or River | Both ship a scheduler |
| You need fan-out to 10,000 consumers with retention | pgmq | Message-queue semantics, not job semantics |

A useful heuristic: **if you would describe the work as "messages", reach for pgmq. If you would describe it as "jobs with retries and a state machine", reach for River or Graphile Worker.**

## Graphile Worker: The Ten-Minute Queue

Graphile Worker's design bet is that a job queue should be a folder of functions. You do not declare queues, you do not define schemas, and you do not write a worker loop.

```bash
npm install graphile-worker
```

A task is a module in `tasks/`:

```javascript
// tasks/send_invoice.js
module.exports = async (payload, helpers) => {
  const { invoiceId } = payload;
  helpers.logger.info(`sending invoice ${invoiceId}`);

  // Throwing marks the job failed and schedules a retry
  await deliverInvoice(invoiceId);
};
```

Enqueue from your application code, inside an existing transaction if you want atomicity:

```javascript
const { makeWorkerUtils } = require("graphile-worker");

const utils = await makeWorkerUtils({ connectionString: process.env.DATABASE_URL });
await utils.addJob("send_invoice", { invoiceId: 9912 }, { maxAttempts: 5 });
```

Then run the worker:

```bash
npx graphile-worker -c "postgres://app@db.internal/app"
```

What you get without writing it: exponential-backoff retries with jitter, `max_attempts` caps, job keys for deduplication, a `crontab` file for periodic work, and `LISTEN/NOTIFY` so workers wake on insert instead of hammering the table with polls.

The catch: task payloads are untyped JSON unless you add a TypeScript task registry, and there is no official UI. You will be reading `graphile_worker.jobs` in `psql` when something goes wrong — which, to be fair, is a better debugging experience than most queue dashboards.

## pgmq: Postgres as a Message Broker

pgmq is the closest thing to "SQS, but it is a table." It deliberately does not manage workers. It gives you four verbs — `send`, `read`, `archive`, `delete` — plus visibility timeouts, and lets you decide what a worker looks like.

```sql
CREATE EXTENSION IF NOT EXISTS pgmq;

SELECT pgmq.create('orders');

SELECT * FROM pgmq.send('orders', '{"order_id": 9912, "action": "reserve"}');

-- Read up to 5 messages with a 30-second visibility timeout
SELECT * FROM pgmq.read('orders', 30, 5);

-- Remove from the queue once processed
SELECT pgmq.archive('orders', 1);
```

Because the interface is SQL, a Go service, a Python cron script and a `psql` session can all participate. That polyglot property is genuinely rare and is why the project sits at 5,370 stars despite having no client library to speak of.

Two operational notes worth internalizing before you adopt it. First, `read()` is a poll — there is no notification hook, so your worker's latency is your poll interval. Teams that set a 100 ms interval and then wonder why the database is busy have answered their own question. Second, archived messages accumulate in a partitioned archive table; retention is your responsibility, and an unmanaged archive will quietly become your largest relation.

## River: Typed Jobs with Transactional Enqueue

River is the most feature-complete option, and the Go API shows why. Job arguments are a struct, the job kind is a method, and the client is explicit about workers and queue concurrency.

```go
type SendInvoiceArgs struct {
	InvoiceID int64 `json:"invoice_id" river:"unique"`
}

func (SendInvoiceArgs) Kind() string { return "send_invoice" }

type SendInvoiceWorker struct {
	river.WorkerDefaults[SendInvoiceArgs]
}

func (w *SendInvoiceWorker) Work(ctx context.Context, job *river.Job[SendInvoiceArgs]) error {
	return deliverInvoice(ctx, job.Args.InvoiceID)
}
```

Wiring it up:

```go
workers := river.NewWorkers()
river.AddWorker(workers, &SendInvoiceWorker{})

client, err := river.NewClient(riverpgxv5.New(pool), &river.Config{
	Queues: map[string]river.QueueConfig{
		river.QueueDefault: {MaxWorkers: 50},
	},
	Workers: workers,
})
if err != nil {
	return err
}
if err := client.Start(ctx); err != nil {
	return err
}

// Enqueue inside the same transaction as the business write
tx, _ := pool.Begin(ctx)
defer tx.Rollback(ctx)
_, _ = tx.Exec(ctx, "UPDATE invoices SET status = 'queued' WHERE id = $1", 9912)
_, err = client.InsertTx(ctx, tx, SendInvoiceArgs{InvoiceID: 9912}, nil)
return tx.Commit(ctx)
```

That last block is the entire argument for Postgres queues in miniature. If the `UPDATE` commits and the process dies before `InsertTx`, the job exists. If the insert fails, the status change rolls back. With an external broker you get to write a compensating transaction and a reconciliation job instead.

River also ships `PeriodicJob` for cron-style work, first-class uniqueness with `ByArgs`/`ByKind`/`ByQueue`, and **River UI** — a real web interface with queue depth, job inspection and retry controls. In production, that UI is often what convinces a skeptical team.

## pgqueuer: Async Python Without the Poll Lag

pgqueuer is the smallest of the four and the only one shaped around Python's asyncio. Its distinguishing choice is dispatch: it uses `LISTEN/NOTIFY` so workers pick up jobs as they arrive rather than on a timer.

```python
from pgqueuer import PgQueuer

pgq = PgQueuer.from_asyncpg_pool(pool)

@pgq.entrypoint("send_invoice")
async def send_invoice(job) -> None:
    invoice_id = job.payload["invoice_id"]
    await deliver_invoice(invoice_id)

await pgq.run()
```

It handles the operational basics — retries with backoff, concurrency limits per entrypoint, job timeouts, and a CLI for queue statistics. What it does not carry is River's breadth: uniqueness is coarse, there is no scheduler, and the ecosystem of bindings is one language deep.

For a Python service that already runs an asyncpg pool, though, it removes an entire deployment: no Celery, no broker, no separate worker image to version. The whole worker is a coroutine in the process you already have.

## The Failure Modes That Show Up at 3 A.M.

**Table bloat is the tax on transactional queues.** Every enqueued and completed job is an `INSERT` and an `UPDATE`. At a few hundred jobs per second, autovacuum keeps up. At a few thousand, you need aggressive per-table settings — `autovacuum_vacuum_scale_factor` near `0.01` on the jobs table — or you will watch latency climb over weeks with no obvious cause. This is the single most common reason teams conclude "Postgres cannot be a queue" when the real problem was configuration.

**Long-running transactions hold the queue hostage.** A worker that opens a transaction, calls a slow external API, and commits afterwards pins row locks and bloats the table. Keep the transaction to the claim step, do the work outside it, then update the result. `SKIP LOCKED` makes claiming cheap only if claims are short.

**Connection count is your real concurrency limit.** Fifty workers do not mean fifty connections — they mean fifty plus your web pool plus your migration runner. Put a pooler in front (PgBouncer in transaction mode works with these libraries, with the caveat that session-level advisory locks break) and size `MaxWorkers` against available connections, not against your optimism.

**Retry storms amplify outages.** When a downstream dependency fails, every queued job retries on the same schedule. Jitter is not optional. Graphile Worker and River both add it by default; if you build on pgmq, add it yourself.

**The queue is a shared fate.** If the database is down, your web tier and your job tier are down together. That is often acceptable — it is usually true anyway — but say it out loud in the design review rather than discovering it during an incident.

**Vacuum cannot clean what your monitoring cannot see.** Track queue depth, oldest-job age, and dead-tuple ratio as first-class metrics. Oldest-job age is the one that catches silent worker death: depth stays flat while nothing is being processed.

## Why Self-Host Your Job Queue?

The default answer in 2026 is a managed queue service, and it is a reasonable answer — until the bill arrives and you notice you are paying per operation for work that a database you already run could do in a single transaction. Managed queues also split your consistency story in two: your data commits in one system, your job in another, and the gap between them is where duplicate charges and missing notifications live.

Self-hosting the queue inside Postgres collapses that gap. It also means one backup strategy, one restore drill, one set of credentials and one thing to monitor. The trade-off is honest: you give up independent scaling of the queue tier. For most applications under a few thousand jobs per second, that trade is a clear win.

If you are still deciding whether a dedicated broker earns its place, our [message queue servers comparison covering NSQ, Beanstalkd and Artemis](../2026-05-17-self-hosted-message-queue-servers-nsq-beanstalkd-artemis-guide/) is the natural next read. Teams running Python workers who want a dashboard rather than a doctrine should look at the [task queue web UI comparison of Flower, RQ Dashboard and Arena](../2026-05-22-self-hosted-task-queue-web-ui-flower-vs-rq-dashboard-vs-arena/). And if your "jobs" are really scheduled commands rather than retryable units of work, the [Docker cron scheduler comparison](../2026-05-02-ofelia-vs-docker-crontab-vs-docker-cron-self-hosted-docker-cron-schedulers-guide/) is the cheaper answer.

## FAQ

**Is Postgres actually fast enough to be a job queue?**

For the overwhelming majority of applications, yes. A single Postgres instance using `SKIP LOCKED` with batched claims will handle thousands of jobs per second before the queue itself is the bottleneck. The failures people attribute to Postgres are usually table bloat from weak autovacuum settings or long-running claim transactions — both configuration problems, not engine limits.

**Do I need the `pgmq` extension installed by a superuser?**

You can run pgmq either as a Postgres extension or as plain SQL installed into a schema, which is what most managed Postgres providers require since they do not grant superuser. Check your provider's extension allowlist first; if pgmq is not available, the SQL-only installation path in the project's repository works without elevated privileges.

**How does Graphile Worker avoid polling the database constantly?**

It combines a polling loop with a `LISTEN/NOTIFY` channel, so an inserted job wakes workers immediately while a slow poll acts as a safety net for missed notifications. That combination keeps latency low without a constant query storm, and it degrades gracefully if a notification is dropped.

**Can River and Graphile Worker enqueue jobs in the same transaction as my business write?**

Yes — that is their central design feature. Both accept a transaction handle when inserting a job, so the job and the data change commit or roll back together. With an external broker you would need an outbox table plus a relay process to approximate the same guarantee.

**What happens to in-flight jobs when I deploy a new worker version?**

The job stays claimed until its visibility timeout or claim expiry, then becomes available again for the new workers. That means your handlers must be idempotent: a job may run twice across a deploy boundary. Uniqueness keys reduce duplicate enqueues but do not prevent duplicate execution, so write handlers that tolerate replays.

**Should I run the queue in a separate database?**

Only if queue write volume is interfering with application query latency or if you need independent maintenance windows. A separate database means a distributed transaction problem between your data and your jobs — which is exactly the problem you chose a Postgres queue to avoid. Start on the same instance, measure, and split only with evidence.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Stop Running Redis Just for Background Jobs: Graphile Worker vs pgmq vs River in 2026",
  "description": "You already run Postgres. Here is how Graphile Worker, pgmq, River and pgqueuer compare for background jobs in 2026 — with real schemas, real code and the failure modes that bite at scale.",
  "datePublished": "2026-11-03",
  "dateModified": "2026-11-03",
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
