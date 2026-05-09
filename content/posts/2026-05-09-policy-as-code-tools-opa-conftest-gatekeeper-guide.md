---
title: "Best Self-Hosted Policy as Code Tools 2026: OPA vs Conftest vs Gatekeeper"
date: "2026-05-09"
tags: ["policy-as-code", "security", "compliance", "opa", "conftest", "kubernetes", "devops"]
draft: false
---

Policy as Code is the practice of defining, testing, and enforcing organizational policies using machine-readable configuration files rather than manual processes. Instead of relying on human reviewers to check compliance, Policy as Code engines automatically evaluate configurations, infrastructure, and application behavior against defined rules.

In this guide, we compare three leading open-source Policy as Code tools built on the Open Policy Agent (OPA) ecosystem: **OPA** (the core policy engine), **Conftest** (CLI-based policy testing), and **OPA Gatekeeper** (Kubernetes-native policy enforcement).

## What Is Policy as Code?

Policy as Code transforms compliance from a reactive checklist into a proactive, automated process:

- **Declarative rules**: Policies are written as code (Rego language) that can be version-controlled and tested
- **Automated enforcement**: Policies are evaluated automatically during CI/CD pipelines or at runtime
- **Consistent application**: The same policies apply across all environments and teams
- **Audit trail**: Every policy evaluation is logged and traceable
- **Shift-left security**: Catch violations before deployment, not after

## Open Policy Agent (OPA)

**Stars**: 11,699+ | **Language**: Go | **License**: Apache 2.0 | **GitHub**: [open-policy-agent/opa](https://github.com/open-policy-agent/opa)

OPA is the core policy engine — a general-purpose policy evaluation engine that integrates with almost any system via its REST API or as a Go library.

### Architecture

OPA operates as a sidecar or embedded service:

1. Your application sends an input query (JSON) to OPA
2. OPA evaluates the input against loaded Rego policies
3. OPA returns a decision (allow/deny) with optional data

### Key Features

- **General-purpose**: Works with any input format (JSON, YAML, HTTP requests)
- **Rego policy language**: Declarative, logic-based query language
- **REST API**: Evaluate policies via HTTP requests
- **Bundle support**: Package and distribute policy bundles
- **Decision logs**: Built-in logging for audit compliance

### Installation

```bash
# Install OPA
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static
chmod +x opa
sudo mv opa /usr/local/bin/
```

### Example Policy (Rego)

```rego
package authz

default allow = false

allow {
    input.method == "GET"
    input.user.role == "admin"
}

allow {
    input.method == "GET"
    input.path[0] == "public"
}
```

Evaluate a policy:

```bash
opa eval --data authz.rego --input request.json "data.authz.allow"
```

### Docker Compose

```yaml
version: "3.8"
services:
  opa:
    image: openpolicyagent/opa:latest
    ports:
      - "8181:8181"
    volumes:
      - ./policies:/policies
    command:
      - "run"
      - "--server"
      - "--addr=:8181"
      - "/policies"
    restart: unless-stopped
```

## Conftest

**Stars**: 3,166+ | **Language**: Go | **License**: Apache 2.0 | **GitHub**: [open-policy-agent/conftest](https://github.com/open-policy-agent/conftest)

Conftest is a CLI tool that uses OPA's Rego language to test configuration files (Kubernetes manifests, Terraform, Dockerfiles) against policies before deployment.

### Key Features

- **CI/CD integration**: Run as a step in your pipeline
- **Multiple input formats**: Kubernetes YAML, Terraform HCL, Dockerfiles, JSON
- **Policy sharing**: Pull policies from OCI registries
- **Multi-file support**: Test multiple configuration files at once
- **Structured output**: JUnit, JSON, and TAP formats for CI tools

### Installation

```bash
# Install Conftest
curl -L -o conftest.tar.gz https://github.com/open-policy-agent/conftest/releases/download/v0.56.0/conftest_0.56.0_Linux_x86_64.tar.gz
tar -xzf conftest.tar.gz
sudo mv conftest /usr/local/bin/
```

### Example Policy

```rego
package main

deny[msg] {
    input.kind == "Deployment"
    not input.spec.template.spec.containers[_].securityContext.readOnlyRootFilesystem
    msg = "Containers must set readOnlyRootFilesystem to true"
}

deny[msg] {
    input.kind == "Deployment"
    input.spec.template.spec.containers[_].securityContext.runAsRoot == true
    msg = "Containers must not run as root"
}
```

Test Kubernetes manifests:

```bash
conftest test deployment.yaml --policy policies/
# Output: 2 tests, 2 passed, 0 warnings, 2 failures
```

Test Terraform plans:

```bash
conftest test tfplan.json --policy terraform-policies/ --input terraformplan
```

### Docker Compose

```yaml
version: "3.8"
services:
  conftest:
    image: openpolicyagent/conftest:latest
    volumes:
      - ./configs:/configs
      - ./policies:/policies
    working_dir: /configs
    command: ["test", "--policy", "/policies", "deployment.yaml"]
```

## OPA Gatekeeper

**Stars**: Part of OPA project | **Language**: Go | **License**: Apache 2.0 | **GitHub**: [open-policy-agent/gatekeeper](https://github.com/open-policy-agent/gatekeeper)

OPA Gatekeeper is a Kubernetes admission controller that enforces OPA policies at the cluster level. It blocks non-compliant resources from being created or modified.

### Key Features

- **Admission webhook**: Intercepts Kubernetes API requests
- **CRD-based policies**: Define constraints as Kubernetes Custom Resources
- **Audit mode**: Scan existing resources for violations
- **Constraint templates**: Reusable policy templates with parameterized rules
- **Mutation support**: Automatically modify resources to comply with policies

### Installation

```bash
# Install Gatekeeper via Helm
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm install gatekeeper/gatekeeper --name-template=gatekeeper --namespace gatekeeper-system --create-namespace
```

### Example Constraint

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: ns-must-have-labels
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Namespace"]
  parameters:
    labels: ["app", "team", "environment"]
```

### Docker Compose (for local testing with kind/minikube)

```yaml
version: "3.8"
services:
  kind-cluster:
    image: kindest/node:v1.29.0
    privileged: true
    volumes:
      - ./gatekeeper-manifests:/manifests
    command: ["--wait", "5m"]
```

For production, deploy directly to your Kubernetes cluster:

```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
```

## Comparison Table

| Feature | OPA | Conftest | OPA Gatekeeper |
|---------|-----|----------|----------------|
| **Stars** | 11,699+ | 3,166+ | Part of OPA |
| **Type** | Policy engine | CLI tool | Kubernetes controller |
| **Deployment** | Sidecar/daemon | CI/CD pipeline | Admission webhook |
| **Enforcement** | Application-level | Pre-deployment | Cluster-level |
| **Policy Language** | Rego | Rego | Rego |
| **Input Format** | JSON | YAML, HCL, JSON | Kubernetes API objects |
| **Real-time** | Yes | No (pipeline only) | Yes (admission) |
| **Audit Mode** | Manual | No | Yes (built-in) |
| **Mutation** | No | No | Yes |
| **Best For** | API authorization | CI/CD validation | Kubernetes governance |

## Choosing the Right Policy Tool

### Use OPA when:
- You need general-purpose policy evaluation for custom applications
- You want to enforce policies via REST API calls
- You are building authorization systems for microservices
- You need fine-grained access control decisions

### Use Conftest when:
- You want to catch policy violations in CI/CD pipelines
- You need to validate Terraform, Dockerfiles, or Kubernetes manifests before deployment
- You want policy testing integrated into pull request workflows
- You need structured test output for CI tools

### Use OPA Gatekeeper when:
- You need cluster-wide Kubernetes policy enforcement
- You want to block non-compliant resources at the API level
- You need to audit existing cluster resources for violations
- You want to enforce pod security standards, resource quotas, or naming conventions

## Why Self-Host Policy as Code?

**Regulatory compliance**: Financial services, healthcare, and government organizations must demonstrate consistent policy enforcement. Self-hosted Policy as Code tools provide audit logs, version-controlled policies, and automated compliance checks that satisfy auditors.

**Prevent configuration drift**: Manual policy enforcement inevitably leads to drift. Policy as Code ensures every resource — whether created by a developer, a CI/CD pipeline, or an automated system — is evaluated against the same rules.

**Faster deployments**: Instead of waiting for security reviews, developers can self-serve. Policies run automatically in the pipeline, and developers get immediate feedback on violations before the code reaches production.

**Centralized governance**: Define policies once and enforce them across all teams, environments, and cloud providers. A single `ContainerMustRunAsNonRoot` policy applies to Kubernetes, Docker Compose, and Terraform deployments equally.

**Cost control**: Enforce resource quotas, prevent over-provisioned instances, and automatically tag resources for cost attribution. Policies can block deployments that exceed budget thresholds or lack proper cost center labels.

For Kubernetes policy enforcement, see our [Kyverno vs OPA Gatekeeper vs Trivy Operator guide](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/). For container security hardening, check our [Docker Bench vs Trivy vs Checkov comparison](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide/). For supply chain security, read our [Cosign vs Notation vs in-toto guide](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/).

## FAQ

### What is Rego and why does every tool use it?

Rego is OPA's declarative policy language. It is designed for expressing rules about structured data (JSON). Rego policies describe what should be true, not how to check it — the OPA engine handles evaluation. Because all three tools in this guide are built on OPA, they share the same policy language, enabling policy reuse across different enforcement contexts.

### Can I use Policy as Code without Kubernetes?

Yes. OPA works as a standalone service that any application can query via REST API. Conftest runs in CI/CD pipelines without any Kubernetes dependency. Gatekeeper is the only tool that requires Kubernetes. If you are not using Kubernetes, OPA and Conftest are your best options.

### How do I write my first Rego policy?

Start with simple allow/deny rules. A basic Rego policy looks like:

```rego
package example
default allow = false
allow { input.user == "admin" }
```

This policy allows requests where the user is "admin" and denies everything else. The OPA documentation includes a comprehensive tutorial and policy library. Conftest also provides example policies for common scenarios.

### Can Conftest test Dockerfiles?

Yes. Conftest can parse Dockerfiles and evaluate them against Rego policies. For example, you can enforce that no image uses the `latest` tag, that a non-root user is specified, or that health checks are defined. Use `--input dockerfile` when testing Dockerfiles.

### Does Gatekeeper support policy mutation?

Yes. Gatekeeper's mutation feature allows it to automatically modify resources to comply with policies. For example, it can inject sidecar containers, add labels, or set resource limits on pods that lack them. This is configured through `Assign` and `AssignImage` custom resources.

### How do I distribute policies across teams?

Use OPA's bundle feature. Package your policies as an OCI artifact and push it to a container registry. Teams can pull the bundle using `opa pull` or Conftest's `--policy` flag with OCI references. This enables centralized policy authoring with decentralized enforcement.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted Policy as Code Tools 2026: OPA vs Conftest vs Gatekeeper",
  "description": "Compare OPA, Conftest, and OPA Gatekeeper for self-hosted policy as code — with Rego examples, Docker Compose configs, and Kubernetes integration.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
