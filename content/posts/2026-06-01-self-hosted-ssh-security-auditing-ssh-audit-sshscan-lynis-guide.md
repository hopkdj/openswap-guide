---
title: "Self-Hosted SSH Security Auditing: ssh-audit vs ssh_scan vs Lynis SSH Hardening Guide 2026"
date: "2026-06-01"
tags: ["ssh", "security", "auditing", "hardening", "linux", "compliance", "self-hosted", "server-security", "openssh"]
draft: false
description: "Compare ssh-audit, ssh_scan, and Lynis for SSH security auditing. Harden your SSH server configuration with automated vulnerability scanning, compliance checks, and remediation guides."
---

## Why Self-Host SSH Security Auditing?

SSH is the backbone of remote server administration — and also the most frequently attacked service on the internet. Misconfigured SSH servers with outdated ciphers, weak key exchange algorithms, or deprecated MACs expose your infrastructure to man-in-the-middle attacks, brute-force attempts, and cryptographic downgrades. Automated SSH security auditing tools scan your SSH server configuration against current best practices, identifying weak algorithms and suggesting concrete remediation steps before attackers find them first.

Running your own SSH auditing on a self-hosted server (or as part of your CI/CD pipeline) ensures every server in your fleet maintains a consistent security baseline. Unlike one-off manual audits, automated tools can be scheduled to run weekly, integrated with monitoring systems for alerting, and even enforced as a pre-deployment gate. With the steady deprecation of older cryptographic primitives (SHA-1, CBC mode ciphers, Diffie-Hellman groups below 2048 bits), staying ahead of SSH hardening requirements is a continuous process — not a one-time setup.

For intrusion prevention at the SSH layer, see our [Fail2ban vs SSHGuard vs CrowdSec comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/). For SSH certificate-based authentication at scale, check our [SSH Certificate Management guide](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/). For general Linux server security auditing beyond SSH, our [Lynis vs OpenSCAP vs Goss guide](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide-2026/) covers broader compliance.

## SSH Auditing Tool Comparison

| Feature | ssh-audit | ssh_scan | Lynis (SSH Module) |
|---------|-----------|----------|---------------------|
| **GitHub Stars** | 4,205 | 1,200+ (Ruby gem) | 15,705 |
| **Language** | Python | Ruby | Shell |
| **Focus** | SSH protocol & crypto | SSH config policy | Full system audit |
| **Key Exchange Audit** | Full algorithm enumeration | Yes | Coverage check |
| **Cipher Audit** | Per-algorithm grading | Policy-based | Best-practice check |
| **Host Key Audit** | Key size & type validation | Key type check | Permission & owner check |
| **Client Simulation** | Yes (tests server preference) | No | No |
| **Compliance Framework** | Custom policy files | STIG/SCAP | CIS, HIPAA, ISO27001 |
| **Output Format** | JSON, text, CSV | JSON, YAML | Text, HTML report |
| **SSH Config Review** | No (server-side only) | Yes (ssh_config + sshd_config) | Yes (full scan) |
| **Last Updated** | Sep 2025 | Active (Ruby gem) | May 2026 |

## ssh-audit: Deep SSH Cryptographic Analysis

ssh-audit is the gold standard for SSH server cryptographic auditing. Unlike general security scanners that check for SSH being "enabled" or "disabled," ssh-audit establishes a complete SSH connection handshake and enumerates every algorithm the server supports: key exchanges, host keys, ciphers, MACs, and compression. It assigns each algorithm a grade (pass/fail/warn) based on current cryptographic best practices and known vulnerabilities.

### Installing and Running ssh-audit

```bash
# Install via pip
pip install ssh-audit

# Or clone and run directly
git clone https://github.com/jtesta/ssh-audit.git
cd ssh-audit

# Basic scan
ssh-audit localhost

# Scan a remote server
ssh-audit 192.168.1.100

# JSON output for automation
ssh-audit -j server.example.com > audit_report.json

# Batch scan multiple servers
for host in server1 server2 server3; do
    ssh-audit -j $host > "audit_${host}.json"
done
```

### Understanding ssh-audit Output

A typical ssh-audit report categorizes findings by severity:

```text
# Key Exchange Algorithms
(kex) curve25519-sha256                    -- [info] available since OpenSSH 7.4
(kex) diffie-hellman-group14-sha1          -- [warn] using weak hashing algorithm
(kex) diffie-hellman-group1-sha1           -- [fail] removed (in server) since OpenSSH 6.7, unsafe

# Host-key Algorithms  
(key) ssh-ed25519                           -- [info] available since OpenSSH 6.5
(key) ssh-rsa                               -- [warn] using weak hashing algorithm

# Encryption Algorithms (ciphers)
(enc) chacha20-poly1305@openssh.com         -- [info] available since OpenSSH 6.5
(enc) aes128-cbc                            -- [warn] using weak cipher mode
```

ssh-audit also supports custom policy files that define your organization's required, recommended, and forbidden algorithms — making it suitable for automated CI/CD pipeline integration where non-compliant servers block deployment.

## ssh_scan: Policy-Driven SSH Configuration Audit

ssh_scan, maintained as a Ruby gem by the Mozilla Foundation's security team, takes a different approach. Rather than deep cryptographic analysis, ssh_scan focuses on configuration policy compliance. It reads both `sshd_config` (server) and `ssh_config` (client) files, checks them against configurable policies (including DISA STIG and Mozilla's own OpenSSH guidelines), and reports deviations.

### Installing and Running ssh_scan

```bash
# Install Ruby gem
gem install ssh_scan

# Policy-based scan
ssh_scan --policy=MozillaModern localhost

# Scan with STIG compliance checking
ssh_scan --policy=STIG server.example.com

# Check sshd_config directly
ssh_scan -c /etc/ssh/sshd_config --policy=MozillaModern

# Output in JSON for automation
ssh_scan -o json --policy=MozillaModern localhost
```

ssh_scan excels in environments with formal compliance requirements (STIG, CIS benchmarks). It checks config directives like `PermitRootLogin`, `PasswordAuthentication`, `X11Forwarding`, `MaxAuthTries`, and dozens of other SSH parameters that ssh-audit's protocol-level scan doesn't cover. For organizations that need to enforce a standardized SSH configuration across hundreds of servers, ssh_scan's policy engine is invaluable.

## Lynis: Comprehensive SSH Security Assessment

Lynis is a full-system security auditing tool that includes an extensive SSH assessment module as part of its broader system scan. While not SSH-specific like ssh-audit, Lynis checks SSH configuration, authentication methods, file permissions on SSH keys and configs, and reports compliance against standards like CIS benchmarks, HIPAA, and ISO 27001.

### Running Lynis SSH Audits

```bash
# Install Lynis
sudo apt install lynis  # or clone from GitHub

# Full system audit (includes SSH checks)
sudo lynis audit system

# SSH-specific test group only
sudo lynis audit system --tests-from-group SSH

# Check key permissions and ownership
sudo lynis audit system --tests SSH-7408
```

Key SSH-specific checks Lynis performs:
- SSH daemon configuration hardening (PermitRootLogin, Protocol version)
- SSH host key permissions and ownership (must be root:root, 600 mode)
- Authorized keys file security (permissions, empty passwords)
- SSH protocol version enforcement (must be v2 only)
- Cipher and MAC algorithm review against best practices

Lynis generates a scored report with suggestions ranked by severity, making it particularly useful for compliance audits where documentation of findings is required.

## Hardening Your SSH Server: Practical Steps

After running these auditing tools, implement these SSH hardening measures:

```bash
# /etc/ssh/sshd_config hardening
# Disable root login
PermitRootLogin no

# Use SSH protocol 2 only
Protocol 2

# Restrict authentication methods
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no

# Limit ciphers to modern, secure algorithms
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com

# Use strong key exchange
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512

# Strong MACs only
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@opensssh.com

# Restrict users and groups
AllowUsers deploy@192.168.0.0/16
MaxAuthTries 3
MaxSessions 5

# Apply and verify
sudo systemctl restart sshd
ssh-audit localhost
```

## Building an SSH Audit Pipeline

For organizations managing dozens or hundreds of servers, individual audits aren't enough. Build a continuous SSH auditing pipeline that scans all servers weekly, compares results against your security baseline policy, and alerts on any regression. Modern SSH hardening is an ongoing discipline, not a one-time checklist — and these three tools together provide comprehensive coverage from cryptographic protocol analysis through configuration policy enforcement."

## FAQ

### How often should I audit my SSH configuration?

For production servers, run SSH audits at minimum monthly — and immediately after any configuration change, OS upgrade, or OpenSSH version update. Automated weekly scans integrated with your monitoring stack (alerting on new [warn] or [fail] findings) provide the best security posture. For CI/CD pipelines, audit as a pre-deployment gate to prevent insecure configurations from reaching production.

### What's the difference between SSH protocol auditing and config auditing?

Protocol auditing (ssh-audit) analyzes what the SSH server actually negotiates during a handshake — the algorithms it presents, their order of preference, and known vulnerabilities. Config auditing (ssh_scan, Lynis) reads the static configuration files and checks for insecure directives. Both are necessary: a server might have a secure config but be running an outdated OpenSSH version that supports weak algorithms, or vice versa.

### Can I automate remediation based on audit findings?

ssh-audit does not auto-remediate, but its JSON output is designed for pipeline integration. You can parse the output and apply fixes via configuration management tools (Ansible, Puppet, Salt). ssh_scan integrates with InSpec for automated compliance enforcement. Lynis includes a `lynis show suggestions` command that provides copy-pasteable remediation commands. For a fully automated approach, combine ssh-audit JSON output with a simple remediation script that updates `/etc/ssh/sshd_config` using `sed` or Ansible.

### Does SSH auditing affect server performance?

No — SSH auditing tools only establish a normal SSH connection handshake (or read config files locally) and close immediately. There is no persistent connection, no resource consumption beyond the scan duration (typically under 2 seconds), and no impact on existing SSH sessions. However, aggressive scanning of many servers simultaneously from a single source may trigger rate limiting or intrusion detection systems — use batch scanning with delays between hosts in production.

### What SSH algorithms should I disable in 2026?

As of 2026, you should disable: all CBC-mode ciphers (aes128-cbc, aes256-cbc, 3des-cbc), diffie-hellman groups below 2048 bits (group1-sha1, group14-sha1), RSA host keys below 2048 bits, DSA keys entirely, and HMAC-MD5 / HMAC-SHA1 MACs. ssh-audit will flag all of these with [fail] or [warn] severity. Keep curve25519, ed25519 keys, chacha20-poly1305, and AES-GCM ciphers as your primary algorithms.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SSH Security Auditing: ssh-audit vs ssh_scan vs Lynis SSH Hardening Guide 2026",
  "description": "Compare ssh-audit, ssh_scan, and Lynis for SSH security auditing. Harden your SSH server configuration with automated vulnerability scanning, compliance checks, and remediation guides.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到科技监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测市场事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
