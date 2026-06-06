---
title: "Self-Hosted Nostr Relays: strfry vs nostream vs nostr-rs-relay — Run Your Own Decentralized Social Infrastructure"
date: "2026-06-06"
tags: ["self-hosted", "nostr", "decentralized", "social-media", "relay", "federation", "privacy", "bitcoin"]
draft: false
---

## Introduction

Nostr (Notes and Other Stuff Transmitted by Relays) is a radically simple, decentralized protocol for social networking. Unlike federated platforms like Mastodon that require you to pick a server and trust its administrator, Nostr separates identity from infrastructure: you own your cryptographic keypair, and relays are dumb message forwarders with no authority over your identity. Anyone can run a relay, and the more relays exist, the more resilient the network becomes.

Running your own Nostr relay gives you complete sovereignty over your social graph data. You control retention policies, rate limits, and who can write to your relay. Whether you're an individual who wants to self-host your social footprint or a community operator who wants to provide infrastructure for others, the relay software ecosystem has matured to the point where deployment takes minutes, not days.

In this guide, we compare three leading open-source Nostr relay implementations — **strfry**, **nostream**, and **nostr-rs-relay** — across performance, resource usage, features, and ease of deployment.

## Comparison Table

| Feature | strfry | nostream | nostr-rs-relay |
|---------|--------|----------|----------------|
| Language | C++ | TypeScript (Node.js) | Rust |
| Stars | 676 | 814 | 698 |
| NIP Support | NIP-01, 02, 04, 09, 11, 12, 15, 16, 20, 22, 26, 28, 33, 40, 42 | NIP-01, 02, 04, 09, 11, 12, 15, 16, 20, 22, 28, 33, 40 | NIP-01, 02, 04, 09, 11, 12, 15, 16, 20, 22, 28, 33, 40 |
| Database | LMDB (embedded) | PostgreSQL, SQLite, MySQL | SQLite |
| Docker Support | Yes (official image) | Yes (official image) | Yes (community) |
| Memory Usage | ~50MB base | ~150MB base | ~30MB base |
| Write Speed | Fastest (C++/LMDB) | Moderate (Node.js) | Fast (Rust/SQLite) |
| Auth (NIP-42) | Yes | Yes | Yes |
| Rate Limiting | Built-in | Built-in | Via reverse proxy |
| WebSocket | Native | Native | Native |
| Configuration | Single config file | Environment variables | Single TOML config |
| Community | Active (sourcehut) | Active (GitHub) | Active (sourcehut) |

## strfry: The Performance King

[strfry](https://github.com/hoytech/strfry) is a C++ Nostr relay designed for raw speed and minimal resource consumption. It uses LMDB (Lightning Memory-Mapped Database) as its storage backend, which means zero-configuration, zero-maintenance, and incredible read/write performance — LMDB is the same engine that powers OpenLDAP.

strfry's standout features include pluggable write policies (you can write custom JavaScript plugins to filter or transform events before they're stored), built-in NIP-42 authentication, and a powerful `strfry sync` command that lets you mirror another relay's data. The sync feature is particularly useful if you want to bootstrap a new relay with existing content.

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  strfry:
    image: ghcr.io/hoytech/strfry:latest
    container_name: strfry
    restart: unless-stopped
    ports:
      - "7777:7777"
    volumes:
      - ./strfry-data:/app/strfry-db
      - ./strfry.conf:/etc/strfry.conf:ro
    environment:
      - DB_PATH=/app/strfry-db
```

strfry's memory footprint is exceptionally low — around 50MB at idle — making it ideal for Raspberry Pi deployments or resource-constrained VPS instances. For production use, placing it behind nginx or Caddy with SSL termination is recommended.

## nostream: The Feature-Rich TypeScript Option

[nostream](https://github.com/Cameri/nostream) (formerly nostr-ts-relay) is a TypeScript implementation that prioritizes flexibility and database portability. Written in Node.js, it supports PostgreSQL, MySQL, and SQLite backends, letting you choose the database that fits your existing infrastructure.

Where nostream shines is in its plugin system and maintenance tooling. It includes a built-in database migration system, WebSocket authentication with NIP-42, and comprehensive logging. The TypeScript codebase is also approachable for JavaScript developers who want to customize their relay behavior.

**Docker Compose deployment with PostgreSQL:**

```yaml
version: "3.8"
services:
  nostream-db:
    image: postgres:16-alpine
    container_name: nostream-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: nostream
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: nostream
    volumes:
      - ./postgres-data:/var/lib/postgresql/data

  nostream:
    image: ghcr.io/cameri/nostream:latest
    container_name: nostream
    restart: unless-stopped
    ports:
      - "8008:8008"
    depends_on:
      - nostream-db
    environment:
      DB_HOST: nostream-db
      DB_PORT: 5432
      DB_USER: nostream
      DB_PASSWORD: changeme
      DB_NAME: nostream
      RELAY_URL: wss://relay.yourdomain.com
      RELAY_NAME: My Nostr Relay
      RELAY_PUBKEY: "your-relay-pubkey"
      RELAY_DESCRIPTION: "A self-hosted Nostr relay"
```

nostream uses more memory than strfry (~150MB base for Node.js) but offers superior observability with structured logging and Prometheus metrics export. If you're already running a PostgreSQL cluster, nostream integrates seamlessly into your existing infrastructure.

## nostr-rs-relay: The Rust Minimalist

[nostr-rs-relay](https://sr.ht/~gheartsfield/nostr-rs-relay/) is a Rust implementation that prioritizes simplicity, correctness, and low resource usage. It uses SQLite as its only storage backend and compiles to a single static binary — no runtime dependencies required.

nostr-rs-relay is the most "boring" option, which in infrastructure terms is a compliment. It does one thing — relay Nostr events — and does it reliably. The SQLite backend means zero external database dependencies, and the Rust binary uses about 30MB of memory at idle.

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  nostr-rs-relay:
    image: scsibug/nostr-rs-relay:latest
    container_name: nostr-rs-relay
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./nostr-data:/usr/src/app/db
      - ./config.toml:/usr/src/app/config.toml:ro
```

Configuration is handled through a single TOML file where you define rate limits, event limits, and database path. The minimalism means fewer features — no built-in authentication, no plugin system — but also fewer things to break.

## Reverse Proxy Configuration (Caddy)

Regardless of which relay you choose, you'll need a reverse proxy for SSL termination. Here's a Caddy configuration that works with any of the three relays:

```caddyfile
relay.yourdomain.com {
    reverse_proxy localhost:7777
    header {
        Access-Control-Allow-Origin *
    }
}
```

For nostream (port 8008) or nostr-rs-relay (port 8080), adjust the `reverse_proxy` target accordingly.

## Why Self-Host Your Nostr Relay?

Running your own Nostr relay is fundamentally different from using a hosted service. When you rely on someone else's relay, they control what events they store, how long they retain them, and whether they stay online. Running your own relay means you're contributing to the network's decentralization while maintaining full control over your data.

Unlike centralized platforms where your account can be deplatformed, Nostr's cryptographic identity model means no relay can ban you — they can only refuse to serve your events, and if your own relay carries them, other relays that sync from you will propagate them. This is a fundamentally different trust model from both centralized platforms and federated systems.

For community operators, running a relay provides infrastructure for your local community without depending on third-party services. For developers building Nostr applications, having your own relay gives you complete control over the data layer for testing and production. For those interested in related decentralized infrastructure, see our [Matrix server comparison guide](../2026-05-02-synapse-vs-dendrite-vs-conduwuit-self-hosted-matrix-server-guide/). If you're evaluating broader decentralized social platforms, our [Fediverse platform comparison](../2026-05-13-misskey-vs-mastodon-vs-akkoma-self-hosted-fediverse-social-platforms/) and [decentralized storage guide](../2026-04-25-ipfs-vs-storj-vs-sia-self-hosted-decentralized-storage-guide-2026/) provide additional context on self-hosted decentralized infrastructure.

## Choosing the Right Relay

Your choice depends primarily on your infrastructure preferences:

- **Choose strfry if**: You want maximum performance with minimum resources. strfry's C++/LMDB stack is essentially unmatched for raw event throughput, and the sync feature makes it easy to mirror other relays. It's the best choice for a personal relay or a relay that needs to handle high traffic on modest hardware.

- **Choose nostream if**: You're comfortable with the Node.js ecosystem and want database flexibility. The PostgreSQL backend means you can leverage existing database clusters and backup infrastructure. nostream is ideal if you're already running other TypeScript/Node.js services and want consistent tooling.

- **Choose nostr-rs-relay if**: You value simplicity above all else. The single-binary, SQLite-only approach means there's almost nothing to maintain. It's the best choice for a "set it and forget it" relay that just works.

## FAQ

### What hardware do I need to run a Nostr relay?

A basic VPS with 1GB RAM and 20GB storage can handle all three relays comfortably. strfry and nostr-rs-relay can even run on a Raspberry Pi 4. Storage usage depends on how many events you store and your retention policy — plan for 10-50GB for a relay that retains events for several months. LMDB (strfry) and SQLite (nostr-rs-relay) are more storage-efficient than PostgreSQL (nostream) for equivalent event volumes.

### Can I run multiple relays on the same server?

Yes. All three relays can coexist on the same machine if you assign them different ports. You can use a reverse proxy like Caddy or nginx to route traffic to different relays based on the hostname or path. This is common for operators who want to run a public relay and a private/paid relay on the same infrastructure.

### How do Nostr relays handle spam and abuse?

NIP-42 authentication allows relays to require clients to authenticate before publishing events. strfry includes pluggable write policies that can filter events based on content, pubkey, or other criteria. nostream and nostr-rs-relay rely on reverse proxy rate limiting or external authentication layers. For production relays, combining NIP-42 with rate limiting at the reverse proxy level is the recommended approach.

### Do I need to open my relay to the public internet?

No. You can run a private relay that only you and trusted peers access, either through a VPN, firewall rules, or by keeping it on your local network. Many users run a personal relay exclusively for their own events and selectively sync from public relays. This is the most privacy-preserving configuration.

### What happens if my relay goes offline?

Nothing catastrophic — your identity and social graph are not tied to any single relay. Nostr clients typically connect to multiple relays simultaneously, so your followers will still see your events through other relays. When your relay comes back online, clients will reconnect and sync any missed events.

### How does Nostr compare to ActivityPub (Mastodon) or Matrix?

Nostr is simpler than both. ActivityPub requires server-to-server federation and places trust in server operators. Matrix uses a homeserver model with room state replication, which is more complex. Nostr relays are "dumb pipes" — they simply accept and forward events without interpreting them. This architectural simplicity makes Nostr relays much easier to operate than Mastodon instances or Matrix homeservers. For a deeper comparison, see our guides on [Matrix servers](../2026-05-02-synapse-vs-dendrite-vs-conduwuit-self-hosted-matrix-server-guide/) and [Fediverse platforms](../2026-05-13-misskey-vs-mastodon-vs-akkoma-self-hosted-fediverse-social-platforms/).

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform, where you can bet on everything from election results to technology regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've made good returns predicting technology-related event outcomes. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Nostr Relays: strfry vs nostream vs nostr-rs-relay — Run Your Own Decentralized Social Infrastructure",
  "description": "Comprehensive comparison of three leading open-source Nostr relay implementations: strfry (C++/LMDB), nostream (TypeScript/PostgreSQL), and nostr-rs-relay (Rust/SQLite). Includes Docker Compose deployment, performance analysis, and Caddy reverse proxy configuration.",
  "datePublished": "2026-06-06",
  "dateModified": "2026-06-06",
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
