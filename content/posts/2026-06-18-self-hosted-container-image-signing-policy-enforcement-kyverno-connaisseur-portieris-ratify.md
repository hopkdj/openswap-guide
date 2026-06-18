---
title: "Self-Hosted Container Image Signing Policy Enforcement: Kyverno vs Connaisseur vs Portieris vs Ratify Compared"
date: "2026-06-18"
tags: ["kubernetes", "container-security", "supply-chain-security", "image-signing", "admission-controller", "cosign", "notation", "devsecops", "self-hosted"]
draft: false
---

## Introduction

Software supply chain attacks targeting container images have become one of the most critical security threats in cloud-native environments. When an attacker compromises a container image in your registry, every pod running that image inherits the compromise. The solution is cryptographic image signing — but signing alone is not enough. You need enforcement: a mechanism that blocks unsigned or tampered images from ever running in your cluster.

Kubernetes admission controllers bridge this gap. They intercept every pod creation request and verify that container images meet your signing policy before the pod is scheduled. In this guide, we compare four leading open-source admission controllers for container image signature verification: **Kyverno**, **Connaisseur**, **Portieris**, and **Ratify**.

## Comparison at a Glance

| Feature | Kyverno | Connaisseur | Portieris | Ratify |
|---------|---------|-------------|-----------|--------|
| Stars | 7,844 | 474 | 341 | 303 |
| CNCF Status | Graduated | N/A | N/A | Sandbox |
| Signature Format | Cosign, Notation | Cosign, Notation | Docker Content Trust, Notary v1 | Cosign, Notation |
| Policy Language | Custom (YAML) | Custom (YAML) | Custom (YAML CRD) | OCI-based |
| Key Management | External (KMS) | Built-in + External | External (KMS) | External (AKV, KMS) |
| Mutable Tags | ❌ Blocks | ✅ Allows (verify latest) | ✅ Per-policy config | ✅ Configurable |
| Namespace Isolation | ✅ ClusterPolicy/Policy | ✅ Namespace-scoped | ✅ ImagePolicy per namespace | ✅ Verifier CRD |
| Deployment Method | Helm | Helm | Helm | Helm |
| External Data Support | ✅ API calls | ❌ | ❌ | ✅ Plugin architecture |
| Audit Mode | ✅ Audit + Enforce | ✅ Alerting mode | ✅ Per-policy config | ✅ Configurable |

## Kyverno

[Kyverno](https://github.com/kyverno/kyverno) is a CNCF Graduated policy engine that goes far beyond image signing. While it includes powerful image verification capabilities, it is primarily a general-purpose Kubernetes policy management tool — handling everything from pod security standards to resource mutation and generation.

### Image Verification with Kyverno

Kyverno's `verifyImages` rule type checks container images against Cosign or Notary signatures:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: check-image-signatures
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: verify-signatures
      match:
        any:
        - resources:
            kinds:
              - Pod
      verifyImages:
      - imageReferences:
        - "registry.example.com/*"
        attestors:
        - entries:
          - keys:
              publicKeys: |-
                -----BEGIN PUBLIC KEY-----
                MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                -----END PUBLIC KEY-----
```

### Deployment

Kyverno is deployed via Helm and runs as a cluster-wide admission webhook:

```bash
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno   --namespace kyverno --create-namespace   --set admissionController.replicas=3
```

**Strengths:** Kyverno's biggest advantage is its unified policy platform — you can manage image signing, pod security, resource validation, and mutation all from one tool. The large community (7,844 stars, CNCF Graduated) means extensive documentation and community support.

**Limitations:** As a general-purpose tool, Kyverno's image verification features are less specialized than dedicated tools. Setting up key management requires external KMS integration, and debugging signature verification failures can be challenging without dedicated tooling.

## Connaisseur

[Connaisseur](https://github.com/sse-secure-systems/connaisseur) is a purpose-built admission controller focused exclusively on container image signature verification. Developed by the Secure Systems Engineering group, it takes a security-first approach with built-in alerting and notification capabilities.

### Key Capabilities

- **Multi-signature support** — verifies Cosign, Notary v1, and Notation signatures
- **Built-in alerting** — sends notifications on policy violations via configurable channels
- **Delegation support** — allows trusted teams to sign images on behalf of other teams
- **Automatic key rotation** — supports key expiry and rotation without policy changes

### Deployment Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: connaisseur-config
data:
  policy.yaml: |
    policy:
      - pattern: "registry.example.com/production/*"
        validator: "cosign"
        with:
          trust_root:
            - name: "production-key"
              key: |
                -----BEGIN PUBLIC KEY-----
                ...
                -----END PUBLIC KEY-----
        mode: "enforce"
      - pattern: "registry.example.com/staging/*"
        validator: "cosign"
        mode: "warn"
```

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/
helm install connaisseur connaisseur/connaisseur   --namespace connaisseur --create-namespace
```

**Strengths:** Connaisseur's focused design makes it easier to configure and debug than general-purpose policy engines. The built-in alerting is valuable for security teams that need immediate notification of policy violations.

**Limitations:** With 474 stars and a smaller community, Connaisseur has fewer integrations and less community support than Kyverno. It handles only image verification — you will need separate tools for other policy enforcement needs.

## Portieris

[Portieris](https://github.com/IBM/portieris) is IBM's Kubernetes admission controller for container image trust enforcement. Originally designed for Docker Content Trust (Notary v1), it has evolved to support modern signing tools while maintaining IBM's enterprise security requirements.

### Configuration

Portieris uses custom resources (`ImagePolicy`) to define trust policies:

```yaml
apiVersion: portieris.cloud.ibm.com/v1
kind: ImagePolicy
metadata:
  name: require-notary
spec:
  repositories:
    - name: "registry.example.com/*"
      policy:
        trust:
          enabled: true
          signerSecrets:
            - name: "notary-signer"
        va:
          enabled: false
    - name: "docker.io/*"
      policy:
        trust:
          enabled: false
```

```bash
helm install portieris   https://github.com/IBM/portieris/releases/download/v0.13.0/portieris-0.13.0.tgz   --namespace portieris --create-namespace
```

**Strengths:** Portieris' per-namespace `ImagePolicy` CRD provides fine-grained control — different teams can have different signing requirements. IBM's backing ensures enterprise-grade stability and long-term support.

**Limitations:** Portieris supports a narrower range of signature formats compared to Kyverno and Ratify. The project has been relatively quiet recently (341 stars), and community contributions are sparse.

## Ratify

[Ratify](https://github.com/deislabs/ratify) is a CNCF Sandbox project that takes a novel approach: instead of being a traditional admission controller, it acts as an external verification service that integrates with Kyverno or OPA Gatekeeper via the external data provider interface.

### Architecture and Configuration

Ratify verifies images using a plugin-based architecture:

```yaml
apiVersion: config.ratify.deislabs.io/v1beta1
kind: Store
metadata:
  name: store-oras
spec:
  name: oras
  address: registry.example.com

---
apiVersion: config.ratify.deislabs.io/v1beta1
kind: Verifier
metadata:
  name: verifier-cosign
spec:
  name: cosign
  artifactTypes: application/vnd.dev.cosign.artifact.sig.v1+json
  parameters:
    key: /etc/ratify/cosign.pub
```

```bash
helm repo add ratify https://deislabs.github.io/ratify
helm install ratify ratify/ratify   --namespace ratify --create-namespace
```

**Strengths:** Ratify's plugin architecture makes it highly extensible — you can add custom verifiers for proprietary signing systems. Integration with OPA Gatekeeper and Kyverno means you can use Ratify's verification while keeping your existing policy engine.

**Limitations:** As a CNCF Sandbox project (303 stars), Ratify is the youngest and least proven of the four. It requires an existing policy engine (Kyverno or Gatekeeper) to function, adding operational complexity.

## Choosing the Right Approach

**Kyverno** is the natural choice if you already use or plan to adopt a comprehensive policy-as-code solution. Its image verification is a subset of a broader policy platform, reducing tool sprawl.

**Connaisseur** excels in environments where image signing is the primary concern and a focused, dedicated tool is preferred. The built-in alerting is valuable for security operations centers.

**Portieris** suits IBM-centric enterprises or teams that need fine-grained, per-namespace trust policies without a full policy engine.

**Ratify** fits organizations with existing policy engines (Gatekeeper or Kyverno) that want to add advanced image verification capabilities without replacing their current tools.

For related reading, see our [supply chain security guide covering Cosign and Notation](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/) and our [Kyverno vs OPA Gatekeeper policy enforcement comparison](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/).

## Why Self-Host Your Image Signing Enforcement?

Running image verification within your own Kubernetes cluster ensures that policy enforcement cannot be bypassed by external service outages. If you rely on a cloud-based verification service that goes down, your admission webhook would time out — potentially blocking all deployments. Self-hosted admission controllers run inside your cluster with local caching, ensuring availability even during external incidents.

Self-hosting also gives you complete control over your verification keys and trust roots. Cryptographic keys for image signing should never leave your security boundary. A self-hosted admission controller keeps all verification operations within your cluster, preventing key material from being exposed to third-party services.

## Deployment Architecture

A layered defense strategy combines image signing enforcement with registry-level controls:

```yaml
# Kyverno deployment with high availability
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kyverno-admission-controller
  namespace: kyverno
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: kyverno
        args:
        - --imagePullSecrets=registry-creds
        - --autoUpdateWebhooks=false
        - --webhookTimeout=10
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Image Signing Policy Enforcement: Kyverno vs Connaisseur vs Portieris vs Ratify Compared",
  "description": "Compare Kyverno, Connaisseur, Portieris, and Ratify for Kubernetes container image signature verification. Enforce supply chain security with admission controllers.",
  "datePublished": "2026-06-18",
  "dateModified": "2026-06-18",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

## FAQ

### What is the difference between image signing and image scanning?

Image signing cryptographically verifies that an image came from a trusted source and has not been tampered with. Image scanning (like Trivy or Grype) checks for known vulnerabilities in the image layers. They address different threats: signing prevents supply chain attacks, while scanning detects vulnerable dependencies.

### Do I need both Kyverno and Connaisseur?

No. These are alternatives, not complements. Choose one admission controller for image verification. Running multiple controllers that all verify signatures would add latency to every pod creation without improving security.

### Can I start in audit mode before enforcing?

Yes. All four tools support an audit or warn mode that logs policy violations without blocking deployments. Start in audit mode, monitor for a week or two, fix any issues with your signing pipeline, then switch to enforce mode.

### What happens if the admission controller is unavailable?

By default, Kubernetes admission webhooks have a failure policy. If set to `Fail`, all pod creations are blocked when the webhook is down. If set to `Ignore`, pods are admitted without verification. For production, deploy at least 3 replicas of your admission controller and use PodDisruptionBudgets to ensure availability.

### Do these tools work with private container registries?

Yes. All four tools authenticate with private registries using image pull secrets or service account credentials. You will need to configure registry credentials as Kubernetes secrets and reference them in the admission controller configuration.

### What signing tools should I use with these controllers?

Cosign (from Sigstore) is the most widely supported across all four tools. Notation (from Notary v2) is gaining adoption and is supported by Kyverno, Connaisseur, and Ratify. Docker Content Trust (Notary v1) is legacy and only supported by Portieris.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
