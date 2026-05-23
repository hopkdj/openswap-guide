---
title: "Self-Hosted Linux Filesystem Event Monitoring: systemd.path vs inotifywait vs incron (2026)"
date: "2026-05-24"
tags: ["linux", "systemd", "inotify", "filesystem", "automation", "monitoring", "system-administration"]
draft: false
---

Monitoring filesystem events on Linux servers is essential for automation workflows — triggering actions when files arrive, detecting configuration changes, and reacting to directory updates. Three primary approaches handle this task: **systemd.path** (native systemd path units), **inotifywait** (the inotify-tools CLI utility), and **incron** (inotify-based cron daemon).

Each method has different strengths in configuration complexity, event granularity, daemon requirements, and integration with existing system management. This guide compares all three with real configurations for common server automation scenarios.

## The Filesystem Monitoring Problem

Server automation often requires reacting to filesystem events:

- Process files dropped into an import directory
- Reload configuration when files change
- Trigger backups when specific directories are modified
- Archive logs when they reach a certain size
- Synchronize directories across servers

The traditional approach — polling with cron — wastes resources and introduces latency. Event-driven monitoring reacts instantly and consumes minimal CPU.

## systemd.path: Native Path Unit Monitoring

systemd.path units monitor files and directories using the kernel's inotify mechanism, all managed through systemd's unified unit system. When a path change is detected, systemd can activate a corresponding service unit.

### Key Features

- **No separate daemon** — managed entirely by systemd
- **Unit-based lifecycle** — start, stop, enable, disable like any systemd unit
- **Multiple trigger types** — PathExists, PathChanged, PathModified, DirectoryNotEmpty
- **Service activation** — automatically starts a paired service unit on event
- **Dependency integration** — full systemd dependency and ordering support
- **Credential support** — can pass credentials to triggered services

### Path Unit Configuration

```ini
# /etc/systemd/system/import-monitor.path
[Unit]
Description=Monitor /var/spool/import for new files

[Path]
PathChanged=/var/spool/import
DirectoryNotEmpty=/var/spool/import
Unit=import-processor.service

[Install]
WantedBy=multi-user.target
```

### Corresponding Service Unit

```ini
# /etc/systemd/system/import-processor.service
[Unit]
Description=Process files from import directory
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/process-imports.sh
WorkingDirectory=/var/spool/import
User=appuser
Group=appgroup

[Install]
WantedBy=multi-user.target
```

### Processing Script Example

```bash
#!/bin/bash
# /usr/local/bin/process-imports.sh
set -euo pipefail

IMPORT_DIR="/var/spool/import"
PROCESSED_DIR="/var/spool/import/processed"
LOG_FILE="/var/log/import-processor.log"

mkdir -p "$PROCESSED_DIR"

for file in "$IMPORT_DIR"/*; do
    [ -f "$file" ] || continue
    filename=$(basename "$file")
    echo "$(date '+%Y-%m-%d %H:%M:%S') Processing: $filename" >> "$LOG_FILE"
    
    # Process the file (example: convert CSV to JSON)
    if [[ "$file" == *.csv ]]; then
        python3 -c "
import csv, json, sys
with open(sys.argv[1]) as f:
    reader = csv.DictReader(f)
    data = list(reader)
with open(sys.argv[2], 'w') as f:
    json.dump(data, f, indent=2)
" "$file" "${PROCESSED_DIR}/${filename%.csv}.json"
    fi
    
    mv "$file" "$PROCESSED_DIR/"
    echo "$(date '+%Y-%m-%d %H:%M:%S') Done: $filename" >> "$LOG_FILE"
done
```

### Enabling and Managing

```bash
# Reload systemd configuration
systemctl daemon-reload

# Enable and start the path monitor
systemctl enable --now import-monitor.path

# Check monitor status
systemctl status import-monitor.path

# View all path units
systemctl list-units --type=path

# Manually trigger the service (for testing)
systemctl start import-processor.service
```

### PathExists vs PathChanged vs PathModified

```ini
# Trigger when path first appears (file or directory)
[Path]
PathExists=/etc/myapp/config.yaml

# Trigger when path contents change (any inode change)
[Path]
PathChanged=/var/log/myapp/

# Trigger when file is written to (modification only)
[Path]
PathModified=/etc/myapp/data.json

# Trigger when directory becomes non-empty
[Path]
DirectoryNotEmpty=/var/spool/incoming/
```

### When to Use systemd.path

systemd.path is the best choice for simple file/directory monitoring that triggers systemd services. Its zero-daemon overhead and tight systemd integration make it ideal for server automation tasks.

**Best for**: Drop-directory processing, configuration change detection, simple event-driven service activation.

**Limitations**: Limited to activating systemd services — cannot run arbitrary inline commands. Less granular event types than raw inotify.

## inotifywait: The Flexible CLI Monitor

inotifywait (part of inotify-tools) provides a command-line interface to the Linux inotify subsystem. It watches files and directories and reports events in real time, making it ideal for scripting and pipeline integration.

### Key Features

- **Real-time event streaming** — outputs events as they occur
- **Granular event types** — create, modify, delete, move, access, open, close, and more
- **Recursive monitoring** — watch entire directory trees with `-r`
- **Format control** — customizable output format with `--format`
- **Pipeline-friendly** — designed to work with shell pipelines and loops
- **No daemon required** — run as a foreground process or background job

### Docker Compose Integration

```yaml
version: "3.8"
services:
  file-monitor:
    image: alpine:latest
    container_name: file-monitor
    volumes:
      - /data/watched:/data/watched
      - ./monitor.sh:/usr/local/bin/monitor.sh:ro
    entrypoint: ["/bin/sh", "/usr/local/bin/monitor.sh"]
    restart: unless-stopped
```

### inotifywait Monitoring Script

```bash
#!/bin/bash
# /usr/local/bin/monitor.sh
WATCH_DIR="/data/watched"
LOG_FILE="/var/log/file-monitor.log"

inotifywait -m -r -e create,modify,delete,moved_to     --format '%T %e %w%f' --timefmt '%Y-%m-%d %H:%M:%S'     "$WATCH_DIR" | while read timestamp event filepath; do
    
    echo "$timestamp | $event | $filepath" >> "$LOG_FILE"
    
    # React to specific events
    case "$event" in
        *CREATE*|*MOVED_TO*)
            echo "New file detected: $filepath"
            # Trigger processing
            /usr/local/bin/process-new-file.sh "$filepath" &
            ;;
        *MODIFY*)
            echo "File modified: $filepath"
            ;;
        *DELETE*)
            echo "File deleted: $filepath"
            ;;
    esac
done
```

### Monitoring Configuration Reload

```bash
#!/bin/bash
# Watch a configuration directory and reload services on change
CONFIG_DIR="/etc/myapp"

inotifywait -m -e modify,delete,create     --format '%e %f'     "$CONFIG_DIR" | while read event filename; do
    
    # Skip temporary files and editor swap files
    [[ "$filename" == *~* ]] && continue
    [[ "$filename" == *.swp ]] && continue
    [[ "$filename" == *.tmp ]] && continue
    
    echo "Config change detected: $event on $filename"
    
    # Debounce: wait for all writes to complete
    sleep 2
    
    # Reload the service
    systemctl reload myapp.service
    echo "Service reloaded at $(date)"
done
```

### Event Types Reference

| Event | Description |
|-------|-------------|
| `access` | File was read |
| `modify` | File content was written to |
| `attrib` | File metadata changed (permissions, timestamps) |
| `close_write` | File opened for writing was closed |
| `close_nowrite` | File opened read-only was closed |
| `create` | File/directory created in watched directory |
| `delete` | File/directory deleted from watched directory |
| `moved_from` | File/directory moved out of watched directory |
| `moved_to` | File/directory moved into watched directory |
| `isdir` | Event occurred on a directory |

### When to Use inotifywait

inotifywait is ideal for complex event handling that requires custom scripting logic, event filtering, or pipeline integration. Its real-time streaming model and granular event types give you fine-grained control over event reactions.

**Best for**: Custom event processing pipelines, complex filtering logic, directory synchronization triggers, real-time log monitoring.

**Limitations**: Requires a running process (daemon or background job). No built-in service management — you handle process lifecycle yourself. Recursive monitoring can miss newly created subdirectories.

## incron: The Inotify Cron Daemon

incron (inotify cron) combines inotify event monitoring with cron-like syntax. You define watch rules in a table file, and the incron daemon triggers commands when matching events occur.

### Key Features

- **Cron-like syntax** — familiar table-based configuration
- **Event-to-command mapping** — each watch rule maps to a specific command
- **User-level tables** — each user has their own incrontab
- **Daemon managed** — incron runs as a background daemon
- **Variable substitution** — `$@` (watched path), `$#` (event file), `$%` (event mask)
- **Lightweight** — minimal resource overhead

### incrontab Configuration

```
# incrontab -e (edit user's incrontab)
# Syntax: <path> <mask> <command>

# Process files dropped in import directory
/var/spool/import IN_CREATE,IN_MOVED_TO /usr/local/bin/process-import.sh $#

# Reload Nginx when config changes
/etc/nginx/nginx.conf IN_MODIFY,IN_CLOSE_WRITE /usr/sbin/nginx -t && /usr/sbin/nginx -s reload

# Archive logs when they exceed 100MB
/var/log/app/ IN_MODIFY [ -f /var/log/app/app.log ] && [ $(stat -c%s /var/log/app/app.log) -gt 104857600 ] && /usr/local/bin/archive-log.sh $#

# Sync directory on any change
/data/shared IN_CREATE,IN_MODIFY,IN_DELETE,IN_MOVED_FROM,IN_MOVED_TO /usr/local/bin/sync-to-backup.sh $@
```

### Enabling incron

```bash
# Install incron (Debian/Ubuntu)
apt install incron

# Install incron (RHEL/CentOS)
yum install incron

# Allow users to use incron
echo "root" >> /etc/incron.allow

# Enable and start the daemon
systemctl enable --now incrond

# Edit user's incrontab
incrontab -e

# List current rules
incrontab -l
```

### Sync Script Example

```bash
#!/bin/bash
# /usr/local/bin/sync-to-backup.sh
# Triggered by incron when files change in watched directory
# Usage: sync-to-backup.sh <watched_directory>

SOURCE_DIR="$1"
BACKUP_DIR="/backup/shared"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG="/var/log/sync-monitor.log"

echo "[$TIMESTAMP] Syncing $SOURCE_DIR to $BACKUP_DIR" >> "$LOG"

rsync -az --delete "$SOURCE_DIR/" "$BACKUP_DIR/"
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "[$TIMESTAMP] Sync completed successfully" >> "$LOG"
else
    echo "[$TIMESTAMP] Sync failed with exit code $RESULT" >> "$LOG"
fi
```

### When to Use incron

incron is the right choice when you want cron-like simplicity for filesystem events. Its table-based configuration is easy to manage, and the daemon handles all the complexity of inotify monitoring.

**Best for**: Simple event-to-command mappings, directory synchronization triggers, configuration reload automation.

**Limitations**: Less flexible than inotifywait for complex event processing. No built-in debouncing — rapid events can trigger duplicate commands. Debugging can be difficult since commands run silently in the background.

## Head-to-Head Comparison

| Feature | systemd.path | inotifywait | incron |
|---------|-------------|-------------|--------|
| **Daemon Required** | No (systemd) | No (CLI process) | Yes (incrond) |
| **Configuration** | Unit files | Shell scripts | incrontab table |
| **Event Granularity** | 4 types | 15+ event types | 8 event types |
| **Recursive Watch** | No (single path) | Yes (`-r` flag) | No (single path) |
| **Service Integration** | Full systemd | Manual | Manual |
| **Debouncing** | Built-in | Manual (sleep) | Manual |
| **User Permissions** | System-level | Any user | User tables |
| **Variable Access** | Via service env | Full shell access | `$@`, `$#`, `$%` |
| **Process Management** | systemd handles it | You manage it | incrond handles it |
| **Best For** | Simple service triggers | Complex pipelines | Cron-like rules |

## Common Use Cases and Recommended Approach

### Drop Directory Processing

For processing files dropped into an import directory:

```ini
# systemd.path — recommended for reliability
[Path]
DirectoryNotEmpty=/var/spool/import
Unit=import-processor.service
```

### Configuration Change Detection

For reloading services when config files change:

```bash
# inotifywait — recommended for debouncing control
inotifywait -m -e close_write /etc/myapp/*.conf | while read; do
    sleep 2  # debounce
    systemctl reload myapp
done
```

### Directory Synchronization

For keeping directories in sync:

```
# incron — recommended for simplicity
/data/shared IN_CREATE,IN_MODIFY,IN_DELETE /usr/local/bin/sync.sh $@
```

## Why Self-Host Your Filesystem Monitoring?

Self-hosting filesystem event monitoring gives you complete control over automation triggers, response timing, and error handling. Unlike cloud-based file monitoring services that introduce latency and dependency on external infrastructure, local event monitoring reacts instantly and works offline.

For teams managing self-hosted infrastructure — from homelab automation to enterprise server management — event-driven file monitoring eliminates the polling overhead of cron and enables real-time reactions to filesystem changes.

For systemd management tools, see our [systemd timer management guide](../2026-05-23-self-hosted-linux-temp-file-management-systemd-tmpfiles-tmpwatch-tmpreaper-guide/). For log monitoring, check our [log forwarding with Fluent Bit and Vector guide](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/). For Linux system administration, our [Linux service restart detection guide](../2026-05-22-self-hosted-linux-service-restart-detection-needrestart-checkrestart-debsums-guide/) covers service lifecycle management.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Filesystem Event Monitoring: systemd.path vs inotifywait vs incron (2026)",
  "description": "Compare systemd.path, inotifywait, and incron for Linux filesystem event monitoring and automation. Includes configuration examples and use case recommendations.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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

### Which filesystem monitoring method should I choose?

Use **systemd.path** for simple directory monitoring that triggers systemd services — it requires no additional packages and integrates natively. Use **inotifywait** for complex event processing with custom scripting logic and granular event filtering. Use **incron** for cron-like event-to-command mappings where you prefer table-based configuration.

### Can systemd.path monitor multiple paths?

Yes. A single systemd.path unit can include multiple `PathChanged=`, `PathModified=`, `PathExists=`, and `DirectoryNotEmpty=` lines. All monitored paths trigger the same associated service unit.

### Does inotifywait support recursive directory watching?

Yes, with the `-r` flag. However, inotifywait does not automatically watch newly created subdirectories during a recursive watch. For reliable recursive monitoring, consider using a polling fallback or restarting the watch when new directories appear.

### How do I prevent incron from firing duplicate commands?

incron does not have built-in debouncing. To prevent duplicate triggers, use a lock file in your command script:

```bash
LOCKFILE="/tmp/incron-sync.lock"
[ -f "$LOCKFILE" ] && exit 0
touch "$LOCKFILE"
# Do work
rm -f "$LOCKFILE"
```

### Can I monitor network filesystems (NFS, CIFS) with these tools?

inotify and therefore all three methods work best on local filesystems (ext4, XFS, Btrfs). NFS and CIFS may not support all inotify events reliably. For network filesystem monitoring, consider polling-based alternatives or filesystem-specific monitoring tools.

## Frequently Asked Questions

### What happens if the triggered service fails?

For systemd.path, the service failure is tracked by systemd and visible in `systemctl status`. For inotifywait, the background process handles errors according to your script logic. For incron, command failures are logged to syslog but not automatically retried.

### Do these methods survive system reboots?

systemd.path and incron units/services are persistent — enabled units and incrontab entries survive reboots. inotifywait processes must be managed by systemd, supervisord, or another process manager to restart after reboot.

### How much CPU does filesystem monitoring consume?

All three methods use the kernel's inotify subsystem, which has near-zero CPU overhead when idle. CPU usage only increases when events occur and your processing logic runs. This is dramatically more efficient than polling-based approaches like `while true; do ls; sleep 1; done`.

## Choosing the Right Filesystem Monitoring Tool

The right choice depends on your operational requirements:

- **Use systemd.path** for reliable, daemon-free monitoring that triggers systemd services — ideal for drop-directory processing and configuration reload automation.
- **Use inotifywait** when you need granular event types, recursive directory watching, or complex scripting logic with pipeline integration.
- **Use incron** for simple event-to-command mappings where cron-like table configuration is preferred over writing shell scripts or unit files.

For most server automation tasks, systemd.path provides the best combination of simplicity and reliability. When you need more control over event processing, inotifywait gives you the flexibility to build any monitoring pipeline you need.
