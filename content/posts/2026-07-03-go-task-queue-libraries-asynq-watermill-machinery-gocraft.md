---
title: "Go Task Queue Libraries: Asynq vs Watermill vs Machinery vs gocraft/work"
date: "2026-07-03"
tags: ["go", "task-queue", "distributed-systems", "background-jobs", "message-queue", "backend"]
draft: false
---

When building Go backend services, you inevitably need to handle background tasks — sending emails, generating reports, processing uploads, or running scheduled cleanup. Rather than blocking your HTTP handlers, you offload these to a task queue. Go's concurrency model makes it an excellent language for building task processing systems, and the ecosystem offers several mature libraries purpose-built for this problem.

In this guide, we compare four Go task queue libraries: **Asynq** (Redis-backed with rich observability), **Watermill** (event-driven pub/sub), **Machinery** (multi-broker, Celery-inspired), and **gocraft/work** (minimalist SQLite/Redis worker). Each takes a different architectural approach, and understanding those trade-offs helps you pick the right tool for your workload.

## Comparison Overview

| Feature | Asynq | Watermill | Machinery | gocraft/work |
|---------|-------|-----------|-----------|-------------|
| **Broker Backend** | Redis | Kafka, Go channels, NATS, Pulsar, Redis Streams, AMQP, SQL | Redis, AMQP, AWS SQS, GCP Pub/Sub | Redis, PostgreSQL, MySQL |
| **GitHub Stars** | 13,474 | 9,782 | 7,350 | 2,524 |
| **Task Retries** | Built-in, exponential backoff | Via middleware (Retry) | Built-in, configurable | Built-in, configurable |
| **Scheduling** | Cron-like scheduler | No built-in scheduler | Periodic tasks via Beat | No built-in scheduler |
| **Observability** | Web UI dashboard, metrics | Logger/routers, traces | Basic logging | Minimal |
| **Middleware** | Custom handler chains | Publisher/Subscriber middleware | Task chains, chord, group | Middleware pattern |
| **At-Least-Once** | Yes | Configurable | Yes | Yes |

## Asynq: Redis-Backed Task Queue with Built-in Dashboard

Asynq, created by Ken Hibino (the same developer behind the popular `redis` Go client), is purpose-built as a distributed task queue on top of Redis. It uses Redis data structures (streams, sorted sets, lists) directly to implement reliable task delivery, retries, and scheduling.

```go
package main

import (
    "log"
    "github.com/hibiken/asynq"
)

func main() {
    // Create Redis connection
    r := asynq.RedisClientOpt{Addr: "localhost:6379"}
    
    // Create a new client
    client := asynq.NewClient(r)
    defer client.Close()
    
    // Create a task
    task, err := asynq.NewTask(
        "email:send",
        map[string]interface{}{"user_id": 42},
    )
    if err != nil {
        log.Fatal(err)
    }
    
    // Enqueue the task with options
    info, err := client.Enqueue(
        task,
        asynq.MaxRetry(3),
        asynq.Timeout(30 * time.Second),
        asynq.Queue("critical"),
    )
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Enqueued task: %s", info.ID)
}
```

```go
// Worker (mux) side
func main() {
    srv := asynq.NewServer(
        asynq.RedisClientOpt{Addr: "localhost:6379"},
        asynq.Config{Concurrency: 10},
    )
    
    mux := asynq.NewServeMux()
    mux.HandleFunc("email:send", handleEmailTask)
    mux.HandleFunc("report:generate", handleReportTask)
    
    if err := srv.Run(mux); err != nil {
        log.Fatal(err)
    }
}
```

Asynq's standout feature is its built-in web dashboard (`asynqmon`) that provides real-time visibility into queue depths, task states, processing rates, and failure histories. For teams that need production observability out of the box, Asynq is hard to beat.

## Watermill: Event-Driven Pub/Sub for Go

Watermill takes a fundamentally different approach. Rather than being a task queue, it's a **message streaming library** built around the pub/sub pattern. This makes it ideal for event-driven architectures where tasks flow through a pipeline of publishers and subscribers.

```go
package main

import (
    "context"
    "log"
    
    "github.com/ThreeDotsLabs/watermill"
    "github.com/ThreeDotsLabs/watermill-redisstream/pkg/redisstream"
    "github.com/ThreeDotsLabs/watermill/message"
    "github.com/redis/go-redis/v9"
)

func main() {
    pubSub := redisstream.NewPublisher(
        redisstream.PublisherConfig{Client: redis.NewClient(&redis.Options{Addr: "localhost:6379"})},
        watermill.NewStdLogger(false, false),
    )
    
    // Publish a message
    msg := message.NewMessage(
        watermill.NewUUID(),
        []byte(`{"user_id": 42, "action": "welcome"}`),
    )
    if err := pubSub.Publish("email-topic", msg); err != nil {
        log.Fatal(err)
    }
    
    // Subscribe
    subscriber := redisstream.NewSubscriber(
        redisstream.SubscriberConfig{Client: redis.NewClient(&redis.Options{Addr: "localhost:6379"})},
        watermill.NewStdLogger(false, false),
    )
    
    messages, err := subscriber.Subscribe(context.Background(), "email-topic")
    if err != nil {
        log.Fatal(err)
    }
    
    go func() {
        for msg := range messages {
            log.Printf("Received: %s", msg.Payload)
            msg.Ack()
        }
    }()
}
```

Watermill's strength lies in its **multi-transport support**. You can start development with Go channels (in-memory, zero dependencies), switch to Redis Streams for staging, and migrate to Kafka for production — all without changing your business logic. The router, middleware, and plugin system make it easy to add retries, rate limiting, and Poison Queue (poison message handling) declaratively.

## Machinery: Multi-Broker, Celery-Inspired Architecture

Machinery is the Go ecosystem's answer to Python's Celery. It supports multiple brokers (Redis, AMQP/RabbitMQ, AWS SQS, GCP Pub/Sub) and multiple result backends (Redis, Memcache, MongoDB). If you're migrating from a Python Celery setup to Go, Machinery will feel familiar.

```go
package main

import (
    "github.com/RichardKnop/machinery/v2"
    "github.com/RichardKnop/machinery/v2/config"
    "github.com/RichardKnop/machinery/v2/tasks"
)

func main() {
    cnf := &config.Config{
        Broker:        "redis://localhost:6379",
        DefaultQueue:  "machinery_tasks",
        ResultBackend: "redis://localhost:6379",
    }
    
    server, err := machinery.NewServer(cnf)
    if err != nil {
        log.Fatal(err)
    }
    
    // Register tasks
    server.RegisterTasks(map[string]interface{}{
        "send_email":  SendEmail,
        "gen_report":  GenerateReport,
    })
    
    // Send a task
    signature := &tasks.Signature{
        Name: "send_email",
        Args: []tasks.Arg{
            {Type: "string", Value: "user@example.com"},
        },
    }
    
    asyncResult, err := server.SendTask(signature)
    if err != nil {
        log.Fatal(err)
    }
}
```

Machinery supports advanced workflows like **groups**, **chords**, and **chains** — patterns where multiple tasks are executed in parallel and their results aggregated before continuing. This makes it suitable for complex data processing pipelines.

## gocraft/work: Minimalist and SQL-Friendly

gocraft/work is refreshingly simple. It doesn't need a message broker — it can use Redis, PostgreSQL, or MySQL directly as its job store. This makes it ideal for projects that already have a database and want to minimize infrastructure dependencies.

```go
package main

import (
    "github.com/gocraft/work"
    "github.com/gomodule/redigo/redis"
)

var redisPool = &redis.Pool{
    MaxActive: 5,
    MaxIdle:   5,
    Wait:      true,
    Dial: func() (redis.Conn, error) {
        return redis.Dial("tcp", "localhost:6379")
    },
}

func main() {
    pool := work.NewEnqueuer("my_app_namespace", redisPool)
    
    // Enqueue a background job
    _, err := pool.Enqueue("send_welcome_email", work.Q{
        "user_id": 42,
        "email":   "user@example.com",
    })
    if err != nil {
        log.Fatal(err)
    }
}
```

```go
// Worker
func main() {
    pool := work.NewWorkerPool(Context{}, 10, "my_app_namespace", redisPool)
    
    pool.Job("send_welcome_email", (*Context).SendEmail)
    pool.Job("run_billing", (*Context).RunBilling)
    
    pool.Start()
    signalChan := make(chan os.Signal, 1)
    signal.Notify(signalChan, os.Interrupt)
    <-signalChan
    pool.Stop()
}
```

gocraft/work's API is deliberately minimal. There are no channels, no orchestration primitives, no built-in scheduler. What you get is a reliable `Enqueue → Dequeue → Execute` loop with retries, uniqueness guarantees, and periodic job enqueueing.

## Choosing the Right Tool

**Use Asynq** when you want a production-ready task queue with built-in observability, scheduled jobs, and rich middleware. It's the best batteries-included choice for teams that need to be up and running fast.

**Use Watermill** when your architecture is event-driven and you need message routing across multiple transports. It excels in CQRS, event sourcing, and microservice communication patterns.

**Use Machinery** when you're migrating from Celery or need advanced workflow primitives (groups, chords, chains) across multiple broker backends.

**Use gocraft/work** when you want minimal infrastructure. If your project already uses PostgreSQL or Redis and you just need to run background jobs without adding new services, gocraft/work fits the bill perfectly.

For general-purpose Go background processing, see our [Python task queue comparison](../celery-vs-dramatiq-vs-arq-self-hosted-task-queues-guide-2026/) for cross-language perspective. If you're deciding between message queues and task queues, our [message queue server comparison](../self-hosted-message-queue-servers-nsq-beanstalkd-artemis-guide/) helps clarify the architectural differences.

## 部署策略

Since these are Go libraries (not standalone services), "deployment" means integrating them into your application. However, every task queue needs a backing broker:

**For Asynq and Watermill (Redis-based):**
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
```

**For Watermill with Kafka:**
```yaml
  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

## FAQ

### Which Go task queue has the best production observability?

**Asynq** stands out with its built-in web dashboard (`asynqmon`) that shows real-time queue depths, task success/failure rates, and processing latency. Watermill provides structured logging and supports tracing middleware, but lacks a dedicated UI. Machinery and gocraft/work require you to build your own monitoring.

### Can I use Watermill as a simple task queue, or do I need to buy into event-driven architecture?

Watermill works fine as a task queue when you publish to a single subscriber topic with one consumer group. You don't need full CQRS/event-sourcing — the pub/sub model degrades gracefully to a worker-queue pattern when you only have one subscriber. However, if all you need is `Enqueue → Process`, Asynq or gocraft/work will have simpler APIs.

### How does Machinery compare to Python Celery?

Machinery was directly inspired by Celery and supports the same workflow patterns: groups, chords, chains, and periodic tasks. The main difference is that Machinery is written in Go, so you get native goroutine-based concurrency instead of Celery's prefork/threaded worker pools. Broker support is similar (Redis, AMQP, SQS).

### Does gocraft/work support PostgreSQL as a job store?

Yes — gocraft/work supports PostgreSQL, MySQL, and Redis as job stores through its `github.com/gocraft/work/webui` package. The SQL-backed approach is unique among these four libraries and lets you run a task queue without adding Redis if your app already uses a relational database.

### Which library handles at-least-once delivery most reliably?

All four support at-least-once semantics, but they implement it differently. Asynq uses Redis streams with consumer groups and explicit acknowledgement. Watermill provides configurable delivery guarantees (at-most-once, at-least-once) per subscriber. Machinery uses visibility timeouts with broker-specific mechanisms. gocraft/work uses a dead man's switch (requeue abandoned jobs after a timeout).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Task Queue Libraries: Asynq vs Watermill vs Machinery vs gocraft/work",
  "description": "Comprehensive comparison of Go task queue libraries for background job processing: Asynq, Watermill, Machinery, and gocraft/work with code examples and decision guide.",
  "datePublished": "2026-07-03",
  "dateModified": "2026-07-03",
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
