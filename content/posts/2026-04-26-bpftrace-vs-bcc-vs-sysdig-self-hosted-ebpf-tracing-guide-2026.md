---
title: "bpftrace vs BCC vs Sysdig: Best eBPF Tracing Tools 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "monitoring", "ebpf", "tracing"]
draft: false
description: "Compare bpftrace, BCC, and sysdig for self-hosted Linux system tracing and troubleshooting. Installation guides, real-world examples, and performance comparison."
---

## Why Self-Host eBPF Tracing Tools

Linux system troubleshooting has historically required either expensive commercial APM suites or cumbersome kernel modules that destabilize production systems. The introduction of [eBPF (extended Berkeley Packet Filter)](https://ebpf.io/) changed this entirely — providing a safe, sandboxed way to observe and modify kernel behavior without loading kernel modules or rebooting.

Self-hosting eBPF tracing tools gives you:

- **Zero-instrumentation observability** — trace production systems without modifying application code or restarting services
- **Kernel-level visibility** — see system calls, network packets, file I/O, and CPU scheduling in real time
- **Minimal performance overhead** — eBPF programs run in-kernel with JIT compilation, adding less than 1% CPU overhead in most cases
- **Complete data ownership** — no third-party SaaS subscription, no telemetry sent to external servers, full control over retention
- **Free and open source** — all three tools covered here are community-driven with permissive licenses

Whether you are diagnosing intermittent latency spikes, tracking down file descriptor leaks, or building a custom observability pipeline, choosing the right eBPF tracing tool matters. This guide compares the three most widely used options: **bpftrace**, **BCC (BPF Compiler Collection)**, and **sysdig**.

## What Is eBPF?

eBPF is a revolutionary technology in the Linux kernel that allows you to run sandboxed programs in the kernel space without changing kernel source code or loading kernel modules. Originally designed for network packet filtering, eBPF has evolved into a general-purpose execution engine powering observability, networking, and security tools.

Key eBPF concepts:
- **Maps** — shared data structures between kernel and user space (hash tables, arrays, ring buffers)
- **Probes** — hooks into kernel functions (kprobes, tracepoints, USDT markers)
- **Helpers** — safe kernel API functions that eBPF programs can call
- **Verifier** — the kernel's safety check that ensures eBPF programs terminate, don't access invalid memory, and can't crash the system

## bpftrace: High-Level One-Liner Tracing

[bpftrace](https://github.com/iovisor/bpftrace) (10,000+ GitHub stars, C++) is a high-level tracing language for Linux that provides a concise scripting syntax inspired by `awk` and `DTrace`. It is the quickest way to run ad-hoc kernel-level diagnostics.

### Key Features

- One-liner syntax for immediate troubleshooting
- DTrace-compatible language for familiar scripting
- Built-in functions for stack traces, histograms, and time series
- Automatic map management and aggregation
- Active development with regular releases (last push: April 2026)

### Installation

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install -y bpftrace
```

**RHEL / CentOS / Rocky:**
```bash
sudo dnf install -y bpftrace
```

**Build from source (latest):**
```bash
sudo apt install -y cmake g++ make bison flex libelf-dev \
  libbfd-dev binutils-dev libdw-dev libsystemd-dev \
  libcereal-dev libclang-dev llvm-dev
git clone https://github.com/iovisor/bpftrace.git
cd bpftrace
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
```

### Docker Usage

bpftrace requires `CAP_SYS_ADMIN` and host kernel access. Run it with privileged mode:

```yaml
# docker-compose.yml for bpftrace one-liners
version: "3.8"
services:
  bpftrace:
    image: bpftrace/bpftrace:latest
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug:rw
      - /lib/modules:/lib/modules:ro
    command: bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'
```

### Real-World Examples

**Find the slowest syscalls:**
```bash
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_* { @start[tid] = nsecs; }
tracepoint:syscalls:sys_exit_* /@start[tid]/ {
  @ns[probe] = hist(nsecs - @start[tid]);
  delete(@start[tid]);
}
'
```

**Track file open latency by process:**
```bash
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_openat { @start[tid] = nsecs; }
tracepoint:syscalls:sys_exit_openat /@start[tid]/ {
  @open_latency[comm] = hist(nsecs - @start[tid]);
  delete(@start[tid]);
}
'
```

**Monitor TCP retransmits in real time:**
```bash
sudo bpftrace -e '
kprobe:tcp_retransmit_skb {
  @retransmits = count();
}
interval:s:5 {
  print(@retransmits);
  clear(@retransmits);
}
'
```

**Find which process is consuming the most disk I/O:**
```bash
sudo bpftrace -e '
tracepoint:block:block_rq_issue {
  @bytes[comm] = sum(args->bytes);
}
interval:s:10 {
  print(@bytes, 10);
  clear(@bytes);
}
'
```

## BCC (BPF Compiler Collection): Comprehensive Tool Suite

[BCC](https://github.com/iovisor/bcc) (22,000+ GitHub stars, C) is the most comprehensive eBPF toolkit available. It provides a Python-based framework for writing custom eBPF programs plus a large collection of ready-to-use tracing tools covering CPU, memory, network, file I/O, and kernel scheduling.

### Key Features

- 100+ pre-built tools for common diagnostics
- Python API for writing custom eBPF programs
- Extensive documentation and examples
- Actively maintained (last push: April 2026, v0.36.1)
- Tools for performance profiling, network analysis, and kernel debugging

### Installation

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install -y bpfcc-tools linux-headers-$(uname -r)
```

**RHEL / CentOS / Rocky:**
```bash
sudo dnf install -y bcc bcc-tools
```

**Build from source:**
```bash
sudo apt install -y bison build-essential cmake flex git \
  libedit-dev libllvm14 llvm-dev libclang-dev libelf-dev \
  liblzma-dev linux-headers-$(uname -r) zlib1g-dev \
  libclang-cpp-dev llvm-14-dev pkg-config python3-dev
git clone https://github.com/iovisor/bcc.git
mkdir bcc/build && cd bcc/build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
```

### Ready-to-Use BCC Tools

Once installed, BCC tools are available in `/usr/share/bcc/tools/`:

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `execsnoop` | Trace process execution | `sudo /usr/share/bcc/tools/execsnoop` |
| `opensnoop` | Trace file open operations | `sudo /usr/share/bcc/tools/opensnoop` |
| `biosnoop` | Trace block I/O latency | `sudo /usr/share/bcc/tools/biosnoop` |
| `tcplife` | Trace TCP connection lifecycle | `sudo /usr/share/bcc/tools/tcplife` |
| `cachestat` | Monitor page cache hit/miss ratio | `sudo /usr/share/bcc/tools/cachestat` |
| `fileslower` | Trace slow file I/O | `sudo /usr/share/bcc/tools/fileslower 10` |
| `runqlat` | CPU scheduler run queue latency | `sudo /usr/share/bcc/tools/runqlat` |
| `ext4slower` | Trace slow ext4 filesystem ops | `sudo /usr/share/bcc/tools/ext4slower 10` |
| `tcpconnlat` | Trace TCP connection latency | `sudo /usr/share/bcc/tools/tcpconnlat` |
| `offcputime` | Off-CPU time analysis | `sudo /usr/share/bcc/tools/offcputime 60` |

### Custom BCC Python Script Example

Track disk I/O latency per process:

```python
#!/usr/bin/env python3
# iolatency.py - Measure block I/O latency histogram
from bcc import BPF

bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/blkdev.h>

BPF_HASH(start, struct request *);
BPF_HISTOGRAM(dist);

int trace_start(struct pt_regs *ctx, struct request *req) {
    u64 ts = bpf_ktime_get_ns();
    start.update(&req, &ts);
    return 0;
}

int trace_completion(struct pt_regs *ctx, struct request *req) {
    u64 *tsp, delta;
    tsp = start.lookup(&req);
    if (tsp != 0) {
        delta = bpf_ktime_get_ns() - *tsp;
        dist.increment(bpf_log2l(delta / 1000));
        start.delete(&req);
    }
    return 0;
}
"""

b = BPF(text=bpf_text)
b.attach_kprobe(event="blk_mq_start_request", fn_name="trace_start")
b.attach_kprobe(event="blk_account_io_done", fn_name="trace_completion")

print("Tracking block I/O latency. Hit Ctrl-C to end.")
try:
    b.trace_print()
except KeyboardInterrupt:
    print("\nFinal latency histogram:")
    b["dist"].print_log2_hist("usec")
```

### Docker Usage for BCC

```yaml
version: "3.8"
services:
  bcc-tools:
    image: zlim/bcc:latest
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /lib/modules:/lib/modules:ro
      - /usr/src:/usr/src:ro
      - /sys:/sys:rw
    command: /usr/share/bcc/tools/execsnoop
```

## Sysdig: System Call Visibility with Container Support

[sysdig](https://github.com/draios/sysdig) (8,200+ GitHub stars, C++) takes a different approach from bpftrace and BCC. Instead of using eBPF directly, sysdig intercepts system calls via a kernel module (or eBPF probe fallback) and provides a powerful filtering and analysis engine. Its standout feature is first-class container awareness — it can filter events by container ID, image name, Kubernetes labels, and more.

### Key Features

- Container-native filtering (filter by container name, image, labels)
- Rich chisel scripting language for custom analysis
- Capture and replay system call traces for post-mortem debugging
- Official Docker image with 1.9M+ pulls
- Kubernetes integration with pod and namespace awareness
- Web UI companion tool (Sysdig Inspect) for visual trace analysis

### Installation

**Ubuntu / Debian:**
```bash
curl -s https://s3.amazonaws.com/download.draios.com/DRAIOS-GPG-KEY.public | sudo gpg --dearmor -o /usr/share/keyrings/draios.gpg
echo "deb [signed-by=/usr/share/keyrings/draios.gpg] https://download.draios.com/stable/apt stable main" | sudo tee /etc/apt/sources.list.d/draios.list
sudo apt update
sudo apt install -y sysdig
```

**RHEL / CentOS / Rocky:**
```bash
sudo rpm --import https://s3.amazonaws.com/download.draios.com/DRAIOS-GPG-KEY.public
curl -s -o /etc/yum.repos.d/draios.repo https://s3.amazonaws.com/download.draios.com/stable/rpm/draios.repo
sudo yum install -y sysdig
```

### Docker Usage

Sysdig has the most mature Docker integration of all three tools:

```yaml
version: "3.8"
services:
  sysdig:
    image: sysdig/sysdig:latest
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /var/run/docker.sock:/host/var/run/docker.sock
      - /dev:/host/dev
      - /proc:/host/proc:ro
      - /boot:/host/boot:ro
      - /lib/modules:/host/lib/modules:ro
      - /usr:/host/usr:ro
    environment:
      - SYSDIG_BPF_PROBE=/root/.sysdigprobes
    command: sysdig -pk -m container -c topcontainers_cpu
```

### Real-World Examples

**Top CPU-consuming processes:**
```bash
sudo sysdig -c topprocs_cpu
```

**Find slow file I/O operations (over 10ms):**
```bash
sudo sysdig -c fileslower 10
```

**Monitor all file access by a specific process:**
```bash
sudo sysdig proc.name=nginx and evt.type=open
```

**Capture and replay system call traces:**
```bash
# Capture 60 seconds of activity
sudo sysdig -w capture.scap -M 60

# Replay the capture, filtering for HTTP errors
sysdig -r capture.scap fd.type=ipv4 and proc.name=nginx
```

**Container-aware filtering:**
```bash
# Show all network activity from a specific container
sudo sysdig -pk container.name=myapp and evt.type=sendto

# Top containers by network bytes
sudo sysdig -pc -c topcontainers_bytes
```

**Kubernetes pod awareness:**
```bash
# Show all errors from pods in the production namespace
sudo sysdig -pk k8s.ns.name=production and evt.type=write and fd.name=/proc/*log*
```

## Head-to-Head Comparison

| Feature | bpftrace | BCC (BPF Compiler Collection) | sysdig |
|---------|----------|-------------------------------|--------|
| **GitHub Stars** | 10,000+ | 22,000+ | 8,200+ |
| **Primary Language** | C++ | C | C++ |
| **Learning Curve** | Low (DTrace syntax) | Medium (Python API) | Low (familiar CLI) |
| **Ad-Hoc Tracing** | Excellent (one-liners) | Limited (script-based) | Good (command filters) |
| **Pre-Built Tools** | ~20 examples | 100+ tools | 80+ chisels |
| **Container Awareness** | No | No | Yes (native) |
| **Capture & Replay** | No | No | Yes (`.scap` files) |
| **Kubernetes Support** | Manual | Manual | Built-in (`-pk`) |
| **Custom Scripting** | bpftrace language | Python + C eBPF | Lua chisels |
| **Kernel Module Required** | No (eBPF only) | No (eBPF only) | Yes (or eBPF fallback) |
| **Docker Image** | Community | Community | Official (`sysdig/sysdig`) |
| **Best For** | Quick diagnostics | Deep performance analysis | Container/K8s environments |

## Which Tool Should You Choose?

### Choose bpftrace when:
- You need **immediate, ad-hoc diagnostics** on a production server
- You are familiar with DTrace and want a similar scripting experience
- You want to write one-liners for quick answers ("what is eating CPU right now?")
- You need stack traces and histograms without writing scripts

### Choose BCC when:
- You need the **broadest set of pre-built diagnostic tools**
- You want to build custom eBPF programs using Python
- You are doing deep performance analysis (CPU scheduling, memory allocation, network stack)
- You need tools for specific subsystems (ext4, TCP, block I/O, scheduler)

### Choose sysdig when:
- You are running **containerized workloads** and need container-aware filtering
- You want to **capture and replay** system call traces for post-mortem analysis
- You need **Kubernetes pod and namespace awareness** out of the box
- You prefer a familiar CLI syntax with rich filtering capabilities

## Combined Deployment Strategy

Many production environments benefit from running all three tools, each for its strengths. Here is how they complement each other:

```
┌─────────────────────────────────────────────────────┐
│                 Production Server                    │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
│  │ bpftrace │  │   BCC    │  │    sysdig    │       │
│  │ one-liner│  │ deep     │  │ containers   │       │
│  │ tracing  │  │ analysis │  │ capture      │       │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘       │
│       │             │               │                │
│       └──────┬──────┘               │                │
│              │  eBPF subsystem       │                │
│              └───────────┬───────────┘                │
│                          │                            │
│              Linux Kernel (eBPF JIT)                  │
└─────────────────────────────────────────────────────┘
```

Quick incident response workflow:
1. **bpftrace** for immediate triage (what is slow right now?)
2. **BCC tools** for deep analysis (why is it slow, at which kernel layer?)
3. **sysdig** for capturing the full trace for later analysis (what exactly happened?)

## Performance Impact Comparison

All three tools have minimal overhead when used correctly, but the impact varies by workload:

| Scenario | bpftrace | BCC | sysdig |
|----------|----------|-----|--------|
| **Idle (no probes)** | ~0% | ~0% | ~0.1% (kernel module loaded) |
| **Single probe active** | <0.1% | <0.1% | 0.5-1% |
| **Multiple probes** | 0.5-1% | 1-2% | 2-5% |
| **Full syscall capture** | N/A | N/A | 5-15% |
| **Memory overhead** | 5-10 MB | 20-50 MB | 30-80 MB |

**Important:** Always test eBPF tools in a staging environment before deploying to production. While eBPF programs are verified safe by the kernel, a poorly designed probe (e.g., tracing every syscall on a high-throughput web server) can add measurable overhead.

## Best Practices for Production eBPF Tracing

1. **Use tracepoints over kprobes** — tracepoints are stable kernel APIs, while kprobes target internal kernel functions that change between kernel versions
2. **Aggregate in-kernel** — use bpftrace histograms (`hist()`) or BCC's `BPF_HISTOGRAM` to summarize data in-kernel rather than streaming raw events to user space
3. **Set time limits** — always use `interval:` or `-d` flags to auto-stop long-running traces
4. **Filter early** — narrow your trace scope with process names, PIDs, or cgroups to reduce overhead
5. **Monitor the tracing tool itself** — ensure your observability tool is not becoming the bottleneck
6. **Use sysdig's capture mode for incidents** — capture to `.scap` files and analyze offline to minimize production impact

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "bpftrace vs BCC vs Sysdig: Best eBPF Tracing Tools 2026",
  "description": "Compare bpftrace, BCC, and sysdig for self-hosted Linux system tracing and troubleshooting. Installation guides, real-world examples, and performance comparison.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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

### What is the difference between bpftrace and BCC?

bpftrace is a high-level tracing language optimized for ad-hoc one-liners and quick diagnostics, using a DTrace-inspired syntax. BCC (BPF Compiler Collection) is a comprehensive toolkit with 100+ pre-built tools and a Python API for writing custom eBPF programs. Use bpftrace for fast answers ("what is consuming CPU right now?") and BCC for deep performance analysis with existing tools like `execsnoop`, `cachestat`, and `runqlat`.

### Can I run bpftrace or BCC in Docker containers?

Yes, but both require privileged mode (`privileged: true`) and host PID namespace (`pid: host`) because eBPF programs run in kernel space. You also need to mount `/sys/kernel/debug` and `/lib/modules`. Note that these are not typical containerized services — they are debugging tools that need kernel-level access. For production containerized environments, sysdig provides better container awareness out of the box.

### Does sysdig use eBPF or kernel modules?

sysdig primarily uses a kernel module (`sysdig-probe`) for system call interception, but it can fall back to an eBPF probe on newer kernels where the kernel module is not available or desired. The eBPF probe is loaded automatically if the kernel module fails to build or load. You can force eBPF mode with the `SYSDIG_BPF_PROBE` environment variable.

### Is it safe to run eBPF tracing tools on production systems?

Yes, with caveats. The kernel's eBPF verifier guarantees that all eBPF programs are safe — they cannot crash the kernel, access invalid memory, or run indefinitely. However, the *performance impact* depends on what you are tracing. Tracing every system call on a high-throughput web server will add measurable overhead. Best practice: start with targeted traces (specific processes, tracepoints instead of kprobes), test in staging first, and use aggregation to minimize data volume.

### Which tool is best for Kubernetes environments?

sysdig is the best choice for Kubernetes because it has built-in container and pod awareness. You can filter events by container name, Kubernetes namespace, pod labels, and more using the `-pk` flag. bpftrace and BCC can also work in Kubernetes but require manual cgroup filtering to scope traces to specific pods.

### How do I capture and replay system activity for post-mortem analysis?

Use sysdig's capture mode: `sudo sysdig -w incident.scap -M 300` captures 5 minutes of system activity to a file. You can then analyze it offline with `sysdig -r incident.scap <filters>` or load it into the Sysdig Inspect GUI for visual analysis. Neither bpftrace nor BCC supports capture and replay natively.

## Further Reading

For related infrastructure monitoring topics, see our [comprehensive eBPF networking guide](../ebpf-networking-observability-cilium-pixie-tetragon-guide-2026/) covering Cilium, Pixie, and Tetragon, and the [GPU monitoring comparison](../nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/) for hardware-level observability. For distributed application tracing, check out our [APM and distributed tracing guide](../signoz-jaeger-uptrace-self-hosted-apm-distributed-tracing-guide/).
