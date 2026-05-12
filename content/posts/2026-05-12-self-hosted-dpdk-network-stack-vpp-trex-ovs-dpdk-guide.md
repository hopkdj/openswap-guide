---
title: "Self-Hosted DPDK Network Stack: VPP vs TRex vs OVS-DPDK Guide"
date: "2026-05-12"
description: "Compare high-performance DPDK-based network solutions — FD.io VPP, TRex traffic generator, and OVS-DPDK for userspace packet processing at line rate."
tags: ["dpdk", "networking", "performance", "packet-processing", "self-hosted"]
draft: false
---

The Data Plane Development Kit (DPDK) enables userspace packet processing at line rate by bypassing the kernel network stack. For organizations running high-throughput network services — routers, load balancers, firewalls, or traffic generators — DPDK-based solutions deliver performance that kernel networking simply cannot match.

This guide compares three prominent DPDK-powered solutions — **FD.io VPP**, **TRex traffic generator**, and **Open vSwitch with DPDK** — covering their architectures, deployment models, and ideal use cases for self-hosted infrastructure.

## What Is DPDK and Why Use Userspace Networking?

Traditional Linux networking passes every packet through the kernel: interrupt → softirq → network stack → socket buffer → userspace application. Each layer adds latency and CPU overhead. At multi-gigabit speeds, this becomes a bottleneck — the kernel spends more time managing packets than your application spends processing them.

DPDK changes this model entirely:

- **Kernel bypass** — network interface cards (NICs) are bound to DPDK drivers, removing the kernel from the data path
- **Poll-mode drivers** — instead of interrupt-driven processing, DPDK polls NIC rings continuously, eliminating interrupt overhead
- **Hugepages** — memory is allocated in 2MB or 1GB hugepages, reducing TLB misses and page walk latency
- **Lock-free data structures** — ring buffers and batch processing minimize synchronization overhead
- **CPU pinning** — dedicated CPU cores handle packet processing without context switching

The result: single-core packet processing at 10-40 Gbps, with latencies under 1 microsecond.

## Tool Comparison Overview

| Feature | FD.io VPP | TRex | OVS-DPDK |
|---------|-----------|------|----------|
| Type | Virtual router / switch | Traffic generator | Virtual switch |
| Primary use | Routing, forwarding, NFV | Traffic testing, benchmarking | SDN, virtual networking |
| Max throughput | 100+ Gbps (multi-core) | 200+ Gbps (stateless) | 40+ Gbps (multi-core) |
| Protocol support | Full TCP/IP stack (L2-L7) | L4-L7 traffic generation | L2-L4 switching |
| Traffic generation | Limited (packet gen plugin) | Core competency | No |
| Routing protocols | BGP, OSPF, IS-IS (plugins) | N/A | None (switching only) |
| Configuration | CLI, YAML, VNET | Python API, GUI | ovs-vsctl, OVSDB |
| Docker deployment | Yes (privileged, DPDK devices) | Yes (privileged, DPDK devices) | Yes (privileged, DPDK devices) |
| GitHub stars | 1,529+ | 1,483+ | 3,946+ |
| Last active | 2026 | 2026 | 2026 |

## FD.io VPP: High-Performance Virtual Router

**VPP** (Vector Packet Processing) is the flagship project of the FD.io (Fast Data I/O) open-source consortium. It implements a complete virtual router and switch using DPDK for line-rate packet processing, with a plugin architecture that supports routing protocols, NAT, firewall, and more.

### Architecture

VPP uses a vector processing model: instead of processing one packet at a time, it groups packets into vectors and applies the same graph node function to all packets in the vector. This maximizes CPU cache utilization and instruction-level parallelism.

```
┌────────────────────────────────────────────────────┐
│                    VPP Graph Nodes                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ dpdk-input│→│ ethernet  │→│  ip4-     │→ ...     │
│  │ (packets) │  │ input    │  │  lookup   │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ ip4-     │→│ ip4-     │→│ dpdk-    │            │
│  │ neighbor │  │ rewrite  │  │ output   │            │
│  └──────────┘  └──────────┘  └──────────┘          │
└────────────────────────────────────────────────────┘
              DPDK PMD drivers (kernel bypass)
```

### Deployment

**Docker Compose** (requires DPDK-compatible NIC with vfio-pci or uio_pci_generic binding):
```yaml
version: "3.8"
services:
  vpp:
    image: ligato/vpp-base:latest
    privileged: true
    volumes:
      - /dev/hugepages:/dev/hugepages
      - /var/run/vpp:/var/run/vpp
      - ./vpp-config:/etc/vpp
    environment:
      - VPP_CONFIG=/etc/vpp/startup.conf
    cap_add:
      - SYS_ADMIN
      - IPC_LOCK
    command: >
      bash -c "
        mkdir -p /dev/hugepages && mount -t hugetlbfs none /dev/hugepages
        echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
        vpp -c /etc/vpp/startup.conf
      "
    restart: unless-stopped
```

**VPP startup configuration** (`startup.conf`):
```
unix {
  nodaemon
  cli-listen /run/vpp/cli.sock
  gid vpp
  full-coredump
}

dpdk {
  dev 0000:03:00.0
  dev 0000:03:00.1
  num-mbufs 65536
  log-level notice
}

api-trace {
  on
}
```

**Basic routing configuration** (via VPP CLI):
```bash
# Connect to VPP CLI
vppctl

# Configure interfaces
set interface ip address HundredGigabitEthernet3/0/0 10.0.1.1/24
set interface ip address HundredGigabitEthernet3/0/1 10.0.2.1/24
set interface state HundredGigabitEthernet3/0/0 up
set interface state HundredGigabitEthernet3/0/1 up

# Enable IP forwarding
ip route add 10.0.3.0/24 via 10.0.2.2

# Show forwarding table
show ip fib
show interfaces
```

## TRex: Stateless and Stateful Traffic Generator

**TRex** (Traffic Generator) by Cisco is a high-performance, DPDK-based traffic generator designed for network equipment testing, performance benchmarking, and load testing. It can generate realistic L4-L7 traffic at hundreds of gigabits per second from a single server.

### Key Capabilities

- **Stateless traffic** — raw packet generation at line rate (UDP, TCP, custom protocols)
- **Stateful traffic** — full TCP session emulation with realistic application-layer payloads
- **Traffic profiles** — Python-based traffic templates for complex multi-flow scenarios
- **Real-time statistics** — per-flow latency, jitter, packet loss, and throughput metrics
- **ASTF mode** — Advanced Stateful Traffic Feature for emulating thousands of concurrent sessions
- **GUI dashboard** — web-based interface for traffic configuration and monitoring

### Deployment

**Docker Compose**:
```yaml
version: "3.8"
services:
  trex:
    image: trex-tgn
    build:
      context: ./trex-docker
    privileged: true
    volumes:
      - /dev/hugepages:/dev/hugepages
      - ./trex-cfg:/etc/trex
    ports:
      - "4500:4500"  # RPC server
      - "4501:4501"  # Text UI
      - "80:80"      # Web GUI
    cap_add:
      - SYS_ADMIN
      - IPC_LOCK
    command: >
      bash -c "
        echo 2048 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
        ./t-rex-64 -i --cfg /etc/trex/trex_cfg.yaml
      "
    restart: unless-stopped
```

**TRex configuration** (`trex_cfg.yaml`):
```yaml
- port_limit: 2
  version: 2
  interfaces: ["03:00.0", "03:00.1"]
  port_info:
    - ip: 10.0.0.1
      default_gw: 10.0.0.2
    - ip: 10.0.1.1
      default_gw: 10.0.1.2
```

**Generate traffic** (Python API):
```python
from trex_stl import *

# Create client
client = STLClients("127.0.0.1")

# Create base traffic stream
stream = STLStream(
    packet=STLPktBuilder(
        pkt=Ether()/IP(src="16.0.0.1", dst="48.0.0.1")/UDP()/
            ('X' * 100)
    ),
    mode=STLTXCont(pps=1000000)  # 1M packets/sec
)

# Add stream to port and start
client.add_streams(stream, ports=[0])
client.start(ports=[0], mult='100%')

# Get statistics
stats = client.get_stats()
print(f"TX: {stats[0]['tx_pkts']} packets, RX: {stats[1]['rx_pkts']} packets")
```

## OVS-DPDK: Software-Defined Networking at Line Rate

**Open vSwitch with DPDK** (OVS-DPDK) combines the industry-standard OVS virtual switch with DPDK's userspace packet processing. This provides SDN capabilities (OpenFlow, OVSDB, VLAN, VXLAN) with near-wire-speed performance.

### Architecture

OVS-DPDK replaces the kernel datapath with a userspace DPDK datapath. The control plane (ovs-vswitchd, ovsdb-server) remains in userspace and manages flow rules, while the datapath processes packets entirely in userspace through DPDK PMDs.

```
┌──────────────────────────────────────────┐
│  ovs-vswitchd (control + datapath)        │
│  ┌────────────┐  ┌──────────────────┐    │
│  │ OpenFlow   │  │ DPDK datapath    │    │
│  │ controller │  │ (userspace)      │    │
│  └────────────┘  └──────────────────┘    │
│                                           │
│  ┌────────────┐  ┌──────────────────┐    │
│  │ OVSDB      │  │ DPDK PMD threads  │    │
│  │ server     │  │ (polling NICs)    │    │
│  └────────────┘  └──────────────────┘    │
└──────────────────────────────────────────┘
              DPDK-bound NICs (no kernel)
```

### Deployment

**Docker Compose**:
```yaml
version: "3.8"
services:
  ovs-dpdk:
    image: openvswitch/ovs:latest
    privileged: true
    volumes:
      - /dev/hugepages:/dev/hugepages
      - /var/run/openvswitch:/var/run/openvswitch
      - /etc/openvswitch:/etc/openvswitch
    cap_add:
      - SYS_ADMIN
      - IPC_LOCK
      - NET_ADMIN
    environment:
      - DB_SOCK=/var/run/openvswitch/db.sock
    command: >
      bash -c "
        echo 2048 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
        ovsdb-tool create /etc/openvswitch/conf.db
        ovsdb-server --remote=punix:/var/run/openvswitch/db.sock
        ovs-vswitchd --dpdk -c 0x3 -n 4 --
        ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-init=true
        sleep infinity
      "
    restart: unless-stopped
```

**Configure OVS-DPDK ports and flows**:
```bash
# Initialize DPDK in OVS
ovs-vsctl set Open_vSwitch . other_config:dpdk-init=true
ovs-vsctl set Open_vSwitch . other_config:pmd-cpu-mask=0x6

# Add DPDK ports
ovs-vsctl add-br br0 -- set bridge br0 datapath_type=netdev
ovs-vsctl add-port br0 dpdk0 -- set Interface dpdk0 type=dpdk
ovs-vsctl add-port br0 dpdk1 -- set Interface dpdk1 type=dpdk

# Add VLAN and VXLAN tunnels
ovs-vsctl add-port br0 vxlan0 -- set Interface vxlan0 type=vxlan options:remote_ip=10.0.0.2

# Show configuration
ovs-vsctl show
ovs-ofctl dump-flows br0
```

## Choosing the Right DPDK Solution

| Scenario | Recommended Tool | Rationale |
|----------|-----------------|-----------|
| High-speed routing / forwarding | VPP | Full L3 routing with BGP, OSPF, IS-IS plugins |
| Network testing / benchmarking | TRex | Industry-standard traffic generation with real-time analytics |
| SDN / virtual networking | OVS-DPDK | OpenFlow, VXLAN, VLAN with DPDK performance |
| NFV platform | VPP | Plugin architecture for firewall, NAT, DPI |
| Load testing web services | TRex | Stateful HTTP/HTTPS traffic emulation |
| Cloud networking | OVS-DPDK | Neutron/OVN integration, multi-tenant isolation |

## Why Self-Host DPDK Infrastructure?

Running DPDK-based networking on self-hosted hardware gives organizations complete control over their network data plane. Cloud-managed network services impose throughput limits, add per-gigabyte egress charges, and introduce latency from virtualized networking layers.

With self-hosted DPDK, you control the entire packet processing pipeline — from NIC driver selection and CPU core pinning to flow table configuration and QoS policies. This matters most for organizations processing millions of packets per second: every microsecond of kernel bypass translates to measurable cost savings and performance gains.

Self-hosted DPDK infrastructure also enables custom protocol development that cloud providers simply don't support. Whether you need specialized packet inspection, custom encapsulation protocols, or protocol-specific load balancing, running VPP, TRex, or OVS-DPDK on bare metal gives you the flexibility to implement exactly what your application requires.

For network simulation and testing workflows, see our [GNS3 vs EVE-ng vs ContainerLab comparison](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) and [packet capture tools guide](../2026-04-27-tcpdump-vs-tshark-vs-termshark-self-hosted-packet-capture-guide-2026/). If you need network discovery capabilities, our [NetDisco vs LibreNMS vs OpenNMS guide](../2026-04-25-netdisco-vs-librenms-vs-opennetadmin-network-discovery-guide-2026/) covers monitoring options.

## FAQ

### What hardware requirements does DPDK have?

DPDK requires NICs with DPDK-compatible drivers. Most Intel (ixgbe, i40e, ice), Mellanox (mlx5), and Broadcom (bnxt) NICs are supported. You also need hugepage support in the kernel (CONFIG_HUGETLBFS), CPU with SSE4.2 or later for optimized PMDs, and sufficient RAM for packet buffers (typically 2-4GB for multi-Gbps setups). Network interfaces must be bound to vfio-pci or uio_pci_generic kernel modules instead of their standard drivers.

### Can VPP replace a physical router?

VPP can handle the forwarding plane of a software router at performance levels comparable to mid-range hardware routers. With multi-core configurations, VPP processes 10-100 million packets per second. For small-to-medium deployments, VPP with BGP/OSPF plugins can serve as a complete edge router. However, it lacks hardware acceleration features (TCAM-based forwarding, hardware crypto) that enterprise routers provide.

### How does TRex compare to iPerf for load testing?

iPerf generates simple TCP/UDP streams at the socket level, limited by kernel networking overhead (typically 10-25 Gbps per server). TRex operates at the packet level using DPDK, generating realistic multi-flow traffic at 100-200+ Gbps with per-flow statistics. TRex is better for testing firewalls, load balancers, and DPI systems where per-flow state matters. Use iPerf for simple bandwidth tests; use TRex for realistic multi-flow, multi-protocol load testing.

### Is OVS-DPDK compatible with Kubernetes?

Yes, OVS-DPDK integrates with Kubernetes through the Multus CNI plugin and the SR-IOV Network Device Plugin. This allows Kubernetes pods to connect to OVS-DPDK bridges for high-performance networking. The OVN-Kubernetes project also supports DPDK datapath for OpenShift and vanilla Kubernetes deployments, providing SDN capabilities with userspace packet processing performance.

### How many CPU cores does a DPDK application need?

The minimum is one dedicated core for the DPDK poll-mode driver thread. In practice, production deployments use: 1 core for RX/TX polling, 1-2 cores for packet processing (VPP graph nodes, OVS flow matching), and optionally 1 core for the control plane. TRex uses 2+ cores for packet generation (one per port pair). The exact count depends on throughput requirements — benchmark with your specific traffic patterns.

### What is the difference between VFIO and UIO for DPDK?

Both provide userspace device access for DPDK PMD drivers. VFIO (Virtual Function I/O) is the modern, secure approach — it provides IOMMU-based DMA protection and interrupt remapping, allowing DPDK to run without full root privileges. UIO (Userspace I/O) is the legacy approach with no IOMMU protection, requiring full root access. Always prefer VFIO for production DPDK deployments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DPDK Network Stack: VPP vs TRex vs OVS-DPDK Guide",
  "description": "Compare high-performance DPDK-based network solutions — FD.io VPP, TRex traffic generator, and OVS-DPDK for userspace packet processing at line rate.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
