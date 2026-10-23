---
title: "Koha vs Evergreen vs FOLIO in 2026: Choosing an Open-Source Library System That Survives Year Three"
date: "2026-10-24"
tags: ["library-systems", "koha", "evergreen", "folio", "ils", "self-hosted", "postgresql"]
draft: false
cover: "/img/screenshots/koha-ils-dashboard.jpg"
description: "Koha, Evergreen and FOLIO compared on architecture, deployment cost, circulation workflows and the migration traps that only appear after go-live."
---

Most library system comparisons are written by people who have installed the software once, on a laptop, with a demo dataset. That is not where library systems fail. They fail in year three, when your consortium has 1.2 million bibliographic records, 40 000 active patrons, a nightly MARC import from three vendors, and a circulation desk that cannot be offline for a Saturday.

Koha, Evergreen and FOLIO are the three open-source systems that actually run production libraries in 2026. They are not three flavours of the same thing: one is a mature monolith with a giant partner network, one is a consortium-first platform built for resource sharing, and one is a microservices platform that looks like a cloud-native application because it *is* one. Choosing wrong is a five-year decision with a migration attached to both ends.

## TL;DR / Quick Verdict

- **Choose Koha** if you are a single library or a small consortium that wants the widest hosting choice, the largest install base, and the shortest path from download to a working OPAC. It is the safest default and the easiest to hire for.
- **Choose Evergreen** if resource sharing between branches is the core requirement — consortia with rotating collections, transiting items, and shared patron records. Its OpenSRF architecture was designed for exactly that, and it shows.
- **Choose FOLIO** only if you have platform engineering capacity. It brings Okapi, Kafka, PostgreSQL and a search cluster together into a genuinely modern system, but a two-person IT team will spend more time operating FOLIO than librarians will spend using it.
- **Do not choose on features alone.** All three do circulation, cataloguing, acquisitions, serials and an OPAC. The differentiator is operational surface area, and that is proportional to how many moving parts you must babysit.

## The Three Systems at a Glance

Repository data pulled at publish time:

| Dimension | Koha | Evergreen | FOLIO |
|---|---|---|---|
| GitHub stars | 595 (synced mirror) | 157 | 134 (Okapi gateway) |
| Last commit | 2026-10-23 | 2026-10-22 | 2026-10-20 |
| License | GPL-3.0 | GPL-2.0 | Apache-2.0 |
| Core stack | Perl, PostgreSQL, Apache/Plack | Perl, C (OpenSRF), PostgreSQL | Java (Okapi modules), PostgreSQL, Kafka, OpenSearch |
| Staff interface | Web (intranet) | Web (Angular) | Web (Stripes) |
| OPAC | OPAC + Bootstrap themes | TPAC | Discovery via Stripes / third party |
| Search engine | Zebra or Elasticsearch | PostgreSQL + Evergreen search | OpenSearch / Elasticsearch |
| Multi-tenant | `koha-create` per instance | Native consortium model | Tenant per deployment |
| Typical install effort | Hours | Days | Days to weeks |
| Hosting partners | Very broad | Moderate | Growing, mostly enterprise |

Star counts understate the picture badly. Koha's GitHub repository is a *mirror* of a project whose real history lives in its own bug tracker; FOLIO is dozens of repositories, of which Okapi is only the gateway. Treat the numbers as an activity signal, not a popularity contest.

## Decision Matrix

| Requirement | Recommended | Reason |
|---|---|---|
| Single public library, small IT team | Koha | One package install, one database, mature upgrade path |
| Regional consortium with inter-library lending | Evergreen | Native transit, hold targeting and shared patron model |
| University system moving to cloud-native ops | FOLIO | Microservices, container deployment, Kafka-based eventing |
| Lowest total cost of ownership | Koha | Fewest services to run, widest hosting market |
| Existing Elasticsearch/OpenSearch expertise | Koha (ES) or FOLIO | Both support clustered search backends |
| Strictly on-premises, air-gapped | Koha or Evergreen | FOLIO's multi-service footprint complicates offline installs |
| Needs Arabic/Hebrew/CJK cataloguing out of the box | Koha | Long-standing RTL and multi-script support in both interfaces |
| Vendor support contract required | All three | Commercial support exists for each, but Koha's ecosystem is largest |

## Koha — The Pragmatic Monolith

Koha is the system most libraries end up with, and for unglamorous reasons: it installs from packages, it upgrades predictably, and every library vendor in your country can support it. The architecture is a Perl application behind Plack, storing everything in PostgreSQL, with Zebra or Elasticsearch for search.

The canonical Debian install is genuinely short:

```bash
# Official Koha Debian repository
wget -qO - https://debian.koha-community.org/koha/gpg.asc \
  | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/koha.gpg
echo "deb http://debian.koha-community.org/koha stable main" \
  | sudo tee /etc/apt/sources.list.d/koha.list
sudo apt update
sudo apt install -y koha-common

# One database + one instance per library
sudo koha-create --create-db mainlib
sudo koha-plack --enable mainlib
sudo koha-plack --start mainlib
```

That produces a working staff interface and OPAC on the same host. Instance isolation is a first-class concept: `koha-create` builds a separate database, a separate Apache virtual host, and a separate configuration directory per library, which is exactly what a small consortium needs without a container platform.

**Where Koha wins:**

- **Operational simplicity.** One application, one database, one search daemon. Backups are `koha-dump` plus a filesystem snapshot.
- **Support market.** Hosting providers, migration specialists and paid support are everywhere, which matters more than any feature list when your cataloguer retires.
- **Multi-script cataloguing.** Arabic, Hebrew, Cyrillic and CJK records work in the staff interface without custom theming.
- **Upgrade cadence.** Monthly maintenance releases and predictable annual feature releases; the community documents schema changes per version.

**Where it hurts:**

- **Zebra is showing its age.** Legacy installs still run Zebra as the default search daemon. Elasticsearch gives better relevance and faceting but doubles the operational surface — plan for it from day one rather than bolting it on in year two.
- **Perl is a hiring filter.** Developers exist, but not in the numbers you get for Python or Go. Budget for vendor support if you need custom reports.
- **Consortium features are bolted on.** Koha handles multi-branch well, but true rotating-collection resource sharing across independent legal entities is not its strength.

## Evergreen — Built for Consortia

Evergreen comes out of the Georgia Public Library Service and it carries that DNA everywhere: OpenSRF messaging between services, PostgreSQL as the system of record, and a data model that assumes multiple libraries share one patron database and transit items between buildings.

```bash
# Build prerequisites on Debian/Ubuntu, then the app itself
sudo make -f Open-ILS/src/extras/Makefile.install debian-bookworm

git clone https://github.com/evergreen-library-system/Evergreen.git
cd Evergreen
./autogen.sh
./configure --prefix=/openils --sysconfdir=/openils/conf
make && sudo make install

# OpenSRF is a separate stack and must be running first
# (perl services + Ejabberd for message routing), then:
sudo systemctl enable --now opensrf
sudo systemctl enable --now evergreen
```

The install is honest about its complexity: you are deploying a messaging fabric (OpenSRF, historically riding on Ejabberd), a Perl application layer, Apache with the TPAC OPAC, and PostgreSQL with a schema that dwarfs a typical web app. Expect a day of work for a skilled admin, and expect to read the install documentation twice.

**Where Evergreen wins:**

- **Consortium model first.** Shared patron records, hold targeting across branches, item transit and org-unit hierarchies are native data structures rather than configuration hacks.
- **Proven at state scale.** Deployments serving hundreds of branches exist; the architecture was stress-tested by public library systems with millions of circulations per year.
- **Predictable performance profile.** PostgreSQL does the heavy lifting; there is no second search cluster to keep in sync unless you add one.
- **Angular staff client.** Modern browser-based staff interface, with the legacy XUL client retired.

**Where it hurts:**

- **Smaller ecosystem.** Fewer hosting partners than Koha means your options for outsourced operations are narrower, and hiring Evergreen-specific skills is harder.
- **OpenSRF is unusual.** Developers who have never met an XMPP-based service bus will need time; debugging a stuck request means understanding the message layer.
- **Documentation quality varies.** Core install and upgrade docs are solid; edge-case configuration is often answered in mailing list archives.
- **Upgrade discipline required.** Schema migrations are substantial. Skip two major versions and you are in for a long weekend.

## FOLIO — A Library Platform, Not a Library App

FOLIO is what happens when a library system is designed in the Kubernetes era. Okapi is the gateway; behind it sit independent modules (mod-inventory, mod-circulation, mod-orders, mod-users) that talk over Kafka, store state in PostgreSQL, and index into OpenSearch. The staff interface is Stripes, a React application.

FOLIO's own installation runbooks make the shape of the project clear — a single-server path and a Kubernetes path, both driven by configuration management:

```bash
git clone https://github.com/folio-org/folio-install.git
cd folio-install/runbooks/single-server

# The single-server runbook provisions the full stack
# (PostgreSQL, Kafka, OpenSearch, Okapi, Stripes) via Vagrant + Ansible
vagrant up
```

For production, the `alternative-install` directory carries Kubernetes instructions (including Rancher-based deployments). Real deployments typically run 15–30 containers before you count monitoring.

**Where FOLIO wins:**

- **Genuine modularity.** Modules upgrade independently. Swap the acquisitions module or write your own without forking a monolith.
- **Event-driven integration.** Kafka means external systems (campus ERP, discovery layers, identity providers) can subscribe to library events instead of polling a database.
- **Cloud-native operations.** Health endpoints, container images and declarative deployment are the default rather than an afterthought.
- **Apache-2.0 licensing.** Friendlier for institutions that want to embed components in commercial or mixed-license systems.

**Where it hurts:**

- **Operational weight.** Kafka, OpenSearch, PostgreSQL and a service mesh of Java modules must all be healthy before a librarian can check out a book. Your on-call rotation now includes distributed systems.
- **Sizing is not optional.** Under-provisioned Kafka or OpenSearch turns circulation into a latency problem during peak desk hours. Budget real memory, not a VM with 8 GB.
- **Migration is a project, not a task.** Moving from a legacy ILS to FOLIO means data mapping across modules, and the tooling assumes an implementation partner.
- **Small-team mismatch.** If nobody on staff has run Kubernetes or Kafka in production, the platform will outrun the team.

## Migration Traps Nobody Warns You About

- **MARC data is the easy part.** Every system imports MARC. What breaks is local practice: item statuses, loan rules, fine calculations and hold queues that were encoded as customisations in your old system.
- **Patron records carry history.** Blocks, expiry dates, privacy flags. Export patron data early and reconcile counts before cutover weekend, not during it.
- **Search relevance changes overnight.** Barcode-scanning workflows depend on exact-match ordering. Test your top 50 real searches — not the demo data — on the new system.
- **Serials and acquisitions are where projects slip.** Prediction patterns, subscription renewals and vendor EDIFACT feeds rarely migrate cleanly. Run one full renewal cycle in parallel if you can.
- **Printers and receipt templates are undocumented.** Label printers, spine label layouts, receipt footers. Photograph every desk setup before migration day.
- **Offline circulation is a requirement, not a feature.** Ask explicitly how each system handles a network outage at the circulation desk, then test it with the network actually unplugged.

## Cost Reality Check

Licence cost is zero for all three; total cost is not. A reasonable planning frame for a mid-size public library (roughly 300 000 titles, 25 000 patrons):

| Cost item | Koha | Evergreen | FOLIO |
|---|---|---|---|
| Server footprint | 1 app + 1 DB (+1 search) | 1 app + 1 DB | 3+ DB nodes, Kafka, search, Okapi |
| Minimum viable RAM | 8–16 GB | 16 GB | 32–64 GB |
| Admin time, steady state | 2–4 h/month | 4–8 h/month | 20+ h/month without automation |
| Upgrade effort | Package upgrade + DB migrate | Schema migrate + service restart | Per-module rollout |
| Skills needed | Linux, PostgreSQL, Perl basics | Linux, PostgreSQL, OpenSRF | Kubernetes, Kafka, OpenSearch, Java ops |

The pattern is consistent: **Koha trades features for simplicity, Evergreen trades simplicity for consortium fidelity, FOLIO trades simplicity for architectural flexibility.** Pick the trade you can staff.

If you are also running a digital repository alongside the ILS, our [Koha vs Omeka vs Invenio comparison](../2026-05-02-koha-vs-omeka-vs-invenio-self-hosted-library-digital-collection-guide/) covers the collection-management side. For the database layer underneath all three systems, see the [PostgreSQL HA guide](../2026-05-21-self-hosted-postgresql-ha-kubernetes-stolon-spilo-patroni-guide/), and for the search cluster that Koha and FOLIO depend on, the [Elasticsearch management UI roundup](../2026-05-11-self-hosted-elasticsearch-management-ui-cerebro-elastichq-dejavu/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Koha vs Evergreen vs FOLIO in 2026: Choosing an Open-Source Library System That Survives Year Three",
  "description": "Koha, Evergreen and FOLIO compared on architecture, deployment cost, circulation workflows and the migration traps that only appear after go-live.",
  "datePublished": "2026-10-24",
  "dateModified": "2026-10-24",
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

**Is Koha or Evergreen better for a single small library?**
Koha, without hesitation. It installs in hours, has the widest support market, and its multi-instance tooling covers branches without requiring consortium-grade infrastructure.

**Can FOLIO run on a single server?**
Yes — the project publishes a single-server runbook — but "single server" describes the host count, not the complexity. You are still operating Kafka, OpenSearch, PostgreSQL and a dozen Java modules. Treat it as a small platform.

**Which system handles resource sharing between independent libraries best?**
Evergreen. Shared patron records, cross-branch hold targeting and item transit are core data model concepts rather than add-ons.

**Do all three support MARC21 and RDA cataloguing?**
Yes. Koha and Evergreen have long-standing MARC21 workflows with authority control; FOLIO's inventory and data-import modules handle MARC21 and RDA fields, with more configuration required per tenant.

**How long does a migration take?**
For a mid-size library, plan three to six months end to end: data extraction and mapping, test loads, staff training, parallel running, then cutover. The software install is a weekend; the migration is a project.

**What if we have no in-house Linux team?**
Choose Koha and buy hosting. Its partner network is the largest of the three, so outsourcing operations is a realistic option rather than a bespoke arrangement.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
