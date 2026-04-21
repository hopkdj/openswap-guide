---
title: "Keepalived vs Corosync + Pacemaker: Self-Hosted High Availability Clustering Guide 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "high-availability", "clustering", "load-balancer"]
draft: false
description: "Compare Keepalived and Corosync + Pacemaker for building self-hosted high availability clusters. Learn VRRP failover, resource management, and deployment with Docker Compose."
---

When a single server handles all traffic for a critical service, one hardware failure, kernel panic, or network partition takes your entire application offline. **High availability (HA) clustering** eliminates this single point of failure by running services across multiple nodes that automatically detect failures and redirect traffic to healthy members.

This guide compares the two dominant open-source approaches to Linux HA clustering: **Keepalived** for lightweight VRRP-based failover, and **Corosync + Pacemaker** for full-featured, enterprise-grade cluster resource management. Both are battle-tested in production, run entirely on your own hardware, and cost nothing to deploy.

## Why Self-Host Your High Availability Stack?

Commercial load balancers and managed HA solutions from AWS, GCP, and Azure are expensive and lock you into a single cloud provider. Self-hosted HA clustering gives you:

- **Zero vendor lock-in** — deploy on bare metal, any VPS, or hybrid multi-cloud
- **Sub-second failover** — VRRP heartbeat detects failures in 1-3 seconds, much faster than DNS-based failover
- **No monthly licensing** — Keepalived and Pacemaker are both GPLv2, completely free
- **Full control** — tune timeouts, health checks, and failover policies to your exact needs
- **Works with any service** — reverse proxies, databases, firewalls, application servers

## What Is Keepalived?

[Keepalived](https://github.com/acassen/keepalived) (4,543 stars on GitHub) is a lightweight daemon that implements the **Virtual Router Redundancy Protocol (VRRP)** on Linux. It monitors node health and manages a shared virtual IP address (VIP) that floats between cluster members.

When the active (MASTER) node fails, a standby (BACKUP) node automatically claims the VIP within 1-3 seconds, and traffic seamlessly redirects. Keepalived also supports custom health check scripts so you can fail over based on application-level conditions — not just "is the network cable plugged in."

**Key characteristics:**

- Implements VRRPv2 and VRRPv3 (RFC 5798)
- Manages a single floating virtual IP (or multiple VIPs for multi-service setups)
- Lightweight — ~2MB binary, minimal memory footprint
- Configuration via a single declarative file (`/etc/keepalived/keepalived.conf`)
- Supports weight-based priority for weighted failover decisions
- Built-in support for HTTP, TCP, SMTP, and script-based health checks

Keepalived is ideal when you need **simple active/passive failover** for a single service — typically a reverse proxy or load balancer front-end.

## What Is Corosync + Pacemaker?

[Corosync](https://github.com/corosync/corosync) (1,200 stars) and [Pacemaker](https://github.com/ClusterLabs/pacemaker) (1,150 stars) form a two-component HA stack. Corosync handles cluster messaging (who's alive), and Pacemaker handles resource management (what should run where).

**Corosync** provides:

- Total Order Broadcast for consistent message delivery across all nodes
- Quorum management — prevents split-brain scenarios
- Sub-millisecond heartbeat via Kronosnet or UDP
- Ring protocol for detecting node departures

**Pacemaker** provides:

- Resource management — start, stop, monitor, and migrate services
- Constraint-based placement rules (colocation, ordering, anti-affinity)
- Support for active/passive and active/active configurations
- STONITH (Shoot The Other Node In The Head) for fencing failed nodes
- Rich CLI tools (`crm`, `pcs`) and CIB (Cluster Information Base) XML configuration

This combination is the foundation of Red Hat High Availability, SUSE HA, and many enterprise Linux distributions. It is ideal when you need to manage **multiple resources** (VIP, filesystem, database, application) with com[plex](https://www.plex.tv/) dependencies and placement rules.

## Architecture Comparison

| Feature | Keepalived | Corosync + Pacemaker |
|---|---|---|
| **Protocol** | VRRP (RFC 5798) | Corosync Ring Protocol + Pacemaker CRM |
| **Topology** | Active/Passive (single VIP) | Active/Passive or Active/Active |
| **Resources managed** | Virtual IP + optional health checks | Any resource type (IP, filesystem, database, systemd, containers) |
| **Failover time** | 1-3 seconds | 2-5 seconds |
| **Split-brain protection** | Priority-based (imperfect) | Quorum-based with configurable tiebreakers |
| **Fencing (STONITH)** | Not built-in | Built-in (IPMI, power switches, cloud APIs) |
| **Configuration** | Single declarative file | CIB XML + CLI tools (`pcs`, `crm`) |
| **Learning curve** | Low — 20-line config for basic setup | Medium-High — requires understanding of cluster concepts |
| **Resource dependencies** | None — manages VIP only | Full DAG of start/stop/migrate dependencies |
| **Monitoring** | Syslog + custom scripts |[prometheus](https://prometheus.io/)s, `crm_mon`, Prometheus exporters |
| **Node count** | 2-3 typical | 2+ (odd number recommended for quorum) |
| **Binary size** | ~2MB | ~50MB (combined) |
| **Memory footprint** | ~10MB | ~100-200MB |

## Keepalived: Installation and Configuration

### Install Keepalived

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install keepalived -y

# RHEL/CentOS/Rocky
sudo dnf install keepalived -y

# Verify installation
keepalived --version
# Keepalived v2.3.2 (2024)
```

### Two-Node Active/Passive Setup

Here is a production-ready configuration for two load balancer nodes sharing a floating VIP.

**Node 1 (MASTER) — `/etc/keepalived/keepalived.conf`:**

```conf
global_defs {
    router_id HA_ROUTER_01
    notification_email {
        admin@example.com
    }
    notification_email_from keepalived@example.com
    smtp_server 127.0.0.1
    smtp_connect_timeout 30
}

vrrp_script chk_haproxy {
    script "/usr/bin/killall -0 haproxy"
    interval 2
    weight -20
    fall 3
    rise 2
}

vrrp_instance VI_01 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass S3cureP@ss!
    }

    virtual_ipaddress {
        192.168.1.100/24 dev eth0 label eth0:vip
    }

    track_script {
        chk_haproxy
    }

    notify_master "/etc/keepalived/notify.sh master"
    notify_backup "/etc/keepalived/notify.sh backup"
    notify_fault  "/etc/keepalived/notify.sh fault"
}
```

**Node 2 (BACKUP) — `/etc/keepalived/keepalived.conf`:**

```conf
global_defs {
    router_id HA_ROUTER_02
}

vrrp_script chk_haproxy {
    script "/usr/bin/killall -0 haproxy"
    interval 2
    weight -20
    fall 3
    rise 2
}

vrrp_instance VI_01 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 90
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass S3cureP@ss!
    }

    virtual_ipaddress {
        192.168.1.100/24 dev eth0 label eth0:vip
    }

    track_script {
        chk_haproxy
    }
}
```

### Notify Script

Create `/etc/keepalived/notify.sh` for logging and alerting on state transitions:

```bash
#!/bin/bash
TYPE="$1"
NAME="$2"
STATE="$3"

logger -t keepalived "Transition to $STATE for $NAME"

# Optional: send webhook notification
if [ "$STATE" = "MASTER" ]; then
    curl -s -X POST http://your-monitoring-endpoint/webhook \
        -H "Content-Type: application/json" \
        -d "{\"event\":\"keepalived_master\",\"node\":\"$(hostname)\",\"timestamp\":\"$(date -Is[docker](https://www.docker.com/))\"}"
fi
```

### Docker Compose Deployment

For containerized deployments, Keepalived requires `NET_ADMIN` and `NET_RAW` capabilities:

```yaml
version: "3.8"

services:
  keepalived:
    image: osixia/keepalived:2.0.20
    container_name: keepalived
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - NET_BROADCAST
      - SYS_NICE
    network_mode: "host"
    volumes:
      - ./keepalived.conf:/container/service/keepalived/assets/keepalived.conf:ro
      - ./notify.sh:/container/service/keepalived/assets/notify.sh:ro
    environment:
      - KEEPALIVED_INTERFACE=eth0
      - KEEPALIVED_VIRTUAL_IPS=192.168.1.100
      - KEEPALIVED_UNICAST_PEERS=192.168.1.10,192.168.1.11
    restart: unless-stopped
```

### Verify Keepalived Status

```bash
# Check VRRP state
ip addr show eth0 | grep 192.168.1.100
# inet 192.168.1.100/24 scope global secondary eth0:vip

# Watch VRRP advertisements with tcpdump
sudo tcpdump -i eth0 -n vrrp

# Check keepalived logs
sudo journalctl -u keepalived -f --no-pager

# Test failover by stopping keepalived on master
sudo systemctl stop keepalived
# VIP should move to backup within 2-3 seconds
```

## Corosync + Pacemaker: Installation and Configuration

### Install Corosync and Pacemaker

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install corosync pacemaker pcs -y

# RHEL/CentOS/Rocky
sudo dnf install corosync pacemaker pcs -y

# Start and enable pcsd (Pacemaker configuration daemon)
sudo systemctl enable pcsd
sudo systemctl start pcsd

# Set hacluster password on all nodes (must be identical)
sudo passwd hacluster
```

### Cluster Setup with pcs

**Step 1: Authenticate nodes**

```bash
# Run on one node
sudo pcs host auth node1.example.com node2.example.com node3.example.com \
    -u hacluster -p your-hacluster-password

# Output:
# node1.example.com: Authorized
# node2.example.com: Authorized
# node3.example.com: Authorized
```

**Step 2: Create the cluster**

```bash
sudo pcs cluster setup ha_cluster \
    node1.example.com node2.example.com node3.example.com

# Start the cluster
sudo pcs cluster start --all

# Enable auto-start on boot
sudo pcs cluster enable --all
```

**Step 3: Configure quorum and STONITH**

```bash
# For a 2-node cluster, disable quorum requirement
sudo pcs quorum update two_node=1

# For testing, disable STONITH (NOT recommended for production)
sudo pcs property set stonith-enabled=false

# In production, configure a STONITH device:
# sudo pcs stonith create fence_ipmi ipmilan \
#     ip=192.168.1.50 action=reboot \
#     lanplus=true pcmk_host_list=node1 \
#     op monitor interval=60s
```

**Step 4: Add resources**

```bash
# Add the floating VIP
sudo pcs resource create vip IPaddr2 \
    ip=192.168.1.100 cidr_netmask=24 \
    op monitor interval=30s

# Add an HAProxy resource
sudo pcs resource create haproxy systemd:haproxy \
    op monitor interval=30s

# Colocate VIP and HAProxy on the same node
sudo pcs constraint colocation add vip haproxy INFINITY

# Ensure VIP starts before HAProxy
sudo pcs constraint order vip then haproxy

# Verify cluster status
sudo pcs status
```

### Cluster Status Output

```
Cluster name: ha_cluster
Cluster Summary:
  * Stack: corosync
  * Current DC: node1.example.com (version 2.1.6-1) - partition with quorum
  * Last updated: Tue Apr 21 12:00:00 2026
  * Last change: Tue Apr 21 11:55:00 2026 by root via cibadmin on node1
  * 3 nodes configured
  * 2 resource instances configured

Node List:
  * Online: [ node1.example.com node2.example.com node3.example.com ]

Full List of Resources:
  * vip   (ocf:heartbeat:IPaddr2):    Started node1.example.com
  * haproxy       (systemd:haproxy):         Started node1.example.com
```

### Docker Compose for Corosync + Pacemaker

Running Corosync + Pacemaker in containers requires multicast-capable networking:

```yaml
version: "3.8"

services:
  corosync:
    image: ghcr.io/clusterlabs/pacemaker:latest
    container_name: pacemaker-node1
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
      - SYS_RAWIO
    network_mode: "host"
    privileged: true
    volumes:
      - /var/lib/pacemaker:/var/lib/pacemaker
      - ./corosync.conf:/etc/corosync/corosync.conf:ro
    environment:
      - PCMK_network_host=node1,node2
      - PCMK_cluster_name=ha_cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "crm_mon", "-1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Key Differences: When to Use Each

### Choose Keepalived When:

- You need **simple active/passive failover** for a single service
- Your primary use case is **floating IP management** for a load balancer or reverse proxy
- You want **minimal configuration overhead** — a 30-line file is sufficient
- You are running on **resource-constrained nodes** (Keepalived uses ~10MB RAM)
- You do not need dependency management between resources
- You are managing 2-3 nodes maximum

Typical Keepalived deployments pair it with HAProxy, Nginx, or Traefik for a high-availability reverse proxy layer. For more on self-hosted load balancers, see our [complete guide to HAProxy, Envoy, and Nginx](../haproxy-vs-envoy-vs-nginx-load-balancer-guide/) and our [load balancer high availability overview](../self-hosted-load-balancers-traefik-haproxy-nginx-high-availability-guide-2026/).

### Choose Corosync + Pacemaker When:

- You need to manage **multiple interdependent resources** (VIP + filesystem + database + app)
- You require **active/active configurations** with load distribution
- You need **STONITH fencing** to prevent data corruption during split-brain
- You have **complex placement constraints** (anti-affinity, node pinning, resource ordering)
- You are running **3+ nodes** and need robust quorum management
- You need **live migration** of resources without service interruption
- You want **detailed cluster state monitoring** via CIB and `crm_mon`

For database-level high availability (which often runs on top of Corosync + Pacemaker), see our [database HA guide covering Patroni, Galera Cluster, and repmgr](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide).

## Production Best Practices

### 1. Avoid Split-Brain

Split-brain occurs when network partitioning causes both nodes to believe they are the active master. This leads to both nodes serving traffic on the same VIP — creating data inconsistency and duplicate transactions.

**Keepalived mitigation:** Use unicast instead of multicast, configure `advert_int 1` for fast detection, and add application-level health checks with `vrrp_script`.

```conf
# Unicast configuration avoids multicast issues
unicast_src_ip 192.168.1.10
unicast_peer {
    192.168.1.11
    192.168.1.12
}
```

**Corosync + Pacemaker mitigation:** Use a 3-node cluster for natural quorum, configure `two_node=1` for 2-node setups, and enable STONITH to fence unreachable nodes.

### 2. Use Odd Number of Nodes for Quorum

For Corosync + Pacemaker, always deploy an **odd number of nodes** (3, 5, 7) to ensure quorum can be reached during partitions. A 3-node cluster tolerates 1 node failure; a 5-node cluster tolerates 2.

### 3. Monitor Health Check Intervals

Keep your health check intervals consistent:

| Component | Recommended Interval | Notes |
|---|---|---|
| VRRP advert (Keepalived) | 1 second | Lower = faster failover, more network traffic |
| Health check script (Keepalived) | 2-5 seconds | Balance detection speed vs. false positives |
| Pacemaker resource monitor | 30 seconds | Standard interval for most resources |
| STONITH monitor (Pacemaker) | 60 seconds | Fencing devices change state infrequently |

### 4. Test Failover Regularly

Scheduled failover testing is essential. Plan monthly failover drills:

```bash
# Keepalived: force failover
sudo systemctl stop keepalived
sleep 5
ip addr show eth0 | grep 192.168.1.100  # Should NOT be on this node
sudo systemctl start keepalived          # Should become BACKUP

# Pacemaker: migrate resource to another node
sudo pcs resource move vip node2.example.com
sudo pcs resource unmove vip             # Remove constraint
```

### 5. Secure VRRP Communication

Never use default passwords in production. Keepalived supports both simple password authentication and IPsec AH (Authentication Header):

```conf
vrrp_instance VI_01 {
    authentication {
        auth_type AH  # IPsec Authentication Header
        # Or use auth_type PASS with a strong password
        auth_pass K33pAl1v3d_Str0ng!
    }
}
```

## Frequently Asked Questions

### Can I use Keepalived and Corosync + Pacemaker together?

Yes. A common architecture uses Keepalived at the edge for floating IP management (active/passive load balancers) and Corosync + Pacemaker for backend services (databases, application servers). This gives you fast VIP failover at the edge and sophisticated resource management in the backend.

### What happens during a network partition (split-brain)?

In Keepalived, the node with higher priority remains MASTER, but if the partition isolates the MASTER, the BACKUP will eventually take over — potentially creating two active nodes. In Corosync + Pacemaker, quorum prevents this: if a partition leaves fewer than half the nodes in a group, that group stops all resources. STONITH then fences the unreachable nodes to ensure safety.

### How fast is the failover?

Keepalived typically achieves 1-3 second failover with `advert_int 1`. Corosync + Pacemaker takes 2-5 seconds due to the additional resource stop/start sequence. Both are significantly faster than DNS-based failover (which takes 30-300 seconds due to TTL propagation).

### Do I need a dedicated network for cluster communication?

For Corosync + Pacemaker, a dedicated network (or VLAN) for cluster messaging is strongly recommended in production to prevent heartbeat delays caused by application traffic. Keepalived sends VRRP advertisements on the same network as the VIP, so a dedicated network is less critical but still beneficial.

### Can Keepalived manage more than one VIP?

Yes. Define multiple `vrrp_instance` blocks in the configuration, each with a different `virtual_router_id` and set of VIPs. You can distribute load by making Node A the MASTER for VIP1 and Node B the MASTER for VIP2 — achieving active/active at the IP level.

### What operating systems are supported?

Keepalived runs on Linux only (it requires Linux kernel support for VRRP and netlink sockets). Corosync + Pacemaker also run on Linux, with official support for Red Hat Enterprise Linux, SUSE Linux Enterprise, Debian, Ubuntu, and Rocky/Alma Linux.

### Is STONITH really necessary?

STONITH is essential for data safety. Without it, a failed node that appears dead but is actually still running (zombie node) could write to a shared filesystem while the promoted node also writes — causing filesystem corruption. STONITH ensures the failed node is truly powered off or isolated before resources start elsewhere.

### How do I monitor my HA cluster?

Keepalived logs to syslog — monitor with `journalctl -u keepalived`. Corosync + Pacemaker provide `crm_mon` for real-time cluster status, `crm_verify` for configuration validation, and CIB XML for programmatic access. For external monitoring, the `pacemaker-prometheus` exporter exposes cluster metrics in Prometheus format.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Keepalived vs Corosync + Pacemaker: Self-Hosted High Availability Clustering Guide 2026",
  "description": "Compare Keepalived and Corosync + Pacemaker for building self-hosted high availability clusters. Learn VRRP failover, resource management, and deployment with Docker Compose.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
