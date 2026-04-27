---
title: "tcpdump vs tshark vs termshark: Self-Hosted Packet Capture Guide 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "networking", "security", "monitoring"]
draft: false
description: "Compare tcpdump, tshark, and termshark for self-hosted packet capture and network analysis. Includes Docker setups, filtering syntax, and practical use cases for server administrators."
---

When a server experiences mysterious network issues — dropped connections, intermittent timeouts, or suspicious traffic patterns — packet capture is the definitive diagnostic tool. Unlike flow-based monitoring or log analysis, packet capture gives you the raw data: every byte on the wire.

For self-hosted infrastructure, three tools dominate the packet capture landscape: **tcpdump**, **tshark**, and **termshark**. Each serves a different niche, from lightweight CLI filtering to full protocol analysis with a terminal UI. This guide compares them side by side, with practical configurations and Docker deployment examples.

For broader network visibility, see our [self-hosted network traffic analysis guide](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide-2026/) and [IDS/IPS comparison](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/).

## Why Self-Hosted Packet Capture

Cloud-based packet capture services require routing your traffic through third-party infrastructure — an unacceptable risk for production environments handling sensitive data. Self-hosted packet capture keeps everything on your own servers:

- **Complete data sovereignty** — no packets leave your network
- **Real-time analysis** — capture and filter on the live interface without API latency
- **Long-term retention** — store PCAP files on your own storage with no egress fees
- **Integration with your stack** — pipe captures directly into your IDS, log aggregation, or alerting pipeline
- **Cost control** — no per-GB or per-capture charges from cloud providers

Whether you are debugging a TCP handshake failure, investigating a potential intrusion, or profiling API latency, having a reliable packet capture tool on every server is essential.

## tcpdump: The Lightweight Classic

**tcpdump** is the original command-line packet analyzer, available on virtually every Unix-like system. Written in C, it uses [libpcap](https://www.tcpdump.org/) for packet capture and the Berkeley Packet Filter (BPF) for expression-based filtering. It has 3,161 stars on GitHub and is actively maintained (last update: April 2026).

### Key Characteristics

- **Binary size**: ~300 KB — negligible disk footprint
- **Dependencies**: libpcap only
- **Output format**: Human-readable text or raw PCAP for offline analysis
- **Learning curve**: Moderate — BPF syntax is powerful but takes practice

### Basic Usage

Capture all traffic on `eth0` and save to a file:

```bash
sudo tcpdump -i eth0 -w capture.pcap
```

Apply a filter to capture only HTTP traffic:

```bash
sudo tcpdump -i eth0 -w http_capture.pcap 'tcp port 80 or tcp port 443'
```

Capture with verbose output and DNS resolution disabled (faster):

```bash
sudo tcpdump -i eth0 -nn -v 'host 10.0.0.5 and port 8080'
```

Capture the first 100 packets of TCP SYN packets:

```bash
sudo tcpdump -i eth0 -c 100 'tcp[tcpflags] & tcp-syn != 0'
```

### Ring Buffer Mode for Continuous Capture

For production servers, use ring buffer mode to prevent disk exhaustion:

```bash
sudo tcpdump -i eth0 \
  -w /var/log/packets/capture.pcap \
  -C 100 \
  -W 10 \
  -G 3600 \
  -Z root
```

This creates 10 files of 100 MB each, rotating every hour. Old files are overwritten automatically.

### BPF Filter Quick Reference

| Filter | Description |
|--------|-------------|
| `host 192.168.1.1` | Traffic to/from specific IP |
| `net 10.0.0.0/24` | Traffic within a subnet |
| `port 443` | Traffic on specific port |
| `tcp portrange 8000-9000` | Traffic in port range |
| `src host 10.0.0.5` | Traffic from specific source |
| `dst port 53` | DNS queries going out |
| `tcp[tcpflags] & (tcp-syn\|tcp-fin) != 0` | SYN or FIN packets only |
| `icmp` | All ICMP traffic |
| `ether host aa:bb:cc:dd:ee:ff` | Specific MAC address |

## tshark: Wireshark's Terminal Powerhouse

**tshark** is the command-line version of Wireshark, the world's most widely used network protocol analyzer. The Wireshark project has 9,256 stars on GitHub and 1,562 stars on GitLab (primary repository), with active daily development.

tshark supports 3,000+ protocol dissectors — far more than tcpdump. It can decode, analyze, and export protocol fields that tcpdump only sees as raw bytes.

### Key Characteristics

- **Protocol support**: 3,000+ dissectors (HTTP/2, gRPC, TLS, SMB, Kerberos, etc.)
- **Output formats**: Text, JSON, XML, CSV, PCAP, PDML, PSML
- **Statistics**: Built-in conversation analysis, endpoint stats, protocol hierarchy
- **Decryption**: TLS key log file support for decrypting HTTPS traffic

### Basic Usage

Capture and display HTTP traffic in real-time:

```bash
sudo tshark -i eth0 -Y "http.request" -T fields \
  -e ip.src -e http.host -e http.request.uri
```

Export captured data as JSON for programmatic processing:

```bash
sudo tshark -i eth0 -c 50 -T json > capture.json
```

Generate protocol hierarchy statistics from a capture file:

```bash
tshark -r capture.pcap -q -z io,phs
```

Analyze a PCAP file for DNS queries:

```bash
tshark -r capture.pcap -Y "dns.qry.name" \
  -T fields -e dns.qry.name -e ip.src | sort | uniq -c | sort -rn
```

### TLS Decryption

Set the `SSLKEYLOGFILE` environment variable to decrypt HTTPS traffic:

```bash
export SSLKEYLOGFILE=/tmp/sslkeylog.log
sudo tshark -i eth0 -o "tls.keylog_file:/tmp/sslkeylog.log" \
  -Y "http2" -T fields -e http2.header.name -e http2.header.value
```

This requires the client application (browser, curl) to write TLS keys to the same log file.

### Statistics Commands

tshark includes powerful built-in statistics that tcpdump cannot match:

```bash
# Top talkers by IP
tshark -r capture.pcap -q -z endpoints,ip

# HTTP response code distribution
tshark -r capture.pcap -Y "http.response" \
  -q -z http,tree

# TCP conversation duration and bytes
tshark -r capture.pcap -q -z conv,tcp

# DNS query statistics
tshark -r capture.pcap -Y "dns" -q -z dns,tree
```

## termshark: TUI Experience

**termshark** brings Wireshark's graphical interface to the terminal. Built in Go, it renders tshark's output as an interactive TUI with packet lists, details panels, and byte views. It has 9,879 stars on GitHub.

### Key Characteristics

- **Interface**: Full TUI with keyboard navigation (like `htop` for packets)
- **Rendering**: Three-panel layout — packet list, protocol tree, hex/ASCII dump
- **Filtering**: Live display filters with syntax highlighting
- **Dependencies**: Requires tshark installed on the system

### Installation

```bash
# From Go binary
go install github.com/gcla/termshark/v2/cmd/termshark@latest

# On Debian/Ubuntu
sudo apt install termshark

# On Arch Linux
sudo pacman -S termshark
```

### Usage

Launch with a live interface:

```bash
sudo termshark -i eth0
```

Open an existing capture file:

```bash
termshark -r capture.pcap
```

Apply a filter from the command line:

```bash
sudo termshark -i eth0 -f "port 443"
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Enter display filter |
| `Enter` | Apply filter |
| `Tab` | Cycle between panels |
| `g` | Go to packet number |
| `j/k` | Navigate packet list |
| `q` | Quit |
| `Ctrl+S` | Search packets |

## Comparison Table

| Feature | tcpdump | tshark | termshark |
|---------|---------|--------|-----------|
| **Stars (GitHub)** | 3,161 | 9,256 (mirror) | 9,879 |
| **Last Updated** | Apr 2026 | Apr 2026 | Apr 2024 |
| **Language** | C | C | Go |
| **Binary Size** | ~300 KB | ~15 MB | ~10 MB |
| **Protocol Dissectors** | Basic (30+) | 3,000+ | 3,000+ (via tshark) |
| **Display Filter Syntax** | BPF only | Wireshark display filters | Wireshark display filters |
| **Capture Filter Syntax** | BPF | BPF | BPF |
| **JSON Export** | No | Yes | No |
| **Interactive UI** | No | No | Yes (TUI) |
| **TLS Decryption** | No | Yes | Yes (via tshark) |
| **Statistics** | Count only | 50+ built-in stats | Via tshark |
| **Ring Buffer** | Yes | Yes | No |
| **Remote Capture** | Via SSH pipe | Via SSH pipe | Via SSH pipe |
| **Best For** | Quick captures, scripts | Deep analysis, exports | Interactive investigation |

## Practical Use Cases

### Use Case 1: Debugging a Slow HTTP API Response

Use tshark to measure server-side response time:

```bash
sudo tshark -i eth0 -Y "http.response" \
  -T fields -e frame.time_relative -e http.response.code \
  -e http.time -e ip.src -e http.content_length
```

This shows response time (`http.time`) for each HTTP response, making it easy to spot slow endpoints.

### Use Case 2: Detecting Port Scanning

Use tcpdump's ring buffer to continuously monitor for SYN scans:

```bash
sudo tcpdump -i eth0 -nn -c 1000 \
  'tcp[tcpflags] & tcp-syn != 0' | \
  awk '{print $3}' | sort | uniq -c | sort -rn | head -20
```

This counts SYN packets per source IP, revealing port scanners.

### Use Case 3: Analyzing DNS Exfiltration

Use tshark to find suspiciously long DNS queries:

```bash
tshark -r capture.pcap -Y "dns.qry.name" \
  -T fields -e dns.qry.name -e frame.len | \
  awk 'length($1) > 50 {print $0}'
```

DNS queries longer than 50 characters may indicate data exfiltration via DNS tunneling. For dedicated DNS traffic analysis, see our [DNS traffic analysis guide](../2026-04-26-pktvisor-vs-dns-collector-vs-dsc-self-hosted-dns-traffic-analysis-guide-2026/).

### Use Case 4: Capturing Specific Docker Container Traffic

Capture traffic from a specific Docker container by its network namespace:

```bash
CONTAINER_ID=$(docker ps -qf "name=myapp")
PID=$(docker inspect -f '{{.State.Pid}}' $CONTAINER_ID)
sudo nsenter -t $PID -n tcpdump -i eth0 -w container_capture.pcap
```

## Docker Deployment

### tcpdump Container

Run tcpdump in a privileged container with host network access:

```yaml
version: "3.8"
services:
  tcpdump:
    image: nicolaka/netshoot:latest
    network_mode: host
    pid: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    volumes:
      - /var/log/packets:/captures
    command: >
      tcpdump -i eth0 -w /captures/$(hostname)-$(date +%Y%m%d).pcap
      -C 100 -W 10 -G 3600 -Z root
    restart: unless-stopped
```

### tshark Container

Run tshark with TLS key log support:

```yaml
version: "3.8"
services:
  tshark:
    image: wireshark/tshark:latest
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    environment:
      - SSLKEYLOGFILE=/captures/sslkeylog.log
    volumes:
      - /var/log/packets:/captures
    command: >
      tshark -i eth0 -Y "http or tls"
      -w /captures/tshark_$(date +%Y%m%d).pcap
      -o tls.keylog_file:/captures/sslkeylog.log
    restart: unless-stopped
```

### termshark Container

For interactive TUI access:

```yaml
version: "3.8"
services:
  termshark:
    image: ghcr.io/gcla/termshark:latest
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    stdin_open: true
    tty: true
    command: termshark -i eth0
```

Run with: `docker compose run --rm termshark`

## Choosing the Right Tool

The best choice depends on your workflow:

**Use tcpdump when:**
- You need the smallest possible footprint (containers, embedded systems)
- You are writing automated scripts or cron-based capture jobs
- You only need basic BPF filtering and PCAP output
- Disk space is limited

**Use tshark when:**
- You need deep protocol analysis (HTTP/2, gRPC, TLS details)
- You need to export data in structured formats (JSON, CSV)
- You need built-in statistics (endpoints, conversations, protocol hierarchy)
- You need TLS decryption capabilities

**Use termshark when:**
- You are investigating packets interactively on a remote server
- You want Wireshark's three-panel view without a GUI
- You need to apply complex display filters on the fly
- You are troubleshooting with a keyboard-only terminal session

In practice, most production setups use all three: tcpdump for automated background capture, tshark for programmatic analysis and export, and termshark for interactive debugging sessions.

## FAQ

### What is the difference between capture filters and display filters?

Capture filters (BPF syntax) determine which packets are saved to disk. They run at the kernel level and reduce CPU and storage overhead. Display filters (Wireshark syntax) are applied after capture and can reference decoded protocol fields. tcpdump only supports capture filters, while tshark supports both. Use capture filters for production long-term capture to minimize disk usage.

### Can I use these tools on a production server without impacting performance?

Yes, with proper configuration. tcpdump with BPF filters has near-zero overhead — the kernel drops unwanted packets before they reach user space. tshark has higher overhead when displaying decoded protocols, but writing raw PCAP output (`-w`) is efficient. For continuous production capture, use tcpdump ring buffer mode (`-C`, `-W`) and analyze PCAP files offline with tshark.

### How do I capture traffic from a Docker container?

Use `docker exec` to run tcpdump inside the container's network namespace: `docker exec <container> tcpdump -i eth0 -w /tmp/capture.pcap`. Alternatively, use `nsenter` to access the container's network namespace from the host. Both methods require the container to run with `CAP_NET_RAW` capability.

### Can these tools decrypt HTTPS/TLS traffic?

tshark can decrypt TLS traffic if you provide the SSL key log file via `-o tls.keylog_file`. The client application (browser or curl) must be configured with `SSLKEYLOGFILE` environment variable to write the session keys. tcpdump and termshark cannot decrypt TLS directly — termshark relies on tshark's decryption capabilities.

### How do I capture on a remote server without installing tools?

Use SSH piping: `ssh user@remote 'sudo tcpdump -i eth0 -w - port 80' > local_capture.pcap`. This streams the PCAP data over SSH to your local machine, where you can analyze it with Wireshark or tshark. No capture files are written to the remote server's disk.

### What file format should I save captures in?

PCAP (`.pcap`) is the universal format, readable by all packet analysis tools. PCAPNG (`.pcapng`) supports additional metadata like interface names and comments but is not supported by older versions of tcpdump. For long-term storage, standard PCAP is recommended for maximum compatibility.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "tcpdump vs tshark vs termshark: Self-Hosted Packet Capture Guide 2026",
  "description": "Compare tcpdump, tshark, and termshark for self-hosted packet capture and network analysis. Includes Docker setups, filtering syntax, and practical use cases for server administrators.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
