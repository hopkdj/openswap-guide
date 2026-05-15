---
title: "Self-Hosted DHCP Management Dashboards: Stork vs Kea Web UI vs NetBox Integration"
date: "2026-05-16"
tags: ["dhcp", "networking", "dashboard", "stork", "kea", "netbox", "infrastructure"]
draft: false
---

Managing DHCP servers through configuration files and CLI commands becomes increasingly difficult as network infrastructure scales. Self-hosted DHCP management dashboards provide centralized, web-based control over DHCP scopes, leases, failover pairs, and subnet configurations. This guide compares the three leading approaches to visual DHCP management: ISC Stork, custom Kea Control Agent frontends, and NetBox-based DHCP integration.

## Why Web-Based DHCP Management Matters

Traditional DHCP server administration relies on editing text configuration files, restarting services, and monitoring log files for lease activity. While this approach works for small networks with a handful of subnets, it quickly becomes untenable in enterprise environments with dozens of VLANs, multiple DHCP servers, and complex failover configurations.

Web-based DHCP dashboards solve these challenges by providing real-time visibility into lease utilization, subnet health, and server status. Administrators can identify exhausted address pools before they cause outages, monitor failover pair synchronization, and audit DHCP configuration changes through intuitive interfaces rather than parsing thousands of log lines.

The shift toward software-defined networking and infrastructure-as-code practices has also raised expectations for DHCP management. Modern network teams want API-driven configuration, Git-backed change tracking, and integration with broader IP address management (IPAM) systems. The tools covered in this comparison represent three distinct philosophies for meeting these needs: purpose-built dashboards, API-centric control planes, and IPAM-integrated workflows.

For broader DHCP server setup guidance, see our [complete Kea vs ISC vs dnsmasq comparison](../2026-05-04-self-hosted-dhcp-server-management-kea-dnsmasq-isc-dhcp-guide/). If you need DHCP high availability configuration, check our [DHCP failover guide](../2026-05-14-self-hosted-dhcp-failover-ha-kea-dhcp-dnsmasq-guide/) which covers Kea HA setup in detail. For load balancing scenarios, our [DHCP load balancer guide](../2026-05-15-self-hosted-dhcp-load-balancer-kea-haproxy-isc-dhcp-split-scope-guide/) covers split-scope and relay configurations.

## ISC Stork: Official DHCP & DNS Dashboard

[Stork](https://github.com/isc-projects/stork) is the official web application developed by ISC (Internet Systems Consortium) for monitoring and managing BIND 9 DNS servers and Kea DHCP servers. It provides a unified dashboard for both services, making it the go-to choice for organizations running ISC's infrastructure stack.

### Key Features

- **Real-time monitoring**: Live lease statistics, subnet utilization graphs, and server health metrics
- **Multi-server management**: Monitor multiple Kea DHCP servers and BIND 9 instances from a single interface
- **Configuration visualization**: View and validate Kea JSON configuration through a web UI
- **Alerting**: Built-in alerting for critical events like subnet exhaustion or server failures
- **REST API integration**: Consumes data from Kea Control Agent and BIND 9 statistics channels
- **Open source**: MPL 2.0 license, actively maintained by ISC

### Architecture

Stork operates as a standalone web application that connects to Kea DHCP servers through their Control Agent REST API and to BIND 9 servers through the statistics channel. It does not modify configurations directly but provides read-only monitoring with validation capabilities.

```yaml
# docker-compose.yml for Stork
version: "3.8"
services:
  stork:
    image: iscorg/stork-server:latest
    container_name: stork
    ports:
      - "8080:8080"
    environment:
      - STORK_DATABASE_URL=postgres://stork:stork@stork-db:5432/stork?sslmode=disable
    depends_on:
      - stork-db

  stork-db:
    image: postgres:15-alpine
    container_name: stork-db
    environment:
      - POSTGRES_USER=stork
      - POSTGRES_PASSWORD=stork
      - POSTGRES_DB=stork
    volumes:
      - stork-data:/var/lib/postgresql/data

volumes:
  stork-data:
```

### Kea Control Agent Configuration

To connect Stork to Kea DHCP servers, enable the Control Agent with statistics collection:

```json
{
  "Dhcp4": {
    "control-socket": {
      "socket-type": "unix",
      "socket-name": "/tmp/kea4-ctrl.sock"
    },
    "hooks-libraries": [
      {
        "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_stat_cmds.so"
      }
    ]
  },
  "Control-agent": {
    "http-host": "0.0.0.0",
    "http-port": 8000,
    "control-sockets": {
      "Dhcp4": {
        "socket-type": "unix",
        "socket-name": "/tmp/kea4-ctrl.sock"
      }
    }
  }
}
```

### Pros and Cons

| Feature | Stork |
|---------|-------|
| Multi-server monitoring | Yes (Kea + BIND) |
| Real-time lease visualization | Yes |
| Configuration editing | Validation only |
| Alerting | Built-in |
| Database backend | PostgreSQL |
| Docker support | Official images |
| Active development | ISC maintained |
| Learning curve | Low |

## Custom Kea Control Agent Frontends

The Kea DHCP Control Agent provides a comprehensive REST API that enables any frontend application to monitor and manage DHCP operations. Several community-built web interfaces leverage this API to provide DHCP management capabilities tailored to specific use cases.

### Popular Kea Frontend Options

**Kea DHCP Web UI** — Community-built web interfaces that provide subnet management, lease browsing, and reservation configuration through a browser. These typically run as lightweight Flask or Node.js applications that proxy Kea Control Agent API calls.

```python
# Example Flask-based Kea management endpoint
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)
KEA_CONTROL_AGENT = "http://kea-dhcp:8000"

@app.route("/api/subnets")
def get_subnets():
    response = requests.post(
        f"{KEA_CONTROL_AGENT}",
        json={"command": "subnet4-list"}
    )
    return jsonify(response.json())

@app.route("/api/leases", methods=["GET"])
def get_leases():
    subnet_id = request.args.get("subnet_id")
    cmd = {"command": "lease4-get-all"}
    if subnet_id:
        cmd = {"command": "lease4-get-page", "arguments": {"subnets-id": [int(subnet_id)]}}
    response = requests.post(f"{KEA_CONTROL_AGENT}", json=cmd)
    return jsonify(response.json())

@app.route("/api/reservations", methods=["POST"])
def add_reservation():
    data = request.json
    cmd = {
        "command": "reservation-add",
        "arguments": {
            "subnet-id": data["subnet_id"],
            "reservation": {
                "hw-address": data["mac"],
                "ip-address": data["ip"]
            }
        }
    }
    response = requests.post(f"{KEA_CONTROL_AGENT}", json=cmd)
    return jsonify(response.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### NetBox Kea Integration

[NetBox](https://github.com/netbox-community/netbox) is the leading open-source IPAM and DCIM platform. Several integrations connect NetBox to Kea DHCP, using NetBox as the source of truth for IP addresses, subnets, and DHCP reservations.

The [netbox-kea](https://github.com/devon-mar/netbox-kea) plugin (117+ stars) synchronizes NetBox IP addresses and prefixes to Kea DHCP configuration. When an IP address is assigned in NetBox, the plugin can automatically create a DHCP reservation in Kea, ensuring that the DHCP server always reflects the IPAM database.

```yaml
# NetBox plugin configuration (configuration.py)
PLUGINS = ["netbox_kea"]
PLUGINS_CONFIG = {
    "netbox_kea": {
        "kea_api_url": "http://kea-ctrl-agent:8000",
        "kea_api_timeout": 10,
        "sync_interval": 300,  # seconds
        "auto_create_reservations": True,
        "subnet_mapping": {
            "10.0.1.0/24": 1,  # NetBox prefix ID -> Kea subnet ID
            "10.0.2.0/24": 2,
        }
    }
}
```

### Kea REST API Key Commands

The Kea Control Agent API provides these essential commands for DHCP management:

| Command | Purpose |
|---------|---------|
| `subnet4-list` | List all IPv4 subnets |
| `lease4-get-all` | Retrieve all active leases |
| `lease4-get-page` | Paginated lease retrieval |
| `reservation-add` | Add a static reservation |
| `reservation-get` | Get reservation details |
| `config-get` | Retrieve current configuration |
| `statistic-get-all` | Get all server statistics |
| `dhcp-disable` / `dhcp-enable` | Toggle DHCP service |

### Pros and Cons

| Feature | Custom Kea UI | NetBox Integration |
|---------|--------------|-------------------|
| Configuration editing | Full (write access) | IPAM-driven sync |
| Source of truth | Kea server | NetBox database |
| Customization | Unlimited | Plugin-scoped |
| Multi-server support | Manual setup | Via NetBox clusters |
| Audit trail | Application-level | Full NetBox changelog |
| Installation complexity | Low to medium | Medium (requires NetBox) |

## Choosing the Right DHCP Management Approach

The best DHCP management solution depends on your infrastructure scale and operational practices:

- **ISC Stork** is ideal for organizations already running Kea DHCP and BIND 9 who need a unified monitoring dashboard with minimal setup. It provides the best out-of-the-box experience for ISC product users.

- **Custom Kea frontends** suit teams that need direct DHCP configuration editing through a web UI and want lightweight, purpose-built interfaces without additional infrastructure dependencies.

- **NetBox Kea integration** is the best choice for organizations that already use NetBox for IPAM and want DHCP management to be driven by their IP address management database, ensuring consistency between planned and actual DHCP configurations.

## FAQ

### Can Stork manage ISC DHCP (dhcpd) servers?
No. Stork is designed specifically for Kea DHCP and BIND 9. It does not support the legacy ISC DHCP (dhcpd) server, which reached end-of-life in September 2022. For legacy ISC DHCP management, consider log-based monitoring or custom scripts.

### Does NetBox Kea integration support DHCPv6?
Yes. The netbox-kea plugin supports both IPv4 and IPv6 prefix synchronization. You can map NetBox IPv6 prefixes to Kea Dhcp6 subnet configurations, and the plugin will create DHCPv6 reservations for addresses tracked in NetBox.

### How does Stork handle Kea HA (High Availability) monitoring?
Stork monitors both members of a Kea HA pair independently through their respective Control Agents. It displays the HA state (hot-standby, load-balancing), synchronization status, and failover events. You can see which server is active and track lease synchronization between peers.

### Can I use Stork to edit Kea configurations?
Stork provides configuration validation and visualization but does not write configurations back to Kea servers. For configuration editing, use the Kea Control Agent API directly or a custom frontend that has write access.

### What database does Stork require?
Stork requires PostgreSQL (version 12 or later) for its own data storage. The database stores application settings, monitored server definitions, alert configurations, and collected statistics. It does not store DHCP leases or configurations — those remain on the Kea servers.

### Is there a Docker Compose setup for the full Kea + Stork stack?
Yes. ISC provides Docker images for both Kea DHCP and Stork. A complete stack includes Kea DHCP4, Kea DHCP6, Kea Control Agent, Stork server, Stork agent, and PostgreSQL database. The official ISC GitHub repository includes reference docker-compose files.

### How does NetBox handle DHCP lease data?
NetBox stores IP address assignments and reservations but does not track active DHCP leases in real time. Lease data remains on the Kea DHCP server. NetBox serves as the authoritative source for planned assignments, while Kea manages actual lease allocation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Management Dashboards: Stork vs Kea Web UI vs NetBox Integration",
  "description": "Compare ISC Stork, custom Kea Control Agent frontends, and NetBox Kea integration for web-based DHCP server management, monitoring, and configuration.",
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
