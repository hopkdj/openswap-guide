---
title: "KubeArmor vs Falco vs Tetragon — Kubernetes Runtime Security Enforcement (2026)"
date: "2026-05-07T11:00:00+00:00"
tags: ["kubernetes", "security", "runtime-security", "self-hosted", "kubearmor", "falco", "tetragon"]
draft: false
---

Runtime security is the last line of defense in Kubernetes. Even with strong image scanning and policy enforcement, a compromised container can execute arbitrary commands. Three open-source tools provide runtime security enforcement: **KubeArmor** (LSM-based policy enforcement), **Falco** (signature-based detection), and **Tetragon** (eBPF-based enforcement).

This guide compares their detection methods, enforcement capabilities, and self-hosted deployment patterns.

## Quick Comparison

| Feature | KubeArmor | Falco | Tetragon |
|---|---|---|---|
| **GitHub** | kubearmor/kubearmor | falcosecurity/falco | cilium/tetragon |
| **Stars** | 2,090 | 6,400+ | 5,800+ |
| **Core Technology** | AppArmor / eBPF / SELinux | Kernel module / eBPF | eBPF |
| **Detection Mode** | Policy-based enforcement | Signature-based detection | eBPF tracing + enforcement |
| **Enforcement** | ✅ Block violations | ❌ Detect & alert only | ✅ Block violations |
| **Zero-Day Protection** | ✅ Whitelist-based policies | ❌ Needs signatures | ✅ Function-level tracing |
| **Language** | Go | C++ | Go |
| **Last Active** | 2026-05 | 2026-05 | 2026-05 |

## KubeArmor: LSM-Based Policy Enforcement

KubeArmor uses Linux Security Modules (AppArmor, SELinux, or eBPF LSM) to enforce security policies at the container runtime level. It translates Kubernetes-native `KubeArmorPolicy` CRDs into LSM profiles.

### Architecture

KubeArmor runs as a DaemonSet on each node. It watches for `KubeArmorPolicy` resources and generates LSM profiles that are applied to containers via the CRI. When a container violates a policy, the action is blocked at the kernel level.

### Installation

```yaml
# Install KubeArmor via Helm
apiVersion: helm.sh/v3
kind: HelmRelease
metadata:
  name: kubearmor
  namespace: kubearmor
spec:
  chart:
    spec:
      chart: kubearmor-operator
      version: "1.3.0"
      sourceRef:
        kind: HelmRepository
        name: kubearmor-charts
  interval: 10m
  install:
    createNamespace: true
```

```bash
helm repo add kubearmor https://kubearmor.github.io/charts
helm install kubearmor kubearmor/kubearmor-operator \
  --namespace kubearmor \
  --create-namespace
```

### Security Policy Example

```yaml
apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: block-shell-access
  namespace: production
spec:
  selector:
    matchLabels:
      app: web-frontend
  process:
    matchPaths:
    - path: /bin/bash
    - path: /bin/sh
    - path: /usr/bin/python3
    action: Block
  file:
    matchPaths:
    - path: /etc/shadow
      action: Block
    - path: /etc/passwd
      action: Allow  # Read-only access
  message: "Shell access blocked in production containers"
```

### System Policy Example

```yaml
apiVersion: security.kubearmor.com/v1
kind: KubeArmorHostPolicy
metadata:
  name: node-hardening
spec:
  nodeSelector:
    matchLabels:
      kubernetes.io/os: linux
  process:
    matchPaths:
    - path: /usr/sbin/tcpdump
      action: Block
    - path: /usr/bin/nmap
      action: Block
  file:
    matchPaths:
    - path: /etc/kubernetes
      action: Block
    - path: /var/run/docker.sock
      action: Block
```

### Key Strengths

- **Active enforcement**: Actually blocks violations, not just alerts
- **Kubernetes-native policies**: CRDs instead of raw AppArmor profiles
- **Zero-day protection**: Whitelist-based policies block unknown behavior
- **Multi-LSM support**: Works with AppArmor, SELinux, or eBPF LSM

## Falco: Signature-Based Runtime Detection

Falco is the most widely deployed runtime security tool for Kubernetes. It uses kernel-level system call monitoring to detect suspicious activity based on predefined rules.

### Installation

```bash
# Install Falco via Helm
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco \
  --namespace falco \
  --create-namespace \
  --set driver.kind=modern_ebpf \
  --set falcoRules.customRules.enabled=true \
  -f falco-values.yaml
```

```yaml
# falco-values.yaml
driver:
  kind: modern_ebpf  # Use eBPF instead of kernel module

falco:
  rulesFile:
    - /etc/falco/falco_rules.yaml
    - /etc/falco/rules.d/

  output:
    # Send alerts to stdout and file
    - stdout
    - file: /var/log/falco_events.json

  httpOutput:
    enabled: true
    url: "http://alertmanager:9093/api/v1/alerts"
```

### Custom Detection Rules

```yaml
# custom-falco-rules.yaml
- rule: Suspicious Reverse Shell
  desc: Detect reverse shell attempts
  condition: >
    spawned_process and
    (proc.name in (sh, bash, python, python3, perl) and
     (proc.cmdline contains "/dev/tcp" or
      proc.cmdline contains "/dev/udp" or
      proc.cmdline contains "nc -e" or
      proc.cmdline contains "ncat --exec"))
  output: "Reverse shell detected (user=%user.name command=%proc.cmdline)"
  priority: CRITICAL
  tags: [shell, attack]

- rule: Kubernetes Secret Access
  desc: Detect access to Kubernetes service account tokens
  condition: >
    open_read and
    (fd.name contains "/var/run/secrets/kubernetes.io/serviceaccount/token" or
     fd.name contains "/var/run/secrets/kubernetes.io/serviceaccount/namespace")
  output: "Service account token accessed (container=%container.name image=%container.image.repository)"
  priority: WARNING
  tags: [k8s, token]
```

### Key Strengths

- **Large rule ecosystem**: 100+ built-in rules maintained by the community
- **Mature project**: CNCF graduated project with enterprise backing
- **Flexible output**: stdout, file, HTTP, gRPC, NATS, Kafka
- **eBPF support**: No kernel module required with modern_ebpf driver

### Limitations

- **Detection only**: Cannot block violations — only generates alerts
- **Signature-dependent**: New attack patterns need new rules
- **High cardinality**: Can generate many false positives without tuning

## Tetragon: eBPF-Based Enforcement and Visibility

Tetragon, from the Cilium project, uses eBPF to trace kernel functions and enforce security policies. It provides both visibility (what's happening) and enforcement (stopping bad behavior).

### Installation

```bash
# Install Tetragon via Helm
helm repo add cilium https://helm.cilium.io
helm install tetragon cilium/tetragon \
  --namespace kube-system \
  --set tetragon.enabled=true \
  --set tetragon.enforce=true \
  -f tetragon-values.yaml
```

```yaml
# tetragon-values.yaml
tetragon:
  enabled: true
  # Enable enforcement mode
  enforce: true
  # Enable process visibility
  processCred: true
  # Enable gRPC API
  enableGRPC: true

cli:
  enabled: true

exportAccumulate:
  maxBatchSize: 100
  expiryTimer: 5s
```

### Tracing Policy Example

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: "detect-credential-access"
spec:
  kprobes:
  - call: "security_file_open"
    syscall: false
    args:
    - index: 0
      type: "file"
    selectors:
    - matchCapabilities:
      - type: Effective
        values:
        - CAP_SYS_ADMIN
      matchBinaries:
      - nsMntIdPathMatcher:
          path: "/run/containerd/io.containerd.runtime.v2.task/k8s.io"
          type: Prefix
    return:
      action: Post
      matchArgs:
      - index: 0
        type: "int"
        values:
        - 0
```

### Enforcing Policy Example

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: "block-sensitive-file-access"
spec:
  kprobes:
  - call: "security_file_open"
    syscall: false
    args:
    - index: 0
      type: "file"
    selectors:
    - matchPaths:
      - path: "/etc/shadow"
      - path: "/etc/kubernetes/pki"
    return:
      action: Post
      matchReturnCodes:
      - values: [0]
```

### Key Strengths

- **eBPF-native**: Deep kernel visibility without kernel modules
- **Enforcement mode**: Can block syscalls and file access
- **Cilium integration**: Works seamlessly with Cilium CNI
- **Low overhead**: eBPF JIT compilation minimizes performance impact

## Choosing the Right Tool

| Scenario | Best Choice | Why |
|---|---|---|
| Block unauthorized processes | KubeArmor | LSM enforcement at container level |
| Detect known attack patterns | Falco | Largest rule set, CNCF graduated |
| eBPF-based visibility + enforcement | Tetragon | Deep kernel tracing with Cilium |
| Compliance (PCI-DSS, SOC2) | Falco + KubeArmor | Detection + enforcement combined |
| Zero-trust container security | KubeArmor | Whitelist-based policies |
| Existing Cilium deployment | Tetragon | Native integration |

## Why Runtime Security is Critical

Container images are scanned before deployment, network policies control traffic between pods, and admission controllers validate configurations. But once a container is running, what prevents an attacker from executing unauthorized commands, accessing sensitive files, or establishing reverse shells?

Runtime security fills this gap by monitoring actual behavior inside containers. Unlike static analysis, runtime security catches:

- **Zero-day exploits**: Attacks that bypass image scanners
- **Supply chain compromises**: Malicious code injected into legitimate images
- **Insider threats**: Authorized users performing unauthorized actions
- **Lateral movement**: Attackers pivoting between containers

For container image scanning before deployment, see our [Trivy vs Grype vs Clair guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/). For Kubernetes policy enforcement, the [Kyverno vs OPA Gatekeeper vs Trivy Operator comparison](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/) covers admission-time security. For eBPF-based networking and observability, check [Cilium vs Pixie vs Tetragon](../ebpf-networking-observability-cilium-pixie-tetragon-guide-2026/).

For container image scanning before deployment, see our [Trivy vs Grype vs Clair guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/). For Kubernetes policy enforcement, the [Kyverno vs OPA Gatekeeper vs Trivy Operator comparison](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/) covers admission-time security. For eBPF-based networking and observability, check [Cilium vs Pixie vs Tetragon](../ebpf-networking-observability-cilium-pixie-tetragon-guide-2026/). For container sandboxing at the runtime level, our [gVisor vs Kata Containers vs Firecracker guide](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/) covers isolation strategies. For network policy enforcement, see [Calico vs Cilium vs Kube-Router](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies-guide-2026/).

## FAQ

### Can KubeArmor, Falco, and Tetragon run simultaneously?

Yes, they serve complementary purposes. Falco provides detection and alerting, KubeArmor enforces container-level policies, and Tetragon provides eBPF-level visibility. Many production deployments run Falco for detection alongside KubeArmor or Tetragon for enforcement.

### Does KubeArmor require a specific container runtime?

KubeArmor supports containerd, CRI-O, and Docker. It works with any Kubernetes distribution that uses these runtimes. The LSM backend (AppArmor, SELinux, or eBPF) depends on the host OS.

### What is the performance overhead of eBPF-based tools?

eBPF programs are JIT-compiled to native code, resulting in minimal overhead (typically 1-3% CPU). Tetragon's overhead is comparable to Cilium's networking eBPF programs. Falco with modern_ebpf has similar overhead to the kernel module approach but avoids kernel module compilation.

### Can I use KubeArmor without AppArmor or SELinux?

KubeArmor supports eBPF LSM as a fallback when neither AppArmor nor SELinux is available. Most modern Linux kernels (5.8+) support eBPF LSM.

### How do I test runtime security policies?

Use a tool like `kubectl run` with a test container that attempts blocked actions (e.g., running `/bin/sh` in a policy-blocked namespace). Check KubeArmor logs with `karmor log` or Falco output for verification.

### Does Falco support Kubernetes audit logs?

Yes. Falco can consume Kubernetes audit logs in addition to system calls. This enables detection of API-level attacks like unauthorized RBAC changes or secret access.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": ""TechArticle",
  "headline": "KubeArmor vs Falco vs Tetragon — Kubernetes Runtime Security Enforcement (2026)",
  "description": "Compare KubeArmor, Falco, and Tetragon for Kubernetes runtime security. Covers LSM enforcement, signature detection, and eBPF-based monitoring.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
