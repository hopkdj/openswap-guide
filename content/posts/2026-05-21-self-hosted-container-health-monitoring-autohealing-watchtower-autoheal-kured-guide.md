---
title: "Self-Hosted Container Health Monitoring & Auto-Healing: Watchtower vs Autoheal vs Kured (2026 Guide)"
date: "2026-05-21"
tags: ["docker", "kubernetes", "container-health", "watchtower", "autoheal", "kured", "auto-healing"]
draft: false
---

Containers are designed to be ephemeral — when one fails, the orchestrator replaces it. But what happens when a container is running but unhealthy? Or when a new image is published and your running containers are stuck on a vulnerable old version? Or when a Kubernetes node needs to reboot for a kernel security update?

This guide compares three self-hosted tools that solve different aspects of container health monitoring and automated remediation: **Watchtower** (automatic Docker container image updates), **Autoheal** (Docker container health monitoring and restart), and **Kured** (Kubernetes node reboot management for security updates). Together, these tools form a comprehensive container health management stack.

For broader container monitoring strategies, see our [Docker container monitoring comparison](../2026-04-28-cadvisor-vs-dozzle-vs-netdata-self-hosted-docker-container-monitoring-guide/) and [Kubernetes node management guide](../2026-05-01-node-problem-detector-vs-node-feature-discovery-vs-goldilocks-kubernetes-node-management/).

## Quick Comparison Table

| Feature | Watchtower | Autoheal | Kured |
|---------|-----------|----------|-------|
| **Stars** | 15,500+ | 2,300+ | 2,541 |
| **Platform** | Docker | Docker | Kubernetes |
| **Purpose** | Auto-update containers | Auto-restart unhealthy containers | Auto-reboot nodes for updates |
| **Trigger** | New image in registry | Health check failure | Reboot required file |
| **Update Strategy** | Pull & replace container | Restart container | Cordon & drain, then reboot |
| **Rollback** | No | No (restart only) | Automatic (via node reboot) |
| **Scheduling** | Cron-based or polling | Continuous monitoring | Continuous monitoring |
| **Notification** | Slack, email, webhook, Gotify | Log-based | Kubernetes events |
| **Graceful Shutdown** | Yes (SIGTERM then SIGKILL) | Yes | Yes (cordon + drain) |
| **Docker Compose** | Single container | Single container | Helm chart / K8s manifest |
| **Image Filtering** | Labels, include/exclude | Labels, health status | Not applicable |
| **License** | Apache 2.0 | MIT | Apache 2.0 |

## Watchtower: Automatic Docker Image Updates

Watchtower monitors your Docker containers for new image versions and automatically pulls and restarts them. It is the simplest way to keep your self-hosted services up to date without manual intervention.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_POLL_INTERVAL=300
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_LABEL_ENABLE=true
      - WATCHTOWER_NOTIFICATIONS=slack
      - WATCHTOWER_NOTIFICATION_SLACK_HOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
```

### Key Watchtower Configuration Options

| Environment Variable | Purpose | Default |
|---------------------|---------|---------|
| `WATCHTOWER_POLL_INTERVAL` | Seconds between checks | 86400 (24h) |
| `WATCHTOWER_CLEANUP` | Remove old images after update | false |
| `WATCHTOWER_LABEL_ENABLE` | Only update containers with watchtower label | false |
| `WATCHTOWER_INCLUDE_RESTARTING` | Include restarting containers in checks | false |
| `WATCHTOWER_NOTIFICATIONS` | Notification channel | empty |
| `WATCHTOWER_SCHEDULE` | Cron schedule for checks | empty (polling) |

### Selective Auto-Update with Labels

The safest approach is to enable label-based filtering so Watchtower only updates containers you explicitly mark:

```yaml
services:
  my-app:
    image: myregistry/my-app:1.2.3
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    restart: unless-stopped

  my-critical-db:
    image: postgres:16
    restart: unless-stopped
    # No watchtower label — will NOT be auto-updated
```

This prevents Watchtower from accidentally updating critical services like databases that require manual migration steps.

## Autoheal: Container Health Check Remediation

Autoheal monitors Docker containers for health check failures and automatically restarts unhealthy containers. While Watchtower updates containers when new images are available, Autoheal acts when containers are running but unhealthy — a fundamentally different problem.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  autoheal:
    image: willfarrell/autoheal:latest
    container_name: autoheal
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - AUTOHEAL_CONTAINER_LABEL=all
      - AUTOHEAL_INTERVAL=30
      - AUTOHEAL_DEFAULT_STOP_TIMEOUT=10
```

### How Autoheal Works

Autoheal queries the Docker API for all containers that have health checks defined. It monitors the health status and takes action when a container transitions to `unhealthy`:

```yaml
services:
  web-app:
    image: myregistry/web-app:latest
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    labels:
      - "autoheal=true"
```

When `web-app` fails its health check 3 consecutive times, Autoheal restarts it. The `AUTOHEAL_DEFAULT_STOP_TIMEOUT` gives the container time to gracefully shut down before a hard kill.

### When to Use Autoheal vs Watchtower

| Scenario | Watchtower | Autoheal |
|----------|-----------|----------|
| New image published upstream | Updates container | No action |
| Application crashes / hangs | No action | Restarts container |
| Health endpoint returns 500 | No action | Restarts container |
| Container exits with code 1 | No action | Docker restarts (not Autoheal) |
| Image tag is updated | Updates container | No action |

Use both tools together: Watchtower keeps your images current, Autoheal keeps your running containers healthy.

## Kured: Kubernetes Node Reboot Orchestration

Kured (Kubernetes Reboot Daemon) solves a different problem entirely — rebooting Kubernetes nodes safely when security updates require it. Unlike Watchtower and Autoheal which operate at the container level, Kured operates at the node (host) level.

### Deployment via Helm

```yaml
# kured-values.yaml
configuration:
  rebootSentinelCommand: sh -c "! needs-restarting --reboothint"
  period: 1h5m
  drainTimeout: 2h
  lockAnnotation: kured.lock
  dsNamespace: kured
  extraArgs:
    blocking-pod-selector:
      - "app=database"
    slackHookURL: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    slackChannel: "#infrastructure"
```

```bash
helm install kured kured   --repo https://kubereboot.github.io/charts/   --namespace kured   --create-namespace   -f kured-values.yaml
```

### How Kured Works

Kured runs as a DaemonSet on every Kubernetes node. Its workflow is:

1. **Check for reboot requirement**: Runs the configured sentinel command (e.g., checking if `/var/run/reboot-required` exists on Debian/Ubuntu, or if `needs-restarting --reboothint` returns true on RHEL/CentOS).
2. **Acquire a lock**: Only one node reboots at a time to maintain cluster capacity.
3. **Cordon the node**: Mark the node unschedulable so no new pods are placed on it.
4. **Drain the node**: Evict all pods gracefully, respecting PodDisruptionBudgets.
5. **Reboot the node**: Execute the reboot.
6. **Wait for node to return**: Monitor until the node is Ready again.
7. **Release the lock** and move to the next node.

### Kured Configuration Options

```yaml
configuration:
  # How often to check for reboot requirements
  period: 1h5m

  # Maximum time to wait for pod eviction
  drainTimeout: 2h

  # Only reboot during maintenance windows
  rebootDays: "mon,tue,wed,thu"
  rebootStartTime: "02:00"
  rebootEndTime: "04:00"

  # Block reboot if these pods are running
  blockingPodSelector:
    - "app=critical-database"
    - "role=stateful"

  # Pre-reboot and post-reboot hooks
  preRebootNodeShell: "kubectl cordon $NODE_NAME"
  postRebootNodeShell: "kubectl uncordon $NODE_NAME"
```

## Combined Container Health Stack

For a comprehensive container health management approach across both Docker and Kubernetes environments:

| Layer | Tool | Responsibility |
|-------|------|----------------|
| **Docker image updates** | Watchtower | Auto-pull new images, restart containers |
| **Docker health remediation** | Autoheal | Restart unhealthy containers |
| **Kubernetes node maintenance** | Kured | Safe node reboots for security patches |
| **Container monitoring** | cadvisor/Dozzle | Visibility into container resource usage |
| **Kubernetes pod health** | Native probes | Liveness/readiness probes + restart policy |

This stack ensures that containers stay updated, unhealthy containers get restarted, and nodes receive security patches without manual intervention.

## Why Self-Host Container Health Tools?

Self-hosting container health and auto-healing tools gives you complete control over update policies, maintenance windows, and notification routing. Cloud-based container management platforms often enforce their own update schedules and notification channels. With self-hosted tools, you decide when containers update, which services get auto-healed, and how your team gets alerted.

For organizations with compliance requirements, self-hosted tools ensure that update and reboot logs stay within your infrastructure. You can integrate with internal ticketing systems, custom Slack channels, or on-call rotation tools like Grafana OnCall — integrations that cloud platforms may not support.

For related infrastructure automation, see our [Kubernetes automated update and restart guide](../2026-04-29-kured-vs-reloader-vs-keel-kubernetes-automated-update-restart-guide/) which covers kured, Reloader, and Keel for Kubernetes automation patterns.

## FAQ

### Q: Is Watchtower safe for production use?

Watchtower is safe when used with label-based filtering and proper testing. The key risk is updating a container to a new image that has breaking changes or bugs. Mitigation strategies: (1) Use `WATCHTOWER_LABEL_ENABLE=true` so only explicitly labeled containers are updated. (2) Pin database containers to specific versions without auto-update labels. (3) Set up notifications so you know when updates happen. (4) Test new image versions in a staging environment before they reach production registries.

### Q: Can Autoheal cause restart loops?

Yes, if a container has a persistent bug that causes health check failures, Autoheal will restart it indefinitely. To prevent this: (1) Set a reasonable health check `start_period` to give the container time to initialize. (2) Monitor restart counts — Autoheal logs each restart. (3) Use Docker's built-in `restart: unless-stopped` policy with a maximum retry count. (4) Alert on high restart frequency so you can investigate the root cause rather than relying on Autoheal as a band-aid.

### Q: Does Kured work with cloud-managed Kubernetes (EKS, GKE, AKS)?

Kured works best with self-managed Kubernetes clusters where you control the node OS. For cloud-managed Kubernetes: EKS Managed Node Groups handle OS patching automatically. GKE Auto-Upgrade handles node reboots. AKS Automatic Cluster Node Maintenance handles patching. If you use self-managed node groups or self-managed Kubernetes on cloud VMs, Kured is still useful for coordinating safe reboots across your node pool.

### Q: How do I prevent Watchtower from updating containers during business hours?

Use the `WATCHTOWER_SCHEDULE` environment variable with a cron expression:
```yaml
environment:
  - WATCHTOWER_SCHEDULE=0 0 2 * * *
```
This runs Watchtower checks only at 2:00 AM. You can also combine this with `WATCHTOWER_NOTIFICATIONS` to receive a summary of what was updated each morning.

### Q: What happens if Kured fails to drain a node?

Kured respects PodDisruptionBudgets (PDBs). If a PDB prevents pod eviction (e.g., you only have 1 replica of a critical service), Kured will wait up to `drainTimeout` (default 2 hours) before giving up. After timeout, Kured logs a warning and skips that node until the next check cycle. This is intentional — Kured prioritizes application availability over timely security patching. You should configure `blockingPodSelector` to explicitly block reboots when critical workloads are running.

### Q: Should I use Watchtower or Autoheal — or both?

They solve different problems and work best together. Watchtower handles the "new image available" scenario — keeping your containers updated with the latest patches and features. Autoheal handles the "container is running but unhealthy" scenario — restarting containers that have crashed, hung, or are returning errors. Without Watchtower, your containers run old (potentially vulnerable) images. Without Autoheal, your unhealthy containers stay running until manually restarted.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Health Monitoring & Auto-Healing: Watchtower vs Autoheal vs Kured (2026 Guide)",
  "description": "Compare Watchtower, Autoheal, and Kured for self-hosted container health monitoring and auto-healing. Covers Docker auto-updates, health check remediation, and Kubernetes node reboot management.",
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
