---
title: "Kured vs Reloader vs Keel: Self-Hosted Kubernetes Automated Update & Restart Guide 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "kubernetes", "automation", "devops"]
draft: false
description: "Compare Kured, Reloader, and Keel — three essential open-source tools for automating Kubernetes node reboots, pod restarts on config changes, and container image updates in self-hosted clusters."
---

Managing a self-hosted Kubernetes cluster means dealing with constant change: OS patches that need node reboots, ConfigMap updates that require pod restarts, and new container images that must roll out to running deployments. Doing all of this manually is error-prone and time-consuming.

This guide compares three open-source Kubernetes operators that automate different aspects of cluster maintenance — each solving a specific piece of the puzzle.

## Why Automate Kubernetes Updates and Restarts?

In a production Kubernetes environment, three types of changes happen constantly:

1. **OS-level updates** — Kernel patches, security fixes, and package upgrades accumulate on worker nodes. Leaving nodes unpatched creates security vulnerabilities, but rebooting nodes manually risks downtime if done incorrectly.
2. **Configuration changes** — Updating a ConfigMap or Secret does not automatically restart the pods that consume them. Pods continue running with stale configuration until someone manually triggers a rollout.
3. **Container image updates** — When a new version of your application image is pushed to the registry, Kubernetes does not automatically pull and deploy it. Someone must update the Deployment spec or trigger a rolling update.

Without automation, cluster operators spend hours each week manually coordinating these tasks. Worse, skipping them leads to security gaps, configuration drift, and stale deployments. The three tools covered here — Kured, Reloader, and Keel — each handle one of these problems.

## Kured: Kubernetes Reboot Daemon

[Kured](https://github.com/kubereboot/kured) is a CNCF incubating project that handles automatic node reboots. It runs as a DaemonSet across all nodes and watches for the reboot sentinel file (`/var/run/reboot-required`) that most Linux package managers create after kernel or security updates.

**GitHub:** kubereboot/kured | **Stars:** 2,487 | **Last Updated:** April 2026

### How Kured Works

1. Each node runs a Kured pod that checks for the reboot sentinel file at configurable intervals.
2. When a sentinel is detected, Kured cordons the node (marks it unschedulable) and drains workloads to other nodes.
3. After a successful reboot, Kured uncordons the node so it can accept new workloads again.
4. A distributed lock in the Kubernetes API ensures only one node reboots at a time, maintaining cluster capacity.

Kured also supports optional safety checks: it can defer reboots when Prometheus alerts are firing or when specific critical pods are running, making it safe for production environments.

### Installing Kured via Helm

```bash
# Add the Kured Helm repository
helm repo add kured https://kubereboot.github.io/charts/
helm repo update

# Install Kured with default settings
helm install kured kured/kured \
  --namespace kube-system \
  --set configuration.rebootSentinelCommand="sh -c 'needs-restarting -r || [ ! -f /var/run/reboot-required ]'"

# Verify installation
kubectl get daemonset -n kube-system kured
```

### Installing Kured via kubectl

```bash
# Apply the official manifests directly
kubectl apply -f https://github.com/kubereboot/kured/releases/latest/download/kured-1.16.0.yaml

# Check the DaemonSet is running
kubectl get pods -n kube-system -l app.kubernetes.io/name=kured
```

### Key Configuration Options

```yaml
# kured-values.yaml
configuration:
  period: "1h"                    # Check interval
  startTime: "02:00"              # Only reboot between 2am-5am
  endTime: "05:00"
  timeZone: "UTC"
  rebootSentinelFile: "/var/run/reboot-required"
  lockTTL: "1h"                   # How long to hold the reboot lock
  extraArgs:
    pre-reboot-node-delay: "5m"   # Wait before rebooting
    drain-grace-period: "15m"     # Pod eviction grace period
    drain-timeout: "30m"          # Maximum time for drain
    lockAnnotation: "kured.lock"  # Custom lock annotation key
```

### When to Use Kured

- You run Ubuntu/Debian or RHEL/CentOS nodes that receive regular kernel updates
- You want automatic security patch reboots without manual intervention
- You need to ensure nodes reboot one at a time to maintain cluster capacity
- You want reboot windows restricted to off-peak hours

## Reloader: Automatic Pod Restarts on Config Changes

[Reloader](https://github.com/stakater/Reloader) by Stakater watches for changes to ConfigMaps and Secrets and automatically triggers rolling upgrades on the pods that reference them.

**GitHub:** stakater/Reloader | **Stars:** 10,000 | **Last Updated:** April 2026

### How Reloader Works

Reloader monitors the Kubernetes API for changes to ConfigMap and Secret resources. When a change is detected, it finds all Deployments, StatefulSets, and DaemonSets that reference the changed resource and triggers a rolling restart by updating an annotation on the pod template spec.

The key insight: Kubernetes does not restart pods when their ConfigMaps or Secrets change. Reloader fixes this gap without requiring application code changes or custom restart logic.

### Installing Reloader via Helm

```bash
# Add the Stakater Helm repository
helm repo add stakater https://stakater.github.io/stakater-charts
helm repo update

# Install Reloader
helm install reloader stakater/reloader \
  --namespace kube-system \
  --set reloader.watchGlobally=true
```

### Installing Reloader via kubectl

```bash
# Apply the official manifests
kubectl apply -f https://github.com/stakater/Reloader/releases/latest/download/reloader.yaml

# Verify the deployment
kubectl get deployment -n kube-system reloader-reloader
```

### Controlling Reloader Behavior

Reloader supports two modes: automatic (watch all resources) and annotation-based (only restart annotated resources).

```yaml
# Annotation mode — only restart these specific deployments
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  annotations:
    reloader.stakater.com/auto: "true"
spec:
  template:
    spec:
      containers:
        - name: my-app
          image: myapp:latest
          envFrom:
            - configMapRef:
                name: my-app-config
            - secretRef:
                name: my-app-secrets
```

```yaml
# Search mode — watch for specific ConfigMaps/Secrets
apiVersion: apps/v1
kind: Deployment
metadata:
  name: another-app
  annotations:
    reloader.stakater.com/search: "true"
    # This deployment restarts when config-shared changes
    configmap.reloader.stakater.com/reload: "config-shared"
    secret.reloader.stakater.com/reload: "tls-secret,db-credentials"
```

### Key Configuration Options

```yaml
# reloader-values.yaml
reloader:
  watchGlobally: true           # Watch all namespaces
  reloadStrategy: annotation    # Use annotation-based restarts
  isArgoRollouts: true          # Support Argo Rollouts
  secretBasedUpdatesEnabled: true
  readOnlyRootFileSystem: true
  resources:
    requests:
      cpu: 10m
      memory: 32Mi
    limits:
      cpu: 50m
      memory: 64Mi
```

### When to Use Reloader

- You manage many ConfigMaps and Secrets that change frequently
- You want pods to automatically pick up new configuration without manual `kubectl rollout restart`
- You need fine-grained control over which deployments restart (annotation mode)
- You use GitOps workflows where config changes are committed and applied automatically

## Keel: Automatic Container Image Updates

[Keel](https://github.com/keel-hq/keel) automates the deployment of new container image versions. When a new image tag is pushed to a registry, Keel detects the change and updates the corresponding Kubernetes resources.

**GitHub:** keel-hq/keel | **Stars:** 2,700 | **Last Updated:** February 2026

### How Keel Works

Keel monitors container registries (Docker Hub, GCR, AWS ECR, GitHub Container Registry) for new image tags. When a new version is detected, it updates the Deployment, DaemonSet, or StatefulSet with the new image tag, triggering a native Kubernetes rolling update.

Keel supports several update policies:
- **Polling** — Periodically check the registry for new tags
- **Webhook** — Registry sends a notification to Keel when a new image is pushed
- **Semver** — Only update to versions matching a semantic version constraint

### Installing Keel via Helm

```bash
# Add the Keel Helm repository
helm repo add keel https://charts.keel.sh
helm repo update

# Install Keel
helm install keel keel/keel \
  --namespace keel \
  --create-namespace \
  --set metrics.enabled=true
```

### Installing Keel with Docker Compose

For those running Keel alongside a local Kubernetes cluster (e.g., kind or k3s):

```yaml
# docker-compose.yml
services:
  keel:
    image: keelhq/keel:latest
    container_name: keel
    environment:
      - KUBERNETES_SERVICE_HOST=host.docker.internal
      - KUBERNETES_SERVICE_PORT=6443
      - BASIC_AUTH_USER=admin
      - BASIC_AUTH_PASSWORD=changeme
    volumes:
      - ~/.kube/config:/root/.kube/config
    ports:
      - '9300:9300'
    restart: unless-stopped
```

```bash
# Start Keel
docker compose up -d

# Access the dashboard
open http://localhost:9300
```

### Configuring Image Update Policies

```yaml
# Example: Auto-update to latest patch versions only
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  annotations:
    keel.sh/policy: "patch"           # Update on patch releases (1.2.3 -> 1.2.4)
    keel.sh/trigger: "poll"            # Use polling (check every 2 minutes)
    keel.sh/match-tag: "true"          # Only update matching tags
spec:
  template:
    spec:
      containers:
        - name: my-app
          image: myapp:1.2.3           # Will update to 1.2.4, 1.2.5, etc.
```

```yaml
# Example: Webhook-based updates (immediate)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  annotations:
    keel.sh/policy: "all"              # Update on any new tag
    keel.sh/trigger: "push"            # Triggered by registry webhook
    keel.sh/force: "true"              # Force update even if pods are running
spec:
  template:
    spec:
      containers:
        - name: web-app
          image: registry.example.com/web-app:v1.0.0
```

### Keel Webhook Integration

Configure your registry to send webhooks to Keel for immediate updates:

```bash
# Docker Hub webhook setup (via Docker Hub settings)
# Target URL: http://keel.keel.svc.cluster.local:9300/v1/webhooks/dockerhub

# Harbor webhook (via Harbor project settings)
# Target URL: http://keel.keel.svc.cluster.local:9300/v1/webhooks/harbor
```

### When to Use Keel

- You push new container images frequently and want automatic deployments
- You want semantic version constraints (only update patches, not major versions)
- You need webhook-based updates for near-instant deployment after a push
- You run a CI/CD pipeline that builds and pushes images, and want Keel to handle the deploy step

## Feature Comparison Table

| Feature | Kured | Reloader | Keel |
|---|---|---|---|
| **Primary Purpose** | Node reboots | Pod restarts | Image updates |
| **Trigger** | OS sentinel file | ConfigMap/Secret change | New image tag |
| **Scope** | Node level | Pod/Deployment level | Deployment/StatefulSet level |
| **Installation** | Helm, kubectl | Helm, kubectl | Helm, Docker Compose |
| **Webhook Support** | No | No | Yes |
| **Semver Policies** | No | No | Yes |
| **Rolling Updates** | Cordon + drain | Annotation-based | Native rolling update |
| **Concurrency Control** | API lock (one node at a time) | None needed | Per-deployment |
| **Time Windows** | Yes (start/end time) | No | No |
| **Dashboard** | No | No | Yes (port 9300) |
| **GitHub Stars** | 2,487 | 10,000 | 2,700 |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Using All Three Tools Together

For a fully automated self-hosted Kubernetes cluster, you can deploy all three tools. They operate at different layers and do not conflict:

```bash
# 1. Install Kured for safe node reboots
helm install kured kured/kured --namespace kube-system \
  --set configuration.startTime="02:00" \
  --set configuration.endTime="05:00"

# 2. Install Reloader for config-driven pod restarts
helm install reloader stakater/reloader --namespace kube-system \
  --set reloader.watchGlobally=true

# 3. Install Keel for automatic image updates
helm install keel keel/keel --namespace keel --create-namespace
```

With this setup:

- **Kured** handles OS-level maintenance — when the package manager signals a reboot is needed, the node safely reboots during the maintenance window.
- **Reloader** handles configuration changes — when you update a ConfigMap or Secret via GitOps, pods automatically restart with the new values.
- **Keel** handles application updates — when CI/CD pushes a new container image, the deployment rolls out automatically.

This combination gives you a cluster that stays patched, configured correctly, and up-to-date — all without manual intervention.

## Choosing the Right Tool for Your Setup

| Scenario | Recommended Tool(s) |
|---|---|
| You only need automatic node reboots after kernel updates | Kured |
| Your main pain point is stale ConfigMaps/Secrets | Reloader |
| You want automatic deployments after CI/CD image pushes | Keel |
| You run a GitOps workflow and want config sync | Reloader + Kured |
| You want a fully automated self-hosted cluster | All three |
| You manage multiple namespaces with different config needs | Reloader (annotation mode) |
| You need strict version control for image updates | Keel (semver policy) |
| You have compliance requirements for maintenance windows | Kured (time windows) |

## Pre-Deployment Checklist

Before deploying any of these tools in production:

1. **Test in a staging cluster first** — Verify that reboots, restarts, and image updates behave as expected.
2. **Set up monitoring** — Watch for failed drains (Kured), stuck rollouts (Reloader), or failed image pulls (Keel).
3. **Configure alerts** — Use Prometheus alerts to notify when a node has been waiting to reboot for too long or when an image update fails.
4. **Document your policies** — Make sure your team understands which tool manages which aspect of cluster automation.
5. **Test failure scenarios** — What happens if Kured reboots while a backup is running? What if Reloader restarts during a database migration? Plan for these edge cases.

For related reading, see our [Kubernetes secrets management guide](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) for securing the ConfigMaps and Secrets that Reloader watches, the [Kubernetes CNI comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) for networking setup, and our [Kubernetes cost monitoring guide](../opencost-vs-goldilocks-vs-crane-kubernetes-cost-monitoring-guide-2026/) to keep automated clusters within budget.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kured vs Reloader vs Keel: Self-Hosted Kubernetes Automated Update & Restart Guide 2026",
  "description": "Compare Kured, Reloader, and Keel — three essential open-source tools for automating Kubernetes node reboots, pod restarts on config changes, and container image updates in self-hosted clusters.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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

### What is the difference between Kured, Reloader, and Keel?

Kured handles **node-level reboots** when the OS needs a restart after kernel or security updates. Reloader handles **pod-level restarts** when ConfigMaps or Secrets change. Keel handles **deployment-level updates** when new container images are pushed to a registry. They operate at different layers of the Kubernetes stack and can be used together without conflict.

### Does Kured work with all Linux distributions?

Kured works with most major Linux distributions including Ubuntu, Debian, RHEL, CentOS, and Fedora. It detects the need for a reboot by checking for the sentinel file `/var/run/reboot-required` (created by unattended-upgrades on Debian/Ubuntu) or by running a configurable command like `needs-restarting -r` on RHEL/CentOS. You can also configure a custom sentinel command for other distributions.

### Can Reloader restart pods without annotations?

Yes. When `watchGlobally: true` is set (the default), Reloader automatically restarts any pod that references a changed ConfigMap or Secret. If you want more control, set `reloadStrategy: annotation` and only annotated deployments will be restarted. This is useful in multi-tenant clusters where you want to prevent unintended restarts.

### How does Keel handle image pull failures?

Keel triggers a Kubernetes rolling update by updating the Deployment spec with the new image tag. If the image pull fails (wrong tag, missing credentials, network issue), Kubernetes handles the failure — the old pods continue running and the rollout stalls. Keel does not roll back automatically; you need to monitor your deployments and fix the image issue manually or through your CI/CD pipeline.

### Can I restrict Kured to only reboot during maintenance windows?

Yes. Kured supports `startTime` and `endTime` configuration options to define a maintenance window. For example, setting `startTime: "02:00"` and `endTime: "05:00"` ensures nodes only reboot between 2 AM and 5 AM. You can also set `timeZone` to match your local timezone. Additionally, Kured can be configured to defer reboots when specific Prometheus alerts are active.

### Do I need cluster-admin permissions to install these tools?

Yes, all three tools require cluster-level permissions. Kured runs as a DaemonSet in `kube-system` and needs access to node resources. Reloader watches ConfigMaps and Secrets cluster-wide and needs permission to update Deployment specs. Keel manages Deployments across namespaces. In all cases, install them using a user with cluster-admin or equivalent RBAC permissions.

### Which tool should I install first?

If you are setting up a new self-hosted Kubernetes cluster, install **Kured first** to ensure nodes can safely reboot after OS updates. Then add **Reloader** to handle configuration changes. Finally, add **Keel** when your CI/CD pipeline is ready to push images and you want automatic deployments. This order ensures the foundational layer (node health) is covered before adding higher-level automation.
