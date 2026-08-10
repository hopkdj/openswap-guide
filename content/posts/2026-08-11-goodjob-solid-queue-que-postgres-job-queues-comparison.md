---
title: "GoodJob vs Solid Queue vs Que in 2026: Postgres-Backed Job Queues for Rails"
date: "2026-08-11"
tags: ["ruby", "rails", "postgres", "background-jobs", "developer-tools"]
draft: false
cover: "/img/screenshots/goodjob-dashboard.png"
---

Redis has been the default home for Rails background jobs for a decade — but it is also one more service to run, monitor, back up, and pay for. Since Rails 8 shipped with Solid Queue as the default queue backend, the debate has flipped: **do you even need Redis anymore?** Three mature, Postgres-only job backends now cover everything from a solo developer's hobby app to multi-tenant production workloads: **GoodJob** (2,990 stars), **Solid Queue** (2,481 stars, maintained by the Rails core team), and **Que** (2,323 stars, the speed demon). All three eliminate Redis entirely by storing jobs in the same Postgres database you already run. This guide compares them with real configuration, real performance characteristics, and a clear recommendation.

## TL;DR / Quick Verdict

**Choose Solid Queue if** you're on Rails 8 and want the boring, well-supported default that the framework's maintainers test against. **Choose GoodJob if** you want to run jobs inside your existing app process (zero extra worker processes to deploy) with a beautiful built-in dashboard. **Choose Que if** you need maximum throughput with a minimal schema and are comfortable with raw SQL. For most teams in 2026: **Solid Queue for Rails 8 defaults, GoodJob for simplicity and visibility**.

## The Quick Comparison

| Dimension | GoodJob | Solid Queue | Que |
|---|---|---|---|
| License | MIT | MIT | MIT |
| GitHub stars / activity | 2,990⭐, updated 2026-08 | 2,481⭐, updated 2026-07 | 2,323⭐, updated 2026-01 |
| Maintainer | Ben Sheldon (community) | Rails core team | Community (que-rb) |
| Storage | Single `good_jobs` table | 6 tables (jobs + supporting) | Single `que_jobs` table |
| Locking mechanism | Advisory locks + `SKIP LOCKED` | `SKIP LOCKED` polling | Postgres advisory locks |
| Wake-up strategy | LISTEN/NOTIFY + polling | Polling (2s default) | LISTEN/NOTIFY + polling |
| Deployment model | In-process threads OR worker | Separate worker processes | Separate worker process |
| Built-in dashboard | Yes (good_job web UI) | Yes (Rails 8.1+ dashboard) | No (third-party: que-web) |
| Cron / recurring jobs | Yes (`cron` config) | Yes (recurring tasks) | Yes (job tags / scheduling) |
| Transactions integration | `discrete` execution option | `transactional` jobs | Runs jobs in transactions by default |
| Default of | — | **Rails 8** | — |

## The Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Fresh Rails 8 app, want framework default | Solid Queue | Ships in the default stack, tested by Rails CI |
| Don't want to deploy a separate worker process | GoodJob | Runs on threads inside Puma/your app |
| Need a job dashboard your team will actually open | GoodJob | Best-in-class web UI, includes cron management |
| Maximum job throughput on one Postgres instance | Que | Advisory locks + bulk insert = lowest overhead |
| Jobs must commit atomically with DB changes | Que | Jobs execute inside the enqueuing transaction |
| Existing Sidekiq app, want to drop Redis | Solid Queue | Closest API and semantics to Sidekiq |
| Multi-tenant isolation with per-tenant queues | GoodJob | Per-queue concurrency and routing controls |

## GoodJob — Jobs Inside Your App Process

GoodJob's design philosophy is "distributed by default": by default it runs jobs **inside your existing Rails process** on a thread pool, which means a Rails app deployed to a single server needs zero additional infrastructure. Since version 3, it can also run in a forking worker mode, and it uses Postgres advisory locks to ensure each job runs exactly once even when multiple processes or servers are competing.

```ruby
# Gemfile
gem "good_job"

# config/initializers/good_job.rb — in-process execution
Rails.application.configure do
  config.active_job.queue_adapter = :good_job
  config.good_job.execution_mode = :async
  config.good_job.max_threads = 5
  config.good_job.enable_cron = true
  config.good_job.cron = {
    refresh_feed: {
      cron: "0 */4 * * *",
      class: "RefreshFeedJob",
      queue: "default"
    }
  }
end

# Or run as a standalone worker:
#   bundle exec good_job start

# A plain Active Job — nothing GoodJob-specific:
class RefreshFeedJob < ApplicationJob
  queue_as :default

  def perform(feed_id)
    Feed.find(feed_id).refresh!
  end
end
```

The dashboard (shown in the cover image) is the strongest reason teams pick GoodJob: it shows live job execution, per-queue concurrency, failed jobs with retry buttons, and cron schedules in a clean web UI. GoodJob also supports **batches** (track a group of jobs and run a callback when all finish) and **discrete execution** — a mode where the database transaction is committed before the job runs, trading atomicity for smaller lock footprints. The trade-off: in-process execution shares memory with your web app, so a memory-hungry job can pressure your web process; you'll want `max_threads` tuned carefully.

## Solid Queue — The Rails 8 Default

Solid Queue is the background-job half of the "Solid" trilogy (Solid Cache, Solid Queue, Solid Cable) that replaces Redis-based components in the Rails default stack. Because it is maintained by the Rails core team, it gets exercised in Rails' own CI and receives updates in lockstep with the framework — the strongest stability argument of the three.

```ruby
# Gemfile
gem "solid_queue"

# config/environments/production.rb
config.active_job.queue_adapter = :solid_queue

# config/queue.yml — per-queue concurrency
default: 3
mailers: 2
low_priority: 1

# Run the supervisor, which manages dispatchers + workers:
#   bin/rails solid_queue:start
# In production you typically run it as a separate service.

# Recurring tasks live in config/recurring.yml:
production:
  period: [30s, 60s, 120s]
  class: ProcessAlertsJob
```

Solid Queue's architecture separates **dispatchers** (which pull scheduled jobs into the ready queue) from **workers** (which execute them), and it polls with `SKIP LOCKED` on a 2-second interval by default. Since version 1.x it supports **transactional jobs**: a job enqueued inside an ActiveRecord transaction only becomes visible to workers if that transaction commits — the same semantics Que gives you by default. The dashboard arrived in Rails 8.1, so you get operational visibility without a third-party gem. The trade-off: its 6-table schema is more moving parts than the single-table designs, and separate worker processes mean one more deployment unit than GoodJob's in-process mode.

## Que — Advisory Locks and Raw Speed

Que predates the Postgres-backend wave and remains the performance leader. It stores every job in a single `que_jobs` table and uses **Postgres advisory locks** so that each job is claimed by exactly one worker without any polling races, plus LISTEN/NOTIFY for instant wake-ups when a job is enqueued. The result is the lowest latency and highest throughput of the three for the same database instance.

```ruby
# Gemfile
gem "que"

# Install the schema (creates que_jobs + support tables):
#   bin/rails generate que:install

# config/initializers/que.rb
Que.connection_mode = :transaction
Que.mode = :async          # run in-process
# Or run a dedicated worker: bundle exec que

# Jobs are plain Ruby objects, not Active Job classes:
class RefreshFeedJob < Que::Job
  # The run method receives the arguments
  def run(feed_id)
    Feed.find(feed_id).refresh!
  end
end

# Enqueue from anywhere — inside a transaction by default
ActiveRecord::Base.transaction do
  RefreshFeedJob.enqueue(feed_id: 42)
  # If this transaction rolls back, the job is never visible
end
```

Because Que executes jobs **inside the same transaction** as the code that enqueued them, you get exactly-once semantics for free in the common case — a job never runs if its triggering data change was rolled back. Que also supports bulk insertion (`Que.execute` with array arguments), job priorities, tags, and per-job scheduling. The trade-offs are real: there is no first-party dashboard (community options like `que-web` and `que-lite` exist), and you'll write a bit more SQL-flavored Ruby than with Active Job wrappers — though Que fully supports Active Job as well, so you can use either style.

## Migration and Coexistence Strategies

Moving off Redis-backed Sidekiq is the most common reason teams land on this page. The migration path is smoother than you'd expect: **all three backends implement Active Job**, so if your app enqueues through `ApplicationJob`, the job classes themselves barely change — you swap the adapter, redeploy, and drain the old queue before switching. The practical recipe:

1. **Freeze deploys**: pick a low-traffic window, enable maintenance mode if you have one.
2. **Stop enqueuing to Sidekiq**: switch `queue_adapter` to your new backend and deploy — new jobs go to Postgres.
3. **Drain the Redis queue**: let Sidekiq workers finish remaining jobs (watch `Sidekiq::Queue` sizes via its dashboard), then stop the Sidekiq processes.
4. **Run both workers briefly** (weeks, not hours, if you have long-running jobs) so nothing is lost.
5. **Decommission Redis** for the job path — you can often drop the Redis instance entirely if it was only serving jobs.

One thing to verify before migrating: **job serialization**. Sidekiq stores arguments as JSON with symbol-keyed hashes; Active Job adapters all round-trip through `GlobalID`, but if you ever enqueued raw arguments bypassing Active Job, you'll need to rework those call sites. Also check for gems that hook into Sidekiq middleware (retry instrumentation, scheduled set manipulation) — their features map differently: GoodJob covers most with built-in cron/batches, Solid Queue with recurring tasks, and Que with tags and scheduling. For the broader picture of where these tools sit in the ecosystem, our [Ruby background job processors comparison](../2026-07-28-ruby-background-job-processors-sidekiq-shoryuken-faktory-sucker-punch-comparison/) covers the Redis-based alternatives, and our [Node.js job scheduling guide](../2026-08-10-nodejs-job-scheduling-libraries-node-cron-bree-agenda/) shows how the same design space looks outside Ruby. If you're evaluating queue infrastructure rather than libraries, our [message queue servers roundup](../2026-05-17-self-hosted-message-queue-servers-nsq-beanstalkd-artemis-guide/) compares NSQ, Beanstalkd, and ActiveMQ Artemis.

## Common Pitfalls and Performance Traps

- **Postgres connection pool starvation**: every worker thread/process needs a database connection. With Puma's default pool of 5, running GoodJob in-process with `max_threads: 5` means 10 connections just for the default pool — raise `pool` in `database.yml` proportionally or you'll see `ActiveRecord::ConnectionTimeoutError` under load.
- **The 2-second polling tax**: Solid Queue's dispatcher polls every 2 seconds by default. For latency-sensitive queues (password resets, payments), that's fine — but don't set `poll_interval` too low or you'll burn CPU and Postgres cycles for nothing.
- **Deadlock from long transactions**: Que runs jobs inside transactions — a job that takes minutes holds locks that long. Keep DB-touching jobs short, and consider `Que.connection_mode = :transaction` only for jobs that must be atomic.
- **`SKIP LOCKED` needs Postgres 9.5+**: all three require it (or advisory locks). Ancient Postgres versions will fail at runtime, not install time.
- **In-process memory creep**: GoodJob's async mode shares the app process. A job that loads a 500 MB CSV into memory takes that memory from your web server. Use forking worker mode or a separate service for heavy jobs.
- **Forgetting the maintenance task**: all three use Postgres sequences/table growth for jobs; Solid Queue and Que clean up completed jobs automatically, but verify your retention settings — an app that enqueues millions of short jobs will grow `good_jobs` or `que_jobs` fast if pruning is disabled.
- **Timezone traps in cron/recurring configs**: GoodJob cron and Solid Queue recurring tasks use your app's configured timezone. Schedule a job that logs its `Time.current` on day one — timezone drift is the #1 "silent" failure in recurring job setups.

## FAQ

**Do I need Redis at all if I use these?** No — that's the entire point. GoodJob, Solid Queue, and Que store jobs in Postgres and use Postgres features (advisory locks, LISTEN/NOTIFY, SKIP LOCKED) for coordination. If Redis was only serving your job queue, you can decommission it. You may still want Redis for caching or rate limiting, which is a separate concern.

**Which is the default for Rails 8?** Solid Queue. Rails 8's default stack uses Solid Queue for background jobs, Solid Cache for caching, and Solid Cable for Action Cable pub/sub — all Postgres-backed, so a default Rails 8 app needs no separate Redis installation at all.

**Can I run GoodJob and Solid Queue in the same app?** Technically yes — Active Job adapters are per-environment, so you can run different adapters in different environments (e.g., GoodJob in development for in-process simplicity, Solid Queue in production). Running two queue backends in the same environment is possible but doubles your operational surface; pick one.

**Which one has the best job dashboard?** GoodJob ships the most polished dashboard with live execution views, retry controls, and cron management. Solid Queue's dashboard (Rails 8.1+) is solid and integrated with the Rails engine ecosystem. Que has no first-party dashboard — use `que-web` or `que-lite` if you need one.

**Is Que still maintained?** Yes, though it moves slower than the others (last push January 2026). It is stable, complete, and widely used in production; the slower cadence reflects maturity rather than abandonment. If you need the newest Rails integration features, Solid Queue or GoodJob are more actively developed.

**How do these compare to Sidekiq for throughput?** Sidekiq (Redis-backed) generally has the edge on raw throughput at very large scale because Redis is a dedicated in-memory store. In practice, for workloads up to millions of jobs per day, Postgres-backed queues are plenty — and they remove a whole class of Redis-specific failure modes (memory eviction, RDB/AOF restore gaps, network hops).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GoodJob vs Solid Queue vs Que in 2026: Postgres-Backed Job Queues for Rails",
  "description": "Deep comparison of GoodJob, Solid Queue, and Que — the Postgres-backed background job queues for Rails that replace Redis. Real configs, performance characteristics, and migration strategies.",
  "datePublished": "2026-08-11",
  "dateModified": "2026-08-11",
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
