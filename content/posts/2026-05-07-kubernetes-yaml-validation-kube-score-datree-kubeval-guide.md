---
title: "Kubernetes YAML Validation: kube-score vs Datree vs kubeval (2026 Guide)"
date: 2026-05-07
tags: ["kubernetes", "yaml-validation", "kube-score", "datree", "kubeval", "self-hosted", "devops", "guide"]
draft: false
---

Kubernetes configuration files are notoriously error-prone. A single typo in a YAML manifest can cause pod scheduling failures, security misconfigurations, or resource waste. Three popular tools help catch these issues before deployment: **kube-score**, **Datree**, and **kubeval**.

In this guide, we compare these Kubernetes YAML validation tools, covering their rule sets, CI/CD integration, self-hosted deployment, and how they fit into a robust GitOps pipeline.

## Why Validate Kubernetes YAML?

Kubernetes accepts YAML configurations that are syntactically valid but semantically incorrect. Common issues include:

- **Missing resource limits/requests**: Pods without limits can starve other workloads
- **Security misconfigurations**: Containers running as root, missing security contexts
- **Deprecated API versions**: Manifests targeting removed Kubernetes API versions
- **Missing probes**: Pods without liveness/readiness probes can cause cascading failures
- **Network policy gaps**: Services exposed without proper network restrictions
- **Replica count issues**: Deployments with `replicas: 1` in production without PDBs

Validation tools catch these issues during CI/CD or even in pre-commit hooks, preventing bad configurations from reaching your cluster.

## Tool Comparison Overview

| Feature | kube-score | Datree | kubeval |
|---------|-----------|--------|---------|
| **GitHub Stars** | 3,000+ | 6,300+ | 3,200+ |
| **License** | MIT | Apache 2.0 | MIT |
| **Language** | Go | Go | Go |
| **Validation Engine** | Custom rules | Policy library | Kubernetes JSON Schema |
| **Schema Validation** | No | Yes | Yes (official K8s schemas) |
| **Best Practice Checks** | Yes (30+ rules) | Yes (100+ policies) | No (schema only) |
| **Custom Policies** | Yes (Go plugins) | Yes (YAML policies) | No |
| **CI/CD Integration** | GitHub Action, CLI | GitHub Action, CLI, Helm plugin | CLI, Helm plugin |
| **Output Formats** | Text, SARIF, JUnit | Text, JSON, SARIF | Text, JSON |
| **Self-Hosted** | Yes (CLI tool) | Yes (CLI + local policies) | Yes (CLI tool) |
| **K8s Version Support** | Latest + N-2 | Multiple versions | Multiple versions |
| **Docker Image** | `zegl/kube-score` | `datree/datree` | `instrumenta/kubeval` |

## kube-score: Kubernetes Object Analysis

kube-score performs static code analysis on Kubernetes YAML files, checking for reliability and security best practices. It provides actionable recommendations rather than just pass/fail results.

**Strengths:**
- 30+ built-in checks covering reliability, security, and networking
- Scoring system gives you a clear quality metric for your manifests
- SARIF output integrates with GitHub Security tab and IDEs
- Active development with regular rule updates
- Lightweight CLI — no server component needed
- Checks for: resource limits, security contexts, pod disruption budgets, network policies, probe configuration, and more

**Limitations:**
- No schema validation (doesn't check field names or types)
- Custom rules require Go programming
- No built-in policy management dashboard

### Docker Compose / Local Usage

kube-score runs as a standalone CLI, but you can containerize it:

```yaml
version: "3.8"
services:
  kube-score:
    image: zegl/kube-score:latest
    volumes:
      - ./k8s:/k8s:ro
    working_dir: /k8s
    command: ["score", "./deployment.yaml", "./service.yaml"]
```

Direct CLI usage:

```bash
# Install via Go
go install github.com/zegl/kube-score/v2/cmd/kube-score@latest

# Score a single file
kube-score score deployment.yaml

# Score all YAML files in a directory
kube-score score ./k8s/**/*.yaml

# Output in SARIF format for GitHub
kube-score score --output-format sarif ./k8s/ > results.sarif

# Set minimum score threshold (fail if below 80)
kube-score score --fail-threshold 80 ./k8s/
```

### Example Output

```
apps/v1/Deployment my-app  🤔 MEDIUM
  [WARNING] Container my-app does not set a security context
    · Set securityContext.runAsNonRoot to true
    · Set securityContext.readOnlyRootFilesystem to true
  [WARNING] Container my-app does not have resource limits
    · Set resources.limits.cpu and resources.limits.memory
```

## Datree: Kubernetes Policy Enforcement

Datree provides comprehensive Kubernetes policy enforcement with 100+ built-in policies, custom policy support, and integration with the entire development workflow from local IDE to production deployment.

**Strengths:**
- 100+ built-in policies covering security, reliability, and best practices
- Custom YAML-based policy definitions
- GitHub Action with pull request comments
- Helm plugin for validation during `helm install`/`helm upgrade`
- Local CLI for pre-commit hooks
- Policy-as-code approach with YAML configuration
- Detailed remediation guidance for each failed check

**Limitations:**
- Last major release was in 2024 — community activity has slowed
- Some advanced features require cloud dashboard
- Policy customization is YAML-based (less flexible than code)

### Docker Compose / Local Usage

```yaml
version: "3.8"
services:
  datree:
    image: datree/datree:latest
    volumes:
      - ./k8s:/k8s:ro
    working_dir: /k8s
    command: ["test", "*.yaml", "--policy-config", "policies.yaml"]
```

Custom policy configuration:

```yaml
# policies.yaml
apiVersion: v1
kind: DatreePolicy
metadata:
  name: my-org-policy
rules:
  - identifier: CONTAINER_MISSING_RESOURCE_LIMITS
    message: "All containers must define resource limits"
    defaultResponse: fail
  - identifier: CONTAINER_MISSING_CPU_REQUEST
    message: "CPU requests are required for cost management"
    defaultResponse: warning
```

CI/CD integration with GitHub Actions:

```yaml
name: Kubernetes Validation
on: [pull_request]
jobs:
  datree:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Datree
        uses: datreeio/action-datree@main
        with:
          path: "k8s/**/*.yaml"
          policy: default
```

## kubeval: Kubernetes Schema Validation

kubeval validates Kubernetes YAML files against the official Kubernetes JSON schema. It catches typos, invalid field names, and incorrect data types — the kinds of errors that cause `kubectl apply` to fail.

**Strengths:**
- Uses official Kubernetes JSON schemas — validates against the actual API spec
- Supports multiple Kubernetes versions for compatibility testing
- Catches field name typos, wrong data types, and missing required fields
- Simple, focused tool that does one thing well
- Works as a pre-commit hook or CI step
- Supports Helm template output validation

**Limitations:**
- Schema validation only — doesn't check best practices or security
- No custom rule support
- Development has slowed; Kubernetes schema updates may lag
- Does not detect logical errors (e.g., missing resource limits)

### Docker Compose / Local Usage

```yaml
version: "3.8"
services:
  kubeval:
    image: instrumenta/kubeval:latest
    volumes:
      - ./k8s:/k8s:ro
    working_dir: /k8s
    command: ["--strict", "deployment.yaml"]
```

Direct CLI usage:

```bash
# Install via Go
go install github.com/instrumenta/kubeval@latest

# Validate against latest K8s version
kubeval deployment.yaml

# Validate against specific Kubernetes version
kubeval --kubernetes-version 1.29.0 deployment.yaml

# Strict mode (reject unknown fields)
kubeval --strict deployment.yaml

# Validate Helm template output
helm template ./mychart | kubeval --strict
```

## Combining All Three Tools

For comprehensive Kubernetes validation, use all three tools in your CI/CD pipeline:

```yaml
# .github/workflows/k8s-validation.yaml
name: K8s YAML Validation
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Schema Validation (kubeval)
        run: |
          docker run -v $PWD:/k8s instrumenta/kubeval --strict /k8s/k8s/*.yaml
      
      - name: Best Practice Check (kube-score)
        run: |
          docker run -v $PWD:/k8s zegl/kube-score score /k8s/k8s/*.yaml
      
      - name: Policy Enforcement (Datree)
        run: |
          docker run -v $PWD:/k8s datree/datree test /k8s/k8s/*.yaml
```

| Layer | Tool | Catches |
|-------|------|---------|
| **Schema** | kubeval | Typos, wrong types, missing required fields |
| **Best Practices** | kube-score | Missing limits, security gaps, no probes |
| **Policy** | Datree | Organization-specific rules, compliance checks |

## Integration with GitOps Workflows

For teams using GitOps, integrate YAML validation before manifests reach your cluster:

1. **Pre-commit hook**: Run kubeval and kube-score locally before committing
2. **Pull request check**: Run all three tools in CI on every PR
3. **Git sync validation**: Run validation in your ArgoCD/Flux sync pipeline
4. **Admission controller**: Use OPA Gatekeeper or Kyverno for runtime validation

For a complete GitOps setup, combine YAML validation with a [GitOps dashboard](../2026-05-14-weave-gitops-vs-kubefirst-vs-cyclops-self-hosted-gitops-dashboard-guide/) for deployment visibility.

## FAQ

### What is the difference between kube-score, Datree, and kubeval?

kubeval validates Kubernetes YAML against the official JSON schema — it catches typos and structural errors. kube-score performs best practice analysis, checking for missing resource limits, security contexts, and reliability issues. Datree provides policy enforcement with 100+ built-in rules and custom policy support. Use all three for comprehensive coverage: schema validation + best practices + organizational policies.

### Do these tools work with Helm charts?

Yes. All three tools can validate Helm chart output. The recommended approach is to run `helm template` to render the chart into raw YAML, then pipe the output to the validation tool: `helm template ./mychart | kubeval --strict`. Datree also provides a dedicated Helm plugin that runs validation during `helm install` and `helm upgrade`.

### Can I run these tools in CI/CD without installing them on runners?

Yes. All three tools provide Docker images, so you can run them in any CI/CD system without installing binaries. Simply use `docker run` with a volume mount pointing to your Kubernetes manifests. They also have GitHub Actions available for direct integration.

### Should I use these tools instead of OPA Gatekeeper or Kyverno?

No — these tools complement runtime admission controllers. kube-score, Datree, and kubeval run during CI/CD (shift-left validation), catching issues before code reaches the cluster. OPA Gatekeeper and Kyverno run inside the cluster as admission controllers, providing a safety net. For best results, use both: validate in CI/CD AND enforce at runtime. See our [Kubernetes policy enforcement guide](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-guide/) for runtime options.

### How do I add custom checks to kube-score?

kube-score supports custom checks through its Go plugin system. You write a Go function that implements the `Scorer` interface and registers it with kube-score. For simpler custom checks, consider using Datree, which allows custom policies defined in YAML without writing code.

### Which tool should I start with?

If you can only pick one, start with **kube-score** — it provides the best balance of actionable feedback, active development, and zero configuration. It catches the most common Kubernetes misconfigurations with minimal setup. Add kubeval for schema validation and Datree for organizational policies as your maturity grows.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kubernetes YAML Validation: kube-score vs Datree vs kubeval (2026 Guide)",
  "description": "Compare kube-score, Datree, and kubeval for Kubernetes YAML validation. Covers schema validation, best practice checks, CI/CD integration, and Docker setup.",
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
