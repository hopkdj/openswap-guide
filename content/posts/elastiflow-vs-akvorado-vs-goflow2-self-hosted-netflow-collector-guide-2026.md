---
title: "ElastiFlow vs Akvorado vs GoFlow2: Self-Hosted NetFlow Collector Guide 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "networking", "monitoring"]
draft: false
description: "Compare ElastiFlow, Akvorado, and GoFlow2 — three open-source NetFlow, sFlow, and IPFIX collectors for self-hosted network traffic analysis."
---

Network flow data is the foundation of infrastructure visibility. Whether you manage a home lab with a handful of switches or an enterprise network with dozens of routers, flow telemetry tells you who is talking to whom, which protocols dominate your bandwidth, and where anomalies hide.

Commercial flow collectors charge per exporter or per flow rate. But three mature open-source projects — ElastiFlow, Akvorado, and GoFlow2 — deliver the same capabilities without licensing costs. This guide compares them side by side and provides Docker-based deployment instructions for each.

## Why Self-Host a Flow Collector?

Flow protocols (NetFlow v5/v9, sFlow, IPFIX) are built into nearly every router, switch, and firewall from Cisco, Juniper, MikroTik, Ubiquiti, and others. Your network hardware is already generating this data — the question is where to collect and analyze it.

Self-hosting a flow collector gives you:

- **Full data ownership** — no third-party SaaS seeing your traffic patterns
- **Unlimited exporters** — commercial tools charge per device; open-source tools do not
- **Long-term retention** — store flow records for months or years for capacity planning and forensics
- **Custom dashboards** — build Grafana panels tailored to your topology
- **Zero licensing cost** — all three tools discussed here are open-source and free

For network operators who also run self-hosted monitoring stacks with tools like Prometheus, Grafana, and [network traffic analysis platforms](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide/), adding a flow collector is a natural next step in building comprehensive observability.

## What Are NetFlow, sFlow, and IPFIX?

Before comparing collectors, a brief primer on the protocols:

| Protocol | Developer | Type | Sampling | Key Strength |
|----------|-----------|------|----------|--------------|
| NetFlow v5 | Cisco | Export | Full | Simple, widely supported |
| NetFlow v9 | Cisco | Export | Full | Template-based, extensible |
| IPFIX | IETF (RFC 7011) | Export | Full | Open standard, most flexible |
| sFlow | InMon | Export | Statistical | Low overhead on high-speed links |

NetFlow v9 and IPFIX are template-based, meaning exporters describe the fields they send before transmitting data. This makes them extensible but more complex to parse. sFlow uses packet sampling — it captures every Nth packet — which is lighter on device CPU but provides statistical rather than exact measurements.

## ElastiFlow

ElastiFlow is the most established open-source flow analytics platform. Originally built on the Elastic Stack (Elasticsearch, Logstash, Kibana), the project has evolved significantly. The GitHub repository ([robcowart/elastiflow](https://github.com/robcowart/elastiflow), **2,514 stars**, last updated March 2024) now serves as documentation for the next-generation ElastiFlow Unified Flow Collector, a purpose-built collector that replaces the legacy Logstash pipeline.

### Architecture

ElastiFlow's new architecture uses a Go-based collector that receives flows, normalizes them, and ships them to an Elasticsearch or OpenSearch cluster. Kibana dashboards provide out-of-the-box visualizations for top talkers, conversations, ASNs, and threat intelligence correlation.

### Key Features

- Supports NetFlow v5/v9, sFlow, and IPFIX simultaneously
- Built-in Kibana dashboards (20+ pre-built panels)
- GeoIP enrichment for source and destination IPs
- Threat intelligence feed integration
- Application classification using port and protocol heuristics
- Option Template support for dynamic field enrichment

### Docker Deployment

ElastiFlow requires a full Elastic Stack deployment. Here is a minimal Docker Compose configuration:

```yaml
version: "3.8"

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms2g -Xmx2g
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.13.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

  elastiflow:
    image: elastiflow/flow-collector:latest
    ports:
      - "2055:2055/udp"   # NetFlow v5/v9
      - "6343:6343/udp"   # sFlow
      - "4739:4739/udp"   # IPFIX
    environment:
      - ELASTIFLOW_ES_URL=http://elasticsearch:9200
      - ELASTIFLOW_NETFLOW_IPV4_PORT=2055
      - ELASTIFLOW_SFLOW_IPV4_PORT=6343
      - ELASTIFLOW_IPFIX_IPV4_PORT=4739
    depends_on:
      - elasticsearch

volumes:
  es_data:
```

Start with `docker compose up -d`. Point your router's flow exporter to the host IP on port 2055 (NetFlow), 6343 (sFlow), or 4739 (IPFIX).

### Resource Requirements

ElastiFlow's Elastic Stack foundation is resource-intensive. Elasticsearch alone needs 2-4 GB RAM for moderate flow rates. The Kibana dashboard layer adds another 500 MB to 1 GB. For networks with more than 50 exporters, plan for 8+ GB RAM dedicated to the stack.

## Akvorado

[Akvorado](https://github.com/akvorado/akvorado) is the modern challenger — a flow collector, enricher, and visualizer built entirely in Go. With **2,179 stars** and active development (last updated April 2026), it has become one of the fastest-growing open-source networking projects.

### Architecture

Akvorado uses a multi-component architecture:

1. **Collector** — receives NetFlow, sFlow, and IPFIX data via UDP
2. **Kafka** — buffers flow records for reliable ingestion
3. **ClickHouse** — stores and indexes flow data with columnar compression
4. **Console** — a built-in web UI for querying and visualizing flows
5. **GeoIP enricher** — optional MaxMind or IPInfo integration

The ClickHouse backend is a key differentiator. Columnar storage enables sub-second queries over billions of flow records with dramatically less disk usage than Elasticsearch.

### Key Features

- Unified web console with real-time flow exploration
- ClickHouse backend for fast, compressed storage
- Kafka-based ingestion for resilience under high load
- BGP data enrichment (ASN, peer, prefix)
- GeoIP lookup for source and destination addresses
- SNMP interface name resolution
- Grafana dashboard integration via the Grafana ClickHouse plugin
- IPv6 support with dual-stack Docker networking

### Docker Deployment

Akvorado ships with an official Docker Compose file. Here is a simplified version for a single-node deployment:

```yaml
networks:
  default:
    enable_ipv6: true
    ipam:
      config:
        - subnet: 172.16.14.0/24

volumes:
  akvorado-clickhouse:
  akvorado-kafka:
  akvorado-geoip:

services:
  kafka:
    image: apache/kafka:3.9.0
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: controller,broker
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_LISTENERS: CLIENT://:9092,CONTROLLER://:9093
      KAFKA_ADVERTISED_LISTENERS: CLIENT://kafka:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: CLIENT
      KAFKA_DELETE_TOPIC_ENABLE: "true"
      KAFKA_LOG_DIRS: /var/lib/kafka/data
    volumes:
      - akvorado-kafka:/var/lib/kafka/data

  clickhouse:
    image: clickhouse/clickhouse-server:24.12
    volumes:
      - akvorado-clickhouse:/var/lib/clickhouse

  collector:
    image: ghcr.io/akvorado/akvorado:latest
    command: collector
    ports:
      - "2055:2055/udp"
      - "6343:6343/udp"
      - "4739:4739/udp"
    environment:
      KAFKA_BROKERS: kafka:9092
      KAFKA_TOPIC: akvorado-flows

  console:
    image: ghcr.io/akvorado/akvorado:latest
    command: console
    ports:
      - "8080:8080"
    environment:
      KAFKA_BROKERS: kafka:9092
      CLICKHOUSE_ADDRS: clickhouse:9000
    depends_on:
      - clickhouse
      - kafka
      - collector
```

Deploy with `docker compose up -d`. The web console is available at `http://<host>:8080`. Configure your network devices to send flow data to port 2055 (NetFlow), 6343 (sFlow), or 4739 (IPFIX).

Akvorado also provides specialized compose variants for Grafana integration, Loki log shipping, and ClickHouse cluster deployments — all available in the `docker/` directory of the repository.

### Resource Requirements

ClickHouse compresses flow data efficiently. For moderate flow rates (10K-50K flows/sec), expect 5-10 GB of storage per day. ClickHouse needs 2-4 GB RAM, Kafka needs 1-2 GB, and the collector/consumer processes use 500 MB combined. A 4-core, 8 GB RAM host is sufficient for most deployments.

## GoFlow2

[GoFlow2](https://github.com/netsampler/goflow2) takes a different approach — it is a lightweight, high-performance flow collector written in Go (**758 stars**, actively maintained). Rather than bundling storage and visualization, GoFlow2 focuses on collecting and exporting flow data to your choice of backend.

### Architecture

GoFlow2 is a collector and exporter only. It receives flow records, decodes them into a protobuf or JSON format, and forwards them to:

- **Kafka** — for downstream processing
- **File output** — JSON lines for log aggregators (GELF, Fluent Bit, Vector)
- **Prometheus** — exposes aggregated metrics on an HTTP endpoint

This minimalist design means you pair GoFlow2 with your existing observability stack. If you already run Elasticsearch, ClickHouse, or a Prometheus/Grafana setup, GoFlow2 plugs right in.

### Key Features

- Supports NetFlow v5/v9, IPFIX, and sFlow v5
- protobuf message format for efficient serialization
- JSON output for easy integration with log pipelines
- Prometheus metrics endpoint for flow rate monitoring
- Configurable decoders and transport layers
- Extremely lightweight — single binary, < 50 MB container
- No built-in storage or UI — BYO backend

### Docker Deployment

GoFlow2 ships with two Docker Compose examples: an ELK stack integration and a Kafka/ClickHouse/Grafana (KCG) stack. Here is the KCG configuration:

```yaml
services:
  kafka:
    image: apache/kafka:3.9.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_LISTENERS: CONTROLLER://:9093,BROKER://:9092
      KAFKA_ADVERTISED_LISTENERS: BROKER://kafka:9092
      KAFKA_DELETE_TOPIC_ENABLE: "true"

  goflow2:
    image: netsampler/goflow2:latest
    ports:
      - "8080:8080"        # Prometheus metrics
      - "6343:6343/udp"    # sFlow
      - "2055:2055/udp"    # NetFlow
    command:
      - -transport=kafka
      - -kafka.brokers=kafka:9092
      - -kafka.topic=flows
      - -format=json
    depends_on:
      - kafka

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_INSTALL_PLUGINS: grafana-clickhouse-datasource
    volumes:
      - grafana_data:/var/lib/grafana

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  grafana_data:
```

Start with `docker compose -f compose/kcg/docker-compose.yml up -d` from the GoFlow2 repository, or adapt the snippet above for your environment. Point your exporters to port 2055 (NetFlow) or 6343 (sFlow). The Prometheus metrics endpoint at `:8080/metrics` provides real-time flow rate statistics.

### Resource Requirements

GoFlow2 itself uses minimal resources — under 200 MB RAM and a single CPU core for moderate flow rates. The backend you choose (Kafka, Elasticsearch, ClickHouse) determines overall resource usage. This makes GoFlow2 ideal for edge deployments or environments where you already have a centralized observability platform.

## Comparison Table

| Feature | ElastiFlow | Akvorado | GoFlow2 |
|---------|-----------|----------|---------|
| **GitHub Stars** | 2,514 | 2,179 | 758 |
| **Language** | Go (collector) + Shell | Go | Go |
| **Last Updated** | Mar 2024 | Apr 2026 | Apr 2026 |
| **NetFlow v5** | Yes | Yes | Yes |
| **NetFlow v9** | Yes | Yes | Yes |
| **IPFIX** | Yes | Yes | Yes |
| **sFlow** | Yes | Yes | Yes |
| **Built-in Storage** | Elasticsearch/Opensearch | ClickHouse | None (BYO) |
| **Built-in UI** | Kibana dashboards | Web console | None |
| **GeoIP Enrichment** | Yes | Yes (MaxMind/IPInfo) | Via backend |
| **BGP Enrichment** | No | Yes | No |
| **Kafka Integration** | No | Yes (required) | Yes (optional) |
| **Prometheus Metrics** | No | Via Grafana plugin | Yes (built-in) |
| **Min RAM** | 4 GB (ES only) | 4 GB (full stack) | 200 MB (collector only) |
| **Best For** | Enterprise with Elastic Stack | Modern all-in-one | Lightweight, BYO backend |

## Which Should You Choose?

### Choose ElastiFlow if:
- You already run Elasticsearch/OpenSearch and Kibana
- You want 20+ pre-built dashboards out of the box
- You need threat intelligence correlation with flow data
- Your team is familiar with the Elastic Stack ecosystem

### Choose Akvorado if:
- You want an all-in-one solution with built-in visualization
- You value ClickHouse's compression and query speed
- You need BGP data enrichment (ASN, prefix, peer)
- You prefer modern, actively maintained Go-based tooling

### Choose GoFlow2 if:
- You want a lightweight collector that plugs into existing infrastructure
- You already run Kafka, Grafana, or a Prometheus stack
- You deploy at the edge with limited resources
- You need flexible output formats (JSON, protobuf, Kafka, file)

## Real-World Deployment Tips

### Router Configuration Examples

**Cisco IOS (NetFlow v9):**
```
interface GigabitEthernet0/0
  ip flow ingress
  ip flow egress
!
ip flow-export version 9
ip flow-export destination 192.168.1.100 2055
```

**MikroTik RouterOS (NetFlow v9):**
```
/ip traffic-flow
set enabled=yes
/ip traffic-flow target
add dst-address=192.168.1.100 dst-port=2055 version=netflow-v9
```

**Linux with nProbe (IPFIX):**
```bash
nprobe -i eth0 -n 192.168.1.100:4739 -V 10
```

### Port Reference

| Protocol | Default UDP Port |
|----------|-----------------|
| NetFlow v5 | 9996 or 2055 |
| NetFlow v9 | 2055 |
| sFlow v5 | 6343 |
| IPFIX | 4739 |

All three collectors listen on these ports by default and can be reconfigured via environment variables or command-line flags.

### Scaling Considerations

For high-flow environments (>100K flows/sec):

- **ElastiFlow**: Scale Elasticsearch horizontally with multiple data nodes. Use ILM (Index Lifecycle Management) to roll over indices and manage retention.
- **Akvorado**: Deploy ClickHouse in distributed mode with sharding. The compose file `docker-compose-clickhouse-cluster.yml` provides a ready-made cluster configuration.
- **GoFlow2**: Run multiple collector instances behind a load balancer, each writing to the same Kafka topic. Partition the topic to distribute flow processing.

For related reading on network observability, see our guide to [Zeek, Arkime, and ntopng for traffic analysis](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide/), the [network monitoring comparison of Zabbix vs LibreNMS vs Netdata](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/), and our [bandwidth monitoring tools guide](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monitoring-guide/).

## FAQ

### What is the difference between NetFlow, sFlow, and IPFIX?

NetFlow (v5/v9) is Cisco's proprietary flow export protocol, with v9 introducing template-based extensibility. IPFIX is the IETF standard based on NetFlow v9, with additional field types and broader vendor support. sFlow uses packet sampling rather than full flow records, making it lighter on device resources but providing statistical rather than exact measurements.

### Can I run multiple flow collectors simultaneously?

Yes. You can configure routers to send flow data to multiple destinations (using `ip flow-export destination` on Cisco, or multiple targets on MikroTik). This is useful for comparing collectors or migrating from one to another without losing data.

### How much storage do flow records consume?

It depends on flow rate and retention. A typical 1 Gbps link generates 5K-20K flows per second. At 200 bytes per flow record, that's 1-4 GB per day raw. ClickHouse (Akvorado) compresses this by 5-10x, while Elasticsearch (ElastiFlow) typically achieves 2-3x compression. GoFlow2's storage depends entirely on your chosen backend.

### Do I need Kafka for a flow collector?

Not always. ElastiFlow writes directly to Elasticsearch without Kafka. GoFlow2 supports direct file output or Prometheus metrics without Kafka. Akvorado, however, uses Kafka as a required buffering layer between the collector and ClickHouse — this provides resilience during ClickHouse maintenance windows and enables multiple consumers (console, Grafana, external integrations).

### Which collector supports the most protocols?

All three support NetFlow v5/v9, IPFIX, and sFlow v5. ElastiFlow additionally has deep integration with Elastic's threat intelligence features. Akvorado uniquely supports BGP data enrichment, correlating flow records with routing tables for ASN and prefix context.

### Is ElastiFlow still actively maintained?

The original GitHub repository (robcowart/elastiflow) was last updated in March 2024. However, the project has transitioned to a new commercial offering at elastiflow.com with a next-generation Unified Flow Collector. The legacy open-source version remains functional but is no longer receiving feature updates. For fully open-source alternatives, Akvorado and GoFlow2 are both actively developed with regular releases.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ElastiFlow vs Akvorado vs GoFlow2: Self-Hosted NetFlow Collector Guide 2026",
  "description": "Compare ElastiFlow, Akvorado, and GoFlow2 — three open-source NetFlow, sFlow, and IPFIX collectors for self-hosted network traffic analysis with Docker deployment guides.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
