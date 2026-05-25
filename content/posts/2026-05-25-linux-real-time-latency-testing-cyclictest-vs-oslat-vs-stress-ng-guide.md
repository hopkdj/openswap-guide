---
title: "Self-Hosted Linux Real-Time Latency Testing: cyclictest vs oslat vs stress-ng"
date: "2026-05-25"
tags: ["linux", "real-time", "latency-testing", "preempt-rt", "performance"]
draft: false
---

Real-time Linux systems — used for industrial automation, financial trading, audio/video production, and telecommunications — require predictable, bounded latency. The **PREEMPT-RT** kernel patch transforms Linux into a fully preemptible real-time operating system, but verifying that your system meets latency targets requires dedicated testing tools.

Three tools dominate the Linux real-time latency testing landscape: **cyclictest** (the gold-standard latency measurement tool), **oslat** (Open Source Latency test, a modern Red Hat tool), and **stress-ng** (a comprehensive stress testing suite with real-time scheduling support).

This guide covers how to install, configure, and use each tool to measure and validate real-time latency on self-hosted Linux infrastructure.

## What Is Real-Time Latency Testing?

Real-time latency testing measures the maximum time between an event occurring and the system responding to it. In a real-time system, this **worst-case latency** (also called **maximum jitter**) must stay within strict bounds — typically under 50 microseconds for industrial control, under 10 microseconds for financial trading, and under 200 microseconds for audio processing.

Standard Linux kernels are not real-time because:
- The kernel is not fully preemptible (long-running kernel code cannot be interrupted)
- Interrupt handlers run with interrupts disabled
- Priority inversion is not systematically prevented
- Lock contention can block high-priority threads indefinitely

The PREEMPT-RT patch set addresses all of these issues, but configuration and hardware choices (CPU governor, interrupt affinity, isolated CPU cores) dramatically affect the achieved latency. Dedicated testing tools are essential for validating your configuration.

## cyclictest: The Gold-Standard Latency Tool

**cyclictest** is part of the `rt-tests` suite and is the most widely used tool for measuring real-time latency on Linux. It spawns one or more threads at real-time scheduling priority, has each thread measure the time between when it should wake up and when it actually does, and reports the maximum, average, and minimum latency observed.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y rt-tests
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y rt-tests
```

On Alpine Linux:

```bash
apk add rt-tests
```

Build from source:

```bash
git clone https://git.kernel.org/pub/scm/utils/rt-tests/rt-tests.git
cd rt-tests
make -j$(nproc)
sudo make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  cyclictest:
    image: ubuntu:24.04
    container_name: cyclictest-runner
    privileged: true
    cap_add:
      - SYS_NICE
      - IPC_LOCK
    volumes:
      - ./cyclictest-results:/output
    command: >
      bash -c "
        apt-get update && apt-get install -y rt-tests &&
        cyclictest -p 80 -m -n -i 200 -l 100000 -q > /output/cyclictest-results.txt &&
        echo 'Results saved to /output/cyclictest-results.txt'
      "
    restart: "no"
```

### Core Usage Patterns

**Basic latency measurement (single thread, 100,000 loops):**

```bash
sudo cyclictest -p 80 -m -n -i 200 -l 100000
```

Flags explained:
- `-p 80` — set thread priority to 80 (SCHED_FIFO, range 1-99)
- `-m` — lock memory pages (prevent page faults)
- `-n` — use nanosleep instead of clock_nanosleep
- `-i 200` — set timer interval to 200 microseconds
- `-l 100000` — run for 100,000 loops

**Multi-threaded measurement (one thread per CPU core):**

```bash
sudo cyclictest -p 80 -m -n -i 1000 -l 1000000 -a -t
```

- `-a` — affinitize threads to specific CPUs (one per core)
- `-t` — use one thread per available CPU

**Histogram output for statistical analysis:**

```bash
sudo cyclictest -p 80 -m -n -i 200 -l 1000000 -h 200 -q > latency-histogram.txt
```

- `-h 200` — create histogram with 200 buckets
- `-q` — quiet mode (only histogram output)

**Long-running overnight test:**

```bash
sudo cyclictest -p 80 -m -n -i 500 -D 12h -h 400 -q > overnight-latency.txt
```

- `-D 12h` — run for 12 hours duration

### Interpreting Results

cyclictest outputs lines like:
```
# Cycle Min Act Avg Max
T: 0 (  5678) P:80 I:200 C: 100000 Min:     12 Act:   18 Avg:   15 Max:     47
```

The **Max** column is your worst-case latency in microseconds. For a real-time system targeting 50us maximum latency, any value above 50 indicates a configuration issue that needs investigation.

## oslat: Modern Open Source Latency Testing

**oslat** (Open Source Latency test) is a newer latency measurement tool developed by Red Hat as part of the CPU Realtime Test Suite. It is designed specifically for testing CPU isolation and real-time latency on cloud and virtualized environments, making it ideal for testing PREEMPT-RT kernels in VMs and containers.

### Installation

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y oslat
```

On Debian/Ubuntu (build from source):

```bash
sudo apt update && sudo apt install -y build-essential libnuma-dev
git clone https://gitlab.com/olycan/oslat.git
cd oslat
make -j$(nproc)
sudo make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  oslat:
    image: ubuntu:24.04
    container_name: oslat-runner
    privileged: true
    cap_add:
      - SYS_NICE
      - IPC_LOCK
    volumes:
      - ./oslat-results:/output
    command: >
      bash -c "
        apt-get update && apt-get install -y build-essential libnuma-dev &&
        cd /tmp && git clone https://gitlab.com/olycan/oslat.git &&
        cd oslat && make &&
        ./oslat --duration 300 --cpu-list 2-3 --rt-prio 90 > /output/oslat-results.txt
      "
    restart: "no"
```

### Core Usage Patterns

**Basic latency test on specific CPU cores:**

```bash
sudo oslat --duration 300 --cpu-list 2-3 --rt-prio 90
```

- `--duration 300` — run for 300 seconds
- `--cpu-list 2-3` — test on CPU cores 2 and 3 (isolated cores)
- `--rt-prio 90` — use SCHED_FIFO priority 90

**Full-system latency test:**

```bash
sudo oslat --duration 600 --cpu-list 0-7 --rt-prio 80 --verbose
```

**Save results to JSON for automated analysis:**

```bash
sudo oslat --duration 300 --cpu-list 2-3 --rt-prio 90 --json /output/oslat-results.json
```

### Interpreting Results

oslat produces detailed output including:
- **Min latency** — minimum observed wake-up latency
- **Max latency** — maximum observed wake-up latency (the key metric)
- **Avg latency** — average latency over the test duration
- **Latency distribution** — histogram showing how latency values are distributed
- **CPU utilization** — per-core CPU usage during the test

A well-tuned PREEMPT-RT system should show max latency under 30 microseconds with CPU isolation enabled.

## stress-ng: Comprehensive Stress Testing with RT Support

**stress-ng** is a comprehensive stress testing tool that can exercise nearly every subsystem of a Linux system. While not primarily a latency measurement tool, its real-time scheduling options make it valuable for testing how real-time workloads behave under system stress.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y stress-ng
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y stress-ng
```

On Alpine Linux:

```bash
apk add stress-ng
```

### Docker Deployment

```yaml
version: "3.8"
services:
  stress-ng:
    image: ubuntu:24.04
    container_name: stress-ng-runner
    privileged: true
    cap_add:
      - SYS_NICE
    volumes:
      - ./stress-results:/output
    command: >
      bash -c "
        apt-get update && apt-get install -y stress-ng &&
        stress-ng --sched 4 --sched-policy fifo --sched-prio 80 \
          --timeout 300 --metrics-brief > /output/stress-results.txt
      "
    restart: "no"
```

### Core Usage Patterns

**Stress test with real-time scheduling:**

```bash
sudo stress-ng --sched 4 --sched-policy fifo --sched-prio 80 --timeout 300
```

This spawns 4 workers using SCHED_FIFO scheduling at priority 80, competing for CPU time and measuring context switch behavior.

**Combined CPU + memory + I/O stress:**

```bash
sudo stress-ng --cpu 4 --vm 2 --hdd 1 --timeout 600 --metrics-brief
```

**Test scheduler latency under load:**

```bash
# Terminal 1: Run cyclictest
sudo cyclictest -p 80 -m -n -i 200 -l 500000

# Terminal 2: Apply stress
sudo stress-ng --cpu 8 --vm 4 --iomix 2 --timeout 300
```

Running cyclictest while stress-ng applies load reveals how the system handles worst-case latency under contention. This is the most realistic test for production readiness.

**Test specific subsystems:**

```bash
# Memory subsystem stress
stress-ng --vm 4 --vm-bytes 80% --timeout 300

# I/O subsystem stress
stress-ng --hdd 4 --hdd-bytes 1G --timeout 300

# Network subsystem stress
stress-ng --sock 8 --timeout 300
```

### Interpreting Results

stress-ng reports per-stressor metrics including:
- **bogo-ops** — number of operations completed (higher is better)
- **bogo-ops/s** — operations per second (throughput)
- **real time** — wall clock time for the test
- **user/system time** — CPU time breakdown

While stress-ng does not directly report latency like cyclictest, running it alongside cyclictest gives you the full picture: stress-ng creates the load, and cyclictest measures the latency impact.

## Comparison Table

| Feature | cyclictest | oslat | stress-ng |
|---------|-----------|-------|-----------|
| **Primary Purpose** | Latency measurement | Latency measurement | System stress testing |
| **Latency Metrics** | Min/Avg/Max/Jitter | Min/Avg/Max/Distribution | Indirect (via sched workers) |
| **Real-time Scheduling** | SCHED_FIFO, SCHED_RR | SCHED_FIFO | SCHED_FIFO, SCHED_RR, SCHED_DEADLINE |
| **CPU Isolation** | Via `-a` flag | Via `--cpu-list` | Via `--taskset` |
| **Histogram Output** | Yes (`-h` flag) | Yes (built-in) | No |
| **JSON Output** | No | Yes (`--json`) | No |
| **Stress Generation** | No | No | Yes (comprehensive) |
| **Duration Control** | Loops (`-l`) or time (`-D`) | `--duration` | `--timeout` |
| **Best Used With** | Standalone or with stress-ng | Standalone | Paired with cyclictest |
| **Active Development** | Stable (kernel.org) | Active (Red Hat) | Very active (ColinIanKing) |
| **GitHub Stars** | N/A (kernel.org) | ~50 | 1,200+ |

## Choosing the Right Latency Testing Tool

**Choose cyclictest when:**
- You need the industry-standard latency measurement tool
- You want to compare results against published PREEMPT-RT benchmarks
- You need histogram output for statistical latency analysis
- You are validating a production PREEMPT-RT deployment

**Choose oslat when:**
- You are testing CPU isolation in virtualized or cloud environments
- You need JSON output for automated CI/CD pipeline integration
- You want modern tooling with active Red Hat development
- You are testing RHEL, CentOS Stream, or Fedora systems

**Choose stress-ng when:**
- You want to test system behavior under realistic load conditions
- You need to validate that real-time tasks meet deadlines during I/O or memory pressure
- You are performing comprehensive system stress testing beyond just latency
- You want to pair load generation with cyclictest/oslat measurement

**Recommended workflow:** Use cyclictest or oslat to measure baseline latency, then run stress-ng to apply realistic load while re-measuring. If max latency stays within bounds under stress, your real-time configuration is production-ready.

## Why Self-Host Real-Time Latency Testing

Running latency testing tools on your own infrastructure is essential for real-time system deployments:

**Hardware-specific results.** Latency behavior depends heavily on CPU architecture, motherboard chipset, BIOS settings (C-states, turbo boost, SMT), and PCIe device configuration. Cloud instances cannot reproduce the exact hardware characteristics of your production servers. On-premises testing gives you results that match your actual deployment environment.

**Continuous validation.** Real-time latency is not a one-time check — kernel updates, BIOS firmware changes, and new PCIe device additions can all affect latency. Self-hosted testing enables automated nightly validation: run cyclictest after every kernel update and alert if max latency exceeds your threshold.

**Configuration tuning feedback loop.** Optimizing a PREEMPT-RT system requires iterative tuning: adjusting CPU governors (performance vs. powersave), isolating CPU cores (`isolcpus`), pinning interrupts (`irqaffinity`), and disabling unnecessary kernel threads. Each change needs latency re-measurement to verify improvement. On-premises testing gives you the rapid iteration needed for effective tuning.

**Compliance requirements.** Industries like financial trading (MiFID II), industrial automation (IEC 61499), and telecommunications (3GPP) require documented real-time performance guarantees. Self-hosted latency testing provides auditable evidence that your systems meet regulatory latency bounds.

**Cost savings.** Real-time validation on cloud infrastructure requires dedicated bare-metal instances (shared VMs cannot guarantee latency), which cost 3-5x more than on-premises servers for continuous testing. Self-hosted testing eliminates this recurring cost.

For related Linux performance optimization, see our [Linux CPU governor management guide](../2026-05-25-linux-cpu-governor-management-auto-cpufreq-cpupower-tuned-guide/) and [Linux I/O scheduler comparison](../2026-05-22-self-hosted-linux-io-scheduler-bfq-mq-deadline-kyber-guide/). For kernel-level analysis of scheduler behavior, our [kernel dynamic tracing guide](../2026-05-25-linux-kernel-dynamic-tracing-trace-cmd-vs-systemtap-vs-perf-probe-guide/) covers how to trace scheduler decisions in real time.

## FAQ

### What is PREEMPT-RT and how does it reduce latency?

PREEMPT-RT is a set of kernel patches that transform Linux into a fully preemptible real-time operating system. Key changes include: converting spinlocks to rt-mutexes (allowing preemption while holding locks), threading interrupt handlers (making them preemptible by higher-priority tasks), converting the timer wheel to high-resolution mode, and implementing priority inheritance to prevent priority inversion. Together, these changes reduce worst-case latency from hundreds of milliseconds (standard kernel) to tens of microseconds (PREEMPT-RT).

### How low can latency go on a properly tuned system?

On a well-configured PREEMPT-RT system with CPU isolation, performance governor, and SMT disabled, typical worst-case latencies are: **5-15 microseconds** for idle systems, **15-30 microseconds** under moderate load, and **30-50 microseconds** under heavy stress. Achieving sub-5-microsecond latency requires specialized hardware (dedicated real-time CPUs, FPGA-based NICs) and is beyond the scope of general-purpose Linux systems.

### Do I need a PREEMPT-RT kernel to use these testing tools?

No. cyclictest, oslat, and stress-ng all work on standard kernels. However, the latency numbers on a standard kernel will be much higher (typically 100-500 microseconds worst case) and more variable. These tools are most valuable when validating PREEMPT-RT configurations, but they can also help you understand the latency characteristics of your hardware on any kernel.

### What CPU governor should I use for real-time workloads?

Always use the **performance** governor for real-time workloads. The powersave or ondemand governors dynamically reduce CPU frequency, which introduces frequency transition latency (typically 50-200 microseconds) — this alone can blow through real-time latency budgets. Set it with: `cpupower frequency-set -g performance` or configure your preferred governor tool.

### How many CPU cores should I isolate for real-time tasks?

The minimum is **one isolated core** for your real-time thread. For production systems, isolate **2-4 cores**: one for the real-time application thread, one for interrupt handling (using `irqaffinity`), and optionally 1-2 more for kernel threads that cannot be fully isolated. Use the kernel boot parameter `isolcpus=2,3,4` and `nohz_full=2,3,4` to isolate cores 2-4 from the scheduler tick.

### Can I run cyclictest in a virtual machine?

Yes, but VM latency results will be significantly higher and more variable than bare-metal due to hypervisor scheduling, virtual interrupt controllers, and shared CPU contention. Use VMs for basic tool validation and workflow testing, but always perform final latency validation on the actual bare-metal hardware that will run production workloads.

### How long should a latency test run?

For initial validation, **1 million iterations** or **1 hour** (whichever comes first) is reasonable. For production certification, run **overnight (8-12 hours)** or **24 hours** to capture rare latency spikes that only occur under specific conditions (cron jobs, backup processes, network bursts). Latency spikes are by definition rare events — short tests may miss the worst case entirely.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Real-Time Latency Testing: cyclictest vs oslat vs stress-ng",
  "description": "Compare three Linux real-time latency testing tools: cyclictest (gold-standard), oslat (modern Red Hat tool), and stress-ng (stress testing with RT support). Includes Docker Compose configs and tuning guides.",
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
