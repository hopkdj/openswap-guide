---
title: "Self-Hosted SSH Bastion & Key Management: Bastillion vs OVH The Bastion vs sshportal"
date: "2026-06-04"
tags: ["ssh", "security", "bastion", "devops", "infrastructure", "self-hosted"]
draft: false
---

## Introduction

SSH is the universal remote access protocol for Linux infrastructure, but managing SSH keys, auditing sessions, and controlling access across dozens or hundreds of servers quickly becomes unmanageable without centralized tooling. SSH bastion hosts and key management platforms solve this by providing a single entry point with authentication, authorization, and audit logging.

This guide compares three open-source SSH bastion and key management platforms — **Bastillion**, **OVH The Bastion**, and **sshportal** — that bring enterprise-grade access control to self-hosted environments without the complexity or cost of commercial solutions.

## Comparison Table

| Feature | Bastillion | OVH The Bastion | sshportal |
|---------|------------|-----------------|-----------|
| **Stars (GitHub)** | 3,470+ | 2,140+ | 1,930+ |
| **Language** | Java | Perl | Go |
| **Web UI** | Yes (full management) | No (CLI-based) | No (CLI-based) |
| **Key Management** | Centralized, uploaded via UI | egress key injection | SSH key forwarding |
| **Session Recording** | Yes (terminal playback) | Yes (ttyrec-based) | No |
| **Audit Logging** | Comprehensive | Comprehensive | Basic command logging |
| **Access Control** | Role-based, per-system | Group-based ACLs | Group-based |
| **Authentication** | Local, LDAP, SSO | Local, LDAP, PAM | Local, database |
| **Install Method** | WAR file, Docker | Package, source | Go binary, Docker |
| **License** | AGPL-3.0 | BSD-3-Clause | MIT |
| **Docker Support** | Official image | Community images | Official image |

## Bastillion: The Web-Based Powerhouse

Bastillion is a Java-based web application that provides a complete SSH bastion solution with a modern browser-based terminal, centralized key management, and session recording with playback. It is designed for teams that need a visual interface for managing access to hundreds of servers.

### Installation with Docker

```yaml
version: "3.8"
services:
  bastillion:
    image: bastillion/bastillion:latest
    container_name: bastillion
    ports:
      - "8443:8443"
    volumes:
      - ./bastillion-data:/opt/bastillion/jetty/bastillion/WEB-INF/classes/bastillion
      - ./bastillion-keys:/opt/bastillion/jetty/bastillion/WEB-INF/classes/keydb
    environment:
      - BASTILLION_SSH_PORT=22
      - BASTILLION_DB_PASSWORD=secure_db_password
    restart: unless-stopped
```

### Key Features

Bastillion's web terminal provides a browser-based SSH experience that requires no client software beyond a modern browser. Administrators upload SSH keys through the web interface, assign them to users and systems, and enforce access policies. Session recording captures all terminal activity for compliance and troubleshooting.

The role-based access control model allows fine-grained permissions: a user can be granted access to specific systems with read-only or full-control privileges. Audit logs track every connection, command execution, and file transfer.

### Configuration

Bastillion stores its configuration in `bastillion.properties`:

```properties
# Database configuration
dbPath=/opt/bastillion/jetty/bastillion/WEB-INF/classes/bastillion/db
dbPassword=your_db_password

# SSH settings
sshPort=22
agentForwarding=true
oneTimePassword=optional

# Session recording
enableRecording=true
recordingPath=/opt/bastillion/jetty/bastillion/WEB-INF/classes/bastillion/recordings

# LDAP integration (optional)
ldapUrl=ldap://ldap.example.com:389
ldapBaseDN=dc=example,dc=com
```

## OVH The Bastion: Battle-Tested at Scale

Developed and used by OVHcloud to manage access across their global infrastructure of hundreds of thousands of servers, The Bastion is a Perl-based SSH bastion that prioritizes security, auditability, and scalability. It operates entirely through standard SSH — users SSH into the bastion and are presented with a restricted shell that enforces access policies.

### Installation

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install the-bastion

# From source
git clone https://github.com/ovh/the-bastion.git
cd the-bastion
sudo ./install.sh
```

### Key Features

The Bastion operates differently from web-based tools: users connect via standard SSH to the bastion host, which authenticates them and presents a restricted shell. From there, users can connect to target servers they are authorized for, but they never directly handle SSH keys — the bastion injects temporary keys for each session.

This architecture provides several security advantages. SSH private keys never leave the bastion. Sessions are recorded using ttyrec format and can be replayed later. Every connection is logged with timestamps, source IPs, and target systems. The group-based access control integrates with LDAP and Active Directory.

### Configuration

```bash
# /etc/bastion/bastion.conf
{
    "bastionName": "MyCorp Bastion",
    "ingressGroups": ["ssh-users"],
    "egressKeysDirectory": "/home/bastion/keys",
    "ttyrecDirectory": "/home/bastion/ttyrec",
    "auditLogFile": "/var/log/bastion/audit.log",
    "maxSessionsPerUser": 5,
    "idleTimeout": 3600
}
```

OVH The Bastion is particularly well-suited for organizations with existing SSH workflows. Because users interact through standard SSH, it integrates seamlessly with tools like Ansible, SCP, and SSH tunnels — there is no web interface to learn or API to integrate.

## sshportal: Lightweight and Modern

sshportal is a Go-based SSH bastion that focuses on simplicity and ease of deployment. A single binary provides SSH jump host functionality with group-based access control and basic auditing. It is ideal for small teams or as a complement to existing infrastructure.

### Installation with Docker

```yaml
version: "3.8"
services:
  sshportal:
    image: moul/sshportal:latest
    container_name: sshportal
    ports:
      - "2222:2222"
    volumes:
      - ./sshportal-data:/var/lib/sshportal
    environment:
      - SSHPORTAL_DB_PATH=/var/lib/sshportal/sshportal.db
      - SSHPORTAL_LISTEN_ADDR=:2222
      - SSHPORTAL_HOST_KEY=/var/lib/sshportal/host_key
    restart: unless-stopped
```

### Key Features

sshportal is intentionally minimal. It provides SSH jump host functionality through a single binary with a SQLite database for configuration. Users connect to sshportal, which authenticates them and proxies the connection to the target server. Access is controlled through groups, and basic command logging is available.

### Configuration

sshportal is configured primarily through its CLI interface after initial setup:

```bash
# Create admin user
sshportal admin create admin --password=secure_password

# Add a server
sshportal server add web-server --host=10.0.1.5 --port=22 --key=/path/to/key

# Create a group and assign users/servers
sshportal group create developers
sshportal group add-user developers alice bob
sshportal group add-server developers web-server db-server

# Connect through sshportal
ssh alice@sshportal.example.com -p 2222
```

## Why Self-Host Your SSH Bastion?

Centralizing SSH access through a bastion host eliminates the nightmare of managing SSH keys across dozens of individual servers. When an employee leaves or a key is compromised, you revoke access in one place rather than hunting through every server's `authorized_keys` file.

A self-hosted bastion keeps your access credentials within your infrastructure. Unlike commercial privileged access management (PAM) solutions that route your SSH traffic through vendor cloud services, a self-hosted bastion ensures that your most sensitive credentials never leave your network.

For organizations already using [infrastructure access management platforms](../2026-05-04-self-hosted-infrastructure-access-management-teleport-boundary-openziti-guide/), a dedicated SSH bastion provides defense-in-depth. Combined with [SSH certificate-based authentication](../2026-05-09-self-hosted-ssh-certificate-management-step-ca-vault-teleport/), you eliminate static SSH keys entirely and move to short-lived certificates. For real-time SSH monitoring, our [web SSH access guide](../2026-04-29-shellhub-vs-sshwifty-vs-wetty-self-hosted-web-ssh-access-guide-2026/) covers additional tools.


## Security Hardening Tips for SSH Bastion Hosts

Deploying an SSH bastion moves your security perimeter to a single point of entry — which means hardening that entry point is critical. Start by running the bastion on a minimal, dedicated host or container with no other services. Disable password authentication entirely and require key-based or certificate-based authentication. Set a low `ClientAliveInterval` (300 seconds) to automatically disconnect idle sessions, preventing abandoned connections from becoming attack vectors.

Use a separate network segment or VLAN for the bastion host so that even if the bastion is compromised, lateral movement to production systems is limited. Apply strict firewall rules: the bastion should accept SSH from trusted IP ranges only and be allowed to initiate connections to target servers on port 22. All other traffic should be denied by default.

Enable two-factor authentication at the bastion level, not just on individual servers. Both Bastillion and OVH The Bastion support TOTP-based 2FA. For sshportal, you can layer system-level PAM 2FA modules. Monitor bastion access logs for unusual patterns — repeated failed authentication attempts, connections from unexpected geographic locations, or sessions at unusual hours. Forward bastion audit logs to a centralized log management system for long-term retention and analysis.

Regular key rotation is essential. Even with a bastion, SSH keys should be rotated at least quarterly. Bastillion automates this through its key management interface. OVH The Bastion's egress key approach means target server keys are managed centrally and can be rotated without touching individual servers.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SSH Bastion and Key Management: Bastillion vs OVH The Bastion vs sshportal",
  "description": "Compare Bastillion, OVH The Bastion, and sshportal for self-hosted SSH bastion hosts. Covers key management, session recording, access control, and audit logging.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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


## FAQ

### Do I still need individual SSH keys on target servers with a bastion?

With Bastillion, keys are managed centrally and injected per-session — target servers do not need individual user keys. With OVH The Bastion, temporary egress keys are generated per session. With sshportal, the bastion proxies the connection using its own key. In all three cases, you can remove individual user keys from target servers.

### How does session recording work?

Bastillion records terminal sessions as replayable web-based videos. OVH The Bastion uses ttyrec format (standard Unix terminal recording). sshportal logs individual commands but does not provide full session replay. For compliance-heavy environments, Bastillion and OVH The Bastion offer more thorough recording.

### Can these tools integrate with my existing SSO or LDAP?

Yes. Bastillion supports LDAP and SAML-based SSO. OVH The Bastion supports LDAP, Active Directory, and PAM-based authentication. sshportal supports local database authentication only, though you can use PAM at the system level as a workaround.

### What about file transfers (SCP/SFTP)?

OVH The Bastion supports SCP and SFTP through the same bastion connection. Bastillion provides file upload/download through its web interface. sshportal supports SSH port forwarding which can be used for SCP.

### How do these compare to Teleport or Boundary?

Teleport and Boundary are more comprehensive identity-aware access platforms that go beyond SSH to include database access, Kubernetes access, and application access. They also involve more complex setup and resource requirements. Bastillion and OVH The Bastion are SSH-specialized and simpler to deploy. For a comparison of broader access management platforms, see our [infrastructure access guide](../2026-05-04-self-hosted-infrastructure-access-management-teleport-boundary-openziti-guide/).

---
---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
