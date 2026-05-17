---
title: "Self-Hosted Kubernetes Cluster Provisioning: kops vs kubeone vs kubeadm (2026)"
date: "2026-05-17"
tags: ["kubernetes", "cluster-provisioning", "kops", "kubeone", "kubeadm", "infrastructure", "devops", "comparison", "guide", "self-hosted", "docker"]
draft: false
---

Provisioning a Kubernetes cluster from scratch is one of the most critical infrastructure decisions you will make. Whether you are deploying on AWS, bare metal, or a hybrid environment, the tool you choose determines your cluster's lifecycle, upgrade path, and operational complexity.

In this guide, we compare three leading Kubernetes cluster provisioning tools: **kops** (Kubernetes Operations), **kubeone** by Kubermatic, and **kubeadm** — the official Kubernetes bootstrapping tool. Each takes a different approach to cluster creation, management, and day-two operations.

## What Is Kubernetes Cluster Provisioning?

Cluster provisioning refers to the process of creating, configuring, and bootstrapping a fully functional Kubernetes cluster. This includes setting up the control plane, joining worker nodes, configuring networking (CNI), establishing certificate authorities, and enabling core add-ons like DNS and the kube-proxy.

The three tools we compare represent distinct philosophies:

| Feature | kops | kubeone | kubeadm |
|---|---|---|---|
| **Creator** | Kubernetes SIG | Kubermatic | Kubernetes SIG |
| **Primary Platform** | AWS (also GCE, OpenStack, Hetzner) | Multi-cloud (AWS, GCP, Azure, vSphere, Equinix Metal) | Any (cloud-agnostic) |
| **Stars** | 16,600+ | 1,500+ | Part of kubernetes/kubernetes |
| **Infrastructure as Code** | Cluster spec YAML + terraform output | Terraform-based | Manual or scripted |
| **HA Support** | Yes (multi-AZ, multi-master) | Yes (multi-master, etcd clustering) | Yes (manual setup) |
| **Managed etcd** | Yes (automatic) | Yes (automatic) | Manual or external |
| **Node Group Management** | Yes (Instance Groups) | Yes (MachineController) | Manual |
| **Upgrade Automation** | Rolling upgrades via `kops update` | Rolling upgrades via `kubeone upgrade` | Manual `kubeadm upgrade` per node |
| **Learning Curve** | Moderate | Moderate | Steep |
| **Best For** | AWS-native teams | Multi-cloud / hybrid | Custom / bare metal |

## kops (Kubernetes Operations)

kops is the oldest and most battle-tested Kubernetes provisioning tool, originally developed by the Kubernetes SIG AWS team. It is the de facto standard for self-hosted Kubernetes on AWS.

### Key Features

- **Declarative cluster spec**: Define your entire cluster in a YAML file, including instance types, zones, networking, and add-ons
- **Managed etcd**: Automatic etcd cluster deployment with backup and restore capabilities
- **Instance Groups**: Define node groups with auto-scaling, mixed instance types, and spot instance support
- **Terraform integration**: Generate Terraform configs from your cluster spec for infrastructure management
- **DNS integration**: Built-in support for Route53, gossip-based DNS, or external DNS providers
- **Rolling updates**: Automated rolling upgrades with configurable disruption budgets

### Docker Compose (Local Development)

While kops is designed for cloud deployment, you can test cluster specs locally using a local Kubernetes cluster:

```yaml
version: "3.8"
services:
  kind-cluster:
    image: kindest/node:v1.30.0
    container_name: kind-kops-test
    privileged: true
    ports:
      - "6443:6443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### Installation

```bash
# Install kops on Linux
curl -Lo kops https://github.com/kubernetes/kops/releases/download/v1.30.0/kops-linux-amd64
chmod +x kops
sudo mv kops /usr/local/bin/

# Verify installation
kops version
```

### Creating a Cluster on AWS

```bash
# Create an S3 bucket for cluster state
export KOPS_STATE_STORE=s3://my-kops-state-bucket
aws s3api create-bucket --bucket my-kops-state-bucket --region us-east-1

# Build cluster configuration
kops create cluster   --name kops.example.com   --state $KOPS_STATE_STORE   --zones us-east-1a,us-east-1b,us-east-1c   --master-count 3   --node-count 5   --node-size t3.medium   --master-size t3.medium   --networking cilium   --topology private   --ssh-public-key ~/.ssh/id_rsa.pub

# Review the generated configuration
kops edit cluster --name kops.example.com

# Apply the cluster
kops update cluster --name kops.example.com --yes

# Validate the cluster
kops validate cluster --wait 10m
```

### Cluster Upgrade

```bash
# Upgrade to a new Kubernetes version
kops upgrade cluster --name kops.example.com --yes

# Rolling update nodes
kops rolling-update cluster --name kops.example.com --yes
```

## kubeone (Kubermatic Kubernetes Platform)

kubeone is developed by Kubermatic and focuses on multi-cloud Kubernetes cluster lifecycle management. It uses Terraform for infrastructure provisioning and then attaches to the cluster to handle Kubernetes-specific configuration.

### Key Features

- **Multi-cloud support**: AWS, GCP, Azure, vSphere, Equinix Metal, Hetzner, and OpenStack
- **Terraform-based infrastructure**: Uses Terraform modules for consistent infrastructure provisioning
- **MachineController integration**: Manages worker nodes via CRDs, supporting auto-scaling and rolling updates
- **Canary upgrades**: Upgrades control plane nodes one at a time with automatic rollback on failure
- **External CNI support**: Works with any CNI plugin (Calico, Cilium, Canal, Weave)
- **Container runtime flexibility**: Supports containerd, Docker (legacy), and CRI-O

### Docker Compose (Local Testing)

```yaml
version: "3.8"
services:
  terraform:
    image: hashicorp/terraform:latest
    working_dir: /workspace
    volumes:
      - ./infra:/workspace
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=us-east-1
```

### Installation

```bash
# Install kubeone on Linux
curl -Lo kubeone https://github.com/kubermatic/kubeone/releases/download/v1.8.0/kubeone_1.8.0_linux_amd64.zip
unzip kubeone
sudo mv kubeone /usr/local/bin/

# Verify installation
kubeone version
```

### Creating a Cluster

```bash
# Step 1: Provision infrastructure with Terraform
cd terraform/aws
terraform init
terraform apply -var cluster_name="kubeone-prod"                 -var ssh_public_key_file="~/.ssh/id_rsa.pub"

# Step 2: Generate kubeone config from Terraform output
terraform output -json > tf.json

# Step 3: Create the Kubernetes cluster
kubeone apply -m kubeone-config.yaml -t tf.json --ssh-agent-env

# Step 4: Install CNI (e.g., Cilium)
kubeone apply -m kubeone-config.yaml -t tf.json   --ssh-agent-env   --manifest-url https://raw.githubusercontent.com/kubermatic/kubeone/main/addons/cilium/cilium.yaml
```

### Cluster Upgrade

```bash
# Upgrade control plane and workers
kubeone upgrade -m kubeone-config.yaml -t tf.json   --ssh-agent-env   --target-version 1.30.0

# The tool handles canary upgrades automatically,
# upgrading one control plane node at a time
```

## kubeadm (Official Kubernetes Bootstrapper)

kubeadm is the official Kubernetes cluster bootstrapping tool, maintained by the Kubernetes SIG Cluster Lifecycle team. It is the most flexible but also the most manual approach to cluster provisioning.

### Key Features

- **Official Kubernetes tool**: Maintained by the upstream Kubernetes project
- **Cloud-agnostic**: Works on any infrastructure — bare metal, VMs, cloud instances
- **Modular design**: Handles only bootstrap; you choose CNI, storage, ingress, and monitoring
- **Certificate management**: Automated PKI with support for custom CAs
- **Component config**: API server, controller manager, scheduler, and kubelet configuration via structured YAML
- **Join workflow**: Simple `kubeadm join` command for adding nodes

### Docker Compose (Local Multi-Node)

```yaml
version: "3.8"
services:
  control-plane:
    image: kindest/node:v1.30.0
    hostname: k8s-control-plane
    privileged: true
    ports:
      - "6443:6443"
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup
    command: ["/usr/local/bin/entrypoint", "/sbin/init"]

  worker-1:
    image: kindest/node:v1.30.0
    hostname: k8s-worker-1
    privileged: true
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup
    depends_on:
      - control-plane
```

### Installation

```bash
# Install kubeadm, kubelet, and kubectl on all nodes
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl

# Add Kubernetes apt repository
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key |   sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /" |   sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

### Creating a Cluster

```bash
# On the control plane node
sudo kubeadm init   --pod-network-cidr=10.244.0.0/16   --service-cidr=10.96.0.0/12   --control-plane-endpoint "k8s.example.com:6443"

# Set up kubeconfig
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install CNI (e.g., Calico)
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml

# Join worker nodes
sudo kubeadm join k8s.example.com:6443   --token <token>   --discovery-token-ca-cert-hash sha256:<hash>
```

### Cluster Upgrade

```bash
# Upgrade control plane
sudo apt-get update
sudo apt-get install -y kubeadm=1.30.0-*
sudo kubeadm upgrade apply v1.30.0

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet=1.30.0-* kubectl=1.30.0-*
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Upgrade each worker node
sudo apt-get install -y kubeadm=1.30.0-*
sudo kubeadm upgrade node
sudo apt-get install -y kubelet=1.30.0-* kubectl=1.30.0-*
```

## Comparison: When to Use Each Tool

### Choose kops if:
- You are primarily deploying on AWS
- You want managed etcd and automatic node group management
- You prefer declarative cluster configuration
- You need rolling upgrades with minimal manual intervention
- Your team values maturity and a large community (16,600+ stars)

### Choose kubeone if:
- You need multi-cloud or hybrid cloud deployments
- You want Terraform-based infrastructure provisioning
- You need automated canary upgrades with rollback
- You plan to integrate with Kubermatic Kubernetes Platform for day-two operations
- You prefer a structured lifecycle management approach

### Choose kubeadm if:
- You are deploying on bare metal or custom infrastructure
- You need maximum control over every aspect of the cluster
- You are building custom distributions or specialized clusters
- You want to learn Kubernetes internals deeply
- You need cloud-agnostic deployment with no vendor lock-in

## Why Self-Host Your Kubernetes Cluster?

Running your own Kubernetes cluster gives you complete control over the control plane, networking, and storage configuration. You avoid the per-node pricing premiums of managed services like EKS, GKE, and AKS while maintaining the flexibility to customize every component.

For teams managing multiple clusters across different environments, self-hosted provisioning tools like kops, kubeone, and kubeadm provide the foundation for consistent, repeatable infrastructure. When combined with GitOps workflows and infrastructure-as-code practices, these tools enable fully automated cluster lifecycle management.

For Kubernetes network policies and CNI selection, see our [CNI comparison guide](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies-guide-2026/). If you need cluster management platforms rather than provisioning tools, check our [Kubernetes management comparison](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/). For Kubernetes security hardening, our [container and cluster hardening guide](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/) covers essential best practices.

## FAQ

### What is the difference between kops and kubeone?

kops is a declarative cluster provisioning tool primarily designed for AWS, with support for a few other platforms. It manages the entire cluster lifecycle including etcd, node groups, and rolling upgrades. kubeone, developed by Kubermatic, uses Terraform for infrastructure and focuses on multi-cloud deployments with automated canary upgrades and MachineController-based node management.

### Is kubeadm suitable for production clusters?

Yes, kubeadm is the official Kubernetes bootstrapping tool and is used in production worldwide. However, it requires manual setup for high availability, etcd clustering, and upgrades. For production use, consider combining kubeadm with automation tools like Ansible or using kops/kubeone for managed lifecycle operations.

### Can I migrate from kubeadm to kops or kubeone?

Direct migration is not officially supported. Each tool manages its own cluster state and configuration. The recommended approach is to provision a new cluster with your target tool and migrate workloads using tools like Velero for backup and restore.

### How does kops handle cluster upgrades?

kops performs rolling upgrades by upgrading one node at a time, respecting Pod Disruption Budgets. It updates the cluster specification, then performs a rolling update of the control plane followed by worker nodes. You can control the pace with `--interval` and `--drain-timeout` flags.

### Does kubeone support air-gapped environments?

Yes, kubeone supports air-gapped and offline installations. You can pre-pull required container images and configure kubeone to use a local image registry. This is particularly useful for regulated industries and environments without internet access.

### Which tool is best for bare metal Kubernetes?

kubeadm is the most flexible option for bare metal since it has no cloud dependencies. kubeone also supports bare metal through its Equinix Metal and generic Terraform providers. kops has limited bare metal support through its baremetal provider but is primarily cloud-focused.

### How does etcd management differ between these tools?

kops automatically deploys and manages an etcd cluster as part of the cluster provisioning. kubeone also manages etcd automatically during cluster creation. With kubeadm, you must configure etcd manually — either as a stacked control plane component or as an external cluster — giving you full control but requiring more operational knowledge.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Cluster Provisioning: kops vs kubeone vs kubeadm (2026)",
  "description": "Compare three leading Kubernetes cluster provisioning tools: kops for AWS-native deployments, kubeone for multi-cloud lifecycle management, and kubeadm for maximum flexibility on bare metal and custom infrastructure.",
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
