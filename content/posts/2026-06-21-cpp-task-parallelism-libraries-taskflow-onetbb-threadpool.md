---
title: "Self-Hosted C++ Task Parallelism: Taskflow vs oneTBB vs BS::thread_pool"
date: "2026-06-21"
tags: ["cplusplus", "developer-tools", "parallelism", "multithreading", "concurrency", "open-source", "task-scheduling"]
draft: false
---

## Introduction

Writing correct, efficient parallel C++ code remains one of the hardest challenges in systems programming. Raw `std::thread` and manual mutex management lead to deadlocks, race conditions, and suboptimal CPU utilization. Modern task parallelism libraries abstract thread management behind high-level APIs — you describe *what* work needs to be done and *which tasks depend on each other*, while the runtime handles thread pools, work stealing, and load balancing automatically.

We compare three leading open-source C++ task parallelism libraries: **Taskflow** (12,018 stars), **oneTBB** (6,676 stars), and **BS::thread_pool** (3,012 stars). Each targets a different level of abstraction: Taskflow provides a full directed acyclic graph (DAG) task programming model, oneTBB is Intel's industrial-strength parallel algorithms framework, and BS::thread_pool is a minimal, elegant thread pool with near-zero learning curve.

| Feature | Taskflow | oneTBB | BS::thread_pool |
|---|---|---|---|
| **GitHub Stars** | 12,018 | 6,676 | 3,012 |
| **Last Updated** | Jun 2026 | Jun 2026 | Jan 2026 |
| **Header-only** | Yes | No (shared library) | Yes |
| **C++ Standard** | C++17 | C++17 | C++17/20 |
| **Programming Model** | Task graphs (DAG) | Parallel algorithms + flow graph | Simple thread pool |
| **Work Stealing** | Yes (lock-free queues) | Yes (advanced scheduler) | Yes |
| **GPU Support** | Yes (CUDA task graphs) | Yes (SYCL/oneAPI) | No |
| **Task Prioritization** | Static priorities | Dynamic priorities | FIFO only |
| **Dependencies** | DAG edges + async/await | TBB flow graph nodes | None |
| **Profiling** | Built-in (Chrome Trace) | VTune integration | No |
| **License** | MIT | Apache-2.0 | MIT |

## Taskflow: Task Graph Parallelism

Taskflow by Tsung-Wei Huang is designed for expressing complex parallel workloads as task dependency graphs. You create tasks (nodes) and dependencies (edges), and the runtime schedules everything across available CPU cores. This model excels at irregular parallelism — workloads where task durations vary and dependencies are non-trivial.

**Integration (CMake):**

```cmake
include(FetchContent)
FetchContent_Declare(
  Taskflow
  GIT_REPOSITORY https://github.com/taskflow/taskflow.git
  GIT_TAG v3.9.0
)
FetchContent_MakeAvailable(Taskflow)
target_link_libraries(my_app PRIVATE Taskflow)
```

**Task graph example:**

```cpp
#include <taskflow/taskflow.hpp>

int main() {
    tf::Executor executor;  // defaults to std::thread::hardware_concurrency()
    tf::Taskflow taskflow("Image Pipeline");

    // Define tasks
    auto [load, decode, resize, sharpen, encode, save] = taskflow.emplace(
        []() { return load_image("input.png"); }, // load
        [](auto& img) { img.decode(); },          // decode
        [](auto& img) { img.resize(1920, 1080); }, // resize
        [](auto& img) { img.sharpen(1.5); },       // sharpen
        [](auto& img) { return img.encode(); },    // encode
        [](auto& data) { save_file("output.jpg", data); }  // save
    );

    // Chain dependencies: load -> decode -> resize -> sharpen -> encode -> save
    load.precede(decode);
    decode.precede(resize);
    resize.precede(sharpen);
    sharpen.precede(encode);
    encode.precede(save);

    executor.run(taskflow).wait();
    std::cout << "Pipeline completed." << std::endl;
    return 0;
}
```

Taskflow's killer feature is its **profiling and visualization**. You can dump any task graph to a Chrome Trace JSON file and view the execution timeline — each task gets a colored bar showing its start, end, and which CPU core ran it:

```cpp
tf::Executor executor(4);
tf::Taskflow taskflow;
// ... define tasks ...
executor.run(taskflow).wait();

// Dump timeline for Chrome tracing
taskflow.dump(std::cout);
```

This is invaluable for identifying bottlenecks and unbalanced workloads in production pipelines.

## oneTBB: Intel's Industrial Framework

oneTBB (oneAPI Threading Building Blocks) is Intel's battle-tested parallelism library, originally developed for their compiler toolchain and now open-sourced under Apache 2.0. It provides three layers: low-level concurrent containers (`concurrent_hash_map`, `concurrent_queue`), mid-level parallel algorithms (`parallel_for`, `parallel_reduce`, `parallel_sort`), and high-level flow graphs for pipeline and dependency-driven parallelism.

**Integration (system package):**

```bash
# Ubuntu/Debian
sudo apt install libtbb-dev

# macOS
brew install tbb

# CMakeLists.txt
find_package(TBB REQUIRED)
target_link_libraries(my_app PRIVATE TBB::tbb)
```

**Parallel for example:**

```cpp
#include <tbb/parallel_for.h>
#include <tbb/blocked_range.h>
#include <vector>

void process_frames(std::vector<Frame>& frames) {
    tbb::parallel_for(tbb::blocked_range<size_t>(0, frames.size()),
        [&](const tbb::blocked_range<size_t>& r) {
            for (size_t i = r.begin(); i != r.end(); ++i) {
                frames[i].denoise();
                frames[i].color_correct();
                frames[i].apply_lut();
            }
        });
}
```

**Flow graph (pipeline) example:**

```cpp
#include <tbb/flow_graph.h>

void pipeline_example() {
    tbb::flow::graph g;

    // Source node: generates work items
    tbb::flow::source_node<int> source(g,
        [](int& v) -> bool {
            static int i = 0;
            if (i < 100) { v = i++; return true; }
            return false;
        });

    // Processing node: runs in parallel (unlimited concurrency)
    tbb::flow::function_node<int, int> process(g,
        tbb::flow::unlimited,
        [](int v) -> int {
            return v * v;  // expensive computation
        });

    // Sink node: collects results
    int sum = 0;
    tbb::flow::function_node<int> sink(g,
        tbb::flow::serial,
        [&sum](int v) { sum += v; });

    tbb::flow::make_edge(source, process);
    tbb::flow::make_edge(process, sink);

    source.activate();
    g.wait_for_all();

    std::cout << "Sum of squares: " << sum << std::endl;
}
```

oneTBB's strongest advantage is its **ecosystem integration**. It powers Intel VTune Profiler, works with Intel's oneAPI GPU programming (SYCL), and is packaged by every major Linux distribution. For enterprises already in the Intel ecosystem, oneTBB is the obvious default.

**Limitation:** oneTBB is not header-only — it requires linking against a shared library (~2MB on Linux). For small utilities where binary size matters, this is a consideration.

## BS::thread_pool: Minimal and Elegant

BS::thread_pool by Barak Shoshany is the polar opposite of oneTBB: a single header file (~500 lines) that provides a clean, modern thread pool with zero dependencies beyond C++17. If you just need to parallelize a loop without learning a framework, this is your library.

**Integration:**

```cmake
# Just copy the header or use FetchContent
include(FetchContent)
FetchContent_Declare(
  thread_pool
  GIT_REPOSITORY https://github.com/bshoshany/thread-pool.git
  GIT_TAG v4.1.0
)
FetchContent_MakeAvailable(thread_pool)
target_include_directories(my_app PRIVATE ${thread_pool_SOURCE_DIR})
```

**Usage:**

```cpp
#include "BS_thread_pool.hpp"

int main() {
    BS::thread_pool pool;  // defaults to hardware concurrency

    // Submit individual tasks
    auto future = pool.submit_task(
        [] { return expensive_computation(42); }
    );
    int result = future.get();

    // Parallelize a loop
    std::vector<double> data(1'000'000);
    pool.detach_loop<size_t>(0, data.size(),
        [&](size_t start, size_t end) {
            for (size_t i = start; i < end; ++i) {
                data[i] = std::sqrt(static_cast<double>(i));
            }
        });

    // Parallel for-each with index
    pool.for_loop(0, data.size(),
        [&](int start, int end) {
            // process chunk [start, end)
        });

    pool.wait();
    return 0;
}
```

The library supports task detaching, future-based result retrieval, pausing/resuming the pool, and changing thread count at runtime. The API surface is tiny — you can learn it in 5 minutes. For one-off scripts, build systems, or tools that need parallel execution but do not warrant a full parallelism framework, BS::thread_pool is hard to beat.

**Limitation:** No task dependencies, no priority scheduling, no GPU offloading. If your workload has complex DAG-structured parallelism, you need Taskflow or oneTBB.

## Performance Considerations

| Workload Type | Best Fit |
|---|---|
| Embarrassingly parallel loops | BS::thread_pool or oneTBB `parallel_for` |
| Pipeline processing (stages) | oneTBB flow graph |
| Irregular task DAGs | Taskflow |
| GPU-accelerated workloads | Taskflow (CUDA) or oneTBB (SYCL) |
| Minimal binary size | BS::thread_pool |
| Distributed across cluster | Taskflow (MPI integration planned) |

Taskflow benchmarks demonstrate near-linear speedup on 64-core machines for workloads with sufficient parallelism. oneTBB's work-stealing scheduler has been tuned over 15+ years for Intel CPUs and shows excellent cache locality. BS::thread_pool is competitive for simple parallel loops but lacks the advanced load balancing that helps with non-uniform task sizes.

If you are working on applications that benefit from lock-free data structures in the hot path, see our [lock-free data structure comparison](../2026-06-20-lock-free-data-structure-libraries-concurrentqueue-readerwriterqueue-boost/). For managing memory allocation patterns in multi-threaded code, our [memory allocators guide](../2026-06-02-memory-allocators-jemalloc-tcmalloc-mimalloc-guide/) covers jemalloc, tcmalloc, and mimalloc. And for async I/O patterns that complement CPU parallelism, check our [async I/O runtime comparison](../2026-06-20-async-io-runtime-libraries-libuv-boost-asio-tokio/).

## FAQ

### Can I use Taskflow and oneTBB together in the same application?

Technically yes, but it is rarely advisable. Both libraries manage their own thread pools, and having two independent thread pools competing for the same CPU cores leads to oversubscription — more threads than hardware threads, causing excessive context switching. If you need both Taskflow's DAG model and oneTBB's parallel algorithms, restrict each to a limited number of threads (e.g., 4 cores each on an 8-core machine) or use a single framework for all parallelism.

### Which library has the lowest latency for sub-millisecond tasks?

BS::thread_pool. Its task submission path is extremely thin — essentially a lock-free push onto a queue followed by a condition variable signal. Taskflow adds a small overhead (~100-200ns) for dependency resolution. oneTBB's flow graph has the most overhead because of its advanced scheduling logic. For high-frequency trading or real-time audio processing with sub-millisecond task durations, use BS::thread_pool or raw threads with a spinlock-based queue.

### How do these libraries handle exceptions thrown inside tasks?

Taskflow propagates exceptions via `std::exception_ptr` — if any task throws, `executor.run(taskflow).wait()` will rethrow the first exception after all currently running tasks complete. oneTBB captures exceptions similarly and rethrows a `tbb::captured_exception` (or the original exception in newer versions). BS::thread_pool stores exceptions in the returned future and throws on `future.get()`. All three libraries guarantee that the process does not silently swallow errors.

### What is the minimum C++ standard required?

Taskflow and oneTBB require C++17. BS::thread_pool requires C++17 for its core API but has optional C++20 features (jthread integration, std::barrier). If you are stuck on C++14, you can use older versions of oneTBB (tbb 2020.x) or hand-roll a thread pool with `std::async`. For C++11, backporting is non-trivial — consider upgrading your compiler toolchain.

### Are these libraries suitable for embedded Linux or ARM SBCs?

Yes, all three compile and run on ARM64 (Raspberry Pi 4, Jetson Nano, AWS Graviton). oneTBB has the widest platform support (x86, ARM, RISC-V through oneAPI). Taskflow is tested on ARM. BS::thread_pool is pure standard C++ and works anywhere `std::thread` is available. For single-board computers with 2-4 cores, BS::thread_pool is usually sufficient — the overhead of Taskflow's DAG engine or oneTBB's flow graph is not justified on low-core-count systems.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Task Parallelism: Taskflow vs oneTBB vs BS::thread_pool",
  "description": "In-depth comparison of three leading C++ task parallelism libraries: Taskflow, oneTBB, and BS::thread_pool. Covers task graph programming, parallel algorithms, thread pool usage, CMake integration, and performance considerations.",
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
