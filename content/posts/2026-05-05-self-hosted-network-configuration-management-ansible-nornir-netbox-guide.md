---
title: "Self-Hosted Network Configuration Management: Ansible vs Nornir vs NetBox 2026"
date: 2026-05-05
tags: ["network-automation", "configuration-management", "ansible", "nornir", "netbox", "network", "infrastructure", "comparison", "guide"]
draft: false
description: "Compare self-hosted network configuration management tools — Ansible, Nornir, and NetBox. Automate network device provisioning, track inventory, and manage configurations with Docker deployment configs."
---

Managing network device configurations across dozens or hundreds of switches, routers, and firewalls is a critical infrastructure challenge. Manual configuration leads to drift, security gaps, and downtime. Automated network configuration management tools solve this by codifying your network state, tracking inventory, and pushing changes consistently.

This guide compares three powerful self-hosted network automation tools: **Ansible**, **Nornir**, and **NetBox**. We cover deployment with Docker Compose, use cases, and help you build a network automation workflow.

## Overview of Network Configuration Management Tools

| Feature | Ansible | Nornir | NetBox |
|---------|---------|--------|--------|
| Type | Configuration management | Python automation framework | IPAM + DCIM + source of truth |
| Stars | 65,000+ | 2,500+ | 20,000+ |
| Language | Python + YAML | Python | Python + Django |
| Agent required | No (SSH/NETCONF) | No (Python libraries) | No (API-driven) |
| Network modules | 300+ network modules | NAPALM, Netmiko, Scrapli | REST API + GraphQL |
| State tracking | Yes (idempotent) | Manual (script-driven) | Yes (database-backed) |
| Docker support | Yes (ansible-runner) | Yes (Python image) | Yes (official compose) |
| Web UI | AWX/Tower (separate) | None | Built-in |

## Ansible — Agentless Configuration Management

**Ansible** (65,000+ stars) is the most widely-used open-source configuration management tool. Its agentless architecture, YAML-based playbooks, and 300+ network-specific modules make it the default choice for network automation.

### Key Features

- **Agentless** — Uses SSH, NETCONF, or REST API — no agents on network devices
- **Idempotent** — Running the same playbook twice produces the same result
- **Massive module library** — Built-in modules for Cisco, Juniper, Arista, F5, and more
- **Vault encryption** — Secure storage of credentials and secrets

### Docker Compose

```yaml
version: "3.8"
services:
  ansible:
    image: ansible/ansible-runner:latest
    working_dir: /runner
    volumes:
      - ./ansible-project:/runner:rw
      - ./ssh-keys:/runner/.ssh:ro
    environment:
      - ANSIBLE_HOST_KEY_CHECKING=False
      - ANSIBLE_CONFIG=/runner/ansible.cfg
    command: bash -c "ansible-playbook -i inventory.yml network-config.yml"
    restart: "no"
```

Example network playbook:

```yaml
---
- name: Configure network devices
  hosts: switches
  gather_facts: no
  connection: network_cli

  tasks:
    - name: Configure VLANs
      cisco.ios.ios_vlans:
        config:
          - vlan_id: 100
            name: production
          - vlan_id: 200
            name: management

    - name: Configure interface
      cisco.ios.ios_interfaces:
        config:
          - name: GigabitEthernet0/1
            description: Uplink to core
            enabled: true
```

```ini
# ansible.cfg
[defaults]
inventory = ./inventory.yml
host_key_checking = False
timeout = 30

[privilege_escalation]
become = False
```

## Nornir — Python-Native Network Automation

**Nornir** (2,500+ stars) is a Python-based automation framework designed specifically for network engineers who prefer code over YAML. It provides an inventory system, task runner, and plugin architecture that integrates with NAPALM, Netmiko, and Scrapli.

### Key Features

- **Python-first** — Write automation in Python, not YAML
- **Concurrent execution** — Run tasks across hundreds of devices simultaneously
- **Plugin ecosystem** — NAPALM, Netmiko, Scrapli integrations
- **Flexible inventory** — YAML, CSV, or custom inventory sources

### Docker Compose

```yaml
version: "3.8"
services:
  nornir:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./nornir-project:/app
    command: bash -c "pip install nornir nornir-napalm nornir-utils && python run_automation.py"
    environment:
      - NETMIKO_USERNAME=admin
      - NETMIKO_PASSWORD=your_password_here
    restart: "no"
```

Example Nornir automation script:

```python
from nornir import InitNornir
from nornir_napalm.plugins.tasks import napalm_configure

nr = InitNornir(config_file="config.yaml")

def configure_vlans(task):
    vlan_config = """
vlan 100
  name production
vlan 200
  name management
"""
    task.run(task=napalm_configure, configuration=vlan_config, dry_run=False)

results = nr.run(task=configure_vlans)
for host, result in results.items():
    print(f"{host}: {'OK' if not result[0].failed else 'FAILED'}")
```

## NetBox — IPAM and DCIM Source of Truth

**NetBox** (20,000+ stars) is the leading open-source IP address management (IPAM) and data center infrastructure management (DCIM) tool. While not a configuration pusher like Ansible, NetBox serves as the authoritative source of truth that feeds automation tools.

### Key Features

- **IP address management** — Track IP allocations, subnets, and VRFs
- **Device inventory** — Complete hardware and software inventory
- **Rack elevation diagrams** — Visual data center layout
- **REST API + GraphQL** — Programmatic access for automation integration
- **Custom fields** — Extend the data model for your organization

### Docker Compose (Official)

```yaml
version: "3.8"
services:
  netbox:
    image: netboxcommunity/netbox:latest
    depends_on:
      - netbox-postgres
      - netbox-redis
      - netbox-redis-cache
    ports:
      - "8000:8080"
    environment:
      - SUPERUSER_EMAIL=admin@example.com
      - SUPERUSER_PASSWORD=changeme
      - ALLOWED_HOST=netbox.example.com
    volumes:
      - netbox-media-files:/opt/netbox/netbox/media
      - netbox-reports:/etc/netbox/reports
      - netbox-scripts:/etc/netbox/scripts

  netbox-postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=netbox
      - POSTGRES_PASSWORD=netbox
      - POSTGRES_DB=netbox
    volumes:
      - netbox-postgres-data:/var/lib/postgresql/data

  netbox-redis:
    image: redis:7-alpine
    command: redis-server --requirepass changeme

  netbox-redis-cache:
    image: redis:7-alpine
    command: redis-server

volumes:
  netbox-media-files:
  netbox-reports:
  netbox-scripts:
  netbox-postgres-data:
```

## Comparison: Building a Network Automation Workflow

A complete network automation workflow typically combines these tools:

1. **NetBox** as the source of truth — inventory, IP allocations, device relationships
2. **Ansible** for configuration pushes — idempotent, agentless playbook execution
3. **Nornir** for custom automation — Python scripts for complex, conditional workflows

### Use Ansible when:
- You need to push configurations to network devices at scale
- You want idempotent, repeatable configuration management
- Your team is familiar with YAML and playbooks

### Use Nornir when:
- You need complex conditional logic in your automation
- Your team prefers Python over YAML
- You are building custom network tools or integrations

### Use NetBox when:
- You need a centralized source of truth for network inventory
- You need IP address management and subnet tracking
- You want visual data center documentation

## Why Automate Network Configuration?

Manual network configuration does not scale. As your infrastructure grows, configuration drift becomes inevitable — leading to security vulnerabilities, service outages, and troubleshooting nightmares. Automated network configuration management ensures consistency, provides audit trails, and enables rapid disaster recovery.

For **network topology mapping**, see our [network topology guide](../2026-05-02-self-hosted-network-topology-mapping-netbox-librenms-guide/). For **DNS management**, check our [DNS management comparison](../self-hosted-dns-management-web-uis-powerdns-admin-technitium-bind-webmin-guide-2026/). For **infrastructure drift detection**, our [drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-guide/) covers automated configuration auditing.

## FAQ

### Can Ansible configure network devices without agents?
Yes. Ansible uses SSH, NETCONF, or vendor-specific APIs (like Cisco REST API) to manage network devices. No agents need to be installed on switches or routers.

### Is NetBox only for large data centers?
No. NetBox is valuable for any environment with multiple network devices, even small home labs. It tracks IP addresses, device relationships, and cable connections — useful at any scale.

### Can Nornir replace Ansible for network automation?
Nornir and Ansible serve different purposes. Ansible is better for declarative configuration pushes. Nornir excels at custom Python automation, complex conditional workflows, and integrations with other Python libraries.

### How do I back up network device configurations?
Ansible can collect running configs from devices and store them. NetBox tracks the intended state. Together, they provide both the desired and actual configuration for comparison.

### Does NetBox support multi-tenancy?
Yes. NetBox has a built-in tenancy model with tenants, tenant groups, and assignment of IP addresses, devices, and circuits to specific tenants.

### How do I integrate NetBox with Ansible?
Use the NetBox Ansible collection (netbox.netbox) to pull inventory data from NetBox and use it as dynamic inventory for playbooks. This ensures your automation always uses the current source of truth.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Configuration Management: Ansible vs Nornir vs NetBox 2026",
  "description": "Compare self-hosted network configuration management tools — Ansible, Nornir, and NetBox. Automate network device provisioning, track inventory, and manage configurations with Docker deployment configs.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
