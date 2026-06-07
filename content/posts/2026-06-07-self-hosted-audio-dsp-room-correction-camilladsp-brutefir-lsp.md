---
title: "Self-Hosted Audio DSP & Room Correction: CamillaDSP vs BruteFIR vs LSP Plugins"
date: "2026-06-07"
tags: ["audio", "dsp", "room-correction", "raspberry-pi", "self-hosted", "multiroom"]
draft: false
---

## Introduction

If you've ever set up a home audio system only to find that the bass response is muddy, the treble is harsh, or the stereo imaging is smeared by room reflections, you've encountered the fundamental challenge of room acoustics. Professional studios spend thousands on acoustic treatment, but for the rest of us, **Digital Signal Processing (DSP)** offers a software-based solution. By applying precise digital filters to your audio signal, you can correct for room modes, speaker non-linearities, and crossover issues — all from a $35 Raspberry Pi.

In this guide, we compare three leading open-source audio DSP engines: **CamillaDSP**, **BruteFIR**, and **LSP Plugins**. Each takes a different approach to real-time audio processing, from the modern Rust-based CamillaDSP to the battle-tested BruteFIR and the versatile plugin suite architecture of LSP.

## Why Self-Host Your Audio DSP?

Running your own DSP engine gives you control that no commercial receiver or soundbar can match. Consumer audio gear applies generic "room correction" presets that can't account for your specific room dimensions, speaker placement, or listening preferences. With a self-hosted solution, you design the filter chain yourself — parametric EQ, FIR convolution, crossovers, and gain staging — all tuned to your exact setup.

Beyond room correction, self-hosted DSP opens up possibilities like active crossover networks for DIY speakers, loudspeaker protection limiting, and even headphone virtualization. Paired with a multiroom streaming setup — see our [self-hosted music streaming guide](../2026-05-01-koel-vs-mopidy-vs-snapcast-self-hosted-music-streaming-guide/) — you can create a whole-home audio system with per-room correction. If you're already running media servers, our [DLNA/UPnP media server comparison](../2026-05-02-minidlna-vs-gerbera-vs-rygel-self-hosted-dlna-upnp-media-servers-guide/) covers the network transport side.

The hardware requirements are modest. A Raspberry Pi 4 with a USB DAC or an I2S HAT (like the HiFiBerry or Allo Boss) provides enough processing power for stereo 192kHz FIR filtering. For multi-channel or higher sample rates, a Pine64 or a small x86 mini-PC works well. The key is low latency — if your DSP introduces more than 20ms of delay, it becomes noticeable for video or live monitoring. All three tools we compare are designed for real-time, sub-20ms processing on modest hardware.

For gamers and streamers concerned about low-latency audio/video sync, our [self-hosted game streaming comparison](../sunshine-vs-parsec-vs-moonlight-self-hosted-game-streaming-guide-2026/) covers solutions that work well alongside DSP processing pipelines.

## Comparison Table

| Feature | CamillaDSP | BruteFIR | LSP Plugins |
|---------|-----------|----------|-------------|
| **Language** | Rust | C | C++ |
| **FIR Filters** | Yes (convolution engine) | Yes (specialized) | Yes (via convolver plugin) |
| **IIR Filters** | Yes (biquad, shelves, peaking) | No (FIR-only) | Yes (extensive biquad library) |
| **Sample Rate Support** | Up to 768 kHz | Up to 384 kHz | Up to 384 kHz |
| **Web UI** | Yes (CamillaGUI) | No (CLI only) | Yes (JACK host + external UI) |
| **Configuration** | YAML-based | Text config file | Plugin chain definitions |
| **Crossovers** | Built-in | Via filter design | Via crossover plugin |
| **PipeWire/JACK** | Loopback + ALSA | JACK support | JACK, LADSPA, LV2 |
| **CPU Efficiency** | Excellent (SIMD-optimized) | Very good | Good (plugin overhead) |
| **Docker Support** | Community images | Manual setup | Manual setup |
| **Active Development** | Yes (969 stars, 2026) | Minimal (mature, stable) | Yes (active plugin suite) |
| **Learning Curve** | Moderate | Steep | Steep |
| **License** | GPLv3 | GPLv2 | LGPLv3 |

## CamillaDSP: Modern, Accessible DSP

[CamillaDSP](https://github.com/HEnquist/camilladsp) (969 stars, MIT/GPL) is the newest contender, written in Rust with a focus on safety and performance. It supports both IIR and FIR filtering, making it flexible for everything from simple bass management to full-range room correction using REW (Room EQ Wizard) generated filters.

CamillaDSP shines in its configuration model. Everything is defined in a single YAML file, which makes version-controlling your DSP pipeline trivial. The companion CamillaGUI provides a web-based interface for real-time adjustments — you can tweak equalizer bands, load new FIR filters, or adjust gain staging without SSH'ing into your device.

```yaml
# camilladsp.yml — minimal stereo room correction config
devices:
  samplerate: 44100
  chunksize: 4096
  capture:
    type: Alsa
    channels: 2
    device: "hw:Loopback,0"
    format: S32LE
  playback:
    type: Alsa
    channels: 2
    device: "hw:DAC,0"
    format: S32LE
filters:
  room_eq:
    type: Conv
    parameters:
      type: File
      filename: /config/room_correction.wav
      format: FLOAT64LE
  bass_boost:
    type: Biquad
    parameters:
      type: Lowshelf
      freq: 80
      gain: 3.0
      q: 0.7
pipeline:
  - type: Filter
    channel: 0
    names:
      - room_eq
      - bass_boost
  - type: Filter
    channel: 1
    names:
      - room_eq
      - bass_boost
```

**Docker Compose deployment** for CamillaDSP with the web GUI:

```yaml
version: "3.8"
services:
  camilladsp:
    image: ghcr.io/henquist/camilladsp:latest
    container_name: camilladsp
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - ./config:/config
      - ./filters:/filters
    network_mode: host
    restart: unless-stopped
  camillagui:
    image: ghcr.io/henquist/camillagui-backend:latest
    container_name: camillagui
    depends_on:
      - camilladsp
    ports:
      - "5000:5000"
    volumes:
      - ./config:/config
    restart: unless-stopped
```

## BruteFIR: The Battle-Tested Convolver

[BruteFIR](https://torger.se/anders/brutefir.html) is a specialized FIR convolution engine that's been the gold standard for room correction since the early 2000s. Unlike CamillaDSP's all-in-one approach, BruteFIR focuses exclusively on FIR filtering — it does one thing and does it extremely well. It processes audio through pre-computed impulse response files, applying precise corrections with minimal CPU overhead.

BruteFIR's configuration is a text file format rather than YAML, which can feel dated compared to CamillaDSP. There's no built-in web UI, and setup requires understanding of coefficient file formats and partition sizes for efficient convolution. However, for advanced users who need maximum FIR filter length (up to 131072 taps) or multi-way speaker crossover networks, BruteFIR remains the reference implementation.

```bash
# Install BruteFIR on Debian/Ubuntu
sudo apt-get install brutefir

# Basic BruteFIR config snippet
# /etc/brutefir/brutefir_config
filter_length: 65536,32;
samplerate: 44100;
input "left", "right" {
  device: "hw:Loopback,0";
  sample: "S32_LE";
  channels: 2;
};
output "left_out", "right_out" {
  device: "hw:DAC,0";
  sample: "S32_LE";
  channels: 2;
};
# Load room correction filter
coeff "left_filter" {
  filename: "/home/pi/filters/left_correction.pcm";
  format: "FLOAT64_LE";
};
filter "left_eq" {
  from_input: "left";
  to_output: "left_out";
  coeff: "left_filter";
};
```

The lack of IIR support means you'll need to pre-generate combined FIR filters using tools like REW or DRC-FIR, which adds complexity to the workflow.

## LSP Plugins: The Plugin Suite Approach

[LSP Plugins](https://lsp-plug.in/) takes yet another approach — instead of a monolithic DSP engine, it provides a comprehensive suite of audio processing plugins (EQ, compressor, delay, crossover, convolver, limiter, spectrum analyzer) that you chain together using a JACK or LADSPA/LV2 host. This modularity gives you incredible flexibility: you can design a custom signal chain with exactly the processing stages you need.

The LSP plugin suite includes a standalone JACK host application with a built-in graphical interface, making it easier to visualize your signal chain than BruteFIR's text-only approach. The convolution plugin handles FIR-based room correction, while the parametric equalizer plugin handles IIR filtering. You can even add dynamics processing (compression/limiting) to protect your speakers.

```bash
# Build LSP Plugins from source
git clone https://github.com/sadko4u/lsp-plugins.git
cd lsp-plugins
make config
make
sudo make install

# Run standalone JACK host
lsp-plugins-jack
```

## Deployment Architecture

A typical self-hosted audio DSP deployment follows this signal path:

```
Digital Source (Spotify Connect / AirPlay / DLNA)
    │
    ▼
Audio Capture (ALSA Loopback / PipeWire / JACK)
    │
    ▼
DSP Engine (CamillaDSP / BruteFIR / LSP Plugins)
    │  └─ Room Correction FIR
    │  └─ Parametric EQ (IIR)
    │  └─ Crossover Network
    │  └─ Limiter / Protection
    ▼
Audio Output (USB DAC / I2S HAT / HDMI)
    │
    ▼
Amplifier → Speakers
```

For AirPlay integration, pair your DSP engine with [Shairport-Sync](https://github.com/mikebrady/shairport-sync) (8,680 stars) — a mature AirPlay 2 receiver that outputs to ALSA, making it a perfect front-end for any of the three DSP engines covered here.

## Choosing the Right DSP Engine

**Choose CamillaDSP if** you want a modern, well-documented, actively maintained solution with both FIR and IIR support, a web GUI, and Docker deployment. It's the best all-around choice for most self-hosters.

**Choose BruteFIR if** you need maximum FIR filter length for complex multi-way speaker crossovers, have an existing workflow built around DRC-FIR or REW-generated coefficients, and are comfortable with CLI-only configuration.

**Choose LSP Plugins if** you want a complete audio processing studio rather than just room correction — the plugin suite includes dynamics processors, analyzers, and effects that go beyond what CamillaDSP or BruteFIR offer.

## FAQ

### Can I run room correction DSP on a Raspberry Pi Zero?
Technically yes, but the CPU is too weak for FIR filters longer than 4096 taps at 44.1kHz. A Raspberry Pi 4 or better is recommended for practical room correction (16384 taps or more). If you only need IIR parametric EQ (no FIR convolution), even a Pi Zero 2W can handle stereo at 48kHz.

### What measurement microphone should I use for room correction?
The miniDSP UMIK-1 is the de facto standard ($79, USB, individually calibrated). Budget alternatives include the Dayton Audio iMM-6 ($25, requires TRRS-to-USB adapter). Both work with Room EQ Wizard (REW), the free and open-source measurement software. REW generates FIR filter coefficients that all three DSP engines can load.

### How do I integrate DSP with my existing multiroom audio setup?
The cleanest approach is to position the DSP engine between your audio source and your amplifier. If you use Snapcast for multiroom audio, insert the DSP between the Snapserver and the Snapclient on each endpoint. Our [music streaming guide](../2026-05-01-koel-vs-mopidy-vs-snapcast-self-hosted-music-streaming-guide/) covers the Snapcast architecture in detail. For DLNA-based setups, apply DSP at the renderer level — see our [DLNA/UPnP server comparison](../2026-05-02-minidlna-vs-gerbera-vs-rygel-self-hosted-dlna-upnp-media-servers-guide/).

### Does DSP add noticeable latency for video or gaming?
With a well-tuned configuration, total latency can stay under 10ms, which is imperceptible for music and acceptable for video (with lipsync adjustment). For competitive gaming, 10ms of audio delay may be noticeable — our [game streaming guide](../sunshine-vs-parsec-vs-moonlight-self-hosted-game-streaming-guide-2026/) covers ultra-low-latency streaming setups. CamillaDSP's chunk-based processing and SIMD optimizations yield the lowest latency of the three engines compared here.

### Can I use these tools for active crossover networks in DIY speakers?
Absolutely. CamillaDSP and BruteFIR both support multi-channel routing with per-channel filtering, making them excellent crossover engines. Define low-pass, high-pass, and band-pass filters for each driver, then route to separate DAC channels. The Okto Research DAC8 PRO (8 channels) is a popular choice for active 3-way or 4-way speaker builds with DSP crossovers.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Audio DSP & Room Correction: CamillaDSP vs BruteFIR vs LSP Plugins",
  "description": "Compare three open-source audio DSP engines for self-hosted room correction and active crossover networks: CamillaDSP (Rust, web GUI), BruteFIR (FIR convolution), and LSP Plugins (plugin suite). Includes Docker Compose deployment on Raspberry Pi.",
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
