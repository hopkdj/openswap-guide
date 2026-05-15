---
title: "Self-Hosted Ceph Storage Management: Ceph Dashboard vs Rook vs Cephadm"
date: "2026-05-16"
tags: ["ceph", "storage", "dashboard", "kubernetes", "distributed-storage", "infrastructure"]
draft: false
---

Ceph is the leading open-source software-defined storage platform, providing object, block, and file storage on a single distributed cluster. However, managing a Ceph cluster through CLI commands alone is complex and error-prone. Self-hosted Ceph management tools provide web-based dashboards, automated deployment, and operational visibility for storage administrators. This guide compares Ceph Dashboard, Rook, and Cephadm — three distinct approaches to Ceph cluster management.

## Why Ceph Cluster Management Needs Dedicated Tools

A production Ceph cluster typically consists of multiple monitor nodes, OSD (Object Storage Daemon) servers, metadata servers, and manager daemons. Each component generates metrics, requires health monitoring, and may need configuration tuning. Without proper management tooling, administrators face several challenges:

- **Cluster health visibility**: Understanding PG (Placement Group) states, OSD health, and capacity utilization requires running multiple CLI commands and interpreting complex output
- **Configuration management**: Ceph configuration spans dozens of parameters across multiple daemon types, making manual edits error-prone
- **Operational tasks**: Adding OSDs, rebalancing data, and managing CRUSH maps are complex operations that benefit from guided workflows
- **Performance monitoring**: Identifying bottlenecks in IOPS, throughput, and latency requires collecting and correlating metrics across the entire cluster

For Ceph deployment guidance, see our [complete Ceph deployment comparison](../2026-05-15-self-hosted-ceph-deployment-cephadm-vs-rook-vs-ceph-ansible-guide/). If you need distributed storage alternatives, our [S3 object storage comparison](../2026-05-14-self-hosted-s3-object-storage-garage-vs-seaweedfs-vs-ceph-rgw-guide/) covers MinIO, SeaweedFS, and Ceph RGW. For container storage integration, our [Kubernetes storage guide](../2026-05-08-kubernetes-csi-drivers-ceph-csi-vs-longhorn-vs-kadalu-guide/) covers Ceph CSI drivers in detail.

## Ceph Dashboard: Built-In Manager Web UI

The Ceph Dashboard is a module for the Ceph Manager daemon (`ceph-mgr`) that provides a comprehensive web-based interface for monitoring and managing Ceph clusters. It is included with Ceph and requires no additional software installation beyond enabling the module.

### Key Features

- **Cluster overview**: Real-time health status, capacity utilization, and performance metrics
- **OSD management**: View OSD status, add/remove OSDs, scrub and deep-scrub operations
- **Pool management**: Create, modify, and delete storage pools with replication and erasure coding settings
- **CRUSH map visualization**: Interactive view of the CRUSH hierarchy and data placement
- **Performance graphs**: Built-in Grafana integration for detailed performance monitoring
- **User and role management**: Role-based access control with read-only and admin roles
- **RGW management**: Manage RADOS Gateway users, buckets, and bucket policies
- **iSCSI and NFS management**: Configure block and file export services

### Enabling the Dashboard

```bash
# Enable the dashboard module on a Ceph manager
ceph mgr module enable dashboard

# Generate a self-signed SSL certificate
ceph dashboard create-self-signed-cert

# Set the dashboard credentials
ceph dashboard set-login-credentials admin <password>

# Check the dashboard URL
ceph mgr services
# Output: {"dashboard": "https://<mgr-host>:8443/"}
```

### Docker Compose for Testing

```yaml
# docker-compose.yml for Ceph with Dashboard (testing only)
version: "3.8"
services:
  ceph-mon:
    image: ceph/ceph:v18
    container_name: ceph-mon
    network_mode: host
    environment:
      - MON_IP=192.168.1.100
      - CEPH_PUBLIC_NETWORK=192.168.1.0/24
      - CEPH_DEMO_UID=demo
      - CEPH_DEMO_PASSWORD=demo
      - CEPH_DEMO_BUCKET=demo-bucket
    volumes:
      - /etc/ceph:/etc/ceph
      - /var/lib/ceph:/var/lib/ceph
    privileged: true
```

### Dashboard Configuration

```bash
# Enable Prometheus metrics endpoint for Grafana
ceph mgr module enable prometheus

# Configure Prometheus target (usually in prometheus.yml)
# - job_name: 'ceph'
#   static_configs:
#     - targets: ['<mgr-host>:9283']

# Set dashboard SSL configuration
ceph config set mgr mgr/dashboard/ssl_server_port 8443
ceph config set mgr mgr/dashboard/url_prefix ""
ceph config set mgr mgr/dashboard/allow_embedded_cluster_dashboard true
```

### Pros and Cons

| Feature | Ceph Dashboard |
|---------|---------------|
| Installation | Built-in (just enable module) |
| Cluster management | Full read/write |
| Performance monitoring | Via Grafana integration |
| User management | RBAC with roles |
| API access | REST API available |
| Kubernetes integration | None (native Ceph only) |
| Version support | Matches Ceph version |
| Overhead | Minimal (runs as mgr module) |

## Rook: Kubernetes Operator for Ceph

[Rook](https://github.com/rook/rook) is an open-source cloud-native storage orchestrator that provides a Kubernetes operator for deploying and managing Ceph clusters. Rook transforms Ceph from a traditionally complex infrastructure component into a Kubernetes-native storage platform.

### Key Features

- **Kubernetes-native deployment**: Deploy Ceph using standard Kubernetes manifests and Helm charts
- **Automated cluster management**: Rook operator handles Ceph deployment, upgrades, and healing automatically
- **CSI integration**: Native Kubernetes CSI provisioners for block (RBD), file (CephFS), and object (RGW) storage
- **Dashboard integration**: Bundles the Ceph Dashboard with automatic configuration
- **StorageClass management**: Create Kubernetes StorageClasses that provision Ceph pools on demand
- **Health monitoring**: Kubernetes-native health checks and alerting through standard mechanisms
- **Multi-cluster support**: Manage multiple Ceph clusters across different Kubernetes clusters

### CephCluster CRD Configuration

```yaml
# cluster.yaml - Rook CephCluster definition
apiVersion: ceph.rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v18.2.2
    allowUnsupported: false
  dataDirHostPath: /var/lib/rook
  mon:
    count: 3
    allowMultiplePerNode: false
  mgr:
    count: 2
    modules:
      - name: dashboard
        enabled: true
  dashboard:
    enabled: true
    ssl: true
  storage:
    useAllNodes: true
    useAllDevices: true
    config:
      osdsPerDevice: "1"
  placement:
    mon:
      podAntiAffinity:
        preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              topologyKey: kubernetes.io/hostname
  resources:
    mon:
      requests:
        cpu: "500m"
        memory: "1Gi"
      limits:
        cpu: "1"
        memory: "2Gi"
```

### Installation via Helm

```bash
# Add Rook Helm repository
helm repo add rook-release https://charts.rook.io/release
helm repo update

# Install Rook operator
helm install --create-namespace --namespace rook-ceph rook-ceph rook-release/rook-ceph   --set csi.enableRbdDriver=true   --set csi.enableCephfsDriver=true   --set csi.enableNfsDriver=true

# Create CephCluster
kubectl create -f cluster.yaml

# Access the dashboard
kubectl -n rook-ceph get secret rook-ceph-dashboard-password -o jsonpath="{['data']['password']}" | base64 --decode
kubectl -n rook-ceph port-forward svc/rook-ceph-mgr-dashboard 8443:8443
```

### StorageClass Configuration

```yaml
# RBD StorageClass for block storage
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rook-ceph-block
provisioner: rook-ceph.rbd.csi.ceph.com
parameters:
  clusterID: rook-ceph
  pool: replicapool
  imageFormat: "2"
  imageFeatures: layering
  csi.storage.k8s.io/provisioner-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-rbd-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
```

### Pros and Cons

| Feature | Rook |
|---------|------|
| Kubernetes integration | Full operator pattern |
| Automated operations | Deploy, upgrade, heal |
| Dashboard | Bundled Ceph Dashboard |
| CSI provisioners | RBD, CephFS, NFS, RGW |
| Learning curve | Medium (Kubernetes knowledge required) |
| Resource overhead | Moderate (operator + Ceph pods) |
| Non-Kubernetes support | No (Kubernetes only) |
| Community | Active CNCF project |

## Cephadm: Ceph Orchestrator with CLI Management

[Cephadm](https://docs.ceph.com/en/latest/cephadm/) is the recommended deployment and management tool for Ceph clusters, introduced in Ceph Octopus (v15.2). It uses SSH and container runtimes to deploy and manage Ceph daemons across cluster nodes, providing a streamlined operational experience.

### Key Features

- **Container-native deployment**: All Ceph daemons run in containers managed by cephadm
- **SSH-based orchestration**: Central management node connects to cluster nodes via SSH
- **Service specification**: Declarative YAML service specs define the desired cluster state
- **Automatic discovery**: cephadm discovers and adopts existing daemons
- **Upgrade management**: Rolling upgrades with automatic health checks between steps
- **Dashboard integration**: Enables Ceph Dashboard automatically during bootstrap
- **Prometheus/Grafana integration**: Deploys monitoring stack alongside the cluster

### Bootstrap a New Cluster

```bash
# Bootstrap a new Ceph cluster on the first monitor node
cephadm bootstrap --mon-ip 192.168.1.100   --dashboard-admin-username admin   --dashboard-admin-password <secure-password>   --allow-fqdn-hostname

# Add hosts to the cluster
ceph orch host add node2 192.168.1.101
ceph orch host add node3 192.168.1.102

# Add OSDs from available devices
ceph orch daemon add osd node1:/dev/sdb
ceph orch daemon add osd node2:/dev/sdb
ceph orch daemon add osd node3:/dev/sdb
```

### Service Specification

```yaml
# service-spec.yaml - Declarative Ceph cluster specification
service_type: host
address: 192.168.1.100
hostname: node1
labels:
  - mon
  - mgr
  - osd
---
service_type: host
address: 192.168.1.101
hostname: node2
labels:
  - mon
  - mgr
  - osd
---
service_type: mon
placement:
  hosts:
    - node1
    - node2
    - node3
---
service_type: mgr
placement:
  hosts:
    - node1
    - node2
---
service_type: osd
service_id: default_drive_group
placement:
  host_pattern: "*"
data_devices:
  all: true
---
service_type: rgw
service_id: mygateway
spec:
  rgw_realm: default
  rgw_zone: default
  rgw_frontend_port: 8080
placement:
  hosts:
    - node1
    - node2
```

### Apply and Verify

```bash
# Apply service specifications
ceph orch apply -i service-spec.yaml

# Verify cluster status
ceph orch ls
ceph orch ps
ceph -s

# Check dashboard availability
ceph mgr services
# Access at: https://<mon-ip>:8443
```

### Pros and Cons

| Feature | Cephadm |
|---------|---------|
| Deployment model | Container-based with SSH |
| Configuration | Declarative YAML specs |
| Dashboard | Auto-enabled during bootstrap |
| Monitoring | Built-in Prometheus/Grafana deploy |
| Kubernetes support | No (bare metal/VM focus) |
| Learning curve | Low to medium |
| Upgrade management | Automated rolling upgrades |
| Resource overhead | Low (containers only) |

## Choosing the Right Ceph Management Tool

The choice depends on your infrastructure platform and operational requirements:

- **Ceph Dashboard** is the foundation for all three approaches. It is always available when you have a Ceph Manager daemon running. Use it as your primary web interface regardless of which management tool you choose for deployment and orchestration.

- **Rook** is the clear choice for Kubernetes environments. It provides the deepest integration with Kubernetes, including CSI provisioners, StorageClasses, and automated lifecycle management. If your Ceph cluster exists to serve Kubernetes workloads, Rook is the natural fit.

- **Cephadm** is the recommended tool for bare metal or virtual machine deployments. It provides declarative cluster management, automated upgrades, and built-in monitoring stack deployment. It is the upstream-recommended approach for traditional infrastructure.

## FAQ

### Can I use Ceph Dashboard without Rook or Cephadm?
Yes. The Ceph Dashboard is a module for `ceph-mgr` and works with any Ceph deployment method, including ceph-deploy, Ansible, or manual installation. Simply enable the dashboard module and configure credentials.

### Does Rook support external (non-Kubernetes) Ceph clusters?
Rook can connect to external Ceph clusters through the `CephBlockPool` and `CephFilesystem` CRDs with external cluster configuration. However, Rook's primary strength is managing Ceph clusters it deploys within Kubernetes.

### How does Cephadm handle OSD disk failures?
Cephadm monitors daemon health through the Ceph Manager. When an OSD daemon fails, cephadm can attempt to restart it. For disk hardware failures, cephadm logs the issue and the Ceph cluster's self-healing mechanisms (data replication, reconstruction) handle data protection. Administrators must replace the physical disk and re-add the OSD.

### Can Rook and Cephadm manage the same Ceph cluster?
No. Rook and Cephadm use different deployment and management paradigms. Rook manages Ceph through Kubernetes operators and CRDs, while cephadm uses SSH and container runtimes. Mixing them on the same cluster would cause conflicts.

### What Ceph version supports the Dashboard module?
The Ceph Dashboard has been available since Ceph Nautilus (v14.2). It is included in all supported Ceph releases (Pacific v16.2, Quincy v17.2, Reef v18.2). The dashboard improves with each release, adding new management capabilities.

### Does Ceph Dashboard require Grafana?
No, but it is highly recommended. The Ceph Dashboard includes links to Grafana dashboards for detailed performance visualization. Cephadm can automatically deploy Prometheus and Grafana alongside the cluster. Without Grafana, the dashboard still provides basic metrics and health information.

### How do I backup Ceph cluster configuration?
With cephadm, export the cluster configuration: `ceph config export > cluster-config.json`. With Rook, backup the CephCluster CRD and related Kubernetes resources: `kubectl get cephcluster -n rook-ceph -o yaml > ceph-cluster-backup.yaml`. Always backup the monitor keyring and OSD encryption keys separately.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Ceph Storage Management: Ceph Dashboard vs Rook vs Cephadm",
  "description": "Compare Ceph Dashboard, Rook Kubernetes operator, and Cephadm orchestrator for managing self-hosted Ceph distributed storage clusters.",
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
