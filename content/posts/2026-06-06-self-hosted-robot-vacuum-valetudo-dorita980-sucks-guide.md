---
title: "Self-Hosted Robot Vacuum Cloud Replacement: Valetudo vs Dorita980 vs Sucks"
date: "2026-06-06"
tags: ["robot-vacuum", "smart-home", "iot", "privacy", "home-automation", "valetudo", "roomba", "ecovacs"]
draft: false
---

## Why Replace Your Robot Vacuum's Cloud?

Modern robot vacuums from Xiaomi, iRobot, and ECOVACS are powerful cleaning assistants — but they come with a hidden cost: every map of your home, every cleaning schedule, and every floor plan is uploaded to a manufacturer's cloud server. With open-source cloud replacement projects, you can reclaim full local control of your robot vacuum while maintaining all smart features.

Self-hosting your vacuum's "brain" means your floor plans never leave your home network, you're protected from manufacturer API shutdowns, and you gain integration capabilities that cloud-locked vacuums can't offer — MQTT integration with Home Assistant, custom automation scripts, and fine-grained control over cleaning behavior. However, not all vacuums are created equal when it comes to hackability.

In this guide, we compare three leading open-source projects for three major vacuum ecosystems: **Valetudo** for Xiaomi/Roborock vacuums, **Dorita980** for iRobot Roomba devices, and **Sucks** for ECOVACS Deebot models. Each takes a fundamentally different approach to cloud replacement.

## Comparison at a Glance

| Feature | Valetudo | Dorita980 | Sucks |
|---------|----------|-----------|-------|
| **Supported Brands** | Roborock, Xiaomi, Dreame | iRobot Roomba, Braava | ECOVACS Deebot |
| **Stars** | 9,162 | 1,175 | 293 |
| **Language** | JavaScript | JavaScript | Python |
| **Deployment** | Runs on vacuum itself | External server/library | External script/library |
| **Web UI** | Full React-based dashboard | None (library only) | None (CLI/library) |
| **MQTT Support** | Native (Homie convention) | Via external bridge | Manual integration |
| **Map Display** | Interactive floor plan | Needs separate frontend | No native map support |
| **Last Update** | June 2026 | February 2026 | May 2020 |
| **Root Required** | Yes (hardware root) | No (local Wi-Fi API) | No (local Wi-Fi API) |
| **License** | Apache 2.0 | MIT | MIT |

## Valetudo: The Full Cloud Replacement

Valetudo is the most mature and fully-featured robot vacuum cloud replacement, with over 9,000 GitHub stars and an active community. It runs **directly on the vacuum itself** — you root the robot's embedded Linux system and install Valetudo as a replacement for the manufacturer's cloud-connected software stack.

### Key Features

- **Local-only operation**: All maps, schedules, and cleaning data stay on the device
- **Full web dashboard**: Interactive React UI with live map display, zone cleaning, and history
- **Native MQTT**: Full Home Assistant auto-discovery via Homie MQTT convention
- **No external server needed**: The vacuum becomes a self-contained smart device

### Installation Overview

Valetudo requires rooting your vacuum, which involves physical disassembly on newer models:

```bash
# After rooting via USB/serial (varies by model):
# Download the latest Valetudo binary for your vacuum arch
wget https://github.com/Hypfer/Valetudo/releases/latest/download/valetudo-armv7
# Push to vacuum and install
scp valetudo root@192.168.1.100:/usr/local/bin/valetudo
ssh root@192.168.1.100 "chmod +x /usr/local/bin/valetudo && reboot"
# Valetudo web UI available at http://<vacuum-ip>
```

Valetudo exposes a REST API and MQTT interface that Home Assistant auto-discovers:

```yaml
# Home Assistant auto-discovered via MQTT — no manual config needed
# Valetudo appears as vacuum entity with all controls:
# - Start/pause/stop/return to dock
# - Zone cleaning with map coordinates
# - Fan speed and water flow control
# - Sensor data (battery, bin status, consumables)
```

## Dorita980: The Roomba Library

Dorita980 is a JavaScript library that communicates with iRobot Roomba vacuums over your local network — **no rooting required**. Instead of replacing the vacuum's firmware, Dorita980 uses the local Wi-Fi API that Roomba devices expose. This makes it the most accessible option for Roomba owners who want local control without hardware modification.

```bash
# Install as a Node.js dependency
npm install dorita980

# Or use the CLI to discover your Roomba
npx dorita980 discover
```

### Key Aspects

- **No rooting needed**: Uses iRobot's local HTTP API — just know your Roomba's IP and credentials
- **Library-first design**: Designed to be integrated into larger home automation systems
- **Bluetooth provisioning**: Helper tools for getting Roomba credentials during initial setup
- **Active maintenance**: Updated through early 2026 with support for i7, i7+, 980, 960, and newer models

A minimal Node.js script to control your Roomba:

```javascript
const dorita980 = require('dorita980');
const robot = new dorita980.Local('username', 'password', '192.168.1.50');

robot.on('connect', () => {
  robot.start();       // Start cleaning
  // robot.pause();    // Pause
  // robot.dock();     // Return to dock
  // robot.cleanRoom({pmap_id: 'room1', user_pmapv_id: 'map1'});
});

robot.on('state', (state) => {
  console.log('Battery:', state.batPct + '%');
  console.log('Phase:', state.cleanMissionStatus.phase);
});
```

## Sucks: ECOVACS Deebot Control

Sucks is a Python library for controlling ECOVACS Deebot vacuums over the local network. Like Dorita980, it uses the vacuum's local API rather than flash replacement. While less actively maintained (last update May 2020), it still works with many Deebot models and provides a solid foundation for Home Assistant integration.

```bash
pip install sucks
```

```python
from sucks import EcoVacsAPI, VacBot
import time

# Authenticate with ECOVACS account (needed for device discovery)
api = EcoVacsAPI('device_id', 'email@example.com', 'password_hash', 'CN')
devices = api.devices()

for device in devices:
    if device['class'] == 'Robot':
        bot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, device, 'CN')
        
        # Start cleaning
        bot.run(Clean())
        time.sleep(10)
        # Return to dock
        bot.run(Charge())
```

### Important Notes

- **ECO contrast authentication required**: You still need ECOVACS credentials to discover devices
- **Python ecosystem**: Easy to integrate with Home Assistant and other Python-based automation
- **Device support**: Covers most Deebot Ozmo, N79, and 900-series models
- **Maintenance status**: Community-maintained; core functionality stable despite infrequent updates

## Choosing the Right Solution

Your choice depends primarily on which vacuum brand you own and your comfort level with hardware modification:

- **Choose Valetudo** if you own a compatible Xiaomi/Roborock vacuum and are willing to root it. You get the best local-control experience with a full web dashboard and native MQTT support.
- **Choose Dorita980** if you own an iRobot Roomba and want local control without disassembling your vacuum. The JavaScript library is production-ready and actively maintained.
- **Choose Sucks** if you own an ECOVACS Deebot. While less actively maintained, it provides the essential local control primitives and integrates well with Python-based automation stacks.

## Why Self-Host Your Robot Vacuum Control?

Robot vacuums are some of the most privacy-invasive IoT devices in modern homes — they literally map your floor plan, room by room. When you send this data to a manufacturer's cloud, you're trusting a corporation with an intimate blueprint of your living space. Consider what happens when the manufacturer discontinues cloud support (as iRobot announced for legacy models in 2024), or when a data breach exposes millions of home floor plans.

Self-hosting returns ownership of your data to you. Your floor plans exist only on your local network. Your cleaning schedules run without an internet connection. And you're protected against the manufacturer pivoting to a subscription model or shutting down cloud services entirely. For Home Assistant users, self-hosted vacuum control also means tighter integration — your vacuum can respond to presence detection (clean when everyone leaves), integrate with alarm systems (return to dock when armed), and participate in complex automations that cloud-connected vacuums can't support.

The three projects covered here — Valetudo, Dorita980, and Sucks — represent different philosophies in the self-hosted vacuum space. Valetudo takes the most aggressive approach (firmware replacement) but delivers the best experience. Dorita980 and Sucks take a lighter-touch approach (local API wrappers) that's easier to set up but leaves some manufacturer firmware intact. Your choice depends on your hardware, your risk tolerance, and how much control you want.

For broader smart home integration strategies, see our [Zigbee2MQTT vs Z-Wave JS UI vs ESPHome comparison](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/). If you're building a comprehensive IoT infrastructure, our [MQTT platform guide](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) covers the messaging backbone that powers most vacuum integrations. And for a full smart home ecosystem approach, our [IoT platform comparison](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/) explores ThingsBoard, IoTSharp, and IoT DC3.

## FAQ

### Do I need to root my robot vacuum to use these tools?

Only Valetudo requires rooting (hardware modification). Dorita980 and Sucks use the vacuum's existing local Wi-Fi API, which requires knowing your device credentials but no physical modification. Rooting difficulty varies by model — newer Roborock vacuums require soldering and UART access.

### Will I lose warranty by installing Valetudo?

Yes, rooting your vacuum typically voids the manufacturer warranty. If warranty coverage is important to you, consider Dorita980 (Roomba) or Sucks (Deebot) as they use the local API without modification.

### Can I still use the manufacturer app alongside these tools?

With Dorita980 and Sucks, yes — the manufacturer app continues to work normally since the vacuum's cloud connection remains intact. With Valetudo, no — the cloud connection is permanently severed, which is by design for privacy.

### Which vacuum brand is the most hackable?

Xiaomi/Roborock vacuums have the most mature open-source ecosystem thanks to Valetudo (9,000+ stars, active community). iRobot Roomba devices have solid library support through Dorita980 and related projects. ECOVACS Deebot support is functional but less actively maintained.

### What happens if the manufacturer blocks local API access?

This is a real risk — manufacturers can push firmware updates that disable or change the local API. Valetudo mitigates this by completely replacing the firmware, making it immune to manufacturer changes. Dorita980 and Sucks users should disable automatic firmware updates on their vacuums.

### How do I integrate these with Home Assistant?

Valetudo has native Home Assistant auto-discovery via MQTT Homie. Dorita980 can be integrated via a REST-to-MQTT bridge or by writing a custom Home Assistant integration. Sucks has a Home Assistant integration maintained by the community under the "Ecovacs" integration.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Robot Vacuum Cloud Replacement: Valetudo vs Dorita980 vs Sucks",
  "description": "Comprehensive comparison of open-source robot vacuum cloud replacement tools: Valetudo for Xiaomi/Roborock, Dorita980 for iRobot Roomba, and Sucks for ECOVACS Deebot. Learn how to self-host your vacuum control for privacy and local automation.",
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
