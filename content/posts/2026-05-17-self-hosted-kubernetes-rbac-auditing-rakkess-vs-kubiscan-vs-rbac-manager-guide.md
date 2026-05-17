---
title: "Self-Hosted Kubernetes RBAC Auditing: rakkess vs KubiScan vs rbac-manager (2026)"
date: "2026-05-17"
tags: ["kubernetes", "rbac", "security", "audit", "access-control", "kubernetes-security", "devops", "comparison", "guide", "self-hosted", "docker"]
draft: false
---

Role-Based Access Control (RBAC) is the foundation of Kubernetes security. But as clusters grow in size and complexity, managing and auditing RBAC configurations becomes increasingly challenging. Overly permissive roles, unused service accounts, and stale bindings create security risks that can lead to lateral movement and privilege escalation.

In this guide, we compare three open-source tools for Kubernetes RBAC auditing: **rakkess** (Review Access), **KubiScan** by CyberArk, and **rbac-manager** by Fairwinds. Each takes a different approach to RBAC visibility, risk detection, and access management.

## What Is Kubernetes RBAC Auditing?

RBAC auditing is the process of reviewing, validating, and monitoring Role and ClusterRole bindings in a Kubernetes cluster. A comprehensive RBAC audit answers critical questions:

- Which users and service accounts have access to which resources?
- Are there any overly permissive wildcard (`*`) permissions?
- Which roles are unused or stale?
- Can any service account escalate its own privileges?
- Are there bindings that violate the principle of least privilege?

| Feature | rakkess | KubiScan | rbac-manager |
|---|---|---|---|
| **Creator** | Cornelius Weig | CyberArk | Fairwinds (now part of Google Cloud) |
| **Stars** | 1,400+ | 1,400+ | 1,600+ |
| **Primary Purpose** | Access review / visualization | Risk assessment / vulnerability scanning | Declarative RBAC management |
| **Type** | kubectl plugin (CLI) | CLI tool | Kubernetes Operator |
| **Risk Detection** | Visual access matrix | Automated risk scoring | Policy-based enforcement |
| **Privilege Escalation Detection** | Yes (via access review) | Yes (explicit checks) | Via policy definitions |
| **Wildcard Permission Detection** | Yes (in access output) | Yes (dedicated checks) | Via RBACDefinition policies |
| **Namespace Scoping** | Yes | Yes | Yes |
| **Export / Reporting** | Table, text, JSON | JSON, CSV | CRD-based state |
| **Best For** | Quick access reviews | Security audits, pentesting | Declarative RBAC governance |

## rakkess (Review Access)

rakkess is a kubectl plugin that provides a visual matrix of who can access what in your Kubernetes cluster. It answers the simple but critical question: "Can this user/service account do this action on this resource?"

### Key Features

- **Access review matrix**: Shows which subjects can perform which actions on which resources
- **Namespace-level scoping**: Review access within specific namespaces
- **Wildcard expansion**: Expands wildcards in roles to show actual permissions
- **Human-readable output**: Clear table format showing allow/deny status
- **Lightweight**: Single binary, no server-side components required
- **kubernetes-sigs aligned**: Follows Kubernetes API conventions

### Installation

```bash
# Install via krew (recommended)
kubectl krew install access-matrix

# Or install binary directly
curl -Lo rakkess https://github.com/corneliusweig/rakkess/releases/download/v0.5.2/rakkess-linux-amd64
chmod +x rakkess
sudo mv rakkess /usr/local/bin/
```

### Usage

```bash
# Show access matrix for current user
kubectl access-matrix

# Show access matrix for a specific service account
kubectl access-matrix --sa my-service-account

# Show access matrix for a specific namespace
kubectl access-matrix -n kube-system

# Show access matrix for all subjects
kubectl access-matrix --all-subjects

# Export as JSON for further analysis
kubectl access-matrix --output json > access-matrix.json
```

### Example Output

```
NAMESPACE   RESOURCE       VERBS        SUBJECT
default     pods           get,list     system:serviceaccount:default:my-sa
default     deployments    get,list,create,delete   system:serviceaccount:default:my-sa
kube-system configmaps    get          system:serviceaccount:kube-system:coredns
cluster     nodes          get,list,watch   system:serviceaccount:monitoring:prometheus
```

### Docker Compose (Local Testing)

```yaml
version: "3.8"
services:
  rakkess:
    image: bitnami/kubectl:latest
    entrypoint: ["sh", "-c", "kubectl krew install access-matrix && kubectl access-matrix --all-subjects"]
    volumes:
      - ${HOME}/.kube/config:/root/.kube/config:ro
    environment:
      - KUBECONFIG=/root/.kube/config
```

## KubiScan (Kubernetes Security Scanner)

KubiScan, developed by CyberArk, is a security-focused RBAC auditing tool that identifies dangerous permissions, potential privilege escalation paths, and misconfigurations in your Kubernetes cluster.

### Key Features

- **Risk-based scanning**: Categorizes risks by severity (critical, high, medium, low)
- **Privilege escalation detection**: Identifies roles that can escalate to cluster-admin
- **Secret access scanning**: Finds roles that can read secrets across namespaces
- **Wildcard permission detection**: Identifies roles with `*` permissions
- **Impersonation detection**: Finds accounts that can impersonate other users
- **JSON/CSV export**: Structured output for compliance reporting

### Installation

```bash
# Clone and install
git clone https://github.com/cyberark/KubiScan.git
cd KubiScan
pip install -r requirements.txt

# Or run via Docker
docker run --rm -it cyberark/kubiscan --help
```

### Usage

```bash
# List all risky subjects (users/service accounts with dangerous permissions)
python3 KubiScan.py -rs

# List all risky roles (roles with wildcard permissions)
python3 KubiScan.py -rr

# Show all subjects with cluster-admin binding
python3 KubiScan.py -sca

# Find roles that can read secrets
python3 KubiScan.py -rsr

# Find roles that can escalate privileges
python3 KubiScan.py -rpe

# Export results as JSON
python3 KubiScan.py -rs -j > risky_subjects.json
```

### Example Risk Categories

```
[CRITICAL] ServiceAccount 'jenkins' in namespace 'ci' has 'cluster-admin' role
[HIGH] Role 'pod-manager' in namespace 'default' has wildcard '*' verbs
[HIGH] ClusterRole 'secret-reader' can read secrets across all namespaces
[MEDIUM] Role 'deployment-admin' can create pods with privileged security context
[LOW] ServiceAccount 'monitoring' has read access to configmaps in kube-system
```

## rbac-manager (Declarative RBAC Management)

rbac-manager is a Kubernetes operator that enables declarative RBAC configuration. Instead of managing Roles and RoleBindings directly, you define RBACDefinition CRDs that the operator translates into the appropriate Kubernetes RBAC resources.

### Key Features

- **Declarative RBAC**: Define access policies as Kubernetes CRDs
- **GitOps-friendly**: Store RBAC definitions in Git for version control and review
- **Automatic reconciliation**: Operator ensures actual RBAC matches desired state
- **Multi-subject binding**: One RBACDefinition can bind multiple subjects to multiple roles
- **Namespace templating**: Use templates to apply RBAC across multiple namespaces
- **Policy-based governance**: Enforce least-privilege through RBACDefinition constraints

### Installation

```bash
# Install via Helm
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install rbac-manager fairwinds-stable/rbac-manager   --namespace rbac-manager --create-namespace

# Or install via kubectl
kubectl apply -f https://github.com/FairwindsOps/rbac-manager/releases/download/v0.13.0/rbac-manager.yaml
```

### Usage

```yaml
# RBACDefinition example
apiVersion: rbacmanager.reactive.pub/v1
kind: RBACDefinition
metadata:
  name: developer-access
rbacBindings:
  - name: developers
    subjects:
      - kind: Group
        name: developers@example.com
    clusterRoles:
      - view
    roles:
      - namespaceSelector:
          matchLabels:
            environment: development
        clusterRoles:
          - edit
      - namespaceSelector:
          matchLabels:
            environment: production
        clusterRoles:
          - view
```

```bash
# Apply the RBAC definition
kubectl apply -f developer-access.yaml

# Verify the generated bindings
kubectl get rolebindings,clusterrolebindings -l rbac-manager=developer-access
```

### Docker Compose (Local Testing)

```yaml
version: "3.8"
services:
  rbac-manager:
    image: quay.io/fairwinds/rbac-manager:latest
    volumes:
      - ${HOME}/.kube/config:/root/.kube/config:ro
    environment:
      - KUBECONFIG=/root/.kube/config
    command: ["--rbac-definition-namespaces=default"]
```

## Comparison: When to Use Each Tool

### Choose rakkess if:
- You need a quick, visual overview of who can access what
- You are conducting routine access reviews
- You want lightweight, client-side auditing with no server components
- You need to answer "can this user do this?" for specific subjects
- Your team values simplicity and kubectl integration

### Choose KubiScan if:
- You are performing a security audit or penetration test
- You need automated risk scoring and categorization
- You want to detect privilege escalation paths and dangerous permissions
- You need compliance-ready reports (JSON/CSV export)
- Your organization requires systematic RBAC vulnerability scanning

### Choose rbac-manager if:
- You want declarative, GitOps-driven RBAC management
- You need to enforce RBAC policies across multiple namespaces
- You prefer CRD-based configuration over imperative commands
- Your team uses GitOps workflows (ArgoCD, Flux)
- You need automated reconciliation to prevent RBAC drift

## Why Self-Host Your RBAC Auditing Tools?

Running RBAC auditing tools on your own infrastructure ensures that sensitive access control data never leaves your environment. Unlike cloud-based security scanners, self-hosted tools operate entirely within your cluster boundary, reading RBAC configurations directly from the Kubernetes API server.

For teams managing multiple clusters, self-hosted RBAC auditing enables consistent security posture assessment across all environments. Combined with GitOps workflows and automated CI/CD pipelines, these tools support continuous RBAC compliance monitoring without external dependencies.

For Kubernetes policy enforcement, see our [policy engine comparison](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/). If you need broader cluster security hardening, check our [Kubernetes hardening guide](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/). For Kubernetes secrets management, our [secrets operator comparison](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) covers complementary security controls.

## FAQ

### What is the most dangerous RBAC misconfiguration in Kubernetes?

The most dangerous RBAC misconfiguration is granting `cluster-admin` or wildcard (`*`) permissions to service accounts that are exposed to user workloads. A compromised pod running with such a service account can take full control of the entire cluster, including reading secrets, modifying RBAC bindings, and deploying malicious workloads.

### How often should I audit RBAC in my Kubernetes cluster?

RBAC audits should be performed regularly — at minimum quarterly, and ideally after every significant change to roles, bindings, or service accounts. Automated tools like KubiScan can run on a schedule (e.g., daily) to continuously monitor for risky configurations.

### Can rakkess detect privilege escalation?

rakkess shows the access matrix for subjects, which allows you to visually identify if a subject has permissions that could lead to privilege escalation (e.g., the ability to create RoleBindings or modify Roles). However, it does not have explicit privilege escalation detection like KubiScan. For systematic escalation path detection, KubiScan is the better choice.

### Is rbac-manager compatible with existing RBAC configurations?

Yes, rbac-manager works alongside existing RBAC configurations. It manages only the resources created from RBACDefinition CRDs and does not modify manually created Roles or RoleBindings. This makes it safe to adopt incrementally.

### How does KubiScan determine risk levels?

KubiScan assigns risk levels based on the potential impact of the permissions. Critical risks include cluster-admin bindings and pod execution privileges. High risks include wildcard permissions and secret access across namespaces. Medium risks include the ability to create privileged pods. Low risks include read-only access to non-sensitive resources.

### Can I use these tools in an air-gapped environment?

All three tools can operate in air-gapped environments. rakkess and KubiScan are CLI tools that communicate directly with the Kubernetes API server. rbac-manager runs as an in-cluster operator. None of the tools require external internet connectivity for their core functionality.

### Should I use RBAC auditing alongside policy engines like OPA Gatekeeper?

Yes. RBAC auditing tools identify existing permission configurations and risks, while policy engines like OPA Gatekeeper or Kyverno enforce policies going forward. They are complementary: auditing tells you what is wrong today, while policy engines prevent future misconfigurations.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes RBAC Auditing: rakkess vs KubiScan vs rbac-manager (2026)",
  "description": "Compare three open-source Kubernetes RBAC auditing tools for access review, risk assessment, and declarative RBAC management in self-hosted clusters.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
