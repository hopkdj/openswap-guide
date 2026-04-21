---
title: "Ansible vs SaltStack vs Puppet: Best Configuration Management 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "automation", "infrastructure"]
draft: false
description: "Compare the top open-source configuration management tools in 2026. Practical guide to Ansible, SaltStack, and Puppet for self-hosted infrastructure automation."
---

Managing a growing fleet of self-hosted services by hand quickly becomes unsustainable. Whether you're running a homelab with a dozen containers or a production cluster with hundreds of nodes, **configuration management** is the discipline that keeps everything consistent, reproducible, and recoverable.

In this guide, we compare the three most widely used open-source configuration management systems — **Ansible**, **SaltStack** (Salt), and **Puppet** — and show you exactly how to set each one up, write your first automation, and decide which tool fits your infrastructure.

## Why Self-Hosted Configuration Management Matters

When you self-host, you own the entire stack. That freedom comes with responsibility: every package update, firewall rule, TLS certificate renewal, and service restart is your problem. Without configuration management, you'll inevitably encounter:

- **Configuration drift** — servers that started identical slowly diverge as manual tweaks accumulate
- **Disaster recovery pain** — rebuilding a failed node from memory or scattered notes takes hours instead of minutes
- **Inconsistent environments** — development, staging, and production slowly drift apart, causing "it works on my machine" bugs
- **Security gaps** — missing a critical patch or misconfigured permission on even one node compromises the entire infrastructure

Configuration management tools solve these problems by treating your infrastructure state as **declarative code**. You define the desired end state, and the tool ensures every node matches it — automatically, repeatedly, and idempotently.

## What Is Configuration Management?

At its core, configuration management does four things:

1. **Provisioning** — install packages, create users, set up directories
2. **Configuration** — write config files, manage services, set environment variables
3. **Orchestration** — run tasks in a specific order across multiple nodes
4. **Enforcement** — continuously verify that the actual state matches the desired state

The three tools we'll compare approach these goals differently, using distinct architectures, languages, and communication patterns.

## Ansible: Agentless Simplicity

### Architecture

Ansible uses an **agentless, push-based** architecture. It connects to managed nodes over SSH (Linux) or WinRM (Windows), uploads small Python modules, executes them, and collects results. No daemon runs on your target servers.

```
┌──────────────┐     SSH + Python modules     ┌──────────────┐
│  Ansible     │ ──────────────────────────►  │  Node A      │
│  Controller  │ ──────────────────────────►  │  Node B      │
│  (your laptop│ ──────────────────────────►  │  Node C      │
│   or server) │                              └──────────────┘
└──────────────┘
```

**Key characteristics:**
- **Language**: YAML playbooks — human-readable, no programming knowledge required
- **Communication**: SSH (port 22) — uses existing infrastructure
- **Execution model**: Imperative with idempotent modules
- **Agent required**: No
- **Learning curve**: Low — the lowest of all three tools

### Installation

The control node needs Python 3.10+. Managed nodes need Python 3 (pre-installed on most distributions) and an SSH server.

```bash
# Install Ansible on the control node
pip install ansible

# Verify installation
ansible --version
```

### Quick Start

Create an inventory file listing your managed hosts:

```ini
# inventory.ini
[webservers]
web1.example.com ansible_user=deploy
web2.example.com ansible_user=deploy

[dbservers]
db1.example.com ansible_user=deploy
```

Write your first playbook to install and configure Nginx:

```yaml
# site.yml
---
- name: Configure web servers
  hosts: webservers
  become: true

  tasks:
    - name: Install Nginx
      apt:
        name: nginx
        state: present
        update_cache: true

    - name: Deploy Nginx configuration
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: Restart Nginx

    - name: Enable and start Nginx
      systemd:
        name: nginx
        enabled: true
        state: started

  handlers:
    - name: Restart Nginx
      systemd:
        name: nginx
        state: restarted
```

The accompanying Jinja2 template (`templates/nginx.conf.j2`):

```nginx
worker_processes {{ ansible_processor_vcpus }};

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    server {
        listen 80;
        server_name {{ inventory_hostname }};

        location / {
            proxy_pass http://127.0.0.1:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

Run the playbook:

```bash
ansible-playbook -i inventory.ini site.yml --check  # Dry run first
ansible-playbook -i inventory.ini site.yml          # Apply changes
```

### Ansible With [docker](https://www.docker.com/) (Dockerized Control Node)

If you prefer not to install Ansible directly on your workstation:

```yaml
# docker-compose.yml
version: "3.9"
services:
  ansible:
    image: cyberark/ansible
    volumes:
      - ./playbooks:/playbooks
      - ~/.ssh:/root/.ssh:ro
      - ./inventory:/etc/ansible/hosts
    working_dir: /playbooks
    entrypoint: ["ansible-playbook", "-i", "/etc/ansible/hosts"]
    command: ["site.yml"]
```

### When Ansible Shines

- **Quick deployments** — no agent setup means you can manage a server in minutes
- **Small to medium fleets** — excellent for 5–200 nodes
- **Ad-hoc tasks** — run one-off commands across your fleet with `ansible all -m shell -a "uptime"`
- **Mixed environments** — seamlessly manages Linux, Windows, network devices, and cloud APIs
- **Beginner-friendly** — YAML is easy to read and write

### Ansible Limitations

- **Speed** — SSH connections serialize execution; 500+ nodes can take a long time
- **Push-only** — no built-in continuous enforcement; you must schedule playbook runs via cron
- **No native state tracking** — unlike Puppet, Ansible doesn't maintain a central record of node state
- **Python dependency** — managed nodes need Python installed

## SaltStack (Salt): Speed at Scale

### Architecture

Salt uses a **master-minion architecture** with a high-speed ZeroMQ or RAET message bus. The master pushes commands to minions, which execute and report back in parallel. Salt also supports **agentless SSH mode** (similar to Ansible) for bootstrapping.

```
┌──────────────┐     ZeroMQ/RAET (fast)      ┌──────────────┐
│   Salt       │ ◄─────────────────────────►  │  Minion A    │
│   Master     │ ◄─────────────────────────►  │  Minion B    │
│              │ ◄─────────────────────────►  │  Minion C    │
└──────────────┘                               └──────────────┘
```

**Key characteristics:**
- **Language**: YAML + Jinja2 for states; Python for custom modules
- **Communication**: ZeroMQ (encrypted AES) on ports 4505–4506
- **Execution model**: Declarative states with reactive event system
- **Agent required**: Yes (minion), but SSH mode is agentless
- **Learning curve**: Medium — more com[plex](https://www.plex.tv/) than Ansible, easier than Puppet

### Installation

```bash
# On the master node (Debian/Ubuntu)
apt install salt-master salt-minion

# On minion nodes
apt install salt-minion

# Configure minions to point to the master
echo "master: salt-master.example.com" > /etc/salt/minion
systemctl enable --now salt-minion

# Accept minion keys on the master
salt-key -A
```

### Docker Setup

```yaml
# docker-compose.yml
version: "3.9"
services:
  salt-master:
    image: saltstack/salt:latest
    command: salt-master -l info
    ports:
      - "4505:4505"
      - "4506:4506"
    volumes:
      - ./salt/etc:/etc/salt
      - ./srv/salt:/srv/salt
      - salt-pki:/etc/salt/pki
    networks:
      salt-net:
        aliases:
          - salt

  salt-minion:
    image: saltstack/salt:latest
    command: salt-minion -l info
    depends_on:
      - salt-master
    environment:
      - SALT_MASTER=salt
    volumes:
      - ./salt/etc/minion:/etc/salt/minion
      - salt-pki:/etc/salt/pki
    networks:
      - salt-net

volumes:
  salt-pki:

networks:
  salt-net:
    driver: bridge
```

### Quick Start

Write a state file to install and configure Nginx:

```yaml
# /srv/salt/nginx/init.sls
nginx-pkg:
  pkg.installed:
    - name: nginx

nginx-conf:
  file.managed:
    - name: /etc/nginx/nginx.conf
    - source: salt://nginx/files/nginx.conf.j2
    - template: jinja
    - require:
      - pkg: nginx-pkg
    - watch_in:
      - service: nginx-service

nginx-service:
  service.running:
    - name: nginx
    - enable: True
    - watch:
      - file: nginx-conf
```

Apply the state to all web server minions:

```bash
salt 'web*' state.apply nginx       # Push to matching minions
salt 'web*' state.apply nginx test=true  # Dry run
```

### Salt's Event System

Salt's standout feature is its **reactive event bus**. Minions fire events for state changes, and you can write reactors that respond automatically:

```yaml
# /srv/salt/reactors/nginx-restart.sls
restart_nginx:
  local.service.restart:
    - tgt: {{ data['id'] }}
    - args:
      - name: nginx
```

Register the reactor on the master:

```yaml
# /etc/salt/master.d/reactor.conf
reactor:
  - 'salt/minion/*/grains_changed':
    - /srv/salt/reactors/nginx-restart.sls
```

### When Salt Shines

- **Large fleets** — ZeroMQ parallel execution handles 10,000+ nodes efficiently
- **Real-time enforcement** — continuous state checking with fast remediation
- **Event-driven automation** — react to infrastructure changes automatically
- **Remote execution** — `salt '*' cmd.run 'apt update && apt upgrade -y'` runs across your fleet in seconds
- **Flexible topology** — supports master-minion, masterless, and SSH modes

### Salt Limitations

- **Infrastructure overhead** — requires a master server and open ports
- **Key management** — minion keys must be accepted before communication
- **Complexity** — the event system and reactor framework add cognitive overhead
- **Smaller community** — fewer third-party modules and tutorials compared to Ansible

## Puppet: Enterprise-Grade Reliability

### Architecture

Puppet uses a **master-agent (or server-agent) architecture** with a custom DSL. Agents check in with the master on a configurable interval (default: 30 minutes), receive a compiled catalog, and apply it locally. Puppet Enterprise adds a web console, RBAC, and reporting.

```
┌──────────────┐     HTTPS (8140) polling    ┌──────────────┐
│   Puppet     │ ◄─────────────────────────►  │  Agent A     │
│   Server     │ ◄─────────────────────────►  │  Agent B     │
│              │ ◄─────────────────────────►  │  Agent C     │
└──────────────┘                               └──────────────┘
        ▲
        │ 30-minute check-in cycle
```

**Key characteristics:**
- **Language**: Puppet DSL (domain-specific language) — purpose-built for configuration
- **Communication**: HTTPS (port 8140) with certificate-based authentication
- **Execution model**: Declarative — define the desired state, Puppet figures out how to get there
- **Agent required**: Yes (puppet-agent package)
- **Learning curve**: Steep — the Puppet DSL and catalog compilation model require dedicated learning

### Installation

```bash
# On the Puppet server
apt install puppetserver
systemctl enable --now puppetserver

# On agent nodes
apt install puppet-agent

# Configure agent to find the server
echo "server = puppet.example.com" >> /etc/puppetlabs/puppet/puppet.conf

# Request certificate from agent
/opt/puppetlabs/bin/puppet agent --test

# Sign the certificate on the server
/opt/puppetlabs/bin/puppetserver ca sign --all
```

### Quick Start

Write a Puppet manifest:

```puppet
# /etc/puppetlabs/code/environments/production/manifests/site.pp

# Base configuration for all nodes
node default {
  # Ensure NTP is installed and running
  package { 'ntp':
    ensure => present,
  }

  service { 'ntp':
    ensure => running,
    enable => true,
    require => Package['ntp'],
  }
}

# Web server nodes
node 'web1.example.com', 'web2.example.com' {
  include nginx
}
```

Define the Nginx class:

```puppet
# /etc/puppetlabs/code/environments/production/modules/nginx/manifests/init.pp
class nginx {
  package { 'nginx':
    ensure => present,
  }

  file { '/etc/nginx/nginx.conf':
    ensure  => file,
    source  => 'puppet:///modules/nginx/nginx.conf',
    owner   => 'root',
    group   => 'root',
    mode    => '0644',
    notify  => Service['nginx'],
    require => Package['nginx'],
  }

  service { 'nginx':
    ensure => running,
    enable => true,
  }
}
```

### Puppet With Docker

```yaml
# docker-compose.yml
version: "3.9"
services:
  puppetserver:
    image: puppet/puppetserver:latest
    hostname: puppet
    ports:
      - "8140:8140"
    volumes:
      - puppet-code:/etc/puppetlabs/code
      - puppet-ssl:/etc/puppetlabs/puppet/ssl
    environment:
      - PUPPETSERVER_HOSTNAME=puppet
      - DNS_ALT_NAMES=puppet,puppet.example.com

  puppet-agent:
    image: puppet/puppet-agent:latest
    hostname: agent1
    depends_on:
      - puppetserver
    environment:
      - PUPPET_SERVER=puppet
      - PUPPET_CA_SERVER=puppet
    volumes:
      - puppet-ssl:/etc/puppetlabs/puppet/ssl

volumes:
  puppet-code:
  puppet-ssl:
```

### When Puppet Shines

- **Compliance and auditing** — detailed reporting on every node's state, ideal for regulated environments
- **Long-running infrastructure** — agents continuously enforce desired state without manual intervention
- **Complex dependency graphs** — the resource dependency model handles intricate relationships elegantly
- **Large enterprises** — Puppet Enterprise provides RBAC, code management pipelines, and orchestration
- **Mature ecosystem** — Puppet Forge offers 7,000+ community modules

### Puppet Limitations

- **Steep learning curve** — the Puppet DSL is unlike any general-purpose language
- **Heavy infrastructure** — the Puppet server is resource-intensive (4 GB+ RAM recommended)
- **Slower iterations** — 30-minute check-in cycles mean slower feedback than push-based tools
- **Certificate management** — SSL certificates add operational complexity

## Comparison Table

| Feature | Ansible | SaltStack | Puppet |
|---|---|---|---|
| **Architecture** | Agentless, push | Master-minion or SSH | Master-agent |
| **Language** | YAML | YAML + Jinja2 | Puppet DSL |
| **Communication** | SSH (port 22) | ZeroMQ (4505-4506) | HTTPS (port 8140) |
| **Learning Curve** | Low | Medium | High |
| **Execution Speed** | Moderate (serial) | Fast (parallel) | Moderate (polling) |
| **Max Practical Nodes** | ~500 | 10,000+ | 5,000+ |
| **Continuous Enforcement** | No (use cron) | Yes (built-in) | Yes (30-min polling) |
| **Windows Support** | Yes (WinRM) | Yes | Yes |
| **Network Device Support** | Excellent | Good | Limited |
| **Community Modules** | 7,000+ (Ansible Galaxy) | 2,000+ | 7,000+ (Puppet Forge) |
| **Enterprise Option** | Ansible Tower/AWX | SaltStack Enterprise (VMware) | Puppet Enterprise |
| **Best For** | Small/medium fleets, quick setup | Large fleets, real-time ops | Compliance, enterprise IT |

## Decision Framework

### Choose Ansible if:

- You want to start managing servers **today** with minimal setup
- Your fleet is under 200 nodes
- You manage **network devices** (routers, switches, firewalls) alongside servers
- Your team prefers **human-readable YAML** over learning a DSL
- You need **ad-hoc remote execution** alongside configuration management

### Choose SaltStack if:

- You manage **500+ nodes** and need parallel execution speed
- You want **event-driven automation** — react to infrastructure changes in real time
- You need a hybrid approach: agent-based for speed, SSH for bootstrapping
- You want **remote execution** as a first-class feature, not an afterthought
- You're building a **self-hosted cloud** or container platform

### Choose Puppet if:

- **Compliance and auditing** are your top priorities
- You need **continuous state enforcement** with detailed reporting
- Your organization already has a **DevOps team** that can invest in learning the DSL
- You're in a **regulated industry** (finance, healthcare, government)
- You want the most mature, battle-tested configuration management platform

## Practical Self-Hosting Recommendations

### The Homelab Approach (5–20 nodes)

Start with **Ansible**. It requires no agents, uses SSH you already have, and your first playbook takes 15 minutes to write. Use a simple directory structure:

```
homelab/
├── inventory.ini
├── ansible.cfg
├── group_vars/
│   ├── all.yml          # Variables for all hosts
│  [pi-hole](https://pi-hole.net/)hole.yml       # Pi-hole specific variables
├── host_vars/
│   └── nas.yml          # NAS-specific variables
├── playbooks/
│   ├── base-setup.yml   # Common packages, SSH hardening
│   ├── docker-host.yml  # Install Docker + compose
│   └── pihole.yml       # Pi-hole deployment
└── roles/
    ├── common/
    ├── docker/
    └── traefik/
```

### The Growing Fleet (50–500 nodes)

Consider **SaltStack** if you need real-time enforcement and parallel execution. The master-minion architecture pays off once you're managing dozens of services across multiple servers. Use Salt's `salt-ssh` for initial bootstrapping, then transition to the agent model.

### The Compliance Environment (any size, strict requirements)

**Puppet** is the right choice when you need audit trails, policy enforcement, and regulatory compliance. The Puppet server's reporting dashboard gives you a real-time view of compliance across every node — invaluable for SOC 2, HIPAA, or PCI DSS requirements.

## Conclusion

All three tools are mature, open-source, and production-ready. The "best" choice depends on your specific constraints:

- **Ansible wins on simplicity** — the fastest path from zero to automated infrastructure
- **SaltStack wins on speed** — unmatched performance for large-scale, real-time operations
- **Puppet wins on compliance** — the most rigorous state enforcement and reporting

For most self-hosters starting out, Ansible is the right choice. It scales further than most people need, and if you eventually outgrow it, both Salt and Puppet have migration paths. The important thing is to start treating your infrastructure as code — the tool you pick matters less than the discipline you build around it.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
