---
title: "Self-Hosted Kubernetes Metrics APIs: metrics-server vs prometheus-adapter vs custom-metrics-apiserver (2026)"
date: "2026-05-10"
tags: ["kubernetes", "metrics", "monitoring", "autoscaling", "custom-metrics", "prometheus", "hpa"]
draft: false
---

Kubernetes built-in autoscaling capabilities rely on metrics APIs to make intelligent scaling decisions. The default metrics-server provides basic CPU and memory data, but modern workloads often need custom application metrics — request rates, queue depths, or business KPIs — to drive accurate scaling. This guide compares the leading Kubernetes metrics API implementations.

## Understanding Kubernetes Metrics APIs

Kubernetes provides two metrics APIs that serve different purposes. The **Resource Metrics API** handles basic CPU and memory data used by Horizontal Pod Autoscaler version 1, while the **Custom Metrics API** handles application-specific metrics used by HPA version 2 for advanced scaling decisions.

The Resource Metrics API is served by metrics-server, a lightweight aggregator that collects data from kubelets on every node. The Custom and External Metrics APIs require additional components — typically prometheus-adapter or the custom-metrics-apiserver — that translate monitoring system data into Kubernetes API responses.

Understanding the distinction is crucial because many clusters run metrics-server but lack custom metrics support, limiting autoscaling to basic CPU and memory thresholds. Application workloads with variable traffic patterns benefit significantly from custom metrics like HTTP request rates, database connection pool utilization, or message queue depth.

## Comparison Overview

| Feature | metrics-server | prometheus-adapter | custom-metrics-apiserver |
|---|---|---|---|
| GitHub Stars | 6,622+ | 2,073+ | 525+ |
| Metrics API | Resource only | Custom + External | Custom + External |
| Data Source | kubelet | Prometheus | Prometheus or Any |
| HPA Support | v1 basic | v2 advanced | v2 advanced |
| Query Language | Not applicable | PromQL | Custom rules |
| Aggregation Layer | Required | Required | Required |
| Docker Available | Yes | Yes | Yes |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Best For | Basic autoscaling | Prometheus users | Custom integrations |

## metrics-server: The Default Resource Metrics Provider

metrics-server is the standard implementation of the Resource Metrics API in Kubernetes clusters. It aggregates resource usage data from kubelets on each node and exposes it through the metrics API for cluster-wide consumption.

### Architecture and Deployment

metrics-server runs as a Deployment in the kube-system namespace and scrapes kubelet endpoints on a configurable interval:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-server
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      k8s-app: metrics-server
  template:
    spec:
      containers:
      - name: metrics-server
        image: registry.k8s.io/metrics-server/metrics-server:v0.7.1
        args:
        - --kubelet-insecure-tls
        - --kubelet-preferred-address-types=InternalIP
        - --metric-resolution=15s
        ports:
        - name: https
          containerPort: 10250
          protocol: TCP
        resources:
          requests:
            cpu: 100m
            memory: 200Mi
          limits:
            cpu: 500m
            memory: 500Mi
```

### Key Features

- **Lightweight**: Minimal resource footprint designed to run on every cluster without significant overhead
- **Standard**: The default metrics provider shipped with most Kubernetes distributions out of the box
- **kubelet-Based**: Collects data directly from node kubelets with no external monitoring dependencies
- **kubectl top Support**: Powers kubectl top pods and kubectl top nodes commands for quick diagnostics
- **Configurable Scrape Interval**: Adjustable from 15 seconds to 60 seconds based on cluster size

### Limitations

metrics-server only provides basic CPU and memory metrics. It cannot expose application-level metrics like HTTP request rates, database query latencies, or message queue depths. For these advanced use cases, you need a custom metrics adapter.

## prometheus-adapter: Prometheus-Powered Custom Metrics

prometheus-adapter is the most widely used implementation of the Custom and External Metrics APIs for Kubernetes. It translates Prometheus metrics into Kubernetes API responses, enabling HPA version 2 to scale based on any Prometheus metric.

### Architecture and Deployment

prometheus-adapter queries Prometheus using PromQL and maps the results to Kubernetes API format through the aggregation layer:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus-adapter
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: prometheus-adapter
  template:
    spec:
      containers:
      - name: prometheus-adapter
        image: registry.k8s.io/prometheus-adapter/prometheus-adapter:v0.12.0
        args:
        - --prometheus-url=http://prometheus.monitoring.svc:9090
        - --metrics-relist-interval=1m
        - --v=4
        ports:
        - containerPort: 6443
        volumeMounts:
        - name: config
          mountPath: /etc/adapter
      volumes:
      - name: config
        configMap:
          name: adapter-config
```

### Key Features

- **PromQL Integration**: Direct access to all Prometheus metrics and functions for flexible metric definitions
- **Flexible Rules**: Map any Prometheus metric to Kubernetes custom metrics with powerful query transformations
- **Multiple Instances**: Run multiple adapter replicas for high availability and load distribution
- **External Metrics API**: Supports cluster-scoped metrics for scaling non-Kubernetes resources like cloud databases
- **Wide Adoption**: The de facto standard for Prometheus-based autoscaling in Kubernetes deployments

## custom-metrics-apiserver: The Framework Approach

The custom-metrics-apiserver is a framework for building custom metrics implementations rather than a specific adapter. It provides the scaffolding for connecting any monitoring backend to the Kubernetes custom metrics API.

### Architecture and Implementation

Unlike prometheus-adapter which is tightly coupled to Prometheus, the custom-metrics-apiserver framework lets you implement your own metric provider connecting to Datadog, New Relic, or any custom monitoring system:

```go
// Implement the CustomMetricsProvider interface
type MyProvider struct {
    // Your monitoring client connection
}

func (p *MyProvider) GetMetricByName(name string, info CustomMetricInfo,
    metricName string) (*MetricValue, error) {
    // Query your monitoring backend
    // Return metric value in Kubernetes API format
    return nil, nil
}
```

### Key Features

- **Backend Agnostic**: Connect to any monitoring system, not just Prometheus instances
- **Framework Design**: Provides the scaffolding while you implement the data retrieval logic
- **Full API Support**: Implements both custom and external metrics APIs for comprehensive coverage
- **Extensible**: Add support for new metric types and custom query patterns as needed
- **Official Project**: Maintained by Kubernetes SIGs with active community contributions

## Choosing the Right Metrics API Implementation

The choice depends on your monitoring stack and autoscaling requirements:

- **Choose metrics-server** if you only need basic CPU and memory-based autoscaling. It is the default option, requires minimal configuration, and powers kubectl top commands.
- **Choose prometheus-adapter** if you use Prometheus and need application-level autoscaling. It is the most mature and widely used custom metrics adapter available.
- **Choose custom-metrics-apiserver** if you need to integrate a non-Prometheus monitoring backend with Kubernetes autoscaling.

## Why Self-Host Kubernetes Metrics Infrastructure?

Running your own metrics APIs keeps your autoscaling decisions within your infrastructure boundary. Managed Kubernetes services provide metrics-server by default, but custom metrics adapters require additional setup and configuration that managed providers may not support or may restrict.

Self-hosting gives you full control over metric collection intervals, retention policies, and query patterns. You can tune the metrics pipeline for your specific workloads by adjusting scrape intervals, configuring metric relabeling rules, and optimizing PromQL queries for your autoscaling requirements.

For teams running stateful workloads with variable traffic patterns, custom metrics-based autoscaling is essential for cost efficiency. Database connection pools, message queue depths, and cache hit rates are far better scaling signals than raw CPU usage. Self-hosting the metrics pipeline ensures these signals are always available, even when external monitoring services experience outages.

The metrics pipeline also serves as the foundation for observability beyond autoscaling. Custom metrics feed into dashboards, alerting rules, and capacity planning tools, making a self-hosted metrics infrastructure a cornerstone of production reliability engineering.

Cost optimization is another significant benefit. By using application-specific metrics for autoscaling decisions, you can scale down resources during low-traffic periods more aggressively, reducing infrastructure costs by 30 to 50 percent compared to CPU-based autoscaling alone.

For comprehensive metrics storage, see our [VictoriaMetrics vs Thanos guide](../2026-04-27-grafana-mimir-vs-thanos-vs-cortex-self-hosted-prometheus-long-term-storage-guide-2026/).
For Kubernetes resource optimization, our [Descheduler vs VPA guide](../2026-05-07-descheduler-vs-vpa-vs-goldilocks-kubernetes-resource-optimization/) covers right-sizing strategies.
And for time-series databases, the [GreptimeDB vs InfluxDB comparison](../2026-04-27-greptimedb-vs-influxdb-vs-victoriametrics-self-hosted-time-series-database-guide-2026/) explores storage options.

## FAQ

### What is the difference between metrics-server and prometheus-adapter?

metrics-server provides basic CPU and memory metrics from kubelets through the Resource Metrics API. prometheus-adapter provides application-level custom metrics from Prometheus through the Custom Metrics API. You typically run both together — metrics-server for kubectl top and basic HPA, prometheus-adapter for advanced HPA version 2 scaling rules.

### Can I use prometheus-adapter without Prometheus?

No. prometheus-adapter requires a running Prometheus server as its data source since it translates PromQL queries into Kubernetes API responses. If you do not use Prometheus, consider the custom-metrics-apiserver framework to connect your preferred monitoring backend instead.

### How often does metrics-server scrape kubelets?

By default, metrics-server scrapes every 15 seconds. This interval is configurable via the metric-resolution flag. Increasing the interval reduces load on kubelets but delays metric availability for HPA scaling decisions.

### What metrics can I use for HPA version 2 autoscaling?

With prometheus-adapter, you can use any Prometheus metric including HTTP request rates, queue lengths, database connections, custom business metrics, or anything else you scrape into Prometheus. The adapter maps Prometheus metrics to Kubernetes custom metrics via configurable YAML rules.

### Does the custom-metrics-apiserver come pre-configured?

No. The custom-metrics-apiserver is a framework, not a ready-to-use adapter. You need to implement the CustomMetricsProvider interface to connect your monitoring backend. prometheus-adapter is a ready-to-use implementation built on top of this same framework.

### How do I verify my metrics adapter is working?

Use kubectl get with the raw API path to list available custom metrics. Then query a specific metric to verify values are returned. If you get metric data back from the API, the adapter is functioning correctly and HPA can consume the metrics.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Metrics APIs: metrics-server vs prometheus-adapter vs custom-metrics-apiserver (2026)",
  "description": "Compare self-hosted Kubernetes metrics API implementations. metrics-server, prometheus-adapter, and custom-metrics-apiserver with deployment configs.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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