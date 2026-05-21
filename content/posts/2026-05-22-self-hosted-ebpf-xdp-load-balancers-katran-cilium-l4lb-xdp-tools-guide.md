---
title: "Self-Hosted eBPF XDP Load Balancers: Katran vs Cilium L4LB vs XDP-Tools"
date: "2026-05-22"
tags: ["load-balancing", "ebpf", "xdp", "networking", "kubernetes"]
draft: false
---

Load balancing at the kernel level with eBPF and XDP (eXpress Data Path) represents the cutting edge of high-performance network traffic distribution. Traditional load balancers like HAProxy and Nginx operate at user-space, incurring packet processing overhead. XDP-based load balancers intercept packets at the earliest point in the kernel networking stack — before memory allocation and socket creation — enabling millions of packets per second on commodity hardware.

In this guide, we compare three leading open-source XDP load balancing implementations: **Facebook's Katran**, **Cilium's L4LB**, and the **XDP-Tools** reference implementation. Each takes a different approach to solving the same problem: distributing network traffic at line rate using eBPF.

## What Is XDP (eXpress Data Path)?

XDP is a Linux kernel technology that allows eBPF programs to run on incoming network packets before they enter the kernel's networking stack. This means:

- **Zero-copy processing**: Packets are processed directly from the NIC ring buffer
- **Sub-microsecond latency**: No context switch between kernel and user space
- **Massive throughput**: Tested at 10M+ packets per second on a single CPU core
- **Programmable**: Custom load balancing logic written in eBPF C or via eBPF bytecode

XDP operates at three modes:
1. **Native (driver-level)**: Best performance, requires NIC driver support
2. **Generic (kernel-level)**: Falls back to a generic kernel path, lower performance but universal
3. **Offloaded (NIC-level)**: eBPF runs directly on the NIC hardware, maximum performance

## Katran — Facebook's Layer 4 Load Balancer

Katran is Facebook's production-grade L4 load balancer built on XDP and eBPF. It powers Facebook's infrastructure, handling terabits per second of traffic across their data centers.

### Architecture

Katran uses a two-tier architecture:
- **XDP program**: Runs on the NIC, classifies packets and forwards them
- **User-space controller**: Manages VIP-to-DIP mappings, health checks, and configuration

Katran supports both **IPIP** and **GRE** encapsulation for forwarding traffic to backend servers. It uses consistent hashing (Maglev algorithm) to ensure session persistence and even distribution.

### Key Features

- **Maglev hashing**: Consistent hashing with minimal disruption on backend changes
- **Health checking**: Active health probes with automatic failover
- **QUIC support**: UDP-based load balancing with connection tracking
- **Scale**: Tested at 10M+ PPS on a single host
- **ECMP-ready**: Designed to work with equal-cost multi-path routing

### Docker Compose Deployment

Katran is primarily deployed as a kernel module with a user-space control plane. The following compose sets up the management plane:

```yaml
services:
  katran-controller:
    image: ghcr.io/facebookincubator/katran:latest
    network_mode: host
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
      - /lib/modules:/lib/modules:ro
      - ./katran-config:/etc/katran:ro
    command: ["katran_controller", "--config", "/etc/katran/config.yaml"]
    restart: unless-stopped

  katran-health-checker:
    image: ghcr.io/facebookincubator/katran:latest
    network_mode: host
    cap_add:
      - NET_RAW
    volumes:
      - ./katran-config:/etc/katran:ro
    command: ["katran_healthcheck", "--config", "/etc/katran/health.yaml"]
    restart: unless-stopped
```

The XDP program itself is loaded via `tc` or `ip link` commands on the target interface.

### When to Use Katran

- You need a battle-tested, production-grade XDP load balancer
- Your traffic volume justifies the operational complexity
- You have ECMP-capable network infrastructure
- You need consistent hashing with minimal disruption during scaling

---

## Cilium L4LB — Kubernetes-Native eBPF Load Balancing

Cilium is the most widely deployed eBPF-based networking solution for Kubernetes. Its L4LB (Layer 4 Load Balancer) replaces kube-proxy with a highly efficient XDP-based implementation.

### Architecture

Cilium's L4LB operates in two modes:
- **kube-proxy replacement**: Directly handles Service IP routing via XDP
- **External L4LB**: Load balances traffic from outside the cluster using Maglev hashing

Cilium uses **Maglev consistent hashing** (same algorithm as Katran) and supports both **direct routing** and **tunneling** (VXLAN/Geneve) for pod-to-pod communication.

### Key Features

- **kube-proxy replacement**: Full replacement with better performance
- **Maglev hashing**: Consistent, deterministic load distribution
- **DSR (Direct Server Return)**: Bypasses the load balancer on the return path
- **NodePort optimization**: Efficient NodePort handling without iptables
- **Cluster-wide service mesh**: Integrated L7 load balancing with Envoy
- **Observability**: Hubble provides flow-level visibility

### Docker Compose / Helm Deployment

Cilium is typically deployed via Helm on Kubernetes:

```yaml
# helm install cilium cilium/cilium --set kubeProxyReplacement=true
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: cilium
  namespace: kube-system
spec:
  chart:
    spec:
      chart: cilium
      version: "1.16.0"
      sourceRef:
        kind: HelmRepository
        name: cilium
  values:
    kubeProxyReplacement: true
    k8sServiceHost: "your-api-server"
    k8sServicePort: 6443
    loadBalancer:
      algorithm: maglev
      mode: snat
    hubble:
      enabled: true
      relay:
        enabled: true
      ui:
        enabled: true
```

For bare-metal deployments without Kubernetes, Cilium can run in standalone mode:

```bash
cilium-agent --enable-l4lb --enable-external-lb --lb-algorithm=maglev
```

### When to Use Cilium L4LB

- You're running Kubernetes and want to replace kube-proxy
- You need integrated L4/L7 load balancing with service mesh capabilities
- You want built-in observability with Hubble
- You need both in-cluster and external load balancing

---

## XDP-Tools — Reference Implementation and Utilities

XDP-Tools is the official reference implementation and utility suite for XDP programs, maintained by the XDP project. While not a production load balancer like Katran or Cilium, it provides essential building blocks and example implementations.

### Architecture

XDP-Tools provides:
- **xdp-loader**: Load and manage XDP programs on network interfaces
- **xdp-dump**: Packet capture at the XDP layer (like tcpdump for XDP)
- **Example programs**: Reference implementations for load balancing, filtering, and forwarding
- **libxdp**: C library for building custom XDP applications

### Key Features

- **Reference implementations**: Learning and prototyping XDP programs
- **xdp-bench**: Benchmarking suite for XDP performance testing
- **AF_XDP support**: Zero-copy user-space packet processing
- **Multi-program support**: Chain multiple XDP programs on a single interface
- **Development toolkit**: Essential for building custom XDP solutions

### Docker Compose for Development

```yaml
services:
  xdp-tools-dev:
    image: ghcr.io/xdp-project/xdp-tools:latest
    network_mode: host
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
      - BPF
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
      - /lib/modules:/lib/modules:ro
      - ./xdp-programs:/opt/xdp-programs
    command: ["tail", "-f", "/dev/null"]
    restart: unless-stopped

  xdp-monitor:
    build:
      context: .
      dockerfile: Dockerfile.xdp-monitor
    network_mode: host
    cap_add:
      - NET_ADMIN
      - PERFMON
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
    command: ["xdp-monitor", "--stats"]
    restart: unless-stopped
```

### When to Use XDP-Tools

- You're building a custom XDP-based load balancer
- You need to benchmark XDP performance on your hardware
- You want to learn XDP programming with reference examples
- You need debugging and diagnostics tools for XDP programs

---

## Comparison Table

| Feature | Katran | Cilium L4LB | XDP-Tools |
|---------|--------|-------------|-----------|
| **Primary Use Case** | Production L4 LB | K8s kube-proxy replacement | XDP toolkit / reference |
| **Hashing Algorithm** | Maglev | Maglev | Configurable (examples) |
| **Encapsulation** | IPIP, GRE | VXLAN, Geneve, Direct | None (reference only) |
| **Health Checking** | Built-in | Via Kubernetes probes | Not included |
| **Kubernetes Integration** | No | Full (native) | No |
| **DSR Support** | Yes | Yes | Example only |
| **Observability** | Limited | Hubble (full) | xdp-dump, xdp-bench |
| **Production Readiness** | Battle-tested (Meta) | Production (CNCF) | Development/reference |
| **License** | GPL-2.0 | Apache-2.0 | GPL-2.0 / LGPL |
| **GitHub Stars** | 5,240+ | 24,398+ | 867+ |
| **Last Active** | May 2026 | May 2026 | May 2026 |

## Choosing the Right XDP Load Balancer

**Choose Katran if** you need a proven, large-scale L4 load balancer and have the infrastructure expertise to deploy it. Facebook's production deployment validates its design at massive scale.

**Choose Cilium L4LB if** you're running Kubernetes and want to replace kube-proxy with a faster, more feature-rich alternative. Cilium provides the most complete ecosystem with observability, security policies, and service mesh capabilities.

**Choose XDP-Tools if** you're building a custom solution and need a development toolkit, reference implementations, or benchmarking utilities. It's not a load balancer itself but provides the building blocks to create one.

## Why Self-Host XDP Load Balancing?

Traditional hardware load balancers (F5, Citrix ADC) cost thousands of dollars and require proprietary licenses. Software load balancers (HAProxy, Nginx) introduce user-space overhead that becomes significant at high packet rates. XDP-based load balancing sits between these options:

- **Commodity hardware**: Runs on standard Linux servers with supported NICs
- **Line-rate performance**: Processes packets at wire speed without user-space context switches
- **Programmable logic**: Custom load balancing algorithms via eBPF programs
- **No vendor lock-in**: Open-source implementations with active communities
- **Cloud-native ready**: Integrates with Kubernetes, service meshes, and GitOps workflows

For organizations handling millions of requests per second, XDP load balancers can reduce infrastructure costs by 60-80% compared to hardware appliances while delivering superior throughput.

### Security Considerations

When deploying XDP load balancers, consider these security best practices:

1. **eBPF verification**: All eBPF programs pass through the kernel verifier before loading, preventing unsafe programs from running
2. **Rate limiting**: Implement XDP-based rate limiting to protect backends from DDoS attacks
3. **Access control**: Restrict who can load and modify XDP programs on production interfaces
4. **Monitoring**: Use tools like Cilium Hubble or xdp-dump to monitor traffic patterns and detect anomalies
5. **Fallback paths**: Always have a generic XDP fallback mode for NICs that don't support native XDP

For related reading on eBPF networking tools, see our [XDP/eBPF network tools guide](../2026-05-13-self-hosted-xdp-ebpf-network-firewalls-xdp-tools-bpftool-cilium-ebpf-guide/) and [sidecarless service mesh comparison](../2026-05-21-self-hosted-sidecarless-service-mesh-istio-ambient-cilium-linkerd-guide/). For load balancing fundamentals, check our [Kubernetes CNI guide](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/).

## FAQ

### What is the difference between XDP and eBPF?

eBPF (extended Berkeley Packet Filter) is a technology that allows running sandboxed programs in the Linux kernel without changing kernel source code. XDP (eXpress Data Path) is a specific eBPF hook point that runs at the earliest stage of packet reception — directly from the NIC driver's receive ring buffer. Think of eBPF as the platform and XDP as one of the execution points.

### Do I need special hardware for XDP load balancing?

No special hardware is required, but performance depends on NIC driver support. Most modern Intel, Mellanox (NVIDIA), and Broadcom NICs support native XDP mode. NICs without native support fall back to generic XDP mode, which still works but with reduced throughput (approximately 1-2M PPS vs 10M+ PPS for native mode).

### Can I run XDP load balancers alongside iptables/nftables?

Yes, but with caveats. XDP runs before iptables in the packet processing pipeline. This means XDP can redirect or drop packets before iptables rules see them. If you need both, ensure your XDP program forwards packets correctly to the kernel stack so iptables can process them. Cilium handles this automatically when running in kube-proxy replacement mode.

### Is Katran production-ready for non-Facebook environments?

Katran has been used in production at Meta (Facebook) for years, handling massive traffic volumes. However, it's primarily designed for Meta's specific infrastructure requirements (ECMP routing, specific encapsulation). Organizations looking to deploy it should be prepared for operational complexity and limited community support compared to Cilium.

### How does Maglev hashing work?

Maglev is a consistent hashing algorithm designed for load balancing. It creates a lookup table where each backend server appears an equal number of times. When a packet arrives, its flow identifier (source IP + port + destination IP + port + protocol) is hashed to select an entry from the table. The key benefit is that adding or removing a backend only affects a small fraction of flows — approximately 1/N of traffic when N backends exist.

### What is DSR (Direct Server Return) and why does it matter?

DSR is a load balancing mode where the return traffic goes directly from the backend server to the client, bypassing the load balancer. This halves the load balancer's bandwidth requirements and reduces latency. Both Katran and Cilium support DSR. The trade-off is that backend servers must be configured to accept traffic destined for the VIP address, which requires additional network configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted eBPF XDP Load Balancers: Katran vs Cilium L4LB vs XDP-Tools",
  "description": "Compare three open-source eBPF XDP load balancers: Facebook's Katran, Cilium L4LB, and XDP-Tools reference implementation. Covers architecture, deployment, and performance.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
