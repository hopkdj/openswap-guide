---
title: "Self-Hosted Container CNI Plugins: Linux Bridge vs IPvLAN vs Macvlan Deep Dive"
date: "2026-05-12"
tags: ["cni", "container-networking", "kubernetes", "docker", "ipvlan", "macvlan", "bridge"]
draft: false
---

Container networking is the foundation of any self-hosted infrastructure. The Container Network Interface (CNI) defines a standard for connecting containers to networks, and the choice of CNI plugin determines how your containers communicate with each other, the host, and external networks.

This guide dives deep into three fundamental CNI plugin types — **Linux Bridge**, **IPvLAN**, and **Macvlan** — comparing their architecture, performance, isolation properties, and ideal use cases for self-hosted container deployments.

## Understanding CNI Plugin Types

| Feature | Linux Bridge | IPvLAN | Macvlan |
|---------|-------------|--------|---------|
| **Kernel Module** | bridge | ipvlan | macvlan |
| **Layer** | L2 (Ethernet) | L3 (IP) / L2 | L2 (Ethernet) |
| **MAC Addresses** | 1 per container (veth pair) | Shared (host MAC) | 1 per container |
| **Performance** | Good (software bridge) | Excellent (no bridge) | Excellent (no bridge) |
| **IPAM Support** | ✅ host-local, DHCP | ✅ host-local, DHCP | ✅ host-local, DHCP |
| **Network Policy** | ✅ Full support | ✅ L3 mode only | ❌ Limited |
| **Hairpin Mode** | Required for host access | Not needed | Required for host access |
| **VLAN Support** | Via vlan plugin | Native (mode l2/l3) | Native (mode bridge) |
| **Best For** | General container networking | High-performance, L3 isolation | Legacy app compatibility, direct L2 |

### Linux Bridge CNI

The Linux Bridge plugin creates a virtual Ethernet bridge on the host and connects each container via a veth (virtual Ethernet) pair. One end of the veth pair lives inside the container's network namespace, and the other end attaches to the bridge. This is the most common and widely supported CNI plugin, forming the foundation for more complex networking setups.

### IPvLAN CNI

IPvLAN creates virtual network interfaces that share the host's MAC address but have unique IP addresses. Unlike Bridge mode, IPvLAN operates at Layer 3 (IP level), meaning the kernel routes packets directly without a software bridge. This eliminates bridge overhead and provides near-native network performance. IPvLAN has three modes: L2 (same subnet), L3 (routed), and L3S (L3 with source NAT).

### Macvlan CNI

Macvlan creates virtual interfaces that each have their own unique MAC address, making containers appear as separate physical devices on the network. This is useful for legacy applications that expect direct network access or for environments where containers need to be individually addressable by external firewalls, load balancers, or monitoring systems.

## Deploying Linux Bridge CNI

The Linux Bridge plugin is part of the standard CNI plugins package:

```bash
# Install CNI plugins
curl -LO https://github.com/containernetworking/plugins/releases/download/v1.5.0/cni-plugins-linux-amd64-v1.5.0.tgz
sudo mkdir -p /opt/cni/bin
sudo tar -C /opt/cni/bin -xzf cni-plugins-linux-amd64-v1.5.0.tgz bridge host-local loopback
```

Bridge CNI configuration (`/etc/cni/net.d/10-bridge.conf`):

```json
{
  "cniVersion": "1.0.0",
  "name": "bridge-network",
  "type": "bridge",
  "bridge": "cni0",
  "isGateway": true,
  "ipMasq": true,
  "ipam": {
    "type": "host-local",
    "subnet": "10.244.0.0/24",
    "routes": [
      {"dst": "0.0.0.0/0"}
    ]
  }
}
```

Docker Compose with custom bridge network:

```yaml
version: '3.8'
services:
  app:
    image: nginx:latest
    networks:
      - bridge-net

  db:
    image: postgres:16
    networks:
      - bridge-net

networks:
  bridge-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.244.0.0/24
          gateway: 10.244.0.1
```

## Deploying IPvLAN CNI

IPvLAN configuration (`/etc/cni/net.d/10-ipvlan.conf`):

```json
{
  "cniVersion": "1.0.0",
  "name": "ipvlan-network",
  "type": "ipvlan",
  "master": "eth0",
  "mode": "l2",
  "ipam": {
    "type": "host-local",
    "subnet": "192.168.1.0/24",
    "rangeStart": "192.168.1.100",
    "rangeEnd": "192.168.1.200",
    "gateway": "192.168.1.1"
  }
}
```

Test IPvLAN with a temporary container:

```bash
# Create a container with IPvLAN networking
docker run -d --name ipvlan-test   --net=none   nginx:latest

# Attach IPvLAN interface manually
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' ipvlan-test)
sudo ln -sf /proc/$CONTAINER_PID/ns/net /var/run/netns/$CONTAINER_PID

# Create IPvLAN interface
sudo ip link add link eth0 name ipvl0 type ipvlan mode l2
sudo ip link set ipvl0 netns $CONTAINER_PID
sudo ip netns exec $CONTAINER_PID ip addr add 192.168.1.100/24 dev ipvl0
sudo ip netns exec $CONTAINER_PID ip link set ipvl0 up
sudo ip netns exec $CONTAINER_PID ip route add default via 192.168.1.1
```

Docker native IPvLAN network:

```bash
# Create an IPvLAN network in Docker
docker network create -d ipvlan   --subnet=192.168.1.0/24   --gateway=192.168.1.1   -o parent=eth0   --ip-range=192.168.1.100/28   ipvlan-net

# Run a container on the IPvLAN network
docker run -d --name app --net=ipvlan-net nginx:latest
```

## Deploying Macvlan CNI

Macvlan configuration (`/etc/cni/net.d/10-macvlan.conf`):

```json
{
  "cniVersion": "1.0.0",
  "name": "macvlan-network",
  "type": "macvlan",
  "master": "eth0",
  "mode": "bridge",
  "ipam": {
    "type": "host-local",
    "subnet": "192.168.1.0/24",
    "rangeStart": "192.168.1.50",
    "rangeEnd": "192.168.1.150",
    "gateway": "192.168.1.1"
  }
}
```

Docker native Macvlan network:

```bash
# Create a Macvlan network
docker network create -d macvlan   --subnet=192.168.1.0/24   --gateway=192.168.1.1   -o parent=eth0   --ip-range=192.168.1.50/28   macvlan-net

# Run containers on the Macvlan network
docker run -d --name web1 --net=macvlan-net nginx:latest
docker run -d --name web2 --net=macvlan-net nginx:latest

# Each container gets a unique MAC address visible on the network
docker exec web1 ip link show
docker exec web2 ip link show
```

Macvlan with VLAN tagging:

```bash
# Create a Macvlan network on a VLAN sub-interface
docker network create -d macvlan   --subnet=10.10.0.0/24   --gateway=10.10.0.1   -o parent=eth0.100   macvlan-vlan100
```

## Performance Comparison

### Throughput and Latency

| Metric | Linux Bridge | IPvLAN (L2) | IPvLAN (L3) | Macvlan |
|--------|-------------|-------------|-------------|---------|
| **TCP Throughput** | ~90% native | ~98% native | ~97% native | ~98% native |
| **UDP Latency** | ~50μs overhead | ~5μs overhead | ~8μs overhead | ~5μs overhead |
| **CPU Overhead** | Moderate (bridge processing) | Minimal | Minimal | Minimal |
| **Context Switches** | Higher (bridge traversal) | Lower (direct route) | Lower (direct route) | Lower (direct route) |
| **Scalability** | Good (1000s of containers) | Excellent | Excellent | Limited (MAC table) |

### Network Isolation

**Linux Bridge** provides L2 isolation — containers on the same bridge can communicate directly. Network policies are enforced via iptables/nftables rules on the bridge interface.

**IPvLAN L3 mode** provides the strongest isolation — containers can only communicate through the host's routing stack. This is ideal for multi-tenant environments where containers must not reach each other directly.

**Macvlan** provides minimal isolation — all containers appear as regular network devices. External firewalls and switches see each container's MAC address independently, which can be both a feature and a security concern.

## Troubleshooting Common Issues

### Bridge: Hairpin Mode

When containers need to reach themselves through the host IP, enable hairpin mode:

```bash
# Enable hairpin mode on the bridge port
sudo brctl hairpin cni0 veth12345 on
# Or with iproute2
sudo ip link set dev veth12345 hairpin on
```

### IPvLAN: Host Communication

Containers on an IPvLAN network cannot reach the host by default. Fix this by creating a macvlan interface on the host:

```bash
# Create a macvlan interface on the host for host-to-container communication
sudo ip link add ipvlan-host link eth0 type macvlan mode bridge
sudo ip addr add 192.168.1.1/32 dev ipvlan-host
sudo ip link set ipvlan-host up
sudo ip route add 192.168.1.100/32 dev ipvlan-host
```

### Macvlan: Host Communication

Same issue as IPvLAN — Macvlan containers cannot reach the host directly:

```bash
# Create a macvlan interface on the host
sudo ip link add macvlan-host link eth0 type macvlan mode bridge
sudo ip addr add 192.168.1.1/32 dev macvlan-host
sudo ip link set macvlan-host up
```

## Choosing the Right CNI Plugin

### Choose Linux Bridge if:
- You need general-purpose container networking with broad compatibility
- You want Kubernetes NetworkPolicy support
- You're running Docker or Kubernetes without specialized networking requirements
- You need NAT for containers to reach external networks

### Choose IPvLAN if:
- You need maximum network performance (minimal overhead)
- You want L3 isolation between container groups (multi-tenant)
- You don't want MAC address proliferation on your network switches
- Your network infrastructure limits the number of MAC addresses per port

### Choose Macvlan if:
- Your containers need to appear as individual devices on the physical network
- You have legacy applications that require direct network access
- External firewalls or monitoring systems need to see individual container MAC addresses
- You're migrating VMs to containers and need the same network behavior

## Why Care About CNI Plugin Choice?

**Performance matters at scale**: For small deployments with a few containers, any CNI plugin works fine. But at hundreds or thousands of containers, the difference between Bridge and IPvLAN becomes measurable — IPvLAN's near-native throughput can reduce network latency by 90% compared to bridge-based networking.

**Security and isolation**: Different plugins offer different isolation guarantees. IPvLAN L3 mode provides strong tenant isolation by default, while Macvlan exposes all containers directly to the physical network. Understanding these differences is critical for compliance and security.

**Network infrastructure compatibility**: Some network switches limit the number of MAC addresses per port (port security). Macvlan creates one MAC per container, which can exhaust switch MAC tables. IPvLAN shares the host MAC, avoiding this limitation entirely.

**Operational complexity**: Linux Bridge is the simplest to understand and troubleshoot — it behaves like a physical Ethernet switch. IPvLAN and Macvlan operate at a lower level and require understanding of kernel networking internals for advanced troubleshooting.

For teams managing container networks at scale, see our [Kubernetes CNI comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) and [sidecar proxy guide](../2026-05-12-self-hosted-sidecar-proxy-envoy-linkerd-cilium-guide/). If you need advanced network policies, our [Kubernetes network policies deep dive](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies-guide-2026/) covers policy enforcement patterns.

## FAQ

### Can I use multiple CNI plugins on the same host?

Yes. CNI supports chaining multiple plugins together. For example, you can use the Bridge plugin for basic connectivity and chain it with the Portmap plugin for port forwarding, or with the Bandwidth plugin for rate limiting. The CNI specification defines how plugins are chained in a single network configuration file.

### What is the difference between IPvLAN L2 and L3 modes?

**IPvLAN L2 mode** allows containers to communicate at Layer 2 — they can see each other's ARP traffic and communicate directly within the same subnet. **IPvLAN L3 mode** routes all traffic through the host's IP stack, providing stronger isolation — containers cannot see each other's Layer 2 traffic and must go through routing for all communication.

### Does Macvlan work with WiFi interfaces?

Generally no. Most WiFi drivers and access points do not support multiple MAC addresses on a single interface (802.11 standard limitation). Macvlan requires the underlying interface to support multiple MAC addresses, which is true for Ethernet but not for most WiFi adapters.

### How do I monitor CNI plugin performance?

Use standard Linux networking tools: `ip -s link` shows byte/packet counts per interface, `tc -s qdisc` shows queueing discipline statistics, and `ethtool -S` shows driver-level statistics. For Kubernetes deployments, Cilium Hubble and Weave Scope provide network observability on top of CNI plugins.

### Can containers on different CNI networks communicate?

Not by default. Containers on separate CNI networks are isolated from each other. To enable cross-network communication, you need a router or gateway between the networks. In Kubernetes, this is handled by the kube-proxy and Service abstraction.

### What happens to existing connections when I change CNI plugins?

Changing CNI plugins requires restarting containers — the network namespace is recreated with the new plugin. Existing TCP connections will be dropped. Plan CNI changes during maintenance windows and use rolling updates to minimize disruption.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container CNI Plugins: Linux Bridge vs IPvLAN vs Macvlan Deep Dive",
  "description": "Deep dive comparison of Linux Bridge, IPvLAN, and Macvlan CNI plugins for container networking — architecture, performance, and deployment guides.",
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
