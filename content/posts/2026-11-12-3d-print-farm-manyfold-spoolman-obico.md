---
title: "Manyfold vs Spoolman vs Obico in 2026: The Self-Hosted Stack That Actually Runs a 3D Print Farm"
date: "2026-11-12"
tags: ["3d-printing", "self-hosted", "open-source", "docker", "homelab"]
draft: false
description: "Running more than one 3D printer means managing files, filament and failures. This is a hands-on comparison of Manyfold, Spoolman and Obico - the three self-hosted tools that cover those layers - with real compose configs and integration notes."
---

One printer is a hobby. Six printers is an inventory problem. The moment a farm crosses three machines, three failures appear that no slicer solves: **which version of the bracket model is the good one**, **how much PETG is actually left on the shelf**, and **which printer has been printing spaghetti since 2am**. OctoPrint, Mainsail and Fluidd give you the control layer, but they deliberately stop at the machine boundary.

Three self-hosted projects fill the layers above and around the control interface, and, importantly, they are not competitors — they occupy different slots in the same stack. Manyfold is the file library. Spoolman is the material ledger. Obico is the watchdog. This article compares them on deployment, APIs and integration reality, and shows where each one quietly fails.

## TL;DR

- **Your model files are scattered across folders, USB sticks and "final_v3_REAL.stl"** → **Manyfold** (2,244 stars, Ruby, AGPL-3.0). A web library that scans your existing folders, extracts metadata from the files themselves and gives every model a stable URL.
- **You keep buying filament you already own, or you cannot tell whether a spool has 300g or 30g left** → **Spoolman** (3,026 stars, Python, MIT). A spool ledger with a REST API that Moonraker, OctoPrint and Home Assistant can read and write.
- **You want to know a print failed before you waste 400g of filament overnight** → **Obico** (1,932 stars, AGPL-3.0). Print monitoring with webcam analysis, notifications and a mobile app, plus a plugin that hooks into OctoPrint or Klipper.
- **If you only install one thing:** Spoolman. It is the highest-value-per-minute install in the entire hobby, and its API is genuinely pleasant.

Deploy all three and you still have not built a "print farm manager" — nobody has open-sourced that layer properly yet. What you get is three well-scoped services plus your slicer and your printer control UI.

## How the three layers divide the work

| Capability | Manyfold | Spoolman | Obico |
|---|---|---|---|
| Primary job | Model library + metadata | Filament inventory | Print monitoring and failure alerts |
| GitHub stars | 2,244 | 3,026 | 1,932 |
| Language | Ruby (Rails) | Python (FastAPI) | Django + Vue |
| License | AGPL-3.0 | MIT | AGPL-3.0 |
| Database | PostgreSQL / MySQL / SQLite | SQLite / PostgreSQL / MariaDB / CockroachDB | SQLite or PostgreSQL, plus Redis |
| REST API | Yes, read/write | Yes, first-class, documented | Yes, plus websocket |
| Talks to printers | No | Indirectly, via Moonraker/OctoPrint plugins | Yes, via plugin on the printer host |
| Mobile app | No | No | Yes (iOS/Android) |
| Container image | `manyfold3d/manyfold` | `donkie/spoolman` | Built from source via compose |
| Last commit (checked) | 2026-11-12 | 2026-11-10 | 2026-11-10 |

## Decision matrix

| Your actual pain | Install | Why this one |
|---|---|---|
| "Where is the latest version of this model?" | Manyfold | Folder scanning plus per-file metadata extraction |
| "Do I have enough black PLA for a 14-hour print?" | Spoolman | Live remaining-weight tracking, consumed per print |
| "Did the print fail at hour 3?" | Obico | Webcam-based failure detection with push alerts |
| You run a print farm for customers and need per-job material cost | Spoolman | API exposes spool usage you can bill against |
| You sell printed parts and need a browsable catalogue | Manyfold | Public collections and shareable links |
| You leave prints unattended overnight | Obico | The only one of the three that watches the machine |

## Manyfold — the model library

Manyfold is the successor to VanDAM, rewritten as a Rails application with a proper data model: models, files, creators, collections, licences, and links out to Thingiverse, Printables and similar sources. It does not upload your files anywhere — it **scans directories you already have** and builds an index.

The official compose example is small enough to read in one screen:

```yaml
services:
  app:
    image: manyfold3d/manyfold:latest
    ports:
      - 3214:3214
    volumes:
      - /srv/models:/models
    environment:
      PUID: 1000
      PGID: 1000
      SECRET_KEY_BASE: a_nice_long_random_string
      REDIS_URL: redis://redis:6379/1
      DATABASE_ADAPTER: postgresql
      DATABASE_HOST: postgres
      DATABASE_PORT: 5432
      DATABASE_USER: manyfold
      DATABASE_PASSWORD: password
      DATABASE_NAME: manyfold
    depends_on:
      - postgres
      - redis
```

Two notes that save an evening. First, `SECRET_KEY_BASE` must be long and random — generate it with `openssl rand -hex 64` rather than typing something. Second, you can skip PostgreSQL entirely by pointing `DATABASE_URL` at SQLite (`sqlite3:/config/manyfold.sqlite3`); for a farm with a few thousand files that is perfectly adequate and removes two containers.

What makes Manyfold worth the install is metadata extraction: it reads embedded information from 3MF and STL files, groups related files into one model, and can pull in thumbnails. Nested folder structures are preserved, so a library organised as `clients/acme/bracket-v4/` stays browsable.

Where it fails: it is a *library*, not a job manager. There is no queue, no printer state, no slicing. It also does not deduplicate identical files across folders — if you keep the same model in three places, you will index it three times.

## Spoolman — the filament ledger

Spoolman exists because everyone lies to themselves about filament. The service keeps a spool inventory with net weight, remaining weight, material, colour, vendor, price per spool and spool weight, and then integrates with the printer host so that each print decrements the right spool automatically.

Running it is a single container:

```bash
docker run -d \
  --name spoolman \
  -p 7912:8000 \
  -v /srv/spoolman:/home/app/.local/share/spoolman \
  -e TZ=Europe/Berlin \
  --restart unless-stopped \
  donkie/spoolman:latest
```

The integration path matters more than the install. On a Klipper host, Moonraker's `[spoolman]` section points at the service:

```ini
[spoolman]
server: http://192.168.1.20:7912
sync_rate: 5
```

From that point, Moonraker reports filament usage back to Spoolman per print, and the remaining weight on the spool drops accordingly. OctoPrint users get the same behaviour through the Spoolman plugin. The REST API is plain and documented — `GET /api/v1/spool?material=PLA` returns JSON you can read from a dashboard, and `PUT /api/v1/spool/3/use` records consumption:

```bash
curl -X PUT http://192.168.1.20:7912/api/v1/spool/3/use \
  -H "Content-Type: application/json" \
  -d '{"use_weight": 42.5}'
```

Where it fails: Spoolman has **no concept of drying, storage location or purchase orders** beyond free-text fields, and there is no multi-user permission model. If three people print from the same spool, the numbers are only as good as the print host integration — a manually aborted print may or may not be recorded depending on where you abort it.

## Obico — the watchdog

Obico (formerly The Spaghetti Detective) is the only project here that watches the printer while you sleep. A plugin runs on the printer host, streams the webcam to the Obico server, and the server flags a print that has turned into a bird's nest, then notifies you by push, email, Telegram or Slack.

Unlike the other two, Obico's compose file **builds images from source** rather than pulling a prebuilt one, and it expects Redis:

```yaml
services:
  web:
    build:
      context: backend
      dockerfile: Dockerfile
    volumes:
      - ./backend:/app
    depends_on:
      - redis
    environment:
      DATABASE_URL: ${DATABASE_URL-sqlite:////app/db.sqlite3}
      REDIS_URL: ${REDIS_URL-redis://redis:6379}
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY-}
      SITE_USES_HTTPS: ${SITE_USES_HTTPS-False}
      ACCOUNT_ALLOW_SIGN_UP: ${ACCOUNT_ALLOW_SIGN_UP-False}
    ports:
      - "3334:3334"

  redis:
    image: redis:7
```

Set `ACCOUNT_ALLOW_SIGN_UP=False` and create users from the Django admin — an open registration endpoint on a monitoring server that holds webcam streams is not something you want exposed. Put it behind TLS (`SITE_USES_HTTPS=True`) and set `CSRF_TRUSTED_ORIGINS` to your real domain, or logins will fail silently behind a reverse proxy.

The value is in the plugin pairing: install the Obico plugin on OctoPrint or Klipper, pair it with a six-digit code, and the server takes over monitoring. It also does timelapse capture, which is the feature people end up using most.

Where it fails: the failure detection is only as good as the camera framing, and it is CPU-hungry on the server side during analysis. On a Raspberry Pi it will crawl; run the server on real hardware and keep the Pi for the printer.

## Integration order that avoids rework

1. **Install Spoolman first** and label every physical spool with its ID. This is a manual step and it is the one people skip — then the data is worthless for a month.
2. **Wire Moonraker or OctoPrint to Spoolman** and verify one print decrements the correct spool before you add more printers.
3. **Add Manyfold** and point it at the folders you already slice from. Do not reorganise first; let it index what exists, then clean up inside the UI.
4. **Add Obico last**, one printer at a time, and tune the detection sensitivity on a known-good print.

Reverse that order and you end up with alerts about failures you cannot cost, on models you cannot find.

If you have not settled the control layer yet, our [OctoPrint vs Mainsail vs Fluidd comparison](../2026-04-20-octoprint-vs-mainsail-vs-fluidd-self-hosted-3d-printer-server-guide/) covers the host software these three integrate with. For slicing choices, see the [2026 slicer comparison](../2026-10-13-3d-print-slicers-orcaslicer-prusaslicer-cura-guide/). And if your model library is bigger than a hobby — client work, shared assets, rights metadata — the [digital asset management review](../2026-05-03-self-hosted-digital-asset-management-resourcespace-pimcore-mayan-edms/) is the enterprise-grade alternative to Manyfold.

## Pitfalls that cost real filament

- **Back up Spoolman's database before every firmware upgrade.** Spool weights live in one SQLite file by default; a broken volume mount resets months of inventory data.
- **Manyfold's library path must be readable by the container UID.** A root-owned `/srv/models` with `PUID: 1000` yields an empty library and no error — check the scan logs.
- **Obico behind a reverse proxy needs both `SITE_USES_HTTPS` and `CSRF_TRUSTED_ORIGINS`.** Setting only one produces a login loop that looks like a password problem.
- **Do not point two Moonraker instances at the same spool simultaneously** unless you accept race conditions in remaining-weight accounting.
- **Model files are not backups.** Manyfold indexes your directory, it does not replicate it; keep the actual library on storage you back up separately.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Manyfold vs Spoolman vs Obico in 2026: The Self-Hosted Stack That Actually Runs a 3D Print Farm",
  "description": "Comparison of Manyfold, Spoolman and Obico as the file, material and monitoring layers of a self-hosted 3D print farm, with compose configs and integration steps.",
  "datePublished": "2026-11-12",
  "dateModified": "2026-11-12",
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

## FAQ

### Do I need all three tools to run a print farm?

No. They solve separate problems. Spoolman alone delivers the biggest operational gain for most people, because filament accounting is the thing that silently bleeds money. Add Manyfold when file sprawl becomes the bottleneck, and Obico when you start leaving prints unattended.

### Does Spoolman work with Klipper and OctoPrint?

Yes. Moonraker has a built-in `[spoolman]` configuration section that syncs filament usage, and OctoPrint has an official Spoolman plugin. Both report consumption per completed print and read remaining weight for the UI.

### Is Manyfold a replacement for OctoPrint or Mainsail?

No. Manyfold is a file library — it scans folders, extracts metadata and serves a browsable catalogue. It has no printer connection, no job queue and no slicing. OctoPrint, Mainsail and Fluidd remain the control layer.

### Can Obico run fully self-hosted without the hosted service?

Yes. The `obico-server` repository ships a complete compose stack you build and run yourself, and the printer plugin can be pointed at your own server during pairing. You give up the vendor's relay infrastructure, which is why the server needs a stable address and TLS in front of it.

### How much RAM does this stack need?

Spoolman is tiny, under 200MB. Manyfold with PostgreSQL and Redis is comfortable in 1GB. Obico is the heavyweight because of webcam analysis — plan 2-4GB and real CPU cores, and keep it off a Raspberry Pi.

### Can I track material cost per printed part?

Only by combining services: Spoolman exposes spool price and consumed weight through its API, so a small script can compute cost per job by reading `/api/v1/spool/{id}` before and after a print. Neither Manyfold nor Obico tracks money.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
