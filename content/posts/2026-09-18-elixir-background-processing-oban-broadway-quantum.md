---
title: "Oban vs Broadway vs Quantum in 2026: Which Elixir Background Processing Layer Should You Use?"
date: 2026-09-18
tags: ["elixir", "job-scheduling", "background-processing", "data-pipelines"]
draft: false
cover: "/img/screenshots/elixir-jobs-oban.jpg"
---

Elixir makes concurrency so cheap that teams quietly accumulate `Task.start/1` calls all over their codebase — until the first deploy kills 4,000 in-flight jobs mid-execution and nobody can say which emails went out. The BEAM gives you lightweight processes for free, but **durability, retries, and back-pressure are not free**, and those are exactly the three things that separate Elixir's background processing libraries.

In 2026 there are three serious choices: **Oban** (durable job processing backed by your database), **Broadway** (multi-stage data ingestion pipelines with back-pressure), and **Quantum** (in-memory cron scheduling). They overlap just enough to be confusing, and picking the wrong one means either an over-engineered dependency tree or silently lost work.

## TL;DR: Quick Verdict

**Need durable jobs — retries, uniqueness, job history, multi-node safety? Use Oban.** It stores jobs in PostgreSQL, SQLite, or MySQL and is the default choice for anything that must not be lost.

**Need a high-throughput ingestion pipeline from Kafka, SQS, RabbitMQ, or a filesystem? Use Broadway.** It is a data pipeline with batching, back-pressure, and per-stage concurrency — not a queue for user-triggered work.

**Need cron-style periodic execution in a single-node app with zero persistence? Use Quantum.** It is small, dependency-light, and executes scheduled callbacks in-process.

The honest answer for most production apps: **Oban for jobs, Broadway for streams, and Quantum only when you do not care about missed runs.**

## How the Three Compare

| Dimension | Oban | Broadway | Quantum |
|---|---|---|---|
| Primary role | durable background job processor | data ingestion / stream processing pipeline | in-memory cron scheduler |
| GitHub stars | 3,973 | 2,684 | 2,416 |
| Last upstream commit | 2026-09-17 | 2026-09-17 | 2026-09-16 |
| License | Apache-2.0 (Pro tier commercial) | Apache-2.0 | Apache-2.0 |
| Backing store | PostgreSQL, SQLite3, MySQL | producer-dependent (Kafka, SQS, RabbitMQ, files) | none, in-memory |
| Survives restart / deploy | yes, jobs resume from the queue | depends on producer offsets and acknowledgement | no, pending runs are lost |
| Automatic retries | yes, per-worker with backoff | producer/manual, messages are acknowledged per batch | no retries, the next cron tick is the retry |
| Uniqueness / dedupe | yes, unique job controls and cron dedupe across nodes | not applicable | not built in |
| Multi-node safety | yes, queue coordination through the database | yes, partition assignment across consumers | no, every node would run every job |
| Back-pressure | queue-level concurrency limits | first-class, built on GenStage | none needed |
| Batching | no | yes, `batch_size` + `batch_timeout` per batcher | no |
| Dashboard | Oban Web (separate package) | none | none |
| Cron support | yes, periodic jobs via plugin | no | yes, cron and `@daily`-style expressions |

The decisive row is **backing store**. Oban and Broadway keep state outside the BEAM; Quantum does not, and that one fact drives everything about how you deploy it.

## Decision Matrix: Pick by Situation

| Your situation | Pick | Why |
|---|---|---|
| Send emails, charge cards, call third-party APIs from a web request | Oban | Persisted, retried, and visible in a dashboard |
| Ingest 5,000 messages per second from Kafka with batching to S3 | Broadway | Back-pressure and batchers are native; jobs are not the model |
| Nightly cache warm-up in a single-node app | Quantum | Smallest possible dependency footprint |
| Periodic job that must run exactly once across six Kubernetes pods | Oban | Periodic jobs coordinate through the database |
| Multi-step ETL where each stage has different concurrency | Broadway | Per-processor and per-batcher concurrency settings |
| You want one library instead of three | Oban | Periodic jobs cover most cron use cases with durability |

## Oban: Durable Jobs Backed by Your Database

Oban's model is a job queue that lives in a database you already operate. Configuration is a queue list plus a repo, and a worker is a module with a `perform/1` callback:

```elixir
# In config/config.exs
config :my_app, Oban,
  repo: MyApp.Repo,
  queues: [mailers: 20]
```

```elixir
defmodule MyApp.MailerWorker do
  use Oban.Worker, queue: :mailers

  @impl Oban.Worker
  def perform(%Oban.Job{args: %{"email" => email} = _args}) do
    _ = Email.deliver(email)
    :ok
  end
end
```

Enqueueing is a single line from anywhere in your app — `MyApp.MailerWorker.new(%{"email" => email}) |> Oban.insert()`. What the library adds on top of a naive `Task` is the entire operational story: **automatic retries with configurable backoff**, **unique job controls** to collapse duplicate work, **periodic jobs** that deduplicate cron scheduling across nodes, and a plugin system for pruning completed jobs. The Oban Web package adds a dashboard for inspecting queues and retrying failures by hand.

The trade-offs are structural. Every job costs a database round trip, so Oban is the wrong tool for millions of tiny messages per hour — that is stream-processing territory. And because your jobs table grows, pruning is mandatory: configure the pruning plugin with an explicit retention window instead of letting succeeded jobs accumulate forever.

![Oban job processing for Elixir](/img/screenshots/elixir-jobs-oban.jpg "Oban is the durable job processing layer for Elixir applications")

## Broadway: Pipelines, Not Queues

Broadway is built on GenStage and models work as a producer → processors → batchers pipeline. If your problem is "consume a stream of messages with back-pressure and write them out in batches," reaching for a job queue is a category error — this is the library that exists for that shape:

```elixir
def deps do
  [
    {:broadway, "~> 1.0"}
  ]
end
```

```elixir
defmodule MyBroadway do
  use Broadway

  alias Broadway.Message

  def start_link(_opts) do
    Broadway.start_link(__MODULE__,
      name: __MODULE__,
      producer: [
        module: {BroadwaySQS.Producer, queue_url: "https://us-east-2.queue.amazonaws.com/100000000001/my_queue"}
      ],
      processors: [
        default: [concurrency: 50]
      ],
      batchers: [
        s3: [concurrency: 5, batch_size: 10, batch_timeout: 1000]
      ]
    )
  end

  def handle_message(_processor_name, message, _context) do
    message
  end
end
```

Three design properties matter here. **Back-pressure is native** — a slow processor slows the producer instead of exhausting memory. **Concurrency is per stage**, so you can run 50 lightweight transformations and only 5 expensive writes. **Batching is first class**, which is what makes Broadway the standard way to load data into S3, ClickHouse, or a warehouse without writing your own buffering logic.

Broadway is not durable in the way Oban is: message replay depends on the producer's acknowledgement model. For Kafka and SQS that is usually acceptable; for a payment flow it is not, which is why the common production pattern is Broadway for ingestion feeding Oban jobs for the business-critical steps.

## Quantum: Cron in a Dependency-Light Package

Quantum gives you cron expressions for Elixir callbacks with almost nothing else attached:

```elixir
defp deps do
  [
    {:quantum, "~> 3.0"}
  ]
end
```

```elixir
defmodule Acme.Scheduler do
  use Quantum, otp_app: :your_app
end
```

```elixir
config :acme, Acme.Scheduler,
  jobs: [
    # Every minute
    {"* * * * *",      {Heartbeat, :send, []}},
    # Every 15 minutes
    {"*/15 * * * *",   fn -> System.cmd("rm", ["/tmp/tmp_"]) end},
    # Runs on 18, 20, 22, 0, 2, 4, 6:
    {"0 18-6/2 * * *", fn -> :mnesia.backup('/var/backup/mnesia') end},
    # Runs every midnight:
    {"@daily",         {Backup, :backup, []}}
  ]
```

Note what is absent: no database, no queue, no retry policy, no execution history. Quantum schedules callbacks in the running node. That makes it perfect for a single-node admin app and dangerous the moment you scale horizontally or care about a run that happened while you were deploying — because the schedule lives in memory, a restart during a cron window means that window simply never happened.

## Production Pitfalls That Bite Elixir Teams

1. **Running Quantum on more than one node duplicates every job.** There is no built-in clustering. Either keep the scheduler on a single designated node or move periodic work to a library that coordinates through shared storage.
2. **In-memory schedules cannot catch up.** If the node is down at 03:00, the 03:00 job does not run late — it never runs. Only use Quantum where a missed tick is harmless.
3. **Unbounded queues hide back-pressure problems.** Oban lets you set queue concurrency, but an enqueue rate above worker throughput grows the table indefinitely. Watch queue latency, not just failure counts.
4. **Prune completed jobs deliberately.** Both Oban and any broker-backed pipeline accumulate state. Set a retention window and verify that pruning actually runs, because a silently disabled pruner is a slow-motion database incident.
5. **Partial batch failures need idempotency.** Broadway acknowledges messages per batch; a crash mid-batch replays the whole batch. Make downstream writes idempotent or you will double-insert.
6. **Worker arguments should be small.** Jobs are serialized into the queue, so pass an identifier and re-read the record rather than embedding a large payload that must be migrated whenever your schema changes.
7. **Do not mix supervision responsibilities.** A `Task.Supervisor` is for concurrent in-request work; it provides no durability. When a piece of work must survive a deploy, it belongs in a persisted queue, full stop.

## Why Elixir Apps Are Consolidating on One Background Layer

The pattern across mature Elixir codebases is convergence: one durable job layer, one streaming library, and almost no ad-hoc `Task.start/1` in the request path. The reason is operational rather than aesthetic — every additional async mechanism adds a failure mode that nobody has tooling for. A single queue with retries and a dashboard means a support question ("did that email go out?") has one place to look.

For teams already running Phoenix applications, adding a persisted job layer is incremental work rather than a rewrite, and it pairs naturally with the rest of the stack — see our [Elixir web framework comparison](../2026-08-12-elixir-web-frameworks-phoenix-plug-ash-comparison/) for the surrounding choices. If you are evaluating the same decision in other ecosystems, the trade-offs map almost one-to-one onto the [Go task queue libraries](../2026-07-03-go-task-queue-libraries-asynq-watermill-machinery-gocraft/) and the [Node.js job queue options](../2026-07-24-nodejs-job-queue-libraries-bullmq-beequeue-pgboss/) we compared earlier.

## FAQ

**Is Oban a replacement for Quantum?**
For most applications, yes. Oban's periodic jobs provide cron-like scheduling with the addition of durability, retries, and coordination across nodes. Quantum remains useful when you explicitly do not want a database dependency for scheduling.

**Does Broadway replace a job queue?**
No. Broadway is a data ingestion and processing pipeline with back-pressure and batching. It has no notion of a durable user-triggered job with retries, so pipelines and job queues complement rather than replace each other.

**Can Quantum run periodic jobs across multiple nodes safely?**
Not by itself. Quantum keeps schedules in memory per node, so every node would execute the same job. Multi-node cron requires external coordination or a database-backed scheduler such as Oban.

**How does Oban avoid duplicate jobs?**
It supports unique job controls that prevent duplicate work within a configurable period, and its periodic job plugin deduplicates cron scheduling across all connected nodes.

**Does Oban require PostgreSQL?**
No. It supports PostgreSQL, SQLite3, and MySQL as storage backends, all through Ecto. PostgreSQL remains the most common choice because it pairs with the rest of the Phoenix stack.

**What is the easiest migration path off `Task.start/1`?**
Wrap the existing logic in an Oban worker module, replace the `Task.start/1` call with an `Oban.insert/1` of that worker, and let the queue handle retries. Start with one queue and split later if throughput demands it.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Oban vs Broadway vs Quantum in 2026: Which Elixir Background Processing Layer Should You Use?",
  "description": "A 2026 comparison of Elixir background processing libraries Oban, Broadway and Quantum: durable job queues versus back-pressure pipelines versus in-memory cron, with code examples, a decision matrix and production pitfalls.",
  "datePublished": "2026-09-18",
  "dateModified": "2026-09-18",
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
