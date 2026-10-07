---
title: "SplitPro vs Spliit vs Kostos in 2026: The Best Self-Hosted Splitwise Alternatives"
date: "2026-10-07"
tags: ["self-hosted", "personal-finance", "expense-splitting", "privacy", "docker", "pwa"]
draft: false
cover: "/img/screenshots/splitpro-dashboard.jpg"
---

Splitting a shared bill should not require uploading your housemates' spending habits to a company that keeps inventing new reasons to charge for it. Splitwise spent the last few years moving daily-use features behind its Pro tier, and the result is a healthy, genuinely capable line-up of self-hosted replacements. Three of them are actively developed right now: **SplitPro** (**1,466 stars**, last pushed 2026-10-05), **Spliit** (**2,980 stars**, last pushed 2026-10-07), and **Kostos** (43 stars, last pushed 2026-10-05).

They look similar on the surface. They are not. One is a full app with accounts and receipts, one is a deliberately minimal link-based ledger, and one is an end-to-end encrypted offline-first app that never stores your data in a readable form.

## TL;DR — Quick Verdict

- **Want the most complete self-hosted experience** — groups, accounts, receipts, balances, dark mode: use **SplitPro**. It is the closest thing to "Splitwise, but yours".
- **Want the smallest possible footprint and zero sign-ups**: use **Spliit**. Groups are links, expenses are entries, and the whole thing is one container plus PostgreSQL.
- **Want cryptographic privacy and true offline use**: use **Kostos**. Expenses are encrypted in the browser before they ever reach your server, and the app works on a plane.

## Feature Comparison

Star counts, licences and last-push dates were read from the GitHub API at publish time.

| | **SplitPro** | **Spliit** | **Kostos** |
|---|---|---|---|
| Stars | 1,466 | 2,980 | 43 |
| Language | TypeScript (Next.js) | TypeScript (Next.js) | TypeScript (SvelteKit PWA) |
| License | MIT | MIT | None declared on GitHub |
| Last push | 2026-10-05 | 2026-10-07 | 2026-10-05 |
| Accounts | Yes (email/OTP) | No — secret group links | No — secret token per group |
| Encryption at rest | Server-side (your database) | Server-side (your database) | **AES-GCM in the browser** — server stores ciphertext |
| Offline support | Limited (PWA) | Limited (PWA) | Yes — Y.js + IndexedDB |
| Database | PostgreSQL | PostgreSQL | None required (file volume) |
| Receipt uploads | Yes | Yes (attachments) | No |
| Multi-currency | Yes | Yes | Yes (153 currencies, rate frozen per expense) |
| Settlement algorithm | Balances + settle-up | Balances + settle-up | Minimum-transfer plan + graph |
| Deployment target | Docker Compose | Docker Compose / GHCR image | Docker, Node, or Cloudflare Workers |
| Best for | Ongoing household use | One-off trips and groups | Privacy-sensitive groups |

## Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Shared flat with recurring bills | **SplitPro** | Groups persist, receipts attach, balances are always visible |
| Two-week holiday with 8 friends | **Spliit** | Create a group, share the link, no accounts to explain |
| Group that refuses to hand over spending data | **Kostos** | The relay only ever sees encrypted blobs |
| Travelling with unreliable connectivity | **Kostos** | Expenses queue in IndexedDB and sync when you reconnect |
| You already run PostgreSQL | **SplitPro** or **Spliit** | Both expect a database; deployment is a compose file |
| You want the absolute cheapest host | **Kostos** | A static bundle plus a tiny sync service; even runs on free-tier Workers |
| Financial records you might need offline forever | **Kostos** or **SplitPro** | Kostos exports JSON/CSV; SplitPro keeps everything in your own database |

## SplitPro — The Complete Household App

SplitPro is the most conventional of the three: a Next.js application with real user accounts, persistent groups, and the features people actually miss from the hosted products. It ships an official production compose file that runs PostgreSQL together with the app image:

```yaml
name: split-pro-prod

services:
  postgres:
    image: ossapps/postgres:17.7-trixie
    restart: always
    environment:
      - POSTGRES_USER=${POSTGRES_USER:?err}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?err}
      - POSTGRES_DB=${POSTGRES_DB:?err}
    command: >
      postgres
      -c shared_preload_libraries=pg_cron
      -c cron.database_name=${POSTGRES_DB:-splitpro}
      -c cron.timezone=UTC
    volumes:
      - database:/var/lib/postgresql/data

  splitpro:
    image: ossapps/splitpro:latest
    restart: always
    ports:
      - ${PORT:-3000}:${PORT:-3000}
    env_file: .env
    healthcheck:
      test: ['CMD', 'wget', '--spider', '-q', 'http://localhost:${PORT:-3000}/api/healthz']
    depends_on:
      postgres:
        condition: service_healthy
```

Two things stand out. The Postgres image preloads **`pg_cron`**, which is how the app schedules recurring expense generation and reminder jobs without a separate worker — a genuinely elegant trick. And the app exposes a health endpoint at `/api/healthz`, so reverse-proxy or orchestrator health checks work out of the box. Copy the repository's `.env` file, set the database credentials and any OAuth provider keys, and you are running.

Feature-wise it covers the ground: email/OTP accounts, groups and group invites, multiple split modes (equal, percentage, shares, exact amounts), non-group "friends" expenses, receipt uploads stored on a volume, activity feeds, and a PWA layout that behaves properly on a phone. The MIT licence is the most permissive of the three, which matters if you ever want to fork or embed it.

**Verdict:** the best default for recurring, long-lived sharing — a household or a couple running their finances together.

![SplitPro dashboard with group balances and recent expenses](/img/screenshots/splitpro-dashboard.jpg)

## Spliit — The Minimalist Ledger

Spliit inverts the model: **no accounts, no email, no password**. A group is identified by a secret link, and anyone holding that link can add expenses. The project publishes a first-party container image, and the deployment is one service plus a database:

```yaml
name: spliit

services:
  app:
    image: ghcr.io/spliit-app/spliit:latest
    user: "1000:1000"     # change to your user id, or remove to run as root
    ports:
      - "8080:3000/tcp"
    environment:
      POSTGRES_PRISMA_URL: postgresql://spliit:***@database:5432/spliit
```

That is essentially the whole configuration surface. The app stores expenses with a title, amount, payer and participants, computes balances, and offers a settle-up view that reduces the number of transfers needed to clear the group. There are no invitations to accept and no password resets to support — which is exactly why people deploy it for conferences, ski trips, and one-off group dinners.

The trade-offs are the flip side of the design. Because group access *is* the link, anyone who obtains the URL can read and edit the ledger, and you should treat those links like credentials. There is also no real "login" to revoke, so rotation means creating a new group. Receipts and attachments are supported, but the app deliberately avoids anything that smells like bookkeeping: no recurring bills, no budgets, no reports.

**Verdict:** the fastest path from "we need to split this" to "it's split", with the least configuration of the three.

## Kostos — End-to-End Encrypted and Offline-First

Kostos is the smallest project here and the most architecturally interesting. It is a PWA built on **Y.js + IndexedDB**, and every update is **AES-GCM encrypted in the browser** before it reaches the sync relay. The relay stores opaque ciphertext; the group's key never leaves the devices. Groups are identified by a token that doubles as the invite link, and there are no accounts, no email, no password.

Self-hosting takes one build and one container:

```sh
docker build -t kostos .
docker run -p 8080:8080 -v kostos-data:/data kostos
```

There is also a static-bundle mode: build the front end, run `node scripts/serve.js`, and route `/sync/<roomId>` WebSockets to the sync service. The project supports deploying the same bundle to **Cloudflare Workers** with Durable Objects, where hibernating WebSockets mean idle groups consume no CPU — so a free-tier account can host a modest group indefinitely.

Functionally it is surprisingly deep for something so small: three split modes (even, weighted shares, exact per-person amounts), a maths expression parser inside amount fields, multi-payer expenses, 153 currencies with the exchange rate frozen at creation time, trip tagging with date ranges, minimum-transfer settlement drawn as a payers-to-receivers graph, QR invitations, and lossless JSON plus CSV export. Because everything is local-first, adding an expense on a train works fine; Y.js merges concurrent edits and asks you to resolve genuine conflicts when two devices edit the same expense.

The honest caveats: the project is young, has a small community, and declares no licence file on GitHub — check before commercial use. Encryption also means **no server-side recovery**. If every member loses their device, the group's history is gone, and export discipline matters more here than anywhere else.

![Kostos home screen showing the settlement graph and who-owes-who list](/img/screenshots/kostos-home.jpg)

## Migration Notes and Common Traps

- **Decide who owns the backup before you invite anyone.** SplitPro and Spliit keep plaintext data in PostgreSQL, so `pg_dump` on a schedule is your backup. Kostos keeps ciphertext on the server, so a server backup cannot restore a group whose devices are gone — rely on the JSON export, not on the volume.
- **Treat group links as passwords.** Spliit and Kostos both use "the link is the key". Anyone with it can read and edit. Do not paste them into public chat rooms, and remember that a leaked Spliit link cannot be revoked without creating a new group.
- **Put every deployment behind TLS.** All three rely on browser crypto and service workers; service workers only register on HTTPS, and Kostos's encryption assumes an uncompromised transport. A reverse proxy with automatic certificates is table stakes.
- **Mind the upload volumes.** SplitPro stores receipts under `/app/uploads`; if you containerize it without a named volume, a redeploy deletes every attachment.
- **Set your base currency first.** All three support multiple currencies, but the group base currency defines how balances are reported. Changing it later rewrites the meaning of historical settlements.
- **Expect different "settle up" answers.** Algorithms differ in how aggressively they minimise transfers. A settlement you planned in one app may look slightly different after importing the same expenses into another — verify before anyone actually pays.
- **Do not migrate mid-month.** Close out your existing balances, export, and start the self-hosted ledger on a clean period. Importing half a year of history into a fresh group is where reconciliation pain lives.

If you are building out a self-hosted financial stack, our [personal finance server comparison covering Maybe, Firefly III and Actual Budget](../2026-05-01-maybe-finance-vs-firefly-iii-vs-actual-budget-self-hosted-personal-finance/) covers the "whole budget" layer, and the [subscription and expense management round-up with Wallos, iHatemiMoney and Spliit](../2026-06-03-self-hosted-subscription-expense-management-wallos-ihatemoney-spliit/) handles the recurring-bill side. If you simply need to keep the server tidy while you run all of this, our guide to [container garbage collection and image pruning](../2026-05-11-self-hosted-container-garbage-collection-docker-gc-distribution-portainer-guide/) is worth reading before the disk fills.

## Frequently Asked Questions

### Which self-hosted Splitwise alternative is easiest to deploy?

**Kostos** — a single `docker run` with a data volume, no database to provision. **Spliit** is a close second because it needs only PostgreSQL and a secret URL; **SplitPro** requires the same database plus an `.env` file with credentials and optional OAuth keys, which is a few more minutes of setup.

### Are these apps actually free, or is there a paid tier?

All three are self-hosted software with no paid tier. **SplitPro** and **Spliit** are MIT-licensed, so you can modify and redistribute them, while **Kostos** publishes no licence file on GitHub — verify terms before using it commercially. Your only recurring cost is the server you already run.

### Does a self-hosted splitter keep my financial data private?

It depends entirely on the model. **SplitPro** and **Spliit** store expenses in your own PostgreSQL in plaintext — private from third parties, but readable by anyone with database access. **Kostos** encrypts each update in the browser with AES-GCM, so the server only holds ciphertext. If your threat model includes the server operator, only the encrypted option qualifies.

### Can I still use these offline?

**Kostos** is built for it: it is a local-first PWA backed by IndexedDB, so you can add expenses with no connection and sync later. **SplitPro** and **Spliit** are installable PWAs and will cache the shell, but writing expenses while offline is not their design centre, so expect failed submissions rather than a synced queue.

### What happens to a group if the server dies?

With **SplitPro** and **Spliit**, restoring the PostgreSQL backup restores the group completely. With **Kostos**, the server only holds ciphertext — recovery requires a device that still has the group key, or a JSON export taken earlier. In all three cases, an export routine beats hoping your disk survives.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SplitPro vs Spliit vs Kostos in 2026: The Best Self-Hosted Splitwise Alternatives",
  "description": "Hands-on comparison of SplitPro, Spliit and Kostos — three actively developed self-hosted Splitwise alternatives — covering encryption models, real Docker deployment configs, offline behaviour and migration traps.",
  "datePublished": "2026-10-07",
  "dateModified": "2026-10-07",
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
