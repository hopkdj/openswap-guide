---
title: "Self-Hosted Linux RAID Health Monitoring: mdadm Monitor vs smartctl vs raid-check Guide"
date: "2026-06-03"
tags: ["linux", "storage", "raid", "monitoring", "system-administration", "hardware"]
draft: false
---

## Introduction

Software RAID (md) is the backbone of self-hosted storage infrastructure, providing redundancy and performance for everything from home NAS devices to enterprise database servers. But RAID arrays don't protect themselves — they need proactive health monitoring to detect failing drives, degraded arrays, and silent data corruption before they cause data loss. This guide compares three essential Linux tools for RAID health monitoring: **mdadm monitor**, **smartctl**, and **raid-check**.

## Tool Comparison

| Feature | mdadm Monitor | smartctl (smartmontools) | raid-check |
|---------|---------------|--------------------------|------------|
| **Purpose** | Array event detection | Disk health prediction | Data integrity verification |
| **Stars** | Part of mdadm (kernel) | 1,160+ | Part of mdadm package |
| **Monitoring Scope** | RAID array state | Individual disk SMART attributes | Array data consistency |
| **Alert Mechanism** | Email / syslog | smartd daemon / email | Cron / email |
| **Detection Speed** | Seconds (events) | Hours/days (trending) | Hours (scrub duration) |
| **Predictive** | No (reactive) | Yes (SMART predicts failure) | No (detects corruption) |
| **Installation** | `apt install mdadm` | `apt install smartmontools` | `apt install mdadm` |

### mdadm Monitor — Real-Time Array Event Detection

The `mdadm --monitor` daemon watches RAID arrays for state changes: disk failures, rebuilds, spare activations, and degraded states. It can send email alerts or execute custom scripts when problems occur.

```bash
# Install mdadm
sudo apt install mdadm

# Start monitoring all arrays in daemon mode
sudo mdadm --monitor --scan --daemonise

# Test monitoring with a test event
sudo mdadm --monitor --scan --test --oneshot

# Configure monitoring in /etc/mdadm/mdadm.conf
# MAILADDR admin@example.com
# MAILFROM mdadm@server.example.com

# Check current array status
cat /proc/mdstat
# Example output:
# md0 : active raid1 sdb1[1] sda1[0]
#       976629440 blocks super 1.2 [2/2] [UU]

# Detailed array information
sudo mdadm --detail /dev/md0
sudo mdadm --detail /dev/md0 | grep -E "State|Active|Working|Failed|Spare"
```

The monitor daemon captures critical events like `Fail`, `FailSpare`, `DeviceDisappeared`, and `RebuildFinished`. Configure it to send alerts through your notification pipeline.

```bash
# Custom alert script
# /etc/mdadm/mdadm.conf:
# PROGRAM /usr/local/bin/mdadm-alert.sh

cat << 'ALERT' | sudo tee /usr/local/bin/mdadm-alert.sh
#!/bin/bash
EVENT="$1" DEVICE="$2"
logger -t mdadm "EVENT=$EVENT on $DEVICE"
echo "RAID alert: $EVENT on $DEVICE at $(date)" | \
  mail -s "RAID ALERT: $EVENT" admin@example.com
ALERT
sudo chmod +x /usr/local/bin/mdadm-alert.sh
```

### smartctl — Predictive Drive Health Monitoring

SMART (Self-Monitoring, Analysis, and Reporting Technology) provides early warning of drive failures through dozens of attributes. `smartctl` reads these attributes, and `smartd` continuously monitors them.

```bash
# Install smartmontools
sudo apt install smartmontools

# Quick health check
sudo smartctl -H /dev/sda
# Expected: "SMART overall-health self-assessment test result: PASSED"

# Full SMART attribute listing
sudo smartctl -A /dev/sda

# Critical attributes to monitor:
sudo smartctl -A /dev/sda | grep -E "Reallocated_Sector|Pending_Sector|Uncorrectable|UDMA_CRC"
# ID#  ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE
# 5    Reallocated_Sector_Ct   0x0033   100   100   010    Pre-fail
# 197  Current_Pending_Sector  0x0012   100   100   000    Old_age
# 198  Offline_Uncorrectable   0x0010   100   100   000    Old_age

# Run a short self-test
sudo smartctl -t short /dev/sda

# Run a long/extended self-test
sudo smartctl -t long /dev/sda

# Check test results
sudo smartctl -l selftest /dev/sda
```

Configure `smartd` for continuous monitoring:

```bash
# /etc/smartd.conf configuration
# Monitor all devices, send mail on errors
sudo tee -a /etc/smartd.conf << 'EOF'
DEVICESCAN -a -o on -S on -s (S/../.././02|L/../../7/03) \
  -m admin@example.com -M exec /usr/local/bin/smartd-alert.sh
EOF

sudo systemctl enable --now smartd
```

Key SMART attributes that predict drive failure: **Reallocated_Sector_Ct** (ID 5), **Current_Pending_Sector** (ID 197), **Offline_Uncorrectable** (ID 198), and **UDMA_CRC_Error_Count** (ID 199). Any non-zero value in the first three warrants immediate attention.

### raid-check — Data Integrity Verification

`raid-check` performs periodic scrubs of RAID arrays, reading every block and verifying parity/mirror consistency. This catches silent data corruption that SMART cannot detect.

```bash
# Check if raid-check is installed (Debian/Ubuntu)
dpkg -l | grep mdadm | grep -q raid-check && echo "Installed" || echo "Not installed"

# Manual check of an array
echo check > /sys/block/md0/md/sync_action

# Monitor check progress
cat /proc/mdstat
# Example: [=====>...............]  check = 25.3% (247372288/976629440)

# Check speed (adjustable)
cat /sys/block/md0/md/sync_speed_max
# Default: 200000 (system default)

# Set faster check speed (KB/s)
echo 500000 | sudo tee /sys/block/md0/md/sync_speed_max

# Automated weekly check via cron
sudo tee /etc/cron.d/raid-check << 'CRON'
# Run RAID data check every Sunday at 1:00 AM
0 1 * * 0 root /usr/share/mdadm/checkarray --cron --all --quiet
CRON
```

For Debian/Ubuntu, the `mdadm` package includes the `checkarray` script:

```bash
# Run check with email notification
sudo /usr/share/mdadm/checkarray --all --quiet

# Check last check date
grep "check" /var/log/syslog | tail -5
```

## Building a Comprehensive RAID Monitoring Pipeline

Using mdadm, smartctl, and raid-check individually provides good coverage, but integrating them into a single monitoring pipeline gives you complete visibility and automated response to storage issues.

### Unified Alerting with a Monitoring Script

Combine all three monitoring sources into a single health check script that runs periodically and reports the overall status:

```bash
#!/bin/bash
# /usr/local/bin/raid-health-check.sh
# Comprehensive RAID health assessment

EXIT_CODE=0
REPORT=""

# 1. Check mdadm array status
echo "=== RAID Array Status ==="
for array in /dev/md*; do
    [ -e "$array" ] || continue
    STATE=$(mdadm --detail "$array" 2>/dev/null | grep "State :" | awk '{print $3}')
    echo "$array: $STATE"
    if [ "$STATE" != "clean" ] && [ "$STATE" != "active" ]; then
        REPORT+="WARNING: $array state is $STATE\n"
        EXIT_CODE=1
    fi
done

# 2. Check SMART status for all member disks
echo -e "\n=== SMART Health ==="
for array in /dev/md*; do
    [ -e "$array" ] || continue
    for disk in $(mdadm --detail "$array" 2>/dev/null | grep "/dev/" | awk '{print $NF}'); do
        HEALTH=$(smartctl -H "$disk" 2>/dev/null | grep "SMART overall-health")
        echo "$disk: $HEALTH"
        if echo "$HEALTH" | grep -q "FAILED"; then
            REPORT+="CRITICAL: $disk SMART health FAILED\n"
            EXIT_CODE=2
        fi
    done
done

# 3. Check last scrub date
echo -e "\n=== Last Data Check ==="
LAST_CHECK=$(grep "check" /var/log/syslog 2>/dev/null | grep -oP "md\d+" | tail -1)
if [ -z "$LAST_CHECK" ]; then
    REPORT+="WARNING: No recent array check found\n"
    EXIT_CODE=1
else
    echo "Last check on $LAST_CHECK"
fi

# Send alert if issues found
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "$REPORT" | mail -s "RAID Health Alert" admin@example.com
fi

exit $EXIT_CODE
```

### Integrating with Prometheus and Grafana

For production environments, export RAID and SMART metrics to Prometheus for dashboard visualization and alerting:

```bash
# Install node_exporter with textfile collector
sudo apt install prometheus-node-exporter

# Create a metrics collection script
cat << 'METRICS' | sudo tee /usr/local/bin/raid-metrics.sh
#!/bin/bash
METRICS_FILE="/var/lib/prometheus/node-exporter/raid.prom"

# Collect mdadm array states
for array in /dev/md*; do
    [ -e "$array" ] || continue
    NAME=$(basename $array)
    STATE=$(mdadm --detail $array 2>/dev/null | grep "State :" | awk '{print $3}')
    ACTIVE=$(mdadm --detail $array 2>/dev/null | grep "Active Devices" | awk '{print $4}')
    WORKING=$(mdadm --detail $array 2>/dev/null | grep "Working Devices" | awk '{print $4}')
    FAILED=$(mdadm --detail $array 2>/dev/null | grep "Failed Devices" | awk '{print $4}')
    
    cat >> "$METRICS_FILE" << EOF
raid_array_state{name="${NAME}",state="${STATE}"} 1
raid_array_active_devices{name="${NAME}"} ${ACTIVE}
raid_array_working_devices{name="${NAME}"} ${WORKING}
raid_array_failed_devices{name="${NAME}"} ${FAILED:-0}
EOF
done

# Collect SMART attributes for all drives
for disk in /dev/sd[a-z] /dev/nvme[0-9]n[0-9]; do
    [ -e "$disk" ] || continue
    DEV=$(basename $disk)
    smartctl -A $disk 2>/dev/null | while read line; do
        ID=$(echo "$line" | awk '{print $1}')
        NAME=$(echo "$line" | awk '{print $2}')
        VALUE=$(echo "$line" | awk '{print $4}')
        [ "$ID" -eq "$ID" ] 2>/dev/null || continue
        echo "smart_attribute{device=\"${DEV}\",id=\"${ID}\",name=\"${NAME}\"} ${VALUE}"
    done >> "$METRICS_FILE"
done
METRICS

sudo chmod +x /usr/local/bin/raid-metrics.sh

# Run every 5 minutes via cron
echo "*/5 * * * * root /usr/local/bin/raid-metrics.sh" | sudo tee /etc/cron.d/raid-metrics
```

### Automated Drive Replacement Workflow

When SMART or mdadm detects a failing drive, a structured response workflow minimizes downtime and data risk:

1. **Detection:** smartd alerts on Reallocated_Sector_Ct > 0 or mdadm reports a Failed device
2. **Isolation:** The failed drive is marked faulty; the array continues operating in degraded mode
3. **Preparation:** Identify the physical drive by serial number (smartctl -i), locate it in the chassis, and procure a replacement
4. **Replacement:** Hot-swap the drive if supported, or schedule maintenance window
5. **Rebuild:** Add the new drive with `mdadm --manage /dev/mdX --add /dev/sdY`; monitor rebuild progress with `cat /proc/mdstat`
6. **Verification:** After rebuild completes, run a full check to verify data integrity

For production servers, keep at least one cold spare drive on hand for each drive model in your arrays. The time between ordering a replacement and installing it is the window where a second drive failure would mean permanent data loss.

## Why Self-Host Your Storage Monitoring

Cloud storage providers handle RAID and drive health transparently — but you get zero visibility. Self-hosting your own storage with proper monitoring gives you data you can act on: SMART attribute trends that predict failures weeks in advance, real-time alerts when a drive drops from the array, and schedule-driven data integrity checks that catch silent corruption before it spreads. Combined, these three tools form a defense-in-depth strategy that cloud abstractions simply cannot match. For more storage management, see our guide on [Linux LVM management](../2026-05-29-self-hosted-linux-lvm-management-lvm2-thin-provisioning-snapshot-tools-guide/). Our [Btrfs snapshot management comparison](../2026-05-26-self-hosted-btrfs-snapshot-management-snapper-timeshift-btrfs-assistant-guide/) covers another layer of data protection. For full filesystem integrity checking, read our [fsck and repair guide](../2026-06-01-linux-filesystem-integrity-check-fsck-xfs-repair-btrfs-guide/).

## FAQ

### How often should I run RAID data checks?

Run a full check (scrub) at least once a month on all arrays. For arrays larger than 4TB, weekly checks are recommended because the scrub duration increases linearly with array size. During a check, the array remains fully operational — performance impact is typically 5-15% depending on your `sync_speed_max` setting. Schedule checks during low-usage windows (e.g., Sunday 1 AM).

### What SMART values indicate an imminent drive failure?

Three counters demand immediate action: **Reallocated_Sector_Ct** > 0 (drive has found and remapped bad sectors), **Current_Pending_Sector** > 0 (sectors that can't be read, pending remap), and **Offline_Uncorrectable** > 0 (permanently unreadable sectors). A drive with any of these above zero should be replaced as soon as practical. Also watch the **Raw_Read_Error_Rate** — an increasing trend, even if below threshold, signals degrading media.

### Can mdadm monitor catch all failure modes?

No, which is why you need all three tools. mdadm monitor catches events that change the array state (disk failures, rebuilds), but it cannot predict failures or detect silent data corruption. A drive with corrupted data that still responds to I/O will not trigger an mdadm event — the data is simply wrong. This is where SMART (predicts failures) and raid-check (detects data corruption) fill the gaps.

### How do I test that my monitoring alerts work?

Simulate failures in a test environment. For mdadm: remove a drive with `mdadm --manage /dev/md0 --fail /dev/sdb1`. Verify you receive an alert, then re-add with `mdadm --manage /dev/md0 --re-add /dev/sdb1`. For smartd: use `smartd -q onecheck` to trigger a one-time check with notification. For raid-check: manually run a check and verify the email notification configured in `/etc/cron.d/raid-check`.

### Can I use these tools with hardware RAID controllers?

Partially. `smartctl` works with most hardware RAID controllers through the `-d` flag (e.g., `-d megaraid,0` for LSI MegaRAID). `mdadm` only monitors Linux software RAID (md) and does not work with hardware RAID. For hardware RAID, use the vendor's management utility — `storcli` for Broadcom/LSI, `hpssacli` for HPE, `perccli` for Dell PERC — which provide equivalent monitoring and alerting capabilities.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux RAID Health Monitoring: mdadm Monitor vs smartctl vs raid-check Guide",
  "description": "Compare mdadm monitor, smartctl (smartmontools), and raid-check for proactive RAID array health monitoring, drive failure prediction, and data integrity verification on self-hosted Linux servers.",
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
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
