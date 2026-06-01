---
title: "Self-Hosted NVMe over Fabrics: SPDK vs Linux NVMe-TCP vs Ceph NVMe-oF Gateway"
date: "2026-06-02"
tags: ["nvme", "storage", "nvme-of", "spdk", "ceph", "linux", "performance", "self-hosted", "infrastructure", "comparison"]
draft: false
---

## Introduction

NVMe over Fabrics (NVMe-oF) extends the high-performance NVMe protocol across network fabrics, enabling remote access to NVMe storage devices with near-local latency. For organizations running self-hosted infrastructure, NVMe-oF offers a way to disaggregate storage from compute — centralizing fast flash storage while serving it to multiple servers over the network.

Three major approaches dominate the self-hosted NVMe-oF landscape: the **Storage Performance Development Kit (SPDK)** from Intel, the **Linux kernel NVMe-TCP target**, and the **Ceph NVMe-oF Gateway**. Each takes a different architectural path, with trade-offs in performance, complexity, and ecosystem integration.

This guide compares these three solutions to help you choose the right NVMe-oF stack for your self-hosted environment.

## NVMe-oF Transport Protocols

Before diving into the implementations, it's important to understand the transport options available:

| Transport | Medium | Latency | Use Case |
|-----------|--------|---------|----------|
| NVMe/TCP | Standard Ethernet | ~10-20µs added | General-purpose, easy deployment |
| NVMe/RDMA | RoCE/InfiniBand | ~5-10µs added | High-performance, low-latency clusters |
| NVMe/FC | Fibre Channel | ~5-10µs added | Enterprise SAN environments |

**NVMe/TCP** has emerged as the most accessible transport — it runs over standard TCP/IP networks without requiring special hardware (RDMA NICs or FC HBAs). Both SPDK and the Linux kernel support NVMe/TCP, making it the recommended starting point for most self-hosted deployments.

## Solution Comparison

### SPDK (Storage Performance Development Kit)

SPDK is an Intel-led open-source project that implements NVMe-oF entirely in userspace, bypassing the kernel for maximum performance. It uses polled-mode drivers and lockless queues to achieve extremely low latency and high IOPS.

**Key features:**
- Userspace NVMe/TCP and NVMe/RDMA targets
- Polled-mode drivers eliminate interrupt overhead
- Supports NVMe, NVMe-oF, iSCSI, and vhost protocols
- JSON-RPC management API
- 3,561+ GitHub stars, active development

**Docker Compose example (SPDK target with NVMe/TCP):**

```yaml
version: "3.8"
services:
  spdk-target:
    image: spdk/spdk:latest
    privileged: true
    volumes:
      - /dev/hugepages:/dev/hugepages
      - /var/run/spdk:/var/run/spdk
    command: >
      /spdk/build/bin/nvmf_tgt -m 0x3
    network_mode: host
```

After the container starts, configure the target via the SPDK RPC interface:

```bash
# Create a malloc-backed bdev (for testing; use NVMe bdev in production)
docker exec spdk-target ./scripts/rpc.py bdev_malloc_create 1024 4096 -b Malloc0

# Create the NVMe-oF subsystem
docker exec spdk-target ./scripts/rpc.py nvmf_create_transport -t tcp -o -u 16384 -p 8

# Add a listener on port 4420
docker exec spdk-target ./scripts/rpc.py nvmf_subsystem_create nqn.2026-06.org.spdk:disk1 -a -s SPDK00000000000001
docker exec spdk-target ./scripts/rpc.py nvmf_subsystem_add_ns nqn.2026-06.org.spdk:disk1 Malloc0
docker exec spdk-target ./scripts/rpc.py nvmf_subsystem_add_listener nqn.2026-06.org.spdk:disk1 -t tcp -a 0.0.0.0 -s 4420
```

### Linux Kernel NVMe-TCP Target

The Linux kernel includes a native NVMe-oF target (nvmet) that runs in-kernel, providing a simpler deployment path for environments already using the Linux storage stack. It supports NVMe/TCP and NVMe/RDMA transports.

**Key features:**
- In-kernel target, zero additional dependencies
- Native integration with Linux block layer and filesystems
- Configurable via configfs (`/sys/kernel/config/nvmet/`)
- Supports NVMe/TCP on any TCP-capable NIC
- Built into mainline Linux since 5.0

**Setup via configfs (no Docker required):**

```bash
# Load kernel modules
modprobe nvmet
modprobe nvmet-tcp

# Create a subsystem
mkdir /sys/kernel/config/nvmet/subsystems/nqn.2026-06.org.linux:disk1
echo 1 > /sys/kernel/config/nvmet/subsystems/nqn.2026-06.org.linux:disk1/attr_allow_any_host

# Create a namespace backed by a block device
mkdir /sys/kernel/config/nvmet/subsystems/nqn.2026-06.org.linux:disk1/namespaces/1
echo /dev/nvme0n1 > /sys/kernel/config/nvmet/subsystems/nqn.2026-06.org.linux:disk1/namespaces/1/device_path
echo 1 > /sys/kernel/config/nvmet/subsystems/nqn.2026-06.org.linux:disk1/namespaces/1/enable

# Create a TCP port listener
mkdir /sys/kernel/config/nvmet/ports/1
echo tcp > /sys/kernel/config/nvmet/ports/1/addr_trtype
echo 0.0.0.0 > /sys/kernel/config/nvmet/ports/1/addr_traddr
echo 4420 > /sys/kernel/config/nvmet/ports/1/addr_trsvcid
ln -s /sys/kernel/config/nvmet/subsystems/nqn.2026-06.org.linux:disk1 /sys/kernel/config/nvmet/ports/1/subsystems/
```

### Ceph NVMe-oF Gateway

The Ceph NVMe-oF Gateway exposes RADOS Block Device (RBD) images as NVMe-oF targets, integrating NVMe storage fabrics with Ceph's distributed storage cluster. This allows NVMe clients to consume Ceph-backed storage with NVMe-oF performance.

**Key features:**
- Bridges Ceph RBD pools to NVMe-oF clients
- Built on SPDK for high-performance userspace I/O
- Supports NVMe/TCP transport
- Integrated with Ceph orchestrator for deployment
- 16,669+ GitHub stars (Ceph project)

**Ceph NVMe-oF Gateway deployment:**

```bash
# Deploy via Cephadm orchestrator
ceph orch apply nvmeof my-nvmeof-pool

# Configure the gateway
ceph nvme-gw create gateway-1 --pool my-nvmeof-pool --group my-group

# Create an RBD image and export it via NVMe-oF
rbd create my-nvmeof-pool/disk1 --size 100G
ceph nvme-gw subsystem add nqn.2026-06.org.ceph:disk1 --pool my-nvmeof-pool --image disk1

# Add a listener
ceph nvme-gw listener add gateway-1 --subsystem nqn.2026-06.org.ceph:disk1 --traddr 192.168.1.100 --trsvcid 4420
```

On the initiator (client) side, connect to any of these targets using the standard `nvme connect` command:

```bash
# Discover available subsystems
nvme discover -t tcp -a 192.168.1.100 -s 4420

# Connect to a subsystem
nvme connect -t tcp -n nqn.2026-06.org.ceph:disk1 -a 192.168.1.100 -s 4420
```

## Comparison Table

| Feature | SPDK | Linux Kernel nvmet | Ceph NVMe-oF Gateway |
|---------|------|--------------------|----------------------|
| Architecture | Userspace | In-kernel | Userspace (SPDK-based) |
| Transports | TCP, RDMA, FC | TCP, RDMA | TCP |
| GitHub Stars | 3,561 | N/A (kernel) | 16,669 (Ceph) |
| Management | JSON-RPC | configfs | Ceph orchestration |
| CPU Efficiency | Very High | Moderate | High (SPDK) |
| Setup Complexity | Medium | Low | High (requires Ceph) |
| Best For | Max performance | Simple deployments | Ceph environments |
| Block Backend | NVMe, malloc, AIO | Any block device | Ceph RBD |
| Multi-path | ANA supported | ANA supported | ANA supported |

## Why Self-Host Your NVMe-oF Storage Fabric?

Self-hosting an NVMe-oF storage fabric gives you complete control over your storage performance and data locality. Unlike cloud providers that charge per-IOPS and limit throughput, your own NVMe-oF deployment runs at line speed — limited only by your network and NVMe drives.

For organizations running database clusters, virtual machine hypervisors, or container orchestration platforms, NVMe-oF eliminates the storage bottleneck. Instead of provisioning local NVMe on each server (which wastes capacity when nodes are idle), you centralize fast storage and allocate dynamically. One 8TB NVMe drive shared via NVMe-oF can serve five compute nodes more efficiently than five individual 2TB drives installed locally.

Security is another advantage. NVMe-oF with DH-HMAC-CHAP authentication ensures only authorized initiators can access storage subsystems. The SPDK target supports TLS encryption for NVMe/TCP connections, protecting data in flight across your network fabric. For environments subject to compliance requirements (HIPAA, PCI-DSS, SOC 2), this is table stakes.

From a cost perspective, disaggregated NVMe storage reduces hardware spend. You invest in fewer, higher-quality NVMe drives and share them across your fleet. NVMe drives are more expensive per-terabyte than SATA SSDs, but their IOPS-per-dollar ratio beats anything else on the market — and NVMe-oF lets you maximize that investment.

For related reading, see our [guide to self-hosted disk health monitoring](../self-hosted-disk-health-monitoring-scrutiny-smartd-nvme-cli-guide-2026/) for tracking NVMe drive wear, and our [iSCSI target comparison](../2026-05-10-self-hosted-iscsi-target-servers-lio-tgt-scst-guide/) for legacy SAN alternatives. If you need distributed object storage instead, check out our [S3-compatible self-hosted storage guide](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/).

## Deployment Architecture

A typical NVMe-oF deployment follows a target-initiator model:

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Compute │  │  Compute │  │  Compute │   ← NVMe Initiators
│  Node 1  │  │  Node 2  │  │  Node 3  │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     └──────────────┼──────────────┘
                    │  NVMe/TCP (10/25/40/100 GbE)
              ┌─────┴─────┐
              │   NVMe-oF │
              │   Target  │   ← SPDK / nvmet / Ceph GW
              └─────┬─────┘
                    │
              ┌─────┴─────┐
              │   NVMe    │
              │   Drives  │   ← Local NVMe SSDs
              └───────────┘
```

For high availability, deploy at least two NVMe-oF targets with Asymmetric Namespace Access (ANA) for multi-path failover. Both SPDK and the Linux kernel target support ANA, allowing initiators to detect path failures and switch to an alternate target seamlessly.

## Performance Tuning

NVMe-oF performance depends heavily on network configuration:

**For NVMe/TCP:**
- Enable jumbo frames (MTU 9000) to reduce packet overhead
- Use 25GbE or faster networking for production workloads
- Set TCP congestion control to `dcp` or `bbr`
- Increase `net.core.rmem_max` and `net.core.wmem_max` to 16MB+

**For SPDK specifically:**
- Allocate 2MB hugepages (`echo 4096 > /proc/sys/vm/nr_hugepages`)
- Pin SPDK to dedicated CPU cores (isolcpus)
- Use the `--cpumask` flag to bind to NUMA-local cores

**For kernel nvmet:**
- Enable block multi-queue (`scsi_mod.use_blk_mq=1`)
- Increase `nvmet` queue depth: `echo 128 > /sys/kernel/config/nvmet/subsystems/<nqn>/attr_cntlid_max`

## FAQ

### When should I use SPDK vs the kernel NVMe-oF target?

Use the kernel nvmet target when you want simplicity and don't need extreme performance. It's built into Linux, requires no extra packages, and integrates naturally with the block layer. Use SPDK when you need the lowest possible latency and highest IOPS — its userspace polled-mode drivers eliminate kernel context switches. For Ceph users, the Ceph NVMe-oF Gateway is the natural choice since it integrates directly with RBD.

### Does NVMe-oF work over 10GbE?

Yes. NVMe/TCP works over any TCP/IP network including 10GbE. While 25GbE or 40GbE delivers better performance for latency-sensitive workloads, 10GbE is perfectly functional for many use cases — especially when you're migrating from iSCSI or NFS, where NVMe-oF will still outperform those protocols at the same network speed.

### How does NVMe-oF compare to iSCSI?

NVMe-oF significantly outperforms iSCSI in both latency and IOPS. NVMe-oF uses a streamlined command set with up to 64K parallel queues (vs iSCSI's single queue), deeper queue depths, and lower protocol overhead. Benchmarks typically show NVMe-oF delivering 2-3x the IOPS and 30-50% lower latency compared to iSCSI on the same hardware.

### Can I use NVMe-oF with Kubernetes?

Yes. The [NVMe CSI driver](https://github.com/spdk/nvme-csi) enables Kubernetes pods to consume NVMe-oF volumes. The driver provisions NVMe namespaces, attaches them to worker nodes, and handles cleanup. Ceph NVMe-oF Gateway integrates with the Ceph CSI driver for a complete Kubernetes-native NVMe-oF experience.

### Does NVMe-oF require special NICs?

For NVMe/TCP, no — any standard Ethernet NIC works. NVMe/RDMA requires RDMA-capable NICs (RoCE v2 or InfiniBand). NVMe/FC requires Fibre Channel HBAs. For most self-hosted deployments, NVMe/TCP is the recommended starting point since it works with existing network infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NVMe over Fabrics: SPDK vs Linux NVMe-TCP vs Ceph NVMe-oF Gateway",
  "description": "Compare SPDK, Linux kernel NVMe-TCP target, and Ceph NVMe-oF Gateway for self-hosted storage fabric deployments. Includes Docker Compose configs, performance tuning, and deployment architecture.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 科技相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
