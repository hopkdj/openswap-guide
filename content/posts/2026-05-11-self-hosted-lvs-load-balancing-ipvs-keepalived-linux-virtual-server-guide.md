---
title: "Self-Hosted LVS Load Balancing: IPVS, Keepalived, and Linux Virtual Server (2026)"
date: "2026-05-11"
tags: ["load-balancing", "lvs", "ipvs", "keepalived", "linux", "high-availability", "networking"]
draft: false
---

When your application outgrows a single server, load balancing becomes the critical infrastructure layer that distributes traffic across multiple backend nodes. While solutions like HAProxy, NGINX, and Envoy dominate the Layer 7 (application layer) conversation, the Linux kernel includes a powerful Layer 4 (transport layer) load balancer that handles billions of packets per second with near-zero overhead: **Linux Virtual Server (LVS)**.

This guide covers the LVS ecosystem — **IPVS** (IP Virtual Server, the kernel module), **Keepalived** (LVS health checking and VRRP failover), and the broader **Linux Virtual Server** architecture. Whether you're building a high-traffic web platform, a real-time service, or a Kubernetes data plane (kube-proxy uses IPVS), understanding LVS is essential for infrastructure engineers.

## What Is Linux Virtual Server (LVS)?

Linux Virtual Server is a kernel-level load balancer built into the Linux kernel since version 2.4. It operates at Layer 4 (TCP/UDP), making forwarding decisions based on IP addresses and port numbers — not HTTP headers or cookies. This makes LVS significantly faster than application-layer load balancers for raw packet throughput, with the trade-off of limited traffic inspection capability.

LVS operates through the **IP Virtual Server (IPVS)** kernel module, which creates a virtual IP address (VIP) that clients connect to. IPVS then forwards packets to one of several real backend servers using configurable scheduling algorithms. The three primary forwarding modes are:

- **NAT (Network Address Translation)**: LVS rewrites both destination and source IP addresses. Simple to set up but becomes a bottleneck at scale since all return traffic must pass through the LVS node.
- **Direct Routing (DR)**: LVS rewrites only the destination MAC address, and backend servers respond directly to clients. Highest performance mode — the LVS node only handles incoming traffic. Requires backend servers to be on the same Layer 2 network or have proper ARP configuration.
- **Tunneling (TUN)**: LVS encapsulates packets in IP-in-IP tunnels to backend servers in different subnets or geographic locations. Useful for geo-distributed deployments but adds encapsulation overhead.

## IPVS: The Kernel Load Balancer

IPVS (IP Virtual Server) is the actual load balancing engine within the Linux kernel. It's managed via the `ipvsadm` userspace utility, which configures virtual services and real servers.

**Key features:**
- 10+ scheduling algorithms: Round Robin, Weighted Round Robin, Least Connections, Weighted Least Connections, Locality-Based Least Connections, Destination Hashing, Source Hashing, Shortest Expected Delay, Never Queue, and more
- Connection tracking and persistence (sticky sessions via client IP hashing)
- Support for TCP, UDP, SCTP, and GRE protocols
- Integration with netfilter/iptables for firewall rules
- Built into the Linux kernel — no additional software to install

**Architecture:** IPVS hooks into the kernel's network stack at the IP layer. When a packet arrives at the VIP, IPVS consults its routing table, applies the configured scheduling algorithm, and either NATs the packet, rewrites the MAC (DR mode), or encapsulates it (TUN mode) before forwarding to the selected real server.

**Performance:** IPVS can handle millions of connections per second with sub-millisecond latency. In production benchmarks, a single LVS node in DR mode has been observed handling 40 Gbps of traffic with minimal CPU utilization. The kernel-level implementation means no context switching or userspace copying — packets are forwarded directly in kernel space.

## Keepalived: Health Checking and VRRP Failover

Keepalived is the companion tool that makes LVS production-ready. While IPVS handles packet forwarding, Keepalived provides:

**Health checking:** Keepalived continuously monitors backend servers using TCP, HTTP, SSL, or custom scripts. Failed servers are automatically removed from the IPVS table, and recovered servers are re-added — all without disrupting active connections.

**VRRP (Virtual Router Redundancy Protocol):** Keepalived implements VRRP to provide LVS node high availability. Two or more Keepalived instances elect a master; if the master fails, a backup takes over the VIP within seconds. This eliminates the LVS node as a single point of failure.

**IPVS management:** Keepalived can dynamically configure IPVS rules from its configuration file, eliminating the need to manually run `ipvsadm` commands. When a backend server's health status changes, Keepalived updates the IPVS table automatically.

**Architecture:** A typical production LVS setup uses two Keepalived instances (master + backup) on separate machines. Both monitor the same pool of backend servers. The master owns the VIP and handles traffic; the backup monitors the master via VRRP and takes over if the master becomes unreachable.

## Comparison: IPVS vs Keepalived vs LVS Architecture

| Aspect | IPVS (Kernel Module) | Keepalived (Userspace) | Combined LVS + Keepalived |
|--------|---------------------|----------------------|--------------------------|
| **Layer** | Layer 4 (TCP/UDP) | Layer 4 + health checks | Layer 4 + HA |
| **Scheduling** | 10+ algorithms | Uses IPVS scheduling | Full scheduling + health |
| **Health Checks** | None (manual) | TCP, HTTP, SSL, scripts | Automated health management |
| **Failover** | None | VRRP-based VIP failover | Active-passive LVS HA |
| **Configuration** | ipvsadm CLI | keepalived.conf | Declarative keepalived.conf |
| **Performance** | Millions of conn/sec | Negligible overhead | Near-native IPVS performance |
| **Single Point of Failure** | Yes (single node) | No (VRRP redundancy) | No (active-passive) |
| **Complexity** | Low (kernel module) | Moderate (config file) | Moderate (2-node setup) |
| **Kubernetes Integration** | kube-proxy IPVS mode | Not directly | Via kube-proxy |
| **Best For** | Packet forwarding | LVS management + HA | Production load balancing |

## Docker Compose Deployments

### Keepalived + IPVS Load Balancer

```yaml
version: "3.8"
services:
  keepalived-master:
    image: osixia/keepalived:latest
    container_name: lvs-master
    cap_add:
      - NET_ADMIN
      - NET_BROADCAST
      - NET_RAW
    environment:
      KEEPALIVED_INTERFACE: eth0
      KEEPALIVED_VIRTUAL_IPS: "#PYTHON2BASH:['192.168.1.100']"
      KEEPALIVED_PRIORITY: 150
      KEEPALIVED_STATE: MASTER
    volumes:
      - ./keepalived-master.conf:/container/service/keepalived/assets/keepalived.conf
    network_mode: host

  keepalived-backup:
    image: osixia/keepalived:latest
    container_name: lvs-backup
    cap_add:
      - NET_ADMIN
      - NET_BROADCAST
      - NET_RAW
    environment:
      KEEPALIVED_INTERFACE: eth0
      KEEPALIVED_VIRTUAL_IPS: "#PYTHON2BASH:['192.168.1.100']"
      KEEPALIVED_PRIORITY: 100
      KEEPALIVED_STATE: BACKUP
    volumes:
      - ./keepalived-backup.conf:/container/service/keepalived/assets/keepalived.conf
    network_mode: host
```

The Keepalived configuration for the master node defines the virtual IP, VRRP priority, and IPVS rules:

```conf
! /etc/keepalived/keepalived.conf - Master Node
global_defs {
    router_id LVS_MASTER
}

vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 150
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass keepalived_secret
    }
    virtual_ipaddress {
        192.168.1.100/24 dev eth0
    }
}

virtual_server 192.168.1.100 80 {
    delay_loop 6
    lb_algo wlc
    lb_kind DR
    protocol TCP

    real_server 192.168.1.10 80 {
        weight 100
        TCP_CHECK {
            connect_timeout 3
            nb_get_retry 3
            delay_before_retry 3
        }
    }

    real_server 192.168.1.11 80 {
        weight 100
        TCP_CHECK {
            connect_timeout 3
            nb_get_retry 3
            delay_before_retry 3
        }
    }

    real_server 192.168.1.12 80 {
        weight 50
        TCP_CHECK {
            connect_timeout 3
            nb_get_retry 3
            delay_before_retry 3
        }
    }
}
```

### Backend Server Configuration (DR Mode)

For Direct Routing mode, each backend server needs to suppress ARP responses for the VIP:

```bash
#!/bin/bash
# Run on each backend server
VIP=192.168.1.100
ip addr add ${VIP}/32 dev lo
sysctl -w net.ipv4.conf.all.arp_ignore=1
sysctl -w net.ipv4.conf.lo.arp_ignore=1
sysctl -w net.ipv4.conf.all.arp_announce=2
sysctl -w net.ipv4.conf.lo.arp_announce=2
```

You can also containerize the backend ARP configuration:

```yaml
version: "3.8"
services:
  web1:
    image: nginx:alpine
    container_name: backend-web-1
    ports:
      - "80:80"
    networks:
      backend-net:
        ipv4_address: 192.168.1.10
    cap_add:
      - NET_ADMIN
    command: >
      sh -c "
        ip addr add 192.168.1.100/32 dev lo &&
        sysctl -w net.ipv4.conf.all.arp_ignore=1 &&
        sysctl -w net.ipv4.conf.lo.arp_ignore=1 &&
        sysctl -w net.ipv4.conf.all.arp_announce=2 &&
        sysctl -w net.ipv4.conf.lo.arp_announce=2 &&
        nginx -g 'daemon off;'
      "

networks:
  backend-net:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.1.0/24
```

## Choosing the Right LVS Deployment Mode

**Use NAT mode** when your backend servers are on a private network and you need the LVS node to handle both incoming and outgoing traffic. This is the simplest to configure but limits throughput since all traffic flows through the LVS node. Ideal for small deployments (under 10 Gbps) where simplicity outweighs performance.

**Use Direct Routing (DR) mode** when you need maximum throughput and your backend servers are on the same Layer 2 network (or you can configure proper ARP handling). DR mode is the most commonly used LVS mode in production — it scales to 40+ Gbps on a single node because the LVS only handles incoming packets. The main operational complexity is ARP suppression on backend servers.

**Use Tunneling (TUN) mode** when your backend servers are in different subnets or geographic locations. TUN mode encapsulates packets in IP-in-IP tunnels, allowing LVS to distribute traffic across data centers. The encapsulation overhead (20 bytes per packet) reduces maximum throughput by ~10-15% compared to DR mode.

## Why Self-Host Your LVS Load Balancing Infrastructure?

LVS is built into the Linux kernel — it costs nothing to run and requires no additional licensing. Compared to commercial load balancers (F5 BIG-IP, Citrix ADC, HAProxy Enterprise), LVS offers comparable Layer 4 performance at a fraction of the cost. The trade-off is operational complexity: you manage health checking, failover, and configuration yourself.

Self-hosted LVS gives you complete control over scheduling algorithms, persistence rules, and health check intervals. You can fine-tune the weighted least connections algorithm to match your backend server capacities, or implement custom health checks that validate your application's specific readiness criteria.

For organizations concerned about supply chain risk, LVS is part of the mainline Linux kernel — audited by thousands of developers and maintained by the kernel community. There's no vendor lock-in, no proprietary firmware, and no risk of the project being discontinued or acquired.

For HA clustering and VRRP-based failover, see our [Keepalived vs Corosync/Pacemaker comparison](../2026-04-21-keepalived-vs-corosync-pacemaker-self-hosted-ha-clustering-guide/). For BGP-based anycast routing as an alternative load balancing approach, check our [DNS anycast guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide/). And for Kubernetes-native load balancing with IPVS, our [Kubernetes CNI guide](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide/) covers kube-proxy's IPVS mode.

## Frequently Asked Questions

### What is the difference between LVS, IPVS, and Keepalived?

LVS (Linux Virtual Server) is the overall architecture for kernel-level load balancing. IPVS (IP Virtual Server) is the actual kernel module that implements packet forwarding and scheduling. Keepalived is a userspace tool that provides health checking, VRRP-based failover, and dynamic IPVS configuration management. In practice, LVS + Keepalived are deployed together as a production-ready load balancing solution.

### Which LVS forwarding mode should I use?

Direct Routing (DR) mode is the best choice for most production deployments — it offers the highest throughput because the LVS node only handles incoming traffic and backends respond directly to clients. Use NAT mode for simple setups where all servers are on a private network. Use Tunneling (TUN) mode for geo-distributed deployments where backends are in different subnets.

### Can LVS do Layer 7 load balancing?

No. LVS operates at Layer 4 (TCP/UDP) and makes forwarding decisions based on IP addresses and port numbers only. It cannot inspect HTTP headers, cookies, or URL paths. For Layer 7 load balancing, use HAProxy, NGINX, or Envoy. A common architecture uses LVS at Layer 4 to distribute traffic to a pool of HAProxy/NGINX instances that handle Layer 7 routing.

### How does Kubernetes use IPVS?

Kubernetes kube-proxy can operate in IPVS mode (instead of the default iptables mode). In IPVS mode, kube-proxy uses the Linux Virtual Server kernel module to implement service load balancing. This provides better performance and scalability than iptables mode, especially for clusters with thousands of services. Enable it by setting `mode: ipvs` in the kube-proxy ConfigMap.

### How do I monitor LVS performance?

Use `ipvsadm -L --stats` to view connection statistics (total connections, packets in/out, bytes in/out). Use `ipvsadm -L --rate` for real-time rates. For production monitoring, integrate with Prometheus using the `node_exporter` (which exposes IPVS metrics) or use `keepalived`'s built-in SNMP support. Keepalived also logs health check failures and failover events to syslog.

### What happens when all backend servers fail in Keepalived?

By default, Keepalived removes all failed servers from the IPVS table, and the virtual server stops accepting connections. You can configure a fallback server (sorry server) that serves a maintenance page when all real servers are down. Add `sorry_server 192.168.1.200 80` inside the `virtual_server` block to redirect traffic to a maintenance server during outages.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LVS Load Balancing: IPVS, Keepalived, and Linux Virtual Server",
  "description": "Complete guide to Linux Virtual Server (LVS) load balancing with IPVS and Keepalived. Covers NAT, DR, and TUN modes with Docker Compose deployment examples.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
