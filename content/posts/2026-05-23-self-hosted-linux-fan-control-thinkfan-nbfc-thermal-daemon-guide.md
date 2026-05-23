---
title: "Self-Hosted Linux Fan Control: thinkfan vs NBFC-Linux vs Intel thermal_daemon"
date: "2026-05-23"
tags: ["fan-control", "linux", "thermal-management", "hardware", "self-hosted"]
draft: false
---

Managing server and laptop temperatures is critical for hardware longevity and performance. While most operating systems ship with basic thermal policies, dedicated fan control daemons offer granular, customizable cooling strategies. This guide compares three popular Linux fan control solutions: **thinkfan**, **NBFC-Linux**, and **Intel thermal_daemon**.

## What Are Linux Fan Control Daemons?

Fan control daemons run as background services on Linux systems, reading temperature sensors from the kernel's hwmon (hardware monitoring) subsystem and adjusting fan speeds via PWM (pulse-width modulation) interfaces. Without proper fan control, servers can overheat under load or waste energy running fans at maximum speed during idle periods.

The Linux kernel exposes temperature sensors through `/sys/class/hwmon/` and fan control interfaces through `/sys/class/thermal/` and `/sys/class/hwmon/hwmon*/pwm*`. Fan control daemons read these values and apply configurable policies — typically step curves or PID control loops — to maintain target temperature ranges.

## thinkfan — Minimalist Fan Control for ThinkPads and Beyond

[thinkfan](https://github.com/vmatare/thinkfan) (695 stars) started as a ThinkPad-specific tool but now supports any Linux system with hwmon sensors. It uses a simple configuration file with temperature thresholds and fan speed percentages.

### Installation

```bash
# Debian/Ubuntu
sudo apt install thinkfan lm-sensors

# Arch Linux
sudo pacman -S thinkfan lm-sensors

# Fedora
sudo dnf install thinkfan lm-sensors
```

### Configuration

thinkfan uses a straightforward threshold-based configuration in `/etc/thinkfan.conf`:

```yaml
# /etc/thinkfan.conf (YAML format, thinkfan ≥ 1.0)
sensors:
  - hwmon: /sys/class/hwmon/hwmon0/temp1_input
  - hwmon: /sys/class/hwmon/hwmon1/temp1_input

fans:
  - hwmon: /sys/class/hwmon/hwmon0/pwm1

levels:
  - [0, 0, 45]      # Fan off below 45°C
  - [1, 30, 55]     # 30% fan speed at 45-55°C
  - [2, 50, 65]     # 50% fan speed at 55-65°C
  - [3, 75, 75]     # 75% fan speed at 65-75°C
  - [7, 70, 32767]  # Full speed above 75°C
```

The configuration maps sensor paths to fan PWM outputs and defines speed levels with hysteresis to prevent fan oscillation at threshold boundaries.

### Starting the Service

```bash
sudo systemctl enable --now thinkfan
journalctl -u thinkfan -f  # Monitor fan control activity
```

## NBFC-Linux — Notebook Fan Control for Multi-Vendor Laptops

[NBFC-Linux](https://github.com/nbfc-linux/nbfc-linux) (734 stars) is a Linux port of the Windows NoteBook FanControl application. It supports a wide range of laptop brands including Acer, ASUS, Dell, HP, Lenovo, MSI, and Toshiba through pre-built configuration profiles.

### Installation

```bash
# From release tarball
wget https://github.com/nbfc-linux/nbfc-linux/releases/latest/download/nbfc-linux-x86_64-linux-gnu.tar.gz
tar xzf nbfc-linux-x86_64-linux-gnu.tar.gz
cd nbfc-linux
sudo make install

# Enable the EC (Embedded Controller) write access
sudo modprobe ec_sys write_support=1
```

### Configuration

NBFC-Linux ships with hundreds of pre-built configs for specific laptop models:

```bash
# List available configs
nbfc config --list

# Apply a config for your model
nbfc config --apply "Acer Predator Helios 300"

# Set manual fan speed (0-100%)
nbfc set 0 50

# Switch back to auto mode
nbfc set 0 -a
```

### Docker Compose Deployment for Monitoring

While NBFC-Linux typically runs directly on the host, you can containerize a monitoring wrapper:

```yaml
version: "3.8"
services:
  fan-monitor:
    image: alpine:latest
    volumes:
      - /sys/class/hwmon:/sys/class/hwmon:ro
      - /sys/class/thermal:/sys/class/thermal:ro
    command: >
      sh -c "
      while true; do
        for f in /sys/class/thermal/thermal_zone*/temp; do
          zone=$$(basename $$(dirname $$f))
          temp=$$(cat $$f)
          echo "$$zone: $$(($$temp / 1000))°C"
        done
        sleep 5
      done
      "
    restart: unless-stopped
```

## Intel thermal_daemon — Intelligent Thermal Management for Intel Platforms

[intel/thermal_daemon](https://github.com/intel/thermal_daemon) (634 stars) is Intel's official thermal management daemon, designed primarily for Intel IA (Intel Architecture) platforms. It uses DPTF (Dynamic Platform and Thermal Framework) to coordinate thermal policies across CPU, GPU, and platform-level cooling.

### Installation

```bash
# Debian/Ubuntu
sudo apt install thermald

# Arch Linux
sudo pacman -S thermald

# Enable with default configuration
sudo systemctl enable --now thermald
```

### Configuration

thermal_daemon uses XML-based thermal zone definitions in `/etc/thermald/thermal-conf.xml`:

```xml
<?xml version="1.0"?>
<ThermalConfiguration>
  <Platform>
    <Name>Custom Server Thermal Profile</Name>
    <ProductName>*</ProductName>
    <Preference>QUIET</Preference>
    <ThermalZones>
      <ThermalZone>
        <Type>cpu_package</Type>
        <TripPoints>
          <TripPoint>
            <SensorType>pkg-temp-0</SensorType>
            <Temperature>75000</Temperature>
            <type>rapl_controller</type>
            <ControlType>SEQUENTIAL</ControlType>
            <CoolingDevice>
              <type>rapl_controller</type>
            </CoolingDevice>
          </TripPoint>
        </TripPoints>
      </ThermalZone>
    </ThermalZones>
  </Platform>
</ThermalConfiguration>
```

For most users, thermal_daemon works effectively with zero configuration — it auto-detects thermal zones and applies conservative thermal policies based on the platform's ACPI tables.

## Comparison Table

| Feature | thinkfan | NBFC-Linux | Intel thermal_daemon |
|---|---|---|---|
| **Stars** | 695 | 734 | 634 |
| **Primary Target** | ThinkPads, generic hwmon | Multi-vendor laptops | Intel IA platforms |
| **Config Format** | YAML (threshold-based) | JSON profiles (per-model) | XML (thermal zones) |
| **Sensor Support** | hwmon, ACPI | Embedded Controller (EC) | DPTF, RAPL, ACPI |
| **Fan Control** | PWM via sysfs | EC register writes | RAPL power capping |
| **Auto-Config** | Manual sensor mapping | Pre-built model profiles | Auto-detect thermal zones |
| **PID Control** | No (threshold only) | No (threshold only) | Yes (adaptive) |
| **GPU Cooling** | Via hwmon | Limited | Via DPTF |
| **Daemon Mode** | systemd service | CLI + systemd service | systemd service |
| **Best For** | ThinkPad owners | Multi-brand laptops | Intel servers/desktops |

## Docker-Based Fan Monitoring Stack

For a production monitoring setup that works alongside any of these tools, deploy a Prometheus-based thermal monitoring stack:

```yaml
version: "3.8"
services:
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.hwmon'
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
```

With `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

## Why Self-Host Your Fan Control?

Running your own fan control daemon rather than relying on BIOS defaults provides several tangible benefits. First, **noise reduction** — most BIOS fan curves prioritize cooling over acoustics, running fans unnecessarily loud at moderate temperatures. A tuned daemon can keep a server library-quiet during idle and light workloads.

Second, **hardware longevity** — constant full-speed fan operation accelerates bearing wear. A properly configured fan curve reduces average RPM, extending fan lifespan by years. For homelab operators running 24/7, this translates to fewer hardware replacements.

Third, **energy savings** — fans consume measurable power. A 120mm server fan at full speed draws 5-12W; across multiple chassis, that adds up. Intelligent fan control can reduce this to 1-3W at idle. For a rack of 10 servers, that is 40-90W saved continuously — roughly 350-790 kWh per year.

Fourth, **thermal optimization per workload** — different workloads generate different heat profiles. A database server with bursty I/O needs different fan behavior than a continuously-compiling build server. Custom fan curves match cooling to actual usage patterns.

For **bare-metal hardware monitoring** that complements fan control, see our [bare-metal hardware monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/). If you need [GPU-specific thermal monitoring](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/), that comparison covers nvtop, DCGM-Exporter, and Netdata. For complete [Linux hardware inventory](../2026-05-23-self-hosted-linux-hardware-inventory-dmidecode-lshw-hwinfo-guide/), dmidecode, lshw, and hwinfo provide the sensor discovery data you need.

## FAQ

### Which fan control tool should I use for my ThinkPad?

For ThinkPads, **thinkfan** is the most mature and widely-used option. It integrates directly with the ThinkPad ACPI interface and has been bundled in major Linux distributions for years. If your model is supported by NBFC-Linux, that tool offers more granular per-fan control, but thinkfan's simplicity makes it the default recommendation.

### Can NBFC-Linux work on desktop servers?

NBFC-Linux is primarily designed for laptops because it communicates with the Embedded Controller (EC) chip found in portable systems. Most desktop motherboards do not have an EC in the same configuration. For desktop servers, use **thinkfan** (with hwmon sensors) or **thermal_daemon** (with DPTF/RAPL interfaces).

### Does thermal_daemon work on AMD processors?

thermal_daemon is Intel-specific — it relies on DPTF (Dynamic Platform and Thermal Framework) and RAPL (Running Average Power Limit), which are Intel technologies. For AMD systems, use **thinkfan** with hwmon sensor paths, or the kernel's built-in `amd-pstate` driver with the `schedutil` CPU frequency governor.

### How do I find my temperature sensor paths for thinkfan?

Use `sensors-detect` from the lm-sensors package to discover all available sensors:

```bash
sudo sensors-detect  # Answer YES to all prompts
sudo systemctl restart lm-sensors
sensors              # Lists all detected sensors and temperatures
```

The sensor paths will appear under `/sys/class/hwmon/hwmon*/temp*_input`.

### Is it safe to let fans stop completely at low temperatures?

For laptop fans, yes — most ThinkPad BIOS designs allow the fan to stop entirely below a threshold (typically 45-50°C). For server chassis fans, running at a minimum of 10-20% is recommended to maintain positive air pressure and prevent dust accumulation. Configure your lowest threshold to a non-zero speed for server fans.

### Can I run multiple fan control daemons simultaneously?

No — running multiple fan control daemons causes conflicts as they compete to write to the same PWM sysfs files. Choose one daemon per system. If you need features from multiple tools, use thermal_daemon for Intel power capping combined with thinkfan for chassis fan control, but ensure they manage different fan PWM outputs.

### How does Docker hwmon monitoring relate to fan control?

Docker containers with `--device` access to hwmon interfaces can read temperature sensors but should not write to PWM controls — fan control should remain on the host. The Docker monitoring stack shown above reads sensors via node-exporter for visualization, while the fan daemon on the host manages actual speed control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Fan Control: thinkfan vs NBFC-Linux vs Intel thermal_daemon",
  "description": "Compare three Linux fan control daemons for self-hosted thermal management: thinkfan for ThinkPads, NBFC-Linux for multi-vendor laptops, and Intel thermal_daemon for IA platforms.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
