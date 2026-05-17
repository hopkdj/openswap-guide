---
title: "Self-Hosted BGP Peer Session Monitoring: GoBGP vs FRRouting vs BIRD (2026)"
date: "2026-05-17"
tags: ["bgp", "monitoring", "gobgp", "frrouting", "bird", "networking"]
draft: false
---

BGP (Border Gateway Protocol) peer sessions are the backbone of Internet routing. Monitoring BGP peer sessions — tracking adjacency state, route exchange health, prefix counts, and session stability — is critical for network reliability. A dropped BGP session can cause traffic blackholing, route flapping, or prefix withdrawal affecting thousands of downstream networks.

In this guide, we compare three open-source routing daemons for their **BGP peer session monitoring capabilities**: **GoBGP**, **FRRouting**, and **BIRD**. We examine how each tool exposes session state, supports programmatic monitoring, and integrates with observability stacks.

## Why BGP Peer Session Monitoring Matters

BGP operates as a long-lived TCP session (port 179) between peers. Each session goes through several states: Idle, Connect, Active, OpenSent, OpenConfirm, and Established. Monitoring these states is essential for:

- **Session health**: Detecting dropped or stuck BGP sessions before they impact routing
- **Prefix count validation**: Ensuring the expected number of routes are received from each peer
- **Route flapping detection**: Identifying unstable peers that frequently reset sessions
- **Convergence tracking**: Measuring how quickly sessions re-establish after a failure
- **Policy verification**: Confirming that route filters, community assignments, and path attributes are applied correctly

## Tool Comparison

| Feature | GoBGP | FRRouting | BIRD |
|---|---|---|---|
| **Monitoring API** | gRPC (native) | REST API + VTYSH | CLI + UNIX socket |
| **Session State Export** | Real-time gRPC streams | VTYSH `show bgp summary` | `birdc show protocols` |
| **Programmatic Access** | Full gRPC API (Go, Python, etc.) | REST API (FRR 9+) | Limited (parser-based) |
| **Prometheus Exporter** | Community `gobgp_exporter` | Official `frr_exporter` | Community `bird_exporter` |
| **BGP Session Events** | Event-driven (gRPC subscribe) | Syslog + VTYSH polling | Syslog + CLI polling |
| **Graceful Restart** | Yes | Yes | Yes |
| **BFD Integration** | Yes | Yes | Yes |
| **Docker Image** | `osrg/gobgp` | `frrouting/frr` | Community images |
| **GitHub Stars** | 4,055+ | 4,132+ | 188+ |
| **Last Updated** | May 2026 | May 2026 | May 2026 |

## GoBGP BGP Peer Monitoring

GoBGP provides the most developer-friendly monitoring interface among the three, with a native gRPC API that streams real-time BGP session events.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp-monitor
    hostname: gobgp-01
    ports:
      - "50051:50051"   # gRPC API
      - "179:179"       # BGP
    volumes:
      - ./gobgp-conf:/etc/gobgp:rw
    command: ["/usr/bin/gobgpd", "-f", "/etc/gobgp/gobgp.conf", "-t", "yaml"]
    restart: unless-stopped
```

### GoBGP Configuration with Monitoring

```yaml
global:
  config:
    as: 65001
    router-id: 192.168.1.1
  use-multiple-paths:
    ebgp:
      config:
        maximum-paths: 4

neighbors:
  - config:
      neighbor-address: 192.168.1.2
      peer-as: 65002
    timers:
      config:
        connect-retry: 10
        hold-time: 90
        keepalive-interval: 30
    route-reflector:
      config:
        route-reflector-client: true
        route-reflector-cluster-id: "192.168.1.1"
    afi-safis:
      - afi-safi-name: ipv4-unicast
        config:
          enabled: true
      - afi-safi-name: ipv6-unicast
        config:
          enabled: true

# gRPC server for monitoring
grpc:
  config:
    listen-address: "0.0.0.0:50051"
```

### Monitoring BGP Peers via gRPC

GoBGP's gRPC API allows real-time monitoring of all peer sessions:

```bash
# Check all BGP peer sessions
gobgp neighbor

# Get detailed session state for a specific peer
gobgp neighbor 192.168.1.2

# Monitor session state changes in real-time
gobgp monitor peer

# Get received routes from a peer
gobgp neighbor 192.168.1.2 received -j

# Check advertised routes to a peer
gobgp neighbor 192.168.1.2 advertised -j
```

GoBGP monitoring strengths:
- **Real-time event streaming**: Subscribe to `WatchEvent` for instant session state change notifications
- **JSON output**: All CLI commands support `-j` for JSON-formatted output
- **gRPC service definitions**: Protobuf definitions available for building custom monitoring tools
- **BMP support**: BGP Monitoring Protocol (RFC 7854) for centralized monitoring
- **Python client**: Official `pygobgp` library for programmatic access

## FRRouting BGP Peer Monitoring

FRRouting provides multiple monitoring interfaces: the traditional VTYSH CLI, a modern REST API, and Prometheus metrics export.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  frr-bgp:
    image: frrouting/frr:latest
    container_name: frr-bgp-monitor
    hostname: frr-bgp-01
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./frr-conf:/etc/frr:rw
      - /var/run/frr:/var/run/frr:rw
    ports:
      - "8000:8000"  # REST API
    restart: unless-stopped
```

### FRRouting BGP Configuration with Monitoring

```
! Enable BGP and related daemons
zebra=yes
bgpd=yes

! BGP configuration
router bgp 65001
 bgp router-id 192.168.1.1
 bgp log-neighbor-changes
 bgp graceful-restart
 bgp graceful-restart restart-time 120
 bgp graceful-restart stalepath-time 360
 !
 neighbor 192.168.1.2 remote-as 65002
 neighbor 192.168.1.2 description "Upstream Peer A"
 neighbor 192.168.1.2 timers 30 90
 neighbor 192.168.1.2 hold-time 90
 neighbor 192.168.1.2 keep-alive 30
 neighbor 192.168.1.2 bfd
 neighbor 192.168.1.2 graceful-restart
 neighbor 192.168.1.2 graceful-restart-helper
 !
 neighbor 192.168.1.3 remote-as 65003
 neighbor 192.168.1.3 description "Upstream Peer B"
 neighbor 192.168.1.3 timers 30 90
 neighbor 192.168.1.3 bfd
 !
 address-family ipv4 unicast
  neighbor 192.168.1.2 activate
  neighbor 192.168.1.2 soft-reconfiguration inbound
  neighbor 192.168.1.3 activate
  neighbor 192.168.1.3 soft-reconfiguration inbound
 !
 address-family ipv6 unicast
  neighbor 2001:db8::1 activate
  neighbor 2001:db8::2 activate
```

### Monitoring BGP Peers via VTYSH and REST API

```bash
# VTYSH: Check all BGP peer sessions
vtysh -c "show bgp summary"

# VTYSH: Detailed peer information
vtysh -c "show bgp neighbors 192.168.1.2"

# VTYSH: BGP route counts
vtysh -c "show bgp ipv4 unicast summary"

# REST API (FRR 9+): Get BGP peer status
curl -s http://localhost:8000/v1/bgp/neighbors | python3 -m json.tool

# REST API: Specific peer details
curl -s http://localhost:8000/v1/bgp/neighbors/192.168.1.2 | python3 -m json.tool
```

FRRouting monitoring strengths:
- **Multiple interfaces**: VTYSH (CLI), REST API, SNMP, and Prometheus exporter
- **BFD integration**: Fast failure detection for BGP sessions
- **Graceful Restart**: Session recovery without route withdrawal
- **Comprehensive logging**: Session state changes logged with timestamps
- **frr_exporter**: Official Prometheus exporter with BGP peer metrics

## BIRD BGP Peer Monitoring

BIRD takes a minimalist approach to BGP peer monitoring, relying on its CLI interface and syslog output for session state information.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  bird-bgp:
    image: alpine:latest
    container_name: bird-bgp-monitor
    hostname: bird-bgp-01
    cap_add:
      - NET_ADMIN
    network_mode: "host"
    volumes:
      - ./bird-conf:/etc/bird:rw
    command: ["bird", "-d"]
    restart: unless-stopped
```

### BIRD BGP Configuration with Monitoring

```
router id 192.168.1.1;

protocol bgp peer_a {
    local as 65001;
    neighbor 192.168.1.2 as 65002;
    description "Upstream Peer A";
    graceful restart;
    hold time 90;
    keepalive time 30;
    connect delay time 10;
    connect retry time 60;
    
    import all;
    export filter {
        if source = RTS_STATIC then accept;
        reject;
    };
}

protocol bgp peer_b {
    local as 65001;
    neighbor 192.168.1.3 as 65003;
    description "Upstream Peer B";
    graceful restart;
    hold time 90;
    keepalive time 30;
    
    import all;
    export filter {
        if source = RTS_STATIC then accept;
        reject;
    };
}

protocol kernel {
    persist;
    scan time 20;
    import all;
    export filter {
        if source = RTS_BGP then accept;
        reject;
    };
}

protocol device {
    scan time 10;
}
```

### Monitoring BGP Peers via BIRD CLI

```bash
# Check all BGP protocol states
birdc show protocols

# Detailed BGP peer information
birdc show protocols "peer_a" all

# BGP route counts
birdc show route count

# BGP routing table
birdc show route all

# BGP neighbor state (parsing required)
birdc show protocols | grep BGP
```

BIRD monitoring strengths:
- **Lightweight**: Minimal resource usage (~5 MB per daemon)
- **Clean output**: Structured, parseable CLI output
- **bird_exporter**: Community Prometheus exporter for BGP metrics
- **Syslog integration**: Session state changes logged to syslog
- **Powerful filtering**: BIRD's expression language for route policy verification

## Building a BGP Monitoring Dashboard

For comprehensive BGP peer session monitoring, combine the routing daemon's native monitoring with an observability stack:

### Prometheus + Grafana Setup

```yaml
version: "3.8"
services:
  frr-exporter:
    image: tynany/frr_exporter:latest
    container_name: frr-exporter
    network_mode: "host"
    command: ["--frr.address=localhost:8000"]
    restart: unless-stopped

  bird-exporter:
    image: sbernet/bird-exporter:latest
    container_name: bird-exporter
    network_mode: "host"
    command: ["--bird.socket=/var/run/bird/bird.ctl"]
    volumes:
      - /var/run/bird:/var/run/bird:ro
    restart: unless-stopped
```

Key Prometheus metrics for BGP monitoring:
- `frr_bgp_peer_state` — BGP session state (1=Established, 2=Idle, etc.)
- `frr_bgp_prefixes_accepted` — Number of prefixes received from each peer
- `frr_bgp_peer_uptime_seconds` — Session uptime for stability tracking
- `bird_protocol_state` — BIRD protocol state per peer
- `bird_bgp_routes_received` — Route count per BGP peer

## Why Self-Host Your BGP Monitoring?

### Complete Visibility
Self-hosted BGP monitoring gives you direct access to peer session state, route exchange statistics, and protocol-level diagnostics. You are not dependent on third-party looking glass services or external monitoring platforms that may have limited visibility into your specific peer sessions.

For **BGP route alerting**, see our [BGP monitoring and route alerting guide](../2026-05-09-self-hosted-bgp-monitoring-route-alerting-bgpalerter-exabgp-gobgp/). For **OSPF adjacency monitoring** (the IGP counterpart), our [OSPF monitoring guide](../2026-05-15-self-hosted-ospf-monitoring-frr-bird-gobgp-guide/) covers the link-state monitoring landscape. For **BGP communities management**, our [communities management article](../2026-05-15-self-hosted-bgp-communities-management-exabgp-gobgp-frrouting-guide/) covers route tagging strategies.

### Faster Incident Response
When a BGP session drops, every second counts. Self-hosted monitoring with real-time alerts (via Prometheus Alertmanager or custom gRPC event handlers) means you detect session failures in seconds rather than waiting for external monitoring checks that poll every 5-15 minutes.

### Cost and Compliance
Enterprise BGP monitoring platforms can cost thousands per month. Open-source alternatives provide the same visibility at zero licensing cost. Additionally, keeping BGP monitoring data on your own infrastructure ensures compliance with data sovereignty requirements.

## FAQ

### What is the most important BGP peer session metric to monitor?

**Session state** is the primary metric — you need to know immediately when a BGP session transitions from Established to any other state. Secondary metrics include prefix counts (sudden drops indicate route withdrawal or filtering issues), session uptime (for stability trending), and BFD state (for fast failure detection).

### How do I detect BGP route flapping?

Route flapping is detected by monitoring rapid session state changes. Configure **BGP route dampening** to automatically suppress flapping routes. In FRRouting: `bgp dampening 30 750 2000 300`. In BIRD: use `graceful restart` with appropriate timers. Monitor session reset frequency with `show bgp neighbors <ip> | grep "Connection resets"`.

### Can I monitor BGP sessions with Prometheus?

Yes. Use `frr_exporter` for FRRouting (official), `bird_exporter` for BIRD (community), or build a custom exporter for GoBGP using its gRPC API. Key metrics include peer state, prefix counts, session uptime, and BFD state changes.

### What is BGP Graceful Restart and why does it matter for monitoring?

Graceful Restart (GR, RFC 4724) allows a BGP speaker to restart its control plane while preserving forwarding state. During GR, the peer continues to forward traffic using the last-known routes. Monitoring GR state is important — a peer stuck in GR for too long indicates a problem. All three implementations support GR.

### How do I set up BGP session alerts?

Configure alerts on:
- Session state != Established for > 60 seconds
- Prefix count deviation > 10% from baseline
- Session uptime reset (indicates flapping)
- BFD state down
Use Prometheus Alertmanager with FRRouting/BIRD exporters, or GoBGP's gRPC event stream with a custom alerting service.

### Should I use BFD with BGP?

**Yes, absolutely.** BFD (Bidirectional Forwarding Detection) provides sub-second failure detection for BGP sessions. Without BFD, BGP relies on the hold timer (typically 90-180 seconds) to detect peer failures. With BFD, failures are detected in milliseconds. All three implementations support BFD integration with BGP.

### How do I troubleshoot a BGP session stuck in Active state?

A BGP session stuck in Active typically indicates:
1. **TCP connectivity issues**: Check `tcpdump port 179` for SYN packets
2. **AS number mismatch**: Verify `remote-as` configuration on both sides
3. **Router ID conflict**: Ensure unique router IDs
4. **Firewall blocking**: Verify port 179 is open in both directions
5. **Maximum prefix limit**: Check if the peer has exceeded prefix limits
Use `show bgp neighbors <ip>` (FRR) or `show protocols <name> all` (BIRD) for detailed diagnostics.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Peer Session Monitoring: GoBGP vs FRRouting vs BIRD (2026)",
  "description": "Compare BGP peer session monitoring capabilities of GoBGP, FRRouting, and BIRD. Includes gRPC API, REST API, Prometheus exporters, and Docker deployment configs.",
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
