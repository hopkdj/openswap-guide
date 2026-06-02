---
title: "Self-Hosted VoIP Media Processing: FreeSWITCH vs RTPEngine vs Asterisk Codec Transcoding Guide"
date: "2026-06-03"
tags: ["self-hosted", "voip", "freeswitch", "asterisk", "rtpengine", "media-processing", "sip"]
draft: false
---

## Introduction

VoIP media processing — the real-time conversion of audio codecs between different endpoints — is one of the most CPU-intensive workloads in telecommunications infrastructure. When a SIP call connects a G.711 leg to an Opus leg, or bridges WebRTC (Opus) to a traditional PSTN trunk (G.711), a media processor must transcode the audio in real time with sub-20ms latency to maintain call quality.

This guide compares three open-source media processing solutions: **FreeSWITCH** (the software-defined telecom stack with broad codec support), **RTPEngine** (the high-performance kernel-based media proxy from Sipwise), and **Asterisk** (the widely-deployed PBX with integrated DSP). Each excels in different deployment scenarios and throughput requirements.

| Feature | FreeSWITCH | RTPEngine | Asterisk |
|---------|-----------|-----------|----------|
| **Primary Role** | Full PBX + media processing | Dedicated media relay & transcoding | Full PBX + media processing |
| **Transcoding Engine** | mod_spandsp + libcodec2 | Kernel-level (xt_RTPENGINE) | codec_* modules + DSP |
| **Concurrent Calls/Core** | 1,000+ | 10,000+ | 500-1,000 |
| **Kernel Bypass** | No (userspace) | Yes (kernel module) | No (userspace) |
| **Codec Support** | 40+ codecs | 10+ codecs (focused) | 30+ codecs |
| **WebRTC Opus** | Native (mod_opus) | Native | Via codec_opus |
| **T.38 Fax** | Yes (mod_spandsp) | Yes (passthrough) | Yes (native) |
| **DTLS-SRTP** | Yes | Yes | Limited |
| **GitHub Stars** | 4,900+ | 940+ | 2,400+ (core) |
| **License** | MPL 2.0 | GPLv3 | GPLv2 |

## FreeSWITCH: The Swiss Army Knife of Media Processing

FreeSWITCH is a full-featured softswitch capable of handling SIP signaling, media processing, and application logic in a single process. Its modular architecture means you can deploy it solely as a media transcoder without running the full PBX stack, or use it as a complete communications platform.

```yaml
version: "3.8"
services:
  freeswitch:
    image: signalwire/freeswitch:latest
    container_name: freeswitch-media
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "16384-32768:16384-32768/udp"
    volumes:
      - freeswitch-config:/etc/freeswitch
    environment:
      - SOUND_RATES=8000:16000:48000
    restart: unless-stopped

volumes:
  freeswitch-config:
```

### FreeSWITCH Transcoding Configuration

```xml
<!-- Enable codec modules -->
<configuration name="modules.conf" description="Modules">
  <modules>
    <load module="mod_opus"/>
    <load module="mod_g723_1"/>
    <load module="mod_g729"/>
    <load module="mod_amr"/>
    <load module="mod_spandsp"/>
    <load module="mod_codec2"/>
  </modules>
</configuration>
```

```bash
# Set codec preferences globally
fs_cli -x "global_setvar codec_prefs=OPUS,G722,PCMA,PCMU"
fs_cli -x "global_setvar inbound_codec_prefs=OPUS,G722"
fs_cli -x "global_setvar outbound_codec_prefs=PCMA,PCMU,G729"

# Monitor active transcoding sessions
fs_cli -x "show calls count"
fs_cli -x "show codec"
```

FreeSWITCH's `mod_opus` module handles the most common transcoding scenario — converting between Opus (WebRTC) and G.711 (PSTN). Opus is a modern, high-quality, royalty-free codec designed for internet telephony, while G.711 is the legacy 64 kbps codec used by virtually all PSTN carriers and SIP trunks. FreeSWITCH bridges these worlds with sub-20ms latency.

For high-density deployments, FreeSWITCH supports **bypass media mode** where RTP flows directly between endpoints without passing through the server, avoiding transcoding altogether when both sides negotiate compatible codecs. This dramatically reduces CPU usage — a single server can handle thousands of concurrent calls when most sessions are in bypass mode, only invoking transcoding when codec negotiation fails.

## RTPEngine: Kernel-Level Media Processing

RTPEngine is a specialized media proxy designed explicitly for high-performance RTP forwarding and transcoding. Developed by Sipwise for their carrier-grade SIP platform, RTPEngine uses a Linux kernel module (`xt_RTPENGINE`) to process RTP packets directly in kernel space, avoiding the overhead of userspace context switching.

```yaml
version: "3.8"
services:
  rtpengine:
    image: sipwise/rtpengine:latest
    container_name: rtpengine
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_NICE
    volumes:
      - rtpengine-config:/etc/rtpengine
    environment:
      - RUN_RTPENGINE=yes
      - LISTEN_NG=127.0.0.1:2223
      - LISTEN_CLI=127.0.0.1:9900
    restart: unless-stopped

volumes:
  rtpengine-config:
```

### RTPEngine Configuration

```bash
# /etc/rtpengine/rtpengine.conf
[rtpengine]
table = 0
interface = internal/192.168.1.10
interface = external/203.0.113.10
listen-ng = 127.0.0.1:2223
port-min = 30000
port-max = 40000
log-level = 6

# Codec transcoding options
codecs = PCMU,PCMA,G722,OPUS,GSM,iLBC
```

```bash
# RTPEngine CLI - check status and throughput
rtpengine-ctl -ip 127.0.0.1 -port 9900 list totals

# Kamailio integration for RTPEngine control
loadmodule "rtpengine.so"
modparam("rtpengine", "rtpengine_sock", "udp:127.0.0.1:2223")
rtpengine_offer("codec-mask-all direction=pub-priv replace-session-connection ICE=force");
```

RTPEngine's true power lies in its kernel-level architecture. By processing RTP packets inside `iptables`/`netfilter` hooks, RTPEngine achieves throughput of **10,000+ concurrent calls per CPU core** — an order of magnitude more than userspace solutions. This makes it the preferred choice for carrier-grade deployments and SIP trunk providers handling massive call volumes. RTPEngine also excels at **NAT traversal**, rewriting IP addresses and ports in both SIP signaling (SDP) and RTP media streams simultaneously.

## Asterisk: Integrated PBX with DSP

Asterisk is the world's most deployed open-source PBX, and its media processing capabilities are deeply integrated into its call handling pipeline. Asterisk's `codec_*` modules provide broad codec support, while `res_pjsip` and `chan_pjsip` handle SIP signaling and RTP media transport.

```yaml
version: "3.8"
services:
  asterisk:
    image: andrius/asterisk:latest
    container_name: asterisk-media
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "10000-20000:10000-20000/udp"
    volumes:
      - asterisk-config:/etc/asterisk
    restart: unless-stopped

volumes:
  asterisk-config:
```

### Asterisk Codec Configuration

```bash
# Check codec translation costs
asterisk -rx "core show translation"

# Set codec preferences per SIP peer
# /etc/asterisk/pjsip.conf
[mytrunk]
type=endpoint
allow=!all,opus,g722,ulaw,alaw
disallow=all
```

Asterisk's `core show translation` command displays the transcoding cost matrix — how many milliseconds each codec conversion takes on your specific hardware. This is invaluable for capacity planning. For example, Opus-to-G.711 translation costs approximately 5ms per 20ms frame, meaning a single core can handle roughly 400 concurrent transcoding sessions at 20 percent CPU usage on modern hardware.

Asterisk's strength is its **ecosystem integration**. When using Asterisk as both PBX and media processor, you get seamless call routing, IVR (Interactive Voice Response), recording, and conferencing alongside transcoding. For organizations already running Asterisk for voice services, adding codec transcoding requires no additional infrastructure — just enable the relevant codec modules.

## Deployment Architecture: Choosing the Right Stack

A production VoIP media processing deployment typically combines these tools based on scale and requirements:

| Scenario | Recommended Solution | Why |
|----------|---------------------|-----|
| **Small office (<100 concurrent calls)** | Asterisk or FreeSWITCH | Full PBX + transcoding, simpler management |
| **WebRTC gateway (Opus to G.711)** | RTPEngine + Kamailio | Kernel-level performance, minimal latency |
| **Carrier interconnect (10,000+ calls)** | RTPEngine cluster | Horizontal scaling, kernel bypass |
| **Mixed PSTN/VoIP environment** | FreeSWITCH | Broad codec support (G.723, G.729, AMR) |
| **Fax + voice on same infra** | FreeSWITCH or Asterisk | Native T.38 support |

## Why Self-Host Your VoIP Media Processing?

Self-hosting your media processing infrastructure gives you complete control over codec selection, transcoding policies, and capacity planning. Cloud VoIP services often restrict which codecs you can use — typically only G.711 and optionally Opus — and charge per-minute transcoding fees that add up quickly at scale. A self-hosted FreeSWITCH or RTPEngine server can transcode thousands of simultaneous calls at zero per-minute cost, paying for itself within months.

Quality of service (QoS) is another advantage. When you control the media path, you can optimize network routing, enable QoS tagging on RTP packets via DSCP marking, and monitor jitter and packet loss in real time. Cloud services abstract away the media path, making it impossible to diagnose quality issues or optimize for your specific network topology. For organizations with distributed offices or remote workers, this visibility into the media path is invaluable for troubleshooting.

Self-hosted media processing also future-proofs your telecommunications infrastructure. As new codecs like LC3 (used in Bluetooth LE Audio) and EVS (Enhanced Voice Services for 5G networks) gain adoption, you can enable support on your own timeline rather than waiting months for a cloud provider to implement them. RTPEngine's open architecture even allows custom transcoding module development for proprietary codecs.

For SIP signaling infrastructure, see our [Kamailio vs Asterisk comparison](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/). For NAT traversal and media relay, our [RTP proxy guide](../2026-05-17-rtp-proxy-rtpengine-rtpproxy-sippy-b2bua-voip-guide/) covers RTPEngine and alternatives in depth. For WebRTC SFU deployment, our [Janus vs Mediasoup guide](../2026-04-25-janus-gateway-vs-mediasoup-vs-livekit-self-hosted-webrtc-sfu-guide-2026/) covers real-time media architectures.

## FAQ

### How many concurrent transcoding sessions can a single server handle?

It depends on codec complexity and server hardware. RTPEngine on a modern Xeon or EPYC server can handle 10,000+ concurrent sessions thanks to kernel-level processing. FreeSWITCH handles 1,000 to 3,000 per core in userspace. Asterisk handles 500 to 1,000 per core. Opus to G.711 is the most common and efficient transcoding pair. G.729, AMR-WB, and iLBC require more CPU due to their compression algorithms.

### Do I need to pay patent royalties for G.729 codec?

G.729 patent pool licenses are still required in some jurisdictions. FreeSWITCH and Asterisk provide passthrough mode for G.729 — relaying the encoded audio without decoding — to avoid licensing requirements. They also offer licensed G.729 transcoding modules through Digium for full decode-reencode support. Opus is a royalty-free alternative that provides better quality at lower bitrates and is the recommended choice for new deployments.

### Can RTPEngine work as a standalone transcoder without Kamailio?

Yes. RTPEngine exposes a control protocol (ng protocol) that any SIP proxy or application server can use. While Kamailio is the primary integration target with native module support, you can control RTPEngine from FreeSWITCH, OpenSIPS, or custom applications via the `rtpengine` module or direct TCP/UDP control socket communication using the ng protocol specification.

### How do I monitor transcoding quality in production?

Key metrics to monitor include: MOS (Mean Opinion Score) — FreeSWITCH and RTPEngine report per-call MOS scores for quality assessment, jitter buffer statistics tracking packet loss concealment events and buffer underruns/overruns, CPU utilization broken down per codec type to identify heavy transcoding loads, and RTP packet loss and latency monitored via RTCP receiver reports.

### What is the difference between transcoding and passthrough mode?

Transcoding decodes the audio, potentially resamples it to a different sample rate, and re-encodes it in a different codec. This uses significant CPU. Passthrough relays the encoded audio as-is without decoding — the media server acts purely as a packet forwarder. Passthrough uses negligible CPU (a few percent per 1,000 calls) while transcoding uses substantial CPU. Modern deployments use passthrough for same-codec calls and only invoke transcoding when endpoints negotiate incompatible codecs.

### Can I use GPU acceleration for audio codec transcoding?

GPU acceleration for audio transcoding is possible but comes with caveats. FreeSWITCH supports H.264/H.265 video transcoding via VAAPI hardware acceleration, but audio codec transcoding is typically CPU-bound and not well-suited to GPU offloading due to strict latency constraints. For audio-only VoIP workloads, CPU-based transcoding remains the standard approach. Some experimental projects explore FPGA-based audio DSP for carrier-grade applications, but this is not yet production-ready for general deployment.

---

**Test your market judgment with [Polymarket](https://polymarket.com/?r=fc8a0) — the world's largest prediction market platform. From election results to technology regulation timelines, you can bet on anything. Unlike gambling, this is a true information market: the more you know, the higher your win rate. I have made substantial gains predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VoIP Media Processing: FreeSWITCH vs RTPEngine vs Asterisk Codec Transcoding Guide",
  "description": "Detailed comparison of self-hosted VoIP media processing and codec transcoding solutions: FreeSWITCH for broad codec support, RTPEngine for kernel-level performance, and Asterisk for integrated PBX with DSP.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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
