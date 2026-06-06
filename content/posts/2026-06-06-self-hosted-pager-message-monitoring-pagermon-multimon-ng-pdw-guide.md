---
title: "Self-Hosted Pager Message Monitoring: Pagermon vs multimon-ng vs Dire Wolf — Decoding POCSAG & FLEX with RTL-SDR"
date: "2026-06-06"
tags: ["pager", "pocsag", "flex", "sdr", "rtl-sdr", "radio-monitoring", "raspberry-pi", "self-hosted"]
draft: false
---

## Introduction

Pager networks — once the backbone of emergency communications and hospital messaging — are still actively broadcasting across the world. Using POCSAG (Post Office Code Standardisation Advisory Group) and FLEX protocols, these networks transmit numeric and alphanumeric messages over VHF and UHF frequencies. While commercial paging services have declined, many hospitals, fire departments, and industrial facilities still operate private paging systems — and with a $25 RTL-SDR dongle and open source software, you can monitor these transmissions from your own server.

Pager decoding isn't just about nostalgia. It's a practical way to monitor emergency service dispatch, hospital codes, and industrial alert systems in your area. This guide compares three open source tools for building a self-hosted pager monitoring station: **Pagermon**, **multimon-ng**, and **Dire Wolf**.

## How POCSAG and FLEX Decoding Works

POCSAG is the most widely used paging protocol, operating at 512, 1200, or 2400 bps on VHF/UHF frequencies. FLEX is a newer, higher-speed protocol (1600-6400 bps) developed by Motorola. The decoding pipeline follows this pattern:

1. **Frequency tuning**: RTL-SDR dongle tunes to a known pager frequency (commonly 148-174 MHz or 450-470 MHz)
2. **Demodulation**: The FM-demodulated audio is processed through a POCSAG/FLEX decoder that extracts the bitstream
3. **Message parsing**: The decoded bits are assembled into complete messages with capcodes (pager addresses), timestamps, and message content
4. **Display and alerting**: Messages are filtered, stored, and displayed on a web dashboard

Each tool in our comparison handles different stages of this pipeline. The key differentiator is whether you need a production-ready web dashboard (Pagermon), a universal decoder engine (multimon-ng), or an integrated solution that also supports other radio modes (Dire Wolf).

## Tool Comparison

| Feature | Pagermon | multimon-ng | Dire Wolf |
|---------|----------|-------------|-----------|
| **Language** | JavaScript/Node.js | C | C |
| **GitHub Stars** | 310+ | 1,108+ | 1,700+ |
| **Web Dashboard** | Built-in (full-featured) | None | None |
| **Protocol Support** | POCSAG, FLEX | POCSAG, FLEX, 30+ modes | POCSAG, APRS, AX.25 |
| **Database** | SQLite/PostgreSQL | N/A | N/A |
| **Alerting** | Push notifications, webhooks | None | None |
| **Message Filtering** | By capcode, content, time | None | None |
| **Headless Operation** | Full web UI | CLI only | CLI only |
| **Docker Support** | Manual setup | Compile from source | Package install |
| **Resource Usage** | ~150MB RAM (Node.js) | ~15MB RAM | ~30MB RAM |

### Pagermon: The Full-Featured Dashboard

Pagermon (`pagermon/pagermon`, 310+ stars) is a self-hosted, Node.js-based web application purpose-built for monitoring pager networks. Unlike command-line decoders that require technical expertise to interpret, Pagermon provides a clean, searchable dashboard with message filtering, alerting, and historical archives.

```bash
# Install Pagermon on Debian/Ubuntu
git clone https://github.com/pagermon/pagermon.git
cd pagermon
npm install
cp server/config/default.json server/config/local.json
# Edit local.json with your settings
npm start
```

```yaml
# systemd service for Pagermon + rtl_fm pipeline
[Unit]
Description=Pagermon Pager Monitor
After=network.target

[Service]
Type=simple
User=pagermon
WorkingDirectory=/opt/pagermon/server
ExecStart=/usr/bin/node app.js
Restart=always

[Install]
WantedBy=multi-user.target
```

Pagermon supports multiple receiver inputs — it can ingest data from `rtl_fm` + `multimon-ng` pipelines, SDRTrunk, or any source that outputs text-format pager messages. Its key strength is the message management layer: assign human-readable aliases to capcodes, set up webhook notifications for specific message patterns, and export message archives.

To feed Pagermon with decoded messages, you pipe the output of a decoder like multimon-ng into Pagermon's message ingestion API:

```bash
# Pipeline: rtl_fm → multimon-ng → Pagermon
rtl_fm -f 148.6375M -M fm -s 22050 | \
  multimon-ng -t raw -a POCSAG -f alpha /dev/stdin | \
  nc localhost 3001
```

### multimon-ng: The Universal Decoder

multimon-ng (`EliasOenal/multimon-ng`, 1,108+ stars) is the swiss army knife of radio signal decoding. It supports over 30 digital modes including POCSAG, FLEX, DTMF, CTCSS, AX.25, and more. For pager monitoring, it serves as the decode engine that sits between the SDR capture and the display layer.

```bash
# Build multimon-ng from source
git clone https://github.com/EliasOenal/multimon-ng.git
cd multimon-ng
mkdir build && cd build
cmake ..
make -j4
sudo make install

# Decode POCSAG from a captured WAV file
multimon-ng -t wav -a POCSAG capture.wav

# Live decode from rtl_fm
rtl_fm -f 148.6375M -M fm -s 22050 -g 49.6 | \
  multimon-ng -t raw -a POCSAG -f alpha -
```

multimon-ng's strength is its breadth — the same tool can decode pagers, APRS packets, DTMF tones, and marine DSC signals. This makes it ideal if you run multiple monitoring services from a single SDR dongle. However, it provides no database, web UI, or alerting — it's purely a decoder that outputs to stdout.

### Dire Wolf: The Multi-Purpose TNC

Dire Wolf is primarily known as an APRS (Automatic Packet Reporting System) software TNC for ham radio, but it also includes POCSAG decoding support. With 1,700+ stars across its ecosystem, Dire Wolf is battle-tested in amateur radio deployments worldwide.

```bash
# Install Dire Wolf
sudo apt-get install direwolf

# Configure direwolf.conf for POCSAG monitoring
cat > ~/direwolf.conf << 'EOF'
ADEVICE stdin null
CHANNEL 0
POCSAG 0
EOF

# Decode POCSAG via Dire Wolf
rtl_fm -f 148.6375M -M fm -s 22050 | \
  direwolf -c ~/direwolf.conf -r 22050 -
```

Dire Wolf's advantage is that it can simultaneously decode POCSAG and APRS traffic on the same SDR — useful for ham radio operators who want pager monitoring as a secondary function. However, its POCSAG support is more limited than dedicated decoders, lacking advanced FLEX support and multi-baud autodetection.

## Building a Complete Pager Monitoring Station

For a production-grade self-hosted pager monitor, the recommended stack combines the strengths of multiple tools:

```
RTL-SDR → rtl_fm (tuner) → multimon-ng (decoder) → Pagermon (dashboard + alerts)
```

This architecture gives you the flexibility of multimon-ng's multi-protocol decoding with Pagermon's polished web UI and alerting engine. On a Raspberry Pi 4, this stack consumes roughly 200MB of RAM and handles continuous decoding without issue.

## Why Self-Host Pager Monitoring?

While commercial pager monitoring services exist, they're typically expensive (hundreds of dollars per month) and designed for professional dispatch centers. Self-hosting gives you the same capabilities at zero recurring cost.

**Privacy and independence**: Your message archives stay on your hardware. No third party tracks which capcodes you're monitoring. In an era where some jurisdictions restrict public access to emergency communications, local monitoring ensures you maintain situational awareness.

**Custom alerting**: Pagermon's plugin system lets you create custom alerting rules — for example, send a Discord notification when a specific hospital code is broadcast, or log all fire department dispatches to a separate database. Commercial services don't offer this level of customization.

**Educational value**: Setting up a pager monitoring station teaches fundamental radio concepts — frequency allocation, modulation types, digital encoding schemes — that apply broadly across RF engineering and SDR experimentation.

For related radio monitoring projects, see our [APRS packet radio guide](../2026-06-05-self-hosted-aprs-packet-radio-infrastructure-direwolf-xastir-aprx-guide/), our [digital voice decoding comparison](../2026-06-06-self-hosted-digital-voice-decoding-dsd-fme-op25-sdrtrunk-guide/), and our [SDR receiver platform overview](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/) for general-purpose software-defined radio servers.

## FAQ

### Is it legal to monitor pager frequencies?

Laws vary significantly by jurisdiction. In the United States, the Electronic Communications Privacy Act (ECPA) generally permits receiving unencrypted radio communications. However, some states have additional restrictions on monitoring emergency service frequencies. In the UK and EU, listening to transmissions not intended for general reception may be restricted. Always check local laws before setting up a monitoring station.

### What frequencies should I scan for pager signals?

Common POCSAG/FLEX pager frequencies include 148-149 MHz, 152-159 MHz, 163-170 MHz, 450-455 MHz, and 460-465 MHz. In the US, 152.0075 MHz, 157.740 MHz, and 462.925 MHz are widely used. Use `rtl_power` to scan your local spectrum for strong narrowband FM signals, then tune to each candidate with `rtl_fm` and check for the characteristic POCSAG preamble tone.

### How can I identify what each capcode represents?

Capcodes map to individual pagers, and their meaning comes from context. Hospital pagers typically broadcast medical codes ("Code Blue ICU"), fire department pagers contain incident addresses, and industrial pagers may have equipment status updates. Over time, you'll learn the patterns — Pagermon's alias feature lets you label each capcode with human-readable descriptions as you identify them.

### Can Pagermon send alerts to my phone?

Yes. Pagermon supports multiple notification plugins including Pushover, Slack, Discord webhooks, Telegram, and email. You can configure per-capcode alerting rules — for example, get a push notification for the fire department dispatch capcode but only log the hospital pager capcodes to the database.

### What's the difference between POCSAG and FLEX?

POCSAG is the older, simpler protocol (introduced 1978) with fixed baud rates (512/1200/2400 bps). FLEX is Motorola's newer protocol (1993) with higher speeds (1600/3200/6400 bps), better error correction, and support for binary data. Most modern paging infrastructure uses FLEX, but many legacy hospital and fire systems still run POCSAG. multimon-ng decodes both; Pagermon displays both.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Pager Message Monitoring: Pagermon vs multimon-ng vs Dire Wolf — Decoding POCSAG & FLEX with RTL-SDR",
  "description": "Complete guide to building a self-hosted pager monitoring station. Compare Pagermon, multimon-ng, and Dire Wolf for POCSAG and FLEX decoding, with setup instructions, Docker Compose configs, and FAQ.",
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
