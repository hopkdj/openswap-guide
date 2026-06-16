---
title: "Self-Hosted ActivityPub Relay Servers: ActivityRelay vs aode-relay vs Pub-Relay Compared 2026"
date: "2026-06-17"
tags: ["activitypub", "fediverse", "mastodon", "relay", "decentralization", "social-media", "docker", "self-hosted"]
draft: false
---

## Why Self-Host an ActivityPub Relay?

The Fediverse is a decentralized social network where thousands of independent servers (instances) communicate using the ActivityPub protocol. The challenge: when you start a new Mastodon, Pleroma, or Misskey instance, your federated timeline is empty. Nobody on your server follows anyone yet, so no content flows in.

ActivityPub relays solve this cold-start problem. A relay is a lightweight server that receives public posts from any subscribing instance and redistributes them to all other subscribers. By connecting your new instance to one or more relays, you immediately populate your federated timeline with content from across the Fediverse — no manual following required.

For a guide to choosing which Fediverse platform to run, see our [self-hosted Fediverse platforms comparison](../self-hosted-fediverse-mastodon-pixelfed-lemmy-guide/). If you are comparing social platform implementations, our [Misskey vs Mastodon vs Akkoma comparison](../2026-05-13-misskey-vs-mastodon-vs-akkoma-self-hosted-fediverse-social-platforms/) covers the major options.

## Comparison Table: ActivityPub Relays at a Glance

| Feature | ActivityRelay | aode-relay | Pub-Relay |
|---------|--------------|------------|-----------|
| **Language** | Go | Rust | Go |
| **Stars** | 327 | 45 | 15 |
| **Memory Usage** | ~30 MB | ~15 MB | ~20 MB |
| **Database** | Redis | SQLite | SQLite |
| **Docker Compose** | ✅ Built-in | ✅ Dockerfile | ✅ Dockerfile |
| **Relay Protocol** | LitePub + ActivityPub | ActivityPub | ActivityPub |
| **Subscriber Management** | Web dashboard | Manual config | CLI only |
| **Whitelist/Blocklist** | ✅ Both | ✅ Blocklist | ❌ |
| **Rate Limiting** | ✅ Configurable | ✅ Basic | ❌ |
| **Multiple Domains** | ✅ | ❌ | ❌ |
| **ARM Support** | ✅ | ✅ | ✅ |
| **Last Updated** | Nov 2025 | Feb 2024 | Nov 2025 |
| **License** | MIT | MIT | MIT |

## How ActivityPub Relays Work

An ActivityPub relay acts as a content redistribution hub for the Fediverse. The workflow is straightforward:

1. An instance admin adds their server to the relay (via the relay's subscription endpoint)
2. The relay accepts the subscription and begins forwarding public posts from that instance
3. When any subscribed instance publishes a public post, the relay receives it via ActivityPub
4. The relay then forwards the post to all OTHER subscribed instances
5. Users on subscriber instances see federated content in their timelines

This is fundamentally different from centralized social media algorithms — a relay does not curate, rank, or filter content. It simply redistributes everything equally.

## ActivityRelay: The Go-Powered Workhorse

ActivityRelay is the most mature and feature-rich self-hosted relay. Written in Go, it supports both the standard ActivityPub relay protocol and the lighter LitePub variant. It includes a built-in web dashboard for managing subscriptions.

**Key Features:**
- **Web dashboard**: Manage subscriptions, view statistics, configure relay settings
- **Whitelist/blocklist**: Control which instances can subscribe and which domains are excluded from forwarding
- **Multi-domain support**: Serve multiple ActivityPub domains from a single relay instance
- **Worker model**: Redis-backed worker queue with configurable concurrency
- **Health metrics**: Prometheus-compatible `/metrics` endpoint

**Docker Compose Deployment:**

```yaml
# docker-compose.yml for ActivityRelay
services:
  redis:
    restart: always
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
    volumes:
      - "./redisdata:/data"

  app:
    build:
      context: https://github.com/yukimochi/Activity-Relay.git#master
    image: yukimochi/activity-relay:latest
    working_dir: /var/lib/relay
    restart: always
    command: relay server
    ports:
      - "8080:8080"
    volumes:
      - "./actor.pem:/var/lib/relay/actor.pem"
      - "./config.yml:/var/lib/relay/config.yml"
    depends_on:
      - redis

  worker:
    image: yukimochi/activity-relay:latest
    working_dir: /var/lib/relay
    restart: always
    command: relay worker
    volumes:
      - "./actor.pem:/var/lib/relay/actor.pem"
      - "./config.yml:/var/lib/relay/config.yml"
    deploy:
      mode: replicated
      replicas: 2
    depends_on:
      - redis
```

The `config.yml` controls the relay's behavior:

```yaml
# config.yml for ActivityRelay
RELAY:
  ACTOR_PEM: /var/lib/relay/actor.pem
  RELAY_DOMAIN: relay.yourdomain.com
  SERVICENAME: "My ActivityPub Relay"
  JOB_CONCURRENCY: 50

REDIS:
  URL: redis:6379

SUBSCRIBE:
  BLOCKED_DOMAIN: []
  LIMITED_DOMAIN: []
```

After deploying, configure your Mastodon/Pleroma instance to use the relay by adding `https://relay.yourdomain.com/inbox` as a relay URL in the instance administration panel.

## aode-relay: Rust-Based Minimalist Relay

aode-relay (ActivityPub Onion Domain Enhanced Relay) is a lightweight relay written in Rust. It prioritizes minimal resource usage and straightforward configuration at the expense of a web dashboard.

**Key Features:**
- **Minimal footprint**: ~15 MB memory usage, single binary
- **SQLite storage**: No external database required
- **Blocklist support**: Prevent specific domains from relaying through your server
- **Simple configuration**: TOML-based config file with minimal options

**Docker Deployment:**

```yaml
# docker-compose.yml for aode-relay
services:
  aode-relay:
    build:
      context: https://github.com/Interstellar-Relay-Community/aode-relay.git#main
    ports:
      - "8081:8080"
    volumes:
      - "./relay-data:/app/data"
      - "./config.toml:/app/config.toml:ro"
    restart: always
```

Configuration is minimal:

```toml
# config.toml for aode-relay
[server]
bind = "0.0.0.0:8080"
domain = "relay.yourdomain.com"

[relay]
name = "My aode-relay"
description = "A lightweight ActivityPub relay"
blocked_instances = []

[database]
path = "/app/data/relay.db"
```

aode-relay is ideal for operators who want a set-and-forget relay with minimal resource overhead — perfect for Raspberry Pi deployments or small VPS instances.

## Pub-Relay: Minimalist Go Implementation

Pub-Relay (S-H-GAMELINKS/activity-pub-relay) is the newest of the three, written in Go with a focus on simplicity. It supports the ActivityPub relay protocol with minimal configuration.

**Key Features:**
- **Simple deployment**: Single binary, SQLite backend
- **Hobbyist-friendly**: Straightforward setup suitable for personal relays
- **Go standard library**: Minimal dependencies, easy to audit

**Docker Deployment:**

```yaml
# docker-compose.yml for Pub-Relay
services:
  pub-relay:
    build:
      context: https://github.com/S-H-GAMELINKS/activity-pub-relay.git#main
    ports:
      - "8082:8080"
    volumes:
      - "./relay-data:/app/data"
    environment:
      - RELAY_DOMAIN=relay.yourdomain.com
      - RELAY_NAME=My Pub-Relay
      - DATABASE_PATH=/app/data/relay.db
    restart: always
```

Pub-Relay is the simplest option for personal or small-community relays where a web dashboard is not needed.

## Choosing the Right Relay for Your Fediverse Instance

| Use Case | Recommendation | Why |
|----------|---------------|-----|
| Multi-instance operator | **ActivityRelay** | Web dashboard, multi-domain support |
| Resource-constrained VPS | **aode-relay** | 15 MB RAM, single binary, no Redis |
| Personal relay | **Pub-Relay** or **aode-relay** | Simple deployment, low maintenance |
| Public relay service | **ActivityRelay** | Blocklist/whitelist, rate limiting, metrics |

For most self-hosters running a single Mastodon or Pleroma instance, aode-relay is the sweet spot: minimal resource usage, straightforward configuration, and solid ActivityPub compliance. ActivityRelay is the choice for operators running multiple Fediverse instances or public relay services that need subscriber management and rate limiting.

## Deployment Architecture

A typical Fediverse relay deployment fits alongside your existing instance:

```
┌──────────────────┐
│ Your Mastodon    │──subscribes──▶┌─────────────┐
│ Instance         │               │ Relay       │
└──────────────────┘               │ Server      │
                                   └──────┬──────┘
┌──────────────────┐                      │
│ Other Subscriber │◀──receives posts─────┘
│ Instance         │
└──────────────────┘
```

The relay does not proxy web traffic — it only handles ActivityPub server-to-server communication. A single relay can serve dozens of subscribing instances with minimal CPU and bandwidth.

## Security and Privacy Considerations

Running a relay means you handle public posts from across the Fediverse. Key considerations:

- **Public posts only**: Relays only forward posts with "Public" visibility. Followers-only and direct messages are never relayed.
- **Blocklist maintenance**: Regularly update your blocklist to exclude spam instances and known bad actors
- **Resource consumption**: A public relay handling 100+ subscribing instances can consume significant bandwidth. Set rate limits and monitor usage.
- **No content moderation**: Relays are content-neutral — they forward everything. If you want moderation, use the blocklist feature.


## Performance Optimization for Self-Hosted Relays

Running an ActivityPub relay efficiently requires attention to a few performance details. For ActivityRelay, the worker pool size (configurable via `JOB_CONCURRENCY`) should match your CPU core count — the Go runtime handles concurrency well, but over-provisioning workers adds Redis contention without throughput gains. For aode-relay, the single-threaded Rust architecture means one relay instance can handle approximately 2,000-3,000 federation requests per minute, which is sufficient for all but the largest public relay services. Pub-Relay benefits from Go's lightweight goroutines and typically processes 1,500-2,500 requests per minute on modest hardware.

All three relays benefit from placing Redis (ActivityRelay) or SQLite databases (aode-relay, Pub-Relay) on fast NVMe storage. Federation traffic is bursty — most instances publish content during their local daytime hours — so provision CPU and bandwidth for peak rather than average loads. A typical relay serving 30-50 instances uses about 1-2 GB RAM and 50-200 GB of monthly bandwidth.


## FAQ

### Do I need a relay if I run a personal Mastodon instance?

Not strictly necessary, but strongly recommended. Without a relay, your federated timeline starts empty. You would need to manually search for and follow accounts on other instances to populate it. A relay gives you immediate content discovery, which is essential for a satisfying Fediverse experience.

### Can I run multiple relays for the same instance?

Yes. You can subscribe your instance to multiple relays simultaneously. Most instance admins connect to 2-3 public relays for redundancy and broader content coverage. Just be mindful of the additional bandwidth and processing overhead.

### How do relays differ from Nostr relays?

ActivityPub relays and Nostr relays serve similar purposes (content redistribution) but for completely different protocols. ActivityPub relays are for the Fediverse (Mastodon, Pleroma, Misskey) while Nostr relays serve the Nostr protocol. They are not interoperable. For Nostr relay hosting, see our [self-hosted Nostr relays guide](../2026-06-06-self-hosted-nostr-relays-strfry-nostream-nostr-rs-relay/).

### What is the typical bandwidth usage of a relay?

A relay serving 20-50 subscribing instances typically uses 50-200 GB/month in bandwidth, depending on instance sizes and activity. Most of this is outbound traffic (forwarding posts to subscribers). Use a VPS with unmetered bandwidth or monitor usage carefully on metered plans.

### Can ActivityPub relays forward to non-Mastodon software?

Yes. ActivityRelay, aode-relay, and Pub-Relay all implement standard ActivityPub, which is compatible with any ActivityPub-compliant software: Mastodon, Pleroma, Misskey, Akkoma, Pixelfed, PeerTube, Friendica, and WriteFreely.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ActivityPub Relay Servers: ActivityRelay vs aode-relay vs Pub-Relay Compared 2026",
  "description": "Compare self-hosted ActivityPub relay servers for the Fediverse. Deep dive into ActivityRelay (Go), aode-relay (Rust), and Pub-Relay with Docker Compose deployment guides, comparison tables, and Fediverse infrastructure recommendations.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
