---
title: "Self-Hosted Live Streaming: Owncast, MediaMTX & Nginx RTMP in 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "streaming"]
draft: false
description: "A complete guide to self-hosted live streaming in 2026. Compare Owncast, MediaMTX, and Nginx RTMP for running your own YouTube and Twitch alternative with full control over your content."
---

## Why Self-Host Your Live Streaming Infrastructure?

The live streaming landscape in 2026 is dominated by a handful of centralized platforms. YouTube Live, Twitch, and Facebook Live control the market, but they come with significant trade-offs: unpredictable algorithm changes, sudden demonetization, strict content moderation policies, and revenue splits that favor the platform over the creator.

Self-hosting your live streaming infrastructure changes the equation entirely. You own the server, the audience data, the chat history, and the entire viewer experience. There are no surprise takedowns, no algorithmic shadow-banning, and no revenue sharing. For organizations, educators, and independent creators, a self-hosted streaming stack provides complete control over branding, moderation, and distribution.

The open-source ecosystem has matured significantly. Tools like Owncast deliver a polished, all-in-one streaming experience with built-in chat, user management, and embed support. MediaMTX (formerly rtsp-simple-server) handles protocol conversion and relay with minimal resource usage. And [nginx](https://nginx.org/) with the RTMP module remains the battle-tested foundation for custom streaming pipelines. This guide covers all three, with practical setup instructions so you can get broadcasting on your own terms.

## Owncast: The All-in-One Streaming Platform

[Owncast](https://owncast.online/) is a self-hosted live video and chat server designed as a direct alternative to Twitch and YouTube Live. It provides a complete out-of-the-box experience: a web interface for viewers, real-time chat, user accounts, directory integration, and customizable branding — all from a single binary.

### Key Features

- **Built-in chat system** with user authentication, moderation tools, and message persistence
- **Video directory** — register your instance in the Owncast Directory for discoverability
- **Offline pages** — automatic fallback when you're not broadcasting
- **Embedded player** — easily embed your stream on any website
- **Webhook integrations** — connect to external services for notifications and automation
- **Multi-platform streaming** — restream to Twitch, YouTube, and other platforms simultaneously
- **API-first design** — full REST API for custom integrations

### [docker](https://www.docker.com/) Installation

Owncast ships as a single binary, but Docker is the recommended deployment method for production:

```bash
# Create persistent directories
mkdir -p /opt/owncast/data /opt/owncast/video

# Run Owncast with Docker
docker run -d \
  --name owncast \
  -p 8080:8080 \
  -p 1935:1935 \
  -v /opt/owncast/data:/app/data \
  -v /opt/owncast/video:/app/video \
  --restart unless-stopped \
  ghcr.io/owncast/owncast:latest
```

Once the container is running, access the admin panel at `http://your-server:8080/admin`. The default credentials are `admin` / `abc123` — change these immediately.

### Streaming to Owncast

Configure OBS Studio (or any RTMP-compatible encoder) with these settings:

| Setting | Value |
|---------|-------|
| Server | `rtmp://your-server:1935/live` |
| Stream Key | Set in Owncast admin panel |
| Video Codec | H.264 |
| Audio Codec | AAC |
| Resolution | 1920x1080 or 1280x720 |
| Frame Rate | 30 or 60 fps |
| Bitrate | 3000–6000 kbps |

```bash
# Example FFmpeg command for direct streaming
ffmpeg -re -i input.mp4 \
  -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k \
  -pix_fmt yuv420p -g 60 \
  -c:a aac -b:a 128k -ar 44100 \
  -f flv rtmp://your-server:1935/live/YOUR_STREAM_KEY
```

### Nginx Reverse Proxy Configuration

For production use, put Owncast behind Nginx with TLS:

```nginx
server {
    listen 443 ssl http2;
    server_name stream.example.com;

    ssl_certificate /etc/letsencrypt/live/stream.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stream.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for chat
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # RTMP passthrough (if needed)
    location /hls/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_buffering off;
        cache off;
    }
}
```

### Owncast Configuration File

For advanced tuning, create a `config.yaml`:

```yaml
# /opt/owncast/data/config.yaml
instance_details:
  instance_url: "https://stream.example.com"
  title: "My Streaming Server"
  summary: "Self-hosted live streaming"

s3:
  enabled: false  # Enable for external storage
  # endpoint: ""
  # bucket: ""
  # region: ""

webserver:
  enable: true
  listen_address: "0.0.0.0"
  http_listen_port: 8080
  rtmp_listen_port: 1935

logging:
  level: info
```

## MediaMTX: The Protocol Conversion Powerhouse

[MediaMTX](https://github.com/bluenviron/mediamtx) (formerly rtsp-simple-server) is a lightweight media server that specializes in protocol conversion, relay, and distribution. It accepts streams in one format and serves them in multiple formats simultaneously — RTSP, RTMP, HLS, SRT, and WebRTC — making it ideal for reaching viewers across different playback environments.

### Key Features

- **Multi-protocol support** — RTSP, RTMP, HLS, SRT, WebRTC, and UDP out of the box
- **Protocol conversion** — publish in one format, consume in another
- **Path configuration** — define per-path behavior with wildcards
- **Authentication** — per-path publish and read access control
- **External authentication hooks** — integrate with your own auth service
- **Minimal resource usage** — runs comfortably on a $5 VPS
- **Run-on-demand** — start publishers automatically when viewers connect
- **Recording** — save incoming streams to disk

### Docker Installation

```bash
mkdir -p /opt/mediamtx/config

# Generate default configuration
docker run --rm bluenviron/mediamtx cat mediamtx.yml > /opt/mediamtx/config/mediamtx.yml

# Run MediaMTX
docker run -d \
  --name mediamtx \
  --network host \
  -v /opt/mediamtx/config/mediamtx.yml:/mediamtx.yml:ro \
  --restart unless-stopped \
  bluenviron/mediamtx:latest
```

The `--network host` flag is recommended because MediaMTX uses multiple ports across different protocols. If you prefer explicit port mapping:

```bash
docker run -d \
  --name mediamtx \
  -p 8554:8554 \   # RTSP
  -p 1935:1935 \   # RTMP
  -p 8889:8889 \   # HLS
  -p 8189:8189/udp \ # SRT
  -p 8890:8890 \   # WebRTC
  -v /opt/mediamtx/config/mediamtx.yml:/mediamtx.yml:ro \
  --restart unless-stopped \
  bluenviron/mediamtx:latest
```

### Essential Configuration

Edit `/opt/mediamtx/config/mediamtx.yml`:

```yaml
# Global settings
logLevel: info
readTimeout: 10s
writeTimeout: 10s
writeQueueSize: 512

# RTSP settings
protocols: [tcp, udp, multicast]
encryption: optional

# RTMP settings
rtmpEncryption: optional

# HLS settings
hlsVariant: lowLatency
hlsSegmentCount: 7
hlsSegmentDuration: 1s
hlsPartDuration: 200ms

# WebRTC settings
webrtcAdditionalHosts: ["stream.example.com"]
webrtcICEHostNAT1To1IPs: ["YOUR_PUBLIC_IP"]

# Path configuration
paths:
  all:
    # Allow any path name
    runOnPublish:
    runOnDemand:
    runOnUnpublish:

  live:
    # Specific path with authentication
    publishUser: publisher
    publishPass: secure_password_here
    readUser: ""
    readPass: ""

  camera1:
    # Camera stream with SRT source
    source: srt://127.0.0.1:9999
    runOnPublish:
      - ffmpeg -i rtsp://127.0.0.1:8554/camera1 \
        -c:v libx264 -preset fast -b:v 2000k \
        -f flv rtmp://127.0.0.1:1935/live/camera1-recording
```

### Streaming Workflow with MediaMTX

MediaMTX shines when you need to accept a stream from one source and distribute it in multiple formats:

```bash
# Publish RTSP to MediaMTX
ffmpeg -re -i input.mp4 -c copy -f rtsp rtsp://your-server:8554/mystream

# Viewers can now consume via:
# RTSP:  rtsp://your-server:8554/mystream
# RTMP:  rtmp://your-server:1935/mystream
# HLS:   http://your-server:8889/mystream/index.m3u8
# WebRTC: https://your-server:8890/mystream (via browser)
# SRT:   srt://your-server:8899?streamid=#!::r=mystream
```

This multi-protocol capability means you can publish once from OBS (RTMP) and have viewers access the stream through whatever protocol their player supports — no extra transcoding needed.

## Nginx RTMP Module: The Classic Streaming Foundation

The [Nginx RTMP module](https://github.com/arut/nginx-rtmp-module) has been the backbone of self-hosted streaming for over a decade. While it lacks the polished web interface of Owncast or the multi-protocol flexibility of MediaMTX, it remains the go-to choice for custom streaming pipelines where you need fine-grained control over every aspect of the stream.

### Key Features

- **Rock-solid stability** — battle-tested in production for over a decade
- **HLS and DASH** — adaptive bitrate streaming support built in
- **Exec directives** — trigger external scripts on stream events (publish, publish done, play, play done)
- **Recording** — automatic stream recording to disk with configurable rotation
- **Relay/pull** — pull streams from other RTMP servers for redundancy
- **Push to multiple destinations** — simultaneously restream to other platforms
- **Bandwidth limiting** — per-application and per-connection rate control
- **Stat endpoint** — XML API for monitoring active streams and viewers

### Building Nginx with RTMP Module

```bash
# Install dependencies
apt update && apt install -y \
  build-essential libpcre3 libpcre3-dev libssl-dev \
  zlib1g-dev git wget

# Download Nginx and RTMP module
NGINX_VERSION=1.25.4
cd /tmp
wget https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz
tar xzf nginx-${NGINX_VERSION}.tar.gz
git clone https://github.com/arut/nginx-rtmp-module.git

# Compile
cd nginx-${NGINX_VERSION}
./configure \
  --with-http_ssl_module \
  --add-module=../nginx-rtmp-module \
  --with-http_v2_module \
  --with-http_stub_status_module

make -j$(nproc)
make install
```

### Docker Alternative (Recommended)

```bash
docker run -d \
  --name nginx-rtmp \
  -p 1935:1935 \
  -p 8080:8080 \
  -p 8443:8443 \
  -v /opt/nginx-rtmp/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /opt/nginx-rtmp/hls:/tmp/hls \
  -v /opt/nginx-rtmp/recordings:/tmp/recordings \
  --restart unless-stopped \
  tiangolo/nginx-rtmp
```

### Nginx RTMP Configuration

A production-ready `/etc/nginx/nginx.conf`:

```nginx
worker_processes auto;
events {
    worker_connections 1024;
}

rtmp {
    server {
        listen 1935;
        chunk_size 4096;
        ping 30s;
        ping_timeout 10s;

        application live {
            live on;
            record off;

            # HLS output
            hls on;
            hls_path /tmp/hls;
            hls_fragment 3s;
            hls_playlist_length 60s;
            hls_continuous on;
            hls_nested on;

            # Adaptive bitrate — multiple qualities
            exec ffmpeg -i rtmp://localhost:1935/live/$name
                -c:v libx264 -preset veryfast -b:v 1500k -s 854x480
                -c:a aac -b:a 64k -f flv rtmp://localhost:1935/live/${name}_480p
                -c:v libx264 -preset veryfast -b:v 3000k -s 1280x720
                -c:a aac -b:a 128k -f flv rtmp://localhost:1935/live/${name}_720p
                -c:v copy -c:a copy -f flv rtmp://localhost:1935/live/${name}_source;

            # Stream events
            on_publish http://localhost:8080/auth/publish;
            on_publish_done http://localhost:8080/events/done;

            # Push to external platform (restream)
            # push rtmp://live.twitch.tv/app/YOUR_KEY;
        }

        application recording {
            live on;
            record all;
            record_path /tmp/recordings;
            record_unique on;
            record_max_size 500M;
            record_max_frames 60000;
        }

        application hls {
            live on;
            hls on;
            hls_path /tmp/hls;
            hls_fragment 2s;
            hls_playlist_length 30s;
        }
    }
}

http {
    include mime.types;
    default_type application/octet-stream;

    server {
        listen 8080;
        server_name _;

        # HLS delivery
        location /hls/ {
            types {
                application/vnd.apple.mpegurl m3u8;
                video/mp2t ts;
            }
            root /tmp;
            add_header Cache-Control no-cache;
            add_header Access-Control-Allow-Origin *;
        }

        # RTMP statistics
        location /stat {
            rtmp_stat all;
            rtmp_stat_stylesheet stat.xsl;
        }

        location /stat.xsl {
            root /path/to/nginx-rtmp-module/;
        }

        # Authentication webhook
        location /auth/publish {
            return 200;
        }

        location /events/done {
            return 200;
        }
    }
}
```

### Adaptive Bitrate Setup

The configuration above demonstrates how to create multiple quality levels from a single incoming stream. Viewers with slow connections get the 480p variant, while those on fast connections receive the source quality. The HLS player automatically switches between variants based on available bandwidth:

```html
<!-- HLS player with adaptive bitrate -->
<video id="player" controls width="960">
    <source src="http://your-server:8080/hls/stream_name/playlist.m3u8"
            type="application/x-mpegURL">
</video>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<script>
    if (Hls.isSupported()) {
        const video = document.getElementById('player');
        const hls = new Hls();
        hls.loadSource(video.src);
        hls.attachMedia(video);
    }
</script>
```

## Comparison: Owncast vs MediaMTX vs Nginx RTMP

| Feature | Owncast | MediaMTX | Nginx RTMP |
|---------|---------|----------|------------|
| **Primary Use Case** | Creator platform | Protocol relay | Custom pipelines |
| **Web Interface** | Full viewer UI + admin | None (API only) | None |
| **Chat System** | Built-in | None | None |
| **Protocols** | RTMP in, HLS out | RTSP, RTMP, HLS, SRT, WebRTC | RTMP in, HLS/DASH out |
| **User Management** | Yes (OAuth, local) | Authentication hooks | External auth via hooks |
| **Multi-bitrate** | No (single quality) | No (passthrough) | Yes (via FFmpeg exec) |
| **Recording** | Automatic | Configurable | Configurable |
| **Directory Listing** | Owncast Directory | N/A | N/A |
| **REST API** | Extensive | Basic (API v2) | Stat endpoint only |
| **Webhooks** | Yes (many events) | Run-on-demand hooks | Exec directives |
| **Resource Usage** | Moderate (~200MB RAM) | Minimal (~30MB RAM) | Low (~50MB RAM) |
| **Transcoding** | No (requires external) | No (passthrough) | Yes (via FFmpeg) |
| **Difficulty** | Easy | Moderate | Advanced |
| **Best For** | Creators, communities | Multi-protocol needs | Custom pipelines |

## Choosing the Right Tool

**Pick Owncast if** you want a complete, ready-to-use streaming platform with minimal setup. It's the best choice for individual creators, small communities, and organizations that need a Twitch-like experience with chat, user accounts, and branding — all from a single deployment. The built-in directory also helps with discoverability.

**Pick MediaMTX if** your primary challenge is protocol conversion. If you have cameras publishing RTSP, viewers needing HLS, and some who want WebRTC, MediaMTX handles all of this simultaneously with near-zero resource overhead. It's also excellent as a relay layer between your encoder and your viewer-facing frontend.

**Pick Nginx RTMP if** you need maximum control over the streaming pipeline. When you require custom transcoding, adaptive bitrate streaming, com[plex](https://www.plex.tv/) event hooks, or integration with existing Nginx infrastructure, the RTMP module gives you the flexibility to build exactly what you need. It's the foundation that Owncast and many other streaming tools are built on top of.

**Combining tools** is also a common pattern: use MediaMTX for protocol ingestion and conversion, then feed the output into Owncast for the viewer-facing experience. Or run Nginx RTMP for transcoding and HLS packaging, with a separate web frontend handling the user interface and chat.

## Hardware and Bandwidth Requirements

For a small self-hosted streaming setup (under 50 concurrent viewers):

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores (for transcoding) |
| **RAM** | 2 GB | 4 GB |
| **Storage** | 20 GB (for recordings) | 100+ GB SSD |
| **Upload** | 10 Mbps | 50+ Mbps |
| **Download** | 5 Mbps | 20+ Mbps |

Without transcoding (Owncast passthrough mode, MediaMTX relay), CPU requirements drop significantly — a 1-core VPS with 1 GB RAM can handle a single stream with dozens of viewers. Transcoding is the main resource consumer, so if you need multiple quality levels, budget for additional CPU capacity or use a GPU-accelerated FFmpeg build.

## Final Thoughts

Self-hosted live streaming in 2026 is no longer a compromise. The tools available — Owncast for the complete experience, MediaMTX for protocol flexibility, and Nginx RTMP for custom pipelines — cover every use case from solo creator broadcasts to enterprise streaming infrastructure. The key is matching the tool to your specific needs: user-facing features, protocol requirements, and available hardware.

Start with Owncast if you want to go live today with a polished viewer experience. Add MediaMTX if you need to handle multiple input protocols or run a low-resource relay. Reach for Nginx RTMP when you need the flexibility to build a custom streaming architecture from the ground up.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
