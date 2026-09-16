---
title: "DHIS2 vs OpenCRVS vs openIMIS in 2026: Self-Hosting Health Information Systems for Public Sector Programs"
date: "2026-09-16"
tags: ["healthcare", "self-hosted", "public-sector", "digital-public-infrastructure", "comparison"]
draft: false
cover: "/img/screenshots/dhis2-logo.jpg"
description: "DHIS2 vs OpenCRVS vs openIMIS compared for 2026: what each self-hosted platform actually does, real Docker Compose configs, licensing traps and rollout pitfalls from real deployments."
---

# DHIS2 vs OpenCRVS vs openIMIS in 2026: Self-Hosting Health Information Systems for Public Sector Programs

SaaS electronic medical records fail in exactly the places where public health systems operate: clinics on intermittent links, ministries that cannot export their own data, and procurement rules that demand source access and local hosting. That is why ministries of health, national statistical offices and large NGOs run a different class of software — **digital public infrastructure** built for aggregate reporting, case surveillance and health financing rather than for a single hospital's billing.

Three projects dominate this space in 2026, and they are frequently confused with one another: **DHIS2** (aggregate health information management), **OpenCRVS** (civil registration and vital statistics) and **openIMIS** (health insurance and claims management). They are not interchangeable — picking the wrong one costs a program years. This comparison uses live repository data pulled on **2026-09-16**, real Compose files from each upstream repo, and the deployment realities that documentation glosses over.

## TL;DR — The 30-Second Verdict

- **Choose DHIS2** if you need national or district-level health data aggregation, dashboards, and routine reporting from hundreds of facilities. It is the most mature option by a wide margin and the de facto standard for health management information systems.
- **Choose OpenCRVS** if the deliverable is **civil registration** — births, deaths, marriage certificates — with a legal identity workflow, offline-capable field registration and verifiable certificates.
- **Choose openIMIS** if you administer **health insurance schemes**: enrolment, claims adjudication, provider payment and reconciliation. It is the only one of the three with claims logic built in.
- **They are complements, not competitors.** Mature national programs run OpenCRVS for registration, openIMIS for claims, and DHIS2 for aggregate reporting, then connect them with interoperability layers.

## Platform Comparison (verified 2026-09-16)

| Dimension | DHIS2 | OpenCRVS | openIMIS |
|---|---|---|---|
| Repository | `dhis2/dhis2-core` | `opencrvs/opencrvs-core` | `openimis/openimis-be_py` |
| Stars | **352** | 120 | 13 |
| Last push | 2026-09-16 | 2026-09-16 | 2026-09-16 |
| Primary language | Java | TypeScript | Python |
| License | **BSD-3-Clause** | **MPL-2.0** | **AGPL-3.0 with additional terms** |
| Primary purpose | aggregate HMIS, tracker, analytics | civil registration (CRVS) | health insurance & claims |
| Deployment shape | Java app + PostgreSQL/PostGIS | many small Node services + PostgreSQL | Django + PostgreSQL (+ optional MSSQL), OpenSearch |
| Container images | `dhis2/core`, `dhis2/core-dev` | `ghcr.io/opencrvs/ocrvs-*` | `ghcr.io/openimis/openimis-*` |
| Compose file in repo | yes (dev-oriented) | yes | yes |
| Production compose | `dhis2/docker-deployment` | country config repo + Compose | Compose + `.env` |
| Offline field capture | via Android apps (tracker) | first-class offline forms | limited (claims entry) |
| Interoperability | ADX/DXF2, FHIR exports, Web API | FHIR, OpenHIM, event bus | FHIR, ILT (interoperability layer) |
| Best fit | national/district reporting | legal identity, vital statistics | scheme administration, payer ops |

## Decision Matrix — Pick by Deliverable

| Your Deliverable | Recommended | Reason |
|---|---|---|
| Monthly facility reporting to a ministry dashboard | DHIS2 | Purpose-built aggregation, org-unit hierarchy, analytics |
| Birth and death certificates with legal validity | OpenCRVS | Registration workflow and certificate issuance are native |
| Claims adjudication and provider payments | openIMIS | Claims, tariffs and scheme rules are core domain objects |
| Immunisation campaign coverage tracking | DHIS2 | Tracker programs plus aggregate reporting |
| Insurance enrolment with household structures | openIMIS | Household/group enrolment model |
| Civil registration feeding statistics | OpenCRVS | Built to export vital statistics |
| One integrated national platform | all three + an interoperability layer | Registration, claims and reporting are different jobs |
| A single clinic's patient records | none of these | Use an EMR — see our [EMR comparison](../2026-06-04-self-hosted-medical-emr-ehr-openemr-openmrs-ehrbase-guide/) |

## DHIS2 — The Aggregate Reporting Workhorse

DHIS2 stores data against an **org-unit hierarchy** (national → region → district → facility) and a **data element** dictionary, which is exactly the shape ministries report in. Version 2.x runs as a single Java application against PostgreSQL with PostGIS.

The core repository ships a Compose file, and upstream explicitly labels it development-only — a detail that gets ignored more often than it should:

```bash
# Quick evaluation (NOT production — upstream warns about this)
git clone https://github.com/dhis2/dhis2-core.git
cd dhis2-core
cp .env.example .env        # DHIS2_IMAGE, DB_HOSTNAME, DB_NAME, DB_USERNAME, DB_PASSWORD
# .env.example defaults: dhis2/core-dev:latest, db, dhis, dhis, dhis
docker compose up -d
```

```yaml
# docker-compose.yml (abridged, from dhis2/dhis2-core)
services:
  web:
    image: "${DHIS2_IMAGE:-dhis2/core-dev:local}"
    environment:
      DB_HOSTNAME: "${DB_HOSTNAME:-db}"
      DB_NAME: "${DB_NAME:-dhis}"
      DB_USERNAME: "${DB_USERNAME:-dhis}"
      DB_PASSWORD: "${DB_PASSWORD}"
  db:
    image: ghcr.io/baosystems/postgis:16-3.5
```

The same Compose file can seed a demo database from `https://databases.dhis2.org/...`, which is genuinely useful for training and schema testing — and genuinely dangerous if pointed at production. For real deployments, upstream maintains a separate production Compose set at `dhis2/docker-deployment` (pushed 2026-09-15), which is where you should start for anything with real data.

**Operational reality:** DHIS2 is a stateful Java application with an analytics layer. Provision CPU and RAM for the analytics generation step, put PostgreSQL on fast storage, and plan a maintenance window for version upgrades — the SQL upgrade scripts are not something to run unattended at 2 a.m. on a whim.

## OpenCRVS — Civil Registration as a Legal Process

![OpenCRVS official project mark](/img/screenshots/opencrvs-logo.jpg "OpenCRVS civil registration and vital statistics platform")

OpenCRVS models registration as a workflow with **declarations, validation, registration and certificate issuance**, plus offline-capable field clients so a registrar in a low-connectivity district can keep working. Nationally, that means it touches legal identity — treat it accordingly.

It is deployed as a fleet of small services published to GHCR under a shared version tag:

```yaml
# docker-compose.yml (abridged, from opencrvs/opencrvs-core)
services:
  client:
    image: ghcr.io/opencrvs/ocrvs-client:${VERSION}
  gateway:
    image: ghcr.io/opencrvs/ocrvs-gateway:${VERSION}
  events:
    image: ghcr.io/opencrvs/ocrvs-events:${VERSION}
  auth:
    image: ghcr.io/opencrvs/ocrvs-auth:${VERSION}
  migration:
    image: ghcr.io/opencrvs/ocrvs-migration:${VERSION}
  documents:
    image: ghcr.io/opencrvs/ocrvs-documents:${VERSION}
```

```bash
export VERSION=v1.8.0       # pin an explicit release tag, never "latest"
docker compose up -d
```

**The catch nobody mentions in the README:** OpenCRVS is designed to be deployed **with a country configuration package** — your forms, certificate templates, location hierarchy and user roles live in a separate repository, not in the core. Budget engineering time for that layer, because it is not optional and it is where most of the real work happens. Pin `VERSION` explicitly: mixing client and gateway tags across releases produces subtle workflow breakage that is painful to debug.

## openIMIS — Claims, Tariffs and Scheme Administration

openIMIS is the odd one out: it exists because insurance schemes need **claims**, not charts. It handles enrolment, policy management, claims submission and adjudication, provider payment and reconciliation — with a Django backend and a substantial data model.

```yaml
# docker-compose.yml (abridged, from openimis/openimis-be_py)
services:
  db:
    container_name: ${PROJECT_NAME:-openimis}-db
    image: ghcr.io/openimis/openimis-pgsql:${DB_TAG:-develop}
    environment:
      - POSTGRES_PASSWORD=$PSQL_DB_PASSWORD
      - POSTGRES_DB=$PSQL_DB_NAME
      - POSTGRES_USER=$PSQL_DB_USER
    volumes:
      - database:/var/lib/postgresql/data

  opensearch:
    image: opensearchproject/opensearch:3.8.0
```

```bash
cp .env.example .env      # set PSQL_DB_*, DB_TAG, PROJECT_NAME
docker compose up -d
```

Two things to know before you commit:

1. **The Compose stack is heavier than it looks.** It ships a PostgreSQL image, an optional MSSQL image for legacy interoperability, and OpenSearch 3.8.0 for search. That is three stateful services to back up, monitor and upgrade — not one.
2. **The licence deserves a legal read.** The repository's `LICENSE.md` places the software under **AGPL-3.0** with additional terms, including a clause stating that disputes are governed by **the public law of Switzerland with jurisdiction in Berne**. If you are a commercial integrator building a hosted offering on top, get that reviewed before you write code — GitHub reports the licence as "Other", which is a hint that automated tooling will not classify it for you.

## Interoperability: Where These Systems Meet

The pragma: aggregate reporting, civil registration and claims each own a different slice of data, and countries connect them rather than force one system to do everything.

- **DHIS2** exposes a documented Web API and supports ADX/DXF2 exchange formats, which is how facility-level HMIS data gets pushed from facility systems.
- **OpenCRVS** publishes events and supports FHIR-based exchange, so a registered birth can feed both the statistics office and a health program.
- **openIMIS** includes an interoperability layer for FHIR resources, designed to plug into national health information exchanges.

If you are designing that layer, our [FHIR and HL7 interoperability platform comparison](../2026-06-04-self-hosted-fhir-hl7-healthcare-interoperability-hapi-microsoft-blaze-ibm-guide/) covers the servers that do the routing, and the same design discipline applies to [clinical research data platforms](../2026-06-13-self-hosted-clinical-research-data-platforms-openclinica-openmrs-loris/) where consent and audit requirements overlap.

## Deployment Pitfalls That Cost Programs Months

**1. Treating DHIS2's dev Compose as production.** The core repository says plainly that its Compose file is not for production. Real deployments need the dedicated production Compose, tuned PostgreSQL, backups, and a plan for the analytics step.

**2. Forgetting the country configuration layer.** OpenCRVS without a country config package does almost nothing. Plan for form design, certificate templates, location hierarchies, and role matrices as first-class project workstreams with version control.

**3. Underestimating openIMIS storage.** PostgreSQL plus optional MSSQL plus OpenSearch means three backup routines. Test restores, not just dumps — a claims database you cannot restore is a liability, not an asset.

**4. Skipping a licence review.** DHIS2 is BSD-3-Clause and OpenCRVS is MPL-2.0, both friendly to commercial integration. openIMIS's AGPL-3.0-plus-additional-terms requires a closer look, particularly for hosted offerings.

**5. Rushing the data model decisions.** Renaming a DHIS2 data element or restructuring an openIMIS tariff after eighteen months of production data is a migration project, not a settings change. Spend the extra week up front with the ministry's actual reporting forms in hand.

**6. Overlooking identity and audit requirements.** These systems hold data about identifiable people. Plan role separation, access logging and retention policy before go-live — retrofitting audit trails into a running national system is far more expensive than enabling them from day one.

**7. Ignoring low-bandwidth behaviour.** Test client flows on a throttled connection and on an intermittent one. Offline-first features only help if the sync conflict rules match how registrars actually work.

**8. Handling dates and reporting periods carelessly.** Fiscal years, reporting periods and timezone boundaries are a classic source of wrong numbers in health reporting. Normalise timestamps to UTC at ingest and keep reporting calendars explicit — the same discipline we described in our [PHP date library comparison](../2026-09-16-php-datetime-libraries-carbon-chronos-brick-comparison/).

**9. Forgetting that a demo dataset is not a template.** The DHIS2 demo dump is excellent for training and schema exploration, and a terrible basis for a national data model.

## Which Should You Choose?

If you are running **national health reporting**, DHIS2 is the default answer and has been for years: mature, documented, and supported by a large implementer community. If you are building **legal identity and vital statistics**, OpenCRVS is the strongest open option, provided you budget for country configuration. If you are administering **health insurance**, openIMIS is the only one of the three with claims logic, and its licence needs sign-off before commercial use.

The most common mistake is expecting one platform to cover all three jobs. Registration produces the identity, insurance produces the payment record, and DHIS2 produces the aggregate picture. Connect them with an interoperability layer and you get a national system; force them into one product and you get a rebuild in three years.

## FAQ

**Is DHIS2 free to use commercially?**
Yes. DHIS2 core is released under the BSD-3-Clause licence, a permissive licence that allows commercial use, modification and redistribution with attribution. Implementer and support services are typically contracted separately, but the software itself carries no licence fee.

**What is the difference between DHIS2 and OpenCRVS?**
DHIS2 aggregates health data for reporting and analytics — case counts, service statistics, campaign coverage — organised by facility hierarchy. OpenCRVS manages individual legal registration events such as births and deaths, with certificates and workflow. A birth record may feed DHIS2 statistics, but the systems serve different legal and analytical purposes.

**Can OpenCRVS run without a country configuration repository?**
Not usefully. The core provides the engine; forms, certificate templates, location hierarchies and user roles come from a country-specific configuration package that you maintain and version yourself. Treat that repository as part of your deployment, not an optional add-on.

**How much server capacity do these platforms need?**
DHIS2 needs a Java application plus PostgreSQL/PostGIS with enough RAM for analytics generation, typically several gigabytes and growing with data volume. OpenCRVS runs a fleet of small services, so capacity scales with the number of services rather than one large JVM. openIMIS needs PostgreSQL plus OpenSearch, and optionally MSSQL for legacy interfaces — budget for three stateful components.

**Do these systems work offline in low-connectivity districts?**
DHIS2 supports offline data capture through its Android client family for tracker programs. OpenCRVS was designed with offline field registration as a core requirement and syncs when connectivity returns. openIMIS assumes a mostly online workflow for claims entry. Test sync behaviour under real network conditions before a national rollout.

**How do I connect them to other systems?**
Use the interoperability layer each project provides: DHIS2's Web API and ADX/DXF2 exchange, OpenCRVS event and FHIR interfaces, and the openIMIS interoperability layer for FHIR. A shared FHIR server or integration engine in the middle is the standard architecture, and it keeps each system's upgrade cycle independent.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DHIS2 vs OpenCRVS vs openIMIS in 2026: Self-Hosting Health Information Systems for Public Sector Programs",
  "description": "Self-hosted health information platforms compared: DHIS2, OpenCRVS and openIMIS — real Docker Compose configurations, licensing differences, interoperability and rollout pitfalls for 2026.",
  "datePublished": "2026-09-16",
  "dateModified": "2026-09-16",
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
