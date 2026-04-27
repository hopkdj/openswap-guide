---
title: "Sliver vs Havoc vs Mythic: Best Self-Hosted C2 Framework 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "security", "red-team"]
draft: false
description: "Compare Sliver, Havoc, and Mythic — the top open-source command and control frameworks for self-hosted red team operations. Full Docker deployment guide, feature comparison, and configuration examples."
---

Command and control (C2) frameworks are the backbone of any professional red team engagement. They provide the infrastructure for operators to manage compromised systems, execute commands, exfiltrate data, and move laterally through target networks. While commercial options like Cobalt Strike dominate the market, open-source alternatives have matured significantly and now offer comparable capabilities with full self-hosted control.

In this guide, we compare three leading open-source C2 frameworks: **Sliver** (by BishopFox), **Havoc** (by HavocFramework), and **Mythic** (by its-a-feature). All three are actively maintained, support cross-platform implants, and can be deployed on your own infrastructure.

## Why Self-Host Your C2 Framework

Running your own C2 infrastructure offers several advantages over commercial SaaS solutions:

- **Full data control**: All operation data, credentials, and captured output stays on your servers
- **No license costs**: All three frameworks are free and open-source (MIT/BSD-3 licensed)
- **Custom callbacks**: Configure your own domains, DNS redirectors, and cloud infrastructure
- **Team collaboration**: Multi-operator support built into each platform
- **Extensibility**: Write custom implants, agents, and tooling for specific engagement needs
- **No vendor lock-in**: You own the infrastructure and can modify it as needed

For authorized penetration testing and adversary emulation exercises, a self-hosted C2 platform gives you the flexibility to simulate real-world attack infrastructure without the constraints of commercial licensing.

## Sliver: The Modern Go-Powered C2 Framework

[Sliver](https://github.com/BishopFox/sliver) is developed by BishopFox and written entirely in Go. It has become the most popular open-source C2 framework with over 11,000 GitHub stars and active development. Sliver supports mutual TLS, WireGuard, HTTP(S), and DNS as callback protocols, with cross-platform implants for Windows, macOS, and Linux.

**Key features:**

- **mTLS callback**: Mutual TLS with automatic certificate generation for encrypted C2 channels
- **WireGuard support**: Built-in WireGuard listener for tunnel-based callbacks
- **Dynamic code generation**: Generates unique implant binaries per-session to evade signature detection
- **Multi-platform implants**: Windows, Linux, and macOS support with shellcode, shared library, and executable output formats
- **Session management**: Full session shell, process migration, and lateral movement tooling
- **Extension system**: Go-based extension architecture for custom commands
- **Multi-operator**: Built-in support for concurrent team operations

**GitHub Stats** (as of April 2026): 11,092 stars · Last updated: 2026-04-22 · Language: Go · License: MIT

### Sliver Docker Deployment

Sliver includes an official `Dockerfile` with multi-stage build support. Here's how to build and run it:

```dockerfile
# Build the production image
docker build --target production -t sliver .

# Run with persistent config volume
docker run -it --rm \
  -v $HOME/.sliver:/home/sliver/.sliver \
  sliver
```

For a production deployment with persistent volumes and port exposure:

```yaml
version: "3.8"

services:
  sliver-server:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: sliver-c2
    ports:
      - "31337:31337"  # mTLS listener
      - "443:443"      # HTTPS callback
      - "53:53/udp"    # DNS callback
      - "51820:51820/udp"  # WireGuard callback
    volumes:
      - sliver-data:/home/sliver/.sliver
    restart: unless-stopped

volumes:
  sliver-data:
    driver: local
```

**Quick install (non-Docker):**

```bash
# Install Sliver on Linux
curl -sSL https://sliver.sh/install | sudo bash

# Start the server
sudo sliver

# Connect from a client machine
sliver -c <config-file>
```

## Havoc: The Flexible Red Team Platform

[Havoc](https://github.com/HavocFramework/Havoc) is a modern C2 framework written in Go with a focus on flexibility and ease of use. It features a clean GUI client, supports sleep obfuscation, indirect syscalls, and includes a modular teamserver architecture. Havoc has over 8,300 stars and supports Windows, Linux, and beacon-based operations.

**Key features:**

- **GUI client**: Native Qt-based GUI for a polished operator experience
- **Sleep obfuscation**: Advanced sleep/execution cycle to evade memory scanning
- **Indirect syscalls**: Evades EDR user-mode API hooking
- **Modular teamserver**: Plugin-based architecture for extending capabilities
- **Built-in listeners**: HTTP, HTTPS, SMB, and TCP redirectors
- **Payload generation**: Shellcode, DLL, EXE, and service payloads with built-in obfuscation
- **Session management**: Real-time session monitoring and command execution

**GitHub Stats** (as of April 2026): 8,311 stars · Last updated: 2025-12-18 · Language: Go · License: GPL-3.0

### Havoc Docker Deployment

Havoc includes a `Teamserver-Dockerfile` in the teamserver directory. The teamserver requires several dependencies including mingw-w64 for cross-compilation of Windows payloads.

```dockerfile
# Havoc Teamserver Dockerfile
ARG GO_VERSION="1.19.1"
FROM golang:${GO_VERSION}

RUN apt update && apt -y install \
    alien debhelper devscripts golang-go \
    nasm mingw-w64 dh-golang dh-make \
    fakeroot pkg-config python3-all-dev \
    python3-pip rpm sudo libcap2-bin upx-ucl \
    && pip install --upgrade jsonschema

RUN git clone https://github.com/HavocFramework/Havoc
# Build from source...
```

**Deployment via Docker Compose:**

```yaml
version: "3.8"

services:
  havoc-teamserver:
    build:
      context: ./havoc/teamserver
      dockerfile: Teamserver-Dockerfile
    container_name: havoc-ts
    ports:
      - "40056:40056"  # Teamserver communication
      - "443:443"      # HTTPS listener
      - "80:80"        # HTTP listener
    volumes:
      - havoc-data:/data
    restart: unless-stopped

volumes:
  havoc-data:
    driver: local
```

**Quick install (recommended for Havoc):**

```bash
# Clone the repository
git clone https://github.com/HavocFramework/Havoc.git
cd Havoc/teamserver

# Run the installer (handles mingw-cross, dependencies)
sudo ./Install.sh

# Build the teamserver
make

# Start the teamserver
sudo ./teamserver server --profile ./profiles/havoc.yaotl -v

# Launch the GUI client
cd ../client
make && ./havoc
```

## Mythic: The Collaborative Multi-Platform C2

[Mythic](https://github.com/its-a-feature/Mythic) is a cross-platform, post-exploit C2 framework built with Go and designed around a Docker-native architecture. With over 4,400 stars, Mythic stands out for its collaborative web UI, agent-based extensibility, and support for over 20 payload types. It uses a service-oriented architecture where each C2 profile, payload type, and translation container runs as a separate Docker service.

**Key features:**

- **Web-based UI**: Full browser-based interface for team collaboration and operation management
- **Agent-based extensibility**: Over 20 payload types (Apfell, Athena, Poseidon, Diana, etc.)
- **Docker-native**: Entire platform runs as orchestrated Docker containers
- **Tasking pipeline**: JSON-based tasking system with configurable callback intervals
- **Reporting**: Built-in operation reporting with exportable findings
- **C2 Profiles**: Customizable C2 communication profiles (HTTP, DNS, SMB, and more)
- **Payload Type separation**: Each implant type runs in its own container for isolation
- **Multi-platform**: Supports Windows, macOS, Linux, and cross-platform agents

**GitHub Stats** (as of April 2026): 4,435 stars · Last updated: 2026-04-25 · Language: JavaScript/Go · License: BSD-3

### Mythic Docker Deployment

Mythic is designed to run entirely via Docker Compose. The `mythic-docker` directory contains the build infrastructure:

```bash
# Clone and install Mythic
git clone https://github.com/its-a-feature/Mythic.git
cd Mythic/mythic-docker

# Build and start all services
sudo make

# Start the platform
sudo ./mythic-cli start

# Add a default agent/payload type
sudo ./mythic-cli payload add
```

**Docker Compose overview** — Mythic orchestrates multiple containers:

```yaml
# Simplified Mythic docker-compose structure
version: "3.8"

services:
  mythic_server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mythic_server
    ports:
      - "7443:7443"  # Web UI and API
      - "8888:8888"  # Agent callback port
    volumes:
      - mythic-data:/Mythic/app/Mythic/installed_c2_profiles
      - mythic-config:/Mythic/app/Mythic/config
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      POSTGRES_USER: mythic_user
      POSTGRES_PASSWORD: mythic_password
      POSTGRES_DB: mythic_db
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  mythic-data:
  mythic-config:
  postgres-data:
```

**Key ports and services:**

| Service | Port | Purpose |
|---------|------|---------|
| Web UI / API | 7443 | Browser interface and REST API |
| Agent callback | 8888 | Payload communication endpoint |
| PostgreSQL | 5432 | Internal database (not exposed) |

## Feature Comparison

| Feature | Sliver | Havoc | Mythic |
|---------|--------|-------|--------|
| **Language** | Go | Go | Go + JavaScript |
| **License** | MIT | GPL-3.0 | BSD-3 |
| **GitHub Stars** | 11,092 | 8,311 | 4,435 |
| **Last Updated** | Apr 2026 | Dec 2025 | Apr 2026 |
| **UI Type** | CLI | Qt GUI | Web Browser |
| **mTLS Support** | Yes | No | No |
| **WireGuard C2** | Yes | No | No |
| **HTTP(S) C2** | Yes | Yes | Yes |
| **DNS C2** | Yes | No | Via profile |
| **SMB C2** | No | Yes | Via profile |
| **Sleep Obfuscation** | No | Yes | Via agent |
| **Indirect Syscalls** | No | Yes | Via agent |
| **Dynamic Payload Gen** | Yes | Partial | Via service |
| **Cross-Platform** | Win/Mac/Linux | Win/Linux | Win/Mac/Linux |
| **Multi-Operator** | Yes | Yes | Yes |
| **Built-in Reporting** | Basic | No | Yes |
| **Docker Native** | Yes (Dockerfile) | Yes (Dockerfile) | Yes (docker-compose) |
| **Extension System** | Go extensions | Plugins | Payload types + C2 profiles |
| **Ease of Setup** | Moderate | Complex | Moderate |

## Choosing the Right Framework

### Choose Sliver if:
- You need the most actively maintained open-source C2
- mTLS or WireGuard callbacks are required for your engagement
- You prefer a CLI-driven workflow
- You want automatic certificate management
- Dynamic code generation for AV evasion is important
- Your team values MIT licensing

### Choose Havoc if:
- You prefer a GUI-based operator experience
- Sleep obfuscation and indirect syscalls are required for EDR evasion
- You need SMB-pivot capabilities
- Your team works primarily in Windows environments
- You want the most modern evasion techniques built-in

### Choose Mythic if:
- Your team needs a browser-based collaborative interface
- You require 20+ payload types for different target environments
- You want Docker-native deployment from the start
- Built-in operation reporting is essential
- You need the most extensible architecture via the payload type system
- BSD-3 licensing is preferred for commercial engagements

## Security Considerations for Self-Hosted C2

When deploying a C2 framework on your own infrastructure, follow these security best practices:

1. **Use redirectors**: Never expose your teamserver directly to target networks. Use CDN, cloud proxies, or reverse proxies (see our [WAF and bot protection guide](../self-hosted-waf-bot-protection-modsecurity-coraza-crowdsec-2026/)) to front your C2 infrastructure.

2. **Isolate the teamserver**: Run the C2 server in a dedicated VM or container. Use network segmentation to limit lateral movement risk.

3. **Restrict access**: Bind listener ports to specific IPs. Use firewall rules to limit operator access to known IPs only.

4. **Rotate certificates**: Regularly regenerate mTLS certificates. Use short-lived certificates where possible.

5. **Log everything**: Enable verbose logging and forward logs to a SIEM system (see our [SIEM deployment guide](../self-hosted-siem-wazuh-security-onion-elastic-guide/)) for audit and compliance.

6. **Secure the web UI**: For Mythic, place the web interface behind authentication and TLS. Never run the UI on an internet-facing port without additional protection.

7. **Back up operation data**: Regularly back up your C2 database and configuration. An engagement database is irreplaceable if the server fails.

## FAQ

### Are these C2 frameworks legal to use?
Yes, all three frameworks (Sliver, Havoc, Mythic) are legal open-source software. They are designed for authorized penetration testing, red team exercises, and adversary emulation. However, using them against systems you don't own or have explicit written authorization to test is illegal in most jurisdictions. Always obtain proper authorization before conducting any security assessment.

### Can I run these C2 frameworks on cloud servers?
Yes, all three can be deployed on cloud providers (AWS, GCP, Azure, DigitalOcean). Sliver and Havoc run well on standard VPS instances. Mythic requires more resources due to its multi-container Docker architecture (at least 4 GB RAM recommended). Use cloud provider redirectors to mask your teamserver's true IP address from target networks.

### Which C2 framework is best for beginners?
Sliver is generally considered the most beginner-friendly due to its straightforward CLI, excellent documentation, and automatic certificate generation. Mythic's web UI is also intuitive, but the Docker-based setup requires more operational knowledge. Havoc has a steeper learning curve due to its complex dependency chain (mingw-w64, cross-compilation tools).

### Do these frameworks support payload customization?
All three support payload customization. Sliver generates unique binaries per-session using dynamic code compilation. Havoc includes built-in obfuscation and sleep profiles. Mythic uses a modular payload type system where each agent type runs as a separate Docker container, allowing deep customization of agent behavior.

### How do I update a self-hosted C2 framework?
For Sliver: rebuild the Docker image with `docker build --target production -t sliver .` and restart the container. For Havoc: pull the latest code with `git pull`, rebuild with `make`, and restart the teamserver. For Mythic: run `git pull` in the Mythic directory and restart services with `sudo ./mythic-cli restart`.

### Can multiple operators use the same C2 server simultaneously?
Yes, all three frameworks support multi-operator collaboration. Sliver uses a client-server model with named operators. Havoc allows multiple GUI clients to connect to the same teamserver. Mythic is explicitly designed as a collaborative platform with role-based access control through its web interface.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Sliver vs Havoc vs Mythic: Best Self-Hosted C2 Framework 2026",
  "description": "Compare Sliver, Havoc, and Mythic — the top open-source command and control frameworks for self-hosted red team operations. Full Docker deployment guide, feature comparison, and configuration examples.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
