---
title: "Self-Hosted Kubernetes Admission Controllers: Kyverno vs OPA Gatekeeper vs Kubewarden (2026)"
date: "2026-05-16"
tags: ["kubernetes", "admission-controller", "policy-as-code", "security", "kyverno", "opa", "kubewarden"]
draft: false
---

Kubernetes admission controllers are the gatekeepers of your cluster — they intercept API requests before objects are persisted, allowing you to enforce security policies, validate configurations, and mutate resources automatically. In this guide, we compare three leading open-source admission controller frameworks: **Kyverno**, **OPA Gatekeeper**, and **Kubewarden**.

## What Are Kubernetes Admission Controllers?

Admission controllers are plugins that intercept requests to the Kubernetes API server prior to persistence of the object, but after the request is authenticated and authorized. There are two types:

- **ValidatingAdmissionWebhook** — rejects requests that violate policies
- **MutatingAdmissionWebhook** — modifies incoming requests (e.g., adding sidecar containers, setting default labels)

While Kubernetes ships with built-in admission controllers (like `NamespaceLifecycle`, `LimitRanger`, `PodSecurity`), custom admission controllers let you define organization-specific policies using declarative configuration.

## Comparison Overview

| Feature | Kyverno | OPA Gatekeeper | Kubewarden |
|---------|---------|----------------|------------|
| **GitHub Stars** | 7,700+ | 4,200+ | 150+ (policy-server) |
| **Policy Language** | YAML (native K8s) | Rego (OPA) | WebAssembly (Rust, Go, C) |
| **Mutating Policies** | Yes (native) | Limited | Yes (via WASM) |
| **Generating Resources** | Yes (Generate rules) | No | No |
| **Learning Curve** | Low (YAML) | High (Rego) | Medium (WASM) |
| **CNCF Status** | Graduated | Graduated | Sandbox (Rancher) |
| **Policy Library** | 200+ policies | 100+ libraries | 50+ policies |
| **OCI Policy Distribution** | Yes | Yes | Yes |
| **Cluster-wide Reports** | Built-in (PolicyReport) | Via ConstraintTemplate audit | Via audit controller |
| **Best For** | Teams wanting native K8s UX | Complex policy logic | Multi-language policy authors |

## Kyverno: Kubernetes-Native Policy Engine

Kyverno is a policy engine designed specifically for Kubernetes. It uses native Kubernetes resource types (no new language to learn) and supports validating, mutating, and generating policies.

### Architecture

Kyverno runs as a dynamic admission controller within your cluster. Policies are defined as `ClusterPolicy` or `Policy` Custom Resource Definitions (CRDs), evaluated by webhooks registered with the API server.

### Installation

```yaml
# Install Kyverno via Helm
# helm repo add kyverno https://kyverno.github.io/kyverno/
# helm install kyverno kyverno/kyverno -n kyverno --create-namespace
```

### Docker Compose (for local testing)

```yaml
version: "3.8"
services:
  kyverno:
    image: ghcr.io/kyverno/kyverno:v1.12.0
    ports:
      - "9443:9443"
    environment:
      - KYVERMO_NAMESPACE=kyverno
    volumes:
      - ./policies:/policies
```

### Sample Policy

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest-tag
  annotations:
    policies.kyverno.io/title: Disallow Latest Tag
    policies.kyverno.io/category: Best Practices
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-image-tag
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Using 'latest' tag is not allowed"
        pattern:
          spec:
            containers:
              - image: "!*:latest"
```

Kyverno's strength is its YAML-native approach. If you know Kubernetes manifests, you already know how to write Kyverno policies.

## OPA Gatekeeper: General-Purpose Policy with Rego

OPA (Open Policy Agent) Gatekeeper brings the general-purpose Rego policy language to Kubernetes. Rego is powerful but has a steeper learning curve than YAML.

### Installation

```yaml
# Install Gatekeeper via Helm
# helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
# helm install gatekeeper gatekeeper/gatekeeper -n gatekeeper-system --create-namespace
```

### Docker Compose (for local testing)

```yaml
version: "3.8"
services:
  gatekeeper:
    image: openpolicyagent/gatekeeper:v3.17.0
    ports:
      - "8443:8443"
    command: ["--audit-interval=60"]
    volumes:
      - ./constraints:/constraints
      - ./templates:/templates
```

### Sample ConstraintTemplate

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        violation[{"msg": msg}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("Missing required labels: %v", [missing])
        }
```

OPA Gatekeeper excels when you need complex, logic-heavy policies that go beyond simple pattern matching. Rego's expressiveness handles nested conditions, set operations, and data lookups.

## Kubewarden: WebAssembly-Powered Policies

Kubewarden (by SUSE/Rancher) uses WebAssembly as its policy execution engine. Policies are written in Rust, Go, or any language that compiles to WASM, then distributed via OCI registries.

### Installation

```yaml
# Install Kubewarden via Helm
# helm repo add kubewarden https://charts.kubewarden.io
# helm install kubewarden-crds kubewarden/kubewarden-crds -n kubewarden --create-namespace
# helm install kubewarden kubewarden/kubewarden-controller -n kubewarden
```

### Docker Compose (policy-server for testing)

```yaml
version: "3.8"
services:
  policy-server:
    image: ghcr.io/kubewarden/policy-server:1.19.0
    ports:
      - "8443:8443"
    environment:
      - POLICY_SERVER_PORT=8443
    volumes:
      - ./policies.yml:/policies/policies.yml
    command: ["--policies-path", "/policies/policies.yml"]
```

### Sample Policy (YAML referencing a WASM policy)

```yaml
apiVersion: policies.kubewarden.io/v1
kind: ClusterAdmissionPolicy
metadata:
  name: pod-privileged
spec:
  module: registry://ghcr.io/kubewarden/policies/pod-privileged:v0.5.0
  rules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      resources: ["pods"]
      operations: ["CREATE", "UPDATE"]
  mutating: false
  settings:
    skip_init_containers: true
    skip_ephemeral_containers: false
```

Kubewarden's WASM approach offers sandboxed policy execution with multi-language support. Policies are portable across platforms and benefit from WebAssembly's security model.

## Why Use Admission Controllers?

Admission controllers are the foundation of Kubernetes security and governance. Without them, you rely entirely on human diligence to follow best practices — which rarely scales beyond a handful of developers.

**Security enforcement** is the primary driver. Admission controllers block dangerous configurations before they reach the cluster: preventing privileged containers, enforcing read-only root filesystems, blocking latest tags, and requiring resource limits. For compliance frameworks like SOC 2, PCI DSS, and HIPAA, admission controllers provide automated enforcement that auditors can verify.

**Operational consistency** is another critical benefit that admission controllers provide. In large organizations with dozens of teams deploying to shared clusters, admission controllers serve as automated governance that ensures every workload meets organizational standards. Without them, one team might deploy privileged containers while another follows security best practices, creating an inconsistent security posture that is difficult to audit and maintain. Admission controllers enforce uniformity — every namespace, every deployment, every pod follows the same rules. This is particularly important for organizations pursuing compliance certifications where consistent configuration is a requirement.

**Cost optimization** is another benefit. Policies can enforce resource requests and limits, prevent over-provisioned workloads, and automatically add cleanup labels to temporary resources. Teams that implement admission controllers typically see 15-30% reductions in wasted compute resources.

**Developer experience** improves when policies provide clear, actionable feedback. Instead of a cryptic API error, developers see "Container image must use a pinned tag, not 'latest'" with guidance on how to fix it. Kyverno's native YAML approach is particularly effective here — developers already understand Kubernetes manifests.

For teams managing multiple clusters, admission controllers ensure consistent policy enforcement across all environments. See our [policy-as-code tools comparison](../2026-05-09-policy-as-code-tools-opa-conftest-gatekeeper-guide/) for broader policy management options, and our [container security hardening guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/) for complementary security practices.

## Choosing the Right Admission Controller

| Scenario | Recommended Tool |
|----------|-----------------|
| **New to Kubernetes policies** | Kyverno — YAML-native, gentle learning curve |
| **Complex conditional logic** | OPA Gatekeeper — Rego's expressiveness handles edge cases |
| **Multi-language policy teams** | Kubewarden — Write policies in Rust, Go, or any WASM-target language |
| **Need mutating policies** | Kyverno — strongest native mutation support |
| **Existing OPA investment** | OPA Gatekeeper — reuse Rego policies across services |
| **Rancher ecosystem** | Kubewarden — native integration with Rancher |

## FAQ

### What is the difference between validating and mutating admission controllers?
Validating admission controllers check incoming requests against policies and either accept or reject them. Mutating admission controllers modify the request before it is processed — for example, adding default resource limits, injecting sidecar containers, or setting required labels.

### Can I run multiple admission controllers simultaneously?
Yes. Kubernetes supports multiple admission webhooks. Each webhook is evaluated in order, and a request must pass all validating webhooks to be accepted. However, the order of evaluation matters — a mutating webhook may change the request before a validating webhook sees it.

### Do admission controllers impact API server performance?
Admission webhooks add latency to API requests because the API server must wait for the webhook response. Typical latency is 10-50ms per webhook. For most clusters, this is negligible. For high-throughput clusters, consider using in-process controllers (like Kyverno) rather than external webhooks.

### Can admission controllers be bypassed?
Admission controllers apply to all API requests unless the requesting user or service account is explicitly excluded. System components (like the kubelet) can be exempted, but regular users cannot bypass admission policies. However, if the admission controller pod crashes or becomes unreachable, the API server behavior depends on the `failurePolicy` setting — it can either fail-closed (reject) or fail-open (allow).

### How do I test admission controller policies before enforcing them?
All three tools support an audit or dry-run mode. Kyverno uses `validationFailureAction: Audit` to log violations without blocking. OPA Gatekeeper runs Constraint violations in audit mode. Kubewarden can be deployed with `failurePolicy: Ignore` to log without blocking. Always test in audit mode before switching to enforce.

### What happens if the admission controller pod goes down?
Kubernetes uses the `failurePolicy` field to determine behavior. With `Fail`, the API request is rejected (fail-closed). With `Ignore`, the request proceeds (fail-open). For production clusters, `Fail` is recommended for security policies, with appropriate timeout settings to avoid cascading failures.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Admission Controllers: Kyverno vs OPA Gatekeeper vs Kubewarden (2026)",
  "description": "Compare three leading Kubernetes admission controller frameworks — Kyverno, OPA Gatekeeper, and Kubewarden — with installation guides, policy examples, and Docker Compose configs.",
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
