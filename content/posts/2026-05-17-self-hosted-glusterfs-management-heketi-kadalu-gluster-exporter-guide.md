---
title: "Self-Hosted GlusterFS Management: Heketi vs Kadalu vs Gluster Exporter"
date: "2026-05-17"
tags: ["glusterfs", "storage-management", "kubernetes", "monitoring", "distributed-storage"]
draft: false
---

GlusterFS is a mature, open-source distributed file system that scales to several petabytes. But managing a GlusterFS cluster — provisioning volumes, monitoring health, and handling brick failures — requires dedicated management tools. In this guide, we compare three approaches: **Heketi** (REST API volume management), **Kadalu** (Kubernetes-native GlusterFS operator), and **Gluster Exporter** (Prometheus metrics exporter).

## Heketi: RESTful Volume Management for GlusterFS

[Heketi](https://github.com/heketi/heketi) (1,260+ stars) provides a RESTful API for dynamically provisioning GlusterFS volumes. It was originally developed by Red Hat as part of the Gluster Kubernetes integration and supports multiple topologies — from simple 3-node clusters to complex multi-datacenter deployments.

### Key Features

- **REST API** for volume lifecycle management (create, delete, expand, snapshot)
- **Device and node management** — automatically discovers and manages bricks across nodes
- **Multiple topology support** — replicates, distribute, and distribute-replicate volume types
- **Kubernetes integration** — used as the dynamic provisioner for GlusterFS storage classes
- **CLI and web UI** — both command-line and optional web interface for administration

### Docker Compose Deployment

```yaml
version: '3'
services:
  heketi:
    image: heketi/heketi:11
    container_name: heketi
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./heketi-db:/var/lib/heketi
      - ./heketi.json:/etc/heketi/heketi.json
      - /etc/ssh:/etc/ssh:ro
    environment:
      - HEKETI_ADMIN_KEY=adminsecret
      - HEKETI_USER_KEY=usersecret
    network_mode: host
    cap_add:
      - SYS_ADMIN
    security_opt:
      - apparmor:unconfined
```

Heketi requires SSH access to GlusterFS nodes to execute volume management commands. The `heketi.json` configuration file defines cluster topology, authentication keys, and executor type (SSH or Kubernetes).

### Configuration Example

```json
{
  "_port_comment": "Heketi Server Port Number",
  "port": "8080",
  "_use_auth": "Enable JWT authentication",
  "use_auth": true,
  "jwt": {
    "admin": {
      "key": "adminsecret"
    },
    "user": {
      "key": "usersecret"
    }
  },
  "_glusterfs_comment": "GlusterFS Configuration",
  "glusterfs": {
    "executor": "ssh",
    "sshexec": {
      "rebalance_on_expansion": true
    }
  }
}
```

### Pros and Cons

| Feature | Heketi |
|---------|--------|
| API-driven provisioning | ✅ Full REST API |
| Kubernetes native | ✅ CSI driver support |
| Multi-cluster support | ✅ Yes |
| Active development | ⚠️ Last update 2023 |
| Web UI | ⚠️ Community UI only |
| Monitoring | ❌ No built-in metrics |

## Kadalu: Kubernetes-Native GlusterFS Operator

[Kadalu](https://github.com/kadalu/kadalu) (749+ stars) is a lightweight, Kubernetes-native storage solution built on GlusterFS. Unlike Heketi, Kadalu is designed specifically for Kubernetes environments and uses Kubernetes Custom Resource Definitions (CRDs) for storage management.

### Key Features

- **Kubernetes Operator** — manages GlusterFS lifecycle through K8s CRDs
- **External and Internal modes** — use existing GlusterFS cluster or deploy Kadalu-managed storage
- **CSI driver** — native Kubernetes storage provisioning
- **Lightweight** — minimal resource footprint compared to full GlusterFS deployments
- **Active development** — regularly updated with Kubernetes compatibility fixes

### Docker Compose / Kubernetes Deployment

```yaml
# Kadalu Operator deployment (Kubernetes)
apiVersion: v1
kind: Namespace
metadata:
  name: kadalu
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: operator
  namespace: kadalu
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: kadalu
      app.kubernetes.io/component: operator
  template:
    metadata:
      labels:
        app.kubernetes.io/name: kadalu
        app.kubernetes.io/component: operator
    spec:
      serviceAccountName: kadalu-operator
      containers:
        - name: kadalu-operator
          image: docker.io/kadalu/operator:latest
          env:
            - name: WATCH_NAMESPACE
              value: ""
            - name: OPERATOR_NAME
              value: "kadalu-operator"
```

For non-Kubernetes deployments, Kadalu provides a CLI tool `kadalu` that manages storage pools directly:

```bash
# Install Kadalu
pip3 install kadalu

# Create a storage pool
kadalu storage-pool create pool1   --type Replica3   node1:/data/brick1   node2:/data/brick1   node3:/data/brick1

# Export a volume
kadalu volume create vol1 --size 100G pool1
```

### Pros and Cons

| Feature | Kadalu |
|---------|--------|
| Kubernetes native | ✅ Full operator + CSI |
| External mode | ✅ Use existing GlusterFS |
| Active development | ✅ Regular updates (2026) |
| Lightweight | ✅ Minimal overhead |
| REST API | ❌ K8s API only |
| Non-K8s support | ⚠️ CLI-only |

## Gluster Exporter: Prometheus Metrics for GlusterFS

[Gluster Exporter](https://github.com/ofesseler/gluster_exporter) (81+ stars) is a Prometheus exporter that collects metrics from GlusterFS clusters. While not a management tool per se, it provides critical observability that Heketi and Kadalu lack.

### Key Features

- **Prometheus integration** — exports GlusterFS metrics in Prometheus format
- **Volume metrics** — IOPS, throughput, latency per volume
- **Brick-level monitoring** — individual brick health and performance
- **Peer status** — cluster node connectivity and health
- **Grafana dashboards** — community dashboards available

### Docker Compose Deployment

```yaml
version: '3'
services:
  gluster-exporter:
    image: gluster/gluster-exporter:latest
    container_name: gluster-exporter
    restart: unless-stopped
    ports:
      - "9189:9189"
    volumes:
      - /var/run/gluster:/var/run/gluster:ro
      - /etc/glusterfs:/etc/glusterfs:ro
      - /var/lib/glusterd:/var/lib/glusterd:ro
    command:
      - "--gluster.binary=/usr/sbin/gluster"
      - "--web.listen-address=:9189"
    network_mode: host
```

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'glusterfs'
    static_configs:
      - targets: ['gluster-node1:9189', 'gluster-node2:9189']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Comparison: All Three Tools

| Feature | Heketi | Kadalu | Gluster Exporter |
|---------|--------|--------|-----------------|
| Primary purpose | Volume provisioning | K8s storage operator | Metrics & monitoring |
| REST API | ✅ Yes | ❌ K8s API only | ❌ Metrics endpoint |
| Kubernetes support | ✅ CSI driver | ✅ Full operator | ✅ Sidecar possible |
| Monitoring | ❌ None | ⚠️ Basic | ✅ Full Prometheus |
| Active development | ⚠️ 2023 | ✅ 2026 | ⚠️ 2023 |
| GitHub Stars | 1,260+ | 749+ | 81+ |
| Best for | Dynamic provisioning | Kubernetes clusters | Observability |

## Why Self-Host GlusterFS Management?

Running your own distributed storage management stack gives you complete control over data placement, replication strategies, and access policies. Unlike managed cloud storage services, self-hosted GlusterFS management tools let you:

**Maintain data sovereignty.** Your storage infrastructure stays on your hardware. No cross-border data transfers, no vendor lock-in, and no surprise pricing changes. For organizations handling sensitive data — medical records, financial transactions, or proprietary research — this control is non-negotiable.

**Optimize for your workload.** Cloud storage services charge for IOPS, egress, and API calls. With self-hosted GlusterFS, you control the disk layout, replication factor, and cache settings. You can tune for throughput (video processing), IOPS (databases), or capacity (archives) without per-operation charges.

**Scale on your terms.** Adding a node to a GlusterFS cluster costs the price of hardware, not a monthly subscription multiplier. Heketi and Kadalu make this scaling operational — new nodes are discovered, bricks are allocated, and volumes are rebalanced automatically.

**Integrate with your existing stack.** Whether you're running Kubernetes, OpenShift, or bare-metal servers, these tools integrate with your existing monitoring (Prometheus/Grafana), logging (ELK/Loki), and automation (Ansible/Terraform) pipelines.

For distributed file system comparisons, see our [distributed file systems guide](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/). If you need NFS-based alternatives, check our [NFS server guide](../2026-04-30-nfs-ganesha-vs-unfs3-vs-kernel-nfs-self-hosted-nfs-server-guide-2026/). For storage replication strategies, our [DRBD and ZFS guide](../2026-05-08-self-hosted-storage-replication-drbd-zfs-glusterfs-georep-guide-2026/) covers complementary approaches.

### Choosing the Right GlusterFS Management Tool

The best tool depends on your deployment context. If you are running Kubernetes and need dynamic storage provisioning, Kadalu provides the most integrated experience with its operator pattern and CSI driver. It actively tracks Kubernetes releases and receives regular updates. For environments that mix Kubernetes with bare-metal servers, Heketi REST API offers flexibility. If observability is your primary concern, Gluster Exporter should be deployed alongside whichever management tool you choose. The exporter provides over 50 GlusterFS-specific metrics including per-volume IOPS, brick-level latency, peer connectivity status, and storage utilization. For production deployments, the recommended stack combines Kadalu or Heketi for volume lifecycle management plus Gluster Exporter on every node for continuous monitoring.

### Security Best Practices

GlusterFS communicates over TCP ports 24007 and 24008. When deploying management tools, ensure firewall rules restrict access to these ports. Heketi REST API should use JWT authentication and TLS in production. Kadalu inherits Kubernetes RBAC for access control. Brick-level encryption is not built into GlusterFS itself — for encrypted transport, deploy over WireGuard or IPsec tunnels.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted GlusterFS Management: Heketi vs Kadalu vs Gluster Exporter",
  "description": "Compare Heketi, Kadalu, and Gluster Exporter for managing self-hosted GlusterFS clusters.",
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

## FAQ

### What is the difference between Heketi and Kadalu?

Heketi is a REST API-based volume manager that works with any GlusterFS cluster and supports both Kubernetes and standalone deployments. Kadalu is a Kubernetes-native operator that uses CRDs for storage management and is designed specifically for Kubernetes environments. If you're running Kubernetes, Kadalu provides a more integrated experience. For mixed environments, Heketi's REST API is more versatile.

### Can I use Gluster Exporter without Heketi or Kadalu?

Yes. Gluster Exporter connects directly to the GlusterFS daemon via local sockets or the `gluster` CLI. It does not require Heketi or Kadalu to be installed. You can deploy it alongside any GlusterFS deployment to get Prometheus-compatible metrics.

### Is Heketi still actively maintained?

Heketi's last major update was in 2023. The project is considered stable but not actively developed. For new deployments, Kadalu (actively maintained through 2026) is recommended for Kubernetes environments. Heketi remains viable for existing deployments that don't require new features.

### How many GlusterFS nodes do I need for a production cluster?

A minimum of 3 nodes is recommended for replicated volumes (Replica 3). For distributed-replicate volumes, you need multiples of the replica count (e.g., 6 nodes for a 2x3 layout). Kadalu supports external mode with as few as 2 nodes in replicate mode, but 3+ is recommended for production.

### Does Kadalu support non-Kubernetes deployments?

Kadalu's primary interface is through Kubernetes CRDs. However, it does provide a CLI tool (`kadalu`) that can manage storage pools on non-Kubernetes nodes. The CLI uses the same backend as the operator but exposes it through command-line commands instead of Kubernetes APIs.

### How do I monitor GlusterFS cluster health?

Deploy Gluster Exporter on each GlusterFS node and configure Prometheus to scrape the metrics endpoint (default port 9189). Use Grafana dashboards to visualize volume IOPS, brick health, peer connectivity, and storage utilization. The exporter provides over 50 GlusterFS-specific metrics including per-volume read/write latency and brick-level disk usage.
