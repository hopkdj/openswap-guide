---
title: "Self-Hosted Network Emulation Platforms: Mininet vs Containernet vs Mininet-WiFi"
date: "2026-05-16"
tags: ["network-emulation", "sdn", "mininet", "containernet", "networking", "testing"]
draft: false
---

Network emulation is a critical capability for software-defined networking (SDN) research, protocol development, and infrastructure testing. Rather than deploying expensive physical testbeds, open-source network emulation platforms allow engineers and researchers to prototype entire network topologies on a single machine — or across a cluster — using lightweight virtualization.

Three major open-source platforms dominate this space: **Mininet**, the original and most widely adopted SDN emulator; **Containernet**, a Mininet fork that adds Docker container support for emulated hosts; and **Mininet-WiFi**, an extension that brings wireless network emulation capabilities to the Mininet framework.

## What Is Network Emulation?

Network emulation creates a realistic software-based representation of a physical network, complete with routers, switches, hosts, and configurable link properties (bandwidth, delay, loss). Unlike pure simulation, emulation runs actual network stack code — real TCP/IP, real routing protocols, real application traffic — inside isolated namespaces or containers.

The key advantages of self-hosted network emulation over cloud-based alternatives include:

- **Zero egress costs** — all traffic stays within your infrastructure
- **Full isolation** — experiments cannot interfere with production networks
- **Deterministic reproducibility** — save topology files and replay experiments identically
- **Custom kernel support** — test with modified networking kernels, custom TCP stacks, or experimental protocols
- **No vendor lock-in** — open-source tools run on any Linux host

For SDN controller development, see our [OpenDaylight vs Faucet vs Ryu SDN controller guide](../2026-04-29-opendaylight-vs-faucet-vs-ryu-self-hosted-sdn-controller-guide/).
For broader network simulation needs, our [GNS3 vs EVE-ng vs ContainerLab comparison](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) covers complementary tools.

## Mininet: The Original SDN Emulator

Mininet was created by Bob Lantz at Stanford University and released in 2010. It quickly became the de facto standard for SDN research and education, offering a Python API to programmatically define network topologies.

**Key features:**
- Linux network namespaces for host isolation
- Open vSwitch (OVS) for software switching
- Native support for OpenFlow controllers
- Python API for topology definition and automation
- SSH access to emulated hosts
- Configurable link properties (bandwidth, delay, loss)
- Built-in CLI for interactive experimentation

Mininet's architecture uses Linux network namespaces (each host gets its own network stack), virtual Ethernet pairs (for links between hosts and switches), and OVS (for switching). This design is lightweight — you can emulate hundreds of hosts on a single machine.

**Star count:** 5,804+ on GitHub
**Last active:** Regularly maintained
**License:** BSD

## Containernet: Docker Containers as Emulated Hosts

Containernet is a fork of Mininet developed by the SONATA-NFV project that replaces Linux network namespaces with Docker containers as emulated hosts. This enables running full applications (web servers, databases, microservices) inside emulated hosts using real Docker images.

**Key features:**
- Docker containers as emulated hosts (not just network namespaces)
- Full Docker image support — run any containerized application
- Kubernetes cluster emulation via miniKube integration
- NFV (Network Function Virtualization) use cases
- Mininet-compatible API — most Mininet scripts work unchanged
- Docker Compose integration for multi-container topologies
- Resource limits per container (CPU, memory)

The primary advantage of Containernet over Mininet is that emulated hosts run full user-space environments. In Mininet, each host is essentially a stripped-down namespace with a shell. In Containernet, each host is a real Docker container that can run services like nginx, MySQL, or custom microservices.

**Star count:** 458+ on GitHub
**Last updated:** Active development
**License:** BSD (compatible with Mininet)

## Mininet-WiFi: Wireless Network Emulation

Mininet-WiFi extends the Mininet framework to support wireless network emulation, including WiFi (802.11), WiMAX, and mobile ad-hoc networks (MANETs). It adds wireless access points, mobility models, and radio propagation simulation to the base Mininet architecture.

**Key features:**
- WiFi 802.11a/b/g/n/ac emulation
- Access point (AP) nodes with configurable channels
- Station mobility models (random walk, reference point group)
- Radio propagation models (path loss, shadowing)
- SDN-based wireless networking
- Vehicular ad-hoc network (VANET) simulation
- IoT network emulation with low-power nodes
- 3D position-based propagation
- Integration with hostapd for real WiFi stack

Mininet-WiFi is particularly valuable for researchers working on wireless SDN, mesh networks, IoT protocols, and vehicular networking. It maintains API compatibility with base Mininet while adding wireless-specific constructs.

**Star count:** 531+ on GitHub
**Last updated:** Active development
**License:** BSD

## Comparison Table

| Feature | Mininet | Containernet | Mininet-WiFi |
|---------|---------|-------------|--------------|
| **Host Type** | Network namespaces | Docker containers | Network namespaces |
| **Switch** | Open vSwitch | Open vSwitch | Open vSwitch |
| **Wireless Support** | No | No | Yes (802.11a/b/g/n/ac) |
| **Docker Integration** | No | Native (primary feature) | Limited |
| **SDN Controller Support** | OpenFlow (all) | OpenFlow (all) | OpenFlow (all) |
| **Mobility Models** | No | No | Yes (multiple models) |
| **Kubernetes Emulation** | No | Via miniKube | No |
| **Python API** | Yes | Yes (compatible) | Yes (extended) |
| **Radio Propagation** | No | No | Yes |
| **IoT Emulation** | Basic | Via containers | With low-power models |
| **NFV Use Cases** | Limited | Strong (SONATA-NFV) | Limited |
| **GitHub Stars** | 5,804+ | 458+ | 531+ |
| **Best For** | SDN research, education | NFV, microservices testing | Wireless SDN, IoT, VANET |

## Installation and Deployment

### Installing Mininet

The recommended way to install Mininet is from source or via the pre-built VM image:

```bash
# Install from source on Ubuntu/Debian
git clone https://github.com/mininet/mininet.git
cd mininet
git checkout -b 2.3.0 2.3.0
./util/install.sh -a

# Verify installation
sudo mn --test pingall
```

### Installing Containernet

Containernet builds on top of Mininet:

```bash
# Install Mininet first, then Containernet
git clone https://github.com/containernet/containernet.git
cd containernet/ansible
sudo ansible-playbook -i "localhost," -c local install.yml

# Run a test topology with Docker containers
sudo python3 examples/demo.py
```

### Installing Mininet-WiFi

```bash
git clone https://github.com/intrig-unicamp/mininet-wifi.git
cd mininet-wifi
sudo util/install.sh -Wlnfv

# Run a wireless topology test
sudo mnwifi --wifi
```

### Docker Compose Deployment for Containernet

For production testing environments, you can wrap Containernet in a Docker Compose setup:

```yaml
version: "3.8"
services:
  containernet:
    image: containernet/containernet:latest
    privileged: true
    network_mode: host
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./topologies:/topologies
    command: python3 /topologies/my_topology.py
```

## Choosing the Right Platform

**Choose Mininet** when:
- You need the most mature and widely supported platform
- Your focus is SDN controller development (OpenFlow)
- You want maximum compatibility with existing research code
- Lightweight hosts (namespaces) are sufficient for your workload

**Choose Containernet** when:
- You need to run real application workloads in emulated hosts
- Your research involves NFV or microservice architectures
- You want to test Docker-based network functions
- You need Kubernetes cluster emulation

**Choose Mininet-WiFi** when:
- Your research involves wireless networking protocols
- You need to model node mobility and radio propagation
- You are working on IoT or vehicular networks (VANETs)
- You need 802.11 WiFi emulation with APs and stations

## Why Self-Host Network Emulation?

Running network emulation infrastructure on-premises offers significant advantages over cloud-based alternatives for research and development teams. Physical testbeds with real routers, switches, and wireless access points can cost tens of thousands of dollars to procure and maintain. Self-hosted emulation platforms provide a cost-effective alternative that runs on commodity hardware.

Data sovereignty is another critical consideration. Network experiments often involve proprietary protocol implementations, unpublished research data, or sensitive enterprise topologies. Keeping emulation workloads on local infrastructure ensures that topology data, traffic patterns, and experimental results never leave your controlled environment. This is particularly important for defense contractors, telecommunications providers, and academic research groups working on unpublished networking papers.

Performance is a third major factor. Network emulation is I/O and CPU-intensive — running hundreds of emulated hosts with realistic traffic patterns requires low-latency access to the kernel networking stack. Local emulation eliminates the network overhead of cloud-based solutions, enabling more realistic performance measurements and higher-scale topologies on the same hardware budget.

The flexibility to modify the emulation kernel itself — testing custom TCP congestion control algorithms, experimental routing protocols, or novel SDN datapath implementations — is only possible with self-hosted platforms where you control the entire software stack.

For organizations building SDN infrastructure, our [Kubernetes CNI comparison covering Antrea, Kube-OVN, and Spiderpool](../2026-05-10-self-hosted-kubernetes-cni-antrea-kube-ovn-spiderpool-guide/) provides complementary insights into production software-defined networking.

## FAQ

### What is the difference between network emulation and network simulation?

Network emulation runs actual network stack code (real TCP/IP, real routing daemons) inside isolated environments, producing realistic behavior and performance characteristics. Network simulation uses mathematical models to approximate network behavior — faster but less accurate. Mininet, Containernet, and Mininet-WiFi are emulators because they run real Linux networking code.

### Can Mininet run on Windows or macOS?

Mininet requires Linux because it relies on Linux network namespaces and Open vSwitch. On Windows or macOS, you must run Mininet inside a Linux VM (VirtualBox, VMware) or use WSL2 on Windows with a nested Linux VM. Containernet has the same Linux requirement due to Docker dependencies.

### How many hosts can Mininet emulate on a single machine?

Mininet can emulate 1,000+ hosts on a modern server with 32+ GB RAM. The actual limit depends on available memory (each namespace uses ~50-100 MB) and CPU cores. For very large topologies, distributed Mininet (across multiple physical machines) is supported.

### Is Containernet backward-compatible with Mininet scripts?

Yes, Containernet maintains API compatibility with Mininet. Most existing Mininet Python scripts work unchanged in Containernet. The primary difference is that you use `Docker` class instead of `Host` class to create container-based emulated hosts.

### Can Mininet-WiFi emulate 5G networks?

Mininet-WiFi supports 802.11 WiFi standards and can be extended for 5G research through custom modules. However, full 5G NR (New Radio) emulation requires additional components. For 5G core network emulation, consider tools like UERANSIM or Open5GS alongside Mininet-WiFi.

### Does network emulation support real traffic replay?

Yes. All three platforms can capture real network traffic (via tcpdump on emulated links) and replay it using tools like tcpreplay. This enables realistic testing of SDN controllers and network functions under production-like traffic loads.

### What OpenFlow versions are supported?

Mininet and its derivatives support OpenFlow 1.0 through 1.5 via Open vSwitch. The specific version depends on your OVS installation and SDN controller capabilities. OVS 3.x supports OpenFlow 1.5 natively.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Emulation Platforms: Mininet vs Containernet vs Mininet-WiFi",
  "description": "Compare three open-source network emulation platforms for SDN research and testing: Mininet, Containernet, and Mininet-WiFi. Installation guides, feature comparison, and deployment tips.",
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
