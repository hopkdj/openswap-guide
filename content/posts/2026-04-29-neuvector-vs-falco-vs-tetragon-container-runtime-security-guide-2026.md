---
title: "NeuVector vs Falco vs Tetragon: Container Runtime Security 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "security", "containers", "kubernetes"]
draft: false
description: "Compare NeuVector, Falco, and Tetragon — the top three open-source container runtime security tools. Includes Docker deployment, Kubernetes setup, and real-world policy examples for protecting your containers in 2026."
---

If you run containers in production — whether on Docker, Kubernetes, or a bare-metal host — you need runtime security. Vulnerability scanners catch problems in images *before* they run, but once a container is live, you need tools that monitor behavior, detect anomalies, and block attacks in real time. That's where container runtime security comes in.

This guide compares three leading open-source options: **NeuVector**, **Falco**, and **Tetragon**. Each takes a different architectural approach, but all three aim to give you visibility into what your containers are actually doing at runtime — and stop bad actors before they escape.

## Why Self-Hosted Container Runtime Security?

Cloud providers offer managed runtime security, but they come with trade-offs:

- **Data sovereignty**: Runtime telemetry (process trees, network connections, file access) leaves your infrastructure
- **Cost**: Per-node or per-container pricing scales poorly at 100+ hosts
- **Vendor lock-in**: Policies, dashboards, and alerting rules are proprietary
- **Compliance**: Healthcare, finance, and government workloads often require on-prem security tooling

Self-hosted runtime security keeps all telemetry within your control, integrates with your existing monitoring stack, and costs nothing beyond the compute it consumes.

## Quick Comparison Table

| Feature | NeuVector | Falco | Tetragon |
|---------|-----------|-------|----------|
| **Developer** | SUSE (acquired NeuVector) | Sysdig (CNCF project) | Cilium (CNCF project) |
| **Detection Engine** | Deep packet inspection + behavior analysis | Syscall monitoring via eBPF/kernel modules | eBPF-based observability |
| **Network Policy** | Built-in Layer 7 network policy | No (requires integration) | CiliumNetworkPolicy |
| **Web Console** | Yes (full management UI) | No (requires Falcosidekick + UI) | No (Hubble UI for observability) |
| **Kubernetes Native** | Yes (CRDs, admission controller) | Yes (daemonset, rules engine) | Yes (Cilium integration) |
| **Docker Support** | Yes (single-host compose) | Yes (daemonset or standalone) | Limited (Kubernetes-first) |
| **Vulnerability Scanning** | Built-in (registry scanning) | No | No |
| **Response Actions** | Block, quarantine, alert | Alert only (sidekick for actions) | Block, alert, log |
| **License** | Apache 2.0 (core) | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 1,299 | 5,300+ | 4,609 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |

## NeuVector: Full-Stack Container Security Platform

NeuVector is the most feature-complete option. It combines runtime threat detection, Layer 7 network policy, vulnerability scanning, and a full web-based management console into a single platform. Originally an independent company, NeuVector was acquired by SUSE and open-sourced under Apache 2.0.

### Architecture

NeuVector runs as three components:
- **Controller**: Central management, policy engine, and web console
- **Enforcer**: Per-host security sensor that monitors containers
- **Manager**: UI and API gateway

The enforcer runs in privileged mode on each node, monitoring all container activity via cgroups and network taps. The controller aggregates telemetry and enforces policies across the cluster.

### Docker Compose Deployment

```yaml
version: "3"
services:
  controller:
    image: neuvector/controller:latest
    container_name: neuvector.controller
    privileged: true
    environment:
      - CLUSTER_JOIN_ADDR=neuvector.controller
    ports:
      - 18300:18300
      - 18301:18301
      - 18301:18301/udp
      - 18400:18400
      - 4443:443
    volumes:
      - /var/neuvector:/var/neuvector
      - /var/run/docker.sock:/var/run/docker.sock
      - /proc:/host/proc:ro

  enforcer:
    image: neuvector/enforcer:latest
    container_name: neuvector.enforcer
    privileged: true
    pid: host
    environment:
      - CLUSTER_JOIN_ADDR=neuvector.controller
    ports:
      - 18301:18301
      - 18301:18301/udp
      - 18401:18401
    volumes:
      - /var/neuvector:/var/neuvector
      - /var/run/docker.sock:/var/run/docker.sock
      - /proc:/host/proc:ro
      - /sys/fs/cgroup/:/host/cgroup/:ro

  manager:
    image: neuvector/manager:latest
    container_name: neuvector.manager
    environment:
      - CLUSTER_JOIN_ADDR=neuvector.controller
    ports:
      - 8443:8443
```

Deploy with `docker compose up -d` and access the console at `https://localhost:8443`. Default credentials are `admin/admin` — change them immediately.

### Kubernetes Deployment

```bash
helm repo add neuvector https://neuvector.github.io/core/
helm install neuvector neuvector/core \
  --namespace neuvector \
  --create-namespace \
  --set controller.admissionControl.enabled=true \
  --set controller.registryScan.enabled=true
```

### Key Features

- **Layer 7 network policy**: Discover and enforce allowed connections between containers at the application protocol level (HTTP, DNS, TLS)
- **Vulnerability scanning**: Scan registry images and running containers for CVEs
- **Compliance templates**: Built-in rules for CIS benchmarks, NIST, and PCI DSS
- **Admission control**: Block non-compliant pods from starting
- ** Quarantine**: Automatically isolate compromised containers

## Falco: The CNCF Runtime Security Standard

Falco is the oldest and most widely adopted container runtime security tool. Originally created by Sysdig and donated to CNCF, it monitors system calls and container events to detect anomalous behavior. Falco uses a rules engine that lets you write detection logic in YAML.

### Architecture

Falco runs as a daemon on each node, tapping into the kernel to observe system calls. It supports two driver modes:
- **eBPF probe**: Modern, low-overhead, recommended for kernels 4.14+
- **Kernel module**: Legacy fallback for older kernels

Alerts are emitted as JSON and can be forwarded to Falcosidekick, which routes them to Slack, PagerDuty, webhooks, or any notification channel.

### Docker Compose Deployment

```yaml
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
      - ./config/falco_rules.yaml:/etc/falco/falco_rules.local.yaml
    image: falcosecurity/falco:latest
    command: ["falco", "--cri", "/host/var/run/docker.sock"]

  falcosidekick:
    container_name: falcosidekick
    image: falcosecurity/falcosidekick:latest
    environment:
      WEBUI_URL: http://falco-webui:2802
      SLACK_WEBHOOKURL: "${SLACK_WEBHOOK_URL}"
    ports:
      - 2801:2801

  falco-webui:
    container_name: falco-webui
    image: falcosecurity/falcosidekick-ui:latest
    ports:
      - 2802:2802
    depends_on:
      - falcosidekick
    command: ['-r', 'falcosidekick:2801', '-d']
```

### Custom Rule Example

```yaml
- rule: Unexpected Package Manager Run Inside Container
  desc: Detect apt-get/yum/apk execution in a container (possible package install)
  condition: >
    spawned_process and container and
    (proc.name = apt-get or proc.name = yum or proc.name = apk)
  output: >
    Package manager executed in container (user=%user.name container=%container.name
    image=%container.image.repository proc=%proc.cmdline)
  priority: WARNING
  tags: [process, container]
```

### Key Features

- **Rich rules engine**: 100+ default rules covering privilege escalation, reverse shells, file tampering, and more
- **CNCF graduated project**: Mature, well-tested, backed by a large community
- **Flexible output**: JSON events to any sink via Falcosidekick (Slack, PagerDuty, Elasticsearch, etc.)
- **Low overhead**: eBPF driver adds <2% CPU overhead
- **Extensible**: Custom rules in YAML, Lua scripting for complex logic

## Tetragon: eBPF-Powered Security Observability

Tetragon is the newest entrant, developed by the Cilium team (also CNCF). Unlike Falco's syscall monitoring, Tetragon operates entirely in eBPF — the kernel's built-in tracing and security framework. This gives it unique visibility into kernel functions, process execution, and network activity with minimal overhead.

### Architecture

Tetragon uses eBPF programs loaded directly into the kernel. It monitors:
- **Process execution**: Track every process start, including full argument lists
- **File access**: Monitor opens, reads, writes to sensitive paths
- **Network connections**: Track TCP/UDP sockets at the kernel level
- **Kernel function calls**: Trace specific kernel functions for deep inspection

Events are collected by the Tetragon daemon and exposed via gRPC, JSON logging, or the Hubble observability UI.

### Installation

Tetragon is primarily designed for Kubernetes environments. For single-host testing:

```bash
# Install the tetragon CLI
curl -LO https://github.com/cilium/tetragon/releases/latest/download/tetragon-linux-amd64.tar.gz
tar xzf tetragon-linux-amd64.tar.gz
sudo mv tetragon /usr/local/bin/

# Run tetragon on the host
sudo tetragon
```

For Kubernetes deployment:

```bash
helm repo add cilium https://helm.cilium.io
helm install tetragon cilium/tetragon \
  --namespace kube-system \
  --set tetragon.enabled=true \
  --set tetragon.enableKprobeMulti=true
```

### TracingPolicy Example

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: detect-shell-execution
spec:
  kprobes:
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"
      selectors:
        - matchBinaries:
            - operator: "In"
              values:
                - "/bin/bash"
                - "/bin/sh"
                - "/bin/zsh"
      output:
        - type: "string"
          label: "Executed shell"
```

This policy detects any execution of a shell binary — a common indicator of container escape or reverse shell attacks.

### Key Features

- **eBPF native**: No kernel modules, no performance penalty, safe kernel execution
- **Process-level visibility**: See full process trees, arguments, and file paths
- **Cilium integration**: Works seamlessly with Cilium CNI for network policy enforcement
- **Hubble UI**: Real-time observability dashboard for flow and event visualization
- **Policy-as-code**: TracingPolicy CRDs for declarative security rules

## Which Should You Choose?

### Choose NeuVector if:
- You want an **all-in-one platform** with UI, network policy, vulnerability scanning, and runtime detection
- You need **Layer 7 network policies** to discover and enforce allowed container connections
- You prefer a **commercial-grade product** that's now open source (SUSE-backed)
- You need **compliance reporting** out of the box (CIS, NIST, PCI DSS)

### Choose Falco if:
- You want the **most mature and widely adopted** runtime security tool
- You need a **large rule library** (100+ default rules) and an active community
- You prefer **flexible alerting** via Falcosidekick to any notification channel
- You run **mixed environments** (Docker, Kubernetes, bare metal) and need broad OS support

### Choose Tetragon if:
- You already use **Cilium CNI** and want tight integration
- You want **eBPF-native** security with minimal overhead
- You need **deep kernel-level visibility** into process execution and file access
- You prefer **declarative policies** via Kubernetes CRDs

For many teams, Falco is the safest starting point — it's the CNCF standard, has the largest community, and works everywhere. NeuVector is ideal if you want a complete security platform with a management UI. Tetragon shines in Cilium-heavy Kubernetes environments where eBPF is already in use.

## FAQ

### What is container runtime security?
Container runtime security monitors containers *while they are running* — tracking process execution, network connections, file access, and system calls. Unlike image scanners that check for known vulnerabilities before deployment, runtime security detects active attacks, privilege escalation, and policy violations in real time.

### Do I need runtime security if I already scan container images?
Yes. Image scanning catches known vulnerabilities in your images, but it cannot detect: zero-day exploits, runtime configuration changes, insider threats, or supply chain attacks that modify behavior at runtime. Runtime security is a complementary layer, not a replacement for scanning. For a complete security posture, consider combining runtime tools with image scanning tools like [Trivy, Grype, and Clair](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anch/).

### Can these tools run on Docker without Kubernetes?
NeuVector and Falco both support standalone Docker deployments via Docker Compose. Tetragon is primarily designed for Kubernetes environments, though it can run on individual hosts for testing. If you're running Docker without Kubernetes, NeuVector or Falco are the practical choices.

### What is the performance overhead of runtime security tools?
With eBPF-based monitoring (Falco's default driver and Tetragon's architecture), overhead is typically 1-3% CPU and negligible memory impact. NeuVector's deep packet inspection mode adds slightly more overhead (~3-5%) but provides richer network visibility. For most workloads, this is a minor trade-off for the security benefits.

### How do these tools compare to traditional endpoint detection (EDR)?
Container runtime security tools are specialized for containerized workloads. They understand container boundaries, image metadata, and Kubernetes context — things traditional EDR tools struggle with. However, EDR tools cover the host OS and non-container processes. For comprehensive security, many teams run both: runtime security for containers and EDR for the host. If you're also interested in host-level runtime security, see our comparison of [Falco, OSQuery, and AuditD](../falco-vs-osquery-vs-auditd-self-hosted-runtime-security-guide/).

### Is NeuVector really free and open source?
The core NeuVector components (controller, enforcer, manager) are open source under Apache 2.0. Some enterprise features (centralized management for multi-cluster setups, premium support) require a SUSE subscription. The open-source version includes runtime detection, network policy, vulnerability scanning, and the web console.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "NeuVector vs Falco vs Tetragon: Container Runtime Security 2026",
  "description": "Compare NeuVector, Falco, and Tetragon — the top three open-source container runtime security tools. Includes Docker deployment, Kubernetes setup, and real-world policy examples.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
