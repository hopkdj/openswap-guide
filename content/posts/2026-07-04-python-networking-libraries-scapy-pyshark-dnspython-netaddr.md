---
title: "Python Networking Libraries: Scapy vs PyShark vs dnspython vs netaddr Comparison 2026"
date: "2026-07-04"
tags: ["python", "networking", "scapy", "pyshark", "dnspython", "netaddr", "packet-analysis", "network-tools", "developer-tools"]
draft: false
---

## Introduction

Network programming in Python spans a wide range of use cases — from crafting custom packets and analyzing network captures to resolving DNS queries and manipulating IP addresses. Four libraries stand out for their specialized capabilities: **Scapy** for packet manipulation, **PyShark** for protocol analysis, **dnspython** for DNS operations, and **netaddr** for IP address management.

Rather than overlapping, these libraries complement each other by addressing different layers of the network stack. This article compares their strengths, provides practical code examples, and helps you decide which library fits your specific networking task.

## Quick Comparison Table

| Feature | Scapy | PyShark | dnspython | netaddr |
|---------|-------|---------|-----------|---------|
| **Stars** | 12,399 | 2,487 | 2,664 | 826 |
| **Last Updated** | July 2026 | March 2026 | July 2026 | July 2024 |
| **Primary Use** | Packet crafting & manipulation | Packet capture analysis | DNS protocol operations | IP address manipulation |
| **OSI Layer** | L2-L7 | L2-L7 (via tshark) | L7 (DNS) | L3 (IP) |
| **Dependencies** | Minimal (stdlib) | Wireshark/tshark | dnspython only | Minimal (stdlib) |
| **Packet Capture** | Built-in (libpcap) | Via tshark | DNS only | N/A |
| **Packet Crafting** | Full (any protocol) | No | DNS queries only | No |
| **IPv4/IPv6** | Yes | Yes | Yes | Yes |
| **License** | GPL 2.0 | MIT | ISC | BSD 3-Clause |

## Installation and Basic Usage

### Scapy: Packet Manipulation

Scapy is the Swiss Army knife of network packets. It can forge, decode, send, capture, and analyze packets at any protocol layer.

```bash
pip install scapy
```

**Crafting and sending an ICMP ping:**

```python
from scapy.all import IP, ICMP, sr1

# Create an ICMP echo request packet
packet = IP(dst="8.8.8.8") / ICMP()

# Send and receive the first response
reply = sr1(packet, timeout=2, verbose=False)

if reply:
    print(f"Reply from {reply.src}: ttl={reply.ttl} time={reply.time:.2f}ms")
else:
    print("No response received")
```

**Capturing live packets:**

```python
from scapy.all import sniff

# Capture 10 HTTP packets on port 80
def process_packet(pkt):
    if pkt.haslayer("TCP") and pkt.haslayer("Raw"):
        print(f"{pkt['IP'].src}:{pkt['TCP'].sport} -> "
              f"{pkt['IP'].dst}:{pkt['TCP'].dport}")

sniff(filter="tcp port 80", prn=process_packet, count=10)
```

**Building a custom TCP SYN scanner:**

```python
from scapy.all import IP, TCP, sr1

def syn_scan(host, port):
    syn_packet = IP(dst=host) / TCP(dport=port, flags="S")
    response = sr1(syn_packet, timeout=1, verbose=False)
    
    if response is None:
        return "filtered"
    elif response.haslayer(TCP):
        if response[TCP].flags == 0x12:  # SYN-ACK
            # Send RST to close gracefully
            sr1(IP(dst=host) / TCP(dport=port, flags="R"), 
                timeout=1, verbose=False)
            return "open"
        elif response[TCP].flags == 0x14:  # RST-ACK
            return "closed"
    return "unknown"

# Scan common ports on localhost
for port in [22, 80, 443, 3306, 8080]:
    result = syn_scan("127.0.0.1", port)
    print(f"Port {port}: {result}")
```

### PyShark: Protocol Analysis with Wireshark

PyShark wraps tshark (Wireshark's command-line tool) to provide Pythonic access to deep packet inspection. It requires Wireshark or tshark installed:

```bash
# Ubuntu/Debian
sudo apt install tshark
pip install pyshark
```

**Reading a pcap file:**

```python
import pyshark

# Open a capture file
cap = pyshark.FileCapture("capture.pcap")

# Iterate through packets with protocol details
for packet in cap:
    try:
        if "IP" in packet:
            src = packet.ip.src
            dst = packet.ip.dst
            proto = packet.transport_layer
            print(f"{src} -> {dst} [{proto}]")
    except AttributeError:
        continue

cap.close()
```

**Live capture with display filters:**

```python
import pyshark

# Live capture on eth0, filtering for DNS traffic
capture = pyshark.LiveCapture(
    interface="eth0",
    display_filter="dns"
)

print("Capturing DNS packets...")
for packet in capture.sniff_continuously(packet_count=20):
    try:
        if hasattr(packet, "dns"):
            query = packet.dns.qry_name
            print(f"DNS Query: {query}")
    except AttributeError:
        pass
```

**Extracting HTTP request details:**

```python
import pyshark

cap = pyshark.FileCapture("http_traffic.pcap", 
                           display_filter="http.request")

for packet in cap:
    if hasattr(packet, "http"):
        method = packet.http.request_method
        host = packet.http.host
        uri = packet.http.request_uri
        user_agent = packet.http.user_agent
        print(f"{method} {host}{uri} | UA: {user_agent[:50]}")

cap.close()
```

### dnspython: DNS Operations

dnspython is the standard library for DNS operations in Python. It supports all DNS record types, zone transfers, DNSSEC validation, and asynchronous resolution.

```bash
pip install dnspython
```

**Basic DNS queries:**

```python
import dns.resolver

# A record lookup
answers = dns.resolver.resolve("example.com", "A")
for rdata in answers:
    print(f"A: {rdata.address}")

# MX record lookup
mx_records = dns.resolver.resolve("gmail.com", "MX")
for mx in mx_records:
    print(f"MX: {mx.exchange} (priority: {mx.preference})")

# TXT record (SPF, DKIM, verification)
txt_records = dns.resolver.resolve("google.com", "TXT")
for txt in txt_records:
    print(f"TXT: {txt.strings}")
```

**Reverse DNS and DNSSEC validation:**

```python
import dns.resolver, dns.reversename, dns.name

# Reverse DNS lookup
addr = dns.reversename.from_address("8.8.8.8")
reverse = dns.resolver.resolve(addr, "PTR")
for rdata in reverse:
    print(f"PTR: {rdata.target}")

# DNSSEC-validated query
resolver = dns.resolver.Resolver()
resolver.use_edns(0, dns.flags.DO, 1232)
try:
    answers = resolver.resolve("cloudflare.com", "A")
    print(f"DNSSEC validated: {answers.response.flags & dns.flags.AD != 0}")
except dns.resolver.NoAnswer:
    print("No DNSSEC records")
```

**Asynchronous DNS resolution:**

```python
import asyncio
import dns.asyncresolver

async def resolve_hosts(hostnames):
    resolver = dns.asyncresolver.Resolver()
    tasks = [resolver.resolve(name, "A") for name in hostnames]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for hostname, result in zip(hostnames, results):
        if isinstance(result, Exception):
            print(f"{hostname}: ERROR - {result}")
        else:
            ips = [str(r) for r in result]
            print(f"{hostname}: {', '.join(ips)}")

asyncio.run(resolve_hosts([
    "github.com", "stackoverflow.com", 
    "python.org", "example.com"
]))
```

### netaddr: IP Address Manipulation

netaddr provides a clean Python API for working with IP addresses, networks, and MAC addresses.

```bash
pip install netaddr
```

**IP address and network operations:**

```python
from netaddr import IPAddress, IPNetwork, IPRange

# IP address arithmetic
ip = IPAddress("192.168.1.100")
print(f"IP: {ip}, Version: {ip.version}, "
      f"Is private: {ip.is_private()}, "
      f"Binary: {ip.bits()}")

# Network operations
network = IPNetwork("192.168.1.0/24")
print(f"Network: {network.network}")
print(f"Netmask: {network.netmask}")
print(f"Broadcast: {network.broadcast}")
print(f"First host: {network[1]}, Last host: {network[-2]}")
print(f"Total hosts: {network.size}")

# Subnetting
subnets = list(network.subnet(26))
for i, subnet in enumerate(subnets):
    print(f"Subnet {i}: {subnet}")
```

**IP range iteration and merging:**

```python
from netaddr import IPRange, IPSet, IPNetwork

# Create an IP range and iterate
ip_range = IPRange("10.0.0.10", "10.0.0.20")
for ip in ip_range:
    print(ip)

# Merge overlapping networks
ipset = IPSet([
    IPNetwork("10.0.0.0/24"),
    IPNetwork("10.0.1.0/24"),
    IPNetwork("10.0.0.128/25"),
])
merged = ipset.iter_cidrs()
for cidr in merged:
    print(f"Merged: {cidr}")

# Check membership and containment
net1 = IPNetwork("192.168.1.0/24")
ip_check = IPAddress("192.168.1.55")
print(f"Is {ip_check} in {net1}? {ip_check in net1}")
```

## Choosing the Right Library

### When to Use Scapy

Scapy is unmatched when you need to craft custom packets, perform network discovery, or build security tools. It is the go-to choice for:

- Network scanning and reconnaissance tools
- Custom protocol fuzzing and testing
- Packet injection and man-in-the-middle testing
- Educational exploration of network protocols
- Building proof-of-concept network tools

### When to Use PyShark

PyShark excels when you need deep protocol dissection without implementing parsing logic yourself. Leveraging Wireshark's 3,000+ protocol dissectors, it is ideal for:

- Analyzing existing packet captures (pcaps)
- Network forensics and incident response
- Protocol behavior analysis
- Building monitoring dashboards from capture data
- Automated traffic classification

### When to Use dnspython

dnspython is the definitive choice for any DNS-related Python development. Use it for:

- DNS monitoring and health checking
- Domain validation and enumeration
- Custom DNS server implementations
- DNSSEC-aware applications
- Automated DNS record management

### When to Use netaddr

netaddr is the right choice when you work extensively with IP addressing. Use it for:

- IP address validation and normalization
- Network planning and subnet calculation
- IP range merging and collision detection
- Building IP address management (IPAM) tools
- Firewall rule generation from network ranges

For other Python library comparisons, see our guides on [Python cryptography libraries](../2026-07-01-python-cryptography-libraries-pyca-pycryptodome-pynacl/) and [Python WebSocket libraries](../2026-07-01-python-websocket-libraries-websockets-autobahn-socketio/). For DNS-specific infrastructure, see our [self-hosted DNS privacy guide](../2026-04-10-self-hosted-dns-privacy-doh-dot-dnscrypt-guide/).

## FAQ

### Does Scapy require root privileges?
Yes, Scapy requires root or administrator privileges for raw socket operations such as packet crafting at L2/L3 layers and live packet capture. You can run Scapy without root for higher-level operations like reading pcap files or working with L7 protocols, but most of its powerful features require elevated permissions. On Linux, you can also use capabilities: `sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)`.

### Why does PyShark need Wireshark installed?
PyShark is a Python wrapper around tshark, Wireshark's command-line tool. It does not implement protocol parsing itself — instead, it delegates to Wireshark's 3,000+ protocol dissectors. This is actually an advantage: you get battle-tested protocol parsing without reinventing the wheel. The trade-off is the Wireshark dependency and slightly higher resource usage.

### Can dnspython perform zone transfers?
Yes, dnspython supports AXFR (full zone transfer). However, most DNS servers restrict zone transfers to authorized secondaries only. Use `dns.query.xfr()` with proper authentication if needed. For public DNS servers, zone transfers are typically blocked for security reasons — this is expected behavior, not a library limitation.

### Is netaddr still actively maintained?
netaddr's last release was in 2024, and the project has slowed down significantly. The standard library's `ipaddress` module (available since Python 3.3) covers many of netaddr's core features. For new projects requiring basic IP manipulation, consider using the stdlib `ipaddress` module. netaddr remains useful for advanced features like IP set operations, range merging, and MAC address handling that go beyond what the standard library offers.

### Can I use Scapy and PyShark together?
Yes, they work well together. A common pattern is using Scapy for packet generation and injection while using PyShark for detailed protocol analysis of the captured traffic. For example, you can use Scapy to send custom packets, capture them with tcpdump, and then analyze the resulting pcap file with PyShark to verify protocol behavior at every layer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Python Networking Libraries: Scapy vs PyShark vs dnspython vs netaddr Comparison 2026",
  "description": "Comprehensive comparison of Python networking libraries: Scapy for packet manipulation, PyShark for protocol analysis, dnspython for DNS operations, and netaddr for IP management. Includes installation, code examples, and selection guide.",
  "datePublished": "2026-07-04",
  "dateModified": "2026-07-04",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

