---
title: "Mojaloop vs Interledger Open Payments vs Tazama in 2026: Building Payment Interoperability Without a Vendor"
date: "2026-10-08"
tags: ["self-hosted", "payments", "fintech", "open-source-alternatives"]
draft: false
cover: "/img/screenshots/tazama-rule-studio-tree.jpg"
description: "A 2026 engineering comparison of Mojaloop, Interledger Open Payments and Tazama — three open-source projects for instant payment switches, wallet payment APIs and real-time fraud monitoring."
---

Every country that has built a working instant payment system has discovered the same uncomfortable truth: the connective tissue — the switch, the API standard, the fraud layer — is where vendor lock-in concentrates. A national payments switch is not a product you can swap out in a quarter. That is why three open-source projects have quietly become the default answer for institutions that refuse to hand over the rails: **Mojaloop** (interoperable payment switching), **Interledger Open Payments** (a wallet-to-wallet payment API standard), and **Tazama** (real-time transaction monitoring).

They live at different layers of the same stack, which is exactly why teams get confused about which one they need. Here is the engineering view, with real deployment configs pulled from the upstream repositories in October 2026.

## TL;DR: Quick Verdict

- **Mojaloop** if you are building an **interoperable switch** that connects multiple banks, mobile money providers and fintechs — the hub-and-spoke model that powers inclusion-focused national rails. Most mature, most operationally demanding.
- **Interledger Open Payments** if you need a **standard API for moving money between accounts** across providers (checkout, P2P transfers, subscriptions, tipping) and you want to implement against a specification rather than adopt an entire switch.
- **Tazama** if the problem is **fraud and anomaly detection on a live rail**. It watches transactions in real time and evaluates rules you author yourself, rather than bolting batch reporting onto the end of the day.
- **The realistic combination:** Open Payments or Mojaloop for moving the money, Tazama for watching it. They are complementary, not competitive.

## The Comparison Table (GitHub data, October 2026)

| Dimension | Mojaloop | Interledger Open Payments | Tazama |
|---|---|---|---|
| Main repository | `mojaloop/mojaloop` — **327 stars** (umbrella) | `interledger/open-payments` — **548 stars** | `tazama-lf/tazama-stack` — **25 stars** |
| Active code repos | `central-ledger` **58 stars** (2026-10-06), `ml-api-adapter` **11 stars** (2026-10-07) | Documentation + specs, pushed **2026-10-07** | `tazama-demo` **15 stars** (2026-10-08), `rule-studio` |
| Licence | **Apache-2.0** (Mojaloop Foundation) | **Apache-2.0** | **Apache-2.0** |
| Layer | Payment switch / clearing hub | Payment API standard (wallet address, resource, auth servers) | Transaction monitoring / fraud rules |
| Protocol emphasis | Mojaloop Interoperability APIs | **GNAP (RFC 9635)** authorisation | Rule evaluation on live transaction streams |
| Deployment | Per-service Docker Compose: Kafka, MySQL, Redis cluster | Node/pnpm toolchain for docs; SDKs for implementers | Docker Compose production stack + Rule Studio UI |
| Operational burden | High — a switch is infrastructure | Low — an API you implement | Medium — depends on your event pipeline |

## Decision Matrix: Which Layer Do You Actually Need?

| Your problem | Use | Why |
|---|---|---|
| Connect 12 banks and 4 wallets so they can transact with each other | **Mojaloop** | Purpose-built switching, clearing and settlement model |
| Let a third-party app initiate a payment from a user's wallet | **Open Payments** | Standard API surface with GNAP-based delegated authorisation |
| Detect mule accounts and structuring in real time | **Tazama** | Rules evaluated on the transaction stream, not next-day reports |
| You are a wallet provider that must be interoperable with others | **Open Payments** | Implement the spec, expose wallet address + resource servers |
| You need both a switch and a fraud layer | **Mojaloop + Tazama** | Same problem domain, different responsibility |
| You only need to take card/e-wallet payments on a website | None of these | Use an open-source payment gateway instead |

## Mojaloop — The Switching Layer

![Mojaloop payment scheme governance model](/img/screenshots/mojaloop-payment-scheme-governance.jpg "The hub-and-spoke payment scheme model that Mojaloop implements")

Mojaloop is the heavyweight. It is governed by the **Mojaloop Foundation**, licensed **Apache-2.0**, and its architecture assumes you are operating a *scheme*: participants connect to a central hub, the hub handles quoting, transfers and settlement positions. That is a fundamentally different operational commitment from running a web app — you are now running Kafka, MySQL and a Redis cluster, and you own the uptime of a payment rail.

The service-level compose files make that concrete. This is an abridged excerpt from the official `ml-api-adapter` `docker-compose.yml` (Mojaloop publishes a compose file per component rather than one monolithic stack):

```yaml
networks:
  ml-mojaloop-net:
    name: ml-mojaloop-net

x-redis-node: &REDIS_NODE
  image: docker.io/bitnamilegacy/redis-cluster:6.2.14
  environment: &REDIS_ENVS
    ALLOW_EMPTY_PASSWORD: yes
    REDIS_NODES: redis-node-0:6379 redis-node-1:9301 redis-node-2:9302
                 redis-node-3:9303 redis-node-4:9304 redis-node-5:9305
  healthcheck:
    test: [ "CMD", "redis-cli", "ping" ]

services:
  ml-api-adapter:
    image: mojaloop/ml-api-adapter:local
    command: sh -c "node /opt/app/wait4/wait4.js ml-api-adapter && node src/api/index.js"
    ports:
      - "3000:3000"
    environment:
      - MLAPI_ENDPOINT_SOURCE_URL=http://ml-api-adapter-endpoint:4545
    depends_on:
      - central-ledger
      - kafka
      - redis-node-0
    healthcheck:
      test: ["CMD", "sh", "-c", "curl --fail --silent --output /dev/null http://localhost:3000/health"]

  central-ledger:
    image: mojaloop/central-ledger:v20.0.0
    command: sh -c "node /opt/app/wait4/wait4.js central-ledger && npm run migrate && node dist/api/index.js"
    ports:
      - "3001:3001"
```

Three things worth noticing. First, `wait4.js` — every service blocks on its dependencies rather than crash-looping, because a switch that starts before its database is a switch that loses transfers. Second, the API adapter and the ledger are **separate deployables**, which is what makes horizontal scaling and per-component upgrades possible. Third, health checks are first-class on every service, since a load balancer in front of a payment API must never route to an unready pod.

Choose Mojaloop when interoperability *is* the product. If you are a single institution that just needs to accept payments, it is dramatically more machinery than you need.

## Interledger Open Payments — The API Standard

Open Payments takes the opposite approach: rather than deploying a switching fabric, it defines **an API standard that account servicing entities — banks, digital wallets, mobile money providers — implement so they can interoperate**. The main repository is documentation and reference material; the actual OpenAPI specifications live in a companion specifications repository, and the published docs live at `openpayments.dev`.

Architecturally it decomposes into three servers, and understanding this split is most of the work:

1. **A wallet address server** — exposes public information about Open Payments-enabled accounts (the human-readable wallet addresses).
2. **A resource server** — exposes APIs that act against the underlying accounts.
3. **An authorisation server** — exposes **GNAP**-compliant APIs (RFC 9635) for obtaining grants to call the resource server.

The use cases the standard targets are deliberately web-scale rather than bank-scale: checkout, person-to-person transfers, subscriptions, invoice payments, tipping and Web Monetization. If you have ever wanted a payment primitive you can call from a normal web stack with scoped, delegated grants instead of long-lived API keys, this is the design intent.

Working with the project locally is ordinary Node tooling, and the repository documents it precisely:

```sh
# install node from .nvmrc, then pnpm via corepack
nvm install
corepack enable

# install dependencies and the specifications submodule
pnpm i
git submodule update --init

# preview the docs locally
pnpm --filter docs start
```

Client SDKs are published for implementers, which is the real adoption lever: you do not hand-roll the GNAP dance. **The honest caveat** is that Open Payments is a standard plus SDKs, not a turnkey wallet. Your institution still has to build the resource server side of the contract.

## Tazama — Real-Time Monitoring on the Rail

![Tazama Rule Studio rule tree](/img/screenshots/tazama-rule-studio-tree.jpg "Tazama Rule Studio: authoring monitoring rules as a decision tree")

Fraud controls in most payment systems are an afterthought — a nightly report, a spreadsheet, a queue someone reviews next week. Tazama inverts that: it consumes transactions as they happen and evaluates **rules you author** to flag suspicious behaviour (structuring, mule activity, unusual velocity) while the payment is still in flight.

Operationally, Tazama is split into a rules UI and the evaluation stack. The **Rule Studio** is a React front end for building and maintaining rule trees — which matters more than it sounds, because it puts rule authorship in the hands of fraud analysts instead of requiring a code deploy for every new pattern. The stack repository builds and publishes the container images for the services.

If you want to *see* it before you commit, the demo repository ships a single-service production compose file you can boot in seconds:

```yaml
services:
  app:
    container_name: Demo-App
    image: demo-app
    build:
      context: ./
      target: production
      dockerfile: Dockerfile
    volumes:
        - .:/app
        - /app/node_modules
        - /app/.next
    ports:
      - "3011:3011"
```

That is the evaluation UI on port 3011 — deliberately thin, because the interesting part of Tazama is the rule semantics, not the container wiring. Everything is **Apache-2.0**, so embedding the monitoring layer in a commercial rail is legally straightforward.

The trade-off: Tazama is only as good as your event pipeline. If your core banking system cannot emit transactions in real time, you have bought a rule engine with nothing to chew on.

## Pitfalls That Cost Teams Months

1. **Do not confuse the layers.** Teams regularly try to solve "connect our banks to each other" with Open Payments (a wallet API standard) or "let a wallet initiate a payment" with Mojaloop (a hub). Get the layer right before you evaluate a single feature.
2. **A switch is production infrastructure with compliance weight.** Running Mojaloop means owning Kafka, MySQL, Redis cluster, upgrade windows and settlement correctness. Staff it like infrastructure, not like a website.
3. **Redis cluster config is not optional detail.** Mojaloop's compose file pins a six-node Redis cluster topology with explicit node ports. Shrinking that to a single Redis instance in production removes the redundancy the design assumes.
4. **`wait4` ordering hides real dependency failures.** The dependency-waiting pattern prevents crash loops but can also mask a permanently unhealthy database. Alert on readiness, not just on process liveness.
5. **GNAP changes your auth model.** Open Payments grants are per-resource and short-lived. If your integration assumes one long-lived API key per merchant, budget for a design change, not a library swap.
6. **Fraud rules need a feedback loop.** Tazama will happily evaluate rules forever; without a process for reviewing alerts and tuning false positives, your fraud layer becomes noise within a month.
7. **Licence review is cheap; retrofitting is not.** All three are Apache-2.0, which is unusually frictionless — but your *data protection* obligations around transaction data remain regardless of licence.

## FAQ

**What is the difference between Mojaloop and Open Payments?**
Mojaloop is an interoperable payment *switch* — a hub that connects multiple providers and handles quoting, transfers and settlement. Open Payments is an API *standard* that account servicing entities implement so payments can be set up between them, built on GNAP authorisation. You deploy a switch; you implement a standard.

**Can I run Mojaloop with Docker Compose?**
Yes — the project publishes Compose files per component (for example `central-ledger`, `ml-api-adapter`) with Kafka, MySQL and a Redis cluster. That gets you a working evaluation environment quickly, but a production switch needs orchestration, monitoring, backups and change control well beyond `docker compose up`.

**Does Tazama replace transaction monitoring in my core banking system?**
It complements it. Tazama evaluates rules on a live transaction stream and flags patterns; your core system still owns balances, limits and blocking decisions. Feed Tazama the event stream and route its alerts into your existing case management process.

**Is Open Payments a wallet I can install?**
No. It is a specification plus client SDKs and documentation. Banks, wallets and mobile money providers implement it on their side; you will be building the resource server and authorisation server integration.

**Which of these is most mature?**
Mojaloop has the longest operational track record and the most heavyweight governance, with the deepest set of component repositories. Open Payments has the broadest specification work and a large star count because it addresses a wider developer audience. Tazama is the newest and smallest by stars, but its release cadence in 2026 has been frequent.

**How do these compare to an open-source payment gateway?**
A gateway (accepting payments on a website) is a different problem from a switch, an interop standard or a fraud layer. If all you need is checkout, use a gateway — see our [comparison of self-hosted payment gateways](../2026-04-29-self-hosted-payment-gateways-hyperswitch-btcpay-server-guide/). If you need to invoice and meter, look at open-source [billing platforms](../2026-04-21-lago-vs-killbill-open-source-billing-platforms-guide/) instead.

## Why Self-Host a Payment Rail at All?

Payment data is regulated, and the rails are critical national infrastructure. Handing the switch to a vendor means handing over your transaction graph — who pays whom, how often, how much — plus the pricing power over a system that cannot be turned off once it is live. That is why even well-funded programmes repeatedly choose open-source here: Apache-2.0 removes the licence negotiation, and the code gives regulators something they can actually inspect.

There is also a resilience argument that only becomes obvious during an incident. When a payment rail degrades, you need to see inside it: the queue depth in Kafka, the readiness of the ledger, which service is holding the transfer. A self-hosted stack gives your engineers that view. A black-box vendor switch gives you a status page and a support ticket.

And the ecosystem effect compounds. Once a switch is open, adjacent capabilities appear — real-time fraud monitoring, wallet interoperability, dispute tooling — because anyone can build against the same interface. Programmes that open-sourced their rails are visibly wider in capability today. If you operate in the humanitarian or development space, the same pattern shows up in [crisis and emergency management platforms](../2026-06-08-self-hosted-crisis-emergency-management-ushahidi-sahana-hot-tasking-manager/), where open rails and open coordination tooling reinforce each other.

## The Verdict

For 2026: **Open Payments if you are an implementer, Mojaloop if you are an operator, Tazama if you are a defender.** Start by deciding which of those three you actually are — the expensive mistake in this space is deploying a switch when you needed a specification, or buying fraud rules when you needed a clearing layer.

Recommended sequence for a national or regional programme: model the flow with Open Payments semantics, implement the switch on Mojaloop when multiple participants must transact, and stand up Tazama against the same event stream before you go live with real money. Open layers compose; that is the entire point.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Mojaloop vs Interledger Open Payments vs Tazama in 2026: Building Payment Interoperability Without a Vendor",
  "description": "Engineering comparison of Mojaloop, Interledger Open Payments and Tazama for self-hosted instant payment switching, wallet payment APIs and real-time transaction monitoring.",
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
