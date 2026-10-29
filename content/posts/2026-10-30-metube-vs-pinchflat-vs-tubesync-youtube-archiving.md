---
title: "MeTube vs Pinchflat vs TubeSync in 2026: Which Self-Hosted YouTube Archiver Actually Keeps Your Library?"
date: "2026-10-30"
tags: ["self-hosted", "media-server", "youtube", "yt-dlp", "homelab"]
draft: false
cover: "/img/screenshots/metube-ui.jpg"
---

A video you bookmarked in 2023 has a coin-flip chance of still being there in 2026. Channels get deleted, videos go private, region blocks appear overnight, and the "watch later" list is not an archive — it is a bookmark to someone else's filesystem. If a tutorial, a conference talk, or a music set matters to you, the only durable copy is the one on your own disk.

Three open-source projects dominate that job in 2026: **MeTube** (15,134 stars), **Pinchflat** (5,432 stars), and **TubeSync** (2,808 stars). All three wrap `yt-dlp`, all three are AGPL-3.0, and all three claim to solve the same problem. They are not interchangeable. One is a downloader with a queue, one is a PVR for channels, and one is a media-library sync engine — and picking the wrong shape costs you either automation or control.

## TL;DR

- **MeTube** — best when you want a fast web UI to paste links and grab files. Queue-based, minimal, no opinion about your library. **Pick it if you download ad hoc.**
- **Pinchflat** — best automation: per-channel "media profiles" with naming, format, and retention rules that produce a Plex/Jellyfin-ready library. **Pick it if you archive channels, not videos.**
- **TubeSync** — best for "set it and forget it" channel mirroring with metadata and a proper database, at the cost of a heavier install. **Pick it if you want a full mirror with history.**
- **One warning up front:** Pinchflat's last commit is 2025-12-16 — nearly a year stale as of this writing. `yt-dlp` moves weekly. That matters more than any feature table.

## Side-by-Side: What Each Project Actually Is

| | **MeTube** | **Pinchflat** | **TubeSync** |
|---|---|---|---|
| Primary shape | Web UI + queue for `yt-dlp` | Channel/playlist PVR with media profiles | Channel/playlist sync engine |
| Stars | 15,134 | 5,432 | 2,808 |
| License | AGPL-3.0 | AGPL-3.0 | AGPL-3.0 |
| Last commit | 2026-10-27 | 2025-12-16 | 2026-10-29 |
| Container | `ghcr.io/alexta69/metube` | `ghcr.io/kieraneglin/pinchflat` | `ghcr.io/meeb/tubesync` |
| Web port | 8081 | 8945 | 4848 |
| Subscriptions / auto-download | Basic (subscriptions added) | Yes — the core feature | Yes — the core feature |
| Naming control | `OUTPUT_TEMPLATE*` environment variables | Per-profile naming presets | Per-source format/naming |
| Metadata sidecars | No | Yes (NFO-ish, library friendly) | Yes (NFO + thumbnails) |
| Resource footprint | Tiny (single Python process) | Small (Elixir/Phoenix + SQLite) | Medium (Django + database + workers) |
| Best for | One-off downloads | Clean libraries with rules | Long-term mirrors with history |

## Decision Matrix: Pick in Ten Seconds

| If your goal is… | Use | Why |
|---|---|---|
| "Download this one video right now" | **MeTube** | Paste URL, click, done. No source config |
| "Mirror 40 channels into Jellyfin with clean names" | **Pinchflat** | Media profiles + naming presets beat manual templates |
| "Keep every video from 12 channels, forever, with metadata" | **TubeSync** | Built as a sync engine with a real database |
| "Run on a 1 GB VPS" | **MeTube** | Smallest footprint by a wide margin |
| "Archive a channel that posts 10 videos a day" | **TubeSync** | Worker model handles sustained queues better |
| "Never touch a config file again" | **MeTube** | Least configuration surface of the three |

## MeTube: The Downloader That Refuses to Be a Framework

MeTube is a thin, opinionated web front end for `yt-dlp`. There is no channel model, no library scanner, no metadata pipeline — you give it a URL, it queues a download, it writes a file. That is the entire product, and it is why it has three times the stars of its more ambitious competitors.

```yaml
services:
  metube:
    image: ghcr.io/alexta69/metube
    container_name: metube
    restart: unless-stopped
    ports:
      - "8081:8081"
    volumes:
      - /srv/media/youtube:/downloads
    environment:
      - TZ=Europe/Berlin
      - OUTPUT_TEMPLATE=%(uploader)s/%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s
```

The environment variables are where the actual power lives, and they are documented in the repo's README rather than buried in code:

| Variable | Default | What it changes |
|---|---|---|
| `DOWNLOAD_DIR` | `/downloads` | Final destination for completed files |
| `TEMP_DIR` | `/downloads` | Staging area; put it on SSD, not a RAM disk, or interrupted downloads cannot resume |
| `STATE_DIR` | `/downloads/.metube` | Queue, history, subscriptions, uploaded cookies |
| `OUTPUT_TEMPLATE` | `%(title)s.%(ext)s` | Filename pattern for single videos |
| `OUTPUT_TEMPLATE_PLAYLIST` | `%(playlist_title)s/%(title)s.%(ext)s` | Pattern for playlist items |
| `OUTPUT_TEMPLATE_CHANNEL` | `%(channel)s/%(title)s.%(ext)s` | Pattern for channel items |

That template syntax is `yt-dlp`'s, which means you get date formatting, uploader folders, and video IDs for free. It also means you inherit `yt-dlp`'s failure modes: when YouTube changes something, MeTube breaks until the underlying binary is updated. Because MeTube tracks `yt-dlp` closely (commits within days), this is usually a non-event — but pin the image tag if you need reproducibility, and rebuild on a schedule rather than running `latest` for a year.

Where MeTube is weak: it does not know what is already in your library. Duplicate detection is filename-based, so a re-upload with a changed title lands as a second file, and there is no "this channel has 900 videos, sync them" workflow that survives a restart gracefully.

## Pinchflat: Media Profiles Are the Killer Feature

Pinchflat is the only one of the three that models *what you want the output to look like*. A "media profile" bundles output format, quality ceiling, subtitle handling, sponsor-block removal, and naming presets — then you attach that profile to a source (channel or playlist). Ten channels, one profile, consistent library.

```yaml
services:
  pinchflat:
    image: ghcr.io/kieraneglin/pinchflat:latest
    container_name: pinchflat
    restart: unless-stopped
    ports:
      - "8945:8945"
    volumes:
      - /srv/pinchflat/config:/config
      - /srv/media/youtube:/downloads
    environment:
      - TZ=Europe/Berlin
```

Two paths matter: `/config` holds the SQLite database and per-source state, `/downloads` is your media library. Back up `/config` — it is the only record of what has been archived and what is still pending.

The practical difference shows up in failure recovery. If a download fails mid-queue, Pinchflat retries on its own schedule and keeps per-source history, so "did episode 412 already download?" is a database query rather than a guess. Retention rules are the other differentiator: you can tell it to keep only the last 20 videos per channel, which turns a bottomless archive into a bounded 400 GB library.

The catch is maintenance velocity. Last commit 2025-12-16 means the project has been quiet for roughly ten months. `yt-dlp` extraction logic changes constantly, so a stale wrapper is a liability: expect to rebuild the container against a newer `yt-dlp` yourself, or accept that some sources will start failing. Check its issue tracker before you commit a 2 TB archive to it.

## TubeSync: The Sync Engine

TubeSync is the oldest idea of the three: define sources, define a schedule, let a worker pool keep your local copy in sync with the remote channel. It is a Django application with a real database, an admin interface, and a task queue — heavier than MeTube by an order of magnitude, and the only one that behaves like infrastructure rather than an app.

```yaml
services:
  tubesync:
    image: ghcr.io/meeb/tubesync:latest
    container_name: tubesync
    restart: unless-stopped
    ports:
      - "4848:4848"
    volumes:
      - /srv/tubesync/config:/config
      - /srv/media/youtube:/downloads
    environment:
      - TZ=Europe/Berlin
      - TUBESYNC_HOSTS=tubesync.example.com
      - TUBESYNC_VIDEO_HEIGHT_CUTOFF=720
      - TUBESYNC_RESET_DOWNLOAD_DIR=true
```

`TUBESYNC_VIDEO_HEIGHT_CUTOFF` is the single most useful knob in the whole comparison: it refuses to download anything below a given vertical resolution, which silently saves terabytes when a channel re-uploads old 480p material. `TUBESYNC_HOSTS` must include your real hostname (Django's `ALLOWED_HOSTS`), or the UI will throw 400s behind a reverse proxy — the most common first-install failure.

TubeSync's worker model scales better than a single queue: sustained ingestion of ten videos a day across a dozen channels is unremarkable for it, whereas MeTube's queue is designed for human-paced requests. The price is operational surface — more memory, more moving parts, more log noise.

## The Things Nobody Tells You Before You Hit 1 TB

- **Storage math is brutal and predictable.** A 1080p video averages roughly 1.5–2.5 GB per hour; 720p is roughly a third of that. A channel posting three 20-minute videos a week is about 200 GB per year at 1080p. Decide your ceiling *before* you subscribe to forty channels.
- **Codec choice decides your CPU bill.** Downloading VP9/AV1 as-is costs no CPU but may force transcoding on weak clients (old TVs, Raspberry Pi). Downloading H.264 costs bandwidth but plays everywhere. Set a format ceiling per profile/source rather than per download.
- **Cookies expire, and then everything breaks.** Age-restricted or member-only content needs exported cookies. MeTube stores them in `STATE_DIR`; Pinchflat and TubeSync each have their own upload path. Rotate them before they expire, not after.
- **Rate limiting looks like a bug.** Hundreds of rapid requests from one IP get throttled. Stagger source syncs, keep concurrent downloads at two or three, and do not "retry aggressively" — that is how an IP gets soft-banned.
- **Do not put `/downloads` on a network share for active downloads.** Write locally, then move. Partial files over SMB/NFS produce silent corruption that only shows up during playback.
- **Verify restores, not backups.** Archiving without a tested restore path is a hobby, not an archive. Copy the library to a second disk and periodically play a random file end-to-end.

## Why Not Just Use the Official App's Offline Mode?

Because offline mode is a license, not a file. It expires with your subscription, it disappears when the platform removes the video, and it gives you no naming control, no metadata, and no library that survives a vendor decision. Self-hosting is not about piracy — it is about the same reason people run their own mail server or their own [podcast archive](../2026-04-22-podgrab-vs-podfetch-vs-podsync-self-hosted-podcast-tools-2026/): durability of access.

If your interest is watching YouTube without the recommendation feed, that is a different problem — our comparison of [TubeArchivist vs Invidious vs Piped](../tubearchivist-vs-invidious-vs-piped-self-hosted-youtube-tools-2026/) covers front ends rather than archivers. And if you are already running a media server, the [audiobook and ebook server comparison](../2026-04-19-audiobookshelf-vs-kavita-vs-calibre-web-self-hosted-ebook-audiobook-server-2026/) shows how the same naming-discipline problem is solved for a different media type.

## FAQ

**Which of the three should a beginner install first?**
MeTube. One container, one volume, a web form. You will know within ten minutes whether archiving is a habit you actually keep. Move to Pinchflat or TubeSync only when you find yourself wanting per-channel rules — that is the signal you have outgrown a downloader.

**Can I run MeTube and Pinchflat against the same library folder?**
Technically yes, but do not. Two tools writing to one directory will produce duplicate files and conflicting naming, and neither tracks the other's state. If you need both behaviours, give each its own staging folder and merge at the media-server layer.

**Is Pinchflat abandoned?**
Not announced as abandoned, but its last commit is 2025-12-16, which is a long silence for a tool whose core dependency changes weekly. It still works today; the risk is that YouTube-side changes eventually break extraction and the fix never lands. Treat it as "maintained until proven otherwise" and keep a tested fallback.

**How much RAM and disk do these need?**
MeTube idles under 150 MB and needs disk only for the media. Pinchflat is a Phoenix application with SQLite: a few hundred MB is comfortable. TubeSync is the heaviest — Django, database, and workers — so budget 1 GB of RAM and give it fast local storage for its database and temp files.

**Do these work for non-YouTube sites?**
All three ultimately rely on `yt-dlp`'s extractor list, so anything `yt-dlp` supports (Vimeo, SoundCloud, many public broadcasters) can usually be downloaded. Automation quality varies: channel/playlist models are tuned for YouTube, and metadata naming for other sites is best-effort. Test one source before scheduling twenty.

**Where do the files go if I use Jellyfin or Plex?**
Point the media server at `/downloads` and keep the archiver's output template library-friendly (`Uploader/YYYY-MM-DD - Title [id].ext`). Both media servers will parse that reliably. Avoid renaming files by hand afterwards — the archiver tracks state by path and will re-download what it cannot find.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MeTube vs Pinchflat vs TubeSync in 2026: Which Self-Hosted YouTube Archiver Actually Keeps Your Library?",
  "description": "MeTube, Pinchflat and TubeSync compared for self-hosted YouTube archiving in 2026: real Docker Compose configs, storage math, naming templates, metadata handling, and maintenance risk.",
  "datePublished": "2026-10-30",
  "dateModified": "2026-10-30",
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
