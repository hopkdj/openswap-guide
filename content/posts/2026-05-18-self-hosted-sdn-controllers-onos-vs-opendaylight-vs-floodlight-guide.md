---
title: "Self-Hosted SDN Controllers: ONOS vs OpenDaylight vs Floodlight (2026)"
date: "2026-05-18"
tags: ["sdn", "openflow", "network-automation", "onos", "opendaylight", "floodlight", "controller"]
draft: false
---

Software-Defined Networking (SDN) decouples the control plane from the data plane, enabling centralized network programmability through standardized protocols like OpenFlow. At the heart of any SDN deployment sits the SDN controller — the "network operating system" that manages flow rules, discovers topology, and exposes programmable APIs for network automation.

In this guide, we compare three of the most established open-source SDN controller platforms: **ONOS** (Open Network Operating System), **OpenDaylight**, and **Floodlight**. Each takes a different architectural approach and targets different deployment scales, from research labs to production enterprise networks.

## What Is an SDN Controller?

An SDN controller acts as the centralized brain of a software-defined network. It communicates with network switches via southbound APIs (primarily OpenFlow, but also NETCONF, OVSDB, and P4Runtime) and exposes northbound REST APIs for application development.

Key responsibilities include:

- **Topology discovery** — LLDP-based automatic discovery of switch and link relationships
- **Flow rule management** — Installing, modifying, and removing OpenFlow entries across switches
- **Path computation** — Calculating optimal paths for traffic flows based on policy
- **Network virtualization** — Creating logical networks overlaying physical infrastructure
- **Event handling** — Processing switch connections, port status changes, and packet-in events

## ONOS (Open Network Operating System)

**GitHub:** [opennetworkinglab/onos](https://github.com/opennetworkinglab/onos) · **Stars:** 1,277 · **License:** Apache 2.0

ONOS is a carrier-grade SDN controller designed for service provider and enterprise networks. Originally developed by ON.Lab (now part of the Linux Foundation's Open Networking Foundation), it emphasizes high availability, scalability, and performance.

### Architecture

ONOS uses a distributed cluster architecture where multiple controller instances form a single logical entity. The distributed core uses Atomix for consistent state replication:

```yaml
# ONOS cluster configuration (atomix.conf)
cluster:
  nodes:
    - id: node1
      address: 10.0.0.1:5679
    - id: node2
      address: 10.0.0.2:5679
    - id: node3
      address: 10.0.0.3:5679
  storage:
    level: DISK
    path: /var/lib/onos/storage
```

### Key Features

- Distributed cluster with automatic failover
- OpenFlow 1.0-1.5, NETCONF, OVSDB, P4Runtime southbound support
- REST and gRPC northbound APIs
- Built-in GUI for topology visualization
- Intent framework for declarative network policies
- Segment routing and MPLS support
- CORD (Central Office Re-architected as a Datacenter) integration

### Docker Deployment

```yaml
# docker-compose.yml for ONOS
version: '3'
services:
  onos:
    image: onosproject/onos:2.7.0
    ports:
      - "8181:8181"   # Web GUI
      - "6653:6653"   # OpenFlow
      - "8101:8101"   # Karaf CLI
    environment:
      - ONOS_APPS=drivers,openflow,proxyarp,lldpprovider
    volumes:
      - onos-data:/root/.onos
    networks:
      - sdn-net

volumes:
  onos-data:

networks:
  sdn-net:
    driver: bridge
```

## OpenDaylight (ODL)

**GitHub:** [opendaylight/controller](https://github.com/opendaylight/controller) · **Stars:** 477 · **License:** Eclipse Public License

OpenDaylight is the most widely adopted open-source SDN controller platform, backed by the Linux Foundation. It uses an OSGi-based modular architecture and supports a broad ecosystem of southbound protocols and northbound applications.

### Architecture

ODL's architecture centers on the Model-Driven Service Abstraction Layer (MD-SAL), which provides a unified data store for network state and a message bus for inter-component communication:

```
┌─────────────────────────────────────┐
│         Northbound APIs             │
│   RESTCONF | NETCONF | gNMI         │
├─────────────────────────────────────┤
│         MD-SAL (Data Store)         │
│    YANG-modeled configuration       │
├─────────────────────────────────────┤
│        Southbound Plugins           │
│  OpenFlow | NETCONF | OVSDB | BGP-LS│
└─────────────────────────────────────┘
```

### Key Features

- MD-SAL with YANG-modeled data models
- OpenFlow 1.0-1.5, NETCONF, OVSDB, BGP-LS, PCEP southbound
- RESTCONF northbound API
- Clustering via Akka distributed data
- Service Function Chaining (SFC)
- Virtual Tenant Network (VTN)
- Integration with OpenStack, Kubernetes (Contiv)

### Docker Deployment

```yaml
# docker-compose.yml for OpenDaylight
version: '3'
services:
  odl:
    image: opendaylight/base:2.0.2
    ports:
      - "8181:8181"   # RESTCONF
      - "6653:6653"   # OpenFlow
      - "830:830"     # NETCONF
      - "2550:2550"   # Akka clustering
      - "4334:4334"   # Karaf SSH
    environment:
      - JAVA_MAX_MEM=4096M
    volumes:
      - odl-data:/opt/opendaylight/data
    networks:
      - sdn-net

volumes:
  odl-data:

networks:
  sdn-net:
    driver: bridge
```

## Floodlight

**GitHub:** [floodlight/floodlight](https://github.com/floodlight/floodlight) · **Stars:** 773 · **License:** Apache 2.0 / BSD

Floodlight is a Java-based SDN controller originally developed by Big Switch Networks. It provides a lightweight, modular controller with a focus on simplicity and ease of use, making it popular for research, education, and small-scale deployments.

### Architecture

Floodlight uses a simple modular architecture with a core module managing the OpenFlow switch connections and pluggable modules for specific functionality:

```
┌───────────────────────────┐
│    Floodlight Modules     │
│  Routing | Firewall | LB  │
├───────────────────────────┤
│      Controller Core      │
│   OpenFlow Provider       │
├───────────────────────────┤
│     Switch Connections    │
│     (OpenFlow 1.0-1.3)    │
└───────────────────────────┘
```

### Key Features

- Modular plugin architecture
- OpenFlow 1.0-1.3 support
- REST API for management and monitoring
- Built-in web UI (Floodlight Web UI)
- Static flow pusher for simple rule installation
- Link discovery via LLDP
- Virtual network forwarding (VNF)

### Docker Deployment

```yaml
# docker-compose.yml for Floodlight
version: '3'
services:
  floodlight:
    image: henrygeorge/floodlight:latest
    ports:
      - "6653:6653"   # OpenFlow
      - "8080:8080"   # REST API
      - "8081:8081"   # Web UI
    volumes:
      - ./floodlight.properties:/var/lib/floodlight/floodlightdefault.properties:ro
      - fl-data:/var/lib/floodlight
    networks:
      - sdn-net

volumes:
  fl-data:

networks:
  sdn-net:
    driver: bridge
```

## Comparison Table

| Feature | ONOS | OpenDaylight | Floodlight |
|---------|------|--------------|------------|
| **Architecture** | Distributed cluster | OSGi modular + MD-SAL | Modular monolith |
| **Primary Use Case** | Carrier/SP networks | Enterprise, multi-vendor | Research, education |
| **OpenFlow Support** | 1.0-1.5 | 1.0-1.5 | 1.0-1.3 |
| **Other Southbound** | NETCONF, OVSDB, P4Runtime | NETCONF, OVSDB, BGP-LS, PCEP | None (OpenFlow only) |
| **Northbound API** | REST, gRPC | RESTCONF, REST, gNMI | REST |
| **Clustering** | Built-in (Atomix) | Built-in (Akka) | None |
| **YANG Support** | Partial | Full (MD-SAL) | None |
| **GUI** | Built-in topology viewer | DLUX web UI | Floodlight Web UI |
| **Language** | Java | Java | Java |
| **Last Major Release** | 2.7 (2023) | 2.0.2 (2024) | 1.14 (2020) |
| **GitHub Stars** | 1,277 | 477 | 773 |
| **Docker Image** | Official | Official | Community |
| **Min. RAM** | 4 GB | 4 GB | 2 GB |
| **High Availability** | Yes (active-active) | Yes (active-active) | No |

## Choosing the Right SDN Controller

### Choose ONOS if:
- You need carrier-grade reliability and horizontal scalability
- Your deployment requires distributed controller clustering
- You need advanced features like segment routing or CORD integration
- You're building a service provider or large enterprise network

### Choose OpenDaylight if:
- You need the broadest southbound protocol support (BGP-LS, PCEP, NETCONF)
- You want YANG-modeled data management via MD-SAL
- You need integration with OpenStack or Kubernetes
- You want the largest community and vendor support ecosystem

### Choose Floodlight if:
- You're learning SDN concepts in a lab or classroom setting
- You need a lightweight controller for small deployments
- You want a simple, easy-to-understand codebase
- You primarily need OpenFlow 1.3 support without advanced protocols

## Why Self-Host Your SDN Controller?

Running your own SDN controller infrastructure gives you complete control over network programmability and automation. Unlike commercial SDN solutions from VMware, Cisco (ACI), or Juniper (Contrail), open-source controllers have no per-switch licensing fees, no vendor lock-in, and full access to the source code for customization.

For organizations managing multi-vendor switch environments, self-hosted SDN controllers provide a unified control plane that works across hardware from different manufacturers. The controller abstracts away vendor-specific implementation details, exposing consistent APIs for network automation and orchestration.

For network teams already running OpenStack or Kubernetes, integrating an open-source SDN controller enables consistent network policy enforcement across virtual machines, containers, and bare-metal workloads. The northbound APIs allow custom automation scripts and CI/CD pipelines to programmatically manage network policies alongside compute resources.

For related reading on network automation, see our [network configuration management guide](../2026-05-05-self-hosted-network-configuration-management-ansible-nornir-netbox-guide/) and [self-hosted network topology discovery tools](../2026-04-26-self-hosted-network-topology-discovery-tools-guide/). For SDN overlay networking, our [VXLAN tunneling comparison](../2026-05-23-self-hosted-vxlan-tunneling-openvswitch-vs-frrouting-vs-ovn/) covers complementary technologies.

## FAQ

### What is the difference between ONOS and OpenDaylight?

ONOS is designed primarily for carrier/service provider networks with a focus on high availability and distributed clustering. OpenDaylight is more enterprise-focused and supports a broader range of southbound protocols (BGP-LS, PCEP, NETCONF) through its MD-SAL architecture. ONOS uses Atomix for clustering while OpenDaylight uses Akka.

### Can Floodlight be used in production?

Floodlight is best suited for research, education, and small-scale lab deployments. Its last major release was in 2020, and it lacks features like controller clustering and advanced southbound protocols (NETCONF, BGP-LS) that production networks typically require. For production use, ONOS or OpenDaylight are more appropriate.

### Do SDN controllers replace traditional routers and switches?

No. SDN controllers manage the forwarding behavior of existing switches via protocols like OpenFlow. The physical switches remain in place but are reconfigured to receive flow rules from the controller instead of computing routes locally. Some SDN deployments use white-box switches running SONiC or DENT for a fully open networking stack.

### What is the MD-SAL in OpenDaylight?

The Model-Driven Service Abstraction Layer (MD-SAL) is OpenDaylight's core architecture. It uses YANG data models to define a unified data store that all modules read from and write to. This allows any module to access any other module's data through a consistent API, enabling loose coupling between components.

### Can I run multiple SDN controllers in the same network?

Yes, but with caveats. Running multiple controllers requires careful partitioning of switch ownership (each switch connects to exactly one controller) or using a hierarchical controller model. OpenDaylight supports hierarchical controllers through BGP-LS for inter-controller communication. ONOS supports cluster mode where multiple instances manage a single logical network.

### How much RAM does an SDN controller need?

Minimum requirements: ONOS and OpenDaylight both need 4 GB RAM for a single-node deployment. Floodlight can run with 2 GB. For production clusters with 100+ managed switches, plan for 8-16 GB per controller node. OpenFlow flow table capacity on switches is typically the bottleneck, not controller resources.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SDN Controllers: ONOS vs OpenDaylight vs Floodlight (2026)",
  "description": "Compare three open-source SDN controller platforms: ONOS, OpenDaylight, and Floodlight. Learn their architectures, features, Docker deployment, and when to choose each.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
