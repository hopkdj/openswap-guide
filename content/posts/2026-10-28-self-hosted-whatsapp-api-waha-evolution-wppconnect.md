---
title: "WAHA vs Evolution API vs WPPConnect in 2026: Which Self-Hosted WhatsApp API Survives Production?"
date: "2026-10-28"
tags: ["self-hosted", "messaging", "api", "docker", "comparison"]
cover: "/img/screenshots/waha-chat-ui.jpg"
description: "A production-focused 2026 comparison of WAHA, Evolution API and WPPConnect Server: engines, multi-instance design, Docker deployments, webhook behaviour and account-ban risk."
draft: false
---

Every WhatsApp integration starts the same way: a support inbox that needs to answer customers where they already are, and no budget for per-conversation messaging fees. Someone finds a self-hosted gateway on GitHub, it works in ten minutes, and three months later the number is banned and the integration is a liability.

The three projects that dominate this space — WAHA, Evolution API and WPPConnect Server — are all unofficial automation layers on top of WhatsApp Web. They differ in engine design, multi-instance handling, and how much operational maturity you get for free. That difference decides whether you run them in production or just in a lab.

**One thing up front, because it governs everything else:** none of these are affiliated with WhatsApp or Meta, and automating a personal WhatsApp account is against the platform's terms. Numbers get banned. If your use case is contractual — customer notifications, OTP delivery, business messaging at volume — the compliant path is the official Cloud API. Read the rest of this article with that in mind.

## TL;DR — Quick Verdict

**For most self-hosted deployments, start with WAHA.** It has the cleanest engine abstraction (four engines behind one HTTP API), the healthiest commit cadence, an Apache-2.0 core, and a real dashboard with API-key scoping. 7,699 stars, pushed today.

**If you need to manage dozens or hundreds of numbers in one place, Evolution API wins on multi-instance ergonomics.** 9,980 stars and 7,387 forks make it the de facto standard in the Brazilian and Latin American integrator ecosystem, and its Manager UI plus Postgres-backed instance table scales better than filesystem sessions.

**If you are already inside the WPPConnect ecosystem, or you need a tiny single-purpose server, WPPConnect Server is fine** — Apache-2.0, 1,061 stars, a bundled manager, and a bearer-token model that is simple to reason about. It is the smallest community of the three.

## Comparison Table (verified 2026-10-28)

| Dimension | WAHA | Evolution API | WPPConnect Server |
|---|---|---|---|
| GitHub stars | 7,699 | **9,980** | 1,061 |
| Forks | 1,853 | **7,387** | 781 |
| Open issues | **463** | 250 | 41 |
| Language | TypeScript | TypeScript | TypeScript |
| License | **Apache-2.0** | Not SPDX-declared on GitHub | **Apache-2.0** |
| Last push | **2026-10-28** | 2026-07-14 | 2026-10-27 |
| Engines | 4 (WEBJS, NOWEB, GOWS, WPP) | Single (Baileys-based) | Single (own library) |
| Persistence | Filesystem sessions or Postgres/Mongo/S3 | Postgres + Redis | Filesystem, Mongo or Redis tokens |
| Dashboard | Built in (`/dashboard`) | Separate Manager container | Manager bundled in image |
| Default port | 3000 | 8080 (+3000 Manager) | 21465 |
| Auth model | API keys, per-session scopes | API key + instance token | Single `SECRET_KEY` bearer |
| Containers needed | 1 | 4 (api, manager, redis, postgres) | 1 |
| Best for | New deployments, mixed engines | Many instances, one control plane | Minimal footprint |

Read the license column carefully. WAHA and WPPConnect Server declare Apache-2.0 on GitHub, which is unambiguous for commercial use. Evolution API's repository does not declare an SPDX license, so have someone read `LICENSE` before you build a product on it — that is a five-minute check that prevents a six-month problem.

![WAHA dashboard chat interface with session list and message thread](/img/screenshots/waha-chat-ui.jpg "WAHA built-in dashboard chat UI, from the official documentation")

## Decision Matrix — Pick in 10 Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| First self-hosted WhatsApp integration | **WAHA** | One container, four engines, dashboard included |
| Need WEBJS for full feature parity | **WAHA** | Puppeteer engine exposes the most WhatsApp Web features |
| Need a lightweight engine for many sessions | **WAHA (GOWS)** | Go websocket engine uses far less RAM than browser engines |
| Managing 50+ numbers for clients | **Evolution API** | Postgres instance table + Manager UI |
| Already using Chatwoot or n8n | **Evolution API** | Most community connectors target it |
| Single number, one webhook, minimal RAM | **WPPConnect Server** | One container, bearer token, no database required |
| Strict commercial compliance required | **None of these** | Use the official Cloud API instead |
| You need guaranteed uptime for revenue flows | **None of these** | Unofficial channels can be blocked without notice |

## WAHA — Four Engines Behind One API

WAHA's architecture is the reason to pick it. WhatsApp Web can be automated in several ways, and each has trade-offs: a real browser gives you the most features but costs 300-500 MB of RAM per session; a websocket implementation is far cheaper but occasionally lags on new features. WAHA exposes **WEBJS** (browser), **NOWEB** (Node websocket), **GOWS** (Go websocket) and **WPP** (browser, WPPConnect-based) behind the same REST surface, so you can switch engines per deployment without rewriting your integration.

The official Compose file from the repository:

```yaml
services:
  waha:
    restart: always
    # WAHA Plus (paid) — for Core use devlikeapro/waha:latest
    image: devlikeapro/waha-plus
    dns:
      - 1.1.1.1
      - 8.8.8.8
    logging:
      driver: 'json-file'
      options:
        max-size: '100m'
        max-file: '10'
    ports:
      - '127.0.0.1:3000:3000/tcp'
    volumes:
      - './sessions:/app/.sessions'
      - './media:/app/.media'
    env_file:
      - .env
```

Three details earn trust here. The port binding is `127.0.0.1:3000` — loopback only, so you must put a reverse proxy in front, which is the correct default for a service that controls a messaging account. The `dns` entries exist because container DNS resolution of `web.whatsapp.com` fails in some Docker networks. And logging is capped, which matters because a busy session writes a lot of noise.

Switch to the free Core image and the API is the same:

```yaml
    image: devlikeapro/waha:latest
```

Beyond the gateway, WAHA ships a dashboard at `/dashboard` with a chat UI, API-key management with per-session scopes, and a real-time event monitor. For debugging "did the webhook fire, or did the session die", the event monitor saves hours compared with tailing JSON logs.

![WAHA dashboard API key management screen](/img/screenshots/waha-api-keys.jpg "WAHA dashboard API keys with per-session scopes, from the official documentation")

**Verdict:** the best default in 2026. Reach for it unless you have a specific reason not to.

## Evolution API — The Multi-Instance Control Plane

Evolution API approaches the same problem from the integrator's side: you are not running one WhatsApp session, you are running many, for different clients, and you need a control plane. Instances live in Postgres, media and state are cached in Redis, and a separate Manager frontend gives non-technical staff a UI.

The official Compose file shows the full stack:

```yaml
services:
  api:
    image: evoapicloud/evolution-api:latest
    restart: always
    depends_on:
      - redis
      - evolution-postgres
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - evolution_instances:/evolution/instances
    env_file:
      - .env
  frontend:
    image: evoapicloud/evolution-manager:latest
    restart: always
    ports:
      - "3000:80"
  redis:
    image: redis:latest
    restart: always
    command: redis-server --port 6379 --appendonly yes
    volumes:
      - evolution_redis:/data
  evolution-postgres:
    image: postgres:15
    restart: always
    env_file:
      - .env
    command: ["postgres", "-c", "max_connections=1000", "-c", "listen_addresses=*"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
volumes:
  evolution_instances:
  evolution_redis:
  postgres_data:
```

Two things break first in real deployments. The example file includes an `external: true` network named `dokploy-network` — that is a leftover from the maintainer's own hosting setup, and `docker compose up` will fail until you delete those network references or create the network yourself. And `max_connections=1000` with `listen_addresses=*` is tuned for a large instance count; on a single-number deployment it just means a Postgres that is easier to exhaust.

The trade-off is honest: four containers, roughly 800 MB to 1 GB of RAM, and a Postgres you must back up — in exchange for an instance model that does not fall over at fifty numbers.

**Verdict:** the right tool when WhatsApp is a business line rather than a feature. Heavier, but the scale story is real.

## WPPConnect Server — Small, Apache-2.0, Predictable

WPPConnect Server is the least glamorous and the easiest to operate. One container, one port (21465), one `SECRET_KEY` that acts as a bearer token, and a bundled manager UI. No Postgres, no Redis unless you want them.

```yaml
services:
  wppconnect:
    container_name: wpp-server
    image: wppconnect/wppconnect-server:${WPP_SERVER_TAG:-latest}
    restart: unless-stopped
    environment:
      PORT: '${PORT:-21465}'
      HOST: '${HOST:-http://localhost}'
      SECRET_KEY: '${SECRET_KEY:-change-me}'
      WEBHOOK_URL: '${WEBHOOK_URL:-}'
      WEBHOOK_RETRY_ATTEMPTS: '${WEBHOOK_RETRY_ATTEMPTS:-3}'
      WEBHOOK_RETRY_DELAY: '${WEBHOOK_RETRY_DELAY:-5000}'
      TOKEN_STORE_TYPE: '${TOKEN_STORE_TYPE:-file}'
      MANAGER_ENABLED: '${MANAGER_ENABLED:-true}'
    volumes:
      - wppconnect_tokens:/usr/src/wpp-server/tokens
      - wppconnect_user_data:/usr/src/wpp-server/userDataDir
      - wppconnect_uploads:/usr/src/wpp-server/uploads
    ports:
      - '${PORT:-21465}:${PORT:-21465}'
volumes:
  wppconnect_tokens: {}
  wppconnect_user_data: {}
  wppconnect_uploads: {}
```

Note the default `SECRET_KEY` value in the upstream file — it is a placeholder literally named as a placeholder. Change it before the container is reachable, because that token authorizes sending messages from your number. Also note the volume list: tokens, user data and uploads are separate, and losing `wppconnect_user_data` means re-pairing every session.

Webhook retry is built in (`WEBHOOK_RETRY_ATTEMPTS`, `WEBHOOK_RETRY_DELAY`), which is more than several competitors offer out of the box. If your consumer endpoint is flaky, this saves you from writing a replay queue.

**Verdict:** a good fit for one or two numbers where you control the code on both sides. The 1K-star community means fewer answers when something breaks.

## Pitfalls That Cost People Their Numbers

**Ban risk is not theoretical and not evenly distributed.** Browser engines look more like a real client and tend to survive longer; cheap websocket implementations send traffic patterns that are easier to fingerprint. If a number matters, do not use it for bulk outbound on day one — warm it up with normal conversational traffic.

**Session directories are state, not cache.** WAHA's `./sessions` and WPPConnect's token volume hold the paired-device credentials. Lose them and every session must be re-paired by scanning a QR code, which for a client-facing number means a maintenance window.

**One container per number is a trap.** Three containers at 400 MB each is worse than one container with three sessions. WAHA supports multiple sessions per instance, and Evolution's whole design is multi-instance — use that instead of scaling sideways with Compose.

**Webhooks need idempotency on your side.** All three deliver at-least-once with retries. If your handler creates a ticket per inbound message, you will get duplicates. Store the message ID and drop repeats.

**Do not put these on the public internet.** WAHA's example binds to loopback for a reason. Reverse proxy with TLS, restrict by IP where possible, and rotate API keys — a leaked key lets anyone send messages as your business.

**Test engine choice against the features you actually use.** Reactions, polls, channels, group metadata and presence support differ per engine. A feature that works in WEBJS may be missing in GOWS, and discovery happens in production unless you test first.

## Where This Fits in a Support Stack

If you are building a support inbox rather than raw message plumbing, the gateway is only one layer. Our [Chatwoot vs Papercups vs Tiledesk comparison](../self-hosted-live-chat-chatwoot-papercups-tiledesk-guide/) covers the inbox side, and most Chatwoot-to-WhatsApp connectors in the wild target Evolution API.

For automation on top of inbound messages, the [Automatisch vs n8n vs Activepieces guide](../2026-04-29-automatisch-vs-n8n-vs-activepieces-self-hosted-workflow-automation-2026/) is the relevant read — n8n has community nodes for both WAHA and Evolution. And if your goal is bridging WhatsApp into an existing chat network rather than exposing an HTTP API, the [Matrix bridge comparison](../2026-04-28-mautrix-whatsapp-telegram-signal-discord-self-hosted-matrix-bridges-guide-2026/) covers mautrix-whatsapp, which solves the same problem with a completely different model.

A sane production pattern: WAHA or Evolution as the gateway behind a private network, Chatwoot as the human interface, n8n for outbound triggers, and a hard rule that no marketing blasts go through the unofficial channel.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "WAHA vs Evolution API vs WPPConnect in 2026: Which Self-Hosted WhatsApp API Survives Production?",
  "description": "A production-focused 2026 comparison of WAHA, Evolution API and WPPConnect Server: engines, multi-instance design, Docker deployments, webhook behaviour and account-ban risk.",
  "datePublished": "2026-10-28",
  "dateModified": "2026-10-28",
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

**Is it legal to self-host a WhatsApp API?**

Hosting the software is legal; using it to automate a WhatsApp account is against WhatsApp's terms of service. The practical consequence is account suspension or a permanent ban, not usually legal action. For business messaging with contractual guarantees, use the official Cloud API.

**Which of the three supports the most WhatsApp features?**

WAHA's WEBJS engine, because it drives a real browser session and therefore inherits most of WhatsApp Web's feature set. Websocket engines such as GOWS are lighter and faster but can lag on newer features like channels or polls.

**How much RAM does each gateway need?**

WAHA with a browser engine runs around 400-600 MB per active session; the GOWS engine is considerably lighter at roughly 100-150 MB. Evolution API needs about 800 MB to 1 GB total for api, manager, Redis and Postgres. WPPConnect Server is the smallest at roughly 250-400 MB for a single number.

**Can I run multiple WhatsApp numbers on one instance?**

Yes for all three, but the models differ. WAHA supports multiple sessions per container and documents sharding for 50+ sessions. Evolution API stores instances in Postgres with a Manager UI, which is the friendliest at scale. WPPConnect Server handles multiple sessions but has the smallest operational tooling.

**Why did my session disconnect after a container restart?**

Almost always a missing or unmounted session volume. WAHA stores credentials in `/app/.sessions` and WPPConnect in `/usr/src/wpp-server/tokens`; if those paths are not persisted, the pairing is lost and a new QR scan is required.

**Does Evolution API need Redis?**

Redis is part of the official Compose stack and is used for caching and instance state. It is possible to run without it in some configurations, but the documented deployment includes it, and removing it means losing the cache layer that keeps large instance counts responsive.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
