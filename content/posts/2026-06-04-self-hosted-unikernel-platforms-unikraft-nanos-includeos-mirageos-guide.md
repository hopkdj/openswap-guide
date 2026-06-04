---
title: "Self-Hosted Unikernel Platforms: Unikraft vs Nanos vs IncludeOS vs MirageOS"
date: "2026-06-04"
tags: ["unikernel", "virtualization", "linux-kernel", "devops", "lightweight-vm", "unikraft", "nanos", "includeos", "mirageos", "infrastructure", "self-hosted"]
draft: false
---

## Introduction

Traditional virtualization runs a full operating system for every application, duplicating kernel services and wasting resources. Unikernels take the opposite approach: compile your application directly into a minimal, single-purpose kernel image that runs directly on the hypervisor. The result is boot times measured in milliseconds, memory footprints under 10 MB, and attack surfaces orders of magnitude smaller than a full VM.

For self-hosted infrastructure, unikernels offer compelling advantages for microservices, edge computing, and high-density server deployments. This article compares four leading open-source unikernel platforms: Unikraft, Nanos, IncludeOS, and MirageOS.

## What Are Unikernels?

A unikernel is a specialized, single-address-space machine image constructed by compiling application code together with only the minimal OS components it needs. Unlike a traditional OS that provides a generic kernel serving multiple processes, a unikernel includes only the libraries, drivers, and kernel subsystems required for the specific application.

This design unlocks several key benefits for self-hosted deployments:

- **Density**: Run hundreds or thousands of unikernel instances on a single physical server, since each consumes minimal memory and CPU.
- **Security**: With no shell, no extra utilities, and no unused system calls, the attack surface is dramatically reduced compared to a full Linux distribution.
- **Performance**: Direct application-to-hardware paths with no context switching between kernel and user space can yield lower latency and higher throughput.
- **Boot Speed**: Unikernels boot in milliseconds, making them ideal for serverless and event-driven architectures.

## Comparison Table

| Feature | Unikraft | Nanos | IncludeOS | MirageOS |
|---------|----------|-------|-----------|----------|
| **Architecture** | Modular library OS | Single-address-space kernel | C++ unikernel framework | OCaml library OS |
| **Language Support** | C, C++, Rust, Go, Python, Lua | C, Go, Rust, Node.js | C++ | OCaml (primary) |
| **Hypervisor Support** | KVM, Xen, VMware, Hyper-V | KVM, Xen, Hyper-V | KVM, VirtualBox | KVM, Xen |
| **Networking** | lwIP, DPDK, vsock | lwIP, custom TCP/IP | Custom TCP/IP stack | mirage-tcpip, solo5 |
| **Filesystem** | 9pfs, initrd, ramfs | TFS (custom), 9p | Custom | Custom |
| **Orchestration** | KraftKit CLI + Kubernetes | Ops CLI + Nanos Operator | Custom tooling | Solo5 + custom scripts |
| **GitHub Stars** | 3,661+ | 3,148+ | 5,239+ | 2,755+ |
| **Last Updated** | June 2026 | May 2026 | May 2026 | May 2026 |

## Unikraft

Unikraft is a modular, library-based unikernel developed by a consortium including NEC Laboratories Europe, the University of Liège, and Lancaster University. It takes a "library operating system" approach where you select exactly which kernel components to include.

**Key features:**
- Extensive POSIX compatibility layer for porting existing applications
- KraftKit CLI for building, running, and packaging unikernels
- Docker-like workflow: `kraft build` and `kraft run`
- Kubernetes integration via the KraftCloud operator
- Support for popular frameworks including NGINX, Redis, SQLite, and Python Flask
- DPDK support for high-performance networking (10 Gbps+ throughput)

**Deployment Example:**

```bash
# Install KraftKit
curl -sSfL https://get.kraftkit.sh | sh

# Initialize a new Unikraft project
kraft init --plat qemu --lang python my-unikernel

# Build the unikernel
kraft build

# Run locally on QEMU/KVM
kraft run -p 8080:8080
```

**Docker Compose for Unikraft orchestration:**

```yaml
version: '3'
services:
  unikraft-builder:
    image: unikraft/kraftkit:latest
    volumes:
      - ./app:/workspace
    command: ["kraft", "build"]
    
  unikraft-runner:
    image: unikraft/kraftkit:latest
    network_mode: host
    privileged: true
    volumes:
      - ./app:/workspace
    command: ["kraft", "run", "-p", "8080:8080"]
```

## Nanos (NanoVMs)

Nanos is a unikernel developed by NanoVMs that focuses on running a single Linux binary as a virtual machine. It emphasizes zero-configuration deployment and broad language support.

**Key features:**
- Ops CLI tooling with a Heroku-like developer experience
- Native support for Go, Rust, C, Node.js, and Java applications
- Built-in TFS (Trivial File System) with snapshot support
- GDB debugging support for production troubleshooting
- AWS, GCP, and Azure image generation
- Kubernetes operator for orchestrating Nanos unikernels at scale

**Deployment Example:**

```bash
# Install Ops
curl https://ops.city/get.sh -sSfL | sh

# Build and run a Go application as a unikernel
ops load golang_1.21 -p 8080 -a myapp

# Generate cloud images
ops image create gcloud -p 8080 -a myapp
```

**Docker Compose for local Nanos development:**

```yaml
version: '3'
services:
  nanos-dev:
    image: nanovms/ops:latest
    privileged: true
    volumes:
      - ./myapp:/app
      - /dev/kvm:/dev/kvm
    working_dir: /app
    command: ["ops", "run", "-p", "8080", "myapp"]
```

## IncludeOS

IncludeOS is a C++ unikernel that compiles your application and OS into a single, bootable image. It was one of the earliest modern unikernel projects and provides a clean, minimal runtime environment.

**Key features:**
- Pure C++ implementation with modern tooling (CMake, Conan)
- Built-in TCP/IP stack with TLS support
- LiveUpdate for zero-downtime application updates without dropping connections
- NAT and firewall capabilities built into the kernel
- Virtio drivers for disk, network, and console
- WebAssembly experimental support

**Deployment Example:**

```bash
# Install IncludeOS
git clone https://github.com/includeos/includeos.git
cd includeos
mkdir build && cd build
cmake .. && make -j$(nproc)

# Create a simple HTTP service
cat > service.cpp << 'EOF'
#include <os>
#include <net/inet4>

void Service::start() {
  auto& inet = net::Inet4::stack<0>();
  inet.tcp().listen(80, [](auto conn) {
    conn->write("HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello World!\n");
    conn->close();
  });
}
EOF

# Build and run
cmake .. -DCMAKE_PREFIX_PATH=../IncludeOS_install && make
boot --create-bridge includeos_service
```

## MirageOS

MirageOS is a library operating system written in OCaml that constructs unikernels for secure, high-performance network applications. It is notable for its strong type safety guarantees and formal verification capabilities.

**Key features:**
- Type-safe OCaml implementation with memory safety guarantees
- Solo5 hypervisor backend for minimal trusted computing base
- mirage-tcpip - a complete TCP/IP stack written in pure OCaml
- Irmin distributed database integration for persistent storage
- TLS stack with formal verification (miTLS)
- Xen/ARM and KVM/ARM64 support for edge/IoT deployments

**Deployment Example:**

```bash
# Install MirageOS
opam init
opam install mirage

# Create a new unikernel project
mirage configure -t hvt
make depend
make

# Run on Solo5/hvt
solo5-hvt --net:service=tap100 mirage-http.hvt
```

## Why Self-Host with Unikernels?

Self-hosting with unikernels addresses several infrastructure challenges that traditional virtualization cannot solve efficiently.

**Resource Consolidation.** In a typical self-hosted environment, each service runs in its own VM or container, consuming 200-500 MB of RAM for the OS kernel alone. Unikernels strip away the unnecessary OS components, reducing per-service memory to 5-20 MB. On a server with 64 GB of RAM, you could run roughly 100 traditional VMs versus 3,000+ unikernels — a 30x improvement in density.

**Reduced Attack Surface.** Traditional Linux servers expose hundreds of system calls, dozens of running daemons, and a shell accessible through SSH. Each component represents a potential vulnerability. Unikernels include only the system calls and libraries the application actually uses — typically under 100 syscalls total, with no shell, no package manager, and no extra network services. For regulated industries hosting sensitive data (healthcare, finance, government), this dramatically simplifies compliance auditing.

**Fast Restart and Scaling.** Unikernels boot in under 10 milliseconds — roughly 1,000x faster than a full Linux VM. This makes them ideal for auto-scaling workloads where you need to spin up new instances rapidly in response to demand spikes. Combined with Kubernetes orchestration, unikernel-based services can scale from zero to thousands of instances in seconds.

For a broader perspective on self-hosted infrastructure, check our [microVM platform comparison](../2026-05-09-microvm-platforms-firecracker-cloud-hypervisor-crosvm-guide/) and [container runtime guide](../containerd-vs-cri-o-vs-podman-self-hosted-container-runtimes-guide-2026/).

## Choosing the Right Unikernel Platform

Different use cases favor different unikernel platforms. Understanding your workload requirements helps narrow the choice.

**For polyglot microservices environments**, Unikraft provides the broadest language and framework support, plus Kubernetes-native tooling via KraftKit. If you are running a mix of Python APIs, Go services, and Rust workers, Unikraft's library approach lets you build consistent unikernel images across all languages.

**For Go-heavy serverless workloads**, Nanos offers the smoothest developer experience. The Ops CLI provides a Heroku-like workflow, and Nanos images are directly deployable to major cloud providers as well as on-premises KVM hosts.

**For C++ high-performance systems**, IncludeOS provides the deepest integration with the C++ ecosystem, including LiveUpdate for zero-downtime deployments — a unique feature among unikernels.

**For security-critical and formally verified systems**, MirageOS's OCaml type system and Solo5 backend provide the strongest correctness guarantees. Its formally verified TLS stack (miTLS) is unique in the unikernel ecosystem.

For additional context on virtualization strategies, see our [KVM web management guide](../2026-06-04-self-hosted-kvm-web-management-webvirtcloud-kimchi-multipass-guide/) and [virtualization networking overview](../2026-06-01-linux-namespace-management-lsns-nsenter-unshare-podman/).

## FAQ

### What is a unikernel?

A unikernel is a specialized virtual machine image that compiles application code together with only the minimal operating system libraries it requires. Unlike a traditional OS that runs multiple processes, a unikernel runs a single application directly on the hypervisor with no separation between kernel and user space.

### When should I use unikernels instead of Docker containers?

Unikernels offer superior isolation (hardware-level via the hypervisor), smaller attack surfaces, and faster boot times than containers. However, containers provide a broader ecosystem with richer tooling and easier debugging. Consider unikernels for latency-sensitive microservices, security-critical workloads, and high-density server consolidation. Containers remain better for development flexibility and CI/CD pipelines.

### Do unikernels support persistent storage?

Yes, through various mechanisms. Unikraft supports 9pfs and virtio-blk for persistent disk access. Nanos uses its TFS (Trivial File System) with snapshot capabilities. IncludeOS supports virtio block devices. For production use, most unikernel platforms recommend external databases or object storage (accessed over the network) rather than local filesystems.

### Can I run unikernels in Kubernetes?

Yes. Unikraft provides the KraftCloud operator for Kubernetes, allowing you to manage unikernel workloads alongside traditional containers using standard kubectl commands. Nanos also has a Kubernetes operator. These operators handle the KVM resource allocation, networking, and lifecycle management within a Kubernetes cluster.

### What are the main limitations of unikernels?

Unikernels have a steeper learning curve than containers, limited debugging tooling (no shell access by default), and narrower hardware support compared to general-purpose Linux. They are not suitable for workloads requiring multiple processes, fork/exec semantics, or dynamic loading of shared libraries at runtime.

### How do I monitor unikernel instances?

Most unikernel platforms expose metrics over the network (HTTP endpoints, SNMP, or custom protocols). For production monitoring, integrate with Prometheus by having your unikernel application expose a `/metrics` endpoint. Unikraft has experimental OTLP support for OpenTelemetry integration with Grafana and Jaeger.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform where you can bet on everything from election results to technology regulatory timelines. Unlike gambling, this is a real information market: the more you know, the better your edge. I've already made good money predicting the direction of technology-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Unikernel Platforms: Unikraft vs Nanos vs IncludeOS vs MirageOS",
  "description": "Comprehensive comparison of four leading open-source unikernel platforms — Unikraft, Nanos, IncludeOS, and MirageOS — for self-hosted lightweight virtualization, microservices, and high-density server deployments.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
