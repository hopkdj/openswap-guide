---
title: "Self-Hosted MIDI Network Routing: rtpmidid vs QmidiNet vs jack-matchmaker"
date: "2026-06-05"
tags: ["midi", "music-production", "network", "audio", "linux", "raspberry-pi", "home-studio"]
draft: false
---

## MIDI Over IP: Why Network Your Instruments?

MIDI has been the universal language of electronic music since 1983, but traditional 5-pin DIN cables limit you to 16 channels over 15 meters. In a modern home studio or multi-room setup, you want to connect a keyboard in the living room to a synthesizer rack in the basement, or route MIDI from a DAW on your desktop to a Raspberry Pi running a software synth by the speakers.

MIDI-over-IP solves this by encapsulating MIDI messages in network packets, giving you unlimited range (over Ethernet or WiFi) and the ability to route multiple devices through a central Linux server. Three open-source tools lead this category: **rtpmidid** (AppleMIDI/RTP protocol daemon), **QmidiNet** (UDP multicast gateway), and **jack-matchmaker** (JACK audio/MIDI auto-patching).

## rtpmidid: The AppleMIDI Standard for Linux

[rtpmidid](https://github.com/davidmoreno/rtpmidid) (241 stars) implements Apple's MIDI Network Driver Protocol (RTP-MIDI / AppleMIDI) as a Linux daemon. This is the same protocol used by macOS, iOS, and Windows (via rtpMIDI driver) — making rtpmidid the universal bridge between Linux and other operating systems in a music studio.

```bash
# Install rtpmidid on Ubuntu/Debian
sudo apt install rtpmidid
# Or build from source
git clone https://github.com/davidmoreno/rtpmidid.git
cd rtpmidid && mkdir build && cd build
cmake .. && make && sudo make install
# Start the daemon
sudo systemctl enable --now rtpmidid
```

Once running, rtpmidid auto-discovers other AppleMIDI devices on the network using Bonjour/mDNS. A MIDI keyboard connected to a MacBook appears automatically as an ALSA MIDI port on your Linux server, and vice versa. The protocol includes session management, clock synchronization, and automatic reconnection — reliable enough for live performance use.

The daemon creates virtual ALSA MIDI ports for each remote session. You can route these through any Linux MIDI application — connect a remote keyboard to a local software synth, or send sequencer output to a remote hardware module, all transparently.

## QmidiNet: UDP Multicast MIDI Gateway

[QmidiNet](https://qmidinet.sourceforge.io/) (29 stars) takes a simpler approach: it sends MIDI messages as raw UDP/IP multicast packets. This is lighter weight than the AppleMIDI session protocol but lacks automatic device discovery and session management. QmidiNet is ideal for low-latency one-to-many routing — for example, sending a master clock from your main sequencer to multiple Raspberry Pi synths simultaneously.

```bash
# Install QmidiNet on Ubuntu/Debian
sudo apt install qmidinet
# Run as daemon
qmidinet --daemon
```

QmidiNet creates ALSA sequencer ports that mirror network traffic. Any MIDI event on the configured ALSA port gets multicast over UDP, and any received UDP packet appears as a local MIDI event. The simplicity means near-zero configuration — set the multicast address and UDP port, and every QmidiNet instance on the network sees the same MIDI stream.

The trade-off is reliability: UDP does not guarantee delivery. For live performance or critical studio work, a single dropped packet can mean a stuck note. QmidiNet is best suited for non-critical routing like MIDI clock distribution, program change messages, or controller data where occasional packet loss is acceptable.

## jack-matchmaker: Automated JACK Port Management

[jack-matchmaker](https://github.com/SpotlightKid/jack-matchmaker) (77 stars) addresses a different problem: once MIDI is flowing over the network, how do you automatically connect the right ports? In a complex studio setup with dozens of virtual MIDI ports, manually running `jack_connect` or `aconnect` every time you restart becomes tedious.

```bash
# Install jack-matchmaker
pip install jack-matchmaker
# Create a rules file
cat > ~/.config/jack-matchmaker/rules.yaml << 'EOF'
- match: "system:midi_capture_.*"
  connect: "zynaddsubfx:midi_input"
- match: "rtpmidid:.*"
  connect: "amsynth:midi_in"
EOF
# Run as daemon
jack-matchmaker -r ~/.config/jack-matchmaker/rules.yaml
```

jack-matchmaker watches for new JACK ports and automatically connects them based on your rules. Combined with rtpmidid or QmidiNet, you get a fully automatic MIDI network: plug in a keyboard anywhere on the network, and jack-matchmaker routes it to the right synth without any manual intervention.

While jack-matchmaker is primarily designed for JACK audio/MIDI, it works with ALSA MIDI ports through the `a2jmidid` bridge. Run `a2jmidid -e` to expose all ALSA MIDI ports as JACK MIDI ports, then let jack-matchmaker handle the routing.

## Comparison Table

| Feature | rtpmidid | QmidiNet | jack-matchmaker |
|---------|----------|----------|-----------------|
| Protocol | RTP-MIDI (AppleMIDI) | UDP/IP Multicast | JACK port matching |
| Stars (GitHub) | 241 | 29 | 77 |
| Role | Network MIDI bridge | MIDI multicast gateway | Auto-connection manager |
| Device discovery | Bonjour/mDNS auto | Manual configuration | Rule-based auto |
| Cross-platform | macOS, iOS, Windows, Linux | Linux only | Linux (JACK) |
| Session management | Yes (reconnection) | No | No |
| Reliability | High (TCP-like session) | Best-effort (UDP) | N/A (connection layer) |
| Latency | ~2-5ms over LAN | <1ms (raw UDP) | N/A (connection layer) |
| Docker support | Community images | Native package | pip install |

## Why Self-Host Your MIDI Network Router?

A dedicated Linux server running rtpmidid and jack-matchmaker becomes the central nervous system of your music studio. Instead of buying a $300 hardware MIDI interface with 8 ports, you use a $35 Raspberry Pi that can route unlimited MIDI streams over Ethernet. Every synthesizer, controller, and DAW becomes a network citizen, accessible from anywhere in the house.

This is especially powerful for multi-room studios: keep noisy computer fans in a closet, run a Raspberry Pi by the recording booth with just a MIDI keyboard and monitor, and route everything over Cat6. The server handles all the plumbing. You focus on making music.

For related networking patterns, see our guide on [self-hosted overlay networks](../self-hosted-overlay-networks-zerotier-nebula-netmaker-guide-2026/) — similar low-latency tunneling concepts. If you are interested in audio streaming alongside MIDI, check our [game streaming comparison](../sunshine-vs-parsec-vs-moonlight-self-hosted-game-streaming-guide-2026/) for low-latency network stream architectures. For Linux audio infrastructure, our [live streaming guide](../self-hosted-live-streaming-owncast-mediamtx-nginx-rtmp-guide-2026/) covers similar real-time media pipeline patterns.


## Building a Studio-Wide MIDI Infrastructure

A well-designed MIDI network goes beyond simple point-to-point connections. With a central Linux server running rtpmidid, you can build a studio-wide infrastructure where every MIDI device is addressable by name, not by cable number. The server becomes a MIDI patchbay: connect any input to any output, split one source to multiple destinations, or merge multiple controllers into a single virtual instrument port.

For a typical home studio, deploy a Raspberry Pi 4 near your equipment rack running rtpmidid and a2jmidid. Connect hardware synthesizers via USB-MIDI (most modern synths have USB ports). Software synths and samplers run on a more powerful machine elsewhere. jack-matchmaker ensures that when you power everything on, all connections are restored automatically — no manual re-patching after a reboot.

For performance reliability, use wired Ethernet between the server and critical devices. WiFi works for controllers and tablets but can introduce jitter. If you are networking multiple rooms, a dedicated VLAN for MIDI and audio traffic prevents congestion from regular internet traffic. Tools like `iperf3` can verify that your network has sufficient headroom — MIDI itself uses negligible bandwidth, but audio-over-IP (Dante, AES67) on the same network may compete for packets.
## FAQ

### Can I use rtpmidid on a Raspberry Pi?

Yes. rtpmidid compiles and runs perfectly on Raspberry Pi OS (ARM). A Pi 3B+ or newer is recommended. Install via `sudo apt install rtpmidid` on recent Raspberry Pi OS versions. For older releases, build from source as shown above. The CPU load is negligible — MIDI is a lightweight protocol (31.25 kbps).

### What happens if the network drops — do I get stuck notes?

rtpmidid handles this gracefully: it sends MIDI "All Notes Off" messages if a session drops, preventing stuck notes. QmidiNet does not — if a UDP packet containing a Note Off message is lost, you will get a stuck note. For live performance, stick with rtpmidid's session-based protocol.

### Do I need JACK for MIDI networking?

No. Both rtpmidid and QmidiNet work with standard ALSA MIDI (`aconnect`). JACK is only needed if you want to use jack-matchmaker for auto-routing. Most Linux DAWs (Ardour, Reaper, Bitwig) support ALSA MIDI natively. Use `a2jmidid` if you need the JACK MIDI bridge.

### Can I send MIDI over the internet to collaborate remotely?

Technically yes, but latency becomes the issue. Over a VPN with <20ms RTT, rtpmidid works acceptably. For remote jam sessions, consider dedicated low-latency tools like Sonobus or Jamulus instead, which are designed for real-time audio collaboration. For non-real-time MIDI (uploading sequences, remote synth editing), any latency is fine.

### How many MIDI devices can I connect?

The protocol limits are generous: AppleMIDI supports 256 sessions per daemon. In practice, a Raspberry Pi 4 handles 40-50 concurrent MIDI ports without issue. The bottleneck is usually your network switch, not the server CPU — MIDI data is trivially small (a few KB/s per port).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MIDI Network Routing: rtpmidid vs QmidiNet vs jack-matchmaker",
  "description": "Compare rtpmidid, QmidiNet, and jack-matchmaker for self-hosted MIDI over IP routing on Linux and Raspberry Pi. Build a networked home studio with automatic MIDI port management.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
