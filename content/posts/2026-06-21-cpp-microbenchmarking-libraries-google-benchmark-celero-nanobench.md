---
title: "Self-Hosted C++ Microbenchmarking Libraries: Google Benchmark vs Celero vs nanobench vs Hayai"
date: "2026-06-21"
tags: ["c++", "benchmarking", "performance", "developer-tools", "open-source", "profiling"]
draft: false
---

Performance is the lifeblood of systems programming. Whether you are optimizing a database engine, a game physics loop, or a WebSocket server, you need to measure how fast your code actually runs — not just guess. **C++ microbenchmarking libraries** give you precisely that: a scientific, reproducible way to time small code snippets across hundreds of thousands of iterations and determine which implementation is faster.

But not all C++ benchmarking libraries are created equal. Some prioritize statistical rigor with p-values and confidence intervals, while others aim for minimal overhead and single-header integration. In this guide, we compare **four leading C++ microbenchmarking frameworks** — Google Benchmark, Celero, nanobench, and Hayai — covering their architecture, ease of use, statistical features, and real-world suitability.

## Overview of C++ Microbenchmarking Libraries

| Feature | Google Benchmark | Celero | nanobench | Hayai |
|---------|-----------------|--------|-----------|-------|
| **GitHub Stars** | 10,244 | 861 | 1,704 | 363 |
| **Last Updated** | June 2026 | June 2026 | Oct 2024 | Aug 2019 |
| **Primary Language** | C++ | C++ | C++ | C++ |
| **Header-Only** | No (lib) | No (lib) | Yes (single header) | Yes (single header) |
| **CMake Integration** | `FetchContent`, `find_package` | `FetchContent`, `find_package` | Copy header | Copy header |
| **Statistical Output** | Mean, median, stddev | Mean, variance, baseline | Mean, median, stddev, MAD | Mean, min, max |
| **Fixture Support** | Yes (`BENCHMARK_F`) | Yes (`CELERO_MAIN`) | No (manual) | Yes (`HAYAI_FIXTURE`) |
| **Custom Counters** | Yes (user counters) | Yes (user metrics) | Limited | No |
| **Template Benchmarks** | Yes | No | No | No |
| **License** | Apache 2.0 | Apache 2.0 | MIT | Apache 2.0 |

## Google Benchmark: The Industry Standard

**Google Benchmark** ([github.com/google/benchmark](https://github.com/google/benchmark)) is the most widely adopted C++ microbenchmark library, maintained by Google. With over 10,000 stars and continuous updates (last commit June 2026), it is the de facto choice for performance-critical projects like Chromium, LLVM, and Abseil.

Its hallmark is **statistical rigor**. Google Benchmark runs each benchmark for a minimum time (configurable), repeats the measurement, and reports the mean, median, and standard deviation. The `BENCHMARK` macro handles warmup and iteration count automatically, preventing common pitfalls like dead-code elimination:

```cpp
#include <benchmark/benchmark.h>
#include <vector>
#include <algorithm>

static void BM_VectorSort(benchmark::State& state) {
    std::vector<int> data(state.range(0));
    for (auto _ : state) {
        state.PauseTiming();
        std::generate(data.begin(), data.end(), std::rand);
        state.ResumeTiming();
        std::sort(data.begin(), data.end());
    }
    state.SetComplexityN(state.range(0));
}
BENCHMARK(BM_VectorSort)
    ->RangeMultiplier(2)->Range(1<<10, 1<<20)
    ->Complexity();

BENCHMARK_MAIN();
```

**Integration** is straightforward via CMake:
```cmake
include(FetchContent)
FetchContent_Declare(
  benchmark
  GIT_REPOSITORY https://github.com/google/benchmark.git
  GIT_TAG v1.9.0
)
FetchContent_MakeAvailable(benchmark)
target_link_libraries(my_benchmarks PRIVATE benchmark::benchmark)
```

**Key strengths:**
- Automatic iteration count scaling (guarantees statistically significant results)
- Template benchmarks (`BENCHMARK_TEMPLATE`) for testing multiple types
- O(n) complexity analysis with Big-O notation
- User-defined counters for custom metrics (cache misses, allocations)
- Integration with `perf` and hardware performance counters

**Limitations:** Larger binary (links as a library, ~200KB+), steeper CMake setup than header-only alternatives, and the output format requires post-processing for human-friendly dashboards.

## Celero: Baseline-Relative Comparisons

**Celero** ([github.com/DigitalInBlue/Celero](https://github.com/DigitalInBlue/Celero)) takes a different philosophical approach. Instead of focusing on raw timing numbers, it centers the workflow around **baseline comparisons**. You designate one benchmark as the baseline, and Celero automatically computes how each subsequent benchmark performs relative to it — expressed as iterations per second and percentage difference.

```cpp
#include <celero/Celero.h>
#include <algorithm>
#include <vector>

CELERO_MAIN

class SortFixture : public celero::TestFixture {
public:
    std::vector<int> data;
    void setUp(int64_t experimentValue) override {
        data.resize(experimentValue);
        std::generate(data.begin(), data.end(), std::rand);
    }
};

BASELINE_F(QuickSort, Baseline, SortFixture, 10, 100000) {
    std::sort(celero::thisFixture->data.begin(),
              celero::thisFixture->data.end());
}

BENCHMARK_F(QuickSort, StableSort, SortFixture, 10, 100000) {
    std::stable_sort(celero::thisFixture->data.begin(),
                     celero::thisFixture->data.end());
}
```

Celero's output table is immediately actionable:

```
|  Experiment  |  Baseline  |  us/Op  |  Iterations  |
|--------------|------------|---------|--------------|
| Baseline     |  1.00000   |  45.23  |  100000      |
| StableSort   |  0.78452   |  57.65  |  100000      |
```

**Key strengths:**
- Clean baseline-relative comparison workflow
- Built-in CSV and JUnit XML output (ready for CI/CD dashboards)
- `TestFixture` class for shared setup/teardown across benchmarks
- Simple CMake integration with `find_package`

**Limitations:** Smaller community (861 stars), fewer statistical features than Google Benchmark (no percentile distribution or Big-O analysis), and the baseline-centric model may not suit all use cases.

## nanobench: Minimalist, Header-Only Precision

**nanobench** ([github.com/martinus/nanobench](https://github.com/martinus/nanobench)) is a **single-header** library that packs remarkable statistical power into a tiny footprint. Developed by Martin Ankerl, it uses the `rdtsc` instruction (or `std::chrono` on non-x86) for cycle-accurate timing and renders beautiful terminal tables with percentile breakdowns.

The entire library is one header — drag it into your project and you are benchmarking:

```cpp
#define ANKERL_NANOBENCH_IMPLEMENT
#include <nanobench.h>
#include <unordered_set>
#include <set>

int main() {
    ankerl::nanobench::Bench bench;
    bench.title("Set Insertion Performance")
         .relative(true)
         .minEpochIterations(200000);

    std::unordered_set<int> uset;
    bench.run("std::unordered_set", [&] {
        uset.insert(42);
        uset.erase(42);
    });

    std::set<int> oset;
    bench.run("std::set", [&] {
        oset.insert(42);
        oset.erase(42);
    });
}
```

Output includes the **MAD** (Median Absolute Deviation), p50/p90/p95/p99 percentiles, instructions per cycle, and branch mispredictions when `perf` is available.

**Key strengths:**
- Zero-dependency single header — just `#include "nanobench.h"`
- Rich terminal output with ASCII charts, percentiles, and relative speedup
- Hardware counter integration via Linux `perf` (instructions, cycles, branches, cache misses)
- Built-in "doNotOptimizeAway" to prevent dead-code elimination

**Limitations:** No built-in fixture pattern (manual setup required for shared state), last updated October 2024, and x86-focused (some features rely on `rdtsc`).

## Hayai: The Lightweight Veteran

**Hayai** ([github.com/nickbruun/hayai](https://github.com/nickbruun/hayai)) was one of the earliest C++ microbenchmark frameworks, inspired by Ruby's `Benchmark` library. It is header-only, dead simple, and has not changed much since 2019 — which makes it ideal for projects that value stability over new features.

```cpp
#include <hayai.hpp>
#include <vector>
#include <algorithm>

class SortFixture : public ::hayai::Fixture {
public:
    virtual void SetUp() { data.resize(10000); }
    virtual void TearDown() {}
    std::vector<int> data;
};

BENCHMARK_F(SortFixture, StdSort, 10, 100) {
    std::sort(data.begin(), data.end());
}

BENCHMARK_F(SortFixture, StableSort, 10, 100) {
    std::stable_sort(data.begin(), data.end());
}

int main() {
    hayai::ConsoleOutputter consoleOutputter;
    hayai::Benchmarker::AddOutputter(consoleOutputter);
    hayai::Benchmarker::RunAllTests();
    return 0;
}
```

**Key strengths:**
- Extremely simple API — `HAYAI_FIXTURE`, `BENCHMARK`, `BENCHMARK_F` macros
- Familiar xUnit-style fixture pattern
- Minimal overhead for basic timing needs
- Header-only, no build system configuration needed

**Limitations:** Effectively unmaintained (last update August 2019), no statistical analysis beyond mean/min/max, no complexity analysis, and limited template support. Best suited for legacy codebases or environments where stability is paramount.

## Integration with Build System and CI/CD Pipeline

All four libraries integrate with CMake, but the pattern differs. Here is a unified CMakeLists.txt for a project that conditionally builds benchmarks:
```cmake
cmake_minimum_required(VERSION 3.16)
project(PerformanceAnalysis LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# Option 1: Google Benchmark (library, most features)
if(USE_GOOGLE_BENCHMARK)
    include(FetchContent)
    FetchContent_Declare(benchmark
        GIT_REPOSITORY https://github.com/google/benchmark.git
        GIT_TAG v1.9.0
    )
    FetchContent_MakeAvailable(benchmark)
    add_executable(bm_google gbench.cpp)
    target_link_libraries(bm_google PRIVATE benchmark::benchmark)
endif()

# Option 2: nanobench (header-only, zero config)
if(USE_NANOBENCH)
    include(FetchContent)
    FetchContent_Declare(nanobench
        URL https://raw.githubusercontent.com/martinus/nanobench/master/src/include/nanobench.h
    )
    FetchContent_Populate(nanobench)
    add_executable(bm_nano nanobench_test.cpp)
    target_include_directories(bm_nano PRIVATE ${nanobench_SOURCE_DIR})
endif()
```

When integrating with CI, Google Benchmark's `--benchmark_format=json` and Celero's CSV/JUnit output are particularly useful. See our [self-hosted CI/CD dashboard guide](../2026-05-05-gocd-vs-buildbot-vs-jenkins-self-hosted-cicd-dashboard-guide/) for automated benchmark regression detection.

## Choosing the Right Library for Your Project

| Use Case | Recommended Library | Reason |
|----------|-------------------|--------|
| Large production project with statistical rigor needs | **Google Benchmark** | Industry standard, active maintenance, complexity analysis |
| Quick, single-file performance checks | **nanobench** | Zero config, beautiful terminal output, hardware counters |
| Baseline-relative comparison workflow | **Celero** | Native baseline comparisons, JUnit output for CI |
| Legacy codebase needing minimal dependency | **Hayai** | Simple API, unmaintained but stable, small footprint |
| Template-heavy benchmarks | **Google Benchmark** | `BENCHMARK_TEMPLATE` for multi-type benchmarks |
| CI dashboard integration | **Celero** or **Google Benchmark** | Native CSV/JUnit output or `--benchmark_format=json` |

## Why Invest in Microbenchmarking Infrastructure?

Regular microbenchmarking catches performance regressions before they reach production. In a study of the Chromium project, Google Benchmark detected over **1,200 performance regressions** in a single year — changes that would have gone unnoticed with integration tests alone. Setting up a benchmarking harness takes an afternoon and pays dividends for the lifetime of the project.

For broader performance analysis, complement microbenchmarks with [system-level profiling tools](../2026-04-18-grafana-pyroscope-vs-parca-vs-profefe-self-hosted-continuous-profiling-guide-2026/) to identify hotspots, and [database benchmarking frameworks](../pgbench-sysbench-hammerdb-self-hosted-database-benchmarking-guide-2026/) for infrastructure-level performance testing. For build system integration, our [self-hosted build systems comparison](../2026-04-29-bazel-vs-pants-vs-please-self-hosted-build-systems-guide-2026/) covers Bazel, Pants, and Please for repeatable benchmark environments.

## FAQ

### What is the difference between microbenchmarking and profiling?
**Microbenchmarking** measures the execution time of small, isolated code snippets (a single function, an algorithm) under controlled conditions. **Profiling** captures a holistic view of where an entire application spends time — it identifies hotspots but cannot isolate individual operations as precisely. Use microbenchmarks to compare two implementations and profiling to find what to optimize.

### Does Google Benchmark prevent dead-code elimination?
Yes. Google Benchmark uses the `benchmark::DoNotOptimize()` helper and the `state.PauseTiming()`/`state.ResumeTiming()` pattern to prevent the compiler from optimizing away the code being measured. nanobench also provides `doNotOptimizeAway()`. Always verify with `-O2` or `-O3` builds.

### Can I use nanobench on ARM or RISC-V?
nanobench's `rdtsc` fallback uses `std::chrono::high_resolution_clock` on non-x86 platforms, so it works on ARM and RISC-V. However, hardware counter support (instructions, cycles) requires Linux `perf` and is platform-dependent.

### Which library has the smallest binary overhead?
**nanobench** and **Hayai** are header-only and add negligible binary size (the timing code is inlined). Google Benchmark links as a static library (~200KB) and Celero also links as a library.

### How often should I run microbenchmarks?
Run microbenchmarks on every commit that touches performance-sensitive code — ideally in CI. Google Benchmark supports the `--benchmark_min_time` and `--benchmark_repetitions` flags to balance statistical significance with CI time budgets. For daily trend tracking, store benchmark results in a time-series database and use regression alerts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted C++ Microbenchmarking Libraries: Google Benchmark vs Celero vs nanobench vs Hayai",
  "description": "Comprehensive comparison of four C++ microbenchmarking libraries — Google Benchmark, Celero, nanobench, and Hayai — covering statistical rigor, CMake integration, ease of use, and CI/CD pipeline integration for performance regression detection.",
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
