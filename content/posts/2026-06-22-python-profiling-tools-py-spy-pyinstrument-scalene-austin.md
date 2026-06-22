---
title: "Self-Hosted Python Profiling Tools: py-spy vs pyinstrument vs Scalene vs Austin"
date: "2026-06-22"
tags: ["python", "profiling", "performance", "developer-tools", "debugging", "optimization"]
draft: false
---

Performance optimization without proper profiling is guesswork. Python applications — whether web servers, data pipelines, or CLI tools — can suffer from CPU bottlenecks, memory leaks, I/O contention, and inefficient data structures. Profiling tools reveal exactly where your code spends time and memory, turning hours of speculation into minutes of targeted fixes. This guide compares four leading Python profilers — **py-spy**, **pyinstrument**, **Scalene**, and **Austin** — examining their profiling approaches, overhead, output quality, and production readiness.

## Comparison: py-spy vs pyinstrument vs Scalene vs Austin

Each profiler uses a different sampling strategy, targeting different profiling dimensions. py-spy is a sampling profiler that reads process memory from outside Python. pyinstrument instruments function calls with structured call trees. Scalene profiles CPU, GPU, and memory simultaneously at the line level. Austin is a frame stack sampler that minimizes overhead.

| Feature | py-spy | pyinstrument | Scalene | Austin |
|---------|--------|-------------|---------|--------|
| **Stars** | 15,283 | 7,939 | 13,455 | 2,199 |
| **Profiling Method** | Sampling (reads process memory) | Instrumentation (call tracing) | Sampling + memory tracing | Frame stack sampling |
| **CPU Profiling** | Yes (flame graphs) | Yes (tree view) | Yes (line-level) | Yes (flame graphs) |
| **Memory Profiling** | No | No | Yes (line-level + copy volume) | Yes (allocations, via austin-tui) |
| **GPU Profiling** | No | No | Yes (NVIDIA) | No |
| **Overhead** | Very low | Moderate | Moderate | Very low |
| **Attach to Running Process** | Yes (PID) | No | No | Yes (PID) |
| **Output Format** | Flame graphs, speedscope | HTML, console, JSON | HTML, console | Flame graphs (via FlameGraph) |
| **Language** | Rust | Python | Python | C |
| **Docker/K8s Friendly** | Excellent (no code changes) | Requires import | Requires import | Excellent (no code changes) |
| **Last Updated** | June 2026 | June 2026 | June 2026 | June 2026 |

## py-spy: Non-Invasive Production Profiling

py-spy, written in Rust by Ben Frederickson, samples a running Python process by reading its memory — no code changes, no imports, and no restarts required. This makes it uniquely suited for profiling production Python applications in Docker containers and Kubernetes pods where modifying code or restarting processes is impractical.

**Installation:**

```bash
pip install py-spy
# Or via cargo (Rust)
cargo install py-spy
```

**Profiling a Running Process:**

```bash
# Attach to a running Python process by PID
py-spy top --pid 12345

# Generate a flame graph (SVG)
py-spy record -o profile.svg --pid 12345

# Profile a new process for 30 seconds
py-spy record -o profile.svg -- python my_script.py --duration 30

# Profile with native (C extension) stack frames
py-spy record --native -o profile.svg --pid 12345
```

**Docker/Kubernetes Usage:**

```bash
# In Docker: run py-spy from outside the container
docker run -it --pid=container:my_app --cap-add SYS_PTRACE py-spy record -o /tmp/profile.svg --pid 1

# In Kubernetes: use kubectl with an ephemeral container
kubectl debug -it my-pod --image=python:3.12 --target=my-container -- py-spy record -o /tmp/profile.svg --pid 1
```

py-spy's sampling approach means it doesn't modify the target process's execution, resulting in near-zero overhead. For a 2000 RPM web server, the performance impact is typically under 1%. The flame graph output makes it immediately obvious where time is spent — wide bars consume the most CPU.

**Strengths:** Zero code changes, attach to running processes, sub-1% overhead, flame graphs, production-safe.

**Weaknesses:** No memory profiling, no line-level detail for pure Python code, limited to CPU sampling.

## pyinstrument: Structured Call Trees

pyinstrument takes the opposite approach: it wraps function calls to build a structured, hierarchical profile that shows the call tree and time spent in each function — including its children. The output is designed to look like a filesystem browser: parent functions at the top, children indented underneath with time percentages.

**Installation:**

```bash
pip install pyinstrument
```

**Usage (in-code):**

```python
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()

# Your code here
result = expensive_computation(data)
process_results(result)

profiler.stop()
profiler.open_in_browser()  # Opens HTML report
# Or print to console
print(profiler.output_text(unicode=True, color=True))
```

**Command-line Usage:**

```bash
# Profile a script
pyinstrument my_script.py

# With timing
pyinstrument --timeline -o profile.html my_script.py

# Profile specific modules
pyinstrument --renderer html my_script.py > profile.html
```

pyinstrument's key insight is that a flat list of function times is confusing because it's hard to separate "this function is slow" from "functions called by this function are slow." The call tree output shows both self-time and cumulative time for each node in the tree, making it easy to identify the actual bottleneck.

**Example Output:**

```
  _     ._   __/__   _ _  _  _ _/_   Recorded: 14:32:01  Samples:  18400
 /_//_/// /_\/ //_// / //_'/ //    Duration: 1.842    CPU time: 1.839
/   _/                     v5.0.1

Program: my_script.py

1.842 <module>  my_script.py:1
├─ 1.238 process_data  utils.py:15
│  ├─ 0.892 pandas.read_csv  <built-in>
│  ├─ 0.234 filter_records  utils.py:42
│  │  └─ 0.210 regex.match  <built-in>
│  └─ 0.112 save_results  utils.py:58
└─ 0.604 generate_report  reports.py:10
   ├─ 0.401 matplotlib.pyplot.savefig  <built-in>
   └─ 0.203 compute_statistics  stats.py:8
```

**Strengths:** Beautiful output, easy to read, good for development profiling, HTML export.

**Weaknesses:** Requires code modification, moderate overhead (~10-20%), can't attach to running processes.

## Scalene: CPU, GPU, and Memory Profiling

Scalene, developed at UMass Amherst, is a high-performance profiler that simultaneously tracks CPU time, GPU time, and memory allocation — all at the line level. It's the only profiler in this comparison that can tell you which exact line of code is allocating the most memory or spending the most time on the GPU.

**Installation:**

```bash
pip install scalene
```

**Usage:**

```bash
# Profile a script (CPU + memory by default)
scalene my_script.py

# Profile with GPU tracking
scalene --gpu my_script.py

# Generate HTML report
scalene --html --outfile profile.html my_script.py

# Profile with reduced overhead (sampling mode)
scalene --cpu-sampling-rate 0.01 my_script.py
```

**In-code Usage:**

```python
from scalene import scalene_profiler

scalene_profiler.start()
result = expensive_computation()
scalene_profiler.stop()
```

Scalene's output shows three columns per line of source code: CPU time %, memory allocation (MB), and copy volume (MB). The copy volume metric is unique — it measures how much data is being copied between Python objects, revealing hidden performance costs from unnecessary data duplication that traditional profilers miss.

**Strengths:** CPU + GPU + memory in one tool, line-level granularity, copy volume metric, academic research-backed.

**Weaknesses:** Higher overhead than sampling profilers, requires code changes, not for production attach.

## Austin: Minimal-Overhead Frame Sampling

Austin, written in C by Gabriele N. Tornetta, is a frame stack sampler that operates at the C level — it samples the Python frame evaluation stack without instrumenting Python code. This gives it extremely low overhead while still providing function-level call stacks suitable for flame graph generation.

**Installation:**

```bash
# Linux only
pip install austin-python
# Or from source
cargo install austin
```

**Usage:**

```bash
# Profile a Python script
austin -i 100 python my_script.py > profile.austin

# Profile with memory allocations
austin -m python my_script.py > profile.austin

# Attach to a running process
austin -i 100 -p 12345 > profile.austin

# Convert to flame graph
cat profile.austin | flamegraph.pl > flame.svg
```

Austin's strength is its minimal footprint — sampling at the C frame evaluation level means it doesn't need to traverse Python objects or instrument anything. For profiling high-throughput production services where even 1% overhead matters, Austin is the lightest option. However, it requires external tools (`flamegraph.pl` from Brendan Gregg's FlameGraph repository) for visualization.

**Strengths:** Lowest possible overhead, attach to running processes, memory profiling mode, production-safe.

**Weaknesses:** Linux-only, requires external flame graph tools, smaller community, steeper setup.

## Performance Benchmarking Workflow

Effective Python performance optimization follows a systematic workflow:

1. **Profile first with low overhead**: Use py-spy or Austin against your production service to get a flame graph overview of where CPU time is spent.

2. **Deep-dive with detailed profiling**: If the bottleneck is in your application code (not a third-party library), run pyinstrument or Scalene in development to get line-level detail.

3. **Check memory**: Run Scalene with memory profiling enabled to identify lines that allocate or copy excessive data. Memory optimizations often yield bigger gains than CPU optimizations.

4. **Verify the fix**: Re-profile after your optimization to confirm the bottleneck moved or was eliminated. Always benchmark, don't assume.

For a thorough benchmarking setup, see our [C++ microbenchmarking libraries guide](../2026-06-21-cpp-microbenchmarking-libraries-google-benchmark-celero-nanobench/) and [storage benchmarking tools comparison](../2026-06-16-self-hosted-storage-benchmarking-fio-sysbench-bonniepp/).

## FAQ

### Can I profile a Python web server in production without restarting it?

Yes. Both **py-spy** and **Austin** support attaching to a running process by PID with zero code changes and no restart. For Docker/Kubernetes deployments, you can run the profiler from a sidecar container or via `kubectl debug` with an ephemeral container. py-spy's `--pid` flag is the simplest approach for production profiling.

### Which profiler is best for finding memory leaks?

**Scalene** is the best choice for memory leak detection because it tracks memory allocation at the line level and measures copy volume — how much data is being duplicated between objects. Many Python memory issues are actually caused by unnecessary data copying rather than straightforward leaks. Austin's `-m` flag also provides memory allocation profiling, but with less detail than Scalene.

### How much does profiling slow down my application?

The overhead varies significantly: **py-spy and Austin** have sub-1% overhead because they sample from outside the Python runtime. **Scalene** has moderate overhead (5-15%) in sampling mode, higher in full instrumentation mode. **pyinstrument** has the highest overhead (10-25%) because it wraps every function call. For production profiling, use py-spy or Austin. For development profiling, the higher-overhead tools provide richer data.

### Can these profilers handle C extensions and native code?

py-spy can profile native (C extension) frames with the `--native` flag, which shows time spent in C extensions like NumPy, pandas, and lxml. Scalene provides some visibility into native code through its memory tracking, and the `--native` flag is available in newer versions. pyinstrument and Austin are primarily limited to Python-level profiling, though pyinstrument also supports `--native`.

### What's the difference between a sampling profiler and an instrumentation profiler?

A **sampling profiler** (py-spy, Austin) periodically checks what the program is doing without modifying it — like taking snapshots of a runner every 100 milliseconds. It has near-zero overhead but lower precision. An **instrumentation profiler** (pyinstrument) wraps functions to record entry and exit times — like placing timing gates at every function. It's more precise but adds overhead to every function call. Scalene uses a hybrid approach with both sampling and instrumentation.

### How do I integrate profiling into CI/CD pipelines?

Add a profiling step to your CI pipeline that runs py-spy or pyinstrument on your test suite with representative data. Compare the generated flame graph or profile report against a baseline from the previous commit. Tools like `pytest-benchmark` can track performance regressions, and py-spy's speedscope format integrates well with CI visualization tools. A typical GitHub Actions workflow:

```yaml
- name: Profile performance
  run: |
    pip install py-spy
    py-spy record -o profile.svg -- python -m pytest tests/performance/ --duration 30
- name: Upload profile
  uses: actions/upload-artifact@v4
  with:
    name: performance-profile
    path: profile.svg
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Python Profiling Tools: py-spy vs pyinstrument vs Scalene vs Austin",
  "description": "Comprehensive comparison of Python profiling tools — py-spy, pyinstrument, Scalene, and Austin — covering sampling vs instrumentation, CPU/memory/GPU profiling, production attach, flame graphs, and Docker/Kubernetes integration.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
