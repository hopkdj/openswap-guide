---
title: "Self-Hosted XDP and eBPF Network Tools: xdp-tools vs bpftool vs cilium-ebpf"
date: "2026-05-10"
tags: ["xdp", "ebpf", "networking", "kernel", "linux", "self-hosted", "performance"]
draft: false
---

The eXpress Data Path (XDP) and the extended Berkeley Packet Filter (eBPF) have revolutionized Linux networking by enabling high-performance packet processing directly in the kernel. For infrastructure operators running self-hosted services, eBPF-based tools provide visibility, security, and performance capabilities that traditional userspace networking cannot match.

In this guide, we compare three essential open-source tools for working with XDP and eBPF on self-hosted Linux systems: **xdp-tools**, **bpftool**, and **cilium/ebpf**. Each serves a different role in the eBPF ecosystem — from ready-to-use XDP programs to kernel-space introspection to a Go library for building custom eBPF applications.

## What Are XDP and eBPF?

**eBPF** (extended Berkeley Packet Filter) is a revolutionary technology that allows sandboxed programs to run in the Linux kernel without modifying kernel source code or loading kernel modules. eBPF programs can hook into various kernel events — network packet reception, system calls, tracepoints — and execute with near-native performance.

**XDP** (eXpress Data Path) is a specific eBPF hook that operates at the earliest possible point in the network stack — right after the network driver receives a packet, before any kernel processing occurs. This enables ultra-low-latency packet processing for:

- **DDoS mitigation:** Drop malicious packets before they consume kernel resources
- **Load balancing:** Forward packets to backend servers at line rate
- **Packet filtering:** Implement high-performance firewalls and ACLs
- **Traffic accounting:** Count bytes and packets per flow with minimal overhead

For related reading on eBPF tracing and security, see our [bpftrace vs BCC vs sysdig eBPF tracing guide](../2026-04-26-bpftrace-vs-bcc-vs-sysdig-self-hosted-ebpf-tracing-guide/) and [KubeArmor vs Falco vs Tetragon runtime security comparison](../2026-05-07-kubearmor-vs-falco-vs-tetragon-runtime-security-guide/). For network-level packet analysis, check our [suricata vs snort vs zeek IDS comparison](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/).

## Why Self-Host XDP/eBPF Tools?

**Performance at Scale:** Traditional userspace packet processing (iptables, nftables, Suricata) involves context switches between kernel and userspace for every packet. XDP operates entirely in the kernel's network driver path, processing millions of packets per second on a single CPU core.

**Observability Without Overhead:** eBPF-based monitoring tools attach to kernel tracepoints and functions, collecting detailed metrics without the performance penalty of traditional monitoring agents. This is critical for production infrastructure where monitoring overhead directly impacts service performance.

**Custom Security Policies:** eBPF enables security policies that adapt to runtime conditions. Unlike static firewall rules, eBPF programs can inspect packet contents, track connection state, and make dynamic filtering decisions based on real-time threat intelligence.

**No Kernel Modules Required:** Traditional kernel extensions require kernel source compatibility and carry the risk of kernel panics. eBPF programs are verified by the kernel before loading, guaranteeing they cannot crash the system or access unauthorized memory.

## xdp-tools — Production-Ready XDP Programs

[xdp-tools](https://github.com/xdp-project/xdp-tools) is the official collection of XDP programs maintained by the XDP project. It includes production-ready programs for packet filtering, forwarding, load balancing, and traffic measurement — all deployable with minimal configuration.

### Key Features

- **xdp-filter:** Layer 3/4 packet filtering with BPF map-based rule management
- **xdp-loader:** Load, unload, and manage XDP programs on network interfaces
- **xdp-dump:** Capture packets at the XDP layer (like tcpdump but earlier in the stack)
- **xdp-bench:** Benchmark XDP program performance on your hardware
- **xdp-pass: A minimal pass-through program for testing XDP attachment
- **AF_XDP support:** Zero-copy packet capture and forwarding to userspace applications
- **Actively maintained** by the kernel networking community
- **GitHub mirror** with regular upstream syncs

### Installation

On modern distributions, xdp-tools is available from the package manager:

```bash
# Ubuntu/Debian
apt-get install xdp-tools

# Fedora/RHEL
dnf install xdp-tools

# Arch Linux
pacman -S xdp-tools
```

### Usage Examples

Load an XDP drop program on an interface:

```bash
# Attach XDP drop program to eth0 (drops all incoming packets)
xdp-loader load eth0 xdp-drop.o

# Attach XDP pass program (allows all packets)
xdp-loader load eth0 xdp-pass.o

# Check loaded XDP programs
xdp-loader status

# Unload XDP program
xdp-loader unload eth0 --all
```

Use xdp-filter to block specific IP addresses at the XDP layer:

```bash
# Create a filter blocking specific source IPs
xdp-filter --dev eth0 --mode skb \
    --block-source 10.0.0.0/8 \
    --block-source 192.168.1.0/24

# Load the filter
xdp-loader load eth0 xdp-filter.o

# Verify the filter is active
bpftool prog show
bpftool map dump named xdp_filter_map
```

The `--mode skb` flag uses the generic XDP mode, which works on any network interface. For maximum performance, use `--mode native` (requires driver support) or `--mode offload` (requires NIC hardware support).

## bpftool — eBPF Introspection and Management

[bpftool](https://github.com/libbpf/bpftool) is the official eBPF introspection and management utility, included in the Linux kernel source tree. It provides a command-line interface for loading, inspecting, and managing eBPF programs and maps — essential for any operator working with eBPF-based networking tools.

### Key Features

- **Program management:** Load, pin, unload, and inspect eBPF programs
- **Map operations:** Create, dump, update, and delete eBPF maps
- **Link tracking:** Monitor eBPF program attachments to kernel hooks
- **JIT inspection:** View the compiled BPF bytecode and JIT-optimized instructions
- **Feature detection:** Check kernel eBPF capabilities and supported program types
- **Skeleton generation:** Create C headers for embedding eBPF programs in applications
- **Included in kernel source** — always matches your kernel version
- **No external dependencies** beyond the kernel

### Installation

bpftool is typically installed as part of the kernel tools package:

```bash
# Ubuntu/Debian
apt-get install linux-tools-common linux-tools-$(uname -r)

# Fedora/RHEL
dnf install bpftool

# Arch Linux
pacman -S bpftool

# Or build from kernel source
cd /usr/src/linux/tools/bpf/bpftool
make && make install
```

### Usage Examples

Inspect loaded eBPF programs:

```bash
# List all eBPF programs
bpftool prog show

# Show details of a specific program
bpftool prog show id 42

# Dump the BPF instructions of a program
bpftool prog dump xlated id 42

# Show JIT-compiled instructions
bpftool prog dump jited id 42
```

Manage eBPF maps:

```bash
# List all eBPF maps
bpftool map show

# Dump the contents of a map
bpftool map dump id 15

# Create a hash map
bpftool map create /sys/fs/bpf/my_map type hash key 4 value 8 entries 1024 name my_map flags 0
```

Monitor eBPF events:

```bash
# Monitor eBPF program load/unload events
bpftool prog show --json | jq '.[].tag'

# Trace eBPF program execution with perf
bpftool prog profile id 42 duration 10
```

## cilium/ebpf — Go Library for Building eBPF Applications

[cilium/ebpf](https://github.com/cilium/ebpf) is a pure Go library that provides a convenient interface for loading and interacting with eBPF programs. Developed by the Cilium project, it enables developers to build custom eBPF-based networking, security, and observability tools entirely in Go — without writing C code.

### Key Features

- **Pure Go:** No CGO dependencies, cross-compilable to any architecture
- **CO-RE support:** Compile Once — Run Everywhere, using BTF (BPF Type Format) for kernel type information
- **Map types:** Full support for all eBPF map types (hash, array, LRU, LPM trie, ring buffer)
- **Program types:** Load all eBPF program types (socket filter, XDP, tc, kprobe, tracepoint, cgroup)
- **Link management:** Attach programs to kernel hooks with automatic cleanup
- **BTF integration:** Use kernel BTF for CO-RE relocations, no kernel headers needed at runtime
- **Active development** by the Cilium team with regular releases
- **Used in production** by Cilium CNI, Tetragon, and other major projects

### Building eBPF Programs with cilium/ebpf

The typical workflow involves writing the eBPF program in C, compiling it to BPF bytecode, and loading it from Go:

```bash
# Install the Go eBPF tools
go install github.com/cilium/ebpf/cmd/bpf2go@latest

# Create your eBPF program in C
cat > filter.c << 'EOF'
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>

SEC("xdp")
int xdp_drop_blocked(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;
    
    // Default: pass all packets
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
EOF

# Compile to BPF bytecode
clang -O2 -target bpf -c filter.c -o filter.bpf.o

# Generate Go bindings
go generate
```

Load and run the eBPF program from Go:

```go
package main

import (
    "log"
    "net"
    "github.com/cilium/ebpf/link"
    "github.com/cilium/ebpf/rlimit"
)

//go:generate go run github.com/cilium/ebpf/cmd/bpf2go -cc clang filter filter.bpf.o

func main() {
    // Remove resource limits for BPF
    if err := rlimit.RemoveMemlock(); err != nil {
        log.Fatal(err)
    }

    // Load the BPF program
    objs, err := loadFilterObjects()
    if err != nil {
        log.Fatal(err)
    }
    defer objs.Close()

    // Attach to network interface
    iface, err := net.InterfaceByName("eth0")
    if err != nil {
        log.Fatal(err)
    }

    link, err := link.AttachXDP(link.XDPOptions{
        Program:   objs.XdpDropBlocked,
        Interface: iface.Index,
    })
    if err != nil {
        log.Fatal(err)
    }
    defer link.Close()

    log.Println("XDP program attached to eth0")
    
    // Keep running
    select {}
}
```

## Comparison Table

| Feature | xdp-tools | bpftool | cilium/ebpf |
|---|---|---|---|
| **Primary role** | XDP program suite | eBPF introspection CLI | Go eBPF library |
| **Language** | C | C | Go |
| **Ready-to-use programs** | Yes (filter, dump, bench) | No | No (build your own) |
| **Program loading** | xdp-loader CLI | `bpftool prog load` | Go library API |
| **Map management** | Via program config | `bpftool map` commands | Go library API |
| **Kernel introspection** | Limited | Comprehensive | Via BTF |
| **CO-RE support** | Yes | Yes | Yes (primary feature) |
| **AF_XDP support** | Yes | Via map inspection | Yes (Go API) |
| **Cross-compilation** | No | No | Yes (pure Go) |
| **Package availability** | distro packages | distro packages | Go module |
| **Best for** | Deploying XDP programs | Inspecting eBPF state | Building eBPF apps in Go |

## Deployment Architecture

A typical self-hosted eBPF networking stack combines all three tools:

1. **cilium/ebpf** for building custom eBPF programs tailored to your infrastructure
2. **xdp-tools** for deploying standard XDP programs (filtering, load balancing)
3. **bpftool** for monitoring and debugging the eBPF programs at runtime

```yaml
# Docker Compose for eBPF monitoring stack
version: "3.8"
services:
  # eBPF-based network monitoring (using cilium/ebpf library)
  ebpf-monitor:
    build: ./ebpf-monitor
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
      - /sys/kernel/debug:/sys/kernel/debug
    restart: unless-stopped

  # Standard XDP programs
  xdp-setup:
    image: alpine:latest
    privileged: true
    network_mode: host
    command: |
      apk add xdp-tools
      xdp-loader load eth0 xdp-pass.o
    restart: unless-stopped
```

## Kernel Requirements

eBPF and XDP require specific kernel versions:

- **eBPF:** Linux 3.18+ (basic), Linux 4.4+ (maps), Linux 5.3+ (CO-RE with BTF)
- **XDP:** Linux 4.8+ (generic mode), Linux 4.12+ (native mode)
- **BTF (CO-RE):** Linux 5.4+ (kernel-compiled BTF)
- **AF_XDP:** Linux 4.18+

For production deployments, use a recent kernel (5.15+ LTS or 6.x) for the best eBPF feature support and bug fixes.

## FAQ

### What is the difference between eBPF and XDP?

eBPF is a general-purpose technology for running sandboxed programs in the kernel. XDP is a specific eBPF program type that runs at the earliest point in the network stack — right after the NIC driver receives a packet. All XDP programs are eBPF programs, but not all eBPF programs are XDP programs.

### Is eBPF safe to use in production?

Yes. eBPF programs go through a kernel verifier that checks them for safety before they are allowed to run. The verifier ensures programs cannot access unauthorized memory, enter infinite loops, or crash the kernel. This is fundamentally different from kernel modules, which have no such safety guarantees.

### Do I need to compile a custom kernel for eBPF?

No. Modern Linux distributions (Ubuntu 22.04+, Fedora 36+, Debian 12+) include kernels with full eBPF support. However, CO-RE (Compile Once — Run Everywhere) requires kernel BTF, which is available in kernels 5.4+ compiled with `CONFIG_DEBUG_INFO_BTF=y`.

### Can XDP replace iptables/nftables?

Partially. XDP can handle simple packet filtering and forwarding at much higher performance than iptables/nftables. However, XDP operates before the kernel network stack, so it cannot perform connection tracking, NAT, or application-layer inspection. XDP and nftables are complementary — use XDP for high-performance filtering at the edge and nftables for stateful firewall rules.

### What is AF_XDP and when should I use it?

AF_XDP is a socket family that allows userspace applications to receive packets directly from the XDP layer, bypassing the entire kernel network stack. This enables zero-copy packet processing at line rate. Use AF_XDP when you need userspace applications (like custom load balancers or protocol parsers) to process packets with minimal latency.

### How do I debug eBPF programs?

Use bpftool to inspect loaded programs and maps. The `bpftool prog dump xlated` command shows the verified BPF bytecode, while `bpftool map dump` shows map contents. For runtime debugging, use `bpftool prog profile` to count program executions, or attach bpftrace probes to eBPF program entry points.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted XDP and eBPF Network Tools: xdp-tools vs bpftool vs cilium-ebpf",
  "description": "Compare xdp-tools, bpftool, and cilium/ebpf for self-hosted high-performance packet processing with XDP and eBPF on Linux.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
