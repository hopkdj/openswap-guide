---
title: "Self-Hosted Network Flow Exporters: softflowd vs fprobe vs pmacct"
date: "2026-06-20"
tags: ["network-monitoring", "flow-exporter", "netflow", "sflow", "network-analysis"]
draft: false
---

Network flow exporters are essential tools for traffic analysis, capacity planning, and security monitoring. They capture packet metadata and export standardized flow records (NetFlow, IPFIX, sFlow) to collectors for analysis. In this guide, we compare three leading open-source flow exporters: **softflowd**, **fprobe**, and **pmacct**.

## What Are Network Flow Exporters?

Network flow exporters passively monitor traffic on network interfaces and generate flow records summarizing communication patterns. Instead of storing every packet, they aggregate traffic into flows defined by shared attributes: source/destination IP, ports, protocol, and timestamps. This approach provides network visibility with minimal storage overhead.

Flow exporters support various protocols:
- **NetFlow v5/v9**: Cisco's original flow export protocol
- **IPFIX (RFC 7011)**: IETF standard based on NetFlow v9
- **sFlow**: Packet sampling protocol for high-speed networks
- **NetStream**: Huawei's flow export protocol

The three tools we compare take different approaches: softflowd focuses on simplicity and accuracy, fprobe provides nfnetlink-based packet capture, and pmacct offers a comprehensive multi-purpose monitoring suite.

## Feature Comparison

| Feature | softflowd | fprobe | pmacct |
|---------|-----------|--------|--------|
| Flow Protocol | NetFlow v5/v9, IPFIX | NetFlow v5/v9, IPFIX | NetFlow v5/v9, IPFIX, sFlow |
| Packet Capture | libpcap | nfnetlink | libpcap, Netlink, nDPI |
| Active Flows Tracking | Yes | Yes | Yes |
| Template-Based Export | IPFIX only | IPFIX only | Yes |
| Flow Aggregation | Basic | Basic | Advanced |
| Database Integration | No | No | Yes (MySQL, PostgreSQL, SQLite) |
| BGP Support | No | No | Yes (BGP, BMP) |
| License | BSD | GPLv2 | GPLv3 |
| GitHub Stars | ~209 | ~193 | ~1,211 |
| Last Updated | Active | Active | Active |

## softflowd: Simple and Reliable

softflowd is a lightweight flow export daemon that mirrors traffic from a network interface or pcap file and exports NetFlow v5/v9 or IPFIX records. It is designed for simplicity, with a single configuration file and minimal resource overhead.

**Key features:**
- Supports NetFlow v5, v9, and IPFIX export
- Works with any libpcap-compatible interface
- Configurable active/inactive flow timeouts
- Low memory footprint suitable for embedded devices
- Can read from pcap files for offline analysis

### Installation

```bash
# Debian/Ubuntu
sudo apt install softflowd

# Build from source
git clone https://github.com/irino/softflowd.git
cd softflowd
./autogen.sh
./configure
make && sudo make install
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  softflowd:
    image: alpine:latest
    container_name: softflowd
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    command: >
      sh -c "apk add softflowd &&
      softflowd -i eth0
        -n 192.168.1.100:2055
        -P udp
        -v 10
        -t 'maxlife=3600'"
    restart: unless-stopped
```

### Configuration

```bash
# Export to collector at 192.168.1.100:2055 using IPFIX
softflowd -i eth0 -n 192.168.1.100:2055 -P udp -v 10 \
  -t 'maxlife=3600' \
  -t 'refresh=300' \
  -t 'icmp=60' \
  -t 'tcp=3600' \
  -t 'udp=60'
```

## fprobe: nfnetlink-Based Flow Collection

fprobe captures packets using the Linux nfnetlink subsystem and exports NetFlow/IPFIX records. It integrates with the kernel's netfilter framework, enabling efficient packet capture without the overhead of libpcap.

**Key features:**
- Uses nfnetlink for kernel-level packet capture
- Lower CPU overhead than libpcap-based solutions
- Supports NetFlow v5/v9 and IPFIX
- Can monitor multiple interfaces simultaneously
- Integrates with iptables/nftables for selective capture

### Installation

```bash
# Build from source
git clone https://github.com/theblackturtle/fprobe.git
cd fprobe
./autogen.sh
./configure --with-nfnetlink
make && sudo make install
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  fprobe:
    build:
      context: .
      dockerfile: Dockerfile.fprobe
    container_name: fprobe
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    environment:
      - COLLECTOR_IP=192.168.1.100
      - COLLECTOR_PORT=2055
      - INTERFACE=eth0
      - FLOW_VERSION=10
    restart: unless-stopped
```

### Basic Usage

```bash
# Monitor eth0 and send IPFIX to collector
fprobe -i eth0 192.168.1.100:2055 -f "ip" -v 10

# With custom timeouts and sampling
fprobe -i eth0 192.168.1.100:2055 \
  -t 300 \
  -T 3600 \
  -s 1:1000 \
  -f "ip and not port 2055"
```

## pmacct: Comprehensive Network Monitoring

pmacct is a versatile network monitoring toolkit that goes beyond flow export. It can account for traffic via multiple methods (libpcap, Netlink, nDPI deep packet inspection), store data in databases, and export to various collectors.

**Key features:**
- Multi-purpose: accounting, aggregation, export, and storage
- Supports NetFlow v5/v9, IPFIX, sFlow export and collection
- Database backends: MySQL, PostgreSQL, SQLite, Kafka
- Deep packet inspection with nDPI integration
- BGP and BMP (BGP Monitoring Protocol) support
- Flexible plugin architecture for custom processing
- Traffic classification and policy-based accounting

### Installation

```bash
# Debian/Ubuntu
sudo apt install pmacct

# Build with nDPI and database support
git clone https://github.com/pmacct/pmacct.git
cd pmacct
autoreconf -fi
./configure --enable-nfacctd --enable-sflow --enable-ndpi \
  --with-mysql --with-pgsql
make && sudo make install
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  pmacct:
    image: ghcr.io/pmacct/pmacct:latest
    container_name: pmacct-nfacctd
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./pmacct.conf:/etc/pmacct/pmacct.conf:ro
    restart: unless-stopped
```

### Configuration (pmacct.conf)

```ini
# nfacctd - NetFlow/IPFIX collector and exporter
daemonize: true
pidfile: /var/run/nfacctd.pid

# Capture from interface
interface: eth0
pcap_filter: "ip and not port 2055"

# Database storage
plugins: mysql
sql_host: 192.168.1.50
sql_db: pmacct
sql_table: acct
sql_user: pmacct
sql_password: secure_password

# Flow export to upstream collector
nfprobe_ip: 10.0.0.100
nfprobe_port: 9995
nfprobe_version: 10
```

## Choosing the Right Flow Exporter

| Use Case | Recommended Tool |
|----------|-----------------|
| Simple NetFlow export from a single interface | softflowd |
| High-performance capture with netfilter integration | fprobe |
| Comprehensive monitoring with storage and BGP support | pmacct |
| Embedded/low-resource deployment | softflowd |
| Deep packet inspection and traffic classification | pmacct + nDPI |
| sFlow export and collection | pmacct |
| Integration with existing database infrastructure | pmacct |

### Performance Considerations

- **softflowd** uses libpcap, which copies all packets to user space. On high-speed links (>1 Gbps), consider using packet sampling or switching to fprobe.
- **fprobe** leverages nfnetlink for kernel-level capture, reducing CPU overhead. Best for dedicated monitoring appliances.
- **pmacct** offers the most flexibility but requires more configuration. Use the appropriate plugin for your workload.

### Security Best Practices

1. **Run as non-root** where possible, using only the required capabilities (`CAP_NET_RAW`, `CAP_NET_ADMIN`)
2. **Filter traffic** to exclude management traffic (SSH, monitoring collector ports)
3. **Use IPFIX with TLS** for encrypted flow export when traversing untrusted networks
4. **Rate-limit flow exports** to prevent overwhelming collectors during traffic spikes
5. **Monitor exporter health** with watchdog scripts that restart the daemon on failure

## Why Self-Host Flow Exporters?

Running your own flow exporters gives you complete control over network visibility infrastructure. Commercial flow collection services often charge per-exporter or per-Gbps, costs that grow quickly as your network expands. With open-source tools like softflowd, fprobe, and pmacct, you can deploy flow exporters across your entire network without licensing fees.

Self-hosted flow exporters also ensure your network metadata never leaves your infrastructure. Flow records contain valuable information about communication patterns, internal service dependencies, and potential security incidents. Keeping this data on-premises is essential for organizations with compliance requirements.

For bandwidth monitoring and analysis, see our [bandwidth monitoring comparison](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monitoring-guide/). For network flow analysis and visualization, check our [network flow analysis guide](../self-hosted-network-flow-analysis-pmacct-nfdump-fprobe/). If you need comprehensive network monitoring, our [Zabbix vs LibreNMS vs NetData comparison](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) covers the full monitoring stack.

## FAQ

### What is the difference between NetFlow and IPFIX?

NetFlow v5 and v9 are Cisco proprietary flow export protocols, while IPFIX (RFC 7011) is the IETF standard based on NetFlow v9. IPFIX supports extensible templates, variable-length fields, and more data types than NetFlow v9. All three tools compared here support both protocols.

### Can these tools run on high-speed links (10 Gbps+)?

For 10 Gbps+ links, consider using packet sampling (sFlow) or kernel-level capture (fprobe with nfnetlink) to reduce CPU overhead. pmacct with nDPI classification adds additional processing overhead but provides deeper traffic insights. softflowd with libpcap may struggle at line rate without sampling.

### Do these flow exporters encrypt flow data in transit?

IPFIX supports TLS transport for encrypted flow export. softflowd and fprobe both support IPFIX over TLS when configured with certificates. pmacct's nfacctd can export IPFIX with TLS. Ensure your flow collector also supports IPFIX/TLS.

### Can I use these tools for security monitoring?

Yes. Flow records can detect DDoS attacks, port scans, data exfiltration, and C2 communication patterns. Export flows to a security-focused collector like Security Onion, Elastic Security, or a custom SIEM for analysis.

### How much storage do flow records consume?

Flow records are compact compared to full packet capture. A typical enterprise network generates 1-10 GB of flow data per day, depending on traffic volume and flow timeout settings. pmacct can store flows directly in a database for long-term retention.

### What is the difference between flow export and packet capture?

Flow export aggregates packets into summarized records (flows), using significantly less storage and processing than full packet capture. A single flow represents thousands of packets with shared attributes. Use flow exporters for ongoing monitoring and packet capture (tcpdump, Wireshark) for detailed forensic analysis.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Flow Exporters: softflowd vs fprobe vs pmacct",
  "description": "Compare three leading open-source network flow exporters for NetFlow, IPFIX, and sFlow traffic analysis with Docker deployment guides.",
  "datePublished": "2026-06-20",
  "dateModified": "2026-06-20",
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
