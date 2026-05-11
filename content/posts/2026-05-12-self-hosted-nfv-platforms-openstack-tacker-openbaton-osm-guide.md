---
title: "Self-Hosted Network Function Virtualization: OpenStack Tacker vs OpenBaton vs OSM Guide 2026"
date: "2026-05-12"
tags: ["nfv", "networking", "orchestration", "openstack", "telecom"]
draft: false
---

Network Function Virtualization (NFV) replaces dedicated network appliances — firewalls, load balancers, WAN optimizers — with software instances running on commodity hardware. An NFV Orchestrator (NFVO) automates the deployment, scaling, and lifecycle management of these virtualized network functions (VNFs), enabling telecom operators and enterprise IT teams to manage network services with the same agility as cloud workloads.

This guide compares three open-source NFV orchestration platforms: OpenStack Tacker, OpenBaton, and ETSI Open Source MANO (OSM), helping you evaluate which platform fits your virtualization requirements.

## What Is NFV Orchestration

NFV orchestration sits above the virtualization infrastructure (typically OpenStack or Kubernetes) and manages the complete lifecycle of network services:

- **Onboarding**: Import VNF descriptors (VNFDs) and network service descriptors (NSDs) that define how virtual network functions connect and communicate
- **Instantiation**: Deploy VNFs on compute nodes, configure virtual networks, and establish connectivity between functions
- **Scaling**: Automatically add or remove VNF instances based on traffic load, using predefined scaling policies
- **Healing**: Detect failed VNF instances and replace them automatically to maintain service availability
- **Termination**: Gracefully shut down network services and release resources when they are no longer needed

The ETSI NFV architecture defines three management layers: NFV Infrastructure (NFVI), VNF Managers (VNM), and the NFV Orchestrator (NFVO). The platforms compared here each implement this architecture with different design philosophies.

## OpenStack Tacker

Tacker is the official NFV Orchestrator for OpenStack, maintained as part of the OpenStack project. It implements the ETSI NFV MANO specification and integrates natively with OpenStack's compute, networking, and storage services.

### Architecture

Tacker operates as a set of OpenStack services that communicate through the OpenStack message bus. It uses Heat (OpenStack's orchestration engine) as its VNF Manager, translating NFV descriptors into Heat templates that OpenStack can execute.

### Docker Compose Deployment (All-in-One Lab)

```yaml
version: "3.8"
services:
  tacker-server:
    image: xosproject/tacker:latest
    container_name: tacker-server
    ports:
      - "9890:9890"
    environment:
      - OS_AUTH_URL=http://keystone:5000/v3
      - OS_USERNAME=admin
      - OS_PASSWORD=admin
      - OS_PROJECT_NAME=admin
      - DATABASE_CONNECTION=mysql+pymysql://tacker:tacker@mysql/tacker
    depends_on:
      - mysql
      - rabbitmq
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: tacker-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=tacker
      - MYSQL_USER=tacker
      - MYSQL_PASSWORD=tacker
    volumes:
      - mysql-data:/var/lib/mysql
    restart: unless-stopped

  rabbitmq:
    image: rabbitmq:3-management
    container_name: tacker-rabbitmq
    ports:
      - "15672:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=tacker
      - RABBITMQ_DEFAULT_PASS=tacker
    restart: unless-stopped

volumes:
  mysql-data:
```

### Key Features

- **ETSI NFV MANO compliance**: Implements the standard NFV orchestration interfaces defined by ETSI
- **OpenStack integration**: Native integration with Nova, Neutron, and Cinder for resource management
- **TOSCA-based descriptors**: Uses OASIS TOSCA (Topology and Orchestration Specification for Cloud Applications) for VNF and NS definitions
- **VNF lifecycle management**: Supports instantiation, scaling, healing, and termination of virtual network functions
- **OpenStack CLI integration**: Manage NFV resources through the standard OpenStack client

### VNF Descriptor Example

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
description: Simple VNF example

topology_template:
  node_templates:
    VDU1:
      type: tosca.nodes.nfv.VDU.Tacker
      properties:
        image: cirros
        flavor: m1.small
        mgmt_driver: noop
      requirements:
        - virtualLink:
            node: CP1
        - virtualLink:
            node: CP2

    CP1:
      type: tosca.nodes.nfv.CP.Tacker
      properties:
        management: true
      requirements:
        - virtualLink:
            node: VL1

    CP2:
      type: tosca.nodes.nfv.CP.Tacker
      requirements:
        - virtualLink:
            node: VL2

    VL1:
      type: tosca.nodes.nfv.VL

    VL2:
      type: tosca.nodes.nfv.VL
```

## OpenBaton

OpenBaton is an open-source NFV Orchestrator developed as part of the EU FP7 open source MANO project. It provides a complete NFV MANO stack with a focus on extensibility and plugin-based architecture.

### Architecture

OpenBaton separates the NFV Orchestrator (NFVO) from the VNF Manager (VNFM) and Virtualized Infrastructure Manager (VIM), communicating through a standardized messaging interface. This design allows operators to mix and match components from different vendors.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  openbaton-nfvo:
    image: openbaton/nfvo:5.1.0
    container_name: openbaton-nfvo
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATA_MONGODB_HOST=mongodb
      - SPRING_DATA_MONGODB_PORT=27017
      - SPRING_DATA_MONGODB_DATABASE=openbaton
      - SPRING_RABBITMQ_HOST=rabbitmq
    depends_on:
      - mongodb
      - rabbitmq
    restart: unless-stopped

  openbaton-generic-vnfm:
    image: openbaton/generic-vnfm:5.0.0
    container_name: openbaton-generic-vnfm
    environment:
      - SPRING_DATA_MONGODB_HOST=mongodb
      - SPRING_RABBITMQ_HOST=rabbitmq
    depends_on:
      - mongodb
      - rabbitmq
    restart: unless-stopped

  mongodb:
    image: mongo:6.0
    container_name: openbaton-mongo
    volumes:
      - mongo-data:/data/db
    restart: unless-stopped

  rabbitmq:
    image: rabbitmq:3-management
    container_name: openbaton-rabbitmq
    ports:
      - "15672:15672"
    restart: unless-stopped

volumes:
  mongo-data:
```

### Key Features

- **Plugin-based architecture**: Extensible VNFM and VIM plugins support multiple infrastructure providers
- **Web dashboard**: Built-in web UI for monitoring and managing NFV deployments
- **Auto-scaling policies**: Define scaling rules based on monitoring metrics
- **Fault management**: Automatic detection and recovery from VNF failures
- **Multi-VIM support**: Orchestrate resources across multiple OpenStack, Kubernetes, or VMware environments

### NSD (Network Service Descriptor) Example

```json
{
  "name": "Simple Network Service",
  "vendor": "example.com",
  "version": "1.0",
  "vnfd-id": ["vdu-vnfd-id-001"],
  "vld": [
    {
      "name": "internal-network",
      "vim-network-name": "internal-vlan",
      "vnffmgd": false
    }
  ]
}
```

## ETSI Open Source MANO (OSM)

OSM is the reference implementation of the ETSI NFV MANO architecture, developed and maintained by ETSI itself. It provides the most complete implementation of the ETSI NFV specifications among open-source platforms.

### Architecture

OSM implements all three ETSI MANO components — NFVO, VIM, and VNF Manager — in a modular architecture. It uses Juju for VNF configuration management and supports both charmed VNFs and traditional VNF descriptors.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  osm:
    image: opensourcemano/osm:latest
    container_name: osm
    ports:
      - "9999:9999"
      - "443:443"
    volumes:
      - osm-data:/app/storage
    environment:
      - OSM_HOSTNAME=osm.local
    restart: unless-stopped
    privileged: true

volumes:
  osm-data:
```

Note: OSM is typically deployed on bare metal or via the OSM installer script. The Docker approach above is suitable for evaluation and lab environments only.

### Key Features

- **ETSI reference implementation**: Closest open-source implementation to the official ETSI NFV MANO specification
- **Juju integration**: Uses Canonical's Juju for VNF lifecycle management and configuration
- **Charmed VNFs**: Support for Juju charms as a VNF packaging format
- **Multi-VIM orchestration**: Manage resources across OpenStack, VMware vCenter, and AWS
- **NSD/VNFD validation**: Built-in descriptor validation against ETSI schemas
- **RBAC and tenancy**: Role-based access control with multi-tenant support

### Deploying a Network Service

```bash
# Upload a VNF package
osm vnfd-create my-vnf.tar.gz

# Upload a network service descriptor
osm nsd-create my-ns.tar.gz

# Instantiate the network service
osm ns-create --nsd_name my-ns --ns_name my-instance   --vim_account openstack-vim

# Monitor the deployment
osm ns-list
osm ns-show my-instance
```

## Comparison Table

| Feature | OpenStack Tacker | OpenBaton | ETSI OSM |
|---------|-----------------|-----------|----------|
| ETSI MANO compliance | Full | Partial | Reference |
| Primary integration | OpenStack | Multi-VIM | Multi-VIM |
| Descriptor format | TOSCA | Custom JSON/YAML | ETSI YAML/JSON |
| VNF Manager | OpenStack Heat | Generic VNFM (plugin) | Juju |
| Web dashboard | Horizon plugin | Built-in | Built-in |
| Multi-VIM support | Limited | Yes | Yes |
| Auto-scaling | Yes (via Heat) | Yes | Yes |
| VNF configuration | Cloud-init | Generic VNFM | Juju charms |
| Community backing | OpenStack Foundation | EU FP7 project | ETSI |
| GitHub stars | 139 | 63 (NFVO) | ETSI-hosted |
| Latest activity | Active | Moderate | Active |
| Learning curve | Moderate (OpenStack knowledge) | Moderate | High |

## Choosing the Right NFV Platform

For **OpenStack-centric deployments**, Tacker is the natural choice. Its native integration with OpenStack services means you can manage NFV resources through familiar OpenStack tools and APIs. If your infrastructure team already operates OpenStack, Tacker adds NFV capabilities without introducing a separate management stack.

For **multi-vendor environments**, OpenBaton's plugin architecture provides the most flexibility. You can integrate VNF Managers and Virtualized Infrastructure Managers from different vendors, making it suitable for environments with heterogeneous infrastructure or legacy VNFs that require specific management interfaces.

For **ETSI compliance and telecom-grade deployments**, OSM provides the most complete implementation of the ETSI NFV MANO specification. Telecom operators and service providers who need strict compliance with ETSI standards, including descriptor validation, multi-tenancy, and RBAC, should evaluate OSM first.

## FAQ

### What is the difference between NFV and SDN?

NFV (Network Function Virtualization) replaces dedicated network appliances with software running on commodity hardware. SDN (Software-Defined Networking) separates the network control plane from the data plane, enabling centralized network management. They are complementary technologies — NFV virtualizes the functions, while SDN manages the network connectivity between them.

### Can I run NFV on Kubernetes instead of OpenStack?

Yes. Modern NFV deployments increasingly use Kubernetes as the NFV Infrastructure (NFVI) layer. OSM supports Kubernetes as a VIM, and Tacker has experimental Kubernetes integration. Container-based VNFs (CNFs) are managed differently from VM-based VNFs but follow the same orchestration principles.

### Is NFV suitable for small enterprise deployments?

NFV is most valuable when you manage many network services across distributed locations. For a single-site deployment with a handful of virtual appliances, a standard virtualization platform (Proxmox, VMware) may be simpler. NFV shines when you need automated lifecycle management, scaling, and service chaining across multiple sites.

### How do VNFs differ from containers?

VNFs are typically virtual machine-based implementations of network functions, while CNFs (Containerized Network Functions) use containers. VNFs provide stronger isolation and are better suited for high-throughput network processing. CNFs offer faster startup times and easier scaling. Modern NFV platforms support both paradigms.

### What hardware do I need for an NFV lab?

A minimum lab setup requires: a server with 32GB+ RAM and a multi-core CPU for the orchestration platform, network switches for management and data plane separation, and sufficient storage for VNF images. For production deployments, SR-IOV-capable NICs and DPDK support are recommended for high-throughput VNFs.

### Can Tacker manage VNFs on non-OpenStack infrastructure?

Tacker is designed for OpenStack integration and does not natively support other VIMs. However, the OpenStack ecosystem includes drivers for VMware vCenter, AWS, and Azure, which Tacker can leverage through OpenStack's abstraction layer.

### How does OSM handle VNF configuration?

OSM uses Juju charms for VNF configuration management. A charm is a package that defines how to deploy, configure, and manage a specific VNF. When OSM instantiates a network service, Juju applies the appropriate charms to each VNF, handling initial configuration, scaling events, and day-2 operations.

## Why Self-Host Your NFV Infrastructure?

Running your own NFV orchestration platform eliminates dependency on proprietary telecom management systems and their associated licensing costs. When you self-host NFV infrastructure, you maintain complete control over service chaining policies, VNF placement decisions, and scaling thresholds — critical parameters that directly impact network performance and reliability.

For organizations already operating self-hosted infrastructure, NFV orchestration complements existing [container orchestration platforms](../2026-05-10-self-hosted-kubernetes-cni-antrea-kube-ovn-spiderpool-guide/) by extending infrastructure-as-code principles to network services. Combined with [network configuration management tools](../2026-04-29-opendaylight-vs-faucet-vs-ryu-self-hosted-sdn-controller-guide/) for the underlying physical network, self-hosted NFV creates a unified automation layer across both physical and virtual infrastructure.

For teams managing complex network topologies, NFV orchestration also integrates with [network simulation environments](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) for pre-deployment testing, enabling you to validate network service designs before deploying them to production infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Function Virtualization: OpenStack Tacker vs OpenBaton vs OSM Guide 2026",
  "description": "Compare three open-source NFV orchestration platforms — OpenStack Tacker, OpenBaton, and ETSI OSM — with Docker deployments, descriptor examples, and decision guidance.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
