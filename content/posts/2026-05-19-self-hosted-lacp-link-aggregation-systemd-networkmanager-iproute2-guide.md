---
title: "Self-Hosted LACP Link Aggregation: systemd networkd vs NetworkManager vs iproute2 (2026)"
date: "2026-05-19"
tags: ["lacp", "link-aggregation", "bonding", "networking", "high-availability", "systemd"]
draft: false
---

Link Aggregation Control Protocol (LACP), defined in IEEE 802.3ad (now 802.1AX), combines multiple physical network interfaces into a single logical bond for increased bandwidth and redundancy. Self-hosting LACP configuration gives you control over link aggregation without relying on managed switch auto-configuration or proprietary vendor tools.

This guide compares three approaches for managing LACP bonds on Linux: **systemd networkd**, **NetworkManager**, and **iproute2** (manual tc/ip commands).

## What Is LACP and Why Use It?

LACP (Link Aggregation Control Protocol) dynamically negotiates link aggregation between a host and a managed switch, providing:

- **Increased bandwidth**: Aggregate throughput across multiple physical links (e.g., 2×1Gbps = 2Gbps logical)
- **Fault tolerance**: Automatic failover when a physical link fails
- **Load balancing**: Traffic distribution across member links using hash-based algorithms
- **Dynamic negotiation**: LACPDU packets verify link health and negotiate aggregation parameters

Key use cases include server uplinks, storage network connections, virtualization host networking, and any scenario where link redundancy and bandwidth scaling are critical.

## systemd networkd

systemd networkd is the network configuration daemon included with systemd. It provides declarative bond configuration through `.netdev` and `.network` files, making it ideal for servers already running systemd.

**GitHub**: [systemd/systemd](https://github.com/systemd/systemd) — ⭐16,307 | Last updated: May 2026 | Language: C

### Key Features

- **Declarative configuration**: Bond settings defined in unit files
- **LACP support**: Full 802.3ad bond mode with configurable transmit policies
- **Integration with systemd**: Unified management via `systemctl`
- **No external dependencies**: Ships with systemd on most distributions
- **Link health monitoring**: Built-in carrier and link state tracking

### Configuration

```ini
# /etc/systemd/network/10-bond-lacp.netdev
[NetDev]
Name=bond0
Kind=bond

[Bond]
Mode=802.3ad
TransmitHashPolicy=layer3+4
MIIMonitorSec=1s
LACPTransmitRate=fast

# /etc/systemd/network/20-bond-member1.network
[Match]
Name=eth0

[Network]
Bond=bond0

# /etc/systemd/network/20-bond-member2.network
[Match]
Name=eth1

[Network]
Bond=bond0

# /etc/systemd/network/30-bond.network
[Match]
Name=bond0

[Network]
DHCP=yes
```

### Activation

```bash
# Restart networkd to apply configuration
sudo systemctl restart systemd-networkd

# Verify bond status
cat /proc/net/bonding/bond0

# Check LACP partner info
sudo networkctl status bond0
```

## NetworkManager

NetworkManager is the default network management daemon for most desktop Linux distributions and increasingly adopted on servers. It provides both CLI (nmcli) and GUI (nm-connection-editor) interfaces for bond management.

**GitHub**: [NetworkManager/NetworkManager](https://gitlab.freedesktop.org/NetworkManager/NetworkManager) — actively maintained | Language: C

### Key Features

- **nmcli CLI**: Full scripting interface for automated configuration
- **LACP modes**: 802.3ad (mode 4) with all standard options
- **Connection profiles**: Save and switch between bond configurations
- **D-Bus API**: Programmatic control from applications and orchestration tools
- **Broad hardware support**: Works with virtually all Linux network drivers

### Configuration via nmcli

```bash
# Create an LACP bond (mode 802.3ad)
sudo nmcli connection add type bond   ifname bond0   mode 802.3ad   xmit_hash_policy layer3+4   miimon 100   lacp_rate fast

# Add member interfaces
sudo nmcli connection add type bond-slave   ifname eth0   master bond0

sudo nmcli connection add type bond-slave   ifname eth1   master bond0

# Bring up the bond
sudo nmcli connection up bond-slave-eth0
sudo nmcli connection up bond-slave-eth1
sudo nmcli connection up bond0

# Verify
nmcli connection show bond0
nmcli device status
```

### Persistent Configuration (Keyfile)

```ini
# /etc/NetworkManager/system-connections/bond0.nmconnection
[connection]
id=bond0
type=bond
interface-name=bond0

[bond]
mode=802.3ad
xmit_hash_policy=layer3+4
miimon=100
lacp_rate=fast

[ipv4]
method=auto

[ipv6]
method=auto
```

## iproute2 (Manual Configuration)

iproute2 provides the `ip` command suite for direct kernel-level network configuration. Manual bond setup gives maximum control and works on any Linux distribution without requiring a network management daemon.

**GitHub**: [shemminger/iproute2](https://github.com/shemminger/iproute2) — ⭐968 | Last updated: May 2026 | Language: C

### Key Features

- **Zero daemon overhead**: Direct kernel configuration, no background service
- **Full kernel bonding API**: All 7 bonding modes supported
- **Immediate effect**: Changes apply instantly without service restarts
- **Scriptable**: Ideal for init scripts, PXE boot, and embedded systems
- **Works everywhere**: Available on all Linux distributions

### Configuration

```bash
# Load the bonding kernel module
sudo modprobe bonding

# Create the bond interface in 802.3ad mode
sudo ip link add bond0 type bond   mode 802.3ad   xmit_hash_policy layer3+4   miimon 100   lacp_rate fast

# Enslave physical interfaces
sudo ip link set eth0 down
sudo ip link set eth0 master bond0
sudo ip link set eth0 up

sudo ip link set eth1 down
sudo ip link set eth1 master bond0
sudo ip link set eth1 up

# Bring up the bond and get an IP
sudo ip link set bond0 up
sudo dhclient bond0

# Verify bond status
cat /proc/net/bonding/bond0
ip -d link show bond0
```

### Systemd Service (Persistent)

```ini
# /etc/systemd/system/lacp-bond.service
[Unit]
Description=Configure LACP Bond
After=network-pre.target
Before=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/setup-lacp-bond.sh
ExecStop=/usr/local/sbin/teardown-lacp-bond.sh

[Install]
WantedBy=multi-user.target
```

```bash
#!/bin/bash
# /usr/local/sbin/setup-lacp-bond.sh
modprobe bonding
ip link add bond0 type bond mode 802.3ad xmit_hash_policy layer3+4 miimon 100 lacp_rate fast
ip link set eth0 master bond0
ip link set eth1 master bond0
ip link set bond0 up
```

## Comparison Table

| Feature | systemd networkd | NetworkManager | iproute2 |
|---------|-----------------|----------------|----------|
| **LACP (802.3ad)** | Yes | Yes | Yes |
| **Configuration Style** | Declarative (INI files) | Declarative + CLI | Imperative (commands) |
| **Dynamic Reconfiguration** | Via file reload | Via nmcli | Manual re-execution |
| **Link Monitoring** | MII/ARP | MII/ARP | MII/ARP |
| **LACP Rate Control** | slow/fast | slow/fast | slow/fast |
| **Hash Policies** | All 6 modes | All 6 modes | All 6 modes |
| **GUI Available** | No | Yes (nm-connection-editor) | No |
| **Desktop Integration** | Limited | Full | None |
| **Server Suitability** | Excellent | Good | Excellent |
| **Dependencies** | systemd | NetworkManager | kernel + iproute2 |
| **Best For** | systemd servers | Desktop/mixed | Minimal/embedded |

## Why Self-Host Your LACP Configuration?

Self-hosting LACP bond configuration on your servers ensures high availability and bandwidth aggregation without depending on cloud provider virtual networking abstractions. When you manage your own link aggregation, you control the failover behavior, load balancing algorithm, and LACP negotiation parameters — critical factors for storage networks, virtualization hosts, and database clusters where network reliability directly impacts service availability.

Running LACP bonds on your own hardware means you can optimize the transmit hash policy for your specific traffic patterns, configure LACP fast transmission rates for quicker failure detection, and integrate bond monitoring with your existing alerting infrastructure. Whether you prefer the declarative simplicity of systemd networkd, the flexibility of NetworkManager, or the bare-metal control of iproute2, self-hosting gives you the freedom to choose the approach that best fits your operational model.

For VLAN configuration on bonded interfaces, see our [VXLAN tunneling guide](../2026-05-18-self-hosted-vxlan-tunneling-open-vswitch-frrouting-ovn-2026/) covering Open vSwitch and OVN. If you need network interface diagnostics, our [ethtool vs mii-tool comparison](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) covers interface management tools. For GRE tunnel management, check our [OVS vs Linux GRE vs GRETAP guide](../2026-05-18-self-hosted-gre-tunnel-management-openvswitch-linux-gre-gretap-guide-2026/).

## FAQ

### What is the difference between LACP and static link aggregation?

LACP (802.3ad, mode 4) dynamically negotiates the bond with the connected switch using LACPDU packets, verifying that both ends agree on the aggregation. Static link aggregation (mode 0, balance-rr) configures the bond without negotiation — both sides must be manually configured to match. LACP is preferred because it detects misconfigurations, validates link state, and can automatically remove failed links from the aggregate.

### Which LACP transmit hash policy should I use?

The `layer3+4` policy (default) hashes based on source/destination IP addresses and TCP/UDP ports, providing good load distribution for most workloads. Use `layer2+3` if you need consistent MAC-level hashing for bridged traffic. For IPv6-heavy environments, `encap2+3` includes inner header hashing for tunneled traffic. Test with your actual traffic patterns — the optimal policy depends on your workload characteristics.

### Can I use LACP with unmanaged switches?

No. LACP requires the connected switch to support and be configured for 802.3ad link aggregation. If your switch does not support LACP, you can use bonding mode `active-backup` (mode 1) for failover-only redundancy, which does not require switch configuration. Alternatively, use `balance-tlb` (mode 5) or `balance-alb` (mode 6) for adaptive load balancing without switch support.

### How do I monitor LACP bond health?

Check `/proc/net/bonding/bond0` for real-time bond status, including active slave interfaces, link state, and LACP partner information. With systemd networkd, use `networkctl status bond0`. With NetworkManager, use `nmcli device status`. For automated monitoring, track the `bonding_mii_status` or use SNMP to poll the `ifOperStatus` of bond member interfaces.

### What is LACP fast transmission rate?

LACP fast mode sends LACPDU packets every 1 second (vs. 30 seconds in slow mode), enabling faster detection of link failures and misconfigurations. Configure `lacp_rate=fast` in your bond settings for environments where rapid failover is critical. The switch must also support fast LACP for this to work — both ends must agree on the transmission rate.

### Does LACP increase per-connection throughput?

No. LACP load balances across member links using a hash algorithm, but a single TCP/UDP flow always uses one physical link. The aggregate bandwidth is shared across multiple independent flows. For a single large file transfer, you will see at most the speed of one member link. Multiple simultaneous transfers will distribute across the aggregate bandwidth.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LACP Link Aggregation: systemd networkd vs NetworkManager vs iproute2 (2026)",
  "description": "Compare systemd networkd, NetworkManager, and iproute2 for self-hosted LACP link aggregation. Includes configuration examples, comparison table, and deployment guides.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
