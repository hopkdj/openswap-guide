---
title: "PHP Job Queues in 2026: Laravel Horizon vs Symfony Messenger vs Enqueue — Which One Should You Actually Use?"
date: "2026-09-20"
tags: ["php", "queues", "background-jobs", "laravel", "symfony", "enqueue", "self-hosted"]
draft: false
cover: "/img/screenshots/laravel-horizon-dashboard.jpg"
---

Your queue works fine until the day a job silently fails three thousand times in a row and nobody notices, because your only monitoring is a `jobs` table with a growing count. The three real options in the PHP ecosystem take fundamentally different positions: Laravel Horizon bets you already chose Redis and Laravel, Symfony Messenger bets you want a framework-agnostic message bus with pluggable transports, and Enqueue bets you want to talk to seven different brokers through one interface.

Here is the honest comparison, with configuration pulled from each project's own repository — including the dashboard that saved more than one on-call engineer.

![Laravel Horizon dashboard showing queue throughput and job metrics](/img/screenshots/laravel-horizon-dashboard.jpg "Laravel Horizon dashboard — official screenshot from laravel.com")

## TL;DR: Quick Verdict

- **You run Laravel on Redis and want a dashboard today → Laravel Horizon.** 4,173 stars, code-driven supervisor configuration, a real metrics dashboard, and `php artisan horizon` as the only command you need to remember.
- **You want a message bus that works in any PHP application, Symfony or not → Symfony Messenger.** 1,111 stars. Transports are selected by DSN, routing is configuration, retries and failure transport are built in, and the same component runs standalone in a plain PHP project.
- **You need to speak to RabbitMQ, Kafka, SQS, STOMP, Redis, MongoDB, or the filesystem through one API → Enqueue.** 2,220 stars, MIT-licensed, with the `Interop\Queue` abstraction at its core and first-class integrations for Symfony, Laravel, Magento, and Yii.

If you want one-line advice: **Laravel app → Horizon. Anything else → Symfony Messenger. Multi-broker integration work → Enqueue.**

## The Three Contenders at a Glance

| Dimension | Laravel Horizon | Symfony Messenger | Enqueue |
|---|---|---|---|
| GitHub stars | **4,173** | 1,111 | 2,220 |
| License | MIT | MIT | MIT |
| Last repo activity | 2026-09-15 | 2026-09-16 | 2026-08-30 |
| Framework requirement | Laravel | None (Symfony bundle optional) | None (bundles for Symfony/Laravel/Magento/Yii) |
| Broker support | Redis only | AMQP, Redis, Doctrine, SQS, Beanstalkd and custom | AMQP, STOMP, Redis, Kafka, SQS/SNS, DBAL, MongoDB, Gearman, filesystem |
| Configuration style | PHP config file, code-driven supervisors | YAML/XML/PHP container config, DSN-based transports | PHP arrays, DSN parser, framework bundles |
| Monitoring UI | **Yes — built-in dashboard** | CLI commands only (third-party UIs exist) | Separate monitoring app |
| Retry handling | Automatic + failed job table | Retry with backoff, failure transport | Delayed retry strategies per message |
| Clustering / scaling | Auto-balanced supervisors | Multiple consumers, transport-dependent | Consumption extension, per-queue scaling |

Star counts and dates come from GitHub at publish time — confirm with `gh repo view laravel/horizon --json stargazerCount,pushedAt` before you standardize on blog advice.

## Decision Matrix: Which One for Your Use Case

| Your situation | Pick | Why |
|---|---|---|
| Laravel app, Redis present, need visibility tomorrow | **Horizon** | Install, run one command, get per-queue metrics and failed job retries |
| Mixed PHP codebases, some Laravel some plain PHP | **Symfony Messenger** | The component works without the full framework |
| Migrating from Beanstalkd to RabbitMQ without rewriting job code | **Enqueue** | Transport swap is configuration; job code talks to the interop layer |
| Need Kafka or Amazon SQS as a transport | **Enqueue** | Broadest broker matrix of the three |
| Want retry backoff and a failure transport without extra packages | **Symfony Messenger** | Built-in retry strategy plus a dedicated failure transport for inspection |
| Multi-tenant queues with distinct process counts per environment | **Horizon** | `environments` block in `config/horizon.php` declares supervisors per environment |
| Symfony or Magento app that needs async events and commands | **Enqueue** | Symfony bundle ships producers, processors, async events and async commands |

## Laravel Horizon: Redis Queues With a Dashboard That Earns Its Keep

Horizon is deliberately narrow: it is a **dashboard and code-driven configuration for Laravel-powered Redis queues**. If your queues are not Redis, stop here. If they are, this is the fastest path from "jobs are running" to "I can prove jobs are running."

Installation is the standard Laravel package flow:

```bash
composer require laravel/horizon
php artisan horizon:install
php artisan horizon
```

The interesting part is `config/horizon.php`, where supervisors are declared per environment rather than in shell scripts. This is the actual structure shipped in the repository:

```php
'environments' => [
    'production' => [
        'supervisor-1' => [
            'maxProcesses' => 10,
            'balanceMaxShift' => 1,
            'balanceCooldown' => 3,
        ],
    ],

    'local' => [
        'supervisor-1' => [
            'maxProcesses' => 3,
        ],
    ],
],
```

Read that `production` block carefully, because it contains the two settings that most teams get wrong. `maxProcesses` is your concurrency ceiling — set it by your database's connection budget, not your server's CPU count. `balanceMaxShift` and `balanceCooldown` control how aggressively Horizon rebalances processes between queues; a `balanceMaxShift` that is too high turns a traffic spike into a fork storm.

Horizon's other underrated feature is the **failed job handling**: retries, metrics, and a searchable failed-job table in the same UI. The dashboard above is not decoration — it is the reason teams discover a poisoned job in minutes instead of at the end of the month.

**Choose Horizon if** you are already on Laravel plus Redis. **Do not choose it if** you might migrate brokers later, or if you need Kafka, SQS, or STOMP — Horizon will not follow you.

## Symfony Messenger: A Message Bus That Does Not Need the Framework

Symfony Messenger is the most portable of the three. It helps applications "send and receive messages to/from other applications or via message queues," and it does that through two abstractions: **transports** (where messages go) and a **bus** (what receives them). Neither requires the full Symfony framework.

Unix is the conventional local development transport, and it is a good illustration of the DSN-driven design — the same config picks up AMQP, Redis, Doctrine, or SQS in production:

```yaml
# config/packages/messenger.yaml
framework:
    messenger:
        transports:
            async: "%env(MESSENGER_TRANSPORT_DSN)%"

            # or expanded to configure more options
            #async:
            #    dsn: "%env(MESSENGER_TRANSPORT_DSN)%"
            #    options: []
```

Routing decides which messages travel asynchronously, which is where Messenger earns its keep in a large codebase — you can make one message class async without touching the code that dispatches it:

```yaml
# config/packages/messenger.yaml
framework:
    messenger:
        transports:
            async: "%env(MESSENGER_TRANSPORT_DSN)%"

        routing:
            # async is whatever name you gave your transport above
            'App\Message\SmsNotification': async
```

Consumers run as long-lived processes:

```bash
php bin/console messenger:consume async --time-limit=3600 --memory-limit=256M
```

Those two flags matter more than they look. Long-running PHP workers leak memory, and a `--memory-limit` guard means the supervisor restarts a worker before the kernel does it for you. Pair it with a process supervisor — systemd, Supervisor, or your container orchestrator — because `messenger:consume` exiting cleanly is the normal case, not a failure.

Messenger also ships a **failure transport**: failed messages are serialized into a dedicated queue rather than vanishing, and `messenger:failed:show` / `messenger:failed:retry` let you inspect and replay them. That single feature is often the difference between debugging an incident in ten minutes and re-running a batch job by hand.

**Choose Symfony Messenger if** portability and explicit routing matter. **Do not choose it if** you wanted a ready-made dashboard — you are building your own observability here.

## Enqueue: One API, Nine Brokers

Enqueue takes the opposite approach to Horizon: instead of one broker done extremely well, it abstracts the broker entirely. Its transport layer implements the `Interop\Queue` message service interface, inspired by JMS, and supports AMQP and STOMP protocols plus dedicated drivers for Redis, Kafka, SQS/SNS, DBAL, MongoDB, Gearman, GPS, and even the filesystem.

Installation is per-broker, which keeps dependencies honest:

```bash
composer require enqueue/amqp-ext   # or enqueue/amqp-bunny or enqueue/amqp-lib
composer require enqueue/fs
```

Sending a message through a connection factory looks like this:

```php
<?php
use Interop\Queue\ConnectionFactory;

/** @var ConnectionFactory $connectionFactory **/
$context = $connectionFactory->createContext();

$destination = $context->createQueue('foo');

$message = $context->createMessage('Hello world!');

$context->createProducer()->send($destination, $message);
```

And consuming, with manual acknowledgement so a crashed worker does not silently lose the message:

```php
<?php
use Interop\Queue\ConnectionFactory;

$context = $connectionFactory->createContext();
$destination = $context->createQueue('foo');
$consumer = $context->createConsumer($destination);

$message = $consumer->receive();

// process a message

$consumer->acknowledge($message);
// $consumer->reject($message);
```

Above that low-level layer sits the **consumption layer**, whose `QueueConsumer` binds message processors to queues and runs until interrupted — the piece you actually wire into a long-running worker process. For Symfony applications the `enqueue/enqueue-bundle` adds a quick tour, config reference, and CLI commands so you configure transports in YAML rather than PHP arrays; Laravel, Magento and Yii each have their own integration.

The trade-off is explicit: **Enqueue asks you to think in transports and processors**, and its ecosystem is a family of packages rather than one monolith. In exchange, switching from RabbitMQ to Kafka does not mean rewriting your job classes.

**Choose Enqueue if** you have real integration requirements across several brokers or several frameworks. **Do not choose it if** you want the shortest possible path to a working queue in a single Laravel application.

## Running Queues in Production

The library choice is the easy part. These are the operational decisions that determine whether your queue survives a traffic spike.

**Supervise your workers, always.** `php artisan horizon` and `messenger:consume` are long-lived processes. Under systemd they should be `Restart=always` with a memory limit; in Kubernetes, a failing readiness probe is the wrong signal for a worker — use a liveness check that restarts on memory growth instead.

**Separate queues by cost, not by name.** A queue holding 30-second report exports and a queue holding 20-millisecond notifications should not share a worker pool. Horizon expresses this with multiple supervisors; Symfony Messenger expresses it with multiple transports; Enqueue with multiple processors.

**Make failures visible.** Horizon gives you this out of the box. Symfony Messenger requires you to monitor the failure transport. Enqueue requires either its separate monitoring application or your own instrumentation. Whichever you use, alert on queue depth growth rate, not depth — a queue that is consistently deep but stable is fine; a queue that doubles every ten minutes is an incident.

**Watch the database boundary.** Most jobs write to the same database your users read from. If your PHP application layer is ORM-heavy, the [PHP ORM comparison](../2026-07-06-php-orm-libraries-laravel-eloquent-doctrine-propel/) is worth reading before you let workers hammer the same connection pool as web requests. If your routing conventions are still fluid, the [PHP routing libraries comparison](../2026-07-28-php-routing-libraries-fastroute-slim-symfony-routing-league-route-comparison/) covers the request side of the same architecture. And if you are comparing queue designs across ecosystems, our [Postgres-backed job queue comparison](../2026-08-11-goodjob-solid-queue-que-postgres-job-queues-comparison/) shows what the Ruby ecosystem traded away for durable queues.

**Test your retry path deliberately.** Kill a worker mid-job and verify the message is redelivered. Send a job that always throws and verify it lands in the failed queue instead of looping forever.

## Common Pitfalls and Migration Notes

**Horizon locks you to Redis.** There is no SQS or Kafka driver. Teams that adopt Horizon and later migrate brokers rewrite the queue layer, not just the configuration.

**Messenger's default transport is not durable in development.** The `sync` transport executes messages inline; the `in-memory` transport loses them on restart. Anything you call asynchronous in production must be routed to a real transport, and that mismatch has shipped broken features to production many times.

**Enqueue's ecosystem is a family, not a package.** Installing `enqueue/enqueue` alone gives you the abstractions; you need the specific transport package and, for Symfony or Laravel, the bundle. Version drift between the transport package and the bundle is the most common setup failure.

**Long-running workers accumulate state.** Reset Doctrine connections, clear entity managers, and bound memory. A worker that runs for a week without recycling is a worker that will fail at 3 a.m.

**Queue naming is an API.** Renaming a queue in configuration while old workers are still consuming the previous name silently drops throughput to zero — one of the classic "we deployed and jobs stopped" incidents.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP Job Queues in 2026: Laravel Horizon vs Symfony Messenger vs Enqueue",
  "description": "Comparison of Laravel Horizon, Symfony Messenger and Enqueue for PHP background jobs in 2026: real configuration examples, transport support, retry handling and production operations.",
  "datePublished": "2026-09-20",
  "dateModified": "2026-09-20",
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

**Can Laravel Horizon work with RabbitMQ or Amazon SQS?**
No. Horizon is specifically built for Laravel-powered Redis queues and provides a dashboard plus code-driven configuration for them. If you need RabbitMQ, SQS, or Kafka with Laravel, use Symfony Messenger-style transports or Enqueue's Laravel integration instead.

**Can I use Symfony Messenger without Symfony?**
Yes. Messenger is a standalone component, so a plain PHP application can use the bus, transports, and consumers without the framework. The `enqueue/enqueue-bundle` route is only needed if you want Enqueue transports configured through Symfony's container.

**Which one has a monitoring dashboard?**
Laravel Horizon ships a built-in dashboard with throughput metrics, wait times, and failed job inspection. Symfony Messenger offers CLI commands such as the `messenger:failed` set for the failure transport. Enqueue provides a separate monitoring application.

**How do these handle failed jobs?**
Horizon retries jobs and stores failures with searchable details in its dashboard. Symfony Messenger retries with configurable backoff and moves exhausted messages to a dedicated failure transport you can inspect and replay. Enqueue applies per-message delayed retry strategies and expects you to wire up alerting through its monitoring.

**Do all three support delayed or scheduled jobs?**
Yes, in different forms. Laravel provides scheduling around queued jobs, Horizon handles the Redis consumption side. Symfony Messenger messages can be dispatched with a delay through transport options. Enqueue supports delayed messages directly on the transport layer.

**Which is the best choice for a multi-broker environment?**
Enqueue, by a wide margin. It supports AMQP, STOMP, Redis, Kafka, SQS/SNS, DBAL, MongoDB, Gearman, GPS, and the filesystem behind a single `Interop\Queue` interface, so transport decisions stay reversible.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
