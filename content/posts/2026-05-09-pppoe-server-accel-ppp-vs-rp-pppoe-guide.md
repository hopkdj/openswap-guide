---
title: "Self-Hosted PPPoE Server: accel-ppp vs rp-pppoe vs ppp Guide"
date: "2026-05-09"
tags: ["comparison", "guide", "self-hosted", "networking", "isp", "vpn"]
draft: false
---

PPPoE (Point-to-Point Protocol over Ethernet) remains the foundation of broadband internet access worldwide. While most users encounter PPPoE as ISP customers, there are many scenarios where running your own PPPoE server makes sense — from building a small ISP to creating isolated network segments for testing. In this guide, we compare two open-source PPPoE server solutions — **accel-ppp** and **rp-pppoe** — and explore when to use each for your self-hosted infrastructure.

## What Is PPPoE and Why Run Your Own Server?

PPPoE encapsulates PPP frames inside Ethernet frames, combining the authentication and session management capabilities of PPP with the ubiquity of Ethernet. It was originally designed for DSL broadband connections but has found uses in many other networking scenarios.

Running your own PPPoE server is useful for:

- **Small ISP operations** — providing broadband internet access to subscribers with per-session authentication, accounting, and bandwidth control
- **Network isolation** — creating separate PPPoE sessions for different network segments, each with its own authentication and routing
- **Testing and development** — simulating ISP environments for application testing, CPE validation, and protocol analysis
- **Captive portal alternatives** — using PPPoE authentication instead of web-based captive portals for network access control
- **Educational labs** — teaching networking students how PPPoE works hands-on

## accel-ppp — The High-Performance PPPoE Server

**accel-ppp** is a high-performance PPPoE server designed for small to medium ISPs. Written in C with a modular architecture, it handles thousands of concurrent sessions efficiently. With over 300 stars on GitHub and active development as recently as 2026, it is the most feature-rich open-source PPPoE server available.

### Key Features

- **High performance** — handles 10,000+ concurrent sessions on commodity hardware
- **Multiple protocols** — supports PPPoE, PPTP, L2TP, and SSTP in a single daemon
- **RADIUS integration** — full RADIUS client for authentication, authorization, and accounting (AAA)
- **VLAN support** — per-session VLAN tagging for network segmentation
- **Bandwidth limiting** — built-in traffic shaping with per-session rate limits
- **IP address pools** — dynamic IP assignment from configurable pools
- **Logging and accounting** — detailed session logs with start/stop records for billing
- **IPv6 support** — dual-stack PPPoE with IPv6CP negotiation

### Installation

Build from source:

```bash
# Install dependencies
sudo apt update
sudo apt install build-essential cmake libpcre3-dev \
  libssl-dev libcrypto++-dev libnetsnmp-perl \
  liblua5.3-dev libprotobuf-c-dev protobuf-c-compiler

# Clone and build
git clone https://github.com/accel-ppp/accel-ppp.git
cd accel-ppp
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr -DKDIR=/usr/src/linux ..
make
sudo make install
```

### Configuration

The configuration file `/etc/accel-ppp.conf` uses an INI-style format:

```ini
[modules]
log_file
accel-ppp
pppoe
auth_pap
auth_chap_md5
auth_mschap_v2
ppp_ipcp
ppp_ipv6cp
session_count
radius
sigchld
net_filter
ippool
shaper_tc
log_tcpwall
chap-secrets

[core]
thread-count=4

[pppoe]
verbose=1
ac-name=openswap-pppoe
service-name=Internet
padi-filter=mac
padi-filter-negative=mac
ifname=pppoe-%n
sid-lower=1
sid-upper=10000
unique-ac=1
called-session-id=1

[auth]
verbose=1
password-file=/etc/accel-ppp/chap-secrets
chap-secrets=/etc/accel-ppp/chap-secrets

[client-ip-range]
192.168.100.0/24

[dns]
dns1=8.8.8.8
dns2=8.8.4.4

[ip-pool]
192.168.100.100-192.168.100.200
192.168.100.1

[radius]
dictionary=/usr/share/accel-ppp/radius/dictionary
nas-identifier=accel-ppp-server
nas-ip-address=10.0.0.1
server=127.0.0.1,authPort=1812,acctPort=1813,reqLimit=100,secret=testing123
dae-server=127.0.0.1:3799,testing123
verbose=1
timeout=3
max-try=3
```

### User Credentials

```
# /etc/accel-ppp/chap-secrets
# client    server    secret    IP address
user1       *         pass123   192.168.100.100
user2       *         pass456   192.168.100.101
*           *         default   192.168.100.102
```

### Docker Deployment

```dockerfile
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
  build-essential cmake libpcre3-dev libssl-dev \
  libcrypto++-dev liblua5.3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone https://github.com/accel-ppp/accel-ppp.git . && \
  mkdir build && cd build && \
  cmake -DCMAKE_INSTALL_PREFIX=/usr .. && \
  make -j$(nproc) && make install

COPY accel-ppp.conf /etc/accel-ppp.conf
COPY chap-secrets /etc/accel-ppp/chap-secrets

EXPOSE 1812/udp 1813/udp
CMD ["accel-pppd", "-d", "-c", "/etc/accel-ppp.conf"]
```

```bash
docker build -t accel-ppp-server .
docker run -d --name accel-ppp \
  --network host \
  --cap-add=NET_ADMIN \
  -v $(pwd)/accel-ppp.conf:/etc/accel-ppp.conf \
  -v $(pwd)/chap-secrets:/etc/accel-ppp/chap-secrets \
  accel-ppp-server
```

### Starting the Service

```bash
# Bring up the PPPoE interface
sudo ip link set eth0 up
sudo accel-pppd -d -c /etc/accel-ppp.conf

# Run as systemd service
sudo systemctl enable accel-ppp
sudo systemctl start accel-ppp
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Performance | Excellent | 10,000+ sessions tested |
| Protocol support | Broad | PPPoE, PPTP, L2TP, SSTP |
| RADIUS integration | Full | Complete AAA support |
| IPv6 support | Yes | Dual-stack capable |
| Bandwidth shaping | Built-in | Per-session traffic control |
| Setup complexity | High | Requires compilation and tuning |
| Documentation | Moderate | Limited beginner guides |
| Docker support | Manual | Build from source required |

## rp-pppoe — The Classic PPPoE Implementation

**rp-pppoe** (Roaring Penguin PPPoE) is one of the oldest and most widely deployed PPPoE implementations. Originally released in 1999, it provides both client and server functionality for PPPoE connections. While the upstream project is no longer actively developed, it remains available in most Linux distributions and continues to work reliably for basic PPPoE use cases.

### Key Features

- **Simplicity** — straightforward configuration with minimal dependencies
- **Client and server** — provides both pppoe-client and pppoe-server in one package
- **Wide compatibility** — works with virtually any PPPoE client
- **PAM integration** — supports system authentication for user verification
- **Low resource usage** — lightweight daemon suitable for embedded systems
- **Established track record** — decades of real-world deployment

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install ppp pppoe
```

On Alpine Linux:

```bash
apk add ppp rp-pppoe
```

### Server Configuration

The PPPoE server configuration is minimal:

```bash
# /etc/ppp/pppoe-server-options
require-chap
lcp-echo-interval 10
lcp-echo-failure 2
ms-dns 8.8.8.8
ms-dns 8.8.4.4
noipdefault
defaultroute
proxyarp
nodefaultroute
```

### Starting the PPPoE Server

```bash
# Basic server on eth0
sudo pppoe-server -I eth0 -L 10.0.0.1 -R 10.0.0.100 -N 10

# With specific options file
sudo pppoe-server -I eth0 -F /etc/ppp/pppoe-server-options

# Limit concurrent sessions
sudo pppoe-server -I eth0 -N 50 -l

# Verbose logging
sudo pppoe-server -I eth0 -V
```

Command-line options:
- `-I eth0` — interface to listen on
- `-L 10.0.0.1` — local IP address (server side)
- `-R 10.0.0.100` — starting remote IP for clients
- `-N 10` — maximum number of sessions
- `-l` — limit sessions per MAC address

### User Authentication

PPP users are configured via the standard PPP secrets file:

```
# /etc/ppp/chap-secrets
# client    server    secret    IP address
user1       pppoe-server    pass123    10.0.0.101
user2       pppoe-server    pass456    10.0.0.102
*           pppoe-server    *          *
```

### Docker Deployment

```dockerfile
FROM alpine:latest
RUN apk add --no-cache ppp rp-pppoe

COPY pppoe-server-options /etc/ppp/pppoe-server-options
COPY chap-secrets /etc/ppp/chap-secrets

EXPOSE 67
ENTRYPOINT ["pppoe-server"]
CMD ["-I", "eth0", "-L", "10.0.0.1", "-R", "10.0.0.100", "-N", "10"]
```

```bash
docker build -t rp-pppoe-server .
docker run -d --name rp-pppoe \
  --network host \
  --cap-add=NET_ADMIN \
  -v $(pwd)/pppoe-server-options:/etc/ppp/pppoe-server-options \
  -v $(pwd)/chap-secrets:/etc/ppp/chap-secrets \
  rp-pppoe-server
```

### Client Configuration

```bash
# Interactive setup
sudo pppoe-setup

# Connect
sudo pppoe-start

# Check status
sudo pppoe-status

# Disconnect
sudo pppoe-stop

# Non-interactive connection
sudo pppoe -I eth0 -u username -p password
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Setup complexity | Low | Install and run in minutes |
| Performance | Moderate | Suitable for small deployments |
| RADIUS support | No | File-based auth only |
| IPv6 support | Limited | Requires additional configuration |
| Bandwidth shaping | No | Requires external tc rules |
| Documentation | Good | Well-documented, widely used |
| Active development | No | Last major release years ago |
| Docker support | Easy | Simple Alpine-based image |

## Comparison Table: accel-ppp vs rp-pppoe

| Feature | accel-ppp | rp-pppoe |
|---------|-----------|----------|
| **Performance** | High (10K+ sessions) | Moderate (hundreds) |
| **Protocol support** | PPPoE, PPTP, L2TP, SSTP | PPPoE only |
| **RADIUS/AAA** | Full integration | No |
| **IPv6** | Yes (dual-stack) | Limited |
| **Bandwidth shaping** | Built-in | External tc required |
| **VLAN tagging** | Yes | No |
| **Session accounting** | Detailed | Basic |
| **PAM authentication** | No | Yes |
| **Active development** | Yes (2026) | No (abandoned) |
| **Configuration** | INI-style config file | Command-line + PPP options |
| **Docker deployment** | Build from source | Simple Alpine image |
| **GitHub stars** | 319 | N/A (classic) |
| **Best for** | Small ISPs, production | Testing, small deployments |

## Choosing the Right PPPoE Server

**Choose accel-ppp if** you are building a production PPPoE service that needs to scale. Its RADIUS integration, per-session bandwidth limiting, and high concurrent session capacity make it the right choice for anyone running a real PPPoE-based service — whether that is a small WISP, a campus network, or a testing lab that needs realistic ISP simulation.

**Choose rp-pppoe if** you need a quick, simple PPPoE server for testing, development, or small-scale deployments. Its minimal configuration requirements and straightforward setup make it ideal for educational environments, protocol testing, and homelab scenarios where RADIUS and bandwidth shaping are not needed.

## Why Self-Host Your PPPoE Server?

Commercial PPPoE concentrators from Cisco, Juniper, and Nokia cost thousands of dollars and require proprietary licenses. Self-hosting with open-source software on standard x86 hardware or even a Raspberry Pi gives you enterprise-grade PPPoE functionality at essentially zero software cost.

**Cost savings** are dramatic. A WISP serving 1,000 subscribers with a commercial PPPoE concentrator might spend $15,000-$50,000 on hardware and licensing. The same capacity with accel-ppp on a $500 server costs nothing in software — only hardware and bandwidth.

**Full control** over your network means you decide authentication policies, bandwidth limits, IP allocation strategies, and logging retention. There is no vendor roadmap to follow, no forced upgrades, and no proprietary lock-in.

**Customization** extends to every aspect of the service. You can integrate with your own billing system via RADIUS attributes, implement custom traffic shaping rules, and modify the source code to add features specific to your deployment. Commercial solutions rarely allow this level of control.

For network security at the perimeter, see our [pfSense vs OPNsense firewall comparison](../2026-04-21-pfsense-vs-opnsense-vs-sophos-firewall-guide-2026/).
For VPN alternatives to PPPoE, our [WireGuard vs OpenVPN vs Tailscale guide](../2026-04-20-wireguard-vs-openvpn-vs-tailscale-self-hosted-vpn-guide/) covers modern remote access options.
For DNS-based network control, check our [AdGuard Home vs Pi-hole comparison](../2026-04-15-adguard-home-vs-pi-hole-dns-filtering-guide-2026/).

## FAQ

### What is the difference between PPPoE and a VPN?

PPPoE is a Layer 2 protocol that creates point-to-point links over Ethernet, primarily used for broadband authentication and session management. A VPN (Virtual Private Network) operates at Layer 3 or higher, creating encrypted tunnels for secure remote access. PPPoE authenticates users and assigns IP addresses; VPNs encrypt traffic between endpoints. They serve different purposes but can be combined — PPPoE for access authentication, then a VPN for encrypted traffic.

### Can I use PPPoE for WiFi hotspot authentication?

Yes, PPPoE can serve as a WiFi authentication mechanism. Configure your access points to bridge WiFi clients to the PPPoE server, and users authenticate with PPP credentials. This is more robust than web-based captive portals because PPPoE provides session-level authentication with accounting records. However, it requires PPPoE client software on the user device, which may not be available on all smartphones without third-party apps.

### How many concurrent PPPoE sessions can accel-ppp handle?

In production deployments, accel-ppp has been tested with over 10,000 concurrent sessions on a single server with 4 CPU cores and 8GB RAM. The actual capacity depends on your hardware, network bandwidth, and session configuration (RADIUS lookups add latency). For most small ISPs, a single server handles 1,000-5,000 sessions comfortably.

### Does rp-pppoe support RADIUS authentication?

No, rp-pppoe does not have built-in RADIUS support. It authenticates users against the `/etc/ppp/chap-secrets` file or through PAM (Pluggable Authentication Modules). If you need RADIUS integration, you would need to use accel-ppp or set up a separate RADIUS proxy.

### How do I troubleshoot PPPoE connection failures?

Start by checking the server logs: `journalctl -u accel-ppp -f` or `tail -f /var/log/syslog | grep pppoe`. Verify the network interface is up: `ip link show eth0`. Check that the PPPoE discovery packets are reaching the server with `tcpdump -i eth0 pppoes`. On the client side, verify credentials match the server's chap-secrets file. Ensure no firewall rules are blocking PPPoE discovery (EtherType 0x8863/0x8864).

### Can I run PPPoE over VLANs?

Yes, accel-ppp supports per-session VLAN tagging. Configure the VLAN settings in the PPPoE section of accel-ppp.conf. For rp-pppoe, you can bind the PPPoE server to a VLAN interface created with `ip link add link eth0 name eth0.10 type vlan id 10`. This is useful for segmenting PPPoE traffic from other network traffic on the same physical interface.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PPPoE Server: accel-ppp vs rp-pppoe vs ppp Guide",
  "description": "Compare accel-ppp and rp-pppoe for self-hosted PPPoE server deployment. Learn configuration, Docker setup, RADIUS integration, and bandwidth shaping for ISP-grade PPPoE services.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
