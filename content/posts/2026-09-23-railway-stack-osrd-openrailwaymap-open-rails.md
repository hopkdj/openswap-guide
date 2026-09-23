---
title: "OSRD vs OpenRailwayMap vs Open Rails in 2026: Self-Hosting a Railway Planning, Mapping and Simulation Stack"
date: "2026-09-23"
tags: ["railway", "self-hosted", "gis", "simulation", "openstreetmap"]
cover: "/img/screenshots/openrailwaymap.jpg"
draft: false
---

Railway engineering has one of the worst open-source toolchains of any infrastructure discipline. Signalling layouts live in proprietary CAD formats, capacity studies are done in vendor software that costs more per seat than a car, and the schedule data your national operator publishes is a PDF. The result is that a small but genuinely useful stack of open tools goes almost completely unnoticed outside a handful of national railway labs.

Three projects cover three different layers of the problem: **OSRD** designs and simulates infrastructure and timetables, **OpenRailwayMap** renders the world's railway infrastructure from OpenStreetMap data, and **Open Rails** simulates a train over real route content. This guide covers what each one actually is, how to stand it up, and where the sharp edges are.

## TL;DR: The Quick Verdict

- **You need to design, edit or analyse a railway network and its timetables:** self-host **OSRD**. It is the only project here that is a real web application with a Docker Compose stack, and it is a stage-2 project of the OpenRailAssociation — the same body that hosts the projects major European operators contribute to.
- **You want a railway map of your country, or a rendering pipeline for OSM rail data:** deploy **OpenRailwayMap**. Budget a real server: the import pipeline expects a planet-scale OSM dump and roughly 70 GB of fast scratch space.
- **You want to drive a train over a modelled route and test whether the timetable is drivable:** use **Open Rails**. It is a desktop simulator, not a service, and it is the least "self-hosted" of the three — but it is the only one that models train physics and signalling interaction in detail.

Do not expect to replace a commercial railway design suite with this stack. Expect to replace the parts of your workflow that are currently "a spreadsheet, a screenshot and an opinion" with something reproducible.

## Feature and Footprint Comparison

Repository data below was pulled live from GitHub on 2026-09-23.

| Project | Layer | License | Core stack | Deployment model | Stars | Last commit |
|---|---|---|---|---|---|---|
| **OSRD** | Infrastructure design, capacity, timetabling, simulation | LGPL-3.0 | Rust (`editoast`), TypeScript frontend, PostgreSQL/PostGIS, Valkey, RabbitMQ, OpenFGA | Docker Compose, web app | 660 | 2026-09-23 |
| **OpenRailwayMap** | Map rendering and railway data visualisation | GPL-3.0 | PHP frontend, PostgreSQL/PostGIS, osm2pgsql, Apache, Mapnik/Tirex | Manual server install (Ansible playbooks upstream) | 514 | 2026-04-20 |
| **Open Rails** | Train and route simulation | GPL-3.0 | C# / .NET (Mono-capable) | Desktop application | 333 | 2026-09-22 |

The activity column is the most important signal in that table. OSRD committed today; Open Rails committed yesterday. OpenRailwayMap's last commit was in April 2026 — the project is alive but not fast-moving, which matters because its dependency chain (PostgreSQL, PostGIS, osm2pgsql, Mapnik, Apache) is exactly the kind of stack that rots when nobody touches it.

## Which Project for Which Job?

| Use case | Recommended project | Why |
|---|---|---|
| Design or edit a track layout and check clearances | OSRD | Track, signalling and rolling-stock objects are first-class entities in its schema |
| Study whether a timetable is feasible on a given infrastructure | OSRD | Capacity and timetable simulation are the project's core purpose |
| Find a path at short notice (ad-hoc or disrupted operation) | OSRD | ST DCM search module finds paths against live infrastructure state |
| Publish a railway map of your region | OpenRailwayMap | Purpose-built rendering rules for railway tagging, signs and speeds |
| Analyse OSM railway data programmatically | OpenRailwayMap setup + PostGIS | The import pipeline gives you a queryable PostGIS database as a side effect |
| Train staff on a route, or test drivability | Open Rails | Physics-driven simulation with signalling and cab interaction |
| Air-gapped or offline demo | OSRD (Compose) or Open Rails | OSRD bundles everything in containers; Open Rails is a single local application |

## OSRD: The Only Genuine Self-Hosted Service in the Set

OSRD — Open Source Railway Designer — is a web application for railway infrastructure design, capacity analysis, timetabling and simulation, developed under the OpenRailAssociation umbrella. It is the tool French national operators have been contributing to publicly, and it shows: the architecture is a modern service stack rather than a monolith.

A single command brings up the whole thing from a clone:

```bash
git clone https://github.com/openrailassociation/osrd.git
cd osrd
docker compose up -d --build
# then open the frontend
xdg-open http://localhost:4000/
```

Two practical details from the project's own documentation save real time. First, Linux and WSL users can use the wrapper `./osrd-compose host` instead of `docker compose` to enable host networking, which is useful when you want to attach a debugger to a service. Second, Apple Silicon users should pin an arm64 PostGIS image before the first start, otherwise every database operation crawls through amd64 emulation:

```bash
# .env — create this before the first `docker compose` command
OSRD_POSTGIS_IMAGE='nickblah/postgis:16-postgis-3'
```

![OSRD — open source railway infrastructure design and simulation](/img/screenshots/osrd-railway.jpg)

The Compose file itself tells you what you are operating. OSRD ships PostgreSQL with PostGIS (default `postgis/postgis:16-3.4-alpine`), **Valkey** for caching, **RabbitMQ** for the workload queue, **OpenFGA** for authorisation, and separate services for the backend core (`editoast`, written in Rust), the API gateway and the frontend. That is not a toy deployment — it is a small platform, and it deserves the same treatment as any other platform you run: backup the PostGIS volume, monitor the RabbitMQ queue depth, and do not run it on a laptop you close at night.

Where OSRD earns its place: a *scenario* is a first-class object. You describe infrastructure, rolling stock and a timetable, then ask the simulator what happens. For capacity studies this is the difference between an argument and a measurement. The ST DCM module covers short-notice path search, which is how real operators handle disruption:

```bash
docker compose exec editoast editoast stdcm-search-env set-from-scenario <id>
```

**The sharp edges:** you must learn the data model. OSRD's native format is railJSON (schemas in the `osrd_schemas` package), and importing existing network data is a genuine engineering task. The service count also means the resource floor is higher than the other projects here — plan for a machine that can hold PostGIS plus four supporting services comfortably, and set `OSRD_POSTGIS_IMAGE` deliberately rather than accepting whatever architecture your laptop happens to be.

## OpenRailwayMap: Rendering Railway Infrastructure from OSM

OpenRailwayMap is an OpenStreetMap-based project for mapping the world's railway infrastructure — tracks, electrification, signalling, signs, speed limits and operating points. On the public instance it is a map. Self-hosted, it is a rendering pipeline plus a very useful PostGIS dataset.

Its install guide is honest about the scale of the job. Dependencies first:

```bash
apt-get install postgresql postgis osm2pgsql wget bc git osmium-tool tar gzip nodejs npm
apt-get install postgresql-common php-gettext unzip zip python3-pip wget php-pgsql libapache2-mod-php libapache2-mod-wsgi-py3 apache2 python3-pil python3-cairo python3-ply zlib1g-dev
apt-get install apache2 apache2-dev
pip3 install pojson polib
```

Then database extensions — note that `hstore` and `unaccent` are required, not optional:

```bash
sudo -u postgres createdb -E UTF8 -O osmimport openrailwaymap
sudo -u postgres psql -d openrailwaymap -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -d openrailwaymap -c "CREATE EXTENSION unaccent;"
sudo -u postgres psql -d openrailwaymap -c "CREATE EXTENSION hstore;"
```

The import is where people get surprised. The upstream scripts are designed for a **planet dump**, and the guide tells you to allocate roughly **70 GB** for the flat-nodes file that caches OSM node locations — on SSD or NVMe, not spinning rust — and to run the import inside a Tmux or screen session because it takes about an hour. Two configuration changes are mandatory before you start: point the scripts at a nearby planet mirror (the canonical host is rate-limited), and raise `max_connections`, because the renderer pool, the API pool and the import workers all want connections at the same time:

```
max_connections = (procs in /etc/tirex/renderer/mapnik.conf) +
                  (maxPoolSize in api/config.json) +
                  (OSM2PGSQL_NUMBER_PROCESSES in scripts/config.cfg) +
                  (superuser_reserved_connections in postgresql.conf)
```

**The pragmatic shortcut:** you do not have to import the planet. The pipeline works on extracts, and the OSM ecosystem publishes per-country and per-region extracts that fit comfortably in memory. For anything smaller than a continent, import the extract, tune the rendering styles, and skip the planet-scale hardware bill entirely. If tiles and vector data are your actual goal rather than railway-specific styling, our [vector tile server comparison](../2026-05-19-self-hosted-vector-tile-servers-tegola-vs-tileserver-gl-vs-martin-guide/) and the [GIS web map viewer guide](../2026-06-09-self-hosted-gis-web-map-viewers-qgis-server-mapbender-lizmap/) cover that layer in more depth.

**The sharp edges:** this project's deployment is Ansible-shaped, not container-shaped. There is no `docker compose up` here, the upstream maintainers' own playbooks live in a separate repository, and the guide assumes Debian or Ubuntu with Apache. If you are a Kubernetes shop, your first day is spent containerising a stack that was never containerised.

## Open Rails: Simulating the Train, Not the Map

Open Rails is a free train simulator that supports the world's largest range of digital content — including the legacy Microsoft Train Simulator route and rolling-stock formats. It is a C#/.NET desktop application, built from source via the solution in `Source/` (with `Build.cmd` on Windows and a Mono/.NET toolchain on Linux), and it is the third leg of a realistic railway workflow: OSRD tells you a path exists, OpenRailwayMap shows you where it goes, and Open Rails lets you actually drive it.

Why include a desktop simulator in a self-hosting article? Because "can a human or an automatic system drive this timetable" is a real question that capacity studies do not answer on their own. Open Rails models traction, braking and signalling interaction at a fidelity that map-based tools cannot, and its route/activity model means you can script and replay a scenario against a fixed route rather than arguing about it.

**The sharp edges:** it is not a service. There is no API to call, no container to orchestrate, and content authoring is its own discipline. Treat it as an offline verification tool that consumes the output of the design process, not as part of the deployed estate.

## Railway Data Hygiene: The Part Nobody Warns You About

Three practical lessons from running this class of tooling.

**1. Coordinate and reference systems will ambush you.** Everything in the OSM-derived pipeline is Web Mercator and WGS84. Everything a railway engineer measures is in a projected local system in metres, referenced to track chainage. Do the conversion once, centrally, and document it — mixing the two is the single most common source of "the map is 400 metres off" bug reports.

**2. Choose your extract size before you choose your hardware.** The difference between a country extract and a planet import is the difference between a 16 GB VM and a machine with 70 GB of NVMe scratch and a long weekend. Start with the smallest extract that contains your area of interest.

**3. Version your scenarios.** OSRD scenarios are data, and data you cannot diff is data you cannot review. Export them, commit them, and treat a changed timetable as a change request — otherwise your capacity study becomes unreproducible the moment somebody edits the infrastructure in place.

## FAQ

**Do I need a Planet OSM dump to run OpenRailwayMap?**
No. The upstream scripts default to planet-scale, but the pipeline accepts extracts. Import a country or regional extract, which is dramatically smaller, and skip the 70 GB flat-nodes cache unless you genuinely need global coverage.

**Is OSRD production-ready for a small operator or consultancy?**
It is actively developed, was committed to on the day of writing, and is a stage-2 OpenRailAssociation project, so the governance is real. The real barrier is not code maturity but data: you must get your infrastructure into railJSON, and that is a project in itself.

**Can these three tools share data?**
Partially. OpenRailwayMap's imported PostGIS database can feed your own analytical queries alongside the renderer, and Open Rails consumes route content in its own format. OSRD is the hub in practice: design there, export for visualisation, and treat the simulator as a verification step.

**What hardware should I plan for?**
For OSRD, a machine comfortable running PostgreSQL/PostGIS plus Valkey, RabbitMQ, OpenFGA and the application services — a 4-core, 16 GB VM is a sane starting point for evaluation, not for a large network. For OpenRailwayMap, disk speed matters more than CPU: the import is I/O-bound, and flat-nodes on NVMe rather than a spinning disk changes the job from painful to tolerable.

**Is there a hosted version I can look at first?**
Yes for OSRD — the project publishes a public demo instance, which is the fastest way to understand the scenario model before you deploy anything. OpenRailwayMap's reference instance is the map most people already know. Open Rails has no hosted mode at all.

**Which one should I deploy first?**
OSRD, if you have a network to design or a timetable to validate — it is the only one with a single-command deployment. Deploy OpenRailwayMap afterwards if you need a visual layer over OSM data. Add Open Rails only when you need driveability verification.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OSRD vs OpenRailwayMap vs Open Rails in 2026: Self-Hosting a Railway Planning, Mapping and Simulation Stack",
  "description": "How to self-host railway infrastructure design, mapping and simulation tools: OSRD, OpenRailwayMap and Open Rails compared with real install commands, hardware requirements and pitfalls.",
  "datePublished": "2026-09-23",
  "dateModified": "2026-09-23",
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
