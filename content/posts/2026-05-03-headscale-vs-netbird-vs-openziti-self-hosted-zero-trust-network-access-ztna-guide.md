---
title: "Headscale vs NetBird vs OpenZiti: Self-Hosted Zero Trust Network Access (ZTNA) Guide 2026"
date: 2026-05-03
tags: ["zero-trust", "ztna", "networking", "vpn", "headscale", "netbird", "openziti", "self-hosted", "docker"]
draft: false
---

Zero Trust Network Access (ZTNA) has replaced the traditional perimeter-based security model. Instead of trusting any device inside the corporate network, ZTNA verifies every connection request — regardless of origin — before granting access. For organizations that want full control over their network infrastructure, self-hosted ZTNA solutions eliminate reliance on cloud vendors like Tailscale, Zscaler, or Cloudflare Access.

This guide compares three leading open-source ZTNA platforms: **Headscale**, **NetBird**, and **OpenZiti**. All three run entirely on your own infrastructure, support Docker deployment, and provide secure, encrypted connectivity between devices, services, and users.

## What Is Zero Trust Network Access (ZTNA)?

Zero Trust is a security architecture built on the principle: "never trust, always verify." Unlike traditional VPNs that grant broad network access once authenticated, ZTNA solutions:

- **Authenticate every connection** — identity-based access, not IP-based
- **Enforce least-privilege policies** — users and devices only access what they need
- **Encrypt all traffic end-to-end** — peer-to-peer or relayed through your own servers
- **Continuously verify posture** — device health and compliance checks before and during sessions
- **Support micro-segmentation** — isolate workloads and restrict lateral movement

For self-hosted deployments, ZTNA eliminates the need for expensive commercial solutions while keeping all authentication, authorization, and routing data under your control.

## Headscale: Open-Source Tailscale Control Server

**Headscale** is a self-hosted implementation of the Tailscale control server protocol. It enables you to run your own WireGuard mesh network with centralized management, NAT traversal, and access control lists (ACLs) — without relying on Tailscale's cloud infrastructure.

### Key Features

- **WireGuard mesh networking** — every node connects directly when possible, falling back to DERP relays
- **Tailscale client compatibility** — use the official `tailscale` CLI as the agent on all devices
- **ACL policy engine** — JSON-based access control for granular network segmentation
- **Multi-user support** — isolate namespaces with user-based network partitioning
- **DNS magic** — automatic DNS resolution for all nodes via MagicDNS
- **DERP relay servers** — deploy your own relays for NAT traversal when direct connections fail

### Docker Compose Setup

```yaml
version: "3.8"
services:
  headscale:
    image: headscale/headscale:latest
    container_name: headscale
    restart: unless-stopped
    volumes:
      - ./config:/etc/headscale
      - ./data:/var/lib/headscale
    ports:
      - "8080:8080"
      - "9090:9090"
    command: serve

  headscale-ui:
    image: ghcr.io/gurucomputing/headscale-webui:latest
    container_name: headscale-ui
    restart: unless-stopped
    environment:
      - TZ=UTC
      - HEADSCALE_URL=http://headscale:8080
    ports:
      - "3000:80"
    depends_on:
      - headscale
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Maturity | Production-ready; widely deployed |
| Client ecosystem | Full Tailscale client compatibility (Linux, macOS, Windows, iOS, Android) |
| Scalability | Handles thousands of nodes; DERP relays scale horizontally |
| Ease of use | Simple config; familiar `tailscale` CLI for agents |
| Advanced features | No built-in SSO/OIDC; no device posture checks |
| Governance | Community-driven; not backed by a commercial entity |

## NetBird: WireGuard-Based Network Management Platform

**NetBird** is an open-source peer-to-peer network management platform built on WireGuard. It provides a comprehensive ZTNA solution with a management UI, API, and agents for all major operating systems. NetBird goes beyond simple tunneling with built-in routing, access controls, and network policies.

### Key Features

- **WireGuard mesh with management plane** — centralized control with distributed data plane
- **Peer-to-peer connectivity** — direct connections via NAT traversal (ICE/STUN/TURN)
- **Access control groups** — rule-based network policies with source/destination groups
- **Built-in routing** — advertise and access subnets behind each peer
- **Management dashboard** — web UI for peer management, policy configuration, and monitoring
- **Single Sign-On (SSO)** — OIDC integration with Auth0, Okta, Keycloak, and more
- **Posture checks** — verify device compliance before granting network access

### Docker Compose Setup

```yaml
version: "3.8"
services:
  netbird-mgmt:
    image: netbirdio/management:latest
    container_name: netbird-mgmt
    restart: unless-stopped
    environment:
      - NB_MGMT_CONFIG=/etc/netbird/management.json
    volumes:
      - ./management.json:/etc/netbird/management.json
      - ./data:/var/lib/netbird
    ports:
      - "80:80"
      - "443:443"

  netbird-signal:
    image: netbirdio/signal:latest
    container_name: netbird-signal
    restart: unless-stopped
    ports:
      - "10000:10000"

  netbird-turn:
    image: coturn/coturn:latest
    container_name: netbird-turn
    restart: unless-stopped
    command: >
      -n --log-file=stdout
      --listening-port=3478
      --external-ip=${PUBLIC_IP}
      --min-port=49152
      --max-port=65535
    ports:
      - "3478:3478"
      - "3478:3478/udp"
      - "49152-65535:49152-65535/udp"
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Maturity | Active development; production-ready |
| Client ecosystem | Native clients for all major platforms |
| Scalability | Designed for enterprise deployments |
| Ease of use | Full web UI; automated client onboarding |
| Advanced features | SSO/OIDC, posture checks, routing, DNS |
| Governance | Backed by NetBird Inc. (commercial entity) |

## OpenZiti: Application-Embedded Zero Trust

**OpenZiti** takes a fundamentally different approach from Headscale and NetBird. Instead of creating a network overlay, OpenZiti embeds zero trust directly into applications. It uses a "dark internet" model where services are not addressable on the network at all — only through the OpenZiti fabric.

### Key Features

- **Application-embedded ZTNA** — services are invisible on the network; access is mediated by the fabric
- **Identity-based addressing** — no IP addresses for services; everything identified by cryptographic identity
- **End-to-end encryption** — mTLS for all connections, managed by the fabric
- **Policy-driven access** — fine-grained authorization at the service level
- **Multi-cloud and hybrid** — deploy across any infrastructure without network changes
- **Programmable SDKs** — embed zero trust directly into your applications (Go, C, Java, Python)
- **Browser-based access** — ZITI Desktop Edge for Chrome enables browser-to-service connectivity

### Docker Compose Setup

```yaml
version: "3.8"
services:
  ziti-controller:
    image: openziti/quickstart:latest
    container_name: ziti-controller
    restart: unless-stopped
    environment:
      - ZITI_CTRL_EDGE_ADVERTISED_ADDRESS=${PUBLIC_IP}
      - ZITI_CTRL_ADVERTISED_PORT=6262
      - ZITI_EDGE_ROUTER_ENROLLMENT_TOKEN=${ENROLLMENT_TOKEN}
    volumes:
      - ./pki:/ziti/pki
      - ./data:/ziti/data
    ports:
      - "6262:6262"
      - "8441:8441"
      - "1280:1280"

  ziti-edge-router:
    image: openziti/quickstart:latest
    container_name: ziti-edge-router
    restart: unless-stopped
    environment:
      - ZITI_ROUTER_NAME=edge-router-01
      - ZITI_CTRL_EDGE_ADVERTISED_ADDRESS=${PUBLIC_IP}
    depends_on:
      - ziti-controller
    ports:
      - "3022:3022"
      - "3023:3023"
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Maturity | Enterprise-grade; LF Networking project |
| Client ecosystem | SDKs for developers; desktop edge for end users |
| Scalability | Designed for global, multi-cloud deployments |
| Ease of use | Steeper learning curve; requires SDK integration for full benefits |
| Advanced features | Identity-based addressing, programmable policies, multi-tenant |
| Governance | Linux Foundation project; open governance model |

## Comparison: Headscale vs NetBird vs OpenZiti

| Feature | Headscale | NetBird | OpenZiti |
|---------|-----------|---------|----------|
| **Protocol** | WireGuard (Tailscale) | WireGuard (custom) | Custom fabric (mTLS) |
| **Network model** | Overlay L3 network | Overlay L3 network | Application-embedded |
| **Service visibility** | IP-addressable | IP-addressable | Invisible on network |
| **Authentication** | Pre-shared keys | OIDC/SSO | Cryptographic identity |
| **Access control** | JSON ACLs | Group-based policies | Fine-grained service policies |
| **Web UI** | Community (headscale-webui) | Built-in | Built-in (ZAC) |
| **SSO/OIDC** | No | Yes | Yes |
| **Device posture** | No | Yes | Yes |
| **Client SDK** | No (uses Tailscale CLI) | No | Yes (Go, C, Java, Python) |
| **DNS resolution** | MagicDNS | Built-in DNS | Service names (no DNS) |
| **Subnet routing** | Yes | Yes | Via services |
| **Mobile clients** | Yes (Tailscale app) | Yes (native) | Yes (mobile SDK) |
| **Deployment** | Docker Compose | Docker Compose | Docker Compose / Helm |
| **License** | MIT | Apache 2.0 | Apache 2.0 |
| **GitHub stars** | ~38,000 | ~25,000 | ~4,100 |

## When to Choose Each Platform

### Choose Headscale if:

- You already use Tailscale and want to self-host without changing client software
- You need a simple, lightweight WireGuard mesh with centralized management
- Your team is comfortable with CLI-based administration
- You need broad client compatibility across all platforms
- You want to run your own DERP relays for NAT traversal

### Choose NetBird if:

- You need a complete ZTNA platform with a web management UI
- SSO/OIDC integration is required for enterprise identity management
- Device posture verification is a security requirement
- You want routing and DNS built into the platform
- You prefer a single-vendor solution with commercial support available

### Choose OpenZiti if:

- You want services to be completely invisible on the network
- You need application-embedded zero trust (SDK integration)
- You are building multi-cloud or hybrid cloud architectures
- You want identity-based addressing instead of IP-based routing
- You need fine-grained, service-level authorization policies

## Why Self-Host Your ZTNA Infrastructure?

Running your own ZTNA platform eliminates several risks associated with commercial providers:

**Data sovereignty**: All authentication events, network topology data, and access logs remain on your infrastructure. There is no telemetry sent to third-party servers, and no dependency on a vendor's data retention policies.

**Cost control**: Commercial ZTNA solutions charge per user or per device. Self-hosted solutions have no per-seat licensing — you only pay for the infrastructure to run them.

**No vendor lock-in**: Open-source ZTNA platforms use standard protocols (WireGuard, mTLS, OIDC). You can migrate between solutions or integrate with existing identity providers without proprietary dependencies.

**Customization**: Self-hosted deployments allow you to modify access policies, integrate with internal systems, and deploy on your own hardware or cloud provider of choice.

For network security best practices, see our [firewall and router comparison](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide/) and [SSH certificate management guide](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide/). If you need intrusion prevention alongside your ZTNA, our [fail2ban vs SSHGuard comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/) covers host-level protection.

## FAQ

### What is the difference between ZTNA and a traditional VPN?

A traditional VPN creates an encrypted tunnel and grants broad network access once connected. ZTNA verifies identity and device posture for every connection, enforces least-privilege access, and can segment access at the application level rather than the network level.

### Is Headscale production-ready?

Yes. Headscale has been used in production environments for several years and is compatible with the official Tailscale client. It supports thousands of nodes and has active community development.

### Can I use the Tailscale client with Headscale?

Yes. The official `tailscale` CLI on all platforms (Linux, macOS, Windows, iOS, Android) can connect to a Headscale server by pointing it to your custom control URL with `tailscale login --login-server`.

### Do these solutions replace my firewall?

No. ZTNA solutions handle identity-based access and encrypted connectivity. They complement — not replace — network firewalls, which handle port filtering, NAT, and perimeter defense.

### How does NAT traversal work in these platforms?

Headscale uses DERP (Distributed Encrypted Relay Protocol) relays. NetBird uses ICE/STUN/TURN for peer discovery and fallback relay. OpenZiti routes through its fabric edge routers. All three fall back to relayed connections when direct peer-to-peer connections cannot be established.

### Can these platforms handle remote workers?

Yes. All three support mobile and remote device connectivity. Headscale and NetBird provide mobile apps, while OpenZiti offers mobile SDKs for application integration.

### What happens if the control server goes down?

In Headscale and NetBird, existing peer connections continue working — only new connections and policy updates require the control server. In OpenZiti, the controller manages policy but edge routers can continue forwarding established sessions.

### Is OpenZiti harder to deploy than Headscale or NetBird?

Yes. OpenZiti's application-embedded architecture requires more initial setup and understanding of its identity model. However, the quickstart Docker Compose configuration provides a working deployment in under 5 minutes.

### Which solution supports the most platforms?

Headscale wins on client compatibility because it uses the official Tailscale client, which is available for Linux, macOS, Windows, iOS, Android, and BSD systems.

### Do these solutions support multi-tenant deployments?

Headscale supports multi-user namespaces. NetBird supports multiple accounts. OpenZiti has native multi-tenant support with project-level isolation and separate authentication domains.

## Self-Hosted ZTNA: Final Recommendation

For most teams replacing Tailscale, **Headscale** is the simplest path — use the same clients, same workflow, but with your own control server. For organizations that need a complete ZTNA platform with SSO, posture checks, and a management UI out of the box, **NetBird** provides the most comprehensive feature set. For developers and architects building zero trust directly into applications, **OpenZiti** offers the most powerful and flexible model.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Headscale vs NetBird vs OpenZiti: Self-Hosted Zero Trust Network Access (ZTNA) Guide 2026",
  "description": "Compare three leading open-source ZTNA platforms for self-hosted zero trust network access. Covers Headscale, NetBird, and OpenZiti with Docker Compose configs, feature comparisons, and deployment guidance.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
