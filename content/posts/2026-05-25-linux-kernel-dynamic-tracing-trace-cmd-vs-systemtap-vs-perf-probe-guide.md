---
title: "Self-Hosted Linux Kernel Dynamic Tracing: trace-cmd vs SystemTap vs perf probe"
date: "2026-05-25"
tags: ["linux", "kernel-tracing", "systemtap", "performance", "debugging"]
draft: false
---

Kernel dynamic tracing allows you to observe running Linux systems in real time — probing kernel functions, tracking system calls, measuring latency, and diagnosing performance bottlenecks without recompiling the kernel or restarting services. Three major toolchains dominate this space: **trace-cmd** (the ftrace frontend), **SystemTap** (Red Hat's scripting-based tracer), and **perf probe** (the perf subsystem's dynamic instrumentation interface).

This guide compares these three approaches, shows how to deploy and use each one, and helps you decide which fits your infrastructure debugging workflow.

## What Is Kernel Dynamic Tracing?

Kernel dynamic tracing inserts instrumentation probes into a running kernel at specific function entry/exit points, trace events, or even arbitrary instruction addresses. Unlike static tracing (which requires kernel recompilation with `CONFIG_TRACEPOINTS`), dynamic tracing works on production kernels out of the box.

Common use cases include:

- **Latency analysis** — measuring how long kernel functions take to execute
- **System call monitoring** — tracking which syscalls a process invokes and with what arguments
- **I/O profiling** — observing block layer requests, disk scheduler behavior, and filesystem operations
- **Network debugging** — tracing socket operations, TCP state transitions, and packet processing paths
- **Scheduler analysis** — understanding CPU scheduling decisions, context switches, and run queue behavior

Each tool approaches dynamic tracing differently, with distinct trade-offs in ease of use, overhead, and flexibility.

## trace-cmd: The ftrace Frontend

**trace-cmd** is a user-space command-line tool that provides a convenient interface to the Linux kernel's built-in **ftrace** framework. ftrace has been part of the mainline kernel since 2.6.27 and requires no additional packages beyond the kernel itself.

trace-cmd translates high-level recording commands into ftrace debugfs operations, captures trace data in a binary format, and provides tools for analysis and visualization.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y trace-cmd kernelshark
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y trace-cmd kernelshark
```

On Alpine Linux:

```bash
apk add trace-cmd
```

### Docker Deployment

While trace-cmd is typically installed directly on the host (since it needs kernel debugfs access), you can run it in a privileged container for isolated analysis sessions:

```yaml
version: "3.8"
services:
  trace-cmd:
    image: alpine:latest
    container_name: trace-cmd-analyzer
    privileged: true
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug:rw
      - /sys/kernel/tracing:/sys/kernel/tracing:rw
      - ./traces:/output
    command: >
      sh -c "
        apk add --no-cache trace-cmd &&
        trace-cmd record -e sched_switch -e sched_wakeup -e syscalls -o /output/trace.dat &&
        trace-cmd report -i /output/trace.dat > /output/report.txt
      "
    restart: "no"
```

### Core Usage Patterns

**Record all scheduler events:**

```bash
trace-cmd record -e sched_switch -e sched_wakeup -e sched_waking
```

**Record syscall events for a specific process:**

```bash
trace-cmd record -e syscalls -P $(pidof nginx)
```

**Record function graph (call chain) for a specific function:**

```bash
trace-cmd record -p function_graph -g do_sys_open
```

**View recorded traces:**

```bash
trace-cmd report -i trace.dat | head -50
```

**Convert to KernelShark GUI format:**

```bash
trace-cmd report --gui -i trace.dat > trace.txt
kernelshark trace.dat
```

### Strengths and Weaknesses

| Aspect | Details |
|--------|---------|
| **Overhead** | Very low — ftrace is kernel-native, minimal instrumentation cost |
| **Ease of use** | Moderate — requires understanding of ftrace event categories |
| **Scripting** | Limited — CLI-driven, no built-in scripting language |
| **Visualization** | KernelShark provides GUI timeline analysis |
| **Portability** | Excellent — works on any kernel with ftrace enabled (virtually all) |
| **Custom probes** | Limited to existing tracepoints and kprobes |

## SystemTap: The Scripting Powerhouse

**SystemTap** is a Linux tracing and probing tool that lets you write custom scripts to instrument the kernel and user-space applications. Originally developed by Red Hat, it compiles scripts into kernel modules that are loaded at runtime and unloaded when tracing stops.

SystemTap's scripting language (`.stp` files) provides variables, conditionals, loops, and associative arrays — making it the most programmable of the three tools.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y systemtap systemtap-runtime linux-headers-$(uname -r)
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y systemtap systemtap-runtime kernel-devel-$(uname -r)
```

### Docker Deployment

SystemTap requires kernel headers and debug symbols, making containerized deployment more complex:

```yaml
version: "3.8"
services:
  systemtap:
    image: ubuntu:24.04
    container_name: systemtap-tracer
    privileged: true
    volumes:
      - /lib/modules:/lib/modules:ro
      - /usr/src:/usr/src:ro
      - /sys:/sys:rw
      - ./scripts:/scripts:ro
      - ./output:/output
    environment:
      - STAP_SESSION=tmp-session
    command: >
      bash -c "
        apt-get update && apt-get install -y systemtap systemtap-runtime &&
        stap -v /scripts/monitor.stp -o /output/stap-output.txt
      "
    restart: "no"
```

### Core Usage Patterns

**Monitor all open() syscalls with filename and process info:**

```systemtap
#!/usr/bin/env stap

probe syscall.open {
    printf("%s[%d] opened %s (flags: %s)
",
           execname(), pid(), argstr, probefunc())
}
```

Run with:
```bash
stap -v monitor-open.stp
```

**Track block I/O latency:**

```systemtap
#!/usr/bin/env stap

global read_times, write_times

probe ioblock.request {
    if (rw == "read")
        read_times[execname()] <<< timestamp()
    else
        write_times[execname()] <<< timestamp()
}

probe ioblock.end {
    if (rw == "read") {
        start = read_times[execname] <<< -1
        if (start > 0)
            printf("READ %s: %d us
", execname(), timestamp() - start)
    }
}
```

**Profile kernel function hotspots:**

```systemtap
#!/usr/bin/env stap

global hotspots

probe kernel.function("*@kernel/*").call {
    hotspots[probefunc()]++
}

probe end {
    foreach (fn in hotspots- limit 20)
        printf("%-40s %d calls
", fn, hotspots[fn])
}
```

Run for 30 seconds:
```bash
stap -v profile-hotspots.stp -e 'probe timer.ms(30000) { exit() }'
```

### Strengths and Weaknesses

| Aspect | Details |
|--------|---------|
| **Overhead** | Moderate — kernel module compilation adds startup delay, but runtime overhead is low |
| **Ease of use** | Steep learning curve — requires learning the `.stp` scripting language |
| **Scripting** | Excellent — full scripting language with variables, arrays, and aggregations |
| **Visualization** | Text-based output; no built-in GUI (pipes to other tools) |
| **Portability** | Good — requires matching kernel headers and debug symbols on each target |
| **Custom probes** | Excellent — can probe any kernel function, tracepoint, or user-space function |

## perf probe: The Perf Subsystem Interface

**perf probe** is part of the Linux `perf` tool suite and provides dynamic instrumentation through the perf_events subsystem. It allows you to add kprobe and uprobe-based trace events that integrate with the broader perf ecosystem (recording, reporting, flame graphs).

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y linux-tools-common linux-tools-$(uname -r)
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y perf
```

On Alpine Linux:

```bash
apk add linux-tools
```

### Docker Deployment

```yaml
version: "3.8"
services:
  perf-probe:
    image: ubuntu:24.04
    container_name: perf-probe-analyzer
    privileged: true
    volumes:
      - /sys:/sys:rw
      - /proc:/proc:rw
      - /lib/modules:/lib/modules:ro
      - ./perf-data:/output
    command: >
      bash -c "
        apt-get update && apt-get install -y linux-tools-common linux-tools-generic &&
        perf probe --add 'do_sys_open filename:string' &&
        perf record -e probe:do_sys_open -a sleep 10 &&
        perf report -i perf.data > /output/perf-report.txt &&
        perf probe --del probe:do_sys_open
      "
    restart: "no"
```

### Core Usage Patterns

**List available probe points:**

```bash
perf probe -L do_sys_open
```

**Add a dynamic probe on a kernel function:**

```bash
sudo perf probe --add 'do_sys_open filename:string flags:long'
```

**Record events from the new probe:**

```bash
sudo perf record -e probe:do_sys_open -a sleep 30
```

**View recorded data:**

```bash
sudo perf report -i perf.data
```

**Add a user-space probe (uprobe):**

```bash
sudo perf probe --exec=/usr/bin/nginx --add 'ngx_http_handler'
sudo perf record -e probe_nginx:ngx_http_handler -a sleep 10
```

**List all active probes:**

```bash
sudo perf probe --list
```

**Remove a probe:**

```bash
sudo perf probe --del probe:do_sys_open
```

### Strengths and Weaknesses

| Aspect | Details |
|--------|---------|
| **Overhead** | Low — perf_events subsystem is optimized for low-cost sampling |
| **Ease of use** | Moderate — simpler than SystemTap but more complex than trace-cmd for basic tasks |
| **Scripting** | Limited — no built-in scripting; integrates with perf report and external tools |
| **Visualization** | Excellent — perf report TUI, flame graphs via `perf script | FlameGraph` |
| **Portability** | Good — requires perf tools and kernel debug symbols for full functionality |
| **Custom probes** | Good — kprobes and uprobes, but less flexible than SystemTap's scripting |

## Comparison Table

| Feature | trace-cmd | SystemTap | perf probe |
|---------|-----------|-----------|------------|
| **Backend** | ftrace | Custom kernel modules | perf_events |
| **Scripting** | No (CLI only) | Yes (`.stp` language) | No (CLI + perf report) |
| **Startup Time** | Instant | Slow (compiles kernel module) | Fast |
| **Runtime Overhead** | Very low | Low | Low |
| **Kernel Probes** | Yes (kprobes) | Yes (full kernel access) | Yes (kprobes) |
| **User-space Probes** | Limited | Yes (uprobes) | Yes (uprobes) |
| **GUI Tools** | KernelShark | None | perf report TUI |
| **Flame Graphs** | No | Via external tools | Native support |
| **Package Size** | ~2 MB | ~30 MB (with runtime) | ~5 MB |
| **Kernel Version** | 2.6.27+ | 2.6.18+ | 2.6.31+ |
| **Best For** | Quick recording, low overhead | Custom analysis scripts | Integration with perf ecosystem |

## Choosing the Right Dynamic Tracing Tool

Your choice depends on your debugging workflow and infrastructure requirements:

**Choose trace-cmd when:**
- You need to capture trace data with minimal overhead on production systems
- You want to analyze scheduler behavior, syscall patterns, or kernel function calls
- You prefer a simple CLI workflow with optional GUI visualization via KernelShark
- Your systems have ftrace enabled (virtually all modern kernels)

**Choose SystemTap when:**
- You need programmable tracing with custom logic, conditionals, and aggregations
- You want to write reusable tracing scripts for recurring diagnostic tasks
- You need to probe both kernel and user-space functions in a single script
- You have kernel headers and debug symbols available on target systems

**Choose perf probe when:**
- You already use the `perf` tool suite for performance analysis
- You want to generate flame graphs from dynamic probe data
- You need to correlate dynamic probe events with hardware performance counters
- You prefer the perf ecosystem's reporting and visualization tools

## Why Self-Host Kernel Tracing Tools

Running kernel dynamic tracing tools on your own infrastructure provides several advantages over relying on external monitoring SaaS platforms:

**Full kernel visibility.** External monitoring tools typically rely on exported metrics (Prometheus, statsd) which only surface pre-defined counters. Dynamic tracing lets you probe any kernel function, system call, or tracepoint — including ones that no pre-built exporter tracks. When debugging a novel performance issue, the ability to instrument arbitrary kernel paths is invaluable.

**Zero data exfiltration.** Kernel trace data reveals detailed information about your workloads: process names, file paths, network addresses, and timing patterns. Keeping this data on-premises ensures sensitive operational details never leave your infrastructure.

**No sampling gaps.** Cloud-based APM platforms sample at fixed intervals (typically 1-10 Hz), which can miss brief but critical events like microsecond-latency spikes or transient lock contention. Kernel dynamic tracing captures every event in real time with no sampling gaps, giving you a complete picture of system behavior.

**Cost savings at scale.** Per-host pricing for enterprise APM platforms becomes expensive beyond 50-100 servers. Kernel tracing tools are free and open-source, with costs limited to storage for trace data and compute for analysis.

**Custom instrumentation.** When your workload has unique characteristics (custom filesystems, specialized network protocols, proprietary kernel modules), commercial APM tools cannot provide relevant probes. SystemTap and perf probe let you instrument any function in your kernel or application code.

For eBPF-based tracing alternatives, see our [complete eBPF tracing guide](../2026-04-26-bpftrace-vs-bcc-vs-sysdig-self-hosted-ebpf-tracing-guide-2026/). If you need continuous profiling instead of event tracing, check our [continuous profiling comparison](../2026-04-18-grafana-pyroscope-vs-parca-vs-profefe-self-hosted-continuous-profiling-guide/). For memory management optimization, our [HugePages management guide](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/) covers related kernel tuning.

## FAQ

### What is the difference between ftrace, SystemTap, and eBPF?

**ftrace** is the kernel's built-in tracing framework — it is always available and has minimal overhead but limited programmability. **SystemTap** compiles custom scripts into kernel modules, offering full programmability at the cost of startup time and potential stability risks if scripts are poorly written. **eBPF** (used by bpftrace and BCC) runs sandboxed bytecode inside the kernel, combining programmability with safety — but requires kernel 4.9+ with eBPF support enabled.

### Does dynamic tracing impact production system performance?

All three tools are designed for production use with low overhead. trace-cmd/ftrace has the lowest overhead (typically <1% CPU) because it uses kernel-native tracepoints. SystemTap's compiled modules have similarly low runtime overhead but require compilation time at startup. perf probe's overhead depends on the sampling rate — event-based probes (kprobes) have minimal per-event cost, while high-frequency sampling can add measurable overhead. Always test in a staging environment before deploying to production.

### Can I use these tools inside containers?

Yes, but containers need privileged access or specific capabilities (`CAP_SYS_ADMIN`, `CAP_PERFMON`). The Docker Compose configs in this guide use `privileged: true` for simplicity. For production, restrict capabilities to the minimum needed and mount only the required kernel filesystems (`/sys/kernel/debug`, `/sys/kernel/tracing`, `/sys/kernel`).

### Which tool is best for beginners?

trace-cmd is the easiest to start with — it has a straightforward CLI and requires no scripting knowledge. Recording a trace and viewing it with `trace-cmd report` or KernelShark gives immediate visibility into kernel behavior. SystemTap has the steepest learning curve due to its scripting language, but pays off for complex, recurring diagnostic tasks.

### Do I need to recompile the kernel to use dynamic tracing?

No. All three tools work with standard distribution kernels. However, SystemTap requires matching kernel headers and debug symbols (`linux-headers`, `kernel-debuginfo`), and perf probe benefits from kernel debug symbols for accurate symbol resolution. These packages are available through standard package managers.

### How much disk space does trace data consume?

Trace data volume depends on event frequency and recording duration. A busy web server recording all syscall events can generate 50-200 MB per minute. Use filters (`-P` for process ID, `-F` for function filter) to limit recording scope. trace-cmd supports buffer size limits (`-m` flag) to prevent disk exhaustion. For long-running analysis, pipe output to a log aggregator instead of writing to local disk.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Kernel Dynamic Tracing: trace-cmd vs SystemTap vs perf probe",
  "description": "Compare three major Linux kernel dynamic tracing tools: trace-cmd (ftrace frontend), SystemTap (scripting-based tracer), and perf probe (perf subsystem instrumentation). Includes Docker Compose configs, usage patterns, and selection guide.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
