---
title: "Self-Hosted Voice Assistants: Mycroft vs Rhasspy vs OVOS vs voice2json"
date: "2026-06-07"
tags: ["voice-assistant", "speech-recognition", "home-automation", "self-hosted", "privacy", "iot", "raspberry-pi"]
draft: false
---

## Introduction

Voice assistants have become a staple of modern smart homes, but most commercial solutions — Alexa, Google Assistant, Siri — route every voice command through corporate cloud servers. For privacy-conscious users who want full control over their data, self-hosted voice assistant platforms offer a compelling alternative. These open source solutions run entirely on your own hardware, process speech locally, and never send your voice data to third parties.

In this guide, we compare four leading self-hosted voice assistant platforms: **Mycroft**, the veteran open source voice assistant with a rich ecosystem; **Rhasspy**, a lightweight offline voice toolkit designed for Home Assistant integration; **OVOS** (Open Voice OS), the community-driven successor to Mycroft; and **voice2json**, a focused command-and-control speech system. Each takes a different approach to the problem of local voice processing, and the right choice depends on your use case.

## Comparison Table

| Feature | Mycroft | Rhasspy 3 | OVOS | voice2json |
|---------|---------|-----------|------|------------|
| Stars | 6,618+ | 382+ | 276+ | 1,108+ |
| Primary Language | Python | Python | Python | Python |
| Wake Word Engine | Precise, Snowboy | porcupine, snowboy, raven | OpenWakeWord, Precise | None (push-to-talk) |
| Speech-to-Text | DeepSpeech, Google STT | Kaldi, DeepSpeech, Vosk | Whisper, Vosk, STT plugins | Kaldi, DeepSpeech, Vosk |
| Text-to-Speech | Mimic, Mimic 2, Mimic 3 | Larynx, espeak, flite | Piper, Mimic 3 | None |
| Intent Engine | Adapt, Padatious | fsticuffs, fuzzywuzzy | Padatious, Adapt | Built-in sentence templates |
| Home Assistant Integration | Via plugin | Native (built-in) | Via plugin | Via shell commands |
| Docker Support | Yes | Yes | Yes | Yes |
| Active Development | Stalled (2024) | Stalled (2023) | Active (2026) | Active (2024) |

## Mycroft: The Pioneer

Mycroft was the first serious open source voice assistant, launched in 2015 with a vision of creating an open alternative to Alexa. It introduced a modular architecture where wake word detection, speech-to-text (STT), intent parsing, and text-to-speech (TTS) are all pluggable components. This design allows users to swap out each component independently — use Google's cloud STT during development, then switch to a local engine like Vosk for production.

### Docker Compose

```yaml
version: '3'
services:
  mycroft-core:
    image: mycroftai/mycroft-core:latest
    container_name: mycroft
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - ./mycroft-config:/root/.mycroft
      - /var/run/dbus:/var/run/dbus
    environment:
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
    restart: unless-stopped
```

Mycroft's strength lies in its **skill ecosystem** — hundreds of community-contributed skills for weather, timers, music playback, and smart home control. Its natural language understanding uses a combination of keyword-based (Adapt) and machine-learning-based (Padatious) intent parsers, giving developers flexibility in how they define voice commands.

However, the company behind Mycroft ceased operations in 2024, and the core repository has been in maintenance mode since. The community has largely migrated to OVOS, which maintains backward compatibility with Mycroft skills while adding new features.

## Rhasspy: Offline-First Voice Control

Rhasspy takes a different philosophical approach — it is designed from the ground up to work **completely offline**. Unlike Mycroft, which historically depended on cloud services for high-quality STT, Rhasspy bundles everything needed for local voice processing: wake word detection, speech recognition, intent handling, and text-to-speech.

### Docker Compose

```yaml
version: '3'
services:
  rhasspy:
    image: rhasspy/rhasspy:latest
    container_name: rhasspy
    ports:
      - "12101:12101"
    volumes:
      - ./rhasspy-data:/data
      - ./rhasspy-profiles:/profiles
    devices:
      - /dev/snd:/dev/snd
    restart: unless-stopped
```

Rhasspy's killer feature is its **deep integration with Home Assistant**. It can expose all voice intents as Home Assistant events and use Home Assistant's entity state for context-aware responses. The web-based training interface lets you record example sentences and train the intent recognizer without writing code.

The project is currently in transition — Rhasspy 2.x is stable but no longer actively developed, while Rhasspy 3 (written in Rust for better performance) reached a usable state before development slowed. For users who want a simple, reliable offline voice pipeline for Home Assistant, Rhasspy 2 remains a solid choice.

## OVOS: The Community Successor

Open Voice OS (OVOS) emerged from the Mycroft community after the parent company shut down. It preserves full backward compatibility with Mycroft skills while modernizing the underlying architecture. OVOS replaces Mycroft's aging components with actively maintained alternatives — **OpenWakeWord** for wake word detection, **Whisper** and **Vosk** for STT, and **Piper** for TTS.

### Docker Compose

```yaml
version: '3'
services:
  ovos-core:
    image: smartgic/ovos-core:latest
    container_name: ovos-core
    ports:
      - "8181:8181"
    volumes:
      - ./ovos-config:/home/ovos/.config
    environment:
      - TZ=America/New_York
    restart: unless-stopped

  ovos-messagebus:
    image: smartgic/ovos-messagebus:latest
    container_name: ovos-messagebus
    ports:
      - "8182:8182"
    restart: unless-stopped

  ovos-audio:
    image: smartgic/ovos-audio:latest
    container_name: ovos-audio
    devices:
      - /dev/snd:/dev/snd
    restart: unless-stopped
```

OVOS is the **most actively developed** platform in this comparison, with daily commits and a growing community. It supports the PHAL (Platform/Hardware Abstraction Layer) concept, making it easy to run on anything from a Raspberry Pi 4 to an x86 server. The plugin architecture allows mixing and matching STT, TTS, and intent engines to suit different hardware capabilities.

One notable advantage is OVOS's support for **Whisper** (OpenAI's open-source STT model), which provides dramatically better accuracy than older engines like PocketSphinx. On a Raspberry Pi 4, Whisper's `tiny` model runs at near-real-time speed and handles accents and background noise much better than previous solutions.

## voice2json: Command-and-Control Specialist

voice2json takes the most minimalist approach of the four — it is not a general-purpose voice assistant but a **command-and-control system** optimized for reliable, offline voice trigger processing. It converts spoken commands directly into JSON objects that can be piped to shell scripts, MQTT topics, or Home Assistant automations.

```bash
# Install voice2json
pip3 install voice2json

# Train on your custom sentences
voice2json --profile en train

# Transcribe and output JSON
voice2json transcribe-wav --audio-in < microphone.wav
```

### Systemd Service Configuration

```ini
[Unit]
Description=voice2json MQTT Bridge
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
ExecStart=/usr/local/bin/voice2json-wake     --profile en     --mqtt-host localhost     --mqtt-topic-prefix voice2json
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

voice2json excels at **deterministic voice commands** — "turn on living room lights," "set thermostat to 72," "lock the front door." Its template-based intent system uses strict sentence patterns defined in a simple text file, which means no fuzzy matching surprises. If you say something outside the defined templates, it simply reports no match rather than guessing.

## Why Self-Host Your Voice Assistant?

The decision to run a self-hosted voice assistant goes beyond just privacy — though that alone is a compelling reason. When you use a commercial voice assistant, every command you utter is recorded, transcribed in the cloud, stored on corporate servers, and potentially used for advertising profiling or training proprietary models. With a self-hosted solution, your voice data stays on your own hardware.

Beyond privacy, self-hosted voice assistants offer **deeper customization**. You can write custom skills that integrate with your specific smart home setup, using MQTT topics, REST APIs, or shell scripts. Commercial assistants lock you into their approved integrations and skill stores; with open source, you control the entire pipeline.

Cost is another factor — while individual smart speakers are inexpensive, the long-term cost of being locked into an ecosystem (requiring specific brand hubs, subscriptions for advanced features) adds up. A Raspberry Pi 4 running OVOS or Rhasspy costs under $100 and can serve as your entire voice control brain.

For smart home integration, see our [Home Assistant vs Homebridge comparison](../2026-04-28-home-assistant-vs-homebridge-vs-scrypted-self-hosted-smart-home-hub-guide-2026/). If you are building a broader smart home ecosystem, check our [Matter smart home controller guide](../2026-05-16-self-hosted-matter-smart-home-controller-sdk-openhab-domoticz-guide/). For connecting physical devices, our [Zigbee2MQTT and Z-Wave bridge guide](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/) covers device-level integration.

## Frequently Asked Questions

### Can these voice assistants run on a Raspberry Pi?

Yes, all four platforms support Raspberry Pi. OVOS and Rhasspy are particularly well-optimized for the Pi 4. With 4GB RAM, you can run the full stack including wake word detection, STT (using Vosk or Whisper tiny), and TTS. voice2json is the lightest, running comfortably on a Pi Zero 2 W. For best results, use a USB microphone array rather than the Pi's built-in audio input.

### Do I need an internet connection?

Rhasspy and voice2json are designed to work completely offline — all speech processing happens locally. OVOS can run offline with Vosk or Whisper STT, though some optional features (weather, news) require internet. Mycroft historically relied on cloud STT but supports local engines now. The key tradeoff: cloud STT provides better accuracy for complex queries, while local STT ensures privacy.

### How accurate is local speech recognition compared to Alexa?

This has improved dramatically in recent years. Whisper's `small` model achieves near-human accuracy on clear speech, even with accents. Vosk provides good accuracy for command-and-control vocabularies. The gap with commercial assistants has narrowed significantly — for defined command sets ("turn on lights"), local engines match commercial accuracy. For open-ended queries ("what is the capital of Burkina Faso"), cloud engines still have an edge, but you can always fall back to a keyboard for those.

### Can I use multiple wake words with these systems?

OVOS supports multiple wake words via OpenWakeWord, which can be trained on custom phrases. Mycroft supports "Hey Mycroft" by default with the ability to add custom wake words through Precise. Rhasspy supports multiple wake words through its plugin architecture (porcupine, snowboy). voice2json does not include wake word functionality — it uses push-to-talk or external wake word detection.

### How do these integrate with Home Assistant?

Rhasspy has the tightest Home Assistant integration — it was built specifically for this use case and exposes intents as native HA events. OVOS and Mycroft integrate through plugins that connect to the Home Assistant WebSocket API. voice2json can trigger Home Assistant automations through MQTT or REST API calls, requiring slightly more configuration but offering maximum flexibility.

### Which one should I choose for a new project?

Start with **OVOS** if you want an actively maintained, general-purpose voice assistant with a skill ecosystem. Choose **Rhasspy** if Home Assistant integration is your primary goal and you want maximum offline reliability. Pick **voice2json** if you need a lightweight, deterministic command-and-control system and are comfortable writing shell scripts. Consider **Mycroft** only if you need specific legacy skills that have not been ported to OVOS.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Voice Assistants: Mycroft vs Rhasspy vs OVOS vs voice2json",
  "description": "Comprehensive comparison of four open source self-hosted voice assistant platforms: Mycroft, Rhasspy, OVOS, and voice2json. Includes Docker Compose configs, Home Assistant integration, and privacy analysis.",
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
