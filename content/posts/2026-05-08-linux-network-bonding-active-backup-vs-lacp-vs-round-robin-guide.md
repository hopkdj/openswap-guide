---
title: "Linux Network Bonding: Active-Backup vs LACP vs Round-Robin (2026)"
date: "2026-05-08"
tags: ["linux", "networking", "bonding", "lacp", "high-availability", "teamd", "ifenslave", "infrastructure", "sysadmin"]
draft: false
---

Network bonding (also called link aggregation or NIC teaming) combines multiple physical network interfaces into a single logical interface. This provides two key benefits: **fault tolerance** — if one NIC or cable fails, traffic continues on the remaining links — and **increased throughput** — traffic can be distributed across multiple physical links simultaneously.

Linux offers several approaches to network bonding: the kernel's built-in **bonding driver** (managed via `ifenslave` or `iproute2`), the userspace **teamd** daemon, and **NetworkManager's** native bonding support. In this guide, we compare these approaches and explain which bonding mode suits your workload.

## Comparison Table

| Feature | Bonding Driver (ifenslave) | teamd | NetworkManager |
|---------|---------------------------|-------|----------------|
| **Layer** | Kernel module | Userspace daemon | Userspace + kernel |
| **Management Tool** | `ip link`, `ifenslave` | `teamdctl` | `nmcli` |
| **Active-Backup** | Yes | Yes | Yes |
| **LACP (802.3ad)** | Yes | Yes | Yes |
| **Round-Robin (balance-rr)** | Yes | No | Via bonding driver |
| **XOR (balance-xor)** | Yes | Yes | Yes |
| **Broadcast (broadcast)** | Yes | No | Via bonding driver |
| **ALB (adaptive load balancing)** | Yes | No | Via bonding driver |
| **TLB (adaptive transmit load)** | Yes | Yes | Via bonding driver |
| **Configuration** | sysfs / modprobe | JSON config | nmcli / keyfile |
| **Hot-plug Support** | Yes | Yes | Yes |
| **VLAN on Bond** | Yes | Yes | Yes |
| **Bridge on Bond** | Yes | Yes | Yes |
| **Systemd Integration** | Via networkd | Via systemd | Native |
| **Project Maturity** | Since 2.4.0 (2001) | Since 2013 | Since 2014 |

## Bonding Modes Explained

Before diving into implementation, it's essential to understand the seven bonding modes available in the Linux kernel:

1. **balance-rr (mode 0)** — Round-robin across all slaves. Provides load balancing and fault tolerance. Transmits packets in sequential order from the first available slave through the last.

2. **active-backup (mode 1)** — Only one slave is active at a time. A different slave becomes active only if the active slave fails. This is the simplest mode and requires no switch configuration.

3. **balance-xor (mode 2)** — XOR-based load balancing. Transmits based on `(source MAC XOR destination MAC) % slave count`. This ensures the same destination always uses the same slave.

4. **broadcast (mode 3)** — Transmits on all slave interfaces. Provides fault tolerance but wastes bandwidth. Used only for specialized applications.

5. **802.3ad (mode 4 / LACP)** — IEEE 802.3ad Dynamic Link Aggregation. Creates aggregation groups that share the same speed and duplex settings. **Requires switch support for LACP**. This is the most common mode for production environments.

6. **balance-tlb (mode 5)** — Adaptive transmit load balancing. Outgoing traffic is distributed based on current load on each slave. Incoming traffic is received by the current slave. Does not require switch configuration.

7. **balance-alb (mode 6)** — Adaptive load balancing. Includes TLB plus receive load balancing for IPv4 traffic via ARP negotiation. Does not require switch configuration.

## Kernel Bonding Driver (ifenslave / iproute2)

The Linux bonding driver is a kernel module (`bonding.ko`) that creates a virtual network interface (`bond0`) backed by multiple physical NICs. It has been part of the Linux kernel since version 2.4.0 and is the most mature and widely-used bonding implementation.

### Configuration via modprobe

```bash
# /etc/modprobe.d/bonding.conf
alias bond0 bonding
options bond0 mode=802.3ad miimon=100 lacp_rate=fast xmit_hash_policy=layer2+3
```

### Configuration via iproute2

```bash
# Create the bond interface
ip link add bond0 type bond mode 802.3ad miimon 100 lacp_rate fast xmit_hash_policy layer2+3

# Add slave interfaces
ip link set eth0 master bond0
ip link set eth1 master bond0

# Bring up the bond and slaves
ip link set eth0 up
ip link set eth1 up
ip link set bond0 up

# Assign IP address
ip addr add 192.168.1.10/24 dev bond0

# Verify bond status
cat /proc/net/bonding/bond0
```

### Persistent Configuration (netplan)

```yaml
# /etc/netplan/01-bond.yaml
network:
  version: 2
  bonds:
    bond0:
      interfaces:
        - eth0
        - eth1
      parameters:
        mode: 802.3ad
        mii-monitor-interval: 100
        lacp-rate: fast
        transmit-hash-policy: layer2+3
      addresses:
        - 192.168.1.10/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

### Docker Compose (Container Network on Bond)

While bonding is a host-level configuration, you can ensure containers use the bonded interface:

```yaml
version: "3.8"
services:
  network-tester:
    image: nicolaka/netshoot
    network_mode: host
    command: ["sh", "-c", "ip link show bond0 && ping -c 3 8.8.8.8"]
  monitoring:
    image: prom/node-exporter:latest
    network_mode: host
    ports:
      - "9100:9100"
```

## teamd (Network Teaming)

teamd is a userspace daemon that implements network teaming using the kernel's team driver (`team.ko`). It was introduced as a modern alternative to the bonding driver, with a focus on extensibility and cleaner configuration.

### Architecture

Unlike the bonding driver which is entirely in the kernel, teamd uses a small kernel module (`team.ko`) for fast datapath operations and a userspace daemon (`teamd`) for control plane logic. The daemon reads a JSON configuration file that defines the runner (equivalent to bonding mode) and port settings.

### Configuration

```json
{
    "device": "team0",
    "runner": {
        "name": "lacp",
        "active": true,
        "fast_rate": true,
        "tx_hash": ["eth", "ipv4", "ipv6"]
    },
    "link_watch": {
        "name": "ethtool"
    }
}
```

### Setup Commands

```bash
# Install teamd
sudo apt install teamd

# Create team interface
teamd -d -n -c '{"device":"team0","runner":{"name":"activebackup"}}'

# Add slave interfaces
ip link set eth0 down
ip link set eth1 down
ip link set eth0 master team0
ip link set eth1 master team0
ip link set team0 up

# Monitor team status
teamdctl team0 state
teamdctl team0 port config dump
```

### Persistent Configuration (systemd-networkd)

```ini
# /etc/systemd/network/10-team0.netdev
[NetDev]
Name=team0
Kind=team

[Team]
Config={"runner": {"name": "lacp", "active": true, "fast_rate": true}}
```

```ini
# /etc/systemd/network/11-team0-slave1.network
[Match]
Name=eth0

[Network]
Team=team0
```

```ini
# /etc/systemd/network/12-team0-slave2.network
[Match]
Name=eth1

[Network]
Team=team0
```

## NetworkManager Bonding

NetworkManager provides a unified interface for configuring bonding, teaming, bridges, and VLANs. It supports all kernel bonding modes and integrates with both CLI (`nmcli`) and GUI tools.

### Configuration via nmcli

```bash
# Create bond interface with LACP
nmcli connection add type bond \
  ifname bond0 \
  mode 802.3ad \
  miimon 100 \
  lacp-rate fast \
  xmit_hash_policy layer2+3 \
  con-name bond0

# Add slave interfaces
nmcli connection add type ethernet \
  slave-type bond \
  master bond0 \
  con-name bond0-port1 \
  ifname eth0

nmcli connection add type ethernet \
  slave-type bond \
  master bond0 \
  con-name bond0-port2 \
  ifname eth1

# Set IP address
nmcli connection modify bond0 \
  ipv4.addresses 192.168.1.10/24 \
  ipv4.gateway 192.168.1.1 \
  ipv4.dns "8.8.8.8 8.8.4.4" \
  ipv4.method manual

# Activate
nmcli connection up bond0
```

### Verification

```bash
# Show bond details
nmcli device show bond0

# Show bond connection
nmcli connection show bond0

# Check kernel bond status
cat /proc/net/bonding/bond0
```

## Choosing the Right Bonding Approach

| Criteria | Bonding Driver | teamd | NetworkManager |
|----------|---------------|-------|----------------|
| **Simplicity** | Moderate | Complex | Simple |
| **Maturity** | Best | Good | Good |
| **All bonding modes** | Yes | Subset | Yes (via bonding) |
| **LACP support** | Yes | Yes | Yes |
| **Hot-plug** | Yes | Yes | Yes |
| **Best for** | Production servers | Advanced users | Desktop/workstation |
| **Configuration persistence** | netplan/modprobe | JSON + systemd | nmcli profiles |

For **production servers**, the kernel bonding driver via netplan is the most reliable and well-tested approach. It supports all seven bonding modes and has been battle-tested for over two decades.

For **environments with systemd-networkd**, teamd integrates cleanly and offers a more modular architecture. However, it doesn't support all bonding modes (notably balance-rr and broadcast).

For **desktop systems and workstations**, NetworkManager provides the easiest configuration experience with `nmcli` commands and automatic connection profiles.

## Why Configure Network Bonding on Your Servers?

Network bonding is one of the simplest yet most impactful infrastructure improvements you can make. For any self-hosted service that handles network traffic — databases, web servers, file shares, or container registries — bonding eliminates single points of failure at the network interface level.

In **active-backup mode**, a NIC or cable failure is transparent to your services. The kernel automatically fails over to the backup interface within milliseconds. No connection drops, no service restarts, no manual intervention required.

In **LACP mode**, you double your available bandwidth by aggregating two 1 Gbps links into a single 2 Gbps logical link. This is critical for storage servers, media streaming, and any workload that saturates a single NIC.

For high-availability clusters, bonding pairs naturally with tools like Keepalived and Pacemaker. The bonded interface provides the redundant network path that VRRP and fencing agents depend on.

For container networking on bonded interfaces, see our [Rook vs Longhorn vs OpenEBS storage guide](../rook-vs-longhorn-vs-openebs-self-hosted-kubernetes-storage-guide-2026/) which covers storage replication across bonded networks. For DNS configuration on bonded interfaces, check our [DNS-over-TLS resolver guide](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/). For network monitoring on bonded links, our [bandwidth monitoring comparison](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monitoring-guide-2026/) covers tools that track per-interface throughput.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Linux Network Bonding: Active-Backup vs LACP vs Round-Robin (2026)",
  "description": "Compare Linux network bonding approaches: kernel bonding driver, teamd, and NetworkManager. Learn which bonding mode suits your self-hosted server infrastructure.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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

## FAQ

### What is the difference between bonding and teaming?

Bonding uses a kernel module (`bonding.ko`) for both data and control plane operations, while teaming uses a small kernel module (`team.ko`) for the data plane and a userspace daemon (`teamd`) for the control plane. Bonding has been in the Linux kernel since 2001 and supports all seven bonding modes. Teaming is newer (2013), supports fewer modes, but offers more extensibility through its JSON configuration format.

### Does LACP require switch configuration?

Yes. IEEE 802.3ad (LACP) requires that the connected switch ports are configured for LACP (also called 802.3ad, Link Aggregation, or port-channel). If the switch doesn't support LACP, use active-backup mode (mode 1) instead, which requires no switch configuration at all.

### Can I bond wireless interfaces?

No. The Linux bonding driver does not support wireless (Wi-Fi) interfaces. Bonding is designed for wired Ethernet NICs. Wireless interfaces use different link-layer protocols and association mechanisms that are incompatible with bonding modes.

### How do I monitor bond interface status?

Use `cat /proc/net/bonding/bond0` to see the current bond mode, active slave, and status of all slave interfaces. For teamd, use `teamdctl team0 state`. For NetworkManager, use `nmcli device show bond0`. All three approaches also integrate with standard monitoring tools like Prometheus node_exporter.

### What is the best bonding mode for a database server?

For a database server, **active-backup (mode 1)** is typically the best choice. Databases benefit from consistent, predictable network behavior more than from load balancing. Active-backup provides fault tolerance without the complexity of LACP switch configuration. If you need higher throughput, **802.3ad (LACP)** is the next best option, assuming your switch supports it.

### Can I use VLANs on a bond interface?

Yes. VLANs work on top of bond interfaces just like physical interfaces. You can create `bond0.100` for VLAN 100 traffic, `bond0.200` for VLAN 200, and so on. The bond interface handles link aggregation and failover, while the VLAN sub-interfaces handle network segmentation.
