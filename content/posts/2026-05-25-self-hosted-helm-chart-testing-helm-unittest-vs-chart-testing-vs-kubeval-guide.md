---
title: "Self-Hosted Helm Chart Testing: helm-unittest vs chart-testing vs kubeval"
date: "2026-05-25"
tags: ["helm", "kubernetes", "testing", "devops", "ci-cd", "chart-validation"]
draft: false
---

Helm is the dominant package manager for Kubernetes, but deploying untested charts to production is a recipe for cluster failures. Self-hosted Helm chart testing frameworks catch misconfigurations, YAML errors, and policy violations before they reach your cluster. This guide compares three leading open-source tools: **helm-unittest**, **chart-testing (ct)**, and **kubeval**.

## Why Helm Chart Testing Matters

Helm charts define complex Kubernetes resource configurations — Deployments, Services, Ingress rules, RBAC policies, and more. A single typo in a chart template can cascade into failed deployments, misconfigured services, or security vulnerabilities. Manual review is error-prone and doesn't scale across teams managing dozens of charts.

Automated chart testing provides three critical guarantees:

1. **Template correctness** — Charts render valid Kubernetes manifests across all value combinations
2. **Policy compliance** — Resources meet organizational standards (resource limits, security contexts, image policies)
3. **Regression prevention** — Changes don't break existing chart behavior

For teams managing internal Helm repositories, see our [chart repository management guide](../chartmuseum-vs-harbor-vs-oci-self-hosted-helm-chart-repositories-2026/). If you're evaluating package management approaches beyond Helm, our [comparison of Kustomize and Kpt](../2026-05-24-self-hosted-kubernetes-package-management-beyond-helm-kapp-kustomize-kpt-guide/) covers alternative strategies.

## helm-unittest: BDD-Style Chart Unit Testing

[**helm-unittest**](https://github.com/helm-unittest/helm-unittest) (1,327+ stars) is a BDD-styled unit test framework for Helm charts, implemented as a Helm plugin. It allows you to write test assertions in YAML that validate rendered chart output against expected values.

### Key Features

- **YAML-based test definitions** — Tests are written as YAML files alongside your chart, using a familiar BDD syntax (describe/it/expect)
- **Snapshot testing** — Capture expected rendered output and detect drift on subsequent runs
- **Document selection** — Target specific Kubernetes resources within rendered manifests for assertions
- **Template assertion** — Verify that templates render correctly with various value overrides
- **Helm plugin integration** — Install via `helm plugin install`, runs as part of standard Helm workflows

### Installation

```bash
helm plugin install https://github.com/helm-unittest/helm-unittest.git
```

### Example Test

```yaml
# tests/deployment_test.yaml
suite: test deployment
templates:
  - deployment.yaml
tests:
  - it: should render correct replica count
    set:
      replicaCount: 3
    asserts:
      - equal:
          path: spec.replicas
          value: 3
      - isKind:
          of: Deployment
  - it: should set resource limits
    set:
      resources.limits.cpu: "500m"
    asserts:
      - equal:
          path: spec.template.spec.containers[0].resources.limits.cpu
          value: "500m"
  - it: should use correct image tag
    set:
      image.tag: "v2.0.0"
    asserts:
      - matchRegex:
          path: spec.template.spec.containers[0].image
          pattern: "v2\.0\.0$"
```

### Running Tests

```bash
helm unittest ./my-chart/
# Run with values override
helm unittest ./my-chart/ --values test-values.yaml
# Output in JUnit format for CI integration
helm unittest ./my-chart/ --output-file junit.xml --output-type JUnit
```

### Docker Deployment

```yaml
version: "3.8"
services:
  helm-test:
    image: alpine/helm:3.14
    volumes:
      - ./charts:/charts
      - ./tests:/tests
    working_dir: /charts
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        helm plugin install https://github.com/helm-unittest/helm-unittest.git
        helm unittest .
```

### When to Use helm-unittest

- **Unit testing individual chart templates** — Verify specific resource configurations
- **Snapshot-based regression testing** — Detect unintended changes in rendered output
- **CI/CD pipeline integration** — Runs fast, produces JUnit-compatible output
- **Value combination testing** — Test charts with multiple `--set` overrides

## chart-testing (ct): CI-Focused Chart Linting and Testing

[**chart-testing**](https://github.com/helm/chart-testing) (1,629+ stars) is a CLI tool specifically designed for linting and testing Helm charts in CI/CD pipelines. It is the standard tool used in the official Helm charts repository CI workflow.

### Key Features

- **Changed chart detection** — Automatically identifies which charts have changed since a target Git branch
- **Comprehensive linting** — Runs `helm lint` plus additional structural checks on chart metadata
- **Install testing** — Deploys charts to a real Kubernetes cluster and verifies successful installation
- **GitHub Actions integration** — Pre-built actions (`helm/chart-testing-action`) for GitHub CI
- **Version validation** — Ensures chart version bumps follow semantic versioning rules

### Installation

```bash
# Via Homebrew
brew install chart-testing

# Via Go install
go install github.com/helm/chart-testing/v3/ct@latest

# Docker
docker run --rm -v "$(pwd):/workdir" -w /workdir quay.io/helmpack/chart-testing:latest
```

### Configuration

```yaml
# ct.yaml
remote: origin
target-branch: main
chart-dirs:
  - charts
  - incubator
chart-repos:
  - stable=https://charts.helm.sh/stable
  - bitnami=https://charts.bitnami.com/bitnami
validate-maintainers: true
validate-chart-schema: true
validate-yaml: true
check-version-increment: true
```

### Running Tests

```bash
# Lint only (fast, no cluster needed)
ct lint --config ct.yaml

# Lint and install (requires Kubernetes cluster)
ct lint-and-install --config ct.yaml

# GitHub Actions workflow
# Uses helm/chart-testing-action with the same ct.yaml
```

### Docker Compose for Local Testing

```yaml
version: "3.8"
services:
  ct-lint:
    image: quay.io/helmpack/chart-testing:latest
    volumes:
      - ./charts:/workdir/charts
      - ./ct.yaml:/workdir/ct.yaml
    working_dir: /workdir
    command: ["ct", "lint", "--config", "ct.yaml"]

  ct-install:
    image: quay.io/helmpack/chart-testing:latest
    volumes:
      - ./charts:/workdir/charts
      - ./ct.yaml:/workdir/ct.yaml
      - ${HOME}/.kube:/root/.kube
    working_dir: /workdir
    command: ["ct", "lint-and-install", "--config", "ct.yaml"]
    depends_on:
      - kind-cluster
```

### When to Use chart-testing

- **CI/CD pipeline gate** — Block PRs with broken charts before merge
- **Multi-chart repository management** — Automatically test only changed charts
- **Version compliance enforcement** — Ensure chart version increments follow SemVer
- **Real cluster validation** — Verify charts actually install, not just lint

## kubeval: Kubernetes Manifest Schema Validation

[**kubeval**](https://github.com/instrumenta/kubeval) (3,227+ stars) is a general-purpose Kubernetes manifest validation tool that checks YAML files against the official Kubernetes API schema. While not Helm-specific, it is widely used in Helm chart testing pipelines.

### Key Features

- **Schema-based validation** — Validates manifests against the official Kubernetes OpenAPI schema
- **Multi-version support** — Test against specific Kubernetes versions (1.20, 1.25, 1.28, etc.)
- **Strict mode** — Enforces that all properties in the schema are present
- **JSON and YAML support** — Validates both output formats
- **Helm template integration** — Pipe `helm template` output directly into kubeval

### Installation

```bash
# Via Homebrew
brew install kubeval

# Download binary
curl -sSLO https://github.com/instrumenta/kubeval/releases/latest/download/kubeval-linux-amd64.tar.gz
tar xf kubeval-linux-amd64.tar.gz
sudo mv kubeval /usr/local/bin/

# Docker
docker run --rm -i instrumenta/kubeval
```

### Running with Helm

```bash
# Validate rendered Helm templates
helm template my-chart/ | kubeval --strict

# Validate against specific Kubernetes version
helm template my-chart/ | kubeval --kubernetes-version 1.28.0

# Validate with custom schema location
helm template my-chart/ | kubeval --schema-location https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  kubeval:
    image: instrumenta/kubeval:latest
    volumes:
      - ./output:/output
    working_dir: /output
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        helm template /charts/my-chart/ | kubeval --strict --kubernetes-version 1.28.0
```

### When to Use kubeval

- **Schema-level validation** — Catch API-incompatible field names and types
- **Multi-version compatibility testing** — Verify charts work across Kubernetes versions
- **Pre-lint safety net** — Run before install testing to catch structural errors early
- **Non-Helm manifest validation** — Works with any Kubernetes YAML, not just Helm output

## Comparison Table

| Feature | helm-unittest | chart-testing (ct) | kubeval |
|---------|---------------|---------------------|---------|
| **Primary Purpose** | Unit testing chart templates | CI linting & install testing | Schema validation |
| **Test Format** | YAML BDD assertions | CLI with config file | CLI pipe validation |
| **Kubernetes Cluster** | Not required | Required for install tests | Not required |
| **Changed Chart Detection** | No | Yes (Git diff-based) | No |
| **Snapshot Testing** | Yes | No | No |
| **Version Validation** | No | Yes (SemVer check) | Yes (K8s version) |
| **CI Integration** | JUnit output | GitHub Actions, native | Any CI (CLI) |
| **Helm Plugin** | Yes | No (standalone CLI) | No |
| **Stars** | 1,327+ | 1,629+ | 3,227+ |
| **Best For** | Template correctness | PR gate in CI | Schema compliance |

## Choosing the Right Tool

### For Helm Chart Developers

Use **helm-unittest** as your primary testing tool. The BDD-style YAML tests are easy to write alongside chart development, and snapshot testing catches unintended changes immediately.

### For CI/CD Pipeline Engineers

Use **chart-testing (ct)** as your CI gate. Its changed-chart detection avoids unnecessary test runs, and its install testing validates charts against a real cluster. Pair it with helm-unittest for comprehensive coverage.

### For Multi-Version Compatibility Teams

Use **kubeval** to validate charts against multiple Kubernetes versions. It catches API schema violations that helm-unittest and ct might miss, especially when supporting older Kubernetes clusters.

### Recommended Pipeline

```
Chart PR → kubeval (schema check) → helm-unittest (unit tests) → ct lint → ct install → Merge
```

This pipeline catches errors at increasing levels of thoroughness: schema validity first, then template correctness, then linting rules, and finally real cluster installation.

## Why Self-Host Helm Chart Testing?

Running chart testing infrastructure on your own servers ensures complete control over test environments, avoids rate limits on cloud CI services, and keeps proprietary chart configurations within your network perimeter. For organizations managing internal Helm repositories, self-hosted testing integrates directly with private registries and internal Kubernetes clusters.

For teams evaluating GitOps deployment strategies, our [Argo CD vs Flux image update guide](../2026-05-16-self-hosted-gitops-container-image-update-automation-argocd-flux-renovate-guide/) covers how tested charts integrate with automated deployment pipelines. Teams managing Helm deployments at scale should also review our [Helm management comparison](../2026-05-06-self-hosted-helm-management-helmfile-flux-argocd-guide/) for deployment orchestration patterns.

## FAQ

### What is the difference between helm-unittest and chart-testing?

helm-unittest focuses on unit testing individual chart templates using BDD-style YAML assertions, while chart-testing (ct) is designed for CI/CD pipelines with features like changed-chart detection, version validation, and real cluster install testing. They serve complementary purposes — use both for comprehensive coverage.

### Does kubeval work with Helm charts directly?

kubeval validates Kubernetes YAML manifests, not Helm templates directly. The standard pattern is to pipe `helm template` output into kubeval: `helm template ./chart/ | kubeval --strict`. This validates the rendered manifests against the Kubernetes API schema.

### Can I run helm-unittest without installing it as a Helm plugin?

Yes. helm-unittest can be run via Docker: `docker run -v "$(pwd):/apps" quay.io/helmunittest/helm-unittest:latest .`. This is useful in CI environments where installing Helm plugins is impractical.

### How does chart-testing detect which charts have changed?

chart-testing uses Git diff to compare the current branch against a target branch (e.g., `main`). It identifies which directories under `chart-dirs` contain modified files and only tests those charts, saving significant CI time in repositories with many charts.

### Should I use kubeval or kubeconform for schema validation?

kubeconform is the modern successor to kubeval with faster performance and active maintenance. kubeval's last release was in early 2026, while kubeconform continues to receive updates. Both use the same schema validation approach, but kubeconform is recommended for new projects.

### How do I integrate Helm chart testing into GitHub Actions?

Use the official `helm/chart-testing-action` for chart-testing, or run helm-unittest via a Docker step. A typical workflow runs `ct lint` on every PR and `ct lint-and-install` on a kind cluster for approved changes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Helm Chart Testing: helm-unittest vs chart-testing vs kubeval",
  "description": "Compare helm-unittest, chart-testing, and kubeval for automated Helm chart testing in CI/CD pipelines — unit testing, linting, schema validation, and install testing.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
