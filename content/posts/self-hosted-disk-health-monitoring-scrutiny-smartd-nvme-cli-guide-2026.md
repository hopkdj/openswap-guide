---
title: "Self-Hosted Disk Health Monitoring: Scrutiny vs smartd vs NVMe-cli Guide 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "storage", "monitoring", "hardware"]
draft: false
description: "Compare Scrutiny, smartd, and NVMe-cli for self-hosted disk health monitoring. Complete guide with Docker configs, SMART data analysis, and proactive failure detection."
---

Drive failures don't happen without warning. S.M.A.R.T. (Self-Monitoring, Analysis, and Reporting Technology) attributes track everything from reallocated sectors to temperature spikes — if you know how to read them. The challenge isn't that monitoring tools don't exist; it's that most homelab and small-team setups rely on a single CLI tool with zero historical trends and no alerting pipeline.

This guide compares three self-hosted approaches to disk health monitoring: **Scrutiny** (a web dashboard with historical trend analysis), **smartd** (the tried-and-true SMART daemon from smartmontools), and **NVMe-cli** (the specialized toolset for modern NVMe drives). We'll cover installation, Docker deployment, configuration, and help you decide which tool — or combination — fits your infrastructure.

## Why Self-Host Disk Health Monitoring?

Before diving into the tools, here's why you shouldn't rely on manufacturer utilities or cloud-based monitoring for your drives:

- **Data sovereignty**: SMART data never leaves your network. You're not sending drive health telemetry to third-party servers.
- **Proactive failure detection**: Historical trend analysis catches degrading drives weeks before they fail, giving you time to replace them and restore from backups.
- **No subscription fees**: Enterprise monitoring platforms charge per-device. Self-hosted tools are free and run on a Raspberry Pi or a low-power VPS.
- **Custom alerting**: Route notifications to your existing pipeline — Discord, Slack, Telegram, email, or PagerDuty — without vendor lock-in.
- **NVMe-specific insights**: Modern NVMe drives expose different metrics than SATA drives. Generic tools often miss critical NVMe-specific attributes like media wear percentage and thermal throttling events.

If you're running a NAS, a homelab, or managing bare-metal servers, having visibility into drive health is as important as monitoring CPU and memory. After all, a dead drive is often the single point of failure that takes your entire service stack offline.

## Tool Comparison at a Glance

| Feature | Scrutiny | smartd (smartmontools) | NVMe-cli |
|---|---|---|---|
| **GitHub Stars** | 7,692 | 1,097 | 1,775 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Language** | Go | C++ | C |
| **Web UI** | Yes (built-in) | No (CLI + email) | No (CLI only) |
| **Historical Trends** | Yes (InfluxDB) | No | No |
| **Docker Support** | First-class | Manual (host access) | Manual |
| **SATA Support** | Yes | Yes | Limited |
| **NVMe Support** | Yes (via smartmontools) | Yes | Yes (native) |
| **Alerting** | Multi-channel (Shoutrrr) | Email only | None (manual) |
| **Multi-Host** | Yes (hub/spoke) | Per-host | Per-host |
| **Config Complexity** | Medium | Low | Low |
| **Best For** | Full monitoring stack | Simple daemon alerts | NVMe-specific diagnostics |

## Scrutiny: Web-Based Disk Health Dashboard

**Scrutiny** is the most feature-complete self-hosted disk monitoring solution. It combines smartmontools' data collection with an InfluxDB time-series backend and a polished React web UI, giving you historical graphs, failure threshold analysis, and multi-channel notifications — all from a single Docker container.

The project offers two deployment modes:
- **Omnibus**: Single container with web UI, collector, and InfluxDB bundled together
- **Hub/Spoke**: Separate web + InfluxDB on a central host, with lightweight collectors on each monitored server

### Docker Compose Deployment (Omnibus)

The simplest way to get started is the omnibus image:

```yaml
version: '3.5'

services:
  scrutiny:
    restart: unless-stopped
    container_name: scrutiny
    image: ghcr.io/analogj/scrutiny:nightly-omnibus
    cap_add:
      - SYS_RAWIO
    ports:
      - "8080:8080"    # Web UI
      - "8086:8086"    # InfluxDB admin
    volumes:
      - /run/udev:/run/udev:ro
      - ./config:/opt/scrutiny/config
      - ./influxdb:/opt/scrutiny/influxdb
    devices:
      - "/dev/sda"
      - "/dev/sdb"
      - "/dev/nvme0"
```

For multi-server setups, the hub/spoke architecture runs the collector on each host:

```yaml
version: '2.4'

services:
  influxdb:
    restart: unless-stopped
    image: influxdb:2.8
    ports:
      - '8086:8086'
    volumes:
      - './influxdb:/var/lib/influxdb2'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 5s
      timeout: 10s
      retries: 20

  web:
    restart: unless-stopped
    image: 'ghcr.io/analogj/scrutiny:nightly-web'
    ports:
      - '8080:8080'
    volumes:
      - './config:/opt/scrutiny/config'
    environment:
      SCRUTINY_WEB_INFLUXDB_HOST: 'influxdb'
    depends_on:
      influxdb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
      interval: 5s
      timeout: 10s
      retries: 20

  collector:
    restart: unless-stopped
    image: 'ghcr.io/analogj/scrutiny:nightly-collector'
    cap_add:
      - SYS_RAWIO
    volumes:
      - '/run/udev:/run/udev:ro'
    environment:
      COLLECTOR_API_ENDPOINT: 'http://web:8080'
      COLLECTOR_HOST_ID: 'scrutiny-collector-hostname'
      COLLECTOR_RUN_STARTUP: false
    depends_on:
      web:
        condition: service_healthy
    devices:
      - "/dev/sda"
      - "/dev/nvme0"
```

### Scrutiny Configuration

The `scrutiny.yaml` config file controls the web server, database, and notification channels:

```yaml
version: 1

web:
  listen:
    port: 8080
    host: 0.0.0.0
    basepath: ''
  database:
    location: /opt/scrutiny/config/scrutiny.db

  influxdb:
    host: 0.0.0.0
    port: 8086
    retention_policy: true

log:
  file: ''
  level: INFO

# Notifications via Shoutrrr
notify:
  urls:
    - discord://token@id
    - telegram://token@telegram?chats=-1001234567890
    - gotify://gotify-host/token
    - ntfy://username:password@ntfy.sh/disk-alerts
```

The notification system uses [Shoutrrr](https://shoutrrr.nickfedor.com/services/overview/), which supports Discord, Telegram, Slack, Matrix, SMTP, Gotify, Ntfy.sh, Pushover, PagerDuty, Opsgenie, and more. Usernames and passwords containing special characters must be URL-encoded.

### Key Features

- **Historical trend graphs**: See how Reallocated_Sector_Count, Temperature_Celsius, and Media_Wearout_Indicator change over weeks and months
- **Vendor-specific thresholds**: Scrutiny uses real-world failure data, not just manufacturer specs, to determine drive health status
- **Multi-device passthrough**: Map individual block devices (`/dev/sda`, `/dev/nvme0n1`) into the container for direct SMART access
- **Reverse proxy support**: Configure `basepath` to run behind Traefik, Caddy, or Nginx at a custom URL path
- **REST API**: Query drive status programmatically via `/api/devices` and `/api/summary`

## smartd: The SMART Daemon

**smartd** is the daemon component of the smartmontools project. It's been around since 2002, runs on virtually every Unix-like system, and provides a simple but effective approach: periodically poll SMART attributes and send email alerts when thresholds are crossed.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install smartmontools
```

On RHEL/CentOS:

```bash
sudo dnf install smartmontools
sudo systemctl enable smartd
sudo systemctl start smartd
```

### Configuration

The configuration lives in `/etc/smartd.conf`. Here's a typical setup:

```
# Monitor all SATA and NVMe drives, check every 30 minutes
# -a: all SMART checks (health, attributes, error log, self-test log)
# -o on: automatic offline testing
# -S on: attribute autosave
# -n standby: skip check if drive is in standby (prevent spin-up)
# -m: email recipient for alerts
# -M exec: run custom script on alert (optional)
/dev/sda -a -o on -S on -n standby -m admin@example.com
/dev/sdb -a -o on -S on -n standby -m admin@example.com
/dev/nvme0 -a -n standby -m admin@example.com
```

Run a short self-test daily and a long self-test weekly:

```
# Schedule self-tests
/dev/sda -a -n standby -m admin@example.com \
  -s (S/../.././02|L/../../6/03)
```

This schedules a short test every day at 2:00 AM and a long test every Saturday at 3:00 AM.

### Email Configuration

smartd sends alerts via the system's `mail` command. On a minimal server, you'll need an MTA like Postfix or use a relay:

```bash
# Install a lightweight MTA
sudo apt install postfix
# Configure as "satellite system" pointing to your SMTP relay

# Or use ssmtp/msmtp for simple SMTP forwarding
sudo apt install msmtp msmtp-mta
```

### Pros and Limitations

smartd excels at simplicity: one config file, one daemon, email alerts. It uses virtually no resources and runs on anything from a Raspberry Pi to an enterprise server. However, it lacks historical data visualization, provides no web interface, and email-only alerting doesn't integrate with modern notification platforms without additional scripting.

## NVMe-cli: Native NVMe Drive Management

**NVMe-cli** is the official Linux command-line toolset for NVMe (Non-Volatile Memory Express) drives. While smartmontools can read NVMe SMART data through translation layers, NVMe-cli speaks the NVMe protocol natively, exposing drive-specific features that generic tools can't access.

### Installation

```bash
# Debian/Ubuntu
sudo apt install nvme-cli

# RHEL/CentOS
sudo dnf install nvme-cli

# Arch Linux
sudo pacman -S nvme-cli
```

### Essential Commands

Check overall drive health:

```bash
sudo nvme smart-log /dev/nvme0
```

Sample output:
```
Smart Log for NVME device:nvme0 namespace-id:ffffffff
critical_warning                    : 0
temperature                         : 38 C
available_spare                     : 100%
available_spare_threshold           : 10%
percentage_used                     : 2%
endurance group critical warning summary:
data_units_read                     : 12,847,392
data_units_written                  : 8,234,567
host_read_commands                  : 245,678,901
host_write_commands                 : 189,012,345
power_cycles                        : 127
power_on_hours                      : 14,523
unsafe_shutdowns                    : 3
media_errors                        : 0
num_err_log_entries                 : 0
Warning Temperature Time            : 0
Critical Composite Temperature Time : 0
Thermal Management T1 Trans Count   : 0
Thermal Management T2 Trans Count   : 0
Thermal Management T1 Total Time    : 0
Thermal Management T2 Total Time    : 0
```

List all NVMe devices with detailed information:

```bash
sudo nvme list
# Output: Node  SN                   Model                                    Namespace  Usage                      Format
#         /dev/nvme0n1  S3X1NX0T123456 Samsung SSD 980 PRO 1TB     1          1.00 TB / 1.00 TB    512   B +  0 B
```

Run a drive self-test:

```bash
# Short self-test
sudo nvme device-self-test /dev/nvme0 -s 1

# Extended self-test
sudo nvme device-self-test /dev/nvme0 -s 2

# Check self-test results
sudo nvme self-test-log /dev/nvme0
```

Check firmware version and update:

```bash
sudo nvme id-ctrl /dev/nvme0 | grep -i fw
sudo nvme fw-download /dev/nvme0 -f firmware.bin
sudo nvme fw-commit /dev/nvme0 -s 1 -a 1
```

### Key NVMe Metrics to Monitor

| Metric | What It Means | Warning Threshold |
|---|---|---|
| `percentage_used` | Drive wear level (0-100%) | > 80% |
| `available_spare` | Remaining spare blocks (%) | < 10% |
| `media_errors` | Uncorrectable data errors | > 0 |
| `critical_warning` | Bitmap of critical alerts | Any non-zero value |
| `temperature` | Current drive temperature | > 70°C |
| `unsafe_shutdowns` | Power losses without clean shutdown | > 10 |
| `power_on_hours` | Total operational hours | Track trend |

## Choosing the Right Tool

### Use Scrutiny When:

- You want a **visual dashboard** with historical graphs
- You manage **multiple servers** and need a centralized view
- You want **multi-channel notifications** (Discord, Telegram, Slack)
- You need **vendor-specific failure thresholds** based on real-world data
- You're comfortable running Docker containers

### Use smartd When:

- You want the **simplest possible setup** — one config file, one daemon
- You're on a **resource-constrained system** (smartd uses < 5 MB RAM)
- Email alerts are sufficient for your workflow
- You need to monitor **SATA, SAS, and NVMe** drives on the same host
- You can't run Docker (bare metal, minimal containers)

### Use NVMe-cli When:

- You need **NVMe-specific diagnostics** that smartmontools can't provide
- You want to **update firmware** on NVMe drives
- You're building **custom monitoring scripts** with direct protocol access
- You need to run **namespace management** or format operations
- You want to verify **security features** like TCG Opal self-encryption

### Recommended: Layered Approach

For a production homelab or small team, the best setup combines all three:

1. **Scrutiny** as your primary dashboard for visual monitoring and alerting
2. **smartd** as a lightweight backup daemon that sends email even if Scrutiny is down
3. **NVMe-cli** in a monthly cron job for detailed NVMe diagnostics and firmware checks

```bash
# Monthly NVMe health report via cron
0 4 1 * * /usr/sbin/nvme smart-log /dev/nvme0 >> /var/log/nvme-health.log 2>&1
0 4 1 * * /usr/sbin/nvme smart-log /dev/nvme1 >> /var/log/nvme-health.log 2>&1
```

## Integrating with Your Monitoring Stack

Scrutiny's REST API makes it easy to integrate with existing monitoring platforms. Here are two common patterns:

### Prometheus Exporter Pattern

While Scrutiny doesn't have a native Prometheus exporter, you can use the generic JSON exporter:

```yaml
# docker-compose.yml addition
  scrutiny-exporter:
    image: prom/blackbox-exporter:latest
    command:
      - '--config.file=/etc/blackbox_exporter/config.yml'
    volumes:
      - ./blackbox-config.yml:/etc/blackbox_exporter/config.yml
```

### Grafana Dashboard

Point Grafana directly at Scrutiny's InfluxDB instance:

```yaml
# Add to your docker-compose
  grafana:
    image: grafana/grafana-oss:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - ./grafana-data:/var/lib/grafana
    depends_on:
      - scrutiny
```

Then configure the InfluxDB datasource in Grafana and import the community Scrutiny dashboard templates.

## Troubleshooting Common Issues

### Drives Not Showing in Scrutiny Container

This usually means the device nodes aren't passed through. Add each drive explicitly:

```yaml
devices:
  - "/dev/sda"
  - "/dev/sdb"
  - "/dev/nvme0n1"
```

Also ensure `/run/udev` is mounted read-only for device enumeration.

### smartd Not Sending Email Alerts

Verify the MTA is working:

```bash
echo "test" | mail -s "smartd test" admin@example.com
```

Check smartd's log:

```bash
sudo journalctl -u smartd --since "1 hour ago"
```

### NVMe-cli Permission Denied

NVMe commands require root or the `disk` group:

```bash
sudo usermod -aG disk $USER
# Log out and back in for group changes to take effect
```

For related infrastructure monitoring, check our [GPU monitoring guide with nvtop and netdata](../nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/) and our [NAS solutions comparison covering TrueNAS and OpenMediaVault](../self-hosted-nas-solutions-openmediavault-truenas-rockstor-guide/). If you're also planning your backup strategy, our [encrypted backup comparison](../duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) covers the tools that protect your data once drive failure strikes.

## FAQ

### Does Scrutiny work with hardware RAID controllers?

Scrutiny relies on the Linux kernel's `/dev/sdX` and `/dev/nvmeXnY` device nodes. Hardware RAID controllers that present a single logical volume (e.g., RAID 5 array) will show the virtual drive's SMART data, not individual physical disks. For per-disk monitoring behind a hardware RAID controller, you'll need the controller's management tools (e.g., `storcli` for MegaRAID, `hpssacli` for HP Smart Array) alongside Scrutiny.

### Can smartd monitor NVMe drives?

Yes. Modern versions of smartmontools (7.2+) support NVMe drives. Use the `-d nvme` device type in `/etc/smartd.conf`:

```
/dev/nvme0 -d nvme -a -n standby -m admin@example.com
```

However, NVMe-cli provides more granular NVMe-specific data that smartd cannot access, such as namespace-level metrics and firmware management.

### How often does Scrutiny collect SMART data?

The Scrutiny collector runs on a cron schedule inside the container, collecting SMART data every 12 hours by default. You can adjust this by setting the `COLLECTOR_CRON_SCHEDULE` environment variable. The collector also runs on container startup if `COLLECTOR_RUN_STARTUP` is set to `true`.

### Do I need to pass through every drive device to the Scrutiny container?

Yes. Unlike typical Docker containers, the Scrutiny collector needs direct access to block devices to read SMART data via the `ioctl()` system call. Each drive you want to monitor must be listed under the `devices:` section of your Docker Compose file. If you add a new drive later, update the compose file and restart the container.

### Is Scrutiny safe to run in production?

Scrutiny runs with the `SYS_RAWIO` capability to access raw I/O for SMART data collection, which is a security consideration. The recommended approach is to run Scrutiny on a dedicated monitoring host or in an isolated network segment. The hub/spoke deployment model helps here: the web UI and database run on a separate host from the collectors, which only need the `SYS_RAWIO` capability.

### What happens when a drive's percentage_used reaches 100%?

An NVMe drive at 100% `percentage_used` has exhausted its rated write endurance. This doesn't mean immediate failure — many drives continue operating beyond this point — but the manufacturer's warranty is void and the risk of failure increases significantly. You should plan a replacement and ensure your backup strategy is solid. For comprehensive backup strategies, see our [backup verification guide](../self-hosted-backup-verification-testing-integrity-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Disk Health Monitoring: Scrutiny vs smartd vs NVMe-cli Guide 2026",
  "description": "Compare Scrutiny, smartd, and NVMe-cli for self-hosted disk health monitoring. Complete guide with Docker configs, SMART data analysis, and proactive failure detection.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
