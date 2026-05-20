---
title: "Self-Hosted sFlow Collection & Analysis: GoFlow2 vs Akvorado vs pmacct"
date: "2026-05-20"
description: "Compare GoFlow2, Akvorado, and pmacct for self-hosted sFlow collection and network traffic analysis. Includes Docker Compose setups and configuration guides."
tags: ["sflow", "network-monitoring", "flow-collection", "network-analysis", "telemetry"]
draft: false
---

Network traffic analysis is essential for capacity planning, anomaly detection, and security monitoring. While NetFlow and IPFIX dominate enterprise environments, **sFlow** (sampled Flow) offers a lightweight alternative that works across switches, routers, and servers at line rate. This guide compares three open-source sFlow collectors you can self-host: **GoFlow2**, **Akvorado**, and **pmacct**.

## What Is sFlow?

sFlow is a multi-vendor, standards-based technology for monitoring high-speed switched and routed networks. Unlike NetFlow/IPFIX which export every flow record, sFlow uses **statistical packet sampling** — typically 1 in N packets — combined with interface counter polling. This makes it:

- **Scalable**: Handles 10/40/100 Gbps links without overwhelming the collector
- **Vendor-agnostic**: Supported by Arista, Juniper, Cisco, HPE, MikroTik, and most Linux NICs
- **Low overhead**: Sampling reduces CPU and bandwidth usage on monitored devices
- **Layer 2-7 visibility**: Captures Ethernet, IP, TCP/UDP headers and application-layer metadata

### sFlow vs NetFlow/IPFIX

| Feature | sFlow | NetFlow v9 | IPFIX |
|---------|-------|------------|-------|
| Sampling | Statistical (1 in N) | Flow-based (all flows) | Flow-based (all flows) |
| Overhead | Very low | Medium | Medium |
| Layer 2 visibility | Yes | No | Partial |
| Counter polling | Yes (interface stats) | No | No |
| Standard | RFC 3176 | Cisco proprietary | IETF RFC 7011 |
| Switch support | Broad (most vendors) | Cisco-centric | Cisco/Juniper |

## 1. GoFlow2

[GoFlow2](https://github.com/netsampler/goflow2) is a high-performance, multi-protocol flow collector written in Go. Originally created by Cloudflare, it supports sFlow v5, NetFlow v5/v9, and IPFIX.

**Key features:**
- **Multi-protocol**: sFlow, NetFlow v5/v9, IPFIX in a single binary
- **High throughput**: Processes millions of flows per second
- **Kafka/protobuf output**: Streams data to downstream consumers
- **Prometheus metrics**: Built-in metrics endpoint for monitoring
- **Kubernetes-native**: Designed for cloud-native deployments

### Docker Compose Setup

```yaml
version: "3.8"
services:
  goflow2:
    image: ghcr.io/netsampler/goflow2:latest
    container_name: goflow2
    ports:
      - "6343:6343/udp"   # sFlow
      - "2055:2055/udp"   # NetFlow/IPFIX
      - "8080:8080"       # Prometheus metrics
    command: >
      -listen :6343
      -listen.nf :2055
      -transport.file /data/flows.log
      -metrics.addr 0.0.0.0
      -metrics.port 8080
    volumes:
      - ./goflow2-data:/data
    restart: unless-stopped
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: goflow2-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: goflow2-grafana
    ports:
      - "3000:3000"
    volumes:
      - ./grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
    restart: unless-stopped
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### Installation on Ubuntu

```bash
# Install from GitHub releases
VERSION="2.2.1"
wget https://github.com/netsampler/goflow2/releases/download/v${VERSION}/goflow2-${VERSION}-linux-amd64.tar.gz
tar xzf goflow2-${VERSION}-linux-amd64.tar.gz
sudo mv goflow2 /usr/local/bin/

# Run as systemd service
sudo tee /etc/systemd/system/goflow2.service > /dev/null << 'EOF'
[Unit]
Description=GoFlow2 sFlow/NetFlow Collector
After=network.target

[Service]
ExecStart=/usr/local/bin/goflow2 -listen :6343 -transport.file /var/log/goflow2/flows.log
Restart=always
User=goflow2

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now goflow2
```

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: goflow2
    static_configs:
      - targets: ["goflow2:8080"]
```

## 2. Akvorado

[Akvorado](https://github.com/akvorado/akvorado) is a modern flow collector, enricher, and visualizer built by OVHcloud. It provides a complete pipeline from flow ingestion to dashboard visualization.

**Key features:**
- **All-in-one**: Collector, enricher, console, and clickhouse storage
- **ClickHouse backend**: Fast analytics on billions of flow records
- **GeoIP enrichment**: Automatic ASN and geolocation data
- **Built-in dashboard**: No need for separate Grafana
- **sFlow + NetFlow + IPFIX**: Multi-protocol support

### Docker Compose Setup

```yaml
version: "3.8"
services:
  akvorado:
    image: ghcr.io/akvorado/akvorado:latest
    container_name: akvorado
    ports:
      - "6343:6343/udp"    # sFlow
      - "2055:2055/udp"    # NetFlow/IPFIX
      - "8080:8080"        # Web console
    environment:
      - AKVORADO_CLICKHOUSE_URL=http://clickhouse:9000
      - AKVORADO_KAFKA_BROKERS=kafka:9092
      - AKVORADO_COLLECTOR_LISTEN=:6343
      - AKVORADO_CONSOLE_HTTP_ADDR=:8080
    depends_on:
      - clickhouse
      - kafka
    restart: unless-stopped
    networks:
      - akvorado

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: akvorado-clickhouse
    ports:
      - "8123:8123"
      - "9000:9000"
    volumes:
      - ./clickhouse-data:/var/lib/clickhouse
    restart: unless-stopped
    networks:
      - akvorado

  kafka:
    image: confluentinc/cp-kafka:latest
    container_name: akvorado-kafka
    ports:
      - "9092:9092"
    environment:
      - KAFKA_NODE_ID=1
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
    restart: unless-stopped
    networks:
      - akvorado

networks:
  akvorado:
    driver: bridge
```

### Reverse Proxy Configuration (Nginx)

```nginx
server {
    listen 80;
    server_name akvorado.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 3. pmacct

[pmacct](https://github.com/pmacct/pmacct) is a Swiss Army knife for network monitoring, supporting sFlow, NetFlow, IPFIX, BGP, BMP, and more. It has been in development since 2003 and is one of the most mature open-source flow tools.

**Key features:**
- **Multi-purpose**: Flow collection, BGP monitoring, RPKI validation
- **Multiple backends**: MySQL, PostgreSQL, MongoDB, Kafka, RabbitMQ, memory
- **BGP integration**: Correlates flow data with BGP routing information
- **Traffic accounting**: Per-host, per-protocol, per-AS aggregation
- **Active development**: Regular releases since 2003

### Docker Compose Setup

```yaml
version: "3.8"
services:
  pmacct:
    image: ghcr.io/pmacct/pmacct:latest
    container_name: pmacct
    ports:
      - "6343:6343/udp"   # sFlow
      - "2055:2055/udp"   # NetFlow/IPFIX
    volumes:
      - ./pmacct.conf:/etc/pmacct/pmacct.conf:ro
      - ./pmacct-data:/var/lib/pmacct
    restart: unless-stopped
    networks:
      - monitoring

  postgres:
    image: postgres:16
    container_name: pmacct-postgres
    environment:
      - POSTGRES_DB=pmacct
      - POSTGRES_USER=pmacct
      - POSTGRES_PASSWORD=pmacct_secret
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### pmacct Configuration (pmacct.conf)

```ini
# sFlow collector configuration
daemonize: true
pidfile: /var/run/pmacct/sfprobe.pid
plugins: memory[pg], print

# sFlow listener
sfacctd_port: 6343
sfacctd_ip: 0.0.0.0
sfacctd_timeouts: 30

# Database output
sql_host: postgres
sql_db: pmacct
sql_user: pmacct
sql_password: pmacct_secret
sql_table: acct
sql_history: 5m
sql_history_roundoff: m

# Aggregation
aggregate: src_host, dst_host, src_port, dst_port, proto, sampling
```

## Comparison Table

| Feature | GoFlow2 | Akvorado | pmacct |
|---------|---------|----------|--------|
| **sFlow v5** | Yes | Yes | Yes |
| **NetFlow v5/v9** | Yes | Yes | Yes |
| **IPFIX** | Yes | Yes | Yes |
| **BGP monitoring** | No | No | Yes |
| **Built-in dashboard** | No (Grafana) | Yes | No |
| **Storage backend** | Kafka/Protobuf | ClickHouse | SQL/NoSQL/Kafka |
| **GeoIP enrichment** | External | Built-in | External |
| **Kubernetes-ready** | Yes | Yes | Limited |
| **Active development** | Yes | Yes | Yes |
| **GitHub stars** | 771 | 2,214 | 1,211 |
| **Best for** | Cloud-native pipelines | End-to-end analytics | Multi-purpose monitoring |

## Choosing the Right sFlow Collector

- **GoFlow2** — Best for cloud-native deployments where you want to pipe flow data into Kafka and process it with downstream consumers (Elasticsearch, custom analytics). Its stateless design makes it easy to scale horizontally.
- **Akvorado** — Best for teams that want an all-in-one solution with a built-in dashboard and ClickHouse storage. The ClickHouse backend enables fast queries across billions of flow records.
- **pmacct** — Best for network engineers who need BGP correlation, RPKI validation, and the ability to aggregate flow data in multiple dimensions simultaneously. It is the most mature and feature-rich option.

## Why Self-Host sFlow Collection?

Running your own sFlow collector gives you complete visibility into network traffic without sending sensitive flow data to third-party services. Self-hosted sFlow collection enables:

- **Data sovereignty**: All flow data stays within your infrastructure, meeting compliance requirements for regulated industries
- **Cost control**: Commercial flow analytics platforms charge per exporter or per Gbps of sampled traffic. Open-source collectors eliminate these recurring costs
- **Custom analytics**: Store raw flow data in your preferred backend (ClickHouse, PostgreSQL, Elasticsearch) and build custom queries for your specific use cases
- **Real-time alerting**: Trigger alerts on traffic anomalies, DDoS patterns, or policy violations without cloud API latency
- **Historical analysis**: Retain flow data for months or years for capacity planning and forensic investigations
- **Integration with existing monitoring**: Feed flow metrics into your existing Prometheus/Grafana stack alongside server and application metrics

For network topology mapping, see our [network topology discovery guide](../2026-05-13-self-hosted-network-topology-discovery-cdpwalker-flashroute-treenet-guide/).
If you need DNS traffic analysis, check our [DNS traffic analysis comparison](../2026-04-26-pktvisor-vs-dns-collector-vs-dsc-self-hosted-dns-traff/).
For general network monitoring, our [network monitoring comparison](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) covers broader infrastructure visibility.

## FAQ

### What is the difference between sFlow and NetFlow?
sFlow uses statistical packet sampling (1 in N packets) which scales to high-speed links with minimal overhead. NetFlow tracks every flow, providing complete visibility but higher CPU and bandwidth usage on both the exporter and collector. sFlow works across vendors (Layer 2 visibility), while NetFlow is Cisco-centric.

### Which sFlow collector should I choose for a small network?
For small networks (under 10 exporters), **GoFlow2** is the simplest to deploy — it runs as a single container and outputs to a file or Prometheus. If you want built-in visualization, **Akvorado** provides a complete stack, though it requires ClickHouse and Kafka.

### Can sFlow detect DDoS attacks?
Yes. sFlow sampling captures the source/destination IPs, ports, and protocols of sampled packets, which is sufficient to identify volumetric DDoS patterns, SYN floods, and DNS amplification attacks. The key advantage is that sFlow works at line rate even on 100 Gbps links where full-flow capture would be impractical.

### How does sFlow sampling rate affect accuracy?
A sampling rate of 1:1000 (1 in 1000 packets) provides good accuracy for high-volume flows (web, video, bulk transfers) but may miss low-volume flows. For networks with many small flows, consider 1:100 or 1:200. Most switches default to 1:2048 or 1:4096, which is adequate for capacity planning but may miss ephemeral connections.

### Does sFlow work with virtual machines and containers?
Yes. The **host-sflow** daemon runs on Linux hosts and captures traffic from virtual interfaces (veth, bridge, VXLAN). This makes it ideal for monitoring Kubernetes pod-to-pod traffic, Docker container communication, and virtual machine traffic on hypervisors.

### Can I combine sFlow with SNMP monitoring?
Absolutely. sFlow provides flow-level visibility (who is talking to whom, what protocols), while SNMP provides interface-level statistics (bandwidth utilization, error rates, link status). Together they give a complete picture: SNMP tells you *that* a link is saturated, and sFlow tells you *why*.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted sFlow Collection & Analysis: GoFlow2 vs Akvorado vs pmacct",
  "description": "Compare GoFlow2, Akvorado, and pmacct for self-hosted sFlow collection and network traffic analysis. Includes Docker Compose setups and configuration guides.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
