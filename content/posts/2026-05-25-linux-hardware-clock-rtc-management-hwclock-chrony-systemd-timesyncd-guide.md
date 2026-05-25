---
title: "Self-Hosted Linux Hardware Clock (RTC) Management: hwclock vs chrony vs systemd-timesyncd"
date: "2026-05-25"
tags: ["linux", "time-synchronization", "system-administration", "rtc", "hardware-clock"]
draft: false
---

Managing accurate time on Linux servers requires synchronizing both the system clock and the hardware real-time clock (RTC). While NTP daemons handle network time synchronization, the hardware clock persists across reboots and power cycles. Choosing the right tool for RTC management is critical for servers that need reliable timekeeping, audit logging compliance, and consistent timestamps across distributed systems.

This guide compares three approaches to hardware clock management on Linux: the traditional `hwclock` utility, `chrony` with its built-in RTC sync, and `systemd-timesyncd` with `systemd-timedated`. We cover installation, configuration, Docker deployment considerations, and best practices for production environments.

## Understanding the Linux Hardware Clock (RTC)

Linux systems maintain two clocks: the **system clock** (kernel-managed, resets on boot) and the **hardware clock** (RTC, battery-backed, persists across reboots). When a Linux system boots, it reads the hardware clock to initialize the system clock. During shutdown, the system clock is typically written back to the RTC.

The relationship between these clocks is managed by user-space tools. If the hardware clock drifts significantly, rebooted servers start with incorrect time, which can cause:

- **Authentication failures** — Kerberos and OAuth tokens are time-sensitive
- **Log corruption** — Timestamps become unreliable for incident investigation
- **Certificate validation errors** — TLS certificates may appear expired or not-yet-valid
- **Distributed system inconsistencies** — Database replication and cluster consensus depend on synchronized time

The hardware clock typically drifts 1-5 seconds per day depending on the motherboard's oscillator quality. Server-grade hardware with temperature-compensated oscillators (TCXO) drifts less than consumer boards.

## Tool Comparison Overview

| Feature | hwclock | chrony (rtc sync) | systemd-timesyncd + timedated |
|---------|---------|-------------------|-------------------------------|
| Package | util-linux | chrony | systemd |
| Type | CLI utility | NTP daemon with RTC support | NTP client + D-Bus daemon |
| RTC Sync | Manual or cron-triggered | Automatic after NTP sync | Via timedatedctl (manual) |
| Drift Compensation | Basic (uses /etc/adjtime) | Advanced (tracks drift rate) | None (relies on NTP) |
| Hardware Support | Universal (any RTC) | Universal | Universal |
| NTP Integration | None (standalone) | Built-in (same daemon) | Separate daemon + timedated |
| Configuration | /etc/default/hwclock | /etc/chrony/chrony.conf | /etc/systemd/timesyncd.conf |
| Daemon Required | No | Yes | Yes |
| Complexity | Low | Medium | Low |
| Best For | Simple servers, containers | Production servers, precision | Desktop, lightweight servers |

## hwclock: The Traditional Approach

`hwclock` is part of the `util-linux` package and has been the standard Linux hardware clock tool since the early days. It provides direct access to the RTC device (`/dev/rtc` or `/dev/rtc0`).

### Installation

`hwclock` comes pre-installed on virtually all Linux distributions as part of `util-linux`:

```bash
# Verify hwclock is available
hwclock --version

# On minimal containers, install util-linux
# Debian/Ubuntu
apt-get update && apt-get install -y util-linux

# RHEL/CentOS/Rocky
dnf install -y util-linux

# Alpine
apk add util-linux
```

### Reading and Setting the Hardware Clock

```bash
# Display hardware clock time
hwclock --show

# Display hardware clock with verbose RTC access info
hwclock --show --verbose

# Set hardware clock from system clock
hwclock --systohc

# Set system clock from hardware clock
hwclock --hctosys

# Set hardware clock to a specific time
hwclock --set --date "2026-05-25 14:30:00"
```

### Configuring Automatic RTC Sync

The most common production setup uses a cron job or systemd timer to periodically sync the hardware clock:

```bash
# Create a systemd timer for hourly RTC sync
cat > /etc/systemd/system/hwclock-sync.timer << 'EOF'
[Unit]
Description=Hourly Hardware Clock Synchronization

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/hwclock-sync.service << 'EOF'
[Unit]
Description=Synchronize Hardware Clock

[Service]
Type=oneshot
ExecStart=/sbin/hwclock --systohc --utc
EOF

systemctl enable --now hwclock-sync.timer
```

### hwclock Docker Deployment

For containers that need RTC access, mount the RTC device:

```yaml
version: "3.8"
services:
  hwclock-sync:
    image: alpine:latest
    volumes:
      - /dev/rtc:/dev/rtc
      - /etc/localtime:/etc/localtime:ro
    cap_add:
      - SYS_TIME
    command: >
      sh -c "apk add --no-cache util-linux &&
             while true; do
               hwclock --systohc --utc;
               sleep 3600;
             done"
    restart: unless-stopped
```

## chrony: NTP Daemon with Built-in RTC Sync

`chrony` is a modern NTP implementation that includes automatic hardware clock synchronization as a core feature. It tracks system clock drift and automatically compensates for RTC inaccuracy.

### Installation

```bash
# Debian/Ubuntu
apt-get update && apt-get install -y chrony

# RHEL/CentOS/Rocky
dnf install -y chrony

# Alpine
apk add chrony
```

### Configuring RTC Synchronization

chrony handles RTC sync automatically when the `rtcsync` directive is enabled:

```bash
# Edit chrony configuration
cat > /etc/chrony/chrony.conf << 'EOF'
# NTP servers
pool time.google.com iburst
pool time.cloudflare.com iburst
pool ntp.ubuntu.com iburst

# Record the rate at which the system clock gains/losses time
driftfile /var/lib/chrony/drift

# Allow the system clock to be stepped in the first three updates
makestep 1.0 3

# Enable kernel synchronization of the real-time clock (RTC)
rtcsync

# Serve time to local network (optional)
#local stratum 10

# Log directory
logdir /var/log/chrony
log measurements statistics tracking
EOF

# Enable and start chrony
systemctl enable --now chronyd
```

### Verifying RTC Sync Status

```bash
# Check chrony tracking status
chronyc tracking

# Check if rtcsync is active
chronyc sourcestats

# View RTC offset
chronyc -n sources -v
```

The `rtcsync` directive enables a kernel mode (via `adjtimex` system call) that automatically updates the RTC every 11 minutes when chrony has synchronized the system clock. This is more accurate than manual `hwclock` calls because chrony continuously measures and compensates for drift.

### chrony Docker Deployment

chrony can run in a container to serve time to other containers on the same host:

```yaml
version: "3.8"
services:
  chrony:
    image: ghcr.io/chainguard-bases/chrony:latest
    cap_add:
      - SYS_TIME
    ports:
      - "123:123/udp"
    volumes:
      - ./chrony.conf:/etc/chrony/chrony.conf:ro
      - chrony-data:/var/lib/chrony
    restart: unless-stopped

volumes:
  chrony-data:
```

## systemd-timesyncd: Lightweight NTP Client

`systemd-timesyncd` is a lightweight SNTP client included with systemd. It does not have built-in RTC sync, but works with `systemd-timedated` for hardware clock management.

### Configuration

```bash
# Configure NTP servers
cat > /etc/systemd/timesyncd.conf << 'EOF'
[Time]
NTP=time.google.com time.cloudflare.com
FallbackNTP=ntp.ubuntu.com
#PollIntervalMinSec=32
#PollIntervalMaxSec=2048
EOF

# Enable the service
systemctl enable --now systemd-timesyncd

# Verify sync status
timedatectl status
```

### Hardware Clock Management with timedated

`systemd-timedated` manages the system timezone and RTC setting (UTC vs local time):

```bash
# Set RTC to UTC (recommended for servers)
timedatectl set-local-rtc 0

# Verify RTC mode
timedatectl | grep "RTC in local TZ"

# Manual RTC sync (after NTP has synced)
hwclock --systohc --utc
```

Note: `systemd-timesyncd` itself does not sync the RTC. You still need `hwclock` or a cron job to periodically write the system clock to the hardware clock. For automatic RTC sync, chrony is the better choice.

### systemd-timesyncd Docker Deployment

```yaml
version: "3.8"
services:
  timesyncd:
    image: alpine:latest
    cap_add:
      - SYS_TIME
    volumes:
      - /dev/rtc:/dev/rtc
      - /etc/localtime:/etc/localtime:ro
    command: >
      sh -c "apk add --no-cache chrony &&
             chronyd -f /dev/null -q 'pool time.google.com iburst'"
    restart: on-failure
```

## Choosing the Right RTC Management Tool

| Scenario | Recommended Tool | Reason |
|----------|-----------------|--------|
| Production server with NTP | chrony with rtcsync | Automatic drift compensation, single daemon |
| Minimal container | hwclock + cron | No daemon overhead, periodic sync |
| Desktop/laptop | systemd-timesyncd + hwclock | Lightweight, integrates with systemd |
| VM guest | chrony with rtcsync | Handles time jumps during migration |
| Edge device with intermittent network | chrony with rtcsync | Maintains accuracy during offline periods |
| Kubernetes node | chrony with rtcsync | Precision required for distributed systems |

## Best Practices for Hardware Clock Management

1. **Always set RTC to UTC, not local time** — Use `hwclock --utc` or `timedatectl set-local-rtc 0`. Local time RTC causes issues during DST transitions and with multi-boot systems.

2. **Enable drift tracking** — chrony's `rtcsync` is superior to hwclock's `/etc/adjtime` because it uses kernel-level compensation that continuously adjusts.

3. **Verify after boot** — Add a boot-time check to ensure the hardware clock was read correctly:
   ```bash
   # Add to /etc/rc.local or a systemd service
   echo "Boot time: $(date -u)"
   echo "RTC was: $(hwclock -r --utc)"
   ```

4. **Monitor RTC drift** — Use `chronyc tracking` to see the RTC offset. If drift exceeds 1 second per day, consider replacing the motherboard battery or using an external time source.

5. **Virtual machine considerations** — VM guests should use `chrony` with the `local` directive disabled. Hypervisors often inject time updates that can conflict with NTP. Enable the `chrony` `makestep` directive to handle large time jumps during VM migration.

6. **Container environments** — Containers share the host's system clock and typically cannot access the RTC. Manage hardware clock synchronization at the host level, not within containers.

For NTP server configuration and monitoring, see our [chrony vs NTPsec vs OpenNTPD guide](../2026-05-02-chrony-vs-ntpsec-vs-openntpd-self-hosted-ntp-server-guide/). For precision time synchronization in data centers, check our [Linux PTP servers comparison](../2026-05-10-self-hosted-ptp-servers-linuxptp-chrony-ntpsec-precision-time-sync/). If you need NTP monitoring dashboards, our [chrony exporter guide](../2026-05-11-self-hosted-ntp-monitoring-chrony-exporter-ntpsec-chronyc-dashboard-guide/) covers the tools.

## FAQ

### What is the difference between the system clock and hardware clock in Linux?

The system clock is maintained by the Linux kernel and starts from the hardware clock value at boot. It runs independently and can be adjusted by NTP daemons. The hardware clock (RTC) is a battery-backed chip on the motherboard that keeps time even when the system is powered off. The system clock is more accurate while running, but the hardware clock is essential for correct time after reboot.

### How often should I synchronize the hardware clock?

For most servers, synchronizing the hardware clock once per hour is sufficient. chrony's `rtcsync` feature writes to the RTC approximately every 11 minutes when the system clock is synchronized. For `hwclock`, a systemd timer or cron job running every 1-6 hours works well.

### Why does my hardware clock drift so much?

Hardware clock drift is caused by the quality of the motherboard's crystal oscillator. Typical drift is 1-5 seconds per day. Factors include temperature variations, oscillator age, and motherboard quality. Server boards with TCXO oscillators drift significantly less. chrony's drift compensation can reduce effective drift to under 0.1 seconds per day.

### Should the hardware clock be set to UTC or local time?

Always set the hardware clock to UTC on servers. Use `hwclock --utc` or `timedatectl set-local-rtc 0`. UTC avoids problems during daylight saving time transitions and simplifies multi-timezone server management. Only set to local time on single-boot desktop systems that dual-boot with Windows.

### Can I manage the hardware clock from inside a Docker container?

Containers share the host's system clock and typically cannot write to the RTC device. You need `--cap-add SYS_TIME` and a volume mount for `/dev/rtc`. However, it is better to manage RTC synchronization at the host level. If a container needs time synchronization, run chrony or an NTP client on the host.

### What happens if the hardware clock battery dies?

When the CMOS battery dies, the hardware clock resets to a default date (often 2000-01-01 or the BIOS build date). On next boot, the system clock will be set to this incorrect time. NTP daemons will eventually correct it, but there is a window where timestamps are wrong. Replace the CR2032 battery and verify time after replacement.

### How does chrony's rtcsync work?

chrony's `rtcsync` enables the kernel's `STA_PLL` and `STA_UNSYNC` flags via the `adjtimex` system call. The kernel then automatically updates the RTC approximately every 11 minutes using the current system clock. chrony continuously measures system clock drift and compensates, making the RTC updates more accurate than periodic `hwclock` calls.

## Why Self-Host Time Management?

Accurate timekeeping is foundational to every self-hosted service. Authentication protocols like Kerberos and TOTP-based MFA reject requests when client and server clocks differ by more than a few minutes. TLS certificate validation depends on correct system time — an incorrect clock can make valid certificates appear expired, breaking HTTPS across all your services.

For database replication, especially PostgreSQL logical replication and MySQL group replication, timestamp ordering determines which transactions apply first. Clock skew between database nodes causes replication conflicts and data inconsistency. In Kubernetes clusters, the API server, etcd, and kubelet all require synchronized clocks for leader election and lease renewal.

Self-hosted monitoring systems like Prometheus and Grafana depend on accurate timestamps to correlate metrics across services. When investigating incidents, log timestamps must be reliable to reconstruct event sequences. Hardware clock management ensures that even after unexpected reboots or power outages, your servers resume with correct time.

For complete NTP server setup, see our [NTP server comparison](../2026-05-02-chrony-vs-ntpsec-vs-openntpd-self-hosted-ntp-server-guide/) covering chrony, NTPsec, and OpenNTPD. For advanced monitoring of time synchronization, our [NTP monitoring guide](../2026-05-11-self-hosted-ntp-monitoring-chrony-exporter-ntpsec-chronyc-dashboard-guide/) provides dashboard and alerting setups.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Hardware Clock (RTC) Management: hwclock vs chrony vs systemd-timesyncd",
  "description": "Compare three approaches to Linux hardware clock management: hwclock utility, chrony with rtcsync, and systemd-timesyncd. Includes Docker Compose configs and best practices.",
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
