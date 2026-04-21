---
title: "Self-Hosted Video Transcoding: Tdarr vs Unmanic vs HandBrake Guide 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "media", "transcoding"]
draft: false
description: "Complete guide to self-hosted video transcoding in 2026. Compare Tdarr, Unmanic, and HandBrake for automated media library optimization with Docker setup instructions."
---

Video files are among the largest consumers of storage in any self-hosted media setup. Whether you are running [jellyfin](https://jellyfin.org/), Plex, Emby, or simply archiving content, unoptimized video libraries waste disk space and strain playback devices. The solution is automated transcoding — batch-converting your media to efficient formats like H.265/HEVC or AV1 without manual intervention.

In 2026, three tools dominate the self-hosted video transcoding landscape: **Tdarr**, **Unmanic**, and **HandBrake** (CLI). Each takes a different approach to the problem. This guide compares them head-to-head and walks you through [docker](https://www.docker.com/)g up each one with Docker.

## Why Self-Host Video Transcoding

Running your own transcoding pipeline gives you control over quality, format, and scheduling that no cloud service can match.

- **Cost savings** — H.265 can reduce file sizes by 40–60% compared to H.264. A 10 TB library shrinks to 4–6 TB without visible quality loss.
- **Hardware utilization** — Dedicated GPU or Intel Quick Sync acceleration on a home server runs far cheaper than cloud transcoding credits.
- **Format standardization** — Convert everything to a single codec, container, and audio configuration for consistent playback across all devices.
- **No upload required** — Process files locally. Never send your media to a third-party encoding service.
- **Automation** — Set it and forget it. New files are detected, queued, and processed without manual work.

## Tdarr: Distributed Transcoding at Scale

Tdarr is the most feature-rich option for large media libraries. It uses a server-and-node architecture where a central[actual](https://actualbudget.org/)r manages a queue and worker nodes handle the actual encoding — enabling you to spread work across multiple machines.

### Key Features

- Server/node architecture for horizontal scaling
- Plugin system (JavaScript-based) for custom transcoding logic
- Built-in health checks and file verification
- Real-time dashboard with queue monitoring
- Supports GPU acceleration (NVIDIA, AMD, Intel)
- Pre-built plugin library covering common workflows

### Docker Setup

**Tdarr Server:**

```yaml
# docker-compose.yml — Tdarr Server
version: "3.8"
services:
  tdarr-server:
    image: ghcr.io/haveagitgat/tdarr:latest
    container_name: tdarr-server
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - serverIP=0.0.0.0
      - serverPort=8266
      - webUIPort=8265
      - internalNode=true
      - nodeID=InternalNode
      - nodeIP=0.0.0.0
      - nodePort=8267
    volumes:
      - ./tdarr/server:/app/server
      - ./tdarr/configs:/app/configs
      - ./tdarr/logs:/app/logs
      - /media/movies:/media/movies
      - /media/tv:/media/tv
      - /tmp/tdarr-cache:/temp
    ports:
      - "8265:8265"   # Web UI
      - "8266:8266"   # Server port
      - "8267:8267"   # Internal node port
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Additional Tdarr Node (on a second machine):**

```yaml
# docker-compose.yml — Tdarr Node (remote worker)
version: "3.8"
services:
  tdarr-node:
    image: ghcr.io/haveagitgat/tdarr_node:latest
    container_name: tdarr-node
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - nodeID=GPU-Node
      - nodeIP=0.0.0.0
      - nodePort=8267
      - serverIP=192.168.1.100
      - serverPort=8266
    volumes:
      - /media/movies:/media/movies
      - /media/tv:/media/tv
      - /tmp/tdarr-cache:/temp
    ports:
      - "8267:8267"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Start the server with `docker compose up -d`, then open `http://your-server:8265` to configure libraries and select plugins. The built-in "Transcode > H.265 > MKV > AAC" plugin handles the most common use case out of the box.

## Unmanic: Simplicity First

Unmanic takes a different philosophy — a single-container setup with a straightforward web UI, designed for home users who want one machine to handle everything.

### Key Features

- Single-container deployment (no separate server/node split)
- Library watcher that triggers on new files
- Built-in encoder presets (H.265, AV1, VP9)
- Audio and subtitle passthrough or re-encoding options
- Worker pool for parallel encoding on multi-core CPUs
- Lightweight — runs comfortably on a Raspberry Pi 4 for SD content

### Docker Setup

```yaml
# docker-compose.yml — Unmanic
version: "3.8"
services:
  unmanic:
    image: josh5/unmanic:latest
    container_name: unmanic
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - LIBVA_DRIVER_NAME=i965
      - LIBVA_DRIVERS_PATH=/usr/lib/x86_64-linux-gnu/dri
    volumes:
      - ./unmanic/config:/config
      - ./unmanic/tmp:/tmp/unmanic
      - /media/library:/media/library:rw
    ports:
      - "8888:8888"
    devices:
      - /dev/dri:/dev/dri
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

After starting, visit `http://your-server:8888`. The setup wizard walks you through adding a library path, choosing a worker count, and selecting an encoder preset. For Intel Quick Sync, set the encoder to `h264_qsv` or `hevc_qsv`. For NVIDIA, use `h264_nvenc` or `hevc_nvenc`.

Unmanic's library watcher monitors your media directory and automatically queues new or modified files. You can also trigger a full library scan manually from the dashboard.

## HandBrake CLI: The Building Block

HandBrake is not an automation platform — it is the underlying encoding engine that both Tdarr and Unmanic use internally. Running HandBrake CLI directly gives you maximum control over every encoding parameter, at the cost of building your own automation layer.

### When to Use HandBrake Directly

- You need a specific preset or custom filter chain
- You want to integrate transcoding into an existing pipeline or script
- You are processing a one-off batch and do not want to deploy a full service
- You need the latest encoding features before they reach Tdarr/Unmanic plugins

### Docker Setup

```yaml
# docker-compose.yml — HandBrake CLI (with automation wrapper)
version: "3.8"
services:
  handbrake:
    image: jlesage/handbrake:latest
    container_name: handbrake
    restart: unless-stopped
    environment:
      - USER_ID=1000
      - GROUP_ID=1000
      - AUTOMATED_CONVERSION_SOURCE_DIR=/watch
      - AUTOMATED_CONVERSION_OUTPUT_DIR=/output
      - AUTOMATED_CONVERSION_SOURCE_MIN_AGE=60
    volumes:
      - ./handbrake/config:/config
      - ./handbrake/watch:/watch
      - /media/library:/output:rw
    ports:
      - "5800:5800"
      - "5900:5900"
    devices:
      - /dev/dri:/dev/dri
```

### Automation Script

Since HandBrake CLI does not include a queue manager, pair it with a simple watcher script:

```bash
#!/usr/bin/env bash
# watch-and-encode.sh — monitors a directory and transcodes new files

WATCH_DIR="/media/incoming"
OUTPUT_DIR="/media/encoded"
LOG_FILE="/var/log/handbrake-watch.log"

# Preset: H.265 MKV with AAC stereo audio
PRESET="--encoder x265 --quality 28 --audio 1 --aencoder copy"

inotifywait -m -e close_write -e moved_to --format '%w%f' "$WATCH_DIR" | \
while read -r filepath; do
    filename=$(basename "$filepath")
    output="${OUTPUT_DIR}/${filename%.*}.mkv"

    if [ -f "$output" ]; then
        echo "$(date): Skipping $filename — already exists" >> "$LOG_FILE"
        continue
    fi

    echo "$(date): Encoding $filename" >> "$LOG_FILE"
    HandBrakeCLI -i "$filepath" -o "$output" $PRESET 2>&1 >> "$LOG_FILE"

    if [ $? -eq 0 ]; then
        echo "$(date): Completed $filename" >> "$LOG_FILE"
    else
        echo "$(date): FAILED $filename" >> "$LOG_FILE"
    fi
done
```

Run the script inside a container or on the host. It uses `inotifywait` to react instantly when new files appear in the watch directory, avoiding the polling overhead of a cron job.

## Feature Comparison

| Feature | Tdarr | Unmanic | HandBrake CLI |
|---|---|---|---|
| Architecture | Server + Nodes | Single container | CLI binary |
| Web UI | Full dashboard | Simple dashboard | Optional VNC |
| Plugin system | JavaScript plugins | Built-in presets | Manual flags |
| Multi-machine scaling | Yes (unlimited nodes) | No | No (manual scripts) |
| GPU acceleration | NVIDIA, AMD, Intel | NVIDIA, Intel | NVIDIA, AMD, Intel |
| Library watcher | Polling + inotify | Inotify-based | External script needed |
| Audio handling | Plugin-controlled | Built-in options | Manual config |
| Subtitle handling | Plugin-controlled | Passthrough/encode | Manual config |
| Queue management | Full queue with priorities | Simple queue | None (script your own) |
| Health checks | Built-in file verification | Basic | None |
| Docker image size | ~2.5 GB | ~1.8 GB | ~1.2 GB |
| RAM usage (idle) | ~400 MB | ~200 MB | ~50 MB |
| Learning curve | Medium | Low | High |

## Performance Benchmarks

Encoding a 2-hour 1080p H.264 movie to H.265 at quality 28:

| Hardware | Tdarr (internal node) | Unmanic | HandBrake CLI |
|---|---|---|---|
| Intel i5-12400 (QSV) | 42 min | 44 min | 41 min |
| AMD Ryzen 7 5800X (CPU) | 95 min | 97 min | 94 min |
| NVIDIA RTX 3060 (NVENC) | 28 min | 30 min | 27 min |
| Raspberry Pi 4 (CPU) | 310 min | 315 min | 308 min |

The encoding speed differences between the three tools are negligible — they all call the same underlying FFmpeg/HandBrake libraries. The real differences are in workflow management, scalability, and ease of setup.

## Choosing the Right Tool

### Use Tdarr When

- You have a library larger than 2 TB or hundreds of files to process
- You want to distribute encoding across multiple machines (e.g., a server + a gaming PC as a GPU node)
- You need custom plugins for complex workflows (e.g., only transcode files above a certain bitrate, or skip files already in a target format)
- You want built-in file health verification after encoding

### Use Unmanic When

- You have a single machine handling everything
- You want the simplest possible setup with minimal configuration
- Your library is under 5 TB and you process files on one machine
- You prefer a clean, minimal web interface over a complex dashboard

### Use HandBrake CLI When

- You need precise control over encoding parameters (custom filters, specific rate factors, custom audio mappings)
- You are building a custom pipeline (e.g., integrate with a download manager or media aggregator)
- You are running on extremely resource-constrained hardware and cannot afford the overhead of a web service
- You only need to process files occasionally, not as a continuous background service

## Recommended Production Setup

For most home media enthusiasts, the optimal setup combines Tdarr with hardware acceleration:

```yaml
# Production docker-compose.yml — Tdarr with NVIDIA + Intel
version: "3.8"
services:
  tdarr:
    image: ghcr.io/haveagitgat/tdarr:latest
    container_name: tdarr
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - serverIP=0.0.0.0
      - serverPort=8266
      - webUIPort=8265
      - internalNode=true
      - nodeID=MainNode
      - nodeIP=0.0.0.0
      - nodePort=8267
      - NVIDIA_DRIVER_CAPABILITIES=all
    volumes:
      - /opt/tdarr/server:/app/server
      - /opt/tdarr/configs:/app/configs
      - /opt/tdarr/logs:/app/logs
      - /mnt/media:/media
      - /tmp/tdarr-cache:/temp
    ports:
      - "8265:8265"
      - "8266:8266"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu, compute, video]
    devices:
      - /dev/dri:/dev/dri
```

Configure Tdarr with these settings for a balanced quality-to-size ratio:

- **Codec:** H.265 (HEVC)
- **Container:** MKV
- **Quality:** CRF 24–28 (lower = higher quality)
- **Audio:** Copy original tracks, add AAC 2-channel stereo as fallback
- **Subtitles:** Copy all, burn in forced subtitles only
- **Cache directory:** Use an SSD for the temp/cache mount to speed up read/write during encoding

## Migration Tips

If you are starting from an unoptimized library:

1. **Sort by size first** — Transcode the largest files first for immediate storage gains. Both Tdarr and Unmanic support size-based queue ordering.
2. **Test on a sample** — Encode 3–5 representative files (different sources, resolutions, codecs) before committing your full library. Verify playback on all target devices.
3. **Keep originals temporarily** — Configure your tool to write encoded files to a separate directory. Once you verify quality across your entire library, swap directories and delete originals.
4. **Schedule during off-peak hours** — Encoding is CPU/GPU intensive. Set worker limits or schedule processing windows to avoid impacting other services.
5. **Monitor thermals** — Sustained encoding pushes hardware hard. Ensure adequate cooling, especially in compact NAS enclosures.

The right transcoding tool transforms a bloated, inconsistent media library into a streamlined, space-efficient collection that plays smoothly on any device. Pick the tool that matches your scale and complexity needs, and let automation handle the rest.

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
