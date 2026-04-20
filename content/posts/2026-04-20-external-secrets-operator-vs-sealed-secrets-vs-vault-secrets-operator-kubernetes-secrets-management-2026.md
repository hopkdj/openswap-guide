---
title: "External Secrets Operator vs Sealed Secrets vs Vault Secrets Operator: Kubernetes Secrets Management 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "kubernetes", "security", "secrets-management"]
draft: false
description: "Compare External Secrets Operator, Sealed Secrets, and Vault Secrets Operator for managing secrets in Kubernetes clusters. Full deployment guides, feature comparison, and best practices for 2026."
---

Managing secrets in Kubernetes is one of the most critical challenges for platform engineers running self-hosted clusters. The native `Secret` object stores data as base64-encoded strings — not encrypted at rest by default — making it unsuitable for production workloads without additional tooling.

Three open-source operators have emerged as the leading solutions for this problem: **External Secrets Operator** (ESO), **Sealed Secrets** by Bitnami, and **Vault Secrets Operator** (VSO) from HashiCorp. Each takes a fundamentally different approach to the same problem. This guide compares them side by side and provides complete deployment instructions.

## Why Self-Host Your Kubernetes Secrets Management

Kubernetes Secrets are a core building block for any production cluster. Database credentials, TLS certificates, API tokens, and OAuth client secrets all need to be stored and distributed to pods securely. Relying on managed cloud services like AWS Secrets Manager or Azure Key Vault creates vendor lock-in and adds per-request costs that scale with cluster size.

Self-hosted secrets management gives you full control over:

- **Data residency** — secrets never leave your infrastructure
- **Cost predictability** — no per-API-call charges as your cluster scales
- **Compliance** — meet regulatory requirements for on-premises data handling
- **Multi-cluster consistency** — the same tooling works across bare metal, VMs, and edge clusters

For teams running self-hosted Kubernetes — whether on [k3s, k0s, or Talos Linux](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/) — having a reliable secrets management layer is essential for day-two operations.

## External Secrets Operator (ESO)

**GitHub:** [external-secrets/external-secrets](https://github.com/external-secrets/external-secrets) | **Stars:** 6,552 | **Language:** Go | **Last Push:** April 2026

External Secrets Operator reads secrets from external providers — including self-hosted backends — and syncs them into native Kubernetes `Secret` objects. It acts as a bridge between your secret store and your cluster.

### Architecture

ESO uses a declarative model with Custom Resource Definitions (CRDs):

- **SecretStore / ClusterSecretStore** — defines the connection to your backend (Vault, AWS Secrets Manager, Git, etc.)
- **ExternalSecret** — declares which secrets to fetch and how to map them into a Kubernetes Secret

The operator polls the backend at configurable intervals and updates the Kubernetes Secret whenever the source value changes.

### Installation via Helm

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

### Configuration: Syncing from HashiCorp Vault

First, create a `SecretStore` pointing to your self-hosted Vault instance:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: production
spec:
  provider:
    vault:
      server: "https://vault.internal:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "eso-reader"
```

Then define which secrets to sync:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: production/database
        property: username
    - secretKey: password
      remoteRef:
        key: production/database
        property: password
```

### Supported Backends

ESO supports the widest range of backends of any tool covered here:

| Backend Type | Examples |
|---|---|
| HashiCorp Vault | KV v1/v2, PKI, transit |
| Cloud providers | AWS Secrets Manager, GCP Secret Manager, Azure Key Vault |
| Self-hosted | Akeyless, 1Password, Keeper, Doppler |
| Infrastructure | Git (encrypted repos), Kubernetes native secrets |
| Password managers | Bitwarden, 1Password, Keeper |
| Specialized | CyberArk Conjur, IBM Secrets Manager, Pulumi ESC |

## Sealed Secrets

**GitHub:** [bitnami-labs/sealed-secrets](https://github.com/bitnami-labs/sealed-secrets) | **Stars:** 9,046 | **Language:** Go | **Last Push:** April 2026

Sealed Secrets takes a completely different approach. Instead of connecting to an external backend, it encrypts secrets **at the client side** using asymmetric cryptography and stores the encrypted result as a `SealedSecret` CRD in your Git repository. Only the cluster-side controller — which holds the decryption key — can turn a `SealedSecret` back into a usable Kubernetes `Secret`.

This makes it ideal for **GitOps workflows**: you can commit sealed secrets to version control without exposing the plaintext.

### Architecture

- **kubeseal CLI** — encrypts a Kubernetes Secret into a SealedSecret manifest using the cluster's public key
- **Sealed Secrets Controller** — runs in the cluster, decrypts SealedSecrets using the private key, and creates native Secrets

The encryption is one-way and per-cluster. A sealed secret created for one cluster cannot be decrypted by another cluster (unless you share the private key).

### Installation

```bash
# Install the controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.3/controller.yaml

# Install the kubeseal CLI (Linux)
curl -LO https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.3/kubeseal-0.27.3-linux-amd64.tar.gz
tar -xzf kubeseal-0.27.3-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

### Sealing a Secret

```bash
# Create a plaintext secret first
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cret-p@ssw0rd \
  --dry-run=client -o yaml > secret.yaml

# Seal it (requires cluster connectivity to fetch the public key)
kubeseal --format yaml < secret.yaml > sealed-secret.yaml

# The sealed-secret.yaml file contains encrypted data — safe to commit to Git
cat sealed-secret.yaml
```

The output looks like this:

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  encryptedData:
    username: AgBy3i4OJSWK+PiTySYZZA...
    password: AgA8mGZkOa4xVX+PiTySYZZA...
  template:
    metadata:
      name: db-credentials
      namespace: production
```

Apply the sealed secret to your cluster:

```bash
kubectl apply -f sealed-secret.yaml
# The controller decrypts it and creates a native Secret automatically
```

### Key Management

The controller generates an RSA-2048 keypair on first startup. You should back up the private key:

```bash
kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key \
  -o yaml > sealed-secrets-key-backup.yaml
```

Loss of this key means all sealed secrets in your cluster become unrecoverable.

## Vault Secrets Operator (VSO)

**GitHub:** [hashicorp/vault-secrets-operator](https://github.com/hashicorp/vault-secrets-operator) | **Stars:** 582 | **Language:** Go | **Last Push:** April 2026

Vault Secrets Operator is HashiCorp's official Kubernetes operator for syncing secrets from HashiCorp Vault into native Kubernetes Secrets. Unlike ESO, VSO only supports Vault as a backend — but it offers deeper Vault-specific features like dynamic secrets, lease renewal, and HCP Vault integration.

### Architecture

VSO mirrors ESO's declarative model but is purpose-built for Vault:

- **HCPAuth** or **Kubernetes Auth** — authentication method for connecting to Vault
- **HCPVaultDynamicSecret** or **VaultStaticSecret** — declares which Vault secrets to sync
- **VaultConnection** — defines the Vault server endpoint

The operator handles automatic lease rotation for dynamic secrets, ensuring database credentials and cloud API tokens are refreshed before expiration.

### Installation

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
helm install vault-secrets-operator hashicorp/vault-secrets-operator \
  --namespace vault-secrets-operator \
  --create-namespace
```

### Configuration: Static Secrets from Vault KV

Define the Vault connection:

```yaml
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultConnection
metadata:
  name: vault-conn
  namespace: production
spec:
  address: "https://vault.internal:8200"
  tlsServerName: "vault.internal"
```

Configure Kubernetes authentication:

```yaml
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultAuth
metadata:
  name: vault-auth
  namespace: production
spec:
  vaultConnectionRef: vault-conn
  method: kubernetes
  mount: kubernetes
```

Sync a static secret from Vault KV v2:

```yaml
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultStaticSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  vaultAuthRef: vault-auth
  mount: secret
  path: production/database
  destination:
    name: db-credentials
    create: true
```

### Dynamic Secrets

VSO's strongest feature is dynamic secret support. For example, rotating database credentials:

```yaml
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultDynamicSecret
metadata:
  name: postgres-role
  namespace: production
spec:
  vaultAuthRef: vault-auth
  mount: database
  path: postgresql/creds/readonly
  renew: true
  rolloutRestartTargets:
    - kind: Deployment
      name: my-app
```

This automatically creates short-lived database credentials and restarts the deployment when they rotate — no manual intervention needed.

## Feature Comparison

| Feature | External Secrets Operator | Sealed Secrets | Vault Secrets Operator |
|---|---|---|---|
| **GitHub Stars** | 6,552 | 9,046 | 582 |
| **Backend Support** | 25+ providers | N/A (client-side encryption) | Vault only |
| **Self-Hosted** | Yes (with Vault, Bitwarden, etc.) | Fully self-hosted | Yes (with Vault) |
| **GitOps Compatible** | Yes (ExternalSecret CRDs) | Yes (SealedSecret CRDs) | Yes (VaultStaticSecret CRDs) |
| **Encryption at Rest** | Depends on backend | AES-256 (client-side) | Depends on Vault config |
| **Dynamic Secrets** | No | No | Yes (lease renewal + auto-rotation) |
| **Secret Rotation** | Poll-based (configurable interval) | Manual re-seal required | Automatic lease renewal |
| **Multi-Cluster** | Yes (shared backend) | Possible (shared key) | Yes (shared Vault) |
| **Cross-Namespace** | ClusterSecretStore | Limited (namespace-scoped) | Limited (namespace-scoped) |
| **Kubernetes Auth** | Yes | No (uses kubeseal CLI) | Yes |
| **Helm Install** | Yes | Yes (via manifest) | Yes |
| **License** | Apache 2.0 | Apache 2.0 | BUSL 1.1 (HashiCorp) |
| **Maturity** | CNCF sandbox project | Production (Bitnami/VMware) | Production (HashiCorp) |

## When to Choose Which

### Choose External Secrets Operator when:

- You need to integrate with multiple secret backends (Vault, AWS, Bitwarden, etc.)
- You want CNCF-project governance and vendor-neutral architecture
- Your team already uses external secret stores and wants a Kubernetes sync layer
- You need broad provider support across cloud and self-hosted environments

ESO is the most flexible option. Its provider abstraction means you can switch backends without changing your `ExternalSecret` definitions. For teams using the [GitOps approach with ArgoCD or Flux](../argocd-vs-flux-self-hosted-gitops-guide/), ESO's declarative CRDs integrate seamlessly.

### Choose Sealed Secrets when:

- You want a zero-infrastructure solution — no external backend required
- Your primary workflow is GitOps with secrets stored in Git (encrypted)
- You have a single cluster or are comfortable sharing the decryption key
- You need simplicity over feature breadth

Sealed Secrets has the highest star count because it's the simplest to deploy. No external dependencies, no backend to maintain — just install the controller and use `kubeseal`. For small teams running a handful of clusters, this is often the fastest path to production-grade secret management.

### Choose Vault Secrets Operator when:

- HashiCorp Vault is already your secrets infrastructure
- You need **dynamic secrets** with automatic lease renewal and credential rotation
- You want deep Vault-specific features (PKI, transit, response wrapping)
- Your organization has standardized on the HashiCorp ecosystem

VSO is the specialist's choice. If you're already running Vault, it gives you the tightest integration — especially for dynamic secrets that auto-rotate database passwords and cloud credentials. Note that VSO uses the BUSL 1.1 license (HashiCorp's post-2023 license change), which restricts commercial redistribution.

## Deployment Guide: Full Self-Hosted Stack

Here's a complete self-hosted setup using Vault as the secrets backend with External Secrets Operator as the sync layer:

### Step 1: Deploy HashiCorp Vault

```yaml
# vault-values.yaml
server:
  ha:
    enabled: true
    replicas: 3
    raft:
      enabled: true
  ui:
    enabled: true
  dataStorage:
    size: 10Gi
  auditStorage:
    enabled: true
    size: 10Gi
```

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault -f vault-values.yaml \
  --namespace vault --create-namespace
```

### Step 2: Enable Kubernetes Auth in Vault

```bash
# Initialize and unseal Vault (use vault operator init for new cluster)
kubectl exec -it vault-0 -n vault -- vault login

# Enable Kubernetes auth method
kubectl exec -it vault-0 -n vault -- vault auth enable kubernetes

# Configure Kubernetes auth
kubectl exec -it vault-0 -n vault -- vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc:443"

# Create a policy for ESO
kubectl exec -it vault-0 -n vault -- vault policy write eso-policy - <<POLICY
path "secret/data/production/*" {
  capabilities = ["read"]
}
POLICY

# Create a role bound to the ESO service account
kubectl exec -it vault-0 -n vault -- vault write auth/kubernetes/role/eso-reader \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=eso-policy \
  ttl=24h
```

### Step 3: Deploy External Secrets Operator

```bash
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace
```

### Step 4: Create SecretStore and ExternalSecret

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-cluster-store
spec:
  provider:
    vault:
      server: "http://vault.vault.svc:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "eso-reader"
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: default
spec:
  refreshInterval: "1m"
  secretStoreRef:
    name: vault-cluster-store
    kind: ClusterSecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: production/database
        property: connection_string
    - secretKey: API_KEY
      remoteRef:
        key: production/api
        property: key
```

## Best Practices for Production

1. **Never commit plaintext secrets to Git** — use Sealed Secrets, ESO with encrypted backends, or Git-encrypted files
2. **Rotate the Sealed Secrets key periodically** — and keep secure backups of every generation
3. **Use namespace-scoped SecretStores** for multi-tenant clusters to prevent cross-namespace secret access
4. **Set appropriate `refreshInterval`** — too short creates Vault load, too long delays secret rotation
5. **Audit secret access** — enable Vault audit logging and monitor ESO sync events
6. **Back up encryption keys** — losing the Sealed Secrets private key or Vault unseal keys means permanent data loss
7. **Test secret rotation** — periodically verify that dynamic secrets rotate correctly and pods receive updated credentials

For teams building a complete self-hosted infrastructure, secrets management is just one piece. A comprehensive approach also covers [secret management at the application layer](../best-self-hosted-secret-management-vault-infisical-passbolt-2026/) and [container security hardening](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide/) to protect the entire stack.

## FAQ

### What is the difference between External Secrets Operator and Vault Secrets Operator?

External Secrets Operator supports 25+ secret backends (Vault, AWS, GCP, Azure, Bitwarden, 1Password, etc.) and is a CNCF sandbox project. Vault Secrets Operator only supports HashiCorp Vault but offers deeper integration with Vault-specific features like dynamic secrets and automatic lease renewal. Choose ESO for flexibility; choose VSO if Vault is your sole backend and you need dynamic secret rotation.

### Can Sealed Secrets be used with multiple Kubernetes clusters?

Yes, but you need to share the Sealed Secrets controller's private key across clusters. Export the key from the primary cluster with `kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml` and import it into secondary clusters before deploying the controller. All clusters using the same key can decrypt the same SealedSecret manifests.

### Does Sealed Secrets support secret rotation?

No. Sealed Secrets uses static, client-side encryption. To rotate a secret, you must: (1) update the plaintext secret, (2) re-run `kubeseal` to create a new SealedSecret manifest, (3) apply the updated manifest to the cluster. If you need automatic rotation, use External Secrets Operator or Vault Secrets Operator instead.

### Is Vault Secrets Operator free to use?

Vault Secrets Operator uses the Business Source License (BUSL) 1.1, which HashiCorp adopted in 2023. This means you can use it freely for internal purposes, but you cannot offer it as a commercial service to third parties. External Secrets Operator and Sealed Secrets both use the Apache 2.0 license, which has no such restrictions.

### Can External Secrets Operator sync secrets in real-time?

ESO uses a polling-based approach with a configurable `refreshInterval` (default 1 hour, minimum ~1 second). For near-real-time sync, set `refreshInterval: "1s"`, but be aware that very short intervals increase load on your backend. ESO does not support webhook-based push notifications from backends. Vault Secrets Operator is better for real-time needs because it handles Vault's native lease renewal mechanism.

### How do I back up Sealed Secrets encryption keys?

Run the following command to export the keypair:
```bash
kubectl get secret -n kube-system \
  -l sealedsecrets.bitnami.com/sealed-secrets-key \
  -o yaml > sealed-secrets-key-backup.yaml
```
Store this file securely (encrypted, off-cluster). Without it, all SealedSecrets in your cluster become unrecoverable. Consider rotating keys periodically and keeping backups of every generation for migration compatibility.

### Which tool is best for a GitOps workflow?

All three support GitOps, but in different ways. Sealed Secrets is the most natural fit — encrypted secrets are committed directly to Git as `SealedSecret` CRDs, and ArgoCD or Flux applies them. External Secrets Operator works well too, with `ExternalSecret` CRDs in Git pointing to backend paths. Vault Secrets Operator uses similar `VaultStaticSecret` CRDs. The key difference is where the actual secret values live: in Git (sealed), in Vault (ESO/VSO), or in cloud providers (ESO).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "External Secrets Operator vs Sealed Secrets vs Vault Secrets Operator: Kubernetes Secrets Management 2026",
  "description": "Compare External Secrets Operator, Sealed Secrets, and Vault Secrets Operator for managing secrets in Kubernetes clusters. Full deployment guides, feature comparison, and best practices for 2026.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
