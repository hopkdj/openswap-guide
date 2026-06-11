---
title: "Self-Hosted Virtual TV Channels: ErsatzTV vs Tunarr vs dizqueTV Compared 2026"
date: "2026-06-12"
tags: ["media-server", "iptv", "live-tv", "plex", "jellyfin", "streaming", "home-server", "docker"]
draft: false
---

## Why Create Your Own Virtual TV Channels?

If you have a large media library on Plex or Jellyfin, you have probably experienced decision fatigue — scrolling endlessly through hundreds of titles, unable to pick something to watch. If you are still building your media library setup, check our [Jellyfin vs Plex vs Emby comparison](../jellyfin-vs-plex-vs-emby/) to choose the right foundation. Virtual TV channel software solves this by transforming your on-demand library into scheduled, linear "live TV" channels. Each piece of software creates the illusion of traditional broadcast television: scheduled programming blocks, channel flipping, and even retro-style commercials if you want them.

These tools act as IPTV servers backed by your existing media library. They generate M3U playlists and XMLTV guide data that any IPTV client can consume — from Kodi to VLC to dedicated IPTV apps on your smart TV. Unlike real IPTV services, there is no external content source: everything streams from your own hard drives.

## Comparison Table

| Feature | ErsatzTV | Tunarr | dizqueTV |
|---------|----------|--------|----------|
| **Stars** | 2,823 | 2,351 | 1,759 |
| **Language** | C# (.NET) | TypeScript | JavaScript |
| **Media Backends** | Plex, Jellyfin, Emby, Local | Plex, Jellyfin | Plex |
| **FFmpeg Transcoding** | Yes (hardware + software) | Yes (hardware + software) | Yes (software only) |
| **Watermark/Logo Overlay** | Yes | Yes | Yes |
| **Flex/Scheduling** | Advanced (time slots, padding) | Advanced (time slots, padding) | Basic (fill-based) |
| **Multi-Channel** | Yes | Yes | Yes |
| **Web UI** | Modern, responsive | Modern, polished | Functional, retro |
| **API** | REST + Swagger | REST | REST |
| **Docker Support** | Official image | Official image | Community image |
| **Active Development** | Yes (2026) | Yes (2026) | Maintenance mode |

## ErsatzTV: The Feature-Rich Powerhouse

ErsatzTV is the most actively developed option with the largest community. Written in C# and running on .NET, it offers the most comprehensive feature set. Its scheduling system lets you define complex rules: create a channel that plays Star Trek episodes Monday through Friday from 8 PM to midnight, fills Saturday with sci-fi movies, and uses Sundays for recently added content. You can add watermarks, channel logos, and even interleave custom "commercial" videos between programs.

ErsatzTV supports hardware transcoding via VAAPI, QSV, and NVENC, making it practical for streaming to devices that cannot handle direct playback. The web UI is modern and responsive, with real-time preview of what is playing on each channel.

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  ersatztv:
    image: ersatztv/ersatztv:latest
    container_name: ersatztv
    ports:
      - "8409:8409"
    volumes:
      - ./ersatztv/config:/root/.local/share/ersatztv
      - /path/to/media:/media:ro
    environment:
      - TZ=America/New_York
    restart: unless-stopped
```

## Tunarr: The Modern Fork with a Fresh UI

Tunarr started as a fork of dizqueTV and has since diverged significantly. Built with TypeScript and React, it features a polished, modern web interface that is notably more intuitive than either ErsatzTV or dizqueTV. The visual programming guide editor lets you drag and drop programs into time slots, making schedule creation feel more like using a DVR than configuring a server.

Tunarr inherits dizqueTV's Plex integration and adds Jellyfin support. Its FFmpeg transcoding pipeline supports hardware acceleration out of the box. One standout feature is the "channel preview" that lets you see exactly what a channel looks like before making it live — thumbnails, guide data, and all.

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  tunarr:
    image: chrisbenincasa/tunarr:latest
    container_name: tunarr
    ports:
      - "8000:8000"
    volumes:
      - ./tunarr/config:/config
      - ./tunarr/data:/data
      - /path/to/media:/media:ro
    environment:
      - TZ=America/New_York
    restart: unless-stopped
```

## dizqueTV: The Original That Started It All

dizqueTV pioneered the concept of turning Plex libraries into live TV channels. While it has entered maintenance mode (the original developer moved on to create Tunarr), it remains a solid, battle-tested option with a large existing user base. Its architecture is JavaScript-based (Node.js), and it integrates exclusively with Plex — no Jellyfin or Emby support.

The interface is functional but visibly older than its successors. Schedule creation is fill-based rather than slot-based: you define what content fills a channel and dizqueTV plays it sequentially, looping when it reaches the end. This is simpler to set up but less flexible for creating a "real TV schedule" feel.

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  dizquetv:
    image: vexorian/dizquetv:latest
    container_name: dizquetv
    ports:
      - "8000:8000"
    volumes:
      - ./dizquetv/config:/home/node/app/.dizquetv
    environment:
      - TZ=America/New_York
    restart: unless-stopped
```

## Choosing the Right Virtual TV Server

Your choice depends on what media backend you use and how much control you want over scheduling. ErsatzTV offers the broadest backend support and most flexible scheduling — ideal if you use Jellyfin or Emby, or want fine-grained control over programming. Tunarr provides the best user experience and is the natural upgrade path for former dizqueTV users, especially with its drag-and-drop visual schedule editor. dizqueTV remains a viable option if you only use Plex and prefer a simpler, fill-based channel model that "just works" without much configuration.

Plex users have the luxury of choice: all three tools support Plex natively. Jellyfin and Emby users should choose ErsatzTV or Tunarr. If hardware transcoding matters (streaming to older smart TVs or mobile devices on slow connections), both ErsatzTV and Tunarr offer GPU-accelerated transcoding. For dedicated video transcoding pipelines, see our [Tdarr vs Unmanic vs HandBrake comparison](../tdarr-vs-unmanic-vs-handbrake-self-hosted-video-transcoding-guide-2026/).

## Performance and Hardware Considerations

Virtual TV software places unusual demands on your server. Unlike Plex or Jellyfin, which transcode on demand when a user presses play, virtual TV channels maintain continuous FFmpeg processes for each active channel. A server running three 24/7 channels with hardware transcoding enabled will typically consume 10-20 percent CPU on a modern Intel processor with Quick Sync, with memory usage around 2-4 GB for FFmpeg buffers plus the application itself.

For software-only transcoding, budget roughly one CPU core per 1080p stream. A six-core CPU can comfortably handle four to five simultaneous channels at 1080p with software encoding. If you plan to create themed channels for different household members — a kids channel, a movie channel, a documentary channel — and expect them to run concurrently, hardware transcoding becomes essential. Intel Quick Sync (available on most consumer Intel CPUs with integrated graphics) handles four to six simultaneous 1080p transcodes with minimal CPU impact.

Storage throughput matters less than you might expect. Since virtual TV channels read media files sequentially (like a playlist), random I/O is minimal. Any modern SSD or even a 7200 RPM hard drive can handle multiple concurrent streams. Network bandwidth is usually the bottleneck for remote streaming — budget 8-15 Mbps per 1080p stream, or up to 50 Mbps for 4K content.

For those already running a self-hosted media infrastructure, see our [DLNA and UPnP media server comparison](../2026-05-02-minidlna-vs-gerbera-vs-rygel-self-hosted-dlna-upnp-media-servers-guide/) for complementary streaming protocols.


## FAQ

### Do I need a Plex Pass or Jellyfin Premium to use these tools?

No. Virtual TV channel software interacts with Plex and Jellyfin through their standard APIs, which are available to all users. You do need a running Plex or Jellyfin server with media already scanned into its library — the virtual TV software reads the library metadata and streams the files directly, without going through Plex's transcoding pipeline.

### Can I watch these virtual channels on my actual TV?

Yes. Each tool generates standard M3U playlist URLs and XMLTV electronic program guide (EPG) data. You can import these into any IPTV client: Kodi (with IPTV Simple Client add-on), VLC, TiviMate, Jellyfin's Live TV feature, Plex's Live TV & DVR, or even Apple TV apps like Channels. The experience is indistinguishable from traditional cable TV — you flip through channels and see what is playing.

### How much CPU power do I need for transcoding?

If your playback devices support direct play of your media formats (H.264, AAC audio), transcoding is minimal and a Raspberry Pi 4 can handle multiple streams. If you need real-time transcoding (H.265 to H.264 conversion, for example), budget for a modern CPU with Quick Sync or a low-end GPU. Each transcoded stream typically uses 10-30% of a modern CPU core.

### Is it legal to create my own TV channels from my media?

Yes, as long as you own the media files or have the right to use them. These tools stream content from your personal library over your local network — there is no external distribution, no public broadcasting, and no copyright violation. It is functionally equivalent to playing files from your hard drive through any media player.

### Can I add real commercials or bumpers between shows?

All three tools support interleaving custom video files as "commercials" or "fillers" between scheduled programs. You can download public domain vintage commercials, create channel bumpers, or even add pre-roll intros. ErsatzTV and Tunarr offer the most control over filler placement, including the ability to schedule specific filler content at specific times.

### What happens if my Plex/Jellyfin server goes down?

The virtual TV channels will stop playing — these tools do not cache or buffer content independently. They stream media files on demand through FFmpeg by reading the source files directly from your storage. If the media server is down or files are inaccessible, channels will show an error or go offline. Consider running your media server and virtual TV software on the same machine to minimize failure points.


---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)**


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Virtual TV Channels: ErsatzTV vs Tunarr vs dizqueTV Compared 2026",
  "description": "Comprehensive comparison of ErsatzTV, Tunarr, and dizqueTV for creating self-hosted live TV channels from your Plex or Jellyfin media library. Includes Docker Compose setups and scheduling tips.",
  "datePublished": "2026-06-12",
  "dateModified": "2026-06-12",
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