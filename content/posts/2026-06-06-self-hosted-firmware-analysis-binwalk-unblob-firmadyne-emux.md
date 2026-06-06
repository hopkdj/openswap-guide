---
title: "Self-Hosted Firmware Analysis Platforms: Binwalk vs unblob vs Firmadyne vs EMUX"
date: "2026-06-06"
tags: ["firmware-analysis", "reverse-engineering", "iot-security", "cybersecurity", "embedded-systems", "binary-analysis"]
draft: false
---

## Introduction

Every IoT device, router, and embedded system ships with firmware — a binary blob that contains the operating system, applications, and configuration of the device. For security researchers, penetration testers, and embedded developers, analyzing firmware is essential for vulnerability discovery, supply chain verification, and understanding how devices actually work. Self-hosted firmware analysis platforms let you extract, dissect, and emulate device firmware in a controlled lab environment — no cloud dependency, no data exfiltration risk.

In this guide, we compare four leading open-source firmware analysis tools: **Binwalk** (the industry-standard firmware extraction tool, rewritten in Rust), **unblob** (a modern, high-performance firmware extractor), **Firmadyne** (a full-system emulation platform for dynamic analysis), and **EMUX** (a lightweight ARM/MIPS emulation framework). We cover installation, Docker deployment, key features, and which tool to use for different analysis scenarios.

## How Firmware Analysis Works

Firmware analysis typically follows a pipeline:

1. **Acquisition** — Obtain the firmware image (from vendor downloads, device extraction via UART/JTAG, or OTA capture)
2. **Unpacking** — Extract the filesystem(s) from the binary blob. This is where Binwalk and unblob excel.
3. **Static Analysis** — Examine binaries, configuration files, and scripts without executing them
4. **Dynamic Analysis** — Run the firmware in an emulated environment to observe runtime behavior. This is Firmadyne and EMUX's territory.
5. **Reporting** — Document vulnerabilities, hardcoded credentials, and security issues

Each tool in this comparison specializes in different stages of this pipeline.

## Tool Comparison

| Feature | Binwalk | unblob | Firmadyne | EMUX |
|---------|---------|--------|-----------|------|
| **GitHub Stars** | 14,017 | 2,516 | 2,075 | 861 |
| **Language** | Rust | Python | Shell/Python | Python |
| **Extraction Method** | Signature-based carving | Multi-tool extraction pipeline | Archive extraction + NBD mount | Manual binary loading |
| **Filesystem Support** | SquashFS, JFFS2, YAFFS, CramFS, ext2/3/4 | 40+ formats via extractors | ext2/3/4, SquashFS | ext2/3/4, FAT |
| **Emulation** | No | No | QEMU system-level emulation | QEMU user-mode + system-mode |
| **Web Interface** | No (CLI only) | No (CLI only) | No (CLI + SSH) | Yes (embedded web console) |
| **Architecture Support** | All (entropy analysis) | All (via extractors) | ARM, MIPS (little-endian) | ARM, MIPS, MIPSEL |
| **NVRAM Simulation** | No | No | Yes (libnvram) | Yes (custom hooks) |
| **Docker Support** | Yes | Yes | Yes | Yes (recommended) |
| **Last Update** | May 2026 | June 2026 | July 2024 | August 2025 |

## Binwalk: The Industry Standard

Binwalk is the most widely-used firmware analysis tool with over 14,000 GitHub stars. Originally written in Python, it was completely rewritten in Rust for version 3.0+, bringing significant performance improvements for large firmware images. It uses entropy analysis and magic byte signatures to identify and extract embedded filesystems, compressed data, and executable code.

**Key Strengths:**
- Fast entropy-based file carving — can find filesystems even in obfuscated firmware
- Extensive signature database covering hundreds of file formats
- Recursive extraction (extract files within extracted filesystems)
- Plugin architecture for custom analysis modules
- Binary diffing capabilities

**Setting Up Binwalk with Docker:**

```bash
# Build the Docker image
git clone https://github.com/ReFirmLabs/binwalk.git
cd binwalk
./build_docker.sh

# Run firmware extraction
docker run --rm -v $(pwd)/firmware:/firmware binwalk \
  binwalk -Me /firmware/router_firmware.bin

# The -M flag performs recursive extraction
# -e extracts known file types automatically
```

**Docker Compose for a Persistent Lab:**

```yaml
version: "3.8"
services:
  binwalk:
    image: binwalk:latest
    container_name: firmware-binwalk
    volumes:
      - ./firmware:/firmware
      - ./output:/output
    entrypoint: ["/bin/bash"]
    stdin_open: true
    tty: true
```

## unblob: The Modern Alternative

unblob takes a different approach from Binwalk's signature-based carving. Instead of reimplementing extraction logic, it acts as an orchestrator — dispatching to specialized extractors for each format. This means it supports over 40 filesystem and compression formats without maintaining its own extraction code. When a new filesystem format emerges, unblob can support it by simply adding the appropriate extractor.

**Key Strengths:**
- Extraction pipeline architecture — uses specialized tools for each format (7zip, sasquatch, ubireader, etc.)
- Comprehensive format coverage: 40+ formats including Android sparse images, UBI, and Chromium OS images
- Parallel extraction for large firmware images
- Clean JSON output for integration with automated analysis pipelines
- Active development by Onekey Security

**Running unblob with Docker:**

```bash
# Pull and run the official Docker image
docker pull ghcr.io/onekey-sec/unblob:latest

# Extract firmware
docker run --rm -v $(pwd)/firmware:/firmware -v $(pwd)/output:/output \
  ghcr.io/onekey-sec/unblob:latest \
  unblob -e /output /firmware/target_firmware.bin

# The -e flag specifies the extraction directory
```

## Firmadyne: Full System Emulation

Firmadyne is not an extraction tool — it's a full-system emulation platform designed to run extracted firmware images in a QEMU environment. This enables dynamic analysis: you can interact with the running firmware, test exploits, monitor network traffic, and observe runtime behavior.

**Key Features:**
- Automated extraction and emulation pipeline
- NVRAM simulation (libnvram) — many embedded devices store configuration in NVRAM and crash without it
- Network virtualization with tap interfaces
- Console access via virtual serial port
- Database-driven result tracking

**Setting Up Firmadyne with Docker:**

```bash
# Clone and build
git clone https://github.com/firmadyne/firmadyne.git
cd firmadyne
docker build -t firmadyne .

# Run the automated analysis
docker run --rm --privileged -v $(pwd)/images:/firmadyne/images \
  firmadyne ./fat.py /firmadyne/images/router.bin

# Access the emulated firmware via network
ssh root@<container-ip>
```

## EMUX: Lightweight IoT Emulation

EMUX (Embedded Emulator) takes a more focused approach than Firmadyne. Rather than full-system QEMU, it uses QEMU user-mode emulation with custom system call handling to run individual binaries from extracted firmware. This is faster and more resource-efficient, making it ideal for quick triage and targeted vulnerability testing.

**Key Features:**
- Built-in web console for managing emulated binaries
- Docker-native deployment (the recommended method)
- Automatic dependency resolution for emulated binaries
- System call translation layer
- Support for ARM, MIPS, and MIPSEL binaries

**Running EMUX with Docker:**

```bash
# Pull the official EMUX Docker image
git clone https://github.com/therealsaumil/emux.git
cd emux/docker
docker compose up -d

# Access the web console at http://localhost:8080
# Upload firmware binaries through the web interface
```

**Docker Compose for EMUX:**

```yaml
version: "3.8"
services:
  emux:
    image: emux:latest
    container_name: emux-lab
    ports:
      - "8080:8080"
    volumes:
      - ./firmware:/app/firmware
      - ./output:/app/output
    privileged: true
    restart: unless-stopped
```

## Building a Complete Firmware Analysis Lab

A comprehensive firmware analysis lab typically combines multiple tools. The recommended workflow:

**Phase 1: Extraction** — Use unblob for broad format coverage first, then fall back to Binwalk for entropy-based carving if unblob misses anything.

```bash
# Parallel extraction with both tools
docker run -v $(pwd)/firmware:/in -v $(pwd)/extracted/unblob:/out \
  ghcr.io/onekey-sec/unblob:latest unblob -e /out /in/firmware.bin

docker run -v $(pwd)/firmware:/in -v $(pwd)/extracted/binwalk:/out \
  binwalk binwalk -Me /in/firmware.bin -C /out
```

**Phase 2: Static Analysis** — Examine the extracted filesystem with tools like `grep`, `strings`, and your binary analysis platform of choice.

**Phase 3: Dynamic Analysis** — If the firmware contains ARM or MIPS binaries, try EMUX for quick testing. For full system emulation (boot process, network services, web interfaces), use Firmadyne.

## Why Self-Host Your Firmware Analysis Lab?

Running firmware analysis on your own infrastructure provides critical advantages over cloud-based services:

**Data Sovereignty:** Firmware images often contain proprietary intellectual property, hardcoded credentials, and sensitive configuration. Uploading them to a third-party analysis service creates legal and security risks for both the researcher and the device vendor. A self-hosted lab keeps all data within your controlled environment.

**Customization and Scripting:** Cloud platforms offer fixed analysis pipelines. With self-hosted tools, you can chain Binwalk extraction with custom Python analysis scripts, integrate with your vulnerability management system, and build automated triage workflows tailored to your organization's needs.

**Cost at Scale:** Security consultancies and large enterprises may analyze hundreds of firmware images per week. At typical per-analysis cloud pricing, costs quickly spiral. Self-hosted tools on your existing infrastructure incur zero per-use fees.

**Offline Capability:** Many security labs operate in air-gapped environments for classified or sensitive work. Self-hosted tools work without internet connectivity — essential for defense contractors, government agencies, and financial institutions.

For broader reverse engineering capabilities, see our [binary analysis and reverse engineering guide](../2026-05-03-ghidra-vs-radare2-vs-rizin-self-hosted-binary-analysis-reverse-engineering-guide-2026/). For firmware OTA update management, check our [firmware OTA update platform comparison](../2026-05-07-self-hosted-firmware-ota-update-management-hawkbit-rauc-swupdate-guide/). If you work with IoT device firmware specifically, our [ESPHome vs Tasmota vs ESPurna comparison](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) covers microcontroller firmware platforms.

## FAQ

### Which tool should I start with as a beginner?

Start with unblob. It has the broadest format support, the simplest command-line interface, and Docker images that work out of the box. Once you understand the extraction pipeline, add Binwalk for entropy-based carving of obfuscated firmware, then explore EMUX or Firmadyne for dynamic analysis.

### Can these tools analyze encrypted firmware?

Binwalk and unblob work primarily with unencrypted firmware images. If the firmware is encrypted (common in modern IoT devices with secure boot), you need to first obtain the decryption key — typically by extracting it from the device's flash memory, reverse-engineering the bootloader, or exploiting a hardware vulnerability. Some tools can identify encryption signatures to confirm the firmware is encrypted even if they can't decrypt it.

### How much disk space does a firmware analysis lab require?

A minimal Docker-based setup needs about 5 GB for the container images and tools. However, extracted firmware filesystems can be large — a single router firmware might expand from 16 MB to 500 MB after extraction. A realistic lab setup should have at least 50-100 GB available, plus additional space for storing original firmware images for reference.

### Does Firmadyne support MIPS big-endian firmware?

Firmadyne primarily supports ARM and MIPS little-endian architectures. Big-endian MIPS (common in older networking equipment) has limited support and may require manual kernel configuration. For big-endian targets, consider using QEMU directly or trying EMUX with appropriate configuration.

### What are the legal considerations for firmware analysis?

In most jurisdictions, analyzing firmware you legally own (on a device you purchased) for security research purposes is protected under fair use, right to repair, and security research exemptions. However, redistributing extracted firmware or exploiting vulnerabilities on devices you don't own is illegal. Always check local laws and have clear rules of engagement.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform. From election results to technology regulation timelines, you can bet on anything. Unlike gambling, this is a real information market: the more you know, the better your odds. I've made significant returns predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Firmware Analysis Platforms: Binwalk vs unblob vs Firmadyne vs EMUX",
  "description": "Compare four open-source firmware analysis tools for security research: Binwalk for entropy carving, unblob for multi-format extraction, Firmadyne for full-system emulation, and EMUX for lightweight ARM/MIPS emulation. Includes Docker Compose deployment guides.",
  "datePublished": "2026-06-06",
  "dateModified": "2026-06-06",
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
