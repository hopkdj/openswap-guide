---
title: "Self-Hosted RF Signal Analysis: Universal Radio Hacker vs SigDigger vs inspectrum Compared"
date: "2026-06-06"
tags: ["sdr", "radio", "signal-analysis", "reverse-engineering", "wireless", "rf", "spectrum", "iot", "security"]
draft: false
---

## Introduction

The electromagnetic spectrum is crowded with signals — Wi-Fi, Bluetooth, Zigbee, LoRa, proprietary IoT protocols, garage door openers, car key fobs, weather sensors, and countless other wireless devices. Understanding what's being transmitted around you requires specialized signal analysis tools that can capture, visualize, demodulate, and even reverse-engineer unknown radio protocols.

Three open-source tools form the backbone of RF signal analysis: **Universal Radio Hacker (URH)** — a full-featured protocol reverse-engineering suite with 12,446 GitHub stars; **SigDigger** — a real-time signal analyzer with a rich visualization toolkit (2,394 stars); and **inspectrum** — a fast, focused offline signal viewer (2,462 stars).

This guide compares their architectures, visualization capabilities, protocol analysis features, and deployment options to help you choose the right tool for your RF analysis workflow.

## Comparison Table

| Feature | Universal Radio Hacker | SigDigger | inspectrum |
|---------|----------------------|-----------|------------|
| **GitHub Stars** | 12,446 | 2,394 | 2,462 |
| **Language** | Python/Cython | C++/Qt | C++/Qt |
| **Last Updated** | December 2025 | February 2026 | Active |
| **Real-time Capture** | Yes (native SDR support) | Yes (Suscan engine) | No (offline only) |
| **Protocol Analysis** | Full reverse-engineering suite | Basic demodulation | None (visual only) |
| **Modulation Demod** | ASK, FSK, PSK, GFSK, QPSK | AM, FM, SSB, IQ | IQ visualization only |
| **Signal Visualization** | Waveform, spectrogram, constellation | Waterfall, spectrogram, 3D, constellation | Spectrogram, amplitude, phase, IQ |
| **Automatic Decoding** | Yes (auto-detection of protocol parameters) | No | No |
| **Fuzzing/Generation** | Yes (transmit crafted signals) | No | No |
| **Scripting/API** | Python API + CLI | Lua scripting | No |
| **Docker Support** | Community images | Manual build | Manual build |
| **GUI Quality** | Functional (Python/Qt) | Modern (C++/Qt) | Clean minimal (C++/Qt) |
| **Resource Usage** | Moderate (500 MB - 1 GB) | Low-Moderate (200-500 MB) | Very Low (100-200 MB) |
| **Learning Curve** | Moderate-Steep | Easy-Moderate | Easy |

## Universal Radio Hacker: The Complete Protocol Reverse-Engineering Suite

URH is the most ambitious RF analysis tool in the open-source ecosystem. It goes far beyond visualization — it's a complete wireless protocol reverse-engineering platform that covers the entire workflow from signal capture to protocol decoding to signal generation.

### Architecture

URH's architecture mirrors the OSI model for wireless protocols:

```
┌──────────────────────────┐
│   Protocol Analysis      │  ← Bit-level decoding, field interpretation
├──────────────────────────┤
│   Demodulation           │  ← ASK/FSK/PSK/QPSK/GFSK demodulators
├──────────────────────────┤
│   Signal Processing      │  ← Filtering, resampling, noise reduction
├──────────────────────────┤
│   Capture / Playback     │  ← SDR device or IQ file input
└──────────────────────────┘
```

### Installation & Key Features

```bash
# Install via pip (recommended)
pip install urh

# Or from source for latest features
git clone https://github.com/jopohl/urh
cd urh
python setup.py install
```

URH's standout features include:

**1. Automatic Protocol Parameter Detection**
URH can analyze a captured signal and automatically determine the modulation type, baud rate, preamble, sync word, and bit encoding — saving hours of manual analysis.

```python
# URH Python API for automated analysis
from urh import Signal, ProtocolAnalyzer

signal = Signal("captured_signal.complex", "My Signal")
signal.modulation_type = "FSK"
signal.auto_detect_parameters()

protocol = ProtocolAnalyzer(signal)
result = protocol.analyze()
print(f"Detected baud rate: {result.baud} symbols/sec")
print(f"Preamble: {result.preamble.hex()}")
```

**2. Protocol Fuzzing & Signal Generation**
Unlike visualization-only tools, URH can generate and transmit crafted signals for protocol testing:

```python
from urh.dev.native.lib import HackRF

# Generate a custom FSK packet
packet = bytes.fromhex("A5A501020304")
modulated = fsk_modulate(packet, deviation=50000, samples_per_symbol=100)

# Transmit via HackRF
hackrf = HackRF()
hackrf.open()
hackrf.set_frequency(433.92e6)
hackrf.set_sample_rate(2e6)
hackrf.start_tx_mode(modulated)
```

**3. Full Protocol Stack Interpretation**
URH goes beyond raw bits — you can define protocol fields (preamble, address, command, payload, CRC), label them, and build a structured interpretation of the protocol. This is invaluable when reverse-engineering proprietary IoT devices, remote controls, or industrial sensors.

### Docker Deployment

```yaml
version: '3.8'
services:
  urh:
    image: jopohl/urh:latest
    container_name: urh
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./urh_projects:/root/urh_projects
      - ./urh_recordings:/recordings
    environment:
      - DISPLAY=${DISPLAY}
      - QT_X11_NO_MITSHM=1
    network_mode: host
    restart: unless-stopped
```

## SigDigger: Real-Time Signal Analysis with Rich Visualization

SigDigger emphasizes real-time signal capture and visualization. Built on the Suscan signal analysis core and the Sigutils DSP library, it provides a modern Qt interface for exploring the spectrum in real time.

### Key Visualization Modes

SigDigger's strength is its rich set of real-time visualization tools:

- **Waterfall Display** — scrolling spectrogram showing frequency vs time vs amplitude
- **3D Spectrogram** — isometric view for pattern recognition
- **IQ Constellation** — real-time phase/amplitude scatter plot
- **Symbol Constellation** — post-demodulation symbol plot for modulation analysis
- **Eye Diagram** — intersymbol interference visualization
- **Channel Inspector** — per-frequency power and modulation analysis

### Installation

```bash
# Build from source
git clone https://github.com/BatchDrake/SigDigger
cd SigDigger
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install

# Launch with RTL-SDR
SigDigger --source rtlsdr --freq 433.92e6 --samp-rate 2.048e6
```

### Automated Signal Classification

SigDigger can automatically classify signals by modulation type using its built-in inspector:

```bash
# Auto-classify signals in a frequency range
SigDigger --source rtlsdr --freq 433.9e6   --inspector auto   --classification-output classified_signals.json
```

### Key Strengths

- **Real-time visualization** — the best waterfall/spectrogram in open-source SDR
- **Low latency** — C++/Qt implementation with hardware-accelerated rendering
- **Multiple simultaneous views** — waterfall + constellation + eye diagram at once
- **Signal classification** — automatic modulation type detection
- **Lua scripting** — extend functionality with custom scripts

## inspectrum: Fast Offline Signal Viewer

inspectrum is a minimal, focused signal viewer designed for offline analysis of IQ recordings. It's the tool you reach for when you've already captured a signal and want to examine it in detail — identifying modulation type, measuring symbol rates, and extracting bit patterns.

### Why inspectrum Matters

While URH and SigDigger are full-featured suites, inspectrum's minimalism is its strength:

- **Sub-second rendering** of multi-gigabyte IQ files
- **Extremely low memory usage** — 100-200 MB even for large files
- **Precise cursor measurements** — measure symbol periods, frequency offsets, and timing
- **Multiple plot types** — amplitude, phase, frequency, IQ constellation with time cursors

### Installation

```bash
# Build from source
git clone https://github.com/miek/inspectrum
cd inspectrum
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install

# Analyze an IQ file
inspectrum captured_signal.cfile
```

### Key Workflow

inspectrum excels at this specific workflow:

1. **Load** a recorded IQ file
2. **Add plots** — amplitude, phase, frequency traces
3. **Zoom and measure** — use time cursors to measure symbol periods
4. **Extract symbols** — derive the digital bitstream from the analog waveform
5. **Export bits** — output decoded bits for protocol analysis in other tools

### Integration with Other Tools

Many RF analysts use inspectrum as the visualization frontend and then feed extracted bits into URH for protocol analysis or into custom Python scripts for decoding:

```bash
# Record with rtl_sdr
rtl_sdr -f 433.92e6 -s 2e6 capture.iq

# Visualize with inspectrum
inspectrum capture.iq

# Export symbols, then analyze protocol with URH Python API
python3 decode_protocol.py --input extracted_bits.json
```

## Why Self-Host Your RF Analysis Lab?

Radio frequency analysis isn't just for signals intelligence professionals — it's increasingly important for IoT developers, security researchers, and hardware hackers who need to understand how wireless devices communicate. A self-hosted RF analysis setup gives you complete control over your signal processing pipeline.

### Privacy and Security

When you analyze wireless signals — especially in industrial, medical, or security contexts — the captured data can be sensitive. Self-hosting ensures your signal recordings never leave your lab. Cloud-based SDR services require uploading IQ recordings to third-party servers; a local setup keeps everything on-premises.

### Cost-Effective Scaling

An RTL-SDR dongle ($30) plus open-source software gives you capabilities that would cost thousands in commercial spectrum analyzers. For exploring the broader reverse-engineering ecosystem beyond RF, check our [binary analysis and reverse engineering guide](../2026-05-03-ghidra-vs-radare2-vs-rizin-self-hosted-binary-analysis-reverse-engineering-guide-2026/). For wireless network analysis specifically, see our [open-source wireless network controllers comparison](../2026-05-15-self-hosted-wireless-network-controllers-openwrt-vs-openwifi-vs-libremesh/).

## FAQ

### Do I need an SDR to use these tools?

**inspectrum** works purely with prerecorded IQ files — no SDR required. **SigDigger** is designed for live capture but can also analyze recordings. **URH** supports both live capture and file-based analysis with or without an SDR. You can download sample IQ recordings from sites like sigidwiki.com to practice without hardware.

### Which tool is best for reverse-engineering an unknown IoT device?

Start with **URH**. Capture the device's transmissions, use the automatic parameter detection to identify modulation and timing, then decode the bit patterns in the protocol analyzer. For tricky signals, use **inspectrum** first to get a clean visualization and measure symbol timing, then import the measurements into URH for protocol-level analysis.

### Can these tools decode encrypted signals?

They can visualize and help you understand the physical-layer characteristics of encrypted signals (modulation, baud rate, packet structure), but they **cannot break encryption**. URH can capture and replay encrypted packets if you're testing replay attacks on devices that don't use rolling codes, but this is for security research purposes only.

### What's the difference between SigDigger and a regular SDR receiver?

A regular SDR receiver (like Gqrx or SDR++) focuses on listening to audio — AM/FM broadcast, ham radio, shortwave. **SigDigger** is an analysis tool — it visualizes the raw RF waveform, measures modulation parameters, and classifies signals by type. It's designed for engineers and researchers, not casual listening.

### Can I run these on a Raspberry Pi?

**inspectrum** runs well on a Pi 4 with 2 GB RAM for file sizes under 500 MB. **SigDigger** can run but the GUI may be sluggish without hardware acceleration. **URH** is the most demanding — a Pi 4 with 4 GB RAM is the minimum, and complex protocol analysis may be slow. For serious RF analysis, a desktop or laptop with 8+ GB RAM is recommended.

### What frequency ranges can these tools analyze?

With an RTL-SDR: 24 MHz to 1.7 GHz (covers ISM bands, LoRa, Zigbee, GSM, GPS, ADS-B). With an Airspy R2: 24 MHz to 1.8 GHz. With a HackRF One: 1 MHz to 6 GHz (covers Wi-Fi, Bluetooth, 5 GHz ISM). The software itself has no frequency limitation — it processes whatever the SDR hardware captures.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted RF Signal Analysis: Universal Radio Hacker vs SigDigger vs inspectrum Compared",
  "description": "Comprehensive comparison of open-source RF signal analysis tools: Universal Radio Hacker (12,446 stars) for protocol reverse-engineering, SigDigger (2,394 stars) for real-time visualization, and inspectrum (2,462 stars) for offline signal analysis. Includes Docker Compose configs, Python API examples, and hardware requirements.",
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
