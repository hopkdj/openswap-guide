---
title: "Self-Hosted PLC Programming & Industrial Control: OpenPLC vs Beremiz vs Rusty PLC"
date: "2026-06-05"
tags: ["plc", "iec-61131", "industrial-automation", "openplc", "beremiz", "ladder-logic", "structured-text"]
draft: false
---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PLC Programming & Industrial Control: OpenPLC vs Beremiz vs Rusty PLC",
  "description": "Compare open-source PLC programming platforms for self-hosted industrial automation. Covers OpenPLC (IEC 61131-3 runtime and editor), Beremiz (research-grade IDE), and Rusty PLC (Structured Text to LLVM compiler) with Docker Compose deployment guides.",
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

## Introduction

Programmable Logic Controllers (PLCs) are the workhorses of industrial automation — controlling everything from assembly lines to water treatment plants. Traditionally, PLC programming required expensive proprietary software locked to specific hardware vendors. The open-source PLC movement has changed this landscape, offering self-hosted alternatives that run on commodity hardware and support the IEC 61131-3 standard.

This guide compares three leading open-source PLC platforms: **OpenPLC** (full-stack runtime and editor), **Beremiz** (IEC 61131-3 IDE with runtime), and **Rusty PLC** (Structured Text compiler with LLVM backend). Whether you're automating a home brewery, building a factory control system, or teaching industrial automation, these tools let you run PLC logic on standard Linux servers.

## Quick Comparison

| Feature | OpenPLC | Beremiz | Rusty PLC |
|---------|---------|---------|-----------|
| **Stars** | 1,546 (Runtime) | 404 | 347 |
| **Language Implementation** | C / Python | Python / C | Rust |
| **IEC 61131-3 Support** | All 5 languages | All 5 languages | Structured Text only |
| **Runtime Platform** | Linux, Windows, Arduino, ESP32 | Linux, Windows | Linux, macOS, Windows |
| **Hardware Targets** | Raspberry Pi, UniPi, Arduino, ESP32 | SoftPLC, EtherCAT | SoftPLC via LLVM |
| **Web Interface** | Built-in web dashboard | No (IDE-based) | No |
| **Docker Support** | Yes (official image) | Community images | Source build |
| **Licensing** | GPLv3 | GPLv2 | MIT / Apache 2.0 |

## OpenPLC: The Full-Stack Solution

OpenPLC is the most comprehensive open-source PLC platform, providing both an IEC 61131-3 editor and a runtime engine that runs on everything from Raspberry Pi to ESP32 microcontrollers. Its built-in web dashboard and Modbus support make it ideal for self-hosted industrial control.

### IEC 61131-3 Language Support

OpenPLC supports all five standard PLC programming languages:
- **Ladder Logic (LD)**: Relay-style graphical programming
- **Function Block Diagram (FBD)**: Data-flow graphical programming
- **Structured Text (ST)**: Pascal-like textual programming
- **Instruction List (IL)**: Assembly-like low-level language
- **Sequential Function Chart (SFC)**: State-based process control

### Docker Deployment

OpenPLC provides an official Docker image for the runtime, making deployment straightforward:

```yaml
version: "3.8"
services:
  openplc:
    image: openplc/openplc:v3
    container_name: openplc-runtime
    network_mode: host
    ports:
      - "8080:8080"
      - "502:502"
    volumes:
      - ./openplc_programs:/usr/local/lib/openplc/st_files
    restart: unless-stopped
```

Once running, access the web dashboard at `http://your-server:8080` to upload programs, monitor I/O, and view real-time variable values.

### Modbus Integration

OpenPLC acts as a Modbus TCP server on port 502, allowing any SCADA system or HMI to read and write PLC variables. Each OpenPLC variable is automatically mapped to a Modbus register:

```python
#!/usr/bin/env python3
import minimalmodbus

# Read OpenPLC variable via Modbus
instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1)
temperature = instrument.read_register(0, 1)  # Register 0
print(f"Temperature: {temperature / 10.0}°C")
```

## Beremiz: The Research-Grade IDE

Beremiz is an integrated development environment for IEC 61131-3 automation, born from academic research and maintained by the open-source community. It combines a graphical editor, compiler, and runtime into a single application.

### Key Features

- **Integrated IDE**: Graphical editor with drag-and-drop FBD, LD, and SFC editors
- **SVG-based visualization**: Built-in HMI designer for operator screens
- **CANopen support**: Native CANopen master for industrial device communication
- **EtherCAT integration**: Support for EtherCAT fieldbus via the IgH EtherCAT master
- **Python extensions**: Extend PLC programs with Python runtime functions

### Self-Hosted Beremiz Runtime

While Beremiz is primarily an IDE, you can export compiled PLC programs and run them headlessly on a server:

```bash
# Install Beremiz IDE
git clone https://github.com/beremiz/beremiz.git
cd beremiz
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 Beremiz.py
```

For a headless runtime deployment on a server, use Beremiz's service mode:

```yaml
version: "3.8"
services:
  beremiz-runtime:
    image: python:3.11-slim
    container_name: beremiz-plc
    network_mode: host
    volumes:
      - ./beremiz:/opt/beremiz
      - ./plc_programs:/programs
    working_dir: /opt/beremiz
    command: >
      sh -c "pip install wxpython pyserial canopen &&
             python3 Beremiz_service.py -p 61131 /programs/my_plc.xml"
    restart: unless-stopped
```

## Rusty PLC: Modern Structured Text Compilation

Rusty PLC brings modern compiler infrastructure to PLC programming. It parses IEC 61131-3 Structured Text and compiles it to native machine code via LLVM — enabling PLC logic to run at near-native performance on any LLVM-supported target.

### Architecture

```
Structured Text (.st) → Parser → AST → LLVM IR → JIT/Native Code → Runtime
```

This compiler-first approach means Rusty PLC programs benefit from LLVM's optimization passes, producing PLC executables that run significantly faster than interpreted alternatives.

### Building and Running

```bash
git clone https://github.com/PLC-Lang/rusty.git
cd rusty
cargo build --release

# Compile a Structured Text program
./target/release/rusty compile my_program.st -o my_program

# Run the compiled PLC program
./my_program
```

For a self-hosted deployment, wrap the compiled binary in a Docker container:

```yaml
version: "3.8"
services:
  rusty-plc:
    image: rust:latest
    container_name: rusty-plc-runtime
    network_mode: host
    volumes:
      - ./plc_programs:/programs
    command: >
      sh -c "cd /programs && ./my_plc_program"
    restart: unless-stopped
```

## Why Self-Host Your PLC Infrastructure?

Traditional PLC programming requires vendor-specific software licenses costing $2,000-$10,000 per seat annually. OpenPLC and Beremiz eliminate these costs entirely — you get a full IEC 61131-3 environment for zero licensing fees, running on commodity hardware you already own.

Hardware independence is another major advantage. Instead of being locked into Siemens, Rockwell, or Beckhoff hardware, open-source PLC runtimes let you choose the best controller for each application. Use a Raspberry Pi for low-cost monitoring, a rugged industrial PC for critical control, or an ESP32 for distributed I/O — all programmed with the same IEC 61131-3 tools.

For integration with broader industrial infrastructure, see our guides on [SCADA systems for operator interfaces](../2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/), [OPC UA servers for data exchange](../2026-05-16-self-hosted-opc-ua-server-eclipse-milo-open62541-node-opcua-guide/), and [Modbus TCP communication](../2026-05-20-self-hosted-modbus-tcp-server-solutions-pymodbus-vs-libmodbus-vs-gomodbus-guide/). These tools form a complete open-source industrial automation stack — from PLC control to SCADA visualization — all self-hosted on your own infrastructure.

Open-source PLCs also excel in education. Universities and training centers can set up dozens of PLC workstations without licensing costs, using the same IEC 61131-3 languages taught in industry certification programs. Students learn ladder logic and structured text on real hardware, gaining skills directly transferable to commercial PLC environments.

Open-source PLCs also excel in education. Universities and training centers can set up dozens of PLC workstations without licensing costs, using the same IEC 61131-3 languages taught in industry certification programs. Students learn ladder logic and structured text on real hardware, gaining skills directly transferable to commercial PLC environments.

The integration possibilities between these open-source PLC tools and modern DevOps practices are particularly compelling. You can version-control your PLC programs in Git, run automated tests on CI/CD pipelines, and deploy updates via Docker containers — practices that are standard in software engineering but rarely possible with proprietary PLC platforms. OpenPLC's REST API and Modbus server make it straightforward to integrate PLC data into Grafana dashboards, InfluxDB time-series databases, and MQTT-based IoT architectures.

For industrial deployments, the cost savings compound quickly. A mid-size factory with 20 PLC-controlled workstations saves $40,000-$100,000 in the first year by replacing proprietary PLC software licenses with OpenPLC or Beremiz. The hardware cost is also dramatically lower — a Raspberry Pi 4 running OpenPLC costs $75, while an equivalent commercial PLC from Siemens or Allen-Bradley costs $1,500-$5,000.

## FAQ

### Can OpenPLC replace a commercial PLC in production?

Yes, with appropriate hardware selection. OpenPLC has been deployed in real industrial applications including water treatment plants, HVAC control systems, and manufacturing lines. The key consideration is hardware reliability — choose industrial-grade controllers (UniPi, Revolution Pi, or industrial Raspberry Pi variants) with proper electrical isolation and watchdog timers. For SIL-rated safety applications, you should still use certified safety PLCs. OpenPLC is best suited for non-safety-critical control tasks where cost savings and flexibility are priorities.

### What's the difference between Ladder Logic and Structured Text?

**Ladder Logic** is a graphical language resembling electrical relay diagrams. It's the traditional choice for electricians transitioning to PLCs and excels at boolean logic and simple sequencing. **Structured Text** is a textual language similar to Pascal — better suited for complex math, data manipulation, and state machines. Most modern projects use a mix: ladder logic for I/O mapping and emergency stops, structured text for process algorithms and communication. OpenPLC supports both, letting you combine them in a single program.

### How do I connect physical sensors and actuators to a self-hosted PLC?

Several options exist depending on your platform: (1) **Raspberry Pi GPIO** — direct wiring for low-voltage digital I/O (with proper protection circuits); (2) **Modbus RTU/TCP** — connect industrial I/O modules over RS-485 or Ethernet; (3) **Arduino/ESP32 as remote I/O** — use microcontrollers over serial or WiFi as distributed I/O nodes; (4) **EtherCAT** — Beremiz supports EtherCAT for high-speed deterministic fieldbus. For production deployments, Modbus TCP I/O modules from brands like Advantech or ICP DAS provide the best reliability.

### Is Structured Text compilation with LLVM production-ready?

Rusty PLC's LLVM-based approach is promising but still maturing. The benefit — native-code performance with compiler optimizations — is real, but the tool's IEC 61131-3 coverage is limited to Structured Text only. For production use today, OpenPLC's interpreted runtime is more battle-tested and supports all five languages. Rusty PLC is an excellent choice for performance-critical ST modules that you integrate into a broader OpenPLC or Beremiz project.

### What hardware do you recommend for a home lab PLC setup?

Start with a **Raspberry Pi 4 or 5** running OpenPLC — it costs under $100 and supports Modbus TCP out of the box. Add an **8-channel relay module** (~$15) for digital outputs and an **ADS1115 ADC module** (~$10) for analog inputs. This gives you a fully functional PLC with ladder logic programming for under $130 total. For automotive or CAN-focused projects, combine it with our [CAN bus gateway guide](../2026-06-05-self-hosted-can-bus-gateways-socketcand-python-can-can-utils-guide/). The learning curve from hobbyist projects to industrial deployment is remarkably smooth with these open-source tools.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
