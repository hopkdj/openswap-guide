---
title: "Self-Hosted Port Knocking & Single Packet Authorization: fwknop vs knockd vs SPA Guide 2026"
date: 2026-05-10
tags: ["comparison", "guide", "self-hosted", "security", "port-knocking", "firewall", "fwknop", "knockd", "spa"]
draft: false
description: "Compare fwknop, knockd, and Single Packet Authorization (SPA) for self-hosted network security. Complete setup guide with iptables configs, Docker deployment, and SPA implementation."
---

Port knocking and Single Packet Authorization (SPA) are network security techniques that hide services behind a firewall until a specific sequence of connection attempts or a cryptographic packet reveals them. While cloud providers offer managed security groups, self-hosted infrastructure requires you to implement these access control mechanisms yourself.

In this guide, we compare three approaches to self-hosted port knocking: **knockd** (the classic port knocking daemon), **fwknop** (Single Packet Authorization with strong cryptography), and the modern **SPA** pattern implemented through tools like **Packet Knock** and custom implementations.

## What Is Port Knocking?

Port knocking works by keeping all ports closed on your firewall until a client sends a predefined sequence of connection attempts to specific ports. A daemon monitors the firewall logs, detects the correct sequence, and dynamically opens the target port for the client's IP address.

**knockd** is the most widely used port knocking implementation. It monitors syslog or pcap for connection attempts and executes firewall rules when it detects a valid knock sequence.

**fwknop** (FireWall KNock OPerator) goes further with Single Packet Authorization. Instead of a sequence of port probes, the client sends a single encrypted and authenticated packet containing the authorization request. The server decrypts, verifies, and opens the port — all in one step, with no open probe ports.

## Why Use Port Knocking or SPA?

The primary use case is reducing your attack surface. If you run SSH on port 22, it will be scanned and attacked constantly. Port knocking hides the service entirely — an attacker scanning your server sees all ports as closed or filtered.

Key advantages:
- **Reduced attack surface**: Services are invisible until authorized
- **No open ports**: Unlike services that listen on alternate ports, knock sequences don't require any port to stay open
- **SPA eliminates timing attacks**: Traditional port knocking is vulnerable to packet sniffing and replay attacks. SPA's cryptographic authentication prevents both
- **Complementary to other security**: Works alongside fail2ban, CrowdSec, and firewall rules

## knockd: Classic Port Knocking

knockd is the original port knocking daemon, available in most Linux distributions. It watches network traffic for a specific sequence of TCP or UDP connection attempts and executes configured commands when the sequence is detected.

### Installation and Configuration

Install knockd on Debian/Ubuntu:

```bash
apt-get update && apt-get install -y knockd
```

Configure the knock sequence in `/etc/knockd.conf`:

```ini
[options]
    UseSyslog
    Interface = eth0

[openSSH]
    sequence      = 7000,8000,9000
    seq_timeout   = 10
    command       = /sbin/iptables -A INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
    tcpflags      = syn
    cmd_timeout   = 30
    stop_command  = /sbin/iptables -D INPUT -s %IP% -p tcp --dport 22 -j ACCEPT

[openHTTP]
    sequence      = 5000,6000,7000
    seq_timeout   = 15
    command       = /sbin/iptables -A INPUT -s %IP% -p tcp --dport 443 -j ACCEPT
    tcpflags      = syn
    cmd_timeout   = 60
    stop_command  = /sbin/iptables -D INPUT -s %IP% -p tcp --dport 443 -j ACCEPT
```

Start the daemon:

```bash
systemctl enable knockd
systemctl start knockd
```

### Docker Deployment

Run knockd in a privileged container with host network access:

```yaml
version: "3.8"
services:
  knockd:
    image: linuxserver/knockd:latest
    container_name: knockd
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./knockd.conf:/config/knockd.conf:ro
    restart: unless-stopped
```

### Client-Side Usage

Send the knock sequence from a client:

```bash
# Install knock client
apt-get install -y knockd

# Send knock sequence
knock -v your-server.com 7000 8000 9000

# SSH will now be available for 30 seconds
ssh user@your-server.com
```

## fwknop: Single Packet Authorization

fwknop replaces the multi-port knock sequence with a single cryptographically authenticated packet. This eliminates several weaknesses of traditional port knocking:

- **No replay attacks**: Each packet includes a timestamp and nonce
- **No packet sniffing**: The payload is encrypted with symmetric or asymmetric keys
- **No port scanning exposure**: Only one port needs to be monitored (UDP 62201 by default)

### Server Setup

Install fwknop server:

```bash
apt-get update && apt-get install -y fwknop-server
```

Configure `/etc/fwknop/access.conf`:

```ini
SOURCE: ANY
KEY: your-encryption-key-here
HMAC_KEY: your-hmac-key-here
OPEN_PORTS: tcp/22
FW_ACCESS_TIMEOUT: 30
REQUIRE_SOURCE_ADDRESS: Y
```

The `REQUIRE_SOURCE_ADDRESS` option ensures the SPA packet's source IP matches the connection attempt, preventing IP spoofing attacks.

### fwknop Docker Compose

```yaml
version: "3.8"
services:
  fwknop-server:
    image: mrlesmithjr/fwknop-server:latest
    container_name: fwknop-server
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - TZ=UTC
    volumes:
      - ./access.conf:/etc/fwknop/access.conf:ro
      - ./fwknopd.conf:/etc/fwknop/fwknopd.conf:ro
    restart: unless-stopped
```

### Client Configuration

Generate keys and send an SPA packet:

```bash
# Generate SPA keys
fwknop -G

# Send SPA request to open SSH
fwknop -n my-server -a your-client-ip -D your-server.com -R tcp/22

# The -a flag specifies your source IP
# The -R flag specifies the port to open
```

## SPA vs Port Knocking: Comparison

| Feature | knockd | fwknop (SPA) | Custom SPA |
|---------|--------|-------------|------------|
| Auth method | Port sequence | Encrypted packet | Encrypted packet |
| Replay protection | No | Yes (timestamp + nonce) | Yes |
| Packet sniffing risk | Yes (sequence visible) | No (encrypted) | No (encrypted) |
| Ports exposed | Multiple probe ports | Single UDP port | Single UDP port |
| IP spoofing protection | No | Yes (source verification) | Varies |
| Docker support | Yes (linuxserver) | Yes (community) | Limited |
| Configuration complexity | Low | Medium | High |
| Performance impact | Minimal | Minimal | Minimal |
| Active development | Maintenance | Active | Project-dependent |

## Security Considerations

Port knocking is not a standalone security measure. It should be combined with:

1. **Strong firewall defaults**: Default-deny INPUT policy with explicit allows
2. **SSH key authentication**: Never rely on passwords for SSH
3. **Intrusion prevention**: Pair with fail2ban or CrowdSec for brute force protection
4. **Network segmentation**: Place critical services in isolated subnets

### iptables Baseline Configuration

Before enabling port knocking, set a restrictive firewall baseline:

```bash
# Set default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow ICMP ping
iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT

# Port knocking daemon will dynamically add rules above
```

Save rules persistently:

```bash
apt-get install -y iptables-persistent
netfilter-persistent save
```

## Why Self-Host Port Knocking?

Managing your own port knocking infrastructure gives you complete control over access policies without depending on cloud provider APIs or managed firewall services. For bare-metal servers, colocation hosts, or home lab environments, port knocking adds a meaningful layer of obscurity that reduces automated scanning and brute force attempts.

When combined with other self-hosted security tools, port knocking creates a defense-in-depth strategy. For SSH certificate management, see our [step-ca vs Teleport vs Vault SSH guide](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/). For broader intrusion prevention, our [fail2ban vs SSHGuard vs CrowdSec comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/) covers complementary approaches. And for web application firewall protection, check our [BunkerWeb vs ModSecurity vs CrowdSec guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/).

## FAQ

### Is port knocking a replacement for a firewall?

No. Port knocking is a complementary security layer that works alongside a firewall. It dynamically opens ports based on authorized knock sequences, but you still need a properly configured firewall with default-deny policies as your baseline.

### Can port knocking sequences be discovered by attackers?

Traditional port knocking sequences can potentially be discovered through log analysis or packet sniffing if the attacker has network visibility. SPA (Single Packet Authorization) eliminates this risk by encrypting the authorization packet, making it unreadable to anyone without the correct key.

### What happens if the knock daemon crashes?

If knockd or fwknop-server crashes, ports remain in their last state. If no ports were opened, all services stay hidden. However, if a port was opened and the daemon crashes before the timeout, that port may remain open until the next daemon restart or manual firewall cleanup.

### Does port knocking work with NAT or cloud networks?

Port knocking works through NAT because the daemon sees the post-NAT source IP. However, in cloud environments with security groups (AWS, GCP, Azure), you need to use the cloud provider's API in addition to local firewall rules, as security groups operate at the hypervisor level.

### Is Single Packet Authorization better than traditional port knocking?

SPA is generally superior because it provides cryptographic authentication, replay protection, and source IP verification in a single packet. Traditional port knocking is simpler to set up but vulnerable to replay attacks and packet sniffing. For production systems, fwknop (SPA) is the recommended choice.

### Can I use port knocking to protect services other than SSH?

Yes. Port knocking can protect any TCP or UDP service — web servers, databases, mail servers, or custom applications. Configure separate knock sequences for each service with appropriate timeout values based on how long you need access.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Port Knocking & Single Packet Authorization: fwknop vs knockd vs SPA Guide 2026",
  "description": "Compare fwknop, knockd, and Single Packet Authorization (SPA) for self-hosted network security. Complete setup guide with iptables configs, Docker deployment, and SPA implementation.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
