---
title: "Self-Hosted Infrastructure Access Management — Teleport vs Boundary vs OpenZiti"
date: 2026-05-04
tags: ["access-management", "zero-trust", "security", "self-hosted", "identity", "infrastructure"]
draft: false
---

Managing access to servers, databases, Kubernetes clusters, and internal applications is one of the hardest challenges in infrastructure operations. Traditional approaches — shared SSH keys, open firewall ports, and VPN-based network access — create security blind spots that attackers exploit. Identity-based access management tools replace these legacy patterns with per-user authentication, short-lived certificates, session recording, and fine-grained authorization.

In this guide, we compare three leading open-source infrastructure access platforms: **Teleport** (by Gravity/Gravitational), **Boundary** (by HashiCorp), and **OpenZiti** (by NetFoundry). Each provides identity-based access to infrastructure, but they differ in architecture, scope, and target use cases.

## Comparison at a Glance

| Feature | Teleport | Boundary | OpenZiti |
|---------|----------|----------|----------|
| **GitHub Stars** | 20,232+ | 4,026+ | 4,126+ |
| **Primary Focus** | Infrastructure access gateway | Identity-based access management | Zero-trust network fabric |
| **Protocol Support** | SSH, Kubernetes, databases, web apps, Windows desktop | TCP, SSH, Kubernetes, database proxies | Any TCP (embedded SDK), SSH, HTTP |
| **Authentication** | SSO (SAML, OIDC, GitHub), MFA, hardware keys | OIDC, LDAP, passwordless | Certificates, JWT, OAuth2 |
| **Session Recording** | Full SSH and Kubernetes session recording | Session recording (TCP streams) | Application-level (via SDK) |
| **Audit Logging** | Comprehensive audit log with playback | Audit log with session details | Network-level and app-level logs |
| **Database Access** | PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, Cassandra | PostgreSQL, MySQL (via plugins) | Any database (via SDK integration) |
| **Kubernetes Access** | Native RBAC integration with kubectl | Via TCP proxy to kube-apiserver | Via SDK or TCP proxy |
| **Desktop Access** | Windows and Linux desktop (RDP/VNC) | No | No |
| **Application Access** | Reverse proxy for internal web apps | Via TCP proxy | Native (embedded SDK) |
| **Network Model** | Proxy-based (connect through gateway) | Proxy-based (connect through worker) | Overlay network (darknet) |
| **Deployment** | Single binary, Docker, Helm | Single binary, Docker, Helm | Controller + Router, Docker, Kubernetes |
| **License** | Apache 2.0 (core), BSL (enterprise features) | BSL (converts to Apache 2.0) | Apache 2.0 |

## Teleport: Unified Infrastructure Access Gateway

[Teleport](https://github.com/gravitational/teleport) is the most widely adopted open-source infrastructure access platform. It provides a unified gateway for SSH, Kubernetes, database, and application access — all authenticated through identity providers and recorded for audit compliance.

### Key Features

- **Unified access proxy** — single gateway for SSH, Kubernetes, databases, web applications, and Windows desktops
- **Short-lived certificates** — automatically issued and revoked, eliminating long-lived key management
- **SSO integration** — supports SAML, OIDC, GitHub, GitLab, and Okta for identity-based authentication
- **Session recording and playback** — full SSH terminal recording and Kubernetes session audit with video-like playback
- **Role-based access control** — fine-grained policies defining who can access what, when, and how
- **Just-in-time access** — temporary elevated privileges with automatic expiration
- **Device trust** — verify the security posture of connecting devices before granting access
- **Access requests** — users can request elevated permissions that require approval from designated reviewers
- **FIPS 140-2 compliance** — available for government and regulated industry deployments

### Docker Compose Deployment

A basic Teleport deployment with a single auth/proxy node:

```yaml
services:
  teleport:
    image: public.ecr.aws/gravitational/teleport-distroless:16
    container_name: teleport
    ports:
      - "3023:3023"   # SSH proxy
      - "3024:3024"   # Kubernetes proxy
      - "3025:3025"   # Auth server (internal)
      - "3080:3080"   # Web UI / Proxy API
      - "443:443"     # HTTPS
    volumes:
      - teleport-config:/etc/teleport
      - teleport-data:/var/lib/teleport
    command: ["teleport", "start", "--config=/etc/teleport/teleport.yaml"]
    restart: unless-stopped

volumes:
  teleport-config:
  teleport-data:
```

Minimal `teleport.yaml` configuration:

```yaml
version: v3
teleport:
  nodename: teleport-server
  data_dir: /var/lib/teleport
  log:
    output: stderr
    severity: INFO
  ca_pin: ""
auth_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3025
  cluster_name: teleport.example.com
  authentication:
    type: local
    second_factor: on
    webauthn:
      rp_id: teleport.example.com
proxy_service:
  enabled: "yes"
  web_listen_addr: 0.0.0.0:3080
  public_addr: teleport.example.com:443
  ssh:
    listen_addr: 0.0.0.0:3023
  kube:
    enabled: yes
    listen_addr: 0.0.0.0:3024
ssh_service:
  enabled: "no"
```

### When to Use Teleport

Choose Teleport when you need a **comprehensive, production-ready access gateway** with the widest protocol support and the most mature feature set. It is ideal for organizations that want to replace SSH keys, VPN access, and database credentials with a single identity-based platform. Its session recording and audit capabilities make it particularly valuable for compliance-driven environments (SOC 2, HIPAA, PCI DSS).

## Boundary: Identity-Based Access Management by HashiCorp

[Boundary](https://github.com/hashicorp/boundary) is HashiCorp's entry into the identity-based access management space. It focuses on providing secure, identity-aware access to any TCP-based service — with first-class support for SSH, databases, and Kubernetes.

### Key Features

- **Identity-based access** — users authenticate via OIDC or LDAP, and access is granted based on identity, not network location
- **Worker-based architecture** — lightweight worker processes handle connections, making it easy to deploy across regions and clouds
- **Credential brokering** — Boundary can inject database credentials at connection time, eliminating shared passwords
- **Target-based authorization** — access is defined per target (host + port), with role-based scoping
- **Session management** — all connections are proxied through Boundary, providing full session visibility
- **Host catalogs** — integrate with AWS EC2, Azure VMs, or static host lists for dynamic target discovery
- **CLI and desktop clients** — `boundary connect` provides seamless access from the terminal, with browser-based desktop access for supported targets
- **HashiCorp ecosystem integration** — works alongside Vault (secrets), Consul (service discovery), and Terraform (provisioning)

### Docker Compose Deployment

A basic Boundary deployment with PostgreSQL backend:

```yaml
services:
  boundary:
    image: hashicorp/boundary:latest
    container_name: boundary
    ports:
      - "9200:9200"   # API / Web UI
      - "9201:9201"   # Worker proxy
      - "9202:9202"   # Ops (health checks)
    cap_add:
      - IPC_LOCK
    command: ["boundary", "server", "-config", "/boundary/config.hcl"]
    volumes:
      - boundary-config:/boundary
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:16
    container_name: boundary_db
    environment:
      - POSTGRES_USER=boundary
      - POSTGRES_PASSWORD=boundary_password
      - POSTGRES_DB=boundary
    volumes:
      - pg_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  boundary-config:
  pg_data:
```

Boundary configuration (`config.hcl`):

```hcl
disable_mlock = true

listener "tcp" {
  address     = "0.0.0.0:9200"
  purpose     = "api"
  tls_disable = true
}

listener "tcp" {
  address     = "0.0.0.0:9201"
  purpose     = "proxy"
  tls_disable = true
}

listener "tcp" {
  address     = "0.0.0.0:9202"
  purpose     = "ops"
  tls_disable = true
}

kms "aead" {
  purpose   = "root"
  aead_type = "aes-gcm"
  key       = "sP1fnF5Xz85RrXyELHFeZg9Ad2qa4HiMltNKnP9Tn8M="
  key_id    = "global_root"
}

kms "aead" {
  purpose   = "worker-auth"
  aead_type = "aes-gcm"
  key       = "sP1fnF5Xz85RrXyELHFeZg9Ad2qa4HiMltNKnP9Tn8M="
  key_id    = "global_worker-auth"
}

kms "aead" {
  purpose   = "recovery"
  aead_type = "aes-gcm"
  key       = "sP1fnF5Xz85RrXyELHFeZg9Ad2qa4HiMltNKnP9Tn8M="
  key_id    = "global_recovery"
}
```

### When to Use Boundary

Choose Boundary when you are already in the **HashiCorp ecosystem** and want access management that integrates with Vault, Consul, and Terraform. It is also a good fit for organizations that need a simpler, more focused tool — Boundary does fewer things than Teleport but does identity-based access for TCP services very well. Its credential brokering feature is particularly useful for database access scenarios.

## OpenZiti: Zero-Trust Network Fabric

[OpenZiti](https://github.com/openziti/ziti) takes a fundamentally different approach. Instead of a gateway or proxy, it creates a zero-trust overlay network (a "darknet") where applications embed the OpenZiti SDK to become zero-trust services. This eliminates the need for VPNs, open firewall ports, and perimeter-based security entirely.

### Key Features

- **Zero-trust overlay network** — applications connect through an encrypted fabric, not through a gateway
- **Application-level identity** — each client and service has its own cryptographic identity, verified before any connection is allowed
- **No open ports required** — services initiate outbound connections to the fabric; no inbound firewall rules needed
- **Embedded SDK** — applications integrate the OpenZiti SDK (Go, C, Java, .NET, Node.js, Python) for native zero-trust connectivity
- **Policy-driven access** — granular policies control which identities can communicate with which services
- **Multi-protocol support** — any TCP-based protocol works through the fabric, with SDK integration for application-level awareness
- **Self-healing network** — automatic reconnection and failover across multiple controller/router endpoints
- **Open-source, fully extensible** — no proprietary features locked behind enterprise editions

### Docker Compose Deployment

A basic OpenZiti deployment with controller and router:

```yaml
services:
  ziti-controller:
    image: openziti/quickstart
    container_name: ziti-controller
    ports:
      - "1280:1280"   # Controller management
      - "8441:8441"   # Controller edge
    environment:
      - ZITI_CTRL_EDGE_ADVERTISED_ADDRESS=ziti.example.com
      - ZITI_CTRL_EDGE_ADVERTISED_PORT=8441
      - ZITI_USER=admin
      - ZITI_PWD=YourSecurePassword
    volumes:
      - ziti-pki:/openziti/pki
      - ziti-controller-data:/openziti/fabric
    command: ["run", "controller"]
    restart: unless-stopped

  ziti-router:
    image: openziti/quickstart
    container_name: ziti-router
    ports:
      - "8442:8442"   # Router edge
      - "10080:10080" # Router management
    environment:
      - ZITI_ROUTER_ADVERTISED_ADDRESS=ziti.example.com
      - ZITI_ROUTER_ADVERTISED_PORT=8442
      - ZITI_ROUTER_LISTENER_BIND_PORT=8442
      - ZITI_CTRL_EDGE_ADVERTISED_ADDRESS=ziti.example.com
      - ZITI_CTRL_EDGE_ADVERTISED_PORT=8441
    depends_on:
      - ziti-controller
    command: ["run", "router"]
    restart: unless-stopped

volumes:
  ziti-pki:
  ziti-controller-data:
```

### When to Use OpenZiti

Choose OpenZiti when you want a **true zero-trust network architecture** rather than a proxy-based access gateway. It is ideal for organizations building cloud-native applications that can embed the SDK, or for scenarios where you want to eliminate VPNs and open firewall ports entirely. OpenZiti's approach means your services are never directly exposed to the internet — only the fabric routers are, and they only forward traffic for authenticated identities.

## Choosing the Right Access Management Platform

| Scenario | Recommended Tool |
|----------|-----------------|
| Replace SSH keys and VPN with unified access gateway | **Teleport** |
| Already use HashiCorp Vault, Consul, Terraform | **Boundary** |
| Need SSH session recording and compliance audit | **Teleport** |
| Want application-level zero-trust with SDK integration | **OpenZiti** |
| Need database credential brokering | **Boundary** |
| Eliminate all inbound firewall ports | **OpenZiti** |
| Desktop access (RDP) through identity gateway | **Teleport** |
| Simple, focused TCP access proxy | **Boundary** |
| Open-source with no enterprise feature lock | **OpenZiti** |

## Why Self-Host Your Access Management?

Managing infrastructure access through self-hosted tools eliminates the dependency on cloud-based access platforms and keeps your authentication data under your control. When you host Teleport, Boundary, or OpenZiti on your own infrastructure, you own the entire access audit trail — no third party can see who accessed what and when.

For regulated industries, self-hosted access management ensures that session recordings, audit logs, and authentication events never leave your infrastructure. This is critical for SOC 2, HIPAA, and PCI DSS compliance, where auditors require direct access to access logs.

For multi-cloud and hybrid environments, a self-hosted access gateway provides a single identity-based entry point to all your infrastructure — regardless of whether it runs on AWS, GCP, Azure, or bare metal. This eliminates the need for separate access controls per cloud provider.

For database access specifically, identity-based tools eliminate shared credentials by issuing per-user, time-limited certificates. When an employee leaves, you revoke their identity — no need to rotate database passwords across dozens of applications.

For related reading, see our [SSH certificate management guide](../2026-04-21-fleet-osquery-vs-wazuh-vs-teleport-self-hosted-endpoint-management-guide-2026/) which covers Teleport's endpoint management capabilities, and our [mutual TLS deployment guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-gateway-guide-2026/) for service-to-service authentication patterns.

## FAQ

### What is the difference between Teleport and a traditional VPN?

A VPN grants network-level access — once connected, you can reach any server on the private network. Teleport grants application-level access — you authenticate to specific resources (a particular server, database, or Kubernetes cluster) and your access is logged and auditable. Teleport also eliminates the need for shared SSH keys by issuing short-lived certificates tied to your identity.

### Can Boundary replace my VPN?

Boundary does not provide network-level access like a VPN. Instead, it proxies individual connections to specific targets (hosts, databases, services). If you need to access an entire private network, a VPN or zero-trust network fabric like OpenZiti is more appropriate. If you need controlled, auditable access to specific services, Boundary is the better choice.

### Does OpenZiti require application code changes?

For full zero-trust benefits, yes — applications embed the OpenZiti SDK to become aware of their zero-trust identity. However, OpenZiti also offers a "tunneler" mode that can proxy existing applications without code changes, similar to how Teleport or Boundary work as proxies. The SDK integration is optional but recommended for the best security posture.

### Which tool has the most permissive open-source license?

OpenZiti is fully Apache 2.0 licensed with no enterprise feature lock. Teleport's core is Apache 2.0, but advanced features like device trust and access requests use a Business Source License. Boundary uses a BSL that converts to Apache 2.0 after a set period. If you need a fully open-source solution with no proprietary features, OpenZiti is the clear choice.

### How do these tools handle high availability?

Teleport supports multi-node clusters with shared backend storage (DynamoDB, etcd, or Firestore). Boundary supports multiple controllers and workers behind a load balancer, with PostgreSQL as the shared backend. OpenZiti supports multiple controllers and routers with automatic failover. All three can be deployed in highly available configurations for production use.

### Can I use these tools with existing Active Directory or LDAP?

Teleport supports LDAP/Active Directory authentication directly. Boundary supports LDAP authentication through its auth methods. OpenZiti supports OIDC, which can be configured to authenticate against Active Directory Federation Services (ADFS) or other identity providers. All three integrate with enterprise identity systems.

### Which tool is easiest to deploy for a small team?

Teleport offers the most straightforward out-of-the-box experience with its unified binary and single configuration file. Boundary requires initial database setup and a multi-step initialization process. OpenZiti has the steepest learning curve due to its controller/router architecture and PKI requirements. For small teams getting started quickly, Teleport is the most accessible.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Infrastructure Access Management — Teleport vs Boundary vs OpenZiti",
  "description": "Compare three open-source infrastructure access management platforms: Teleport unified access gateway, HashiCorp Boundary identity-based access, and OpenZiti zero-trust network fabric.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
