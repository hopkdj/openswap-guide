---
title: "Self-Hosted Linux Network Interface Diagnostics: ethtool vs mii-tool vs ip-link"
date: "2026-06-01"
tags: ["linux", "networking", "diagnostics", "sysadmin", "network-monitoring"]
draft: false
---

## Introduction

When your server's network performance degrades — packet loss, link flapping, or unexpected speed drops — your first instinct should be to check the network interface itself. Linux provides three powerful command-line tools for interrogating and manipulating network interfaces: **ethtool**, **mii-tool**, and **ip-link**. Each serves a distinct role in the diagnostic toolkit, from querying driver-level hardware settings to inspecting link-layer state and configuring virtual interfaces.

This guide compares these three essential diagnostics tools, covering their strengths, limitations, and when to reach for each one.

## Feature Comparison

| Feature | ethtool | mii-tool | ip-link |
|---------|---------|----------|---------|
| **Scope** | Driver/NIC hardware level | Media Independent Interface (MII) | Link layer + virtual interfaces |
| **Speed/Duplex** | Full control (autoneg, fixed) | Read + basic set | Basic status only |
| **Ring Buffer** | Query + resize RX/TX rings | Not supported | Not supported |
| **Driver Info** | Driver name, version, firmware | Not supported | Not supported |
| **Wake-on-LAN** | Full WoL configuration | Not supported | Basic WoL support |
| **Statistics** | Per-queue, per-ring stats | Link status only | Basic RX/TX counters |
| **Virtual Interfaces** | Not applicable | Not applicable | VLAN, bridge, bond, MACVLAN, VXLAN |
| **Cable Testing** | TDR diagnostics (some NICs) | Not supported | Not supported |
| **Kernel Module** | Driver-specific ioctls | Deprecated SIOC ioctls | Netlink (modern) |
| **Package** | ethtool | net-tools (legacy) | iproute2 |

## ethtool — Deep Hardware Inspection

`ethtool` is the go-to tool for querying and modifying Ethernet device settings at the driver level. It communicates directly with the NIC driver through `ioctl()` calls, exposing parameters that other tools cannot see.

### Installation

```bash
# Debian/Ubuntu
sudo apt install ethtool

# RHEL/CentOS/Fedora
sudo dnf install ethtool

# Arch Linux
sudo pacman -S ethtool
```

### Essential Diagnostic Commands

```bash
# Display basic interface information
ethtool eth0

# Show driver information and firmware version
ethtool -i eth0

# Display ring buffer parameters
ethtool -g eth0

# Show NIC statistics (per-queue drops, errors)
ethtool -S eth0

# Test cable integrity (supported NICs only)
ethtool --cable-test eth0

# Set speed and duplex manually
ethtool -s eth0 speed 1000 duplex full autoneg off

# View and set RX/TX ring buffer sizes
ethtool -G eth0 rx 4096 tx 4096

# Check Wake-on-LAN settings
ethtool eth0 | grep Wake-on
```

### When to Use ethtool

Use ethtool when you need to diagnose hardware-level issues: link negotiation failures, ring buffer overflows leading to packet drops, NIC firmware bugs, or Wake-on-LAN misconfiguration. If `dmesg` shows driver errors like `tg3: RX ring full`, ethtool is your tool.

## mii-tool — The Legacy MII Inspector

`mii-tool` is the original Media Independent Interface diagnostic utility, part of the `net-tools` package. It predates ethtool and uses the older SIOCGMIIPHY/SIOCGMIIREG ioctl interface. While deprecated on modern kernels, it still ships in many distributions and works for basic link checks.

### Installation

```bash
# Debian/Ubuntu (may not be available on newer releases)
sudo apt install net-tools

# RHEL/CentOS
sudo dnf install net-tools
```

### Usage Examples

```bash
# Check link status for all interfaces
mii-tool

# Monitor an interface continuously
mii-tool --watch eth0

# Force interface to restart auto-negotiation
mii-tool --restart eth0

# Advertise specific capabilities
mii-tool --advertise=100baseTx-FD eth0
```

### When to Use mii-tool

Reserve mii-tool for quick link status checks on legacy systems or embedded devices where ethtool is unavailable. Its output is simpler and more human-readable than ethtool's verbose output, making it useful for shell scripts that need a binary link-up/link-down answer.

**Important caveat:** Many modern NIC drivers (e.g., igb, ixgbe, bnxt_en) do not implement the MII ioctl interface. On these systems, mii-tool will report "no MII interfaces found" — use ethtool or ip-link instead.

## ip-link — The Modern Swiss Army Knife

`ip link` is the modern replacement for the deprecated `ifconfig`, `route`, and other net-tools commands. Part of the `iproute2` suite, it uses the Netlink socket interface — a far more robust and extensible protocol than the old ioctl-based tools.

### Installation

```bash
# Debian/Ubuntu
sudo apt install iproute2

# RHEL/CentOS/Fedora  
sudo dnf install iproute

# Arch Linux
sudo pacman -S iproute2
```

### Essential Diagnostic Commands

```bash
# Show all interfaces with link state
ip link show

# Show detailed interface statistics
ip -s link show eth0

# Show interface in JSON format for scripts
ip -j link show eth0

# Bring interface up/down
ip link set eth0 up
ip link set eth0 down

# Change interface MTU
ip link set eth0 mtu 9000

# Change interface MAC address
ip link set eth0 address 00:11:22:33:44:55

# Create virtual interfaces
ip link add name br0 type bridge
ip link add link eth0 name eth0.10 type vlan id 10
ip link add name bond0 type bond mode 802.3ad

# Show bridge FDB (forwarding database)
bridge fdb show
```

### When to Use ip-link

Use ip-link for everyday interface management: checking link state, bringing interfaces up/down, adjusting MTU, creating VLANs and bridges, and managing interface aliases. It is the standard tool on all modern Linux distributions and the only one of the three that handles virtual interfaces.

## Diagnostic Decision Tree

```
Network problem detected
│
├─ Is the link physically up?
│   ├─ ip link show eth0 → Check "state UP"
│   └─ ethtool eth0 → Check "Link detected: yes"
│
├─ Is the speed/duplex correct?
│   ├─ ethtool eth0 → Check "Speed" and "Duplex"
│   └─ mii-tool eth0 → Quick confirmation (legacy NICs only)
│
├─ Are there hardware errors?
│   ├─ ethtool -S eth0 → Check rx_crc_errors, tx_errors
│   └─ ip -s link show eth0 → Check RX/TX errors/dropped
│
├─ Is the ring buffer adequate?
│   └─ ethtool -g eth0 → Check current vs maximum ring sizes
│
└─ Virtual interfaces misconfigured?
    └─ ip link show → Verify VLANs, bridges, bonds
```

## Why Self-Host Your Network Diagnostics Stack?

When troubleshooting production network issues, relying on cloud-based monitoring dashboards introduces latency and dependency risks. Self-hosted diagnostic tools give you direct, immediate access to interface-level metrics without an internet connection — critical during network outages when cloud UIs are unreachable.

For comprehensive bandwidth testing across your infrastructure, see our [iperf3 vs netperf vs qperf comparison](../2026-05-08-iperf3-vs-netperf-vs-qperf-self-hosted-network-bandwidth-testing/). If you need to capture and analyze raw network traffic, our [tcpdump vs tshark packet capture guide](../2026-04-27-tcpdump-vs-tshark-vs-termshark-self-hosted-packet-capture-guide-2026/) covers terminal-based alternatives to Wireshark. For ongoing bandwidth utilization monitoring across multiple interfaces, our [vnstat vs nethogs vs iftop guide](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monitoring-guide-2026/) provides real-time and historical traffic analysis.

These tools form a complete network observability pipeline: interface health (ethtool/ip-link), traffic capture (tcpdump/tshark), throughput testing (iperf3/netperf), and ongoing monitoring (vnstat/nethogs). Together they eliminate dependency on external services for diagnosing even the most subtle network issues.

## FAQ

### What is the difference between ethtool and ip-link for link status?

`ethtool` queries the NIC driver directly through hardware-specific ioctl calls, giving you physical-layer information like negotiated speed, duplex mode, and auto-negotiation status. `ip link show` reports the kernel's view of the interface — whether it is administratively UP and operationally LOWERLAYERUP. For physical link problems (cable disconnected, wrong speed), ethtool provides more detail. For logical state (admin down, VLAN misconfiguration), ip-link is the right tool.

### Is mii-tool deprecated? Should I still use it?

Yes, mii-tool is deprecated. It uses legacy SIOC ioctls that many modern NIC drivers no longer implement. On systems with Intel igb/ixgbe, Broadcom bnxt_en, or Mellanox mlx5 drivers, mii-tool will return "no MII interfaces found." Use ethtool for detailed hardware diagnostics and ip-link for basic link status. The only reason to keep mii-tool around is for compatibility with very old shell scripts or embedded systems running kernels older than 3.x.

### Can ethtool fix packet loss issues?

Indirectly, yes. Packet loss often occurs when the NIC's RX ring buffer overflows under high traffic load. `ethtool -g eth0` shows current and maximum ring buffer sizes. Increasing the RX ring with `ethtool -G eth0 rx 4096` often resolves burst-related packet loss. ethtool can also detect physical layer problems: `ethtool -S eth0` exposes per-queue drop counters like `rx_missed_errors` or `rx_fifo_errors` that point to hardware-level issues.

### Why use ip-link instead of the old ifconfig command?

`ifconfig` (from net-tools) was deprecated over a decade ago and no longer receives updates. It cannot display or manage VLANs, bridges, network namespaces, MACVLAN interfaces, or VXLAN tunnels. It reports incorrect statistics on 64-bit counters and does not understand modern features like SR-IOV. `ip link` from iproute2 is actively maintained, supports all modern networking features, and uses the efficient Netlink protocol instead of the fragile /proc/net/dev interface that ifconfig relies on.

### How do I check if my NIC firmware needs updating?

Use `ethtool -i eth0` to display the driver name, version, and firmware version. Compare the firmware version against your hardware vendor's latest release. For Intel NICs, the `ixgbe` driver typically reports firmware in the output. For Broadcom, check the `bnxt_en` output. Outdated firmware is a common root cause of intermittent link flaps and unexpected packet corruption — especially on 10GbE and faster interfaces.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 科技政策监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 科技行业的发展趋势已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Network Interface Diagnostics: ethtool vs mii-tool vs ip-link",
  "description": "Comprehensive comparison of Linux network interface diagnostic tools — ethtool for hardware-level inspection, mii-tool for legacy MII status, and ip-link for modern interface management. Includes installation guides, diagnostic decision trees, and troubleshooting workflows.",
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
