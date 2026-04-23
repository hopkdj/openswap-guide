---
title: "Kyverno vs OPA Gatekeeper vs Trivy Operator: Kubernetes Policy Enforcement 2026"
date: 2026-04-23
tags: ["comparison", "guide", "kubernetes", "security", "policy-as-code", "self-hosted"]
draft: false
description: "Compare Kyverno, OPA Gatekeeper, and Trivy Operator for Kubernetes policy enforcement. Learn installation, YAML policy examples, and which tool fits your cluster governance needs."
---

Kubernetes clusters run dozens of workloads across multiple teams and namespaces. Without policy enforcement, a single misconfigured deployment can expose sensitive data, exhaust resources, or introduce vulnerable container images. Policy-as-code tools solve this by defining rules that automatically validate and mutate Kubernetes resources before they reach the cluster.

This guide compares three open-source policy enforcement solutions for Kubernetes: **Kyverno**, **OPA Gatekeeper**, and **Trivy Operator**. We cover installation, policy writing, real-world configurations, and help you pick the right tool for your environment.

## Why Self-Hosted Kubernetes Policy Enforcement Matters

Cloud-managed Kubernetes services give you the control plane, but they don't enforce your organization's security standards. You need self-hosted policy engines running inside your cluster to:

- **Block non-compliant deployments** — prevent pods running as root, missing resource limits, or using unapproved container registries
- **Auto-mutate resources** — inject sidecar proxies, add default labels, or set resource quotas automatically
- **Scan for vulnerabilities** — continuously check running workloads against CVE databases
- **Audit and report** — generate compliance reports for SOC 2, HIPAA, or internal governance

All three tools covered here run entirely within your cluster — no external SaaS dependency, no data leaving your infrastructure. For related reading on Kubernetes security, see our [Kubernetes hardening guide with kube-bench, Trivy, and Kubescape](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/) and [runtime security monitoring with Falco, osquery, and auditd](../falco-vs-osquery-vs-auditd-self-hosted-runtime-security-guide-2026/).

## Kyverno: Kubernetes-Native Policy Engine

[Kyverno](https://kyverno.io/) (Greek for "govern") is a policy engine designed specifically for Kubernetes. Unlike general-purpose policy languages, Kyverno policies are written as standard Kubernetes YAML resources — no new language to learn.

**GitHub**: [kyverno/kyverno](https://github.com/kyverno/kyverno) — ⭐ 7,664 stars | Language: Go | Last active: April 2026

### Installation

```bash
# Add the Kyverno Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

# Install Kyverno in the kyverno namespace
helm install kyverno kyverno/kyverno \
  --namespace kyverno \
  --create-namespace \
  --set featuresGate.PolicyReports=true
```

### Policy Example: Require Resource Limits

This Kyverno policy enforces that every container must have CPU and memory limits defined:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-resource-limits
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "All containers must have CPU and memory limits set."
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    memory: "?*"
                    cpu: "?*"
```

### Policy Example: Enforce Image Registry

Restrict container images to your private registry only:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
spec:
  validationFailureAction: Enforce
  rules:
    - name: validate-image-registry
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Images must come from the approved registry."
        pattern:
          spec:
            containers:
              - image: "registry.internal.io/*"
```

### Kyverno Mutation Example

Auto-inject a security context into every pod:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-security-context
spec:
  rules:
    - name: add-run-as-non-root
      match:
        any:
          - resources:
              kinds:
                - Pod
      mutate:
        patchStrategicMerge:
          spec:
            securityContext:
              runAsNonRoot: true
            containers:
              - name: "*"
                securityContext:
                  allowPrivilegeEscalation: false
```

### Key Kyverno Features

- **No Rego required** — policies are Kubernetes YAML, making them accessible to platform engineers who already know K8s manifests
- **Built-in mutation** — modify resources at admission time, not just validate
- **Policy reports** — generates Kubernetes `PolicyReport` CRDs for auditing
- **CLI testing** — `kyverno test` command validates policies against sample resources locally
- **Generate rules** — automatically create resources (NetworkPolicies, RBAC) when other resources are created

## OPA Gatekeeper: General-Purpose Policy Framework

[OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/) is a Kubernetes admission controller built on top of the Open Policy Agent (OPA). It uses **Rego**, a declarative policy language, for maximum flexibility.

**GitHub**: [open-policy-agent/gatekeeper](https://github.com/open-policy-agent/gatekeeper) — ⭐ 4,195 stars | Language: Go | Last active: April 2026

### Installation

```bash
# Add the Gatekeeper Helm repository
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update

# Install Gatekeeper
helm install gatekeeper gatekeeper/gatekeeper \
  --namespace gatekeeper-system \
  --create-namespace
```

### ConstraintTemplate: Define the Policy Logic

Gatekeeper uses a two-step approach: first define a `ConstraintTemplate` with Rego logic, then create a `Constraint` to apply it:

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
          some label in input.parameters.labels
          not input.review.object.metadata.labels[label]
          msg := sprintf("Missing required label: %v", [label])
        }
```

### Constraint: Apply the Policy

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-team-label
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Namespace"]
  parameters:
    labels: ["team", "cost-center", "environment"]
```

### Policy Example: Block Privileged Containers

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sdenprivileged
spec:
  crd:
    spec:
      names:
        kind: K8sDenyPrivileged
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sdenyprivileged

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          container.securityContext.privileged == true
          msg := sprintf("Privileged container not allowed: %v", [container.name])
        }
```

### Key OPA Gatekeeper Features

- **Rego language** — extremely expressive, used across the entire OPA ecosystem (not just Kubernetes)
- **Reusable ConstraintTemplates** — write once, apply many times with different parameters
- **Audit functionality** — periodically evaluates all existing resources against policies
- **External data sources** — Rego can query external APIs for dynamic policy decisions
- **Large community** — OPA is a CNCF graduated project with extensive documentation and examples

## Trivy Operator: Security-Focused Kubernetes Operator

[Trivy Operator](https://github.com/aquasecurity/trivy-operator) extends the popular Trivy scanner into a Kubernetes Operator. Instead of admission-time policy enforcement, it runs as a background operator that continuously scans workloads for vulnerabilities, misconfigurations, and exposed secrets.

**GitHub**: [aquasecurity/trivy-operator](https://github.com/aquasecurity/trivy-operator) — ⭐ 1,851 stars | Language: Go | Last active: April 2026

### Installation

```bash
# Add the Aqua Security Helm repository
helm repo add aquasecurity https://aquasecurity.github.io/helm-charts/
helm repo update

# Install Trivy Operator
helm install trivy-operator aquasecurity/trivy-operator \
  --namespace trivy-system \
  --create-namespace \
  --set trivy.ignoreUnfixed=true \
  --set operator.scanJobs.ttl=30s
```

### Scanning Configuration

Configure scan targets and schedules via Helm values:

```yaml
# trivy-operator-values.yaml
operator:
  scanJobs:
    ttl: 30s
    concurrentScanJobsLimit: 10
    scanJobTolerations:
      - key: "trivy"
        operator: "Exists"

trivy:
  ignoreUnfixed: true
  severity: CRITICAL,HIGH
  securityCheck: vuln,config,secret
  mode: Standalone
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 1Gi
```

```bash
helm upgrade trivy-operator aquasecurity/trivy-operator \
  --namespace trivy-system \
  -f trivy-operator-values.yaml
```

### Viewing Scan Results

Trivy Operator stores results as Kubernetes Custom Resources:

```bash
# List vulnerability reports
kubectl get vulnerabilityreports --all-namespaces

# Describe a specific report
kubectl describe vulnerabilityreport \
  deployment-myapp-myapp \
  -n production

# View config audit reports
kubectl get configauditreports --all-namespaces

# View exposed secret reports
kubectl get exposedsecretreports --all-namespaces
```

### Policy Integration with Kyverno/Gatekeeper

Trivy Operator can feed scan results into Kyverno or Gatekeeper for enforcement:

```yaml
# Kyverno policy: block deployments with CRITICAL vulnerabilities
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: block-critical-vulnerabilities
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-vulnerability-scan
      match:
        any:
          - resources:
              kinds:
                - Deployment
      validate:
        message: "Deployment has CRITICAL vulnerabilities. Fix before deploying."
        deny:
          conditions:
            any:
              - key: "{{ request.object.metadata.annotations.\"trivy-operator.aquasecurity.github.io/critical-count\" }}"
                operator: GreaterThanOrEquals
                value: 1
```

### Key Trivy Operator Features

- **Continuous scanning** — runs background scans on a schedule, not just at admission time
- **Multiple scan types** — vulnerabilities (CVEs), misconfigurations, exposed secrets, and SBOM generation
- **No policy language needed** — uses Trivy's built-in scanning rules; no Rego or YAML policy authoring
- **Kubernetes-native results** — stores findings as CRDs viewable with `kubectl`
- **Integrates with existing pipelines** — works alongside admission controllers for defense in depth

## Comparison: Kyverno vs OPA Gatekeeper vs Trivy Operator

| Feature | Kyverno | OPA Gatekeeper | Trivy Operator |
|---------|---------|----------------|----------------|
| **Primary purpose** | Admission-time policy enforcement | Admission-time policy enforcement | Continuous security scanning |
| **Policy language** | Kubernetes YAML | Rego | Built-in Trivy rules |
| **Learning curve** | Low (K8s-native) | High (new language) | Low (configuration only) |
| **Mutation support** | Yes (built-in) | No (validation only) | No |
| **Mutation types** | Strategic merge, JSON patches | N/A | N/A |
| **Admission control** | Yes | Yes | No |
| **Background scanning** | Yes (via Kyverno Scanner) | Yes (audit mode) | Yes (primary mode) |
| **Vulnerability scanning** | Via external plugins | Via external plugins | Built-in |
| **Config audit** | Via policies | Via policies | Built-in (OPA/Rego under the hood) |
| **Secret detection** | Via policies | Via policies | Built-in |
| **SBOM generation** | No | No | Yes |
| **GitHub stars** | 7,664 | 4,195 | 1,851 |
| **CNCF status** | Sandbox | Graduated | Sandbox |
| **Language** | Go | Go (Rego is Go-based) | Go |
| **Helm installable** | Yes | Yes | Yes |
| **Best for** | Teams already using K8s YAML | Multi-platform policy needs | Security scanning and compliance |

## When to Use Each Tool

### Choose Kyverno When

- Your team is already comfortable writing Kubernetes YAML manifests
- You need **mutation** policies (auto-inject sidecars, set defaults, add labels)
- You want the fastest path from zero to enforced policies
- You prefer reading policies in familiar K8s resource format over learning a new language

Kyverno is the most approachable option for platform teams managing Kubernetes clusters. The YAML-based policy format means any engineer who can write a Deployment can also write a Kyverno policy.

### Choose OPA Gatekeeper When

- You need policies across **multiple platforms** (Kubernetes, APIs, CI/CD, Terraform)
- Your organization already uses Rego for other OPA integrations
- You need complex policy logic that requires Rego's expressive power
- You want a CNCF graduated project with the widest ecosystem support

OPA Gatekeeper shines when policy enforcement extends beyond Kubernetes. The same Rego policies can gate Terraform plans, validate API requests, and control service mesh routing.

### Choose Trivy Operator When

- Your priority is **security scanning**, not admission-time policy enforcement
- You want continuous, scheduled scanning of all running workloads
- You need vulnerability reports, SBOMs, and secret detection out of the box
- You want to layer scanning on top of existing admission controllers

Trivy Operator is complementary to Kyverno and Gatekeeper, not a replacement. Many teams run Trivy Operator for continuous scanning AND Kyverno or Gatekeeper for admission-time enforcement — a defense-in-depth approach. For securing the secrets these policies protect, see our [Kubernetes secrets management guide with External Secrets Operator, Sealed Secrets, and Vault](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/).

## Combined Deployment: Best Practice Architecture

For production clusters, the recommended architecture combines all three:

```yaml
# kyverno-values.yaml
featuresGate:
  PolicyReports: true
admissionController:
  replicas: 3
backgroundController:
  replicas: 2
reportsController:
  replicas: 2
```

```bash
# Install all three in separate namespaces
helm install kyverno kyverno/kyverno \
  --namespace kyverno --create-namespace \
  -f kyverno-values.yaml

helm install gatekeeper gatekeeper/gatekeeper \
  --namespace gatekeeper-system --create-namespace

helm install trivy-operator aquasecurity/trivy-operator \
  --namespace trivy-system --create-namespace \
  --set trivy.ignoreUnfixed=true \
  --set trivy.securityCheck=vuln,config,secret
```

In this setup:
- **Kyverno** handles admission-time validation and mutation (resource limits, image registries, security contexts)
- **Gatekeeper** handles cross-cutting policies shared with other infrastructure (compliance rules in Rego)
- **Trivy Operator** runs continuous background scans for vulnerabilities, misconfigurations, and secrets

## FAQ

### What is the difference between Kyverno and OPA Gatekeeper?

Kyverno uses Kubernetes YAML to define policies, making it easier for teams already familiar with K8s manifests. OPA Gatekeeper uses Rego, a general-purpose declarative policy language that works across multiple platforms beyond Kubernetes. Kyverno supports mutation (changing resources at admission time); Gatekeeper is validation-only.

### Can I run Kyverno and Gatekeeper together?

Yes. Both are admission controllers that register webhooks with the Kubernetes API server. You can configure them to run in different orders using `failurePolicy` and webhook ordering. Many organizations run both — Kyverno for mutation and simple validation, Gatekeeper for complex Rego-based policies.

### Does Trivy Operator block deployments?

No. Trivy Operator is a background scanning tool, not an admission controller. It continuously scans running workloads and stores results as Kubernetes Custom Resources. To block deployments based on scan results, pair Trivy Operator with Kyverno or Gatekeeper using policies that read the scan reports.

### Which tool should I start with for Kubernetes security?

If your goal is to **prevent bad configurations from being deployed**, start with Kyverno — it has the lowest learning curve and covers most common enforcement scenarios. If your goal is to **find vulnerabilities in running workloads**, start with Trivy Operator. For organizations needing policy consistency across Kubernetes, APIs, and IaC, OPA Gatekeeper is the best long-term investment.

### Do these tools work with managed Kubernetes (EKS, GKE, AKS)?

Yes. All three tools are installed as Kubernetes resources (Helm charts) and work on any conformant Kubernetes cluster, including managed services like Amazon EKS, Google GKE, and Azure AKS. The only requirement is that your cluster supports admission webhooks, which all managed providers support.

### How do I write custom scanning rules for Trivy Operator?

Trivy Operator uses Trivy's built-in scanning engines. For custom config audit policies, you can write Rego policies that Trivy evaluates. Place them in a ConfigMap with the label `trivy-operator.policy.kind=ConfigAudit` and the operator will pick them up. Vulnerability scanning uses the Trivy vulnerability database, which updates automatically.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kyverno vs OPA Gatekeeper vs Trivy Operator: Kubernetes Policy Enforcement 2026",
  "description": "Compare Kyverno, OPA Gatekeeper, and Trivy Operator for Kubernetes policy enforcement. Learn installation, YAML policy examples, and which tool fits your cluster governance needs.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
