---
title: "Self-Hosted Linux Audit Framework: auditd vs GoAudit vs Auditbeat (2026)"
date: "2026-05-16"
tags: ["security", "audit", "compliance", "linux", "monitoring", "forensics"]
draft: false
description: "Compare Linux audit frameworks for self-hosted security monitoring. Complete guide covering auditd, GoAudit, and Elastic Auditbeat with rule configurations and deployment examples."
---

The Linux Audit Framework is the kernel-level subsystem that records security-relevant events on your system. Every file access, system call, user login, privilege escalation, and configuration change can be captured, logged, and analyzed. For self-hosted servers handling sensitive data, the audit framework provides the forensic trail needed for incident response, compliance reporting, and security investigations.

Three primary tools interface with the Linux Audit Framework: **auditd** (the traditional userspace daemon), **GoAudit** (a modern Go-based replacement), and **Auditbeat** (Elastic's audit shipper to the ELK stack). Each serves a different operational model — from standalone audit logging to centralized security analytics.

This guide compares all three tools, provides rule configurations, and helps you build a comprehensive audit pipeline for your self-hosted infrastructure.

## Why Linux Audit Matters

The Linux kernel audit subsystem operates at the lowest level of userspace-visible activity. When you write an audit rule, the kernel intercepts matching events before they reach the application layer. This means:

- **Tamper-resistant**: Audit logs are written directly by the kernel, bypassing user-space interception
- **Comprehensive**: Every matching system call, file access, or configuration change is recorded
- **Attributable**: Each event includes the UID, PID, and process tree that triggered it
- **Forensically sound**: Audit logs provide legally defensible evidence for compliance audits

| Feature | auditd | GoAudit | Auditbeat |
|---------|--------|---------|-----------|
| **Language** | C | Go | Go |
| **Developer** | Linux Audit Project | Open source community | Elastic |
| **GitHub Stars** | 711+ (audit-userspace) | Community project | Part of Elastic Beats |
| **Architecture** | Traditional daemon | Modern single binary | Beat agent |
| **Output** | Local log files | Local files + JSON | Elasticsearch/Kafka |
| **Rule Format** | Native audit.rules | Native + YAML | Native + YAML |
| **Log Rotation** | Built-in (auditd.conf) | External needed | Beat-managed |
| **Remote Shipping** | audispd plugins | JSON output | Native |
| **Elasticsearch** | Via Logstash | Via Logstash | Direct |
| **Compliance** | STIG, PCI-DSS, HIPAA | Emerging | STIG, PCI-DSS, HIPAA |

## auditd: The Traditional Audit Daemon

auditd is the reference implementation of the Linux Audit userspace tools. It ships with every major Linux distribution and provides the `auditctl`, `ausearch`, `aureport`, and `auditd` binaries for rule management, log searching, report generation, and daemon operation. With 711+ GitHub stars in the linux-audit/audit-userspace repository, it remains the most widely deployed audit tool.

### Docker Compose: auditd in Container Monitoring

```yaml
version: "3.8"
services:
  auditd:
    image: ubuntu:24.04
    command: >
      bash -c "
      apt-get update && apt-get install -y auditd audispd-plugins &&
      mkdir -p /var/log/audit &&
      auditd -f &&
      sleep infinity
      "
    privileged: true
    cap_add:
      - AUDIT_CONTROL
      - AUDIT_WRITE
    volumes:
      - /var/log/audit:/var/log/audit
      - ./audit/rules:/etc/audit/rules.d
      - ./audit/auditd.conf:/etc/audit/auditd.conf
    restart: unless-stopped

  log-shipper:
    image: ubuntu:24.04
    command: >
      bash -c "
      apt-get update && apt-get install -y rsyslog &&
      echo '/var/log/audit/audit.log /var/log/audit/' >> /etc/rsyslog.d/audit.conf &&
      rsyslogd -n
      "
    volumes:
      - /var/log/audit:/var/log/audit:ro
      - ./rsyslog/audit.conf:/etc/rsyslog.d/audit.conf
    restart: unless-stopped
```

### Essential auditd Rules for Self-Hosted Servers

```bash
# Delete all existing rules
auditctl -D

# Monitor user login/logout events
-a always,exit -F arch=b64 -S execve -F exe=/usr/bin/login -k user-login
-a always,exit -F arch=b64 -S execve -F exe=/usr/sbin/sshd -k ssh-login

# Monitor privilege escalation
-a always,exit -F arch=b64 -S execve -F euid=0 -k privilege-escalation
-w /etc/sudoers -p wa -k sudo-changes
-w /etc/sudoers.d/ -p wa -k sudo-changes

# Monitor sensitive file changes
-w /etc/passwd -p wa -k identity-changes
-w /etc/shadow -p wa -k identity-changes
-w /etc/group -p wa -k identity-changes
-w /etc/ssh/sshd_config -p wa -k sshd-config

# Monitor Docker socket access
-w /var/run/docker.sock -p rwxa -k docker-access

# Monitor kernel module loading
-a always,exit -F arch=b64 -S init_module -S finit_module -k module-load

# Monitor network configuration changes
-w /etc/hosts -p wa -k network-config
-w /etc/resolv.conf -p wa -k network-config

# Make rules immutable (requires reboot to change)
-e 2
```

### Querying Audit Logs

```bash
# Search for recent login events
ausearch -k user-login -ts recent

# Find all privilege escalations today
ausearch -k privilege-escalation -ts today

# Generate a summary report
aureport --summary

# List all failed syscall attempts
aureport --failed

# Find who accessed a specific file
ausearch -f /etc/shadow -i

# Generate an authentication report
aureport --auth --summary
```

## GoAudit: Modern Go-Based Audit Daemon

GoAudit is a modern reimplementation of the audit userspace tools written in Go. It provides a single binary that replaces `auditd`, `ausearch`, and `aureport`, with improved performance, simpler configuration, and native JSON output for modern log pipelines.

### Key Advantages

- **Single binary**: Replaces the entire audit userspace toolchain
- **JSON output**: Native structured logging for Logstash, Fluent Bit, or custom parsers
- **Simplified config**: YAML-based rule management instead of cryptic audit.rules syntax
- **Better performance**: Go's concurrency model handles high-volume audit events more efficiently
- **Modern tooling**: Built-in HTTP API for rule management and log querying

### Deployment

```bash
# Download GoAudit binary
curl -L https://github.com/go-audit/go-audit/releases/latest/download/go-audit-linux-amd64   -o /usr/local/bin/go-audit
chmod +x /usr/local/bin/go-audit

# Configure via YAML
cat > /etc/go-audit.yaml << EOF
log:
  file: /var/log/go-audit/go-audit.log
  max_size: 100
  max_age: 30

rules:
  - syscall: [execve]
    arch: [b64]
    fields:
      - field: euid
        op: "="
        value: 0
    key: privilege-escalation

  - path: /etc/passwd
    permissions: [write, attribute]
    key: identity-changes

outputs:
  - type: file
    path: /var/log/go-audit/
  - type: stdout
    format: json
EOF

# Start as systemd service
cat > /etc/systemd/system/go-audit.service << EOF
[Unit]
Description=Go Audit Daemon
After=network.target

[Service]
ExecStart=/usr/local/bin/go-audit -config /etc/go-audit.yaml
Restart=on-failure
CapabilityBoundingSet=CAP_AUDIT_CONTROL CAP_AUDIT_WRITE

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now go-audit
```

## Auditbeat: Elastic's Audit Shipper

Auditbeat is part of the Elastic Beats family — lightweight data shippers that collect audit events and send them directly to Elasticsearch or Logstash. It uses the Linux Audit Framework kernel subsystem but adds Elastic's ecosystem integration, including pre-built dashboards, file integrity monitoring, and process tracking.

### Key Advantages

- **Elastic integration**: Direct shipping to Elasticsearch with Kibana dashboards
- **File Integrity Monitoring (FIM)**: Detect unauthorized file changes alongside audit events
- **Process tracking**: Correlate audit events with process tree information
- **Pre-built dashboards**: Kibana visualizations for compliance reporting
- **Centralized management**: Fleet Server for managing Auditbeat across hundreds of hosts

### Docker Compose: Auditbeat with ELK Stack

```yaml
version: "3.8"
services:
  auditbeat:
    image: docker.elastic.co/beats/auditbeat:8.14.0
    user: root
    command: auditbeat -e --strict.perms=false
    cap_add:
      - AUDIT_CONTROL
      - AUDIT_READ
    volumes:
      - ./auditbeat.yml:/usr/share/auditbeat/auditbeat.yml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc:/hostfs/proc:ro
      - /etc:/hostfs/etc:ro
    environment:
      - ELASTICSEARCH_HOSTS=https://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=auditbeat_internal
      - ELASTICSEARCH_PASSWORD=${ES_PASSWORD}
    restart: unless-stopped

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=${ES_PASSWORD}
    volumes:
      - esdata:/usr/share/elasticsearch/data
    restart: unless-stopped

  kibana:
    image: docker.elastic.co/kibana/kibana:8.14.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=https://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=kibana_system
      - ELASTICSEARCH_PASSWORD=${ES_PASSWORD}
    depends_on:
      - elasticsearch
    restart: unless-stopped

volumes:
  esdata:
```

## Choosing the Right Audit Framework

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Standalone server compliance | auditd | Default on all distros, STIG-certified |
| Modern log pipeline (JSON) | GoAudit | Native JSON output, simpler config |
| Elasticsearch/ELK stack | Auditbeat | Direct integration, pre-built dashboards |
| Multi-server fleet | Auditbeat + Fleet | Centralized management, visual dashboards |
| Minimal footprint | GoAudit | Single binary, lower memory usage |
| Government compliance | auditd | Only tool with full STIG certification |
| Developer/learning | auditd | Most documentation, community support |
| Cloud-native environment | Auditbeat | Kubernetes DaemonSet support |

## Why Self-Host Your Audit Pipeline?

Running the audit framework on self-hosted servers provides complete control over what events are captured, how long logs are retained, and who can access them. Cloud provider audit logs (like AWS CloudTrail) capture cloud API calls but cannot see what happens inside your VM — file modifications, process execution, or privilege escalation within your operating system.

The kernel audit subsystem captures every configured event regardless of the attacker's sophistication. If an intruder gains access to your self-hosted server, the audit log provides the forensic trail needed to understand their actions, identify compromised files, and determine the scope of the breach.

For compliance frameworks (PCI-DSS Requirement 10, HIPAA Security Rule, SOC 2 CC7.2), audit logging is mandatory. Self-hosted audit frameworks ensure you meet these requirements without depending on third-party logging services.

For runtime security monitoring, see our [Falco vs OSQuery vs auditd guide](../2026-04-17-falco-vs-osquery-vs-auditd-self-hosted-runtime-security-guide/). For centralized log collection, check our [systemd journal remote guide](../2026-05-06-self-hosted-centralized-journal-collection-graylog-vector-systemd-journal-remote/).

## FAQ

### What is the Linux Audit Framework?

The Linux Audit Framework is a kernel subsystem that records security-relevant events based on configurable rules. It operates at the syscall level, intercepting events before they reach user space. The framework consists of kernel components (the audit subsystem itself) and userspace tools (auditd for logging, auditctl for rule management, ausearch for querying, and aureport for reporting).

### What is the difference between auditd and Auditbeat?

auditd is the traditional Linux audit daemon that writes events to local log files (`/var/log/audit/audit.log`). Auditbeat is Elastic's lightweight shipper that collects the same kernel audit events but sends them directly to Elasticsearch. auditd is standalone and self-contained; Auditbeat requires an Elasticsearch cluster for full functionality. You can also run both — auditd for local compliance logs and Auditbeat for centralized analytics.

### How do I monitor Docker containers with the audit framework?

Use auditd rules to watch the Docker socket and container filesystem: `-w /var/run/docker.sock -p rwxa -k docker-access` monitors all Docker API calls. You can also monitor container filesystem changes with path-based rules like `-w /var/lib/docker/overlay2/ -p wa -k docker-fs`. For container-specific audit, consider running auditd inside privileged containers with the `AUDIT_CONTROL` and `AUDIT_WRITE` capabilities.

### Can GoAudit replace auditd entirely?

GoAudit can replace auditd's core functionality (running the daemon, processing events, writing logs) but lacks some advanced features like audit rotation configuration (`auditd.conf`), detailed reporting (`aureport`), and the extensive rule syntax validation of the reference implementation. For basic audit logging with JSON output, GoAudit is sufficient. For compliance environments requiring specific auditd features, stick with the reference implementation.

### How much disk space does audit logging consume?

Audit log volume depends on rule granularity. A typical server with identity monitoring and privilege escalation rules generates 50-200 MB per day. With comprehensive syscall monitoring, volumes can reach 1-5 GB per day. Configure `max_log_file` and `max_log_file_action` in `auditd.conf` to manage disk usage. For high-volume environments, ship logs to a centralized storage system (Elasticsearch, S3) and configure local rotation with short retention.

### Does the audit framework impact system performance?

The kernel audit subsystem has minimal overhead when rules are selective. Monitoring specific files (`-w /etc/passwd -p wa`) adds negligible overhead. Monitoring all execve syscalls (`-a always,exit -S execve`) adds 2-5% CPU overhead under heavy load. For production systems, avoid overly broad syscall rules and use path-based or user-based filters to limit the event volume. The GoAudit daemon typically uses less memory than auditd due to Go's efficient event handling.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Audit Framework: auditd vs GoAudit vs Auditbeat (2026)",
  "description": "Compare Linux audit frameworks for self-hosted security monitoring. Complete guide covering auditd, GoAudit, and Elastic Auditbeat with rule configurations and deployment examples.",
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
