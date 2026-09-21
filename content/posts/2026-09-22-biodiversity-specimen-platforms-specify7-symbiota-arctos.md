---
title: "Specify 7 vs Symbiota vs Arctos in 2026: Self-Hosted Platforms for Natural History Collections"
date: "2026-09-22"
tags: ["self-hosted", "biodiversity", "collections", "research-data", "data-management"]
draft: false
cover: "/img/screenshots/specify7-collection-dashboard.jpg"
---

A natural history collection with two million specimens and one curator is not an unusual situation — it is the normal situation. Herbaria, insect collections, fossil repositories and tissue banks across universities and museums are digitising legacy labels under grant deadlines, and they are discovering that the bottleneck was never the scanner. It is the database: whether the collection management platform can model taxonomy, stratigraphy, tissues and field notes without a bespoke development project, and whether it can publish to global aggregators without a second copy of the data living in a spreadsheet.

Three open-source platforms carry most of that load in 2026: **Specify 7**, **Symbiota**, and **Arctos**. They are often described as interchangeable "collection management systems", which is like calling a laboratory notebook and a statistical package interchangeable because both involve numbers. This guide explains what each one actually is, how to deploy it, and which fits a herbaria, a palaeontology repository or a multi-institution network.

![Specify 7 collection management interface showing specimen records and data entry](/img/screenshots/specify7-collection-dashboard.jpg "Specify 7 specimen collection management dashboard")

## TL;DR — Quick Verdict

- **Choose Specify 7** if you run a single institution's collection and need deep, configurable schema — palaeontology, entomology, archaeology, botany, with support for tissues, loans, permits and preparation records. GPL-3.0, actively developed, and the most institutionally mature of the three. Budget for a real pilot: the shipped Docker composition is explicitly a development stack.
- **Choose Symbiota** if your goal is a **published, queryable portal** across many collections — regional herbaria networks, biodiversity checklists, keys and occurrence maps. It is GPL-2.0 PHP software, and its centre of gravity is Darwin Core occurrence data feeding aggregators like GBIF and iDigBio rather than internal curation workflow.
- **Choose Arctos** if you are joining (or running) a **multi-institution consortium** that needs one shared, rigorously normalised data model across museums, with per-collection control. Django + PostgreSQL, code published openly on GitHub, and the licensing question needs a direct conversation with maintainers before you commit.

In one line: **Specify 7 curates a collection, Symbiota publishes one, Arctos federates many.**

## The Contenders at a Glance (live GitHub data, September 2026)

| Platform | Repo | Stars | Last commit | License | Stack | Database | Model | Best for |
|---|---|---|---|---|---|---|---|---|
| **Specify 7** | `specify/specify7` | 100 | 2026-09-21 | GPL-3.0 | Python/Django + TypeScript frontend | MariaDB/MySQL | Single institution, highly configurable schema | Herbarium, entomology, palaeontology, archaeology repositories |
| **Symbiota** | `Symbiota/Symbiota` | 55 | 2026-09-21 | GPL-2.0 | PHP 8.2+ on Apache/Nginx | MySQL/MariaDB | Multi-collection portal with occurrence publishing | Regional networks, biodiversity data portals, checklists |
| **Arctos** | `ArctosDB/arctos` | 71 | 2025-11-20 | No SPDX license file detected | Python/Django | PostgreSQL | Shared multi-institution data model | Consortia, natural history museums, geology collections |

The licence column deserves attention. Specify 7 is GPL-3.0 and Symbiota is GPL-2.0 — both copyleft, both unambiguously open. Arctos publishes its source openly but no SPDX licence file is detected by tooling, which means you should confirm terms in writing with the maintainers if your institution has procurement or legal review. Do that before the pilot, not after curation begins.

## Scenario Decision Matrix

| Your situation | Recommended | Why |
|---|---|---|
| One herbarium, 50k–1M specimens, grant-funded digitisation | **Specify 7** | Configurable schema, label workflows, loan and permit records |
| Regional network of 30 herbaria needing one search portal | **Symbiota** | Built for multi-collection portals and occurrence publishing |
| Palaeontology with stratigraphy, localities and tissue links | **Specify 7** | Discipline-specific data model beyond flat occurrence records |
| Publishing to GBIF on a schedule | **Symbiota** | Occurrence-centric schema and Darwin Core export as a first-class workflow |
| Multi-museum consortium sharing one taxonomic authority | **Arctos** | Normalised shared model with per-collection access control |
| Small collection with no system administrator | **Specify 7** (managed pilot) or hosted Symbiota instance | Lowest barrier is hosted; self-hosting implies ops capacity |
| Need barcode label printing on day one | **Symbiota** | Documented optional barcode library for specimen labels |
| Fully offline, air-gapped lab network | **Specify 7** | Docker or native deployment with no external service dependency |
| Archive of documents and photographs, not specimens | Neither | See the museum and archive platforms comparison linked below |

## Specify 7 — Configurable Curation Depth

Specify 7 is a Django application with a TypeScript front end, backed by MariaDB. It inherits a schema built over two decades of collection work: specimens with determinations, taxa with synonymy, localities with geography and stratigraphy, collectors and agents, accession, loan and deaccession records, permits, preparations, and tissue and DNA links.

The repository ships a `docker-compose.yml` openly — read the comments in it before you plan a production rollout, because they are unusually candid:

```yaml
# docker-compose.yml (as shipped in specify/specify7)
# This is a Development Docker Composition of Specify 7
# It has nice features like hot reloading and debugging support
# However, it is not suited for production use due to memory leaks and security
# issues
services:
  mariadb:
    container_name: mariadb
    image: mariadb:11.8
    volumes:
      - "database:/var/lib/mysql"
      - "./seed-database:/docker-entrypoint-initdb.d"
    ports:
      - "127.0.0.1:3306:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}

  specify7:
    container_name: specify7
    build:
      context: ./.
      target: run-development
    command: ve/bin/python manage.py runserver 0.0.0.0:8000
    volumes:
      - "./config:/opt/Specify/config:ro"
      - "static-files:/volumes/static-files"
      - "./specifyweb:/opt/specify7/specifyweb"
    env_file: .env
```

That composition is the correct way to **evaluate** Specify 7 in an afternoon, and the wrong way to run a collection on it long term. Production compositions are provided to members of the Specify Collections Consortium. The practical path for most institutions is: pilot on the development composition with a seed copy of real data, then either join the Consortium for a supported production deployment or build and maintain your own hardened composition with a qualified Django operator. Budget that decision explicitly — it is the single most common surprise in Specify rollouts.

```bash
git clone https://github.com/specify/specify7.git
cd specify7
cp .env.example .env 2>/dev/null || cp .env_sample .env
# Set MYSQL_ROOT_PASSWORD and application settings in .env
docker compose up -d
# Verify the three services are healthy before loading data
docker compose ps
```

## Symbiota — Occurrence Data as the Product

Symbiota is a PHP application whose design goal is a portal: many collections, one search interface, occurrence records normalised toward Darwin Core and published outward. That orientation shows up in the install requirements, which are documented in `docs/INSTALL.md` and specify PHP 8.2 or newer for best performance (minimum 8.1, with 8.2 required if third-party authentication is enabled), Apache or nginx, and MySQL/MariaDB.

```bash
# LAMP deployment outline (Apache + PHP 8.2 + MySQL)
sudo apt-get install -y apache2 php8.2 php8.2-{mbstring,curl,gd,mysqli,zip,xml}
git clone https://github.com/Symbiota/Symbiota.git /var/www/html/symbiota
```

```ini
; php.ini — recommended adjustments from Symbiota's INSTALL.md
upload_max_filesize = 100M
max_input_vars = 2000
memory_limit = 512M
extension=curl
extension=exif
extension=gd
extension=mysqli
extension=zip
```

The three values that matter most in practice: `upload_max_filesize` must accommodate your largest batch import (herbarium image ingestion and DwC-A archives both blow past PHP defaults), `max_input_vars` governs how many fields a single curation form may submit — large specimen forms silently truncate fields when this is too low — and `memory_limit` determines whether taxonomy rebuilds complete or die halfway with an unhelpful error.

Optional extras are worth installing deliberately: the Pear `Image_Barcode2` package enables barcode printing on specimen labels, which is what makes retroactive barcoding of legacy cabinets practical, and Pear `Mail` provides SMTP support for notifications.

Symbiota's strength is that **publishing is not an afterthought**. Occurrence records are the primary object, taxonomic thesaurus management is built in, and checklists, keys and distribution maps are generated from the same data rather than exported and re-imported elsewhere.

## Arctos — One Model, Many Museums

Arctos is a Django application on PostgreSQL built around a deliberately normalised, shared data model: agents, places, taxonomy, media and transactions are global entities, and each participating collection controls its own records while contributing to the same authority tables. That is the opposite architectural bet from Specify's per-institution database and Symbiota's per-portal database, and it is why Arctos is common in multi-institution consortia where taxonomic duplication across museums is the core problem.

The trade is operational: a shared model means schema changes are consortium decisions, and upgrading is a coordinated activity rather than an institution-local one. Arctos is also the slowest-moving of the three upstream — the last commit recorded at the time of writing is November 2025 — so treat "the code is on GitHub" as a starting point for a conversation about governance rather than a self-service install:

```bash
# Evaluation deployment (Django + PostgreSQL)
git clone https://github.com/ArctosDB/arctos.git
cd arctos
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# Configure the database connection, then:
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Before you invest curation effort, confirm with the maintainers (a) the licensing terms that apply to your use, and (b) whether your institution should run its own instance or contribute to the communal one. The second question is the architectural decision; the first is the procurement blocker.

## The Data Layer Nobody Plans For

**Taxonomic authority files drift.** Three collections using three spellings of the same species produce three occurrences in aggregators. Decide early whether your taxonomic backbone is local, imported from a global authority, or shared consortium-wide, and document who may edit it. This is the most common cause of unusable data five years in.

**Plan your export before you plan your import.** Ask one question of every candidate platform: *can I get my full dataset out as Darwin Core Archive, including media links, without vendor assistance?* All three can, but the effort differs and must be tested on day one with real data, not in year three.

**Herbarium sheet imaging is a storage problem, not a database problem.** A single collection's sheet images routinely reach multiple terabytes at archival resolutions. Decide the resolution tier you will keep, store originals in object storage, and let the database reference them by stable identifiers rather than embedding paths that break when directories are reorganised.

**Obscure sensitive localities.** Threatened species localities, private land access and culturally sensitive sites should be generalised at publication time — ideally in the platform's own publishing rules, not by editing records, so the precise coordinates survive internally while the public record stays safe.

**Stable identifiers are a publication commitment.** If you mint ARKs or DOIs for specimens, the resolution target must remain valid across a platform migration. Test that a record's public URL still resolves after a schema change.

**Do not confuse specimen records with observations.** Observed occurrences have no physical voucher and different provenance rules. Aggregators handle both, but your internal workflow will break if the two share a form with the same required fields.

**Backups plus restore drills, monthly.** A collection database is often the only structured record of a physical object's metadata. Schedule `mysqldump` or `pg_dump`, restore into a scratch instance on a calendar, and keep a copy off-site. Verify that media storage has an independent backup path.

If your collection is mixed — specimens plus archival documents, field notebooks and photographs — the specimen database is only half the system, and our [museum and archive collection management comparison](../2026-06-08-self-hosted-museum-archive-collection-management-collectionspace-atom-archivesspace/) covers the cultural-heritage side. For archaeological context data that sits alongside natural history records, see the [archaeology data platforms guide](../2026-06-15-self-hosted-archaeology-data-platforms-arches-openatlas/), and for library and digital-collection cataloguing, the [digital collection comparison](../2026-05-02-koha-vs-omeka-vs-invenio-self-hosted-library-digital-collection-guide/) is the relevant reference.

## FAQ

**Can I migrate from Specify 6 to Specify 7 without re-keying data?**
Yes — Specify 7 is designed to read a Specify 6 database, and the Docker composition mounts a `./config` directory to supply Specify 6 configuration files to both the application and the web server. The practical constraint is version: upgrade the Specify 6 instance to a supported release first, take a verified dump, then run the migration against a copy. Test on a copy of the real database, never on the only instance.

**Does Symbiota require PHP 8.2 specifically?**
The official install documentation recommends PHP 8.2 or higher for performance, security and feature support, with 8.1 as the minimum — and PHP 8.2 or above becomes mandatory when third-party authentication is enabled. Running below 8.1 is documented as likely to cause security and performance problems over time.

**Which platform publishes to GBIF most easily?**
Symbiota, because occurrence records are its primary object and Darwin Core export is part of normal operation rather than an add-on. Specify 7 collections publish through portal software or an export pipeline, and Arctos participants typically publish through the consortium's existing arrangements. Whichever you choose, test a full round-trip export → aggregator validation before committing to a public dataset.

**Is a collection management system the same as a digital repository for scanned documents?**
No, and conflating them causes pain. Specify 7, Symbiota and Arctos model biological and geological objects and their determinations. Documents, photographs and institutional records belong in archival platforms with different metadata standards and different retention rules. Mixed institutions generally run both.

**What does self-hosting actually cost?**
For a collection of tens of thousands of records, a modest virtual server with a managed database is sufficient for the application layer; the budget line that grows is object storage for specimen images and its backup, which scales with your imaging resolution and cannot be compressed away. The other recurring cost is administrator time: patching, restore drills and annual upgrade testing. Plan it as a role, not a task.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Specify 7 vs Symbiota vs Arctos in 2026: Self-Hosted Platforms for Natural History Collections",
  "description": "A 2026 comparison of open-source natural history collection management platforms: Specify 7, Symbiota and Arctos, with verified deployment configurations, data standard guidance and migration pitfalls.",
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
