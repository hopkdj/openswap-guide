---
title: "Oxidized vs Netmiko vs NAPALM: Network Configuration Backup & Automation 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "networking", "automation", "backup"]
draft: false
description: "Compare Oxidized, Netmiko, and NAPALM for self-hosted network device configuration backup, change tracking, and automation. Includes Docker Compose setups, real-world configs, and a decision matrix."
---

Managing network device configurations manually is a recipe for disaster. When a router goes down at 2 AM, the last thing you want is guessing what changed since last week. Self-hosted network configuration backup and automation tools solve this by pulling configs on schedule, tracking diffs, and enabling automated changes across multi-vendor environments.

In this guide, we compare three open-source approaches to network configuration management: **Oxidized** (a purpose-built backup tool), **Netmiko** (a Python SSH library for custom scripts), and **NAPALM** (a vendor-agnostic automation abstraction layer). Each represents a different philosophy — from "set it and forget it" to "build it yourself" — and the right choice depends on your team's size, network com[plex](https://www.plex.tv/)ity, and automation maturity.

## Why Self-Hosted Network Configuration Backup Matters

Network devices — routers, switches, firewalls, load balancers — are the backbone of any infrastructure. Yet most organizations still manage their configs through a mix of manual SSH sessions, scattered spreadsheets, and tribal knowledge. Here is why that approach fails:

- **No audit trail**: Without version-controlled configs, you cannot determine who changed what or when.
- **Slow disaster recovery**: Rebuilding a failed switch from memory takes hours instead of minutes.
- **Compliance violations**: Audits require proof of configuration management and change tracking.
- **Vendor lock-in**: Each vendor (Cisco, Juniper, Arista, MikroTik) has different config formats and management interfaces.
- **Configuration drift**: Without automated backups, slow drift between intended and actual state accumulates unnoticed.

Self-hosted tools eliminate these risks by running entirely within your infrastructure — no cloud dependency, no vendor telemetry, no data leaving your network. For organizations managing sensitive infrastructure, this is non-negotiable.

## Tool Overview at a Glance

| Feature | Oxidized | Netmiko | NAPALM |
|---|---|---|---|
| **GitHub Stars** | 3,344 | 4,144 | 2,447 |
| **Language** | Ruby | Python | Python |
| **License** | Apache-2.0 | MIT | Apache-2.0 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Primary Use** | Automated config backup | SSH connectivity library | Network automation abstraction |
| **Supported Vendors** | 150+ | 200+ | 30+ |
| **Built-in Web UI** | Yes | No | No |
| **Git Integration** | Native (output hook) | Manual (via script) | Manual (via script) |
| **Diff Tracking** | Yes (built-in) | Manual (via script) | Via external tools |
| **Scheduled Pulls** | Yes (built-in) | Manual (via cron/systemd) | Manual (via script) |
| **Config Templates** | No | No | Yes (Jinja2) |
| **Config Deployment** | No (read-only) | Yes | Yes |
| **Learning Curve** | Low | Medium | Medium-High |
| **Best For** | Backup-first teams | Python developers | Multi-vendor automation |

Oxidized positions itself explicitly as a RANCID replacement — it focuses entirely on pulling, storing, and versioning device configurations. Netmiko is a lower-level SSH library that simplifies multi-vendor connectivity, giving you building blocks to create custom solutions. NAPALM sits above Netmiko, providing a unified API across vendors so your code works the same way whether you are talking to Cisco IOS, Juniper Junos, or Arista EOS.

## Oxidized: The Set-It-and-Forget-It Backup Tool

Oxidized is the most opinionated of the three tools — it has one job (backup network configs) and does it exceptionally well. It runs as a daemon, polls your device inventory on a schedule, SSHes into each device, pulls the running configuration, and stores it in a Git repository.

### Key Features

- **150+ supported OS types**: Cisco IOS/NX-OS, Juniper Junos, Arista EOS, MikroTik RouterOS, Palo Alto PAN-OS, FortiOS, Ubiquiti EdgeOS, HP Comware, Dell OS10, and dozens more.
- **Built-in web UI**: Browse configs, view diffs, and search across your entire fleet from a browser.
- **Git output**: Every config change creates a Git commit with full history.
- **HTTP API**: RESTful endpoints for inventory management and on-demand pulls.
- **Group support**: Apply different credentials, commands, and post-processing[docker](https://www.docker.com/)evice group.

### Docker Compose Setup

Here is a production-ready Docker Compose configuration that runs Oxidized with persistent config storage and a local Git repository:

```yaml
services:
  oxidized:
    image: oxidized/oxidized:latest
    container_name: oxidized
    restart: unless-stopped
    ports:
      - "8080:8888"
    volumes:
      - ./config:/home/oxidized/.config/oxidized
      - ./output:/home/oxidized/output
    environment:
      - CONFIG_RELOAD_INTERVAL=300
    networks:
      - monitoring

  # Optional: Gitea for Git hosting of backed-up configs
  gitea:
    image: gitea/gitea:latest
    container_name: gitea
    restart: unless-stopped
    ports:
      - "3000:3000"
      - "2222:22"
    volumes:
      - gitea-data:/data
      - gitea-config:/etc/gitea
    networks:
      - monitoring

volumes:
  gitea-data:
  gitea-config:

networks:
  monitoring:
    driver: bridge
```

### Oxidized Configuration

The core configuration file (`~/.config/oxidized/config`) defines how Oxidized discovers devices, authenticates, and stores configs:

```yaml
---
username: admin
password: "${DEVICE_PASSWORD}"
model: junos
resolve_dns: true
interval: 3600
use_syslog: false
debug: false
threads: 30
timeout: 20
retries: 3
prompt: !ruby/regexp /^([\w.@-]+[#>]\s?)$/
rest: 0.0.0.0:8888
next_adds_job: false
vars: {}
groups: {}
models: {}
pid: /home/oxidized/.config/oxidized/pid

input:
  default: ssh, telnet
  debug: false
  ssh:
    secure: false

output:
  default: git
  git:
    user: Oxidized
    email: oxidized@example.com
    repo: "/home/oxidized/output/configs.git"

source:
  default: csv
  csv:
    file: /home/oxidized/.config/oxidized/router.db
    delimiter: !ruby/regexp /:/
    map:
      name: 0
      ip: 1
      model: 2
      username: 3
      password: 4
      group: 5

model_map:
  cisco: ios
  juniper: junos
  arista: eos
  mikrotik: routeros
  fortinet: fortios
```

The `router.db` file is a simple CSV inventory:

```
core-rtr-01:10.0.1.1:ios:admin:${PASS}:core
dist-sw-01:10.0.1.2:cisco:admin:${PASS}:distribution
fw-main-01:10.0.1.3:fortios:admin:${PASS}:firewall
```

### Running and Verifying

Once the containers are up, Oxidized starts polling immediately. Check the web UI at `http://localhost:8080` to see device statuses, browse configurations, and review diffs between revisions. You can also trigger an on-demand pull via the API:

```bash
curl -X POST http://localhost:8080/node/fetch/core-rtr-01
```

The Git repository at `./output/configs.git` contains every revision. You can push this to a remote like [Gitea or Forgejo](../gitea-vs-forgejo-vs-gitlab-ce-self-hosted-git-forge/) for team access and additional backup.

## Netmiko: The Build-It-Yourself SSH Library

Netmiko takes a fundamentally different approach. Instead of being a ready-to-use tool, it is a Python library that simplifies SSH connections to network devices. You write scripts — Oxidized tells you what to do, Netmiko gives you the tools to build whatever you need.

### Key Features

- **200+ platform support**: The largest vendor list of any tool in this comparison.
- **Command execution**: Send config commands, show commands, and file transfers over SSH.
- **Session management**: Automatic prompt detection, error handling, and session state tracking.
- **TextFSM/ntc-templates**: Parse unstructured CLI output into structured data.
- **Proxy jump support**: SSH through bastion hosts to reach isolated devices.

### Installation

```bash
pip install netmiko ntc-templates
```

### Custom Backup Script with Netmiko

Here is a complete backup script that connects to multiple devices, pulls configs, and stores them with Git versioning:

```python
#!/usr/bin/env python3
"""Network config backup using Netmiko."""

import os
import datetime
from netmiko import ConnectHandler
from git import Repo

# Device inventory
DEVICES = [
    {
        "device_type": "cisco_ios",
        "host": "10.0.1.1",
        "username": "admin",
        "password": os.environ["DEVICE_PASSWORD"],
        "secret": os.environ["ENABLE_PASSWORD"],
    },
    {
        "device_type": "juniper_junos",
        "host": "10.0.2.1",
        "username": "admin",
        "password": os.environ["DEVICE_PASSWORD"],
    },
    {
        "device_type": "arista_eos",
        "host": "10.0.3.1",
        "username": "admin",
        "password": os.environ["DEVICE_PASSWORD"],
    },
]

BACKUP_DIR = "/opt/network-backups"

def backup_device(device):
    """Connect to a device and save its running config."""
    hostname = device["host"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")

    try:
        with ConnectHandler(**device) as net_connect:
            if device["device_type"] == "cisco_ios":
                net_connect.enable()
                output = net_connect.send_command("show running-config")
            elif device["device_type"] == "juniper_junos":
                output = net_connect.send_command("show configuration | display set")
            elif device["device_type"] == "arista_eos":
                output = net_connect.send_command("show running-config")
            else:
                output = net_connect.send_command("show running-config")

            filename = os.path.join(BACKUP_DIR, f"{hostname}_{timestamp}.cfg")
            with open(filename, "w") as f:
                f.write(output)
            print(f"[OK] {hostname}: backed up to {filename}")
            return filename

    except Exception as e:
        print(f"[FAIL] {hostname}: {e}")
        return None

def commit_to_git(filepath):
    """Commit new config to Git repository."""
    repo = Repo(BACKUP_DIR)
    repo.index.add([os.path.basename(filepath)])
    repo.index.commit(f"Auto-backup: {os.path.basename(filepath)}")

if __name__ == "__main__":
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for device in DEVICES:
        result = backup_device(device)
        if result:
            commit_to_git(result)
```

Schedule this with cron for automated backups:

```bash
# Run every 6 hours
0 */6 * * * /usr/bin/python3 /opt/netmiko-backup/backup.py >> /var/log/net-backup.log 2>&1
```

### When to Choose Netmiko

Netmiko shines when you need fine-grained control over device interactions. It is ideal for teams with Python developers who want to build custom workflows: config validation before deployment, automated testing of changes, or integration with existing ITSM platforms. However, it requires significantly more development effort than Oxidized.

## NAPALM: Vendor-Agnostic Network Automation

NAPALM (Network Automation and Programmability Abstraction Layer with Multivendor support) provides a unified API across network vendors. Where Netmiko gives you raw CLI access, NAPALM gives you structured methods like `get_interfaces()`, `get_bgp_neighbors()`, and `load_merge_candidate()` that work identically across Cisco, Juniper, Arista, and others.

### Key Features

- **Unified API**: Same method calls regardless of underlying vendor OS.
- **Config management**: Load, merge, compare, and commit configurations programmatically.
- **Validation framework**: `napalm-validate` checks device state against YAML-defined expectations.
- **Structured data**: Returns Python dictionaries, not raw text — no regex parsing needed.
- **Proxy support**: SSH through jump hosts for segmented networks.

### Installation

```bash
pip install napalm
```

### NAPALM Config Backup Script

```python
#!/usr/bin/env python3
"""Network config backup and validation using NAPALM."""

import os
import datetime
import napalm
from git import Repo

DRIVER_MAP = {
    "ios": "ios",
    "nxos": "nxos_ssh",
    "eos": "eos",
    "junos": "junos",
}

DEVICES = [
    {"hostname": "10.0.1.1", "vendor": "ios", "username": "admin"},
    {"hostname": "10.0.2.1", "vendor": "junos", "username": "admin"},
    {"hostname": "10.0.3.1", "vendor": "eos", "username": "admin"},
]

BACKUP_DIR = "/opt/napalm-backups"

def backup_device(device_info):
    """Pull running config using NAPALM's unified API."""
    hostname = device_info["hostname"]
    vendor = device_info["vendor"]
    driver_name = DRIVER_MAP[vendor]
    password = os.environ["DEVICE_PASSWORD"]

    driver = napalm.get_network_driver(driver_name)
    device = driver(
        hostname=hostname,
        username=device_info["username"],
        password=password,
    )

    try:
        device.open()
        config = device.get_config(retrieve="running")
        running_config = config["running"]

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = os.path.join(BACKUP_DIR, f"{hostname}_{timestamp}.cfg")

        with open(filename, "w") as f:
            f.write(running_config)

        print(f"[OK] {hostname}: backed up ({len(running_config)} bytes)")

        # Validate device state
        facts = device.get_facts()
        print(f"  Hostname: {facts['hostname']}, Model: {facts['model']}")
        print(f"  Uptime: {facts['uptime']}s, Interfaces: {facts['interface_list']}")

        device.close()
        return filename

    except Exception as e:
        print(f"[FAIL] {hostname}: {e}")
        return None

if __name__ == "__main__":
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for device in DEVICES:
        backup_device(device)
```

### NAPALM Validation Example

Beyond backup, NAPALM can validate that your network matches your intended state:

```yaml
# validate.yml
---
- get_bgp_neighbors:
    requires:
      - peer: 10.0.0.1
        is_enabled: true
        is_up: true
- get_interfaces_ip:
    requires:
      - eth0:
          ipv4:
            - 10.0.1.1
```

```bash
napalm-validate --validate-file validate.yml --vendor ios --user admin 10.0.1.1
```

### When to Choose NAPALM

NAPALM is the right choice when you need to do more than just backup configs. If your team needs to programmatically deploy changes, validate network state, or build automation that works across Cisco and Juniper without rewriting code, NAPALM's abstraction layer saves significant development time. The trade-off is a smaller supported vendor list — 30+ compared to Netmiko's 200+.

## Decision Matrix: Which Tool to Choose?

| Scenario | Recommended Tool | Why |
|---|---|---|
| "I just need config backups ASAP" | **Oxidized** | Zero-code setup, runs out of the box with a config file and inventory CSV |
| "I have 200+ devices, mixed vendors" | **Oxidized** | Broadest vendor support for backup-only use case, web UI for quick browsing |
| "I need to deploy config changes programmatically" | **NAPALM** | Unified API with merge/replace/commit workflows and pre-commit validation |
| "I want to build custom automation workflows" | **Netmiko** | Maximum flexibility — SSH to any device, run any command, parse any output |
| "My team knows Python well" | **Netmiko or NAPALM** | Both are Python-first; Netmiko for low-level, NAPALM for high-level abstraction |
| "I need structured data, not CLI text" | **NAPALM** | Returns typed Python dictionaries — no regex or TextFSM needed |
| "I want Git history and diffs for free" | **Oxidized** | Native Git output with built-in diff viewer in the web UI |

## Combining Tools in Practice

Many production environments use multiple tools together:

- **Oxidized + NAPALM**: Oxidized handles daily config backups and Git versioning; NAPALM scripts run weekly validation checks and deploy approved changes.
- **Netmiko + Oxidized**: Oxidized backs up all devices on a schedule; custom Netmiko scripts handle emergency config pushes when the backup reveals drift.
- **NAPALM + Ansible**: For teams that already use [Ansible for configuration management](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/), NAPALM provides the network device driver layer while Ansible orchestrates the broader workflow.

A typical production architecture might look like this:

```
[Oxidized] ──┐
             ├──> [Git Repo] ──> [Gitea/Forgejo] (config history + team access)
[NAPALM] ────┘
     │
     ├──> [Validation] (napalm-validate against expected state)
     │
[Ansible] ──> [Orchestration] (schedule NAPALM runs, alert on failures)
```

For teams that also manage firewall rules and routing policies, this integrates well with a broader network strategy. See our [pfSense vs OPNsense vs IPFire guide](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide-2026/) for firewall appliance selection, and pair it with Oxidized to ensure every firewall change is backed up automatically.

## FAQ

### What is the difference between Oxidized and RANCID?

Oxidized was explicitly designed as a RANCID replacement. While RANCID uses Expect scripts and CVS/SVN for version control, Oxidized uses Ruby with built-in Git support, a modern HTTP API, and a web interface. Oxidized also supports significantly more device types (150+ vs RANCID's ~30) and handles multi-vendor environments more gracefully.

### Can Netmiko be used for configuration changes, not just backups?

Yes. Netmiko's `send_config_set()` method sends configuration commands to devices and handles the enter/exit config mode transitions automatically. However, unlike NAPALM, Netmiko does not provide a dry-run or diff mechanism — you are sending raw commands directly to the device. For safe config changes, combine Netmiko with a pre-change backup and manual diff verification.

### Does NAPALM support Windows or non-network devices?

No. NAPALM is specifically designed for network operating systems. It supports Cisco IOS/NX-OS, Juniper Junos, Arista EOS, F5 BIG-IP, Cisco ASA, Huawei VRP, and similar network platforms. It does not support general-purpose servers, Windows hosts, or cloud APIs.

### How does Oxidized handle devices that require enable mode or privileged access?

Oxidized supports per-device and per-group variables in its configuration. You can set `enable: true` for Cisco devices that require privileged EXEC mode, or specify custom `post_login` and `pre_logout` commands in the config for devices that need special handling:

```yaml
groups:
  cisco:
    username: admin
    vars:
      enable: true
      auth_methods: ["publickey", "passw[kubernetes](https://kubernetes.io/)
### Is it possible to run Oxidized in a Kubernetes cluster?

Yes. Oxidized can be containerized and deployed as a Kubernetes Deployment. You need persistent volumes for the config directory and Git output, and a Service to expose the web UI. For production, consider running it as a CronJob if you only need periodic pulls rather than a continuous daemon.

### Which tool works best with MikroTik RouterOS devices?

Both Oxidized and Netmiko support MikroTik RouterOS. Oxidized has a dedicated `routeros` model that handles the CLI properly. Netmiko includes `mikrotik_routeros` as a device type. NAPALM does not currently support RouterOS natively, though community drivers exist.

### Can I use these tools to manage cloud networking (AWS VPC, Azure NSG)?

Not directly. These tools are designed for physical and virtual network devices accessible via SSH or NETCONF. For cloud infrastructure, consider Terraform for infrastructure-as-code and tools like `aws-cli` or Azure CLI for direct API interaction. However, NAPALM's Salt integration (`napalm-salt`) can bridge on-premises network automation with broader infrastructure management.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Oxidized vs Netmiko vs NAPALM: Network Configuration Backup & Automation 2026",
  "description": "Compare Oxidized, Netmiko, and NAPALM for self-hosted network device configuration backup, change tracking, and automation. Includes Docker Compose setups and real-world configs.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
