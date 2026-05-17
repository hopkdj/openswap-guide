---
title: "Self-Hosted VRF Management Platforms — FRRouting vs Linux VRF vs Netavark (2026)"
date: "2026-05-18"
tags: ["vrf", "networking", "routing", "linux", "frrouting", "self-hosted", "container-networking", "netavark"]
draft: false
---

Virtual Routing and Forwarding (VRF) enables multiple independent routing tables to coexist on a single Linux system, effectively creating isolated network namespaces for different tenants, services, or applications. VRF is the Linux equivalent of Cisco's VRF-lite, allowing a single server to act as multiple virtual routers.

In this guide, we compare three approaches to self-hosted VRF management: **FRRouting (VRF-aware routing)**, **Linux VRF (kernel-native)**, and **Netavark (container-focused VRF)** — covering architecture, configuration, Docker deployment, and production use cases.

## What Is VRF and Why Does It Matter?

VRF (Virtual Routing and Forwarding) creates isolated routing domains on a single system. Each VRF has its own routing table, ARP cache, and network interfaces. Traffic in one VRF cannot reach another VRF without explicit policy-based routing or a gateway.

Key use cases for VRF:

- **Multi-tenant isolation**: Separate routing for different customers on shared infrastructure
- **Service separation**: Isolate management, production, and backup traffic
- **Container networking**: Per-container or per-pod routing tables
- **Testing environments**: Run conflicting network configurations on the same host
- **Network function virtualization**: Deploy multiple virtual routers on commodity hardware

Without VRF, you need separate physical machines or full network namespaces for routing isolation. VRF provides isolation at the routing layer while sharing the same kernel, reducing resource overhead.

## Comparison: FRRouting vs Linux VRF vs Netavark

| Feature | FRRouting VRF | Linux Kernel VRF | Netavark VRF |
|---------|--------------|-----------------|-------------|
| **Type** | Routing daemon VRF | Kernel-level VRF device | Container network VRF |
| **Isolation Level** | Routing table + protocol | Full routing + interface | Container network namespace |
| **BGP per VRF** | Yes (native) | Via FRR/iproute2 | Via container runtime |
| **OSPF per VRF** | Yes (native) | Via FRR/iproute2 | No |
| **Interface Binding** | Yes | Yes (vrf device) | Via CNI |
| **Policy-Based Routing** | Via zebra | Via iproute2 rules | Via iptables/nftables |
| **Management Tool** | vtysh | iproute2 (ip vrf) | netavark CLI |
| **Docker Integration** | Via host network | Via host network | Native (Podman) |
| **Container Runtime** | Any | Any | Podman (native) |
| **VLAN Integration** | Yes | Yes | Via CNI plugins |
| **VXLAN Integration** | Yes | Yes | Via CNI plugins |
| **Performance** | Kernel-speed | Kernel-speed | Kernel-speed |
| **GitHub Stars (OVS)** | FRR: 4,132+ | Linux kernel | Netavark: 680+ |
| **License** | GPL-2.0 | GPL-2.0 | Apache-2.0 |
| **Primary Language** | C | C | Rust |

## FRRouting VRF — Full Protocol Support per VRF

FRRouting provides the most comprehensive VRF implementation among open-source routing daemons. Each VRF gets its own instance of every routing protocol (BGP, OSPF, IS-IS, RIP, PIM), with full configuration isolation.

### Key Features

- **Per-VRF routing protocols**: Independent BGP, OSPF, IS-IS instances per VRF
- **VRF-aware RIB**: Separate Routing Information Base per VRF
- **Route leaking**: Controlled route exchange between VRFs
- **VRF-aware BGP**: Per-VRF BGP sessions, route maps, and policies
- **Integration with kernel VRF**: Uses Linux kernel VRF devices as the underlying mechanism
- **Multi-tenant BGP**: Run separate BGP AS numbers per VRF

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  frr-vrf:
    image: frrouting/frr:v10.2.1
    container_name: frr-vrf
    hostname: frr-vrf
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
      - frr-run:/var/run/frr
      - frr-log:/var/log/frr
    restart: unless-stopped

volumes:
  frr-run:
  frr-log:
```

**frr.conf** (multi-VRF BGP + OSPF):

```
! VRF definitions
vrf red
 vni 100
 exit-vrf
vrf blue
 vni 200
 exit-vrf

! BGP in VRF red
router bgp 65000 vrf red
  neighbor 10.1.0.2 remote-as 65001
  neighbor 10.1.0.2 fall-over bfd
  !
  address-family ipv4 unicast
    neighbor 10.1.0.2 activate
    network 10.1.0.0/24
  exit-address-family
!

! BGP in VRF blue
router bgp 65000 vrf blue
  neighbor 10.2.0.2 remote-as 65002
  !
  address-family ipv4 unicast
    neighbor 10.2.0.2 activate
    network 10.2.0.0/24
  exit-address-family
!

! OSPF in VRF red
router ospf vrf red
  network 10.1.0.0/24 area 0
  passive-interface default
  no passive-interface eth1
!

! Route leaking between VRFs
ip vrf red
  rd 65000:100
  route-target export 65000:100
  route-target import 65000:200
```

**daemons** file:

```
bgpd=yes
bfdd=yes
ospfd=yes
isisd=no
zebra=yes
```

### Native Configuration

```bash
# Create VRF devices
sudo ip vrf add red
sudo ip vrf add blue

# Bind interfaces to VRFs
sudo ip link set eth1 master red
sudo ip link set eth2 master blue

# Bring up VRF devices
sudo ip link set red up
sudo ip link set blue up

# Start FRRouting
sudo systemctl start frr

# Verify VRF routing
vtysh -c "show vrf"
vtysh -c "show ip route vrf red"
vtysh -c "show ip route vrf blue"
vtysh -c "show bgp vrf red summary"
```

## Linux Kernel VRF — Lightweight and Native

The Linux kernel includes native VRF support through the `vrf` device type (available since kernel 4.3). It provides routing table isolation at the kernel level, which can be used with or without a routing daemon.

### Key Features

- **Kernel-native**: No userspace daemon required for basic VRF operation
- **Lightweight**: Minimal resource overhead — just a virtual device
- **iproute2 integration**: Standard `ip vrf` commands for management
- **Policy routing**: Use `ip rule` to direct traffic into specific VRFs
- **Works with any routing daemon**: Compatible with FRR, BIRD, or static routes
- **Socket binding**: Applications can bind sockets to specific VRFs

### Native Configuration

```bash
# Create VRF device
sudo ip vrf add mgmt
sudo ip vrf add production

# Bring up VRF devices
sudo ip link set mgmt up
sudo ip link set production up

# Assign interfaces to VRFs
sudo ip link set eth1 master mgmt
sudo ip link set eth2 master production

# Add IP addresses
sudo ip addr add 10.10.0.1/24 dev eth1
sudo ip addr add 10.20.0.1/24 dev eth2

# Configure default routes per VRF
sudo ip route add default via 10.10.0.254 vrf mgmt
sudo ip route add default via 10.20.0.254 vrf production

# Policy-based routing: send local processes to specific VRF
sudo ip rule add table mgmt oif mgmt
sudo ip rule add table production oif production

# Verify
ip vrf show
ip vrf show mgmt
ip route show vrf mgmt
ip route show vrf production
```

**Persistent configuration** (`/etc/network/interfaces`):

```
auto mgmt
iface mgmt inet manual
  vrf-table auto

auto production
iface production inet manual
  vrf-table auto

auto eth1
iface eth1 inet static
  address 10.10.0.1/24
  vrf mgmt

auto eth2
iface eth2 inet static
  address 10.20.0.1/24
  vrf production
```

### Running Services in a VRF

```bash
# Run a command inside a VRF context
sudo ip vrf exec mgmt ping 10.10.0.254
sudo ip vrf exec mgmt curl http://10.10.0.100:8080

# Run a service bound to a VRF
sudo systemd-run --property=BindToVRF=mgmt /usr/sbin/nginx
```

## Netavark — Container-Focused VRF Management

Netavark is the default network stack for Podman (and an alternative for Docker via plugins). It manages container networking with built-in VRF-like isolation through network namespaces and custom CNI plugins.

### Key Features

- **Podman native**: Default networking backend for Podman 4.0+
- **Rust-based**: Fast, memory-safe implementation
- **Bridge and macvlan drivers**: Multiple network topologies
- **DNS integration**: Built-in DNS resolver for container names
- **Firewall support**: iptables and nftables backends
- **Aardvark DNS**: Companion DNS server for container name resolution

### Docker/Podman Deployment

```yaml
# Using Podman with Netavark networks
version: "3.8"

services:
  app-red:
    image: nginx:alpine
    container_name: app-red
    networks:
      red-net:
        ipv4_address: 10.100.0.10

  app-blue:
    image: nginx:alpine
    container_name: app-blue
    networks:
      blue-net:
        ipv4_address: 10.200.0.10

networks:
  red-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.100.0.0/24
  blue-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.200.0.0/24
```

**Create isolated networks with Netavark**:

```bash
# Create isolated networks (each is its own routing domain)
podman network create --driver bridge red-net
podman network create --driver bridge blue-net

# Run containers on isolated networks
podman run -d --network red-net --name app-red nginx:alpine
podman run -d --network blue-net --name app-blue nginx:alpine

# Verify isolation
podman exec app-red ping 10.200.0.10  # Should fail (no route)
podman exec app-blue ping 10.100.0.10  # Should fail (no route)

# List networks
podman network ls
podman network inspect red-net
```

**Netavark configuration** (`/etc/containers/networks/red-net.json`):

```json
{
  "name": "red-net",
  "id": "abc123",
  "driver": "bridge",
  "network_interface": "podman-red",
  "subnets": [
    {
      "gateway": "10.100.0.1",
      "subnet": "10.100.0.0/24"
    }
  ],
  "ipv6_enabled": false,
  "internal": false,
  "dns_enabled": true,
  "labels": {
    "isolation": "red"
  }
}
```

### Netavark with Custom Routing

```bash
# Install netavark
sudo apt install netavark aardvark-dns

# Create a network with custom routing
netavark setup /etc/containers/networks/custom.json

# Add VRF-like routing rules
ip rule add from 10.100.0.0/24 table red
ip route add default via 10.100.0.254 table red
```

## Choosing the Right VRF Approach

### Choose FRRouting VRF when:

- You need **per-VRF routing protocols** (BGP, OSPF, IS-IS)
- You're building a **multi-tenant routing platform**
- You need **route leaking** between VRFs with policy control
- You want **full BGP per VRF** with independent AS numbers
- You're replacing **physical routers** with a software solution
- You need **VRF-aware BFD** for fast failure detection per VRF

### Choose Linux Kernel VRF when:

- You need **lightweight VRF isolation** without routing daemons
- You want **static routing** per VRF with `ip route vrf`
- You need **application-level VRF binding** (`ip vrf exec`)
- You're building **server multi-homing** with separate management/production VRFs
- You want **minimal resource overhead** (no userspace daemon)
- You need **policy-based routing** with `ip rule`

### Choose Netavark when:

- You're running **containerized workloads** with Podman
- You need **automatic DNS** resolution between containers
- You want **built-in firewall** integration (iptables/nftables)
- You prefer **Rust-based tooling** for reliability
- You need **CNI-compatible** network plugins
- You're deploying **microservices** with isolated networking

## VRF Best Practices

1. **Plan VRF naming carefully**: Use descriptive names (mgmt, production, backup) for maintainability
2. **Document route leaking**: Any route exchange between VRFs should be documented and reviewed
3. **Use VRF-aware monitoring**: Standard tools like `ping` and `traceroute` need `ip vrf exec` prefix
4. **Test failover per VRF**: Each VRF may have different failure characteristics — test independently
5. **Monitor VRF routing tables**: Use `ip route show vrf <name>` or `vtysh -c "show ip route vrf <name>"`
6. **Combine with BFD**: Use BFD (see our BFD guide) for fast failure detection per VRF
7. **Use policy-based routing carefully**: `ip rule` entries are processed in order — misconfigured rules can break connectivity

## Why Self-Host VRF Infrastructure?

VRF technology lets you consolidate multiple virtual routers onto a single physical server, reducing hardware costs while maintaining network isolation. With open-source VRF implementations, you can:

- **Replace expensive hardware routers** with commodity servers running FRR
- **Isolate tenant networks** on shared infrastructure without VM overhead
- **Build multi-tenant cloud platforms** with per-tenant routing
- **Test network configurations** in isolated VRFs before production deployment
- **Run conflicting services** (overlapping IP ranges) on the same host

For **GRE tunneling** between VRF endpoints, see our [GRE tunnel management guide](../2026-05-18-self-hosted-gre-tunnel-management-openvswitch-linux-gre-gretap/). If you need **BFD failure detection** per VRF, check our [BFD protocol daemons article](../2026-05-18-self-hosted-bfd-protocol-daemons-frrouting-bird-gobgp/). For **VXLAN overlay networks** with VRF integration, our [VXLAN tunneling guide](../2026-05-12-self-hosted-vxlan-tunneling-ovs-frr-ovn-guide.) covers the setup.

## FAQ

### What is VRF and how does it differ from network namespaces?

VRF (Virtual Routing and Forwarding) creates isolated routing tables within the same network namespace. Network namespaces create completely isolated network stacks (interfaces, routing, iptables). VRF is lighter weight — interfaces in different VRFs share the same namespace but have separate routing tables. Use VRF for routing isolation; use network namespaces for complete network stack isolation.

### Can I run BGP in multiple VRFs simultaneously?

Yes, FRRouting supports per-VRF BGP instances. Each VRF can have its own BGP process with independent AS numbers, neighbors, and routing policies. Configure with `router bgp <AS> vrf <name>` in FRR. This is commonly used in multi-tenant environments where each tenant needs their own BGP peering.

### How do I run a command inside a VRF context?

Use `ip vrf exec <vrf-name> <command>`. For example: `ip vrf exec mgmt ping 10.0.0.1` or `ip vrf exec production curl http://10.0.0.100`. For systemd services, use `BindToVRF=<name>` in the service unit file.

### What is route leaking between VRFs?

Route leaking is the controlled exchange of routes between VRFs. It allows selective traffic flow between isolated routing domains. In FRRouting, configure route leaking with route-maps and redistribution between VRF instances. In Linux kernel VRF, use policy-based routing (`ip rule`) to forward traffic between VRF tables.

### Does VRF work with Docker containers?

Docker uses network namespaces, not VRFs. Each Docker container gets its own network namespace with separate interfaces and routing. Netavark (Podman's network stack) provides similar isolation with additional features like built-in DNS. For VRF-like isolation in Docker, use macvlan or ipvlan drivers with separate subnets.

### How many VRFs can Linux support?

Linux can support thousands of VRFs. Each VRF is a lightweight virtual device with its own routing table. The practical limit depends on available memory and the routing daemon's capacity. FRRouting routinely supports 100+ VRFs with full BGP/OSPF per VRF on standard server hardware.

### Can I combine VRF with VXLAN?

Yes, VRF and VXLAN are commonly used together. VXLAN provides Layer 2 overlay tunneling, while VRF provides Layer 3 routing isolation. In FRRouting, configure VXLAN interfaces inside VRF contexts for per-tenant overlay networks. This is the standard architecture for multi-tenant cloud platforms.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VRF Management Platforms — FRRouting vs Linux VRF vs Netavark (2026)",
  "description": "Compare VRF management approaches: FRRouting VRF, Linux kernel VRF, and Netavark container networking. Learn configuration, Docker deployment, and best practices.",
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
