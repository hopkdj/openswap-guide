---
title: "GeoNature vs TaxonWorks vs Living Atlases in 2026: Self-Hosted Biodiversity Data Platforms Compared"
date: "2026-11-08"
tags: ["self-hosted", "biodiversity", "data-management", "gis", "open-science"]
cover: "/img/screenshots/geonature-logo.jpg"
draft: false
---

Ecologists have a data problem that most software categories never face: the same sighting has to exist as a field observation, a voucher in a collection, a row in a national reporting database, and a Darwin Core record published to GBIF — and every one of those needs the same taxon name, the same coordinates, and the same date. Spreadsheets break at about the third person.

The open-source answer is not one application but three families of platform that occupy different parts of that pipeline. **GeoNature** is an occurrence and monitoring hub. **TaxonWorks** is a taxonomy and specimen workbench. **Living Atlases** (the Atlas of Living Australia stack) is a national aggregation portal. Choosing the wrong one means rebuilding your data model in year two, so here is an honest comparison of what each actually does.

## TL;DR / Quick Verdict

- **You collect field observations with protocols, need a mobile app, and must report to a national biodiversity hub** → **GeoNature**. The most complete occurrence workflow of the three, with a real data-entry frontend and mobile clients.
- **You are describing taxa, managing nomenclature, specimens and literature, and need a citable taxonomic backbone** → **TaxonWorks**. It is a taxonomist's workbench first and a database second, and nothing else here comes close on nomenclatural acts.
- **You are standing up a national or regional biodiversity portal that aggregates millions of records from many publishers** → **Living Atlases / ALA**. Built exactly for that job, and correspondingly heavy.

They are complementary rather than competing. A realistic national stack uses TaxonWorks (or an institutional collection system) as the source of truth for taxonomy, GeoNature for structured field inventory, and an ALA-style portal for public aggregation — with Darwin Core as the contract between them.

## Comparison Table (live GitHub data, 2026-11-08)

| Dimension | GeoNature | TaxonWorks | Living Atlases (ALA) |
|---|---|---|---|
| GitHub repo | PnX-SI/GeoNature | SpeciesFileGroup/taxonworks | AtlasOfLivingAustralia/ala-install |
| Stars | 133 | 117 | 28 |
| Language | Python (Django) + Angular | Ruby (Rails) | Jinja / Ansible playbooks |
| License | GPL-3.0 | MIT | Mixed, per component |
| Last commit | 2026-11-07 | 2026-11-07 | 2026-11-02 |
| Core purpose | Occurrence entry, synthesis, monitoring protocols | Taxonomy, nomenclature, specimens, literature | Aggregation, indexing and public portal |
| Primary users | Park rangers, NGOs, regional agencies | Taxonomists, natural history collections | National biodiversity facilities |
| Mobile data capture | Yes (Occtax and monitoring modules) | Limited (web workbench) | No (ingests published datasets) |
| Standards | Darwin Core, Chiroptères/standard protocols | Darwin Core export, nomenclature standards | Darwin Core, DwC-A, occurrence indexing |
| Database | PostgreSQL + PostGIS | PostgreSQL + PostGIS | Multiple (Cassandra, Elasticsearch, Postgres) |
| Deployment | `docker compose` services repo | Docker dev compose, Ansible for production | Ansible playbooks only |
| Documentation language | Primarily French | English | English |

## Scenario Decision Matrix

| Use case | Recommended | Why |
|---|---|---|
| A regional park recording flora/fauna transects | GeoNature | Protocol modules plus offline-capable mobile entry |
| A museum digitising type specimens | TaxonWorks | Nomenclatural acts, type designation, source citation |
| Publishing a checklist with synonymy | TaxonWorks | Built for taxonomy, not just occurrence rows |
| National biodiversity portal aggregating 40 publishers | Living Atlases | Biocache indexing and spatial portal are the whole point |
| Small NGO with 3 staff and no sysadmin | GeoNature (Docker) | One compose project, French docs, active community |
| Municipal "what lives here" public site | ALA-style portal or GBIF-hosted IPT | Do not build a portal for 5,000 records |
| Mixed: field data + collection vouchers | GeoNature + TaxonWorks | Link by taxon name and catalogue number, not by merging systems |

## GeoNature — the field-data workhorse

GeoNature (133 stars, GPL-3.0, Python/Django) is the reference biodiversity data platform for French protected areas. Its scope is deliberately operational: rangers enter observations, the system synthesises them by taxon and territory, and the data can be exported in standard formats.

Deployment is a separate repository, `GeoNature-Docker-services`, and the workflow is genuinely simple:

```bash
git clone https://github.com/PnX-SI/GeoNature-Docker-services.git
cd GeoNature-Docker-services
cp .env.sample .env
# edit POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, and the host names
docker compose up -d
docker compose logs -f --tail 100
```

The stack is not a single container. It brings up GeoNature's backend, its Angular frontend, UsersHub (the shared identity provider), a PostgreSQL/PostGIS instance, and optionally Traefik as an edge proxy — the `docker-compose.traefik.yml` file is included as a compose overlay, and you toggle it through the `COMPOSE_FILE` variable in `.env`. That overlay approach is worth stealing for your own projects: it keeps TLS termination out of the core file.

What GeoNature does better than the alternatives here is **protocol-based inventory**. Monitoring programmes are not "a list of sightings" — they are fixed protocols with visit schedules, sampling units and effort metadata. GeoNature models those as modules, which is why ecology NGOs keep choosing it over generic collection software.

The friction is documentation language. Most of the operational docs and community answers are in French, and the module ecosystem assumes you understand the French institutional context (ZNIEFF, EIN, regional hubs). English-speaking teams can absolutely run it — the code and configuration are readable — but budget extra time for the learning curve.

![TaxonWorks logo](/img/screenshots/taxonworks-logo.jpg "TaxonWorks — a biodiversity informatics workbench oriented around taxonomy and specimens")

## TaxonWorks — where nomenclature lives

TaxonWorks (117 stars, MIT, Ruby/Rails) is a different animal. It is described by its own maintainers as a *workbench for biodiversity informatics*, and the emphasis is on the taxonomic act: describing a species, designating a holotype, recording the publication, tracking synonymy, building matrix keys.

The repository ships a development compose file that shows the shape of the system:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.development
    volumes:
      - .:/app
    ports:
      - '127.0.0.1:3000:3000'
  db:
    image: postgis/postgis:17-3.5
    environment:
      - POSTGRES_HOST_AUTH_METHOD=trust
    ports:
      - '0.0.0.0:15432:5432'
```

Note the PostGIS image, and note the comment at the top of that file: it is a **development** target. Production deployment is a different path — the project maintains Ansible-based installation tooling and a separate installer repository rather than a single "production compose" file. If you want a container-first production story, GeoNature is closer to that than TaxonWorks.

That is not a criticism of the software. A Rails application with PostGIS, background jobs and a large bibliographic model is not something you `docker run` and forget; the maintainers are explicit about it. Plan for a normal Rails deployment: managed Postgres, a job runner, a reverse proxy, and scheduled backups.

Where TaxonWorks earns its place is **provenance of names**. If your institutional question is "which publication established this combination, and what did the previous author call it", a plain occurrence database cannot answer you. TaxonWorks can, and it exports Darwin Core when you need to talk to the aggregators.

## Living Atlases — the national portal, with national obligations

The Atlas of Living Australia stack — distributed internationally as **Living Atlases** — is what a country runs when it needs a public portal over tens of millions of occurrence records from dozens of publishers. The `ala-install` repository (28 stars) is not an application but a set of **Ansible playbooks**: the project's own README documents Ansible 2.17.3 core / 10.3.0 community as the supported versions, and expects a target host you provision from scratch.

A demo deployment follows the standard Ansible shape:

```bash
git clone https://github.com/AtlasOfLivingAustralia/ala-install.git
cd ala-install/ansible
ansible-galaxy install -r requirements.yml
ansible-playbook -i inventories/demo.ini ala-demo.yml
```

Be clear-eyed about the scale: a full ALA instance is a multi-service platform with an occurrence index (biocache), a spatial portal, a collections registry, a taxonomic name service, and a web frontend. The reference deployment is measured in tens of gigabytes of RAM, not hundreds of megabytes. Ansible version drift is the classic failure — pin the versions the playbooks expect, because roles break silently on newer releases.

The payoff is the only thing of its kind in open source: a genuine public biodiversity portal, with the spatial query interface and species pages that researchers and the public expect from a national atlas. If your ambition is smaller than that, hosting your dataset on an existing portal is almost always cheaper than building one.

## Pitfalls That Cost Weeks in Biodiversity Deployments

**1. The taxonomic backbone is the real project.** Occurrence data is easy; agreeing which taxon name is current is not. Decide which backbone you follow, version it, and store the backbone identifier on every row. GeoNature, TaxonWorks and ALA all have opinions, and none of them will reconcile differences for you.

**2. Coordinates need a CRS decision on day one.** PostGIS will happily store mixed projections and then silently misplace records in a map. Pick WGS84 / EPSG:4326 for anything that will be published, and transform at import, not at export.

**3. Darwin Core is a contract, not a format.** Term names, controlled vocabularies and date formats matter. A CSV that "looks right" will fail validation at GBIF and you will discover it weeks later, when the dataset is already referenced. Validate against the Darwin Core archive schema before publishing.

**4. Sensitive records need blurring.** Nesting sites, rare orchids, poaching risk: most jurisdictions require generalised coordinates for sensitive taxa. Build the generalisation rule into the export path, not into the spreadsheet.

**5. French documentation is not optional for GeoNature.** Install guides, module configuration and error messages assume French institutional vocabulary. If nobody on the team reads it, choose a different platform — misconfigured UsersHub permissions are a security problem, not a nuisance.

**6. Do not deploy ALA for small data.** If your dataset fits in a single IPT and a GBIF publication, you do not need biocache. Our [GBIF IPT vs iNaturalist vs PyBossa comparison](../2026-06-14-self-hosted-biodiversity-data-platforms-gbif-ipt-inaturalist-pybossa/) covers the lightweight publishing path.

**7. GIS services are a separate discipline.** All three platforms assume you can run a spatial stack. Tile serving, projection handling and WMS/WFS endpoints are their own operational skill set — see our [QGIS Server vs Mapbender vs Lizmap comparison](../2026-06-09-self-hosted-gis-web-map-viewers-qgis-server-mapbender-lizmap/) before you promise a map interface.

## FAQ

**Is GeoNature only useful in France?**
No, but it is France-shaped. The platform is used internationally, mostly by francophone organisations and European protected areas. Its strengths — protocol modules and a national-hub export path — map onto European reporting obligations particularly well. Elsewhere it still works, but you will be the one writing the integration.

**Can TaxonWorks replace a collection management system?**
It can hold specimen records and their determinations, and many collections use it for exactly that. What it does not try to be is a loan-management, accessioning and insurance system. If your registrar needs those workflows, pair TaxonWorks with a dedicated collection system and [connect them through stable identifiers](../2026-09-22-biodiversity-specimen-platforms-specify7-symbiota-arctos/).

**How many records can GeoNature handle?**
A single Docker deployment on 4 vCPU / 8 GB runs regional datasets of hundreds of thousands of observations without drama. The bottlenecks are PostgreSQL indexing on the synthesis views and PostGIS spatial queries on large polygons — tune `shared_buffers` and add GiST indexes before blaming the application.

**Do I need Ansible experience to run ALA?**
Yes, practically speaking. `ala-install` is a collection of playbooks, not a container image. If your team has never written an inventory file, the first deployment will take days. Containerisation efforts exist in the community but none is a supported path for a full instance.

**Which platform publishes to GBIF?**
All three can export Darwin Core archives, but the cleanest publishing route is usually a dedicated IPT instance fed by whichever platform holds the authoritative records. Aggregators do not care which database you use — they care that your archive validates.

**What about the mobile apps?**
GeoNature's Occtax and monitoring mobile clients are the strongest offline field-entry story of the three. TaxonWorks is web-first, and ALA expects data to arrive as published datasets rather than from field devices.

## Bottom line

Start from the data you actually hold. If it is **field observations with protocols**, deploy GeoNature and stop reading comparison articles. If it is **taxonomy and specimens**, TaxonWorks is the only one of the three built for your daily work. If it is **other people's datasets that must become a public portal**, that is Living Atlases — and if the answer is "a few thousand records", skip all three and publish an IPT archive.

The mistake to avoid is picking the platform with the nicest landing page. Biodiversity software is judged by whether your data survives the tenth schema change, and all three of these have survived several.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GeoNature vs TaxonWorks vs Living Atlases in 2026: Self-Hosted Biodiversity Data Platforms Compared",
  "description": "Hands-on comparison of GeoNature, TaxonWorks and the Living Atlases (ALA) stack for self-hosted biodiversity data management, with real deployment commands, standards support and operational pitfalls.",
  "datePublished": "2026-11-08",
  "dateModified": "2026-11-08",
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
