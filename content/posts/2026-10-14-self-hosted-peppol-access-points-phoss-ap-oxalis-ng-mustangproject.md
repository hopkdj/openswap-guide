---
title: "Self-Hosted Peppol Access Points in 2026: phoss-AP vs Oxalis-NG vs Mustangproject"
date: "2026-10-14"
tags: ["peppol", "e-invoicing", "self-hosted", "b2b-compliance", "java"]
draft: false
cover: "/img/screenshots/mustangproject-zugferd-ui.jpg"
description: "Compare three open-source Peppol e-invoicing stacks — phoss-AP, Oxalis-NG and Mustangproject — with real Docker Compose configs, CLI commands and honest deployment caveats."
---

**Europe is quietly deleting the paper invoice.** Germany already requires every B2B supplier to be *able to receive* structured e-invoices, France's clearance mandate is rolling out, Belgium's B2B obligation starts in January 2026 and Poland's KSeF platform goes live in phases through 2026. If you run an ERP, an accounting tool, or an internal billing service, the question is no longer *whether* you need structured invoicing — it is whether you rent a SaaS access point forever or self-host the plumbing.

The good news: the open-source Peppol stack is now mature enough for production. The bad news: the three projects that matter sit at completely different layers, and picking the wrong one wastes weeks. This guide breaks down **phoss-AP**, **Oxalis-NG** and **Mustangproject** with real repository data, verified configs, and the certification caveats nobody mentions in their README.

## TL;DR / Quick Verdict

- **Want a working Peppol Access Point with a database and a UI, deployed this afternoon?** → **phoss-AP**. One Docker Compose file, PostgreSQL included, 8080 exposed. It is the fastest path from zero to an AS4 endpoint.
- **Building invoicing *logic* inside an existing Java application (validate, extract, generate, convert)?** → **Mustangproject**. The library does Factur-X, ZUGFeRD, UN/CEFACT CII and XRechnung, and the CLI lets you validate a folder of invoices in CI.
- **Migrating an established Norwegian/EU Peppol integration with an operations team that already knows it?** → **Oxalis-NG**. Battle-tested AS4 implementation, LGPL, standalone mode — but understand that classic Oxalis is frozen and only the NG fork gets new Peppol specifications.

**Blunt advice:** if you have never run an access point before, start with phoss-AP for transport and Mustangproject for invoice content. Oxalis-NG is excellent engineering, but its operational surface is bigger than most small teams need.

## Comparison Table: The Three Stacks Side by Side

Live data pulled from GitHub on 2026-10-14:

| Dimension | phoss-AP | Oxalis-NG | Mustangproject |
|---|---|---|---|
| Repository | `phax/phoss-ap` | `OxalisCommunity/oxalis-ng` | `ZUGFeRD/mustangproject` |
| GitHub stars | **54** | 51 | **481** |
| Last push | 2026-10-13 | 2026-10-04 | 2026-10-13 |
| Language | Java | Java | Java |
| License | Apache-2.0 | LGPL | Apache-2.0 |
| Layer in Peppol | Access Point (AS4 send/receive) | Access Point (AS4 send/receive) | Invoice content library + validator + CLI |
| Docker Compose in repo | ✅ `docker-compose.yml` (+ DB2 variant) | ❌ (Dockerfile, Makefile, CI publish workflows) | ❌ (Maven artifact / CLI JAR) |
| Database | PostgreSQL (or IBM DB2) | Configurable (JPA/Spring Boot) | None — stateless library |
| Web UI | ✅ built in | Minimal / API-first | ❌ CLI + library |
| Standalone CLI mode | ❌ | ✅ `oxalis-standalone` | ✅ `Mustang-CLI` |
| Formats | Peppol AS4 envelope | Peppol AS4 envelope | Factur-X, ZUGFeRD, CII, XRechnung, UBL |
| Best for | Fastest self-hosted AP | Mature AS4 integrations | Invoice generation & validation |

The star counts are small for all three — and that is normal for compliance infrastructure. Peppol software is boring by design; the market is a few thousand integrators, not a million hobbyists. Judge these projects by release cadence and specification coverage, not popularity.

## Decision Matrix: Pick Your Path in Ten Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| No Peppol presence yet, want a live AP today | **phoss-AP** | Complete Compose stack: PostgreSQL + AP + UI, 8080 |
| You also need to *produce* valid invoice XML | **Mustangproject** | Only one of the three that builds and validates invoice content |
| Validating thousands of legacy PDFs before migration | **Mustangproject CLI** | `--action validate --directory ./invoices` in CI |
| You already speak AS4 and need a library to embed | **phoss-AP** or **phase4** | Apache-2.0, embeddable, Peppol eDelivery support |
| Large integration with existing Oxalis ops runbooks | **Oxalis-NG** | Same operational model, current spec support |
| You need an SMP (registry) rather than an AP | **phoss-SMP** | Peppol/OASIS BDXR SMP server, EC eDelivery compliant |

## phoss-AP: The Fastest Way to a Working Access Point

`phax/phoss-ap` is the Apache-2.0 access point from Philip Helger, the same maintainer behind the widely used `phase4` AS4 library and the `phoss-smp` registry server. It is young (54 stars) but released continuously — the repository was updated on 2026-10-13, the same day as this article.

What makes it the pragmatic default is that the repository ships a complete deployment file. This is the actual `docker-compose.yml` from the project, trimmed to the essentials:

```yaml
services:
  postgres:
    image: postgres:latest
    restart: always
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: phoss-ap
      POSTGRES_USER: peppol
      POSTGRES_PASSWORD: peppol
    volumes:
      - pg18data:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U peppol -d phoss-ap"]
      interval: 5s
      timeout: 3s
      retries: 5

  phoss-ap:
    image: phelger/phoss-ap
    restart: always
    ports:
      - "8080:8080"
    environment:
      PHOSSAP_JDBC_URL: jdbc:postgresql://postgres:5432/phoss-ap
      PHOSSAP_JDBC_USER: peppol
      PHOSSAP_JDBC_PASSWORD: peppol
      PEPPOL_STAGE: test
      FORWARDING_MODE: http_post_async
      FORWARDING_HTTP_ENDPOINT: http://host.docker.internal:8888/forwarding
    volumes:
      - ap-data:/var/phoss-ap/data
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pg18data:
  ap-data:
```

Deploy it with two commands and you have a Peppol endpoint listening on port 8080:

```bash
git clone https://github.com/phax/phoss-ap.git
cd phoss-ap && docker compose up -d
docker compose logs -f phoss-ap
```

Three environment variables deserve attention before you point production traffic at it:

- **`PEPPOL_STAGE: test`** — you are running against the Peppol test network. Switch to production only after your access point certificate is issued and your SMP entry is registered.
- **`FORWARDING_MODE`** — `http_post_async` pushes inbound invoices to your ERP endpoint and returns immediately; synchronous modes make the sender wait on your internal system. Choose async unless you have strong delivery guarantees downstream.
- **`FORWARDING_HTTP_ENDPOINT`** — the outbound target. In the shipped file it points at `host.docker.internal:8888`, which is a demo receiver, not your ERP.

The repository also carries a `docker-compose.db2.yml` variant for teams standardised on IBM DB2 — a small signal that this project is aimed at enterprises with existing database policy, not just lab setups.

## Oxalis-NG: Mature AS4, With One Important Caveat

Oxalis is the elder statesman of Peppol. Originally written by SendRegning, maintained for years by the Norwegian Agency for Public Management and eGovernment (Difi) until March 2020, and now stewarded by the NorStella Oxalis Community, it is the reference open-source implementation of the OpenPeppol eDelivery AS4 specifications. The classic repository (`OxalisCommunity/oxalis`) has 150 stars and last shipped in April 2026.

That repository opens with a warning that every operator must read before committing:

> **Repository Status Notice — Further Development Frozen — Please Use Oxalis-NG.** No new features will be added. Bug fixes will be limited or not provided. This codebase will not support new Peppol specifications. Migrate to Oxalis-NG for continued support and updates.

So the decision is not "Oxalis or phoss-AP" — it is **Oxalis-NG or phoss-AP**. Oxalis-NG (51 stars, pushed 2026-10-04) is described as an open-source implementation of the OpenPeppol AS4 profile, carries the same LGPL licensing, and the same repository layout: `Dockerfile`, `Makefile`, and CI workflows named `build-docker.yml` and `publish-docker.yml`, meaning container images are produced by the project's own pipeline rather than hand-rolled by users.

Two operating modes are documented, and this is where Oxalis differs most from phoss-AP:

```bash
# Mode 1: embed as an API component
# Maven Central artifact: network.oxalis:oxalis

# Mode 2: standalone Peppol solution with a command-line sender
# oxalis-standalone persists inbound messages to the filesystem out of the box
git clone https://github.com/OxalisCommunity/oxalis-ng.git
cd oxalis-ng && mvn clean package
docker build -t oxalis-ng .
```

The filesystem persistence in standalone mode is a genuine operational advantage for compliance work: inbound invoices land as files you can archive, hash and replay, without writing application code first. The trade-off is that you own the retention policy, the disk alerts and the re-drive tooling.

## Mustangproject: Where the Invoice Actually Lives

Here is the part most "self-host an access point" guides skip. AS4 transport moves a payload from A to B. It says nothing about whether the payload is a valid invoice. **A Peppol access point will happily deliver malformed XML** — the receiving party's AP will accept it and their ERP will reject it, and you will spend a week reading rejection emails.

Mustangproject (481 stars, Apache-2.0, updated 2026-10-13) is the other half of the problem. It is a Java library plus a CLI that reads, writes and validates Factur-X, ZUGFeRD, UN/CEFACT CII, XRechnung and UBL invoice content.

The CLI options below come straight from the project's `Main.java` source (the `--action` list is verbatim), not from memory:

```bash
# Build the CLI once
git clone https://github.com/ZUGFeRD/mustangproject.git
cd mustangproject && mvn -pl Mustang-CLI package

# Validate a single invoice
java -jar Mustang-CLI.jar --action validate --source invoice.xml

# Extract the embedded XML from a hybrid PDF/A-3 invoice
java -jar Mustang-CLI.jar --action extract --source invoice.pdf --out invoice.xml

# Batch-validate a whole directory, no fatal-stop on the first bad file
java -jar Mustang-CLI.jar --action validate --directory ./invoices --format xml

# Check a ZUGFeRD 1 payload and ignore PDF/A attachment errors
java -jar Mustang-CLI.jar --action validate --source legacy.xml \
  --ignorefileextension --no-notices
```

The available actions are `metrics`, `combine`, `extract`, `a3only`, `ubl`, `validate`, `validateExpectInvalid`, `validateExpectValid` and `visualize`. The two `validateExpect*` actions are designed for test suites: they assert that a fixture is either broken or valid, which is exactly what you want in a CI pipeline that guards against regressions in your invoice generator. `--no-arithmetic-check` lets you skip line-item recalculation when you are validating third-party documents whose rounding you do not control, and `--profile` / `--version` pin the standard profile and version explicitly instead of trusting defaults.

Wire it into CI like this:

```bash
#!/usr/bin/env bash
set -euo pipefail
mvn -q -pl Mustang-CLI package
java -jar Mustang-CLI.jar --action validate --directory ./src/test/resources/invoices --no-notices
```

If a generated invoice stops matching the profile, the build fails before it ever reaches an access point.

## Supporting Pieces Worth Knowing

Three adjacent projects complete the picture:

| Project | Stars | Role |
|---|---|---|
| `phax/phase4` | 242 | AS4 client and server library, Peppol and CEF eDelivery support |
| `phax/phoss-smp` | 210 | Peppol / OASIS BDXR SMP server, EC eDelivery compliant |
| `OpenPeppol/peppol-bis-invoice-3` | 155 | The BIS Billing 3.0 specification artefacts themselves |

If you plan to run both a registry and an access point internally — common in closed supplier networks — `phoss-smp` plus `phoss-ap` is a consistent Apache-2.0 pairing from a single maintainer, which simplifies upgrades.

![ZUGFeRD and mustang invoice validation in practice](/img/screenshots/mustangproject-zugferd-ui.jpg "ZUGFeRD validator output produced by the mustang project toolchain")

## Pitfalls and Migration Notes

**1. Self-hosting the software is not the same as being allowed to exchange invoices.** Peppol is a governed network. You need an access point certificate from a Peppol Authority-approved PKI provider, you need your participant identifier registered in an SMP, and in most jurisdictions you need to prove identity of the legal entity. Budget for a certificate fee and a registration step; there is no open-source shortcut around either. Plan this *first* — it is the long-lead item, not the Docker container.

**2. Port 8080 must be reachable over public HTTPS with a valid certificate.** AS4 is point-to-point and the counterparty's access point initiates the connection. Behind a reverse proxy, verify that the full AS4 endpoint path is preserved and that request bodies are not buffered to a size limit.

**3. Test and production are separate Peppol networks with separate certificates.** Nearly every failed first integration I have seen came from mixing the stages: a production certificate pointed at the test SMP, or `PEPPOL_STAGE: test` left in a production compose file. Make the stage an explicit environment variable that fails loudly when unset.

**4. Do not migrate to classic Oxalis in 2026.** The frozen-repository notice means new Peppol specification releases will not be implemented there. Go straight to Oxalis-NG.

**5. Async forwarding shifts the failure mode rather than removing it.** With `http_post_async`, inbound invoices are acknowledged before your ERP accepts them. You must build a dead-letter path and monitor it — otherwise invoices silently disappear at the seam between the access point and your accounting system.

**6. Validate content, not just transport.** Keep Mustangproject validation in CI. A transport-level green light is not evidence that the XML satisfies the receiver's profile.

## Why Self-Host Your E-Invoicing Gateway?

The honest argument for self-hosting is not licence cost — commercial access points are not expensive. It is **data residency and continuity of evidence**. An invoice is a tax document: it must be retrievable, verifiable and reproducible years later, often under audit. When the transport layer and the archive live in your own infrastructure, the chain from received AS4 payload to archived XML to ERP journal entry stays inside your boundary and inside your backup policy.

The second argument is integration depth. When you control the access point, forwarding modes, retry queues and validation profile are yours to shape. You can reject a malformed invoice at the door instead of discovering it in month-end reconciliation.

The third is cost structure at volume. Rent scales with documents; self-hosting scales with servers. A busy supplier billing tens of thousands of invoices a month crosses that line quickly.

For related reading, our [self-hosted ERP and procurement comparison](../2026-06-05-self-hosted-erp-procurement-axelor-idempiere-metasfresh-guide/) covers the systems these invoices land in, the [document automation guide](../2026-05-03-docassemble-vs-docxtemplater-vs-pandoc-self-hosted-document-automation-guide/) explains how invoices get generated from templates in the first place, and the [data contract validation walkthrough](../2026-05-09-self-hosted-data-contract-validation-soda-dbtspec-datacontract-cli-guide/) is worth reading if you want the same build-time validation discipline for other structured payloads. If your pipeline touches PDFs before they become invoices, see our [PDF processing comparison](../2026-05-02-stirling-pdf-vs-gotenberg-vs-ocrmypdf-self-hosted-pdf-processing-guide/).

## FAQ

**Do I need a commercial Peppol access point to send invoices in the EU?**
No, but you need more than software. Self-hosting gives you the technical endpoint; Peppol compliance additionally requires an access point certificate from an approved PKI provider, registration of your participant identifier in an SMP, and identity verification of the legal entity. Budget days for the registration, not minutes.

**What is the difference between an access point and an SMP?**
An access point sends and receives invoice documents over AS4. An SMP (Service Metadata Publisher) is the registry that tells the network which access point handles a given participant identifier and which document profiles they support. For a self-hosted registry, `phoss-smp` is the Apache-2.0 option; `phoss-ap` covers the access point role.

**Can I use Mustangproject without running any access point?**
Yes, and many teams do. Mustangproject validates and generates invoice content as a plain library or CLI. It is common to generate and validate invoices internally with Mustangproject while delegating AS4 transport to a commercial provider — the content discipline is independent of the transport.

**Is classic Oxalis still safe to run in production?**
It works, but the maintainers have frozen development on it and state that it will not support new Peppol specifications. Running it means accepting that future spec releases require a migration. New deployments should start on Oxalis-NG.

**How do I validate thousands of invoices quickly?**
Use the Mustangproject CLI in directory mode (`--action validate --directory ./invoices`). It walks the tree, reports per-file results and supports `--ignorefileextension` plus `--no-notices` to suppress non-fatal noise. Run it in CI on every generated invoice so profile regressions fail the build rather than the customer.

**Does self-hosting remove per-invoice fees?**
It removes per-invoice software fees from your vendor, but it does not remove certificate costs, registration costs, hosting and the operations time to monitor an endpoint that counterparties depend on. Run the arithmetic for your actual monthly volume before assuming self-hosting is cheaper.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Peppol Access Points in 2026: phoss-AP vs Oxalis-NG vs Mustangproject",
  "description": "Compare three open-source Peppol e-invoicing stacks with real Docker Compose configs, CLI commands and honest deployment caveats.",
  "datePublished": "2026-10-14",
  "dateModified": "2026-10-14",
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
