---
title: "Self-Hosted Terminal Music Players: cmus vs ncmpcpp vs musikcube Compared"
date: "2026-06-17"
tags: ["music", "terminal", "linux-tools", "cli", "mpd", "audio"]
draft: false
---

For self-hosting enthusiasts who manage music libraries on Linux servers, a terminal-based music player is the perfect companion. Whether you're SSH'd into a home server that hosts your FLAC collection, or setting up a dedicated music streaming box, terminal players offer keyboard-driven control, low resource usage, and gapless playback — without needing a desktop environment.

In this guide, we compare three leading open-source terminal music players: **cmus**, **ncmpcpp**, and **musikcube**. Each takes a different architectural approach to music playback.

## Quick Comparison Table

| Feature | cmus | ncmpcpp | musikcube |
|---------|------|---------|-----------|
| **Stars** | 6,154 | 2,440 | 4,784 |
| **Language** | C | C++ | C++ |
| **Architecture** | Standalone player | MPD client | Standalone + server |
| **Backend** | Built-in (libmad, vorbis, flac) | MPD (requires separate daemon) | Built-in (FFmpeg) |
| **Library Format** | CUE/PLS/M3U | MPD database | SQLite |
| **Gapless Playback** | Yes | Yes (via MPD) | Yes |
| **Last.fm Scrobbling** | Yes | Yes (via mpdscribble) | Yes |
| **Visualizer** | Yes (built-in) | Yes (ncmpcpp visualizer) | Yes (built-in) |
| **Server Mode** | No | No (MPD is the server) | Yes (musikcube server) |
| **Memory Usage** | ~15MB | ~20MB (+MPD ~40MB) | ~25MB (standalone) |
| **Best For** | All-in-one simplicity | MPD power users | Multi-room streaming |

## Why Use a Terminal Music Player?

**Resource efficiency on headless servers**: A terminal music player uses 15-60MB of RAM compared to 500MB+ for GUI players like Rhythmbox or Clementine. When running on a Raspberry Pi media server or a low-spec VPS, every megabyte counts.

**Remote control over SSH**: Manage your music library from anywhere via SSH. Queue tracks, adjust volume, browse albums — all without a graphical session. Pair with `tmux` or `screen` to keep the player running after you disconnect.

**Gapless playback and bit-perfect audio**: Unlike web-based players that may add latency or resampling, terminal players can output directly to ALSA or PulseAudio for bit-perfect playback. Essential for classical music, live albums, and audiophile-grade listening.

**Integration with self-hosted music servers**: These players complement self-hosted music streaming servers like Navidrome, Airsonic, or Funkwhale by providing a local, low-latency playback interface while the server handles remote streaming. For web-based music streaming comparisons, see our [music server guide](../navidrome-vs-funkwhale-vs-airsonic-self-hosted-music-guide/).

## Deep Dive: Each Music Player

### cmus — The Standalone Swiss Army Knife

cmus (C* Music Player) is a self-contained, lightweight music player written in C. It handles everything from decoding audio files to managing the library to gapless playback — no external daemons required. Its interface uses vi-like keybindings, with views for library browsing (artist/album tree), playlist queue, file browser, and playback settings.

```bash
# Install cmus
sudo apt install cmus           # Debian/Ubuntu
sudo pacman -S cmus             # Arch
brew install cmus               # macOS

# Add music directory
cmus
# Press '5' to switch to file browser
# Navigate to your music folder and press 'a' to add
```

cmus supports virtually every audio format through libmad (MP3), libvorbis (OGG), libFLAC, FFmpeg, and Opus. Its library view shows your collection organized by artist and album, and you can queue tracks with a single keypress.

```bash
# cmus configuration (~/.config/cmus/rc)
set output_plugin=alsa
set dsp.alsa.device=hw:0,0    # Direct hardware output
set softvol=true
set softvol_state=80            # 80% volume
set status_display_program=cmus-status-display
```

**Pros**: Zero-external-dependency playback, supports all audio formats, vi keybindings, built-in spectrum visualizer.
**Cons**: Single-instance only, no server mode, no multi-room sync.

### ncmpcpp — The MPD Power User's Dream

ncmpcpp (NCurses Music Player Client Plus Plus) is a feature-rich client for the **Music Player Daemon (MPD)**. This split architecture means MPD handles audio playback as a background daemon, while ncmpcpp provides the user interface. The separation lets you restart the UI without interrupting playback, and multiple clients can connect to the same MPD instance.

```bash
# Install MPD and ncmpcpp
sudo apt install mpd ncmpcpp    # Debian/Ubuntu
sudo pacman -S mpd ncmpcpp      # Arch

# Configure MPD (~/.config/mpd/mpd.conf)
cat > ~/.config/mpd/mpd.conf << 'EOF'
music_directory    "~/music"
playlist_directory "~/.config/mpd/playlists"
db_file            "~/.config/mpd/database"
pid_file           "~/.config/mpd/pid"
state_file         "~/.config/mpd/state"
audio_output {
    type    "alsa"
    name    "ALSA output"
    device  "hw:0,0"
}
EOF

# Start MPD and ncmpcpp
mpd
ncmpcpp
```

ncmpcpp's standout features include a **tag editor** for fixing metadata, a **visualizer** with frequency spectrum and waveform views, a **lyrics fetcher**, and smart playlist generation. Its clock display shows album art (via kitty protocol or external viewers) and lyrics synchronized with playback.

```bash
# ncmpcpp config (~/.ncmpcpp/config)
mpd_music_dir = "~/music"
visualizer_type = "spectrum"
visualizer_look = "▋▋"
song_list_format = "{%a - }{%t}|{$8%f$9}%{$LF%5{   $8%l$9}"
```

**Pros**: MPD ecosystem (headless playback, multi-client), excellent visualizer, tag editor, lyrics support.
**Cons**: Requires MPD setup, higher total resource usage, more complex configuration.

### musikcube — The Multi-Room Streaming Contender

musikcube is a unique player that combines a terminal interface with an optional **streaming server**. This means you can use musikcube as a standalone player on your desktop, or run it as a server that streams your music library to other devices — including Android, iOS, and other musikcube instances on your network.

```bash
# Install musikcube
# Download from https://github.com/clangen/musikcube/releases
wget https://github.com/clangen/musikcube/releases/download/3.0.4/musikcube_3.0.4_linux_x86_64.deb
sudo dpkg -i musikcube_3.0.4_linux_x86_64.deb

# Run as standalone player
musikcube

# Run as streaming server
musikcube --server

# Connect client to server
musikcube --server-address=192.168.1.100
```

musikcube's built-in server makes it ideal for multi-room audio setups. Run the server on your main music library machine, and connect from lightweight clients on Raspberry Pis in different rooms. The SQLite-based library supports metadata indexing, playlists, and Last.fm scrobbling.

**Pros**: Built-in streaming server, cross-platform clients, SQLite library, multi-room support.
**Cons**: Larger binary, newer project with smaller community, terminal-only on Linux (no web UI).

## Setting Up a Headless Music Server

Here's how to set up MPD with ncmpcpp as a headless music server on a Raspberry Pi or VPS:

```bash
# Install dependencies
sudo apt install mpd ncmpcpp mpc -y

# Configure MPD for headless operation
sudo nano /etc/mpd.conf
# Set:
#   bind_to_address "0.0.0.0"    # Accept remote connections
#   music_directory "/mnt/music"  # Your music drive

# Set up autostart
sudo systemctl enable --now mpd

# Control remotely
ncmpcpp --host your-server-ip

# Alternatively, control via simple commands:
mpc add /             # Add entire library
mpc play              # Start playback
mpc volume +5         # Increase volume
mpc next              # Skip track
```

For a full music streaming stack, combine MPD+ncmpcpp for local playback with a web-based server like Navidrome or Airsonic for remote listening. Our [music streaming comparison](../navidrome-vs-funkwhale-vs-airsonic-self-hosted-music-guide/) covers the server-side options in detail.

## Choosing the Right Terminal Music Player

**Choose cmus if** you want a simple, self-contained player with zero external dependencies. It's the best choice for casual listeners and those who want a single binary that "just works."

**Choose ncmpcpp if** you're building a headless music server and want the full MPD ecosystem. The client-server split gives you flexibility: run MPD 24/7 on a server, control it from any device, and never interrupt playback.

**Choose musikcube if** you want multi-room audio streaming without the complexity of MPD. Its built-in server and cross-platform clients make it ideal for whole-home audio setups.

## FAQ

### Can terminal music players output to Bluetooth or network speakers?

Yes, but indirectly. MPD (used with ncmpcpp) supports HTTP streaming outputs and PulseAudio sinks, which can route audio to Bluetooth speakers via `pulseaudio-module-bluetooth`. cmus outputs through ALSA or PulseAudio, so any sink configured in PulseAudio works. musikcube's server streams its audio output to connected clients over the network. For dedicated multi-room setups, consider pairing with Snapcast for synchronized playback.

### How do I manage a large music library (100,000+ tracks) on a headless server?

MPD with ncmpcpp handles large libraries efficiently. MPD's database is optimized for fast queries, and ncmpcpp's search is near-instant even with 100K+ tracks. cmus scans directories on startup, which becomes slow with very large collections. musikcube's SQLite backend scales well but indexing 100K tracks may take several minutes initially. For very large libraries, ensure your music is on an SSD and consider splitting collections across multiple MPD instances by genre.

### Can I stream music FROM these players to my phone or other devices?

ncmpcpp itself is a client, but MPD supports HTTP streaming output — configure an `audio_output` of type `httpd` in `mpd.conf`, and any device on your network can stream the MPD output. musikcube has a built-in server mode specifically designed for remote streaming. cmus has no built-in streaming; for remote listening, pair it with services like Navidrome or Airsonic for the server side while keeping cmus for local playback.

### What's the difference between a terminal music player and a self-hosted music streaming server?

Terminal players (cmus, ncmpcpp, musikcube) handle **local audio playback** on the machine where they run — they decode audio files and output to the sound card. Self-hosted streaming servers (Navidrome, Airsonic, Funkwhale, Jellyfin) serve music over HTTP to **remote clients** (web browsers, mobile apps, Subsonic-compatible players). Many setups use both: MPD+ncmpcpp for high-quality local playback, and Navidrome for remote streaming to phones and laptops.

### How do I display album art in a terminal?

ncmpcpp can display album art in terminals that support the kitty graphics protocol, or by launching an external image viewer like `feh` or `sxiv`. cmus shows artist/album/track text information only. musikcube can display embedded album art in terminals with kitty/sixel support. For a full album art experience via terminal, use `chafa` (covered in our [terminal image viewer guide](../2026-06-17-terminal-image-viewers-chafa-timg-viu/)) alongside your music player.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Terminal Music Players: cmus vs ncmpcpp vs musikcube Compared",
  "description": "Compare three open-source terminal music players (cmus, ncmpcpp, musikcube) for headless Linux servers. Includes MPD setup guide, multi-room streaming with musikcube, and remote control via SSH.",
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
  }
}
</script>
