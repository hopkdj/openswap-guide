---
title: "Self-Hosted Network Bandwidth Testing: iperf3 vs netperf vs qperf Guide 2026"
date: "2026-05-08"
tags: ["networking", "bandwidth-testing", "iperf3", "netperf", "qperf", "server-admin"]
draft: false
---

When managing server infrastructure, knowing the actual network capacity between your machines is essential. Whether you're validating a new 10 Gbps link, troubleshooting throughput between data centers, or benchmarking your SD-WAN deployment, you need reliable network bandwidth testing tools. This guide compares three of the most widely used open-source bandwidth testing utilities: **iperf3**, **netperf**, and **qperf**.

## What Are Network Bandwidth Testing Tools?

Network bandwidth testing tools measure the maximum data transfer rate between two endpoints on a network. They generate controlled traffic flows and report metrics like throughput, jitter, packet loss, and retransmissions. Unlike passive monitoring tools that observe existing traffic, these tools actively saturate the link to reveal its true capacity and identify bottlenecks.

## iperf3: The Most Popular Bandwidth Testing Tool

**iperf3** is the third generation of the iperf project, maintained by ESnet (Energy Sciences Network). It is the most widely used bandwidth testing tool in the world, pre-installed on many Linux distributions and available for Windows, macOS, and BSD.

### Key Features

- TCP and UDP bandwidth measurement
- Simultaneous bidirectional (full-duplex) testing
- JSON and XML output for automation
- Customizable buffer sizes and window scaling
- Support for SCTP and DCCP protocols
- Built-in server mode for remote testing

### Installation

```bash
# Debian/Ubuntu
sudo apt install iperf3

# RHEL/CentOS
sudo yum install iperf3

# Docker
docker run --network host --name iperf3-server esnet/iperf3:latest -s
```

### Basic Usage

Start the server on the target machine:

```bash
iperf3 -s -p 5201
```

Run the client test:

```bash
# TCP bandwidth test (10 seconds)
iperf3 -c <server-ip> -t 10 -P 4

# UDP test with specific bandwidth
iperf3 -c <server-ip> -u -b 1G -t 10

# JSON output for automation
iperf3 -c <server-ip> -J -o results.json
```

### Docker Compose

```yaml
version: "3.8"
services:
  iperf3-server:
    image: esnet/iperf3:latest
    container_name: iperf3-server
    network_mode: host
    command: ["-s", "-p", "5201"]
    restart: unless-stopped

  iperf3-client:
    image: esnet/iperf3:latest
    container_name: iperf3-client
    network_mode: host
    command: ["-c", "192.168.1.100", "-t", "30", "-P", "4", "-J"]
    depends_on:
      - iperf3-server
```

## netperf: Hewlett Packard Enterprise's Network Benchmark

**netperf** is a network performance measurement tool originally developed by Hewlett Packard Enterprise (HPE). It supports a wider range of test types than iperf3, including request/response benchmarks that simulate real application patterns rather than pure bandwidth saturation.

### Key Features

- TCP_STREAM and UDP_STREAM for bulk throughput
- TCP_RR and UDP_RR for request/response latency
- TCP_CRR (Connection Request/Response) for connection overhead
- Customizable message sizes and test durations
- Historical data collection mode
- Support for Unix domain sockets

### Installation

```bash
# Debian/Ubuntu
sudo apt install netperf

# Build from source
git clone https://github.com/HewlettPackard/netperf.git
cd netperf
./autogen.sh
./configure
make
sudo make install
```

### Basic Usage

Start the netserver daemon:

```bash
netserver -p 12865
```

Run bandwidth and latency tests:

```bash
# TCP bulk throughput (default 10 seconds)
netperf -H <server-ip> -t TCP_STREAM

# Request/response latency
netperf -H <server-ip> -t TCP_RR -l 30 -- -r 64,64

# UDP throughput
netperf -H <server-ip> -t UDP_STREAM -l 15 -- -m 1472
```

### Docker Deployment

```yaml
version: "3.8"
services:
  netserver:
    build:
      context: .
      dockerfile_inline: |
        FROM ubuntu:22.04
        RUN apt-get update && apt-get install -y netperf
        EXPOSE 12865
    container_name: netserver
    network_mode: host
    command: ["netserver", "-p", "12865"]
    restart: unless-stopped
```

## qperf: Mellanox/NVIDIA's Network Performance Tool

**qperf** (Quick Performance) was developed by Mellanox (now NVIDIA) for testing high-performance networks, particularly InfiniBand and high-speed Ethernet. While less known than iperf3, it offers unique features for RDMA (Remote Direct Memory Access) testing and detailed latency measurement.

### Key Features

- RDMA/RoCE bandwidth and latency testing
- Bidirectional bandwidth measurement in a single run
- Detailed latency distribution statistics
- Customizable message sizes from 1 byte to 4 MB
- Low-level network protocol support
- Compact output format

### Installation

```bash
# Debian/Ubuntu
sudo apt install qperf

# RHEL/CentOS
sudo yum install qperf

# Build from source
git clone https://github.com/linux-rdma/qperf.git
cd qperf
./autogen.sh
./configure
make
sudo make install
```

### Basic Usage

Start the qperf server:

```bash
qperf
```

Run tests (client connects to server on port 19765):

```bash
# TCP bandwidth
qperf <server-ip> tcp_bw

# TCP latency
qperf <server-ip> tcp_lat

# Combined bandwidth and latency
qperf <server-ip> tcp_bw tcp_lat

# RDMA bandwidth (requires InfiniBand/RoCE)
qperf <server-ip> rdma_write_bw rdma_read_bw

# Custom message sizes
qperf <server-ip> -oo msg_size:1024:1M:*2 -vu tcp_bw
```

## Comparison Table

| Feature | iperf3 | netperf | qperf |
|---------|--------|---------|-------|
| **TCP Throughput** | Yes | Yes | Yes |
| **UDP Throughput** | Yes | Yes | No |
| **Request/Response Latency** | No | Yes | Yes |
| **RDMA/RoCE Testing** | No | No | Yes |
| **Full-Duplex Testing** | Yes | No | Yes |
| **JSON Output** | Yes | No | No |
| **Bidirectional Test** | `--bidir` | No | Built-in |
| **Windows Support** | Yes | No | No |
| **Docker Image** | Official (esnet) | Community-built | Community-built |
| **Last Active** | 2026 | 2025 | 2024 |
| **GitHub Stars** | 2,600+ (esnet/iperf) | 960+ (HPE/netperf) | N/A (linux-rdma/qperf) |
| **License** | BSD-3-Clause | GPL-2.0 | BSD-2-Clause |
| **Package Availability** | All major distros | Most distros | Debian, RHEL |

## Why Self-Host Network Bandwidth Testing Tools

Network bandwidth testing is a fundamental requirement for any organization that operates its own infrastructure. Relying on cloud-based speed tests or SaaS benchmarking services has significant drawbacks that make self-hosted tools like iperf3, netperf, and qperf the superior choice for server administrators and network engineers.

First, cloud speed tests measure your connection to a third-party server, not the actual paths your production traffic takes. When you deploy iperf3 on your own machines, you test the exact network paths between your application servers, storage nodes, and database clusters. This gives you accurate, actionable data about the bottlenecks that affect your services directly.

Second, self-hosted testing enables continuous benchmarking as part of your infrastructure monitoring pipeline. You can schedule iperf3 tests every hour between all server pairs, store results in a time-series database, and alert when throughput drops below expected thresholds. This proactive approach catches degrading network links before they impact users. Cloud speed tests cannot be automated at this frequency without incurring significant API costs.

Third, self-hosted tools give you complete control over test parameters. You can test with specific buffer sizes, parallel streams, protocol variations, and duration settings that match your production workload profiles. Cloud tools offer fixed configurations that may not reflect your actual traffic patterns. For example, if your database replication uses 64 KB request/response patterns, netperf's TCP_RR test with matching parameters gives you far more relevant data than a generic bandwidth test.

For network simulation and lab environments, combining these bandwidth testing tools with virtualization platforms provides comprehensive network validation. Our [network simulation tools comparison](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) covers how to set up realistic test topologies before deploying changes to production infrastructure.

Additionally, when troubleshooting network issues, having benchmarking tools already deployed on your servers means you can start testing immediately without downloading or installing anything. This is especially critical during incident response, where every minute of downtime has a measurable cost. Tools like Toxiproxy can simulate network faults, and our [fault injection guide](../2026-04-20-toxiproxy-vs-pumba-vs-chaosmonkey-self-hosted-fault-injection-chaos-testing-guide-2026/) shows how to combine chaos engineering with bandwidth testing for resilience validation.

For server administrators managing reverse proxy deployments, understanding the bandwidth characteristics between your proxy layer and backend services is essential. Our [reverse proxy comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/) covers proxy setup, and bandwidth testing tools help you validate that the proxy isn't becoming a bottleneck.

## Choosing the Right Bandwidth Testing Tool

Select the tool that matches your testing scenario:

- **Use iperf3** when you need the simplest, most widely available tool for basic TCP/UDP throughput testing. Its JSON output, multi-platform support, and familiarity make it the default choice for most administrators.
- **Use netperf** when you need request/response latency testing that simulates application-level traffic patterns. Its TCP_RR and TCP_CRR tests are unmatched for measuring the overhead of connection establishment.
- **Use qperf** when you work with RDMA networks (InfiniBand, RoCE) or need the most detailed latency measurements. Its bidirectional test mode and latency distribution statistics provide insights that neither iperf3 nor netperf can match.

## FAQ

### What is the difference between iperf3 and iperf2?

iperf3 is a complete rewrite of iperf2 with a redesigned architecture. Key differences include: iperf3 uses a single-threaded server (vs. multi-threaded in iperf2), supports JSON output, has a cleaner codebase, and does not support multicast or DSCP testing. However, iperf3 does support SCTP and DCCP protocols. For most use cases, iperf3 is the recommended version.

### Can I run bandwidth tests over the internet?

Yes, all three tools work over the internet, but results will be affected by ISP throttling, NAT, firewalls, and routing. For accurate results, open the required ports (5201 for iperf3, 12865 for netperf, 19765 for qperf) on any firewalls between the test endpoints. Use TCP tests for reliable measurements, as UDP results can be distorted by ISP rate limiting.

### How long should a bandwidth test run?

For stable networks, 10-30 seconds is usually sufficient. For networks with variable performance (wireless, cellular, shared links), run tests for 60-120 seconds to capture fluctuations. Use the `-t` flag in iperf3 and `-l` flag in netperf to set the test duration. Run multiple tests at different times of day to understand peak vs. off-peak performance.

### What is the difference between TCP and UDP testing?

TCP testing measures the maximum reliable throughput with error correction, flow control, and congestion management. UDP testing measures raw capacity without protocol overhead, which is useful for real-time applications like VoIP and video streaming. TCP tests typically show lower throughput on lossy links because retransmissions consume bandwidth.

### How do I interpret bandwidth test results?

Results are typically reported in bits per second (bps, Kbps, Mbps, Gbps). The "retransmits" column in iperf3 output shows TCP retransmissions — high values indicate packet loss or congestion. Jitter (variation in latency) matters more for real-time applications than raw throughput. Compare results against your link's advertised capacity: consistently achieving 80-90% of rated speed is excellent for TCP, while UDP can approach 95%+ on clean links.

### Can I automate bandwidth testing with cron jobs?

Yes. All three tools support command-line execution and output to files. A common pattern is to schedule iperf3 tests every hour via cron, save JSON output to a log directory, and use a monitoring tool to analyze trends. Example cron entry: `0 * * * * iperf3 -c 10.0.0.2 -t 10 -J >> /var/log/bandwidth/$(date +\%Y\%m\%d).json`

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Bandwidth Testing: iperf3 vs netperf vs qperf Guide 2026",
  "description": "Compare iperf3, netperf, and qperf for self-hosted network bandwidth testing. Includes Docker Compose configs, usage examples, and performance comparison.",
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
