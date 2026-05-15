---
title: "Self-Hosted DHCP Load Balancer — Kea Split-Horizon vs HAProxy DHCP vs ISC DHCP Split-Scope"
date: "2026-05-15"
tags: ["dhcp", "load-balancing", "network-infrastructure", "kea", "isc-dhcp"]
draft: false
---

When managing DHCP across large networks with thousands of clients, a single DHCP server becomes a bottleneck. Load balancing DHCP requests across multiple servers improves reliability, reduces latency, and distributes the processing burden. Unlike DHCP high-availability failover (which keeps one server in standby), **DHCP load balancing** actively distributes requests across all participating servers.

In this guide, we compare three approaches to self-hosted DHCP load balancing: ISC DHCP split-scope, Kea DHCP load balancing with lease synchronization, and HAProxy-based DHCP request distribution.

## How DHCP Load Balancing Works

DHCP is built on UDP broadcast, which makes traditional layer-4 load balancing challenging. There are three primary strategies for distributing DHCP load:

1. **Split-scope**: Each server is configured with a different IP address range. Both servers respond to requests, but the scope of addresses they hand out does not overlap. This is the simplest approach but requires careful capacity planning.

2. **Load-balancing with lease synchronization**: Both servers share the same IP pool and synchronize lease databases in real-time. Kea DHCP supports this through its HA hook library with a `load-balancing` HA mode.

3. **Proxy-based distribution**: A proxy server intercepts DHCP requests and forwards them to backend servers based on a distribution algorithm. This is less common but provides the most flexibility for complex topologies.

## ISC DHCP Split-Scope Configuration

ISC DHCP does not have a built-in load balancing protocol. The standard approach is split-scope configuration, where each server handles a different percentage of the available address pool.

### Server 1 Configuration (70% of scope)

```
# /etc/dhcp/dhcpd.conf - Primary Server (70%)
subnet 192.168.1.0 netmask 255.255.255.0 {
    range 192.168.1.10 192.168.1.175;  # 166 addresses (70%)
    option domain-name-servers 8.8.8.8, 8.8.4.4;
    option routers 192.168.1.1;
    default-lease-time 3600;
    max-lease-time 7200;
}
```

### Server 2 Configuration (30% of scope)

```
# /etc/dhcp/dhcpd.conf - Secondary Server (30%)
subnet 192.168.1.0 netmask 255.255.255.0 {
    range 192.168.1.176 192.168.1.250;  # 75 addresses (30%)
    option domain-name-servers 8.8.8.8, 8.8.4.4;
    option routers 192.168.1.1;
    default-lease-time 3600;
    max-lease-time 7200;
}
```

The split ratio should match the expected server capacity. If both servers have equal hardware, a 50/50 split is ideal. If one server is more powerful, allocate proportionally.

### ISC DHCP Docker Deployment

```yaml
# docker-compose-isc-dhcp-primary.yml
version: "3.8"
services:
  isc-dhcp-primary:
    image: networkboot/dhcpd
    container_name: isc-dhcp-primary
    network_mode: host
    volumes:
      - ./dhcpd-primary.conf:/etc/dhcp/dhcpd.conf
      - dhcp-leases-primary:/var/lib/dhcp
    environment:
      - DHCPD_RANGE=192.168.1.10 192.168.1.175
      - DHCPD_DNS=8.8.8.8 8.8.4.4
      - DHCPD_ROUTER=192.168.1.1
    restart: unless-stopped

volumes:
  dhcp-leases-primary:
```

## Kea DHCP Load Balancing with HA Hook

Kea DHCP (by ISC) has native load balancing support through the HA (High Availability) hook library. Unlike ISC DHCP, Kea can actively distribute requests across multiple servers with synchronized lease databases.

### Kea Server 1 Configuration

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "memfile",
      "persist": true,
      "name": "/var/lib/kea/dhcp4.leases"
    },
    "hooks-libraries": [
      {
        "library": "/usr/lib/kea/hooks/libdhcp_lease_cmds.so"
      },
      {
        "library": "/usr/lib/kea/hooks/libdhcp_ha.so",
        "parameters": {
          "high-availability": [
            {
              "this-server-name": "kea-primary",
              "mode": "load-balancing",
              "heartbeat-delay": 10000,
              "max-response-delay": 10000,
              "max-ack-delay": 5000,
              "max-unacked-clients": 0,
              "peers": [
                {
                  "name": "kea-primary",
                  "url": "http://192.168.1.10:8080/",
                  "role": "primary"
                },
                {
                  "name": "kea-secondary",
                  "url": "http://192.168.1.11:8080/",
                  "role": "secondary"
                }
              ]
            }
          ]
        }
      }
    ],
    "subnet4": [
      {
        "subnet": "192.168.1.0/24",
        "pools": [{"pool": "192.168.1.10 - 192.168.1.250"}]
      }
    ]
  },
  "Control-agent": {
    "sockets": [
      {
        "socket-type": "AF_INET",
        "socket-name": "192.168.1.10",
        "socket-port": 8080
      }
    ]
  }
}
```

### Kea Docker Compose

```yaml
# docker-compose-kea-lb.yml
version: "3.8"
services:
  kea-dhcp:
    image: keaproject/kea:2.4.1
    container_name: kea-dhcp-lb
    network_mode: host
    volumes:
      - ./kea-dhcp4.json:/etc/kea/kea-dhcp4.conf
      - kea-leases:/var/lib/kea
    environment:
      - KEA_CONFIG=/etc/kea/kea-dhcp4.conf
    cap_add:
      - NET_ADMIN
      - NET_RAW
    restart: unless-stopped

volumes:
  kea-leases:
```

The `load-balancing` mode in Kea's HA hook ensures both servers actively respond to DHCP requests. The `max-unacked-clients: 0` setting means there is no limit on unacknowledged clients — both servers handle requests simultaneously. Lease synchronization happens through the REST API control channel.

## HAProxy DHCP Load Balancing

While HAProxy is primarily known for TCP/HTTP load balancing, it can also handle DHCP through its layer-4 UDP proxy mode. This approach centralizes DHCP request distribution.

### HAProxy Configuration

```
# /etc/haproxy/haproxy.cfg
global
    log /dev/log local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin

defaults
    log     global
    mode    tcp
    option  tcplog
    timeout connect 5000ms
    timeout client  50000ms
    timeout server  50000ms

frontend dhcp-fe
    bind *:67 udp
    mode tcp
    default_backend dhcp-be

backend dhcp-be
    mode tcp
    balance source
    server dhcp1 192.168.1.10:67 check
    server dhcp2 192.168.1.11:67 check
```

### HAProxy Docker Compose

```yaml
# docker-compose-haproxy-dhcp.yml
version: "3.8"
services:
  haproxy:
    image: haproxy:2.9-alpine
    container_name: haproxy-dhcp
    network_mode: host
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    restart: unless-stopped
```

Note: DHCP load balancing via HAProxy requires careful network configuration since DHCP uses broadcast. The `balance source` algorithm ensures requests from the same client MAC always reach the same backend server, preventing duplicate IP assignments.

## Comparison: DHCP Load Balancing Approaches

| Feature | ISC DHCP Split-Scope | Kea DHCP HA Load Balancing | HAProxy DHCP Proxy |
|---------|---------------------|---------------------------|-------------------|
| **Active Distribution** | No (static ranges) | Yes (shared pool) | Yes (proxy-based) |
| **Lease Synchronization** | Manual | Automatic (REST API) | None (proxy only) |
| **Failover Support** | Yes (both servers active) | Yes (built-in) | Limited |
| **Setup Complexity** | Low | Medium | High |
| **Scalability** | Limited (2 servers) | Up to 2 servers | Multiple backends |
| **IP Pool Utilization** | Inefficient (split) | Optimal (shared) | Depends on backend |
| **Monitoring** | Log-based | REST API + stats | HAProxy stats page |
| **Docker Support** | Community images | Official images | Official images |
| **Configuration Format** | Text config | JSON | Text config |
| **Active Development** | Archived (EOL) | Active (ISC) | Active |

## Choosing the Right DHCP Load Balancing Strategy

**For small to medium networks** with fewer than 500 clients, ISC DHCP split-scope is the simplest approach. The static range allocation requires no synchronization mechanism, and both servers operate independently. The downside is that if one server goes down, its address range becomes unavailable, reducing total capacity.

**For enterprise networks** with thousands of clients, Kea DHCP with HA load balancing is the recommended choice. The shared IP pool ensures maximum utilization, and automatic lease synchronization prevents duplicate assignments. The REST API control channel enables integration with monitoring and automation tools.

**For complex multi-site topologies** where centralized control is needed, HAProxy-based DHCP distribution provides the most flexibility. However, this approach requires careful network design to handle DHCP broadcast semantics properly.

## Why Self-Host DHCP Load Balancing?

Managing DHCP at scale requires distributing the request-handling load across multiple servers. Self-hosted DHCP load balancing offers several advantages over cloud-managed or single-server approaches:

**Performance under load.** A single DHCP server handling thousands of concurrent lease requests can experience latency spikes, especially during network outages when many clients simultaneously request new leases. Load balancing distributes these bursts across multiple servers, maintaining consistent response times.

**No vendor lock-in.** Cloud DHCP services (like AWS VPC DHCP or Azure DHCP) tie your network configuration to a specific provider. Self-hosted solutions keep you in control of lease policies, option configurations, and network topology.

**Cost efficiency at scale.** Cloud DHCP services charge per-request or per-VPC. For large organizations with multiple subnets and thousands of clients, self-hosted load balancing is significantly cheaper over time.

**Compliance and auditability.** Self-hosted DHCP keeps all lease data within your infrastructure. This is critical for organizations with regulatory requirements around network access logging and IP address assignment tracking.

For related reading on DHCP infrastructure, see our [DHCP high availability guide](../2026-05-09-self-hosted-dhcp-high-availability-kea-ha-vs-isc-dhcp-vs-keepalived-guide/), [DHCP monitoring setup](../2026-05-10-self-hosted-dhcp-monitoring-kea-dashboard-exporter-guide/), and [DHCP option management](../2026-05-13-self-hosted-dhcp-option-management-kea-isc-dnsmasq-guide/).

## FAQ

### What is DHCP load balancing vs DHCP failover?

DHCP load balancing distributes active client requests across multiple servers simultaneously, with all servers processing requests. DHCP failover keeps one server active and one in standby, only activating the secondary when the primary fails. Load balancing improves performance; failover improves reliability.

### Can Kea DHCP handle more than 2 load balancing peers?

Kea's HA hook currently supports a maximum of 2 peers in load-balancing mode. For larger deployments, you need multiple independent HA pairs, each handling a different subnet or using DHCP relay agents to direct traffic to specific pairs.

### How does ISC DHCP split-scope handle server failures?

When one server in a split-scope configuration fails, clients that would normally receive addresses from that server's range cannot get new leases. The surviving server continues serving its own range. This is why split-scope is less resilient than Kea's shared-pool approach.

### Is HAProxy suitable for production DHCP load balancing?

HAProxy can proxy DHCP requests, but it is not purpose-built for DHCP. The main limitation is that DHCP uses UDP broadcasts, and HAProxy's layer-4 UDP proxy mode does not handle broadcast semantics natively. For production DHCP, Kea's native load balancing is recommended.

### How do I monitor DHCP load balancer health?

For Kea, use the REST API control channel (`curl http://<server>:8080/`) with the `statistic-get-all` command. For ISC DHCP, parse lease files and syslog output. For HAProxy, the built-in stats page (`http://<haproxy>:8404/stats`) shows backend connection counts and health status.

### Can I mix different DHCP servers in a load balancing configuration?

No. Lease synchronization requires servers to use the same database format and protocol. Kea servers must pair with Kea servers, and ISC DHCP with ISC DHCP. Mixing vendors in a load balancing setup will result in duplicate IP assignments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Load Balancer — Kea Split-Horizon vs HAProxy DHCP vs ISC DHCP Split-Scope",
  "description": "Compare DHCP load balancing approaches: Kea HA load balancing, ISC DHCP split-scope, and HAProxy DHCP proxy. Includes Docker Compose configs, comparison tables, and deployment guides.",
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
