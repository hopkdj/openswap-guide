---
title: "Argo Events vs Brigade vs Keptn: Best Self-Hosted Event-Driven Kubernetes Automation 2026"
date: "2026-05-08"
tags: ["kubernetes", "event-driven", "automation", "argoproj", "brigade", "keptn", "devops", "gitops"]
draft: false
---

Event-driven architectures are becoming the backbone of modern cloud-native operations. Instead of polling for changes or running scheduled jobs, event-driven Kubernetes platforms react to real-time triggers — webhook deliveries, file system changes, message queue events, Git commits, and monitoring alerts. This guide compares three leading open-source event-driven automation frameworks for Kubernetes: **Argo Events**, **Brigade**, and **Keptn**.

## What Are Event-Driven Kubernetes Workflows?

Traditional CI/CD pipelines are linear and scheduled. Event-driven workflows are reactive and dynamic. A webhook from GitHub triggers a build. A new file in an S3 bucket launches a data processing job. A Prometheus alert initiates auto-remediation. These frameworks provide the plumbing to detect events, route them to handlers, and execute Kubernetes-native workloads in response.

The three platforms we compare take different architectural approaches:

- **Argo Events** is an event dependency manager built by the Argo project (CNCF). It uses a Kubernetes-native CRD approach with EventSources and Sensors to define event-to-action pipelines.
- **Brigade** (by Brigade project, originally from Microsoft Azure) is an event-driven scripting platform that runs JavaScript/TypeScript scripts as first-class Kubernetes workloads triggered by events.
- **Keptn** (by Dynatrace, formerly CNCF sandbox) is a cloud-native application life-cycle orchestration platform focused on SLO-driven multi-stage delivery, operations, and remediation.

## Comparison Table

| Feature | Argo Events | Brigade | Keptn |
|---------|-------------|---------|-------|
| **GitHub Stars** | 2,650+ | 2,400+ | 1,770+ |
| **Last Active** | 2026 | 2023 | 2023 |
| **Language** | Go | JavaScript/TypeScript | Go |
| **Event Sources** | 20+ built-in (webhook, calendar, S3, Kafka, GitHub, Slack, etc.) | 20+ gateways (webhook, timer, S3, GitHub, Docker Hub, etc.) | Pluggable via Keptn integrations |
| **Execution Model** | Sensor triggers Kubernetes workloads (Jobs, Argo Workflows) | JavaScript/TypeScript scripts as Kubernetes Jobs | Sequences and stages with automated quality gates |
| **Kubernetes Native** | Yes (CRDs: EventBus, EventSource, Sensor) | Yes (CRDs: Project, Event, Worker) | Yes (CRDs: Shipyard, Stage) |
| **CNCF Status** | Graduated (part of Argo) | Sandbox (independent) | Sandbox |
| **Scalability** | Horizontal via NATS/JetStream EventBus | Per-project workers, scales with K8s | Horizontal via Keptn distributor |
| **Quality Gates** | Via Argo Workflows integration | Script-based | Built-in SLO evaluation |
| **Dashboard UI** | Argo Events UI (separate) | Brigade UI (limited) | Keptn's Bridge (full-featured) |
| **Multi-Stage Delivery** | Via Argo Workflows pipelines | Via scripted pipelines | Native shipyard definitions |
| **Community Activity** | Very active | Maintenance mode | Maintenance mode |

## Argo Events: The Kubernetes Event Dependency Manager

Argo Events is the event-driven automation framework within the Argo project (alongside Argo CD, Argo Workflows, and Argo Rollouts). It follows the EventSource → EventBus → Sensor pattern:

1. **EventSource** detects and consumes events from external systems (webhooks, S3, Kafka, GitHub, GitLab, Slack, NATS, etc.)
2. **EventBus** (NATS or JetStream) routes events reliably
3. **Sensor** subscribes to events and triggers actions (Kubernetes resources, Argo Workflows, webhooks, etc.)

### Docker Compose Deployment

Argo Events is deployed via Helm on Kubernetes. Here's a minimal deployment:

```yaml
# Install Argo Events via kubectl
kubectl create namespace argo-events
kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml
```

```yaml
# EventSource: GitHub webhook receiver
apiVersion: argoproj.io/v1alpha1
kind: EventSource
metadata:
  name: github
  namespace: argo-events
spec:
  webhook:
    github-push:
      port: "12000"
      endpoint: "/push"
      method: POST
```

```yaml
# Sensor: Trigger Argo Workflow on GitHub push
apiVersion: argoproj.io/v1alpha1
kind: Sensor
metadata:
  name: github-sensor
  namespace: argo-events
spec:
  template:
    serviceAccountName: operate-workflow-sa
  dependencies:
    - name: github-dep
      eventSourceName: github
      eventName: github-push
  triggers:
    - template:
        name: github-workflow-trigger
        argoWorkflow:
          operation: submit
          source:
            resource:
              apiVersion: argoproj.io/v1alpha1
              kind: Workflow
              metadata:
                generateName: ci-build-
              spec:
                entrypoint: build
                templates:
                  - name: build
                    container:
                      image: alpine:latest
                      command: [sh, -c, "echo Building from event"]
```

Argo Events excels when you need complex event dependency logic — "trigger this workflow only when events A AND B have occurred" or "trigger when event A OR event B fires."

## Brigade: Event-Driven Scripting as Code

Brigade treats event-driven automation as a scripting problem. Each Brigade project has a `brigade.js` or `brigade.ts` file that defines event handlers. When an event arrives, Brigade spins up a Kubernetes worker pod that executes the matching script.

### Docker Compose / Helm Deployment

```bash
# Install Brigade v2 via Helm
helm repo add brigade https://brigadecore.github.io/charts
helm install brigade brigade/brigade --namespace brigade --create-namespace
```

```javascript
// brigade.ts - Event handler script
import { events, Job } from "@brigadecore/brigade";

events.on("github", "push", async (event) => {
  const job = new Job("build", "alpine:latest", event);
  job.primaryContainer.command = ["sh"];
  job.primaryContainer.arguments = [
    "-c",
    `echo "Processing push to ${event.source}"`
  ];
  await job.run();
});

events.on("timer", "schedule", async (event) => {
  const job = new Job("cleanup", "alpine:latest", event);
  job.primaryContainer.command = ["sh"];
  job.primaryContainer.arguments = ["-c", "echo Running scheduled cleanup"];
  await job.run();
});
```

Brigade's strength is developer familiarity — if you know JavaScript, you can write event-driven automation. The scripting model is more flexible than declarative CRDs for complex conditional logic.

## Keptn: SLO-Driven Multi-Stage Delivery

Keptn takes a higher-level approach. Instead of wiring individual events to actions, Keptn manages the entire application life-cycle through **shipyards** — declarative definitions of multi-stage delivery pipelines with automated quality gates.

### Helm Deployment

```bash
# Install Keptn via Helm
helm install keptn keptn/kubernetes --namespace keptn --create-namespace \
  --set=control-plane.enabled=true \
  --set=execution-plane.enabled=true
```

```yaml
# shipyard.yaml - Multi-stage delivery pipeline
apiVersion: spec.keptn.sh/0.2.0
kind: Shipyard
metadata:
  name: shipyard-demo
spec:
  stages:
    - name: dev
      sequences:
        - name: delivery
          tasks:
            - name: deployment
              properties:
                deploymentstrategy: direct
            - name: test
              properties:
                teststrategy: functional
    - name: staging
      sequences:
        - name: delivery
          triggeredOn:
            - event: dev.delivery.finished
          tasks:
            - name: deployment
              properties:
                deploymentstrategy: blue_green_service
            - name: evaluation
              properties:
                pass: "90%"
                warning: "75%"
            - name: approval
              properties:
                pass: "manual"
                warning: "manual"
    - name: production
      sequences:
        - name: delivery
          triggeredOn:
            - event: staging.delivery.finished
          tasks:
            - name: deployment
              properties:
                deploymentstrategy: blue_green
            - name: release
```

Keptn shines for teams that need automated promotion pipelines with quality gates based on SLOs, SLIs, and automated test results.

## Choosing the Right Event-Driven Framework

| Use Case | Recommended Tool |
|----------|-----------------|
| Complex event dependency logic | Argo Events |
| JavaScript-based scripting workflows | Brigade |
| Multi-stage delivery with quality gates | Keptn |
| GitOps-triggered automation | Argo Events + Argo CD |
| Automated remediation from monitoring alerts | Argo Events or Keptn |
| Simple webhook-to-job pipelines | Brigade |
| Enterprise multi-stage delivery | Keptn |

### Important Maintenance Note

Both **Brigade** and **Keptn** have seen reduced commit activity since 2023. Brigade's last major release was v2.3 in early 2023, and Keptn's core development slowed in late 2023. **Argo Events** remains actively maintained as part of the CNCF-graduated Argo project. For greenfield projects, Argo Events is the safest long-term choice. For existing Brigade or Keptn installations, both remain functional and production-ready.

## Why Self-Host Event-Driven Kubernetes Automation?

Running event-driven automation on your own Kubernetes cluster gives you full control over how events are processed, where data flows, and what actions are triggered. Unlike SaaS automation platforms (Zapier, Make, GitHub Actions cloud), self-hosted event-driven frameworks:

- **Keep sensitive data on-premises** — webhooks, secrets, and payload data never leave your infrastructure
- **Eliminate per-execution costs** — SaaS event platforms charge per trigger; self-hosted runs on your existing K8s capacity
- **Enable custom event sources** — integrate with internal systems, proprietary APIs, and on-premises services that SaaS platforms cannot reach
- **Provide audit trails** — all event processing is logged within your cluster, satisfying compliance requirements

For organizations already running Kubernetes for [GitOps deployment automation](../argocd-vs-flux-self-hosted-gitops-guide/), adding an event-driven layer enables fully automated, reactive infrastructure — from auto-scaling based on custom metrics to automated incident response triggered by monitoring alerts. Teams managing [CI/CD pipelines](../2026-04-19-woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide/) can use event-driven workflows to trigger builds from non-Git sources like S3 uploads or message queue events.

## FAQ

### What is the difference between Argo Events and Argo Workflows?

Argo Events detects and routes external events to triggers. Argo Workflows executes those triggers as container-based workflows. Together, they form a complete event-to-workflow pipeline: an EventSource detects an event, a Sensor maps it to an Argo Workflow, and Argo Workflows runs the actual steps.

### Can Brigade run non-JavaScript workloads?

Yes. Brigade scripts define jobs that can run any container image. The scripting layer is JavaScript/TypeScript, but the actual workload containers can be anything — Python, Go, bash scripts, or custom Docker images. The script orchestrates which containers run and in what order.

### Does Keptn replace CI/CD tools like Jenkins or GitLab CI?

No. Keptn orchestrates the delivery stages (deploy → test → evaluate → approve → release) but does not build or compile code. It integrates with existing CI systems via webhooks. The CI tool builds the artifact; Keptn manages the multi-stage rollout with quality gates.

### What event sources does Argo Events support?

Argo Events supports 20+ built-in event sources including: webhook, calendar (cron), AWS S3, AWS SNS, AWS SQS, Kafka, NATS, GitHub, GitLab, Slack, MQTT, Redis Streams, Azure Event Hubs, GCP Pub/Sub, and more. Custom event sources can also be defined.

### Is Keptn still maintained?

Keptn entered maintenance mode in late 2023. The core platform remains stable and production-ready, but new feature development has slowed. The community continues to maintain integrations and bug fixes. For new projects, evaluate whether the existing feature set meets your needs or if Argo Events provides a more actively developed alternative.

### How does Argo Events handle high-throughput event processing?

Argo Events uses NATS or JetStream as its EventBus, which provides durable message queues with at-least-once delivery guarantees. Under heavy load, you can scale the Sensor pods horizontally and use JetStream's streaming capabilities to buffer events. The EventBus is the critical scaling component.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Argo Events vs Brigade vs Keptn: Best Self-Hosted Event-Driven Kubernetes Automation 2026",
  "description": "Compare Argo Events, Brigade, and Keptn for self-hosted event-driven Kubernetes automation. Learn which framework best fits your CI/CD, GitOps, and reactive infrastructure needs.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
