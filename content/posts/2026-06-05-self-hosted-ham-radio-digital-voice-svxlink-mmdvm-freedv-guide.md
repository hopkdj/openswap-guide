---
title: "Self-Hosted Ham Radio Digital Voice Gateways & Repeater Linking: SvxLink vs MMDVM vs FreeDV"
date: "2026-06-05"
tags: ["ham-radio", "amateur-radio", "digital-voice", "repeater", "self-hosted", "raspberry-pi", "voip", "communication"]
draft: false
---

## Introduction

Amateur radio has evolved far beyond analog voice. Today's ham radio operators use digital voice modes, IP-based repeater linking, and software-defined radio to build global communication networks — all from a self-hosted Linux server in the shack. Whether you're running a repeater site, building a digital voice hotspot, or experimenting with HF digital modes on a Raspberry Pi, open source software makes it possible.

In this guide, we compare three leading self-hosted amateur radio digital voice and repeater linking platforms: **SvxLink** (a general-purpose repeater controller and linking server), **MMDVMHost** (the standard for multi-mode digital voice hotspots), and **FreeDV** (an open-source digital voice codec for HF radio). We'll cover setup, Docker deployment, hardware requirements, and use cases to help you choose the right tool for your station.

## Comparison Table

| Feature | SvxLink | MMDVMHost | FreeDV |
|---------|---------|-----------|--------|
| **Primary Use** | FM repeater controller, EchoLink gateway, remote base | Multi-mode digital voice hotspot (DMR, D-STAR, Fusion, P25, NXDN) | HF digital voice codec (160m-10m) |
| **Stars** | 524 | 440 | 317 |
| **Language** | C++ | C++ | C / C++ |
| **License** | GPL-2.0 | GPL-2.0 | LGPL-2.1 |
| **Hardware Required** | Sound card + radio interface | MMDVM modem board (~$30) + Raspberry Pi | SSB transceiver + computer sound card |
| **Supported Modes** | FM, EchoLink, DTMF, CTCSS, remote base | DMR, D-STAR, YSF/C4FM, P25, NXDN, M17, POCSAG | FreeDV 1600/700D/700E/2020 modes |
| **Web Interface** | No (terminal/CLI) | Via Pi-Star / WPSD dashboard | FreeDV GUI application |
| **Docker Support** | Unofficial (community images) | Via Pi-Star image | Via FreeDV GUI |
| **Repeater Linking** | ✅ SvxLink Reflector protocol | ✅ Via BrandMeister / TGIF / DMR+ networks | ❌ (peer-to-peer only) |
| **Raspberry Pi** | ✅ (RPi 3B+ or better) | ✅ (native RPi target) | ✅ (RPi 4 recommended) |
| **Active Development** | ✅ (May 2026) | ✅ (May 2026) | ✅ (June 2026) |

## SvxLink: The Swiss Army Knife of Repeater Control

SvxLink is a general-purpose voice services system for Linux. Originally developed as an EchoLink client for Linux, it has grown into a full-featured repeater controller, remote base station, and VoIP linking platform. It's the backbone of many VHF/UHF repeater systems worldwide.

### Key Capabilities

- **FM Repeater Controller**: Full logic for repeater operation — squelch detection, CTCSS encode/decode, courtesy tones, ID announcements, and timeout timers
- **EchoLink Gateway**: Connect your repeater to the worldwide EchoLink network (over 300,000 registered users)
- **Remote Base**: Control a remote transceiver over IP — change frequencies, modes, and power levels
- **SvxLink Reflector**: Link multiple repeaters and simplex nodes together over the internet
- **DTMF Control**: Full DTMF command set for remote control of repeater functions

### Docker Compose Setup

```yaml
version: "3.8"
services:
  svxlink:
    image: lnxsrv/svxlink:latest
    container_name: svxlink
    devices:
      - /dev/snd:/dev/snd  # USB sound card
    volumes:
      - ./svxlink-config:/etc/svxlink
      - ./svxlink-events:/usr/share/svxlink/events
    ports:
      - "5198:5198/udp"  # EchoLink
      - "5199:5199/udp"  # EchoLink
      - "5300:5300/udp"  # SvxLink Reflector
    restart: unless-stopped
    privileged: true  # Required for real-time audio
```

### Minimal Configuration

```ini
# /etc/svxlink/svxlink.conf
[GLOBAL]
MODULE_PATH=/usr/lib/arm-linux-gnueabihf/svxlink
LOGICS=RepeaterLogic

[RepeaterLogic]
TYPE=Repeater
MODULES=ModuleEchoLink
CALLSIGN=YOURCALL
SHORT_IDENT_INTERVAL=10
LONG_IDENT_INTERVAL=60

[ModuleEchoLink]
NAME=EchoLink
CALLSIGN=YOURCALL-L
PASSWORD=yourpassword
SYSOPNAME=Your Name
LOCATION=Your City, ST
```

## MMDVMHost: The Multi-Mode Digital Voice Standard

MMDVM (Multi-Mode Digital Voice Modem) is the de facto standard for amateur radio digital voice hotspots. MMDVMHost is the host software that interfaces with an MMDVM modem board to bridge multiple digital voice modes — DMR, D-STAR, YSF/C4FM (System Fusion), P25, NXDN, and the open-source M17 protocol.

A typical setup costs under $100: a Raspberry Pi Zero 2 W ($15) plus an MMDVM duplex hotspot board ($30-50) and an antenna. This tiny device creates a personal digital voice access point that connects your handheld radio to worldwide digital networks via your home internet.

### Pi-Star Dashboard Deployment

The most common deployment method is Pi-Star, a purpose-built Raspberry Pi OS image:

```bash
# Download and flash Pi-Star to SD card
wget https://www.pistar.uk/downloads/Pi-Star_RPi_V4.3.0_2025-01-01.zip
unzip Pi-Star_RPi_V4.3.0_2025-01-01.zip
sudo dd if=Pi-Star_RPi_V4.3.0_2025-01-01.img of=/dev/sdX bs=4M status=progress

# After boot, access web dashboard at http://pistar.local
# Configure via browser: mode, frequency, network credentials
```

### MMDVMHost Configuration

```ini
# /etc/mmdvmhost
[General]
Callsign=YOURCALL
Id=123456701  # DMR ID
Timeout=240
Duplex=1
RFHangTime=20
NetHangTime=20

[Modem]
Protocol=UART
UARTPort=/dev/ttyAMA0
UARTSpeed=115200
TXFrequency=438800000
RXFrequency=438800000

[DMR]
Enable=1
ColorCode=1
SelfOnly=0

[DMR Network]
Enable=1
Address=3103.repeater.net
Port=62031
Jitter=360
Password=passw0rd
```

### Supported Networks

- **BrandMeister**: Largest worldwide DMR network (5,000+ repeaters)
- **TGIF Network**: Community-focused DMR talkgroup network
- **DMR+ (IPSC2)**: Motorola-based DMR network infrastructure
- **YSF Reflectors**: Yaesu System Fusion rooms (FCS, YSF)
- **D-STAR Reflectors**: REF, XRF, DCS, and XLX reflectors

## FreeDV: Open Source HF Digital Voice

FreeDV takes a fundamentally different approach: instead of bridging existing proprietary digital voice modes, it's an entirely open-source digital voice codec designed specifically for HF (high frequency) bands. It compresses speech to 700-1600 bits per second — narrow enough to fit within a standard SSB channel — while providing superior noise resilience.

### How FreeDV Works

FreeDV encodes your voice using the open **Codec 2** speech codec (as low as 700 bit/s), adds forward error correction, and modulates the result onto an SSB radio carrier. The receiving station demodulates and decodes the signal back to voice. The entire chain is open and patent-free.

### Connection to Your Transceiver

```
Microphone → Computer (FreeDV encodes) → USB Sound Card → SSB Transmitter
                                                                  ↓ (RF)
Speaker    ← Computer (FreeDV decodes) ← USB Sound Card ← SSB Receiver
```

### FreeDV Compose File

```yaml
version: "3"
services:
  freedv-gui:
    image: ghcr.io/drowe67/freedv-gui:latest
    container_name: freedv
    devices:
      - /dev/snd:/dev/snd
    environment:
      - DISPLAY=${DISPLAY}
      - PULSE_SERVER=unix:/run/pulse/native
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
      - /run/user/1000/pulse:/run/pulse
    network_mode: host
    restart: unless-stopped
```

### FreeDV Modes Comparison

| Mode | Bit Rate | Bandwidth | Range | Use Case |
|------|----------|-----------|-------|----------|
| 1600 | 1600 bit/s | 1125 Hz | Short-Medium | High quality, local nets |
| 700D | 700 bit/s | 1125 Hz | Medium-Long | General purpose |
| 700E | 700 bit/s | 1125 Hz | Medium-Long | Enhanced FEC |
| 2020 | 2020 bit/s | 1600 Hz | Short | FM-quality on HF |
| 2020B | 1700 bit/s | 1600 Hz | Short-Medium | Broadcast mode |

## Hardware Requirements

Each platform requires different hardware interfacing:

| Component | SvxLink | MMDVMHost | FreeDV |
|-----------|---------|-----------|--------|
| **Computer** | Raspberry Pi 3B+ or x86 Linux | Raspberry Pi Zero 2 W / 3B / 4 | Raspberry Pi 4 / x86 Linux |
| **Radio Interface** | USB sound card + PTT circuit (GPIO) | MMDVM modem board (STM32F4 or similar) | Two USB sound cards (TX + RX) |
| **Radio** | Any FM transceiver with discriminator tap | Any DMR/D-STAR/Fusion HT or mobile | Any SSB HF transceiver |
| **Antenna** | Standard VHF/UHF | VHF/UHF whip (hotspot range ~50m) | HF antenna (dipole, vertical, beam) |
| **Network** | Internet for EchoLink/Reflector linking | Internet for digital network bridging | None required (peer-to-peer) |
| **Total Cost (approx)** | $80-150 | $50-80 | $50-100 + HF transceiver |

## Why Self-Host Your Ham Radio Gateway?

Running your own digital voice server gives you complete control over your amateur radio operations. A self-hosted setup on a Linux server or Raspberry Pi means no recurring fees, no cloud dependency, and the ability to customize every aspect of your station.

When you self-host SvxLink, you own your EchoLink gateway and repeater logic — no third party can shut it down or change the rules. With a self-hosted MMDVM hotspot, you control which talkgroups and reflectors you connect to, without relying on someone else's bridge. Running FreeDV locally means your digital voice transmissions are truly open-source from microphone to antenna, with no proprietary codecs or patent licensing fees.

For related infrastructure, see our [self-hosted server management guide](../2026-04-27-cockpit-vs-webmin-vs-ajenti-self-hosted-server-management-web-ui-guide-2026/) to remotely administer your shack computer, and our [WireGuard mesh networking guide](../2026-05-15-self-hosted-wireguard-mesh-networking-webmesh-wirespider-edge-core-guide/) for securely linking repeaters over the internet. If you're integrating ham radio with home automation, check our [Home Assistant smart home hub comparison](../2026-04-28-home-assistant-vs-homebridge-vs-scrypted-self-hosted-smart-home-hub-guide-2026/).

Ham radio operators have been self-hosting long before "self-hosting" was a tech buzzword — packet radio BBSes, DX clusters, and APRS igates have run on home servers for decades. Modern open-source tools make it easier than ever to build sophisticated digital voice systems on commodity hardware.

Setting up your own digital voice gateway also deepens your understanding of the technology. Instead of buying a commercial hotspot and treating it as a black box, building one yourself teaches you about codec negotiation, network routing, and RF fundamentals — skills that make you a better operator.

## FAQ

### Do I need an amateur radio license to use these tools?

**Yes.** All three tools are designed for licensed amateur radio operators. SvxLink transmits on VHF/UHF ham bands, MMDVMHost operates on amateur digital voice frequencies, and FreeDV transmits on HF amateur bands. You must hold a valid amateur radio license (Technician or higher in the US, Foundation or higher in the UK) to legally transmit with these tools. However, you can install and configure them for receive-only operation without a license for learning purposes.

### Can I run SvxLink and MMDVMHost on the same Raspberry Pi?

**Yes, with caveats.** A Raspberry Pi 4 with 4GB RAM can run both simultaneously if you have sufficient USB ports for the sound card (SvxLink) and MMDVM modem board (MMDVMHost). However, both applications need real-time audio processing, so CPU contention can cause audio dropouts on a Pi 3B+. For critical repeater operations, dedicate one Pi per application.

### What's the difference between a "hotspot" and a "repeater"?

A **hotspot** (like what MMDVMHost creates) is a low-power, short-range device (typically 10mW output, ~50m range) that bridges your handheld radio to internet-linked digital voice networks. It's for personal use at home. A **repeater** is a high-power, wide-coverage station (typically 25-100W, 10-50km range) that retransmits signals to extend range for all users in an area. SvxLink is designed for full repeater control, while MMDVMHost is optimized for personal hotspots (though it can drive repeaters with a power amplifier).

### Is FreeDV compatible with other digital voice modes like DMR or D-STAR?

**No.** FreeDV uses its own open-source Codec 2, which is fundamentally different from the proprietary AMBE+2 codec used in DMR, D-STAR, and Fusion. They are not interoperable. FreeDV is designed for HF bands (below 30 MHz), while DMR/D-STAR/Fusion operate on VHF/UHF (above 30 MHz). Think of them as complementary tools: FreeDV for long-distance HF digital voice, MMDVM-based systems for local VHF/UHF digital communications.

### How do I link my SvxLink repeater to other repeaters?

SvxLink supports two linking methods: **EchoLink** (the most widely used, connecting to 300,000+ users worldwide) and the **SvxLink Reflector** protocol (native SvxLink-to-SvxLink linking with lower latency). To link to a reflector, configure the `[ReflectorLogic]` section in `svxlink.conf` with the reflector's hostname and port. Multiple repeaters can connect to the same reflector, creating a wide-area linked system.

### Can these tools work without internet?

**SvxLink:** Yes, as a standalone FM repeater controller. Internet is only needed for EchoLink and reflector linking. **MMDVMHost:** The hotspot needs internet to connect to digital networks (BrandMeister, etc.), but the modem board can operate in simplex "parrot" mode without internet for local testing. **FreeDV:** Yes — it's completely peer-to-peer over HF radio, no internet required for operation. This makes it ideal for emergency communications when internet infrastructure is unavailable.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Ham Radio Digital Voice Gateways & Repeater Linking: SvxLink vs MMDVM vs FreeDV",
  "description": "Comprehensive comparison of open-source amateur radio digital voice platforms: SvxLink for repeater control, MMDVMHost for multi-mode hotspots, and FreeDV for HF digital voice. Includes Docker Compose configs and setup guides.",
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
