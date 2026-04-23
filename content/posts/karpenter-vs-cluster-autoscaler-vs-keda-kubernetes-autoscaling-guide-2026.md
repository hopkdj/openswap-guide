---
title: "Karpenter vs Cluster Autoscaler vs KEDA: Kubernetes Autoscaling Guide 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "kubernetes", "autoscaling"]
draft: false
description: "Compare Karpenter, Cluster Autoscaler, and KEDA for Kubernetes autoscaling. Complete self-hosting guide with installation, configuration, and performance comparison."
---

## Why Kubernetes Autoscaling Matters

Running Kubernetes clusters without proper autoscaling means either over-provisioning (wasting money on idle nodes) or under-provisioning (services crash during traffic spikes). The right autoscaling strategy ensures your cluster dynamically adjusts to workload demands while minimizing costs.

Three projects dominate the Kubernetes autoscaling landscape, each with a fundamentally different approach:

- **Cluster Autoscaler** — the original, battle-tested node autoscaler from the Kubernetes project itself
- **Karpenter** — Amazon's next-generation node autoscaler built for speed and flexibility
- **KEDA** — event-driven pod autoscaler that scales workloads based on external triggers like message queues, HTTP requests, or cron schedules

Understanding when to use each tool — and how to combine them — is essential for anyone operating self-hosted Kubernetes clusters, whether on bare metal, VMware, or any cloud provider.

For a broader view of container orchestration options, see our [Kubernetes vs Docker Swarm vs Nomad comparison](../kubernetes-vs-docker-swarm-vs-nomad/) which covers the foundational platform choices before you even get to autoscaling.

## Cluster Autoscaler: The Original Node Autoscaler

[Cluster Autoscaler (CA)](https://github.com/kubernetes/autoscaler) is part of the official Kubernetes incubator project. It automatically adjusts the size of a Kubernetes cluster by adding nodes when pods fail to schedule due to insufficient resources, and removing nodes when they are underutilized.

### How Cluster Autoscaler Works

Cluster Autoscaler runs as a Deployment inside your cluster and periodically checks for pods that cannot be scheduled. When it finds unschedulable pods, it requests new nodes from your infrastructure provider (AWS Auto Scaling Groups, Azure VM Scale Sets, GCP Managed Instance Groups, or cloud-init scripts for bare metal). It also periodically checks for nodes that are underutilized and can be safely removed.

The key limitation: CA operates at the **node level only**. It knows nothing about individual pod resource needs — it simply sees "there are unschedulable pods, so I need more nodes."

### Installation via Helm

```bash
# Add the official autoscaler Helm repository
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update

# Install Cluster Autoscaler for AWS
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=my-cluster \
  --set awsRegion=us-east-1 \
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.skip-nodes-with-local-storage=false \
  --set extraArgs.skip-nodes-with-system-pods=false

# Install for generic cloud-provider (self-hosted)
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set cloudProvider=generic \
  --set extraArgs.node-group-auto-discovery=my-node-pool
```

### Key Configuration Parameters

| Parameter | Description | Default |
|---|---|---|
| `scale-down-delay-after-add` | How long to wait before scaling down after a scale-up | 10m |
| `scale-down-unneeded-time` | How long a node must be underutilized before removal | 10m |
| `scale-down-utilization-threshold` | CPU/memory threshold below which a node is considered underutilized | 0.5 |
| `max-node-provision-time` | Maximum time to wait for a new node to become ready | 15m |
| `balance-similar-node-groups` | Evenly distribute pods across similar node groups | false |

### Strengths and Weaknesses

**Strengths:**
- Mature and battle-tested (production use since 2016)
- Works across all major cloud providers and on-premises
- Deep integration with Kubernetes scheduler
- Supports pod disruption budgets and graceful node termination

**Weaknesses:**
- Slow provisioning cycles (typically 2-5 minutes to add a node)
- Requires pre-defined node groups with fixed instance types
- Cannot optimize for specific pod resource requirements
- Scale-down decisions are conservative and can leave idle nodes running

## Karpenter: Next-Generation Node Autoscaling

[Karpenter](https://github.com/aws/karpenter) was created by AWS to solve the fundamental limitations of Cluster Autoscaler. Instead of working within the constraints of predefined node groups, Karpenter observes pending pods and provisions exactly the right compute capacity — selecting instance types, sizes, and even purchase models (on-demand vs. spot) on the fly.

### How Karpenter Works

Karpenter watches the Kubernetes API server for pending pods that the scheduler cannot place. When it detects them, it evaluates its provisioner policies (defined as custom resources) and launches the optimal nodes to satisfy those pods. This happens in seconds, not minutes.

Karpenter's key innovation is **Just-In-Time (JIT) node provisioning**. Rather than maintaining a pool of pre-sized node groups, it selects from the full catalog of available instance types and launches exactly what's needed.

### Current Status

- **7,617 GitHub stars**
- Last updated: April 23, 2026
- Primary language: Go
- Default branch: main
- Supports AWS natively; Azure and bare-metal support via the NodePool API

### Installation

```bash
# Install Karpenter using Helm
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version 1.3.0 \
  --namespace karpenter \
  --create-namespace \
  --set settings.clusterName=my-cluster \
  --set settings.clusterEndpoint=https://my-cluster.example.com \
  --set serviceAccount.create=true \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789:role/KarpenterNodeRole

# Create a NodePool (the Karpenter equivalent of a node group)
cat <<'EOF' | kubectl apply -f -
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge", "c5.large", "c5.xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
EOF

# Create the EC2NodeClass
cat <<'EOF' | kubectl apply -f -
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2023
  role: KarpenterNodeRole
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
EOF
```

### Strengths and Weaknesses

**Strengths:**
- Extremely fast node provisioning (typically 30-60 seconds)
- Automatic instance type selection — no need to pre-define node groups
- Intelligent bin-packing across instance families
- Native spot instance support with automatic fallback to on-demand
- Consolidation removes underutilized nodes and reschedules pods

**Weaknesses:**
- Historically AWS-only (multi-cloud support is in progress)
- Requires IAM role configuration and VPC subnet tagging
- Less mature than Cluster Autoscaler — more frequent breaking changes
- Not suitable for environments without a supported cloud provider API

## KEDA: Event-Driven Pod Autoscaling

[KEDA (Kubernetes-based Event Driven Autoscaling)](https://github.com/kedacore/keda) takes a completely different approach. Instead of managing nodes, KEDA manages **pod replicas** based on external event sources. It is a CNCF graduated project and integrates natively with Kubernetes' Horizontal Pod Autoscaler (HPA).

### How KEDA Works

KEDA introduces two custom resource definitions (CRDs):

1. **ScaledObject** — defines how to scale a Deployment based on an external trigger
2. **ScaledJob** — defines how to scale a Kubernetes Job based on queue depth

KEDA acts as a Kubernetes Metrics Server. It queries external systems (RabbitMQ, Kafka, Redis, PostgreSQL, Azure Service Bus, AWS SQS, etc.) and exposes metrics that the Kubernetes HPA uses to scale pods up and down. Critically, KEDA can scale workloads **to and from zero**, meaning pods are completely terminated when there is no work to process.

### Current Status

- **10,127 GitHub stars** (largest of the three)
- Last updated: April 23, 2026
- Primary language: Go
- Default branch: main
- CNCF graduated project

### Installation

```bash
# Install KEDA via Helm
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

helm install keda kedacore/keda \
  --namespace keda \
  --create-namespace

# Verify installation
kubectl get pods -n keda
kubectl get crd | grep keda
```

### Example: Scaling a Worker Based on RabbitMQ Queue Depth

```yaml
# ScaledObject for RabbitMQ-triggered scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: rabbitmq-worker-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: order-processor
  pollingInterval: 10
  cooldownPeriod: 60
  minReplicaCount: 0
  maxReplicaCount: 30
  triggers:
    - type: rabbitmq
      metadata:
        protocol: amqp
        mode: QueueLength
        value: "10"
        targetQueueLength: "5"
        queueName: orders
        queueLength: "10"
      authenticationRef:
        name: rabbitmq-auth
---
# Authentication reference
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: rabbitmq-auth
  namespace: default
spec:
  secretTargetRef:
    - parameter: host
      name: rabbitmq-secret
      key: host
```

### Supported Event Sources (Scalers)

KEDA supports **60+ event sources**, including:

| Category | Scalers |
|---|---|
| Message Queues | RabbitMQ, Kafka, Redis, AWS SQS, Azure Service Bus, NATS |
| Databases | PostgreSQL, MySQL, MongoDB, Elasticsearch |
| HTTP | HTTP metrics, Prometheus metrics |
| Cloud | Azure Monitor, AWS CloudWatch, GCP Stackdriver |
| Streaming | Apache Pulsar, Kinesis, Event Hubs |
| Scheduling | Cron-based scaling |

### Strengths and Weaknesses

**Strengths:**
- Scale to zero — eliminates costs when workloads are idle
- 60+ event source connectors out of the box
- Works with any containerized workload (not just serverless functions)
- CNCF graduated — production-grade with strong community backing
- Cloud-agnostic — works on any Kubernetes cluster

**Weaknesses:**
- Only scales **pods**, not nodes — you still need CA or Karpenter for node-level autoscaling
- Requires configuration for each trigger source
- Some scalers require external credentials and network access
- Cannot directly influence infrastructure provisioning

## Head-to-Head Comparison

| Feature | Cluster Autoscaler | Karpenter | KEDA |
|---|---|---|---|
| **What it scales** | Nodes | Nodes | Pods |
| **Provisioning speed** | 2-5 minutes | 30-60 seconds | N/A (pod-level) |
| **Scale to zero** | No | No | Yes |
| **Instance type selection** | Pre-defined groups | Automatic JIT | N/A |
| **Spot instance support** | Manual config | Native | N/A |
| **Multi-cloud** | Yes | AWS primary, expanding | Yes |
| **Event-driven triggers** | No | No | 60+ connectors |
| **CNCF status** | Kubernetes subproject | Incubating | Graduated |
| **GitHub stars** | 8,828 | 7,617 | 10,127 |
| **Best for** | Stable, predictable workloads | Dynamic, spiky workloads | Event-driven, queue-based workloads |

## Combining All Three: The Recommended Architecture

The most powerful Kubernetes autoscaling setup uses these tools together, each handling a different layer:

```
┌─────────────────────────────────────────────────┐
│                   KEDA                          │
│   Scales pod replicas based on event sources    │
│   (RabbitMQ, Kafka, Cron, HTTP, Prometheus)     │
├─────────────────────────────────────────────────┤
│           Kubernetes HPA + VPA                  │
│   Standard pod-level resource-based scaling     │
├─────────────────────────────────────────────────┤
│         Karpenter or Cluster Autoscaler         │
│   Node-level provisioning and consolidation     │
├─────────────────────────────────────────────────┤
│              Infrastructure Layer               │
│   EC2 / VM Scale Sets / Bare Metal / EKS / AKS  │
└─────────────────────────────────────────────────┘
```

In this architecture:
1. **KEDA** monitors external event sources and scales pod replicas up when events arrive, or down to zero when the queue is empty
2. **Kubernetes HPA** handles CPU/memory-based scaling for stateless services
3. **Karpenter** (or Cluster Autoscaler) provisions nodes when new pods are pending and removes them when they are no longer needed
4. The **infrastructure layer** provides the actual compute resources

### Example: Combined Deployment

```yaml
# 1. Deploy your application
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-processor
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-processor
  template:
    metadata:
      labels:
        app: order-processor
    spec:
      containers:
        - name: processor
          image: myregistry/order-processor:v2.1
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
---
# 2. KEDA ScaledObject for event-driven pod scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-processor-scaler
  namespace: production
spec:
  scaleTargetRef:
    name: order-processor
  minReplicaCount: 0
  maxReplicaCount: 50
  triggers:
    - type: rabbitmq
      metadata:
        protocol: amqp
        queueName: orders
        queueLength: "20"
---
# 3. Karpenter NodePool for automatic node provisioning
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: production
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: production
  limits:
    cpu: 2000
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
```

If you are managing Kubernetes clusters at scale, you may also want to look at our [Rancher vs Kubespray vs Kind management guide](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) for cluster lifecycle management tools that complement your autoscaling setup.

For serverless and FaaS deployments that pair well with KEDA's event-driven model, see our [OpenFaaS vs Knative vs OpenWhisk comparison](../openfaas-vs-knative-vs-openwhisk-self-hosted-faas-serverless-guide-2026/).

## When to Use Each Tool

### Choose Cluster Autoscaler when:
- You run on-premises or bare-metal Kubernetes with cloud-init provisioning scripts
- Your workloads have predictable, stable resource requirements
- You need the most mature, battle-tested solution with minimal operational risk
- You are already using Kubernetes node groups and want minimal configuration changes
- You need support for multiple cloud providers with a single tool

### Choose Karpenter when:
- You run on AWS (or plan to) and want the fastest possible node provisioning
- Your workloads have spiky, unpredictable demand patterns
- You want to minimize costs through intelligent spot instance usage
- You want to eliminate the complexity of managing multiple node group configurations
- You need rapid scale-up for batch processing or CI/CD runner fleets

### Choose KEDA when:
- Your workloads are driven by external events (message queues, HTTP requests, cron schedules)
- You want to scale to zero when there is no work to process
- You run event-driven architectures or microservices with variable load
- You need fine-grained scaling based on business metrics (queue depth, lag, custom metrics)
- You want a cloud-agnostic solution that works across any Kubernetes distribution

### Use them together when:
- You want a complete autoscaling stack from events to infrastructure
- You have event-driven workloads (KEDA) running on dynamically provisioned nodes (Karpenter/CA)
- You want to optimize both pod count and node count for cost efficiency

## FAQ

### Can I run Karpenter and Cluster Autoscaler together?

Running both simultaneously is not recommended because they will compete for the same scaling decisions — both will try to add and remove nodes, leading to thrashing and unpredictable behavior. Choose one node autoscaler. Karpenter is generally preferred on AWS due to faster provisioning and better cost optimization. On other cloud providers or on-premises, Cluster Autoscaler remains the better choice.

### Does KEDA replace the Kubernetes Horizontal Pod Autoscaler (HPA)?

No, KEDA **extends** the HPA. KEDA acts as an external metrics server that provides custom metrics to the HPA. When you deploy a ScaledObject, KEDA automatically creates and manages the underlying HPA for you. You can still use the standard HPA for CPU and memory-based scaling alongside KEDA's event-driven triggers.

### Can KEDA scale nodes, or just pods?

KEDA only scales pod replicas. It has no ability to provision or remove nodes. If your cluster runs out of capacity when KEDA scales up pods, you will need a node-level autoscaler like Karpenter or Cluster Autoscaler to add nodes. This is why the recommended architecture uses KEDA at the pod layer and Karpenter or CA at the node layer.

### How much does Karpenter cost compared to Cluster Autoscaler?

Both tools are free and open-source. The cost savings come from how efficiently they use infrastructure. Karpenter typically saves 20-40% on compute costs compared to Cluster Autoscaler because it selects optimal instance types and leverages spot instances automatically. Cluster Autoscaler requires manual configuration of node groups and spot instance policies, often resulting in over-provisioned or suboptimally sized nodes.

### Is KEDA production-ready for high-traffic applications?

Yes. KEDA is a CNCF graduated project (the highest maturity level), which means it has undergone rigorous review for security, governance, and production readiness. It is used in production by organizations worldwide. The project has 10,000+ GitHub stars, active maintainer teams from Microsoft, Red Hat, and the broader community, and regular release cycles with security patches.

### How do I monitor autoscaling events?

For Cluster Autoscaler, check the logs with `kubectl logs -n kube-system deployment/cluster-autoscaler`. For Karpenter, use `kubectl logs -n karpenter deployment/karpenter` or query the `nodepool` and `nodeclaim` custom resources. For KEDA, monitor with `kubectl get scaledobject` and check the operator logs in the `keda` namespace. All three integrate with Prometheus for metrics export.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Karpenter vs Cluster Autoscaler vs KEDA: Kubernetes Autoscaling Guide 2026",
  "description": "Compare Karpenter, Cluster Autoscaler, and KEDA for Kubernetes autoscaling. Complete self-hosting guide with installation, configuration, and performance comparison.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
