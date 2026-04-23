---
title: "KubeEdge vs OpenYurt vs SuperEdge: Best Self-Hosted Edge Computing Platforms 2026"
date: 2026-04-23
tags: ["kubernetes", "edge-computing", "kubeedge", "openyurt", "superedge", "self-hosted", "cloud-native"]
draft: false
description: "Compare the top three open-source edge computing platforms built on Kubernetes. Learn which self-hosted solution — KubeEdge, OpenYurt, or SuperEdge — is best for your edge infrastructure in 2026."
---

Edge computing brings data processing and application logic closer to where data is generated — factories, retail locations, vehicles, remote sites, and IoT deployments. Instead of sending everything to a centralized cloud, edge computing reduces latency, saves bandwidth, and keeps sensitive data local.

For teams already invested in Kubernetes, the challenge is extending that orchestration layer to the edge. Running a standard Kubernetes cluster at the edge is impractical: the control plane is too heavy, nodes frequently lose connectivity, and bandwidth constraints make constant API server communication impossible.

This is where specialized edge computing platforms come in. Three open-source projects have emerged as the leading Kubernetes-native solutions for edge deployments: **KubeEdge** (CNCF graduation-level), **OpenYurt** (CNCF incubating), and **SuperEdge** (Tencent-backed). Each extends Kubernetes to the edge with different architectural choices, trade-offs, and feature sets.

This guide compares all three platforms in depth — architecture, deployment, edge autonomy, device management, and real-world suitability — so you can choose the right tool for your edge infrastructure.

## Why Self-Host Edge Computing Infrastructure?

Running edge computing software yourself, rather than relying on managed cloud services, offers several concrete advantages:

- **Data sovereignty**: Process sensitive data on-premises without it ever leaving your network. Critical for healthcare, manufacturing, and financial services.
- **Reduced latency**: Local processing means sub-millisecond response times for time-sensitive applications like robotics, quality inspection, and autonomous systems.
- **Bandwidth savings**: Filter and aggregate data at the edge before sending summaries to the cloud. A single camera stream can consume 4-8 Mbps — processing locally can reduce that to kilobytes.
- **Offline operation**: Edge nodes must continue functioning when the WAN link fails. Self-hosted edge platforms provide local autonomy that managed cloud edge services cannot guarantee.
- **Cost control**: No per-device or per-node licensing fees. The platforms below are all fully open-source under Apache 2.0.

If you're already running Kubernetes in the cloud (see our [k3s vs k0s vs Talos Linux guide](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/) for lightweight distributions), extending that same control plane to the edge is the most operationally consistent approach.

## KubeEdge — CNCF Graduated Edge Framework

**GitHub**: [kubeedge/kubeedge](https://github.com/kubeedge/kubeedge) | **Stars**: 7,429 | **Latest**: v1.23.0 | **Language**: Go

KubeEdge is the most mature and widely adopted edge computing platform for Kubernetes. Originally developed by Huawei and donated to the CNCF in 2019, it reached graduation status in October 2024 — the highest maturity level in the CNCF lifecycle.

### Architecture

KubeEdge follows a cloud-edge split architecture:

- **CloudHub** (cloud side): A WebSocket server that watches for changes in the Kubernetes API server, caches messages, and communicates with EdgeHub on each edge node.
- **EdgeController** (cloud side): An extended Kubernetes controller that manages edge node and pod metadata, routing data to specific edge nodes.
- **DeviceController** (cloud side): Manages edge device metadata and synchronizes device status between cloud and edge.
- **EdgeCore** (edge side): The lightweight agent running on each edge node. It includes EdgeHub (communicates with CloudHub), MetaManager (local metadata store), DeviceTwin (device state management), and EventBus (MQTT broker for device communication).

The key design principle is that the Kubernetes API server stays entirely in the cloud. Edge nodes do not run a full control plane — they connect back via WebSocket and maintain a local metadata cache for autonomy.

### Key Advantages

- **Edge autonomy**: EdgeCore caches pod and config metadata locally. If the cloud-edge link drops, running containers continue operating normally. The node can handle restarts and recover without cloud connectivity.
- **MQTT support**: Built-in MQTT broker enables direct integration with IoT sensors, PLCs, and industrial devices using the standard industrial messaging protocol.
- **Device management via CRDs**: Define edge devices (cameras, sensors, actuators) as Kubernetes Custom Resource Definitions. Manage them with the same `kubectl` workflows you use for pods and services.
- **Resource-constrained friendly**: EdgeCore runs on hardware with as little as 256MB RAM and single-core ARM processors.
- **Large ecosystem**: As a CNCF graduated project, KubeEdge has the most contributors, documentation, and community support of the three platforms.

### Deployment

KubeEdge uses `keadm` — a command-line tool that bootstraps both cloud and edge sides:

```bash
# Install keadm on the cloud node
wget https://github.com/kubeedge/kubeedge/releases/download/v1.23.0/keadm-v1.23.0-linux-amd64.tar.gz
tar -zxvf keadm-v1.23.0-linux-amd64.tar.gz
sudo cp keadm/keadm /usr/local/bin/

# Initialize the cloud side (runs on a machine with kubectl access)
sudo keadm init --advertise-address=<CLOUD_NODE_IP>

# On the edge node, join the cloud
sudo keadm join --cloudcore-ipport=<CLOUD_NODE_IP>:10000 --token=<TOKEN>
```

For a cloud-native installation, KubeEdge also provides Helm charts:

```yaml
# Install via Helm
helm repo add kubeedge https://kubeedge.github.io/charts
helm install kubeedge kubeedge/cloudcore --namespace kubeedge --create-namespace
```

A sample deployment manifest for scheduling workloads to edge nodes uses node selectors and tolerations:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edge-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: edge-app
  template:
    metadata:
      labels:
        app: edge-app
    spec:
      nodeSelector:
        node-role.kubernetes.io/edge: ""
      tolerations:
      - key: "node-role.kubernetes.io/edge"
        operator: "Exists"
        effect: "NoSchedule"
      containers:
      - name: processor
        image: your-registry/edge-processor:v1.0
        resources:
          limits:
            cpu: "500m"
            memory: "256Mi"
```

## OpenYurt — Alibaba's Cloud-Edge Extension

**GitHub**: [openyurtio/openyurt](https://github.com/openyurtio/openyurt) | **Stars**: 1,949 | **Latest**: v1.6.1 | **Language**: Go

OpenYurt was developed by Alibaba and donated to CNCF in 2020. It takes a different approach from KubeEdge: instead of replacing the edge node agent, it injects a sidecar proxy (YurtHub) on each edge node that intercepts and manages all communication to the API server.

### Architecture

OpenYurt's architecture consists of four main components:

- **YurtHub**: A node-local sidecar proxy running as a static pod on each edge node. It intercepts all kubelet-to-apiserver traffic, caches responses, and serves cached data during network outages. This approach means the edge node still uses the standard kubelet — no custom edge agent is needed.
- **Yurt-Manager**: A set of controllers and webhooks that manage edge-specific lifecycle operations, including node pooling, application deployment, and device integration.
- **Raven-Agent**: Handles inter-node and edge-to-cloud networking, providing Layer 3 connectivity between pods across different physical regions. This effectively extends the pod network across WAN links as if all nodes were in the same data center.
- **YurtIoTDock**: Bridges EdgeX Foundry (the Linux Foundation IoT platform) with Kubernetes CRDs, enabling device management through the Kubernetes API.

### Key Advantages

- **Non-intrusive design**: Because YurtHub operates as a transparent proxy, edge nodes run the standard kubelet. This means OpenYurt is compatible with any Kubernetes distribution and version with minimal adaptation.
- **Node pooling**: Groups edge nodes into logical "pools" based on physical location. You can schedule applications to run in specific pools (e.g., "Beijing-DC1", "Shanghai-DC2") using native Kubernetes affinity rules.
- **Built-in network tunneling**: Raven-Agent eliminates the need for a separate overlay network or VPN between edge sites. Pods in different edge pools can communicate directly.
- **Application daemon**: Ensures that edge applications are automatically deployed and maintained in each pool, even when new nodes join or leave.
- **Helm-based installation**: Deployed entirely through Helm charts, making it easy to integrate into existing GitOps pipelines.

### Deployment

OpenYurt converts an existing vanilla Kubernetes cluster into an edge cluster:

```bash
# Install yurtctl
wget https://github.com/openyurtio/openyurt/releases/download/v1.6.1/yurtctl-v1.6.1-linux-amd64.tar.gz
tar -zxvf yurtctl-v1.6.1-linux-amd64.tar.gz
sudo cp yurtctl /usr/local/bin/

# Convert an existing Kubernetes cluster to OpenYurt
yurtctl convert --provider kubeadm

# Label edge nodes
kubectl label node <edge-node-name> openyurt.io/is-edge-node=true

# Deploy YurtHub to an edge node
yurtctl join --token <TOKEN> --discovery-token-ca-cert-hash <HASH>
```

Helm chart installation for the core components:

```bash
helm repo add openyurt https://openyurtio.github.io/charts
helm install yurt-manager openyurt/yurt-manager --namespace openyurt-system --create-namespace
```

YurtHub configuration for autonomous operation:

```yaml
# YurtHub caches API responses locally at /var/lib/yurthub
# During network outages, kubelet reads from the cache
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: yurthub
  namespace: kube-system
spec:
  template:
    spec:
      containers:
      - name: yurthub
        image: openyurt/yurthub:v1.6.1
        args:
        - --bind-address=127.0.0.1
        - --server-addr=https://<API_SERVER_IP>:6443
        - --node-name=$(NODE_NAME)
        volumeMounts:
        - name: cache-dir
          mountPath: /var/lib/yurthub
```

## SuperEdge — Tencent's Edge-Native Platform

**GitHub**: [superedge/superedge](https://github.com/superedge/superedge) | **Stars**: 1,071 | **Latest**: v0.9.0 | **Language**: Go

SuperEdge is an open-source edge computing project originally developed by Tencent and contributed to the OpenAtom Foundation. It focuses on providing a complete edge-native solution with built-in health monitoring, application orchestration, and network tunneling — all designed for managing Kubernetes clusters spread across multiple geographical regions.

### Architecture

SuperEdge's architecture extends Kubernetes with several specialized components:

- **EdgeHealth**: A distributed health monitoring system that runs on edge nodes. Unlike Kubernetes' standard node health checks (which are cloud-side), EdgeHealth performs edge-side monitoring and can detect and respond to node failures locally without cloud coordination.
- **Application Grid**: A custom controller that manages edge application deployment across multiple edge regions. It ensures that applications are deployed and maintained in a closed-loop manner at the edge — meaning edge services don't depend on the cloud for their lifecycle.
- **TunnelCloud/TunnelEdge**: A network tunneling system that provides secure communication between the cloud control plane and edge nodes, even across NAT and firewall boundaries.
- **Kins (v0.9.0+)**: The newest feature provisions lightweight K3s sub-clusters on edge NodeUnits. This enables fully offline operation — each edge site runs its own K3s cluster managed by SuperEdge.
- **Lite-APIServer**: A lightweight API server component on the edge side that caches and serves Kubernetes resources locally during cloud-edge disconnections.

### Key Advantages

- **Multi-level edge autonomy**: SuperEdge provides the most granular autonomy levels — from L3 (read-only during disconnection) to L4/L5 (fully offline K3s sub-cluster operation).
- **Native K3s integration**: The Kins feature provisions real K3s clusters at the edge, giving you a full Kubernetes control plane at each site while maintaining central management.
- **Distributed health monitoring**: Edge-side health checks mean faster failure detection and response without relying on cloud-side node health probes.
- **NAT traversal**: Built-in tunneling handles complex network topologies where edge nodes sit behind NAT gateways or firewalls — common in retail and branch office deployments.
- **Easy conversion**: SuperEdge can convert a standard kubeadm cluster to an edge cluster with a single command, similar to OpenYurt.

### Deployment

SuperEdge provides `edgeadm`, a modified version of kubeadm that bootstraps edge-ready clusters:

```bash
# Download edgeadm
wget https://github.com/superedge/edgeadm/releases/download/v0.9.0/linux-amd64-edgeadm-v0.9.0.tar.gz
tar -zxvf linux-amd64-edgeadm-v0.9.0.tar.gz
sudo cp edgeadm /usr/local/bin/

# Install the cloud (control plane) node
sudo edgeadm init --install-pkg-path ./kube-linux-*.tar.gz \
  --apiserver-cert-extra-sans=<CLOUD_IP> \
  --apiserver-advertise-address=<CLOUD_IP> \
  --edge-enable-revision=latest

# Join an edge node
sudo edgeadm join <CLOUD_IP>:<PORT> --token <TOKEN> \
  --discovery-token-ca-cert-hash <HASH> \
  --install-pkg-path ./kube-linux-*.tar.gz \
  --edge-enable-revision=latest
```

Deploying the edge-health monitoring component:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: edge-health
  namespace: edge-system
spec:
  selector:
    matchLabels:
      app: edge-health
  template:
    metadata:
      labels:
        app: edge-health
    spec:
      containers:
      - name: edge-health
        image: edgehealth/edge-health:v0.9.0
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
```

## Comparison Table

| Feature | KubeEdge | OpenYurt | SuperEdge |
|---|---|---|---|
| **CNCF Status** | Graduated | Incubating | Not CNCF (OpenAtom) |
| **GitHub Stars** | 7,429 | 1,949 | 1,071 |
| **Latest Version** | v1.23.0 | v1.6.1 | v0.9.0 |
| **Last Updated** | Apr 2026 | Apr 2026 | v0.9.0 release |
| **Primary Language** | Go | Go | Go |
| **Edge Agent** | Custom (EdgeCore) | Sidecar Proxy (YurtHub) | Modified kubelet (edgeadm) |
| **Cloud-Edge Protocol** | WebSocket | HTTP (intercepted) | Tunnel (TCP/HTTP) |
| **Edge Autonomy** | Local metadata cache | YurtHub response cache | L3-L5 (up to offline K3s) |
| **Device Management** | DeviceTwin CRD + MQTT | YurtIoTDock (EdgeX Foundry) | Custom CRDs |
| **Network Tunneling** | No (requires external) | Raven-Agent (built-in) | TunnelCloud/TunnelEdge (built-in) |
| **IoT Protocol** | MQTT (native) | EdgeX Foundry bridge | Custom |
| **Helm Support** | Yes | Yes | Limited |
| **CLI Tool** | keadm | yurtctl | edgeadm |
| **K3s Integration** | No | No | Yes (Kins feature) |
| **Health Monitoring** | Standard K8s | Standard K8s | EdgeHealth (distributed) |
| **Node Pooling** | Manual labels | Native (Pool CRD) | NodeUnit concept |
| **Min Edge Resources** | 256MB RAM | 512MB RAM | 512MB RAM |
| **Multi-Cluster** | EdgeSite feature | YurtManager | Kins sub-clusters |

## Choosing the Right Platform

### Pick KubeEdge if:

- You need the most mature, battle-tested solution with the largest community
- MQTT device integration is a core requirement (industrial IoT, sensor networks)
- You want CNCF graduation-level project assurance for enterprise adoption
- Your edge nodes have very constrained resources (256MB RAM)
- You need extensive documentation and a large pool of experienced operators

KubeEdge's graduation status and 7,400+ stars make it the safest choice for organizations that need vendor-neutral, community-backed infrastructure. The MQTT integration is uniquely valuable for industrial IoT deployments.

### Pick OpenYurt if:

- You want the least disruptive migration path (YurtHub proxy doesn't replace kubelet)
- You need multi-region node pooling with location-aware scheduling
- Built-in overlay networking (Raven-Agent) is important for cross-site pod communication
- You want Helm-native installation that fits into existing GitOps workflows
- EdgeX Foundry integration is already part of your IoT stack

OpenYurt's non-intrusive design is its strongest differentiator. Because it doesn't replace kubelet, you can convert a running production cluster to OpenYurt with minimal risk.

### Pick SuperEdge if:

- Fully offline edge operation is a requirement (Kins provisions local K3s clusters)
- You need distributed health monitoring that doesn't depend on cloud-side probes
- Edge nodes are behind NAT/firewalls with no direct inbound connectivity
- You want the most granular autonomy levels (L3 through L5)
- You're already in the Tencent ecosystem or prefer OpenAtom Foundation governance

SuperEdge's Kins feature — provisioning real K3s sub-clusters at each edge site — is unique among the three platforms. For scenarios where the WAN link can go down for hours or days, this level of autonomy is unmatched.

## Migration and Setup Considerations

Before deploying any edge platform, consider these infrastructure prerequisites:

```bash
# Verify edge node connectivity to cloud
ping -c 3 <CLOUD_NODE_IP>

# Check required ports
# KubeEdge: 10000 (CloudHub WebSocket), 10002 (DeviceTwin)
# OpenYurt: 6443 (API server, intercepted by YurtHub)
# SuperEdge: 6443 (API server), 10250 (kubelet tunnel)

# Ensure DNS resolution works bidirectionally
nslookup <CLOUD_NODE_HOSTNAME>
nslookup <EDGE_NODE_HOSTNAME>

# Verify time synchronization (critical for TLS certificates)
timedatectl status
```

For resource planning, a typical edge node running any of these platforms requires:

- **Cloud node**: 4+ CPU cores, 8GB+ RAM (runs the full Kubernetes control plane)
- **Edge node**: 2+ CPU cores, 1GB+ RAM minimum (256MB for KubeEdge EdgeCore)
- **Network**: Stable WebSocket/HTTP connection with 1-5ms latency for optimal performance

For teams managing multiple edge sites, consider pairing your edge platform with [Rancher vs KubeSpray vs KinD](../rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) for centralized cluster management, and securing your edge workloads with our [Kubernetes hardening guide](../kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/).

## FAQ

### What is the difference between edge computing and cloud computing?

Cloud computing processes data in centralized data centers, requiring all data to travel over the network. Edge computing processes data closer to where it's generated — on local servers, gateways, or devices — reducing latency and bandwidth usage. Edge computing is complementary to cloud computing, not a replacement: raw data is processed locally at the edge, while aggregated results and long-term storage go to the cloud.

### Can I run these edge platforms on Raspberry Pi or ARM devices?

Yes, all three platforms support ARM architectures. KubeEdge has the lightest edge agent (EdgeCore) and can run on devices with as little as 256MB RAM, making it suitable for Raspberry Pi 4 and similar SBCs. OpenYurt and SuperEdge require slightly more resources (512MB+) since their edge components (YurtHub and Lite-APIServer) run as additional processes on the node.

### Do I need to rebuild my Kubernetes cluster to use edge computing platforms?

No, not necessarily. OpenYurt and SuperEdge can convert an existing kubeadm-based Kubernetes cluster into an edge cluster with a single command (`yurtctl convert` and `edgeadm init`, respectively). KubeEdge can be installed alongside an existing Kubernetes cluster using its Helm chart or `keadm init` command. In all cases, your existing workloads continue running — the edge components are added to the cluster without disrupting current operations.

### What happens to edge workloads when the network connection to the cloud is lost?

All three platforms provide edge autonomy mechanisms. KubeEdge's EdgeCore caches pod metadata locally so containers keep running. OpenYurt's YurtHub caches API server responses and serves them to kubelet during outages. SuperEdge provides the most options — from L3 autonomy (read-only cached operations) to L5 (fully autonomous K3s sub-cluster with its own control plane). The specific behavior depends on the platform and configuration.

### How do these platforms compare to running plain K3s at each edge site?

Running independent K3s clusters at each site gives you full autonomy but requires managing each cluster separately — no centralized view, no cross-site scheduling, and no unified deployment pipeline. Edge computing platforms like KubeEdge, OpenYurt, and SuperEdge provide a single Kubernetes control plane that manages all edge sites as one logical cluster, with built-in autonomy for network outages. SuperEdge's Kins feature actually combines both approaches: it provisions K3s sub-clusters at the edge while maintaining central orchestration.

### Which platform is best for industrial IoT (IIoT)?

KubeEdge is the strongest choice for IIoT scenarios. Its native MQTT support (via the EventBus component) directly integrates with industrial sensors, PLCs, and SCADA systems that communicate over MQTT. The DeviceTwin CRD provides a Kubernetes-native way to define and manage edge devices. OpenYurt can also integrate with IoT systems through its YurtIoTDock bridge to EdgeX Foundry, but this requires an additional EdgeX deployment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "KubeEdge vs OpenYurt vs SuperEdge: Best Self-Hosted Edge Computing Platforms 2026",
  "description": "Compare the top three open-source edge computing platforms built on Kubernetes. Learn which self-hosted solution — KubeEdge, OpenYurt, or SuperEdge — is best for your edge infrastructure in 2026.",
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
