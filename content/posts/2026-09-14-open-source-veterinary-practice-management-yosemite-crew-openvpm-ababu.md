---
title: "The Definitive Guide to Open-Source Veterinary Practice Management in 2026: Yosemite Crew vs OpenVPM vs Ababu"
date: "2026-09-14"
description: "Yosemite Crew vs OpenVPM vs Ababu compared for 2026 — architecture, Docker Compose deployment, PostgreSQL row-level security, and real clinic migration pitfalls for self-hosted veterinary PIMS software."
tags: ["veterinary", "practice-management", "self-hosted", "postgresql", "healthcare"]
draft: false
cover: "/img/screenshots/yosemite-crew-dashboard.jpg"
---

Most veterinary clinics in 2026 are running one of two things: a decades-old desktop application that only works on the front-desk Windows machine, or a per-seat cloud platform that charges every month and holds your patient records hostage. Neither option is acceptable when you are the one legally responsible for those medical records.

The open-source veterinary practice management market has quietly become real. **Yosemite Crew has 2,021 stars and shipped a commit within the last day.** **OpenVPM is an AGPL-3.0, API-first system with genuine PostgreSQL row-level security.** **Ababu is a PHP and MariaDB system that has been quietly serving clinics for years.** This guide compares all three with architecture details and deployment commands pulled from their repositories, not from memory.

## TL;DR — The Quick Verdict

**Pick Yosemite Crew if you want the most complete, most actively developed system** — it is the only one of the three with a web client, a native mobile app for pet owners, and a desktop shell all sharing one API and one database schema. **Pick OpenVPM if you care most about auditability and integration**: it is AGPL-3.0, it enforces per-tenant isolation at the database level with row-level security policies, and it ships a versioned REST API with signed webhooks. **Pick Ababu if you want the smallest possible footprint** — PHP and MariaDB on one machine, no Node.js toolchain, no monorepo build step, and it still runs fine on modest hardware.

One honest caveat before you go further: **none of these systems removes your compliance obligations.** Controlled-substance logging, record retention, and local veterinary board rules are yours to satisfy regardless of which platform you deploy.

## The Three Systems Compared

All star counts, licenses, languages, and commit dates below were read from GitHub in September 2026.

| | Yosemite Crew | OpenVPM | Ababu |
|---|---|---|---|
| **Repository** | `YosemiteCrew/Yosemite-Crew` | `evangauer/openvpm` | `oldauntie/ababu` |
| **GitHub stars** | **2,021** | 29 | 26 |
| **License** | Custom OSS license (review before commercial use) | **AGPL-3.0** | **AGPL-3.0** |
| **Backend** | Express 4 on TypeScript | Next.js 15 API routes + tRPC + REST v1 | PHP (Laravel/Blade) |
| **Frontend** | Next.js 15, React 19, Zustand | Next.js 15 App Router, shadcn/ui, Radix, Tailwind | Server-rendered Blade views |
| **Database** | Supabase PostgreSQL via Prisma | **PostgreSQL 16 + Drizzle ORM** | **MariaDB** |
| **Multi-tenant isolation** | Postgres **schema per tenant** | PostgreSQL **row-level security policies** | Separate deployment per clinic |
| **Clients** | Web + React Native mobile + Electron desktop | Web + client portal | Web / desktop |
| **Background jobs** | BullMQ workers, Socket.IO realtime | Signed webhook delivery | — |
| **File storage** | Application-managed | S3-compatible / MinIO | Filesystem |
| **Docker Compose included** | **Yes** (`docker-compose.yml`) | **Yes** (`docker/docker-compose.yml`) | No (LAMP-style install) |
| **Last commit** | **Sep 13, 2026** | **Sep 13, 2026** | Mar 2025 |
| **Best for** | Clinics wanting a modern full-stack PIMS | Teams needing API access and auditable isolation | Small clinics wanting minimal infrastructure |

The gap between **2,021 stars and 29 stars** is misleading in one direction and meaningful in another. Yosemite Crew has vastly more development momentum — an entire monorepo with web, mobile, desktop, architecture decision records, and SonarQube quality gates. OpenVPM is smaller but has the more rigorous data-isolation design on paper, and it is the only one shipping database-enforced tenant boundaries. Stars measure attention; architecture measures whether your records are safe.

## Decision Matrix: Pick Your Platform in 10 Seconds

| Your situation | Platform | Why |
|---|---|---|
| Multi-doctor clinic, want mobile access for pet owners | **Yosemite Crew** | Only option here with a native mobile client |
| You need to build integrations on a versioned REST API | **OpenVPM** | `/api/v1` with signed webhooks and scoped API keys |
| Single clinic, one server, minimal maintenance | **Ababu** | PHP + MariaDB, no build toolchain required |
| You must prove database-level tenant separation to an auditor | **OpenVPM** | PostgreSQL row-level security with a least-privilege role |
| You want the fastest-moving project | **Yosemite Crew** | Daily commits, biggest contributor base |
| Hosting for several clinics on one deployment | **Yosemite Crew** | Schema-per-tenant isolation rather than one app per clinic |
| Controlled-substance inventory tracking | **OpenVPM** or **Yosemite Crew** | Both document lot linkage and audit trails |
| Old hardware, no Node.js experience on staff | **Ababu** | Lowest technical barrier of the three |

## Yosemite Crew — Four Clients, One API, One Source of Truth

Yosemite Crew describes itself as an "open-source operating system for animal health," and the architecture is the most interesting thing about it. The repository's own framing is direct: **"Four clients, one API, one source of truth. Every product in the repo speaks to the same Express service and the same Postgres schema."**

![Yosemite Crew desktop application dashboard — official project screenshot](/img/screenshots/yosemite-crew-dashboard.jpg "Yosemite Crew desktop PIMS dashboard")

That gives you this shape:

- **Web PIMS** — Next.js 15, React 19, Zustand, Storybook, with Playwright end-to-end and accessibility suites
- **Mobile app** (`apps/mobileAppYC`) — React Native 0.81, Redux, i18next localization, Detox end-to-end tests
- **Desktop shell** (`apps/desktop`) — Electron, packaged with electron-builder, notarized, with auto-update
- **Backend API** (`apps/backend`) — Express 4 on TypeScript, Prisma, Socket.IO for realtime, BullMQ workers, Stripe

The critical design decision, documented as **ADR 0001 — Postgres and Prisma as source of truth**: tenant data is isolated by **Postgres schema**, not by a filter column. The repository states the reasoning plainly: schema-level isolation means "one clinic's records cannot leak into another's through a forgotten `WHERE`." If you have ever audited a multi-tenant application that relied on developers remembering a tenant filter, you know exactly why this matters.

The whole thing is a **pnpm + Turborepo workspace**, which means installing and running it is standardized:

```bash
# Prerequisites: Node.js 20 (see .nvmrc) and pnpm 8
pnpm install                     # Git hooks install automatically (Husky, commitlint, secret scanning)

# The backend needs a reachable PostgreSQL database on boot
# and Redis for the background job queues
pnpm run dev --filter frontend   # web app only
pnpm run dev --filter backend    # API only
pnpm run dev                     # website + api together

pnpm run verify                  # lint + type-check + test + build
```

For container deployment, the repo ships a `docker-compose.yml` that builds the website and API as separate services on a shared bridge network:

```yaml
services:
  website:
    build:
      context: .
      dockerfile: apps/website/Dockerfile
    ports:
      - "5173:5173"
    depends_on:
      - api
    networks:
      - app-network

  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    ports:
      - "3000:3000"
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

**Where it falls down:** the license is a custom OSS license rather than a standard SPDX identifier, so read it before you build a business on it. It also brings the heaviest stack of the three — Node 20, pnpm, Turborepo, PostgreSQL, **and Redis** — so a single small clinic server needs to be reasonably sized.

## OpenVPM — API-First With Database-Enforced Isolation

OpenVPM is AGPL-3.0, describes itself as "cloud-native but self-hostable," and was updated on the same day as Yosemite Crew. Its stack is modern and, for a self-hosted project, unusually disciplined:

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, React 19 |
| UI | shadcn/ui + Radix UI + Tailwind CSS |
| API | tRPC dashboard API **plus a versioned `/api/v1` REST API** |
| Database | **PostgreSQL 16 + Drizzle ORM** |
| Auth | NextAuth.js, role-based access, optional TOTP multi-factor, recovery codes |
| Events | Signed webhook delivery for integrations |
| Payments | Stripe |
| File storage | S3-compatible or MinIO for self-hosted |
| Monorepo | Turborepo + pnpm workspaces |
| Deployment | **Docker Compose (self-host)** or Vercel (cloud) |

![OpenVPM clinic dashboard with metrics, follow-up queue, and upcoming appointments](/img/screenshots/openvpm-clinic-dashboard.jpg "OpenVPM veterinary PIMS dashboard")

The self-hosting story is more rigorous than most. The Compose stack lives under `docker/` and brings up **PostgreSQL 16 with health checks and MinIO for S3-compatible file storage**, plus a one-shot bootstrap container that creates the required bucket. The documented quick start is:

```bash
# Prerequisites: Node.js 20+, pnpm 9+, Docker
git clone <repo-url>
cp .env.example .env

# Start local PostgreSQL and MinIO dependencies
docker compose -f docker/docker-compose.yml up -d postgres minio minio-bootstrap

pnpm install --frozen-lockfile
pnpm verify:oss-release     # confirm this clone contains only public release material
pnpm db:migrate             # apply committed migrations

# Apply and verify row-level security policies
OPENPIMS_APP_DB_PASSWORD='local-openpims-app' pnpm db:rls
OPENPIMS_APP_DB_PASSWORD='local-openpims-app' pnpm db:rls:test

pnpm db:seed                # realistic demo practice data
pnpm dev
```

**That `db:rls` step is the differentiator.** OpenVPM applies PostgreSQL row-level security policies and verifies them with a dedicated test command, then expects production deployments to point the application at a **least-privilege `openpims_app` database role**. In other words, tenant isolation is enforced by the database engine, not by application code. For anyone whose audit requirements include proving separation of clinic data, that is a materially stronger story than a `WHERE tenant_id = ?` convention.

The clinical feature set is substantially complete for a project this size: **patient and client management** with weight-history trend charts, microchip tracking, and allergy alerts; **scheduling** with column-per-doctor views and conflict detection; **SOAP-note EMR** with problem lists, vaccination certificates, lab result reference ranges, and prescription dosing calculators; **billing and invoicing** with estimates converting to invoices and payment tracking; **inventory** with lot/batch tracking and expiry dates; and **controlled-substance logging** with patient and lot linkage, running balances, waste-witness fields, and full audit trails.

On the integration side, the versioned `/api/v1` REST API comes with API reference documentation, a webhook system for events like appointment created, patient checked in, and invoice paid, API key management with scopes, rate limiting, and audit logging. The project also publishes a **Clinic Pilot Readiness Guide** that separates supported, configuration-dependent, and not-yet-supported capabilities — a refreshingly honest document, and the first thing you should read before committing real clinic data.

**Where it falls down:** only 29 stars means a small contributor pool, so you should expect to fix some of your own problems. AGPL-3.0 is also a real consideration if you plan to offer it as a hosted service. And several delivery services — email, hosted SMS — require external provider configuration rather than working out of the box.

## Ababu — The Minimalist Option That Still Runs

Ababu is a different philosophy entirely. It is **written in PHP and stores data in MariaDB**, it is AGPL-3.0 licensed, and its own description positions it as a "problem oriented, open source multi-platform veterinary practice management software."

The repository is explicit that it "can run on a single computer, in a local network (e.g., a veterinary clinic) or on a cloud computing (over the internet)." That is the entire pitch, and for a two-vet practice with a receptionist and a Linux box, it is a good pitch. There is no Node.js, no pnpm, no Turborepo, no Redis, and no container orchestration.

The trade-offs are equally clear: the last commit was in **March 2025**, so you are adopting a slower-moving project. There is no bundled Docker Compose configuration. The README notes that setup programs were still pending on the official website, which means you are deploying from source. And the feature set is narrower than the two TypeScript projects above.

If you have PHP experience on staff and want to be running this afternoon, Ababu is the shortest path. If you need mobile clients, webhooks, or documented API integrations, it is not the right tool.

## The Wider Landscape — And Why Most Options Are Dead

The veterinary open-source ecosystem is small, and a lot of it is abandoned. Before you commit, know what you are looking at:

| Project | Status | Reality |
|---|---|---|
| **OpenVPMS** | Active project, stale GitHub mirrors | The long-running Java-based PIMS has its own site, but the GitHub forks and mirrors stop around 2019 |
| `carlosribas/medvet` | Last commit **Feb 2023** | PHP/JavaScript system vets; treat as archived |
| `aarkerio/vet4pet` | Last commit **2016** | Rails + ReactJS + Redux clinic manager; effectively dead |
| `oldauntie/ababu` | Last commit **Mar 2025** | Still maintained, but slow-moving |
| `YosemiteCrew/Yosemite-Crew` | Commit **Sep 13, 2026** | Fast-moving, largest contributor base |
| `evangauer/openvpm` | Commit **Sep 13, 2026** | Fast-moving, AGPL-3.0, API-first |

**The pattern worth internalizing:** two projects are actively developed and both are TypeScript monorepos. Everything else in the category either has stale mirrors or has stopped shipping. If you are choosing a platform to run a real clinic on for five years, that distribution matters more than any feature table.

## Pitfalls and Migration Gotchas

**1. Never test on live clinic data.** OpenVPM's own documentation includes a Clinic Pilot Readiness Guide for exactly this reason. Stand up the system, seed the demo practice, run your workflows, and only then begin a parallel-run migration. Both fast-moving projects here ship demo seed data — use it.

**2. Controlled-substance compliance is yours, not the software's.** OpenVPM documents controlled-substance logging with lot linkage, running balances, and waste-witness fields, and then says outright that practices should validate the configured workflow against their own federal, state, and local procedures. That sentence is the most important line in either repository. Confirm your obligations with your regulator and your veterinary board before you change anything.

**3. Read the license before you build a business on it.** Ababu and OpenVPM are AGPL-3.0 — if you host a modified version as a service for other clinics, the network copyleft clause applies. Yosemite Crew uses a custom OSS license that is not a standard SPDX identifier. Neither is a reason to avoid the software, but both are reasons to read the actual text first.

**4. Verify tenant isolation yourself.** Yosemite Crew isolates by Postgres schema; OpenVPM isolates with row-level security policies. Both are defensible designs, and neither is a substitute for testing. After deployment, create two test clinics, insert records in both, and confirm from the application that neither can read the other's data.

**5. Do not skip the background infrastructure.** Yosemite Crew's backend requires **both PostgreSQL and Redis** on boot. Not having Redis running produces confusing startup failures. OpenVPM requires PostgreSQL plus an S3-compatible store, with MinIO providing it in the bundled Compose stack — and its bootstrap container creates the `openpims` bucket. If you swap in external S3 storage, you must create the bucket yourself and grant read, write, delete, and head permissions.

**6. Migration from a legacy desktop PIMS is a data project, not an install.** Patient records, weight histories, vaccination dates, and invoice line items rarely map cleanly. Budget more time for extraction and validation than for the deployment itself, and keep the old system readable for at least one full billing cycle.

**7. Back up the database and the object store together.** Clinical records increasingly live in two places: rows in PostgreSQL and images or documents in S3 or MinIO. A database-only backup gives you patient records with broken attachments.

If you run other self-hosted business software, this fits the same operating model. Our [self-hosted CRM comparison](../2026-05-07-monica-vs-espocrm-vs-suitecrm-self-hosted-crm-guide/) covers the client-records side of the stack, the [appointment scheduling comparison](../2026-05-13-calcom-vs-easyappointments-vs-rallly-self-hosted-scheduling-guide/) covers booking systems if you want something lighter than a full PIMS, and the [self-hosted billing comparison](../2026-05-03-fossbilling-vs-paymenter-vs-solidinvoice-self-hosted-billing-guide/) covers invoicing and subscriptions when client billing goes beyond in-clinic invoices.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "The Definitive Guide to Open-Source Veterinary Practice Management in 2026: Yosemite Crew vs OpenVPM vs Ababu",
  "description": "Yosemite Crew vs OpenVPM vs Ababu compared for 2026 — architecture, Docker Compose deployment, PostgreSQL row-level security, and real clinic migration pitfalls for self-hosted veterinary PIMS software.",
  "datePublished": "2026-09-14",
  "dateModified": "2026-09-14",
  "keywords": "veterinary practice management, open source PIMS, Yosemite Crew, OpenVPM, Ababu, self-hosted clinic software",
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

### Is there a genuinely production-ready open-source veterinary PIMS?

Yes, with an important qualifier. **Yosemite Crew** and **OpenVPM** were both updated on September 13, 2026, both ship Docker Compose configurations, and both implement deliberate multi-tenant data isolation — schema-per-tenant and PostgreSQL row-level security respectively. That combination of active development plus an explicit isolation design is what makes them suitable for real clinics. What none of them removes is your own compliance responsibility for controlled substances, record retention, and local veterinary board rules.

### How do I deploy a veterinary PIMS with Docker Compose?

Both leading options include a Compose file. Yosemite Crew ships `docker-compose.yml` at the repository root, building the website on port 5173 and the API on port 3000. OpenVPM ships `docker/docker-compose.yml`, which brings up PostgreSQL 16 with health checks, MinIO for S3-compatible storage, and a one-shot bootstrap container that creates the required bucket. Run `docker compose -f docker/docker-compose.yml up -d`, then apply database migrations before serving traffic. Yosemite Crew additionally requires Redis for its background job queues.

### What is the difference between schema-per-tenant and row-level security isolation?

Schema-per-tenant gives each clinic its own PostgreSQL schema, so queries issued in one tenant's context physically cannot address another tenant's tables — Yosemite Crew's stated rationale is that one clinic's records cannot leak through a forgotten `WHERE` clause. Row-level security keeps one shared schema but attaches policies that the database engine enforces per row, which is what OpenVPM implements and verifies with a dedicated test command. Both are stronger than application-level filtering, and both should still be verified by you after deployment.

### Can I migrate my existing clinic records into an open-source PIMS?

Yes, but treat it as a data engineering project rather than a feature of the software. Patient records, weight histories, vaccination schedules, and invoice line items rarely map one-to-one, and older desktop systems frequently store history in formats that need extraction work. The practical sequence is: deploy the new system on a non-production server, seed and explore the demo data, build and validate an import for a single sample clinic, then run both systems in parallel for a billing cycle before switching.

### Which open-source PIMS is best for a small single-vet practice?

**Ababu** is usually the right answer for the smallest practices, because it needs only PHP and MariaDB and can run on one computer or a local network with no container platform, no Node.js, and no Redis. The trade-off is a slower release cadence — the last commit was March 2025 — and a narrower feature set than the TypeScript projects. If you expect to grow to multiple vets, add a client portal, or build integrations, start with Yosemite Crew or OpenVPM instead and accept the heavier infrastructure.

### Are these platforms multi-tenant, or do I need one deployment per clinic?

Yosemite Crew and OpenVPM are both designed to host multiple clinics, using schema-per-tenant and row-level security respectively. Ababu is oriented toward a single clinic per deployment, which is a simpler and often safer operational model if you only run one practice. Multi-tenant operation concentrates risk: a policy mistake or an isolation bug affects every clinic you host. If you host for multiple practices, test isolation explicitly with two real tenant accounts before trusting it with live records.

### Does open-source veterinary software include billing and inventory?

Both Yosemite Crew and OpenVPM implement billing and inventory. OpenVPM documents structured visit closeout, treatment templates that populate draft invoices, itemized line items, tax calculation, estimates that convert into invoices, payment tracking, account balances, and revenue reporting, plus inventory with stock levels, reorder alerts, lot and batch tracking, and expiration dates. Yosemite Crew's backend includes Stripe integration for payments. Ababu covers the clinical and front-desk basics but is narrower on financial reporting.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
