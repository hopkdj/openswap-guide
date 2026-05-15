---
title: "Self-Hosted BGP Communities Management — ExaBGP vs GoBGP vs FRRouting for Traffic Engineering"
date: "2026-05-15"
tags: ["bgp", "networking", "traffic-engineering", "exabgp", "gobgp", "frrouting"]
draft: false
---

BGP communities are a powerful mechanism for controlling route propagation, implementing traffic engineering policies, and automating network operations. By tagging routes with community values, network operators can signal routing preferences across autonomous systems without modifying the underlying routing protocol.

In this guide, we compare three open-source tools for managing BGP communities: **ExaBGP** (the BGP Swiss army knife), **GoBGP** (BGP in Go), and **FRRouting** (the FRR protocol suite). Each offers different approaches to community manipulation, from programmable policy engines to router-native configuration.

## Understanding BGP Communities

BGP communities are 32-bit values attached to BGP routes. They consist of two 16-bit parts: an ASN and a local value. The standard format is `ASN:value`, such as `65000:100`.

Three community types exist:
- **Standard communities** — 32-bit values (`ASN:local`)
- **Large communities** — 96-bit values (`ASN:local:context`), defined in RFC 8092
- **Extended communities** — 64-bit values with type codes (RFC 4360)

Communities are used for:
- **Traffic engineering** — controlling inbound/outbound path selection
- **Route filtering** — accepting or rejecting routes based on community tags
- **Route propagation control** — no-export, no-advertise, nopeer communities
- **Service signaling** — communicating service attributes between ASes

## ExaBGP: Programmable BGP Community Management

ExaBGP is a Python-based BGP daemon that exposes BGP operations through a simple text-based API. It excels at dynamic community manipulation through external scripts.

### Installation

```bash
pip3 install exabgp
# Or from source
git clone https://github.com/Exa-Networks/exabgp.git
cd exabgp
pip3 install -e .
```

### BGP Configuration with Community Manipulation

```ini
# exabgp.conf
group upstream {
    router-id 192.168.1.1;
    local-as 65000;
    local-address 192.168.1.1;

    neighbor 203.0.113.1 {
        local-address 192.168.1.1;
        peer-as 65001;
        ipv4 unicast;
        additive;
    }

    process community-manager {
        encoder json;
        run /opt/bgp-scripts/community_manager.py;
    }
}
```

### Python Community Manager Script

```python
#!/usr/bin/env python3
"""ExaBGP process script for dynamic BGP community management."""
import sys
import json

def manage_communities(message):
    """Parse BGP updates and apply community policies."""
    parsed = json.loads(message)

    if parsed.get("type") == "update":
        routes = parsed.get("neighbor", {}).get("message", {}).get("update", {})

        for announced in routes.get("announce", {}).get("ipv4 unicast", {}).values():
            for prefix, attributes in announced.items():
                # Apply traffic engineering communities
                if "10.0.0.0/8" in prefix:
                    attributes.setdefault("community", [])
                    attributes["community"].append("65000:100")  # Internal route
                    attributes["community"].append("65000:500")  # Low preference

                # Tag customer routes with bandwidth community
                if "172.16.0.0/12" in prefix:
                    attributes.setdefault("community", [])
                    attributes["community"].append("65000:200")  # Customer route
                    attributes["community"].append("65000:1000")  # 1Gbps bandwidth

        return json.dumps({"neighbor": {"message": {"update": routes}}})

    return message

if __name__ == "__main__":
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            result = manage_communities(line.strip())
            if result:
                sys.stdout.write(result + "
")
                sys.stdout.flush()
        except (json.JSONDecodeError, KeyError):
            continue
```

### ExaBGP Docker Compose

```yaml
# docker-compose-exabgp.yml
version: "3.8"
services:
  exabgp:
    image: exabgp/exabgp:latest
    container_name: exabgp-communities
    volumes:
      - ./exabgp.conf:/etc/exabgp/exabgp.conf:ro
      - ./community_manager.py:/opt/bgp-scripts/community_manager.py:ro
    environment:
      - exabgp_log_level=INFO
    network_mode: host
    restart: unless-stopped
```

## GoBGP: High-Performance Community Management

GoBGP is a BGP implementation in Go that provides a gRPC-based control plane. Its policy system supports sophisticated community matching and manipulation.

### Installation

```bash
go install github.com/osrg/gobgp/v3/cmd/gobgp@latest
gobgpd --help
```

### GoBGP Configuration with Communities

```toml
# gobgpd.conf
[global.config]
  as = 65000
  router-id = "192.168.1.1"

[[neighbors]]
  [neighbors.config]
    neighbor-address = "203.0.113.1"
    peer-as = 65001

[[neighbors]]
  [neighbors.config]
    neighbor-address = "203.0.113.2"
    peer-as = 65002

[policy-definitions]
  [[policy-definitions.policy]]
    name = "community-inbound"

    [[policy-definitions.policy.statements]]
      name = "tag-customer-routes"
      [policy-definitions.policy.statements.conditions.bgp-conditions]
        [[policy-definitions.policy.statements.conditions.bgp-conditions.community-list]]
          community-list = "customer-prefixes"
          match-type = "any"
      [policy-definitions.policy.statements.actions]
        [policy-definitions.policy.statements.actions.route-action]
          route-action = "accept"
        [policy-definitions.policy.statements.actions.bgp-actions]
          [[policy-definitions.policy.statements.actions.bgp-actions.set-community]]
            set-community.method = "add"
            set-community.options = ["65000:200"]

  [[policy-definitions.policy]]
    name = "community-outbound"

    [[policy-definitions.policy.statements]]
      name = "set-traffic-engineering"
      [policy-definitions.policy.statements.actions.bgp-actions]
        [[policy-definitions.policy.statements.actions.bgp-actions.set-community]]
          set-community.method = "add"
          set-community.options = ["65000:100", "65000:500"]

[routing-policy]
  [[routing-policy.defined-sets.community-sets]]
    community-set-name = "customer-prefixes"
    community-list = ["^65000:200$"]

  [[routing-policy.apply-policy.apply-policy-config]]
    policy-name = ["community-inbound", "community-outbound"]
    import-policy = ["community-inbound"]
    export-policy = ["community-outbound"]
```

### CLI Community Operations

```bash
# Add a route with specific communities
gobgp global rib add 10.0.0.0/8 community 65000:100 65000:500

# View routes and their communities
gobgp global rib -a ipv4

# Add large communities (RFC 8092)
gobgp global rib add 10.0.0.0/8 large-community 65000:100:1

# Set community policy for a neighbor
gobgp neighbor 203.0.113.1 policy import community-inbound add
```

### GoBGP Docker Compose

```yaml
# docker-compose-gobgp.yml
version: "3.8"
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp-communities
    volumes:
      - ./gobgpd.conf:/etc/gobgp/gobgpd.conf:ro
    network_mode: host
    cap_add:
      - NET_ADMIN
    restart: unless-stopped
```

## FRRouting: Router-Native Community Management

FRRouting (FRR) is a full-featured routing protocol suite that supports BGP communities through traditional router-style configuration. It is the most production-proven option.

### FRR Configuration

```
! /etc/frr/frr.conf
frr version 9.1
frr defaults traditional
hostname frr-bgp
log syslog informational

! BGP configuration
router bgp 65000
  bgp router-id 192.168.1.1
  neighbor 203.0.113.1 remote-as 65001
  neighbor 203.0.113.2 remote-as 65002

  ! Community lists
  bgp community-list standard INTERNAL permit 65000:100
  bgp community-list standard CUSTOMER permit 65000:200
  bgp community-list expanded LOW_PREF permit 65000:5.*

  ! Route maps for community manipulation
  route-map SET_COMMUNITY_IN permit 10
    match ip address prefix-list INTERNAL_PREFIXES
    set community 65000:100 65000:500 additive
  route-map SET_COMMUNITY_IN permit 20
    match ip address prefix-list CUSTOMER_PREFIXES
    set community 65000:200 65000:1000 additive
  route-map SET_COMMUNITY_IN permit 30

  ! Apply route maps to neighbors
  neighbor 203.0.113.1 route-map SET_COMMUNITY_IN in
  neighbor 203.0.113.1 route-map SET_COMMUNITY_OUT out
  neighbor 203.0.113.2 route-map SET_COMMUNITY_IN in
  neighbor 203.0.113.2 send-community both

  ! Large communities
  bgp community-list large LARGE_CUST permit 65000:200:100
  route-map SET_LARGE_COMMUNITY permit 10
    set large-community 65000:200:100 additive

  ! Address family configuration
  address-family ipv4 unicast
    neighbor 203.0.113.1 activate
    neighbor 203.0.113.2 activate
  exit-address-family

! Prefix lists
ip prefix-list INTERNAL_PREFIXES seq 5 permit 10.0.0.0/8
ip prefix-list CUSTOMER_PREFIXES seq 5 permit 172.16.0.0/12
```

### FRR Docker Compose

```yaml
# docker-compose-frr.yml
version: "3.8"
services:
  frr:
    image: frrouting/frr:v9.1.0
    container_name: frr-bgp-communities
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    sysctls:
      - net.ipv4.ip_forward=1
    restart: unless-stopped
```

### FRR Operational Commands

```bash
# View BGP routes with communities
vtysh -c "show ip bgp community"

# Show routes matching a specific community
vtysh -c "show ip bgp community-list INTERNAL"

# View community list definitions
vtysh -c "show ip community-list"

# Debug community processing
vtysh -c "debug bgp updates"
```

## Comparison: BGP Community Management Tools

| Feature | ExaBGP | GoBGP | FRRouting |
|---------|--------|-------|-----------|
| **Language** | Python | Go | C |
| **Configuration** | INI + Python scripts | TOML + CLI | Cisco-style config |
| **Community Types** | Standard, extended, large | Standard, extended, large | Standard, extended, large |
| **Dynamic Updates** | Yes (real-time via API) | Yes (gRPC) | Yes (vtysh) |
| **Policy Engine** | Custom Python code | TOML-based policies | Route maps |
| **Large Communities** | Yes (RFC 8092) | Yes (RFC 8092) | Yes (RFC 8092) |
| **Multi-protocol** | BGP only | BGP + BMP | Full suite (OSPF, ISIS, etc.) |
| **Production Ready** | Lab/edge use | Production | Carrier-grade |
| **Learning Curve** | Medium (Python) | Medium (Go + TOML) | Low (router CLI) |
| **Docker Support** | Community image | Official image | Official image |
| **Stars / Active Dev** | 2,268+ stars | 4,054+ stars | 4,128+ stars |

## Choosing the Right BGP Community Tool

**For programmable, API-driven community management**, ExaBGP is the most flexible. Its Python-based process interface allows you to implement any community manipulation logic, from simple static tagging to complex dynamic policies based on external data sources (monitoring systems, APIs, databases).

**For high-performance, production-grade BGP with structured policies**, GoBGP offers the best balance. Its TOML-based configuration is version-control friendly, and the gRPC control plane enables integration with automation frameworks. The policy system supports complex community matching and manipulation.

**For carrier-grade, multi-protocol routing with traditional configuration**, FRRouting is the industry standard. Its Cisco-style configuration will be familiar to network engineers, and the route-map system provides powerful community manipulation capabilities. FRR also supports the full range of routing protocols beyond BGP.

## Why Self-Host BGP Community Management?

**Traffic engineering control.** BGP communities are the primary mechanism for controlling traffic flow across autonomous systems. By tagging routes with specific community values, you can influence path selection, set local preference, and implement backup routing policies — all without manual BGP configuration changes on every router.

**Automation and CI/CD for networking.** Self-hosted BGP tools enable programmatic control of routing policies. ExaBGP's Python API and GoBGP's gRPC interface allow integration with infrastructure-as-code pipelines, enabling version-controlled, tested, and automated BGP community management.

**Multi-tenant routing.** For hosting providers and cloud operators, BGP communities enable per-customer traffic engineering. By assigning unique community values to customer routes, you can implement differentiated routing policies, bandwidth allocations, and path preferences for each tenant.

**Compliance and auditability.** Self-hosted BGP community management keeps all routing policy data within your infrastructure. Route maps, community lists, and policy configurations can be version-controlled, audited, and backed up alongside the rest of your infrastructure configuration.

For related reading, see our [BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/), [BGP monitoring tools](../2026-05-04-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter-looking-glass-guide/), and [BGP route reflector setup](../2026-05-12-self-hosted-bgp-route-reflector-frr-bird-gobgp-guide/).

## FAQ

### What are BGP large communities and why use them?

BGP large communities (RFC 8092) extend the 32-bit standard community to 96 bits (`ASN:local:context`). This provides vastly more address space for encoding routing information. For example, you can encode customer ID, service tier, and geographic region in a single large community value: `65000:12345:100` where 12345 is the customer ID and 100 is the service tier.

### Can I use ExaBGP as a production BGP speaker?

ExaBGP is best suited for edge cases and programmable BGP applications rather than core routing. It lacks some advanced BGP features and has not been battle-tested for carrier-grade routing at scale. For production core routing, FRRouting or GoBGP are recommended. ExaBGP excels at dynamic route injection, monitoring, and community manipulation through external scripts.

### How do I propagate communities across multiple ASes?

BGP communities are transitive by default — they are carried across AS boundaries. However, many ISPs strip standard communities at their borders. To ensure community propagation: (1) Use large communities (RFC 8092), which are less commonly stripped. (2) Establish community propagation agreements with upstream providers. (3) Use extended communities with well-known type codes.

### Does GoBGP support route reflection?

Yes, GoBGP supports route reflection. Configure a neighbor as a route reflector client using the `route-reflector-client` option in the neighbor configuration. GoBGP also supports route reflector clusters and originator-id for loop prevention, following RFC 4456.

### How do I debug community matching issues in FRR?

Enable community debugging in FRR using `vtysh` with `debug bgp community`. Then run `show ip bgp community` to see which routes have which communities, and `show ip bgp community-list` to verify your community list definitions. The `show route-map` command displays route-map processing details.

### Can BGP communities prevent route leaks?

Yes, BGP communities are commonly used to prevent route leaks. Well-known communities like `NO_EXPORT` (0xFFFFFF01) prevent a route from being advertised outside the local AS, and `NO_ADVERTISE` (0xFFFFFF02) prevent a route from being advertised to any peer. Custom community-based policies can implement more granular leak prevention, such as restricting routes to specific peer groups or geographic regions.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Communities Management — ExaBGP vs GoBGP vs FRRouting for Traffic Engineering",
  "description": "Compare BGP community management tools: ExaBGP, GoBGP, and FRRouting. Includes Docker Compose configs, community policies, and traffic engineering guides.",
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
