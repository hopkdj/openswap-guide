---
title: "Self-Hosted Event Bus Libraries: EventBus vs Guava vs MBassador vs Otto — In-Process Pub-Sub Comparison"
date: "2026-06-21"
tags: ["event-bus", "pub-sub", "java", "messaging", "decoupling", "in-process", "developer-libraries"]
draft: false
---

## Introduction

When building complex server-side applications, managing communication between components without tight coupling is a fundamental challenge. While message brokers like RabbitMQ and NATS handle inter-service communication, **in-process event buses** solve a different problem: enabling decoupled communication between components within the same application process.

An event bus implements the **publish-subscribe pattern** in-process, allowing one component to publish events without knowing which other components will handle them. This is essential for keeping your codebase modular, testable, and maintainable — especially in plugin architectures, UI frameworks, and microservices with complex internal logic.

In this article, we compare four leading open-source in-process event bus libraries: **greenrobot EventBus** (24,725 ⭐), **Guava EventBus** (part of Google Guava, 51,487 ⭐), **MBassador** (975 ⭐), and **Square Otto** (5,122 ⭐). We evaluate their performance characteristics, thread models, annotation styles, and suitability for different use cases.

## Comparison Table

| Feature | EventBus (greenrobot) | Guava EventBus | MBassador | Otto (Square) |
|---------|----------------------|----------------|-----------|---------------|
| Stars | 24,725 | 51,487 (Guava) | 975 | 5,122 |
| Language | Java | Java | Java | Java |
| Thread Model | Flexible (posting/single/async) | Synchronous by default; async executor | Configurable per-handler | Main thread + async |
| Subscription | @Subscribe annotation | @Subscribe annotation | @Handler annotation | @Subscribe/@Produce |
| Sticky Events | Yes | No | No | No |
| Priority/Ordering | Subscriber priority | No ordering | Handler priority | No ordering |
| Error Handling | SubscriberExceptionEvent | SubscriberExceptionContext | Custom error handlers | EventBus catches + rethrows |
| Last Updated | Feb 2026 | Jun 2026 (active) | Dec 2025 | Dec 2018 (deprecated) |
| Android Support | Excellent (first-class) | Limited | Via Java | Good |
| Thread Safety | Yes | Yes | Yes | Yes |

## EventBus (greenrobot) — The Performance King

[EventBus](https://github.com/greenrobot/EventBus) by greenrobot is the most widely-used standalone event bus library in the Java ecosystem, with over 24,000 GitHub stars. Originally designed for Android, it has proven equally effective in server-side Java applications.

**Key Features:**
- **Thread mode annotations**: `@Subscribe(threadMode = ThreadMode.BACKGROUND)` gives you fine-grained control over which thread handles events
- **Sticky events**: Late subscribers can receive the most recent event of a type
- **Subscriber priorities**: Control the order in which subscribers receive events
- **Zero configuration**: Works without any setup — just annotate and go
- **ProGuard/R8 friendly**: No reflection overhead in production builds

**Basic Usage:**

```java
// Define an event
public class OrderCreatedEvent {
    private final String orderId;
    private final BigDecimal amount;
    // constructor, getters...
}

// Register subscriber
EventBus.getDefault().register(this);

// Subscribe to events
@Subscribe(threadMode = ThreadMode.ASYNC)
public void onOrderCreated(OrderCreatedEvent event) {
    // Handle asynchronously — good for email sending, logging
    emailService.sendConfirmation(event.getOrderId());
}

// Post events
EventBus.getDefault().post(new OrderCreatedEvent("ORD-123", new BigDecimal("99.99")));
```

EventBus delivers events in approximately **2-5 microseconds** per post on modern hardware, making it suitable for high-throughput server applications. Its thread mode flexibility (`POSTING`, `MAIN`, `MAIN_ORDERED`, `BACKGROUND`, `ASYNC`) gives developers precise control over execution context.

## Guava EventBus — The Google Standard

[Guava](https://github.com/google/guava)'s EventBus is part of Google's core Java libraries, used internally at Google across thousands of services. With 51,000+ stars on the parent project, it benefits from rigorous testing and battle-hardened reliability.

**Key Features:**
- **Simple API**: `@Subscribe` annotation with no thread mode — synchronous by default, async via executor
- **Dead events**: Unhandled events are automatically posted to a dead event channel
- **Hierarchical events**: Subscribers to a parent event type also receive child event types
- **Lightweight**: Zero external dependencies beyond Guava itself

**Basic Usage:**

```java
// Create event bus with async executor
EventBus eventBus = new AsyncEventBus(Executors.newFixedThreadPool(4));

// Register subscriber
eventBus.register(new Object() {
    @Subscribe
    public void handleUserLogin(UserLoginEvent event) {
        auditService.log(event.getUserId(), event.getTimestamp());
    }
});

// Post event
eventBus.post(new UserLoginEvent("user-456", Instant.now()));
```

Guava's EventBus is deliberately simple — it doesn't offer sticky events, subscriber priorities, or thread mode annotations. This simplicity is its strength: there's less to configure, fewer footguns, and the behavior is always predictable. The dead event mechanism (`@Subscribe void handleDead(DeadEvent e)`) provides a safety net for unhandled events that other libraries lack.

## MBassador — High Throughput Specialist

[MBassador](https://github.com/bennidi/mbassador) (Message Bus Ambassador) is purpose-built for high-throughput, multi-threaded environments. While smaller in adoption (975 stars), it offers unique features not found in other event buses.

**Key Features:**
- **Handler priorities**: Numeric priority values determine execution order
- **Filtered subscriptions**: Subscribe with conditions: `@Handler(priority = 1, filters = {@Filter(HighPriority.class)})`
- **Strong reference mode**: Prevents garbage collection of subscribers
- **Configurable reference types**: Weak, strong, or custom references
- **Async message publication**: Built-in support for asynchronous dispatch
- **MessagePublication object**: Track per-message delivery status

**Basic Usage:**

```java
// Configure bus with high-throughput settings
MBassador<Object> bus = new MBassador<>(
    new BusConfiguration()
        .addFeature(Feature.SyncPubSub.Default())
        .addFeature(Feature.AsynchronousHandlerInvocation.Default())
        .addFeature(Feature.AsynchronousMessageDispatch.Default())
        .setProperty(Properties.Common.Id, "order-processing-bus")
);

// Subscribe
bus.subscribe(new Object() {
    @Handler(priority = 10)
    public void handlePayment(PaymentProcessedEvent event) {
        inventoryService.updateStock(event.getSku());
    }
    
    @Handler(priority = 5, delivery = Invoke.Asynchronously)
    public void sendNotification(PaymentProcessedEvent event) {
        notificationService.notify(event.getUserId());
    }
});

// Publish and track
bus.publishAsync(new PaymentProcessedEvent("sku-789", "user-456"));
```

MBassador can handle **millions of events per second** on multi-core systems when properly configured. Its handler priority system and filtered subscriptions make it the best choice for complex event processing pipelines where ordering and conditional delivery matter.

## Otto (Square) — The Deprecated Classic

[Otto](https://github.com/square/otto) by Square was one of the first popular event bus libraries for Android and Java. While officially deprecated since 2018, it deserves mention as the spiritual predecessor to many modern event bus designs. Otto was a fork of Guava's EventBus enhanced with Android-specific features.

**Basic Usage (Historical):**

```java
// Otto uses a Bus singleton
Bus bus = new Bus(ThreadEnforcer.ANY);

// Producer pattern for sticky events
@Produce
public ConfigLoadedEvent produceConfig() {
    return new ConfigLoadedEvent(config);
}

// Standard subscription
@Subscribe
public void onConfigLoaded(ConfigLoadedEvent event) {
    initializeWithConfig(event.getConfig());
}
```

Otto's key contributions were the **@Produce** annotation (for initial-value events) and `ThreadEnforcer` (for compile-time thread safety checks). While Otto itself is deprecated, its design patterns live on in EventBus and modern reactive frameworks.

## Performance Benchmark Comparison

Here's a summary of performance characteristics based on community benchmarks (operations per second on a 4-core system):

| Metric | EventBus | Guava EventBus | MBassador |
|--------|----------|---------------|-----------|
| Single-thread posts/sec | ~2.5M | ~1.8M | ~3.2M |
| Multi-thread posts/sec | ~5.0M | ~3.2M | ~8.1M |
| Post-to-handler latency | ~3µs | ~5µs | ~1.5µs |
| Memory overhead (no subscribers) | ~500KB | ~300KB | ~800KB |
| Zero-GC pressure | Good | Excellent | Very Good |

MBassador consistently leads in raw throughput, followed by EventBus, then Guava. However, Guava has the lowest memory footprint and the most predictable behavior under load.

## Choosing the Right Event Bus

- **Choose EventBus if**: You need a battle-tested, Android-compatible solution with flexible thread models and sticky events. Ideal for applications spanning mobile and server-side.
- **Choose Guava EventBus if**: You already use Guava, value simplicity over features, and need hierarchical event dispatch. Best for server-side applications where predictable synchronous behavior is preferred.
- **Choose MBassador if**: You need maximum throughput, handler priorities, or filtered subscriptions. The right choice for high-performance event processing pipelines where every microsecond counts.
- **Use Otto's patterns, not its code**: Otto is deprecated, but its @Produce concept and ThreadEnforcer approach are worth implementing in custom solutions.

For related patterns, see our guides on [zero-downtime message broker HA](../2026-06-01-self-hosted-message-broker-ha-rabbitmq-kafka-nats-guide/) for inter-service messaging, [circuit breaker resilience patterns](../2026-06-21-circuit-breaker-libraries-resilience4j-hystrix-failsafe-go-polly/) for fault tolerance, and [brokerless messaging with ZeroMQ](../2026-05-12-self-hosted-brokerless-messaging-zeromq-nanomsg-nng-guide/) for lightweight IPC alternatives.

## FAQ

### When should I use an in-process event bus instead of a message broker?

Use an in-process event bus when all communicating components live within the same JVM process. It offers sub-microsecond latency (versus millisecond-range for brokers) and zero network overhead. Use a message broker (RabbitMQ, NATS, Kafka) when components run in different processes, containers, or machines.

### Is an event bus the same as reactive streams (RxJava, Reactor)?

No. An event bus is a **many-to-many** broadcast mechanism where any subscriber can receive any event type. Reactive streams (RxJava, Project Reactor) are **composable pipelines** for asynchronous data processing with backpressure support. Event buses complement reactive programming by providing the event source.

### Are event buses thread-safe?

Yes — all four libraries discussed are explicitly designed for thread safety. However, thread safety means the bus itself won't corrupt under concurrent access, not that your handler code is automatically thread-safe. Always synchronize shared state accessed from multiple handler threads.

### What happens to events if no subscriber is registered?

In EventBus and MBassador, events with no subscribers are silently dropped. Guava EventBus posts them to a `DeadEvent` channel, allowing you to register a handler for unhandled events — useful for logging, metrics, or triggering fallback logic.

### Can I use these event buses in Kotlin or other JVM languages?

Yes. All four libraries work seamlessly with Kotlin, Scala, Groovy, and Clojure. Kotlin's coroutine support pairs well with EventBus's async thread modes, and Scala developers often combine Akka's actor model with EventBus for intra-actor messaging.

### How do I avoid memory leaks with event bus subscribers?

The most common memory leak pattern is forgetting to unregister subscribers. Always call `bus.unregister(this)` in your cleanup/shutdown lifecycle. EventBus uses weak references by default for some configurations, but explicit unregistration is the safest approach. Consider using try-with-resources or lifecycle-aware components (Spring beans, Android Lifecycle) to automate cleanup.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Event Bus Libraries: EventBus vs Guava vs MBassador vs Otto — In-Process Pub-Sub Comparison",
  "description": "Compare four open-source in-process event bus libraries for Java applications: greenrobot EventBus, Google Guava EventBus, MBassador, and Square Otto. Includes performance benchmarks, code examples, and guidance for choosing the right event bus for your architecture.",
  "datePublished": "2026-06-21",
  "dateModified": "2026-06-21",
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
