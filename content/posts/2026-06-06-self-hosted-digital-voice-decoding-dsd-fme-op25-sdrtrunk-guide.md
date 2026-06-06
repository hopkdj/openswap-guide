---
title: "Self-Hosted Digital Voice Decoding: dsd-fme vs OP25 vs SDRTrunk for P25/DMR/NXDN Radio"
date: "2026-06-06"
tags: ["sdr", "radio", "digital-voice", "p25", "dmr", "nxdn", "decoding", "ham-radio", "signal-processing"]
draft: false
---

## Introduction

Digital voice has transformed land mobile radio. Public safety agencies, transit systems, utilities, and amateur radio operators have migrated from analog FM to digital protocols like P25 (Phase 1 and 2), DMR (Digital Mobile Radio), NXDN, and TETRA. For radio hobbyists, researchers, and interoperability developers, decoding these digital voice streams requires specialized software that can demodulate the complex digital modulation schemes and reconstruct intelligible audio.

Three open-source tools lead the field: **dsd-fme** (Digital Speech Decoder – Florida Man Edition, 348 stars) — a focused command-line decoder rebuilt from the original DSD project; **OP25** (462 stars) — a specialized P25 Phase 1 and 2 decoder originally developed for the Osmocom project; and **SDRTrunk** (2,100 stars) — a full-featured Java application for trunked radio system monitoring, recording, and streaming.

This guide compares all three tools across supported protocols, audio quality, resource usage, and deployment patterns, with practical configuration examples for each.

## Comparison Table

| Feature | dsd-fme | OP25 | SDRTrunk |
|---------|---------|------|----------|
| **GitHub Stars** | 348 | 462 | 2,100 |
| **Language** | C/C++ | C++/Python | Java |
| **Last Updated** | May 2026 | June 2026 | June 2026 |
| **P25 Phase 1** | Yes | Yes (primary focus) | Yes |
| **P25 Phase 2** | Yes (experimental) | Yes (full support) | Yes |
| **DMR (MotoTRBO)** | Yes | No | Yes |
| **NXDN (Kenwood/ICOM)** | Yes | No | Yes |
| **TETRA** | Partial | No | No |
| **ProVoice (EDACS)** | Yes | No | No |
| **Trunking Support** | Limited (manual) | Full P25 trunking | Full multi-protocol trunking |
| **GUI** | CLI only | CLI + optional web | Web UI + desktop GUI |
| **Audio Streaming** | Local audio + TCP | Local audio | Built-in streaming server |
| **Recording** | Per-call WAV files | Per-call WAV | Built-in recorder + playlist |
| **Multi-VFO** | Single channel | Multi-channel | Multi-channel + priority |
| **Docker Support** | Community Dockerfile | Manual build | Official Docker image |
| **Resource Usage** | Very Low (50-100 MB) | Moderate (200-500 MB) | High (1-4 GB, Java VM) |
| **Learning Curve** | Moderate | Steep | Easy-Moderate |
| **Raspberry Pi** | Yes (Pi 3+) | Yes (Pi 4, 2 GB+) | No (needs 4+ GB RAM) |

## dsd-fme: The Focused Digital Speech Decoder

dsd-fme (Digital Speech Decoder – Florida Man Edition) is a reboot of the classic DSD project, rewritten and maintained with modern compiler support and expanded protocol coverage. It's the go-to tool for rapid decoding of individual digital voice channels — simple, lightweight, and highly effective.

### Architecture

dsd-fme follows a clean Unix pipeline philosophy: audio from an SDR source flows through a demodulator chain specific to each protocol, then through a voice codec (IMBE, AMBE, AMBE+2), and finally to your speakers or a WAV file.

```
┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────┐
│ SDR Audio│───▶│ Demodulator   │───▶│ Vocoder     │───▶│ Audio Out│
│ Source   │    │ P25/DMR/NXDN │    │ IMBE/AMBE   │    │ Speakers │
└──────────┘    └──────────────┘    └────────────┘    └──────────┘
```

### Installation & Basic Usage

```bash
# Clone and build
git clone https://github.com/lwvmobile/dsd-fme
cd dsd-fme
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install

# Decode P25 Phase 1 from an RTL-SDR
rtl_fm -f 855.0125e6 -s 24000 -g 49.6 -p 0 |   dsd-fme -i - -o /dev/dsp -fr

# Decode DMR with auto protocol detection
rtl_fm -f 452.550e6 -s 48000 -g 49.6 |   dsd-fme -i - -o /dev/dsp -fa
```

### Key Features

**Protocol Auto-Detection**: dsd-fme can automatically identify the digital protocol in use and switch decoders accordingly — useful when monitoring unknown frequencies:

```bash
# -fa enables auto-detection of P25/DMR/NXDN/ProVoice
dsd-fme -i input.wav -o output.wav -fa
```

**Per-Call Recording with Metadata**:

```bash
# Record each call to a separate WAV file with metadata
dsd-fme -i rtl_input -o /recordings/call -fr   --per-call-output   --call-metadata-file=/recordings/calls.csv
```

**Low Resource Footprint**: dsd-fme typically uses 50-100 MB of RAM and minimal CPU — it runs comfortably on a Raspberry Pi 3 alongside rtl_fm.

## OP25: The P25 Specialist

OP25 (originally "Osmocom P25") is the reference implementation for P25 digital radio decoding. It implements the complete TIA-102 P25 standard for both Phase 1 (FDMA, 12.5 kHz channels) and Phase 2 (TDMA, two-slot 6.25 kHz equivalent) with support for trunked radio system following.

### Why OP25 for P25?

While dsd-fme and SDRTrunk both decode P25, OP25 offers the most complete and standards-compliant implementation. It's the tool of choice for:

- **P25 trunking system analysis** — following control channel grants and hopping to voice channels automatically
- **Phase 2 TDMA decoding** — the most mature open-source Phase 2 implementation available
- **Encryption identification** — identifies encryption algorithms (ADP, DES-OFB, AES-256) even without keys
- **Low-level protocol analysis** — detailed P25 frame structure logging and diagnostics

### Installation

```bash
git clone https://github.com/boatbod/op25
cd op25
./install.sh

# Configure for your SDR and target P25 system
cd op25/gr-op25_repeater/apps
./rx.py --args 'rtl'   --gains 'lna:49'   -f 855.0125e6   -S 24000   -q 0   -T trunk.tsv   -V   -U   -w 2> stderr.log
```

### P25 Trunking Configuration

OP25 uses a TSV file (`trunk.tsv`) to define the trunked radio system parameters:

```tsv
"Sysname"	"Control Channel List"	"Offset"	"NAC"	"Modulation"	"TGID Tags File"	"Whitelist"	"Blacklist"	"Center Frequency"
"County Simulcast"	"855.0125,855.2625,855.5125,855.7625"	"0"	"0x1A7"	"CQPSK"	"county-tags.tsv"	""	""	"855.5"
```

The companion `county-tags.tsv` file maps talkgroup IDs to human-readable labels:

```tsv
1001	Police Dispatch
1003	Fire Dispatch
1005	EMS Operations
2001	Sheriff Tactical
3001	Public Works
```

### Docker Deployment

```yaml
version: '3.8'
services:
  op25:
    image: ghcr.io/boatbod/op25:latest
    container_name: op25
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./op25_config:/app/config
      - ./op25_audio:/app/audio
      - ./op25_logs:/app/logs
    environment:
      - PULSE_SERVER=unix:/run/pulse/native
    restart: unless-stopped
    privileged: true
```

## SDRTrunk: The Full-Featured Trunking Monitor

SDRTrunk is the most polished and user-friendly option, offering a modern web interface, built-in streaming server, and support for multiple trunking protocols simultaneously. It's written in Java and runs as a self-contained application with no external dependencies.

### Architecture

SDRTrunk uses a multi-channel architecture where a single SDR can be split across multiple virtual tuners, each decoding a different frequency or protocol:

```
                 ┌──────────────────┐
                 │    SDRTrunk      │
                 │                  │
  ┌──────────┐   │  ┌────────────┐  │   ┌──────────────┐
  │ RTL-SDR  │───▶──│ Channel 1  │──▶──│ P25 Decoder   │──▶ Audio + Stream
  │ (2.4 MHz)│   │  │ (P25 CC)   │  │   └──────────────┘
  └──────────┘   │  └────────────┘  │
                 │  ┌────────────┐  │   ┌──────────────┐
                 │  │ Channel 2  │──▶──│ DMR Decoder   │──▶ Audio + Stream
                 │  │ (DMR VC)   │  │   └──────────────┘
                 │  └────────────┘  │
                 │  ┌────────────┐  │   ┌──────────────┐
                 │  │ Channel 3  │──▶──│ NXDN Decoder  │──▶ Audio + Stream
                 │  │ (NXDN VC)  │  │   └──────────────┘
                 └──────────────────┘
```

### Docker Deployment

SDRTrunk has the best Docker support of the three tools:

```yaml
version: '3.8'
services:
  sdrtrunk:
    image: ghcr.io/dsheirer/sdrtrunk:latest
    container_name: sdrtrunk
    ports:
      - "8080:8080"
      - "5000:5000"
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./sdrtrunk_config:/opt/sdrtrunk/config
      - ./sdrtrunk_recordings:/opt/sdrtrunk/recordings
    environment:
      - JAVA_OPTS=-Xmx2g -Xms512m
    restart: unless-stopped
```

### Web Interface Features

SDRTrunk's web UI (accessible at `http://localhost:8080`) provides:

- **Now Playing** — real-time display of active calls with talkgroup labels and durations
- **Channel Status** — per-channel signal quality, frequency, and protocol details
- **Recording Library** — browse and playback recorded calls with metadata search
- **Stream Management** — configure audio streaming to Icecast, Broadcastify, or custom endpoints
- **System Configuration** — add/edit P25, DMR, NXDN, and LTR systems through the UI

## Why Self-Host Your Digital Voice Decoder?

Setting up your own digital voice decoding station gives you direct access to radio communication monitoring without relying on commercial scanner apps or subscription services. Whether you're a ham radio operator experimenting with digital modes, a journalist monitoring public safety communications (where legally permitted), or a developer building radio interoperability systems, these tools put you in control.

### Complete Control Over Your Data

Commercial scanner streaming services decide what channels to monitor, apply audio processing, and may impose listening restrictions. A self-hosted setup lets you choose exactly which frequencies and talkgroups to decode, store recordings on your own storage, and apply custom audio processing pipelines.

### Learning and Experimentation

Digital radio is a complex stack — C4FM/QPSK modulation, IMBE/AMBE vocoders, trunking control channels, encryption algorithms. Building and operating your own decoder teaches you every layer. For those interested in the broader radio ecosystem, see our [SDR receiver comparison guide](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/) for general-purpose reception, and our [APRS packet radio infrastructure guide](../2026-06-05-self-hosted-aprs-packet-radio-infrastructure-direwolf-xastir-aprx-guide/) for amateur radio data modes.

## FAQ

### Is it legal to decode digital voice radio?

**Laws vary by jurisdiction.** In the United States, receiving unencrypted radio transmissions is generally legal under federal law, but some states restrict mobile scanner use in vehicles. In the UK, listening to transmissions not intended for general reception is technically illegal under the Wireless Telegraphy Act, though enforcement for hobbyist monitoring is rare. In most countries, decoding **encrypted** communications is illegal regardless. Always check your local regulations before setting up a monitoring station.

### What hardware do I need?

A single **RTL-SDR v3** ($25-35) can monitor a 2.4 MHz swath of spectrum, enough for a single P25 site or 2-3 DMR channels. For monitoring multiple trunking sites or frequency bands, use two or more SDRs. The **Airspy R2** ($169) offers 10 MHz bandwidth — enough for an entire P25 simulcast system. Pair with a discone or tuned antenna appropriate for your target frequency band.

### Which tool is best for beginners?

**SDRTrunk** is the most beginner-friendly. Its web UI eliminates command-line complexity, it auto-detects many system parameters, and its Docker deployment is straightforward. Start with SDRTrunk, then explore **dsd-fme** for lightweight single-channel decoding, and graduate to **OP25** for advanced P25 trunking analysis.

### Can I decode encrypted P25?

**No.** These tools can identify that encryption is in use (ADP, DES-OFB, or AES-256) and display the encryption algorithm and key ID, but they **cannot decrypt** the audio without the proper encryption key. Decrypting encrypted radio communications without authorization is illegal in virtually all jurisdictions.

### What's the difference between P25 Phase 1 and Phase 2?

**Phase 1** uses FDMA (Frequency Division Multiple Access) — one voice call per 12.5 kHz channel. **Phase 2** uses TDMA (Time Division Multiple Access) — two voice calls sharing the same 12.5 kHz channel by alternating time slots. Phase 2 effectively doubles capacity. Most new P25 systems are Phase 2 capable but fall back to Phase 1 for compatibility with older subscriber radios.

### Can these tools run 24/7 on a Raspberry Pi?

**dsd-fme** — yes, on a Pi 3 or better, decoding a single channel. **OP25** — yes on a Pi 4 with 2 GB RAM, for a single P25 system. **SDRTrunk** — not recommended; the Java VM overhead and multi-channel decoding demand 4+ GB RAM and active cooling. For 24/7 monitoring, a low-power x86 mini PC (Intel N100, ~$150) is the sweet spot for cost, performance, and reliability.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Digital Voice Decoding: dsd-fme vs OP25 vs SDRTrunk for P25/DMR/NXDN Radio",
  "description": "Comprehensive comparison of open-source digital voice decoding tools: dsd-fme (348 stars) for lightweight multi-protocol decoding, OP25 (462 stars) for P25 Phase 1/2 trunking, and SDRTrunk (2,100 stars) for full-featured trunked radio monitoring with web UI. Includes Docker Compose configs and trunking setup guides.",
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
