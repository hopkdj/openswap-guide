---
title: "Self-Hosted HashiCorp Vault Web UIs: Goldfish vs vault-ui vs Dashboards"
date: "2026-05-22"
tags: ["vault", "hashicorp", "secrets-management", "web-ui", "security"]
draft: false
---

HashiCorp Vault is the industry-standard secrets management platform, providing secure storage, dynamic credential generation, encryption-as-a-service, and identity-based access control. While Vault's CLI and API are comprehensive, many teams need a web interface for day-to-day secret management, especially for non-CLI users like developers and auditors.

This guide compares three open-source HashiCorp Vault web UIs — **Goldfish**, **vault-ui** (djenriquez), and **vault-ui** (nyxcharon) — to help you choose the right interface for your self-hosted Vault deployment.

## Why Self-Host a Vault Web UI?

Vault's built-in capabilities are powerful but its native web interface is limited. A self-hosted web UI bridges the gap between Vault's full API capabilities and the needs of teams who prefer graphical interfaces:

- **Developer self-service** — let developers read and write secrets without learning the Vault CLI or API
- **Audit and compliance** — provide auditors read-only access to review secret policies and access logs
- **Faster onboarding** — new team members can browse and manage secrets through an intuitive interface
- **Reduced operator burden** — operators spend less time fulfilling secret access requests through the CLI
- **Policy visualization** — understand which policies grant which permissions through a visual interface

If you're also managing Nomad clusters, check our [Nomad management UI comparison](../2026-05-22-self-hosted-hashicorp-nomad-management-uis-hashi-ui-damon-ntui-guide/). For broader secrets management strategies, see our [Vault secrets rotation guide](../2026-05-02-self-hosted-secrets-rotation-vault-infisical-external-secrets-operator-guide/).

## Goldfish: The Vue.js Vault Dashboard

[Goldfish](https://github.com/Caiyeon/goldfish) (2,128+ GitHub stars) is a HashiCorp Vault web UI built with Vue.js and Go. It was one of the earliest and most popular third-party Vault interfaces, providing a clean, modern interface for secret management.

### Key Features

- **Secret browser** — navigate KV v1 and v2 secret engines with a tree-view interface
- **Policy management** — view, create, and edit Vault policies through a visual editor
- **Auth method configuration** — configure AppRole, LDAP, Kubernetes, and other auth backends
- **Token lifecycle** — generate, renew, and revoke tokens from the UI
- **Seal/unseal support** — perform Vault seal and unseal operations through the browser
- **Multi-Vault support** — switch between multiple Vault instances from a single session

### Deployment

Goldfish is distributed as a Docker image and can be deployed alongside your Vault server:

```yaml
version: "3"
services:
  goldfish:
    image: caiyeon/goldfish:latest
    ports:
      - "8000:8000"
    environment:
      - VAULT_ADDR=https://vault-server:8200
      - GOLDFISH_CONFIG=/config/config.hcl
    volumes:
      - ./goldfish-config.hcl:/config/config.hcl
    restart: unless-stopped
```

Configuration file (`goldfish-config.hcl`):

```hcl
vault = {
  address = "https://vault-server:8200"
}

listen = "0.0.0.0:8000"

secret_mounts = [
  { path = "secret", type = "kv2" },
  { path = "database", type = "database" }
]
```

### Strengths and Limitations

Goldfish offers the most polished UI experience with its Vue.js frontend and comprehensive feature set. It supports both KV v1 and v2 secret engines and provides excellent policy visualization. However, the project's last significant update was in 2018, and it may not support newer Vault features like PKI certificate management or Transit encryption engine.

## vault-ui (djenriquez): The React-Based Manager

[vault-ui by djenriquez](https://github.com/djenriquez/vault-ui) (1,314+ GitHub stars) is a React-based Vault management interface that provides a comprehensive web UI for all major Vault operations.

### Key Features

- **Full secret engine support** — KV v1/v2, database, PKI, Transit, and SSH secret engines
- **Auth backend management** — configure and manage all major auth methods
- **Policy editor** — syntax-highlighted policy editor with HCL validation
- **Token generation** — create tokens with specific policies, TTLs, and metadata
- **Audit device management** — configure file, syslog, and socket audit backends
- **Replication status** — view Vault Enterprise replication topology and performance

### Deployment

```yaml
version: "3"
services:
  vault-ui:
    image: djenriquez/vault-ui:latest
    ports:
      - "8000:8000"
    environment:
      - VAULT_URL_DEFAULT=https://vault-server:8200
    restart: unless-stopped
```

### Strengths and Limitations

The djenriquez vault-ui provides broader secret engine coverage than Goldfish, including PKI and Transit engine management. Its React-based interface is responsive and handles complex policy editing well. Like Goldfish, however, this project has seen reduced maintenance activity in recent years and may not support the latest Vault features.

## vault-ui (nyxcharon): The Lightweight Alternative

[vault-ui by nyxcharon](https://github.com/nyxcharon/vault-ui) (141+ GitHub stars) is a simpler Vault web interface focused on core secret management operations. It provides a more minimal but functional UI for everyday Vault tasks.

### Key Features

- **Secret CRUD operations** — create, read, update, and delete secrets in KV stores
- **Token management** — generate and revoke tokens with specified policies
- **Auth method login** — authenticate via token, AppRole, username/password
- **Basic policy viewing** — read existing policies (write support is limited)
- **Mount point browsing** — discover and browse mounted secret engines

### Deployment

```yaml
version: "3"
services:
  vault-ui:
    image: nyxcharon/vault-ui:latest
    ports:
      - "8080:8080"
    environment:
      - VAULT_ADDR=https://vault-server:8200
    restart: unless-stopped
```

### Strengths and Limitations

This vault-ui is the most lightweight option, making it suitable for environments where you only need basic secret browsing and token management. It has fewer dependencies and a smaller attack surface. The tradeoff is limited support for advanced features like PKI certificate issuance, dynamic database credentials, or policy editing.

## Comparison Table

| Feature | Goldfish | vault-ui (djenriquez) | vault-ui (nyxcharon) |
|---------|----------|----------------------|---------------------|
| **Framework** | Vue.js + Go | React + Node.js | Node.js |
| **GitHub Stars** | 2,128+ | 1,314+ | 141+ |
| **KV v2 Support** | Yes | Yes | Yes |
| **PKI Engine** | No | Yes | No |
| **Transit Engine** | No | Yes | No |
| **Policy Editor** | Yes (visual) | Yes (HCL) | View only |
| **Auth Methods** | Multiple | Multiple | Token/AppRole |
| **Seal/Unseal** | Yes | Yes | No |
| **Multi-Vault** | Yes | No | No |
| **Audit Devices** | No | Yes | No |
| **Last Active** | 2018 | 2018 | 2017 |
| **Docker Image** | Official | Community | Community |
| **Best For** | General secret mgmt | Full Vault admin | Quick secret browsing |

## Choosing the Right Vault Web UI

**Use Goldfish if:** You need a polished, user-friendly interface for general secret management. Its Vue.js frontend provides the smoothest experience for developers and auditors who need to browse and manage KV secrets. The multi-Vault support is useful for teams managing staging and production environments.

**Use vault-ui (djenriquez) if:** You need comprehensive Vault administration including PKI certificate management, Transit encryption, and audit device configuration. It's the most feature-complete option for operators who manage the full breadth of Vault's capabilities.

**Use vault-ui (nyxcharon) if:** You need a minimal interface for basic secret browsing and token generation. It's suitable for environments where you want the smallest possible UI footprint and only need core KV operations.

## Why Self-Host Your Vault UI?

Running a self-hosted Vault web interface is critical for security-sensitive environments:

- **No third-party data exposure** — your secrets never transit through external SaaS dashboards
- **Full audit trail** — all UI interactions are logged through Vault's native audit devices
- **Air-gapped compatible** — deploy in environments with no internet connectivity
- **Custom integration** — connect to your existing LDAP, OIDC, or SAML identity providers
- **Cost control** — no per-user or per-secret licensing fees

For teams building out a complete HashiCorp stack, our [Nomad management UI guide](../2026-05-22-self-hosted-hashicorp-nomad-management-uis-hashi-ui-damon-ntui-guide/) covers the orchestration side. For SSH certificate workflows, see our [SSH certificate management guide](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide/).

## FAQ

### Are these Vault UIs still maintained?

All three projects have seen reduced maintenance activity since 2018-2019. They remain functional for core Vault operations (KV secret management, token generation, policy viewing), but may not support newer Vault features introduced in recent releases. For production use, thoroughly test each UI against your specific Vault version.

### Can I use these UIs with Vault Enterprise?

Yes. All three UIs connect to Vault via its HTTP API, which is the same for both open-source and Enterprise editions. However, Enterprise-specific features like HSM integration, performance replication, and Sentinel policies may not be fully supported in the UI.

### How do I authenticate with these UIs?

Each UI supports different authentication methods. Goldfish and djenriquez vault-ui support token-based auth, AppRole, username/password (LDAP), and Kubernetes auth. The nyxcharon vault-ui primarily supports token and AppRole authentication.

### Is it safe to expose a Vault web UI to the internet?

Generally no. Vault web UIs should be deployed on internal networks only. If remote access is required, use a VPN or SSH tunnel rather than exposing the UI directly. Always place the UI behind a reverse proxy with TLS termination and strong authentication.

### Do these UIs support Vault's PKI engine?

Only the djenriquez vault-ui provides PKI engine management, including certificate issuance, role configuration, and CRL management. Goldfish and nyxcharon vault-ui do not support PKI operations.

### Can I run multiple Vault UIs simultaneously?

Yes. Each UI runs as an independent service on its own port. You can deploy Goldfish on port 8000, djenriquez vault-ui on port 8001, and use each for different purposes (e.g., Goldfish for developers, djenriquez for operators).

## Security Best Practices

1. **Never expose Vault UIs publicly** — always deploy behind a reverse proxy with TLS and restrict access to internal networks or VPN.

2. **Use short-lived tokens** — configure UI sessions to use tokens with short TTLs (1-4 hours) rather than long-lived admin tokens.

3. **Apply least-privilege policies** — create specific Vault policies for UI users that grant only the permissions needed for their role.

4. **Enable audit logging** — configure Vault's file or socket audit device to capture all API requests made through the UI.

5. **Keep Vault updated** — even if the UI project is unmaintained, keep your Vault server updated to the latest stable version for security patches.

6. **Regularly review mounted paths** — audit which secret engines and auth methods are accessible through the UI to prevent unintended data exposure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted HashiCorp Vault Web UIs: Goldfish vs vault-ui vs Dashboards",
  "description": "Compare three open-source HashiCorp Vault web interfaces — Goldfish, vault-ui (djenriquez), and vault-ui (nyxcharon) — for self-hosted secrets management.",
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
