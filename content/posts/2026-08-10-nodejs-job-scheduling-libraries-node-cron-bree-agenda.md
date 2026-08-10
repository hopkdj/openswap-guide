---
title: "Node.js Job Scheduling in 2026: node-cron vs Bree vs Agenda — Which Scheduler Should You Use?"
date: "2026-08-10"
tags: ["nodejs", "job-scheduling", "cron", "agenda", "bree", "backend", "developer-tools"]
draft: false
---

## Your Cron Job Is About to Silently Fail

Every Node.js developer has shipped the same time bomb: a `setInterval` in the main process that runs a cleanup task, dies when the process restarts, and — worse — fires *twice* when two instances run behind a load balancer. Production job scheduling is a different discipline from writing a script: you need persistence across restarts, overlap prevention, retry semantics, and a way to see what ran. Three libraries dominate Node.js scheduling — **node-cron**, **Bree**, and **Agenda** — and they solve very different problems under the same label.

## TL;DR / Quick Verdict

If you need **lightweight cron syntax with zero dependencies** for a single-process app, use **node-cron**. If you need **worker-thread isolation, graceful shutdown, and human-readable schedules** without a database, use **Bree**. If you need **durable, persistent job state shared across multiple server instances**, use **Agenda** — it is the only one of the three backed by MongoDB, and its 9,692 GitHub stars reflect a decade of production use. Pick the one whose *persistence model* matches your deployment, not the one with the prettiest API.

## Quick Comparison Table

| Dimension | node-cron | Bree | Agenda |
|---|---|---|---|
| GitHub stars | 3,273 | 3,290 | 9,692 |
| Last pushed | 2026-08-02 | 2026-02-17 | 2026-07-21 |
| License | ISC | MIT | MIT |
| Storage backend | None (in-memory) | None (in-memory) | MongoDB |
| Worker isolation | No (same process) | Yes (worker threads) | Yes (separate process via `agenda` instance) |
| Cron syntax | Standard 5-field | 5-field + human syntax | 5-field + every X |
| Overlap prevention | v4 built-in | Built-in | Built-in (unique jobs) |
| Graceful shutdown | Manual | First-class (`stop()` + async jobs) | First-class (`stop()` drains queue) |
| Distributed multi-instance | No | No | Yes (shared MongoDB) |
| Dependencies | Zero | Small set | mongodb driver only |
| Best for | Simple recurring tasks | CPU-heavy jobs in isolation | Persistent, retriable enterprise jobs |

## Decision Matrix: Pick in 10 Seconds

| Use Case | Recommended | Why |
|---|---|---|
| Simple recurring task in one process | node-cron | Zero dependencies, 3 lines of code, cron string you already know |
| Jobs that must not corrupt on crash | Bree | Worker threads isolate CPU-heavy work; async job cleanup on shutdown |
| Multi-instance deployment (PM2, K8s, cluster) | Agenda | MongoDB lock ensures exactly-once semantics across instances |
| Jobs with retry + failure history | Agenda | Persistent state; failed jobs survive restarts with run history |
| Team already using BullMQ for queues | Bree (or BullMQ repeatable jobs) | Matches the queue ecosystem; see our [Node.js job queue comparison](../2026-07-24-nodejs-job-queue-libraries-bullmq-beequeue-pgboss/) |

## node-cron — The Zero-Dependency Workhorse

node-cron (3,273 stars, last push 2026-08-02) is the closest thing Node.js has to the system crontab: a tiny scheduler that takes a standard five-field cron expression and runs a callback. Version 4 removed all runtime dependencies and added two features that matter more than they look: **overlap prevention** (a task that is still running is not started again) and **timezone support**. The API has been stable for years:

```javascript
import cron from 'node-cron';

// Run every 5 minutes (5-field cron: min hour dom mon dow)
cron.schedule('*/5 * * * *', () => {
  console.log('Sweeping expired sessions...');
}, {
  timezone: 'Europe/Berlin',
  name: 'session-sweep',
  runOnInit: false
});
```

The whole library is ~3 KB and has zero dependencies, which makes it attractive for serverless functions and edge runtimes where dependency weight matters. node-cron's own README notes it is used by 220k+ repositories — it is the default answer to "I just need a cron job."

Where node-cron falls short: there is **no persistence**. Restart the process and every schedule restarts its in-memory timer; a job that was mid-flight is gone. There is also no built-in retry, no job history, and no inter-process coordination — run two instances and both execute every schedule. For anything beyond simple recurring work, node-cron is a starting point, not a platform.

## Bree — Worker Threads and Graceful Shutdown

Bree (3,290 stars, last push 2026-02-17) was built by the team behind Forward Email (Lad) to solve a specific pain: long-running jobs in a Node.js process **block the event loop**, and crashes in job code take down the parent process. Bree executes each job in a **worker thread**, so a memory leak or exception in a job cannot kill your API server. It also supports cron, Date, and human-readable scheduling syntax:

```javascript
import Bree from 'bree';

const bree = new Bree({
  jobs: [
    {
      name: 'nightly-report',
      cron: '0 3 * * *',            // 3 AM every day
      timeout: 0
    },
    {
      name: 'cache-warm',
      every: '2 hours',             // human syntax
      worker: { workerData: { region: 'eu-west' } }
    }
  ]
});

bree.start();
```

Bree's killer feature is **graceful shutdown**: `bree.stop()` waits for the currently running job to finish (or times out), then cleans up workers — no more "job half-written to the database because the deploy killed the process." It also ships with a built-in **error event bus**, job status reporting (`bree.getWorkerMetadata()`), and support for extending jobs with plugins. The `@ladjs` ecosystem integrates Bree with logging and rate limiting out of the box.

The trade-offs: Bree's state is **in-memory**, so it is not safe for multi-instance deployments — you must pin jobs to one process (PM2 `instances: 1` or a dedicated worker pod). Jobs are also **file-based** (each job is a script in `jobs/` by default), which is clean for a monorepo but awkward if you want to define jobs dynamically from a database.

## Agenda — Durable, Persistent, Multi-Instance Scheduling

Agenda (9,692 stars, last push 2026-07-21) is the heavyweight: every job definition, schedule, run, and failure is stored in **MongoDB**, which turns scheduling into a shared, durable state machine. Multiple server instances (or pods) can run the same Agenda instance; the MongoDB lock ensures each job runs exactly once, and jobs interrupted by a crash are re-queued when the process comes back. That persistence is why Agenda has carried production workloads since 2013:

```javascript
import Agenda from 'agenda';

const agenda = new Agenda({ db: { address: 'mongodb://localhost/agenda' } });

agenda.define('send-invoice-reminders', async (job) => {
  const { invoiceIds } = job.attrs.data;
  await emailService.sendReminders(invoiceIds);
}, { concurrency: 4 });

await agenda.start();

// Cron-style repetition, stored in MongoDB
await agenda.every('0 9 * * 1', 'send-invoice-reminders');
// Or a one-off job 30 minutes from now
await agenda.schedule('in 30 minutes', 'send-invoice-reminders', { invoiceIds });
```

Agenda's model gives you three things for free: **retries** (failed jobs can be re-queued with `job.schedule()` on failure), **job history** (every run is recorded in the `agendaJobs` collection), and **exactly-once semantics across instances**. It also exposes `agenda.jobs()` queries so you can build a small admin UI to inspect and re-run jobs.

The costs are real: you need a MongoDB instance (or Atlas) just for scheduling, and the API has a steeper learning curve — concepts like `job.attrs`, unique jobs, and lock lifetimes take time to internalize. Throughput is also lower than in-memory schedulers for very high-frequency jobs, because every state change hits the database. Agenda is the right choice when correctness beats speed.

## Common Pitfalls When Scheduling Jobs in Node.js

**Running cron in every process.** PM2 cluster mode or multiple replicas will each fire the same schedule. If you use node-cron or Bree, pin scheduling to a single instance (`instances: 1` or a dedicated scheduler deployment); if you need horizontal scaling, move to Agenda's MongoDB lock or BullMQ's repeatable jobs.

**No timezone discipline.** Crontab entries are evaluated in the server's local timezone. Set `timezone` explicitly (node-cron supports it; Bree uses the process TZ) and store schedule definitions in UTC plus a display offset — otherwise DST transitions double-fire or skip jobs.

**Overlapping runs.** A cleanup job that takes 40 minutes with a `*/30 * * * *` schedule will overlap. node-cron v4 and Bree prevent overlap by default; Agenda's `concurrency` option controls how many parallel instances of a job are allowed. Always verify which behavior your library defaults to.

**Jobs that swallow errors.** An unhandled rejection inside a node-cron callback is invisible — the timer keeps running and the job silently dies. Wrap job bodies in try/catch and route failures to your logger; Bree and Agenda expose explicit error events for this. Our [Node.js logging comparison](../2026-08-10-nodejs-logging-libraries-winston-pino-bunyan/) shows how to wire failure logging properly.

**Crash mid-job.** In-memory schedulers lose the job state on restart. For anything with side effects (payments, emails, external API calls), either make the job idempotent or move it to Agenda so a crash re-queues it rather than silently dropping it.

**Scheduling vs queueing confusion.** If your workload is "many short tasks, processed by a pool of workers, with retries and delayed delivery," you likely want a job queue, not a scheduler. Schedulers fire on a calendar; queues process on demand. See our [Node.js job queue comparison](../2026-07-24-nodejs-job-queue-libraries-bullmq-beequeue-pgboss/) and the [C# scheduling landscape](../2026-07-24-csharp-job-scheduling-hangfire-quartznet-coravel/) for how other ecosystems split the same problem.

## FAQ

### What is the difference between node-cron, Bree, and Agenda?

node-cron is a minimal in-memory cron scheduler (zero dependencies). Bree adds worker-thread isolation and graceful shutdown but is still in-memory. Agenda persists every job in MongoDB, which enables retries, history, and exactly-once execution across multiple server instances. Choose by persistence needs: none → node-cron, isolation → Bree, durability → Agenda.

### Can node-cron run jobs on multiple server instances?

Not safely — every instance fires the schedule independently, so jobs run twice. Use Agenda (MongoDB lock) or BullMQ repeatable jobs for multi-instance deployments. For node-cron or Bree, run the scheduler in a single dedicated process.

### Does Bree require a database?

No. Bree is entirely in-memory and file-based: each job is a script, schedules are defined in the config, and no storage is needed. That makes it the simplest choice for single-process deployments that need worker-thread isolation.

### Is Agenda still maintained in 2026?

Yes — the last push was 2026-07-21, and it remains the most-starred Node.js scheduler at 9,692 stars. Development is steady rather than frantic: the core API has been stable for years, which is exactly what production teams want from a scheduler.

### Which scheduler is best for serverless functions?

For serverless, avoid long-running schedulers entirely — a 15-minute Lambda/Cloud Function timeout cannot host a persistent timer. Use the platform's native cron trigger (AWS EventBridge, Google Cloud Scheduler) that invokes your function, or run node-cron inside a long-lived container if you must.

### Can I use human-readable schedules like "every 2 hours"?

Yes — Bree supports `every: '2 hours'` syntax natively, and Agenda supports relative strings like `'in 30 minutes'` for one-off jobs. node-cron is strictly five-field cron syntax.

### How do I test scheduled jobs?

Abstract the job body into a plain async function and unit-test it directly; test the schedule expression separately. Agenda exposes `agenda.now('job-name')` to trigger jobs immediately in tests, and Bree lets you call the job script directly. Never sleep-wait in tests — inject a fake clock.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js Job Scheduling in 2026: node-cron vs Bree vs Agenda",
  "description": "Deep comparison of the three dominant Node.js job schedulers: node-cron, Bree, and Agenda, covering persistence models, worker isolation, multi-instance coordination, real code examples, and production pitfalls.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
