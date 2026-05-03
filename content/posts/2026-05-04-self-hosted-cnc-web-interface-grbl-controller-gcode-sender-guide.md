---
title: "Best Self-Hosted CNC Web Interfaces for GRBL Controllers in 2026"
date: 2026-05-04T10:00:00+00:00
draft: false
tags: ["cnc", "manufacturing", "grbl", "self-hosted", "g-code", "3d-printing"]
---

Computer Numerical Control (CNC) machines — from desktop routers to industrial mills — are controlled by G-code, a programming language that tells the machine where to move, how fast, and what tool to use. Getting G-code from your CAM software to the machine requires a **sender** — a program that streams commands over serial or network connections to the machine's controller.

Modern CNC senders offer web-based interfaces, letting operators monitor and control machines from any device on the network. This is especially valuable in workshop environments where the operator needs to move between machines, or when managing multiple CNC routers from a central monitoring station. This guide compares three popular open-source CNC web interfaces: **CNCjs**, **bCNC**, and **Universal Gcode Sender**.

## What Is a G-Code Sender?

A G-code sender bridges the gap between your CAM (Computer-Aided Manufacturing) software and the physical CNC machine. It reads G-code files, parses them into individual commands, sends them to the machine controller (typically GRBL, Smoothieware, TinyG, or Marlin), and provides real-time feedback on machine position, status, and errors.

A web-based sender adds network accessibility — you can start a job from your phone, monitor progress from a tablet mounted near the machine, or oversee multiple machines from a dashboard. For makerspaces, small machine shops, and educational labs, this flexibility is invaluable.

## Comparison Overview

| Feature | CNCjs | bCNC | Universal Gcode Sender |
|---------|-------|------|----------------------|
| **License** | MIT | GPL-3.0 | GPL-3.0 |
| **Language** | Node.js | Python/Tkinter | Java |
| **Web Interface** | ✅ Full web UI | ❌ Desktop GUI | ⚠️ Pendant (web) |
| **Connection** | Serial/Network | Serial | Serial/Network |
| **Supported Controllers** | GRBL, Smoothieware, TinyG, Marlin | GRBL, TinyG, GrblHAL | GRBL, Smoothieware, TinyG, G2core |
| **3D Visualization** | ✅ WebGL | ✅ Canvas | ❌ |
| **Autoleveling** | ❌ | ✅ Built-in | ⚠️ Via plugin |
| **Job Queue** | ✅ Multiple files | ✅ File manager | ✅ Job planner |
| **Probe Support** | ✅ Z-probe | ✅ Auto-level probe | ✅ Work coordinate probe |
| **Jog Control** | ✅ On-screen + keyboard | ✅ On-screen | ✅ On-screen |
| **Plugins** | ✅ Plugin system | ✅ Plugin system | ⚠️ Limited |
| **Camera Overlay** | ✅ Via plugin | ✅ Built-in | ❌ |
| **GitHub Stars** | 2,592 | 1,728 | 2,205 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |

## CNCjs — The Web-First CNC Controller

[CNCjs](https://github.com/cncjs/cncjs) is the most popular web-based CNC sender, built on Node.js with a modern responsive interface. It runs as a server that you access from any browser on your network — desktop, tablet, or phone. The interface includes a 3D G-code viewer, real-time position tracking, and a comprehensive set of jog controls.

CNCjs excels at multi-machine management. A single CNCjs server can manage multiple CNC machines simultaneously, each on its own connection port. The plugin ecosystem adds camera overlay (for visual job alignment), macro buttons for common operations, and webhook integration for job completion notifications.

### Deploying CNCjs with Docker Compose

CNCjs runs as a Node.js server and is easily containerized. The official Docker image handles all dependencies:

```yaml
services:
  cncjs:
    image: cncjs/cncjs:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    volumes:
      - cncjs_config:/home/cnc/.cnc
      - /dev/ttyUSB0:/dev/ttyUSB0
    environment:
      - CNCJS_PORT=8000
      - CNCJS_WATCH_DIR=/home/cnc/gcode
    command: cncjs -p 8000 --port /dev/ttyUSB0 -b 115200

  # Optional: mount a shared G-code directory
  gcode_share:
    image: alpine:latest
    volumes:
      - ./gcode:/gcode
    command: tail -f /dev/null

volumes:
  cncjs_config:
```

After deployment, open `http://your-server:8000` and configure your machine connection. CNCjs auto-detects GRBL controllers and provides a setup wizard for first-time configuration.

## bCNC — The Swiss Army Knife of GRBL Control

[bCNC](https://github.com/vlachoudis/bCNC) is a feature-rich GRBL sender written in Python with a Tkinter GUI. While not a web interface in the traditional sense, it offers the most comprehensive set of CNC-specific features of any open-source sender, including automatic bed leveling, camera-assisted alignment, and a powerful G-code editor.

bCNC's autoleveling workflow is its standout feature: it probes the bed surface at a configurable grid of points, generates a compensation mesh, and modifies your G-code on-the-fly to account for bed irregularities. This is essential for PCB milling, engraving on uneven surfaces, and any operation where cut depth matters.

### Running bCNC

bCNC is a Python application best run directly on the machine host rather than in Docker (since it needs serial port access and a display). Install via pip:

```bash
# Install bCNC and dependencies
pip install bCNC pyserial numpy

# Launch the application
python -m bCNC
# Or if installed as a package:
bCNC
```

For headless operation, bCNC can be accessed via VNC or X forwarding:

```bash
# Run bCNC on a Raspberry Pi connected to your CNC
# Then access via VNC from your workstation
sudo apt install x11vnc
x11vnc -display :0 -forever &
```

The bCNC interface includes a G-code editor with syntax highlighting, a 2D visualization canvas, a control panel with jog buttons, and a terminal for direct GRBL commands.

## Universal Gcode Sender (UGS) — The Cross-Platform Standard

[Universal Gcode Sender](https://github.com/winder/Universal-G-Code-Sender) is a Java-based CNC sender that runs on any platform with a JVM. It features a clean, tabbed interface with separate panels for job control, machine status, G-code visualization, and settings. UGS supports the widest range of GRBL-compatible controllers, including Smoothieware, TinyG, and G2core.

UGS Platform — the newer variant built on NetBeans — adds a modular plugin architecture, 3D G-code visualization, and a visual workflow designer. The "Pendant" module provides a lightweight web interface accessible from mobile devices, giving UGS web capabilities despite its desktop-first architecture.

### Running Universal Gcode Sender

UGS runs on any system with Java 8 or later. The recommended approach uses the Platform variant:

```bash
# Download the latest release
wget https://github.com/winder/Universal-G-Code-Sender/releases/latest/download/ugs-platform-app.zip
unzip ugs-platform-app.zip
cd ugsplatform

# Launch the application
./bin/ugsplatform
```

For the lightweight Pendant (web interface) on a Raspberry Pi:

```bash
# Install the standalone pendant
wget https://github.com/winder/Universal-G-Code-Sender/releases/latest/download/ugs-pendant.zip
unzip ugs-pendant.zip

# Start the pendant (web UI on port 8080)
java -jar ugs-pendant.jar --port /dev/ttyUSB0 --baud 115200 --webport 8080
```

Access the pendant at `http://your-pi:8080` from any device on the network.

## Why Self-Host Your CNC Interface?

Self-hosting a CNC web interface gives workshop operators the flexibility to monitor and control machines from anywhere on the local network. Instead of being tethered to a specific workstation, operators can start jobs from a tablet mounted at the machine, check progress from their phone while at another station, or have a central dashboard showing the status of all machines.

For makerspaces and educational labs, a shared CNC server means anyone can submit jobs from their laptop without installing specialized software. The server manages the serial connection to the machine, queues jobs, and provides a consistent interface regardless of the operator's device.

If you are already running self-hosted 3D printer management tools like OctoPrint, adding a CNC web interface creates a unified manufacturing dashboard covering both additive and subtractive processes. See our [3D printer server comparison](../2026-04-20-octoprint-vs-mainsail-vs-fluidd-self-hosted-3d-printer-server-guide-2026/) for complementary manufacturing infrastructure. For makers managing a mixed workshop, our [home inventory management guide](../2026-04-22-grocy-vs-homebox-self-hosted-home-inventory-management-guide-2026/) also covers patterns for tracking tools, materials, and consumables.

## FAQ

### What is GRBL and why do I need a sender?

GRBL is an open-source firmware that runs on Arduino-compatible microcontrollers to drive CNC machines. It interprets G-code commands and moves stepper motors accordingly. A sender is needed because GRBL itself has no user interface — it only accepts serial commands. The sender reads G-code files, streams commands to GRBL one at a time (respecting the controller's buffer limits), and provides the operator with visual feedback on machine position and job progress.

### Can I control multiple CNC machines from one sender?

CNCjs supports managing multiple machines from a single server instance — each machine gets its own connection and web interface accessible at different ports. bCNC and UGS are single-machine focused; you would need separate instances for each machine. For multi-machine workshops, CNCjs is the clear choice.

### What is bed autoleveling and do I need it?

Bed autoleveling compensates for slight unevenness in your work surface by probing the bed at multiple points, creating a height map, and adjusting the Z-axis position during cutting. This is critical for PCB milling (where trace depth must be consistent) and engraving. It is less important for through-cutting operations where the bit goes completely through the material. bCNC has the most robust autoleveling implementation of the three tools.

### Can these senders work with controllers other than GRBL?

Yes. All three support multiple controller firmware. CNCjs supports GRBL, Smoothieware, TinyG, and Marlin. UGS supports GRBL, Smoothieware, TinyG, and G2core. bCNC focuses primarily on GRBL and GrblHAL. If you are using a different controller (like LinuxCNC or Mach3), you will need a different sender designed for that ecosystem.

### How do I set up the Pendant web interface for UGS?

The UGS Pendant is a separate download from the main UGS Platform. After downloading the pendant JAR, run it with the serial port and baud rate matching your controller: `java -jar ugs-pendant.jar --port /dev/ttyUSB0 --baud 115200`. The pendant serves a web interface on port 8080 by default. It provides basic jog controls, file upload, job start/stop, and machine status — a subset of the full desktop interface optimized for mobile browsers.

### Is it safe to leave a CNC sender running unattended?

GRBL-based systems are generally safe for unattended operation because the firmware handles limit switches, emergency stops, and buffer overflow protection. However, you should always: (1) ensure your machine has functional limit switches, (2) set up a webcam for remote monitoring, (3) configure your sender to pause on error rather than crash, and (4) never run jobs that could cause fire hazards (e.g., cutting flammable materials) unattended.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted CNC Web Interfaces for GRBL Controllers in 2026",
  "description": "Compare CNCjs, bCNC, and Universal Gcode Sender — the top open-source web interfaces for controlling GRBL-based CNC machines.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
