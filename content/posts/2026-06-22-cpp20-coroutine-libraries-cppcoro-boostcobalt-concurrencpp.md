---
title: "Self-Hosted C++20 Coroutine Libraries: cppcoro vs Boost.Cobalt vs concurrencpp"
date: "2026-06-22"
tags: ["c++", "coroutines", "c++20", "async", "concurrency", "cppcoro", "boost", "development"]
draft: false
---

Coroutines are the most transformative C++ feature since move semantics. With C++20, the language gained native coroutine support through the `co_await`, `co_yield`, and `co_return` keywords — but the standard library did not provide any concrete coroutine types. This intentional gap left the ecosystem to innovate, and three libraries have emerged as the leading options: **cppcoro** by Lewis Baker, **Boost.Cobalt** from the Boost organization, and **concurrencpp** by David Haim.

This article compares these libraries across their programming models, performance characteristics, ecosystem integration, and suitability for production C++ services. We focus on practical concerns: how to write, debug, and deploy coroutine-based C++ applications.

## Understanding C++20 Coroutines

C++20 coroutines are **stackless** — they don't have their own stack, unlike Go goroutines or Rust async tasks. When a coroutine suspends at `co_await`, it stores only the local variables that are live across the suspension point, and the coroutine frame is allocated on the heap (or via a custom allocator). This makes them extremely efficient but also places the burden of lifetime management on the library.

The C++20 standard defines the coroutine machinery — `promise_type`, `awaitable`, `awaiter` — but leaves the actual task types, schedulers, and I/O integration to libraries. This is where cppcoro, Boost.Cobalt, and concurrencpp differ fundamentally.

## Library Comparison

| Feature | cppcoro | Boost.Cobalt | concurrencpp |
|---------|---------|-------------|--------------|
| Stars | 3,858 | 342 | 2,756 |
| Latest Update | Jan 2024 | June 2026 | May 2025 |
| Core Abstraction | `task<T>`, `generator<T>` | `cobalt::task<T>`, `cobalt::generator<T>` | `concurrencpp::result<T>` |
| I/O Integration | `io_service` + socket wrappers | ASIO integration (native) | `concurrencpp::timer`, custom executors |
| Executor Model | Single `io_service` | ASIO `io_context` | Thread pool + manual executor |
| Thread Safety | Single-threaded I/O loop | ASIO strand model | Thread-safe executors |
| Sync Primitives | `async_mutex`, `async_manual_reset_event` | `cobalt::channel`, `cobalt::mutex` | `concurrencpp::timer_queue` |
| Cancellation | Via `cancellation_token` | ASIO cancellation slots | `concurrencpp::timer::cancel()` |
| Debugging Support | Limited | ASIO handler tracking | Stack trace on exception |

## cppcoro: The Pioneer

cppcoro, created by Lewis Baker (a key contributor to the C++ coroutine TS), was the first comprehensive coroutine library. It established many patterns that later libraries adopted, including the `task<T>` type and `generator<T>` for synchronous coroutines.

**Key strengths:**
- **Battle-tested design**: The `task<T>` pattern from cppcoro influenced both Boost.Cobalt and the proposed `std::execution`
- **File I/O operations**: `cppcoro::read_file()` and `cppcoro::write_file()` for async file handling
- **Network wrappers**: `cppcoro::net::socket` wrappers that integrate with the `io_service`
- **Generator support**: `cppcoro::generator<T>` for lazy range generation using `co_yield`

**Limitations:**
- No longer actively maintained (last update January 2024)
- Limited to a single `io_service` — no multi-threaded execution
- No support for ASIO's `io_context` natively (uses its own `io_service`)

```cpp
#include <cppcoro/task.hpp>
#include <cppcoro/sync_wait.hpp>
#include <cppcoro/when_all.hpp>
#include <cppcoro/generator.hpp>
#include <iostream>

// Generator example: lazy Fibonacci
cppcoro::generator<uint64_t> fibonacci() {
    uint64_t a = 0, b = 1;
    while (true) {
        co_yield a;
        auto next = a + b;
        a = b;
        b = next;
    }
}

// Async task: fetch and process data
cppcoro::task<int> fetch_and_sum(int a, int b) {
    // Simulate async work
    co_return a + b;
}

cppcoro::task<void> process_parallel() {
    // Run multiple tasks concurrently
    auto [result1, result2, result3] = 
        co_await cppcoro::when_all(
            fetch_and_sum(10, 20),
            fetch_and_sum(30, 40),
            fetch_and_sum(50, 60)
        );
    
    std::cout << "Results: " << result1 << ", " << result2 << ", " << result3 << "\n";
    std::cout << "Total: " << (result1 + result2 + result3) << "\n";
}

int main() {
    // Print first 10 Fibonacci numbers
    std::cout << "Fibonacci: ";
    int count = 0;
    for (auto n : fibonacci()) {
        std::cout << n << " ";
        if (++count >= 10) break;
    }
    std::cout << "\n";
    
    // Run async task
    cppcoro::sync_wait(process_parallel());
    return 0;
}
```

## Boost.Cobalt: The ASIO-Native Solution

Boost.Cobalt (formerly Boost.Async) is the Boost organization's answer to C++20 coroutines. It is built as a thin layer on top of Boost.ASIO, leveraging ASIO's battle-tested I/O infrastructure, executor model, and cancellation support.

**Key strengths:**
- **ASIO integration**: Every `cobalt::task<T>` runs on an ASIO `io_context`, enabling seamless integration with network I/O, timers, and signals
- **Channel-based communication**: `cobalt::channel<T>` for coroutine-to-coroutine message passing (like Go channels)
- **Active maintenance**: Part of Boost, with regular releases and LTS support
- **Cancellation**: Native ASIO cancellation slots propagate through coroutine chains
- **`co_main` entry point**: Simplifies application startup with `cobalt::main`

```cpp
#include <boost/cobalt.hpp>
#include <boost/asio.hpp>
#include <iostream>

namespace cobalt = boost::cobalt;
namespace asio = boost::asio;

// Coroutine: read sensor data with timeout
cobalt::task<double> read_sensor(asio::steady_timer& sensor, int id) {
    // Simulate sensor reading delay
    co_await sensor.async_wait(cobalt::use_op);
    sensor.expires_after(std::chrono::milliseconds(100));
    co_return 20.0 + (id * 1.5);
}

// Coroutine: process with channel communication
cobalt::task<void> sensor_aggregator(
    cobalt::channel<double>& readings,
    std::vector<double>& results
) {
    for (int i = 0; i < 5; ++i) {
        auto value = co_await readings.read();
        results.push_back(value);
        std::cout << "Received reading: " << value << "\n";
    }
}

// Main coroutine coordinates everything
cobalt::task<void> run_monitoring(asio::io_context& ctx) {
    cobalt::channel<double> readings(32);
    std::vector<double> results;
    
    // Spawn sensor reader
    cobalt::spawn(ctx, [&]() -> cobalt::task<void> {
        asio::steady_timer sensor(ctx, std::chrono::milliseconds(50));
        for (int i = 0; i < 5; ++i) {
            auto value = co_await read_sensor(sensor, i);
            co_await readings.write(value);
        }
        readings.close();
    }, asio::detached);
    
    // Spawn aggregator
    co_await sensor_aggregator(readings, results);
    
    // Calculate statistics
    double sum = 0;
    for (auto v : results) sum += v;
    std::cout << "Average: " << (sum / results.size()) << "\n";
}

cobalt::main co_main(int argc, char* argv[]) {
    asio::io_context ctx;
    co_await run_monitoring(ctx);
    co_return 0;
}
```

## concurrencpp: The Executor-First Approach

concurrencpp takes a fundamentally different approach — instead of being tied to a single I/O event loop, it provides a hierarchy of executors (thread pool, manual, inline, worker thread) that coroutines run on.

**Key strengths:**
- **Flexible executor model**: Run coroutines on thread pools, single threads, or custom executors
- **`concurrencpp::when_all` + `when_any`**: Powerful composition primitives
- **`concurrencpp::timer`**: Schedule coroutine execution after a delay or at regular intervals
- **Exception propagation**: Exceptions thrown in coroutines are captured and re-thrown when the result is consumed
- **Runtime polymorphism**: `concurrencpp::runtime` manages executor lifecycles

```cpp
#include "concurrencpp/concurrencpp.h"
#include <iostream>
#include <vector>

// Task: compute factorial with thread pool
concurrencpp::result<unsigned long long> factorial(unsigned int n) {
    if (n <= 1) co_return 1;
    co_return n * co_await factorial(n - 1);
}

// Task: parallel map-reduce pattern
concurrencpp::result<double> parallel_sum(
    std::shared_ptr<concurrencpp::thread_pool_executor> tpe,
    const std::vector<double>& data
) {
    std::vector<concurrencpp::result<double>> tasks;
    tasks.reserve(data.size());
    
    // Dispatch each element to the thread pool
    for (auto value : data) {
        tasks.push_back(tpe->submit([value]() -> double {
            // Simulate computation
            return value * value;
        }));
    }
    
    // Wait for all and sum
    auto results = co_await concurrencpp::when_all(tpe, tasks.begin(), tasks.end());
    double sum = 0;
    for (auto& result : results) {
        sum += result.get();
    }
    co_return sum;
}

int main() {
    concurrencpp::runtime runtime;
    
    // Compute factorial on thread pool
    auto result = runtime.thread_pool_executor()->submit([]() -> concurrencpp::result<unsigned long long> {
        co_return co_await factorial(10);
    });
    
    std::cout << "10! = " << result.get() << "\n";
    
    // Parallel computation
    std::vector<double> data = {1.0, 2.0, 3.0, 4.0, 5.0};
    auto sum = runtime.thread_pool_executor()->submit(
        [&runtime, &data]() -> concurrencpp::result<double> {
            co_return co_await parallel_sum(runtime.thread_pool_executor(), data);
        }
    );
    
    std::cout << "Sum of squares: " << sum.get() << "\n";
    return 0;
}
```

## Docker Dev Environment for Coroutine Testing

```dockerfile
# Dockerfile for C++20 coroutine development
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    g++-14 \
    cmake \
    git \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone concurrencpp
RUN git clone --depth 1 https://github.com/David-Haim/concurrencpp.git /opt/concurrencpp

# Clone cppcoro
RUN git clone --depth 1 https://github.com/lewissbaker/cppcoro.git /opt/cppcoro

COPY CMakeLists.txt .
COPY src/ src/

# Build with C++20 coroutine support
RUN cmake -B build -DCMAKE_CXX_STANDARD=20 -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build -j$(nproc)

CMD ["./build/coroutine_demo"]
```

## Choosing the Right Coroutine Library

| Use Case | Recommended Library | Rationale |
|----------|-------------------|-----------|
| Greenfield ASIO project | Boost.Cobalt | Native ASIO integration, maintained, Boost ecosystem |
| Learning coroutines | cppcoro | Simple API, excellent examples, established patterns |
| CPU-bound parallel computation | concurrencpp | Thread pool executors, `when_all` for fan-out |
| High-throughput network service | Boost.Cobalt | ASIO's proven I/O performance, cancellation support |
| Mixed I/O + CPU workloads | concurrencpp | Separate executors for I/O and compute |
| Legacy code modernization | cppcoro | Easier incremental adoption, `sync_wait` for bridging |

## FAQ

### Are C++20 coroutines as fast as hand-written state machines?

In most cases, yes. C++20 coroutines are implemented as compiler-generated state machines, and modern compilers (GCC 12+, Clang 15+) optimize coroutine frames aggressively. In benchmarks, coroutine-based async code typically achieves 90-98% of the throughput of hand-rolled callback-based state machines, with significantly less code and fewer bugs.

### How much heap memory does a coroutine frame consume?

A typical coroutine frame is 64-256 bytes, allocated once per coroutine invocation. Libraries like cppcoro and Boost.Cobalt support custom allocators (via `operator new` in the `promise_type`) to use arena or pool allocators, eliminating per-coroutine heap overhead in hot paths.

### Can I mix coroutine libraries in the same codebase?

Technically yes, but practically it creates maintenance headaches. Each library has its own `task<T>` type with different semantics — you cannot `co_await` a `cobalt::task` from a `concurrencpp::result`. Choose one library as your primary coroutine framework and use it consistently. If you must bridge libraries, use `sync_wait`-style primitives at the boundary, but accept the performance cost.

### Does Boost.Cobalt require the full Boost distribution?

Boost.Cobalt depends on Boost.ASIO, Boost.System, and Boost.Container. With Boost's BCP tool, you can extract just these modules (about 3 MB of headers). Alternatively, use a package manager like Conan or vcpkg which installs Boost in a modular fashion.

### How do I debug a suspended coroutine?

GDB 12+ and LLDB 16+ include experimental coroutine frame inspection. You can inspect the `promise_type` and local variables stored in the coroutine frame. With Boost.Cobalt, enable ASIO handler tracking (`-DBOOST_ASIO_ENABLE_HANDLER_TRACKING`) for detailed logs of which coroutines are suspended and where. concurrencpp provides automatic stack trace capture on exceptions.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++20 Coroutine Libraries: cppcoro vs Boost.Cobalt vs concurrencpp",
  "description": "Comprehensive comparison of C++20 coroutine libraries: cppcoro, Boost.Cobalt, and concurrencpp. Includes code examples, Docker dev environment setup, executor models, and performance analysis.",
  "datePublished": "2026-06-22",
  "dateModified": "2026-06-22",
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

For more C++ concurrency topics, see our [C-level coroutine libraries comparison](../2026-06-21-coroutine-libraries-libaco-greenlet-libco-boost-context/) and [async I/O runtime libraries guide](../2026-06-20-async-io-runtime-libraries-libuv-boost-asio-tokio/). For task parallelism patterns, check our [taskflow and thread pool comparison](../2026-06-21-cpp-task-parallelism-libraries-taskflow-onetbb-threadpool/).
