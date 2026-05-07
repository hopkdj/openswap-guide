---
title: "Self-Hosted Ceph Cluster Deployment: Cephadm vs Rook vs Ceph-ansible (2026 Guide)"
date: "2026-05-15"
draft: false
tags: ["ceph", "storage", "kubernetes", "deployment", "infrastructure", "distributed-storage"]
---

Ceph is the leading open-source software-defined storage platform, providing object, block, and file storage in a unified system. But deploying and managing a Ceph cluster requires choosing the right orchestration tool. This guide compares the three most popular Ceph deployment methods: **Cephadm** (the official orchestrator), **Rook** (the Kubernetes operator), and **Ceph-ansible** (the legacy Ansible-based approach).

Whether you are building a bare-metal storage cluster, deploying Ceph on Kubernetes, or managing legacy infrastructure, this comparison will help you pick the right tool for your environment.

## What Is Ceph?

Ceph is a distributed storage system designed to provide excellent performance, reliability, and scalability. It was created in 2006 as part of Sage Weil's PhD research and has since become the backbone of many cloud storage infrastructures, including OpenStack and Proxmox.

Ceph provides three storage interfaces:

- **RADOS Block Device (RBD)** — block storage for virtual machines and containers
- **CephFS** — POSIX-compliant distributed file system
- **RADOS Gateway (RGW)** — S3/Swift-compatible object storage API

The core of Ceph is the RADOS (Reliable Autonomic Distributed Object Store) layer, which handles data distribution, replication, and self-healing across all cluster nodes.

## Ceph Deployment Tools Overview

### Cephadm

Cephadm is the official Ceph deployment tool introduced in Ceph Octopus (v15.2.0). It uses SSH and containers to deploy and manage Ceph clusters on bare-metal or virtual machine hosts. Cephadm replaced the older `ceph-deploy` tool and provides a modern, container-based approach to cluster management.

Key features of cephadm include:
- Container-based deployment (uses Podman or Docker)
- Automatic service discovery and placement
- Built-in orchestration daemon (`cephadm` agent on each node)
- Declarative cluster specification via YAML
- Integrated with the Ceph Manager dashboard
- Automatic certificate management with SSL

### Rook

Rook is a Kubernetes operator that automates the deployment, configuration, and management of Ceph clusters within Kubernetes environments. Rook transforms Ceph into a cloud-native storage solution that integrates seamlessly with Kubernetes storage classes, persistent volumes, and the CSI (Container Storage Interface) driver.

Key features of Rook include:
- Native Kubernetes integration via Custom Resource Definitions (CRDs)
- Automatic Ceph cluster provisioning from YAML manifests
- Ceph CSI driver for dynamic volume provisioning
- StorageClass integration for Kubernetes workloads
- Automated failure domain management (rack, zone, region awareness)
- Dashboard integration with Grafana

### Ceph-ansible

Ceph-ansible is an Ansible playbook collection for deploying and managing Ceph clusters. It was the primary deployment method before cephadm and remains useful for environments where Ansible is already the standard configuration management tool.

Key features of ceph-ansible include:
- Idempotent Ansible playbooks for repeatable deployments
- Highly customizable through Ansible variables and roles
- Support for bare-metal, VM, and container deployments
- Integration with existing Ansible inventories and workflows
- Mature, battle-tested codebase with extensive documentation
- Support for legacy Ceph versions

## Comparison Table

| Feature | Cephadm | Rook | Ceph-ansible |
|---------|---------|------|-------------|
| **Primary Use Case** | Bare-metal/VM clusters | Kubernetes environments | Ansible-managed infra |
| **Container-based** | Yes (Podman/Docker) | Yes (Kubernetes pods) | Optional |
| **Minimum Nodes** | 2 | 3 (for production) | 2 |
| **Kubernetes Integration** | No | Native (operator) | No |
| **Deployment Method** | SSH + containers | Kubernetes CRDs | Ansible playbooks |
| **Orchestration** | Built-in daemon | Kubernetes controller | Ansible runs |
| **Dashboard** | Ceph Manager UI | Rook Dashboard + Grafana | None built-in |
| **Auto-healing** | Yes | Yes | Manual re-run |
| **Learning Curve** | Low | Medium | High (Ansible required) |
| **Ceph Version Support** | v15.2+ (Octopus+) | v14+ (Nautilus+) | v10+ (Jewel+) |
| **GitHub Stars** | Part of ceph/ceph | 13,490+ | 1,779+ |

## Deploying Ceph with Cephadm

Cephadm is the simplest way to deploy a Ceph cluster on bare-metal or virtual machines. It requires SSH access to all nodes and uses containers for all Ceph services.

### Prerequisites

- Ceph Octopus (v15.2.0) or later
- Podman or Docker on all nodes
- SSH access from the bootstrap node to all cluster nodes
- NTP synchronization across all nodes
- DNS resolution or /etc/hosts entries for all nodes

### Bootstrap the First Node

```bash
# Download cephadm
curl --silent --remote-name --location https://github.com/ceph/ceph/raw/quincy/src/cephadm/cephadm
chmod +x cephadm

# Bootstrap the first monitor
./cephadm bootstrap --mon-ip 192.168.1.10

# This will:
# - Create the initial monitor and manager daemons
# - Generate SSH keys for cluster communication
# - Create the initial admin keyring
# - Write a ceph.conf configuration file
```

### Add Additional Nodes

```bash
# Copy the SSH public key to new nodes
ssh-copy-id -f -i /etc/ceph/ceph.pub root@node2
ssh-copy-id -f -i /etc/ceph/ceph.pub root@node3

# Add hosts to the cluster
ceph orch host add node2 192.168.1.11
ceph orch host add node3 192.168.1.12

# Deploy monitors on new hosts
ceph orch apply mon --placement="node1 node2 node3"

# Deploy OSDs (automatic discovery)
ceph orch apply osd --all-available-devices
```

### Verify Cluster Status

```bash
# Check cluster health
ceph -s

# Expected output:
#   cluster:
#     id:     <cluster-id>
#     health: HEALTH_OK
#
#   services:
#     mon: 3 daemons, quorum node1,node2,node3
#     mgr: node1(active), standbys: node2
#     osd: 9 osds: 9 up, 9 in
#
#   data:
#     pools:   1 pools, 128 pgs
#     objects: 0 objects, 0 B
#     usage:   9.0 GiB used, 270 GiB / 279 GiB avail
#     pgs:     128 active+clean
```

## Deploying Ceph with Rook on Kubernetes

Rook provides a Kubernetes-native approach to Ceph deployment using Custom Resource Definitions.

### Prerequisites

- Kubernetes v1.22+ cluster
- kubectl configured with admin access
- At least 3 worker nodes with raw block devices
- Helm v3 installed (optional, for Helm-based installation)

### Install Rook Operator

```yaml
# cluster.yaml - Rook Ceph Cluster Configuration
apiVersion: ceph.rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v18
    allowUnsupported: false
  dataDirHostPath: /var/lib/rook
  mon:
    count: 3
    allowMultiplePerNode: false
  mgr:
    count: 2
    modules:
      - name: rook
        enabled: true
  dashboard:
    enabled: true
    ssl: true
  storage:
    useAllNodes: true
    useAllDevices: true
    deviceFilter: ""
    config:
      osdsPerDevice: "1"
  network:
    provider: host
    connections:
      encryption:
        enabled: true
      compression:
        enabled: true
```

### Apply the Cluster Configuration

```bash
# Install the Rook operator
kubectl create -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/common.yaml
kubectl create -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/crds.yaml
kubectl create -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/operator.yaml

# Deploy the Ceph cluster
kubectl create -f cluster.yaml

# Monitor the cluster creation
kubectl -n rook-ceph get pods -w
```

### Create a StorageClass

```yaml
# storageclass.yaml - RBD StorageClass
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
  csi.storage.k8s.io/controller-expand-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-rbd-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
  csi.storage.k8s.io/fstype: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
```

```bash
kubectl apply -f storageclass.yaml

# Test with a PVC
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ceph-test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: rook-ceph-block
  resources:
    requests:
      storage: 1Gi
EOF
```

## Deploying Ceph with Ceph-ansible

Ceph-ansible uses Ansible playbooks to deploy Ceph across your infrastructure. This method is ideal for organizations already using Ansible for infrastructure management.

### Prerequisites

- Ansible 2.10+ on the control node
- Python 3 on all target nodes
- SSH access to all Ceph nodes
- Raw block devices available for OSDs

### Installation

```bash
# Clone the ceph-ansible repository
git clone https://github.com/ceph/ceph-ansible.git
cd ceph-ansible
git checkout stable-7.0

# Install dependencies
pip install -r requirements.txt

# Configure inventory
cat > inventory.ini <<EOF
[mons]
node1
node2
node3

[osds]
node1
node2
node3

[mgrs]
node1
node2
node3

[rgws]
node1
EOF

# Configure group variables
cat > group_vars/all.yml <<EOF
ceph_origin: repository
ceph_repository: community
ceph_stable_release: reef
monitor_interface: eth0
public_network: "192.168.1.0/24"
cluster_network: "10.0.0.0/24"
osd_auto_discovery: true
EOF
```

### Run the Playbooks

```bash
# Deploy the cluster
ansible-playbook site.yml -i inventory.ini -v

# Monitor the deployment output. The playbooks will:
# 1. Install Ceph packages on all nodes
# 2. Configure monitors (MONs)
# 3. Deploy managers (MGRs)
# 4. Configure OSDs with discovered devices
# 5. Deploy optional services (RGW, MDS, NFS)
```

## Choosing the Right Deployment Method

### Choose Cephadm when:
- Deploying on bare-metal or VMs without Kubernetes
- You want the simplest, most official deployment path
- You prefer container-based management
- Running Ceph v15.2 (Octopus) or later

### Choose Rook when:
- Your infrastructure is Kubernetes-native
- You need dynamic storage provisioning via StorageClasses
- You want Ceph to integrate with Kubernetes lifecycle management
- Your team is already familiar with Kubernetes operators

### Choose Ceph-ansible when:
- Ansible is your organization's standard configuration management tool
- You need fine-grained control over every deployment step
- You are managing legacy Ceph versions (pre-Octopus)
- You require custom deployment workflows and integrations

## Why Self-Host Ceph Storage?

Self-hosting Ceph gives you complete control over your data storage infrastructure. Unlike commercial cloud storage services, Ceph runs on your own hardware, meaning no vendor lock-in, no egress fees, and full data sovereignty.

For organizations managing large-scale storage needs, Ceph provides a cost-effective alternative to proprietary solutions like EMC Isilon or NetApp. The open-source nature of Ceph means you can inspect, modify, and extend every component to fit your specific requirements.

For a broader look at distributed file storage options, see our [Ceph vs GlusterFS vs MooseFS comparison](../ceph-vs-glusterfs-vs-moosefs-distributed-file-storage-2026/). If you are running Kubernetes, our [Rook vs Longhorn vs OpenEBS storage guide](../rook-vs-longhorn-vs-openebs-self-hosted-kubernetes-storage-guide-2026/) covers the best Kubernetes-native storage solutions. For distributed file systems that integrate with Ceph, check our [JuiceFS vs Alluxio vs CephFS guide](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/).

## FAQ

### What is the minimum number of nodes required for a production Ceph cluster?

For production deployments, a minimum of 3 nodes is recommended. This ensures that the Ceph monitor quorum can be maintained (majority of 3 = 2) and that data can be replicated across multiple failure domains. While cephadm technically supports 2-node clusters with a special "tiebreaker" configuration, this is only suitable for lab or testing environments.

### Can I migrate from Ceph-ansible to Cephadm?

Yes, Ceph provides a documented migration path from ceph-ansible to cephadm starting with Ceph Pacific (v16.2.0). The migration involves converting your existing cluster to use containers and the cephadm orchestration daemon. However, the process is complex and requires careful planning. It is recommended to test the migration in a staging environment before attempting it in production.

### Does Rook support external Ceph clusters?

Yes, Rook can manage external (non-Kubernetes) Ceph clusters through the CephCluster CRD with `external` mode. This allows you to use Rook's CSI driver to provision storage from an existing Ceph cluster that was deployed with cephadm or ceph-ansible, giving Kubernetes workloads access to external Ceph storage.

### How does Ceph handle node failures?

Ceph automatically handles node failures through its CRUSH algorithm and replication settings. When a node goes offline, Ceph marks its OSDs as down and begins redistributing data to maintain the configured replication factor (typically 3 copies). The recovery process is automatic and does not require manual intervention. You can monitor recovery progress with `ceph -s` and `ceph health detail`.

### Is Ceph suitable for small-scale deployments?

Ceph is designed for scale-out architectures and can work with as few as 2-3 nodes. However, the overhead of running Ceph daemons (MON, MGR, OSD) means that each node should have adequate resources (minimum 4GB RAM, 2 CPU cores, and SSD storage for journals). For very small deployments with limited resources, consider simpler solutions like NFS or GlusterFS instead.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Ceph Cluster Deployment: Cephadm vs Rook vs Ceph-ansible (2026 Guide)",
  "description": "Compare the three leading Ceph deployment tools: Cephadm (official orchestrator), Rook (Kubernetes operator), and Ceph-ansible (Ansible-based). Includes Docker Compose configs, installation guides, and best practices.",
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
