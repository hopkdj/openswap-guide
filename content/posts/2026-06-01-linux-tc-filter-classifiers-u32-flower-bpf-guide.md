---
title: "Linux Traffic Control Filter Classifiers: tc-u32 vs tc-flower vs tc-bpf"
date: "2026-06-01"
tags: ["linux", "networking", "traffic-control", "tc", "qos", "ebpf", "packet-filtering"]
draft: false
---

## Introduction

Linux traffic control (`tc`) is the kernel's Swiss Army knife for packet scheduling, shaping, and classification. At its core, `tc` uses classifiers (filters) attached to queuing disciplines (qdiscs) to match packets and direct them to the correct queue. Choosing the right classifier determines both the accuracy of your traffic shaping and the CPU cost per packet.

Three classifiers dominate production use: the universal 32-bit filter (tc-u32), the flow-based classifier (tc-flower), and the extended Berkeley Packet Filter classifier (tc-bpf). Each serves a distinct niche — from simple IP/port matching to full deep packet inspection with programmable logic. This article compares their capabilities, performance, and real-world deployment patterns.

| Feature | tc-u32 | tc-flower | tc-bpf |
|---------|--------|-----------|--------|
| **Matching Capability** | Fixed-offset bit patterns | Flow keys (L2-L4) | Full programmable BPF |
| **Performance** | Fast (hash lookups) | Fast (flow dissector) | Fastest (JIT compiled) |
| **Complexity** | Low | Medium | High |
| **Kernel Support** | 2.2+ | 3.3+ (enhanced 4.1+) | 3.18+ |
| **Use Case** | Simple IP/port/VLAN match | OpenFlow/OVS pipeline | Custom logic, DPI |
| **Offload Support** | No | Hardware (TC Flower) | Hardware (XDP) |
| **IPv6 Support** | Manual offset | Native | Native |
| **Encapsulation** | Manual parsing | VXLAN/GENEVE/GRE | Programmable |
| **Learning Curve** | Moderate | Easy | Steep (requires C/eBPF) |

## tc-u32: The Universal Classifier

`tc-u32` is the original general-purpose classifier, introduced in kernel 2.2. It matches arbitrary bit patterns at fixed offsets within packet headers. The "u32" name comes from its core operation: extracting 32-bit words from the packet and comparing them against a mask and value.

```bash
# Match SSH traffic (TCP port 22) and direct to class 1:10
tc qdisc add dev eth0 root handle 1: htb default 30
tc class add dev eth0 parent 1: classid 1:10 htb rate 100mbit
tc class add dev eth0 parent 1: classid 1:30 htb rate 10mbit

# u32 filter: match TCP destination port 22
tc filter add dev eth0 protocol ip parent 1: prio 1 u32 \
    match ip protocol 6 0xff \
    match tcp dst 22 0xffff \
    flowid 1:10
```

u32 filters can match any byte range in a packet:

```bash
# Match packets from 192.168.1.0/24 network
tc filter add dev eth0 protocol ip parent 1: prio 2 u32 \
    match ip src 192.168.1.0/24 \
    flowid 1:20

# Match VLAN-tagged traffic (VLAN ID 100)
tc filter add dev eth0 protocol 802.1q parent 1: prio 3 u32 \
    match u16 0x0064 0x0fff at -4 \
    flowid 1:30

# Match DSCP EF (Expedited Forwarding, value 46 = 0x2e)
tc filter add dev eth0 protocol ip parent 1: prio 4 u32 \
    match ip tos 0xb8 0xfc \
    flowid 1:10
```

u32's strength is simplicity — no kernel headers or external dependencies needed. Its weakness is that offset-based matching breaks with variable-length headers (IPv6 extension headers, VLAN stacking, MPLS labels). You must manually account for header offsets, which becomes fragile as network complexity grows.

## tc-flower: Flow-Based Classification

`tc-flower` (Flow Layer) provides named field matching using the kernel's flow dissector. Instead of raw byte offsets, you match by protocol field names — `src_ip`, `dst_port`, `vlan_ethtype`, and more. flower is the classifier used by Open vSwitch and many SDN controllers, and it supports hardware offloading on supported NICs.

```bash
# Basic flower: match SSH to specific class
tc filter add dev eth0 protocol ip parent 1: prio 1 flower \
    ip_proto tcp dst_port 22 \
    action mirred egress redirect dev eth1

# Match encrypted traffic on VLAN 100 with specific source
tc filter add dev eth0 protocol 802.1q parent 1: prio 2 flower \
    vlan_id 100 \
    vlan_ethtype ip \
    src_ip 10.0.0.0/8 \
    ip_proto tcp \
    dst_port 443 \
    action skbedit priority 1 \
    action goto chain 1

# Match VXLAN encapsulated traffic
tc filter add dev eth0 protocol ip parent 1: prio 3 flower \
    enc_dst_ip 172.16.0.0/12 \
    enc_dst_port 4789 \
    enc_key_id 1000 \
    action mirred egress redirect dev vxlan100
```

flower supports encapsulation matching (VXLAN, GENEVE, GRE) natively, making it the preferred classifier for tunneling and overlay network scenarios. It also integrates with `tc chains` for multi-stage pipeline processing:

```bash
# Create a filter chain
tc chain add dev eth0 ingress protocol ip chain 0
tc filter add dev eth0 ingress protocol ip chain 0 flower \
    ip_proto tcp \
    action jump 1

# Chain 1: rate-limit matched traffic
tc filter add dev eth0 ingress protocol ip chain 1 flower \
    dst_port 80 \
    action police rate 50mbit burst 10k conform-exceed drop/ok
```

## tc-bpf: Programmable Packet Classification

`tc-bpf` lets you attach compiled BPF programs as classifiers. The BPF program runs for every packet and returns a classid (or -1 for no match). This gives you Turing-complete packet inspection — match on any header combination, maintain per-flow state using BPF maps, and combine classification with custom actions.

```c
// classify_traffic.c — BPF program for traffic classification
#include <linux/bpf.h>
#include <linux/pkt_cls.h>
#include <linux/ip.h>
#include <linux/tcp.h>

// BPF map for tracking flow rates
struct bpf_map_def SEC("maps") flow_map = {
    .type = BPF_MAP_TYPE_HASH,
    .key_size = sizeof(__u32),
    .value_size = sizeof(__u64),
    .max_entries = 10000,
};

SEC("classifier")
int classify_packets(struct __sk_buff *skb) {
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;
    struct ethhdr *eth = data;
    
    if (data + sizeof(*eth) > data_end)
        return TC_ACT_UNSPEC;
    
    // Classify SSH (TCP/22) to class 1:10
    if (eth->h_proto == __constant_htons(ETH_P_IP)) {
        struct iphdr *ip = data + sizeof(*eth);
        if ((void *)(ip + 1) > data_end)
            return TC_ACT_UNSPEC;
        if (ip->protocol == IPPROTO_TCP) {
            struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
            if ((void *)(tcp + 1) > data_end)
                return TC_ACT_UNSPEC;
            if (tcp->dest == __constant_htons(22))
                return 0x10010; // classid 1:10
        }
    }
    return TC_ACT_UNSPEC; // no match
}

char _license[] SEC("license") = "GPL";
```

Compile and attach:

```bash
# Compile the BPF program
clang -O2 -target bpf -c classify_traffic.c -o classify_traffic.o

# Attach as a tc filter
tc qdisc add dev eth0 clsact
tc filter add dev eth0 ingress bpf \
    direct-action obj classify_traffic.o sec classifier
```

BPF classifiers are JIT-compiled to native machine code, making them the fastest option at high packet rates. They also work with XDP for even earlier packet processing before the kernel networking stack:

```bash
# Attach as XDP program (even faster than tc-bpf)
ip link set dev eth0 xdp obj classify_traffic.o sec classifier
```

## Why Self-Host Linux Traffic Control

Cloud providers offer "QoS" as an extra-cost add-on, but running your own traffic control on Linux gives you byte-level precision without ongoing fees. A single tc command can guarantee SSH access during bandwidth saturation — something no cloud dashboard exposes. For self-hosters running multiple services on a single VM, tc prevents a runaway database backup from starving your web server of bandwidth.

Network observability improves with tc classification. Tagging packets with `skbedit priority` in a flower filter lets tools like `tcpdump` and `nstat` attribute bandwidth usage to specific services. Combined with a metrics stack (Prometheus + node_exporter), you get per-queue drop counters, queue lengths, and rate measurements — all without proprietary monitoring agents.

For learning more about Linux networking, see our [Linux network bonding guide](../2026-05-08-linux-network-bonding-active-backup-vs-lacp-vs-round-robin-guide/) and our [traffic shaping and QoS comparison](../2026-05-13-self-hosted-traffic-shaping-qos-sqm-scripts-tcgui-wondershaper-guide/). If you need network-wide visibility, our [network discovery and topology guide](../2026-05-13-self-hosted-network-topology-discovery-cdpwalker-flashroute-treenet-guide/) covers the tools to map your infrastructure.

## FAQ

### Which classifier is fastest?

tc-bpf with JIT compilation is the fastest — BPF programs compile to native x86_64 or ARM64 instructions and run as kernel callbacks. tc-flower with hardware offloading (on supported NICs like Mellanox ConnectX or Intel E810) can achieve line-rate classification without consuming CPU cycles. tc-u32 with hash-table optimizations is fast enough for most workloads below 10 Gbps, typically adding 1–3 microseconds of latency per packet.

### Can I use multiple classifiers on the same interface?

Yes. tc supports a priority-based filter chain. Higher-priority filters are evaluated first. If a packet matches no filters, it falls through to the default class. A common pattern is to use tc-flower for the top 90% of traffic (simple IP/port matches) and tc-bpf for the remaining 10% that need custom logic. The kernel evaluates each filter in priority order until the first match — the matched filter returns a classid and processing stops.

### Does tc-flower work with hardware offloading?

Yes. Set `skip_sw` to bypass the software data path and `skip_hw` to force software-only processing. Hardware offloading requires a NIC that supports TC Flower offload (switchdev mode). Common supported NICs include Mellanox ConnectX-4/5/6, Intel E810 (ice driver), and Netronome Agilio. Check your NIC's capabilities with `ethtool -k eth0 | grep hw-tc-offload`.

### How do I debug tc filter matching?

Use `tc -s filter show dev eth0` to view per-filter statistics (packet count, byte count). The `-s` flag shows hit counts. If a filter shows zero hits, your match criteria may be wrong. Use `tcpdump -i eth0 -e` to inspect raw packet headers and verify your offsets (for u32) or field names (for flower). For BPF, use `bpftool prog show` to see the compiled program and `bpftool prog tracelog` for trace output.

### What is the difference between tc-bpf and XDP?

XDP (eXpress Data Path) runs BPF programs before the kernel allocates socket buffers — the program sees raw DMA packet buffers. tc-bpf runs after sk_buff allocation, inside the kernel's traffic control layer. XDP is faster (sub-microsecond processing) but has no access to conntrack, routing tables, or socket state. tc-bpf is slightly slower but can use kernel infrastructure like connection tracking and iptables marks. Use XDP for DDoS filtering and tc-bpf for quality-of-service classification.

---

**💡 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it is the world's largest prediction market platform, where you can wager on everything from election outcomes to AI regulation timelines. Unlike gambling, this is a genuine information market: the more you know, the higher your win rate. I have made solid returns predicting AI-related events. Sign up with my invite link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Linux Traffic Control Filter Classifiers: tc-u32 vs tc-flower vs tc-bpf",
  "description": "Compare tc-u32, tc-flower, and tc-bpf classifiers for Linux traffic control. Includes configuration examples, performance benchmarks, and use cases for each filter type.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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
