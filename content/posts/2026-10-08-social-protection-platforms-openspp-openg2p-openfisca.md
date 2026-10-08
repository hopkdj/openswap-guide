---
title: "OpenSPP vs OpenG2P vs OpenFisca in 2026: Which Open-Source Stack Actually Delivers Social Protection?"
date: "2026-10-08"
tags: ["self-hosted", "social-protection", "digital-public-infrastructure", "open-source-alternatives"]
draft: false
cover: "/img/screenshots/openspp-api-swagger.jpg"
description: "A hands-on 2026 comparison of OpenSPP, OpenG2P and OpenFisca for governments, NGOs and integrators building self-hosted social protection and benefit-delivery systems."
---

Roughly **half the world's population has no social protection coverage at all**, and the systems that *do* exist are frequently a spreadsheet taped to a decade-old database. When a ministry decides to modernise, the usual answer is a six-figure proprietary licence plus a consultant who owns the source code. That is exactly the problem the open-source G2P ("government-to-person") ecosystem was built to solve — and in 2026 three very different projects are competing for that job: **OpenSPP, OpenG2P and OpenFisca**.

They are not interchangeable. One is an Odoo-based programme management suite, one is a Kubernetes-native digital public infrastructure (DPI) framework, and one is a rules-as-code calculation engine that computes entitlements rather than storing beneficiaries. Picking the wrong one costs you a rewrite.

## TL;DR: Quick Verdict

- **Choose OpenSPP** if you need a working beneficiary registry, programme enrolment and payment-cycle management *this quarter*, and you are comfortable running Odoo. Fastest path from install to a usable UI.
- **Choose OpenG2P** if you are a ministry or large implementer with a Kubernetes platform team and a mandate to build national-scale DPI with strict separation between registries, consent and payments.
- **Choose OpenFisca** if your problem is *rules*, not records — eligibility formulas, tax-benefit simulation, "what happens to 40 million households if we change this threshold?" — and you want to version those rules like code.
- **The pragmatic combo:** OpenSPP or OpenG2P for the registry of record, OpenFisca for the entitlement calculation layer. Teams that understand this split ship faster.

## The Comparison Table (data pulled from GitHub, October 2026)

| Dimension | OpenSPP | OpenG2P | OpenFisca |
|---|---|---|---|
| Primary repo | `OpenSPP/openspp-modules` — **38 stars** (pushed 2026-08-31) | `OpenG2P/openg2p-registry` — **9 stars** (pushed 2026-06-17) | `openfisca/openfisca-core` — **242 stars** (pushed 2026-10-08) |
| Companion repo | `OpenSPP/openspp-docker` — 25 stars | `OpenG2P/openg2p-deployment` — updated 2026-10-08 | `openfisca/openfisca-france` — **314 stars** |
| Language | Python (Odoo modules) | Python | Python + NumPy |
| Licence | **LGPL-3.0-or-later** | **MPL-2.0** | **AGPL-3.0** |
| Deployment model | Docker Compose (Doodba-style) | Kubernetes / Rancher | pip package + `openfisca serve` (gunicorn) |
| Core abstraction | Beneficiary + programme records | Registries, consent, payments as services | Variables, parameters, reforms |
| Best fit | NGOs, pilot programmes, district deployments | National DPI, multi-ministry programmes | Policy simulation, entitlement engines |
| Time to first UI | **Hours** | Days to weeks | N/A (API/library) |

## Decision Matrix: Use Case → Tool

| Your situation | Use | Why |
|---|---|---|
| Cash transfer pilot for 5,000 households, no platform team | **OpenSPP** | Ships registries, enrolment workflows and a full admin UI out of the box |
| National ID-linked social registry with multiple integrating agencies | **OpenG2P** | Service-oriented, Kubernetes-native, designed for institutional separation |
| "Model the cost of raising the child grant by 15%" | **OpenFisca** | Purpose-built microsimulation over legislation, not a database |
| You must reproduce a benefit decision three years later for an audit | **OpenFisca** + registry | Rules are versioned artefacts in Git |
| Village-level data collection with offline officers | **OpenSPP** | Odoo mobile-capable forms plus a mature permissions model |
| Multi-country rollout under one governance umbrella | **OpenG2P** | Designed as reusable building blocks rather than one monolith |

## OpenSPP — The Pragmatic Programme Suite

![OpenSPP core registry and programme architecture](/img/screenshots/openspp-core-architecture.jpg "OpenSPP core module architecture from the official documentation")

OpenSPP is the most *usable* of the three on day one, and that is not an accident: it is built on **Odoo**, so you inherit a mature web UI, role-based access control, reporting and a huge module ecosystem. The project licenses its own code under **LGPL-3.0-or-later**, which matters if you plan to write proprietary extensions on top — you can, as long as your changes to OpenSPP itself stay open.

The practical reality check: the official Docker repository literally opens with *"This is experimental and not ready for production use."* Treat that as a serious instruction, not boilerplate. The Docker setup is built on **Doodba** (a well-known Odoo deployment pattern) driven by `invoke` tasks:

```bash
# Clone the deployment repository, then work from a copier-generated environment
git clone https://github.com/OpenSPP/openspp-docker.git
cd openspp-docker

# Pull base images, build your project images, aggregate Odoo addons from Git
invoke img-pull
invoke img-build --pull
invoke git-aggregate

# Initialise a fresh database (--demo loads sample programmes and beneficiaries)
invoke resetdb --demo

# Start Odoo
invoke start
```

The default development stack exposes Odoo at `http://localhost:${ODOO_MAJOR}069` and runs a bundled MailHog SMTP relay that intercepts every outgoing message — genuinely useful when you are debugging the notification flow of an enrolment workflow without spamming real beneficiaries. The Docker network runs in `--internal` mode by default, so a restored production database cannot silently dial home to third-party mail or API endpoints; if you need egress you flip `internal: false` deliberately.

Two OpenSPP details that matter in the field: the API surface is documented with a live **OpenAPI/Swagger console** (the screenshot below), which is what most integrators end up using to feed an existing national registry, and the modules ship as ordinary Odoo addons — meaning your team can extend them with normal Python instead of learning a bespoke plugin format.

![OpenSPP OpenAPI and Swagger console](/img/screenshots/openspp-api-swagger.jpg "OpenSPP API explorer — the integration surface most national registries consume")

**Where OpenSPP bites:** the Odoo coupling is both its superpower and its constraint. Version upgrades are Odoo upgrades, customisations live in addon directories that must be re-aggregated on every deploy, and the `invoke`-based workflow expects operators who read documentation carefully. Budget real time for the first production hardening.

## OpenG2P — Infrastructure-Grade DPI

OpenG2P is aimed at a different buyer: a ministry or a national programme with a platform team. It is licensed **MPL-2.0** (file-level copyleft — friendlier for integrators than the GPL family) and it deliberately refuses to be a single monolith. Instead you assemble registries, consent management and payment connectors as separate services.

Deployment is **Kubernetes-first**. The official `openg2p-deployment` repository is explicit about its three automation tracks:

```bash
# The deployment repository describes three tracks
#   automation/production/   -> 3-node production (registry + compute + storage)
#   automation/environment/  -> standalone environment scaffolding
#                                (namespace / project / gateway)
#   automation/sandbox/      -> single-VM sandbox / proof of concept

git clone https://github.com/OpenG2P/openg2p-deployment.git
cd openg2p-deployment
```

Note the deliberate governance quirk documented in the repository README: production scaffolding **does not** install the shared "Commons" components — you install those from the **Rancher UI only**, after the environment stage completes. That is a design choice about who holds cluster-admin privileges, and it tells you a lot about the intended operator maturity. Without a Kubernetes cluster, a container registry and someone who understands namespaces and ingress, OpenG2P will stall at the evaluation stage.

The upside of that strictness: the same building blocks can back a social registry, a farmer registry and a benefit-payment bridge without each programme inventing its own integration. If your ambition is national scale and you already run Rancher, this is the architecture that scales with you.

## OpenFisca — Rules as Code, Not a Registry

OpenFisca does not store beneficiaries and does not want to. It is a **microsimulation engine**: you describe a tax-benefit system as Python variables and parameters, then ask it what any household is entitled to under any date's legislation. The core engine is **AGPL-3.0**, and country packages (`openfisca-france` alone has **314 stars**) carry the actual legal content.

Installation is standard Python tooling, and newer documentation drives it through `uv`:

```bash
uv init
# then add the country package you need
pip install openfisca-france
```

Serving your own instance is a single command — the built-in server wraps **gunicorn**, so anything you already know about gunicorn applies:

```bash
# Serve the French tax-benefit system on the default port
openfisca serve --country-package openfisca_france

# Add local extensions and policy reforms, exactly as documented upstream
openfisca serve --country-package openfisca_france --extensions openfisca_paris
openfisca serve --country-package openfisca_france \
  --reforms openfisca_france.reforms.plf2015.plf2015

# Tune it like any gunicorn app (workers, bind, timeout, reload)
openfisca serve --country-package openfisca_france --bind 0.0.0.0:4000 --workers 4
```

There is also a public instance you can query before you deploy anything — useful for a 30-minute feasibility check. The documented endpoints expose parameters, variables and full calculations, for example the hourly minimum-wage parameter and the base family-allowance variable:

```bash
curl "https://api.fr.openfisca.org/latest/parameter/marche_travail.salaire_minimum.smic.smic_b_horaire"
curl "https://api.fr.openfisca.org/latest/variable/af_base"
```

Bootstrapping a *new* country package is a documented sprint rather than a research project — the project ships a `country-template` repository precisely so a new jurisdiction starts from a working skeleton. That is rare and valuable: most entitlement software makes your country the edge case.

**The trap:** teams regularly buy OpenFisca expecting a beneficiary management system. It has no case management, no document workflow, no payment reconciliation. It answers "how much?" with auditable, versioned logic — nothing more. Pair it with a registry.

## Avoiding the Classic Integration Mistakes

1. **Do not put beneficiary PII into Git.** OpenFisca models are code and belong in version control. Registries are not. Keep the two lifecycles separate or your first audit will be painful.
2. **Do not treat the OpenSPP Docker repository as production-ready.** The maintainers say it is experimental. Start there, then harden: pinned image digests, external managed PostgreSQL, backups, and a real reverse proxy.
3. **Do not underestimate Odoo version coupling.** OpenSPP tracks specific Odoo major versions. Pick your OpenSPP version and your Odoo upgrade calendar together, or you will be maintaining two divergent forks.
4. **Do not deploy OpenG2P without cluster ownership.** If your Kubernetes cluster is rented from a vendor that controls ingress and storage classes, you cannot complete the Rancher-based Commons installation cleanly.
5. **Licence hygiene matters at scale.** LGPL (OpenSPP) lets you ship proprietary modules around the core; AGPL (OpenFisca) effectively obliges you to publish modifications when you expose the software over a network. Get legal sign-off *before* the pilot, not after.

## FAQ

**Is OpenSPP production-ready?**
The module code is mature and actively maintained, but the official Docker deployment repository describes itself as experimental and not ready for production. Plan for a hardening phase: managed PostgreSQL, pinned images, monitoring and a proper reverse proxy before you handle real beneficiary data.

**Can OpenFisca replace a social registry?**
No. OpenFisca computes entitlements from rules and household situations. It stores no beneficiaries, no enrolment history and no payment records. Use it alongside a registry such as OpenSPP or OpenG2P.

**Does OpenG2P require Kubernetes?**
In practice, yes. The deployment automation targets Kubernetes and its production track assumes a three-node topology with namespaces, gateways and Rancher-managed components. The sandbox track exists for single-VM proofs of concept, but production without a cluster is not a supported path.

**Which project has the most permissive licence for commercial integrators?**
OpenG2P (MPL-2.0) and OpenSPP (LGPL-3.0) are both workable for commercial integration — MPL is file-level copyleft, LGPL permits proprietary modules alongside the licensed core. OpenFisca is AGPL-3.0, which is the strictest of the three for network-exposed deployments.

**How much hardware do I need to evaluate these?**
OpenSPP needs a modest VM — a couple of CPU cores and 4-8 GB of RAM runs the development stack comfortably. OpenG2P's sandbox track fits on a single VM, but its production topology assumes dedicated nodes. OpenFisca needs almost nothing: it is a Python package, and you can start with the public API before installing anything.

**Can these coexist in one programme?**
Yes, and this is the recommended architecture: a registry of record (OpenSPP or OpenG2P) for identities and enrolment, plus OpenFisca to compute entitlement amounts from versioned legislation. Keep a clean interface between them so either side can be replaced.

## Why Self-Host Social Protection Infrastructure?

Beneficiary data is the most sensitive category of personal information any institution holds: identity documents, addresses, disability status, income, sometimes biometrics. Sending it to a third-party SaaS platform means your programme's legal exposure is governed by someone else's terms of service, infrastructure and jurisdiction — and for many public-sector programmes that is simply not permissible.

Self-hosting also buys you the two things social protection systems actually need at scale: **auditability** and **permanence**. When entitlement rules live in version control and decisions are reproducible, you can answer an ombudsman's question about a payment made three years ago. When the registry runs on your infrastructure, a vendor pivot or price increase cannot strand forty million beneficiaries mid-payment-cycle.

And the cost argument is real. Programmes that move off per-beneficiary proprietary licensing often redirect the licence savings into field operations and grievance-handling — the parts of delivery that actually determine whether people get paid. If you are assembling a wider open-source public-sector stack, our [comparison of citizen participation platforms](../2026-06-08-self-hosted-citizen-participation-e-democracy-decidim-consul-polis/) covers the governance layer, our [health information systems comparison](../2026-09-16-dhis2-vs-opencrvs-vs-openimis-health-information-systems/) covers the health registry analogue, and our [document automation guide](../2026-05-03-docassemble-vs-docxtemplater-vs-pandoc-self-hosted-document-automation-guide/) covers the forms and letters layer that sits on top of any of these registries.

## The Verdict

For 2026, the honest answer is that these three tools solve three different layers of the same problem. **OpenSPP wins on time-to-value** — you can show a working beneficiary registry in a day, and the Swagger API gets you integrated with legacy systems quickly. **OpenG2P wins on institutional architecture** — it is the only one designed from the ground up for multiple agencies and national scale, and its MPL-2.0 licence is the friendliest for integrators. **OpenFisca wins on correctness and auditability** — rules as versioned code is the only approach that survives a policy change and a public audit.

Start with OpenSPP to get a real registry in front of real users, introduce OpenFisca the moment entitlement rules become contested, and graduate to OpenG2P when your programme outgrows a single ministry.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenSPP vs OpenG2P vs OpenFisca in 2026: Which Open-Source Stack Actually Delivers Social Protection?",
  "description": "Hands-on 2026 comparison of OpenSPP, OpenG2P and OpenFisca for self-hosted social protection, beneficiary registries and rules-as-code entitlement calculation.",
  "datePublished": "2026-10-08",
  "dateModified": "2026-10-08",
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
