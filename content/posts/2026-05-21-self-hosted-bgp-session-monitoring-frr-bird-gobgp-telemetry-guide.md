---
title: "Self-Hosted BGP Session Monitoring: FRRouting vs BIRD vs GoBGP Telemetry"
date: "2026-05-21"
tags: ["networking", "bgp", "monitoring", "telemetry"]
draft: false
---

BGP (Border Gateway Protocol) is the routing protocol that powers the Internet. When BGP sessions flap, peer connections drop, or routes are incorrectly advertised, the impact can range from degraded application performance to complete network isolation. This guide compares how FRRouting, BIRD, and GoBGP expose BGP session state, telemetry data, and monitoring interfaces — enabling you to build comprehensive BGP observability on self-hosted infrastructure.

## Why BGP Session Monitoring Is Critical

BGP sessions carry routing information between autonomous systems. A single session failure can withdraw thousands of routes, redirecting traffic through suboptimal paths or making destinations unreachable. Monitoring BGP session state — peer status, route counts, update messages, and flap history — is essential for network operators who need to detect issues before they cause outages.

Key metrics for BGP monitoring include:
- **Peer state**: Established, Idle, Active, Connect, OpenSent, OpenConfirm
- **Route counts**: Routes received, routes advertised, routes filtered
- **Update statistics**: Messages sent/received, withdrawals, notification errors
- **Session uptime**: Duration of current established session
- **Flap history**: Number of session resets over time

## FRRouting BGP Monitoring

FRRouting (FRR) is the most feature-complete open-source BGP implementation, supporting BGP, OSPF, IS-IS, RIP, and more. Its monitoring interface is accessed through the `vtysh` CLI and a JSON API.

### VTYSH CLI Monitoring

```bash
# Show all BGP peers and their state
vtysh -c "show bgp summary"

# Show BGP peer details including timers and capabilities
vtysh -c "show bgp neighbors"

# Show routes received from a specific peer
vtysh -c "show bgp neighbors 192.168.1.1 routes"

# Show BGP update statistics
vtysh -c "show bgp neighbors 192.168.1.1 advertised-routes"
```

### JSON API for Automation

FRR supports JSON output for all CLI commands, enabling programmatic monitoring:

```bash
# Get BGP summary as JSON
vtysh -c "show bgp summary json"

# Get neighbor details as JSON
vtysh -c "show bgp neighbors 192.168.1.1 json"
```

Sample output includes peer address, AS number, state, uptime, messages sent/received, and route counts — all parseable by monitoring scripts.

### Prometheus Integration via FRR Exporter

The `frr_exporter` scrapes FRR's VTYSH JSON output and exposes it as Prometheus metrics:

```bash
# Install frr_exporter
go install github.com/tynany/frr_exporter@latest

# Run with FRR VTYSH socket
frr_exporter --frr.vtysh.socket=/var/run/frr/vtysh
```

Key metrics: `frr_bgp_peer_state`, `frr_bgp_peer_uptime_seconds`, `frr_bgp_peer_prefixes_received`, `frr_bgp_peer_updates_received_total`.

### Docker Compose Deployment

```yaml
services:
  frr:
    image: frrouting/frr:stable_9.1
    container_name: frr
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
      - SYS_PTRACE
    network_mode: "host"
    volumes:
      - ./frr.conf:/etc/frr/frr.conf
      - ./daemons:/etc/frr/daemons
    restart: unless-stopped

  frr-exporter:
    image: tynany/frr_exporter:latest
    container_name: frr-exporter
    ports:
      - "9342:9342"
    volumes:
      - /var/run/frr:/var/run/frr
    command:
      - "--frr.vtysh.socket=/var/run/frr/vtysh"
    depends_on:
      - frr
    restart: unless-stopped
```

## BIRD BGP Monitoring

BIRD (BGP Internet Routing Daemon) is a lightweight, high-performance routing daemon popular in IXPs and small-to-medium networks. Its monitoring interface uses the `birdc` CLI and a Unix socket protocol.

### BIRD CLI Monitoring

```bash
# Show BGP protocol status
birdc "show protocols all bgp*"

# Show BGP routes from a specific peer
birdc "show route protocol bgp_peer_name"

# Show BGP route table
birdc "show route"

# Show BGP peer session details
birdc "show protocol all bgp_peer_name"
```

BIRD's output format is structured and parseable, showing peer state, BGP state machine transitions, route counts, and filter results.

### BIRD Exporter for Prometheus

The `bird_exporter` connects to BIRD's Unix socket and exposes metrics:

```bash
# Install bird_exporter
go install github.com/czerwonk/bird_exporter@latest

# Run with BIRD socket
bird_exporter --bird.socket=/var/run/bird/bird.ctl
```

Metrics include `bird_bgp_protocol_state`, `bird_bgp_prefixes_received`, `bird_bgp_prefixes_accepted`, `bird_bgp_uptime_seconds`.

### Docker Compose Deployment

```yaml
services:
  bird:
    image: xaviertorres/bird2:latest
    container_name: bird
    cap_add:
      - NET_ADMIN
    network_mode: "host"
    volumes:
      - ./bird.conf:/etc/bird/bird.conf
    restart: unless-stopped

  bird-exporter:
    image: czerwonk/bird_exporter:latest
    container_name: bird-exporter
    ports:
      - "9324:9324"
    volumes:
      - /var/run/bird:/var/run/bird
    command:
      - "--bird.socket=/var/run/bird/bird.ctl"
    depends_on:
      - bird
    restart: unless-stopped
```

## GoBGP Monitoring

GoBGP is a BGP implementation written in Go, designed for programmatic control via gRPC and CLI. It's particularly suited for SDN environments and cloud-native networking.

### CLI Monitoring

```bash
# Show BGP neighbors
gobgp neighbor

# Show neighbor details
gobgp neighbor 192.168.1.1

# Show received routes
gobgp neighbor 192.168.1.1 adj-in

# Show global BGP statistics
gobgp global rib
```

### gRPC API for Automation

GoBGP exposes a comprehensive gRPC API for programmatic monitoring and control:

```go
// Go client example
conn, _ := grpc.Dial("localhost:50051", grpc.WithInsecure())
client := api.NewGobgpApiClient(conn)
resp, _ := client.ListPeer(context.Background(), &api.ListPeerRequest{})
for _, peer := range resp.Peers {
    fmt.Printf("Peer: %s, State: %s, Uptime: %d
",
        peer.State.NeighborAddress,
        peer.State.SessionState,
        peer.State.Uptime.Seconds)
}
```

### Prometheus Metrics

GoBGP has built-in Prometheus metrics exposure:

```toml
# gobgp.toml
[global.config]
  as = 65000
  router-id = "192.168.1.1"

[global.apply-policy.config]

[[neighbors]]
  [neighbors.config]
    neighbor-address = "10.0.0.1"
    peer-as = 65001

[metrics.config]
  enable = true
```

GoBGP exposes metrics on port 50052 by default when metrics are enabled, including peer state, route counts, and update statistics.

### Docker Compose Deployment

```yaml
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp
    cap_add:
      - NET_ADMIN
    network_mode: "host"
    volumes:
      - ./gobgp.toml:/etc/gobgp/gobgp.toml
    restart: unless-stopped
```

## Comparison Table

| Feature | FRRouting | BIRD | GoBGP |
|---------|-----------|------|-------|
| **CLI Interface** | vtysh (Cisco-style) | birdc (own syntax) | gobgp CLI |
| **JSON Output** | Built-in (--json flag) | No (text-only) | Built-in (gRPC) |
| **Prometheus Exporter** | frr_exporter (community) | bird_exporter (community) | Built-in |
| **gRPC API** | No | No | Yes (first-class) |
| **BGP Protocol Support** | Full (RFC 4271 + extensions) | Full (BGP4) | Full (BGP4 + extensions) |
| **BFD Integration** | Yes | Yes | Yes |
| **Route Server Mode** | Yes | Yes | Yes |
| **Policy Language** | Route maps, prefix lists | Filter expressions | Policy config (TOML) |
| **Multiprotocol BGP** | Yes | Yes | Yes |
| **GitHub Stars** | 4,100+ | 189 | 4,000+ |
| **License** | GPLv2 | GPLv2+ | Apache 2.0 |

## Building BGP Monitoring Dashboards

A comprehensive BGP monitoring dashboard should include:

- **Peer state panel**: Color-coded peer status (green = Established, red = any other state)
- **Route count trends**: Historical graph of routes received per peer
- **Session uptime**: Current session duration with alerts on resets
- **Update rate**: Messages per second (sudden spikes may indicate route flapping)
- **Filter effectiveness**: Routes accepted versus routes received

```yaml
# Example Prometheus recording rules for BGP
groups:
  - name: bgp_recording_rules
    rules:
      - record: bgp_peer_established
        expr: frr_bgp_peer_state == 6

      - record: bgp_peer_uptime_hours
        expr: frr_bgp_peer_uptime_seconds / 3600

      - record: bgp_route_count_change_rate
        expr: rate(frr_bgp_peer_prefixes_received[5m])
```

## Why Self-Host BGP Monitoring?

Running your own BGP routing stack with integrated monitoring gives you complete visibility into session state, route propagation, and policy effectiveness. Managed BGP services hide the protocol internals behind abstraction layers — you can't see individual peer state, filter results, or update messages. Self-hosted BGP with FRR, BIRD, or GoBGP, combined with Prometheus exporters, enables real-time alerting on peer state changes, historical trending of route counts, and integration with your broader network observability stack.

For BGP routing fundamentals, see our [FRRouting vs BIRD vs OpenBGPD guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/). For BGP monitoring and alerting, check our [BGPalerter vs ExaBGP vs GoBGP guide](../2026-05-09-self-hosted-bgp-monitoring-route-alerting-bgpalerter-exabgp-gobgp/). For anycast deployment, see our [Bird/FRR anycast guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide/).

## FAQ

### What BGP session states should trigger alerts?

Any state other than "Established" should trigger an alert. The BGP finite state machine progresses through Idle, Connect, Active, OpenSent, and OpenConfirm before reaching Established. Sessions stuck in Active or Connect typically indicate TCP connectivity issues.

### How often should I poll BGP session state?

Every 15-30 seconds is sufficient for most monitoring needs. BGP session state changes are rare during stable operation, and the BGP keepalive interval (typically 60 seconds) sets an upper bound on how quickly state changes can occur.

### What is the difference between BGP and BFD for session monitoring?

BGP monitors the protocol-level session (route exchange, policy enforcement), while BFD (Bidirectional Forwarding Detection) monitors the underlying IP connectivity between peers. BFD detects link failures in milliseconds, while BGP hold timers typically take 30-180 seconds. Using both provides fast failure detection with protocol-level visibility.

### Can I monitor BGP sessions without root access?

FRR and BIRD require root (or CAP_NET_ADMIN) to bind to privileged ports and manage routing tables. However, the monitoring exporters (frr_exporter, bird_exporter) only need read access to the VTYSH socket or Unix control socket, which can be configured for non-root users.

### How do I detect BGP route leaks?

Monitor the prefix count received from each peer against expected baselines. A sudden increase in received routes may indicate a route leak. Set alerts when `prefixes_received` deviates by more than 10-20% from the historical average. RPKI validation (with `rpki` in FRR or BIRD) can also filter invalid routes.

### Does GoBGP support BGP FlowSpec?

Yes, GoBGP supports BGP FlowSpec (RFC 8955) for traffic filtering and DDoS mitigation. You can install FlowSpec rules programmatically via the gRPC API, enabling automated response to traffic anomalies detected by your monitoring system.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Session Monitoring: FRRouting vs BIRD vs GoBGP Telemetry",
  "description": "Compare BGP session monitoring across FRRouting vtysh JSON API, BIRD socket exporter, and GoBGP gRPC telemetry — including Prometheus integration and Docker Compose deployments.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
