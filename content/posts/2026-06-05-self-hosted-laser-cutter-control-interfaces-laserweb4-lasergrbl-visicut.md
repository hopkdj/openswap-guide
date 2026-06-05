---
title: "Self-Hosted Laser Cutter Control Interfaces: LaserWeb4 vs LaserGRBL vs VisiCut"
date: "2026-06-05"
tags: ["laser-cutter", "laser-engraver", "laserweb", "lasergrbl", "visicut", "cnc", "maker", "diy-electronics", "digital-fabrication"]
draft: false
---

## Introduction

Laser cutters and engravers have become essential tools in makerspaces, small manufacturing shops, and home workshops. While the hardware is increasingly affordable — with diode lasers starting under $200 and CO2 lasers becoming accessible — the software that controls these machines is often overlooked. The right control interface transforms a capable laser cutter from a frustrating machine requiring constant manual G-code editing into a smooth, reliable production tool.

This guide compares three open-source, self-hosted laser cutter control interfaces: **LaserWeb4**, a full-featured browser-based CAM and control platform; **LaserGRBL**, the most popular Windows-native solution with extensive material libraries; and **VisiCut**, a Java-based vector-to-laser workflow tool with strong Inkscape integration. Each platform approaches laser control differently, and the best choice depends on your workflow and hardware.

## Comparison Table

| Feature | LaserWeb4 | LaserGRBL | VisiCut |
|---------|-----------|-----------|---------|
| **GitHub Stars** | 789 | 1,593 | 293 |
| **Interface Type** | Web application (browser) | Windows desktop application | Java desktop application |
| **Cross-Platform** | Yes (any browser, runs on Raspberry Pi) | Windows only | Yes (Windows, macOS, Linux) |
| **G-Code Sender** | Built-in (Smoothieware, Grbl, Marlin) | Built-in (Grbl-focused) | Built-in (Grbl, Epilog, generic) |
| **CAM Processing** | Full CAM pipeline (SVG → G-code) | Basic image-to-G-code | Advanced vector processing |
| **Material Library** | Basic presets | Extensive community library | User-defined presets |
| **Image Engraving** | Dithering, grayscale, vector trace | Dithering (multiple algorithms), line-by-line | Limited (focuses on vector) |
| **Jog Control** | Yes (keyboard and on-screen) | Yes (keyboard and joystick) | Yes (basic jog) |
| **Z-Axis Control** | Yes (auto-focus support) | Yes (manual + probe) | Limited |
| **Camera Alignment** | Yes (USB camera overlay) | No | No |
| **SVG Import** | Yes (drag-and-drop) | Limited (converts to raster) | Yes (native Inkscape integration) |
| **Rotary Support** | Yes (roller/rotary axis) | Experimental | No |
| **Firmware Compatibility** | Grbl, Smoothieware, Marlin, TinyG | Grbl 0.9/1.1 | Grbl, Epilog, LaOS, custom drivers |
| **Self-Hosted** | Yes (local server) | Yes (local application) | Yes |

## LaserWeb4: The Browser-Based Workhorse

LaserWeb4 is a complete laser cutter workflow platform that runs entirely in a web browser. It connects directly to your laser's controller over a serial port via WebSocket-to-serial bridge, handling everything from SVG import and CAM processing to G-code streaming and real-time job monitoring.

### Key Features

- **End-to-end workflow**: import SVG, DXF, PNG, or JPEG → configure toolpaths → generate G-code → stream to laser — all in one interface without switching between multiple programs
- **Multiple operation types**: laser cut, vector engrave, raster engrave, and fill operations can be combined in a single job with different speed/power settings per operation
- **Camera alignment system**: connect a USB camera mounted on the laser head to see a live preview of your workpiece, align designs precisely to material edges, and account for workpiece rotation
- **Job time estimation**: LaserWeb4 calculates estimated job duration based on toolpath length and configured speeds, helping you plan production runs
- **Raspberry Pi deployment**: runs on a Raspberry Pi connected directly to the laser, enabling headless operation where you design on your main computer and send jobs to the Pi over the network

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  laserweb4:
    image: ghcr.io/laserweb/laserweb4:latest
    container_name: laserweb4
    ports:
      - "8080:80"
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    volumes:
      - ./laserweb-config:/app/config
      - ./laserweb-uploads:/app/uploads
    restart: unless-stopped
    environment:
      - TZ=America/Chicago
```

### Serial Bridge Setup

LaserWeb4 needs a WebSocket-to-serial bridge to communicate with your laser controller. The most common setup uses the `laserweb-serial` companion:

```bash
# Install the serial bridge
git clone https://github.com/LaserWeb/lw.comm-server.git
cd lw.comm-server
npm install
node server.js --port 8000 --serial /dev/ttyUSB0 --baud 115200
```

## LaserGRBL: The Windows Community Standard

LaserGRBL is the most widely adopted open-source laser control software, with over 1,500 GitHub stars and an active community. It is Windows-native and specifically optimized for Grbl-based laser controllers, which power the vast majority of diode and CO2 laser machines at the hobbyist and prosumer level.

### Key Capabilities

- **Rich image-to-G-code conversion**: supports multiple dithering algorithms (Atkinson, Floyd-Steinberg, Jarvis, Stucki, Sierra, ordered, threshold) for converting photographs into engravable patterns
- **Material database**: a community-maintained library of speed and power settings for hundreds of material types (plywood, acrylic, leather, anodized aluminum, slate, glass) — dramatically reduces trial-and-error when working with new materials
- **Real-time preview**: shows the toolpath overlay on your design image with estimated engraving time, letting you verify alignment and catch issues before the laser fires
- **Override controls**: adjust speed and power in real-time during a job — essential for fine-tuning on new materials without restarting the engraving
- **Shape library**: built-in vector shapes (circles, rectangles, polygons, text) for quick test patterns and simple designs without external software

### Installation

```bash
# LaserGRBL is Windows-native. To run on Linux, use Wine or a VM.
# For Linux users, the recommended approach is to use the Windows version via Wine:

# Install Wine
sudo apt install wine wine32

# Download LaserGRBL
wget https://github.com/arkypita/LaserGRBL/releases/latest/download/LaserGRBL.exe

# Run with Wine
wine LaserGRBL.exe
```

For a fully native Linux experience, LaserWeb4 or VisiCut are better options. Many Linux-based makers run LaserGRBL in a Windows virtual machine to access its material library while using LaserWeb4 for day-to-day control.

## VisiCut: The Vector Specialist

VisiCut takes a different approach from LaserWeb4 and LaserGRBL — it focuses on vector-based workflows with deep integration into Inkscape, the leading open-source vector graphics editor. Instead of importing files, VisiCut works directly with Inkscape's SVG data, preserving layer information, stroke properties, and fill colors as laser operation settings.

### Key Features

- **Inkscape plugin integration**: VisiCut can be launched directly from Inkscape. Select your design elements, assign them to laser operations (cut, engrave, mark) based on stroke color, and send the job — no file export or format conversion needed
- **Parameter mapping**: map Inkscape stroke colors to laser parameters. For example, red strokes = cut at 100% power 10mm/s, blue strokes = engrave at 30% power 100mm/s, black fills = raster engrave at 20% power
- **Nesting and layout optimization**: automatically arrange multiple parts on your material to minimize waste — a critical feature for production environments where material cost matters
- **Multiple driver backends**: supports Grbl, Epilog, LaOS, and generic G-code, making it suitable for a wide range of laser hardware that newer tools may not support
- **Material thickness calibration**: built-in tool for measuring actual kerf (the width of material removed by the laser) and adjusting toolpaths for precise press-fit joints

### Installation (Linux)

```bash
# Install Java Runtime
sudo apt install default-jre

# Download VisiCut
wget https://github.com/t-oster/VisiCut/releases/latest/download/VisiCut-2.0.0.zip
unzip VisiCut-2.0.0.zip
cd VisiCut

# Run VisiCut
java -jar VisiCut.jar
```

## Why Self-Host Your Laser Control Software?

Commercial laser software often comes bundled with specific machine brands and locks you into that manufacturer's ecosystem. If you upgrade from a budget K40 to a professional machine, or add a second laser to your workshop, you may find yourself learning an entirely new software workflow for each machine. Open-source control interfaces like LaserWeb4 and LaserGRBL work with any Grbl-compatible controller regardless of the laser brand, giving you a consistent workflow across your entire tool collection.

Self-hosted control also eliminates recurring costs. Commercial laser software suites often require annual subscriptions for features like camera alignment, rotary axis support, or advanced image processing modes — features that are included for free in LaserWeb4 and LaserGRBL. For a makerspace with multiple users and machines, these savings compound quickly.

Data privacy is another consideration. When you use cloud-connected commercial software, your designs — potentially including proprietary product designs, client artwork, or trade-secret prototypes — may be uploaded to the vendor's servers. Self-hosted interfaces keep all design files and job data on your local network.

For makers building a complete digital fabrication workflow, see our [self-hosted 3D printer server comparison](../2026-04-20-octoprint-vs-mainsail-vs-fluidd-self-hosted-3d-printer-server-guide-2026/). If you are working with ESP-based machine controllers, check our [ESPHome vs Tasmota vs ESPurna guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/). For integrating laser control into a broader home automation setup, see our [smart home hub comparison](../2026-04-28-home-assistant-vs-homebridge-vs-scrypted-self-hosted-smart-home-hub-guide-2026/).

## Safety Considerations for Laser Operation

Laser cutters present fire, fume, and eye safety hazards that software alone cannot mitigate. Always:

- Never leave a laser cutter unattended while operating — fires can start in seconds
- Install a proper fume extraction system vented outside — laser cutting plastics, acrylic, and wood releases toxic fumes
- Use laser safety glasses rated for your laser's wavelength — diode lasers (445nm/455nm), CO2 lasers (10,600nm), and fiber lasers each require different eye protection
- Configure software limit switches and endstops — LaserWeb4 and LaserGRBL both support homing cycles and soft limits to prevent the laser head from crashing into mechanical stops
- Add a physical emergency stop button wired in series with the laser power supply — software e-stops are not sufficient for fire safety

## FAQ

### Can I use LaserWeb4 with a cheap K40 laser?

Yes. LaserWeb4 works with any Grbl-compatible controller. Most K40 lasers ship with a basic M2 Nano controller that uses proprietary software, but replacing it with a Grbl-compatible board (like the Cohesion3D Mini or Makerbase MKS DLC32, typically $30-60) enables full LaserWeb4 compatibility with camera alignment, rotary support, and job queuing.

### Why would I use VisiCut when LaserWeb4 also imports SVG?

VisiCut's Inkscape integration goes deeper than simple SVG import. It preserves Inkscape's layer structure and maps stroke/fill properties directly to laser operations, meaning you can define all your cut and engrave settings inside your design file rather than reconfiguring them in the laser software each time. For users who design primarily in Inkscape, this eliminates a significant amount of repetitive setup work between design and production.

### Does LaserGRBL work on a Raspberry Pi?

Not natively. LaserGRBL is built on the .NET Framework and is Windows-only. For Raspberry Pi-based laser control, use LaserWeb4 (which runs beautifully on a Pi connected directly to the laser) or VisiCut (which runs on any platform with Java, including ARM64 Raspberry Pi). Some users run LaserGRBL on a Windows machine and stream G-code over the network to a Raspberry Pi acting as a serial bridge — but this adds complexity that LaserWeb4 avoids entirely.

### What is the difference between raster engraving and vector engraving?

Raster engraving works like an inkjet printer — the laser scans back and forth line by line, turning on and off to create a shaded image (like engraving a photograph onto wood). Vector engraving follows the actual lines of your design at a constant power level, similar to how a pen plotter works (like engraving text or outlines onto a material). LaserWeb4 supports both modes and can mix them in a single job; LaserGRBL excels at raster engraving with its multiple dithering algorithms.

### Can these tools control a CNC router as well?

LaserWeb4 and LaserGRBL both connect to Grbl-based controllers, and Grbl was originally designed for CNC milling. In theory, they can send G-code to any Grbl machine. However, they lack CNC-specific features like tool changes, coolant control, spindle speed management, and multi-depth pocketing strategies. For CNC-specific operations, use dedicated tools like bCNC, Universal G-code Sender, or Candle. VisiCut has some CNC driver support but is primarily optimized for laser workflows.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Laser Cutter Control Interfaces: LaserWeb4 vs LaserGRBL vs VisiCut",
  "description": "Detailed comparison of open-source laser cutter and engraver control platforms including LaserWeb4 for browser-based CAM, LaserGRBL for Windows-native control with material libraries, and VisiCut for Inkscape-integrated vector workflows.",
  "datePublished": "2026-06-05",
  "dateModified": "2026-06-05",
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
