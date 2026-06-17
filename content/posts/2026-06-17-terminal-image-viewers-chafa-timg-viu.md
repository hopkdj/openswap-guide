---
title: "Self-Hosted Terminal Image Viewers: chafa vs timg vs viu"
date: "2026-06-17"
tags: ["terminal-tools", "image-viewer", "cli", "ascii-art", "devops", "media"]
draft: false
---

## Introduction

When you're SSH'd into a remote server and need to quickly inspect an image — whether it's a generated chart, a screenshot for debugging, or a camera capture — opening a GUI file manager or copying the file to your local machine is tedious. Terminal image viewers solve this by rendering images directly in your terminal using Unicode block characters, sixel graphics, or iTerm/Kitty protocols.

In this guide, we compare three leading terminal image viewers: **chafa** (versatile and feature-rich), **timg** (supports both images and video), and **viu** (fast and simple with wide protocol support).

## Comparison Table

| Feature | chafa | timg | viu |
|---------|-------|------|-----|
| Stars | 4,925 | 2,667 | 3,217 |
| Language | C | C++ | Rust |
| Image Formats | PNG, JPEG, GIF, SVG, WebP, BMP, TIFF | PNG, JPEG, GIF, WebP, BMP, HEIC, AVIF | PNG, JPEG, GIF, WebP, BMP, ICO |
| Video Support | No | Yes (GIF, WebP anim, video files) | No |
| Rendering Methods | Sixel, iTerm2, Kitty, Unicode, ANSI | Sixel, iTerm2, Kitty, Unicode, truecolor | Sixel, iTerm2, Kitty, Unicode |
| Dithering | Multiple algorithms | Floyd-Steinberg, Atkinson | Basic |
| Resize/Fit | Auto-fit, custom size | Auto-fit, custom size, crop | Auto-fit, custom size |
| EXIF Rotation | Yes | Yes | No |
| SVG Rendering | Yes (librsvg) | No | No |
| Install Size | ~2 MB | ~3 MB | ~2 MB |
| Best For | Maximum format support | Video & animation support | Speed and simplicity |

## chafa: The Format Powerhouse

chafa supports the widest range of image formats of the three tools, including SVG rendering via librsvg. It offers multiple dithering algorithms for optimal output on different terminal types and can produce everything from simple ASCII art to full-color sixel graphics.

### Installation

```bash
# Debian/Ubuntu
sudo apt install chafa

# macOS
brew install chafa

# From source
git clone https://github.com/hpjansson/chafa.git
cd chafa && ./autogen.sh && make && sudo make install
```

### Basic Usage

```bash
# Display an image in the terminal
chafa image.png

# Fit to terminal width
chafa --mode fit image.jpg

# Specify output size
chafa --size 80x40 photo.jpg

# Use specific rendering method
chafa --symbols block screenshot.png     # Unicode blocks
chafa --symbols ascii logo.png           # ASCII only
chafa --format sixel chart.png           # Sixel graphics

# Batch process a directory
chafa photos/*.jpg
```

chafa excels at handling unusual formats:

```bash
# Render SVG directly in terminal
chafa diagram.svg --size 100x60

# WebP with animation frames
chafa animated.webp --duration 5s

# TIFF with EXIF data
chafa scanned.tiff --exif-rotate
```

### Server Integration

chafa can be integrated into monitoring pipelines to preview generated charts before serving them:

```bash
#!/bin/bash
# Generate and preview CPU chart
gnuplot -e "set terminal png; set output '/tmp/cpu.png'; plot '/tmp/cpu.dat' with lines"
chafa /tmp/cpu.png --size 80x25
```

## timg: Images and Video in the Terminal

timg is unique among terminal image viewers for its video playback support. It can render animated GIFs, WebP animations, and actual video files (MP4, WebM, AVI) directly in the terminal. For static images, it supports modern formats including HEIC and AVIF.

### Installation

```bash
# Debian/Ubuntu
sudo apt install timg

# macOS
brew install timg

# From source
git clone https://github.com/hzeller/timg.git
cd timg && mkdir build && cd build && cmake .. && make && sudo make install
```

### Basic Usage

```bash
# Display a static image
timg image.jpg

# Play an animated GIF
timg animation.gif

# Play a video file
timg video.mp4

# Fit to terminal with specific grid
timg -g80x40 photo.png

# Crop mode
timg -C image.jpg

# Rotate image
timg -r90 photo.jpg
```

### Video Playback in Terminal

timg's standout feature is real-time video rendering:

```bash
# Loop a video
timg -l video.mp4

# Control frame rate
timg -F10 video.mp4  # 10 fps

# Play with subtitles (if embedded)
timg tutorial.mp4
```

This is particularly useful for headless servers where you need to quickly verify video file integrity or preview surveillance footage:

```bash
# Check security camera recording
ssh server "timg -g120x40 /var/recordings/cam1_2026-06-17_09.mp4"
```

### Docker Deployment

```yaml
version: '3'
services:
  timg:
    image: ubuntu:22.04
    entrypoint: ["timg"]
    volumes:
      - ./media:/media
    environment:
      - TERM=xterm-256color
```

## viu: Fast and Simple

viu (written in Rust) prioritizes speed and simplicity. It detects your terminal's capabilities and automatically selects the best rendering protocol — Kitty graphics protocol for Kitty users, iTerm2 inline images for iTerm2 users, and Unicode block characters as a universal fallback.

### Installation

```bash
# Via cargo
cargo install viu

# Via Homebrew
brew install viu

# Via package manager
sudo apt install viu  # On newer Ubuntu/Debian
```

### Basic Usage

```bash
# Display an image
viu image.jpg

# Custom dimensions
viu -w 80 -h 40 photo.png

# Disable true color (force 256-color mode)
viu -n image.jpg

# Use specific protocol
viu -t kitty image.png    # Force Kitty protocol
viu -t iterm image.jpg    # Force iTerm2 protocol
viu -t block image.gif    # Force Unicode blocks
```

viu's auto-detection means it works out of the box in most environments:

```bash
# Works on any terminal - viu auto-detects best method
ssh server viu /path/to/chart.png

# Quick preview in tmux
viu screenshot.png -h 20
```

## Deployment Architecture

For teams that need shared image preview capabilities, deploy these tools in a jump host container:

```yaml
version: '3.8'
services:
  image-preview:
    image: ubuntu:22.04
    command: ["tail", "-f", "/dev/null"]
    volumes:
      - shared_media:/media
      - ./scripts:/scripts
    environment:
      - TERM=xterm-256color

volumes:
  shared_media:
```

Install all three tools:

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \
    chafa timg cargo \
    && cargo install viu
```

## Why Self-Host Your Terminal Image Viewers?

For server administrators, being able to preview images without leaving the SSH session saves time and reduces context switching. When debugging a web application that generates charts, having `chafa` available means you can verify the output instantly without downloading files to your local machine.

Security-conscious teams benefit from keeping image data on the server. Rather than transferring potentially sensitive screenshots or generated charts to a local machine for viewing, terminal image viewers process and display everything server-side. For teams using our [terminal recording tools](../self-hosted-terminal-recording-asciinema-vhs-ttyrec-guide-2026/), these viewers let you preview recorded sessions directly on the server.

Terminal image viewers also shine in automated pipelines. When a CI job generates screenshots of visual regression tests, a quick `chafa screenshot.png` in the build log provides immediate visual feedback. For remote pair programming sessions using our [terminal multiplexer guide](../self-hosted-terminal-multiplexer-tmux-screen-abduco-remote-dev-guide-2026/), these tools let both participants view images without leaving the shared session.

For managing photo collections, our [self-hosted photo management comparison](../2026-04-28-librephotos-vs-immich-vs-photoprism-self-hosted-photo-management-guide-2026/) covers full-featured web-based photo platforms. Terminal image viewers complement these by providing quick, ad-hoc image inspection without the overhead of a web UI.

## Choosing the Right Terminal Image Viewer

**chafa** is the best general-purpose choice. Its broad format support (including SVG and TIFF), multiple dithering algorithms, and robust EXIF handling make it suitable for virtually any image preview task. If you install only one, install chafa.

**timg** is the choice when you need video or animation support. Its ability to play MP4 files and animated GIFs directly in the terminal is unique among CLI image viewers. Security camera previews, tutorial video checks, and animated WebP verification are all timg strengths.

**viu** is ideal when simplicity and speed are priorities. Its automatic protocol detection means it works on any terminal without configuration, and its Rust implementation makes it the fastest of the three for simple image display tasks.

For most teams, installing both chafa (format coverage) and timg (video support) provides complete terminal-based media preview capabilities.

## FAQ

### Do I need a special terminal for these tools to work?

For best results, use iTerm2 (macOS), Kitty, WezTerm, or any modern terminal that supports 256-color or truecolor output. The tools fall back to Unicode block characters on basic terminals like xterm or the Linux console. Sixel graphics require terminal support (xterm with `-ti 340` flag or mlterm).

### Can I use these over SSH?

Yes — all three tools work over SSH without any special configuration, as long as your terminal supports color/Unicode. For sixel graphics over SSH, you may need to enable sixel passthrough: `ssh -t server "TERM=xterm-256color bash"`.

### How large can the images be?

chafa handles images up to available memory. timg is optimized for terminal-sized output (typically 80-200 columns) and handles very large images by downscaling. viu has similar memory usage to chafa. For multi-megapixel photos, all three tools will downsample to fit your terminal dimensions.

### Can these tools convert images between formats?

No — these are viewers, not converters. Use ImageMagick or FFmpeg for format conversion. However, chafa can export its rendered output as an image: `chafa input.png --format sixel > output.sixel`.

### Do any of these support remote URLs?

chafa can read from HTTP URLs directly: `chafa https://example.com/image.jpg`. timg and viu require the file to be local — use `curl` to download first: `curl -sO https://example.com/image.jpg && viu image.jpg`.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Terminal Image Viewers: chafa vs timg vs viu",
  "description": "Comprehensive comparison of three terminal-based image viewers — chafa, timg, and viu. Covers image and video display in the terminal, Docker deployment, SSH workflows, and server monitoring integration.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
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
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://hopkdj.github.io/openswap-guide/posts/2026-06-17-terminal-image-viewers/"
  }
}
</script>
