---
title: "Self-Hosted Kubernetes Automated Remediation: Robusta vs Keptn vs Goldilocks"
date: "2026-05-17"
tags: ["kubernetes", "automation", "monitoring", "incident-response"]
draft: false
---

When Kubernetes workloads fail, manual intervention is slow and error-prone. Automated remediation platforms detect anomalies, diagnose root causes, and execute corrective actions before human operators even open their laptops. This guide compares three self-hosted tools that bring autonomous operations to Kubernetes clusters: **Robusta**, **Keptn**, and **Goldilocks**.

## The Need for Kubernetes Automated Remediation

Kubernetes natively handles basic failure recovery — restart crashed containers, reschedule evicted pods, and replace failed nodes. But production incidents require deeper intelligence:

- **Alert correlation** — grouping related alerts to identify root causes instead of alert storms
- **Automatic diagnostics** — fetching pod logs, describing resources, and checking recent deployments when alerts fire
- **Self-healing actions** — restarting deployments, scaling workloads, or clearing stuck jobs automatically
- **Resource optimization** — right-sizing CPU and memory requests based on actual utilization patterns
- **Playbook automation** — executing runbooks in response to specific alert conditions

## Robusta: Prometheus Alert Enrichment and Remediation

Robusta (3,000+ stars) is an open-source Kubernetes engine that enhances Prometheus alerts with automatic diagnostics and remediation actions. It sits between Prometheus Alertmanager and your notification channels, enriching alerts with context and executing predefined playbooks.

### Architecture

Robusta deploys as a set of Kubernetes workloads that:
1. Subscribe to Prometheus alerts via Alertmanager webhook
2. Enrich alerts with cluster context (pod logs, events, recent changes)
3. Execute remediation playbooks based on alert rules
4. Deliver enriched notifications to Slack, PagerDuty, or webhooks

### Docker/Helm Deployment

```yaml
# values.yaml for Robusta Helm chart
global:
  clusterName: production-us-east-1

sinks:
  - name: slack_main
    params:
      slack_channel: "#kubernetes-alerts"
      api_key: "${SLACK_BOT_TOKEN}"

playbookConfig:
  # Custom remediation playbooks
  triggers:
    - on_prometheus_alert:
        alert_name: KubePodCrashLooping
      actions:
        - collect_pod_logs: {}
        - get_pod_previous_logs: {}
        - get_related_events: {}
        - get_deployment_changes: {}
```

```bash
# Install Robusta via Helm
helm repo add robusta https://robusta-charts.storage.googleapis.com
helm repo update
helm install robusta robusta/robusta   --namespace robusta   --create-namespace   -f values.yaml

# Install Robusta CLI for management
pip install robusta-cli
robusta gen-config
```

### Key Playbooks

Robusta ships with 30+ built-in playbooks:

```python
# Example: Auto-restart deployment on OOMKilled
from robusta.api import *

@action
def restart_on_oom(alert: PrometheusKubernetesAlert, event: ExecutionBaseEvent):
    if alert.get_alert_metric_name() == "OOMKilled":
        deployment = alert.get_deployment()
        deployment.restart()
        alert.enrichment["action_taken"] = f"Restarted deployment {deployment.name}"
```

Additional built-in playbooks cover pod crash loops, node pressure alerts, PVC capacity warnings, certificate expiry checks, and HPA scaling events.

## Keptn: Cloud-Native Lifecycle Management

Keptn (400+ stars for lifecycle-toolkit, 3,500+ for main repo) is a CNCF project for event-driven cloud-native lifecycle management. It uses a control-plane architecture with GitOps integration to automate deployments, operations, and remediation through event-driven workflows.

### Keptn Lifecycle Toolkit Deployment

```yaml
apiVersion: lifecycle.keptn.sh/v1
kind: KeptnWorkload
metadata:
  name: order-service
spec:
  version: "2.1.0"
  preDeploymentTasks:
    - check-database-connectivity
  postDeploymentTasks:
    - run-smoke-tests
  postDeploymentEvaluations:
    - evaluate-performance-slo
---
apiVersion: lifecycle.keptn.sh/v1
kind: KeptnTaskDefinition
metadata:
  name: check-database-connectivity
spec:
  retries: 3
  timeout: 30
  container:
    name: db-check
    image: curlimages/curl:latest
    command:
      - curl
      - -f
      - http://database-service:5432/health
```

### Key Features

- **Pre/post deployment hooks** — run validation tasks before and after deployments
- **SLO-based evaluation** — automatically evaluate service level objectives after changes
- **Multi-stage delivery** — manage deployments across dev, staging, and production environments
- **Event-driven architecture** — CloudEvents-based communication between lifecycle stages
- **GitOps integration** — works with Argo CD and Flux for Git-driven deployments

## Goldilocks: VPA Recommendations Dashboard

Goldilocks (3,200+ stars) by Fairwinds provides a dashboard displaying Vertical Pod Autoscaler (VPA) recommendations alongside actual resource usage. While not an autonomous remediation platform, it enables data-driven resource optimization that prevents incidents caused by resource misconfiguration.

### Helm Deployment

```yaml
# values.yaml for Goldilocks
controller:
  extraArgs:
    on-by-default: true
  vpa:
    enabled: true
    updater:
      enabled: true
    recommender:
      enabled: true
    admissionController:
      enabled: true
    recommenders:
      - name: default

dashboard:
  ingress:
    enabled: true
    hosts:
      - goldilocks.example.com
```

```bash
# Install Goldilocks
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install goldilocks fairwinds-stable/goldilocks   --namespace goldilocks   --create-namespace   -f values.yaml

# Label namespaces for VPA tracking
kubectl label namespace default goldilocks.fairwinds.com/enabled=true
```

### Goldilocks Dashboard

The web dashboard displays each namespace with:
- Current resource requests and limits for every container
- VPA-recommended values based on historical usage
- Visual indicators showing over-provisioned and under-provisioned workloads
- Cost estimates for current vs recommended configurations

## Feature Comparison

| Feature | Robusta | Keptn Lifecycle Toolkit | Goldilocks |
|---------|---------|------------------------|------------|
| Primary focus | Alert enrichment + remediation | Deployment lifecycle management | Resource optimization |
| Automated actions | Yes (playbook execution) | Yes (pre/post deployment tasks) | No (recommendations only) |
| Prometheus integration | Native | Via metric providers | Via VPA recommender |
| Slack notifications | Native | Via webhooks | No |
| Auto-scaling remediation | Yes (HPA adjustments) | Via evaluations | VPA recommendations |
| Pod diagnostics | Auto log/event collection | Via custom tasks | No |
| Deployment rollback | Via playbooks | Via lifecycle hooks | No |
| Cost optimization | Basic | Via evaluations | Detailed dashboard |
| Installation complexity | Helm + Prometheus required | CRDs + controller | Helm + VPA CRDs |
| GitHub stars | 3,000+ | 400+ (toolkit), 3,500+ (main) | 3,200+ |
| CNCF status | Community | Graduated (Keptn) | Community (Fairwinds) |

## Combined Deployment Strategy

For comprehensive Kubernetes automation, these tools complement each other:

```yaml
# Complete automation stack - docker-compose for reference
# In practice, these run as Helm releases on the cluster
services:
  prometheus:
    # Metrics collection - feeds alerts to Robusta
  alertmanager:
    # Routes alerts to Robusta webhook
  robusta:
    # Enriches alerts, runs remediation playbooks
  keptn-lifecycle:
    # Manages deployment lifecycle, SLO evaluation
  goldilocks:
    # VPA recommendations for resource optimization
  grafana:
    # Visualization dashboard for all tools
```

The layered approach uses Goldilocks for proactive resource optimization (preventing incidents), Keptn for safe deployment lifecycles (preventing bad releases), and Robusta for reactive remediation (fixing issues when they occur).

## Why Self-Host Kubernetes Remediation Tools?

Running remediation platforms on self-hosted Kubernetes clusters eliminates the dependency on external SaaS tools that require cluster access credentials and incur per-node pricing. Self-hosted platforms keep diagnostic data (pod logs, events, deployment history) within your infrastructure — critical for compliance with data residency requirements. The cost savings are significant: managed Kubernetes observability platforms charge $50-200 per node per month, while self-hosted alternatives run on cluster resources you already pay for. For organizations operating Kubernetes at the edge or in air-gapped environments, self-hosted remediation is the only viable option.

For cluster-level hardening before deploying automation tools, see our [Kubernetes security guide](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/). If you need network-level protection for remediation webhooks, our [network policies guide](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies-guide/) covers isolation patterns. For advanced workload controllers that work alongside remediation platforms, check our [workload controllers comparison](../2026-05-17-self-hosted-kubernetes-workload-controllers-openkruise-argo-rollouts-flagger-guide/).

## FAQ

### What is the difference between Robusta and Prometheus Alertmanager?

Prometheus Alertmanager routes and deduplicates alerts based on labels and grouping rules. Robusta sits on top of Alertmanager and enriches those alerts with cluster context (pod logs, events, recent deployments) before forwarding them to notification channels. Robusta also executes remediation playbooks in response to alerts — automatically restarting deployments, collecting diagnostics, or scaling workloads. Alertmanager handles the routing; Robusta handles the intelligence and action.

### Can Keptn replace my CI/CD pipeline?

Keptn is not a CI/CD pipeline — it is a lifecycle management layer that operates alongside your existing pipeline. Keptn adds pre-deployment validation, post-deployment evaluation, and SLO checking to any deployment process. It integrates with Argo CD, Flux, Jenkins, and other CI/CD tools rather than replacing them. Think of Keptn as the quality gate and lifecycle coordinator, not the build and deploy engine.

### Does Goldilocks automatically apply VPA recommendations?

No, Goldilocks is a read-only dashboard that displays VPA recommendations alongside actual resource usage. It does not automatically apply changes to your workloads. To auto-apply recommendations, you would configure VPA in "Auto" mode (separate from Goldilocks), which adjusts pod resource requests based on historical usage patterns. Goldilocks provides the visibility to make informed decisions about whether to enable auto-mode.

### How does Robusta handle alert storms?

Robusta inherits Alertmanager's alert grouping and deduplication. When multiple related alerts fire (e.g., 10 pods in the same deployment crash-looping), Alertmanager groups them into a single notification. Robusta then enriches that grouped alert with diagnostics from all affected pods, providing a consolidated view of the incident rather than 10 separate messages. Custom playbooks can further aggregate related alerts by deployment, namespace, or node.

### What Kubernetes permissions does Robusta require?

Robusta needs read access to pods, deployments, events, and logs within the namespaces it monitors, plus write access to create enrichment records. The Helm chart configures a ClusterRole with appropriate RBAC permissions. For remediation playbooks that modify resources (restart deployments, scale HPAs), Robusta needs additional write permissions scoped to specific resource types. The principle of least privilege applies — grant only the permissions needed for your active playbooks.

### Can I use Robusta without Prometheus?

Robusta requires Prometheus as its alert source. It subscribes to Prometheus alerts via the Alertmanager webhook receiver. If you do not run Prometheus, you would need an alternative alert enrichment platform or integrate your existing monitoring system with Prometheus as a metrics bridge. Robusta also provides its own Prometheus deployment as part of the Helm chart for clusters that do not have Prometheus installed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Automated Remediation: Robusta vs Keptn vs Goldilocks",
  "description": "Compare Robusta, Keptn, and Goldilocks for self-hosted Kubernetes automated remediation, alert enrichment, and resource optimization.",
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
