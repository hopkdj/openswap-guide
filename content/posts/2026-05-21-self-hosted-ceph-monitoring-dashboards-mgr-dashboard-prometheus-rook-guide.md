---
title: "Self-Hosted Ceph Monitoring & Dashboards: Ceph MGR Dashboard vs Prometheus Exporter vs Rook Ceph Dashboard"
date: "2026-05-21"
tags: ["ceph", "monitoring", "storage", "prometheus", "rook", "dashboard"]
draft: false
---

Ceph is the leading open-source distributed storage platform, but managing a multi-node cluster without proper visibility is nearly impossible. In this guide, we compare the top self-hosted Ceph monitoring solutions: the built-in **Ceph MGR Dashboard**, **Prometheus exporters**, and the **Rook Ceph Dashboard** for Kubernetes deployments.

## Why Monitor Ceph?

Ceph clusters manage petabytes of data across dozens or hundreds of nodes. Without monitoring, you cannot detect:

- **OSD failures** — a single disk failure can trigger a cascade of recovery operations that impact cluster performance
- **PG state anomalies** — placement groups stuck in `degraded`, `undersized`, or `inactive` states indicate data at risk
- **Capacity exhaustion** — Ceph's CRUSH algorithm redistributes data when pools fill up; running out of space causes immediate cluster degradation
- **Network bottlenecks** — monitor and OSD network saturation causes client timeouts and slow I/O operations
- **Performance degradation** — slow OSDs, journal bottlenecks, or recovery storms all manifest as latency spikes

Proper Ceph monitoring answers critical questions: Is data safe? Is performance within SLAs? Is capacity adequate for growth?

## Ceph Monitoring Landscape

There are three primary approaches to monitoring Ceph self-hosted:

| Approach | Tool | Complexity | Best For |
|----------|------|------------|----------|
| Built-in Web UI | Ceph MGR Dashboard | Low | Small to medium clusters, quick overview |
| Prometheus Integration | ceph_exporter + Grafana | Medium | Production clusters, alerting, historical data |
| Kubernetes Operator | Rook Ceph Dashboard | Low-Medium | Kubernetes-native Ceph deployments |

## Ceph MGR Dashboard

The Ceph Manager Dashboard is a built-in web UI that ships with every Ceph cluster. It provides real-time visibility into cluster health, performance, and configuration without requiring additional infrastructure.

### Architecture

The MGR Dashboard runs as a module within the Ceph Manager daemon (`ceph-mgr`). It exposes a REST API and web interface on each active manager node.

### Docker Compose Deployment

While Ceph is typically deployed via cephadm or Rook, you can enable the MGR dashboard on any existing cluster:

```yaml
services:
  ceph-mgr-dashboard:
    image: quay.io/ceph/ceph:v18
    command: ["ceph-mgr", "-n", "mgr.$(hostname)", "--set-uid", "0"]
    network_mode: host
    volumes:
      - /etc/ceph:/etc/ceph:ro
      - /var/lib/ceph:/var/lib/ceph:ro
    environment:
      - CEPH_USE_RANDOM_NONCE=1
    restart: unless-stopped
```

Enable the dashboard module:

```bash
ceph mgr module enable dashboard
ceph dashboard create-self-signed-cert
ceph dashboard set-login-credentials admin <password>
```

### Key Features

- **Real-time health overview** — cluster status, OSD count, PG states
- **Performance metrics** — IOPS, throughput, latency graphs
- **Pool management** — create, modify, and delete storage pools
- **OSD tree visualization** — hierarchical view of OSD distribution across hosts and racks
- **RGW management** — S3-compatible object gateway administration
- **NFS-Ganesha export management** — configure NFS shares
- **iSCSI target management** — manage block storage exports

### Strengths

- **Zero external dependencies** — no Grafana, Prometheus, or additional servers needed
- **Immediate visibility** — works out of the box with `ceph mgr module enable dashboard`
- **Management capabilities** — not just monitoring; you can configure pools, OSDs, and gateways
- **REST API** — programmatic access for custom integrations

### Limitations

- **No historical data** — metrics are real-time only; no time-series storage
- **Limited alerting** — basic threshold alerts, no complex rule evaluation
- **No Grafana integration** — cannot use Grafana's rich visualization ecosystem
- **Single-tenant** — no RBAC for multiple teams

## Prometheus Exporter + Grafana

The most popular production Ceph monitoring stack combines a Prometheus exporter with Grafana dashboards. The `ceph_exporter` by DigitalOcean scrapes Ceph's admin socket and manager metrics, exposing them in Prometheus format.

### Architecture

```
Ceph Cluster → ceph_exporter → Prometheus → Grafana Dashboards
     ↓                ↓              ↓            ↓
  Admin Socket   /metrics       TSDB Store   Visualization
  MGR Metrics    endpoint       + Alerts     + Alerting
```

### Docker Compose Deployment

```yaml
services:
  ceph-exporter:
    image: digitalocean/ceph_exporter:latest
    network_mode: host
    volumes:
      - /etc/ceph:/etc/ceph:ro
      - /var/run/ceph:/var/run/ceph:ro
    command:
      - "-telemetry.addr=:9128"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    network_mode: host
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.listen-address=:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    network_mode: host
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

Prometheus configuration (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "ceph"
    static_configs:
      - targets: ["localhost:9128"]
```

### Key Grafana Dashboards

The Ceph community maintains several official Grafana dashboards:

| Dashboard ID | Purpose | Panels |
|-------------|---------|--------|
| 2842 | Ceph Cluster Overview | 40+ panels covering health, capacity, IOPS |
| 5336 | Ceph Pools | Per-pool metrics: usage, IOPS, latency |
| 5342 | Ceph OSDs | Per-OSD metrics: utilization, latency, errors |
| 5337 | Ceph MONs | Monitor node health, quorum status |
| 11118 | Ceph RGW | Object gateway metrics: requests, bandwidth |

### Strengths

- **Historical analysis** — Prometheus stores time-series data for weeks or months
- **Rich visualization** — Grafana provides customizable dashboards with 60+ panel types
- **Advanced alerting** — Prometheus Alertmanager supports complex alert rules, routing, and deduplication
- **Multi-cluster support** — monitor multiple Ceph clusters from a single Grafana instance
- **Integration ecosystem** — connect with PagerDuty, Slack, email, and webhook notifications
- **PromQL queries** — perform complex aggregations and calculations across metrics

### Limitations

- **Infrastructure overhead** — requires separate Prometheus and Grafana servers
- **Configuration complexity** — scrape targets, recording rules, and alert rules require expertise
- **Exporter dependency** — ceph_exporter must run on a node with access to the Ceph admin socket
- **Ceph 18+ changes** — newer Ceph versions include native Prometheus metrics in the MGR, reducing the need for a separate exporter

## Rook Ceph Dashboard

Rook is the Kubernetes operator for Ceph that automates deployment, scaling, and management. Its dashboard provides Ceph monitoring specifically designed for Kubernetes-native environments.

### Architecture

Rook deploys Ceph as a collection of Kubernetes resources (CRDs). The Rook Ceph Dashboard is essentially the Ceph MGR Dashboard, but integrated into the Kubernetes ecosystem with additional operator-level visibility.

### Kubernetes Deployment

```yaml
apiVersion: ceph.rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v18.2.2
  dashboard:
    enabled: true
    ssl: true
    port: 8443
    urlPrefix: /ceph-dashboard
  monitoring:
    enabled: true
    externalMgrEndpoints: []
    rulesNamespace: rook-ceph
  mgr:
    count: 2
    modules:
      - name: dashboard
        enabled: true
```

Enable the Prometheus module in Rook:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rook-ceph-mgr-config
  namespace: rook-ceph
data:
  mgr_module: |
    prometheus
```

### Key Features

- **Kubernetes-native monitoring** — Ceph health visible alongside pod, node, and service metrics
- **Operator-level visibility** — watch CephCluster, CephObjectStore, and CephFilesystem CRD states
- **Integrated Prometheus** — Rook can deploy Prometheus and Grafana as part of the Ceph cluster
- **Automated dashboard provisioning** — Grafana dashboards auto-configured when monitoring is enabled
- **Service mesh integration** — works with Istio, Linkerd for encrypted dashboard traffic
- **CRD-based management** — manage pools, OSDs, and gateways through Kubernetes YAML

### Rook Monitoring Stack

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: rook-ceph-mgr
  namespace: rook-ceph
  labels:
    team: rook
spec:
  selector:
    matchLabels:
      app: rook-ceph-mgr
  endpoints:
    - port: http-metrics
      interval: 15s
```

### Strengths

- **Kubernetes integration** — Ceph monitoring visible in the same Grafana as Kubernetes metrics
- **Automated deployment** — Rook operator handles all monitoring setup
- **CRD-based configuration** — no need to edit Ceph config files; everything through Kubernetes YAML
- **Sidecarless monitoring** — no additional pods needed; Ceph MGR exposes metrics natively
- **AlertManager integration** — PrometheusRule CRDs define alerts as Kubernetes resources

### Limitations

- **Kubernetes-only** — cannot monitor non-Kubernetes Ceph clusters
- **Rook dependency** — tied to Rook operator version and release cycle
- **Learning curve** — requires Kubernetes and Ceph expertise
- **Resource overhead** — monitoring stack adds resource requirements to the Kubernetes cluster

## Comparison Summary

| Feature | Ceph MGR Dashboard | Prometheus + Grafana | Rook Ceph Dashboard |
|---------|-------------------|---------------------|---------------------|
| **Setup complexity** | Minimal (one command) | Medium (3 services) | Medium (operator + CRDs) |
| **Historical data** | No | Yes (configurable retention) | Yes (via Prometheus) |
| **Alerting** | Basic | Advanced (Alertmanager) | Advanced (PrometheusRule CRDs) |
| **Custom dashboards** | Limited | Unlimited (Grafana) | Unlimited (Grafana) |
| **Kubernetes integration** | No | Manual (ServiceMonitor) | Native (CRDs) |
| **Multi-cluster** | No | Yes | Yes (per cluster) |
| **REST API** | Yes | Prometheus API | Kubernetes API |
| **External dependencies** | None | Prometheus + Grafana | Rook operator + Prometheus |
| **Best for** | Quick overview, small clusters | Production, SRE teams | Kubernetes-native teams |

## Choosing the Right Ceph Monitoring Solution

**Use Ceph MGR Dashboard when:**
- You need immediate visibility with zero additional infrastructure
- Your cluster is small (<50 OSDs) and doesn't require historical analysis
- You want built-in management capabilities (pool creation, OSD management)

**Use Prometheus + Grafana when:**
- You need historical performance analysis and capacity planning
- Your team requires advanced alerting with multiple notification channels
- You monitor multiple Ceph clusters alongside other infrastructure
- You need custom Grafana dashboards tailored to your SLOs

**Use Rook Ceph Dashboard when:**
- Ceph runs on Kubernetes and you want unified monitoring
- Your team manages infrastructure through Kubernetes CRDs
- You want automated dashboard and alert provisioning
- You need Ceph health visible alongside pod and node metrics

## Why Self-Host Ceph Monitoring?

Running your own Ceph monitoring infrastructure provides complete control over data retention, alerting rules, and dashboard customization. Cloud-based monitoring services cannot match the depth of Ceph-specific metrics available through the admin socket and MGR daemon. Self-hosted monitoring also keeps sensitive cluster topology and performance data within your infrastructure, which is critical for compliance in healthcare, finance, and government environments.

For teams managing Kubernetes storage, our [Rook vs Longhorn vs OpenEBS storage comparison](../rook-vs-longhorn-vs-openebs-self-hosted-kubernetes-storage-guide-2026/) covers the broader storage orchestration landscape. If you're evaluating Ceph management tools, our [Ceph management dashboard comparison](../2026-05-16-self-hosted-ceph-management-dashboard-rook-cephadm-guide/) explores administrative interfaces beyond monitoring.

## FAQ

### What is the best way to monitor a Ceph cluster?

For production environments, Prometheus + Grafana is the most widely adopted approach. The `ceph_exporter` exposes over 200 metrics covering OSD health, PG states, pool utilization, and network throughput. Grafana dashboards (especially ID 2842) provide comprehensive cluster visibility with configurable alerting through Alertmanager.

### Does Ceph have a built-in monitoring dashboard?

Yes, the Ceph Manager Dashboard is included with every Ceph installation. Enable it with `ceph mgr module enable dashboard`. It provides real-time cluster health, performance metrics, pool management, and OSD tree visualization. However, it does not store historical data or support advanced alerting.

### How does Rook monitor Ceph in Kubernetes?

Rook enables the Ceph MGR Dashboard and optionally deploys Prometheus and Grafana as part of the CephCluster CRD. When `monitoring.enabled: true` is set in the cluster spec, Rook creates ServiceMonitor resources that automatically configure Prometheus to scrape Ceph metrics. Grafana dashboards are auto-provisioned through the Rook monitoring stack.

### Can I use Grafana to monitor multiple Ceph clusters?

Yes. Configure multiple scrape targets in your `prometheus.yml`, each pointing to a different ceph_exporter or Ceph MGR Prometheus endpoint. In Grafana, add a cluster selector variable to switch between clusters on the same dashboard. This is a common pattern for organizations managing Ceph across multiple data centers.

### What Ceph metrics should I alert on?

Critical alerts should include: `ceph_health_status != 0` (any health issue), `ceph_osd_down > 0` (OSD failure), `ceph_pg_degraded > 0` (degraded placement groups), `ceph_mon_quorum_status != 1` (monitor quorum loss), and `ceph_cluster_available_bytes / ceph_cluster_total_bytes < 0.15` (capacity below 15%).

### How often should Ceph metrics be scraped?

The recommended scrape interval is 15 seconds for production clusters. This captures transient issues like brief OSD failures or recovery storms without overwhelming the Prometheus server. For large clusters (100+ OSDs), you may increase to 30 seconds to reduce scrape load.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Ceph Monitoring & Dashboards: Ceph MGR Dashboard vs Prometheus Exporter vs Rook Ceph Dashboard",
  "description": "Compare self-hosted Ceph monitoring solutions: built-in MGR Dashboard, Prometheus exporter with Grafana, and Rook Ceph Dashboard for Kubernetes deployments.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
