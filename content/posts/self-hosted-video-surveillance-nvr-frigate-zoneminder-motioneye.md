---
title: "Best Self-Hosted Video Surveillance & NVR 2026: Frigate vs ZoneMinder vs MotionEye"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy", "security", "home-automation"]
draft: false
description: "A comprehensive comparison of the best self-hosted video surveillance and NVR systems in 2026. Set up Frigate, ZoneMinder, or MotionEye with Docker and take full control of your security camera infrastructure."
---

Running your own video surveillance system gives you complete ownership of every frame your cameras record. No cloud subscriptions, no data sent to third-party servers, and no monthly fees for recording history. In 2026, the open-source NVR (Network Video Recorder) landscape offers mature, production-ready options that rival commercial products — with the added benefits of privacy and total control.

This guide compares three of the most capable self-hosted surveillance platforms: Frigate, ZoneMinder, and MotionEye. Each has a different philosophy, and the right choice depends on your hardware, camera setup, and feature requirements.

## Why Self-Host Your Video Surveillance

The case for running your own NVR goes far beyond avoiding subscription fees:

**Complete privacy.** Commercial cloud cameras stream your footage to external servers. With a self-hosted system, every frame stays on your local network. Your home, your family, and your property are not someone else's data asset.

**No recurring costs.** Cloud camera subscriptions range from $3 to $30 per camera per month. A self-hosted NVR running on a low-power mini PC or a Raspberry Pi with an external drive costs nothing beyond electricity and storage hardware.

**Unlimited recording history.** Cloud plans cap you at 7 or 30 days of footage. With local storage, you decide how long to keep recordings — days, weeks, or months — limited only by your disk capacity.

**Integration flexibility.** Self-hosted systems integrate with Home Assistant via MQTT, expose APIs for custom automations, and work with virtually any ONVIF or RTSP camera. You are not locked into a single camera brand.

**Resilience during outages.** When your internet goes down, cloud cameras often stop recording or lose functionality. A local NVR keeps recording regardless of your internet connection status.

**Multi-camera scalability.** Commercial systems charge per camera. With self-hosted solutions, adding a camera costs nothing — just plug it in and configure it.

## Frigate: The Modern Contender

Frigate is a rapidly growing NVR built from the ground up for modern hardware. It uses hardware-accelerated video decoding and is designed to run efficiently on consumer-grade equipment, including Raspberry Pi 4/5 and Intel NUC machines with integrated GPUs.

### Architecture

Frigate's architecture is purpose-built for performance:

- **FFmpeg processes** — one per camera, handling RTSP stream ingestion, decoding, and recording
- **Detection pipeline** — processes frames at configurable intervals to identify objects
- **MQTT broker** — publishes detection events for integration with other systems
- **Web UI** — modern interface for live viewing, event review, and configuration
- **SQLite database** — stores event metadata and timeline information

### Key Features

- Hardware-accelerated decoding (Intel QuickSync, VAAPI, NVIDIA NVDEC)
- Native Home Assistant integration via the Frigate add-on
- MQTT event publishing for automation triggers
- Built-in notification system with snapshot delivery
- Support for multiple camera types (ONVIF, RTSP, generic IP cameras)
- Timeline-based event browser with filtering
- Birdseye view — combines all cameras into a single overview
- Go2RTC integration for low-latency WebRTC streaming

### Docker Installation

The recommended way to run Frigate is with Docker Compose. Here is a complete configuration for a typical setup with hardware acceleration on an Intel NUC:

```yaml
version: "3.9"
services:
  frigate:
    container_name: frigate
    image: ghcr.io/blakeblackshear/frigate:stable
    restart: unless-stopped
    privileged: true
    shm_size: "256m"
    devices:
      - /dev/dri/renderD128:/dev/dri/renderD128  # Intel QuickSync
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - ./frigate/config:/config
      - ./frigate/media:/media:rw
      - type: tmpfs
        target: /tmp/cache
        tmpfs:
          size: 1000000000  # 1GB RAM cache for recording
    ports:
      - "5000:5000"   # Web UI
      - "8554:8554"   # RTSP feeds
      - "8555:8555"   # WebRTC
    environment:
      - FRIGATE_RTSP_PASSWORD=your_rtsp_password
```

### Frigate Configuration

Create `./frigate/config/config.yml`:

```yaml
mqtt:
  enabled: true
  host: mqtt-broker.local
  port: 1883
  topic_prefix: frigate
  user: frigate_user
  password: mqtt_password

detectors:
  cpu_detector:
    type: cpu

cameras:
  front_door:
    ffmpeg:
      inputs:
        - path: rtsp://admin:password@192.168.1.100:554/stream1
          roles:
            - detect
            - record
        - path: rtsp://admin:password@192.168.1.100:554/stream2
          roles:
            - record
    detect:
      width: 1280
      height: 720
      fps: 5
    record:
      enabled: true
      retain:
        days: 14
        mode: all
      events:
        retain:
          default: 30
          mode: motion
    motion:
      mask:
        - 0,0,200,0,200,200,0,200  # Mask a tree that moves in wind

objects:
  track:
    - person
    - car
    - dog
  filters:
    person:
      min_area: 5000
      threshold: 0.7

snapshots:
  enabled: true
  clean_copy: true
  retain:
    default: 30
```

This configuration sets up a single camera with dual RTSP streams — a lower-resolution stream for detection and a higher-resolution stream for recording. The motion mask prevents false triggers from a tree swaying in the wind.

### Hardware Requirements

- **Minimum:** Raspberry Pi 4 with 4 GB RAM, handles 2-3 cameras at lower resolution
- **Recommended:** Intel NUC or similar with QuickSync, handles 8-16 cameras
- **Storage:** 1 TB HDD for ~14 days of 1080p recording across 4 cameras
- **Network:** Gigabit Ethernet recommended for multiple cameras

## ZoneMinder: The Battle-Tested Veteran

ZoneMinder has been around since 2003, making it one of the oldest and most feature-complete open-source surveillance platforms. It is available in most Linux distribution repositories and has been hardened by two decades of real-world deployment.

### Architecture

ZoneMinder follows a traditional client-server model:

- **zmfilter** — event filtering and notification daemon
- **zmc** — capture daemon, one instance per monitor
- **zma** — analysis daemon, performs motion detection
- **zmdc** — daemon controller that manages all other processes
- **Web interface** — PHP-based console for configuration and monitoring
- **MySQL/MariaDB** — stores event metadata and configuration

### Key Features

- Supports virtually any camera (V4L2, FFmpeg, ONVIF, RTSP, HTTP, local capture cards)
- Advanced motion detection with configurable zones
- Event-based recording with pre- and post-event buffering
- PTZ (Pan-Tilt-Zoom) camera control
- Multi-monitor display with customizable layouts
- API for external integration
- Event export in multiple formats
- User permission system with role-based access
- Bandwidth management with adaptive quality
- Plugin ecosystem for extended functionality

### Docker Installation

ZoneMinder runs well in Docker. The `dlandon/zoneminder` image is the most widely used and actively maintained:

```yaml
version: "3.9"
services:
  zoneminder:
    container_name: zoneminder
    image: dlandon/zoneminder:latest
    restart: unless-stopped
    network_mode: host
    privileged: true
    volumes:
      - ./zoneminder/config:/config
      - ./zoneminder/data:/var/cache/zoneminder
      - ./zoneminder/events:/var/lib/zoneminder/events
    environment:
      - TZ=America/New_York
      - ZM_PASSWORD=admin
      - MYSQL_ROOT_PASSWORD=zmsql_root_pass
      - SHMEM="50%"
```

For a more production-oriented setup, separate the database:

```yaml
version: "3.9"
services:
  zm-db:
    container_name: zm-db
    image: mariadb:10.11
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=zmsql_root_pass
      - MYSQL_DATABASE=zm
      - MYSQL_USER=zmuser
      - MYSQL_PASSWORD=zmpass
    volumes:
      - ./zm-db/data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  zoneminder:
    container_name: zoneminder
    image: dlandon/zoneminder:latest
    restart: unless-stopped
    depends_on:
      zm-db:
        condition: service_healthy
    ports:
      - "8080:80"
      - "9000:9000"
    volumes:
      - ./zoneminder/config:/config
      - ./zoneminder/events:/var/lib/zoneminder/events
    environment:
      - TZ=America/New_York
      - SHMEM="50%"
      - MYSQL_HOST=zm-db
      - MYSQL_ROOT_PASSWORD=zmsql_root_pass
```

### Initial Configuration

After launching, access ZoneMinder at `http://your-server:8080/zm`. The first steps:

1. Log in with the default credentials (admin/admin)
2. Navigate to **Options > System** and set your timezone
3. Go to **Monitors > Add New Monitor** to add your first camera
4. Select **Source Type: FFMpeg** and enter your camera's RTSP URL
5. Configure **Motion Detection Zones** by drawing regions on the camera view
6. Set **Recording Mode** to "Modect" (motion detection) or "Record" (continuous)

For ONVIF cameras, use the ONVIF probe feature:

```bash
# Install onvif-cli inside the container for camera discovery
docker exec zoneminder pip3 install onvif-zeep
docker exec zoneminder python3 -c "
from onvif import ONVIFCamera
cam = ONVIFCamera('192.168.1.100', 80, 'admin', 'password')
media = cam.create_media_service()
profiles = media.GetProfiles()
for p in profiles:
    print(f'Profile: {p.Name}, Token: {p.token}')
"
```

### Performance Tuning

ZoneMinder can be resource-intensive. Key tuning parameters in **Options > System**:

| Parameter | Recommended Value | Effect |
|-----------|-------------------|--------|
| `IMAGE_BUFFER_SIZE` | 20-50 | Pre-event frames buffered in RAM |
| `MAX_PACKET_SIZE` | 10000 | Network packet size for IP cameras |
| `EVENT_CHECK_HOUR` | 2 | Hour to run event cleanup |
| `WATCH_MAX_DELAY` | 30 | Seconds before restarting a dead capture process |

For multi-camera setups, consider running `zmc` and `zma` on separate machines using ZoneMinder's distributed analysis feature.

## MotionEye: The Lightweight Option

MotionEye is a web frontend for the `motion` daemon, a lightweight motion detection program. It is the simplest option to set up and runs comfortably on low-power hardware like a Raspberry Pi Zero 2 W.

### Architecture

MotionEye's architecture is straightforward:

- **motion daemon** — captures video and performs motion detection
- **motionEye** — Python-based web frontend for configuration and viewing
- **SQLite** — optional database for settings persistence
- **File system** — stores captured images and videos directly

### Key Features

- Simple, clean web interface
- Motion detection with configurable sensitivity and thresholds
- Timelapse support with configurable intervals
- Multi-camera support
- Email and webhook notifications on motion events
- Built-in scheduling (arm/disarm on a schedule)
- Network share support (NFS, SMB, Google Drive)
- Camera streaming via MJPEG
- Low resource footprint — runs on minimal hardware

### Docker Installation

```yaml
version: "3.9"
services:
  motioneye:
    container_name: motioneye
    image: ccrisan/motioneye:master-amd64
    restart: unless-stopped
    ports:
      - "7999:7999"   # Web UI
      - "8081:8081"   # Camera stream 1
      - "8082:8082"   # Camera stream 2
      - "8083:8083"   # Camera stream 3
    volumes:
      - ./motioneye/config:/etc/motioneye
      - ./motioneye/media:/var/lib/motioneye
    environment:
      - TZ=America/New_York
```

### Configuration

Access the web UI at `http://your-server:7999`. The default login is `admin` with a blank password — change this immediately.

To add an RTSP camera, edit `./motioneye/config/camera-1.conf`:

```ini
[cameras]
camera_1_name = Front Door
camera_1_proto = network
camera_1_url = rtsp://admin:password@192.168.1.100:554/stream
camera_1_resolution = 1920x1080
camera_1_framerate = 15

[motion_detection]
motion_detection = on
threshold = 1500
minimum_motion_frames = 3
noise_level = 32
smart_mask_speed = 0

[storage]
storage_device = local
storage_path = /var/lib/motioneye
automatic_storage_cleanup = on
maximum_storage_days = 30
```

Motion detection settings that matter most:

- **Threshold** — number of pixels that must change to trigger. Lower = more sensitive.
- **Noise Level** — ignores small changes (light flickering, sensor noise). Higher = fewer false alarms.
- **Minimum Motion Frames** — requires motion to persist across N frames. Prevents single-frame glitches.
- **Smart Mask Speed** — adapts the motion mask for lighting changes (dawn/dusk transitions).

### Resource Usage

MotionEye is exceptionally lightweight:

| Hardware | Cameras | CPU Usage | RAM Usage |
|----------|---------|-----------|-----------|
| Pi Zero 2 W | 1 (720p) | 30-50% | 80 MB |
| Pi 4 | 3 (1080p) | 20-40% | 150 MB |
| x86 mini PC | 8 (1080p) | 15-25% | 200 MB |

## Feature Comparison

| Feature | Frigate | ZoneMinder | MotionEye |
|---------|---------|------------|-----------|
| **Setup complexity** | Moderate | High | Low |
| **Hardware requirements** | Medium | High | Very Low |
| **Camera support** | RTSP/ONVIF | Virtually any | RTSP/ONVIF/USB |
| **Motion detection** | Object-based | Zone-based | Pixel-based |
| **Hardware acceleration** | Yes (QuickSync, NVDEC) | Limited | No |
| **Home Assistant integration** | Native (add-on) | Via API | Via API |
| **MQTT support** | Built-in | Via plugin | Via webhook |
| **Web UI quality** | Modern, fast | Functional, dated | Simple, clean |
| **Multi-user support** | Limited | Full RBAC | Basic (admin/user) |
| **PTZ control** | No | Yes | Limited |
| **Recording retention** | Configurable per camera | Configurable per monitor | Configurable |
| **Event notifications** | Snapshots + MQTT | Email, webhook | Email, webhook |
| **Storage efficiency** | High (smart recording) | Medium | Low |
| **Scalability** | 16+ cameras | 32+ cameras | 4-8 cameras |
| **Active development** | Very active | Active | Moderate |

## Choosing the Right Platform

**Choose Frigate if:** You want a modern, efficient NVR with object-based detection and excellent Home Assistant integration. It is the best choice for most home users who have at least an Intel NUC or Raspberry Pi 4.

**Choose ZoneMinder if:** You need enterprise-grade features — PTZ control, user permissions, advanced event filtering, and support for virtually any camera type including analog capture cards. It requires more resources but delivers the most comprehensive feature set.

**Choose MotionEye if:** You have limited hardware (Raspberry Pi Zero, old laptop) or need a simple setup for a small number of cameras. It sacrifices advanced features for ease of use and minimal resource consumption.

## Storage Planning

Regardless of which platform you choose, storage is the primary cost driver. Here is a practical calculator for planning:

```
Storage per day (GB) = cameras × bitrate_mbps × 3600 × 24 / 8000

Examples at H.264 encoding:
- 1080p @ 2 Mbps:  2 × 3600 × 24 / 8000 = ~21.6 GB/day per camera
- 1080p @ 4 Mbps:  4 × 3600 × 24 / 8000 = ~43.2 GB/day per camera
- 720p @ 1 Mbps:   1 × 3600 × 24 / 8000 = ~10.8 GB/day per camera
- 4K @ 8 Mbps:     8 × 3600 × 24 / 8000 = ~86.4 GB/day per camera

For 4 cameras at 1080p (2 Mbps) recording 14 days:
4 × 21.6 × 14 = ~1,210 GB (use a 2 TB drive)
```

Using H.265 encoding reduces these numbers by roughly 40-50%. All three platforms support H.265 passthrough recording.

## Network Camera Setup Tips

**Camera placement:** Position cameras to cover entry points, driveways, and high-value areas. Avoid pointing directly at light sources (streetlights, the sun) which cause exposure issues.

**Network segmentation:** Put cameras on a separate VLAN. Most IP cameras have known security vulnerabilities. Isolating them prevents lateral movement if a camera is compromised:

```bash
# Create a camera VLAN on a Linux router
ip link add link eth0 name vlan10 type vlan id 10
ip addr add 192.168.10.1/24 dev vlan10
ip link set vlan10 up

# Block camera VLAN from accessing the internet but allow NVR access
iptables -A FORWARD -i vlan10 -o eth0 -j DROP
iptables -A FORWARD -i vlan10 -o vlan10 -d 192.168.10.100 -j ACCEPT
iptables -A FORWARD -i vlan10 -o vlan10 -m state --state ESTABLISHED,RELATED -j ACCEPT
```

**Secure your RTSP streams:** Always set a strong RTSP password. Never expose camera ports to the internet. If remote access is needed, use a WireGuard VPN to connect to your home network first.

**POE vs WiFi:** Use Power-over-Ethernet (POE) cameras when possible. WiFi cameras are easier to install but suffer from signal degradation, bandwidth contention, and reliability issues. A POE switch costs $50-100 for 4-8 ports and provides both power and data over a single cable.

## Backing Up Your Surveillance System

A surveillance system is only useful if it survives hardware failures:

```bash
#!/bin/bash
# Backup Frigate config and recent events to a remote server

FRIGATE_CONFIG="/opt/frigate/config"
FRIGATE_MEDIA="/opt/frigate/media"
BACKUP_DEST="/backup/frigate-$(date +%Y%m%d)"

mkdir -p "$BACKUP_DEST"

# Backup configuration
rsync -av "$FRIGATE_CONFIG/" "$BACKUP_DEST/config/"

# Backup recent clips (last 7 days)
find "$FRIGATE_MEDIA/clips" -mtime -7 -exec cp --parents {} "$BACKUP_DEST/clips/" \;

# Compress and sync to remote
tar czf "$BACKUP_DEST.tar.gz" "$BACKUP_DEST"
rsync -av "$BACKUP_DEST.tar.gz" backup-server:/backups/surveillance/

# Clean up local backup after successful sync
rm -rf "$BACKUP_DEST" "$BACKUP_DEST.tar.gz"
```

Set this up as a daily cron job to ensure your configuration and recent footage are always backed up off the primary storage device.

## Conclusion

Self-hosted video surveillance has matured to the point where it rivals commercial systems in features while surpassing them in privacy, cost, and flexibility. Frigate leads the pack for modern home setups with its efficient architecture and smart detection pipeline. ZoneMinder remains the most feature-complete option for demanding deployments. MotionEye excels at lightweight, simple setups on minimal hardware.

The best system is the one you actually deploy. Start with a single camera, get comfortable with your chosen platform, and expand from there. Your footage, your rules.
