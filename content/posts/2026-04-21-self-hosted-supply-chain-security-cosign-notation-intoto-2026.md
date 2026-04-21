---
title: "Self-Hosted Supply Chain Security: Sigstore/Cosign vs Notation vs in-toto 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "security", "supply-chain", "signing"]
draft: false
description: "Complete guide to self-hosted supply chain security tools — compare Sigstore/Cosign, Notation (Notary v2), and in-toto for container and artifact signing, verification, and provenance tracking."
---

Software supply chain attacks have grown exponentially in recent years. Compromised packages, tampered container images, and unauthorized code modifications threaten every organization that builds and deploys software. Self-hosted supply chain security tools give you full control over artifact signing, verification, and provenance — without trusting third-party SaaS platforms.

This guide compares three leading open-source frameworks for supply chain integrity: **Sigstore (Cosign)**, **Notation (Notary v2)**, and **in-toto**. Each takes a different approach to securing the software supply chain, and understanding their strengths helps you choose the right tool for your infrastructure.

## Why Self-Host Your Supply Chain Security?

Most cloud-based signing services require you to store private keys or trust remote infrastructure. For organizations with strict compliance requirements, regulatory obligations, or air-gapped environments, self-hosted signing and verification is essential.

Self-hosting supply chain security tools gives you:

- **Full key control** — private keys never leave your infrastructure
- **Air-gapped compatibility** — works in environments with no internet access
- **Auditability** — every signing event is logged on your own systems
- **No vendor lock-in** — migrate between registries and CI systems freely
- **Custom policies** — define signing requirements specific to your workflows

For a broader view of container security, see our [container vulnerability scanning guide](../openvas-trivy-grype-self-hosted-vulnerability-scanner-guide/) and [self-hosted SBOM pipeline tutorial](../self-hosted-sbom-dependency-tracking-dependency-track-syft-cyclonedx-guide-2026/) — supply chain signing works best alongside scanning and SBOM generation.

## Understanding the Landscape: Three Approaches

The three tools covered here represent distinct philosophies:

| Aspect | Sigstore/Cosign | Notation (Notary v2) | in-toto |
|--------|----------------|---------------------|---------|
| **Primary Goal** | Code signing + transparency log | OCI artifact signing | End-to-end supply chain integrity |
| **Key Management** | OIDC-based (keyless) or local keys | X.509 certificates + KMS | Link certificates + root layout |
| **Verification Model** | Transparency log (Rekor) | Registry-based (notation) | Step-by-step provenance verification |
| **Artifact Types** | Containers, binaries, files | OCI artifacts (containers, Helm charts) | Any file, any build step |
| **OCI Compliance** | Yes (cosign attest/sign) | Yes (native OCI spec) | No (external framework) |
| **Best For** | CI/CD pipelines, container signing | Kubernetes, OCI registries | Multi-step build pipelines, compliance |
| **Language** | Go | Go | Python |
| **GitHub Stars** | 5,834 (cosign) | 477 (notation) | 994 (in-toto) |
| **Last Active** | April 2026 | March 2026 | April 2026 |

## Sigstore/Cosign: Signing + Transparency

[Sigstore](https://github.com/sigstore/cosign) is a CNCF project that provides code signing and transparency for containers and binaries. Cosign is the flagship CLI tool.

### Key Features

- **Keyless signing** — uses short-lived OIDC certificates, no persistent private keys to manage
- **Transparency log** — every signature is recorded in Rekor, an append-only public ledger
- **Fulcio CA** — ephemeral certificate authority binds identities to signatures
- **Container-native** — designed from the ground up for OCI image signing

### Installation

```bash
# Linux
curl -sL https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64 \
  -o /usr/local/bin/cosign
chmod +x /usr/local/bin/cosign
cosign version

# macOS
brew install cosign

# Docker
docker pull gcr.io/projectsigstore/cosign:v2.4.0
```

### Docker Compose Deployment (Self-Hosted Fulcio + Rekor)

For fully self-hosted deployments, Sigstore provides components you can run on your own infrastructure:

```yaml
version: "3.8"

services:
  rekor-server:
    image: ghcr.io/sigstore/rekor/rekor-server:v1.3.7
    ports:
      - "3000:3000"
    environment:
      - REKOR_SERVER_ADDRESS=0.0.0.0:3000
      - REKOR_STORAGE_TYPE=mysqli
    depends_on:
      - rekor-db
      - redis-server

  rekor-db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: rekor

  redis-server:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  fulcio:
    image: ghcr.io/sigstore/fulcio/fulcio-ci:v1.6.5
    ports:
      - "5555:5555"
    command:
      - /ko-app/fulcio
      - --ca=googleca
      - --host=0.0.0.0
      - --port=5555
    environment:
      - FULCIO_CONFIG_PATH=/etc/fulcio-config/config.json
    volumes:
      - ./fulcio-config:/etc/fulcio-config
```

### Signing and Verifying a Container Image

```bash
# Sign an image with a local key
cosign generate-key-pair
cosign sign --key cosign.key myregistry.example.com/myapp:v1.0.0

# Verify the signature
cosign verify --key cosign.pub myregistry.example.com/myapp:v1.0.0

# Verify with a self-hosted Rekor server
cosign verify --key cosign.pub \
  --rekor-url https://rekor.mycompany.com:3000 \
  myregistry.example.com/myapp:v1.0.0
```

### Attestations (SBOM, Provenance)

Cosign supports attaching attestations to images:

```bash
# Generate SBOM and attach as attestation
cosign attest --predicate sbom.json \
  --type spdxjson \
  --key cosign.key \
  myregistry.example.com/myapp:v1.0.0

# Generate SLSA provenance attestation
cosign attest --predicate provenance.json \
  --type slsaprovenance \
  --key cosign.key \
  myregistry.example.com/myapp:v1.0.0
```

## Notation (Notary v2): OCI-Native Artifact Signing

[Notation](https://github.com/notaryproject/notation) is the CNCF Notary v2 project — a CLI tool for signing and verifying OCI artifacts (containers, Helm charts, WASM modules). It is the successor to Docker Notary, rebuilt to align with the OCI distribution specification.

### Key Features

- **OCI-native** — works directly with OCI registries using the standard distribution API
- **X.509 certificates** — uses standard PKI infrastructure for key management
- **Multi-registry support** — Docker Hub, Harbor, ECR, ACR, and any OCI-compliant registry
- **Policy-driven verification** — define trust policies per registry and namespace
- **Kubernetes integration** — Ratify admission controller verifies signatures before deployment

### Installation

```bash
# Linux
curl -sL https://github.com/notaryproject/notation/releases/latest/download/notation_1.1.0_linux_amd64.tar.gz \
  | tar xz -C /usr/local/bin notation

# macOS
brew install notation

# Docker
docker pull ghcr.io/notaryproject/notation:1.1.0
```

### Docker Compose Deployment

Notation itself is a CLI tool, but for a self-hosted PKI backend you can deploy a certificate authority:

```yaml
version: "3.8"

services:
  step-ca:
    image: smallstep/step-ca:latest
    ports:
      - "9000:9000"
    environment:
      - DOCKER_STEPCA_INIT_NAME=My Company CA
      - DOCKER_STEPCA_INIT_DNS_NAMES=step-ca.local
      - DOCKER_STEPCA_INIT_REMOTE_MANAGEMENT=true
    volumes:
      - step_data:/home/step
    command: >
      step-ca /home/step/certs/db.json
      --address :9000

  registry:
    image: registry:2
    ports:
      - "5000:5000"
    environment:
      REGISTRY_HTTP_TLS_CERTIFICATE: /certs/domain.crt
      REGISTRY_HTTP_TLS_KEY: /certs/domain.key
    volumes:
      - registry_data:/var/lib/registry
      - ./certs:/certs

volumes:
  step_data:
  registry_data:
```

### Signing and Verifying with Notation

```bash
# Import your signing key
notation key import --key-path ./signing-key.pem --cert-path ./signing-cert.pem

# Sign a container image
notation sign myregistry.example.com/myapp:v1.0.0

# Configure trust policy
cat > trust-policy.json << 'POLICY'
{
  "version": "1.0",
  "trustPolicies": [
    {
      "name": "production-images",
      "registryScopes": ["myregistry.example.com/myapp"],
      "signatureVerification": {
        "level": "strict"
      },
      "trustStores": ["ca:my-company-ca"],
      "trustedIdentities": [
        "x509.subject: CN=My Company CA, O=My Company"
      ]
    }
  ]
}
POLICY

notation policy import trust-policy.json

# Verify before deployment
notation verify myregistry.example.com/myapp:v1.0.0
```

## in-toto: End-to-End Supply Chain Integrity

[in-toto](https://github.com/in-toto/in-toto) is a framework that protects the entire software supply chain, not just the final artifact. It verifies that every step in the build process was performed correctly and by authorized personnel.

### Key Features

- **Step-by-step verification** — each build step is cryptographically recorded
- **Root layout** — defines the expected supply chain workflow
- **Link metadata** — each step produces a signed "link" file documenting what was done
- **Language-agnostic** — works with any build system, any language
- **SLSA alignment** — in-toto is the reference implementation for SLSA provenance

### Installation

```bash
# Python (pip)
pip install in-toto

# Docker
docker pull ghcr.io/in-toto/in-toto:latest

# Virtual environment (recommended)
python3 -m venv /opt/in-toto
/opt/in-toto/bin/pip install in-toto
ln -s /opt/in-toto/bin/in-toto-* /usr/local/bin/
```

### Defining a Supply Chain Layout

The root layout defines the expected steps:

```python
# layout.template
{
  "_type": "layout",
  "expires": "2027-04-21T00:00:00Z",
  "steps": [
    {
      "name": "clone",
      "expected_materials": [],
      "expected_products": [
        ["MATCH", "source/*", "IN", "source"]
      ],
      "pubkeys": ["alice_key_id"]
    },
    {
      "name": "build",
      "expected_materials": [
        ["MATCH", "source/*", "FROM", "clone"]
      ],
      "expected_products": [
        ["MATCH", "binary/app", "IN", "dist"]
      ],
      "pubkeys": ["bob_key_id"]
    },
    {
      "name": "package",
      "expected_materials": [
        ["MATCH", "binary/app", "FROM", "build"]
      ],
      "expected_products": [
        ["MATCH", "package/app.tar.gz", "IN", "release"]
      ],
      "pubkeys": ["bob_key_id"]
    }
  ],
  "inspect": [
    {
      "name": "verify-binary",
      "expected_materials": [
        ["MATCH", "binary/app", "FROM", "build"]
      ],
      "run": ["sha256sum", "binary/app"]
    }
  ]
}
```

### Running the in-toto Pipeline

```bash
# Generate keys for each party
in-toto-keygen-alice

# Each step is run with in-toto-run, which records metadata
in-toto-run --step-name clone \
  --key alice_key \
  --materials . \
  --products source/ \
  -- git clone https://github.com/example/app.git source

in-toto-run --step-name build \
  --key bob_key \
  --materials source/ \
  --products dist/ \
  -- make -C source

in-toto-run --step-name package \
  --key bob_key \
  --materials dist/ \
  --products release/ \
  -- tar czf release/app.tar.gz dist/app

# Final verification (runs on the consumer side)
in-toto-verify --layout layout.template \
  --layout-keys alice_key.pub
```

## Comparison: Which Tool Should You Choose?

| Criterion | Cosign | Notation | in-toto |
|-----------|--------|----------|---------|
| **Setup Complexity** | Low | Medium | High |
| **Key Management** | Keyless (OIDC) or local keys | X.509 PKI | Custom key pairs |
| **Registry Integration** | Good (OCI) | Excellent (OCI-native) | None (external) |
| **Kubernetes Support** | Via Kyverno/Gatekeeper | Via Ratify admission controller | Via custom controllers |
| **Transparency** | Public Rekor log | Private to registry | Link files per step |
| **Build Step Tracking** | No (signs final artifact) | No (signs final artifact) | Yes (tracks every step) |
| **CI/CD Integration** | Excellent (GitHub Actions, GitLab) | Good (Azure, GitHub) | Manual or scripted |
| **Compliance Ready** | Good | Good | Excellent (auditable chain) |
| **Learning Curve** | Low | Medium | High |
| **Community Size** | Large (CNCF) | Growing (CNCF) | Niche but active |

### Decision Matrix

- **Choose Cosign** if you need quick container signing with minimal setup. Its keyless mode eliminates key management overhead, and the transparency log provides public accountability. Best for teams already using GitHub Actions or GitLab CI.

- **Choose Notation** if you are building on OCI registries and Kubernetes. Its native OCI compliance and Ratify admission controller make it the strongest choice for Kubernetes-native workflows. Ideal if you already use Harbor or ACR.

- **Choose in-toto** if you need end-to-end supply chain verification across multiple build steps. It is the most comprehensive option for compliance-heavy environments (SOC 2, ISO 27001) where every step must be auditable.

## Building a Complete Self-Hosted Pipeline

For maximum security, combine multiple tools. A production-grade pipeline might use:

1. **in-toto** for build step verification during CI
2. **Cosign** for signing the final container image
3. **Notation** for registry-level signature verification before Kubernetes deployment
4. **Trivy** for vulnerability scanning (see our [vulnerability scanner comparison](../openvas-trivy-grype-self-hosted-vulnerability-scanner-guide/))
5. **Syft + Dependency-Track** for SBOM generation and tracking (see our [SBOM pipeline guide](../self-hosted-sbom-dependency-tracking-dependency-track-syft-cyclonedx-guide-2026/))

```yaml
# Complete CI/CD pipeline example (GitHub Actions style)
name: Secure Build Pipeline
on:
  push:
    branches: [main]

jobs:
  build-and-sign:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4

      # Step 1: Build container image
      - name: Build image
        run: docker build -t myregistry.example.com/myapp:${{ github.sha }} .

      # Step 2: Sign with Cosign
      - name: Sign image
        uses: sigstore/cosign-installer@v3.7.0
      - run: |
          cosign sign --key env://COSIGN_KEY \
            myregistry.example.com/myapp:${{ github.sha }}

      # Step 3: Generate and attach SBOM
      - name: SBOM attestation
        run: |
          cosign attest --predicate sbom.json \
            --type spdxjson \
            --key env://COSIGN_KEY \
            myregistry.example.com/myapp:${{ github.sha }}

      # Step 4: Vulnerability scan
      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myregistry.example.com/myapp:${{ github.sha }}
          severity: CRITICAL,HIGH
```

## Verification at Deployment Time

Regardless of which signing tool you choose, verification at deployment time is critical. Here is how to enforce signature verification in Kubernetes:

### With Notation + Ratify

```yaml
# ratify-config.yaml
apiVersion: config.ratify.deislabs.io/v1beta1
kind: Verifier
metadata:
  name: notation-verifier
spec:
  name: notation
  artifactTypes: application/vnd.cncf.notary.signature.v1
  parameters:
    verificationCertStores:
      my-ca:
        - type: secret
          name: my-ca-cert
```

### With Cosign + Kyverno

```yaml
# kyverno-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-cosign-signature
spec:
  validationFailureAction: Enforce
  rules:
    - name: verify-image-signature
      match:
        any:
          - resources:
              kinds: ["Pod"]
      verifyImages:
        - imageReferences: ["myregistry.example.com/*"]
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      ...
                      -----END PUBLIC KEY-----
```

## Conclusion

Self-hosted supply chain security is no longer optional — it is a baseline requirement for any organization shipping software. Cosign, Notation, and in-toto each solve different parts of the puzzle:

- **Cosign** provides the easiest path to signed containers with transparency
- **Notation** offers the deepest OCI registry integration
- **in-toto** delivers comprehensive step-by-step supply chain verification

For most teams, starting with Cosign for container signing and adding Notation for Kubernetes enforcement is the most practical path. For regulated industries, in-toto provides the audit trail that compliance frameworks demand.

## FAQ

### What is the difference between Cosign and Docker Notary?

Cosign is a CNCF project designed for container signing with a transparency log. Docker Notary (v1) was Docker's original signing tool, now deprecated. Notation (Notary v2) is the official successor, rebuilt as a CNCF project with native OCI distribution support.

### Do I need to self-host all Sigstore components?

No. Cosign can use the public Sigstore infrastructure (Fulcio CA, Rekor transparency log) without self-hosting anything. However, for air-gapped environments or organizations that cannot trust public infrastructure, Fulcio and Rekor can be deployed on your own servers using the Docker Compose configuration provided above.

### Can I use multiple signing tools together?

Yes. Many organizations use Cosign for CI/CD signing and Notation for registry-level verification. They operate at different layers — Cosign signs the image content, while Notation stores signatures in the OCI registry's manifest index. Using both provides defense in depth.

### How does in-toto differ from SLSA?

in-toto is the reference implementation for SLSA (Supply-chain Levels for Software Artifacts) provenance. SLSA defines a framework and maturity levels; in-toto provides the cryptographic tooling to implement it. You can think of SLSA as the standard and in-toto as the implementation.

### Is keyless signing (Cosign) secure for production?

Keyless signing uses short-lived OIDC certificates (typically valid for 10 minutes) tied to your identity provider. This is considered more secure than persistent private keys because there are no long-lived secrets to steal. The signature is permanently recorded in Rekor's transparency log, providing non-repudiation.

### Which tool integrates best with Harbor registry?

Notation has the deepest Harbor integration, as Harbor natively supports Notary v2 signatures. Cosign also works well with Harbor. Both can be configured to enforce signature verification before images are pulled.

### Can these tools sign non-container artifacts?

Yes. Cosign can sign binaries, files, and Helm charts. Notation supports any OCI artifact type. in-toto can track any build step regardless of artifact type. The key difference is the verification model, not the supported formats.

### How do I rotate signing keys with each tool?

With **Cosign keyless mode**, there are no persistent keys to rotate — each signing session generates a fresh certificate. With **local Cosign keys**, replace the key pair and re-sign all images. With **Notation**, rotate your X.509 certificates through your CA and update the trust policy. With **in-toto**, generate new key pairs and update the root layout with new key IDs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Supply Chain Security: Sigstore/Cosign vs Notation vs in-toto 2026",
  "description": "Complete guide to self-hosted supply chain security tools — compare Sigstore/Cosign, Notation (Notary v2), and in-toto for container and artifact signing, verification, and provenance tracking.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
