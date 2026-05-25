---
title: "Self-Hosted iptables Rule Persistence and Management: iptables-persistent vs netfilter-persistent vs Firewalld Offline"
date: "2026-05-25"
tags: ["iptables", "firewall-management", "linux-system-administration", "network-security"]
draft: false
---

The Linux netfilter framework powers iptables, the most widely deployed firewall on Linux servers. But iptables rules exist only in kernel memory — a server reboot wipes every rule, potentially leaving systems completely unprotected until an administrator manually restores the configuration. For self-hosted infrastructure, automating iptables rule persistence is not a convenience; it is a security requirement. Three approaches dominate this space: the Debian **iptables-persistent** package, the Red Hat **netfilter-persistent** framework, and **Firewalld offline** mode with direct interface rules. Each handles persistence differently, and choosing the right one depends on your distribution and management philosophy.

## iptables-persistent: The Debian/Ubuntu Standard

The `iptables-persistent` package (also known as `netfilter-persistent` on newer Debian releases) provides automatic loading and saving of iptables rules through systemd services. It stores rules in plain-text files under `/etc/iptables/` and hooks into the boot and shutdown process to ensure rules survive reboots.

### Installation and Setup

```bash
# Install on Debian/Ubuntu
sudo apt install -y iptables-persistent

# During installation, you will be prompted to save current rules
# Accept to save current IPv4 rules: Yes
# Accept to save current IPv6 rules: Yes
```

### Rule File Locations

```bash
# IPv4 rules
/etc/iptables/rules.v4

# IPv6 rules
/etc/iptables/rules.v6
```

### Manual Save and Load

```bash
# Save current running rules to persistent files
sudo netfilter-persistent save

# Load rules from persistent files (without reboot)
sudo netfilter-persistent reload

# Stop the firewall (clears rules — use with caution)
sudo netfilter-persistent stop
```

### Sample rules.v4 Configuration

```bash
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

# Allow loopback
-A INPUT -i lo -j ACCEPT

# Allow established connections
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
-A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p tcp --dport 443 -j ACCEPT

# Allow ICMP (ping)
-A INPUT -p icmp -j ACCEPT

# Drop everything else (implicit by INPUT DROP policy)
COMMIT
```

## netfilter-persistent: The Modern Debian Framework

On Debian 10+ and Ubuntu 18.04+, `iptables-persistent` has been superseded by the `netfilter-persistent` framework. While the package name changed, the underlying mechanism remains the same — it is a plugin-based system that saves and loads netfilter rules during boot and shutdown.

The key difference is extensibility: netfilter-persistent supports plugins for iptables, ip6tables, ebtables, and arptables, making it a unified framework for all netfilter rule persistence.

### Plugin Architecture

```bash
# List available plugins
ls /usr/share/netfilter-persistent/plugins.d/

# Typical plugins:
# 15-ip4tables  — saves/loads IPv4 iptables rules
# 25-ip6tables  — saves/loads IPv6 ip6tables rules
# 30-eiptables  — saves/loads ebtables rules (if installed)
```

### Service Management

```bash
# Check status
sudo systemctl status netfilter-persistent

# Enable automatic loading at boot
sudo systemctl enable netfilter-persistent

# Disable (not recommended for production)
sudo systemctl disable netfilter-persistent

# Manual reload after editing rules files
sudo systemctl reload netfilter-persistent
```

### Docker Compose Integration

When running containerized workloads, iptables rules must account for Docker's own chain manipulations:

```yaml
version: "3.8"
services:
  firewall-rules:
    image: alpine:latest
    volumes:
      - /etc/iptables:/etc/iptables:ro
      - /var/run/netfilter-persistent:/run/netfilter-persistent
    command: >
      sh -c "
        netfilter-persistent reload &&
        tail -f /dev/null
      "
    restart: unless-stopped
    network_mode: host
    privileged: true
```

## Firewalld Direct Rules: The Red Hat Alternative

Firewalld is the default firewall management tool on RHEL, CentOS, Fedora, and related distributions. Unlike the static rules files used by iptables-persistent, firewalld maintains rules dynamically through D-Bus and stores its configuration in XML files under `/etc/firewalld/`.

For administrators who need raw iptables rules alongside firewalld's zone-based management, firewalld supports **direct interface rules** — iptables rules that are inserted directly into the kernel's netfilter tables, bypassing firewalld's zone abstraction.

### Managing Firewalld Direct Rules

```bash
# Add a direct rule (persists across reloads)
sudo firewall-cmd --permanent --direct --add-rule ipv4 filter INPUT 0 -p tcp --dport 8080 -j ACCEPT

# Reload firewalld to apply direct rules
sudo firewall-cmd --reload

# List all direct rules
sudo firewall-cmd --permanent --direct --get-all-rules

# Remove a direct rule
sudo firewall-cmd --permanent --direct --remove-rule ipv4 filter INPUT 0 -p tcp --dport 8080 -j ACCEPT
```

### Firewalld XML Configuration

Firewalld stores its configuration in XML files that can be edited directly or managed through `firewall-cmd`:

```bash
# Direct rules are stored in:
/etc/firewalld/direct.xml

# Zone configurations:
/etc/firewalld/zones/public.xml
/etc/firewalld/zones/internal.xml
```

### Export/Backup Firewalld Configuration

```bash
# Backup all firewalld configuration
sudo tar czf /backup/firewalld-config.tar.gz /etc/firewalld/

# Restore
sudo tar xzf /backup/firewalld-config.tar.gz -C /
sudo firewall-cmd --reload
```

## Comparison Table

| Feature | iptables-persistent | netfilter-persistent | Firewalld Direct Rules |
|---|---|---|---|
| **Distribution** | Debian/Ubuntu (legacy) | Debian 10+/Ubuntu 18.04+ | RHEL/CentOS/Fedora |
| **Rule Format** | Plain text (iptables-save) | Plain text (iptables-save) | XML (firewalld native) |
| **Storage Location** | `/etc/iptables/rules.v4` | `/etc/iptables/rules.v4` | `/etc/firewalld/direct.xml` |
| **IPv6 Support** | Yes (rules.v6) | Yes (via plugin) | Yes (native) |
| **ebtables Support** | No | Yes (via plugin) | No |
| **Dynamic Updates** | No (save then reload) | No (save then reload) | Yes (D-Bus API) |
| **Zone Management** | No | No | Yes (built-in) |
| **Rich Rules** | No | No | Yes (firewalld syntax) |
| **Automation Friendly** | Yes (text files) | Yes (text files) | Yes (firewall-cmd CLI) |
| **Docker Compatible** | Requires manual ordering | Requires manual ordering | Handles Docker chains |
| **Rollback Support** | Manual (edit text file) | Manual (edit text file) | `firewall-cmd --reload` reverts uncommitted changes |

## Choosing the Right Persistence Method

**Use iptables-persistent/netfilter-persistent when:** You are running Debian or Ubuntu and prefer the simplicity of plain-text rule files. The `iptables-save` and `iptables-restore` format is universally understood, easily version-controlled with Git, and can be diffed to track changes over time. This is the most straightforward approach for servers with static firewall requirements.

**Use Firewalld when:** You are on RHEL, CentOS, or Fedora, or you need zone-based firewall management with runtime changes that can be rolled back. Firewalld's D-Bus API enables programmatic management, and its direct interface lets you combine zone-based rules with raw iptables syntax when needed.

**Use a hybrid approach when:** You need both zone-based management and fine-grained iptables control. Firewalld handles the broad policy zones while direct rules manage application-specific exceptions. For Debian systems, netfilter-persistent handles the base rules while application-specific chains are managed by individual service scripts.

## Why Self-Host Your Firewall Persistence Strategy?

Every self-hosted server is a potential target for network-based attacks the moment it connects to a public network. A default-deny firewall policy with carefully managed allow rules is the first line of defense — but that defense vanishes entirely if the server reboots and the rules are not automatically restored.

Having a reliable persistence mechanism means your firewall rules survive planned maintenance windows, unexpected crashes, and kernel updates that require reboots. The alternative — manually re-applying rules after every restart — is not just inconvenient; it creates dangerous windows of exposure where your server may be running with no firewall at all.

For teams managing heterogeneous infrastructure across Debian and RHEL families, understanding both the netfilter-persistent and firewalld approaches ensures consistent security posture regardless of the underlying distribution. When deploying [containerized workloads](../2026-05-12-self-hosted-nbd-storage-server-nbd-server-nbdkit-drbd-guide/) that manipulate iptables chains for port forwarding and network isolation, having predictable base rules that persist across reboots prevents Docker's chain modifications from conflicting with your security policy.

The operational discipline of version-controlling your firewall rules — whether as plain text in `/etc/iptables/` or XML in `/etc/firewalld/` — also enables change tracking and audit trails. When an incident occurs, being able to diff the current rules against last week's baseline is invaluable for forensic analysis. For broader firewall policy management across multiple servers, see our [firewall policy management guide](../2026-05-14-self-hosted-firewall-policy-management-capirca-aerleon-fworch-guide/) which covers tools for managing rules at scale.

## Automated Rule Validation

Before persisting any rule changes, validate them to avoid locking yourself out of the server:

```bash
# Test new rules with a safety timeout
sudo iptables-restore < /tmp/new-rules.v4 &&   echo "Rules applied. Checking connectivity..." &&   sleep 30 &&   echo "If you can read this, rules are OK. Saving..." &&   sudo netfilter-persistent save ||   echo "Timeout reached — reverting rules"

# Or use a cron-based safety net:
# Add this BEFORE applying new rules:
(crontab -l 2>/dev/null; echo "*/5 * * * * iptables-restore /etc/iptables/rules.v4") | crontab -
# After confirming rules work, remove the cron entry
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted iptables Rule Persistence and Management: iptables-persistent vs netfilter-persistent vs Firewalld Offline",
  "description": "Compare iptables-persistent, netfilter-persistent, and Firewalld direct rules for persistent firewall management on self-hosted Linux servers.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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

### What happens if I lose SSH access after applying new iptables rules?
If you applied rules without a safety timeout and locked yourself out, you will need out-of-band access to the server — either through a console connection, IPMI/iLO remote console, or a rescue boot environment. This is why the safety timeout pattern shown above is critical: it automatically reverts rules if you cannot confirm connectivity.

### Can I version-control my iptables rules with Git?
Yes, and you should. The plain-text format used by iptables-persistent and netfilter-persistent is ideal for Git tracking. Initialize a repository at `/etc/iptables/` and commit after every rule change. This provides a complete audit trail of who changed what and when.

### Do Docker containers interfere with iptables-persistent rules?
Docker modifies iptables rules at runtime by adding its own chains (DOCKER, DOCKER-USER, etc.) for port forwarding and container networking. These runtime changes are NOT saved by `netfilter-persistent save`. To preserve Docker-related rules, either manage them through Docker Compose `--iptables=false` mode with manual rules, or accept that Docker will rebuild its chains on every daemon restart.

### Is firewalld compatible with Docker?
Firewalld and Docker can conflict because both manipulate iptables rules. Firewalld may block Docker's port forwarding rules. The recommended solution is to add the Docker interface to firewalld's trusted zone: `sudo firewall-cmd --permanent --zone=trusted --add-interface=docker0 && sudo firewall-cmd --reload`. Alternatively, configure Docker to use `--iptables=false` and manage all rules through firewalld.

### How do I migrate from iptables-persistent to firewalld?
Export your current rules with `sudo iptables-save > /tmp/rules.backup`, install firewalld, then recreate the rules using `firewall-cmd` commands or by importing them as direct rules. Test thoroughly before disabling netfilter-persistent.

### Can netfilter-persistent handle nftables rules?
The netfilter-persistent framework supports nftables through a separate plugin (`nftables-persistent` package). Install it alongside netfilter-persistent, and nftables rules in `/etc/nftables.conf` will be loaded at boot. Note that iptables and nftables are different backends — you should use one or the other, not both simultaneously.
