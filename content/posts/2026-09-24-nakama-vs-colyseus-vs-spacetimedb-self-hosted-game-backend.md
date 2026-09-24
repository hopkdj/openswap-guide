---
title: "Nakama vs Colyseus vs SpacetimeDB in 2026: Which Self-Hosted Game Backend Should You Actually Run?"
date: "2026-09-24"
tags: ["game-development", "self-hosted", "multiplayer", "backend", "docker"]
draft: false
cover: "/img/screenshots/nakama-dashboard.jpg"
---

Managed game backends price like a tax on success. PlayFab, Unity Gaming Services, and Photon all bill per monthly active user or per concurrent player — so the moment your indie project finds an audience, your infrastructure line item becomes your biggest cost. A game with 30,000 monthly players can quietly burn several hundred dollars a month before you have shipped a single cosmetic item.

The alternative is to run the backend yourself. Three open-source projects dominate that conversation in 2026, and they are **not** variations on the same idea: Nakama is a batteries-included server platform, Colyseus is a room-based state-sync framework for Node.js teams, and SpacetimeDB asks you to delete the server tier entirely.

## TL;DR: The 30-Second Verdict

- **Want accounts, matchmaking, leaderboards, chat, and storage without writing them?** → **Nakama**. You get a production game backend plus an admin console on day one.
- **Are you a TypeScript/Node shop that wants authoritative rooms as code?** → **Colyseus**. Your game logic stays in your repo, your state syncs automatically.
- **Do you want to stop operating a separate application server at all?** → **SpacetimeDB**. Your logic runs inside the database and clients subscribe directly to tables.

If you only remember one line: **Nakama for breadth, Colyseus for control, SpacetimeDB for architecture minimalism.**

## The Contenders Side by Side

All figures below were pulled live from GitHub on **September 24, 2026**:

| | **Nakama** | **Colyseus** | **SpacetimeDB** |
|---|---|---|---|
| Repository | heroiclabs/nakama | colyseus/colyseus | clockworklabs/SpacetimeDB |
| Stars | **13,402** | **7,317** | **25,241** |
| Last push | 2026-09-22 | 2026-09-23 | 2026-09-24 |
| Primary language | Go | TypeScript | Rust |
| License | Apache-2.0 | MIT | BSL 1.1 |
| Model | Authoritative server + services | Authoritative room framework | Database that is also a server |
| State sync | RPC + server-authoritative writes | Delta-compressed binary schema patches | Table subscriptions pushed to clients |
| Persistence | CockroachDB (required) | Bring your own (Postgres, Redis, etc.) | Built-in commit log, state in RAM |
| Default ports | 7349 gRPC, 7350 HTTP/WS, 7351 console | 2567 HTTP/WS | 3000 (node), CLI-managed |
| Multi-node scaling | Native cluster | Redis presence driver + LB | Native (module replicated across nodes) |
| Client SDKs | Unity, Unreal, Godot, JS, Defold, Cocos | Unity, Godot, JS/TS, React, Haxe, GameMaker, Defold, C | Rust, C#, TypeScript, C++, Unity, Godot |

## Use-Case Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Turn-based or social game with friend lists, leaderboards, IAP wallets | Nakama | These are built-in modules, not projects you schedule |
| Real-time action game, small team of Node/TS developers | Colyseus | Room + schema model maps directly onto gameplay code |
| MMO-style persistent world with heavy shared state | SpacetimeDB | State lives in one transactional store, no cache layer |
| You already run Postgres and want to keep your schema | Colyseus | No opinionated database, no migration required |
| You want the fewest moving parts to operate | SpacetimeDB | One binary replaces app server + database + replication |
| You need a web admin UI for support staff today | Nakama | Ships a real console out of the box |
| You must stay strictly MIT/Apache for commercial redistribution | Nakama or Colyseus | SpacetimeDB's BSL 1.1 has service-hosting restrictions |

## Nakama: The Batteries-Included Game Backend

Nakama is the closest thing the open-source world has to a drop-in PlayFab replacement. It is a Go server (13,402 stars, Apache-2.0) that ships accounts, authentication across a dozen providers, friends, groups, leaderboards, tournaments, matchmaking, real-time multiplayer sockets, chat, in-app purchase validation, a storage engine, and a virtual wallet — all behind one binary.

It does require CockroachDB. Here is the **official `docker-compose.yml` from the repository**, trimmed to the essentials:

```yaml
services:
  cockroachdb:
    image: cockroachdb/cockroach:latest-v24.1
    command: start-single-node --insecure --store=attrs=ssd,path=/var/lib/cockroach/
    volumes:
      - data:/var/lib/cockroach
    ports:
      - "26257:26257"
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health?ready=1"]
      interval: 3s
  nakama:
    image: registry.heroiclabs.com/heroiclabs/nakama:3.37.0
    entrypoint:
      - "/bin/sh"
      - "-ecx"
      - >
          /nakama/nakama migrate up --database.address root@cockroachdb:26257 &&
          exec /nakama/nakama --name nakama1 --database.address root@cockroachdb:26257
          --logger.level DEBUG --session.token_expiry_sec 7200 --metrics.prometheus_port 9100
    depends_on:
      cockroachdb:
        condition: service_healthy
    ports:
      - "7349:7349"
      - "7350:7350"
      - "7351:7351"
    healthcheck:
      test: ["CMD", "/nakama/nakama", "healthcheck"]
      interval: 10s
volumes:
  data:
```

Three ports matter: **7350** for the client API and real-time sockets, **7349** for gRPC, and **7351** for the operator console. The console is the reason many teams pick Nakama — player search, storage inspection, and leaderboard resets are all point-and-click:

![Nakama operator console showing players, storage, and API explorer panels](/img/screenshots/nakama-dashboard.jpg "Nakama console: player management, storage browser, and API explorer in one UI")

Server-side logic can be extended in Go, Lua, or TypeScript, and the same compose file optionally launches Prometheus on port 9090 with a scrape job already pointed at Nakama's metrics endpoint. For a small studio that needs a credible backend this week, that combination is hard to beat.

## Colyseus: Room-First State Sync for Node.js Teams

Colyseus (7,317 stars, MIT, TypeScript) takes the opposite approach: instead of shipping features, it ships a *pattern*. You define a room, define the schema of the state that room owns, and Colyseus handles matchmaking, delta-compressed binary state patches, and reconnection. Every client sees a consistent view of the authoritative state without you writing a serialization layer.

The official quickstart is two commands:

```bash
npm create colyseus-app@latest ./my-server
cd my-server
npm start
```

That scaffolds a TypeScript project with a room already wired up. A room's state is declared with schema classes, and mutations are synchronized automatically:

```ts
import { Room, Client } from "colyseus";
import { Schema, type, MapSchema } from "@colyseus/schema";

export class Player extends Schema {
  @type("number") x: number = 0;
  @type("number") y: number = 0;
}

export class GameState extends Schema {
  @type({ map: Player }) players = new MapSchema<Player>();
}

export class BattleRoom extends Room<GameState> {
  onCreate() {
    this.setState(new GameState());
  }
  onJoin(client: Client) {
    this.state.players.set(client.sessionId, new Player());
  }
  onLeave(client: Client) {
    this.state.players.delete(client.sessionId);
  }
}
```

In development, a built-in monitor panel shows live rooms, connected clients, and the traffic your schema patches generate — the fastest way to discover that you are broadcasting a 400-field state to 8 players at 30 Hz:

![Colyseus monitor panel showing live rooms and traffic metrics during a load test](/img/screenshots/colyseus-monitor.jpg "The Colyseus monitor panel: live room inspection and patch traffic metrics")

The trade-off is that Colyseus is a framework, not a platform. Accounts, friends, inventory, and purchase validation are yours to build — or to bolt on from Postgres, Redis, and your existing auth provider. It scales horizontally with a Redis presence driver plus a load balancer, which is exactly the shape a Node team already knows how to deploy.

## SpacetimeDB: When the Database Is the Server

SpacetimeDB (25,241 stars, Rust, BSL 1.1) is the most radical of the three. There is no separate application server: you upload your logic as a *module* compiled to WebAssembly, and clients connect straight to the database, call reducers, and subscribe to tables. All state is held in memory with a commit log on disk for durability, which is why Clockwork Labs runs the entire backend of its MMORPG *BitCraft Online* — chat, items, terrain, player positions — as a single module.

Installation and a local development node:

```bash
# macOS / Linux
curl -sSf https://install.spacetimedb.com | sh

# start a local node (equivalent to a self-hosted server)
spacetime start

# scaffold, build, and hot-reload a project from a template
spacetime dev --template chat-react-ts
```

A module defines tables and reducers in Rust, C#, TypeScript, or C++. The canonical Rust shape from the official README:

```rust
#[spacetimedb::table(accessor = messages, public)]
pub struct Message {
    #[primary_key]
    #[auto_inc]
    id: u64,
    sender: Identity,
    text: String,
}
```

There is also an official container image, `clockworklabs/spacetimedb`, for teams that want to run the node under Docker rather than with the install script. The architectural payoff is real: no cache layer, no cache invalidation bugs, no separate replication story for game state, and no "the websocket server and the database disagree" class of incident. The cost is that your state must fit in RAM, your logic must be deterministic inside the module, and BSL 1.1 means you cannot turn around and sell SpacetimeDB hosting as a service.

## A Self-Hosting Reality Check: Sizing and Money

The whole point of self-hosting is cost control, and the three options size very differently:

| Deployment | Practical minimum | Notes |
|---|---|---|
| Nakama + CockroachDB | 4 vCPU / 8 GB RAM, SSD | CockroachDB is the memory-hungry half |
| Colyseus | 2 vCPU / 4 GB RAM | Single process; add Redis for multi-node |
| SpacetimeDB | 4 vCPU / 8 GB+ RAM | Scale RAM with your working set, not user count |
| Managed alternative | From roughly $0.0015–$0.02 per MAU plus CCU tiers | Costs grow linearly with success |

A single mid-range VPS — the classic 4 vCPU / 8 GB class that runs €15–€25 per month — comfortably carries Nakama or SpacetimeDB for a game measured in hundreds of concurrent players, and Colyseus on the same box will idle. Compare that with a per-MAU bill and the break-even point arrives far earlier than most teams expect: for many projects it is a few thousand monthly players.

## Pitfalls and Migration Landmines

**Nakama**

- The official compose file starts CockroachDB with `--insecure` and connects as `root`. Acceptable for a local test; unacceptable for anything reachable from the internet.
- Port **7351 is an admin console**. Never expose it publicly — put it behind a VPN or an authenticated reverse proxy.
- Client SDK versions must match the server's major version. A 3.x server with an older Unity SDK produces confusing handshake failures rather than clean errors.
- Downgrading Nakama after a `migrate up` is not supported. Snapshot CockroachDB before every upgrade.

**Colyseus**

- Room state is **not** persisted. If a process dies, in-memory game state dies with it; long-lived data belongs in your own database.
- The monitor panel is a development tool. Shipping it enabled in production leaks your room structure and traffic patterns.
- A single Node process is the default. Beyond one core, plan for the Redis presence driver and sticky routing — reconnect storms are the usual first production surprise.
- Colyseus is still pre-1.0, so pin versions and read release notes before upgrading mid-project.

**SpacetimeDB**

- BSL 1.1 allows almost every use except offering a competing hosted database service. Read the license before you build a platform business on it.
- Pre-1.0 release cadence means module APIs move. Pin the CLI version in your build pipeline.
- Because state is resident in memory, instance sizing is a function of your world size, not your player count. Measure your working set before you migrate.
- Reducers must be deterministic. Anything that touches wall-clock time or external services has to be handled carefully inside the module boundary.

**Applies to all three:** never trust the client. All three push you toward an authoritative model, but a self-hosted backend is still only as cheat-resistant as the validation you actually write. Terminate TLS in front of these services — none of them ships a hardened public-facing edge by default.

## Why Self-Host Your Game Backend?

There are three durable reasons, and none of them is "it is free." First, **cost predictability**: a fixed VPS line item does not scale with a viral moment, so a launch spike is a capacity problem rather than an invoice problem. Second, **data ownership**: player accounts, match history, and telemetry stay in your database, which matters enormously when you later want to analyze retention or migrate platforms. Third, **no platform risk**: managed backends change pricing, deprecate features, and occasionally shut down; the game you shipped should not depend on a vendor's roadmap.

For the hosting layer underneath, see our [self-hosted game server platforms guide](../2026-05-07-self-hosted-game-server-platforms-minetest-openttd-openra-guide/) for how to run the game servers themselves. If you are weighing the transport underneath your real-time layer, our [Node.js realtime library comparison](../2026-09-03-nodejs-realtime-libraries-socketio-socketcluster-uwebsockets-comparison/) covers the socket-level options. And if you are writing your own client from scratch, the [WebSocket client library roundup](../2026-06-20-websocket-client-libraries-gorilla-ws-websocketclient-tokio-tungstenite/) will save you a week of evaluation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nakama vs Colyseus vs SpacetimeDB in 2026: Which Self-Hosted Game Backend Should You Actually Run?",
  "description": "A hands-on comparison of three open-source game backends in 2026: Nakama, Colyseus, and SpacetimeDB. Covers official Docker and CLI setup, live GitHub data, hosting costs, scaling limits, and migration pitfalls.",
  "datePublished": "2026-09-24",
  "dateModified": "2026-09-24",
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

### Which self-hosted game backend is cheapest to run?

For most indie projects, **Colyseus** is cheapest because it needs no database sidecar — a 2 vCPU / 4 GB instance is enough for a small real-time game. **Nakama** costs more because CockroachDB is a required dependency and wants 8 GB to breathe. **SpacetimeDB** sits in between but scales its memory requirement with your world size, so a large persistent world is the most expensive of the three to host.

### Do I need Kubernetes to self-host Nakama, Colyseus, or SpacetimeDB?

No. All three run happily on a single VPS with Docker. Kubernetes only starts to pay off past roughly 2,000–5,000 concurrent players, or when you need multi-region presence and automated failover. Nakama and SpacetimeDB both support multi-node clusters natively when you get there.

### Can I run Nakama without CockroachDB?

No. CockroachDB is Nakama's only supported storage backend and the server runs a `migrate up` step against it on boot. You can run CockroachDB as a single node for small deployments, but you cannot swap it for PostgreSQL or SQLite.

### Is SpacetimeDB really open source?

Its source is public and self-hosting is free, but it is licensed under **BSL 1.1**, not a classic open-source license. You may use it freely for your own applications, including commercial games; you may not offer it as a hosted database service that competes with the vendor's own cloud offering.

### How do I stop cheaters if I host the backend myself?

Run all authoritative logic on the server: movement validation, inventory changes, currency, and hit detection. Push only what the client needs to render. Treat every client message as hostile input, rate-limit reducers and RPCs, and audit anything that mutates a wallet or inventory. Both Nakama and Colyseus are explicitly designed around this authoritative model.

### Which one has the best Unity and Godot support?

**Nakama** has the broadest first-party SDK coverage — Unity, Unreal, Godot, Defold, Cocos, and JavaScript. **Colyseus** is nearly as broad for engine clients (Unity, Godot, Haxe, GameMaker, Defold, plus a native C static library). **SpacetimeDB** covers Rust, C#, TypeScript, C++, and Godot/Unity integrations, and is the strongest choice if your team already writes Rust or modern C#.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
