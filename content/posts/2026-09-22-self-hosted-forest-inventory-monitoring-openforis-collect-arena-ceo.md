---
title: "Self-Hosted Forest Inventory Platforms in 2026: Open Foris Collect vs Arena vs Collect Earth Online"
date: "2026-09-22"
tags: ["self-hosted", "geospatial", "forestry", "open-source", "data-collection"]
draft: false
cover: "/img/screenshots/openforis-ceo-widget.jpg"
---

National forest inventories still run on spreadsheets emailed between field crews, and that is exactly where the data dies. A single country-level inventory can involve **thousands of plots, dozens of field teams, and five-year reporting cycles** — and if your data pipeline is a shared drive, you are one laptop failure away from re-measuring a forest. The Open Foris stack is the most complete open-source answer to this problem that exists, and unlike most scientific software, all of it runs on infrastructure you control.

**TL;DR — the quick verdict:** If you need structured field surveys with offline mobile data entry and a real relational database, start with **Open Foris Collect**. If your teams enter and review data in a browser and you want per-survey roles and validation chains, run **Arena**. If your inventory is based on visual interpretation of satellite imagery rather than ground plots, **Collect Earth Online** is the only serious open-source option. And if you are processing drone or airborne **LiDAR** point clouds into per-tree metrics, add **3DFin** to the same host — it is the piece most inventories are missing.

## The Open Foris Stack at a Glance

All four projects are maintained under the Open Foris umbrella (originally FAO, now with an active community), and all four are permissively licensed. Star counts and last-commit dates below were pulled from GitHub at the time of writing.

| Project | Role in the pipeline | Language / stack | License | Stars | Last commit |
|---|---|---|---|---|---|
| **Open Foris Collect** | Survey designer + data entry + server database | Java (server + desktop designer) | MIT | 59 | 2026-09-14 |
| **Open Foris Arena** | Browser-based survey platform with roles and validation | Java + JavaScript (Docker) | MIT | 27 | 2026-09-21 |
| **Collect Earth Online** | Crowd-sourced satellite image interpretation | Clojure + PostGIS + Vue | MIT | 58 | 2026-09-21 |
| **3DFin** | LiDAR point-cloud forest metrics (per-tree) | Python (PyVista / Qt) | GPL-3.0 | 99 | 2025-12-05 |
| **Collect Earth (desktop)** | Offline visual interpretation via Earth engine clients | Java | MIT | 51 | 2026-09-10 |
| **USDA FIESTA** | Statistical estimation for sample-based inventories | R / Java | Public domain (US Gov) | 36 | 2026-05-22 |

A note on the stars: low star counts are normal in this domain. These are institutional tools used by ministries and research institutes, not developer-trending projects. Judge them by commit activity and documentation, both of which are healthy — three of the four repositories above were updated **within the last two weeks**.

## Which Tool for Which Job

| Your situation | Use this | Why |
|---|---|---|
| Field crews with tablets, no reliable connectivity | **Collect** (+ Collect Mobile) | Offline-first data entry, then sync into a central PostgreSQL database |
| Multiple organisations submitting to one national dataset | **Arena** | Per-survey user roles, validation rules, and a web UI — no desktop installation |
| Assess land cover or degradation from satellite imagery | **Collect Earth Online** | Gridded plot sampling over imagery collections, with quality control |
| Drone LiDAR flights, need DBH / height / volume per tree | **3DFin** | Automated point-cloud normalisation and individual tree segmentation |
| Statistical estimates and error bounds from plot samples | **FIESTA** | Purpose-built estimators for sample-based designs |
| Zero servers allowed, offline analysis only | **Collect Earth (desktop)** | Runs locally against Earth engine clients, no backend |

## Open Foris Collect: The Engine of Field Inventories

Collect is the workhorse. You design a survey in the desktop designer, publish it to a server, and field teams enter records against it — either through the bundled server web interface or through Collect Mobile, which caches the survey definition and queues submissions until a connection returns.

Collect ships a **Dockerfile in the repository root**, so containerising it is a first-class path rather than an afterthought. The official requirements, straight from the project documentation, are:

- Java Development Kit 11 or 17
- PostgreSQL database server
- The Collect distribution (installer for Windows, or the server war/jar for Linux)

The data model is deliberately boring, which is its strength: surveys, records, and attributes are stored in PostgreSQL, so your inventory lives in tables you can query with SQL and back up with `pg_dump` — no proprietary export step between the field and the analysis.

```bash
# Typical server-side deployment pattern for Collect
# 1. Provision PostgreSQL (12+ recommended) and create a role/database
sudo -u postgres createuser -P collect
sudo -u postgres createdb -O collect collect_db

# 2. Deploy the Collect server archive extracted from the official release
unzip collect-server-*.zip -d /opt/openforis/
# 3. Point the server at the database in the configuration and start it
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
/opt/openforis/collect-server/bin/startup.sh

# 4. Back up the whole inventory as plain SQL, nightly
pg_dump -Fc -U collect collect_db > /srv/backups/collect_$(date +%F).dump
```

The backup line is the one that matters. Everything else in Collect is replaceable software; that dump is the actual national asset.

![Collect Earth Online widget configuration screen](/img/screenshots/openforis-ceo-widget.jpg "Collect Earth Online widget configuration — real product interface from the official repository")

## Open Foris Arena: The Web-First Survey Platform

Arena is what you deploy when your data collectors are not trained field crews but **regional offices, consultants, and partner organisations** who need browser access with role separation. It is a Java application with a JavaScript frontend, and it ships its own Docker Compose stack under `infra/web/`:

```yaml
# infra/web/docker-compose.yml (from the official repository)
version: '3.4'

services:
  web:
    ports:
      - "9990:9090"
    build:
      context: ../..
      dockerfile: ./infra/web/Dockerfile
      target: arena-web
    image: of-arena-web
```

The practical reading of that snippet: Arena builds its own image, exposes a single HTTP port (**9090 inside the container, mapped to 9990 by default**), and expects you to put a reverse proxy with TLS in front of it for anything beyond a lab. In production you should override the port mapping, wire it to an external PostgreSQL instance rather than a container-local one, and back up the database on the same schedule as your survey submissions.

Arena's design assumption is that **data validation is collaborative**: a survey can define validation rules that run on entry, records move through review states, and a coordinator can lock a dataset once it has been checked. If your process currently ends with "the district office emails us a spreadsheet", Arena removes that entire failure mode.

![Open Foris Arena login interface](/img/screenshots/openforis-arena-login.jpg "Open Foris Arena web interface — authentic product asset from the official repository")

## Collect Earth Online: Satellite-First Inventories

Collect Earth Online (CEO) flips the model: instead of measuring trees, **human interpreters classify plots against satellite imagery collections**. You define a sampling grid, assign plots to interpreters, and they label each plot with land-use or degradation classes. It is the standard approach for land-cover assessment and REDD+ style monitoring where field access is impossible.

CEO is a Clojure application backed by PostgreSQL with **PostGIS** for the spatial work. The official installation requirements are explicit and worth reading before you start, because they are stricter than most self-hosted apps:

- **Java Development Kit** version 11 or 17
- **Clojure CLI tools** 1.10 or newer
- **PostgreSQL 12** with **PostGIS 3.2+**
- **Node 18**, Python 3, and p7zip for asset tooling

Configuration is a single file. On startup CEO reads `config.edn` from the repository root; copy the provided `config.example.edn` and fill in every value wrapped in angle brackets, including your imagery API keys and database credentials.

```bash
# Prepare the repository configuration
cp config.example.edn config.edn
$EDITOR config.edn     # replace every <placeholder> value

# Create the database, roles, extensions and default data
clojure -M:build-db build-all --dev-data

# If you are restoring a production dump instead of dev data
clojure -M:build-db restore -f /srv/ceo/database/ceo-db-2026-09-01.dump
```

The `--dev-data` flag is a trap for the unwary: it seeds three users, an imagery source, and a project so you can click around immediately — **do not deploy a production instance that still has dev data in it**. Run `build-all` without the flag, then load your real imagery collections and create your own first administrator.

## 3DFin: LiDAR In, Inventory Numbers Out

The piece that most self-hosted inventories leave out is the point-cloud stage. Collect and Arena give you records; they do not tell you what is inside a drone LiDAR scan. **3DFin** (99 stars, GPL-3.0, Python) handles the physical measurement end: it normalises point clouds to a common ground reference, segments individual trees, and derives per-tree metrics such as height, crown dimensions, and diameter at breast height from the segmented stems.

The workflow that actually works in practice is a two-stage pipeline on one host:

1. **3DFin** processes the point clouds and emits per-plot, per-tree metrics as tabular output.
2. Those tables are imported into the **Collect** database (or joined in PostgreSQL against your plot register) so that field measurements and LiDAR-derived measurements live in the same schema and can be compared directly.

Because 3DFin is a Python application, it belongs on a workstation or a batch node with a decent CPU allocation rather than inside your survey server container. Keep it out of the request path, schedule it, and write its output into the same PostgreSQL instance your survey platform reads from.

## Pitfalls When Self-Hosting a Forest Inventory Stack

- **PostGIS is not optional.** CEO's spatial functions will fail at runtime, not at install time, if PostGIS is missing or older than 3.2. Install it before the first `build-all`.
- **Do not containerise PostgreSQL for a national dataset unless you also back it up properly.** A named Docker volume is not a backup. Dump to a separate filesystem and copy it off-host.
- **Survey definitions are the real deliverable.** Before you upgrade Collect or Arena, export every survey definition. Application upgrades are reversible; a lost survey template means re-training field crews.
- **Version drift between designer and server.** Design a survey with a newer designer than the server build and the publish step fails in confusing ways. Pin both to the same release.
- **Plan for offline conflicts.** Collect Mobile queues records locally. If two crews edit the same record, decide *in your protocol* who wins before you discover it during the reporting deadline.
- **Imagery costs are invisible until they are not.** CEO is free; the satellite or aerial imagery you load into it usually is not. Budget for imagery access separately.

## Why Self-Host Your Forest Inventory Data?

Forest inventory data is politically sensitive. Plot locations can reveal commercially valuable timber, and in many jurisdictions land-cover classifications feed directly into carbon accounting and enforcement. Putting that dataset on a third-party platform means accepting their terms of service, their jurisdiction, and their uptime.

Self-hosting keeps three things under your control. First, **sovereignty**: the plots, the classifications, and the audit trail stay on infrastructure your institution can defend in a review. Second, **cost predictability**: a modest PostgreSQL server plus object storage for point clouds and imagery costs a fixed amount per month, instead of per-seat or per-hectare licences that scale with the size of the forest you happen to be surveying. Third, **integration**: when your survey database is PostgreSQL, your national statistics office can query it, your GIS team can join it to vector layers, and your remote sensing team can publish results without a data-export negotiation.

That integration point is why the Open Foris stack rewards a little planning. If you are building the surrounding spatial infrastructure yourself, our guide to [self-hosted geospatial mapping servers](../self-hosted-geospatial-mapping-servers-nominatim-tileserver-gl-geoserver-guide-2026/) covers the vector and raster tile layer, and the [GIS web map viewers comparison](../2026-06-09-self-hosted-gis-web-map-viewers-qgis-server-mapbender-lizmap/) explains how to publish inventory layers to non-technical staff. If your inventory includes LiDAR, the [point cloud web servers guide](../2026-06-09-self-hosted-point-cloud-web-servers-potree-entwine-pdal-guide/) shows how to serve those clouds to a browser instead of shipping multigigabyte files around.

## FAQ

**Can I run the whole Open Foris stack on one server?**
Yes, for small to medium inventories. PostgreSQL, Arena, and Collect will coexist comfortably on a 8 GB / 4 vCPU host for a few dozen concurrent users. Put Collect Earth Online on the same box only if your interpreters are few; its imagery tooling and background workers are the hungriest part of the stack.

**Does Collect work offline in the field?**
That is its primary design goal. The mobile client caches the survey definition and stores submissions locally, then synchronises once connectivity returns. Plan your identifiers so that records created offline cannot collide when they sync.

**How much does the imagery for Collect Earth Online cost?**
The software is free under the MIT licence. Imagery is a separate cost that depends on the provider and resolution you need; open collections are available for coarse-resolution land-cover work, while high-resolution interpretation for small plots is where the budget goes.

**Can I migrate from spreadsheets to Collect mid-project?**
Yes, and it is worth the disruption. Model your existing spreadsheet columns as survey attributes, import historical rows as records, and keep the original files as an audit reference. Doing this mid-project is far cheaper than discovering year five of a cycle that your data cannot be analysed consistently.

**Is Arena a replacement for Collect, or a companion?**
A companion. Collect excels at authoring complex survey instruments and offline field entry; Arena excels at web-based entry and review by distributed teams. Many programmes use Collect for design and field capture, then load the data into Arena for validation and sharing.

**What backup frequency should I use for a multi-year inventory?**
Nightly database dumps with 30-day retention, plus weekly off-site copies held for the full reporting cycle. Survey definitions and imagery metadata should be versioned in git alongside the deployment configuration, so a rebuild is reproducible from source control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Forest Inventory Platforms in 2026: Open Foris Collect vs Arena vs Collect Earth Online",
  "description": "A practical comparison of self-hosted forest inventory and land monitoring platforms: Open Foris Collect, Arena, Collect Earth Online and 3DFin, with real deployment commands and pitfalls.",
  "datePublished": "2026-09-22",
  "dateModified": "2026-09-22",
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
