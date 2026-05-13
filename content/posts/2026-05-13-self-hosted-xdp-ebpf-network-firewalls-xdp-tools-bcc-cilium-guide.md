---
title: "Self-Hosted XDP/eBPF Network Firewalls: xdp-tools vs BCC vs Cilium XDP"
date: "2026-05-13"
tags: ["security", "networking", "ebpf", "self-hosted", "comparison", "guide"]
draft: false
---

XDP (eXpress Data Path) and eBPF (extended Berkeley Packet Filter) represent the most significant advancement in Linux network security in the past decade. By running packet filtering programs directly in the kernel's network driver layer, XDP firewalls achieve line-rate packet processing at millions of packets per second — far surpassing traditional iptables and nftables performance. This guide compares three leading open-source XDP/eBPF firewall toolsets: **xdp-tools**, **BCC (BPF Compiler Collection)**, and **Cilium XDP**.

## Why Use XDP/eBPF for Network Security?

Traditional Linux firewalls (iptables, nftables, firewalld) operate at the Netfilter layer, which means every packet traverses the full network stack before being evaluated. XDP programs run at the earliest possible point in the kernel — directly in the network driver's receive path — allowing packets to be dropped before any kernel processing overhead.

**Line-rate performance at scale.** XDP programs can process 10-30 million packets per second on commodity hardware, compared to roughly 1-3 million for nftables. For organizations handling DDoS attacks, high-traffic web properties, or multi-tenant infrastructure, this performance difference is the boundary between service availability and outage.

**DDoS mitigation at the edge.** XDP's ability to drop packets before they consume kernel memory or CPU makes it the ideal first line of defense against volumetric attacks. SYN flood mitigation, ICMP rate limiting, and IP blacklisting at the XDP layer consume minimal resources compared to connection tracking in Netfilter.

**Dynamic rule updates without connection interruption.** Unlike iptables, which requires full rule set replacement and can briefly interrupt established connections, eBPF programs can be atomically replaced with zero packet loss. BPF maps allow rules to be updated in-place from user space without reloading the program.

**Deep packet inspection capabilities.** eBPF programs can parse packet headers at any layer (Ethernet, IP, TCP/UDP, application layer) and make filtering decisions based on content. This enables application-aware firewall rules that traditional tools cannot express, such as blocking specific HTTP paths or DNS query patterns.

For traditional firewall management, see our [nftables GeoIP firewall guide](../2026-05-10-self-hosted-nftables-geoip-firewall-nft-geo-filter-nftables-geoip-geoipsets-guide/). For broader network security, our [SSL/TLS proxy comparison](../2026-05-15-self-hosted-ssl-tls-proxy-stunnel-sslh-hitch-guide/) covers encryption-layer security. For runtime enforcement with eBPF, our [KubeArmor vs Falco vs Tetragon guide](../2026-05-07-kubearmor-vs-falco-vs-tetragon-runtime-security-guide.) provides additional context.

## Comparison Overview

| Feature | xdp-tools | BCC (BPF Compiler Collection) | Cilium XDP |
|---------|-----------|------------------------------|------------|
| Primary Focus | XDP utilities and examples | Full eBPF toolkit | Kubernetes networking & security |
| GitHub Stars | 866 | 22,405 | 24,338 |
| Language | C + libxdp | Python + C (BPF) | Go + C (eBPF) |
| XDP Mode Support | Generic, driver, HW offload | Generic, driver | Generic, driver, HW offload |
| Kubernetes Integration | None | Limited (manual) | ✅ Native |
| Learning Curve | Medium | High | Medium |
| Use Case | XDP reference programs | Custom eBPF programs | Production K8s clusters |
| Maintenance | Kernel team | Netflix/IOVisor community | Isovalent/CNCF |
| License | GPL-2.0 / BSD-2-Clause | Apache-2.0 | Apache-2.0 |

## xdp-tools: Reference XDP Implementation Suite

xdp-tools is the official reference implementation suite from the XDP Project (xdp-project), providing utilities, libraries, and example programs for building XDP-based network security solutions.

**Architecture:** xdp-tools provides `libxdp` — a shared library that simplifies XDP program loading and management — along with a collection of production-ready XDP programs for common networking tasks. The toolkit works directly with the kernel's XDP infrastructure without additional dependencies.

**Key Features:**
- `libxdp` for simplified XDP program loading and management
- Multi-program support with dispatcher chaining
- Reference implementations for XDP forwarding, filtering, and load balancing
- Hardware offload support for compatible NICs
- XDP metadata passthrough for inter-program communication
- AF_XDP socket support for high-performance user-space packet processing

**Building and installing:**

```bash
# Clone and build
git clone https://github.com/xdp-project/xdp-tools.git
cd xdp-tools
./configure --prefix=/usr
make -j$(nproc)
sudo make install

# Load an XDP filter program
sudo xdp-loader load eth0 xdp-filter.o --mode drv

# List loaded XDP programs
sudo xdp-loader status

# Unload
sudo xdp-loader unload eth0 --all
```

**XDP filtering with custom rules:**

```bash
# Compile the XDP filter program
clang -O2 -target bpf -c xdp-filter.c -o xdp-filter.o

# Add an IP blacklist rule
sudo xdp-filter --add-ip 10.0.0.0/8 -i eth0 -p xdp-filter.o

# Add a port block rule
sudo xdp-filter --add-port 25 --proto tcp -i eth0 -p xdp-filter.o

# Dump current rules
sudo xdp-filter --dump -i eth0 -p xdp-filter.o
```

**Best for:** Network engineers and security researchers who need reference implementations and a lightweight toolkit for building custom XDP programs. Ideal for bare-metal servers and network appliances.

## BCC: Full-Featured eBPF Development Framework

BCC (BPF Compiler Collection) is the most comprehensive eBPF toolkit available, providing a Python-based framework for writing, compiling, and running eBPF programs with extensive tracing and networking tools.

**Architecture:** BCC uses a Python frontend that embeds C code for eBPF programs. At runtime, it compiles the C code to BPF bytecode using LLVM, loads it into the kernel, and attaches it to the appropriate hook points. The framework includes dozens of pre-built tools for tracing, profiling, and networking.

**Key Features:**
- 80+ pre-built eBPF tools for tracing and networking
- Python API for custom eBPF program development
- Automatic BPF-to-Python data pipe management
- Built-in tools: tcplife, tcpconnlat, bindsnoop, execsnoop, opensnoop
- Network filtering: `tc` and XDP support
- Support for kprobes, tracepoints, USDT probes, and raw tracepoints
- Active community with 22,400+ GitHub stars

**Installation:**

```bash
# Ubuntu/Debian
sudo apt-get install -y bpfcc-tools linux-headers-$(uname -r)

# RHEL/CentOS
sudo yum install -y bcc-tools

# Or build from source
git clone https://github.com/iovisor/bcc.git
mkdir bcc/build; cd bcc/build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr
make -j$(nproc)
sudo make install
```

**Network tracing and filtering examples:**

```bash
# Trace TCP connection latency
sudo /usr/share/bcc/tools/tcpconnlat

# Monitor new TCP connections
sudo /usr/share/bcc/tools/tcplife

# Trace DNS queries (network-level monitoring)
sudo /usr/share/bcc/tools/bindsnoop -p 53

# Monitor all file opens (security auditing)
sudo /usr/share/bcc/tools/opensnoop

# Custom XDP program for DDoS mitigation
sudo bcc-xdp -i eth0 --drop-rst-flood
```

**Best for:** System administrators and developers who need a comprehensive eBPF toolkit with ready-to-use tools. The Python API makes it accessible for rapid prototyping of custom network security programs.

## Cilium XDP: Kubernetes-Native eBPF Networking

Cilium is the leading Kubernetes CNI plugin that leverages eBPF for networking, security, and observability. Its XDP integration provides line-rate packet filtering at the cluster edge.

**Architecture:** Cilium replaces the traditional Kubernetes networking stack (kube-proxy, iptables) with an eBPF-based datapath. The Cilium agent compiles eBPF programs based on Kubernetes NetworkPolicy resources and loads them into the kernel. XDP programs run at the node's network interface level, providing pre-filtering before packets enter the cluster.

**Key Features:**
- Kubernetes NetworkPolicy enforcement via eBPF
- XDP-based DDoS mitigation at cluster ingress
- L3-L7 network policy support (HTTP, DNS, Kafka)
- Service mesh capabilities without sidecar proxies
- Hubble observability with eBPF-based flow logs
- Multi-cluster networking via Cluster Mesh
- IPsec and WireGuard encryption
- CNCF graduated project status

**Helm-based installation with XDP enabled:**

```bash
# Add Cilium Helm repository
helm repo add cilium https://helm.cilium.io/

# Install Cilium with XDP acceleration
helm install cilium cilium/cilium   --namespace kube-system   --set kubeProxyReplacement=true   --set bpf.masquerade=true   --set routingMode=native   --set bpf.hostLegacyRouting=false   --set bpf.lbAcceleration=true

# Verify eBPF datapath is active
cilium status --verbose

# Check XDP mode
cilium bpf lb list
```

**XDP-based ingress filtering with NetworkPolicy:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: ddos-protection
spec:
  endpointSelector:
    matchLabels:
      app: web-frontend
  ingress:
    - fromEndpoints:
        - matchLabels:
            role: trusted
      toPorts:
        - ports:
            - port: "80"
              protocol: TCP
            - port: "443"
              protocol: TCP
    - fromCIDR:
        - 0.0.0.0/0
      icmps:
        - fields:
            - type: 8
              family: IPv4
```

**Best for:** Kubernetes operators who need eBPF-powered networking and security. Cilium's XDP integration is production-grade and handles millions of flows across large clusters.

## Choosing the Right XDP/eBPF Firewall

| Criteria | Choose xdp-tools | Choose BCC | Choose Cilium XDP |
|----------|-----------------|------------|-------------------|
| Bare-metal firewall | ✅ Best option | Good | Not applicable |
| Kubernetes clusters | No | Limited | ✅ Best option |
| DDoS mitigation | ✅ XDP-native | Good | ✅ XDP-native |
| Learning eBPF | ✅ Reference code | ✅ Tutorial tools | Documentation |
| Production readiness | Good | Good | ✅ Enterprise-grade |
| L7 policy support | No | Limited | ✅ Full HTTP/DNS |
| Observability | Manual | ✅ Built-in tools | ✅ Hubble |
| Community size | Small | Large (22K+ stars) | Largest (24K+ stars) |

## FAQ

### What is XDP and how does it differ from iptables?
XDP (eXpress Data Path) runs programs directly in the network driver's receive path, before packets enter the kernel network stack. iptables operates at the Netfilter layer, which means packets traverse the full stack before being evaluated. XDP achieves 10-30 million packets per second versus 1-3 million for iptables.

### Do I need special hardware for XDP?
No. XDP works in three modes: generic (works on any network interface, lower performance), driver (requires NIC driver support, full performance), and hardware offload (requires SmartNIC, maximum performance). Generic mode provides immediate benefits on any Linux system with kernel 4.8+.

### Can XDP replace my existing firewall?
For high-performance scenarios like DDoS mitigation and bulk packet filtering, yes. For stateful firewall rules (connection tracking, NAT), XDP needs to be combined with nftables or a full-featured solution like Cilium. XDP excels at stateless filtering at line rate.

### Is eBPF safe to use in production?
Yes. eBPF programs are verified by the kernel's eBPF verifier before loading, which guarantees they cannot crash the kernel, access invalid memory, or run indefinitely. All major cloud providers (AWS, Google Cloud, Azure) run eBPF in production at massive scale.

### How do I debug XDP programs?
Use `bpftool` to inspect loaded programs and maps: `bpftool prog show`, `bpftool map dump`. For packet-level debugging, XDP programs can use `bpf_trace_printk()` which outputs to `/sys/kernel/debug/tracing/trace_pipe`. The `xdp_monitor` tool from xdp-tools provides real-time statistics.

### What kernel version do I need for XDP?
XDP requires Linux kernel 4.8 or newer. Most modern distributions ship with kernel 5.x or 6.x, which include full XDP support. For hardware offload mode, kernel 5.3+ is recommended along with a compatible SmartNIC (Mellanox ConnectX-5 or newer).

## Choosing the Right XDP/eBPF Solution

For **bare-metal network security**, xdp-tools provides the most direct path to building custom XDP filtering programs with minimal dependencies. The reference implementations serve as excellent starting points for production firewall rules.

For **general-purpose eBPF development**, BCC offers the richest toolset with 80+ pre-built programs and a Python API that makes eBPF accessible to developers without C programming experience.

For **Kubernetes environments**, Cilium is the definitive choice, providing production-grade eBPF networking, security policies, and observability in a single CNCF-graduated project.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted XDP/eBPF Network Firewalls: xdp-tools vs BCC vs Cilium XDP",
  "description": "Compare three leading XDP/eBPF network firewall solutions: xdp-tools, BCC, and Cilium for high-performance packet filtering and DDoS mitigation.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
