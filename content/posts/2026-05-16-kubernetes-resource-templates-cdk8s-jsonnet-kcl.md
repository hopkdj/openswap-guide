---
title: "Self-Hosted Kubernetes Resource Templates: cdk8s vs Jsonnet vs KCL"
date: "2026-05-16"
tags: ["kubernetes", "iac", "cdk8s", "jsonnet", "kcl", "configuration-management"]
draft: false
---

Managing Kubernetes manifests at scale is one of the most common pain points for platform engineering teams. Raw YAML files quickly become unmanageable as the number of deployments grows — duplication, inconsistent labeling, and configuration drift are inevitable without a templating strategy.

This guide compares three powerful approaches to Kubernetes manifest generation: **cdk8s** (Cloud Development Kit for Kubernetes), **Jsonnet** (data templating language), and **KCL** (Configuration Constraint Language). Each offers a fundamentally different paradigm for defining and managing Kubernetes resources.

## The Problem with Raw YAML

Kubernetes YAML manifests are declarative but lack the abstractions needed for large-scale management:

- **No variables** — you must copy-paste and manually edit values for each environment
- **No conditionals** — no way to include/exclude resources based on environment or cluster
- **No functions** — common patterns (Deployments, Services, Ingress) must be repeated verbatim
- **No validation** — typos in field names or invalid values are only caught at apply time
- **No composition** — no way to define a "component" that generates multiple resources

Template languages solve these problems by adding programming constructs to manifest generation.

## cdk8s

cdk8s (Cloud Development Kit for Kubernetes) is an open-source framework from AWS that lets you define Kubernetes resources using familiar programming languages — TypeScript, Python, Go, and Java. It uses the Constructs programming model (the same foundation as AWS CDK) to create reusable, composable Kubernetes definitions.

### Architecture

cdk8s works by translating programmatic resource definitions into standard Kubernetes YAML manifests. You write code that constructs Kubernetes objects, then run `cdk8s synth` to generate the YAML files that `kubectl apply` consumes.

```typescript
import { Construct } from 'constructs';
import { App, Chart } from 'cdk8s';
import { Deployment, Service, Protocol } from 'cdk8s-plus-28';

class WebAppChart extends Chart {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    const deployment = new Deployment(this, 'webapp', {
      replicas: 3,
      containers: [{
        name: 'webapp',
        image: 'myregistry/webapp:1.0.0',
        portNumber: 8080,
        env: {
          DATABASE_URL: { value: 'postgres://db:5432/app' },
        },
      }],
    });

    const service = new Service(this, 'webapp-svc', {
      ports: [{ port: 80, targetPort: 8080 }],
      selector: deployment,
      type: ServiceType.CLUSTER_IP,
    });
  }
}

const app = new App();
new WebAppChart(app, 'webapp');
app.synth();
```

Key features:
- **Multi-language support** — TypeScript, Python, Go, Java with full IDE autocomplete
- **Type-safe definitions** — compile-time validation of Kubernetes API fields
- **Construct composition** — build reusable component libraries (charts, patterns)
- **Import CRDs** — generate type-safe bindings for any Custom Resource Definition
- **No custom runtime** — generates static YAML, no server or daemon needed
- **4,811 GitHub stars** — maintained by AWS under the cdk8s-team

### Installation

```bash
# Install CLI
npm install -g cdk8s-cli

# Initialize a TypeScript project
mkdir k8s-infra && cd k8s-infra
cdk8s init typescript-app

# Synthesize manifests
cdk8s synth
```

## Jsonnet

Jsonnet is a data templating language developed at Google that extends JSON with variables, conditionals, functions, and imports. It has been used internally at Google for over a decade and powers Kubernetes management tools like ksonnet (now deprecated) and Jsonnet-based Helm alternatives.

### Architecture

Jsonnet files (`.jsonnet`) are evaluated to produce JSON/YAML output. The language provides object-oriented features like inheritance, mixins, and parametric functions that make it ideal for templating complex Kubernetes configurations.

```jsonnet
local k = import 'k.libsonnet';

local container(name, image, port) =
  k.Container.new(name, image)
  + k.Container.mixin.ports([{ containerPort: port }]);

local deployment(name, replicas, containers) =
  k.apps.v1.deployment.new(name=name, replicas=replicas, containers=containers)
  + k.apps.v1.deploymentMixin.metadataLabels({ app: name });

local service(name, port, targetPort, selector) =
  k.Service.new(name=name, ports=[{ port: port, targetPort: targetPort }])
  + k.Service.mixin.selector(selector);

{
  webapp: deployment('webapp', 3, [
    container('web', 'myregistry/webapp:1.0.0', 8080),
  ]),
  webappSvc: service('webapp-svc', 80, 8080, { app: 'webapp' }),
}
```

Key features:
- **JSON superset** — any valid JSON is valid Jsonnet
- **Object-oriented** — inheritance (`+`), mixins, and parametric objects
- **Lazy evaluation** — expressions are only evaluated when needed
- **Import system** — modular templates with clean separation of concerns
- **K.libsonnet** — standard library for Kubernetes API objects
- **7,514 GitHub stars** — Google-maintained, production-proven

### Installation

```bash
# Install jsonnet
apt-get install jsonnet  # Debian/Ubuntu
brew install jsonnet     # macOS

# Install k.libsonnet
jb init
jb install github.com/jsonnet-libs/k8s-libsonnet/1.28

# Render manifests
jsonnet main.jsonnet | kubectl apply -f -
```

## KCL

KCL (Configuration Constraint Language) is a CNCF Sandbox project that provides a constraint-based configuration language designed specifically for cloud-native infrastructure. Unlike general-purpose templating languages, KCL adds validation, type checking, and constraint enforcement directly into the language.

### Architecture

KCL programs (`.k` files) define configuration with built-in validation rules. The KCL compiler checks constraints at compile time and generates YAML/JSON output. It supports schema definitions, inheritance, and rule-based validation.

```kcl
schema PodSpec:
    name: str
    image: str
    replicas: int = 3
    port: int
    env: {str: str} = {}

    check:
        replicas >= 1, "Replicas must be at least 1"
        replicas <= 100, "Replicas cannot exceed 100"
        port > 0 and port < 65536, "Port must be valid"

schema WebApp:
    base: PodSpec
    database_url: str

    check:
        "postgres" in database_url, "Must use PostgreSQL"

webapp = WebApp {
    name = "webapp"
    image = "myregistry/webapp:1.0.0"
    replicas = 3
    port = 8080
    database_url = "postgres://db:5432/app"
    env = {
        NODE_ENV = "production"
    }
}

# Generate Kubernetes resources
import k8s.api.apps.v1 as apiv1
import k8s.api.core.v1 as corev1

deployment = apiv1.Deployment {
    metadata.name = webapp.name
    spec.replicas = webapp.replicas
    spec.selector.matchLabels = { app: webapp.name }
    spec.template.metadata.labels = { app: webapp.name }
    spec.template.spec.containers = [{
        name = webapp.name
        image = webapp.image
        ports = [{ containerPort = webapp.port }]
        env = [{ name = k, value = v } for k, v in webapp.env]
    }]
}
```

Key features:
- **Constraint validation** — built-in `check` blocks validate values at compile time
- **Schema system** — strong typing with inheritance and default values
- **Plugin ecosystem** — extensible via Python-based plugins
- **Multi-target output** — generates YAML, JSON, or Kubernetes manifests
- **Language server** — IDE support with autocomplete and error highlighting
- **2,350 GitHub stars** — CNCF Sandbox project, rapidly growing

### Installation

```bash
# Install KCL
pip install kcl-lang

# Or via official installer
curl -fsSL https://kcl-lang.io/install.sh | bash

# Initialize a project
kcl mod init my-infra

# Compile manifests
kcl main.k -o output.yaml
```

## Comparison Table

| Feature | cdk8s | Jsonnet | KCL |
|---------|-------|---------|-----|
| **Language paradigm** | OOP (TypeScript/Python/Go/Java) | Functional data templating | Constraint-based |
| **Type safety** | Compile-time (host language) | Runtime | Compile-time (built-in) |
| **Validation** | Via host language checks | Manual assertions | Built-in `check` blocks |
| **Learning curve** | Low (if you know a supported language) | Moderate | Moderate |
| **IDE support** | Full (VS Code, IntelliJ) | Basic | Full (LSP) |
| **CRD support** | Import generates bindings | Manual or via libraries | Via plugins |
| **Runtime dependencies** | Node.js/Python/Go/Go runtime | Jsonnet binary | KCL compiler |
| **Output** | Static YAML | Static YAML/JSON | Static YAML/JSON |
| **CNCF status** | AWS project | Google project | CNCF Sandbox |
| **Stars (GitHub)** | 4,811+ | 7,514+ | 2,350+ |
| **Best for** | Teams with existing programming expertise | Google-style infrastructure teams | Teams needing validation constraints |

## Why Use Kubernetes Template Languages?

Raw YAML works for small deployments but becomes a liability as your infrastructure grows. Template languages provide three critical benefits that YAML alone cannot deliver:

**Reusability through abstraction.** Define a "web service" component once — with Deployment, Service, Ingress, HPA, and monitoring sidecar — then instantiate it for every microservice with just a few parameters. This eliminates copy-paste errors and ensures consistent configuration across all services.

**Validation before deployment.** Catch configuration errors at template compile time rather than waiting for `kubectl apply` to fail. KCL's constraint system and cdk8s's type checking prevent invalid manifests from ever reaching the cluster.

**Environment-specific configuration.** Generate production, staging, and development manifests from a single source of truth using variables, conditionals, and parameterized templates. No more maintaining separate YAML directories for each environment.

For broader Kubernetes configuration management, see our [Helm vs Kustomize comparison](../helm-vs-kustomize-vs-helmfile-kubernetes-package-management-guide/) and [Helm management guide](../2026-05-06-self-hosted-helm-management-helmfile-flux-argocd-guide/). If you're building Kubernetes operators, our [Operator SDK vs Kubebuilder comparison](../2026-05-01-operator-sdk-vs-kubebuilder-vs-java-operator-sdk-kubernetes-operator-frameworks/) covers the development side.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Resource Templates: cdk8s vs Jsonnet vs KCL",
  "description": "Compare three Kubernetes manifest generation tools: cdk8s (AWS, TypeScript/Python/Go), Jsonnet (Google, data templating), and KCL (CNCF, constraint-based validation). Choose the right templating approach for your team.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  }
}
</script>

## FAQ

### Should I use cdk8s, Jsonnet, or KCL for my Kubernetes templates?

Choose cdk8s if your team already uses TypeScript, Python, Go, or Java and wants full IDE support with type safety. Choose Jsonnet if you prefer a lightweight, language-agnostic data templating approach with a proven track record at Google scale. Choose KCL if you need built-in constraint validation and schema enforcement as a first-class language feature.

### Can cdk8s generate manifests for Custom Resource Definitions (CRDs)?

Yes. cdk8s includes a `cdk8s import` command that reads CRD definitions from your cluster or YAML files and generates type-safe constructs in your chosen programming language. This means you can use autocomplete and compile-time checking for any Kubernetes resource, including custom ones.

### Is Jsonnet still actively maintained?

Yes. Jsonnet is maintained by Google and receives regular updates. While the ksonnet project that popularized Jsonnet for Kubernetes was deprecated, Jsonnet itself remains widely used — including by Tanka, a modern Jsonnet-based Kubernetes deployment tool from Grafana Labs.

### How does KCL's constraint validation work?

KCL uses `check` blocks within schema definitions to declare validation rules. These rules are evaluated at compile time, before any YAML is generated. For example, `check: replicas >= 1` ensures that no deployment can be configured with zero or negative replicas. Constraints can reference other fields, use regular expressions, and include custom error messages.

### Do these tools replace Helm?

No. These tools solve a different problem than Helm. Helm is a package manager with templating (Go templates) and release management. cdk8s, Jsonnet, and KCL are manifest generation tools that produce static YAML. They can be used together — for example, you could generate YAML with cdk8s and then package it as a Helm chart for distribution.

### Can I migrate from raw YAML to these tools incrementally?

Yes. All three tools generate standard Kubernetes YAML, so you can adopt them gradually. Start by templating your most complex or frequently-changing manifests, then expand coverage over time. Your existing `kubectl apply` workflows remain unchanged since the output is always standard YAML.
