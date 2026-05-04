---
title: "Self-Hosted Network Traffic Generation: TRex, MoonGen, and Pktgen Load Testing Guide 2026"
date: 2026-05-04T12:00:00+00:00
tags: ["networking", "traffic-generation", "load-testing", "trex", "moongen", "pktgen", "network-testing", "performance"]
draft: false
---

Network traffic generation tools create realistic network workloads to test infrastructure capacity, validate firewall rules, benchmark switch/router performance, and verify network monitoring systems. Unlike application-level load testing tools that generate HTTP requests, traffic generators operate at the **packet level**, giving you precise control over protocol headers, traffic patterns, and line-rate performance testing.

These tools are essential for network engineers who need to validate infrastructure before deployment, test QoS configurations under realistic load, or benchmark new hardware against vendor specifications.

## What Is Packet-Level Traffic Generation?

Application-level load tools (like k6, Locust, or Gatling) generate traffic by making HTTP/gRPC requests from user-space applications. Packet-level traffic generators bypass the OS network stack entirely and inject raw Ethernet frames directly through the network interface card (NIC), achieving **line-rate throughput** of 10-100+ Gbps on modern hardware.

This distinction matters because:
- **Firewall testing** requires malformed packets, protocol violations, and edge-case header combinations
- **Switch benchmarking** needs line-rate traffic to measure forwarding capacity and latency
- **QoS validation** requires specific traffic classes with precise bandwidth ratios
- **Monitoring verification** needs known traffic patterns to validate flow collection accuracy

## TRex — Cisco's Open Source Traffic Generator

[TRex](https://github.com/cisco-system-traffic-generator/trex-core) is Cisco's open-source stateful and stateless traffic generator with 1,500+ GitHub stars. It supports both simple stateless traffic replay and complex stateful traffic with TCP/UDP session tracking.

**Key Features:**
- Stateless and stateful traffic generation
- Up to 200 Gbps on dual-port 100G NICs
- Python-based traffic profiles with full programmability
- Built-in latency measurement with hardware timestamps
- Real-time statistics dashboard (text and web UI)
- Supports IPv4/IPv6, VLAN, MPLS, VXLAN encapsulation
- TCP state machine emulation (SYN, ACK, retransmission)

**Installation:**

```bash
# Clone and install
git clone https://github.com/cisco-system-traffic-generator/trex-core.git
cd trex-core
# Requires Python 3.6+ and DPDK-capable NIC
# TRex binds directly to NICs, bypassing the OS stack
```

**Docker Compose Setup:**

```yaml
version: "3.8"
services:
  trex-server:
    image: trex-tgn:latest
    privileged: true
    network_mode: host
    volumes:
      - ./trex-cfg:/etc/trex_cfg.yaml
      - ./profiles:/opt/trex/v2.95/traffic_profiles
      - ./results:/results
    command: >
      bash -c "/opt/trex/v2.95/t-rex-64 -i --cfg /etc/trex_cfg.yaml"
    ulimits:
      memlock: -1
      nofile:
        soft: 65536
        hard: 65536

  trex-console:
    image: trex-tgn:latest
    volumes:
      - ./profiles:/opt/trex/v2.95/traffic_profiles
    command: >
      bash -c "sleep 5 &&
               ./trex-console -s trex-server"
    depends_on:
      - trex-server
```

**Example Traffic Profile (Python):**

```python
from trex_stl_lib.api import *

def create_traffic():
    # Stateless: simple UDP stream
    base_pkt = Ether()/IP(src="16.0.0.1", dst="48.0.0.1")/UDP(sport=1234, dport=80)/Raw('x' * 60)
    
    vm = STLScVmRaw([
        STLVmFlowVar(name="src_ip", min_value="16.0.0.1", max_value="16.0.0.255", size=4, op="inc"),
        STLVmWrFlowVar(fv_name="src_ip", pkt_offset="IP.src"),
        STLVmFixIpv4(offset="IP")
    ])
    
    return STLStream(packet=STLPktBuilder(pkt=base_pkt, vm=vm),
                     mode=STLTXCont(percentage=100))
```

## MoonGen — High-Speed Packet Generation

[MoonGen](https://github.com/emmericp/MoonGen) is a high-speed packet generator built on DPDK and LuaJIT, achieving line-rate on 10G and 40G NICs. It is designed for research and benchmarking with precise timing control.

**Key Features:**
- LuaJIT-based scripting for traffic profiles
- Line-rate packet generation on 10G/40G NICs
- Precise inter-packet timing control (nanosecond accuracy)
- Hardware timestamp support for latency measurement
- Built-in rate limiting and traffic shaping
- Support for custom protocol headers

**Installation:**

```bash
# Clone the repository
git clone https://github.com/emmericp/MoonGen.git
cd MoonGen
git submodule update --init --recursive
./build.sh
# Requires DPDK-compatible NIC and hugepages
```

**Example MoonGen Script:**

```lua
local mg = require "MoonGen"
local device = require "device"
local memory = require "memory"
local hist = require "histogram"

function master(txPort, rxPort, rate)
    txDev = device.config{port = txPort, rxQueues = 2, txQueues = 2}
    rxDev = device.config{port = rxPort, rxQueues = 2, txQueues = 2}
    device.wait()
    
    txDev:getTxQueue(0):setRate(rate)
    
    local txTask = txDev:getTxQueue(0):fillPacket{
        ethDst = "ff:ff:ff:ff:ff:ff",
        ethType = 0x0800,
        ip4Dst = "192.168.1.1",
        udpSrc = 1234,
        udpDst = 80,
        pktLength = 64
    }
    
    mg.sleepMillis(10000)
    txTask:stop()
end
```

## Pktgen — Interactive Packet Generator

[Pktgen](https://pktgen-dpdk.readthedocs.io/) is an interactive, DPDK-based packet generator with a curses-based terminal UI. It provides real-time control and monitoring of traffic streams without requiring scripting.

**Key Features:**
- Interactive terminal UI with real-time statistics
- Per-port and per-queue traffic control
- Real-time traffic pattern modification
- Supports unicast, multicast, and broadcast
- VLAN tagging and IPv6 support
- Built-in throughput and latency measurement
- Scriptable via Lua for automated testing

**Installation:**

```bash
# Build from source (requires DPDK)
git clone https://github.com/pktgen/Pktgen-DPDK.git
cd Pktgen-DPDK
meson setup build
ninja -C build
```

**Docker Compose Setup:**

```yaml
version: "3.8"
services:
  pktgen:
    image: pktgen-dpdk:latest
    privileged: true
    network_mode: host
    volumes:
      - ./scripts:/scripts
      - ./results:/results
    environment:
      - RTE_SDK=/opt/dpdk
      - DPDK_NIC1=0000:03:00.0
      - DPDK_NIC2=0000:03:00.1
    command: >
      bash -c "/opt/pktgen/app/x86_64-native-linuxapp-gcc/pktgen -l 0-3 -n 4 -- -P -m '1.0,2.1'"
    ulimits:
      memlock: -1
```

## Comparison Table

| Feature | TRex | MoonGen | Pktgen |
|---------|------|---------|--------|
| Developer | Cisco | Academic (TU Berlin) | Individual/Open Source |
| GitHub Stars | 1,500+ | 1,800+ | 500+ (docs repo) |
| Scripting Language | Python | LuaJIT | Lua + Interactive UI |
| Max Throughput | 200 Gbps | 40 Gbps | 100 Gbps |
| Stateless Traffic | ✅ Yes | ✅ Yes | ✅ Yes |
| Stateful Traffic | ✅ TCP emulation | ❌ No | ⚠️ Limited |
| Real-time UI | ✅ Web + Text | ❌ No | ✅ Curses terminal |
| Hardware Timestamps | ✅ Yes | ✅ Yes | ✅ Yes |
| Protocol Support | IPv4/6, VLAN, MPLS, VXLAN | IPv4/6, VLAN, Custom | IPv4/6, VLAN |
| DPDK Required | ✅ Yes | ✅ Yes | ✅ Yes |
| Docker Friendly | ✅ Good | ⚠️ Moderate | ⚠️ Moderate |
| Use Case | Network testing, benchmarking | Research, precise timing | Interactive testing |
| License | Apache 2.0 | MIT | BSD |

## When to Use Packet-Level Traffic Generators

### Firewall and IDS Testing

Generate traffic with malformed headers, protocol violations, and known attack patterns to verify your firewall or intrusion detection system correctly blocks malicious traffic:

```bash
# TRex: Generate traffic with invalid TCP flags
trex-console
start -f profiles/malformed_tcp.py --port 0
```

### Switch and Router Benchmarking

Test maximum forwarding rate, latency, and buffer behavior under sustained line-rate load. This is the standard methodology used by the [RFC 2544](https://tools.ietf.org/html/rfc2544) and [RFC 2889](https://tools.ietf.org/html/rfc2889) benchmarking frameworks.

### QoS Policy Validation

Verify that Quality of Service policies correctly classify and prioritize traffic under realistic mixed-workload conditions:

```python
# TRex: Mixed traffic with different DSCP values
streams = [
    create_stream(dscp=46, rate=0.4),   # EF - voice
    create_stream(dscp=26, rate=0.3),   # AF31 - video
    create_stream(dscp=0, rate=0.3),    # BE - best effort
]
```

### Network Monitoring Verification

Inject known traffic patterns to validate that your flow collectors (NetFlow, sFlow, IPFIX) accurately capture and report traffic statistics. See our [NetFlow analyzer comparison](../elastiflow-vs-akvorado-vs-goflow2-self-hosted-netflow-collector-guide-2026/) for tools that consume this data.

For packet capture and analysis of the generated traffic, use [tcpdump vs tshark vs Termshark](../2026-04-27-tcpdump-vs-tshark-vs-termshark-self-hosted-packet-capture-guide-2026/). For Kubernetes-level traffic analysis during testing, check [Kubeshark vs ksniff vs Wireshark](../2026-04-29-kubeshark-vs-ksniff-vs-wireshark-kubernetes-traffic-analysis-guide-2026/).

## Why Self-Host Traffic Generation?

Commercial traffic generators (Spirent, IXIA) cost $10,000-$100,000+ and require proprietary hardware. Open-source alternatives running on commodity DPDK-capable NICs deliver comparable performance at a fraction of the cost:

- **Cost-effective** — software-only solution on standard server hardware
- **Programmable** — define complex traffic patterns in Python or Lua
- **Reproducible** — scripted tests ensure consistent benchmarking methodology
- **Extensible** — add custom protocol support for proprietary or emerging standards
- **Integrated** — run traffic generation alongside your self-hosted monitoring stack

## FAQ

### What is DPDK and why do traffic generators need it?

DPDK (Data Plane Development Kit) is a set of libraries and drivers that allows user-space applications to bypass the Linux kernel network stack and access NICs directly. This enables packet processing at line rate (millions of packets per second) without kernel overhead. All three tools in this guide require DPDK-compatible NICs.

### Can I run TRex in a virtual machine?

TRex can run in a VM if the hypervisor provides SR-IOV or PCI passthrough for the NICs. Without hardware passthrough, TRex falls back to a software loopback mode that cannot achieve line-rate. For testing purposes, TRex's loopback mode works fine for validating traffic profiles and logic.

### Do I need special hardware for packet-level traffic generation?

You need a DPDK-compatible NIC (Intel ixgbe, i40e, or mlx5 drivers are well-supported) and a CPU with enough cores to handle packet processing. For 10Gbps testing, a modern 4-core CPU and Intel X520 NIC (~$50 used) is sufficient. For 100Gbps+, you need multi-core server CPUs and 100G NICs.

### What is the difference between stateful and stateless traffic?

**Stateless** traffic sends packets without tracking connections — each packet is independent. **Stateful** traffic emulates real TCP/UDP sessions with proper handshakes, acknowledgments, retransmissions, and connection teardown. Stateful testing is essential for testing firewalls, load balancers, and NAT devices that track connection state.

### How does TRex compare to application-level load tools like k6?

TRex operates at the packet level (Layer 2-4), generating raw Ethernet frames at line rate. k6 operates at the application level (Layer 7), making HTTP/gRPC requests. TRex is for testing network infrastructure (switches, routers, firewalls); k6 is for testing web APIs and applications. They are complementary: use TRex to validate your network can handle the traffic, then k6 to validate your application performs correctly.

### Can I generate realistic user traffic patterns?

Yes. TRex supports traffic replay from PCAP files, allowing you to capture real user traffic and replay it at any scale. MoonGen and Pktgen also support PCAP-based replay. This is invaluable for testing with realistic traffic mixes rather than synthetic patterns.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Traffic Generation: TRex, MoonGen, and Pktgen Load Testing Guide 2026",
  "description": "Guide to self-hosted network traffic generation using TRex, MoonGen, and Pktgen. Compare packet-level traffic generators for firewall testing, switch benchmarking, and QoS validation.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
