---
title: "Self-Hosted Network Emulation Platforms — Mininet vs Containernet vs CORE Guide (2026)"
date: "2026-05-23"
tags: ["network-emulation", "mininet", "containernet", "core-network", "networking", "testing"]
draft: false
---

Network emulation is essential for testing network protocols, validating SDN controllers, evaluating routing algorithms, and training network engineers — all without requiring physical hardware. Self-hosted network emulation platforms create virtual network topologies on a single machine, enabling researchers and engineers to experiment safely. In this guide, we compare three leading open-source network emulation tools: **Mininet**, **Containernet**, and **CORE (Common Open Research Emulator)**.

## Mininet: The Standard for SDN Testing

Mininet is the most widely used network emulation platform, specifically designed for Software-Defined Networking (SDN) research and development. Created by Bob Lantz at Stanford University, Mininet creates a realistic virtual network running real kernel, switch, and application code on a single machine.

Mininet uses **Linux network namespaces** to create isolated virtual hosts, each with its own network stack. Open vSwitch instances serve as virtual switches, and the entire topology is programmable via Python APIs.

Key features include:
- **Instant topology creation**: Launch a 100-node network in seconds
- **Real kernel networking**: Uses actual Linux network stack, not simulated
- **OpenFlow support**: Native integration with OpenFlow switches for SDN testing
- **Python API**: Programmatic topology creation and experiment automation
- **CLI interface**: Interactive shell for running commands on virtual hosts
- **Custom topologies**: Define arbitrary network structures with configurable links
- **Bandwidth/delay emulation**: Set link parameters (bandwidth, delay, loss) via tc

Mininet is the de facto standard for SDN controller testing, with built-in support for OpenFlow controllers like OpenDaylight, Ryu, and Floodlight.

## Containernet: Docker-Integrated Network Emulation

Containernet is an extension of Mininet that adds first-class support for Docker containers as network nodes. While Mininet hosts run as lightweight processes, Containernet nodes are full Docker containers with their own filesystems, processes, and resource limits.

This makes Containernet ideal for testing **containerized network services** — load balancers, proxies, firewalls, and microservices — in realistic network conditions.

Key features include:
- **Docker container hosts**: Each node is a full Docker container
- **Mininet compatibility**: All Mininet APIs and CLI commands work identically
- **Resource isolation**: CPU, memory, and I/O limits per container
- **Volume mounting**: Mount host directories into container nodes
- **Custom Docker images**: Use any Docker image as a network node
- **Link emulation**: Same bandwidth, delay, and loss control as Mininet
- **Docker API integration**: Programmatically manage containers during experiments

Containernet bridges the gap between network emulation and container orchestration, making it ideal for testing microservice deployments.

## CORE (Common Open Research Emulator): Full System Emulation

CORE is a network emulation tool that provides a graphical interface for creating and experimenting with virtual networks. Unlike Mininet, which uses lightweight namespaces, CORE can run full system emulation with virtual machines or containers.

CORE provides a **drag-and-drop GUI** for network topology design, making it accessible to users who prefer visual configuration over scripting. It supports both real-time emulation and faster-than-real-time simulation.

Key features include:
- **Graphical topology editor**: Drag-and-drop network design with a Qt-based GUI
- **Multiple node types**: Hosts, routers, switches, PCs, and cloud nodes
- **Service configuration**: Pre-configured services (OSPF, BGP, DHCP, DNS, iptables)
- **Real-time and accelerated modes**: Run at wall-clock speed or faster for simulation
- **EMANE integration**: Wireless and RF network emulation support
- **Session recording**: Save and replay network experiments
- **Python API**: Scriptable topology creation and experiment control
- **Docker container support**: Nodes can run as Docker containers or full VMs

CORE is the most comprehensive option for users who need a GUI-based approach with support for complex routing protocols and wireless emulation.

## Feature Comparison Table

| Feature | Mininet | Containernet | CORE |
|---------|---------|-------------|------|
| Node Type | Linux namespace | Docker container | Container/VM/host |
| Interface | Python API + CLI | Python API + CLI | GUI + Python API |
| SDN Support | Native OpenFlow | Native OpenFlow | Via emulation |
| Link Emulation | tc-based | tc-based | tc-based |
| Docker Integration | No | Native | Via container mode |
| GUI | No | No | Full Qt-based GUI |
| Wireless Emulation | Limited | Limited | EMANE integration |
| Routing Protocols | Via host OS | Via container OS | Pre-configured (OSPF, BGP) |
| Resource Limits | cgroups | Docker limits | Docker/VM limits |
| Scalability | 1000+ hosts | 100-500 containers | 50-200 nodes |
| Best For | SDN testing | Container networking | Visual network design |

## Installation and Deployment

### Mininet Setup

Mininet can be installed from source or via the official VM image. For Docker-based deployment:

```bash
# Install Mininet from source
git clone https://github.com/mininet/mininet.git
cd mininet
git checkout -b 2.3.1 2.3.1
util/install.sh -a

# Verify installation
sudo mn --version

# Launch a simple topology: 2 hosts, 1 switch, 1 controller
sudo mn --topo single,2 --mac --switch ovsk --controller remote
```

Docker Compose deployment for a Mininet testing environment:

```yaml
services:
  mininet:
    image: wnpl/mininet:latest
    container_name: mininet
    hostname: mininet
    privileged: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./mininet-topologies:/topologies
    working_dir: /topologies
    networks:
      - emulation
    command: ["bash"]
    stdin_open: true
    tty: true

networks:
  emulation:
    driver: bridge
```

Example Python topology script:

```python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink

class MyTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        self.addLink(h1, s1, bw=10, delay='5ms')
        self.addLink(h2, s1, bw=10, delay='5ms')

topo = MyTopo()
net = Mininet(topo=topo, link=TCLink)
net.start()
net.pingAll()
net.stop()
```

### Containernet Setup

Containernet extends Mininet with Docker support:

```bash
# Install Containernet from source
git clone https://github.com/Containernet/containernet.git
cd containernet/ansible
sudo ansible-playbook -i "localhost," -c local install.yml

# Verify installation
sudo python3 examples/containernet_example.py
```

Docker Compose configuration:

```yaml
services:
  containernet:
    image: containernet/containernet:latest
    container_name: containernet
    hostname: containernet
    privileged: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./containernet-topologies:/topologies
    working_dir: /topologies
    networks:
      - emulation
    command: ["bash"]
    stdin_open: true
    tty: true

networks:
  emulation:
    driver: bridge
```

Example Containernet topology with Docker containers:

```python
from mininet.net import Containernet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.log import info

net = Containernet(controller=None)
info('Adding Docker nodes...')
d1 = net.addDocker('d1', ip='10.0.0.1', dimage="ubuntu:22.04")
d2 = net.addDocker('d2', ip='10.0.0.2', dimage="nginx:latest")

info('Adding switch and links...')
s1 = net.addSwitch('s1')
net.addLink(d1, s1, bw=10, delay='5ms')
net.addLink(d2, s1, bw=10, delay='5ms')

info('Starting network...')
net.start()
net.pingAll()
info('Running test on nginx container...')
info(d1.cmd('curl -s http://10.0.0.2'))
net.stop()
```

### CORE Setup

CORE provides both GUI and CLI installation:

```bash
# Install CORE from packages (Ubuntu/Debian)
sudo apt-get install core-network

# Install via pip
pip3 install core-network

# Launch the GUI
core-gui &

# Or run in daemon mode for scripted experiments
core-daemon &
```

Docker Compose for CORE:

```yaml
services:
  core:
    image: paulsperl/core-network:latest
    container_name: core-emulator
    hostname: core
    privileged: true
    volumes:
      - ./core-sessions:/root/.core/sessions
      - /tmp/.core:/tmp/.core
    ports:
      - "8080:8080"
    networks:
      - emulation
    command: ["core-daemon", "-f"]
    stdin_open: true
    tty: true

networks:
  emulation:
    driver: bridge
```

## Choosing the Right Network Emulator

**Choose Mininet if:**
- You are testing SDN controllers (OpenFlow, P4)
- You need maximum scalability (1000+ virtual hosts)
- You prefer Python scripting over graphical interfaces
- Your focus is network protocol research and development

**Choose Containernet if:**
- You are testing containerized microservices in network scenarios
- You need Docker containers as first-class network nodes
- You want to test real application deployments (web servers, databases)
- Your experiments require container-specific features (volumes, environment variables)

**Choose CORE if:**
- You prefer a graphical topology editor
- You need pre-configured routing protocols (OSPF, BGP, RIP)
- You are training network engineers who benefit from visual tools
- You need wireless/RF emulation via EMANE integration

For teams working with SDN controllers, our [OpenDaylight vs Floodlight vs Ryu guide](../2026-05-18-self-hosted-sdn-controllers-onos-vs-opendaylight-vs-floodlight/) covers the controllers that pair with these emulation tools. For broader network protocol testing, our [network packet broker comparison](../2026-05-19-self-hosted-network-packet-brokers-ovs-pfring-xdp-guide/) covers production traffic management.

## Why Self-Host Network Emulation?

**Cost savings** are immediate — physical network testbeds with multiple switches, routers, and hosts cost thousands of dollars. A single server running Mininet, Containernet, or CORE can emulate entire data center topologies at zero additional hardware cost.

**Experiment reproducibility** is guaranteed with software-defined topologies. Every test runs on an identical virtual network, eliminating hardware variability. Python scripts and configuration files serve as version-controlled experiment definitions that can be shared, reviewed, and reproduced by anyone.

**Risk-free testing** allows you to test destructive network scenarios — routing loops, broadcast storms, link failures — without impacting production infrastructure. Virtual networks can be destroyed and recreated instantly, enabling rapid iteration.

**Skill development** is accelerated when engineers can practice on realistic topologies. Network certification candidates (CCNA, CCNP, JNCIA) can build complex lab environments on a laptop, practicing routing protocols, firewall rules, and troubleshooting techniques without dedicated hardware.

**Protocol validation** benefits from the ability to test new protocols against realistic network conditions. Researchers developing new routing algorithms, congestion control mechanisms, or QoS policies can validate their work on emulated networks before deploying to production.

## FAQ

### Can Mininet emulate WAN conditions like packet loss and jitter?

Yes, Mininet uses Linux traffic control (tc) to set link parameters including bandwidth, delay, packet loss, and jitter. You can specify these when creating links: `net.addLink(h1, s1, bw=10, delay='10ms', loss=1, jitter='2ms')`. This allows realistic WAN condition emulation for testing application behavior under poor network conditions.

### How many virtual hosts can Mininet realistically support?

Mininet can support 1,000+ virtual hosts on a modern server with sufficient RAM and CPU. The actual limit depends on host memory (each namespace uses minimal RAM), CPU cores (for packet processing), and the complexity of your topology. For extreme scale, Containernet's Docker containers consume more resources, typically supporting 100-500 nodes.

### Does CORE support OpenFlow and SDN testing?

CORE can emulate OpenFlow switches through its integration with external tools, but it is not primarily designed for SDN testing like Mininet. For SDN controller testing, Mininet is the better choice due to its native OpenFlow switch implementation and direct controller integration.

### Can I run Containernet on macOS or Windows?

Containernet requires Linux kernel features (network namespaces, cgroups) that are not available natively on macOS or Windows. You can run it inside a Linux VM (VirtualBox, VMware) or use Docker Desktop with a Linux backend. Mininet has similar requirements.

### How do I save and share network topologies?

Mininet and Containernet topologies are defined as Python scripts, which can be version-controlled with Git and shared via repositories. CORE sessions can be saved as `.imn` files and shared with other CORE users. For all three tools, storing topology definitions in a Git repository ensures reproducibility and collaboration.

### Is network emulation suitable for production testing?

Network emulation is ideal for pre-production testing and validation. However, emulated networks cannot perfectly replicate production hardware behavior (especially ASIC-level forwarding, hardware offload, or line-rate performance). Always validate critical changes on production-equivalent hardware before deployment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Emulation Platforms — Mininet vs Containernet vs CORE Guide",
  "description": "Comprehensive comparison of Mininet, Containernet, and CORE for self-hosted network emulation. Includes Docker deployment configs and topology examples.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
