---
title: "Self-Hosted Firmware OTA Update Management: Eclipse hawkBit vs RAUC vs SWUpdate"
date: "2026-05-07"
tags: ["firmware", "ota", "iot", "embedded", "device-management", "self-hosted"]
draft: false
---

Managing firmware updates across hundreds or thousands of embedded devices is one of the most challenging aspects of IoT deployment. Over-the-Air (OTA) update systems allow you to push firmware images, configuration changes, and security patches to devices remotely, eliminating costly physical visits. While cloud-based OTA services exist, self-hosting your OTA infrastructure gives you full control over update rollouts, device enrollment, and data sovereignty.

In this guide, we compare three leading open-source OTA update management solutions: **Eclipse hawkBit**, **RAUC**, and **SWUpdate**. Each takes a different architectural approach to firmware updates, and understanding their trade-offs helps you build a reliable update pipeline for your device fleet.

## What Is Firmware OTA Management?

Firmware OTA (Over-the-Air) management encompasses the server infrastructure, client agents, and deployment workflows needed to deliver software updates to remote embedded devices. A complete OTA system includes an update server that stores firmware images, a device management interface for scheduling rollouts, a client-side update agent that downloads and applies updates, and a rollback mechanism for handling failed updates.

Self-hosting your OTA server is critical for organizations that manage devices in regulated environments, handle sensitive telemetry data, or operate in air-gapped networks. By keeping the OTA infrastructure on-premises, you maintain full visibility into device status, update history, and firmware distribution patterns.

## Eclipse hawkBit

**Eclipse hawkBit** is a full-featured device management server from the Eclipse Foundation, designed for software update management of IoT devices. It provides a web-based management UI, REST APIs for integration, and support for the DDI (Device Data Integration) protocol that enables communication with device-side update agents.

### Key Features

- **Multi-tenant architecture** — manage multiple device groups and organizations from a single instance
- **Rollout management** — schedule, monitor, and control update campaigns across device fleets
- **Target management** — track device inventory, metadata, and update status
- **Distribution sets** — package firmware images, configuration files, and metadata into deployable bundles
- **Rollout strategies** — forced, voluntary, or time-scheduled updates with error thresholds
- **REST API** — comprehensive API for automation and integration with CI/CD pipelines
- **Spring Boot based** — runs as a standalone JAR or Docker container
- **PostgreSQL and MySQL support** — production-grade database backends

### Deploying hawkBit

hawkBit ships as a Spring Boot application and can be deployed using Docker Compose with a PostgreSQL backend:

```yaml
version: "3.8"
services:
  hawkbit-db:
    image: postgres:16-alpine
    container_name: hawkbit-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: hawkbit
      POSTGRES_USER: hawkbit
      POSTGRES_PASSWORD: hawkbit-secret
    volumes:
      - hawkbit-data:/var/lib/postgresql/data

  hawkbit:
    image: eclipse/hawkbit-update-server:latest
    container_name: hawkbit
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://hawkbit-db:5432/hawkbit
      SPRING_DATASOURCE_USERNAME: hawkbit
      SPRING_DATASOURCE_PASSWORD: hawkbit-secret
      SPRING_JPA_HIBERNATE_DDL_AUTO: update
    depends_on:
      - hawkbit-db

volumes:
  hawkbit-data:
```

Access the hawkBit management UI at `http://your-server:8080` and log in with the default credentials (`admin` / `admin`). In production, change these defaults and configure TLS termination via a reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name ota.example.com;

    ssl_certificate /etc/ssl/certs/ota.crt;
    ssl_certificate_key /etc/ssl/private/ota.key;

    location / {
        proxy_pass http://hawkbit:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### When to Choose hawkBit

Eclipse hawkBit is the best choice when you need a **complete device management server** with a web UI, multi-tenant support, and rollout orchestration. It's particularly suited for organizations managing large device fleets that need centralized control over update scheduling, device grouping, and rollback policies.

## RAUC

**RAUC** (Robust Auto-Update Controller) is a client-side update framework for embedded Linux systems. Unlike hawkBit, RAUC focuses on the device side — it handles the safe installation of updates, manages multiple boot slots (A/B partitioning), and provides rollback capability when an update fails.

### Key Features

- **A/B partition updates** — install updates to an inactive partition, then switch the boot target
- **Atomic updates** — updates either succeed completely or leave the system unchanged
- **Automatic rollback** — if the new system fails to boot, RAUC reverts to the previous slot
- **Castrated update bundles** — cryptographically signed update packages with metadata
- **Custom update handlers** — extensible hooks for pre- and post-install actions
- **D-Bus API** — programmatic control from your device application
- **Cross-platform** — supports ARM, x86, and other embedded architectures
- **Integration with hawkBit** — works with RAUC's hawkBit adapter for server-managed rollouts

### Deploying RAUC on a Device

RAUC is installed on the target device, not on a server. Here is a typical installation and configuration:

```bash
# Install RAUC on the target device
apt-get install rauc

# Create a RAUC configuration file
cat > /etc/rauc/system.conf << 'EOF'
[system]
compatible=my-device-v1

[keyring]
path=/etc/rauc/keys/ca.cert.pem

[slot.bootfs.0]
device=/dev/mmcblk0p1
type=ext4
bootname=system0

[slot.bootfs.1]
device=/dev/mmcblk0p2
type=ext4
bootname=system1
EOF
```

Create a signed update bundle using the RAUC bundle tool:

```bash
# Create bundle manifest
cat > manifest.raucm << 'EOF'
[update]
compatible=my-device-v1
version=2026.05

[image.rootfs]
filename=rootfs.ext4
hooks=install-check

[image.bootfs]
filename=boot.vfat
EOF

# Build the signed bundle
rauc bundle --signing-keyring=/path/to/keys update-bundle-v2026.05.raucb manifest.raucm
```

### When to Choose RAUC

RAUC is the right choice when you need **robust, atomic update installation on the device side**. It excels in environments where update reliability is critical — medical devices, industrial controllers, or any system where a failed update could brick the device. RAUC pairs well with hawkBit (via the RAUC hawkBit adapter) for a complete server-to-device update pipeline.

## SWUpdate

**SWUpdate** is another client-side update framework for embedded Linux, developed as part of the Embedded Linux Conference ecosystem. It provides a flexible update engine that supports multiple update sources (local storage, HTTP, hawkBit server) and various installation strategies.

### Key Features

- **Multiple update sources** — local file, HTTP/HTTPS, hawkBit server, USB
- **Multiple installation modes** — raw copy, image write, file extraction, script execution
- **Dual boot support** — A/B partitioning with automatic fallback
- **Progress reporting** — real-time update progress via HTTP, D-Bus, or UDP
- **Hardware compatibility check** — verify device type before applying updates
- **Post-install hooks** — run custom scripts after successful or failed updates
- **Suricatta daemon** — built-in client for connecting to hawkBit servers
- **Configuration file based** — declarative update rules in INI format

### Deploying SWUpdate

SWUpdate runs as a daemon on the target device. Install and configure it:

```bash
# Install SWUpdate from source
git clone https://github.com/sbabic/swupdate.git
cd swupdate
make defconfig
make

# Configuration file
cat > /etc/swupdate.cfg << 'EOF'
[global]
loglevel = 3
logfile = /var/log/swupdate.log

[scandevices]

[handlers]
LOGLEVEL = "INFO"

[progress]
unencrypted = false
EOF
```

To connect SWUpdate to a hawkBit server, enable the Suricatta daemon:

```ini
[suricatta]
url = http://ota.example.com
id = my-device-001
tenant = DEFAULT
confirm = 1
polling = 300
max_wait = 600
```

Start the SWUpdate service:

```bash
systemctl enable swupdate
systemctl start swupdate
```

### When to Choose SWUpdate

SWUpdate is ideal when you need a **flexible, multi-source update engine** that can pull updates from various sources (local, HTTP, hawkBit). It's particularly useful for heterogeneous device fleets where different device models may receive updates through different channels.

## Comparison Table

| Feature | Eclipse hawkBit | RAUC | SWUpdate |
|---------|----------------|------|----------|
| **Architecture** | Server | Client agent | Client agent |
| **Web Management UI** | Yes | No | No |
| **A/B Partition Support** | No (server) | Yes | Yes |
| **Atomic Updates** | No (server) | Yes | Yes |
| **Automatic Rollback** | No (server) | Yes | Yes |
| **Multi-Tenant** | Yes | N/A | N/A |
| **Rollout Orchestration** | Yes | No | No |
| **hawkBit Integration** | Native | Via adapter | Via Suricatta |
| **Signed Bundles** | No (server) | Yes | Yes |
| **Update Sources** | Server storage | hawkBit | Local, HTTP, hawkBit |
| **GitHub Stars** | 569 | 1,134 | 1,795 |
| **Best For** | Fleet management | Safe device updates | Flexible update engine |

## Why Self-Host Your Firmware OTA Infrastructure?

Running your own OTA update server means **complete control over the update lifecycle**. You decide when updates roll out, which devices receive them, and how failed updates are handled. Cloud-based OTA services introduce latency, data residency concerns, and ongoing subscription costs that compound as your device fleet grows.

Self-hosted OTA systems also **integrate seamlessly with your CI/CD pipeline**. When a firmware build passes testing, it can be automatically uploaded to your hawkBit server, grouped into a rollout campaign, and pushed to a subset of devices for canary testing. This automation is harder to achieve with third-party services that require manual intervention or custom API integrations.

For organizations operating in **regulated industries** (healthcare, automotive, industrial automation), self-hosting OTA infrastructure ensures that firmware images, device telemetry, and update logs remain within your security boundary. This simplifies compliance audits and eliminates the risk of firmware leaks through third-party infrastructure.

For related IoT infrastructure topics, see our [IoT platform comparison](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/) covering device data management and our [MQTT platform guide](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide/) for device messaging. Our [smart home bridges article](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/) covers device connectivity patterns.

## FAQ

### Can I use hawkBit without a device-side agent?

No. hawkBit is a server-only solution — it manages update campaigns and stores firmware images, but it needs a client-side agent (RAUC, SWUpdate with Suricatta, or a custom DDI client) running on each device to download and install updates. The server communicates with agents using the DDI REST API.

### What is the difference between RAUC and SWUpdate?

Both are client-side update frameworks for embedded Linux, but they differ in approach. RAUC focuses on A/B partition management with atomic, signed bundle updates — it's designed for maximum update reliability. SWUpdate offers more flexibility in update sources and installation methods, supporting everything from raw image writes to script-based installations. SWUpdate also includes the Suricatta daemon for hawkBit integration out of the box.

### Do RAUC and SWUpdate work together?

They serve different purposes and can be used independently. However, they both integrate with hawkBit as the server-side component. If you're building a complete OTA pipeline, you would typically use hawkBit as the server and choose either RAUC or SWUpdate as the client agent on your devices.

### How do I handle rollback when an OTA update fails?

Both RAUC and SWUpdate support automatic rollback. RAUC uses A/B partitioning — if the updated system fails to boot, the bootloader automatically falls back to the previous partition. SWUpdate provides similar dual-boot support with configurable fallback behavior. In both cases, the rollback happens at the device level without server intervention.

### Is hawkBit suitable for large device fleets?

Yes. hawkBit is designed for enterprise-scale deployments with multi-tenant support, rollout orchestration, and error thresholds that can pause or cancel campaigns if too many devices fail. The Spring Boot backend scales horizontally, and the PostgreSQL database handles large device inventories. For fleets with tens of thousands of devices, consider deploying hawkBit behind a load balancer with a read replica database.

### How do I secure firmware updates in a self-hosted OTA system?

Use TLS for all communication between devices and the OTA server. Sign firmware bundles with cryptographic keys (RAUC and SWUpdate both support signed bundles). Restrict hawkBit access using authentication and role-based access control. Regularly rotate signing keys and audit update logs for unauthorized access patterns.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Firmware OTA Update Management: Eclipse hawkBit vs RAUC vs SWUpdate",
  "description": "Compare three self-hosted firmware OTA update solutions for IoT device management: Eclipse hawkBit for fleet orchestration, RAUC for atomic A/B partition updates, and SWUpdate for flexible multi-source update delivery.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
