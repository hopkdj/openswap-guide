---
title: "Self-Hosted Kubernetes Config Encryption at Rest: aescbc vs KMS vs Secretbox (2026)"
date: "2026-05-22"
tags: ["kubernetes", "security", "encryption", "secrets", "self-hosted"]
draft: false
description: "Compare native Kubernetes encryption providers for securing secrets at rest — aescbc, KMS v2, and secretbox. Complete guide with configuration examples and security trade-offs."
---

Kubernetes stores sensitive configuration data — passwords, API keys, TLS certificates — as `Secret` objects in etcd. By default, these values are stored as base64-encoded plaintext, meaning anyone with etcd access can read them. Kubernetes provides multiple encryption-at-rest providers to protect this data. This guide compares the three most practical approaches for self-hosted clusters.

## Why Encrypt Kubernetes Secrets at Rest?

etcd is the single source of truth for your entire Kubernetes cluster state. Every Secret, ConfigMap, ServiceAccount token, and custom resource lives there. Without encryption at rest, a compromised etcd backup or direct filesystem access exposes every credential in your cluster.

The Kubernetes API server supports multiple encryption providers that transform Secret data before writing to etcd. Each provider offers different security guarantees, performance characteristics, and operational complexity.

**Key considerations when choosing an encryption provider:**

- **Security level**: AES-256-GCM provides authenticated encryption; aescbc lacks authentication tags
- **Key management**: KMS providers support external key rotation; local providers require manual key management
- **Performance**: Local encryption (aescbc, secretbox) adds negligible latency; KMS adds network round-trip overhead
- **Compliance**: FIPS 140-2, SOC 2, and HIPAA requirements may mandate specific encryption standards
- **Operational overhead**: KMS requires running and maintaining an external key management service

## Encryption Provider Comparison

| Feature | aescbc | KMS v2 | secretbox (AES-GCM) |
|---------|--------|--------|---------------------|
| Algorithm | AES-CBC + HMAC-SHA256 | Envelope encryption via KMS | AES-256-GCM |
| Authenticated encryption | Yes (HMAC) | Yes (depends on KMS) | Yes (GCM tag) |
| Key rotation | Manual (update config + re-encrypt) | Automatic via KMS | Manual |
| External key storage | No | Yes (AWS KMS, Azure KV, Vault) | No |
| Performance overhead | ~1ms per operation | 5-15ms (network call) | ~1ms per operation |
| FIPS 140-2 compliant | No | Yes (with compliant KMS) | No |
| Minimum K8s version | All versions | 1.26+ (KMS v2) | All versions |
| etcd storage increase | ~32 bytes per secret | ~100 bytes per secret | ~16 bytes per secret |
| Disaster recovery | Export keys from config file | Depends on KMS availability | Export keys from config file |

## Provider 1: aescbc — The Traditional Choice

aescbc combines AES-CBC encryption with HMAC-SHA256 authentication. It has been the default recommendation for Kubernetes encryption at rest since version 1.7.

### Configuration

Create an `EncryptionConfiguration` resource:

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

Generate the encryption key:

```bash
# Generate a random 32-byte key and base64 encode it
head -c 32 /dev/urandom | base64
# Example output: bXlzZWNyZXRrZXlmb3JrdWJlcm5ldGVzZW5jcnlwdGlvbjEyMzQ1Njc4OTA=
```

Apply to your API server configuration (for kubeadm clusters, edit `/etc/kubernetes/manifests/kube-apiserver.yaml`):

```yaml
spec:
  containers:
  - name: kube-apiserver
    command:
    - kube-apiserver
    - --encryption-provider-config=/etc/kubernetes/encryption-config.yaml
    volumeMounts:
    - name: encryption-config
      mountPath: /etc/kubernetes/encryption-config.yaml
      readOnly: true
  volumes:
  - name: encryption-config
    hostPath:
      path: /etc/kubernetes/encryption-config.yaml
      type: File
```

### Docker Compose for Local Testing

```yaml
version: "3.8"
services:
  etcd:
    image: registry.k8s.io/etcd:3.5.12-0
    command:
      - etcd
      - --advertise-client-urls=http://127.0.0.1:2379
      - --listen-client-urls=http://0.0.0.0:2379
      - --data-dir=/var/lib/etcd
    volumes:
      - etcd-data:/var/lib/etcd

  apiserver:
    image: registry.k8s.io/kube-apiserver:v1.29.4
    command:
      - kube-apiserver
      - --etcd-servers=http://etcd:2379
      - --encryption-provider-config=/etc/kubernetes/encryption-config.yaml
      - --service-account-key-file=/etc/kubernetes/sa.pub
      - --service-account-signing-key-file=/etc/kubernetes/sa.key
    volumes:
      - ./encryption-config.yaml:/etc/kubernetes/encryption-config.yaml:ro

volumes:
  etcd-data:
```

### Pros and Cons

**Pros:**
- No external dependencies — encryption keys stored in the configuration file
- Mature and well-tested across thousands of production clusters
- Supports key rotation by adding new keys to the `keys` list (new data encrypted with first key, old data decrypted with any key)
- Fast — no network calls during encryption/decryption

**Cons:**
- Keys must be stored on the API server filesystem — if the server is compromised, keys are accessible
- Manual key rotation process requires updating the config file and restarting the API server
- CBC mode requires careful IV handling; while Kubernetes handles this correctly, it's considered less modern than GCM

## Provider 2: KMS v2 — Envelope Encryption with External Key Management

KMS v2 (introduced in Kubernetes 1.26) uses envelope encryption: a locally-generated Data Encryption Key (DEK) encrypts the secret, and an external Key Management Service encrypts the DEK. The KMS plugin communicates with the external service via gRPC.

### Supported KMS Providers

| KMS Service | Plugin Repository | Stars | Description |
|-------------|-------------------|-------|-------------|
| AWS KMS | `kubernetes-sigs/aws-encryption-provider` | 580+ | AWS-managed key service |
| Azure Key Vault | `Azure/kubernetes-kms-plugin` | 120+ | Azure-managed key vault |
| HashiCorp Vault | `hashicorp/vault` (built-in) | 35,000+ | Self-hosted secrets management |
| Google Cloud KMS | `googlecloudplatform/k8s-cloud-kms-plugin` | 100+ | GCP-managed key service |

### Configuration with HashiCorp Vault

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - kms:
          name: vault-kms
          endpoint: unix:///var/run/kmsplugin/socket.sock
          apiVersion: v2
      - identity: {}
```

### Vault KMS Plugin Deployment

```yaml
version: "3.8"
services:
  vault:
    image: hashicorp/vault:1.16
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: myroot
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
    ports:
      - "8200:8200"
    cap_add:
      - IPC_LOCK

  kms-plugin:
    image: ghcr.io/hashicorp/vault-k8s:0.19.0
    command:
      - vault-kms-plugin
      - --address=http://vault:8200
      - --auth-method=token
      - --token=myroot
      - --key-name=encryption-key
      - --listen=unix:///var/run/kmsplugin/socket.sock
    volumes:
      - kms-socket:/var/run/kmsplugin
    depends_on:
      - vault

volumes:
  kms-socket:
```

### Key Rotation

KMS v2 handles key rotation automatically. When you rotate the key in your KMS service:
1. New secrets are encrypted with a new DEK
2. The new DEK is encrypted with the new KMS key
3. Old secrets remain decryptable using the old KMS key version
4. No API server restart required

### Pros and Cons

**Pros:**
- External key management — keys never touch the API server filesystem
- Automatic key rotation through the KMS service
- Audit logging for key access (depending on KMS provider)
- Meets compliance requirements for key separation
- KMS v2 eliminates the caching vulnerability present in KMS v1

**Cons:**
- Requires running and maintaining an external KMS service
- Adds 5-15ms latency per encryption/decryption operation
- KMS service outage can prevent reading/writing secrets
- More complex disaster recovery — requires KMS backup restoration

## Provider 3: secretbox (AES-GCM) — Lightweight Authenticated Encryption

secretbox uses NaCl's crypto_secretbox (AES-256-GCM under the hood) for authenticated encryption. It's simpler than aescbc and produces smaller ciphertext.

### Configuration

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - secretbox:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

Generate the key (same process as aescbc):

```bash
head -c 32 /dev/urandom | base64
```

### Pros and Cons

**Pros:**
- Authenticated encryption built into the cipher (GCM mode)
- Smaller ciphertext overhead (~16 bytes vs ~32 bytes for aescbc)
- Simpler implementation than aescbc (no separate HMAC step)
- No external dependencies

**Cons:**
- Same key management limitations as aescbc
- Less widely deployed than aescbc (newer feature)
- No FIPS 140-2 compliance

## Choosing the Right Provider

### For Development and Testing

Use **secretbox** or **aescbc**. Both require zero external infrastructure and provide strong encryption. The choice between them is marginal — secretbox is slightly more modern, while aescbc has more production history.

### For Production Self-Hosted Clusters

Use **KMS v2 with HashiCorp Vault**. Vault is the most popular self-hosted secrets management platform (35,000+ GitHub stars), and the KMS v2 integration provides automatic key rotation, audit logging, and compliance-grade key separation.

### For Cloud-Managed Kubernetes

Use your cloud provider's KMS service (AWS KMS, Azure Key Vault, or GCP Cloud KMS). These integrate natively with your cloud identity management and provide the simplest operational experience.

## Why Self-Host Your KMS?

Running your own key management service gives you full control over encryption keys without depending on cloud providers. For organizations with data residency requirements, air-gapped environments, or multi-cloud strategies, self-hosted KMS eliminates vendor lock-in.

HashiCorp Vault is the most mature option, offering HSM-backed key storage, automatic key rotation, and comprehensive audit logging. For lighter deployments, the `aws-encryption-provider` proxy can run locally against a self-hosted MinIO instance using AWS-compatible APIs.

For additional Kubernetes security hardening, see our [Kubernetes admission controllers guide](../2026-05-16-self-hosted-kubernetes-admission-controllers-kyverno-opa-gatekeeper-kubewarden-guide/) and [container runtime security comparison](../2026-05-07-kubearmor-vs-falco-vs-tetragon-runtime-security-guide/).

## Security Best Practices

1. **Always include `identity: {}` as the last provider** — this allows reading unencrypted data during migration but should never be the active provider in production
2. **Rotate keys regularly** — for local providers, add a new key to the top of the `keys` list and restart the API server
3. **Encrypt etcd backups** — encryption at rest protects live data, but backups need separate encryption
4. **Restrict etcd access** — limit filesystem and network access to etcd regardless of encryption
5. **Monitor encryption status** — use `kubectl get secrets --all-namespaces -o jsonpath='{.kind}'` to verify secrets are encrypted

## FAQ

### What happens if I lose my encryption key?

All secrets encrypted with that key become permanently unreadable. For local providers (aescbc, secretbox), the key is in your `EncryptionConfiguration` file — back it up securely. For KMS providers, key recovery depends on your KMS service's backup and recovery procedures.

### Can I switch encryption providers without downtime?

Yes. Add the new provider to the top of the `providers` list while keeping the old provider second. New secrets will use the new provider; old secrets will still be readable. Then run a re-encryption:

```bash
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
```

After re-encryption, remove the old provider from the configuration.

### Does encryption at rest protect against API server compromise?

No. If an attacker has access to the API server, they can read the encryption configuration and decrypt secrets. Encryption at rest protects against etcd backup exposure and direct filesystem access, not runtime attacks. For runtime protection, combine with network policies and pod security standards.

### Which provider is recommended for production?

KMS v2 with an external key management service (Vault, AWS KMS, Azure Key Vault) is the recommended approach for production. It provides automatic key rotation, audit logging, and key separation from the API server.

### Does encryption at rest affect Kubernetes performance?

Local providers (aescbc, secretbox) add approximately 1ms per secret operation — negligible for most workloads. KMS providers add 5-15ms per operation due to the network call to the KMS service. For clusters with high secret churn (thousands of secret operations per second), local providers are preferred.

### How do I verify that my secrets are encrypted?

Check the etcd data directly:

```bash
ETCDCTL_API=3 etcdctl get /registry/secrets/default/my-secret --print-value-only
```

Encrypted values appear as base64-encoded ciphertext. Unencrypted values appear as readable base64 (the original secret content).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Config Encryption at Rest: aescbc vs KMS vs Secretbox (2026)",
  "description": "Compare native Kubernetes encryption providers for securing secrets at rest — aescbc, KMS v2, and secretbox. Complete guide with configuration examples.",
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
