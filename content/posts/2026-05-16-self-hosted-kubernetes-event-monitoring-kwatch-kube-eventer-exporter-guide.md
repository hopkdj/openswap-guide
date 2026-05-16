---
title: "Self-Hosted Kubernetes Event Monitoring: kwatch vs kube-eventer vs kubernetes-event-exporter"
date: "2026-05-16"
tags: ["kubernetes", "monitoring", "event-management", "alerting", "observability"]
draft: false
---

Kubernetes events capture important cluster state changes — pod scheduling failures, node conditions, deployment rollouts, and resource quota violations. By default, events are stored in etcd with a short TTL and are only visible through `kubectl get events`. For production clusters, dedicated event monitoring tools provide persistent storage, alerting, and integration with notification channels.

This guide compares three open-source Kubernetes event monitoring tools — **kwatch**, **kube-eventer**, and **kubernetes-event-exporter** — each with different approaches to capturing, forwarding, and alerting on cluster events.

## Why Monitor Kubernetes Events?

Kubernetes events are ephemeral by design — they are stored in etcd and garbage-collected after one hour by default. This means critical operational signals like pod crash loops, node not-ready conditions, and image pull failures can disappear before you notice them.

Event monitoring tools solve this by:

- **Persisting events** beyond etcd's TTL
- **Forwarding events** to external sinks (Slack, PagerDuty, Elasticsearch, webhooks)
- **Detecting patterns** like repeated container crashes or node failures
- **Correlating events** with metrics and logs for root cause analysis

| Feature | kwatch | kube-eventer | kubernetes-event-exporter |
|---------|--------|-------------|--------------------------|
| **GitHub Stars** | 1,004 | 1,079 | 1,048 |
| **Last Updated** | May 2026 | Apr 2026 | Aug 2022 |
| **Primary Goal** | Crash detection & alerting | Event forwarding to sinks | Event export as metrics/logs |
| **Language** | Go | Go | Go |
| **Alerting** | Built-in (Slack, Discord, Teams, webhook) | Via sinks (webhook, Kafka, Elasticsearch) | Via Prometheus metrics or log output |
| **Installation** | Helm chart / YAML manifest | Helm chart / YAML manifest | Helm chart / YAML manifest |
| **Best For** | SRE teams needing instant crash alerts | Event-driven architectures | Metrics-driven monitoring |

## kwatch — Instant Crash Detection for Kubernetes

[kwatch](https://github.com/abahmed/kwatch) is a lightweight Kubernetes event monitor focused on detecting pod crashes and sending instant notifications. It watches for CrashLoopBackOff, OOMKilled, and other failure events and alerts through Slack, Discord, Microsoft Teams, or custom webhooks.

### Key Features

- **Crash detection**: Automatically detects CrashLoopBackOff, OOMKilled, and ImagePullBackOff events
- **Multi-channel alerts**: Slack, Discord, Microsoft Teams, Telegram, and webhooks
- **Pod logs inclusion**: Attaches recent pod logs to alert messages for faster debugging
- **Namespace filtering**: Monitor specific namespaces or exclude system namespaces
- **Lightweight footprint**: Minimal resource usage — runs as a single Deployment

### Deployment

kwatch is deployed as a Kubernetes Deployment with ClusterRole and ServiceAccount:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kwatch
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kwatch
  template:
    metadata:
      labels:
        app: kwatch
    spec:
      serviceAccountName: kwatch
      containers:
      - name: kwatch
        image: ghcr.io/abahmed/kwatch:latest
        env:
        - name: ALERT_SLACK_WEBHOOK
          value: "https://hooks.slack.com/services/REPLACE/WITH/YOUR-WEBHOOK"
        - name: ALERT_SLACK_CHANNEL
          value: "#k8s-alerts"
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 100m
            memory: 128Mi
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kwatch
rules:
- apiGroups: [""]
  resources: ["events", "pods", "pods/log"]
  verbs: ["get", "watch", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kwatch
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kwatch
subjects:
- kind: ServiceAccount
  name: kwatch
  namespace: monitoring
```

### Configuration

kwatch uses environment variables for configuration. Key settings include:

```yaml
env:
- name: ALERT_SLACK_WEBHOOK
  value: "https://hooks.slack.com/services/REPLACE/WITH/YOUR-WEBHOOK"
- name: ALERT_SLACK_CHANNEL
  value: "#kubernetes-alerts"
- name: NAMESPACES
  value: "default,production,staging"
- name: EXCLUDE_NAMESPACES
  value: "kube-system,monitoring"
- name: MAX_RESTART_COUNT
  value: "3"
```

The `MAX_RESTART_COUNT` setting controls how many restarts trigger an alert, reducing noise from transient failures.

## kube-eventer — Event Forwarding to Multiple Sinks

[kube-eventer](https://github.com/AliyunContainerService/kube-eventer) is a Kubernetes event forwarder that captures cluster events and sends them to various sinks including webhooks, Kafka, Elasticsearch, and logging services. Originally developed by Alibaba Cloud, it is designed for event-driven architectures where Kubernetes events need to trigger downstream processing.

### Key Features

- **Multiple sink types**: Webhook, Kafka, Elasticsearch, DingTalk, Slack
- **Event filtering**: Filter events by type, reason, or namespace
- **High throughput**: Designed for large clusters with high event volumes
- **Batch processing**: Groups events before forwarding to reduce API calls
- **Sink fallback**: Configurable retry and fallback behavior for failed deliveries

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-eventer
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kube-eventer
  template:
    metadata:
      labels:
        app: kube-eventer
    spec:
      serviceAccountName: kube-eventer
      containers:
      - name: kube-eventer
        image: registry.cn-hangzhou.aliyuncs.com/acs/kube-eventer-amd64:v1.2.0
        command:
        - /kube-eventer
        - --source=kubernetes:https://kubernetes.default
        - --sink=webhook:https://your-webhook.example.com/events
        - --sink=elasticsearch:http://elasticsearch:9200?sniff=false
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kube-eventer
rules:
- apiGroups: [""]
  resources: ["events"]
  verbs: ["get", "watch", "list"]
```

### Sink Configuration

kube-eventer supports multiple sinks simultaneously using the `--sink` flag:

```bash
# Webhook sink with custom headers
--sink=webhook:https://hooks.example.com/k8s?level=Info&custom_header=Authorization:Bearer+token

# Kafka sink for event streaming
--sink=kafka:broker1:9092,broker2:9092?topic=k8s-events&level=Warning

# Elasticsearch sink for persistent storage
--sink=elasticsearch:http://es-cluster:9200?sniff=false&index=k8s-events
```

Multiple `--sink` flags can be specified to forward events to multiple destinations simultaneously.

## kubernetes-event-exporter — Events as Prometheus Metrics

[kubernetes-event-exporter](https://github.com/opsgenie/kubernetes-event-exporter) by Opsgenie exports Kubernetes events as Prometheus metrics and/or structured logs. This approach enables event-driven alerting through existing Prometheus/Alertmanager pipelines, integrating events with your existing monitoring workflow.

### Key Features

- **Prometheus metrics**: Exports events as metrics for Prometheus scraping
- **Structured logging**: Outputs events as JSON logs for log aggregation pipelines
- **Webhook forwarding**: Sends events to external webhooks
- **Event deduplication**: Avoids duplicate metric emissions for recurring events
- **Namespace filtering**: Selective event export by namespace

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-event-exporter
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: k8s-event-exporter
  template:
    metadata:
      labels:
        app: k8s-event-exporter
    spec:
      serviceAccountName: k8s-event-exporter
      containers:
      - name: exporter
        image: opsgenie/kubernetes-event-exporter:latest
        args:
        - -conf=/etc/config/config.yaml
        ports:
        - containerPort: 8080
          name: metrics
        volumeMounts:
        - name: config
          mountPath: /etc/config
      volumes:
      - name: config
        configMap:
          name: k8s-event-exporter-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-event-exporter-config
data:
  config.yaml: |
    logLevel: info
    logFormat: json
    namespace: ""
    host: "0.0.0.0"
    port: 8080
    rules:
      - match:
          type: "Warning"
          reason: ".*"
        emit: true
    receivers:
      - name: "webhook"
        webhook:
          endpoint: "https://your-webhook.example.com/events"
          headers:
            Content-Type: "application/json"
```

### Prometheus Integration

To scrape metrics from the event exporter, add a ServiceMonitor or scrape config:

```yaml
# Prometheus scrape config addition
- job_name: k8s-event-exporter
  kubernetes_sd_configs:
  - role: endpoints
    namespaces:
      names:
      - monitoring
  relabel_configs:
  - source_labels: [__meta_kubernetes_pod_label_app]
    regex: k8s-event-exporter
    action: keep
```

The exporter emits metrics like `kubernetes_event_count` and `kubernetes_event_last_seen` that can be queried in Prometheus and Alertmanager.

## Comparison: Crash Alerts vs Event Forwarding vs Metrics

| Aspect | kwatch | kube-eventer | kubernetes-event-exporter |
|--------|--------|-------------|--------------------------|
| **Primary Use Case** | Instant crash alerts | Event streaming to sinks | Metrics-driven alerting |
| **Notification Channels** | Slack, Discord, Teams, Telegram | Webhook, Kafka, ES, DingTalk | Prometheus/Alertmanager, Webhook |
| **Event Persistence** | No (alert-and-forget) | Yes (ES, Kafka) | Yes (Prometheus, logs) |
| **Pod Log Attachment** | Yes | No | No |
| **Event Filtering** | Namespace-based | Type, reason, namespace | Rule-based matching |
| **Resource Usage** | Very low (~64 MB) | Low (~128 MB) | Low (~128 MB) |
| **Setup Complexity** | Low (env vars) | Medium (sink config) | Medium (YAML config + Prometheus) |

## When to Use Each Tool

**kwatch** is ideal when:
- You need instant notifications for pod crashes and OOMKilled events
- Your team uses Slack/Discord/Teams for operational communication
- You want pod logs automatically attached to alert messages
- You have a small-to-medium cluster and need simple setup

**kube-eventer** excels when:
- You need to forward events to multiple sinks simultaneously
- You are building event-driven architectures (events trigger downstream processing)
- You need persistent event storage in Elasticsearch or Kafka
- You operate large clusters with high event volumes

**kubernetes-event-exporter** is best when:
- You already use Prometheus/Alertmanager for monitoring
- You want to correlate events with metrics using PromQL
- You prefer rule-based event matching and filtering
- Your team is comfortable with Prometheus alerting rules

## Building a Complete Event Monitoring Pipeline

For comprehensive Kubernetes observability, combine event monitoring with other tools:

- **Metrics**: Prometheus + [Alertmanager dashboard](../2026-05-16-self-hosted-alertmanager-dashboard-karma-unsee-native-guide/) for metric-based alerting
- **Logs**: [Vector + Fluent Bit](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/) for log aggregation from monitored pods
- **Tracing**: Distributed tracing for request-level debugging
- **Policy**: [Kubernetes policy enforcement](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/) with Kyverno or OPA Gatekeeper to prevent issues before they generate events

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Event Monitoring: kwatch vs kube-eventer vs kubernetes-event-exporter",
  "description": "Compare Kubernetes event monitoring tools for crash detection, event forwarding, and metrics-driven alerting in production clusters.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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

## FAQ

### How long are Kubernetes events stored by default?

Kubernetes stores events in etcd with a default TTL of one hour. After this period, events are garbage-collected. This is why dedicated event monitoring tools are necessary — without them, you lose visibility into past events that could indicate recurring issues.

### Can these tools detect node-level issues?

kwatch primarily monitors pod-level events (crashes, image pulls, scheduling failures). kube-eventer and kubernetes-event-exporter can capture node-level events like `NodeNotReady`, `NodeUnderMemoryPressure`, and `NodeUnderDiskPressure` by watching all events in the cluster, not just pod events.

### Do these tools work with managed Kubernetes (EKS, GKE, AKS)?

Yes, all three tools work with managed Kubernetes clusters. They require ClusterRole permissions to read events, which are available on all major managed Kubernetes platforms. Note that some managed platforms (like GKE) have their own event export mechanisms that may overlap with these tools.

### How do I reduce alert noise from kwatch?

Use the `EXCLUDE_NAMESPACES` environment variable to exclude noisy system namespaces, and set `MAX_RESTART_COUNT` to a higher threshold (e.g., 5) to avoid alerts from transient restarts. You can also configure namespace-specific alerting by deploying multiple kwatch instances with different namespace filters.

### Can I forward events to both Slack and Elasticsearch?

Yes, but you need different tools for this. kwatch only supports notification channels (Slack, Discord, etc.) without persistent storage. kube-eventer can forward to both webhooks (Slack) and Elasticsearch simultaneously using multiple `--sink` flags. Alternatively, use kube-eventer for ES persistence and kwatch for instant Slack alerts.

### What RBAC permissions do these tools need?

All three tools need at minimum `get`, `watch`, and `list` permissions on the `events` resource. kwatch additionally needs access to `pods` and `pods/log` to attach log output to alerts. Deploy each tool with a dedicated ServiceAccount and ClusterRole scoped to only the required permissions.
