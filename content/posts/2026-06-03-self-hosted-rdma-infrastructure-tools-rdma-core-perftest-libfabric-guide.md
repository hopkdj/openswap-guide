---
title: "Self-Hosted RDMA Infrastructure Tools: rdma-core vs perftest vs libfabric"
date: "2026-06-03"
tags: ["rdma", "infiniband", "hpc", "networking", "low-latency", "performance", "roce", "self-hosted"]
draft: false
---

## Introduction

Remote Direct Memory Access (RDMA) is the backbone of high-performance computing, enabling direct memory transfers between servers without involving the CPU. Technologies like InfiniBand, RoCE (RDMA over Converged Ethernet), and iWARP power everything from financial trading systems to distributed databases and HPC clusters.

Managing an RDMA fabric requires specialized tools for diagnostics, performance testing, and fabric communication. This guide compares three essential open-source RDMA infrastructure toolkits: **rdma-core** (the standard userspace library suite), **perftest** (RDMA performance benchmarking), and **libfabric** (the OpenFabrics Interfaces framework).

## Comparison Table

| Feature | rdma-core | perftest | libfabric |
|---------|:---------:|:--------:|:---------:|
| **GitHub Stars** | ⭐ 2,261 | ⭐ 973 | ⭐ 797 |
| **Purpose** | Core RDMA userspace libraries | RDMA performance testing | Provider-agnostic fabric API |
| **Maintained By** | Linux RDMA Community | Linux RDMA Community | OpenFabrics Alliance |
| **Protocol Support** | InfiniBand, RoCE, iWARP | InfiniBand, RoCE | InfiniBand, RoCE, iWARP, TCP, UDP, shm |
| **Key Components** | ibverbs, rdma_cm, librdmacm | ib_send_bw, ib_write_bw, ib_read_bw | fi_msg, fi_rma, fi_tagged |
| **Programming Model** | Verbs API (low-level) | CLI benchmarking tools | libfabric API (provider abstraction) |
| **Latest Version** | v54.0 (2026) | 24.10.0 (2026) | v2.0.0 (2026) |
| **Installation** | Distro packages + source | Distro packages + source | Distro packages + source |
| **Dependencies** | Kernel RDMA subsystem | rdma-core, libibverbs | Kernel RDMA subsystem |
| **Monitoring/Diag** | ✅ ibdiag, rdma tool | ❌ None | ❌ None |

## rdma-core

rdma-core is the canonical userspace library suite for Linux RDMA. It provides the Verbs API implementation (`libibverbs`), connection management (`librdmacm`), and a comprehensive set of diagnostic and management tools. Every RDMA application on Linux ultimately depends on rdma-core.

**Key components:**

- **ibverbs** — The core Verbs library for queue pair (QP) creation, memory registration, and work request posting
- **librdmacm** — RDMA connection manager for establishing reliable connections
- **ibdiag tools** — Diagnostic utilities including `ibstat`, `ibstatus`, `ibping`, `ibdiagnet`, and `ibdiagpath`
- **rdma utility** — Modern command-line tool for RDMA device and resource management

**Installation (Ubuntu/Debian):**

```bash
# Install RDMA userspace packages
sudo apt update
sudo apt install -y rdma-core libibverbs1 librdmacm1   ibverbs-utils rdmacm-utils ibverbs-providers

# Load kernel modules
sudo modprobe rdma_cm
sudo modprobe ib_uverbs
sudo modprobe mlx5_ib  # For Mellanox ConnectX adapters

# Verify RDMA devices are available
rdma link show
ibstat
```

**Diagnostics workflow — checking fabric health:**

```bash
# List all RDMA devices
rdma link show

# Check InfiniBand port status
ibstat mlx5_0

# Run a fabric diagnostic scan
sudo ibdiagnet --ls 10 --pm_pause_time 300

# Ping across the fabric (LID-based)
ibping -S 1  # Start server on LID 1
ibping -G 0xfe800000000000000002c9030045a6b1  # Ping via GID

# Query performance counters
perfquery -x mlx5_0 1
```

rdma-core is the foundation — you install it on every RDMA-capable node in your cluster. Its diagnostic tools are essential for troubleshooting fabric issues, verifying link health, and monitoring congestion.

## perftest

perftest is the standard RDMA performance testing suite. It provides a set of microbenchmarks that measure the raw throughput and latency of your RDMA fabric — essential for baseline performance validation, regression testing, and hardware comparison.

**Key benchmarks:**

- **ib_send_bw / ib_send_lat** — RDMA Send throughput and latency
- **ib_write_bw / ib_write_lat** — RDMA Write throughput and latency
- **ib_read_bw / ib_read_lat** — RDMA Read throughput and latency
- **ib_atomic_bw / ib_atomic_lat** — Atomic operation benchmarks

**Installation and basic testing:**

```bash
# Install from distribution packages
sudo apt install -y perftest

# Or build from source for latest version
git clone https://github.com/linux-rdma/perftest.git
cd perftest
./autogen.sh && ./configure && make -j$(nproc)
sudo make install
```

**Benchmark workflow — client/server model:**

```bash
# Server node (Node A)
ib_write_bw -d mlx5_0 -F --report_gbits

# Client node (Node B) — connect to server via IP or GID
ib_write_bw -d mlx5_0 -F --report_gbits <server-ip>
# Output example:
# RDMA_Write BW Test
# 8388608 bytes: 96.45 Gbps

# Latency test
ib_write_lat -d mlx5_0 -F <server-ip>
# Output example:
# RDMA_Write Latency Test
# 2 bytes: 0.98 usec

# Comprehensive run with multiple message sizes
ib_send_bw -d mlx5_0 -F --report_gbits -a -n 10000 <server-ip>
```

**Performance tuning example — adjusting QP attributes:**

```bash
# Test with different MTU sizes
for mtu in 1024 2048 4096; do
    ib_write_bw -d mlx5_0 -F --report_gbits -m $mtu <server-ip>
done

# Test with multiple queue pairs for parallelism
ib_write_bw -d mlx5_0 -F --report_gbits -q 4 <server-ip>

# Test RDMA over Converged Ethernet (RoCE)
ib_write_bw -d mlx5_0 -F --report_gbits -R <server-ip>
```

perftest is the go-to tool when you need to validate that your RDMA fabric is performing at line rate, diagnose throughput anomalies, or compare different hardware configurations. Run it after every firmware upgrade, driver update, or fabric topology change.

## libfabric (OpenFabrics Interfaces)

libfabric (also known as OFI) provides a provider-agnostic API for fabric communication services. Unlike rdma-core's Verbs API (which requires RDMA-capable hardware), libfabric abstracts the transport layer — applications written against libfabric can run over InfiniBand, RoCE, TCP, UDP, shared memory, and other providers without code changes.

**Key features:**

- **Provider abstraction** — Applications use the same API regardless of the underlying transport
- **Multiple transport modes** — Reliable Connected (RC), Reliable Datagram (RD), and more
- **Tag matching** — Hardware-accelerated message matching for MPI implementations
- **RMA operations** — Remote memory access with completion semantics
- **Active development** — Used by MPICH, DAOS, and numerous HPC middleware projects

**Installation and provider discovery:**

```bash
# Install libfabric
sudo apt install -y libfabric-bin libfabric-dev fabtests

# List available providers
fi_info -l
# Output includes: psm2, verbs, sockets, tcp, udp, shm, rxd, rxm

# Show detailed capabilities of a provider
fi_info -p verbs

# Show which provider would be used for a specific endpoint
fi_info -p verbs -f FI_EP_RDM
```

**Running libfabric performance tests:**

```bash
# Server node
fi_rdm_tagged_pingpong -p verbs

# Client node
fi_rdm_tagged_pingpong -p verbs <server-ip>
# Output:
# bytes   #sent   #ack   total   time     MB/sec   usec/xfer   Mxfers/sec
# 8192    1000    0      4.3m    0.01s    8103.21  1.01        0.99

# Test over shared memory provider (intra-node)
fi_rdm_tagged_pingpong -p shm
```

libfabric is ideal for developers building portable HPC applications and for organizations that need to support heterogeneous fabric environments. It's the foundation of MPICH's OFI networking layer and is increasingly used in distributed storage systems like DAOS.

## RDMA Network Topology Comparison

Understanding your fabric topology is critical for performance tuning. Here's how each tool helps:

**rdma-core — Fabric discovery:**
```bash
# Discover the entire InfiniBand fabric topology
ibnetdiscover

# Generate a topology graph
ibnetdiscover -f /tmp/fabric-topology.dot
dot -Tpng /tmp/fabric-topology.dot -o fabric-topology.png

# Check for slow links or errors
ibdiagnet --lw 1x --pm_pause_time 300
```

**perftest — Hop-by-hop latency measurement:**
```bash
# Measure latency to each switch hop
for gid in $(ibroute mlx5_0 | grep GidOut | awk '{print $NF}'); do
    echo -n "Hop to $gid: "
    ib_send_lat -d mlx5_0 -F -n 100 $gid 2>/dev/null | grep "t_avg"
done
```

**libfabric — Provider-level topology:**
```bash
# Query fabric domain attributes
fi_info -p verbs -v | grep -E "domain|fabric"

# Map processes to NUMA-optimal providers
fi_info -p verbs --filter="domain=mlx5_0" --filter="numa_node=0"
```

## Why Self-Host Your RDMA Infrastructure

Building and managing your own RDMA infrastructure gives you complete control over network performance characteristics that cloud providers abstract away. In RDMA environments, every microsecond of latency and every gigabit of bandwidth matters — cloud abstractions that add even 5-10 microseconds of overhead negate RDMA's primary advantage. Running your own fabric lets you optimize from the application down to the physical link layer.

The open-source RDMA tooling ecosystem is mature and production-hardened. The Linux kernel's RDMA subsystem has been stable for over a decade, and tools like rdma-core and perftest are used in production at national laboratories, financial institutions, and hyperscale data centers. The cost of entry is surprisingly accessible — used InfiniBand adapters and switches are available on the secondary market, and RoCE v2 lets you run RDMA over standard Ethernet switches with appropriate NICs.

For organizations running HPC workloads, our [HPC MPI implementations guide covering OpenMPI, MPICH, and MVAPICH](../2026-06-01-self-hosted-hpc-mpi-implementations-openmpi-mpich-mvapich-guide/) builds on the RDMA foundation — MPI libraries use Verbs and libfabric as their transport layer. For measuring end-to-end application performance, our [network performance measurement guide with perfSONAR, iPerf, and SmokePing](../2026-05-13-self-hosted-network-performance-measurement-perfsonar-iperf-smokeping-guide/) provides the higher-layer monitoring that complements RDMA-level benchmarks. For containerized HPC environments, our [HPC container runtimes comparison](../2026-06-01-self-hosted-hpc-container-runtimes-apptainer-charliecloud-podman-hpc-guide/) shows how to preserve RDMA performance within containers using Apptainer, Charliecloud, and Podman.

## FAQ

### Do I need InfiniBand hardware to use RDMA?

No — while InfiniBand is the traditional RDMA fabric, **RoCE v2 (RDMA over Converged Ethernet)** allows RDMA over standard Ethernet networks with compatible NICs. Many modern NICs from NVIDIA/Mellanox (ConnectX series), Intel, and Broadcom support RoCE. You can also use **SoftRoCE (RXE)** — a software RDMA implementation included in rdma-core — for development and testing without RDMA-capable hardware at all.

### What's the difference between the Verbs API and libfabric?

The **Verbs API** (provided by rdma-core's libibverbs) is the low-level, hardware-specific interface that directly maps to RDMA adapter capabilities. **libfabric** provides a higher-level, provider-agnostic API that can run over Verbs, TCP, shared memory, and other transports. Use Verbs when you need maximum performance on known hardware; use libfabric when you need portability across transport types or are building on existing libfabric-based middleware like MPICH.

### How do I troubleshoot RDMA performance issues?

A systematic RDMA troubleshooting workflow:
1. **Check link health** with `ibstat` and `ibdiagnet` (rdma-core)
2. **Measure raw throughput** with `ib_write_bw` (perftest) to baseline hardware performance
3. **Check for congestion** with `perfquery` counters (rdma-core)
4. **Test with libfabric** to identify provider-level issues
5. **Verify PCIe bandwidth** — an x8 Gen3 slot can bottleneck a 100Gbps link

### Can I run RDMA inside Docker containers?

Yes. Use the `--device=/dev/infiniband/` flag or the RDMA cgroup device plugin. For Kubernetes, the RDMA device plugin (`k8s-rdma-sriov-dev-plugin`) enables RDMA in pods. Containers share the host's RDMA kernel stack, so performance overhead is minimal (sub-microsecond), but you need to ensure the container has access to the appropriate device files and the `IPC_LOCK` capability for memory registration.

### How does RDMA compare to DPDK for low-latency networking?

RDMA and DPDK serve different purposes. **RDMA** provides CPU-bypass for data movement — the NIC writes directly to application memory without kernel involvement, ideal for storage, databases, and HPC messaging. **DPDK** provides kernel-bypass for packet processing — the application polls the NIC directly, ideal for network functions, load balancers, and packet processing. They're complementary: many financial trading systems use DPDK for feed handlers and RDMA for inter-server state replication.

### What monitoring should I set up for an RDMA fabric?

At minimum, monitor:
- **Link status and speed** via `rdma link` and `ibstat`
- **Port counters** (errors, discards, congestion) via `perfquery`
- **Temperature** for InfiniBand switches and adapters
- **Bandwidth utilization** per port
- **QP errors and retries** for application-level debugging

Export these metrics to Prometheus using the `infiniband_exporter` and visualize in Grafana for a comprehensive RDMA monitoring dashboard.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted RDMA Infrastructure Tools: rdma-core vs perftest vs libfabric",
  "description": "Complete guide to open-source RDMA infrastructure tools comparing rdma-core (userspace library suite), perftest (performance benchmarking), and libfabric (provider-agnostic fabric API) for InfiniBand, RoCE, and HPC environments.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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
