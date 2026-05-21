---
title: "Self-Hosted Storage Dashboard: Ceph Dashboard vs Rook vs GlusterFS Web UI"
date: "2026-05-21"
tags: ["storage", "ceph", "rook", "glusterfs", "dashboard", "monitoring", "self-hosted"]
draft: false
---

Managing distributed storage systems at scale requires visibility into cluster health, capacity utilization, and performance metrics. While each storage platform ships with command-line tools and REST APIs, having a web-based dashboard dramatically simplifies day-to-day operations. In this guide, we compare three open-source storage dashboard solutions: the native Ceph Dashboard, Rook Dashboard for Kubernetes-orchestrated storage, and the GlusterFS Web UI ecosystem.

## Ceph Dashboard

Ceph Dashboard is the official web-based management interface built into the Ceph Manager daemon (ceph-mgr). It replaced the older Ceph Manager modules and provides a comprehensive view of cluster status.

**Key Features:**
- Real-time cluster health monitoring with OSD, MON, and MDS status
- Pool management with capacity visualization
- Performance metrics with Grafana integration
- User role-based access control (RBAC)
- iSCSI, NFS-Ganesha, and RGW management panels

**Installation:**
The Ceph Dashboard is included in ceph-mgr since Ceph Nautilus (14.x). Enable it with:

```bash
# Enable the dashboard module
ceph mgr module enable dashboard

# Generate a self-signed certificate (or configure your own)
ceph config set mgr mgr/dashboard/ssl true

# Set the dashboard address and port
ceph config set mgr mgr/dashboard/server_addr 0.0.0.0
ceph config set mgr mgr/dashboard/server_port 8443

# Create an admin user
ceph dashboard ac-user-create admin -i password-file administrator

# View the dashboard URL
ceph mgr services
```

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  ceph-mon:
    image: quay.io/ceph/daemon:latest-mgr
    network_mode: host
    volumes:
      - /etc/ceph:/etc/ceph
      - /var/lib/ceph:/var/lib/ceph
    environment:
      - CEPH_DAEMON=MGR
      - NETWORK_AUTO_DETECT=4
    restart: unless-stopped

  ceph-dashboard:
    image: quay.io/ceph/daemon:latest-mgr
    network_mode: host
    volumes:
      - /etc/ceph:/etc/ceph
      - /var/lib/ceph:/var/lib/ceph
    command: ["ceph-mgr", "-f", "--name", "mgr.dashboard"]
    depends_on:
      - ceph-mon
    restart: unless-stopped
```

The dashboard integrates natively with Prometheus for metrics and can forward alerts to Alertmanager. It supports SSO via SAML 2.0 and OpenID Connect.

## Rook Dashboard

Rook is a Kubernetes storage orchestrator that manages Ceph clusters as custom resources. The Rook Dashboard extends the Ceph Dashboard with Kubernetes-specific views and integrates with the Kubernetes API for storage provisioning.

**Key Features:**
- Kubernetes-native storage class management
- CephCluster CRD status visualization
- Persistent Volume Claim (PVC) binding views
- Integration with Kubernetes RBAC
- Storage expansion and shrink operations via UI

**Installation via Rook Operator:**
```yaml
apiVersion: rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v18
  dashboard:
    enabled: true
    port: 8443
    ssl: true
  mon:
    count: 3
    allowMultiplePerNode: false
  storage:
    useAllNodes: true
    useAllDevices: true
```

```bash
# Apply the Rook operator
kubectl create -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/common.yaml
kubectl create -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/crds.yaml
kubectl create -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/operator.yaml
kubectl create -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/cluster.yaml

# Access the dashboard
kubectl -n rook-ceph port-forward svc/rook-ceph-mgr-dashboard 8443:8443
```

**Docker Compose for standalone Rook-like deployment:**
```yaml
version: "3.8"
services:
  rook-operator:
    image: rook/ceph:latest
    volumes:
      - /var/lib/rook:/var/lib/rook
      - /etc/kubernetes:/etc/kubernetes
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - ROOK_LOG_LEVEL=INFO
    restart: unless-stopped
    network_mode: host
```

Rook's strength is its Kubernetes integration — the dashboard surfaces storage provisioning, PVC status, and storage class configurations alongside raw Ceph metrics. For teams running Kubernetes, Rook eliminates the need to manage a separate Ceph cluster.

## GlusterFS Web UI

GlusterFS does not ship with an official web dashboard in its core distribution. However, several community and third-party projects provide web-based management:

- **Cockpit Gluster** — A Cockpit plugin that provides GlusterFS cluster management through the Cockpit web interface
- **Grafana GlusterFS Dashboards** — Community Grafana dashboards using GlusterFS Prometheus exporter
- **GlusterFS Manager** — Community web UI for volume management and monitoring

**Cockpit Gluster setup:**
```bash
# Install Cockpit and the Gluster plugin
apt-get install cockpit cockpit-gluster -y

# Enable and start Cockpit
systemctl enable --now cockpit.socket

# Access at https://<server>:9090
```

**Prometheus exporter for GlusterFS metrics:**
```bash
# Install the GlusterFS Prometheus exporter
pip install gluster-prometheus

# Configure the exporter
cat > /etc/gluster-prometheus/config.yaml << 'EXPORTER'
gluster:
  binary: /usr/sbin/gluster
  timeout: 30
  volumes: true
  bricks: true
  peers: true
EXPORTER

# Start the exporter
systemctl enable --now gluster-prometheus
```

**Docker Compose for monitoring stack:**
```yaml
version: "3.8"
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped

  gluster-exporter:
    image: gluster/gluster-prometheus:latest
    network_mode: host
    volumes:
      - /var/run/glusterd.socket:/var/run/glusterd.socket
    restart: unless-stopped

volumes:
  grafana-data:
```

Prometheus configuration:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "glusterfs"
    static_configs:
      - targets: ["localhost:8080"]
```

The GlusterFS dashboard ecosystem is more fragmented than Ceph's — you need to assemble multiple components (Cockpit + Grafana + exporter) to get comparable functionality. However, this modular approach allows you to customize the monitoring stack to your exact needs.

## Comparison Table

| Feature | Ceph Dashboard | Rook Dashboard | GlusterFS Web UI |
|---------|---------------|----------------|------------------|
| **Official UI** | Yes (built-in) | Yes (extends Ceph) | No (community plugins) |
| **Installation** | Single command | K8s operator | Multi-component setup |
| **Kubernetes Integration** | No | Yes (native) | Limited |
| **Metrics** | Prometheus + Grafana | Prometheus + Grafana | Prometheus exporter |
| **User Management** | RBAC, SAML, OIDC | Kubernetes RBAC | Cockpit auth |
| **Storage Provisioning** | Pool creation | PVC + StorageClass | Volume creation |
| **Alerting** | Alertmanager | Alertmanager | Grafana alerts |
| **Active Development** | Very active (Ceph core) | Very active (CNCF) | Moderate (community) |
| **GitHub Stars** | 16,600+ (ceph/ceph) | 13,500+ (rook/rook) | 5,100+ (gluster/glusterfs) |
| **Last Updated** | Active (2026) | Active (2026) | Active (2026) |
| **Container Support** | Official image | Kubernetes operator | Community images |

## Why Self-Host a Storage Dashboard?

Managing distributed storage without a dashboard means relying on CLI commands, parsing JSON output, and manually correlating metrics across multiple tools. A web-based storage dashboard consolidates this information into a single pane of glass, making it possible for operations teams to monitor cluster health, respond to alerts, and manage capacity without deep CLI expertise.

Self-hosting a storage dashboard gives you complete control over your monitoring infrastructure. Unlike cloud-managed storage consoles, a self-hosted dashboard does not share telemetry with external vendors. All data remains within your infrastructure, which is critical for organizations with strict data sovereignty requirements or compliance mandates.

The cost savings are significant when managing large-scale storage deployments. Cloud storage management consoles often charge per-node or per-terabyte fees for dashboard access. Open-source storage dashboards eliminate these licensing costs while providing equivalent or superior functionality.

For organizations running mixed storage environments, having dashboard visibility across Ceph, Rook, and GlusterFS clusters enables unified operational practices. Teams can standardize monitoring workflows, use consistent alerting thresholds, and apply the same incident response procedures regardless of the underlying storage technology.

For related reading on distributed storage architectures, see our [JuiceFS vs Alluxio vs CephFS comparison](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/) and [S3 object storage guide](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/).

## Choosing the Right Storage Dashboard

**Choose Ceph Dashboard if:** You run a native Ceph cluster outside Kubernetes and want a battle-tested, fully-featured dashboard with zero additional dependencies. The Ceph Dashboard is the most mature option, with comprehensive OSD, pool, and RGW management capabilities built directly into the ceph-mgr daemon.

**Choose Rook Dashboard if:** Your infrastructure is Kubernetes-native and you want storage management tightly integrated with your K8s control plane. Rook's dashboard surfaces storage provisioning alongside application workloads, making it ideal for platform teams managing both compute and storage in a single cluster.

**Choose GlusterFS Web UI (Cockpit + Grafana) if:** You need a lightweight, modular monitoring stack for GlusterFS volumes and want the flexibility to customize dashboards. While it requires more initial setup, the modular approach lets you combine GlusterFS metrics with system-level monitoring in a unified Grafana view.

## FAQ

### What is the Ceph Dashboard and how does it work?
The Ceph Dashboard is a web-based management interface built into the Ceph Manager daemon (ceph-mgr). It provides a REST API backend with a modern frontend, offering real-time cluster health monitoring, pool management, performance metrics, and user management. It has been part of Ceph since the Nautilus release (14.x) and requires no additional installation beyond enabling the module.

### Is the Rook Dashboard different from the Ceph Dashboard?
Rook Dashboard is essentially the Ceph Dashboard with additional Kubernetes-specific panels. Since Rook manages Ceph clusters via Kubernetes operators, the dashboard exposes Ceph metrics alongside Kubernetes storage resources like Persistent Volume Claims, StorageClasses, and CephCluster custom resources. The underlying dashboard engine is the same ceph-mgr module.

### Does GlusterFS have an official web dashboard?
No, GlusterFS does not include an official web dashboard in its core distribution. The recommended approach is to use Cockpit with the cockpit-gluster plugin for basic management, combined with Grafana dashboards fed by the gluster-prometheus exporter for comprehensive metrics visualization.

### Can I run Ceph Dashboard without a full Ceph cluster?
No, the Ceph Dashboard is a module of ceph-mgr, which requires a functioning Ceph cluster (at minimum, MON and MGR daemons) to operate. It cannot run as a standalone dashboard for external storage systems.

### Which storage dashboard supports SSO authentication?
The Ceph Dashboard supports SAML 2.0 and OpenID Connect for single sign-on. Rook inherits this capability since it uses the same Ceph Dashboard backend. GlusterFS through Cockpit uses system-level PAM authentication and does not natively support SSO.

### How do I back up dashboard configurations?
For Ceph Dashboard, configurations are stored in the Ceph monitor database and are included in `ceph mon dump` backups. For Rook, dashboard settings are part of the CephCluster CRD in Kubernetes etcd. For GlusterFS, Cockpit settings are in `/etc/cockpit/` and Grafana dashboards are in the Grafana data volume or provisioning directory.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Storage Dashboard: Ceph Dashboard vs Rook vs GlusterFS Web UI",
  "description": "Compare open-source storage dashboards for distributed storage management — Ceph Dashboard, Rook Dashboard, and GlusterFS Web UI tools with Docker deployment guides.",
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
