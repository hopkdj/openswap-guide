---
title: "Mautrix WhatsApp vs Telegram vs Signal vs Discord: Self-Hosted Matrix Bridges 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "messaging", "matrix"]
draft: false
description: "Complete guide to deploying self-hosted Matrix bridges with the mautrix project. Compare WhatsApp, Telegram, Signal, and Discord bridges with Docker Compose configs, setup instructions, and feature comparisons."
---

The [Mautrix](https://github.com/mautrix) project provides a family of open-source bridge applications that connect the Matrix protocol to external messaging platforms. By deploying these bridges on your own infrastructure, you can unify WhatsApp, Telegram, Signal, Discord, and other services through a single Matrix client like Element — without handing your conversation metadata to third-party cloud providers.

## Why Self-Host Matrix Bridges

Matrix is an open, federated protocol for real-time communication. Its strength lies in interoperability: through application service bridges (commonly called "appservice bridges"), a Matrix homeserver can relay messages to and from other platforms. The mautrix bridges are among the most actively maintained in this ecosystem, all written in Go (with some Python-based legacy bridges), sharing a common architecture and configuration pattern.

Self-hosting your bridges gives you several advantages:

- **Full data control**: Bridge traffic passes through your server. No third-party server processes or stores your message routing metadata.
- **Unified inbox**: Connect all your messaging accounts to a single Matrix client. One interface for WhatsApp, Telegram, Signal, Discord, and more.
- **End-to-end encryption**: Messages bridged through Matrix can maintain E2EE where the underlying platform supports it (Signal, WhatsApp via QR code pairing).
- **Backup and archiving**: All bridged conversations are stored in your homeserver's database, searchable and exportable.
- **No vendor lock-in**: If one platform shuts down or bans your account, your conversation history remains in Matrix.

For a complete guide to setting up your own Matrix homeserver, see our [Matrix Synapse self-hosted messaging guide](../matrix-synapse-self-hosted-messaging-guide/).

## Mautrix Bridge Ecosystem Overview

The mautrix project maintains bridges for the most popular messaging platforms. Here is a comparison of the four primary bridges that are actively developed and suitable for self-hosting:

| Feature | mautrix-whatsapp | mautrix-telegram | mautrix-signal | mautrix-discord |
|---------|-----------------|------------------|----------------|-----------------|
| GitHub Stars | 1,756 | 1,669 | 646 | 446 |
| Last Updated | 2026-04-24 | 2026-04-27 | 2026-04-16 | 2026-04-21 |
| Language | Go | Go | Go | Go |
| License | AGPL-3.0 | AGPL-3.0 | AGPL-3.0 | AGPL-3.0 |
| Docker Image | `ghcr.io/mautrix/whatsapp` | `ghcr.io/mautrix/telegram` | `ghcr.io/mautrix/signal` | `ghcr.io/mautrix/discord` |
| Auth Method | QR code scan | Phone number + code | Phone number + linking | Bot token |
| E2EE Support | Yes (via phone) | Yes (secret chats) | Yes (native) | No (Discord lacks E2EE) |
| Media Bridging | Yes | Yes | Yes | Yes |
| Group Chat Bridge | Yes | Yes | Yes | Yes (servers/channels) |
| Backfill History | Yes | Yes | Limited | Yes |
| Puppeting Mode | Yes | Yes | Yes | Yes |
| Relay Bot Mode | Yes | Yes | Yes | Yes |

In addition to these four, the mautrix project also maintains bridges for Meta Messenger/Instagram (combined as `mautrix-meta`, 361 stars), Google Chat (122 stars), iMessage (macOS-only), Slack, and Hangouts. These are either less actively maintained or have platform-specific limitations.

If you're looking at other messaging self-hosting options, our guide to [Mattermost vs Rocket.Chat vs Zulip](../mattermost-vs-rocketchat-vs-zulip/) covers self-hosted team chat platforms that also support Matrix federation.

## Bridge Architecture: How Mautrix Bridges Work

All mautrix bridges share the same architectural pattern. They run as separate services alongside your Matrix homeserver and communicate through the Matrix Application Service API. Here is how the data flows:

1. **User authenticates** to the bridge (QR code for WhatsApp, phone verification for Telegram/Signal, bot token for Discord).
2. **Bridge registers** with the homeserver via a registration YAML file that defines event filters and webhook endpoints.
3. **Bridge creates portal rooms** in Matrix for each conversation (DMs, groups, channels).
4. **Messages flow bidirectionally**: messages from the external platform appear in Matrix rooms, and Matrix messages are relayed back to the external platform.
5. **User state is ghosted**: each external user appears as a "ghost user" in Matrix, allowing direct addressing and proper message attribution.

There are two operational modes:

- **Puppeting**: The bridge logs in as your actual user on the external platform. All your contacts see messages coming from you. This is the most common mode.
- **Relay bot**: The bridge operates as a bot account on the external platform. Messages from Matrix users are relayed through the bot's identity. Useful for community channels where multiple Matrix users share one external platform connection.

## Docker Compose Deployment

The mautrix bridges are distributed as Docker images and follow a consistent deployment pattern. Each bridge requires:

- A data volume for configuration and database files
- Network access to your Matrix homeserver
- Port exposure for the appservice listener (default ports vary per bridge)

Here is a complete Docker Compose setup for deploying the WhatsApp and Telegram bridges together:

```yaml
version: "3.8"

services:
  mautrix-whatsapp:
    image: ghcr.io/mautrix/whatsapp:latest
    container_name: mautrix-whatsapp
    restart: unless-stopped
    volumes:
      - ./whatsapp-data:/data
    ports:
      - "29318:29318"
    networks:
      - matrix-net
    depends_on:
      - postgres

  mautrix-telegram:
    image: ghcr.io/mautrix/telegram:latest
    container_name: mautrix-telegram
    restart: unless-stopped
    volumes:
      - ./telegram-data:/data
    ports:
      - "29317:29317"
    networks:
      - matrix-net
    depends_on:
      - postgres

  mautrix-signal:
    image: ghcr.io/mautrix/signal:latest
    container_name: mautrix-signal
    restart: unless-stopped
    volumes:
      - ./signal-data:/data
    ports:
      - "29320:29320"
    networks:
      - matrix-net
    depends_on:
      - postgres

  mautrix-discord:
    image: ghcr.io/mautrix/discord:latest
    container_name: mautrix-discord
    restart: unless-stopped
    volumes:
      - ./discord-data:/data
    ports:
      - "29334:29334"
    networks:
      - matrix-net
    depends_on:
      - postgres

  postgres:
    image: postgres:16-alpine
    container_name: matrix-bridges-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: mautrix
      POSTGRES_PASSWORD: change-this-to-a-strong-password
      POSTGRES_DB: mautrix_bridges
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - matrix-net

volumes:
  postgres-data:

networks:
  matrix-net:
    driver: bridge
```

## Initial Configuration

When you start a mautrix bridge container for the first time, it generates a default `config.yaml` in the data directory. You need to edit this file before starting the bridge properly. Here is the critical configuration section for any mautrix bridge:

```yaml
# Homeserver connection
homeserver:
    address: https://matrix.example.com
    domain: example.com
    software: standard

# Appservice listener
appservice:
    address: http://mautrix-whatsapp:29318
    hostname: 0.0.0.0
    port: 29318

    database:
        type: postgres
        uri: postgres://mautrix:change-this-to-a-strong-password@postgres/mautrix_bridges?sslmode=disable
        max_open_conns: 20

    bot:
        username: whatsappbot
        displayname: WhatsApp Bridge Bot

# Bridge settings
bridge:
    username_template: whatsapp_{{.}}
    displayname_template: "{{or .Name .JID}}"
    double_puppet_server_map:
        example.com: https://matrix.example.com
    encryption:
        allow: true
        default: true
```

After editing the config, restart the container. It will generate a `registration.yaml` file that you must copy to your homeserver's appservice directory and reference in your homeserver config. For Synapse, add to `homeserver.yaml`:

```yaml
app_service_config_files:
    - /data/appservices/mautrix-whatsapp-registration.yaml
    - /data/appservices/mautrix-telegram-registration.yaml
    - /data/appservices/mautrix-signal-registration.yaml
    - /data/appservices/mautrix-discord-registration.yaml
```

Then restart Synapse to load the bridges.

## Bridge-Specific Setup Notes

### WhatsApp Bridge

The WhatsApp bridge uses QR code authentication, similar to WhatsApp Web. After starting the bridge, open the bot room in your Matrix client and send `!wa login`. The bridge responds with a QR code that you scan using WhatsApp on your phone. Once authenticated, all your WhatsApp contacts and groups appear as Matrix rooms.

Key considerations:
- Requires a linked phone; the bridge does not work as a standalone WhatsApp account.
- Multi-device support is fully implemented; you can use the bridge while your phone is offline.
- Media bridging works for images, videos, documents, and voice messages.

### Telegram Bridge

The Telegram bridge requires a Telegram API ID and hash, which you obtain from [my.telegram.org](https://my.telegram.org/apps). Create a new application, note the `api_id` and `api_hash`, and add them to your bridge config:

```yaml
bridge:
    relaybot:
        auth_key: ""
    telegram_api_id: YOUR_API_ID
    telegram_api_hash: YOUR_API_HASH
```

Authentication is done by sending `!tg login` to the bot room, then providing your phone number and the verification code Telegram sends via SMS or to the official Telegram app.

The Telegram bridge has the most mature feature set among all mautrix bridges, with excellent support for topics, formatted messages, stickers, and animated emoji.

### Signal Bridge

The Signal bridge is the simplest to set up. Send `!signal login` to the bot room, provide your phone number, and enter the verification code sent via SMS. The bridge links to your existing Signal account.

Important notes:
- Signal's strict rate limits mean the bridge can occasionally be slow to deliver messages during high-traffic periods.
- The Signal bridge supports the latest Signal protocol version and maintains full end-to-end encryption.
- Contact discovery works through your phone's contact list synced to the bridge.

### Discord Bridge

The Discord bridge operates differently from the others. Instead of linking a personal account, it requires a Discord bot token that you create through the [Discord Developer Portal](https://discord.com/developers/applications). This means the bridge acts as a bot on Discord servers rather than impersonating a user.

Setup steps:
1. Create a Discord application and bot in the Developer Portal.
2. Copy the bot token into your bridge config.
3. Invite the bot to your Discord servers.
4. The bridge creates Matrix portal rooms for each Discord channel.

This approach has advantages and tradeoffs:
- **Advantage**: No risk of account bans; the bot uses official Discord API access.
- **Tradeoff**: The bot cannot read messages from channels where it lacks permission, and it cannot see user status or presence information the same way a user account could.

## Comparison with Alternative Bridge Projects

While mautrix is the most comprehensive bridge ecosystem, other Matrix bridge projects exist:

| Project | Platforms Covered | Language | Activity Level | Docker Support |
|---------|------------------|----------|---------------|----------------|
| mautrix bridges | WhatsApp, Telegram, Signal, Discord, Meta, Google Chat, iMessage, Slack | Go/Python | Very Active | Official images |
| matrix-appservice-irc | IRC networks | TypeScript/JS | Active | Community images |
| matrix-appservice-slack | Slack | TypeScript/JS | Maintenance mode | Community images |
| beeper bridges | Multiple (commercial) | Mixed | Active | Not self-hostable |
| double-puppet (half-shot) | Discord (legacy) | TypeScript/JS | Inactive | No |

For IRC bridging, which uses a different architecture, see our comprehensive guide to [self-hosted IRC servers and bouncers](../self-hosted-irc-server-bouncer-web-client-the-lounge-znc-ergo-guide-2026/).

## Resource Requirements

Each mautrix bridge is lightweight:

- **CPU**: Minimal; typically under 5% of a single core for normal usage.
- **Memory**: 100-300 MB per bridge process depending on the number of active connections and rooms.
- **Storage**: 50-500 MB for the database, depending on message backfill depth.
- **Network**: Low bandwidth; messages are small and infrequent compared to media streaming.

A single modest VPS (2 cores, 2 GB RAM) can comfortably run a Synapse homeserver plus four mautrix bridges simultaneously.

## Troubleshooting Common Issues

**Bridge not responding to commands**: Check that the registration file was correctly placed in your homeserver's appservice directory and that Synapse was restarted after adding it. Verify with `curl http://localhost:29318/health` (adjust port per bridge).

**Duplicate messages**: This happens when double puppeting is misconfigured. Ensure the `double_puppet_server_map` in your bridge config points to the correct homeserver URL and that the `allow_discovery` setting is enabled on your homeserver.

**Media not bridging**: Media bridging requires the bridge to have network access to both the Matrix media repository and the external platform's media servers. Check that no firewall rules block outbound HTTPS traffic from the bridge container.

**Database connection failures**: The mautrix bridges support both SQLite and PostgreSQL. For production use, PostgreSQL is strongly recommended. Verify the database URI in your config and ensure the Postgres container is running and accessible from the bridge network.

For more on voice communication alternatives that you might want to bridge alongside these services, our comparison of [Mumble vs TeamSpeak vs Jamulus](../2026-04-21-mumble-vs-teamspeak-vs-jamulus-self-hosted-voice-chat-2026/) covers self-hosted voice chat options.

## FAQ

### What is a Matrix bridge and why would I use one?

A Matrix bridge is a service that connects the Matrix protocol to another messaging platform (WhatsApp, Telegram, Signal, Discord, etc.). It allows you to use a single Matrix client like Element to send and receive messages across all your messaging accounts. You would use one if you want a unified inbox for all your conversations while keeping your data under your own control.

### Do mautrix bridges support end-to-end encryption?

Yes, most mautrix bridges support Matrix's native Megolm E2EE encryption for portal rooms. The WhatsApp and Signal bridges can also leverage the underlying platform's encryption. Telegram's "secret chats" are not supported because the Telegram Bot API does not expose them, but regular Telegram cloud chats are bridged with Matrix-side encryption.

### Can I run multiple mautrix bridges on the same server?

Absolutely. Each bridge is an independent service with its own Docker container, database schema, and port. You can run all mautrix bridges on the same server alongside your Matrix homeserver. Just ensure each bridge uses a unique port and database table prefix, as shown in the Docker Compose example above.

### What happens if the external platform bans my account?

If you are using puppeting mode (WhatsApp, Telegram, Signal) and the external platform bans or suspends your account, the bridge will lose its connection. Your Matrix-side conversation history is preserved in the homeserver, but you will no longer be able to send or receive messages on that platform through the bridge. The Discord bridge uses a bot token, so your personal Discord account is not at risk.

### How do I migrate between Matrix homeservers with bridges installed?

You need to re-register each bridge with the new homeserver. Copy the registration YAML files to the new homeserver, update the `homeserver.address` field in each bridge's config to point to the new homeserver, and restart the bridges. Portal rooms and bridged history are preserved since they are stored in the bridge's own database, not the homeserver's.

### Is there a limit to how many bridges I can use?

There is no technical limit imposed by the mautrix project or Matrix protocol. Each bridge runs independently, so the only constraints are your server's resources (CPU, memory, storage). In practice, running 5-6 bridges on a single server is well within the capacity of a standard VPS.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Mautrix WhatsApp vs Telegram vs Signal vs Discord: Self-Hosted Matrix Bridges 2026",
  "description": "Complete guide to deploying self-hosted Matrix bridges with the mautrix project. Compare WhatsApp, Telegram, Signal, and Discord bridges with Docker Compose configs, setup instructions, and feature comparisons.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
