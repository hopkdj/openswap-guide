---
title: "Self-Hosted Computer-Aided Dispatch in 2026: Resgrid vs SnailyCAD vs OpenCAD Compared"
date: "2026-09-22"
tags: ["self-hosted", "emergency-management", "dispatch", "operations", "cad"]
draft: false
cover: "/img/screenshots/resgrid-dispatch-app.jpg"
---

Commercial computer-aided dispatch (CAD) platforms are priced like enterprise software because they are enterprise software: per-seat licensing, five-figure implementation fees, and a support contract that renews whether or not you ever see the invoice line. For a volunteer fire department, a campus security team, a search-and-rescue group or an event operations command post, that pricing model is simply out of reach — which is why three open-source CAD platforms have quietly become the default for organisations that need incident logging, unit status and personnel accountability without a procurement cycle.

This guide compares **Resgrid**, **SnailyCAD v4** and **OpenCAD** as self-hosted dispatch platforms: what each actually does, how to deploy it, where the sharp edges are, and which one fits your organisation in 2026.

![Resgrid computer-aided dispatch application interface](/img/screenshots/resgrid-dispatch-app.jpg "Resgrid dispatch application showing incident and unit status management")

## TL;DR — Quick Verdict

- **Choose Resgrid** if you are a real first-response organisation (fire, EMS, SAR, disaster response, industrial safety). It is the only one of the three built around personnel accountability, shift signups, unit/AVL tracking and run logs for actual emergency operations. Apache-2.0, actively developed, and it ships official mobile apps that talk to any standard installation.
- **Choose SnailyCAD v4** if you need a modern, well-documented web dispatch stack with a clean TypeScript codebase and a production Docker composition you can stand up in an evening. MIT licensed, PostgreSQL-backed, and the best-documented install path of the three. Its community roots are roleplay and civil-simulation networks, but the dispatch mechanics — calls, units, officers, records — are the same mechanics any operations centre needs.
- **Only choose OpenCAD** if you are already running PHP/MySQL infrastructure and want a small, familiar footprint. It is GPL-3.0 and functional, but the last upstream commit was in **February 2024**, so treat it as a legacy system you maintain yourself rather than a living project.

If your requirement is "log incidents, track units, prove who was assigned" and you have a competent Linux admin, all three will do the job. If your requirement is "run a shift roster for 60 volunteers with certifications and mutual-aid agreements", only Resgrid is designed for that.

## The Contenders at a Glance (live GitHub data, September 2026)

| Platform | Repo | Stars | Last commit | License | Stack | Database | Deployment | Mobile apps |
|---|---|---|---|---|---|---|---|---|
| **Resgrid** | `Resgrid/Core` | 228 | 2026-09-21 | Apache-2.0 | ASP.NET Core (.NET) + web UI | PostgreSQL | Docker composition in `Docker/`, IIS/Windows supported | Official iOS + Android |
| **SnailyCAD v4** | `SnailyCAD/snaily-cadv4` | 169 | 2026-05-01 | MIT | TypeScript — NestJS API + React client (pnpm monorepo) | PostgreSQL | `production.docker-compose.yml` (api + client + postgres) | Progressive web app |
| **OpenCAD** | `opencad-community/OpenCAD-php` | 107 | 2024-02-22 | GPL-3.0 | PHP + MySQL | MySQL/MariaDB | Classic LAMP: clone into webroot, import schema | Responsive web UI |

Two numbers matter more than the rest. First, Resgrid's commit timestamp — same-day activity means security patches land quickly. Second, OpenCAD's 2024 timestamp — a dispatch system that has not been touched in two and a half years will accumulate PHP compatibility debt and unpatched dependencies faster than a self-hosting team can track.

## Scenario Decision Matrix

| Your situation | Recommended | Why |
|---|---|---|
| Volunteer fire department with shift signups and certifications | **Resgrid** | Duty shift system, personnel certification records, run logs, unit status |
| Campus / industrial site security with incident escalation | **Resgrid** or **SnailyCAD** | Resgrid for accountability workflows; SnailyCAD for a lighter web-only footprint |
| Event operations centre that needs a public-facing call board | **SnailyCAD** | Modern React UI, per-record citizen/business/officer models, active documentation |
| Search and rescue with vehicle location tracking | **Resgrid** | Native AVL/unit grouping and mobile apps for field responders |
| Air-gapped or offline-only network | **Resgrid** | Self-contained .NET deployment behind IIS or Docker, no external service dependency |
| Small team that wants one `docker compose up` and no compilers | **SnailyCAD** | Published production composition; no build toolchain beyond Docker |
| Existing PHP hosting, no Docker skills | **OpenCAD** | Upload-and-import deployment; expect to patch PHP notices yourself |
| You need 911/NG911 or CAD-to-CAD integration | None of the three | All are standalone CAD systems with APIs, not certified public-safety integrations |

## Resgrid — Built for Real Emergency Operations

Resgrid is the most feature-complete of the three because it does not stop at dispatch. The platform covers personnel and contact records, certifications and roles, units and groups, automatic vehicle location, calls and incidents with both manual and automatic dispatch, messaging and command chat, duty shift signups with trade/swap support, training completion records, run logs, reporting, calendar RSVP events, and inventory tracking for apparatus and perishable supplies.

That breadth is the point. A dispatch system that only tracks calls still leaves you reconciling who was actually on shift in a spreadsheet at the end of the quarter.

Installation assets are versioned in the repository under a `Docker/` directory that contains a `docker-compose.yml`, a `run.sh` helper, an `resgrid.env` environment file, plus `db`, `mailserver.env` and `monitoring` subdirectories — in other words, a composable stack rather than a single container:

```bash
# Clone the full platform
git clone https://github.com/Resgrid/Core.git
cd Core/Docker

# Review the environment file before first boot:
#   resgrid.env   -> connection strings, mail settings, signing keys
#   mailserver.env -> SMTP relay configuration for notification email
cat resgrid.env

# Bring the stack up
docker compose up -d
docker compose logs -f --tail=50
```

```yaml
# Docker/docker-compose.yml (structure as shipped in the repo)
services:
  postgres:
    image: postgres
    env_file: resgrid.env
    volumes:
      - ./docker-data/db:/var/lib/postgresql/data
  resgrid:
    build: ..
    env_file: resgrid.env
    depends_on:
      - postgres
    ports:
      - "443:443"
```

Exact service names and image tags change between releases, so read `Docker/docker-compose.yml` and `Docker/resgrid.env` in the revision you clone rather than copying a blog snippet — including this one. Windows-native deployments via IIS are also documented at `docs.resgrid.com` if your organisation standardises on Windows Server.

The mobile applications are the strongest operational argument for Resgrid: apps for personnel, units, stations and commanders work against **any standard installation**, so field responders get status updates without you building a client.

## SnailyCAD v4 — The Modern Web Stack

SnailyCAD v4 is a pnpm workspace monorepo with `apps/api` (NestJS) and `apps/client` (React), wired together by a `Dockerfile` with separate build targets per service. The repository ships both a development composition and a genuine production composition, which is rarer than it should be in this space.

```yaml
# production.docker-compose.yml (as shipped)
services:
  postgres:
    container_name: "snaily-cad-postgres"
    image: postgres:latest
    environment:
      POSTGRES_PORT: ${DB_PORT}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${DB_PORT}:5432"
    networks:
      - cad_web
    volumes:
      - ./.data:/var/lib/postgresql/data
    restart: unless-stopped

  api:
    container_name: "snaily-cad-api"
    build:
      context: .
      dockerfile: ./Dockerfile
      target: api
    ports:
      - "${PORT_API}:${PORT_API}"
    depends_on:
      - postgres
    networks:
      - cad_web
    restart: always
    volumes:
      - ./apps/api/public:/snailycad/apps/api/public

  client:
    container_name: "snaily-cad-client"
    build:
      context: .
      dockerfile: ./Dockerfile
      target: client
    ports:
      - "${PORT_CLIENT}:${PORT_CLIENT}"
    depends_on:
      - postgres
    networks:
      - cad_web
    restart: always

networks:
  cad_web:
    external: true
```

Note the last block: the network is declared **external**, so you must create it before the first `compose up`, or the stack fails with a "network cad_web declared as external, but could not be found" error. This single line accounts for a large share of first-install failures:

```bash
docker network create cad_web
cp .env.example .env
# Set at minimum: POSTGRES_PASSWORD, POSTGRES_USER, POSTGRES_DB,
# DB_HOST=postgres, DB_PORT=5432, PORT_API, PORT_CLIENT
docker compose -f production.docker-compose.yml up -d --build
```

The `.env.example` shipped in the repo is unusually well annotated — every variable links to the corresponding reference page on `docs.snailycad.org`, including the distinction between `DB_HOST=postgres` for Docker installs and `localhost` for standalone installs. That documentation quality is why SnailyCAD is the easiest of the three to hand to a junior admin.

## OpenCAD — The PHP Legacy Option

OpenCAD is a classic LAMP application: PHP pages named after their function (`index.php`, `cad.php`, `dashboard.php`, `mdt.php`, `civilian.php`), a separate `oc-admin` administration panel, `actions/` handlers, and an `.htaccess.dist.txt` you rename to `.htaccess`. Deployment is a webroot copy plus a schema import:

```bash
# Deploy to a LAMP host (Apache + PHP + MySQL/MariaDB)
cd /var/www/html
git clone https://github.com/opencad-community/OpenCAD-php.git cad
cd cad
cp htaccess.dist.txt .htaccess
# Create the database and import the schema
mysql -u root -p -e "CREATE DATABASE opencad CHARACTER SET utf8mb4;"
# Edit the connection settings in the config file referenced by index.php,
# then browse to /cad and run the installer.
```

It works, it is small, and GPL-3.0 gives you the freedom to modify it. But be honest about the trade: **no upstream commits since February 2024**, no container images, and no mobile client. If you deploy it in 2026 you own every future PHP version bump, and you should expect to fix deprecation warnings on modern PHP releases. For a small team with PHP skills and low change tolerance, that is an acceptable trade; for anything with a public safety mandate, it is not.

## Deployment Pitfalls That Cost Real Hours

**The external Docker network trap.** As shown above, SnailyCAD's production composition expects a pre-created `cad_web` network. Create it once per host, not per project, or you will re-debug the same failure after every host migration.

**Map tiles and geocoding are not free.** Dispatch UIs render unit positions on a map. Point them at your own tile server or use a provider key you control, and set usage limits — a public-facing dispatch map that suddenly gets scraped can generate a surprising provider bill. Our [self-hosted GPS tracking and fleet management comparison](../2026-05-04-self-hosted-gps-tracking-fleet-management-traccar-owntracks-gpslogger-guide/) covers the open alternatives for the tracking layer behind the UI.

**Push notifications need your own credentials.** Resgrid's mobile apps rely on platform push services. Self-hosting the server does not exempt you from generating and rotating the notification credentials for iOS and Android, and those credentials expire.

**Time syncing is a correctness issue, not a nicety.** Every CAD record is timestamped, and incident timelines are used in after-action reviews. Run `chrony` or `systemd-timesyncd` on the host, in UTC, and render local time at the UI layer. The same applies to the telemetry side — see our [emergency and crisis management platform comparison](../2026-06-08-self-hosted-crisis-emergency-management-ushahidi-sahana-hot-tasking-manager/) for how incident data flows between systems.

**Backups must be tested, not scheduled.** A dispatch database is a legal record in many jurisdictions. Run `pg_dump` on a schedule, restore into a scratch container monthly, and store the dump off-host. An untested backup is a rumour.

**Do not self-host without a second administrator.** If the only person who can restore the CAD server is on the call the cad system is dispatching, your incident logging has a single point of failure that is not a server.

**Plan the reverse proxy before go-live.** All three assume a web server in front. Terminate TLS at Caddy or nginx, forward to the application ports, and force HTTPS — dispatch data should never traverse plain HTTP, even inside a private network.

**Licence review is part of deployment.** Resgrid is Apache-2.0 (permissive, with patent grant), SnailyCAD is MIT, OpenCAD is GPL-3.0 (copyleft — modifications you distribute must carry the source). If your organisation distributes a modified platform to partner agencies, the GPL choice has consequences.

## FAQ

**Is it legal to run an open-source CAD system for a real fire department?**
Yes — nothing about dispatch software requires a certified commercial vendor, and Resgrid is Apache-2.0 licensed with no field-of-use restriction. What you must accept is the operational responsibility: you become the vendor, which means patching, backups, uptime and disaster recovery are yours. Many departments run self-hosted CAD for internal logistics and accountability while keeping a certified system for public-safety answering point obligations. Verify local regulatory requirements before replacing anything that touches emergency call handling.

**How much does self-hosting CAD actually cost compared to SaaS?**
Hosting only: a small VPS with 2 vCPU, 4 GB RAM and 50 GB SSD is enough to run any of the three for a single department, plus object storage for attachments and a backup target. The real cost is administrative time — budget a few hours a month for patching and verification. Against per-seat licensing for 60 responders, self-hosting usually wins within the first year; against a two-person department, it may not.

**Does Resgrid require Windows Server?**
No. The platform is ASP.NET Core, which runs on Linux, and the repository ships a Docker composition with supporting `run.sh` and `resgrid.env` files. Windows/IIS deployment is documented as an alternative, not a requirement.

**Can SnailyCAD run without Docker?**
Yes — the monorepo is a standard pnpm workspace with `apps/api` and `apps/client`, both of which can be built and run natively against an external PostgreSQL instance. Docker is simply the best-documented path, and the `.env.example` explicitly documents both Docker and standalone values for `DB_HOST`.

**Can these systems replace a commercial records management system?**
Partly. Resgrid includes run logs, reporting and exports designed for integration, and the API exposes call information. SnailyCAD models citizens, businesses, officers and records in its own schema. Neither provides certified RMS/NFIRS reporting out of the box, so most organisations pair a self-hosted CAD with an existing records workflow rather than replacing it outright. For the adjacent logistics layer, our [field service and logistics platform comparison](../2026-06-16-self-hosted-field-service-logistics-fleetbase-openboxes-traccar/) shows how inventory and dispatch data are usually joined.

**Which one should a new team start with?**
SnailyCAD v4 for a first self-hosted deployment — the production composition, the annotated `.env.example` and the reference documentation remove most of the guesswork, and PostgreSQL skills transfer directly. Move to Resgrid when your requirements grow into personnel certification, shift signups and responder mobile apps.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Computer-Aided Dispatch in 2026: Resgrid vs SnailyCAD vs OpenCAD Compared",
  "description": "A 2026 comparison of open-source computer-aided dispatch platforms: Resgrid, SnailyCAD v4 and OpenCAD, with verified Docker compositions, deployment steps, licensing and operational pitfalls.",
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
