---
title: "Self-Hosted Python Benchmarking: pytest-benchmark vs CodSpeed vs pyperf vs airspeed-velocity"
date: "2026-07-02"
tags: ["python", "benchmarking", "performance", "testing", "pytest", "developer-tools", "optimization"]
draft: false
---

## Introduction

Performance regressions are among the most painful bugs to diagnose. A function that was fast yesterday becomes slow today, and nobody knows why. Without systematic benchmarking integrated into your development workflow, performance degradation creeps in silently — one pull request at a time — until your application feels sluggish and your users notice before you do.

Python's benchmarking ecosystem provides several tools for measuring, tracking, and preventing performance regressions. This guide compares four leading solutions: **pytest-benchmark** (the pytest-integrated standard), **CodSpeed** (CI-native performance tracking), **pyperf** (the PSF's statistical benchmark toolkit), and **airspeed-velocity** (for tracking performance across git commits).

## Comparison Table

| Feature | pytest-benchmark | CodSpeed | pyperf | airspeed-velocity |
|---------|-----------------|----------|--------|-------------------|
| **Type** | pytest plugin | CI platform + pytest plugin | Standalone toolkit | CLI for git bisection |
| **Statistical Rigor** | Basic (min/max/mean) | Advanced (with CI integration) | Advanced (outlier detection, warmup) | Basic (timing comparison) |
| **CI Integration** | Native (pytest) | Native (GitHub Actions) | Manual (scripts) | Manual (git bisect) |
| **Historical Tracking** | No (single run) | Yes (dashboard) | No (single run) | Yes (across commits) |
| **GitHub Stars** | ~1,500 | ~300 | ~1,000 | ~900 |
| **JSON Output** | Yes | Yes | Yes | Yes |
| **Calibration** | No | Yes | Yes (CPU calibration) | No |
| **Web UI** | No | Yes (dashboard) | No | Limited (ASV web) |
| **Best For** | Unit-benchmarking in CI | Performance regression prevention | Scientific benchmarking | Git-based regression hunting |

## pytest-benchmark: The Pytest-Native Standard

pytest-benchmark is the most widely adopted Python benchmarking tool. It integrates directly into pytest, allowing you to write benchmarks alongside your tests.

**Installation:**

```bash
pip install pytest-benchmark
```

**Basic Usage:**

```python
# test_benchmarks.py
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def fibonacci_iterative(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def test_fib_benchmark(benchmark):
    """Benchmark the iterative Fibonacci implementation."""
    result = benchmark(fibonacci_iterative, 20)
    assert result == 6765

def test_comparison(benchmark):
    """Compare two implementations side by side."""
    # pytest-benchmark will run this N times and collect stats
    @benchmark
    def sort_builtin():
        return sorted([5, 3, 1, 4, 2] * 1000)

def test_with_setup(benchmark):
    """Benchmark with setup/teardown."""
    data = list(range(10000))

    @benchmark
    def with_setup():
        # Setup happens before each iteration
        local_data = data.copy()
        return sorted(local_data)
```

**Running benchmarks:**

```bash
# Run all benchmarks
pytest --benchmark-only

# Compare against a saved baseline
pytest --benchmark-only --benchmark-autosave
pytest --benchmark-only --benchmark-compare=0001

# Output JSON for programmatic analysis
pytest --benchmark-only --benchmark-json=benchmarks.json

# Run with specific options
pytest --benchmark-only --benchmark-min-rounds=10 --benchmark-warmup=on
```

pytest-benchmark outputs a detailed comparison table with min, max, mean, median, interquartile range, and standard deviation. It automatically detects outliers and marks them in the output, making it easy to spot noisy benchmarks.

```python
# Fixture-based benchmarking with parametrize
import pytest

@pytest.mark.parametrize("size", [100, 1000, 10000])
def test_sort_scaling(benchmark, size):
    import random
    data = [random.random() for _ in range(size)]
    result = benchmark(sorted, data)
```

## CodSpeed: CI-Native Performance Tracking

CodSpeed takes a different approach: rather than a one-shot benchmarking tool, it's a continuous performance tracking platform that integrates with GitHub Actions. Every PR automatically runs benchmarks against the main branch, and CodSpeed reports whether the PR introduced performance regressions.

**Installation:**

```bash
pip install pytest-codspeed
```

**Setup (GitHub Actions):**

```yaml
name: Performance Benchmarks
on: [push, pull_request]

jobs:
  benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pytest pytest-codspeed

      - name: Run benchmarks
        uses: CodSpeedHQ/action@v3
        with:
          run: pytest tests/ --codspeed
          token: ${{ secrets.CODSPEED_TOKEN }}
```

**Writing CodSpeed benchmarks:**

```python
# test_performance.py
def process_data(items):
    return [item * 2 for item in items if item > 0]

def test_process_large_list(benchmark):
    data = list(range(100000))
    benchmark(process_data, data)

def test_string_operations(benchmark):
    text = "hello world " * 1000
    benchmark(str.upper, text)
```

CodSpeed's key advantage is its calibration system — it measures your CI runner's baseline performance and normalizes results, eliminating noise from shared CI infrastructure. It provides a web dashboard showing performance trends over time, PR-level regression detection, and per-function performance profiles.

## pyperf: The PSF's Statistical Toolkit

pyperf is the Python Software Foundation's benchmarking toolkit, designed for statistical rigor. It handles CPU calibration, process isolation, warmup rounds, and outlier detection, making it ideal for precise benchmarking where measurement noise could mask real differences.

**Installation:**

```bash
pip install pyperf
```

**Writing Benchmarks:**

```python
# bench.py
import pyperf

def bench_list_comprehension(loops, n):
    """Benchmark list comprehension vs loop."""
    range_it = range(n)
    t0 = pyperf.perf_counter()

    for _ in range(loops):
        [i * 2 for i in range_it]

    return pyperf.perf_counter() - t0

def bench_for_loop(loops, n):
    """Benchmark explicit for loop."""
    range_it = range(n)
    t0 = pyperf.perf_counter()

    for _ in range(loops):
        result = []
        for i in range_it:
            result.append(i * 2)

    return pyperf.perf_counter() - t0

if __name__ == "__main__":
    runner = pyperf.Runner()

    runner.bench_time_func(
        'list_comprehension',
        bench_list_comprehension,
        10000,  # n
    )

    runner.bench_time_func(
        'for_loop',
        bench_for_loop,
        10000,
    )
```

**Running:**

```bash
# Run benchmark with automatic calibration
python3 bench.py -o results.json

# Compare two benchmark results
python3 -m pyperf compare_to results1.json results2.json --table

# Show detailed statistics
python3 -m pyperf stats results.json
```

pyperf's output includes calibrated timings, outlier detection, and statistical significance testing. It can detect differences as small as 1-2% between benchmark runs with high confidence. For scientific benchmarking where correctness matters more than convenience, pyperf is the gold standard.

## airspeed-velocity: Git-Based Performance Tracking

airspeed-velocity (ASV) takes a unique approach: it benchmarks your code across git commits, making it ideal for finding exactly which commit introduced a performance regression.

**Installation:**

```bash
pip install asv
```

**Setup:**

```bash
# Initialize ASV configuration
asv init
# or for existing projects:
asv quickstart
```

**Configuration (asv.conf.json):**

```json
{
  "version": 1,
  "project": "my-project",
  "project_url": "https://github.com/user/repo",
  "repo": ".",
  "branches": ["main"],
  "environment_type": "virtualenv",
  "matrix": {
    "req": {
      "numpy": [""],
      "pandas": [""]
    }
  },
  "benchmark_dir": "benchmarks",
  "results_dir": "results",
  "html_dir": "asv-html"
}
```

**Writing ASV Benchmarks:**

```python
# benchmarks/bench_example.py
class TimeSuite:
    """Benchmark with setup."""
    def setup(self):
        self.data = list(range(100000))

    def time_sort(self):
        sorted(self.data)

    def time_filter(self):
        [x for x in self.data if x % 2 == 0]

    def mem_list(self):
        """Track memory usage."""
        return [0] * 100000

class ScalingSuite:
    params = [100, 1000, 10000, 100000]

    def setup(self, n):
        self.data = list(range(n))

    def time_sort(self, n):
        sorted(self.data)
```

**Running:**

```bash
# Run benchmarks on current commit
asv run

# Compare across a range of commits
asv run v1.0..v2.0

# Find the commit that caused a regression
asv find_regression v1.0..v2.0

# Generate HTML report
asv publish
asv preview
```

ASV's web interface shows performance timelines, making it straightforward to visualize when regressions were introduced and by which commits. This makes it invaluable for post-mortem analysis of performance bugs.

## CI Integration Pattern

For comprehensive performance regression detection, combine multiple tools:

```yaml
# .github/workflows/benchmarks.yml
name: Performance CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  pytest-bench:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-benchmark
      - name: Run benchmarks
        run: pytest benchmarks/ --benchmark-only --benchmark-json=results.json
      - name: Compare with main
        run: |
          git fetch origin main
          git checkout origin/main
          pytest benchmarks/ --benchmark-only --benchmark-save=main
          git checkout -
          pytest benchmarks/ --benchmark-only --benchmark-compare=main --benchmark-compare-fail=mean:10%

  codspeed:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-codspeed
      - uses: CodSpeedHQ/action@v3
        with:
          run: pytest tests/ --codspeed
          token: ${{ secrets.CODSPEED_TOKEN }}
```

## Why Self-Host Your Benchmarking Pipeline?

Performance benchmarking should be part of your CI pipeline, not an afterthought. Self-hosted benchmarking tools give you complete control over the measurement environment — consistent hardware, isolated processes, and no shared-CI noise. Unlike SaaS performance monitoring platforms that charge per benchmark-minute, self-hosted tools run on your infrastructure at zero marginal cost.

Benchmarking complements other quality practices covered in our guides. For static analysis, see our [Python type checkers guide](../2026-07-02-python-type-checkers-mypy-pyright-pyre-pytype-beartype/). For runtime safety, our [rate limiting libraries comparison](../2026-07-02-python-rate-limiting-limits-slowapi-flask-limiter-django-ratelimit/) covers protecting your APIs. Our [Python profiling tools guide](../2026-06-22-python-profiling-tools-py-spy-pyinstrument-scalene-austin/) covers tools for finding performance hotspots that you should then benchmark.

## FAQ

### How do I get reliable benchmarks on shared CI runners?

Shared CI runners (like GitHub Actions free tier) are noisy — CPU throttling, co-tenancy, and varying load affect results. Mitigation strategies: (1) use CodSpeed's calibration, (2) run benchmarks multiple times and use median not mean, (3) use pyperf's system tuning (`pyperf system tune`), (4) for critical benchmarks, use self-hosted runners on dedicated hardware, (5) set a regression threshold of at least 5-10% to avoid false positives from noise.

### Should I benchmark in unit tests or separate benchmark files?

Start with unit-level benchmarks alongside your tests (pytest-benchmark in test files). They catch obvious regressions with minimal overhead. As your project matures, add dedicated benchmark suites (separate `benchmarks/` directory) for more thorough, longer-running benchmarks that you run less frequently or on a schedule.

### What makes a good benchmark?

A good benchmark: (1) runs fast enough to complete in CI (under 1 second total), (2) measures a single, well-defined operation, (3) uses realistic input sizes, (4) avoids I/O (disk, network) which introduces noise, (5) includes setup/teardown that isn't counted in measurement time. Bad benchmarks measure wall-clock time of operations that involve network calls, database queries, or filesystem access — these are integration tests, not benchmarks.

### How do I compare benchmarks across different Python versions?

Use pyperf with system tuning or CodSpeed with its calibration system. Both normalize for hardware differences. For ASV, create separate environments per Python version and run benchmarks in each. Always record the Python version and system information alongside benchmark results for fair comparison.

### Can benchmarking catch algorithmic regressions?

Yes, if your benchmarks use realistic input sizes. An O(n) function replacing an O(n log n) one won't show much difference at n=100, but benchmarks at n=10000 will reveal the regression. Parametrize your benchmarks with multiple input sizes to catch algorithmic complexity regressions.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Python Benchmarking: pytest-benchmark vs CodSpeed vs pyperf vs airspeed-velocity",
  "description": "Comprehensive comparison of Python benchmarking tools — pytest-benchmark, CodSpeed, pyperf, and airspeed-velocity — covering statistical rigor, CI integration, historical tracking, and production deployment patterns for preventing performance regressions.",
  "datePublished": "2026-07-02",
  "dateModified": "2026-07-02",
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
