---
title: "Self-Hosted Kubernetes Validating Admission Policies: CEL vs OPA Gatekeeper vs Kyverno (2026)"
date: "2026-05-22"
tags: ["kubernetes", "security", "policy", "admission", "self-hosted"]
draft: false
description: "Compare Kubernetes policy enforcement approaches — native CEL Validating Admission Policies, OPA Gatekeeper, and Kyverno. Complete guide with configuration examples."
---

Kubernetes admission controllers intercept API requests before objects are persisted to etcd. Validating admission controllers enforce organizational policies — requiring labels, restricting container images, preventing privileged containers. This guide compares three approaches to admission control in self-hosted Kubernetes clusters.

## Why Enforce Admission Policies?

Without admission policies, any user with API access can deploy privileged containers, bypass resource limits, or use unapproved container images. Admission controllers act as a gatekeeper, validating every create, update, and delete operation against your organization's security and operational standards.

**Key use cases:**
- Require specific labels on all namespaces and deployments
- Block containers running as root or with privileged access
- Enforce approved container image registries
- Restrict resource requests and limits
- Prevent deletion of critical resources
- Validate custom resource configurations

## Admission Controller Comparison

| Feature | CEL (Native VAP) | OPA Gatekeeper | Kyverno |
|---------|-----------------|----------------|---------|
| Type | Built-in Kubernetes | Custom admission webhook | Custom admission webhook |
| Language | CEL (Common Expression Language) | Rego (OPA policy language) | YAML (JMESPath for conditions) |
| Minimum K8s version | 1.26+ | 1.14+ | 1.14+ |
| External dependencies | None | OPA Gatekeeper deployment | Kyverno deployment |
| Policy as code | Yes | Yes | Yes (YAML) |
| Mutating capabilities | No (validation only) | Yes (with Gatekeeper mutations) | Yes |
| Policy reporting | Limited (audit log) | Yes (constraint violations) | Yes (policy reports) |
| Learning curve | Moderate (CEL syntax) | Steep (Rego language) | Low (YAML-based) |
| GitHub stars | N/A (upstream K8s) | 1,600+ | 5,000+ |
| CNCF status | Built-in | Sandbox (OPA) | Graduated |

## Approach 1: Native CEL Validating Admission Policies

Introduced in Kubernetes 1.26, Validating Admission Policies (VAP) use the Common Expression Language (CEL) to define validation rules directly in Kubernetes CRDs. No external controllers or webhooks required.

### Basic Policy: Require Labels

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-labels
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
  validations:
    - expression: "object.metadata.labels.containsKey('app.kubernetes.io/name')"
      message: "All deployments must have the 'app.kubernetes.io/name' label"
```

Bind the policy to namespaces:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-labels-binding
spec:
  policyName: require-labels
  matchResources:
    namespaceSelector:
      matchLabels:
        environment: production
```

### Advanced Policy: Block Privileged Containers

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: no-privileged-containers
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: >
        object.spec.containers.all(c, !has(c.securityContext) || 
        !has(c.securityContext.privileged) || 
        c.securityContext.privileged == false)
      message: "Privileged containers are not allowed"
    - expression: >
        object.spec.containers.all(c, !has(c.securityContext) || 
        !has(c.securityContext.runAsUser) || 
        c.securityContext.runAsUser != 0)
      message: "Containers must not run as root (UID 0)"
```

### Docker Compose for Local Testing

```yaml
version: "3.8"
services:
  kind-cluster:
    image: kindest/node:v1.29.2
    command:
      - /usr/local/bin/entrypoint
      - /sbin/init
    privileged: true
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
    ports:
      - "6443:6443"
    environment:
      - KUBECONFIG=/etc/kubernetes/admin.conf
```

### Pros and Cons

**Pros:**
- Zero external dependencies — built into Kubernetes
- No additional pods, services, or network calls
- Fast validation (in-process with API server)
- CEL is a standardized expression language (used across Google Cloud, Envoy, and Kubernetes)
- No webhook timeout issues or connectivity dependencies

**Cons:**
- Validation only — cannot mutate or modify resources
- CEL syntax can be verbose for complex policies
- Limited to K8s 1.26+ (not available on older clusters)
- No built-in policy reporting dashboard
- Smaller policy library community compared to OPA/Kyverno

## Approach 2: OPA Gatekeeper

OPA (Open Policy Agent) Gatekeeper runs as a custom admission webhook that evaluates Rego policies against incoming API requests. It's a CNCF Sandbox project with 1,600+ GitHub stars.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gatekeeper-controller:
    image: openpolicyagent/gatekeeper:v3.16.0
    command:
      - --audit-interval=60
      - --constraint-violations-limit=20
    ports:
      - "443:8443"
    volumes:
      - ./certs:/certs:ro
    environment:
      - POD_NAMESPACE=gatekeeper-system
```

### Constraint Template: Require Labels

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
          missing := {label | label := input.parameters.labels[_]; not input.review.object.metadata.labels[label]}
          count(missing) > 0
          msg := sprintf("Missing required label(s): %v", [missing])
        }
```

Constraint instance:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-app-label
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
  parameters:
    labels: ["app.kubernetes.io/name", "app.kubernetes.io/instance"]
```

### Pros and Cons

**Pros:**
- Rego is a powerful, general-purpose policy language
- Large community and extensive policy library
- Supports both validation and mutation
- Audit mode for monitoring violations without blocking
- Cross-platform (works with any Kubernetes distribution)

**Cons:**
- Requires deploying and managing Gatekeeper pods
- Rego has a steep learning curve
- Webhook adds latency (network call to Gatekeeper service)
- Webhook downtime can block or allow requests (depending on `failurePolicy`)
- Complex Rego policies can be difficult to debug

## Approach 3: Kyverno

Kyverno is a CNCF Graduated policy engine that uses YAML-based policies (no new language to learn). With 5,000+ GitHub stars, it's the most popular Kubernetes-native policy engine.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kyverno:
    image: ghcr.io/kyverno/kyverno:v1.11.4
    command:
      - --backgroundScan=true
      - --backgroundScanInterval=1h
    ports:
      - "9443:9443"
    environment:
      - KYVERNO_NAMESPACE=kyverno
```

### Policy: Block Privileged Containers

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
  annotations:
    policies.kyverno.io/title: Disallow Privileged Containers
    policies.kyverno.io/category: Pod Security Standards
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  backgroundScan: true
  rules:
    - name: deny-privileged
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Privileged containers are not allowed"
        pattern:
          spec:
            containers:
              - securityContext:
                  =(privileged): "false"
    - name: deny-root-user
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Running as root is not allowed"
        pattern:
          spec:
            containers:
              - securityContext:
                  =(runAsUser): "!0"
```

### Pros and Cons

**Pros:**
- Policies written in YAML — no new language to learn
- Supports validation, mutation, and generation
- Built-in policy reports for compliance tracking
- Large policy library (100+ pre-built policies)
- Background scanning to audit existing resources
- Easy to read and review policies

**Cons:**
- Requires deploying and managing Kyverno pods
- YAML-based approach can become verbose for complex logic
- Webhook adds latency and introduces availability dependency
- Some advanced policies require JMESPath expressions (separate learning curve)

## Choosing the Right Approach

### For Kubernetes 1.26+ with Simple Validation Rules

Use **native CEL Validating Admission Policies**. They require no additional infrastructure, have zero latency overhead, and are maintained by the Kubernetes project itself. Ideal for standard requirements like label enforcement, image registry whitelisting, and resource limit validation.

### For Complex Policy Logic and Cross-Platform Deployment

Use **OPA Gatekeeper** if your organization already uses OPA for other services (API gateways, service mesh) and your team is comfortable with Rego. The Rego language is powerful enough to express virtually any policy.

### For Teams That Prefer YAML and Need Mutating Policies

Use **Kyverno** if you want policies that are easy to read and review in pull requests. The YAML-based approach is accessible to Kubernetes administrators who don't want to learn a new programming language.

For additional Kubernetes security controls, see our [Kubernetes secrets management comparison](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) and [network policy management guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-enterprise-guide/).


## Policy Management Best Practices

Regardless of which admission controller you choose, following these best practices ensures effective policy enforcement across your Kubernetes clusters:

**Start with audit mode**: Before enforcing policies, run them in audit mode for 1-2 weeks to identify existing violations. Both OPA Gatekeeper and Kyverno support audit mode — they log violations without blocking API requests. This prevents breaking existing workloads when you first deploy policies.

**Version your policies**: Store admission policies in Git alongside your infrastructure code. Use semantic versioning for policy changes and require pull request reviews for policy modifications. This creates an audit trail and prevents accidental policy regressions.

**Test policies before deployment**: Use policy testing frameworks to validate your rules against sample Kubernetes objects. Kyverno provides a `kyverno test` CLI; OPA provides `opa eval` for testing Rego policies. CEL policies can be tested using the Kubernetes API dry-run feature (`kubectl apply --dry-run=server`).

**Monitor policy violations**: Set up alerting for policy violations in production. Kyverno generates `PolicyReport` and `ClusterPolicyReport` CRDs that can be monitored with Prometheus. Gatekeeper provides constraint violation metrics. For CEL policies, use the Kubernetes audit log.

**Plan for exceptions**: Some workloads legitimately need policy exceptions (system namespaces, legacy applications). All three approaches support namespace-level or resource-level exceptions. Document every exception and set expiration dates to prevent permanent policy gaps.

## FAQ

### Can I use multiple admission controllers together?

Yes. Kubernetes processes admission controllers in a defined order. Native CEL policies, OPA Gatekeeper, and Kyverno can all run simultaneously. Each controller evaluates its own policies independently.

### What happens if the admission controller is unavailable?

For native CEL policies, validation always works (built into the API server). For webhook-based controllers (Gatekeeper, Kyverno), the `failurePolicy` field determines behavior: `Fail` blocks the request, `Ignore` allows it through.

### Do CEL policies support mutation?

No. CEL Validating Admission Policies only validate — they cannot modify resources. For mutation, use Kyverno or a dedicated mutating webhook.

### How do I migrate from OPA/Kyverno to CEL policies?

CEL and Rego/YAML use different expression languages. Policies must be rewritten. Start with simple policies (label requirements, image restrictions) and migrate incrementally.

### Which approach has the best performance?

Native CEL policies have the best performance — they execute in-process with the API server with no network overhead. Webhook-based approaches add 5-50ms per request depending on controller load and network latency.

### Are CEL policies auditable?

CEL policy violations appear in the Kubernetes audit log. However, CEL does not provide a dedicated policy report like Kyverno's `PolicyReport` CRD or Gatekeeper's constraint violation reports. For comprehensive audit reporting, consider pairing CEL policies with a log aggregation system.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Validating Admission Policies: CEL vs OPA Gatekeeper vs Kyverno (2026)",
  "description": "Compare Kubernetes policy enforcement approaches — native CEL Validating Admission Policies, OPA Gatekeeper, and Kyverno.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
