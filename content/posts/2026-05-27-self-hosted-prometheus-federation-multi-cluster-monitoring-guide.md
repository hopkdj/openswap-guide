---
title: "Self-Hosted Prometheus Federation: Multi-Cluster Monitoring Setups in 2026"
date: "2026-05-17"
tags: ["prometheus", "monitoring", "federation", "multi-cluster", "observability"]
draft: false
---

Monitoring at scale across multiple Kubernetes clusters or data centers requires more than a single Prometheus server. **Prometheus federation** lets you aggregate metrics from multiple sources into a central view — without shipping raw data across the wire. In this guide, we compare three production-ready federation approaches: native Prometheus federation, VictoriaMetrics vmagent, and Thanos receive federation.

## What Is Prometheus Federation?

Prometheus federation is the practice of having one Prometheus server scrape metrics from other Prometheus servers. This creates a hierarchical metric collection pipeline where "child" instances collect local metrics and "parent" instances aggregate them for global dashboards, alerting, and long-term analysis.

Federation is essential when you operate:
- Multiple Kubernetes clusters across regions
- Hybrid cloud environments (on-premises + cloud)
- Separate monitoring stacks per team or environment
- Edge computing deployments with intermittent connectivity

Without federation, each Prometheus instance operates in isolation. Cross-cluster alerting becomes impossible, and dashboards can only show data from a single scrape target.

## Comparison: Federation Approaches

| Feature | Prometheus Native Federation | VictoriaMetrics vmagent | Thanos Receive |
|---------|------------------------------|------------------------|----------------|
| **Protocol** | HTTP /federate endpoint | Prometheus remote_write | Prometheus remote_write |
| **Scalability** | Single-server bottleneck | Horizontal scaling | Horizontal scaling with hashring |
| **Storage** | Local TSDB only | Local + remote storage | Object storage (S3, GCS) |
| **Query Layer** | PromQL on aggregated data | PromQL with extensions | PromQL via Query component |
| **Retention** | Limited by disk | Configurable, long-term | Unlimited (object storage) |
| **Complexity** | Low | Medium | High |
| **Docker Support** | Official image | Official image | Official image |
| **GitHub Stars** | 63,000+ | 21,000+ | 14,000+ |
| **Best For** | Small multi-cluster setups | High-throughput ingestion | Enterprise-scale federation |

## 1. Prometheus Native Federation

Native Prometheus federation uses the `/federate` endpoint to pull select metrics from downstream Prometheus servers. This is the simplest approach but has limitations: the parent server must actively scrape each child, and query performance degrades with many federated sources.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  prometheus-child:
    image: prom/prometheus:latest
    container_name: prometheus-child
    ports:
      - "9090:9090"
    volumes:
      - ./child-prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - child-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=7d"
      - "--web.enable-lifecycle"
    restart: unless-stopped

  prometheus-parent:
    image: prom/prometheus:latest
    container_name: prometheus-parent
    ports:
      - "9091:9090"
    volumes:
      - ./parent-prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - parent-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=30d"
      - "--web.enable-lifecycle"
    depends_on:
      - prometheus-child
    restart: unless-stopped

volumes:
  child-data:
  parent-data:
```

**Child prometheus.yml** — collects local metrics:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "node"
    static_configs:
      - targets: ["node-exporter:9100"]
```

**Parent prometheus.yml** — federates from the child:
```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: "federate"
    honor_labels: true
    metrics_path: "/federate"
    params:
      "match[]":
        - '{__name__=~"job:.*"}'
        - '{__name__=~"cluster:.*"}'
    static_configs:
      - targets: ["prometheus-child:9090"]
```

The `match[]` parameter uses PromQL to select which metrics to federate. Using label-based selectors (like `job:.*`) is more efficient than scraping everything. The `honor_labels: true` directive prevents label conflicts between parent and child.

## 2. VictoriaMetrics Federation via vmagent

VictoriaMetrics offers a high-performance alternative using `vmagent` for metric collection and `remote_write` for forwarding. This approach pushes metrics rather than pulling them, which is more resilient to network partitions and reduces the parent server's scrape overhead.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  vmagent:
    image: victoriametrics/vmagent:latest
    container_name: vmagent
    ports:
      - "8429:8429"
    volumes:
      - ./vmagent.yml:/etc/vmagent/vmagent.yml:ro
      - vmagent-data:/vmagent-data
    command:
      - "--promscrape.config=/etc/vmagent/vmagent.yml"
      - "--remoteWrite.url=http://victoriametrics:8428/api/v1/write"
      - "--remoteWrite.tmpDataPath=/vmagent-data"
    restart: unless-stopped

  victoriametrics:
    image: victoriametrics/victoria-metrics:latest
    container_name: victoriametrics
    ports:
      - "8428:8428"
    volumes:
      - vm-data:/storage
    command:
      - "--storageDataPath=/storage"
      - "--retentionPeriod=90d"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "admin"
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - victoriametrics
    restart: unless-stopped

volumes:
  vmagent-data:
  vm-data:
  grafana-data:
```

**vmagent scrape config** (`vmagent.yml`):
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "kubernetes-nodes"
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
```

VictoriaMetrics stores data in a custom columnar format that achieves 10x better compression than Prometheus TSDB. The `remoteWrite.tmpDataPath` provides a disk buffer — if the VictoriaMetrics server goes down, vmagent queues metrics locally and replays them on recovery.

## 3. Thanos Receive Federation

Thanos provides enterprise-scale federation with a `receive` component that ingests metrics via `remote_write`, stores them locally, and optionally uploads to object storage. The Thanos Query component then provides a unified PromQL interface across all ingested data.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  thanos-receive:
    image: quay.io/thanos/thanos:latest
    container_name: thanos-receive
    ports:
      - "19291:19291"
      - "10901:10901"
    volumes:
      - ./thanos-receive.yml:/etc/thanos/receive.yml:ro
      - receive-data:/data
    command:
      - "receive"
      - "--tsdb.path=/data"
      - "--grpc-address=0.0.0.0:19291"
      - "--http-address=0.0.0.0:10901"
      - "--remote-write.address=0.0.0.0:19291"
      - "--label=receive_replica=R1"
      - "--label=receive_cluster=eu-west"
      - "--tsdb.retention=15d"
    restart: unless-stopped

  thanos-query:
    image: quay.io/thanos/thanos:latest
    container_name: thanos-query
    ports:
      - "10902:10902"
    command:
      - "query"
      - "--grpc-address=0.0.0.0:10902"
      - "--http-address=0.0.0.0:10902"
      - "--store=thanos-receive:19291"
    restart: unless-stopped

volumes:
  receive-data:
```

For production deployments, add the Thanos Sidecar to upload TSDB blocks to S3-compatible storage:

```yaml
  thanos-sidecar:
    image: quay.io/thanos/thanos:latest
    volumes:
      - receive-data:/data
      - ./bucket.yml:/etc/thanos/bucket.yml:ro
    command:
      - "sidecar"
      - "--tsdb.path=/data"
      - "--objstore.config-file=/etc/thanos/bucket.yml"
```

**bucket.yml** for MinIO/S3:
```yaml
type: S3
config:
  bucket: "thanos-data"
  endpoint: "minio:9000"
  access_key: "minioadmin"
  secret_key: "minioadmin"
  insecure: true
```

## Choosing the Right Federation Approach

**Use native Prometheus federation when:**
- You have 2-5 clusters and need a quick setup
- Your metric volume is manageable (< 1M samples/sec)
- You don't need long-term storage beyond 30 days
- Operational simplicity is the top priority

**Use VictoriaMetrics vmagent when:**
- You need high-throughput ingestion (> 1M samples/sec)
- Better storage compression matters for cost
- You want drop-tolerance with local buffering
- You need multi-tenant metric isolation

**Use Thanos receive when:**
- You operate 10+ clusters across multiple regions
- Unlimited retention via object storage is required
- You need horizontal scaling with hashring routing
- Global deduplication and downsampling are needed


When evaluating federation performance, monitor the parent server's scrape duration and memory usage. Prometheus federation queries execute at the child server, which can strain resources during high-cardinality queries. VictoriaMetrics and Thanos both support query federation at the storage layer — aggregating results after ingestion rather than during scraping — which distributes the computational load more evenly across your infrastructure.

## Why Self-Host Your Monitoring Federation?

Centralized monitoring is the backbone of reliable infrastructure operations. When you self-host your federation layer, you retain full control over metric data — which flows across your internal network, never touching third-party SaaS platforms. This matters for compliance regimes like SOC 2, HIPAA, and GDPR, where telemetry data may contain sensitive operational information.

Cost is another factor. Managed monitoring services charge per metric ingested, and at scale (millions of time series across dozens of clusters), these costs can exceed $5,000/month. Self-hosted federation with open-source tools runs on commodity hardware for a fraction of that cost.

Self-hosting also means you choose the retention policy, query performance characteristics, and integration points. You can federate metrics into your existing Grafana dashboards, hook them into your alerting pipeline, and export them to data lakes — all without vendor-imposed limits.

For multi-cluster Kubernetes management, see our [Kubernetes monitoring operators guide](../2026-04-30-k8s-monitoring-operators-kube-prometheus-victoriametrics-opentelemetry-guide/). If you need long-term metrics storage, check our [VictoriaMetrics vs Thanos vs Cortex comparison](../victoriametrics-vs-thanos-vs-cortex-self-hosted-metrics-storage-guide/). For alerting on federated metrics, our [Prometheus Alertmanager vs ntfy vs Gotify guide](../2026-05-07-prometheus-alertmanager-vs-ntfy-vs-gotify-self-hosted-alert-routing-guide/) covers notification routing.

## FAQ

### What is the difference between Prometheus federation and remote_write?

Federation pulls metrics from the `/federate` endpoint at scrape intervals, while remote_write pushes metrics in real-time as they are collected. Federation is simpler to set up but creates a scrape bottleneck at the parent. Remote_write (used by VictoriaMetrics and Thanos) scales better and survives network partitions with local buffering.

### Can I mix federation approaches in the same environment?

Yes. You can use native federation for a few critical clusters while pushing high-volume clusters to VictoriaMetrics via remote_write. Thanos Query can federate from both Prometheus servers and VictoriaMetrics instances using the appropriate store API.

### How does federation affect metric cardinality?

Federation itself doesn't increase cardinality — it aggregates existing metrics. However, when multiple child servers send metrics with different label sets to a parent, the total cardinality at the parent equals the sum of all children. Use consistent labeling across clusters to avoid cardinality explosion.

### What happens to metrics if the federation parent goes down?

With native federation, metrics are simply not scraped during the outage — they are lost. With VictoriaMetrics vmagent and Thanos receive, the `remote_write` protocol includes a local disk buffer that queues metrics and replays them when the parent recovers. This makes push-based federation more resilient.

### How do I avoid duplicate metrics in a federated setup?

Use `honor_labels: true` in Prometheus federation configs to preserve original labels. In Thanos, enable the `--query.replica-label` flag to deduplicate metrics from replicas of the same source. VictoriaMetrics provides the `dedup.minScrapeInterval` setting for the same purpose.

### Can I federate only specific metrics instead of everything?

Yes. Prometheus federation uses `match[]` parameters to select metrics via PromQL selectors. VictoriaMetrics uses `relabel_configs` to filter before forwarding. Thanos receive ingests everything but you can filter at query time using Thanos Query's relabeling rules.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Prometheus Federation: Multi-Cluster Monitoring Setups in 2026",
  "description": "Compare Prometheus native federation, VictoriaMetrics vmagent, and Thanos receive for multi-cluster monitoring. Docker Compose setups and configuration guides.",
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
