---
title: "Falco vs Osquery vs Auditd: Best Self-Hosted Runtime Security 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "security", "monitoring", "runtime"]
draft: false
description: "Compare Falco, Osquery, and Auditd for self-hosted runtime security. Complete deployment guides with Docker Compose configs and rules for container and host-level threat detection."
---

Runtime security is the last line of defense in your infrastructure. When firewalls, intrusion detection systems like those covered in our [Suricata vs Snort vs Zeek guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/), and network perimeter controls fail, runtime security tools detect malicious behavior as it happens — unauthorized process spawns, unexpected network connections, file tampering, and privilege escalation attempts.

Three open-source projects dominate this space: **Falco**, **Osquery**, and **Auditd**. Each takes a fundamentally different approach to runtime visibility. In this guide, we compare them head-to-head and provide production-ready deployment configurations for each.

## Why Self-Host Runtime Security

Commercial runtime detection tools like Sysdig Secure, CrowdStrike Falcon, and Datadog Runtime Security require sending sensitive telemetry data to third-party cloud platforms. For organizations with strict data residency requirements, compliance mandates (SOC 2, HIPAA, PCI DSS), or air-gapped environments, self-hosted runtime security is non-negotiable.

Self-hosting gives you:

- **Full data sovereignty** — all event logs, process trees, and network flow data stay on your infrastructure
- **No telemetry limits** — commercial tools cap events per second; open-source tools process everything
- **Custom detection rules** — write rules specific to your workload without vendor approval
- **Integration with existing SIEM** — pipe events directly into your [self-hosted SIEM stack](../self-hosted-siem-wazuh-security-onion-elastic-guide/)
- **Zero per-host licensing costs** — deploy to 10 or 10,000 nodes without scaling fees

## Falco: Cloud-Native Runtime Security

**Falco** (8,881 stars, last updated April 2026) is a CNCF-graduated project by Sysdig that uses eBPF and kernel modules to monitor system calls in real-time. It ships with a curated rule set for detecting suspicious behavior in containers and hosts, and can forward alerts to Slack, PagerDuty, webhooks, and more via Falco Sidekick.

Falco is the right choice when you need **real-time, behavior-based detection** in [kubernetes](https://kubernetes.io/) or container-heavy environments. It detects things like:

- Shell spawned inside a container
- Unexpected outbound network connection from a database container
- Sensitive file access (`/etc/shadow`, Kubernetes tokens)
- Privilege escalation attempts
- Cryptocurrency mining processes

### Falco Architecture

Falco operates at the kernel level, intercepting system calls via eBPF probes (preferred) or kernel modules. When a system call matches a rule condition, Falco generates an alert with full context: process name, user, container ID, and command line.

```yaml
# [docker](https://www.docker.com/)/docker-compose/docker-compose.yaml (from official Falco repo)
version: "3"
services:
  falco:
    container_name: falco
    cap_drop:
      - all
    cap_add:
      - sys_admin
      - sys_resource
      - sys_ptrace
    volumes:
      - /var/run/docker.sock:/host/var/run/docker.sock
      - /proc:/host/proc:ro
      - /etc:/host/etc:ro
      - ./config/http_output.yml:/etc/falco/config.d/http_output.yml
    image: falcosecurity/falco:latest

  sidekick:
    container_name: falco-sidekick
    image: falcosecurity/falcosidekick
    environment:
      WEBUI_URL: http://falco-webui:2802

  webui:
    container_name: falco-webui
    image: falcosecurity/falcosidekick-ui:2.2.0
    ports:
      - 2802:2802
    depends_on:
      - redis
    command: ['-r', 'redis:6379', '-d']

  redis:
    image: redis/redis-stack:7.2.0-v11
```

For Kubernetes deployments, Falco is installed as a DaemonSet via Helm:

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

helm install falco falcosecurity/falco \
  --set falcosidekick.enabled=true \
  --set falcosidekick.webui.enabled=true \
  --set tty=true
```

### Custom Falco Rule Example

```yaml
- rule: Unauthorized Database Access
  desc: Detect shell access to database containers
  condition: >
    spawned_process and container and
    container.image contains "postgres" and
    proc.name in (bash, sh, zsh)
  output: "Shell spawned in DB container (user=%user.name container=%container.id image=%container.image.repository)"
  priority: CRITICAL
  tags: [database, shell, container]
```

## Osquery: SQL-Powered Endpoint Visibility

**Osquery** (23,225 stars, last updated April 2026) by Meta (formerly Facebook) takes a radically different approach: it exposes the operating system as a high-performance relational database. You write SQL queries to inspect running processes, loaded kernel modules, open network connections, installed packages, and thousands of other system attributes.

Osquery excels at **scheduled compliance checks and ad-hoc investigation**. Instead of alerting on real-time events, Osquery lets you ask questions like "Which processes are listening on port 443?" or "Show me all SUID binaries changed in the last 24 hours."

### Osquery Architecture

Osquery uses a pluggable architecture:

- **osqueryd** — daemon for scheduled query execution and log aggregation
- **osqueryi** — interactive shell for ad-hoc queries
- **Extensions** — custom tables and log plugins written in Python, Go, or C++

```bash
# Install osquery on Ubuntu/Debian
export OSQUERY_VERSION=5.15.0
curl -L "https://github.com/osquery/osquery/releases/download/${OSQUERY_VERSION}/osquery_${OSQUERY_VERSION}_1.amd64.deb" -o /tmp/osquery.deb
sudo dpkg -i /tmp/osquery.deb

# Start the daemon with a config file
sudo systemctl enable osqueryd
sudo systemctl start osqueryd
```

### Osquery Configuration

```json
{
  "options": {
    "config_plugin": "filesystem",
    "logger_plugin": "filesystem",
    "logger_path": "/var/log/osquery",
    "disable_logging": false,
    "log_result_events": true,
    "schedule_splay_percent": 10
  },
  "schedule": {
    "crontab": {
      "query": "SELECT * FROM crontab;",
      "interval": 300
    },
    "listening_ports": {
      "query": "SELECT address, port, protocol, pid FROM listening_ports;",
      "interval": 60
    },
    "suid_binaries": {
      "query": "SELECT * FROM suid_bin WHERE setuid = 1 OR setgid = 1;",
      "interval": 3600
    },
    "open_connections": {
      "query": "SELECT local_address, local_port, remote_address, remote_port, state FROM process_open_sockets WHERE remote_address != '0.0.0.0' AND remote_address != '::';",
      "interval": 120
    }
  },
  "packs": {
    "osquery-monitoring": ["/usr/share/osquery/packs/osquery-monitoring.conf"],
    "incident-response": ["/usr/share/osquery/packs/incident-response.conf"]
  }
}
```

### Osquery Docker Deployment

```bash
docker run --rm -it \
  --pid=host \
  --env OSQUERY_SECRET_KEY="your-secret-key" \
  -v /var/log/osquery:/var/log/osquery \
  osquery/osquery:latest \
  osqueryi --config_plugin=filesystem --config_path=/etc/osquery/osquery.conf
```

For fleet management, Osquery integrates with TLS servers like **FleetDM** or **Kolide** to centrally distribute queries and collect results across hundreds of hosts.

## Auditd: Linux Kernel Auditing Framework

**Auditd** (708 stars in its userspace tools repo, last updated April 2026) is the userspace component of the Linux Audit Framework built into the kernel. It provides the most granular level of system call auditing available on Linux, logging every file access, process execution, and system call that matches configured rules.

Auditd is the right choice when you need **comprehensive, legally-defensible audit trails** — particularly for compliance frameworks like PCI DSS, HIPAA, and FISMA that mandate detailed audit logging.

### Auditd Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install auditd audispd-plugins

# RHEL/CentOS/Fedora
sudo dnf install audit audit-libs-plugins
sudo systemctl enable auditd
sudo systemctl start auditd
```

### Auditd Rule Configuration

Rules are defined in `/etc/audit/rules.d/audit.rules`:

```bash
# Monitor sensitive file access
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k privilege-escalation
-w /etc/ssh/sshd_config -p wa -k ssh-config

# Monitor process execution by specific users
-a always,exit -F arch=b64 -S execve -F uid=0 -k root-exec

# Monitor network configuration changes
-a always,exit -F arch=b64 -S sethostname -S setdomainname -k system-identity

# Monitor Docker socket access (container breakout detection)
-w /var/run/docker.sock -p rwxa -k docker-access

# Monitor kernel module loading
-a always,exit -F arch=b64 -S init_module -S delete_module -k kernel-module

# Immutable mode (prevents rule modification without reboot)
-e 2
```

### Searching Audit Logs

```bash
# Search by key
sudo ausearch -k identity

# Search by executable
sudo ausearch -x /bin/bash

# Search by user ID
sudo ausearch -ui 1000

# Generate a human-readable report
sudo aureport --summary

# Failed authentication attempts
sudo aureport -au --summary -i --failed
```

## Comparison: Falco vs Osquery vs Auditd

| Feature | Falco | Osquery | Auditd |
|---------|-------|---------|--------|
| **Detection Model** | Real-time event-driven | Scheduled SQL queries | Kernel-level syscall auditing |
| **Primary Use Case** | Container/runtime threat detection | Endpoint visibility & compliance | System audit trails |
| **Query Language** | Custom rule syntax (YAML) | SQL | Rule-based (auditctl syntax) |
| **Container Support** | Excellent (Docker + K8s native) | Good (can query container metadata) | Basic (logs host-level events) |
| **Performance Impact** | Low (eBPF) to Medium (kernel module) | Low-Medium (scheduled queries) | Low-Medium (depends on rule count) |
| **Alerting** | Built-in + Sidekick (Slack, webhooks) | Via external log consumers | Via audisp plugins |
| **Ease of Use** | Moderate (rule writing required) | Easy (SQL is familiar) | Moderate (com[plex](https://www.plex.tv/) rule syntax) |
| **Kubernetes Integration** | Native (DaemonSet via Helm) | Via FleetDM + K8s operator | Requires DaemonSet wrapper |
| **Historical Queries** | No (event stream only) | Yes (query any point in time) | Yes (search logs with ausearch) |
| **eBPF Support** | Yes (preferred driver) | Limited (via custom tables) | No |
| **Cross-Platform** | Linux only | Linux, macOS, Windows | Linux only |
| **License** | Apache 2.0 | Apache 2.0 | GPL v2 |
| **GitHub Stars** | 8,881 | 23,225 | 708 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |

## Choosing the Right Tool

### Use Falco When:
- You run Kubernetes or container-heavy workloads
- You need **real-time alerting** on suspicious behavior
- You want pre-built rules for common attack patterns (crypto mining, reverse shells, sensitive file access)
- Your security team prefers event-driven detection over scheduled scanning

### Use Osquery When:
- You need **continuous compliance monitoring** across heterogeneous fleets (Linux, macOS, Windows)
- Your team is comfortable with SQL and wants flexible querying
- You want to investigate incidents by asking arbitrary questions about system state
- You're building a security operations center with scheduled baseline checks

### Use Auditd When:
- You need **legally-defensible audit logs** for compliance (PCI DSS, HIPAA, FISMA)
- You want kernel-level granularity for every system call
- Your primary concern is file integrity and access logging
- You're already using tools like the [file integrity monitoring stack with AIDE and OSSEC](../self-hosted-file-integrity-monitoring-aide-ossec-tripwire-guide/) and need complementary syscall-level data

### Production Stack: Use All Three

Many production environments layer all three tools:

1. **Auditd** provides the foundational syscall-level audit trail required for compliance
2. **Osquery** runs scheduled compliance checks and provides ad-hoc investigation capability
3. **Falco** provides real-time alerting for container-specific threats

This layered approach is similar to how eBPF observability tools like [Cilium and Tetragon](../ebpf-networking-observability-cilium-pixie-tetragon-guide-2026/) complement network-level security — each tool operates at a different layer of the stack, providing defense in depth.

## Deployment Quick Reference

### Falco Quick Start

```bash
# Docker standalone
docker run --rm -i -t \
  --name falco \
  --privileged \
  -v /var/run/docker.sock:/host/var/run/docker.sock \
  -v /dev:/host/dev \
  -v /proc:/host/proc:ro \
  -v /boot:/host/boot:ro \
  -v /lib/modules:/host/lib/modules:ro \
  -v /usr:/host/usr:ro \
  -v /etc:/host/etc:ro \
  falcosecurity/falco:latest

# Test a rule: open a shell in a container
# You should see: "Shell was spawned in a container"
```

### Osquery Quick Start

```bash
# Interactive mode
sudo osqueryi

# Run a single query
sudo osqueryi --json "SELECT name, pid, state FROM processes WHERE state = 'Z';"

# Check for listening ports
sudo osqueryi "SELECT DISTINCT protocol, local_address, local_port, pid FROM listening_ports ORDER BY local_port;"
```

### Auditd Quick Start

```bash
# Add a watch rule
sudo auditctl -w /etc/passwd -p wa -k passwd-change

# List active rules
sudo auditctl -l

# Monitor the log in real-time
sudo tail -f /var/log/audit/audit.log | aureport -x --summary

# Make rules persistent (write to rules.d)
echo "-w /etc/shadow -p wa -k shadow-access" | sudo tee /etc/audit/rules.d/custom.rules
sudo augenrules --load
```

## FAQ

### What is the difference between Falco and Osquery?

Falco is an event-driven runtime security tool that alerts in real-time when system calls match predefined rules (e.g., shell spawned in container). Osquery is a scheduled query engine that exposes the OS as a SQL database — it doesn't alert on events but lets you run SQL queries to inspect system state at any point in time. Falco is better for real-time threat detection; Osquery is better for compliance scanning and incident investigation.

### Can Falco run on bare metal, or is it only for containers?

Falco works on both bare metal and containerized environments. While it's designed with cloud-native workloads in mind and ships with container-specific rules, it monitors all system calls on the host regardless of whether processes run in containers. On bare metal, container-specific rules simply won't trigger, but the remaining rules (file access, network connections, process execution) work identically.

### Does Auditd impact system performance?

Auditd's performance impact depends on the number and scope of active rules. A minimal rule set (monitoring key files and a few syscalls) typically adds less than 2% CPU overhead. Heavy rule sets that audit every file access or every syscall can add 5-15% overhead. The key is to be specific: use targeted watch rules (`-w`) rather than broad syscall filters (`-a always,exit -S all`) in production.

### How do I forward Falco alerts to my SIEM?

Use **Falco Sidekick**, which is included in the official Docker Compose file above. Falco Sidekick supports output to Slack, Microsoft Teams, PagerDuty, webhooks, Elasticsearch, Kafka, NATS, and more. For SIEM integration, configure the Elasticsearch or Kafka output and point it at your existing log ingestion pipeline.

### Can Osquery replace traditional endpoint detection and response (EDR)?

Osquery provides excellent visibility but is not a full EDR replacement. It lacks real-time alerting (queries run on a schedule, not on events), endpoint isolation capabilities, and automated remediation. However, when combined with a real-time tool like Falco and a centralized management server like FleetDM, Osquery becomes a powerful component of an EDR-like stack.

### Is Auditd required for PCI DSS compliance?

PCI DSS Requirement 10 mandates tracking and monitoring all access to network resources and cardholder data. Auditd is the most common tool used to fulfill this requirement on Linux systems, as it provides tamper-resistant logs of file access, user authentication, and privilege escalation. While other tools can supplement Auditd, most auditors expect to see kernel-level audit logs from Auditd or an equivalent.

### How do I manage Osquery across hundreds of servers?

Deploy **FleetDM** (open-source) as the central management server. FleetDM distributes query packs, collects results, and provides a web UI for browsing host status. Alternatively, Kolide offers a managed Osquery platform. For a fully self-hosted stack, FleetDM + Osquery gives you centralized query management without any cloud dependency.

### Can I use Falco and Osquery together on the same host?

Yes, and many organizations do exactly this. Falco provides real-time event detection while Osquery provides scheduled compliance scanning. They operate at different layers — Falco hooks into system calls via eBPF/kernel modules, while Osquery reads from `/proc`, `/sys`, and other kernel interfaces. There is no conflict between them, and their combined telemetry gives broader coverage than either tool alone.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Falco vs Osquery vs Auditd: Best Self-Hosted Runtime Security 2026",
  "description": "Compare Falco, Osquery, and Auditd for self-hosted runtime security. Complete deployment guides with Docker Compose configs and rules for container and host-level threat detection.",
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
