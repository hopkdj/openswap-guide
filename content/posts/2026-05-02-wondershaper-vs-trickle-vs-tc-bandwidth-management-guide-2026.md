---
title: "Self-Hosted Network Bandwidth Management: Wondershaper vs Trickle vs Traffic Control (tc) Guide (2026)"
date: 2026-05-02
tags: ["guide", "self-hosted", "networking", "bandwidth", "qos"]
draft: false
---

Network bandwidth management controls how data flows across your network interfaces, preventing bandwidth hogging, ensuring quality of service, and optimizing traffic for critical applications. While enterprise network equipment offers hardware-level QoS, Linux-based software tools provide powerful bandwidth shaping at the server level. This guide covers the leading self-hosted bandwidth management solutions.

## Why Manage Bandwidth?

Without bandwidth management, a single application or user can consume all available network capacity, causing:

- **Latency spikes** for interactive applications (SSH, VoIP, video conferencing)
- **Packet loss** when network buffers overflow
- **Unequal resource distribution** where bulk transfers starve latency-sensitive traffic
- **SLA violations** in shared hosting or multi-tenant environments
- **Security risks** from unchecked bandwidth usage by compromised systems

## Wondershaper

[Wondershaper](https://github.com/magnific0/wondershaper) is a simple shell script that uses Linux Traffic Control (tc) to shape network traffic. It provides an easy interface for limiting download and upload bandwidth on a per-interface basis.

### Key Features

- **Simple interface** — single command to set up bandwidth limits
- **Per-interface shaping** — apply different limits to different network interfaces
- **HTB queuing discipline** — uses Linux''s Hierarchical Token Bucket for accurate shaping
- **Priority queuing** — interactive traffic (SSH, DNS) gets priority over bulk transfers
- **Lightweight** — minimal CPU and memory overhead
- **Open source** — GPLv2 licensed, actively maintained

### Installation and Usage

```bash
# Install on Debian/Ubuntu
sudo apt install wondershaper

# Install from source
git clone https://github.com/magnific0/wondershaper.git
cd wondershaper
sudo make install

# Set bandwidth limits (interface, download kbps, upload kbps)
sudo wondershaper -a eth0 -d 10000 -u 5000

# Set limits with burst sizes for better performance
sudo wondershaper -a eth0 -d 10000 -u 5000 -ds 250 -us 100

# Clear limits
sudo wondershaper -c -a eth0

# Check current status
sudo wondershaper -s -a eth0
```

### Docker Compose Setup (Systemd Service)

```yaml
# Note: Wondershaper requires root access to network interfaces
# Best deployed as a systemd service or init script
version: '3.8'

services:
  network-shaper:
    image: alpine:latest
    network_mode: host
    privileged: true
    volumes:
      - /usr/sbin/wondershaper:/usr/sbin/wondershaper:ro
      - /etc/wondershaper.conf:/etc/wondershaper.conf:ro
    command: >
      sh -c "
        wondershaper -a eth0 -d 10000 -u 5000 &&
        tail -f /dev/null
      "
    restart: unless-stopped
```

### Pros and Cons

| Feature | Details |
|---------|---------|
| Pros | Simple to use, low overhead, priority queuing built-in, actively maintained |
| Cons | Per-interface only, no application-level filtering, requires root |
| GitHub Stars | 400+ |
| Best for | Simple bandwidth caps on servers and routers |

## Trickle

[Trickle](https://github.com/mariusae/trickle) is a lightweight userspace bandwidth shaper that works by intercepting socket calls through LD_PRELOAD. It can limit bandwidth for individual applications without requiring root access or kernel modifications.

### Key Features

- **Per-application limiting** — shape traffic for specific processes
- **No root required** — works in userspace via LD_PRELOAD
- **Cooperative mode** — multiple trickle instances coordinate to share a bandwidth pool
- **TCP and UDP support** — shapes both protocol types
- **Lightweight** — minimal overhead, written in C

### Installation and Usage

```bash
# Install on Debian/Ubuntu
sudo apt install trickle

# Install from source
git clone https://github.com/mariusae/trickle.git
cd trickle
./autogen.sh && ./configure && make && sudo make install

# Limit a single application's download speed to 100 KB/s
trickle -d 100 wget https://example.com/large-file.iso

# Limit both download and upload
trickle -d 500 -u 100 rsync -avz /data/ remote:/backup/

# Cooperative mode: set a shared pool of 1000 KB/s across all trickle instances
trickled -d 1000
trickle -d 100 wget https://example.com/file1.iso &
trickle -d 100 wget https://example.com/file2.iso &

# Run a command with trickle
trickle -s -d 200 -u 50 ./my-application
```

### Docker Compose Setup

```yaml
version: '3.8'

services:
  app-with-bandwidth-limit:
    image: myapp:latest
    environment:
      - LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtrickle.so
      - TRICKLE_LIMIT_D=500
      - TRICKLE_LIMIT_U=100
    volumes:
      - /usr/lib/x86_64-linux-gnu/libtrickle.so:/usr/lib/x86_64-linux-gnu/libtrickle.so:ro
    command: >
      sh -c "
        trickle -d 500 -u 100 ./my-application
      "
    networks:
      - app-net

networks:
  app-net:
    driver: bridge
```

### Pros and Cons

| Feature | Details |
|---------|---------|
| Pros | Per-application control, no root needed, cooperative mode, works in containers |
| Cons | LD_PRELOAD compatibility issues with some apps, no queuing priorities |
| GitHub Stars | 300+ |
| Best for | Development environments, shared servers, per-application limits |

## Linux Traffic Control (tc)

The Linux [tc](https://man7.org/linux/man-pages/man8/tc.8.html) command is the most powerful bandwidth management tool available on Linux. It provides fine-grained control over packet scheduling, classification, policing, and shaping at the kernel level.

### Key Features

- **Complete control** — every aspect of packet scheduling and queuing
- **Multiple queuing disciplines** — HTB, CBQ, SFQ, FQ_Codel, Cake
- **Traffic classification** — filter by IP, port, protocol, DSCP mark, or application
- **Policing and shaping** — enforce hard limits or smooth traffic bursts
- **Built into Linux** — no additional packages needed
- **Extensible** — supports custom classifiers and actions

### Configuration Examples

```bash
# Basic rate limiting on eth0 (10 Mbps down, 5 Mbps up)
tc qdisc add dev eth0 root handle 1: htb default 10
tc class add dev eth0 parent 1: classid 1:1 htb rate 10mbit
tc class add dev eth0 parent 1: classid 1:10 htb rate 5mbit ceil 10mbit

# Prioritize SSH and DNS traffic
tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dport 22 0xffff flowid 1:1
tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dport 53 0xffff flowid 1:1

# Use FQ_Codel for better latency under load
tc qdisc add dev eth0 root fq_codel limit 10240 flows 1024 quantum 1514 target 5ms interval 100ms

# Complex setup with Cake (modern QoS)
tc qdisc replace dev eth0 root cake bandwidth 100mbit rtt 10ms besteffort

# Monitor current queuing disciplines
tc -s qdisc show dev eth0
```

### Systemd Service for Persistent Configuration

```ini
# /etc/systemd/system/bandwidth-shaper.service
[Unit]
Description=Bandwidth Shaping Configuration
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-tc.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
#!/bin/bash
# /usr/local/bin/setup-tc.sh
# Clear existing rules
tc qdisc del dev eth0 root 2>/dev/null

# Set up HTB with bandwidth classes
tc qdisc add dev eth0 root handle 1: htb default 30
tc class add dev eth0 parent 1: classid 1:1 htb rate 100mbit

# Priority class: SSH, DNS, VoIP (guaranteed 20%)
tc class add dev eth0 parent 1:1 classid 1:10 htb rate 20mbit ceil 100mbit prio 0
tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dport 22 0xffff flowid 1:10
tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dport 53 0xffff flowid 1:10
tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dport 5060 0xffff flowid 1:10

# Bulk class: HTTP, FTP (up to 60%)
tc class add dev eth0 parent 1:1 classid 1:20 htb rate 60mbit ceil 100mbit prio 1
tc filter add dev eth0 parent 1:0 protocol ip prio 2 u32 match ip dport 80 0xffff flowid 1:20
tc filter add dev eth0 parent 1:0 protocol ip prio 2 u32 match ip dport 443 0xffff flowid 1:20

# Default class: everything else (up to 20%)
tc class add dev eth0 parent 1:1 classid 1:30 htb rate 20mbit ceil 100mbit prio 2
```

### Pros and Cons

| Feature | Details |
|---------|---------|
| Pros | Most powerful option, built into Linux, application-level filtering, modern algorithms (Cake, FQ_Codel) |
| Cons | Complex syntax, steep learning curve, requires root access |
| GitHub Stars | N/A (kernel built-in) |
| Best for | Production servers, routers, complex QoS requirements |

## Comparison Table

| Feature | Wondershaper | Trickle | Traffic Control (tc) |
|---------|-------------|---------|---------------------|
| Complexity | Simple | Moderate | Advanced |
| Root required | Yes | No | Yes |
| Granularity | Per-interface | Per-application | Per-flow / per-class |
| Priority queuing | Yes (basic) | No | Yes (advanced) |
| Protocol support | TCP + UDP | TCP + UDP | All protocols |
| Kernel vs userspace | Kernel (tc wrapper) | Userspace (LD_PRELOAD) | Kernel |
| Configuration | Command line | Command line | Command line + scripts |
| Container support | Limited (host net) | Good (LD_PRELOAD) | Limited (host net) |
| Modern algorithms | HTB only | Token bucket | HTB, FQ_Codel, Cake |
| Persistence | Manual script | Per-process | Systemd service |
| Best for | Simple bandwidth caps | Per-app limits | Production QoS |

## Why Self-Host Bandwidth Management?

Managing bandwidth at the server level provides capabilities that network-level QoS often cannot achieve:

**Application-aware shaping**: Unlike router-level QoS that only sees IP addresses and ports, server-level tools like Trickle understand which application is generating traffic. You can limit backup software while giving priority to your web server — all on the same interface.

**No hardware dependency**: Software bandwidth management works on any Linux server, from a $5 VPS to a bare-metal datacenter server. You don''t need expensive managed switches or routers to implement effective QoS policies.

**Multi-tenant isolation**: In shared hosting or colocation environments, per-application or per-interface bandwidth limits prevent noisy neighbors from degrading service quality for other tenants.

**Cost savings**: Enterprise network QoS equipment costs thousands of dollars. Linux tc and its wrappers provide equivalent functionality at zero software cost, running on commodity hardware.

For related networking guides, see our [self-hosted DNS failover guide](../2026-04-24-self-hosted-dns-failover-keepalived-powerdns-haproxy-guide-2026/) for high-availability networking, and our [WireGuard management comparison](../wg-easy-vs-wireguard-ui-vs-wg-gen-web-self-hosted-wireguard-management-2026/) for secure network access.

## FAQ

### Which bandwidth management tool should I use?

For simple bandwidth caps on a server interface, use Wondershaper. For per-application limits without root access, use Trickle. For production-grade QoS with traffic prioritization, use Linux tc directly. Wondershaper is actually a wrapper around tc, so all three ultimately use the same kernel mechanism.

### Does Trickle work with all applications?

Trickle uses LD_PRELOAD to intercept socket calls, which means it only works with dynamically linked applications that use standard libc socket functions. It will not work with statically linked binaries, Go applications (which use their own network stack), or Java applications without special configuration.

### Can I use bandwidth management in Docker containers?

Wondershaper and tc require host network mode or privileged containers since they modify kernel queuing disciplines. Trickle works inside regular containers by injecting libtrickle.so via LD_PRELOAD. For production container orchestration, consider Kubernetes network policies or Cilium bandwidth management.

### What is the difference between policing and shaping?

Policing drops packets that exceed the rate limit immediately, causing TCP retransmissions. Shaping buffers excess packets and releases them at the configured rate, providing smoother traffic flow. Shaping is generally preferred for production environments as it avoids unnecessary packet loss.

### How do I make tc rules persistent across reboots?

Save your tc configuration in a script (e.g., `/usr/local/bin/setup-tc.sh`) and create a systemd service that runs it after network startup. Many distributions also provide `/etc/network/if-up.d/` hooks that execute scripts when interfaces come up.

### Is Cake better than HTB for modern networks?

Cake (Common Applications Kept Enhanced) is a newer queuing discipline that combines fair queuing, rate policing, and active queue management. It provides better latency under load than HTB and is recommended for broadband connections and home routers. HTB remains the best choice for server environments with multiple traffic classes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Bandwidth Management: Wondershaper vs Trickle vs Traffic Control (tc) Guide (2026)",
  "description": "Compare self-hosted bandwidth management tools: Wondershaper, Trickle, and Linux Traffic Control (tc). Configuration examples, Docker setups, and QoS guides.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
