---
title: "Synapse vs Dendrite vs Continuwuity: Self-Hosted Matrix Homeserver Comparison 2026"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "messaging", "matrix", "privacy"]
draft: false
description: "Compare the three major open-source Matrix homeserver implementations — Synapse, Dendrite, and Continuwuity. Performance, features, and deployment guidance."
---

The Matrix protocol has become the leading open standard for decentralized, end-to-end encrypted communication. Unlike proprietary messaging platforms that lock you into a single provider's servers, Matrix lets you run your own homeserver, federate with the global Matrix network, and bridge to other networks including IRC, Slack, Discord, Telegram, and WhatsApp.

But choosing which Matrix homeserver to run is not straightforward. There are three major open-source implementations, each with different architectures, performance characteristics, and feature sets: **Synapse** (the reference implementation), **Dendrite** (the next-generation Go rewrite), and **Continuwuity** (the high-performance Rust fork of Conduit).

This guide compares all three to help you pick the right homeserver for your self-hosted messaging infrastructure.

## Comparison at a Glance

| Feature | Synapse | Dendrite | Continuwuity |
|---|---|---|---|
| **Language** | Python + Rust (hot paths) | Go | Rust |
| **GitHub Stars** | 4,132+ | 5,645+ | 751+ |
| **Last Active** | May 2026 | November 2024 | May 2026 |
| **Architecture** | Monolith / workers | Monolith / polylith | Monolith |
| **Database** | PostgreSQL / SQLite | PostgreSQL / SQLite | SQLite / PostgreSQL |
| **Memory Usage** | High (1-4 GB typical) | Medium (256-512 MB) | Very low (64-256 MB) |
| **Federation** | ✅ Full | ✅ Full | ✅ Full |
| **E2E Encryption** | ✅ Full | ✅ Full | ✅ Full |
| **Cross-signing** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Application Services** | ✅ Full | Limited | ❌ No |
| **MSC Support** | Extensive | Selective | Growing |
| **Admin API** | ✅ Full | Partial | Partial |
| **Registration** | Open, token, recaptcha | Open, token | Open, shared secret |
| **Space Support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **VoIP/TURN** | Via separate TURN | Via separate TURN | Via separate TURN |
| **Docker Image** | Official | Official | Community |
| **Best For** | Production, full features | Lightweight federation | Minimal resource usage |

## Synapse — The Reference Matrix Homeserver

[Synapse](https://github.com/element-hq/synapse) is the original and most feature-complete Matrix homeserver implementation, written primarily in Python with performance-critical paths optimized in Rust. It is developed by Element (the primary Matrix client developer) and serves as the reference implementation for the Matrix specification.

**Core features:**

- **Complete Matrix spec compliance** — Synapse implements the largest portion of the Matrix specification, including all stable endpoints and most Matrix Specification Changes (MSCs). It is the gold standard for spec compliance
- **Worker-based scalability** — Multi-process architecture with dedicated worker processes for federation, client API, background tasks, media repository, and push notifications. Enables horizontal scaling across multiple machines
- **Federation** — Full federation support with server-to-server communication, directory lookups, and third-party network invitations
- **End-to-end encryption** — Olm and Megolm cryptographic protocols for E2E encrypted rooms. Cross-signing for device verification, secure key backup, and in-room encryption
- **Application services** — Bridge framework for connecting Matrix to external networks (IRC, Slack, Discord, Telegram, WhatsApp, email, and more)
- **Media repository** — Built-in media storage with thumbnail generation, content scanning, and remote media caching
- **User directory** — Searchable user directory for discovering users on your homeserver and federated servers
- **Spaces** — Hierarchical room grouping for organizing communities and projects
- **Push notifications** — Push gateway integration for mobile and desktop notifications via Apple Push Notification Service (APNS), Google Firebase Cloud Messaging (FCM), and UnifiedPush
- **Admin API** — Comprehensive administrative REST API for user management, room moderation, server statistics, and federation control
- **Metrics and monitoring** — Prometheus metrics for monitoring performance, federation health, and resource usage

**Strengths:** Synapse is the most complete and battle-tested Matrix homeserver. It powers matrix.org (the largest public homeserver) and thousands of self-hosted instances worldwide. The worker architecture enables it to handle millions of users when properly scaled. It supports the widest range of Matrix features, MSCs, and application service bridges. If you need full spec compliance and the largest feature set, Synapse is the only choice.

**Limitations:** Synapse is resource-intensive. A small instance serving 10-50 users requires 1-2 GB RAM. The Python codebase, while improved with Rust optimizations, is inherently slower than Go or Rust alternatives. The worker configuration is complex for beginners. Database migrations can be slow for large instances.

### Docker Deployment for Synapse

```yaml
version: '3.8'

services:
  synapse:
    image: element-hq/synapse:latest
    ports:
      - "8008:8008"
    volumes:
      - synapse_data:/data
    environment:
      - SYNAPSE_SERVER_NAME=matrix.example.com
      - SYNAPSE_REPORT_STATS=yes
    restart: unless-stopped

volumes:
  synapse_data:
```

On first run, generate the configuration:

```bash
docker run --rm -v ./synapse_data:/data \
  -e SYNAPSE_SERVER_NAME=matrix.example.com \
  -e SYNAPSE_REPORT_STATS=yes \
  element-hq/synapse:latest generate
```

Then edit `homeserver.yaml` in the data directory to configure PostgreSQL, registration settings, and TURN server credentials. Start the server with `docker compose up -d`. Register the first user:

```bash
docker exec -it synapse register_new_matrix_user \
  http://localhost:8008 -c /data/homeserver.yaml -u admin -p <password> --admin
```

## Dendrite — The Next-Generation Go Homeserver

[Dendrite](https://github.com/matrix-org/dendrite) is a second-generation Matrix homeserver written in Go, developed by the Matrix core team. It was designed from the ground up to address Synapse's performance limitations, with a focus on efficiency, lower memory usage, and simpler deployment.

**Core features:**

- **Monolith and polylith modes** — Run as a single process (monolith) for simplicity, or split into multiple microservices (polylith) for horizontal scaling
- **Go-based performance** — Significantly lower memory footprint than Synapse. A typical instance uses 256-512 MB RAM compared to Synapse's 1-4 GB
- **Federation** — Full federation support with efficient outbound and inbound federation handling
- **End-to-end encryption** — Olm and Megolm support for E2E encrypted rooms. Cross-signing and secure key backup
- **PostgreSQL and SQLite backends** — Supports both PostgreSQL for production and SQLite for lightweight single-user deployments
- **Space support** — Matrix Spaces for organizing rooms into hierarchical groups
- **User registration** — Open registration, shared secret registration, and recaptcha support
- **Media repository** — Built-in media storage and thumbnailing
- **Admin API** — Partial admin API for user and room management

**Strengths:** Dendrite's Go implementation delivers significantly better performance per resource unit than Synapse. It is ideal for homeservers that need federation but don't require every bleeding-edge Matrix feature. The monolith mode makes deployment straightforward — a single binary with a PostgreSQL database. The polylith mode provides a path to horizontal scaling for larger deployments.

**Limitations:** Dendrite does not implement all Matrix specification features. Application services (bridges) are limited or unsupported. Some MSCs are not yet implemented. Development pace has slowed since late 2024 — the project is in maintenance mode while the Matrix team focuses on Synapse's Rust optimizations and Continuwuity's development. Some advanced admin features available in Synapse are missing.

### Docker Deployment for Dendrite

```yaml
version: '3.8'

services:
  dendrite:
    image: matrixdotorg/dendrite-monolith:latest
    ports:
      - "8009:8008"
    volumes:
      - dendrite_data:/etc/dendrite
    restart: unless-stopped

volumes:
  dendrite_data:
```

Configuration is done via `dendrite.yaml`. Key settings to configure:

```yaml
global:
  server_name: "matrix.example.com"
  
database:
  connection_string: "postgresql://dendrite:dendrite_secret@postgres/dendrite?sslmode=disable"

app_service:
  config_files:
    - /etc/dendrite/appservice/*.yaml
```

Start with `docker compose up -d` and register the first user:

```bash
docker exec -it dendrite dendrite-create-account \
  -config /etc/dendrite/dendrite.yaml -username admin -admin
```

## Continuwuity — The High-Performance Rust Homeserver

[Continuwuity](https://github.com/continuwuity/continuwuity) is the community-driven fork of Conduit, a Matrix homeserver written in Rust. It emerged when the original Conduit project's development stalled, and the community stepped in to continue development. Continuwuity prioritizes minimal resource usage, fast performance, and simplicity.

**Core features:**

- **Rust performance** — Extremely low memory footprint. A typical instance serving 10-100 users uses 64-256 MB RAM — far less than Synapse or Dendrite
- **SQLite and PostgreSQL backends** — SQLite for single-user and small deployments (zero additional database setup). PostgreSQL for larger deployments with concurrent access
- **Federation** — Full federation support with efficient server-to-server communication
- **End-to-end encryption** — Olm and Megolm cryptographic protocol support for E2E encrypted rooms
- **Space support** — Matrix Spaces for room organization
- **Minimal deployment** — Single binary, single database. No complex configuration, no worker processes, no microservice orchestration
- **Admin API** — Basic admin API for user management and server statistics
- **Media repository** — Built-in media storage
- **User registration** — Open registration and shared secret registration

**Strengths:** Continuwuity is the lightest-weight Matrix homeserver available. It is ideal for personal servers, small teams, and resource-constrained environments (Raspberry Pi, low-cost VPS). The Rust implementation delivers excellent performance with minimal overhead. The SQLite backend means you can run a complete Matrix homeserver with a single binary and a data directory — no database server needed. The active community (updated May 2026, 751+ stars) ensures ongoing development and bug fixes.

**Limitations:** Continuwuity does not support application services (bridges). Some advanced Matrix features and MSCs are not yet implemented. The admin API is more limited than Synapse. It is not suitable for large-scale deployments with thousands of users. The project is younger and has less production testing than Synapse.

### Docker Deployment for Continuwuity

```yaml
version: '3.8'

services:
  conduit:
    image: continuwuity/continuwuity:latest
    ports:
      - "8010:6167"
    environment:
      - CONDUIT_SERVER_NAME=matrix.example.com
      - CONDUIT_DATABASE_PATH=/var/lib/conduit
      - CONDUIT_DATABASE_CONNECTION_STRING=sqlite:///var/lib/conduit
      - CONDUIT_MAX_REQUEST_SIZE=20000000
      - CONDUIT_ALLOW_REGISTRATION=true
      - CONDUIT_ALLOW_FEDERATION=true
    volumes:
      - conduit_data:/var/lib/conduit
    restart: unless-stopped

volumes:
  conduit_data:
```

For SQLite-based deployments, no additional database configuration is needed. For PostgreSQL, change the connection string:

```bash
CONDUIT_DATABASE_CONNECTION_STRING=postgresql://conduit:conduit_secret@postgres/conduit
```

Register the first admin user via the admin API after starting the server:

```bash
curl -X POST http://localhost:8010/_conduit/admin/register \
  -H "Content-Type: application/json" \
  -d '{"user_id": "@admin:matrix.example.com", "password": "secure_password"}'
```

## Why Self-Host Your Messaging Server?

Running your own Matrix homeserver provides advantages no proprietary messaging platform can offer:

**Complete data ownership:** Every message, file, and metadata record lives on your hardware. No third party scans, mines, or sells your conversation patterns. You control data retention policies, backup schedules, and archival. This is critical for organizations with regulatory requirements (HIPAA, GDPR, financial compliance) or anyone who values communication privacy.

**Decentralized federation:** Matrix homeservers federate with the global Matrix network. Your users can communicate with users on any other Matrix homeserver — including matrix.org, institutional servers, and other self-hosted instances — without creating accounts on external platforms. This is the email model applied to messaging: anyone can run their own server, and everyone can communicate.

**Network bridging:** Matrix application services bridge to IRC, Slack, Discord, Telegram, WhatsApp, Signal, email, and many other networks. A single Matrix client can serve as a unified interface for all your communication channels. Synapse has the most mature bridge ecosystem, with official bridges for most major platforms.

**No vendor lock-in:** You control your server's upgrade schedule, feature set, and data retention. If a feature is missing from your chosen homeserver, you can migrate to a different implementation (all three use the same Matrix protocol) without losing your message history or user accounts.

If you're also interested in **bridging Matrix to other networks**, our [Matrix bridges guide](../2026-04-28-mautrix-whatsapp-telegram-signal-discord-self-hosted-matrix-bridges-guide-2026/) covers mautrix bridges for WhatsApp, Telegram, Signal, and Discord. For **team chat alternatives** to Slack and Microsoft Teams, our [team chat comparison](../mattermost-vs-rocketchat-vs-zulip/) and [Matrix bridges guide](../2026-04-28-mautrix-whatsapp-telegram-signal-discord-self-hosted-matrix-bridges-guide-2026/) evaluates Mattermost, Rocket.Chat, and Zulip for self-hosted workplace communication.

## Choosing the Right Homeserver

| Scenario | Recommended Homeserver |
|---|---|
| Full feature set, production deployment | Synapse — most complete spec support, largest community |
| Personal server, minimal resources | Continuwuity — lowest RAM usage, simplest deployment |
| Small team, good balance of features and resources | Dendrite — Go performance, reasonable feature set |
| Need bridges to other networks | Synapse — only one with full application service support |
| Raspberry Pi or low-cost VPS | Continuwuity — runs comfortably on 512 MB RAM |
| Large deployment (1,000+ users) | Synapse — worker-based horizontal scaling |
| Want to support Rust ecosystem | Continuwuity — actively developed in Rust |
| Need latest Matrix features/MSCs | Synapse — fastest to implement new spec features |

## FAQ

### Which Matrix homeserver should I choose for a small team (10-50 users)?

For a small team with limited server resources, **Continuwuity** is the best choice. It uses 64-256 MB RAM, deploys with a single binary and SQLite database, and supports all essential Matrix features including E2E encryption, federation, and Spaces. If you need bridge integrations (IRC, Slack, Discord), choose **Synapse** instead — it is the only homeserver with full application service support.

### Can I migrate between homeserver implementations?

Yes, but not seamlessly. All three implement the same Matrix protocol, but they use different database schemas and internal data structures. Tools like `matrix-appservice-state` and community migration scripts can export and import room state, user accounts, and message history. However, E2E encryption keys are device-specific and cannot be migrated — users will need to re-verify their devices after migration.

### Do I need a separate TURN server for voice and video calls?

Yes. Matrix voice and video calls use WebRTC, which requires a TURN/STUN server for NAT traversal when users are behind firewalls. Coturn is the most common open-source TURN server. All three homeservers can be configured to use an external TURN server — they do not include TURN functionality built in.

### How much disk space does a Matrix homeserver need?

Disk usage depends on message volume, media uploads, and federation activity:
- **Small server (10 users)**: 5-10 GB (messages + local media)
- **Medium server (100 users)**: 20-50 GB (includes federated media cache)
- **Large server (1,000+ users)**: 100+ GB (federation cache dominates)

The media repository is the primary driver of disk usage. Configure media retention policies to automatically purge old remote media.

### Can I run Matrix without federation?

Yes. All three homeservers support standalone (non-federated) mode. Disable federation in the configuration, and your server operates as a closed messaging platform. This is useful for internal team communication where external connectivity is not needed and reduces resource usage significantly.

### How do these compare to self-hosted team chat platforms?

Matrix is a federated, decentralized protocol, while platforms like Mattermost, Rocket.Chat, and Zulip are centralized team chat applications. Matrix homeservers can communicate with each other across organizations; Mattermost/Rocket.Chat/Zulip instances are siloed. Matrix has stronger E2E encryption by default. However, team chat platforms have richer workplace features (threaded conversations, integrations, channel management) out of the box. Choose Matrix for decentralized communication and team chat platforms for self-contained workplace messaging.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Synapse vs Dendrite vs Continuwuity: Self-Hosted Matrix Homeserver Comparison 2026",
  "description": "Compare the three major open-source Matrix homeserver implementations — Synapse, Dendrite, and Continuwuity. Performance, features, and deployment guidance.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
