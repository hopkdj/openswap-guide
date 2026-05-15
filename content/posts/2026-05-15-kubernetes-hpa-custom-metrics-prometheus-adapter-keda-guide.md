---
title: "Self-Hosted Kubernetes HPA with Custom Metrics: Prometheus Adapter vs KEDA vs Custom Metrics API (2026)"
date: "2026-05-15"
tags: ["kubernetes", "autoscaling", "prometheus", "keda", "custom-metrics"]
draft: false
---

Horizontal Pod Autoscaling (HPA) is one of Kubernetes' most powerful features, allowing your workloads to scale automatically based on demand. While CPU and memory-based scaling works well for simple use cases, real-world applications often need to scale based on application-specific metrics like queue depth, requests per second, or business KPIs.

This guide covers three approaches to custom metrics-based HPA in Kubernetes: the Prometheus Adapter, KEDA (Kubernetes Event-Driven Autoscaling), and the raw Custom Metrics API — comparing their architecture, configuration, and use cases.

## Understanding Kubernetes HPA and Custom Metrics

The Kubernetes HPA controller natively supports CPU and memory metrics via the Metrics Server. However, for application-aware scaling, you need the custom metrics pipeline:

```
Application → Metrics Exporter → Metrics Store → Custom Metrics API → HPA Controller
```

The key components are:
- **Metrics exporter**: Your application exposes metrics (typically Prometheus format)
- **Metrics store**: Prometheus, VictoriaMetrics, or similar time-series database
- **Custom Metrics API**: Translates stored metrics into the Kubernetes metrics API
- **HPA controller**: Reads custom metrics and adjusts replica counts

## Prometheus Adapter for HPA

The Prometheus Adapter is the official Kubernetes SIG project that exposes Prometheus metrics through the `custom.metrics.k8s.io` API, enabling HPA to scale based on any Prometheus metric.

### Architecture

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  prometheus-adapter:
    image: registry.k8s.io/prometheus-adapter/prometheus-adapter:v0.12.0
    ports:
      - "6443:6443"
    volumes:
      - ./adapter-config.yaml:/etc/adapter/config.yaml
    command:
      - --cert-dir=/tmp
      - --secure-port=6443
      - --prometheus-url=http://prometheus:9090
      - --config=/etc/adapter/config.yaml

volumes:
  prometheus-data:
```

### Adapter Configuration

```yaml
rules:
- seriesQuery: 'http_requests_total{namespace!="",pod!=""}'
  resources:
    overrides:
      namespace: {resource: "namespace"}
      pod: {resource: "pod"}
  name:
    matches: "^http_requests_total"
    as: "http_requests_per_second"
  metricsQuery: 'sum(rate(http_requests_total{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

The Prometheus Adapter is ideal when you already run Prometheus and need fine-grained control over which metrics are exposed to HPA. It supports pod, object, and external metrics types.

**Pros:** Official Kubernetes SIG project, tight Prometheus integration, flexible metric queries
**Cons:** Requires Prometheus, complex configuration for advanced scenarios, no event-driven scaling

## KEDA (Kubernetes Event-Driven Autoscaling)

KEDA extends Kubernetes HPA with 50+ event source scalers, including Prometheus, Kafka, RabbitMQ, AWS SQS, and more. Unlike the Prometheus Adapter, KEDA can scale workloads to zero when no events are present.

### Architecture

KEDA operates through two components:
- **KEDA Operator**: Manages HPA resources and connects to event sources
- **Metrics Server**: Exposes external metrics to the Kubernetes API

### HPA with KEDA Prometheus Scaler

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: web-app-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: web-app
  pollingInterval: 15
  cooldownPeriod: 300
  minReplicaCount: 1
  maxReplicaCount: 30
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc:9090
      metricName: http_requests_per_second
      threshold: "1000"
      query: |
        sum(rate(http_requests_total{service="web-app"}[2m]))
```

### KEDA Deployment

```yaml
version: "3.8"
services:
  keda-operator:
    image: ghcr.io/kedacore/keda-operator:latest
    environment:
      - WATCH_NAMESPACE=default
    volumes:
      - /var/run/secrets/kubernetes.io/serviceaccount:/var/run/secrets/kubernetes.io/serviceaccount

  keda-metrics-server:
    image: ghcr.io/kedacore/keda-metrics-apiserver:latest
    ports:
      - "6443:6443"
```

### KEDA Kafka Scaler Example

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: consumer-scaler
spec:
  scaleTargetRef:
    name: kafka-consumer
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka-cluster.kafka.svc:9092
      consumerGroup: my-consumer-group
      topic: orders
      lagThreshold: "100"
```

KEDA's major advantage is scale-to-zero capability and its vast ecosystem of scalers. It's the go-to choice for event-driven architectures.

**Pros:** Scale-to-zero, 50+ event source scalers, simple ScaledObject CRD, active community
**Cons:** Additional CRDs to manage, requires KEDA operator deployment, less flexible metric queries than Prometheus Adapter

## Custom Metrics API (Manual Implementation)

For organizations that need maximum control or have non-standard metrics pipelines, implementing a custom metrics server directly is an option. This approach requires building a service that implements the `custom.metrics.k8s.io` API.

### API Server Implementation

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-metrics-api
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: custom-metrics-api
  template:
    spec:
      containers:
      - name: api-server
        image: your-registry/custom-metrics-api:latest
        ports:
        - containerPort: 443
        volumeMounts:
        - name: tls-certs
          mountPath: /tls
      volumes:
      - name: tls-certs
        secret:
          secretName: custom-metrics-api-certs
---
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1beta1.custom.metrics.k8s.io
spec:
  service:
    name: custom-metrics-api
    namespace: kube-system
  group: custom.metrics.k8s.io
  version: v1beta1
  insecureSkipTLSVerify: false
  groupPriorityMinimum: 100
  versionPriority: 100
```

### HPA Using External Metrics

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: External
    external:
      metric:
        name: queue_depth
      target:
        type: AverageValue
        averageValue: "50"
```

This approach is rarely used in practice because building and maintaining a custom metrics API server is complex. Most teams should use the Prometheus Adapter or KEDA instead.

**Pros:** Complete control, can integrate any metrics backend
**Cons:** Significant development effort, TLS/APIService complexity, no community support

## Comparison: Prometheus Adapter vs KEDA vs Custom Metrics API

| Feature | Prometheus Adapter | KEDA | Custom Metrics API |
|---------|-------------------|------|-------------------|
| **GitHub Stars** | 2,073 | 10,186 | N/A (API spec) |
| **Scale to Zero** | No | Yes | Depends on implementation |
| **Event Sources** | Prometheus only | 50+ scalers | Custom |
| **CRD Required** | No | Yes (ScaledObject) | Yes (APIService) |
| **Setup Complexity** | Medium | Low | High |
| **Metric Types** | Pods, Objects, External | External | Any |
| **Best For** | Prometheus-centric shops | Event-driven apps | Custom metrics backends |
| **Docker Support** | Yes | Yes | Custom |

## Why Self-Host Kubernetes Autoscaling?

Running your own autoscaling infrastructure gives you complete control over scaling policies, metric collection, and data privacy. Cloud-managed autoscaling services often lock you into specific metrics pipelines or charge premium rates for custom metric ingestion.

Self-hosted autoscaling with Prometheus Adapter or KEDA means:
- **No vendor lock-in**: Your scaling logic works identically across on-premises, edge, and multi-cloud environments
- **Cost control**: No per-metric ingestion fees from cloud providers
- **Data sovereignty**: All metrics stay within your infrastructure, critical for regulated industries
- **Custom metric pipelines**: Integrate with any internal monitoring system

For teams running Kubernetes on bare metal or in hybrid environments, self-hosted autoscaling is not optional — it's essential. The combination of Prometheus for metrics collection and KEDA for event-driven scaling provides enterprise-grade autoscaling without cloud dependencies.

For Kubernetes networking fundamentals, see our [CNI comparison guide](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) and [ingress controller comparison](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide/).

## Choosing the Right Autoscaling Approach

**Use Prometheus Adapter when:**
- You already run Prometheus for monitoring
- You need fine-grained control over metric aggregation and labeling
- Your scaling metrics are application-level (request rate, error rate, latency)

**Use KEDA when:**
- You need scale-to-zero for cost optimization
- Your workloads are event-driven (message queues, HTTP requests, cron jobs)
- You want pre-built scalers for popular event sources (Kafka, RabbitMQ, Redis, AWS)

**Use Custom Metrics API when:**
- Your metrics live in a non-Prometheus backend (InfluxDB, Datadog, custom database)
- You have unique scaling requirements not met by existing solutions
- You're building a platform product with embedded autoscaling

## FAQ

### What is the difference between HPA and VPA in Kubernetes?

HPA (Horizontal Pod Autoscaler) adjusts the number of pod replicas based on metrics, while VPA (Vertical Pod Autoscaler) adjusts the CPU and memory requests/limits of individual pods. They can be used together but require careful configuration to avoid conflicts.

### Can KEDA scale to zero pods?

Yes, KEDA supports scale-to-zero through the `minReplicaCount: 0` setting in ScaledObject. When no events are present, KEDA scales the deployment to zero replicas, saving resources. The Prometheus Adapter does not support scale-to-zero natively.

### How often does the HPA controller check metrics?

By default, the HPA controller syncs every 15 seconds. You can adjust this with the `--horizontal-pod-autoscaler-sync-period` flag on the kube-controller-manager. KEDA's polling interval is configurable per ScaledObject (default 15 seconds).

### Do I need Prometheus to use KEDA?

No. KEDA has 50+ scalers that connect directly to event sources (Kafka, RabbitMQ, Redis, AWS SQS, etc.) without requiring Prometheus. The Prometheus scaler is just one of many options. However, you need a metrics server (like metrics-server) installed for KEDA to function.

### What happens if the Custom Metrics API server goes down?

If the Custom Metrics API server becomes unavailable, the HPA controller will fail to retrieve metrics and will stop scaling actions. It will maintain the current replica count but won't scale up or down until the API server recovers. High availability deployments of the metrics API server are recommended for production.

### Can I use multiple autoscaling approaches together?

Yes. You can run KEDA alongside the Prometheus Adapter. KEDA manages its own HPA resources and doesn't interfere with HPAs created by the Prometheus Adapter. However, having multiple autoscalers targeting the same deployment can cause conflicts — ensure each HPA targets a different workload.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes HPA with Custom Metrics: Prometheus Adapter vs KEDA vs Custom Metrics API (2026)",
  "description": "Compare three approaches to Kubernetes Horizontal Pod Autoscaling with custom metrics: Prometheus Adapter, KEDA, and the Custom Metrics API. Includes Docker Compose configs, YAML examples, and decision guide.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
