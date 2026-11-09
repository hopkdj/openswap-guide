---
title: "PiGallery2 vs Photofield vs HomeGallery in 2026: Which Self-Hosted Photo Gallery Actually Scales?"
date: "2026-11-09"
tags: ["self-hosted", "photo-gallery", "docker", "pigallery2", "photofield"]
draft: false
cover: "/img/screenshots/photofield-gallery.jpg"
---

You have 60,000 photos on a NAS, a Raspberry Pi doing nothing, and a growing suspicion that paying a cloud provider to index your own memories is a bad deal. So you look at the self-hosted gallery options, and every guide points you at the same heavyweight platforms: Immich, PhotoPrism, LibrePhotos. They are excellent — and they are also PostgreSQL clusters, background job queues, and multi-gigabyte machine-learning containers that will happily eat 8 GB of RAM before showing you a single thumbnail.

There is a quieter category of gallery software that never got the same attention: **directory-first, read-only galleries** that treat your existing folder tree as the database and generate thumbnails on demand. No import step. No migration that takes three days. Point it at `/mnt/photos`, open a browser, done. **PiGallery2, Photofield and HomeGallery** are the three strongest projects in that category — and they make very different trade-offs.

## TL;DR — the 30-second verdict

**Pick Photofield** if your library already has a sane folder structure and you want the fastest possible browse experience from a single Go binary. **Pick PiGallery2** if you need a polished, feature-complete gallery with sharing, face grouping, and a proven Raspberry Pi track record. **Pick HomeGallery** if you want tagging, map view, and duplicate detection over 100k+ files and you do not mind running a separate API container.

None of the three needs a database server. All three are MIT-licensed. All three will run comfortably in 512 MB–2 GB of RAM depending on library size. If you want the cloud-replacement feature set — mobile auto-upload, shared albums, multi-user libraries — stop reading and go set up Immich instead.

## Side-by-side comparison

| Dimension | PiGallery2 | Photofield | HomeGallery |
|---|---|---|---|
| GitHub stars | **2,315** | 617 | 1,213 |
| Primary language | TypeScript (Node) | Go + Svelte | JavaScript (Node) |
| Latest activity | Nov 2026 | Oct 2026 | Nov 2026 |
| License | MIT | MIT | MIT |
| Database | Embedded SQLite | Embedded cache DB | Embedded + API server |
| Import step required | No (index only) | No (index only) | No (index only) |
| Face grouping | Yes (optional) | Basic | Yes |
| Video thumbnails | Yes | Yes (needs ffmpeg) | Yes |
| Map / GPS view | Yes | Limited | Yes |
| Duplicate detection | No | No | Yes |
| Mobile-friendly UI | Yes | Yes | Yes |
| Typical RAM (50k photos) | ~1 GB | ~150–300 MB | ~700 MB + API |
| Docker image | `bpatrik/pigallery2` | `ghcr.io/smilyorg/photofield` | `xemle/home-gallery` |

The star counts are not a proxy for quality here. Photofield has one-tenth of PiGallery2's stars and is still the fastest of the three at cold-start indexing, because it is compiled Go reading directory entries instead of Node walking a filesystem through a JavaScript runtime.

## Decision matrix: match the tool to your situation

| Your situation | Recommended tool | Why |
|---|---|---|
| 500 GB of photos on a Synology, 4 GB RAM | **Photofield** | Single binary, read-only mount, no background jobs |
| Raspberry Pi 4 with a USB SSD and 30k photos | **PiGallery2** | Documented Pi support, thumbnail worker is tunable |
| 150k files, several photographers, need tags | **HomeGallery** | Tagging + duplicate detection + map clustering |
| You want to share one album via a link | **PiGallery2** | Built-in sharing and per-user permissions |
| You refuse to run Node.js in production | **Photofield** | Go binary, zero runtime dependencies |
| You want face grouping without a GPU | **HomeGallery** | CPU backend via WASM works on ARM |
| You already run Immich and want a lightweight viewer for an archive drive | **Photofield** | Mount the archive read-only next to Immich |

## PiGallery2 — the polished all-rounder

PiGallery2 is the oldest and most complete project in this group. It is an Angular frontend over a Node backend, and it deliberately avoids importing your library: it builds a SQLite index next to the config, generates thumbnails into its own directory, and never touches the originals. The official compose file runs nginx in front and mounts your photos read-only:

```yaml
services:
  nginx:
    image: nginx:latest
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt/:/etc/letsencrypt/
    ports:
      - 80:80
      - 443:443
    restart: always

  pigallery2:
    image: bpatrik/pigallery2:latest
    deploy:
      resources:
        limits:
          memory: 3G
    environment:
      - NODE_ENV=production
    volumes:
      - "./pigallery2/config:/app/data/config"
      - "db-data:/app/data/db"
      - "./pigallery2/images:/app/data/images:ro"
      - "./pigallery2/tmp:/app/data/tmp"
    expose:
      - "80"
    restart: always

volumes:
  db-data:
```

Three things in that file matter more than they look. **`NODE_ENV=production`** is not cosmetic — in debug mode PiGallery2 logs every indexed file and can triple indexing time on a large library. **The `:ro` suffix** on the images mount is your insurance policy: a gallery should never be able to delete a photo. And the **3 GB memory limit** in the official file is there because the thumbnail worker is a Node process; on a 1 GB box, drop it to 768 MB and expect garbage collection pauses during the first index.

First-run sequence that actually works:

```bash
mkdir -p pigallery2/{config,db,images,tmp}
docker compose up -d
docker compose logs -f pigallery2 | grep -i "indexing"
```

Then open the admin UI, add `/app/data/images` as a source folder, and let the indexer finish before touching anything else. On a Pi 4 with a USB SSD, 30,000 photos take roughly 25–40 minutes for the first pass; subsequent starts are near-instant because the SQLite index persists.

PiGallery2's killer feature is not the grid view — it is **sharing**. You can create a public link for a single folder with an expiry date, which is the one thing Photofield and HomeGallery do not do well. Face grouping exists and runs on CPU, but it is optional and slow; on a Pi, enable it for one folder at a time rather than the whole library.

## Photofield — the speed demon

Photofield is what happens when someone decides the filesystem is the database and means it. The backend is Go, the frontend is Svelte, and the entire index is a cache that can be deleted at any time without data loss. The README is explicit about the design goal: **indexing runs at the speed of the filesystem, 1,000–10,000 files per second on a fast SSD**.

Deployment is a single command:

```bash
mkdir -p data photos
docker run -d --name photofield \
  -p 8080:8080 \
  -v "$PWD/data:/app/data" \
  -v "$PWD/photos:/app/photos:ro" \
  --restart unless-stopped \
  ghcr.io/smilyorg/photofield
```

That is the whole install. There is no database container, no migration, no admin account. If you want multiple collections, or you need to tune caching, drop a `configuration.yaml` into the `data` directory:

```yaml
collections:
  - name: Photos
    path: /app/photos
    # optional: hide folders from the UI
    exclude:
      - "**/@eaDir/**"
      - "**/.stfolder/**"
  - name: Archive
    path: /app/archive

# serve on a different port than the default :8080
address: ":8080"
```

Two environment variables are worth memorising: `PHOTOFIELD_ADDRESS` (listen address, default `:8080`) and `PHOTOFIELD_DATA_DIR` (where the cache and `configuration.yaml` live). For video metadata, install `exiftool` inside the container image or on the host — without it, video dates come from filesystem timestamps, which are wrong after any rsync. Installing `libjpeg-turbo` gives a measurable speedup on JPEG-heavy libraries because Photofield can use `djpeg` for decoding.

Where Photofield falls short: **no sharing, no multi-user permissions, no face grouping beyond basic detection, and the UI is deliberately minimal**. It is a viewer, not a platform. If your family needs accounts and album links, this is the wrong tool — but for a personal archive on a low-power box, nothing else comes close on responsiveness.

![Photofield face and people grouping view](/img/screenshots/photofield-faces.jpg "Photofield people view generated from folder metadata")

## HomeGallery — the analyst's gallery

HomeGallery sits between the two. It is a Node.js application with a separate API server container that handles thumbnail generation, video probing, and the heavier analysis work (faces, objects, geo clustering). The official compose file is production-ready and already separates the concerns:

```yaml
services:
  api:
    image: xemle/home-gallery-api-server
    environment:
      - BACKEND=wasm
  gallery:
    image: xemle/home-gallery
    environment:
      - GALLERY_API_SERVER=http://api:3000
      - GALLERY_API_SERVER_CONCURRENT=1
      - GALLERY_API_SERVER_TIMEOUT=60
      - GALLERY_OPEN_BROWSER=false
      - GALLERY_WATCH_POLL_INTERVAL=300
    volumes:
      - ./data:/data
      - ${HOME}/Pictures:/data/Pictures
    ports:
      - "3000:3000"
    user: "${CURRENT_USER}"
```

The comments in that file are the actual deployment guide. **`BACKEND=wasm`** is the right choice on ARM and on any machine without a GPU; `node` is faster on x86 but pulls a heavier native dependency chain. **`GALLERY_API_SERVER_CONCURRENT=1`** exists specifically for Raspberry Pi-class devices — leave it at 1 on a Pi, raise it to 5 on a proper server. **`GALLERY_WATCH_POLL_INTERVAL=300`** switches file watching to polling, which is what you want on NFS or SMB mounts where inotify does not fire.

HomeGallery's differentiator is the query layer. Every photo gets extracted metadata — camera, lens, GPS, tags, detected faces, perceptual hashes — and the UI exposes it as faceted search. That is how you answer questions like "show me every photo taken with the 35mm lens in Lisbon before 2019" without a single SQL query. Duplicate detection is built in and genuinely useful when your library has been through three backup tools.

The cost is operational complexity: two containers, a data directory that grows with the cache, and a first index that is slower than Photofield by an order of magnitude. Budget 1–2 hours for 50,000 files on a modern x86 box.

## Pitfalls that cost people weekends

**Never mount photos read-write unless you must.** All three tools support read-only mounts, and all three have had bugs that wrote sidecar files. `:ro` costs nothing and prevents the worst outcome.

**HEIC and RAW need extra binaries.** PiGallery2 handles common RAW via embedded previews; HomeGallery needs `libraw`/`dcraw` in the image for full RAW decoding; Photofield relies on `exiftool` for metadata and will show placeholder thumbnails for formats it cannot decode. If your library is iPhone-heavy, convert to JPEG on import or accept slower thumbnails.

**Symlinks are not free.** A folder of symlinks pointing outside the mounted volume will index as broken entries. Mount the real path.

**Thumbnail cache size is the hidden cost.** PiGallery2 and HomeGallery store derived images at roughly 3–6% of the original library size. A 500 GB library means 15–30 GB of cache. Put `/app/data` on a real disk, not a tmpfs.

**Do not index the same folder from two tools at once.** Three thumbnail workers reading the same spinning disk will make all three feel broken.

## Why bother self-hosting a gallery at all?

Because a photo library is the one dataset where the cloud's economics are backwards. Storage is cheap; **egress is not**, and every "share this album" link is an egress event. A €5/month VPS plus a 2 TB USB SSD holds a lifetime of photos, and the only recurring cost is electricity. You also get something no subscription offers: the originals in a plain folder tree that any future tool can read.

If you are still deciding whether to run a full management platform, our [Immich vs PhotoPrism vs LibrePhotos comparison](../2026-04-28-librephotos-vs-immich-vs-photoprism-self-hosted-photo-management-guide-2026/) covers the heavyweight tier in detail, and the [PhotoView walkthrough](../2026-04-29-photoview-self-hosted-photo-gallery-guide-2026/) covers a fourth lightweight option with a very different UI philosophy. For the deployment layer underneath all of them, see our [Docker Compose management UI comparison](../2026-05-14-portainer-compose-vs-dockge-vs-coolify-docker-compose-management-ui/).

## FAQ

**Do I need to import my photos into PiGallery2, Photofield or HomeGallery?**
No. All three index in place. PiGallery2 and HomeGallery build a sidecar index; Photofield builds a disposable cache. Your folder structure remains the source of truth, which is why you can switch tools later without a migration.

**Which one is fastest on a Raspberry Pi 4?**
Photofield, by a wide margin, because it is a compiled Go binary that streams directory entries. PiGallery2 is the most feature-complete option that still runs well on a Pi 4 with 4 GB RAM, provided you keep the thumbnail worker concurrency low and avoid enabling face grouping on the whole library at once.

**Can these tools handle video files?**
Yes, all three generate video thumbnails, but all three need `ffmpeg` (and for reliable metadata, `exiftool`) present in the container or on the host. Without those binaries you get first-frame placeholders and filesystem-based dates.

**Do any of them support multiple users with separate libraries?**
PiGallery2 has the most mature user and sharing model, including per-folder access and expiring public links. HomeGallery supports multiple users but is designed around a shared library. Photofield is effectively single-user and has no permission layer.

**What happens if I delete the index or cache directory?**
Nothing is lost. The cache is derived data; the next start re-indexes from the filesystem. This is the main reason directory-first galleries are safer than import-based platforms — there is no authoritative database to corrupt.

**Which one should I choose for a 200,000-photo archive?**
HomeGallery, because duplicate detection, faceted search and map clustering are the features that make a library that large navigable. Pair it with a fast NVMe for the data directory; the API server will be your bottleneck long before the CPU is.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PiGallery2 vs Photofield vs HomeGallery in 2026: Which Self-Hosted Photo Gallery Actually Scales?",
  "description": "A hands-on comparison of three directory-first self-hosted photo galleries: PiGallery2, Photofield and HomeGallery, with real Docker Compose configs, memory requirements and scaling advice.",
  "datePublished": "2026-11-09",
  "dateModified": "2026-11-09",
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
