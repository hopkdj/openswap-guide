---
title: "Self-Hosted MQTT Diagnostic Tools: MQTTX vs MQTT Explorer vs HiveMQ CLI"
date: "2026-06-07"
tags: ["mqtt", "iot", "diagnostics", "debugging", "self-hosted", "messaging", "monitoring"]
draft: false
---

## Introduction

MQTT has become the backbone of IoT communication, powering everything from smart home sensors to industrial telemetry. But when your MQTT broker handles thousands of topics across dozens of devices, diagnosing issues — rogue publishers, malformed payloads, topic storms, or authentication problems — requires specialized tools beyond basic `mosquitto_sub` and `mosquitto_pub` commands.

This guide compares three leading open-source MQTT diagnostic and management tools: **MQTTX** by EMQX (a full-featured desktop, CLI, and web client), **MQTT Explorer** (a structured topic browser), and **HiveMQ MQTT CLI** (a shell-native command-line tool). Each serves different use cases, and together they form a complete MQTT diagnostic toolkit.

| Feature | MQTTX (EMQX) | MQTT Explorer | HiveMQ MQTT CLI |
|---------|-------------|---------------|-----------------|
| **Interface** | Desktop (Electron), CLI, Web | Desktop (Electron) | CLI (Shell) |
| **MQTT Version** | 3.1.1, 5.0 | 3.1.1, 5.0 | 3.1.1, 5.0 |
| **Topic Visualization** | Tree + message list | Structured topic tree | Flat list |
| **Message Publishing** | JSON/formatted editor | Raw/JSON/Hex input | Command-line with stdin |
| **Scripting/Automation** | CLI + WebSocket API | Limited | Full shell scripting |
| **Connection Profiles** | Multiple saved profiles | Multiple saved profiles | Environment variables |
| **Message History** | Scrollback buffer | Scrollback buffer | Shell history |
| **TLS/Auth Support** | Full TLS, mTLS, username/password, token | TLS, username/password | Full TLS, mTLS, client certs |
| **Docker/Headless** | Web version available | Desktop only | Native (CLI) |
| **GitHub Stars** | 4,933 | 3,961 | 1,096 |
| **Best For** | All-in-one MQTT toolbox | Visual topic browsing | Scripting and automation |

## MQTTX: The All-in-One MQTT Toolbox

MQTTX, developed by EMQX (the team behind the EMQX broker), is the most feature-complete MQTT client in the open-source ecosystem. It offers desktop, command-line, and web-based interfaces, making it versatile across development, testing, and production debugging scenarios.

### Key Capabilities

- **Multi-platform**: Desktop app (Windows, macOS, Linux), CLI (`mqttx`), and web version accessible from any browser
- **MQTT 5.0 support**: Full support for session expiry, message expiry, reason codes, user properties, shared subscriptions
- **Script simulation**: The CLI version can simulate device traffic with configurable message rates, payload templates, and connection counts — invaluable for load testing
- **Connection management**: Save and organize multiple broker connections with unique TLS certificates, authentication credentials, and topic subscriptions

### Docker Compose for MQTTX Web

```yaml
version: "3.8"
services:
  mqttx-web:
    image: emqx/mqttx-web:latest
    container_name: mqttx-web-client
    ports:
      - "8088:80"
    restart: unless-stopped
    environment:
      - MQTTX_WEB_DEFAULT_HOST=your-mqtt-broker
      - MQTTX_WEB_DEFAULT_PORT=1883
```

### CLI Usage Examples

```bash
# Install MQTTX CLI
npm install -g mqttx-cli

# Connect and subscribe with MQTT 5.0
mqttx sub -h broker.local -p 1883 -t "sensors/#" -q 2 --mqtt-version 5

# Publish with user properties
mqttx pub -h broker.local -t "device/status"   -m '{"online": true, "battery": 87}'   --user-properties "device-id:esp32-01"

# Simulate 100 devices publishing temperature data
mqttx simulate -h broker.local -t "sensors/temp"   -c 100 -im 5000 --payload-template '{"temp": {{random 15 35}}}'
```

## MQTT Explorer: Visual Topic Browsing

MQTT Explorer provides a structured, spreadsheet-like view of your MQTT topic tree. Instead of flat lists of topics, it organizes them hierarchically, showing message history per topic and making it easy to spot patterns across related topics.

### Key Capabilities

- **Hierarchical topic tree**: Topics are displayed as a collapsible tree matching the MQTT topic structure (`building/floor/room/sensor`)
- **Value differencing**: Automatically highlights when a retained message value changes, making it easy to track sensor state transitions
- **Message plotting**: Built-in charting for numeric payloads — plot temperature, humidity, or power readings over time
- **Payload formatting**: Auto-formats JSON, displays hex for binary payloads, renders plain text with syntax awareness
- **Export**: Save topic trees or message histories as JSON for documentation or debugging reports

MQTT Explorer is a desktop application (Electron-based) and does not have a native web or headless server mode. For remote access, you can use X11 forwarding, VNC, or the MQTTX web client as an alternative. However, for hands-on debugging during development or troubleshooting, its structured topic view is unmatched.

## HiveMQ MQTT CLI: Shell-Native Scripting Power

HiveMQ MQTT CLI is a Java-based command-line tool designed for automation and scripting. Unlike the GUI tools, it is built from the ground up for shell pipelines, CI/CD integration, and automated testing workflows.

### Key Capabilities

- **Shell integration**: Native stdin/stdout piping, making it ideal for shell scripts and monitoring pipelines
- **Performance testing**: Built-in benchmark mode for measuring broker throughput and latency under load
- **Shell mode**: Interactive shell with connection persistence — connect once, then run multiple pub/sub commands
- **TLS and authentication**: Full support for TLS 1.3, mutual TLS, client certificates, username/password, and token-based authentication

### Installation and Usage

```bash
# Install via SDKMAN or direct download
sdk install hivemq-mqtt-cli

# Subscribe and pipe output to jq for JSON filtering
mqtt cli sub -h broker.local -t "sensors/#" --jsonOutput | jq '.payload | fromjson | .temperature'

# Benchmark: measure broker publish throughput
mqtt cli bench pub -h broker.local -t "bench/test" -c 50 -m 10000

# Shell mode: persistent connection for interactive debugging
mqtt cli shell -h broker.local -u admin -pw password
Connected to broker.local:1883
mqtt> sub -t "device/+/status" -q 1
mqtt> pub -t "device/controller" -m "restart"
```

### Docker Deployment for CI/CD Testing

```yaml
version: "3.8"
services:
  mqtt-test:
    image: hivemq/mqtt-cli:latest
    container_name: mqtt-test-runner
    entrypoint: ["mqtt"]
    command: ["cli", "test", "-h", "${MQTT_HOST}", "-t", "test/topic", "-m", "${TEST_MESSAGE_COUNT}"]
    environment:
      - MQTT_HOST=broker.local
      - TEST_MESSAGE_COUNT=5000
    depends_on:
      - mosquitto
```

## Building Your MQTT Diagnostic Workflow

Each tool serves a distinct role in a comprehensive MQTT diagnostic workflow:

1. **MQTTX (Web)** — Deploy the web version for team-wide access to broker monitoring and ad-hoc message inspection without installing anything
2. **MQTT Explorer** — Use during development and debugging for its structured topic visualization and message diffing
3. **HiveMQ MQTT CLI** — Automate load testing in CI/CD pipelines, run scheduled broker health checks, and integrate MQTT monitoring into shell scripts

For a production setup, consider combining these with broker-side monitoring using Prometheus exporters (EMQX and Mosquitto both expose metrics) and Grafana dashboards for long-term traffic analysis.

## FAQ

### Can I run MQTT diagnostic tools on a headless server?

MQTTX offers a web version that can be deployed via Docker, accessible from any browser. The HiveMQ MQTT CLI is fully headless and works over SSH. MQTT Explorer is desktop-only and requires a GUI environment, though you can use X11 forwarding or VNC as a workaround.

### How do I debug MQTT authentication failures?

All three tools provide detailed error messages for connection failures. With HiveMQ MQTT CLI, use the `-V` (verbose) flag to see TLS handshake details and authentication exchanges. MQTTX displays authentication error codes inline. Check your broker logs simultaneously — both Mosquitto and EMQX log auth failures with timestamps and client IDs. Common issues include expired client certificates, wrong TLS version configuration, and ACL restrictions on topic access.

### What is the best way to monitor MQTT broker health?

Beyond client-side tools, deploy a Prometheus exporter for broker metrics. For Mosquitto, use the built-in `$SYS` topic hierarchy with a metrics collector. For EMQX, the built-in Prometheus endpoint at port 18083 provides connection counts, message rates, and session statistics. Combine with Grafana dashboards for visual monitoring. The HiveMQ MQTT CLI can run periodic health checks: publish a test message and verify it is received on the subscribed topic to confirm end-to-end broker functionality.

### How do I handle large MQTT payloads during debugging?

MQTTX's web and desktop versions display full payloads with scrollable views and JSON formatting. For binary payloads, MQTT Explorer offers a hex view. With the HiveMQ MQTT CLI, pipe output through `xxd` for hex dumps. For very large payloads (hundreds of KB), consider using MQTTX CLI with the `--pretty` flag and redirecting output to a file: `mqttx sub -h broker -t "large/topic" > payload.json`. Remember that MQTT's maximum payload size defaults to 256KB in most brokers.

## Why Self-Host Your MQTT Diagnostic Tools?

Managing MQTT infrastructure without proper diagnostic tooling is like operating a database without a query client — technically possible but frustrating and error-prone. Self-hosting your diagnostic tools keeps your MQTT credentials, message payloads, and topic structures entirely within your network perimeter. This is especially important when dealing with sensitive sensor data from industrial equipment, healthcare devices, or home security systems.

Second, having diagnostic tools ready when problems arise prevents downtime cascades. A misbehaving IoT device flooding your broker with 10,000 messages per second can bring down other services. With MQTTX or the HiveMQ CLI already deployed, you can identify the rogue client in seconds rather than minutes — the difference between a blip and an outage.

Third, self-hosted diagnostic access enables team collaboration. Deploying MQTTX Web via Docker gives your entire engineering team browser-based MQTT access without distributing broker credentials to individual machines. This centralized approach simplifies audit trails and credential rotation while keeping sensitive broker access controlled.

For choosing the right MQTT broker, see our [Mosquitto vs EMQX vs HiveMQ broker comparison](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/). For lightweight broker alternatives, our [VerneMQ vs NanoMQ vs FlashMQ guide](../2026-06-02-vernemq-vs-nanomq-vs-flashmq-mqtt-brokers-guide/) covers three options optimized for edge deployment. If you are building a complete IoT platform, see our [ThingsBoard vs IoTSharp comparison](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MQTT Diagnostic Tools: MQTTX vs MQTT Explorer vs HiveMQ CLI",
  "description": "Compare MQTTX, MQTT Explorer, and HiveMQ MQTT CLI for self-hosted MQTT debugging and monitoring. Docker Compose setups, scripting examples, and diagnostic workflows for IoT infrastructure.",
  "datePublished": "2026-06-07",
  "dateModified": "2026-06-07",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
