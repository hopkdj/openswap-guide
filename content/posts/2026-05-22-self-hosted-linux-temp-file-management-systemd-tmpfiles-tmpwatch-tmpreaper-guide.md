---
title: "Self-Hosted Linux Temp File Management: systemd-tmpfiles vs tmpwatch vs tmpreaper (2026)"
date: "2026-05-22"
tags: ["linux", "system-administration", "file-management", "cleanup", "self-hosted"]
draft: false
---

Every Linux server accumulates temporary files: application caches, session data, crash reports, package manager downloads, and log archives. Without automated cleanup, `/tmp` and `/var/tmp` fill up, causing service failures, login issues, and system instability.

This guide compares three self-hosted Linux temp file management solutions: **systemd-tmpfiles** (the modern default), **tmpwatch** (Red Hat classic), and **tmpreaper** (Debian derivative). Each handles stale file removal with different policies, performance characteristics, and configuration approaches.

## Why Temp File Management Matters

Temporary directories serve as shared scratch space for every process on the system. When cleanup fails:

- **Disk exhaustion**: `/tmp` at 100% prevents new file creation, breaking SSH logins, package installs, and application startups
- **Stale locks**: Abandoned lock files prevent services from restarting
- **Security risk**: World-readable temp files may contain sensitive data (credentials, tokens, keys)
- **Inode exhaustion**: Millions of small temp files consume all available inodes, even with free disk space
- **Performance degradation**: Large directories with thousands of files slow down `ls`, `find`, and directory scans

Automated cleanup solves these problems by removing files older than a configurable age threshold, typically 10 days for `/tmp` and 30 days for `/var/tmp`.

## Tool Comparison Overview

| Feature | systemd-tmpfiles | tmpwatch | tmpreaper |
|---------|-----------------|----------|-----------|
| **Origin** | systemd project (freedesktop) | Red Hat | Debian (fork of tmpwatch) |
| **Package** | Included with systemd | `tmpwatch` (RPM) | `tmpreaper` (DEB) |
| **Configuration** | `.conf` files in `/etc/tmpfiles.d/` | Cron job with CLI args | Cron job + `/etc/tmpreaper.conf` |
| **Scheduling** | systemd timer (`systemd-tmpfiles-clean.timer`) | Cron (manual setup) | Cron (manual setup) |
| **Age Criteria** | Access time, modification time, change time | Access time only | Access time only |
| **Symlink Safety** | Safe (does not follow symlinks) | Safe (checks for symlinks) | Safe (skips symlinks by default) |
| **Exclusion Patterns** | Glob patterns in config | CLI `-x` / `-X` flags | Config file exclusions |
| **Dry Run** | `--dry-run` flag | `--test` flag | `--test` flag |
| **Verbose Mode** | `--verbose` flag | `--verbose` flag | `--verbose` flag |
| **Size-based Cleanup** | No (age only) | Yes (`--all` removes empty dirs) | Yes (removes empty dirs) |
| **SELinux Aware** | Yes | No | No |
| **Docker Support** | Yes (container image) | Manual install | Manual install |

## systemd-tmpfiles — The Modern Default

**systemd-tmpfiles** is part of the systemd suite and is the default temp file manager on virtually all systemd-based distributions. It manages not only `/tmp` and `/var/tmp` but also creates runtime directories, sets permissions, and handles FIFO/socket creation.

### How It Works

systemd-tmpfiles reads configuration files from three locations (in order of precedence):
1. `/usr/lib/tmpfiles.d/` — Package defaults
2. `/run/tmpfiles.d/` — Runtime overrides
3. `/etc/tmpfiles.d/` — Administrator customizations

Each `.conf` file contains directives with this format:
```
Type Path Mode UID GID Age Argument
```

### Default Configuration

The default temp cleanup rules are in `/usr/lib/tmpfiles.d/tmp.conf`:

```ini
# Clear tmp directories separately, to make them easier to override
d /tmp 1777 root root 10d
d /var/tmp 1777 root root 30d

# Exclude namespace mount points created with PrivateTmp=yes
x /tmp/systemd-private-*
x /var/tmp/systemd-private-*
X /tmp/systemd-private-*/tmp
X /var/tmp/systemd-private-*/tmp
```

Directive types:
- **`d`**: Create directory if it doesn't exist; clean contents older than Age
- **`x`**: Exclude path from cleanup (globs supported)
- **`X`**: Exclude path and all contents from cleanup
- **`f`**: Create file (truncate if exists)
- **`w`**: Write to file (append)
- **`r`**: Remove file or directory
- **`R`**: Recursively remove directory

### Custom Configuration

Create `/etc/tmpfiles.d/custom-cleanup.conf`:

```ini
# Clean application cache older than 7 days
d /var/cache/myapp 0755 myapp myapp 7d

# Clean old session files older than 1 day
d /var/lib/sessions 0750 www-data www-data 1d

# Remove old upload files older than 3 days
d /var/www/uploads 0755 www-data www-data 3d

# Never clean these directories
x /var/lib/important-data
x /opt/persistent-cache
```

### Manual Execution and Scheduling

```bash
# Run cleanup manually (all configs)
sudo systemd-tmpfiles --clean

# Run cleanup for specific config only
sudo systemd-tmpfiles --clean /etc/tmpfiles.d/custom-cleanup.conf

# Dry run to see what would be deleted
sudo systemd-tmpfiles --clean --dry-run

# Create directories (without cleaning)
sudo systemd-tmpfiles --create

# Check timer status
systemctl status systemd-tmpfiles-clean.timer

# Enable automatic cleanup (usually enabled by default)
sudo systemctl enable --now systemd-tmpfiles-clean.timer

# View timer schedule
systemctl cat systemd-tmpfiles-clean.timer
```

The default timer runs daily and also triggers on boot:

```ini
# /usr/lib/systemd/system/systemd-tmpfiles-clean.timer
[Timer]
OnBootSec=15min
OnUnitActiveSec=1d
```

### Docker Deployment

```yaml
version: "3.8"
services:
  tmpfiles-cleaner:
    image: alpine:latest
    volumes:
      - /tmp:/tmp
      - /var/tmp:/var/tmp
      - ./tmpfiles.d:/etc/tmpfiles.d:ro
    command: |
      apk add --no-cache systemd-libs &&
      systemd-tmpfiles --create --clean
    restart: "no"
```

## tmpwatch — The Red Hat Classic

**tmpwatch** is the traditional temp file cleanup utility from Red Hat. It is simpler than systemd-tmpfiles but highly effective for straightforward cleanup needs. It is available on RHEL, CentOS, and Fedora (though systemd-tmpfiles is now preferred).

### Installation

```bash
# RHEL/CentOS/Fedora
sudo dnf install tmpwatch

# Or from source
git clone https://pagure.io/tmpwatch.git
cd tmpwatch
./configure
make
sudo make install
```

### Usage

tmpwatch is typically run via cron. The basic syntax:

```bash
tmpwatch [options] <max-age> <directories...>
```

Common options:
- **`-a`**: Use access time for age calculation (default)
- **`-m`**: Use modification time instead
- **`-c`**: Use ctime (inode change time)
- **`-u`**: Update access time on directories being scanned
- **`-d`**: Remove empty directories
- **`-x /path`**: Exclude a specific path
- **`-X /path`**: Exclude paths matching a pattern
- **`--test`**: Dry run (show what would be deleted)
- **`-v`**: Verbose output
- **`-f`**: Force removal of files owned by other users

### Cron Configuration

Create `/etc/cron.daily/tmpwatch`:

```bash
#!/bin/sh
# Clean /tmp - remove files not accessed for 10 days
/usr/sbin/tmpwatch --test 240 /tmp

# Clean /var/tmp - remove files not accessed for 30 days
/usr/sbin/tmpwatch --test 720 /var/tmp

# Clean /var/cache - remove files not accessed for 7 days
/usr/sbin/tmpwatch -a -d 168 /var/cache

# Clean /var/spool/cups - remove files older than 12 hours
/usr/sbin/tmpwatch 12 /var/spool/cups
```

Make executable:
```bash
sudo chmod +x /etc/cron.daily/tmpwatch
```

### Advanced Examples

```bash
# Remove files in /tmp not accessed in 10 days, excluding .X11-unix
tmpwatch -a 240 --exclude=/tmp/.X11-unix /tmp

# Remove empty directories and use modification time
tmpwatch -m -d 48 /var/tmp

# Exclude multiple patterns
tmpwatch -a -d 720 -x /tmp/important -X '/tmp/app-*' /tmp
```

## tmpreaper — The Debian Derivative

**tmpreaper** is a fork of tmpwatch maintained by Debian. It adds several features not found in the original tmpwatch, including configuration file support and safer default behavior.

### Installation

```bash
# Debian/Ubuntu
sudo apt install tmpreaper
```

### Configuration

tmpreaper uses a configuration file at `/etc/tmpreaper.conf`:

```bash
# Enable tmpreaper (must be set to "yes")
SHOWWARNING=true

# Directories to clean
# Space-separated list
TIMETOCLEAN="10d"
EXCLUDEDIRS="/tmp/.X11-unix /tmp/.ICE-unix /tmp/.font-unix"

# Use access time (default) or modification time
# "atime" or "mtime"
TIME="atime"

# Additional options
ADDOPTIONS="--test"

# Don't remove files newer than this
DONTDELETEMINAGE="0"
```

### Running tmpreaper

```bash
# Manual run
sudo tmpreaper 10d /tmp

# Dry run
sudo tmpreaper --test 10d /tmp

# Verbose mode
sudo tmpreaper --verbose 10d /tmp

# Using configuration file settings
sudo /etc/cron.daily/tmpreaper
```

### Cron Configuration

tmpreaper installs its own cron job at `/etc/cron.daily/tmpreaper`:

```bash
#!/bin/sh
# tmpreaper cron job - runs daily

# Read configuration
. /etc/tmpreaper.conf

# Run cleanup
tmpreaper $TIMETOCLEAN /tmp /var/tmp
```

## Comparing Configuration Approaches

| Approach | systemd-tmpfiles | tmpwatch | tmpreaper |
|----------|-----------------|----------|-----------|
| **Config location** | `/etc/tmpfiles.d/*.conf` | CLI args in cron script | `/etc/tmpreaper.conf` |
| **Config syntax** | Structured (Type Path Mode UID GID Age) | Shell script with CLI flags | Shell-style config file |
| **Multiple directories** | Multiple config files or directives | Multiple CLI args | Space-separated in config |
| **Exclusions** | `x` / `X` directives | `-x` / `-X` flags | `EXCLUDEDIRS` variable |
| **Declarative vs imperative** | Declarative (desired state) | Imperative (run and clean) | Imperative (run and clean) |
| **Idempotent** | Yes (safe to run repeatedly) | Yes | Yes |

## Why Self-Host Temp File Management?

Running your own temp file cleanup gives you precise control over what gets removed and when. Third-party cloud services or managed hosting often use aggressive cleanup policies that can delete files your applications still need, or conversely, never clean up at all, leading to disk exhaustion.

**Predictable behavior**: With self-hosted temp management, you define exactly which directories are cleaned, how old files must be before removal, and what patterns are excluded. systemd-tmpfiles' declarative configuration means the cleanup behavior is version-controlled and auditable. For teams managing multiple servers, this consistency prevents "it worked on staging but not production" incidents caused by different cleanup policies.

**Compliance and data retention**: Some industries require that temporary files containing sensitive data be deleted within a specific timeframe. Self-hosted management with explicit age policies (e.g., "delete all files in `/var/cache/credentials` older than 1 hour") ensures compliance without manual intervention.

**Storage optimization**: For disk usage monitoring and capacity planning, see our [disk usage analyzer comparison](../2026-05-08-dust-vs-ncdu-vs-dua-self-hosted-disk-usage-analyzers/). Effective temp file management is a prerequisite for accurate disk usage analysis — stale temp files distort storage metrics and waste valuable space. For automated storage cleanup workflows, our [ZFS snapshot management guide](../2026-05-20-self-hosted-zfs-snapshot-management-sanoid-zrepl-zfs-auto-snapshot-guide/) shows how to combine scheduled cleanup with snapshot retention policies. For server hardware monitoring and health tracking, our [bare metal monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/) complements filesystem management with hardware-level oversight.

## Choosing the Right Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| **systemd-based distro** | systemd-tmpfiles (already integrated) |
| **Debian/Ubuntu server** | tmpreaper (native package, safer defaults) |
| **RHEL/CentOS legacy** | tmpwatch (traditional, well-tested) |
| **Declarative config needed** | systemd-tmpfiles (Type/Path/Mode format) |
| **Simple cron-based cleanup** | tmpwatch (single command, easy cron) |
| **Container environments** | systemd-tmpfiles (lightweight, no cron needed) |
| **Migration from tmpwatch** | tmpreaper (compatible, enhanced features) |

## FAQ

### What is the difference between `/tmp` and `/var/tmp`?

Both are temporary directories, but they serve different purposes. `/tmp` is for short-lived temporary files — application scratch space, session files, and caches that are only needed during a single boot session. Files in `/tmp` are typically cleaned after 10 days (or on reboot). `/var/tmp` is for temporary files that should persist across reboots — files that a process needs to survive a restart but still have a limited lifetime. Files in `/var/tmp` are typically cleaned after 30 days. The distinction matters: a database recovery file belongs in `/var/tmp` (survive reboot), while a render scratch file belongs in `/tmp` (gone after reboot).

### Why does systemd-tmpfiles use "Age" instead of a simple file age?

The Age field in systemd-tmpfiles directives specifies the maximum age before a file is eligible for cleanup. But systemd-tmpfiles checks three timestamps: access time (atime), modification time (mtime), and change time (ctime). A file is only cleaned if ALL three timestamps are older than the specified age. This prevents accidental deletion of files that are still being accessed (even if their content hasn't changed). tmpwatch and tmpreaper, by contrast, typically check only access time.

### Can I use systemd-tmpfiles to clean directories other than `/tmp`?

Yes. The `d` directive works for any directory. Create a custom config in `/etc/tmpfiles.d/` with entries for your application directories:

```ini
# Clean old application logs
d /var/log/myapp 0755 myapp myapp 14d

# Clean old upload files
d /var/www/uploads 0755 www-data www-data 3d

# Clean old PDF exports
d /var/spool/exports 0755 exporter exporter 1d
```

Run `sudo systemd-tmpfiles --create --clean` to apply.

### What happens if tmpreaper or tmpwatch tries to delete a file that is still open?

Both tools check for open files before deletion. If a file is still open by a running process, it will NOT be deleted — the filesystem keeps the inode alive until all file descriptors are closed. However, the directory entry (filename) is removed, so the file becomes invisible to new processes. This is generally safe but can lead to "ghost" disk usage where `df` shows high usage but `du` cannot account for it. Restarting the holding process releases the space.

### How do I test my cleanup configuration before enabling it?

All three tools support dry-run mode:

```bash
# systemd-tmpfiles
sudo systemd-tmpfiles --clean --dry-run

# tmpwatch
tmpwatch --test 240 /tmp

# tmpreaper
sudo tmpreaper --test 10d /tmp
```

Dry-run mode lists every file that WOULD be deleted without actually removing anything. Always run this after changing configuration to verify the cleanup scope is correct.

### Can I exclude specific file patterns from cleanup?

Yes. With systemd-tmpfiles, use the `x` directive for exact paths or globs:

```ini
x /tmp/.X11-unix
x /tmp/myapp-*
x /var/tmp/important-data
```

With tmpwatch, use `-x` for exact paths and `-X` for shell glob patterns:

```bash
tmpwatch -a -d -x /tmp/.X11-unix -X '/tmp/myapp-*' 240 /tmp
```

With tmpreaper, add paths to `EXCLUDEDIRS` in `/etc/tmpreaper.conf`:

```bash
EXCLUDEDIRS="/tmp/.X11-unix /tmp/.ICE-unix /tmp/myapp-*"
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Temp File Management: systemd-tmpfiles vs tmpwatch vs tmpreaper (2026)",
  "description": "Compare three Linux temp file cleanup solutions: systemd-tmpfiles, tmpwatch, and tmpreaper. Configure automated stale file removal for self-hosted Linux servers.",
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
