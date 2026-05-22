---
title: "Self-Hosted Prometheus Recording Rules Management: Operator vs Mimir vs Thanos"
date: "2026-05-22"
tags: ["prometheus", "monitoring", "observability", "kubernetes", "comparison"]
draft: false
---

Prometheus recording rules precompute frequently needed or computationally expensive expressions and save the result as a new set of time series. For large-scale monitoring setups, recording rules are essential — they reduce query load, speed up dashboards, and enable complex aggregations without real-time computation.

But managing recording rules across multiple Prometheus instances, environments, and teams quickly becomes challenging. This guide compares three approaches to Prometheus recording rules management: **Prometheus Operator** (Kubernetes-native), **Grafana Mimir** (horizontal scaling), and **Thanos Ruler** (multi-cluster federation).

## Why Recording Rules Matter for Self-Hosted Monitoring

Without recording rules, every dashboard panel computes its PromQL expressions from scratch. For a monitoring stack with 50+ dashboards querying 10,000+ time series, this creates:

- **High query latency** — complex expressions take seconds to evaluate
- **Increased CPU usage** — Prometheus repeatedly computes the same aggregations
- **Dashboard timeouts** — Grafana panels fail to load during peak query load
- **Scaling bottlenecks** — single Prometheus instance becomes a query bottleneck

Recording rules solve this by computing expressions on a schedule (typically every 1-5 minutes) and storing the results. Dashboards then query the precomputed series, reducing both latency and computational load.

## Architecture Comparison

Each tool approaches recording rules from a different architectural angle.

| Feature | Prometheus Operator | Grafana Mimir | Thanos Ruler |
|---------|-------------------|---------------|-------------|
| **Type** | Kubernetes Operator | Distributed TSDB | Sidecar/Ruler |
| **Rule Storage** | PrometheusRule CRD | YAML files + object store | YAML files + object store |
| **Evaluation Engine** | Prometheus server | Mimir ruler component | Thanos ruler component |
| **Multi-Tenant** | Via namespaces | Native (tenant header) | Via external labels |
| **High Availability** | Prometheus replicas | Native replication | Ruler HA pairs |
| **Rule Validation** | Admission webhook | `mimirtool rule check` | `thanos rule validate` |
| **Object Store** | N/A (local TSDB) | S3, GCS, Azure, Swift | S3, GCS, Azure, Swift |
| **Long-Term Storage** | Via Thanos sidecar | Native (compactor) | Native (compactor) |
| **Alert Integration** | Prometheus Alertmanager | Mimir ruler (built-in) | Thanos ruler (built-in) |
| **GitHub Stars** | 9,900+ | 5,100+ | 14,000+ |
| **License** | Apache 2.0 | AGPLv3 | Apache 2.0 |

### Prometheus Operator: Kubernetes-Native Rule Management

The Prometheus Operator introduces the `PrometheusRule` Custom Resource Definition (CRD), which stores recording rules as Kubernetes resources. This integrates seamlessly with GitOps workflows — rules are version-controlled alongside your cluster configuration.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-recording-rules
  namespace: monitoring
  labels:
    prometheus: main
    role: recording-rules
spec:
  groups:
    - name: node.rules
      interval: 1m
      rules:
        - record: node:cpu_utilization:avg5m
          expr: 1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)
        - record: node:memory_utilization:ratio
          expr: 1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
        - record: node:disk_utilization:ratio
          expr: 1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})
```

The Operator automatically discovers `PrometheusRule` resources across namespaces and merges them into the Prometheus configuration. This eliminates manual config file management and enables team-level rule ownership through namespace isolation.

### Grafana Mimir: Horizontally Scalable Rules

Mimir's ruler component evaluates recording rules in a horizontally scalable manner. Rules are stored as YAML files and uploaded via `mimirtool` or the Mimir API. The ruler distributes rule groups across multiple ruler instances, providing both parallelism and high availability.

```yaml
# recording-rules.yaml
groups:
  - name: api_latency.rules
    interval: 30s
    rules:
      - record: job:http_request_duration_seconds:p99_5m
        expr: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le))
      - record: job:http_request_duration_seconds:p95_5m
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le))
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job, method, status_code)
```

Upload rules with mimirtool:

```bash
mimirtool rules load recording-rules.yaml --address=https://mimir.example.com --id=team-backend --key=secret-key
```

Mimir's multi-tenant architecture means each team can manage their own recording rules without interfering with others. The `--id` and `--key` flags specify the tenant for rule storage.

### Thanos Ruler: Multi-Cluster Rule Evaluation

Thanos Ruler evaluates recording rules across multiple Prometheus instances and stores results in an object store. This is ideal for multi-cluster setups where you need aggregated metrics from several independent Prometheus servers.

```yaml
# thanos-rule.yaml
groups:
  - name: cluster_aggregation.rules
    interval: 2m
    rules:
      - record: cluster:node_cpu:ratio_rate5m
        expr: avg(rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (cluster)
      - record: cluster:pod_memory:working_set_bytes
        expr: sum(container_memory_working_set_bytes{pod!=""}) by (cluster, namespace)
      - record: cluster:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (cluster, job)
```

Run Thanos Ruler with object store configuration:

```bash
thanos rule   --data-dir=/data/thanos/ruler   --rule-file=/etc/thanos/rules/*.yaml   --alert.querier-address=query.example.com:10901   --objstore.config-file=/etc/thanos/objstore.yaml   --label="replica=1"
```

## Docker Compose Deployments

### Prometheus Operator (via kube-prometheus-stack)

While the Prometheus Operator runs on Kubernetes, you can test it locally with kind or k3s:

```yaml
# k3s setup for Prometheus Operator testing
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: kube-prometheus-stack
  namespace: kube-system
spec:
  chart: kube-prometheus-stack
  repo: https://prometheus-community.github.io/helm-charts
  targetNamespace: monitoring
  valuesContent: |-
    prometheus:
      prometheusSpec:
        ruleSelectorNilUsesHelmValues: false
        ruleNamespaceSelector: {}
```

### Grafana Mimir

```yaml
# docker-compose-mimir.yml
services:
  mimir:
    image: grafana/mimir:2.13.0
    command:
      - "-target=all"
      - "-config.file=/etc/mimir/mimir.yaml"
    ports:
      - "8080:8080"
    volumes:
      - ./mimir-config.yaml:/etc/mimir/mimir.yaml
      - mimir-data:/data
    deploy:
      resources:
        limits:
          memory: 2G

  grafana:
    image: grafana/grafana:11.0.0
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    depends_on:
      - mimir

volumes:
  mimir-data:
```

### Thanos Ruler with Local Prometheus

```yaml
# docker-compose-thanos.yml
services:
  thanos-ruler:
    image: quay.io/thanos/thanos:v0.36.0
    command:
      - "rule"
      - "--data-dir=/data"
      - "--rule-file=/rules/*.yaml"
      - "--objstore.config-file=/config/objstore.yaml"
      - "--grpc-address=0.0.0.0:10901"
      - "--http-address=0.0.0.0:10902"
    ports:
      - "10902:10902"
    volumes:
      - ./rules:/rules
      - ./objstore.yaml:/config/objstore.yaml
      - thanos-data:/data

  prometheus:
    image: prom/prometheus:v2.53.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prom-data:/prometheus

volumes:
  thanos-data:
  prom-data:
```

## Rule Validation and CI/CD Integration

Validating recording rules before deployment prevents broken queries from reaching production.

### Prometheus Operator: Admission Validation

The Operator includes a validating admission webhook that checks rule syntax before accepting `PrometheusRule` resources:

```bash
# Check if webhook is active
kubectl get validatingwebhookconfigurations prometheus-admission

# Test rule validation
kubectl apply -f broken-rule.yaml
# Error: spec.groups[0].rules[0].expr: invalid PromQL expression
```

### Mimir: mimirtool Rule Check

```bash
# Validate rules before uploading
mimirtool rule check recording-rules.yaml

# Dry-run upload (shows what would change)
mimirtool rules diff recording-rules.yaml --address=https://mimir.example.com
```

### Thanos: Rule File Validation

```bash
# Validate rule files locally
thanos rule validate --rule-file=./rules/*.yaml

# Check rule evaluation with test data
thanos rule validate --rule-file=./rules/*.yaml --test-files=./tests/*.yaml
```

## Choosing the Right Tool

### Choose Prometheus Operator if:
- You run Prometheus on Kubernetes
- You want GitOps-friendly rule management (rules as CRDs)
- Your team prefers namespace-based rule isolation
- You already use kube-prometheus-stack

### Choose Grafana Mimir if:
- You need horizontal scaling for rule evaluation
- Multi-tenant rule management is required
- You want long-term storage built into the same system
- You manage rules across many teams or departments

### Choose Thanos Ruler if:
- You have multiple independent Prometheus clusters
- You need cross-cluster rule aggregation
- You already use Thanos for query federation
- You want to keep existing Prometheus instances unchanged

## Related Guides

For broader monitoring tool comparisons, see our [Hertzbeat vs Prometheus vs Netdata guide](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide/).
If you need observability beyond metrics, check our [OpenObserve vs Quickwit vs Siglens comparison](../2026-04-20-openobserve-vs-quickwit-vs-siglens-self-hosted-observability-guide-2026/).
For alert routing on top of these rules, our [Prometheus Alertmanager vs ntfy vs Gotify guide](../2026-05-07-prometheus-alertmanager-vs-ntfy-vs-gotify-self-hosted-alert-routing-guide/) covers notification management.

## Frequently Asked Questions

### How often should recording rules be evaluated?

For most use cases, a 1-minute or 5-minute interval is sufficient. High-frequency rules (30s) are useful for real-time dashboards but increase computational load. Choose intervals based on your dashboard refresh needs — if dashboards refresh every 30 seconds, a 1-minute rule interval is adequate.

### Can recording rules reference other recording rules?

Yes, but be careful about evaluation order. If Rule B references Rule A's output, Rule A must be evaluated first. Prometheus evaluates rules in the order they appear in the configuration file. Group related rules together and order groups by dependency.

### How do I migrate recording rules between tools?

PromQL expressions are compatible across all three tools. The migration effort involves converting the rule format: `PrometheusRule` CRD to YAML files for Mimir/Thanos, or vice versa. The expressions themselves remain unchanged. Use `mimirtool rules sync` to migrate from Prometheus to Mimir.

### What happens if a recording rule fails to evaluate?

Failed rule evaluations produce errors in the Prometheus/Mimir/Thanos logs but do not stop other rules from running. The output time series simply won't be updated until the next successful evaluation. Monitor rule evaluation errors via the `prometheus_rule_evaluation_failures_total` metric.

### How many recording rules can I have?

There is no hard limit, but each rule adds computational overhead. A typical production setup has 50-200 recording rules. Monitor the `prometheus_rule_group_duration_seconds` metric to ensure rules complete within their evaluation interval. If rules consistently take longer than the interval, consider reducing the rule count or increasing the interval.

### Do recording rules increase storage usage?

Yes — each recording rule creates new time series. However, the storage cost is usually offset by the reduced cardinality. For example, a rule that aggregates 1,000 per-instance metrics into 10 per-job metrics actually reduces storage by 99%. Plan for approximately 10-20% additional storage for a typical recording rule set.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Prometheus Recording Rules Management: Operator vs Mimir vs Thanos",
  "description": "Compare three approaches to managing Prometheus recording rules: Prometheus Operator, Grafana Mimir, and Thanos Ruler. Covers deployment, validation, and CI/CD.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
