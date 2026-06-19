---
title: "Self-Hosted Lock-Free Concurrent Data Structures: crossbeam vs Disruptor vs Folly vs concurrency-kit"
date: "2026-06-19"
tags: ["concurrency", "data-structures", "performance", "rust", "cpp", "developer-tools", "comparison", "guide"]
draft: false
---

## The Lock-Free Programming Paradigm

Traditional concurrent programming relies on mutexes and locks to protect shared data. When one thread holds a lock, all other threads must wait — leading to contention, priority inversion, and in the worst case, deadlocks. Lock-free data structures eliminate these problems by using atomic CPU instructions (compare-and-swap, fetch-and-add) to allow multiple threads to operate on shared data simultaneously without ever blocking each other.

The benefits for self-hosted services are substantial. A lock-free queue can sustain 100 million messages per second on a modern server CPU, while a mutex-protected equivalent typically tops out at 5-10 million. For high-throughput services like message brokers, API gateways, and real-time analytics pipelines, lock-free data structures aren't just an optimization — they're an architectural necessity.

In this comparison, we examine four leading open-source lock-free concurrency libraries: crossbeam (Rust's concurrency toolkit), LMAX Disruptor (Java's high-performance inter-thread messaging), Folly (Facebook's C++ concurrency library), and concurrency-kit (portable C lock-free primitives). Each represents a different point in the design space of lock-free programming.

## Quick Comparison

| Feature | crossbeam | LMAX Disruptor | Folly | concurrency-kit |
|---------|-----------|----------------|-------|----------------|
| **Language** | Rust | Java | C++ | C |
| **Stars** | 8,488 | 18,378 | 30,423 | 1,200+ (estimated) |
| **Key Primitive** | Channels, deque, epoch GC | Ring buffer | MPMC queue, Hazptr | SMR, stack, fifo |
| **Memory Reclamation** | Epoch-based GC | None (pre-allocate) | Hazard pointers, RCU | Epoch-based, hazard ptr |
| **Safety Guarantee** | Compile-time (borrow check) | Runtime | Manual + sanitizers | Manual |
| **Wait-Free Progress** | Mostly lock-free | Fully wait-free | Mixed | Mostly lock-free |
| **no_std Support** | Partial (no alloc) | N/A (JVM) | Yes (Folly futures) | Yes |
| **Last Updated** | 2026-06 | 2025-04 | 2026-06 | Active |
| **License** | MIT/Apache-2.0 | Apache-2.0 | Apache-2.0 | BSD-2-Clause |

## crossbeam: Rust's Concurrency Swiss Army Knife

crossbeam is the de facto standard for advanced concurrency in Rust. It provides lock-free channels, work-stealing deques, epoch-based garbage collection for safe memory reclamation in lock-free code, and scoped threads that eliminate the need for Arc<Mutex<T>> in many cases.

```rust
use crossbeam::channel;
use crossbeam::epoch::{self, Atomic, Owned, Guard};
use std::sync::Arc;
use std::thread;

// Lock-free MPMC channel — multiple producers, multiple consumers
fn lockfree_channel_example() {
    let (tx, rx) = channel::unbounded();

    // Spawn 4 producers
    for i in 0..4 {
        let tx = tx.clone();
        thread::spawn(move || {
            for j in 0..1000 {
                tx.send(format!("p{}-msg{}", i, j)).unwrap();
            }
        });
    }
    drop(tx); // Close channel when all senders done

    // Consume all messages
    let mut count = 0;
    while let Ok(msg) = rx.recv() {
        count += 1;
    }
    println!("Received {} messages", count); // 4000
}

// Lock-free stack with epoch-based memory reclamation
fn lockfree_stack_example() {
    let stack = Arc::new(Atomic::null());

    let s = stack.clone();
    thread::spawn(move || {
        let guard = &epoch::pin();
        let node = Owned::new(42u64).into_shared(guard);
        s.store(node, std::sync::atomic::Ordering::Release);
    }).join().unwrap();

    let guard = &epoch::pin();
    let value = stack.load(std::sync::atomic::Ordering::Acquire, guard);
    if let Some(node) = unsafe { value.as_ref() } {
        println!("Stack value: {}", *node);
    }
}

fn main() {
    lockfree_channel_example();
    lockfree_stack_example();
}
```

crossbeam's killer feature is its epoch-based garbage collection (crossbeam-epoch), which solves the ABA problem — the notorious bug where a pointer appears unchanged between operations but the memory it points to has been freed and reallocated. With epoch GC, memory is only freed when no thread holds a reference to it, making lock-free data structures safe without garbage collection overhead.

## LMAX Disruptor: The High-Performance Ring Buffer

LMAX Disruptor, created by the London Multi Asset Exchange, is a high-performance inter-thread messaging library built on a pre-allocated ring buffer. Its key insight: instead of passing messages through queues with producer and consumer locks, use a single-producer or multi-producer sequencer that coordinates access to slots in a circular array.

```java
import com.lmax.disruptor.*;
import com.lmax.disruptor.dsl.Disruptor;
import java.util.concurrent.Executors;

public class DisruptorExample {
    static class OrderEvent {
        private long orderId;
        private double price;
        private String symbol;
        // getters and setters...

        public void set(long orderId, double price, String symbol) {
            this.orderId = orderId;
            this.price = price;
            this.symbol = symbol;
        }
    }

    static class OrderHandler implements EventHandler<OrderEvent> {
        public void onEvent(OrderEvent event, long sequence, boolean endOfBatch) {
            // Process order — no locking, no contention
            System.out.printf("Processing order %d: %s @ %.2f%n",
                event.getOrderId(), event.getSymbol(), event.getPrice());
        }
    }

    public static void main(String[] args) {
        int bufferSize = 1024; // Must be power of 2

        Disruptor<OrderEvent> disruptor = new Disruptor<>(
            OrderEvent::new,
            bufferSize,
            Executors.defaultThreadFactory(),
            ProducerType.MULTI,
            new BusySpinWaitStrategy()
        );

        disruptor.handleEventsWith(new OrderHandler());
        disruptor.start();

        RingBuffer<OrderEvent> ringBuffer = disruptor.getRingBuffer();

        // Publish events — no lock contention even with multiple producers
        for (long i = 0; i < 100; i++) {
            long sequence = ringBuffer.next();
            OrderEvent event = ringBuffer.get(sequence);
            event.set(i, 100.0 + i, "AAPL");
            ringBuffer.publish(sequence);
        }

        disruptor.shutdown();
    }
}
```

The Disruptor achieves its speed through several clever design decisions: padding cache lines to prevent false sharing, using memory barriers instead of locks, and pre-allocating all event objects to eliminate garbage collection pressure. At LMAX, the Disruptor processes over 6 million orders per second on a single thread — performance that's impossible with traditional blocking queues.

## Folly: Facebook's C++ Concurrency Library

Folly (Facebook Open Source Library) contains some of the most battle-tested concurrent data structures in production. Its MPMCQueue (multi-producer multi-consumer queue) handles billions of messages daily across Facebook's infrastructure, and its Hazard Pointers implementation provides safe memory reclamation for lock-free code without the overhead of epoch-based schemes.

```cpp
#include <folly/MPMCQueue.h>
#include <folly/concurrency/Hazptr.h>
#include <thread>
#include <iostream>

// Lock-free MPMC queue
void mpmc_queue_example() {
    folly::MPMCQueue<int> queue(1024); // Lock-free, bounded

    std::thread producer([&] {
        for (int i = 0; i < 1000; i++) {
            while (!queue.write(i)) {
                std::this_thread::yield(); // Backpressure
            }
        }
    });

    std::thread consumer([&] {
        int value;
        int count = 0;
        while (count < 1000) {
            if (queue.read(value)) {
                count++;
            }
        }
        std::cout << "Consumed " << count << " items\n";
    });

    producer.join();
    consumer.join();
}

// Hazard pointer-protected lock-free stack node
struct Node : public folly::hazptr_obj_base<Node> {
    int value;
    Node* next;
    Node(int v) : value(v), next(nullptr) {}
};

int main() {
    mpmc_queue_example();
    std::cout << "Folly MPMCQueue example complete\n";
    return 0;
}
```

Folly's MPMCQueue is notable for being one of the few truly wait-free multi-producer multi-consumer queue implementations. Most "lock-free" queues are actually lock-free but not wait-free — a slow producer can delay fast producers. Folly's implementation guarantees that no thread ever blocks another, making it ideal for latency-sensitive services handling mixed-priority workloads.

## concurrency-kit: Portable C Lock-Free Primitives

concurrency-kit (CK) is a lightweight, portable C library providing lock-free data structures and safe memory reclamation. Unlike crossbeam (Rust-only), Disruptor (JVM-only), and Folly (C++ with heavy dependencies), CK compiles anywhere with a C11 compiler and has no external dependencies.

```c
#include <ck_ring.h>
#include <ck_fifo.h>
#include <ck_epoch.h>
#include <pthread.h>
#include <stdio.h>

static ck_epoch_t global_epoch;
static ck_epoch_record_t records[4]; // One per thread

// Lock-free SPSC ring buffer (single-producer, single-consumer)
static ck_ring_buffer_t ring_buffer[1024];
static ck_ring_t ring;

void *producer(void *arg) {
    ck_epoch_register(&global_epoch, &records[0]);

    for (uint64_t i = 0; i < 1000; i++) {
        while (!ck_ring_enqueue_sp(&ring, ring_buffer, &i)) {
            ck_pr_stall(); // Back off
        }
    }
    return NULL;
}

void *consumer(void *arg) {
    ck_epoch_register(&global_epoch, &records[1]);

    uint64_t value;
    int count = 0;
    while (count < 1000) {
        if (ck_ring_dequeue_sc(&ring, ring_buffer, &value)) {
            count++;
        }
    }
    printf("Consumed %d items from lock-free ring\n", count);
    return NULL;
}

int main() {
    ck_epoch_init(&global_epoch);
    ck_ring_init(&ring, 1024);

    pthread_t prod, cons;
    pthread_create(&prod, NULL, producer, NULL);
    pthread_create(&cons, NULL, consumer, NULL);
    pthread_join(prod, NULL);
    pthread_join(cons, NULL);
    return 0;
}
```

CK's portability makes it the natural choice for embedded self-hosted services on ARM or RISC-V, where JVM-based and C++ template-heavy libraries won't work. It's used in production by database systems (PostgreSQL extensions), message brokers, and high-frequency trading systems where C is still the lingua franca.

## Deployment Architecture: Integrating Lock-Free Data Structures

The deployment pattern for these libraries differs fundamentally from Docker-based service deployment. crossbeam, Folly, and concurrency-kit are compile-time dependencies — you add them to your Cargo.toml, CMakeLists.txt, or Makefile, and they become part of your binary. LMAX Disruptor is a JVM dependency added via Maven or Gradle.

For Rust services: add `crossbeam = "0.8"` to your `Cargo.toml` and import the specific sub-crate you need (crossbeam-channel for MPMC channels, crossbeam-deque for work-stealing, crossbeam-epoch for lock-free memory reclamation). Rust's borrow checker ensures you don't accidentally share mutable data without synchronization — a guarantee none of the other libraries provide.

For Java services: the Disruptor integrates as a standard Maven dependency. Its ring buffer pattern works best when you can pre-allocate all event objects at startup, avoiding garbage collection entirely during the hot path. This makes it ideal for services with predictable load patterns, like trading engines and real-time analytics.

For C++ services: Folly has the heaviest build requirements (Google Test, Boost for some modules, CMake 3.13+), but its MPMCQueue and Hazard Pointer implementations are best-in-class for raw throughput. Facebook uses Folly's concurrency primitives in Proxygen (HTTP server), McRouter (memcached router), and HHVM.

For embedded or portable C services: concurrency-kit compiles anywhere and adds minimal overhead. Use it when you need lock-free performance but can't pull in Rust's toolchain or JVM.

## Choosing the Right Lock-Free Library for Your Stack

The choice largely depends on your language ecosystem and performance requirements. If you're building Rust services, crossbeam is the clear winner — it leverages Rust's type system for safety while providing excellent throughput. If you're on the JVM, LMAX Disruptor offers unparalleled single-machine messaging throughput. If you're in C++ and need maximum control, Folly provides the most comprehensive set of primitives. And if portability is paramount, concurrency-kit runs everywhere C does.

For self-hosted services processing tens of thousands of concurrent requests, the performance difference between lock-based and lock-free data structures isn't marginal — it's the difference between horizontal scaling at 10 nodes versus 2 nodes. A service that uses crossbeam channels instead of Arc<Mutex<Vec<T>>> can reduce tail latency from hundreds of milliseconds to single-digit microseconds.

For more on distributed coordination, see our [distributed locking comparison](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/). For message queuing systems that leverage lock-free queues internally, check our [message broker guide](../rabbitmq-vs-nats-vs-activemq-self-hosted-message-queue-guide/). For task processing patterns, see our [task queue comparison](../celery-vs-dramatiq-vs-arq-self-hosted-task-queues-guide-2026/).

## FAQ

### Are lock-free data structures always faster than mutex-based ones?

Not always. For low-contention scenarios (1-2 threads occasionally accessing shared data), a simple mutex can be faster than a lock-free structure due to lower constant overhead. Lock-free structures shine under contention — when 4+ threads are hammering the same data structure, mutex-based approaches degrade rapidly while lock-free structures maintain steady throughput.

### How do I handle memory reclamation in lock-free code?

This is the hardest problem in lock-free programming. After a thread removes a node from a lock-free data structure, you can't immediately free it because another thread might still be reading it. Solutions include: epoch-based reclamation (crossbeam-epoch, CK epoch), hazard pointers (Folly hazptr), reference counting, and RCU (read-copy-update). Each has different latency/throughput trade-offs.

### Can lock-free data structures cause starvation?

Lock-free structures prevent deadlocks and priority inversion, but they don't guarantee freedom from starvation. In the LMAX Disruptor, a slow consumer can prevent the ring buffer from wrapping around, effectively stalling all producers. Mitigation strategies include: bounded queue sizes with explicit backpressure, consumer timeouts, and monitoring consumer lag with health checks.

### Which is more important: lock-free or wait-free?

Wait-free is a stronger guarantee — every thread makes progress within a bounded number of steps regardless of what other threads do. Lock-free guarantees system-wide progress (some thread always makes progress) but not per-thread progress. For soft real-time services (video streaming, voice chat), wait-free is essential. For most web services, lock-free is sufficient and has better average throughput.

### Do I need to worry about CPU cache lines when using these libraries?

The libraries handle cache-line optimization internally. LMAX Disruptor pads its ring buffer entries to 64 bytes, Folly's MPMCQueue uses cache-line alignment for its head/tail pointers, and crossbeam's channels pad internal slots. You typically don't need to add manual padding unless you're building custom lock-free structures.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Lock-Free Concurrent Data Structures: crossbeam vs Disruptor vs Folly vs concurrency-kit",
  "description": "Compare open-source lock-free concurrency libraries for high-throughput self-hosted services: crossbeam for Rust, LMAX Disruptor for Java, Folly for C++, and concurrency-kit for portable C.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  },
  "proficiencyLevel": "Advanced",
  "about": {
    "@type": "Thing",
    "name": "Lock-Free Data Structures"
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
