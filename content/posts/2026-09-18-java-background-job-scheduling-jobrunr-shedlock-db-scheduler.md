---
title: "JobRunr vs ShedLock vs db-scheduler in 2026: How to Run Background Jobs in Java Without Duplicates"
date: 2026-09-18
tags: ["java", "job-scheduling", "spring-boot", "background-processing"]
draft: false
cover: "/img/screenshots/java-scheduling-jobrunr.jpg"
---

You scale your Spring Boot service from one instance to four, and suddenly every `@Scheduled` method fires four times: four invoices emailed, four reports generated, four webhooks delivered. The instinct is to reach for a distributed lock — but **ShedLock, JobRunr, and db-scheduler solve three genuinely different problems**, and treating them as interchangeable is why teams end up with duplicated side effects or silently skipped jobs after a restart.

This guide breaks down what each library actually guarantees in 2026, with real configuration pulled from their upstream repositories, a decision matrix, and the operational traps that show up only in production.

## TL;DR: Quick Verdict

**You already have `@Scheduled` methods and just need them to run once per cluster: use ShedLock.** It is a lock, not a scheduler — install it, annotate your methods, done.

**You want a real background job platform — enqueued from request handlers, persisted, retried, observable in a dashboard: use JobRunr.**

**You want persistent, cluster-safe recurring and one-time tasks with transactionally staged execution, driven by your database: use db-scheduler.**

If you need a message-queue-grade throughput of tens of thousands of jobs per second, none of these are the right tool — use a broker instead.

## The Three Libraries Solve Different Problems

| Dimension | JobRunr | ShedLock | db-scheduler |
|---|---|---|---|
| Primary role | background job platform | distributed lock for scheduled tasks | persistent job scheduler |
| Latest version (2026-09) | 8.x line | 7.10.1 | 16.11.0 |
| GitHub stars | 3,088 | 4,220 | 1,650 |
| Last upstream commit | 2026-09-18 | 2026-09-16 | 2026-09-14 |
| License | LGPLv3 (Pro tier commercial) | Apache-2.0 | Apache-2.0 |
| Persists jobs to disk/DB | yes (RDBMS or MongoDB) | no, only lock rows | yes (RDBMS) |
| Cluster-safe execution | yes, background job servers coordinate via storage | yes, one lock holder per task | yes, one execution per cluster |
| Fire-and-forget from request handler | yes (`BackgroundJob.enqueue`) | no | yes (one-time tasks) |
| Delayed / scheduled one-off jobs | yes | no | yes |
| Recurring with cron | yes | no (uses Spring's cron) | yes (v5.3+) |
| Automatic retries | yes, with backoff | none | yes, with configurable backoff |
| Built-in dashboard | yes | no | no (third-party UIs exist) |
| Recovers missed runs after downtime | yes, persisted state | no, skipped runs are lost | yes, tasks stay in the table |
| Transactional staging with app data | no | not applicable | yes |

The important line in that table is **"recovers missed runs after downtime."** ShedLock is a coordination primitive; JobRunr and db-scheduler are stores of record. That single distinction decides most architecture choices.

## Decision Matrix: Pick by Situation

| Your situation | Pick | Why |
|---|---|---|
| Four replicas of a service with one `@Scheduled` report job | ShedLock | Minimal change, no new tables for job state |
| Send welcome emails, generate PDFs on user request | JobRunr | Enqueue from the request path, retries, dashboard visibility |
| Nightly billing that must run exactly once and must not be lost | db-scheduler | Tasks survive restarts and cluster scaling |
| Background work must commit atomically with business data | db-scheduler | Transactionally staged jobs (job runs iff the transaction commits) |
| You want human-visible job history and manual retry | JobRunr | Dashboard ships with the library |
| You only have a database, no message broker, and no Redis | all three | Each is DB-backed; no extra infrastructure |

## ShedLock: The Lock You Add to Tasks You Already Have

ShedLock deliberately refuses to be a scheduler. You keep Spring's `@Scheduled`, and ShedLock guarantees that only one instance holds the lock for a given task name at a time. There is no job queue, no retry, and no history — which is exactly why it is a 20-minute change instead of a migration.

First declare a lock provider backed by a table:

```java
import net.javacrumbs.shedlock.provider.jdbctemplate.JdbcTemplateLockProvider;

@Bean
public LockProvider lockProvider(DataSource dataSource) {
    return new JdbcTemplateLockProvider(
        JdbcTemplateLockProvider.Configuration.builder()
        .withJdbcTemplate(new JdbcTemplate(dataSource))
        .usingDbTime() // Works on Postgres, MySQL, MariaDb, MS SQL, Oracle, DB2, HSQL and H2
        .build()
    );
}
```

`usingDbTime()` matters more than it looks: it takes the clock from the database server, so app-server clock skew cannot hand the same lock to two nodes. Then annotate the task:

```java
@Scheduled(cron = "0 0 2 * * *")
@SchedulerLock(name = "nightlyReport", lockAtMostFor = "14m", lockAtLeastFor = "1m")
public void nightlyReport() {
    LockAssert.assertLocked();
    // generate and email the report
}
```

`LockAssert.assertLocked()` is the cheap insurance policy that turns a misconfiguration into a loud failure instead of silent double-sends. `lockAtMostFor` should exceed your worst-case runtime, and `lockAtLeastFor` suppresses clock-drift double execution on very fast tasks.

**Where ShedLock stops:** if every instance is down at 02:00, nothing runs and nothing records the miss. There is no retry, no queue, no dashboard. That is the correct design for a lock — just do not mistake it for a job platform.

## JobRunr: A Background Job Platform in One Dependency

JobRunr turns any method call into a persisted job. The API is lambda-based, which means no worker classes, no serialization boilerplate, and no interfaces to implement:

```java
BackgroundJob.enqueue(() -> System.out.println("This is all you need for distributed jobs!"));
```

It supports fire-and-forget, delayed, scheduled, and recurring jobs, and it writes state to either a relational database (Postgres, MariaDB/MySQL, Oracle, SQL Server, DB2, SQLite) or MongoDB. Adding it to a Spring Boot application is mostly configuration:

```properties
# the job-scheduler is enabled by default
# the background-job-server and dashboard are disabled by default
jobrunr.job-scheduler.enabled=true
jobrunr.background-job-server.enabled=true
jobrunr.dashboard.enabled=true
```

What you get for that: **automatic retries**, **clustered execution** where background job servers coordinate through the shared storage so a job runs once, and a dashboard for inspecting succeeded, failed, and scheduled jobs. For teams whose current "observability" is grepping logs for a stack trace, the dashboard alone usually justifies the adoption.

**Where JobRunr hurts:** it is LGPLv3, which some organizations review before embedding (a commercial Pro edition exists with additional features), and its job tables grow continuously — you must configure retention and delete succeeded jobs on a schedule, or your database will quietly bloat by millions of rows.

## db-scheduler: Persistence and Exactly-Once by Default

db-scheduler stores every task in your own database and treats that table as the source of truth. A recurring task is declared in plain Java and registered on a scheduler backed by your `DataSource`:

```java
RecurringTask<Void> hourlyTask = Tasks.recurring("my-hourly-task", FixedDelay.ofHours(1))
        .execute((inst, ctx) -> {
            System.out.println("Executed!");
        });

final Scheduler scheduler = Scheduler
        .create(dataSource)
        .startTasks(hourlyTask)
        .build();

// hourlyTask is automatically scheduled on startup if not already started (i.e. exists in the db)
scheduler.start();
```

Three properties make it attractive for anything that touches money or state:

1. **Missed executions are recovered.** If the whole cluster is down over the weekend, tasks are still in the table and get picked up when an instance returns.
2. **Transactionally staged jobs.** With the Spring Boot starter you can register a job inside the same transaction as your business write, so the job runs *if and only if* that transaction commits — the reliable pattern for order confirmation emails and outbound syncs.
3. **Long-running jobs survive restarts.** The documented examples persist progress on shutdown so a nightly batch resumes instead of restarting from zero.

The cost is a smaller ecosystem (1,650 stars), a polling loop you should tune deliberately, and a scheduler that is intentionally lower-level than JobRunr — no dashboard, more wiring.

## Production Pitfalls That Actually Bite

1. **Sizing `lockAtMostFor` wrong is the classic ShedLock outage.** Too short and a slow run overlaps with the next trigger; too long and a crashed node blocks the task for hours. Set it from measured p95 runtime, not from optimism.
2. **Do not put a scheduler on your main connection pool.** Scheduler threads and job workers hold connections while your request path is also competing for them. Give them a dedicated pool — see our [Java connection pool comparison](../2026-08-31-java-connection-pools-hikaricp-commons-dbcp-tomcat-jdbc/).
3. **Prune job history.** JobRunr and db-scheduler both accumulate rows. Set retention windows from day one; retrofitting cleanup onto a 40-million-row job table is painful.
4. **Polling interval is a latency-versus-load dial.** A one-second poll against a busy database is measurable overhead; a one-minute poll means jobs start up to a minute late. Decide which one your SLA needs.
5. **Never let the dashboard be public.** JobRunr's UI exposes payloads and lets operators requeue jobs. Put it behind your existing auth proxy.
6. **Retries need idempotency.** All the retry logic in the world does not help if the job charges a card twice. Make handlers idempotent before you celebrate the retry feature.
7. **Timezone drift in cron expressions.** Confirm whether your scheduler evaluates cron in UTC or server-local time before a DST weekend surprises your nightly job.

## Why Java Teams Run Jobs From the Database Instead of a Broker

Adding Kafka or RabbitMQ to run a nightly report is a large architectural bet for a small problem: another cluster to operate, another failure mode to page someone about, and a new consistency gap between your business transaction and the enqueued message. Database-backed schedulers collapse that gap — the job row commits with your data, and the scheduler is the same system you already back up and monitor.

The trade-off is throughput. If you are dispatching tens of thousands of jobs per second, a broker is the correct answer. For the far more common case — hundreds to thousands of jobs per hour, where correctness matters more than raw dispatch rate — a table, a lock, and a retry policy is the simpler system that keeps working at 3 a.m. For scheduling patterns in other stacks, see our [cross-language scheduler comparison](../2026-06-19-self-hosted-job-scheduling-libraries-apscheduler-robfig-cron-gocron-quartz/) and the [.NET equivalent with Hangfire, Quartz.NET and Coravel](../2026-07-24-csharp-job-scheduling-hangfire-quartznet-coravel/).

## FAQ

**Is ShedLock a replacement for a job scheduler?**
No. ShedLock is a distributed lock for methods that a scheduler already invokes, typically Spring's `@Scheduled`. It does not persist jobs, retry failures, or recover runs missed while your service was down.

**Which one handles multiple instances of the same service best?**
All three are cluster-safe, but in different ways. ShedLock guarantees one lock holder per task name. JobRunr coordinates background job servers through shared storage. db-scheduler keeps a single execution per cluster through its own database-backed locking.

**Does JobRunr require a message broker?**
No. JobRunr persists jobs to a relational database or MongoDB, so a broker is optional. That is a common reason teams pick it over queue-based job systems.

**How do db-scheduler jobs survive a full cluster restart?**
Tasks live in a database table, so an instance that starts later finds pending and recurring jobs still there and executes according to their schedule. Nothing is lost while the cluster is offline.

**Can I use ShedLock with Quartz instead of Spring's scheduler?**
Yes. ShedLock ships integrations for Quartz, Spring, Micronaut, and other schedulers; the lock provider and the annotation stay the same, only the integration module changes.

**What license should I watch for?**
JobRunr's community edition is LGPLv3 with a commercial Pro edition on top, while ShedLock and db-scheduler are Apache-2.0. Check your organization's policy on LGPL dependencies before embedding JobRunr in a distributed binary.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JobRunr vs ShedLock vs db-scheduler in 2026: How to Run Background Jobs in Java Without Duplicates",
  "description": "A practical 2026 comparison of JobRunr, ShedLock and db-scheduler for Java and Spring Boot: distributed locking versus persistent job scheduling, with real configuration examples, a decision matrix and production pitfalls.",
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
