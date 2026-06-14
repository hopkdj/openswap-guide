---
title: "Self-Hosted Network Flow Deduplication & Pre-Processing: pmacct vs goflow2 vs ElastiFlow"
date: "2026-06-14"
tags: ["netflow", "ipfix", "sflow", "network-monitoring", "flow-analysis", "pmacct", "traffic-analysis"]
draft: false
---

## Introduction

Network flow protocols — NetFlow, IPFIX, and sFlow — generate massive volumes of telemetry data. In a medium-sized data center, flow exporters can produce millions of flow records per minute. Sending all this raw data directly to a collector or analytics platform overwhelms storage, increases licensing costs, and buries signal in noise. Flow deduplication and pre-processing — aggregating, sampling, filtering, and enriching flow data at the edge — is the essential first step in building a scalable network observability pipeline.

This guide compares three open-source flow processing engines: **pmacct** (the veteran Swiss Army knife of flow collection), **goflow2** (high-performance sFlow/NetFlow/IPFIX collector), and **ElastiFlow** (flow analytics with built-in enrichment).

## Comparison Table

| Feature | pmacct | goflow2 | ElastiFlow |
|---------|--------|---------|------------|
| **Protocols** | NetFlow v5/v9, IPFIX, sFlow, BGP | sFlow v5, NetFlow v9, IPFIX | NetFlow v9, IPFIX, sFlow |
| **Language** | C | Go | Java |
| **Memory per 100k flows/s** | ~200 MB | ~150 MB | ~500 MB |
| **Deduplication** | Yes (nfacctd with cache) | Built-in (exporter+sequence check) | Configurable pipeline |
| **Aggregation** | Primitive-based (flexible) | Fixed fields | UI-driven pipeline builder |
| **BGP Enrichment** | Native (BMP + BGP thread) | External only | Via enrichment pipeline |
| **Output Targets** | Kafka, MySQL, PostgreSQL, files, AMQP | Kafka, stdout | Elasticsearch, Kafka |
| **Docker Support** | Official image | Official image | Official Docker Compose |
| **Web UI** | No (CLI + SQL) | No (metrics only) | Yes (Kibana dashboards) |
| **Sampling** | Yes (sFlow, NetFlow sampling) | Configurable | Pipeline-based |
| **GeoIP Enrichment** | Via pre-processing | External | Built-in MaxMind |
| **Learning Curve** | High (config syntax) | Medium (Go + YAML) | Low (GUI pipeline) |

## pmacct: The Swiss Army Knife

pmacct has been collecting and processing network flows for over 20 years. Its daemon `nfacctd` handles deduplication, aggregation, and BGP correlation natively.

### Docker Deployment

```yaml
version: "3.8"
services:
  pmacct:
    image: pmacct/pmacct:latest
    container_name: pmacct-collector
    network_mode: host
    volumes:
      - ./pmacct.conf:/etc/pmacct/pmacct.conf
      - ./pmacct-data:/var/lib/pmacct
    restart: unless-stopped
```

### pmacct Configuration for Flow Deduplication

```
! pmacct nfacctd configuration
daemonize: false
nfacctd_port: 2055
nfacctd_ip: 0.0.0.0

! Flow deduplication
nfacctd_disable_checks: false
nfacctd_time_secs: 60

! Aggregation primitives (what to group by)
aggregate[inbound]: src_host, dst_host, src_port, dst_port, proto, tos, in_iface
aggregate[outbound]: src_host, dst_host, src_port, dst_port, proto, tos, out_iface
aggregate[as_paths]: src_as, dst_as, peer_as_src, peer_as_dst

! BGP enrichment
bgp_daemon: true
bgp_daemon_ip: 127.0.0.1
bgp_daemon_port: 1790

! Output to Kafka for downstream analytics
plugins: kafka[flow_out]
kafka_topic[flow_out]: pmacct.flows
kafka_broker_host[flow_out]: kafka:9092
```

### Key pmacct Features

```bash
# Primitives for granular aggregation
# pmacct supports 80+ aggregation primitives:
# - Network: src_net, dst_net, src_mask, dst_mask
# - AS Path: src_as, dst_as, peer_as_src, peer_as_dst
# - Interface: in_iface, out_iface, iface_in, iface_out  
# - MPLS: mpls_label_top, mpls_label_bottom, mpls_vpn_rd
# - Application: class (via nDPI), app_tag
```

## goflow2: High-Performance Go Collector

goflow2 is a modern, high-performance flow collector written in Go. It's designed for scale — handling millions of flows per second with minimal resource usage.

### Docker Deployment

```yaml
version: "3.8"
services:
  goflow2:
    image: netsampler/goflow2:latest
    container_name: goflow2-collector
    ports:
      - "2055:2055/udp"   # NetFlow/IPFIX
      - "6343:6343/udp"   # sFlow
    environment:
      GFLOW2_TRANSPORT: "kafka"
      GFLOW2_KAFKA_BROKERS: "kafka:9092"
      GFLOW2_KAFKA_TOPIC: "goflow2.flows"
      GFLOW2_METRICS_ADDR: ":8080"
    restart: unless-stopped
```

### goflow2 Configuration for Sampling and Dedup

```yaml
# goflow2.yaml
flow:
  sampling-rate:
    sflow: 1000         # sFlow already sampled
    netflow: 1          # No sampling for NetFlow (already aggregated)
    ipfix: 1
  deduplication:
    enabled: true
    cache-size: 100000
    expire-seconds: 300
  enrichment:
    geoip:
      enabled: true
      database: "/data/GeoLite2-City.mmdb"

output:
  kafka:
    brokers: ["kafka:9092"]
    topic: "goflow2.flows"
    format: "json"
  prometheus:
    enabled: true
    port: 8080
```

### Performance Characteristics

goflow2 excels at raw throughput. On modern hardware, a single instance handles:
- sFlow: 500,000+ samples/second
- NetFlow v9: 300,000+ flows/second
- IPFIX: 350,000+ flows/second

The built-in deduplication cache tracks exporter IP + sequence number pairs, dropping duplicate flow records that commonly occur when multiple collectors are deployed or when network congestion causes retransmissions.

## ElastiFlow: Flow Analytics with Enrichment Pipelines

ElastiFlow takes a different approach — it's a flow analytics platform with a visual pipeline builder for pre-processing, enrichment, and deduplication.

### Docker Deployment

```yaml
version: "3.8"
services:
  elastiflow:
    image: elastiflow/flow-collector:latest
    container_name: elastiflow-collector
    ports:
      - "2055:2055/udp"
      - "4739:4739/udp"
      - "6343:6343/udp"
    environment:
      EF_OUTPUT_ELASTICSEARCH_ADDRESS: "elasticsearch:9200"
      EF_FLOW_DEDUPLICATION_ENABLED: "true"
      EF_FLOW_DEDUPLICATION_TTL: "300"
      EF_GEOIP_ENRICHMENT_ENABLED: "true"
      EF_ASN_ENRICHMENT_ENABLED: "true"
    volumes:
      - ./geoip:/usr/share/elastiflow/geoip
    restart: unless-stopped

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
    volumes:
      - ./es-data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: "http://elasticsearch:9200"
```

### ElastiFlow Pipeline Builder

ElastiFlow's visual pipeline UI lets you build processing stages:

1. **Ingest** — Receive flow data (NetFlow, IPFIX, sFlow)
2. **Dedup** — Drop duplicate flows based on hash + TTL
3. **Enrich** — GeoIP lookup, ASN mapping, device name resolution
4. **Filter** — Drop unwanted traffic (RFC 1918, broadcast, known scanners)
5. **Aggregate** — Group by dimensions (application, AS, country)
6. **Output** — Send to Elasticsearch for Kibana dashboards

## Why Self-Host Flow Pre-Processing?

Flow data volume grows linearly with network traffic — and network traffic always grows. Self-hosting your flow pre-processing pipeline at the network edge means you control what data reaches your analytics backend. Without deduplication, 15-30% of flow records in multi-collector deployments are duplicates caused by overlapping exporter coverage or TCP retransmissions — that's storage and licensing cost you're paying for nothing.

For large-scale deployments, edge pre-processing is the only scalable architecture. Sending raw flows from 500 network devices directly to a central Elasticsearch cluster will crush it. Instead, deploy pmacct or goflow2 collectors regionally to aggregate flows to 1-minute summaries with BGP enrichment, then forward only the pre-processed data to your central analytics platform. This pattern reduces flow volume by 100-1000x before it hits your expensive storage tier.

For network security teams, flow enrichment during pre-processing — adding BGP AS paths (see our [BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/)), GeoIP locations, and threat intelligence tags — means your SIEM or flow analytics platform can immediately flag anomalous traffic without post-hoc enrichment. Combine this with DNS traffic analysis (see our [DNS traffic guide](../2026-04-26-pktvisor-vs-dns-collector-vs-dsc-self-hosted-dns-traffic-analysis-guide-2026/)) for a complete network observability stack.

## Flow Enrichment During Pre-Processing

Raw flow records contain IP addresses, ports, and byte counts — useful but incomplete. Enriching flows during pre-processing adds context that transforms raw telemetry into actionable intelligence.

**GeoIP and ASN Enrichment**: Mapping source and destination IPs to geographic locations and autonomous systems is the most common enrichment. pmacct can do this natively with MaxMind GeoIP databases, while goflow2 and ElastiFlow support both MaxMind and IP2Location formats. This enrichment answers questions like "how much traffic goes to China?" or "which transit provider carries most of our European traffic?" without post-hoc lookups.

**Application Identification via nDPI**: pmacct integrates with nDPI, an open-source deep packet inspection library that identifies over 300 protocols and applications — from YouTube and Netflix to BitTorrent and SSH. By running nDPI during flow pre-processing, you can tag flows with application IDs before they reach your analytics platform. This is far more efficient than running DPI at query time.

**Threat Intelligence Correlation**: Feeding threat intelligence feeds (Emerging Threats, Abuse.ch, AlienVault OTX) into your flow pre-processor lets you tag flows involving known-malicious IPs at ingest time. ElastiFlow supports custom enrichment pipelines that can query threat intel APIs, while pmacct can use its pre_tag_map feature to match IPs against blacklists.

**BGP Path and Community Enrichment**: pmacct's unique strength is native BGP correlation — it maintains a full BGP routing table and tags each flow with the AS path, next-hop, and communities it traversed. This enables questions like "show me all flows that transited AS 3356 (Level 3)" or "which flows used our backup transit link (community 65001:200)?" that are impossible to answer with raw flow data alone.

**Flow-to-Metadata Correlation**: Advanced pipelines combine flow data with other telemetry sources. For example, correlating flow records with DNS query logs lets you replace destination IPs with domain names — turning `198.51.100.25:443` into `api.github.com:443`. Similarly, correlating with DHCP lease data maps IPs to specific devices, enabling per-device traffic accounting even in dynamic IP environments.

The most effective observability architectures perform enrichment at the edge — close to where flows are generated — and forward enriched records to centralized analytics. This distributes the processing load and ensures that every downstream system (SIEM, capacity planning, billing) works with context-rich data rather than raw IP tuples.


## FAQ

### What's the difference between flow sampling and flow deduplication?

Flow sampling reduces data volume by only collecting a subset of flows (e.g., 1 in every 1,000). Flow deduplication removes identical flow records that appear multiple times — typically because multiple exporters see the same traffic. Sampling is lossy; deduplication is lossless.

### How much does flow deduplication reduce data volume?

In typical multi-collector deployments, deduplication removes 15-30% of flow records. In environments with redundant collectors (high availability pairs), duplicate rates can reach 40-50%. With edge aggregation (1-minute summaries instead of per-flow records), total volume reduction can exceed 99%.

### Can pmacct handle both sFlow and NetFlow on the same port?

No — pmacct's nfacctd handles NetFlow/IPFIX (port 2055) and sfacctd handles sFlow (port 6343). You need separate daemons for each protocol. goflow2 can handle all protocols on their respective ports from a single binary.

### What's the performance cost of BGP enrichment in pmacct?

pmacct's BGP thread maintains a full BGP RIB in memory. For a full internet routing table (~950,000 routes), this requires approximately 1-2 GB of RAM. The enrichment lookup is a hash table operation that adds negligible latency per flow record.

### How do I choose between pmacct, goflow2, and ElastiFlow?

Choose pmacct if you need maximum flexibility (80+ aggregation primitives, native BGP, multiple output plugins) and are comfortable with its configuration syntax. Choose goflow2 if you need raw throughput with minimal resource usage and are already using Kafka. Choose ElastiFlow if you want a turnkey solution with visual dashboards and don't mind the Elasticsearch dependency.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Flow Deduplication & Pre-Processing: pmacct vs goflow2 vs ElastiFlow",
  "description": "Compare three open-source network flow processing engines: pmacct for flexible aggregation and BGP enrichment, goflow2 for high-performance sFlow/NetFlow/IPFIX collection, and ElastiFlow for visual pipeline-based flow analytics with built-in enrichment.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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
