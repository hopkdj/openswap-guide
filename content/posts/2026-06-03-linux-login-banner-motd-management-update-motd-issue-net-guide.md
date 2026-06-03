---
title: "Self-Hosted Linux Login Banner Management: update-motd vs motd-dynamic vs issue.net SSH Display Guide"
date: "2026-06-03"
tags: ["linux", "ssh", "security", "system-administration", "automation", "server-management"]
draft: false
---

## Introduction

Login banners and Message of the Day (MOTD) displays are essential components of Linux server administration that serve both security and operational purposes. A well-designed login banner provides legal warnings required by compliance frameworks, displays critical system health information to administrators, and reinforces security awareness every time a user connects. For organizations managing dozens or hundreds of servers, standardized login banners ensure consistent communication and reduce the cognitive load of context-switching between systems.

In this guide, we compare three approaches to Linux login banner management: **update-motd** (Ubuntu's dynamic MOTD framework), **motd-dynamic** (custom script-based dynamic banners), and **issue.net** (the pre-login SSH banner). Each serves distinct purposes at different stages of the connection lifecycle.

## Comparison Table

| Feature | update-motd (Ubuntu) | motd-dynamic (Custom) | issue.net (SSH Banner) |
|---------|---------------------|----------------------|------------------------|
| **Display Timing** | After successful login | After successful login | Before authentication |
| **Dynamic Content** | Yes (script-generated) | Yes (custom scripts) | Partially (escape sequences) |
| **Compliance Warnings** | Via pam_motd | Via custom scripts | Via sshd Banner directive |
| **System Health Info** | Built-in scripts (disk, memory, updates) | Fully customizable | Limited to hostname/network |
| **Multi-User Visibility** | All local + SSH logins | All local + SSH logins | SSH only |
| **Configuration Path** | `/etc/update-motd.d/` | Custom script + crontab/systemd timer | `/etc/issue.net` |
| **Complexity** | Low | Medium | Low |
| **Distribution Support** | Ubuntu/Debian (default) | Any Linux | Any Linux with SSH |
| **Best For** | Ubuntu servers, quick setup | Custom enterprise environments | Pre-auth compliance banners |

## update-motd: Ubuntu's Dynamic MOTD Framework

Ubuntu's `update-motd` system provides a modular, script-driven framework for generating dynamic login messages. Scripts in `/etc/update-motd.d/` are executed in numerical order at each login, and their combined output forms the MOTD displayed to the user.

Directory structure:

```bash
ls -la /etc/update-motd.d/
# 00-header       - Distribution name and version
# 10-help-text    - Documentation links
# 50-landscape-sysinfo - System information (Landscape)
# 50-motd-news    - Ubuntu news
# 80-livepatch    - Livepatch status
# 90-updates-available - Package update count
# 91-release-upgrade - Release upgrade availability
# 95-hwe-eol      - HWE support status
# 97-overlayroot  - Overlayroot status
# 98-fsck-at-reboot - Filesystem check status
# 98-reboot-required - Reboot requirement notification
```

Creating a custom MOTD script:

```bash
cat > /etc/update-motd.d/99-custom-info << 'EOF'
#!/bin/bash
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Server: $(hostname -f)"
echo "  IP: $(hostname -I | awk '{print $1}')"
echo "  Uptime: $(uptime -p | sed 's/up //')"
echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "  Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "  Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')"
echo "  Docker: $(docker ps -q 2>/dev/null | wc -l) containers running"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
EOF

chmod +x /etc/update-motd.d/99-custom-info
```

Disabling specific MOTD components:

```bash
# Make a script non-executable to disable it
chmod -x /etc/update-motd.d/50-motd-news

# Or remove entirely
rm /etc/update-motd.d/50-motd-news
```

Security hardening — adding a compliance warning:

```bash
cat > /etc/update-motd.d/00-compliance-warning << 'EOF'
#!/bin/bash
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  WARNING: This system is for authorized use only.           ║"
echo "║  All activities are monitored and recorded.                 ║"
echo "║  Unauthorized access is prohibited and will be prosecuted.  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
EOF

chmod +x /etc/update-motd.d/00-compliance-warning
```

**Advantages:**
- Zero configuration required on Ubuntu
- Modular script architecture
- Built-in system health reporting
- Runs via PAM, works for all login types

**Drawbacks:**
- Ubuntu/Debian specific (CentOS/RHEL use different system)
- Landscape integration requires Ubuntu Pro
- Limited customization of built-in scripts

## motd-dynamic: Custom Script-Based Banners

For environments requiring complete control over MOTD content, custom dynamic banners provide maximum flexibility. By combining systemd timers or cron jobs with shell scripts, you can generate update-to-date MOTD content that reflects real-time system state.

Systemd timer approach for dynamic MOTD generation:

```bash
# /etc/systemd/system/motd-update.service
cat > /etc/systemd/system/motd-update.service << 'EOF'
[Unit]
Description=Generate dynamic MOTD

[Service]
Type=oneshot
ExecStart=/usr/local/bin/generate-motd.sh
EOF

# /etc/systemd/system/motd-update.timer
cat > /etc/systemd/system/motd-update.timer << 'EOF'
[Unit]
Description=Update MOTD every 5 minutes

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now motd-update.timer
```

The generation script (`/usr/local/bin/generate-motd.sh`):

```bash
#!/bin/bash
OUTPUT="/run/motd.dynamic"

{
  echo "╔══════════════════════════════════════════════════╗"
  echo "║  $(hostname -f) — $(date '+%Y-%m-%d %H:%M:%S')"
  echo "╚══════════════════════════════════════════════════╝"
  echo ""
  echo "System Status:"
  echo "  • CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1)% used"
  echo "  • Memory: $(free | awk '/^Mem:/ {printf "%.1f", $3/$2*100}')% used"
  echo "  • Disk /: $(df -h / | awk 'NR==2 {print $5}') used"
  echo "  • Swap: $(free | awk '/^Swap:/ {if($2>0) printf "%.1f", $3/$2*100; else print "0"}')% used"
  echo ""
  
  # Security checks
  echo "Security Status:"
  if systemctl is-active --quiet fail2ban; then
    echo "  • fail2ban: ACTIVE ✓"
  else
    echo "  • fail2ban: INACTIVE ✗"
  fi
  if systemctl is-active --quiet ufw; then
    echo "  • Firewall: ACTIVE ✓"
  else
    echo "  • Firewall: INACTIVE ✗"
  fi
  
  # Pending updates
  UPDATES=$(apt list --upgradable 2>/dev/null | grep -c upgradable)
  if [ "$UPDATES" -gt 0 ]; then
    echo "  • Updates: $UPDATES packages pending"
  fi
  
  echo ""
  echo "Last 5 logins:"
  last -5 | awk '{print "  • " $1 " from " $3 " at " $4 " " $5 " " $6 " " $7}'
} > "$OUTPUT"

# Symlink for PAM
ln -sf "$OUTPUT" /etc/motd
```

Docker Compose example for centralized MOTD server:

```yaml
version: "3.8"
services:
  motd-server:
    image: nginx:alpine
    container_name: motd-server
    volumes:
      - ./motd-templates:/usr/share/nginx/html:ro
    ports:
      - "8080:80"
    restart: unless-stopped

  motd-generator:
    image: alpine:latest
    container_name: motd-gen
    volumes:
      - ./motd-templates:/output
    entrypoint: |
      /bin/sh -c '
        while true; do
          echo "<pre>Server Farm Status — $$(date)" > /output/index.html
          echo "" >> /output/index.html
          echo "Active Servers: $$(grep -c "^" /etc/hosts 2>/dev/null || echo "N/A")" >> /output/index.html
          sleep 300
        done
      '
    restart: unless-stopped
```

**Advantages:**
- Complete control over content and formatting
- Works on any Linux distribution
- Can integrate with monitoring systems (Nagios, Prometheus, Zabbix)

**Drawbacks:**
- Requires script creation and maintenance
- Timer/cron job must run reliably
- No built-in modular script architecture (must build yourself)

## issue.net: Pre-Authentication SSH Banner

The `/etc/issue.net` file is displayed by SSH **before** the user authenticates. This is the correct location for legal compliance warnings — it ensures unauthorized users see the warning even if they never successfully log in.

SSH server configuration (`/etc/ssh/sshd_config`):

```ini
# Enable banner display before authentication
Banner /etc/issue.net

# Restart SSH to apply
# systemctl restart sshd
```

Example compliance-focused `/etc/issue.net`:

```
**********************************************************************
*                                                                    *
*  WARNING: You are accessing a private computer system.            *
*  This system is for the use of authorized users only.             *
*  Individuals using this computer system without authority, or     *
*  in excess of their authority, are subject to having all of       *
*  their activities on this system monitored and recorded.          *
*                                                                    *
*  Anyone using this system expressly consents to such monitoring   *
*  and is advised that if such monitoring reveals possible          *
*  evidence of criminal activity, system personnel may provide      *
*  the evidence of such monitoring to law enforcement officials.    *
*                                                                    *
*  By logging in, you acknowledge that you have read and understand *
*  this notice.                                                      *
*                                                                    *
**********************************************************************
```

Dynamic hostname in issue.net using escape sequences:

```bash
# Supported SSH escape sequences in Banner:
# %% = literal '%'
# %h = hostname (from reverse DNS)
# %d = date

# Example with hostname:
echo "Connecting to %h — Unauthorized access prohibited." > /etc/issue.net
```

Generating issue.net from system info:

```bash
cat > /usr/local/bin/update-issue.sh << 'SCRIPT'
#!/bin/bash
cat > /etc/issue.net << EOF
===================================================
  WARNING: Authorized access only to $(hostname -f)
  System location: $(curl -s ifconfig.me 2>/dev/null || echo "unknown")
  All connections are logged and monitored.
===================================================
EOF
SCRIPT

chmod +x /usr/local/bin/update-issue.sh

# Run at boot and periodically
echo "@reboot root /usr/local/bin/update-issue.sh" >> /etc/crontab
```

**Advantages:**
- Displayed before authentication — covers unauthorized access attempts
- Simple text file, easy to deploy via configuration management
- Works with all SSH clients
- Meets compliance requirements (PCI DSS, HIPAA, SOX)

**Drawbacks:**
- Static by default (requires cron for dynamic updates)
- No system health information (pre-auth, no access to system state)
- Limited to text — no ANSI color or formatting

## Why Self-Host Your Login Banner Configuration?

Standardizing login banners across your server fleet is not just about aesthetics — it is a critical security control. Compliance frameworks like PCI DSS (Requirement 8.3), SOC 2, and HIPAA all require clear notice that systems are monitored and unauthorized access is prohibited. A well-implemented banner provides legal protection by establishing that intruders were warned, which is essential for prosecution under computer fraud statutes.

Beyond compliance, dynamic MOTD banners reduce operational friction. When an administrator SSHes into a server at 3 AM during an incident, seeing the hostname, IP address, load average, and disk usage immediately — without running a single command — saves precious seconds. For teams managing hundreds of servers, the cognitive benefit of standardized banners cannot be overstated. For more on Linux system administration automation, see our [systemd timer scheduling guide](../2026-05-23-linux-cron-job-scheduling-fcron-vs-cronie-vs-anacron-guide/) for automating MOTD updates and other periodic tasks.

For SSH security beyond login banners, our [SSH configuration hardening guide](../2026-06-01-linux-ssh-agent-management-ssh-agent-gpg-agent-keychain-ssh-askpass/) covers key-based authentication, agent forwarding security, and connection hardening. And for broader authentication infrastructure, our [PAM authentication modules guide](../2026-06-01-self-hosted-pam-authentication-modules-google-authenticator-pam-u2f-pam-ssh-guide/) explores multi-factor authentication integration with the Linux PAM stack.

## FAQ

### What is the difference between /etc/motd and /etc/issue.net?

`/etc/motd` is displayed **after** successful authentication (both local and SSH logins) and is suitable for system status information and operational messages. `/etc/issue.net` is displayed **before** authentication (SSH only) and should contain legal warnings and compliance notices. Never put system health information in issue.net — it reveals details to unauthenticated users.

### Can I use ANSI colors in MOTD banners?

Yes, but with caveats. For `/etc/motd` (post-login), ANSI escape codes work in most terminal emulators. For `/etc/issue.net` (pre-auth), some SSH clients strip ANSI codes. The safest approach: use ASCII box-drawing characters (like ╔═╗) for pre-auth banners and reserve colors for post-login MOTD. Test your banners with common clients (OpenSSH, PuTTY, Termius) before deploying fleet-wide.

### How do I disable the Ubuntu MOTD entirely?

To disable the dynamic MOTD on Ubuntu, either remove or make non-executable the scripts in `/etc/update-motd.d/`. For a completely static MOTD, create `/etc/motd` as a regular file (not a symlink). Ubuntu's `pam_motd` checks for a regular file first and skips the dynamic framework if it exists. Alternatively, comment out the `session optional pam_motd.so` line in `/etc/pam.d/sshd`.

### Does showing system info in MOTD create a security risk?

Post-login MOTD is only visible to authenticated users, so the risk is low. However, avoid exposing sensitive information like internal IP addresses, running services list, or user account details. Focus on actionable operational info: disk usage, uptime, pending updates, and service status. Never put this information in issue.net where unauthenticated users can see it.

### How do I deploy standardized banners across multiple servers?

Use configuration management tools like Ansible, Puppet, or Salt. For Ansible, create a role that deploys `/etc/issue.net`, `/etc/update-motd.d/` scripts, and `/etc/ssh/sshd_config` with the `Banner` directive. Use Jinja2 templates to inject host-specific information (hostname, IP, role). Commit your banner templates to version control to maintain a single source of truth for your compliance messaging.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Login Banner Management: update-motd vs motd-dynamic vs issue.net SSH Display Guide",
  "description": "Complete guide to Linux login banner and MOTD management comparing Ubuntu update-motd, custom dynamic banners, and SSH pre-auth issue.net with compliance requirements, configuration examples, and security best practices.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
