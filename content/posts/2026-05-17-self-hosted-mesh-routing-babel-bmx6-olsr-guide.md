---
title: "Self-Hosted Mesh Routing: Babel vs BMX6 vs OLSR"
date: "2026-05-17"
tags: ["mesh-networking", "routing", "networking", "wireless", "infrastructure"]
draft: false
---

Mesh routing protocols enable decentralized, self-healing network topologies where nodes dynamically discover routes to each other without a central router. This is essential for community networks, disaster recovery communications, and IoT deployments where traditional routing infrastructure is unavailable. In this guide, we compare three open-source mesh routing protocols: **Babel** (loop-free distance-vector), **BMX6** (layer 3 mesh routing), and **OLSR** (optimized link state routing).

## Babel: Loop-Free Distance-Vector Routing

[Babel](https://github.com/jech/babeld) (430+ stars) is a loop-free distance-vector routing protocol designed for both wired and wireless mesh networks. It combines the simplicity of distance-vector with the loop-free guarantees of link-state protocols, making it suitable for unstable networks where links frequently appear and disappear.

### Key Features

- **Loop-free guarantee** — no routing loops even during topology changes
- **Fast convergence** — reacts quickly to link failures and new routes
- **Dual-stack** — supports IPv4 and IPv6 simultaneously
- **Wireless-optimized** — handles link quality estimation for wireless interfaces
- **RFC standard** — published as RFC 8966, interoperable implementations exist

### Docker Compose Deployment

```yaml
version: '3'
services:
  babeld:
    image: ghcr.io/quagga/babeld:latest
    container_name: babeld
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: host
    command: [
      "-C", "/etc/babeld.conf",
      "-g", "6696",
      "-S", "/var/run/babeld.state",
      "eth0", "wlan0"
    ]
    volumes:
      - ./babeld.conf:/etc/babeld.conf:ro
      - /var/run:/var/run
```

### Babel Configuration

```ini
# /etc/babeld.conf
local-port 6696

# Interface configuration
interface eth0
    type wired
    hello-interval 4
    update-interval 2

interface wlan0
    type wireless
    hello-interval 2
    update-interval 1
    rxcost 256

# Redistribution rules
redistribute local ip6-prefix ::/0 metric 0
redistribute local deny
```

Babel's configuration is minimal compared to traditional routing protocols. The daemon automatically discovers neighbors, exchanges routing information, and computes optimal paths. The `rxcost` parameter on wireless interfaces allows Babel to factor in link quality when computing routes.

## BMX6: Layer 3 Mesh Routing Protocol

BMX6 is a layer 3 mesh routing protocol designed for community networks and decentralized internet infrastructure. It operates at the IP layer (unlike BATMAN which works at layer 2) and provides automatic gateway detection, IP address autoconfiguration, and decentralized DNS.

### Key Features

- **Layer 3 routing** — works at the IP layer, compatible with standard networking
- **Auto-addressing** — nodes auto-configure IP addresses without DHCP
- **Gateway detection** — automatic detection and announcement of internet gateways
- **Decentralized DNS** — built-in name resolution without central DNS servers
- **Multiple interfaces** — supports wired, wireless, and tunnel interfaces simultaneously

### Installation and Configuration

```bash
# Install BMX6 from source
git clone https://github.com/Intermesh/bmx6.git
cd bmx6
make
sudo make install

# Start BMX6 on all interfaces
sudo bmx6 -i eth0 -i wlan0 -i tun0
```

### Docker Compose Deployment

```yaml
version: '3'
services:
  bmx6:
    build:
      context: ./bmx6
      dockerfile: Dockerfile
    container_name: bmx6-router
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: host
    command: [
      "-i", "eth0",
      "-i", "wlan0",
      "--tun_outgoing_network", "10.0.0.0/8",
      "--originator_mac", "auto"
    ]
    volumes:
      - /var/run:/var/run
```

BMX6 creates a `tunl0` tunnel interface that carries all mesh traffic. The protocol automatically assigns globally unique IPv6 addresses to each node and maintains routing tables that adapt to topology changes in real-time.

## OLSR: Optimized Link State Routing

OLSR (Optimized Link State Routing) is one of the most widely deployed mesh routing protocols. It uses a proactive link-state approach where nodes periodically exchange topology information, enabling fast route computation and stable routing tables. OLSR2 (RFC 7181) is the current version with improved scalability.

### Key Features

- **Proactive routing** — routes are pre-computed, zero latency for first packet
- **MPR optimization** — Multipoint Relays reduce control traffic overhead
- **ETX metric** — Expected Transmission Count for link quality estimation
- **Extensive ecosystem** — plugins for HTTP info, nameservice, dynamic gateway
- **Mature deployment** — used in community networks worldwide (Freifunk, Guifi.net)

### Docker Compose Deployment

```yaml
version: '3'
services:
  olsrd:
    image: openvpn/olsrd:latest
    container_name: olsrd
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: host
    command: [
      "-d", "2",
      "-f", "/etc/olsrd.conf",
      "-fork"
    ]
    volumes:
      - ./olsrd.conf:/etc/olsrd.conf:ro
```

### OLSR Configuration

```ini
# /etc/olsrd.conf
DebugLevel 2
IpVersion 6

# Plugins
LoadPlugin "olsrd_nameservice.so.0.1"
{
    PlName "meshnode.local"
    PlSuffix "_gw.mesh"
}

LoadPlugin "olsrd_dyn_gw.so.0.5"
{
    Ping "8.8.8.8"
    Ping "1.1.1.1"
    Interval "60"
}

# Interface defaults
Interface "wlan0"
{
    HelloInterval 2.0
    HelloValidityTime 20.0
    TcInterval 5.0
    TcValidityTime 300.0
    MidInterval 5.0
    MidValidityTime 300.0
    HnaInterval 5.0
    HnaValidityTime 75.0
}
```

### Protocol Comparison

| Feature | Babel | BMX6 | OLSR |
|---------|-------|------|------|
| Protocol type | Distance-vector | Layer 3 mesh | Link-state |
| Loop-free | ✅ Guaranteed | ✅ Yes | ✅ Yes |
| IPv6 support | ✅ Native | ✅ Primary | ✅ Supported |
| Convergence speed | Fast (reactive) | Medium | Fast (proactive) |
| Control overhead | Low | Medium | Medium-High |
| RFC standard | RFC 8966 | Proprietary | RFC 7181 (OLSR2) |
| Community adoption | Growing | Niche | Very high |
| GitHub Stars | 430+ | Community | Community |
| Best for | Mixed networks | Community networks | Large deployments |

## Why Self-Host Mesh Routing?

Deploying mesh routing protocols on your own infrastructure enables network architectures that traditional routing cannot achieve:

**Resilient multi-path connectivity.** Mesh routing protocols automatically discover and maintain multiple paths between nodes. If one link fails, traffic seamlessly reroutes through alternative paths. For critical infrastructure — industrial control systems, hospital networks, or emergency communications — this automatic failover is invaluable.

**Decentralized architecture.** No central router means no single point of failure. Each node independently participates in route computation and can forward traffic for other nodes. This is fundamentally different from traditional star or tree topologies where the core router is a critical dependency.

**Community network enablement.** Mesh routing protocols power community internet initiatives worldwide — Freifunk in Germany, Guifi.net in Spain, and NYC Mesh in the United States. By deploying these protocols on commodity hardware, communities can build internet infrastructure independent of commercial ISPs.

**IoT and sensor network support.** For deployments with hundreds of low-power sensors across a campus, factory, or agricultural field, mesh routing provides reliable connectivity without requiring each sensor to have a direct route to a gateway. Intermediate nodes forward traffic, extending effective range far beyond individual radio reach.

For network topology discovery, see our [LLDP and CDP guide](../2026-05-11-self-hosted-lldp-network-discovery-lldpd-frr-2026/). For overlay networking, check our [ZeroTier vs Nebula comparison](../self-hosted-overlay-networks-zerotier-nebula-netmaker-guide-2026/). For broader network configuration management, our [Ansible vs Nornir guide](../self-hosted-network-configuration-management-ansible-vs-nornir-vs-netbox/) covers automation approaches.

### Choosing the Right Mesh Routing Protocol

For mixed wired-wireless deployments with unstable links, Babel offers the best combination of fast convergence, low overhead, and loop-free guarantees. Its RFC-standard status ensures interoperability. For community networks, BMX6 provides unique features like automatic IP address assignment and decentralized DNS. OLSR remains the most widely deployed mesh routing protocol with proactive nature providing zero-latency forwarding, though control traffic overhead scales with network size.

### Security Considerations

Mesh routing protocols were designed for trusted environments and do not include built-in authentication or encryption. To secure deployments, combine the routing protocol with encrypted tunnels — run Babel, BMX6, or OLSR over WireGuard or IPsec tunnels so routing messages are encrypted and authenticated at the transport layer. Monitor routing tables for anomalies indicating potential routing manipulation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mesh Routing: Babel vs BMX6 vs OLSR",
  "description": "Compare Babel, BMX6, and OLSR mesh routing protocols for decentralized networking.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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

### What is the difference between Babel and OLSR?

Babel is a distance-vector protocol that reacts to topology changes and guarantees loop-free routing. OLSR is a proactive link-state protocol that pre-computes routes and uses Multipoint Relays to reduce control traffic. Babel has lower overhead and faster reaction to changes, while OLSR provides more stable routing tables with zero-latency first-packet forwarding.

### Can mesh routing protocols work over the internet?

Yes. Babel, BMX6, and OLSR can all operate over IP tunnels (WireGuard, GRE, or IPsec) that span the internet. This is how community networks like Freifunk connect nodes across cities. The tunnel acts as a virtual link, and the mesh routing protocol treats it like any other interface.

### How many nodes can OLSR support?

OLSR with MPR optimization can handle networks of 100-500 nodes effectively. Beyond that, control traffic overhead becomes significant. OLSR2 (RFC 7181) improves scalability with better metric handling and reduced control message frequency. For very large networks (1000+ nodes), Babel is often preferred due to its lower overhead.

### Does BMX6 require a central server?

No. BMX6 is fully decentralized. Nodes discover each other through periodic broadcast messages on shared interfaces. However, BMX6's auto-addressing and gateway detection features benefit from having at least one node configured as a gateway to provide internet access to the mesh.

### Which protocol is best for a wireless mesh network?

For wireless mesh networks with unstable links, Babel is generally the best choice. Its reactive nature and link quality estimation handle wireless link fluctuations well. OLSR is also viable but requires careful tuning of hello intervals and MPR selection to avoid excessive control traffic on lossy links. BMX6 works well for community networks with mixed wired and wireless links.

### How do I monitor mesh routing health?

Babel provides a JSON API on port 6696 (configurable) that exposes routing tables, neighbor states, and interface statistics. OLSR has the `olsrd_info` plugin that provides an HTTP interface with routing tables, topology maps, and neighbor information. BMX6 provides status information through its control socket and the `bmx6 -s` command.
