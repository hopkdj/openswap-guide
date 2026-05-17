---
title: "Self-Hosted RTP Proxy Comparison: RTPengine vs RTPproxy vs Sippy B2BUA (2026)"
date: "2026-05-17"
tags: ["voip", "sip", "media-proxy", "rtp", "kamailio", "telecom"]
draft: false
---

When deploying a self-hosted VoIP or SIP infrastructure, the RTP (Real-time Transport Protocol) media path is just as critical as the SIP signaling path. An RTP proxy sits between the SIP proxy (Kamailio, OpenSIPS, Asterisk) and the media endpoints, handling NAT traversal, codec transcoding, media recording, and DTMF relay. In this guide, we compare three major open-source RTP media handling solutions: **RTPengine**, **RTPproxy**, and **Sippy B2BUA**.

## What Is an RTP Proxy?

The Session Initiation Protocol (SIP) handles call signaling — setup, teardown, and negotiation. The actual voice and video media travels over RTP, a separate protocol that runs on dynamically allocated UDP ports. When endpoints are behind NAT (which is almost always the case in production), the RTP media stream cannot establish a direct peer-to-peer connection. An RTP proxy solves this by acting as a media relay, rewriting SDP (Session Description Protocol) payloads to redirect media through itself.

Beyond basic relay, modern RTP proxies offer codec transcoding (G.711 to Opus), SRTP encryption, media recording (PCAP/PCAPNG), DTMF detection, statistics reporting, and topology hiding. Choosing the right RTP proxy directly impacts call quality, scalability, and operational visibility in your VoIP deployment.

## RTPengine — Sipwise Media Proxy

**RTPengine** ([sipwise/rtpengine](https://github.com/sipwise/rtpengine)) is the most actively developed open-source RTP proxy, with **938+ GitHub stars** and continuous updates from the Sipwise team. Originally forked from the SEMS project, it has grown into a production-grade media proxy used by telecom operators and VoIP providers worldwide.

### Key Features

- Full NAT traversal with ICE support
- SRTP/SRTCP encryption and decryption
- Codec transcoding (G.711, Opus, G.722, G.729, AMR, AMR-WB, VP8, H.264)
- DTMF relay (RFC 2833 and SIP INFO)
- Media recording (PCAP/PCAPNG) with correlation IDs
- RTCP statistics and endpoint monitoring
- Kernel module support for high-throughput media forwarding
- Integration with Kamailio, OpenSIPS, and Asterisk via ng protocol

### Docker Deployment

```yaml
version: "3.8"
services:
  rtpengine:
    image: sipwise/rtpengine:mr12.5
    network_mode: host
    cap_add:
      - NET_ADMIN
    environment:
      - RTPENGINE_LISTEN_NG=127.0.0.1:2223
      - RTPENGINE_LISTEN_CLI=127.0.0.1:9901
      - RTPENGINE_PORT_MIN=10000
      - RTPENGINE_PORT_MAX=20000
      - RTPENGINE_TABLE=0
    restart: always
    volumes:
      - /dev/null:/dev/log
```

### Kamailio Integration

```cfg
# In Kamailio config
modparam("rtpengine", "rtpengine_sock", "udp:127.0.0.1:2223")
modparam("rtpengine", "rtpengine_tout_ms", 1000)

route[NATMANAGE] {
    if (is_request()) {
        if (has_body("sdp")) {
            rtpengine_manage();
        }
    }
}
```

## RTPproxy — Sippy Software RTP Relay

**RTPproxy** ([sippy/rtpproxy](https://github.com/sippy/rtpproxy)) is the original open-source RTP proxy, maintained by Sippy Software, with **473+ GitHub stars**. It provides a lightweight, high-performance media relay designed specifically to work with SIP proxies like Kamailio, OpenSIPS, and SER.

### Key Features

- Simple, single-process architecture
- RTP media relay with NAT traversal
- RTP bridging for codec negotiation
- Recording to WAV/PCAP files
- RTCP statistics generation
- IPv4/IPv6 dual-stack support
- Low memory footprint (~5-10 MB per active call)
- Multiple control protocols (UNIX socket, UDP, TCP)

### Docker Deployment

```yaml
version: "3.8"
services:
  rtpproxy:
    image: mailsvb/rtpproxy:latest
    ports:
      - "7722:7722/udp"
      - "10000-20000:10000-20000/udp"
    environment:
      - RTPPROXY_OPTS=-F -l public_ip_address
    restart: always
```

### SIP Proxy Integration

```cfg
# OpenSIPS configuration
modparam("rtpproxy", "rtpproxy_sock", "udp:127.0.0.1:7722")

route[MANAGE_RTP] {
    if (is_method("INVITE") || is_method("ACK")) {
        rtpproxy_manage("ro");
    } else if (is_method("BYE") || is_method("CANCEL")) {
        rtpproxy_unmanage();
    }
}
```

## Sippy B2BUA — SIP Stack with Built-in RTP Proxy

**Sippy B2BUA** ([sippy/b2bua](https://github.com/sippy/b2bua)) is a full RFC3261-compliant SIP B2BUA (Back-to-Back User Agent) written in Python, with **201+ GitHub stars**. Unlike the dedicated RTP proxies above, Sippy B2BUA combines SIP signaling and RTP media handling into a single integrated platform — the original project from which RTPproxy was derived.

### Key Features

- Complete SIP B2BUA with full RFC3261 compliance
- Integrated RTP proxy (no separate media relay needed)
- Call routing and manipulation
- Radius accounting integration
- CDR (Call Detail Record) generation
- SIP-to-SIP media bridging
- Python-based extensibility and plugin architecture
- Real-time call monitoring and management socket

### Docker Deployment

```yaml
version: "3.8"
services:
  sippy-b2bua:
    image: sippy/b2bua:latest
    network_mode: host
    environment:
      - SIP_LISTEN=0.0.0.0:5060
      - RTP_PORT_MIN=10000
      - RTP_PORT_MAX=20000
    volumes:
      - ./b2bua_config.ini:/etc/b2bua/b2bua.ini:ro
    restart: always
```

### Configuration

```ini
# b2bua.ini
[SIP]
listen = 0.0.0.0:5060
max_calls = 1000

[RTP]
port_min = 10000
port_max = 20000
relay_addr = 0.0.0.0

[Radius]
enabled = yes
server = 127.0.0.1
secret = radius_secret
acct_port = 1813
```

## Comparison Table

| Feature | RTPengine | RTPproxy | Sippy B2BUA |
|---------|-----------|----------|-------------|
| GitHub Stars | 938+ | 473+ | 201+ |
| Language | C | C | Python |
| Architecture | Dedicated RTP proxy | Dedicated RTP proxy | SIP B2BUA + RTP |
| Codec Transcoding | Yes (extensive) | Limited | No |
| SRTP Support | Yes | No (by default) | Yes |
| Kernel Module | Yes (optional) | No | No |
| Media Recording | PCAP/PCAPNG | WAV/PCAP | No |
| ICE Support | Yes | No | No |
| Kamailio Integration | ng protocol | rtpproxy module | Direct SIP |
| Resource Usage | Medium | Low | Medium-High |
| Active Development | Very Active | Active | Moderate |
| Best For | High-scale VoIP | Simple relay | Integrated SIP+RTP |

## Why Self-Host Your RTP Proxy?

Running your own RTP proxy gives you complete control over media routing, encryption, and recording in your VoIP infrastructure. Commercial SIP trunk providers often charge per-minute fees that include media relay costs — by self-hosting, you eliminate these markups and gain full visibility into call quality metrics.

A self-hosted RTP proxy also enables compliance requirements that cloud providers cannot meet. Media recording for regulatory compliance (PCI-DSS, HIPAA, financial services) requires full control over the media path. With RTPengine or RTPproxy, you can record raw PCAP files and feed them into your own analysis pipeline.

For geographic distribution, deploying RTP proxies at edge locations reduces latency for international calls. RTPengine's kernel module can handle hundreds of thousands of concurrent RTP streams on commodity hardware, making it suitable for carrier-grade deployments. The modular architecture means you can deploy RTP proxies independently from your SIP proxies, scaling each layer separately.

If you are building a complete VoIP platform, also consider pairing your RTP proxy with a SIP proxy like [Kamailio or FreeSWITCH](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/) for full signaling control, or a [WebRTC SFU like Janus](../2026-04-25-janus-gateway-vs-mediasoup-vs-livekit-self-hosted-webrtc-sfu-guide-2026/) for browser-based audio/video applications.

For additional media security, combining your RTP proxy with a [TLS proxy like stunnel](../2026-05-15-self-hosted-ssl-tls-proxy-stunnel-sslh-hitch-guide/) adds an extra encryption layer for inter-site media links.

## Choosing the Right RTP Proxy

- **RTPengine** is the best choice for production VoIP deployments that need codec transcoding, SRTP, media recording, and kernel-level performance. Its extensive Kamailio integration and active development make it the industry standard.
- **RTPproxy** excels in simple relay scenarios where you need a lightweight, single-purpose media forwarder with minimal resource consumption. Ideal for small to medium deployments.
- **Sippy B2BUA** is optimal when you want an all-in-one SIP+B2BUA+RTP solution. Its Python-based architecture makes it highly customizable for carrier billing, routing, and accounting use cases.

## Security Best Practices for RTP Media

Securing your RTP proxy deployment involves multiple layers. First, always enable SRTP encryption on RTPengine to prevent media eavesdropping. Configure firewall rules to restrict RTP port ranges (typically 10000-20000) to known SIP proxy IPs only. Use the ng protocol's TLS mode instead of plain UDP for control channel communication between your SIP proxy and RTP engine.

For compliance scenarios requiring call recording, RTPengine's PCAP recording feature captures both RTP and RTCP streams with correlation IDs that link back to SIP call legs. Store recordings on encrypted volumes with strict access controls. Implement log rotation and automated retention policies to manage storage consumption — a busy VoIP platform generates gigabytes of PCAP data daily.

Network-level security should include rate limiting on the ng protocol port to prevent abuse, and binding the control interface to localhost when the SIP proxy runs on the same machine. For distributed deployments across multiple data centers, use IPsec or WireGuard tunnels to protect inter-site RTP proxy traffic.


## FAQ

### What is the difference between a SIP proxy and an RTP proxy?
A SIP proxy handles call signaling — routing INVITE, BYE, and other SIP messages between endpoints. An RTP proxy handles the actual media stream (voice and video data) that flows after the call is established. They work together but serve completely different roles in a VoIP architecture.

### Do I need an RTP proxy for internal calls?
If all endpoints are on the same network without NAT, you may not need an RTP proxy since media can flow directly peer-to-peer. However, for recording, transcoding, or monitoring purposes, routing media through an RTP proxy is still recommended.

### Can RTPengine transcode between any codecs?
RTPengine supports transcoding between most common VoIP codecs including G.711 (A-law/μ-law), Opus, G.722, G.729, AMR, AMR-WB, and video codecs like VP8 and H.264. However, transcoding is CPU-intensive — plan your hardware accordingly.

### How many concurrent calls can a single RTP proxy handle?
RTPengine with its kernel module can handle 100,000+ concurrent RTP streams on a single commodity server. RTPproxy without kernel support typically handles 10,000-30,000 calls depending on CPU and network throughput.

### Does RTPproxy support SRTP encryption?
Standard RTPproxy does not support SRTP natively. If you need encrypted media, RTPengine is the recommended choice as it has full SRTP/SRTCP encryption and decryption support.

### Can I use RTPengine with Asterisk?
Yes, RTPengine integrates with Asterisk via the chan_rtpengine module. It can replace Asterisk's built-in media handling, providing better performance and additional features like transcoding and recording.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted RTP Proxy Comparison: RTPengine vs RTPproxy vs Sippy B2BUA (2026)",
  "description": "Comprehensive comparison of open-source RTP proxy solutions for self-hosted VoIP infrastructure — RTPengine, RTPproxy, and Sippy B2BUA with Docker configs and integration guides.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
