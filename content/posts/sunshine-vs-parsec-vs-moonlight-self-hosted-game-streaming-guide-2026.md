---
title: "Sunshine vs Parsec vs Moonlight: Self-Hosted Game Streaming Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "gaming", "streaming"]
draft: false
description: "Compare Sunshine, Parsec, and Moonlight for self-hosted game streaming. Complete Docker setup guides, performance comparison, and best practices for playing PC games remotely in 2026."
---

## Why Self-Host Your Game Streaming?

Remote gaming has evolved from a niche homelab curiosity into a practical way to access your entire PC game library from any device, anywhere in your home or on the go. Whether you want to play AAA titles on a laptop from your couch, stream games to a phone on a business trip, or share your gaming rig with family members across different rooms, self-hosted game streaming gives you that flexibility without the recurring subscription costs of cloud gaming services.

The open-source game streaming ecosystem has matured dramatically. Sunshine — the community-maintained GameStream host — has surpassed 36,000 GitHub stars and receives active development. Moonlight, the companion client, runs natively on Windows, macOS, Linux, Android, iOS, and even the Steam Deck. Together, they form a completely free, self-hosted alternative to proprietary services like GeForce Now or Steam Remote Play.

Self-hosting your game streaming setup means:

- **Zero subscription fees** — no monthly costs, no game library restrictions
- **Full control over quality** — set your own bitrate, resolution, and frame rate limits
- **No vendor lock-in** — your streaming infrastructure belongs to you
- **LAN-level latency** — on a wired network, latencies below 10ms are achievable
- **Cross-platform flexibility** — stream from a Linux gaming rig to an iPad, from a Windows PC to an Android phone
- **Privacy** — no telemetry about what you play, when you play, or how long you play

For homelab enthusiasts with a dedicated gaming machine, families sharing a single powerful PC, and travelers who want access to their Steam library from a thin client, a self-hosted game streaming stack is one of the highest-impact projects you can set up.

If you're also interested in remote desktop solutions for non-gaming use cases, check out our [self-hosted remote desktop guide](../self-hosted-remote-desktop-guacamole-rustdesk-meshcentral-guide/) comparing Apache Guacamole, RustDesk, and MeshCentral. For game server management rather than game streaming, see our [Pterodactyl game server panel guide](../pterodactyl-self-hosted-game-server-management-guide/).

## The Game Streaming Landscape: Three Approaches

There are three main approaches to self-hosted game streaming, each with a different architecture:

| Approach | Host Software | Client Software | Protocol | Open Source |
|----------|--------------|-----------------|----------|-------------|
| **Sunshine + Moonlight** | Sunshine (server) | Moonlight (client) | NVIDIA GameStream (custom) | ✅ Full |
| **Parsec** | Parsec Host | Parsec Client | Parsec Protocol (proprietary) | ❌ Closed source |
| **Steam Remote Play** | Steam Client | Steam Link | Steam Protocol (proprietary) | ❌ Closed source |

Sunshine is a free, open-source game stream host that replaced NVIDIA's deprecated GameStream protocol. Originally created by LizardByte, the project now has over 36,000 stars on GitHub and was last updated in April 2026. It captures your desktop or individual game windows, encodes them with hardware acceleration (NVENC, AMD AMF, or Intel Quick Sync), and streams the video/audio to any Moonlight client.

Moonlight is the client side of the equation — a GameStream-compatible receiver that runs on virtually every platform. The Qt desktop client alone has nearly 17,000 GitHub stars, with additional ports for Android (6,500+ stars) and iOS/tvOS. Moonlight handles input forwarding (keyboard, mouse, gamepad) back to the host, decodes the video stream, and plays back the audio — all with sub-15ms latency on a local network.

Parsec takes a different approach. It is a proprietary service (freemium) that handles the streaming infrastructure centrally. You install the Parsec host on your gaming machine and the Parsec client on your target device. While not self-hosted in the traditional sense, Parsec's free tier is generous and offers excellent performance over the internet, making it a popular complement to the Sunshine/Moonlight stack.

Steam Remote Play is Valve's built-in streaming solution. If you already use Steam, it requires zero additional configuration — just enable Remote Play in settings and connect from any Steam Link client. It is the most convenient option but offers the least configurability and is locked to your Steam game library.

## Detailed Comparison Table

| Feature | Sunshine + Moonlight | Parsec (Free) | Steam Remote Play |
|---------|---------------------|---------------|-------------------|
| **Cost** | Free | Free (paid tier for teams) | Free |
| **Open Source** | ✅ Both host and client | ❌ Closed source | ❌ Closed source |
| **Max Resolution** | 4K (configurable) | 4K | 4K |
| **Max Frame Rate** | 120 FPS (configurable) | 60 FPS (free), 120 FPS (paid) | 120 FPS |
| **HDR Support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Controller Support** | ✅ XInput, DualSense, Switch Pro | ✅ Yes | ✅ Yes |
| **Multi-Monitor** | ✅ Select per-stream | ✅ Yes | ❌ Limited |
| **Touch Input** | ✅ Moonlight Android/iOS | ✅ Yes | ✅ Steam Link app |
| **LAN Latency** | ~5-15ms | ~10-20ms | ~10-25ms |
| **Internet Streaming** | Requires port forwarding or Tailscale/ZeroTier | ✅ Built-in NAT traversal | ✅ Built-in NAT traversal |
| **Cross-Platform Host** | Windows, Linux | Windows, Linux, macOS | Windows, Linux, macOS |
| **Cross-Platform Client** | Windows, macOS, Linux, Android, iOS, WebOS, Apple TV | Windows, macOS, Linux, Android, iOS, Raspberry Pi | Windows, macOS, Linux, Android, iOS, Steam Deck |
| **Docker Support** | ✅ Official Docker image | ❌ No | ❌ No |
| **Self-Hosted** | ✅ Fully | ❌ Cloud-dependent | ❌ Cloud-dependent |
| **Multi-User** | ✅ Concurrent sessions possible | ✅ (paid tier) | ❌ Single session |

## Installing Sunshine: Three Methods

### Method 1: Native Installation (Recommended for Gaming Hosts)

For a gaming PC that needs direct GPU access and minimal overhead, a native installation is the best approach. Sunshine runs as a system service and provides a web-based configuration interface.

**On Ubuntu/Debian:**

```bash
# Add the Sunshine repository
sudo apt install -y wget gnupg
wget -qO - https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x6A7E5656C2D6B36C | sudo gpg --dearmor -o /etc/apt/keyrings/sunshine.gpg

# Install Sunshine (replace with latest version from GitHub releases)
sudo apt install sunshine
```

**On Windows:** Download the `.exe` installer from the [LizardByte/Sunshine GitHub releases page](https://github.com/LizardByte/Sunshine/releases) and run it. Sunshine installs as a Windows service and starts automatically.

After installation, access the Sunshine web UI at `https://localhost:47990` to configure your streaming settings, including resolution, bitrate, and encoder selection.

### Method 2: Docker Deployment

Sunshine provides official Docker images on both Docker Hub (`lizardbyte/sunshine`) and GitHub Container Registry. The container requires GPU device passthrough and specific port mappings.

```yaml
version: '3'
services:
  sunshine:
    image: lizardbyte/sunshine:latest-ubuntu-24.04
    container_name: sunshine
    restart: unless-stopped
    privileged: true
    devices:
      - /dev/dri:/dev/dri
    volumes:
      - ./sunshine-config:/config
      - /tmp/.X11-unix:/tmp/.X11-unix
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - DISPLAY=:0
    ipc: host
    network_mode: host
    ports:
      - "47984-47990:47984-47990/tcp"
      - "48010:48010"
      - "47998-48000:47998-48000/udp"
```

**Important Docker notes:**
- The `--privileged` flag or explicit `/dev/dri` device mapping is required for hardware-accelerated encoding
- `network_mode: host` is recommended for lowest latency; port mapping works but adds overhead
- The `DISPLAY=:0` environment variable must match your host X server
- For Wayland compositors, additional configuration is needed (see Sunshine's DOCKER_README.md)

### Method 3: Games on Whales (Community Docker Stack)

The [Games on Whales](https://games-on-whales.github.io) project provides a comprehensive Docker stack that bundles Sunshine with a full desktop environment, making it easy to run a cloud gaming rig from any server:

```yaml
version: '3'
services:
  sunshine:
    image: ghcr.io/games-on-whales/sunshine:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=all
    volumes:
      - ./sunshine:/etc/sunshine
      - ./games:/mnt/games
    ports:
      - "47984-47990:47984-47990/tcp"
      - "48010:48010"
      - "47998-48000:47998-48000/udp"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

This approach is ideal for dedicated GPU servers or cloud instances where you want a containerized gaming environment.

## Configuring Moonlight Clients

Moonlight is available on every major platform. The setup process is consistent across all clients:

1. **Install Moonlight** from your platform's app store or [moonlight-stream.org](https://moonlight-stream.org)
2. **Open Moonlight** — it will auto-discover Sunshine hosts on the local network via mDNS
3. **Pair the devices** — Moonlight displays a PIN; enter it in the Sunshine web UI under "PIN" to complete pairing
4. **Configure stream settings** — resolution, bitrate, frame rate, and decoder preference

### Optimal Moonlight Settings for Different Scenarios

**LAN Gaming (wired connection):**
- Resolution: Native (up to 4K)
- Frame Rate: 120 FPS
- Bitrate: 50-80 Mbps
- Decoder: Hardware (NVDEC/VA-API)

**Wi-Fi Gaming (5GHz):**
- Resolution: 1440p or 1080p
- Frame Rate: 60 FPS
- Bitrate: 25-40 Mbps
- Decoder: Hardware

**Internet Streaming (via Tailscale/ZeroTier):**
- Resolution: 1080p
- Frame Rate: 60 FPS
- Bitrate: 15-25 Mbps
- Decoder: Hardware (or software if hardware decoder unavailable)

## Streaming Over the Internet

The Sunshine/Moonlight stack works flawlessly on a local network, but streaming over the internet requires additional infrastructure. Here are the three most common approaches:

### Option 1: Tailscale or ZeroTier (Recommended)

Set up a WireGuard-based mesh VPN to create a secure private network between your host and clients:

```bash
# Install Tailscale on the Sunshine host
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --advertise-exit-node

# Install Tailscale on the client device
# Then connect to the host's Tailscale IP (100.x.x.x) from Moonlight
```

This approach requires no port forwarding, provides encryption, and works behind NAT. Latency is typically 5-15ms higher than direct LAN but still very playable.

### Option 2: Port Forwarding

Forward the Sunshine ports on your router directly to the host machine:

```
TCP: 47984-47990, 48010
UDP: 47998-48000
```

This gives the lowest internet latency but exposes your gaming machine directly to the internet. Combine with strong Sunshine PIN authentication and consider restricting source IPs if your router supports it.

### Option 3: Cloudflare Tunnel

For advanced users, Cloudflare Tunnel can proxy the Sunshine web UI for configuration, while game streaming itself uses direct UDP connections. This is more complex to set up but provides DDoS protection.

## Performance Tuning and Encoder Selection

Sunshine supports multiple hardware encoders. The choice significantly impacts both quality and latency:

| Encoder | Platform | Quality | Latency | Best For |
|---------|----------|---------|---------|----------|
| **NVENC H.264** | NVIDIA GPU | Excellent | Lowest | NVIDIA RTX/GTX GPUs |
| **NVENC HEVC** | NVIDIA GPU | Best (10-bit/HDR) | Lowest | HDR gaming, 4K |
| **AMF H.264** | AMD GPU | Good | Low | AMD Radeon GPUs |
| **AMF HEVC** | AMD GPU | Good | Low | HDR on AMD |
| **QSV H.264** | Intel iGPU | Good | Low | Intel Arc or integrated graphics |
| **Software (x264)** | CPU | Good | High | Fallback (no GPU encoder) |

For the best experience, use NVENC HEVC with an NVIDIA GPU. Enable the following Sunshine settings:

```json
{
  "encoder": "nvenc",
  "encoderOptions": {
    "hevc_mode": 2,
    "preset": "p4",
    "tune": "ull",
    "rc_mode": 3
  }
}
```

In the Sunshine web UI, navigate to Configuration → Video and set:
- **Encoder:** NVENC (HEVC for HDR, H.264 for SDR)
- **Rate Control Mode:** CBR (constant bitrate)
- **Adaptive Quantization:** Enabled
- **Look-ahead:** Disabled (adds latency)

For AMD GPUs, select AMF with the "Low Latency" preset. For Intel, use QSV with the "Quality" preset.

## Common Issues and Troubleshooting

**Moonlight cannot find Sunshine host:**
- Ensure both devices are on the same subnet
- Check that Sunshine is running: `systemctl status sunshine`
- Verify firewall rules allow ports 47984-47990 (TCP) and 47998-48000 (UDP)
- Try connecting manually by entering the host IP in Moonlight

**Stuttering or frame drops:**
- Reduce the stream bitrate in Sunshine's web UI
- Switch from HEVC to H.264 encoding (lower CPU/GPU overhead)
- Ensure the client uses hardware decoding (not software)
- On Wi-Fi, check signal strength and channel interference

**Controller not recognized:**
- Verify the controller is connected to the client device (not the host)
- In Moonlight settings, ensure "Gamepad" is enabled
- For DualSense controllers, enable "Adaptive Triggers" in Sunshine configuration

**Audio not working:**
- On Linux hosts, install PulseAudio or PipeWire
- In Sunshine settings, select the correct audio output device
- Restart Sunshine after changing audio configuration

**Black screen on connect:**
- This usually indicates a GPU encoder initialization failure
- Check `sunshine.log` for encoder errors
- Verify GPU drivers are installed and up to date
- Try switching to a different encoder in the Sunshine web UI

## FAQ

### Is Sunshine completely free to use?
Yes, Sunshine is 100% free and open-source (GPLv3 license). There are no premium tiers, subscription fees, or feature limitations. It is developed and maintained by the LizardByte community on GitHub.

### Do I need an NVIDIA GPU to use Sunshine?
No. Sunshine supports NVIDIA NVENC, AMD AMF, and Intel Quick Sync hardware encoders. It also includes a software encoder (x264) as a fallback if no GPU encoder is available, though this adds noticeable latency.

### Can I play games on my phone using Sunshine?
Yes. Moonlight is available on Android and iOS with full touch input, virtual gamepad controls, and Bluetooth controller support. You can stream your PC games to any smartphone or tablet on your network or over the internet.

### What is the difference between Sunshine and Moonlight?
Sunshine is the **host** — it runs on your gaming PC, captures the screen, encodes the video, and streams it. Moonlight is the **client** — it runs on your target device (phone, laptop, TV), receives the stream, and sends input back. You need both for game streaming.

### Does Sunshine work with Wayland on Linux?
Yes, Sunshine has Wayland support through PipeWire screen capture. However, some compositors (GNOME, KDE Plasma) may require additional configuration. X11 is still the most tested and stable option for Linux hosts.

### Can multiple people stream from the same Sunshine host simultaneously?
Sunshine supports multiple concurrent streams, but this requires significant GPU resources. Each active stream needs its own encoder session. A modern NVIDIA GPU (RTX 3060 or better) can typically handle 2-3 simultaneous 1080p streams.

### Is Parsec better than Sunshine for internet streaming?
Parsec has built-in NAT traversal and relay servers, making it easier to set up for internet streaming without port forwarding or VPN configuration. However, Sunshine + Tailscale achieves similar results with full self-hosting and no proprietary dependencies.

### How do I update Sunshine in Docker?
Pull the latest image and recreate the container:
```bash
docker pull lizardbyte/sunshine:latest-ubuntu-24.04
docker compose down
docker compose up -d
```
Your configuration persists in the mounted `/config` volume, so no re-setup is needed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Sunshine vs Parsec vs Moonlight: Self-Hosted Game Streaming Guide 2026",
  "description": "Compare Sunshine, Parsec, and Moonlight for self-hosted game streaming. Complete Docker setup guides, performance comparison, and best practices for playing PC games remotely in 2026.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
