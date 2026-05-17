---
title: "Self-Hosted IGMP Proxy Comparison: igmpproxy vs mcproxy vs udpxy (2026)"
date: "2026-05-17"
tags: ["multicast", "igmp", "networking", "iptv", "proxy", "routing"]
draft: false
---

IP multicast enables efficient one-to-many data distribution — IPTV streams, financial market data feeds, IoT sensor broadcasts, and live event distribution all rely on it. However, multicast traffic cannot cross network boundaries without an IGMP (Internet Group Management Protocol) proxy or a multicast-to-unicast converter. In this guide, we compare three open-source solutions: **igmpproxy**, **mcproxy**, and **udpxy**.

## Why Multicast Needs a Proxy

Multicast uses IGMP signaling to let hosts join and leave multicast groups. Routers use PIM (Protocol Independent Multicast) to build distribution trees. The problem: most consumer and enterprise networks segment multicast traffic at the router or firewall boundary. Without an IGMP proxy, downstream clients cannot receive multicast streams from upstream sources.

An IGMP proxy sits between two or more network segments, forwarding IGMP membership reports upstream and multicast data downstream. A multicast-to-HTTP proxy like udpxy goes further — it converts multicast UDP streams into HTTP unicast streams that any standard media player or web browser can consume.

## igmpproxy — Simple IGMP Multicast Forwarding

**igmpproxy** ([pali/igmpproxy](https://github.com/pali/igmpproxy)) is a lightweight IGMP proxy daemon with **169+ GitHub stars**. It forwards IGMP membership reports from downstream interfaces to upstream interfaces and routes multicast traffic back. Designed for simple home and small office multicast routing.

### Key Features

- IGMPv1, IGMPv2, and IGMPv3 support
- Multiple downstream interfaces
- Simple static routing configuration
- Low resource usage (single C binary)
- Compatible with standard Linux multicast routing
- Works with any upstream multicast source

### Installation and Configuration

```bash
# Debian/Ubuntu
apt install igmpproxy

# Configuration: /etc/igmpproxy.conf
cat > /etc/igmpproxy.conf << 'CONF'
# Upstream interface (toward multicast source)
phyint eth0 upstream ratelimit 0 threshold 1

# Downstream interface (toward clients)
phyint eth1 downstream ratelimit 0 threshold 1

# Optional: whitelist specific multicast ranges
altnet 239.0.0.0/8
altnet 224.0.0.0/4
CONF

# Start the service
systemctl enable igmpproxy
systemctl start igmpproxy
```

### Docker Deployment

```yaml
version: "3.8"
services:
  igmpproxy:
    image: huntastikus/igmpproxy:latest
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./igmpproxy.conf:/etc/igmpproxy.conf:ro
    restart: always
```

## mcproxy — Advanced Multicast Proxy with MLD Support

**mcproxy** ([mcproxy/mcproxy](https://github.com/mcproxy/mcproxy)) is a more feature-rich multicast proxy with **81+ GitHub stars**. It supports both IGMP (IPv4) and MLD (IPv6), making it suitable for dual-stack networks. mcproxy includes a configuration language for advanced routing policies and can replace traditional multicast routing daemons in small networks.

### Key Features

- IGMPv1/v2/v3 and MLDv1/v2 support
- IPv4 and IPv6 multicast forwarding
- Rule-based filtering and routing policies
- Multiple upstream and downstream interfaces
- Proxy mode and router mode operation
- Active development with recent commits

### Configuration

```
# mcproxy.conf
instance "main" {
    protocol IGMPv3 {
        interface "eth0" {
            direction upstream
        }
        interface "eth1" {
            direction downstream
        }
    }
    protocol MLDv2 {
        interface "eth0" {
            direction upstream
        }
        interface "eth1" {
            direction downstream
        }
    }
    routing "main" {
        interface "eth0" {
            direction upstream
        }
        interface "eth1" {
            direction downstream
        }
    }
}
```

### Building from Source

```bash
git clone https://github.com/mcproxy/mcproxy.git
cd mcproxy
mkdir build && cd build
cmake ..
make
sudo make install
```

## udpxy — Multicast-to-HTTP Unicast Gateway

**udpxy** ([pcherenkov/udpxy](https://github.com/pcherenkov/udpxy)) is a multicast-to-HTTP relay daemon with **303+ GitHub stars**. Instead of forwarding IGMP signals, udpxy listens for HTTP requests from clients, joins the corresponding multicast group on their behalf, and streams the content back as a standard HTTP response. This means any HTTP client — VLC, a web browser, or a smart TV app — can consume multicast content without IGMP support.

### Key Features

- Multicast UDP to HTTP unicast conversion
- Built-in web status page with stream statistics
- Fast channel change (FCC) support for IPTV
- Multicast subscription management
- HTTP keep-alive for persistent streams
- Cross-platform (Linux, BSD, embedded routers)

### Installation

```bash
# Build from source
git clone https://github.com/pcherenkov/udpxy.git
cd udpxy
make
sudo make install

# Or install from package manager (some distributions)
apt install udpxy
```

### Configuration and Usage

```bash
# Start udpxy on port 4022, bound to eth1
udpxy -p 4022 -a eth1 -m eth0 -B 1Mb -c 50 -S

# Clients access multicast streams via HTTP:
# http://<udpxy-server>:4022/udp/239.1.1.1:5000
# http://<udpxy-server>:4022/udp/239.1.1.2:5001

# Systemd service
cat > /etc/systemd/system/udpxy.service << 'UNIT'
[Unit]
Description=udpxy Multicast-to-HTTP Gateway
After=network.target

[Service]
ExecStart=/usr/local/bin/udpxy -p 4022 -a 192.168.1.1 -m eth0 -B 2Mb -c 100
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

systemctl enable udpxy
systemctl start udpxy
```

### Docker Deployment

```yaml
version: "3.8"
services:
  udpxy:
    image: fanmingming/docker-udpxy:latest
    ports:
      - "4022:4022/tcp"
    environment:
      - UDPXY_PORT=4022
      - UDPXY_BIND_ADDR=0.0.0.0
      - UDPXY_SRC_ADDR=eth0
    network_mode: host
    restart: always
```

## Comparison Table

| Feature | igmpproxy | mcproxy | udpxy |
|---------|-----------|---------|-------|
| GitHub Stars | 169+ | 81+ | 303+ |
| Protocol | IGMP only | IGMP + MLD | HTTP proxy |
| IPv6 Support | No | Yes (MLD) | No |
| IGMPv3/SSM | Yes | Yes | N/A |
| HTTP Output | No | No | Yes |
| Web Status Page | No | No | Yes |
| Fast Channel Change | No | No | Yes |
| Max Clients | Unlimited | Unlimited | Configurable |
| Configuration | Simple file | Rule-based DSL | CLI flags |
| Best For | Simple forwarding | Dual-stack networks | IPTV/streaming |

## Why Self-Host Your Multicast Proxy?

Running your own multicast proxy or HTTP gateway eliminates dependency on proprietary IPTV middleware solutions. Many commercial IPTV platforms charge per-subscriber licensing fees — with udpxy or igmpproxy, you can serve unlimited clients on your own infrastructure at zero marginal cost.

For home lab and homelab IPTV setups, udpxy enables any device with an HTTP player to consume multicast TV streams. Smart TVs, tablets, and phones that lack native IGMP support can still access your multicast content through the HTTP conversion layer. This is particularly valuable for IPTV providers who need to serve heterogeneous client devices.

In enterprise environments, mcproxy's IGMPv3 and MLDv2 support enables source-specific multicast (SSM) for security-sensitive deployments. SSM ensures that receivers only accept data from authorized sources, preventing multicast spoofing attacks. Combined with proper firewall rules, this creates a secure multicast distribution channel for internal data feeds.

For broader network infrastructure needs, consider deploying [FRRouting](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) alongside your IGMP proxy for full PIM multicast routing, or pairing with [network flow analysis tools](../2026-05-24-self-hosted-network-flow-collectors-goflow2-softflowd-nfdump-guide/) to monitor multicast traffic patterns and bandwidth consumption.

## Choosing the Right Multicast Solution

- **igmpproxy** is ideal for simple multicast forwarding between two network segments. Its minimal configuration and low resource usage make it perfect for routers, access points, and edge devices.
- **mcproxy** is the right choice when you need IPv6 multicast support (MLD), advanced filtering rules, or source-specific multicast in a dual-stack network environment.
- **udpxy** excels as an IPTV gateway, converting multicast UDP streams into HTTP that any client device can consume. Essential for serving heterogeneous devices in a home or commercial IPTV deployment.

## Network Architecture Considerations

When deploying multicast proxies in production, network topology matters significantly. Place igmpproxy or mcproxy at the network boundary between your multicast source network and client network — typically on your core router or a dedicated multicast gateway appliance. The upstream interface should connect to the network where multicast sources (IPTV headends, data feeds) reside, while downstream interfaces serve client subnets.

For udpxy deployments, the HTTP gateway should be placed on the client-facing network so that end devices can reach it directly. The udpxy server itself needs access to the multicast source network on its upstream interface. In a typical IPTV architecture, this means udpxy runs on a server connected to both the multicast distribution VLAN and the client access VLAN.

Bandwidth planning is critical — each udpxy client consumes the full stream bitrate from the server. A 1080p IPTV stream at 8 Mbps with 50 concurrent clients requires 400 Mbps of server egress bandwidth. Deploy udpxy behind a load balancer or run multiple instances on different servers for larger deployments. Monitor multicast traffic using tools like tcpdump or the built-in udpxy status page to detect issues early.


## FAQ

### What is the difference between IGMP proxy and PIM routing?
IGMP proxy operates at the host-group level, forwarding membership reports between interfaces. PIM (Protocol Independent Multicast) is a full multicast routing protocol that builds distribution trees across multiple routers. IGMP proxy is simpler and sufficient for small networks; PIM is needed for large-scale multicast routing.

### Can udpxy handle encrypted multicast streams?
udpxy relays the raw UDP multicast stream as-is over HTTP. If the source stream is encrypted (e.g., DRM-protected IPTV), udpxy will relay the encrypted data. Decryption must happen at the client side.

### How many simultaneous streams can udpxy serve?
The limit is configurable via the `-c` flag (default varies). On a typical server with gigabit networking, udpxy can serve hundreds of simultaneous streams, each consuming 2-8 Mbps depending on video quality.

### Does igmpproxy support IGMPv3 source-specific multicast?
Yes, modern versions of igmpproxy support IGMPv3 including source-specific multicast (SSM), which allows clients to request multicast from specific source addresses only.

### Can I run mcproxy and udpxy together?
Yes, they serve different purposes. mcproxy handles IGMP/MLD signal forwarding between network segments, while udpxy converts multicast streams to HTTP for client consumption. You can run mcproxy to enable multicast routing and udpxy to serve HTTP clients on the downstream network.

### Is multicast routing safe for internet-facing networks?
Multicast traffic should never be exposed directly to the internet. Always place your IGMP proxy or multicast gateway behind a firewall and restrict multicast group access to authorized networks only. Use SSM (IGMPv3) to further limit which sources can send to each group.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IGMP Proxy Comparison: igmpproxy vs mcproxy vs udpxy (2026)",
  "description": "Compare open-source IGMP proxy and multicast-to-HTTP solutions — igmpproxy, mcproxy, and udpxy with Docker configs, installation guides, and IPTV deployment tips.",
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
