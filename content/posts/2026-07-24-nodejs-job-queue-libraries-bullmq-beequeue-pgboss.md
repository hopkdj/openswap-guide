---
title: "Node.js Job Queue Libraries: BullMQ vs Bee-Queue vs pg-boss — Complete Comparison"
date: "2026-07-24"
tags: ["nodejs", "job-queue", "task-processing", "redis", "postgresql", "developer-tools", "queue"]
draft: false
---

Background job processing is fundamental to modern Node.js applications. Whether you are sending emails, generating reports, processing uploaded files, or running scheduled tasks, a reliable job queue ensures these operations happen reliably without blocking your HTTP request cycle.

Three open source libraries stand out in the Node.js job queue ecosystem: **BullMQ** (Redis-based, from the team behind Bull), **Bee-Queue** (lightweight Redis-backed queue), and **pg-boss** (PostgreSQL-based job queue). Each takes a different architectural approach to solving the same problem.

## Why Job Queues Matter in Node.js

Node.js's single-threaded event loop excels at handling many concurrent I/O operations, but CPU-intensive or long-running tasks block the event loop and degrade responsiveness. Job queues solve this by moving heavy work out of the main request path:

```javascript
// Bad: Blocking the request handler
app.post('/report', async (req, res) => {
    const pdf = await generateReport(req.body); // Takes 30 seconds!
    await sendEmail(pdf);
    res.json({ status: 'done' }); // User waits 30 seconds
});

// Good: Offloading to a job queue
app.post('/report', async (req, res) => {
    await reportQueue.add('generate', req.body); // Returns instantly
    res.json({ status: 'queued' }); // User gets immediate response
});
```

## Comparison Table: BullMQ vs Bee-Queue vs pg-boss

| Feature | BullMQ | Bee-Queue | pg-boss |
|---------|--------|-----------|---------|
| **GitHub Stars** | 9,184 | 4,033 | 3,786 |
| **Last Updated** | July 2026 | July 2026 | July 2026 |
| **Backend** | Redis | Redis | PostgreSQL |
| **Job Priorities** | Yes (numeric) | Yes (numeric) | Yes (numeric) |
| **Delayed Jobs** | Yes | Yes | Yes |
| **Repeatable/Cron Jobs** | Yes (built-in) | Limited | Yes (cron expressions) |
| **Job Progress** | Yes (real-time updates) | Yes | No |
| **Concurrency Control** | Yes (per-queue) | Yes (per-queue) | Yes (batch size) |
| **Rate Limiting** | Yes (group-based) | No | Yes (throttle) |
| **Job Completion Events** | Yes (Redis pub/sub) | Yes (Redis pub/sub) | Yes (Postgres NOTIFY) |
| **Dashboard/UI** | Yes (Bull Board) | Yes (Arena) | Limited |
| **Distributed Workers** | Yes | Yes | Yes |
| **Parent-Child Jobs** | Yes (flows) | No | No |
| **Debounce/Idempotency** | Yes (deduplication) | Limited | Yes (singleton + debounce) |
| **Dependencies** | Redis only | Redis only | PostgreSQL only |

### BullMQ: The Full-Featured Workhorse

BullMQ is the successor to the popular Bull library and offers the richest feature set in the Node.js job queue ecosystem. Its Redis-based architecture provides excellent throughput with advanced workflow features:

```javascript
import { Queue, Worker, QueueScheduler } from 'bullmq';
import IORedis from 'ioredis';

const connection = new IORedis({ maxRetriesPerRequest: null });

// Create a queue
const emailQueue = new Queue('email', { connection });

// Add jobs with options
await emailQueue.add('welcome', {
    to: 'user@example.com',
    template: 'welcome'
}, {
    priority: 1,          // Higher priority
    delay: 5000,          // Delay 5 seconds
    attempts: 3,           // Retry 3 times on failure
    backoff: { type: 'exponential', delay: 2000 },
    removeOnComplete: true,
    removeOnFail: 100       // Keep last 100 failed jobs
});

// Repeatable/cron job
await emailQueue.add('daily-digest', { type: 'digest' }, {
    repeat: { pattern: '0 8 * * *' }  // Every day at 8 AM
});

// Worker
const worker = new Worker('email', async (job) => {
    console.log(`Processing ${job.name} for ${job.data.to}`);
    
    // Report progress
    await job.updateProgress(30);
    
    // Do the actual work
    await sendEmail(job.data);
    
    await job.updateProgress(100);
    return { sent: true, timestamp: Date.now() };
}, { connection, concurrency: 5 });

// Job flow — parent-child dependencies
import { FlowProducer } from 'bullmq';
const flow = new FlowProducer({ connection });
await flow.add({
    name: 'order-process',
    queueName: 'orders',
    data: { orderId: 123 },
    children: [
        { name: 'charge-card', data: { amount: 99 }, queueName: 'payments' },
        { name: 'send-receipt', data: { email: 'a@b.com' }, queueName: 'email' }
    ]
});
```

**Key Strengths:**
- Built-in cron-style repeatable jobs with `repeat.pattern`
- Job flow orchestration (parent-child, sequential processing)
- Rate limiting per group
- Real-time progress tracking
- Rich Bull Board dashboard for monitoring

**Installation:**

```bash
npm install bullmq ioredis
```

### Bee-Queue: Lightweight and Fast

Bee-Queue focuses on simplicity and performance. It strips away advanced features in favor of a minimal, predictable API that handles the core job queue use case extremely well:

```javascript
import Queue from 'bee-queue';

const reportQueue = new Queue('reports', {
    redis: { host: 'localhost', port: 6379 },
    removeOnSuccess: true,
    activateStalledJobThrottle: { count: 3, interval: 300000 }
});

// Add a job
const job = await reportQueue.createJob({
    reportType: 'monthly-sales',
    userId: 42,
    dateRange: { start: '2026-06-01', end: '2026-06-30' }
}).timeout(60000).retries(3).save();

// Listen for completion
job.on('succeeded', (result) => {
    console.log(`Report generated: ${result.fileUrl}`);
});

// Worker
reportQueue.process(3, async (job) => {
    // Concurrency of 3 jobs
    console.log(`Generating report for user ${job.data.userId}`);
    
    // Report progress (0-100)
    job.reportProgress(50);
    
    const report = await generateMonthlyReport(job.data.dateRange);
    
    job.reportProgress(100);
    return { fileUrl: `/reports/${report.id}.pdf` };
});

// Health check
reportQueue.checkHealth().then(stats => {
    console.log(`Waiting: ${stats.waiting}, Active: ${stats.active}`);
});

// Clean stalled jobs
reportQueue.checkStalledJobs(30000); // Every 30 seconds
```

**Key Strengths:**
- Minimal, clean API with low cognitive overhead
- Event-based job lifecycle (succeeded, failed, retrying)
- Lightweight — faster startup and lower memory than BullMQ
- Good for teams that want queue functionality without complexity

**Installation:**

```bash
npm install bee-queue
```

### pg-boss: PostgreSQL-Native Job Queue

pg-boss takes a unique approach by building its queue directly on PostgreSQL. If your application already uses Postgres, you get a full-featured job queue with zero additional infrastructure:

```javascript
import PgBoss from 'pg-boss';

const boss = new PgBoss({
    host: 'localhost',
    database: 'myapp',
    user: 'postgres',
    password: 'secret'
});

await boss.start();

// Subscribe to job types
await boss.work('send-email', { batchSize: 3 }, async (jobs) => {
    // Batch processing — up to 3 jobs at a time
    for (const job of jobs) {
        console.log(`Sending email to ${job.data.to}`);
        await sendEmail(job.data);
    }
});

// Send a job
const jobId = await boss.send('send-email', {
    to: 'user@example.com',
    subject: 'Welcome!'
}, {
    priority: 10,
    retryLimit: 3,
    retryDelay: 60,       // seconds
    expireIn: '1 hour',
    singletonKey: 'welcome-email-42',  // Deduplicate
    startAfter: 30        // seconds delay
});

// Schedule recurring jobs with cron
await boss.schedule('daily-cleanup', '0 3 * * *', {}, {
    tz: 'America/New_York'
});

// Debounce — collapse rapid duplicate jobs
await boss.send('regenerate-cache', { userId: 42 }, {
    singletonKey: 'cache-42',
    singletonSeconds: 300,   // Only run once per 5 minutes
    singletonNextSlot: true   // If one is already scheduled, extend
});

// Monitoring
const states = await boss.getQueueSize('send-email');
console.log(states); // { waiting: 5, active: 2, completed: 120, failed: 1 }
```

**Key Strengths:**
- No additional infrastructure — works with your existing PostgreSQL
- Cron expressions for scheduled jobs (via `boss.schedule()`)
- Singleton/debounce patterns built-in
- Transactional job creation within database transactions
- Archive and retention policy management

**Installation:**

```bash
npm install pg-boss
```

**PostgreSQL Migration:**

```sql
-- pg-boss creates its own schema automatically
-- But you may want to check it exists:
CREATE SCHEMA IF NOT EXISTS pgboss;
```

## Code Examples: Side-by-Side

### Sending a Welcome Email with Retry

**BullMQ:**
```javascript
await emailQueue.add('welcome-email', { userId }, {
    attempts: 3,
    backoff: { type: 'exponential', delay: 5000 }
});
```

**Bee-Queue:**
```javascript
await emailQueue.createJob({ userId })
    .retries(3)
    .backoff('exponential', 5000)
    .save();
```

**pg-boss:**
```javascript
await boss.send('welcome-email', { userId }, {
    retryLimit: 3,
    retryDelay: 5,
    retryBackoff: true
});
```

## Choosing the Right Library

**Choose BullMQ** when you need the most comprehensive feature set — parent-child job flows, real-time progress tracking, built-in cron scheduling, rate limiting, and a monitoring dashboard. If your application has complex job processing requirements and you are already using Redis, BullMQ is the natural choice. It is battle-tested at scale by companies like Microsoft, GitHub, and Uber.

**Choose Bee-Queue** when you want queue functionality without the complexity. Its API surface is significantly smaller than BullMQ's, making it easier to learn, debug, and maintain. If you are building a medium-sized application that needs reliable job processing but does not require advanced features like flows or rate limiting, Bee-Queue's simplicity is an asset.

**Choose pg-boss** when you want to avoid introducing Redis to your stack — or when you need job creation to participate in database transactions. Its singleton and debounce features are excellent for cache invalidation and idempotent operations. If your team already manages PostgreSQL well, adding pg-boss means zero new infrastructure to monitor or secure.

For other queue and task processing options, see our [Python task queues comparison](../celery-vs-dramatiq-vs-arq-self-hosted-task-queues-guide-2026/), our [Go task queue libraries guide](../2026-07-03-go-task-queue-libraries-asynq-watermill-machinery-gocraft/), and our [message queue servers comparison](../rabbitmq-vs-nats-vs-activemq-self-hosted-message-queue-guide/).

## FAQ

### Does BullMQ require a separate Redis instance?

BullMQ uses Redis for job storage and pub/sub messaging. You can use the same Redis instance that your application uses for caching or sessions, though for production workloads with high job throughput, a dedicated Redis instance is recommended to avoid resource contention. BullMQ supports Redis Cluster and Redis Sentinel for high availability.

### Can I use pg-boss without PostgreSQL?

No. pg-boss is built exclusively on PostgreSQL and uses its advisory locks, LISTEN/NOTIFY, and SKIP LOCKED features for queueing. It is the right choice if PostgreSQL is already your primary database. If you use MySQL, MongoDB, or another database, choose BullMQ or Bee-Queue instead (both require Redis).

### How do these libraries handle job idempotency?

BullMQ supports deduplication via `deduplication.id` option — it prevents identical jobs from being added within a configurable window. Bee-Queue has basic support via custom job IDs that reject duplicates. pg-boss has the most flexible approach with `singletonKey`, `singletonSeconds`, and `singletonNextSlot` options that handle deduplication, debouncing, and throttling all within the library.

### What happens to jobs if Redis/PostgreSQL goes down?

All three libraries handle backend failures differently. BullMQ and Bee-Queue will fail to enqueue new jobs and workers will stall if Redis is unavailable — jobs already in Redis persist across worker restarts (Redis durability). pg-boss jobs are stored in PostgreSQL with full ACID guarantees and survive database restarts. Both backends support replication and failover. The key difference: pg-boss provides stronger consistency guarantees, while Redis-based queues provide higher throughput.

### Which library is best for a TypeScript-first project?

All three have TypeScript type definitions. BullMQ has the most comprehensive types with generic job data typing (`Queue<MyDataType, MyReturnType>`). Bee-Queue includes TypeScript definitions in the package. pg-boss provides full TypeScript support with typed `send()` and `work()` methods. For complex typed workflows, BullMQ's generics provide the best IDE experience.

### How do I monitor and debug queued jobs?

BullMQ integrates with Bull Board, a web UI that shows queue statistics, job statuses, and allows manual retry/delete operations. Bee-Queue integrates with Arena, a similar monitoring dashboard. pg-boss relies on SQL queries for monitoring (`boss.getQueueSize()`, `boss.getJobs()`) — you can build custom dashboards or use pgAdmin to inspect the `pgboss` schema tables directly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js Job Queue Libraries: BullMQ vs Bee-Queue vs pg-boss — Complete Comparison",
  "description": "Detailed comparison of Node.js job queue libraries: BullMQ (Redis, feature-rich), Bee-Queue (Redis, lightweight), and pg-boss (PostgreSQL, zero-infrastructure). Includes code examples, deployment patterns, and selection guide.",
  "datePublished": "2026-07-24",
  "dateModified": "2026-07-24",
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
