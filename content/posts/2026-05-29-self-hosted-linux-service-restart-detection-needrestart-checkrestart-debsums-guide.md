---
title: "Self-Hosted Linux Service Restart Detection: needrestart vs checkrestart vs debsums"
date: "2026-05-29"
tags: ["linux", "system-administration", "debian", "ubuntu", "process-management", "security"]
draft: false
---

After installing package updates on a Debian or Ubuntu server, some running services continue using old library code until they are restarted. This is one of the most common reasons why "patched" servers remain vulnerable — the security fix was installed, but the running process never loaded the updated binary. This guide compares three tools for detecting which services need restarting after package updates: **needrestart**, **checkrestart** (from debian-goodies), and **debsums**.

Understanding which services are running outdated code is essential for any Linux administrator. A service that loads a vulnerable version of OpenSSL at boot will remain vulnerable even after the package is upgraded — until it is restarted. These tools bridge the gap between "update installed" and "update active."

## The Problem: Running Services vs Installed Packages

When you run `apt upgrade`, new versions of libraries and binaries are written to disk. However, Linux processes that were started before the upgrade continue using the old file descriptors in memory. The process only picks up the new code after a restart.

This affects:
- **Web servers** (Nginx, Apache) — using old OpenSSL or libpcre
- **Database servers** (PostgreSQL, MySQL) — using old client libraries
- **SSH daemons** — using old PAM or crypto libraries
- **Application servers** — using outdated runtime libraries

Without a restart detection tool, you either manually check every service after every update (tedious) or assume everything is fine (risky). The tools below automate this detection.

## needrestart: Comprehensive Restart Detection

**Needrestart** is the most widely used service restart detection tool on modern Debian and Ubuntu systems. It checks running processes against installed package versions and reports which services need restarting — and can even restart them automatically.

**Repository**: `https://salsa.debian.org/liske/needrestart`  
**Stars**: N/A (Debian repository package)  
**License**: GPL-2.0+

### Key Features

- Detects processes using deleted or replaced library files
- Identifies which systemd services own those processes
- Supports automatic restart (interactive, batch, or none mode)
- Kernel upgrade detection (reboot suggestion)
- Container detection (skips processes inside containers)
- Supports Perl, Python, Ruby interpreter restart detection
- Configurable notification methods (console, syslog, email)

### Installation

```bash
sudo apt install needrestart
```

### Configuration

Main config: `/etc/needrestart/needrestart.conf`

```perl
# Run in batch mode (no interactive prompts)
$nrconf{restart} = 'l';  # 'l' = list only, 'a' = auto-restart, 'i' = interactive

# Use systemd to restart services
$nrconf{rcmethod} = 'systemd';

# Skip specific services from restart suggestion
$nrconf{blacklist_rc_expr} = [
    qr/^docker/,
    qr/^containerd/,
];

# Send notification email
$nrconf{notify} = 0;  # Set to 1 to enable email notifications

# Kernel upgrade detection
$nrconf{kernelhints} = 1;
```

### Running needrestart

```bash
# Interactive mode (default)
sudo needrestart

# Batch mode — just list, no prompts
sudo needrestart -b

# Verbose output
sudo needrestart -v

# JSON output for automation
sudo needrestart -j
```

### Docker Compose Setup (Centralized Monitoring)

```yaml
version: "3.8"
services:
  needrestart-check:
    image: debian:bookworm-slim
    volumes:
      - /run/systemd/system:/run/systemd/system:ro
      - /proc:/host/proc:ro
      - /var/run:/host/var/run:ro
    command: >
      bash -c "
        apt-get update -qq &&
        apt-get install -y -qq needrestart procps > /dev/null &&
        needrestart -b -l
      "
    restart: "no"
```

## checkrestart: Lightweight Alternative from debian-goodies

**Checkrestart** is part of the `debian-goodies` package collection. It uses the `lsof` command to find processes running with deleted files (which indicates an upgrade has replaced the binary or library on disk). It is simpler than needrestart but requires fewer dependencies.

**Repository**: `https://salsa.debian.org/debian-goodies-team/debian-goodies`  
**Stars**: N/A (Debian repository package)  
**License**: GPL-2.0+

### Key Features

- Uses `lsof` to detect processes with deleted file references
- Groups results by package and service
- Lightweight — single script, no configuration file
- Works on any Debian-based system
- No daemon or timer — run manually or via cron
- Shows exact deleted files causing the restart suggestion

### Installation

```bash
sudo apt install debian-goodies
```

### Usage

```bash
sudo checkrestart
```

Sample output:

```
Found 3 processes using old versions of upgraded files
(2 distinct programs)
(1 distinct packages)

Of these, 2 seem to contain systemd service replacements or potential replacements:
apache2.service
  1337  /usr/sbin/apache2

Of these, 1 seem to contain init script replacements or potential replacements:
postgresql
  2048  /usr/lib/postgresql/15/bin/postgres
```

### Comparison: checkrestart vs needrestart

| Aspect | checkrestart | needrestart |
|--------|-------------|-------------|
| **Detection method** | lsof + deleted files | /proc/*/maps + package database |
| **Dependencies** | lsof, dpkg | perl, dpkg, systemd |
| **Auto-restart** | No | Yes |
| **Kernel detection** | No | Yes |
| **Container awareness** | No | Yes |
| **Interpreter detection** | No | Yes (Perl, Python, Ruby) |
| **Configuration** | None needed | Extensive .conf file |
| **Output format** | Plain text | Plain text, JSON |

## debsums: File Integrity Verification

**Debsums** is primarily a file integrity checker, but it can also detect which packages have files that differ from the installed package checksums. After an upgrade, running `debsums -s` silently passes if all files match — but if a process is still using an old file that was replaced, the checksums will differ.

**Repository**: `https://salsa.debian.org/debian/debsums`  
**Stars**: N/A (Debian repository package)  
**License**: MIT

### Key Features

- Verifies file checksums against the dpkg database
- Detects modified configuration files separately from binaries
- Can check specific packages or all installed packages
- Useful for post-incident forensics (did an attacker modify a binary?)
- Generates reports of all changed files

### Installation

```bash
sudo apt install debsums
```

### Usage

```bash
# Check all installed packages
sudo debsums -s  # silent (only show mismatches)

# Show changed configuration files
sudo debsums -ac

# Check a specific package
sudo debsums nginx

# Generate a baseline for future comparison
sudo debsums -g > /var/lib/debsums/baseline
```

### Using debsums for Restart Detection

While debsums does not directly tell you which processes need restarting, you can combine it with process inspection:

```bash
#!/bin/bash
# Check which packages have changed binaries
CHANGED=$(debsums -s 2>/dev/null | grep -v '^debsums:' | awk '{print $NF}')

for pkg in $CHANGED; do
    # Find processes running from this package
    PIDS=$(lsof +c 0 2>/dev/null | grep "/usr/sbin/$pkg" | awk '{print $2}' | sort -u)
    if [ -n "$PIDS" ]; then
        echo "Package $pkg has changed files. Running PIDs: $PIDS"
    fi
done
```

## Comparison Table

| Feature | needrestart | checkrestart | debsums |
|---------|------------|-------------|---------|
| **Primary purpose** | Restart detection | Restart detection | File integrity |
| **Detection method** | /proc maps + dpkg | lsof deleted files | Checksum verification |
| **Auto-restart** | Yes | No | No |
| **Kernel upgrade alert** | Yes | No | No |
| **Container detection** | Yes | No | No |
| **Interpreter restarts** | Yes (Perl, Python, Ruby) | No | No |
| **JSON output** | Yes | No | No |
| **Forensic capability** | No | No | Yes |
| **Resource usage** | Low | Very low | Low |
| **Best for** | Production servers | Quick checks | Security audits |

## Choosing the Right Tool

### For Production Servers

**Needrestart** is the clear choice. Its auto-restart capability, kernel upgrade detection, and systemd integration make it the most comprehensive option. Configure it in batch mode (`-b`) and run it after every `apt upgrade` via an APT hook:

```bash
# /etc/apt/apt.conf.d/99needrestart
DPkg::Post-Invoke { "needrestart -b -q"; };
```

### For Quick Checks

**Checkrestart** is perfect for a quick "what needs restarting?" check after a manual upgrade. It has no configuration overhead and gives you a clear list of services. Install `debian-goodies` on all your servers and run it whenever you feel like checking.

### For Security Audits

**Debsums** is essential for post-incident forensics. If you suspect a server has been compromised, running `debsums -s` immediately reveals which binaries have been modified from their packaged state. This is invaluable for incident response.

## Why Self-Host Service Restart Detection?

Cloud providers do not manage the relationship between package updates and running services on your VMs. After a kernel live-patch is applied, or after OpenSSL is upgraded, the responsibility to restart affected services falls entirely on you. Self-hosted restart detection tools automate this critical step in the patch management lifecycle.

For comprehensive process management on your servers, see our [process supervisor comparison](../2026-04-25-supervisord-vs-s6-overlay-vs-runit-self-hosted-process-management/). For automated log rotation that ensures services pick up new log files after rotation, check our [log rotation guide](../2026-04-26-logrotate-vs-s6-log-vs-svlogd-self-hosted-log-rotation-guide-2026/).

## FAQ

### Do I really need to restart services after every update?

Not every update affects running services. Minor updates to documentation packages, development headers, or unused libraries have no impact on running processes. However, updates to core libraries (OpenSSL, libc, libpam) or daemon binaries absolutely require a restart. Restart detection tools tell you exactly which services are affected.

### Can needrestart restart services automatically?

Yes. Set `$nrconf{restart} = 'a'` in the configuration to auto-restart all detected services. However, exercise caution — some services (like database servers) should be restarted during maintenance windows, not immediately. Use `'l'` (list-only) mode and review the output before restarting manually.

### Why does checkrestart show fewer services than needrestart?

Checkrestart only detects processes using **deleted** files. Needrestart also detects processes using files that were **replaced** (same path, different inode). This means needrestart catches more cases, especially for services that keep file handles open after upgrades.

### Does debsums detect security compromises?

Debsums detects when files on disk differ from the package checksums. This catches both legitimate modifications (admin changed a config file) and malicious ones (an attacker replaced a binary). Run `debsums -s` regularly and alert on any unexpected changes to binary files (not configuration files).

### How do I automate restart detection after apt upgrade?

Use an APT post-invoke hook. Create `/etc/apt/apt.conf.d/99needrestart` with:

```
DPkg::Post-Invoke { "needrestart -b -q"; };
```

This runs needrestart in batch mode after every package installation, showing only the services that need restarting.

### Will restarting a service cause downtime?

For most services, a restart is a brief interruption (typically under one second). For stateful services like databases, a restart may take longer as the service flushes buffers and replays logs. Always test restart behavior in staging before automating in production.

### Can these tools detect if a kernel update requires a reboot?

**Needrestart** can detect kernel upgrades and suggest a reboot. **Checkrestart** and **debsums** cannot. For automated reboot detection, consider **kured** (Kubernetes) or **needrestart** with kernel hints enabled.

## Conclusion

Service restart detection is a critical but often overlooked part of Linux system administration. Needrestart provides the most comprehensive solution with auto-restart capabilities and kernel detection. Checkrestart offers a lightweight alternative for quick manual checks. Debsums serves a different but complementary purpose — file integrity verification for security audits. Together, they ensure that installed security patches actually take effect in running services.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Service Restart Detection: needrestart vs checkrestart vs debsums",
  "description": "Compare needrestart, checkrestart, and debsums for detecting which Linux services need restarting after package updates on Debian and Ubuntu.",
  "datePublished": "2026-05-29",
  "dateModified": "2026-05-29",
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
