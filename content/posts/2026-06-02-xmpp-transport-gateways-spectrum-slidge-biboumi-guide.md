---
title: "Self-Hosted XMPP Transport Gateways: Spectrum 2 vs Slidge vs Biboumi"
date: "2026-06-02"
tags: ["xmpp", "gateway", "messaging", "federation", "chat", "irc", "transport", "self-hosted"]
draft: false
---

XMPP (Extensible Messaging and Presence Protocol) has a unique advantage in the messaging ecosystem: transport gateways that bridge XMPP to other protocols, allowing users to communicate across networks from a single XMPP client. Rather than running separate clients for IRC, Telegram, WhatsApp, Discord, and other services, XMPP transport gateways let you consolidate all your conversations into one interface while maintaining control over your infrastructure. This guide compares the three leading self-hosted XMPP gateway frameworks: Spectrum 2, Slidge, and Biboumi.

## Spectrum 2: The Battle-Tested Transport Framework

Spectrum 2 is a mature XMPP transport framework that has been in development for over a decade. It provides a modular architecture where each protocol is implemented as a separate backend process, communicating with the main Spectrum instance via a defined API. Spectrum 2 ships with backends for IRC, Telegram, Discord, Facebook Messenger, and many other protocols.

The architecture uses a main daemon (`spectrum2_manager`) that loads individual transport backends. Each backend runs as a separate process for fault isolation — a crash in the IRC backend won't affect your Telegram bridge. Configuration is XML-based and stored per-transport:

```xml
<!-- /etc/spectrum2/transports/irc.cfg -->
<config>
  <jid>irc.example.com</jid>
  <server>irc.libera.chat</server>
  <port>6697</port>
  <tls>true</tls>
  <identify>true</identify>
</config>
```

Docker deployment uses the official image:

```yaml
# docker-compose.yml for Spectrum 2 with IRC and Telegram backends
version: "3.8"
services:
  spectrum2:
    image: spectrum2/spectrum2:latest
    container_name: spectrum2
    restart: unless-stopped
    ports:
      - "5347:5347"
    volumes:
      - ./spectrum2-data:/var/lib/spectrum2
      - ./spectrum2-config:/etc/spectrum2:ro
    environment:
      - SPECTRUM2_DB_TYPE=sqlite3

  spectrum2-irc:
    image: spectrum2/backend-irc:latest
    restart: unless-stopped
    volumes:
      - ./transports/irc.cfg:/etc/spectrum2/transports/irc.cfg:ro
    depends_on:
      - spectrum2

  spectrum2-telegram:
    image: spectrum2/backend-telegram:latest
    restart: unless-stopped
    volumes:
      - ./transports/telegram.cfg:/etc/spectrum2/transports/telegram.cfg:ro
    depends_on:
      - spectrum2
```

## Slidge: The Modern Gateway Framework

Slidge (Slick XMPP Gateway) is a newer framework that takes a fundamentally different approach to bridging. Instead of running separate backend processes, Slidge plugins are loaded directly into the gateway process using Python's plugin architecture. Each plugin handles the protocol-specific logic — authentication, message translation, presence synchronization — while Slidge manages the XMPP communication layer.

Slidge's design emphasizes simplicity and modern development practices. Plugins are Python packages installed via pip, and configuration is done through a single YAML file. The framework currently supports WhatsApp, Telegram, Discord, Signal, Facebook Messenger, Steam, and more through community plugins.

Key architectural differences from Spectrum 2:
- Single-process design reduces operational overhead
- Python plugin system enables rapid protocol development
- Automatic avatar and media synchronization
- Built-in support for message reactions and replies
- Native multi-account support per plugin

Installation and basic configuration:

```bash
# Install Slidge core and desired plugins
pip install slidge[all]

# Minimal configuration (slidge.yml)
# server: example.com
# xmpp:
#   jid: gateway.example.com
#   secret: your-component-secret
# plugins:
#   telegram:
#     enabled: true
```

Docker Compose for a Slidge setup:

```yaml
# docker-compose.yml for Slidge with Prosody XMPP server
version: "3.8"
services:
  prosody:
    image: prosody/prosody:latest
    container_name: prosody
    restart: unless-stopped
    ports:
      - "5222:5222"
      - "5269:5269"
    volumes:
      - ./prosody-data:/var/lib/prosody
      - ./prosody-config:/etc/prosody:ro

  slidge:
    image: nicocool84/slidge:latest
    container_name: slidge
    restart: unless-stopped
    volumes:
      - ./slidge-data:/var/lib/slidge
      - ./slidge.yml:/etc/slidge/slidge.yml:ro
    depends_on:
      - prosody
```

## Biboumi: The IRC Specialist

Biboumi takes a focused approach — it bridges exactly one protocol: IRC. This narrow scope allows Biboumi to excel at IRC-specific features that general-purpose gateways often struggle with, including proper channel mode synchronization, IRC network-specific quirks, SASL authentication, and multi-network connectivity.

Unlike Spectrum 2 and Slidge, which connect one XMPP user to one account per protocol, Biboumi connects an entire XMPP domain to IRC networks. Each IRC channel appears as a Multi-User Chat (MUC) room in XMPP, and users join by simply entering the room. Biboumi handles the IRC connection pooling, nick management, and channel state transparently:

```yaml
# docker-compose.yml for Biboumi
version: "3.8"
services:
  biboumi:
    image: biboumi/biboumi:latest
    container_name: biboumi
    restart: unless-stopped
    volumes:
      - ./biboumi-data:/var/lib/biboumi
      - ./biboumi.cfg:/etc/biboumi/biboumi.cfg:ro
    ports:
      - "5347:5347"
```

A basic Biboumi configuration for connecting to multiple IRC networks:

```cfg
# biboumi.cfg
hostname=irc-gateway.example.com
password=your-xmpp-component-secret
xmpp_server_ip=127.0.0.1
admin=admin@example.com
identd_port=0
realname_customization=true
realname_from_jid=true
```

## Comparison Table

| Feature | Spectrum 2 | Slidge | Biboumi |
|---------|-----------|--------|---------|
| **Architecture** | Multi-process (C++ backends) | Single-process (Python plugins) | Single-process (C++) |
| **Protocols Supported** | 15+ (IRC, Telegram, Discord, etc.) | 10+ (WhatsApp, Telegram, Discord, Signal, etc.) | 1 (IRC only) |
| **GitHub Stars** | 416+ | Community-driven | 90+ |
| **Deployment Complexity** | Medium (multiple containers) | Low (single container) | Low (single container) |
| **Docker Support** | Official images per backend | Community image | Official image |
| **Plugin System** | Backend API (C++/Python) | Python plugins (pip installable) | N/A |
| **IRC Support** | Full (via libcommuni) | Basic (via community plugin) | Best-in-class |
| **Active Development** | Yes (June 2026) | Yes (actively maintained) | Stale (2022) |
| **Resource Usage** | ~200 MB RAM | ~100 MB RAM | ~50 MB RAM |
| **Multi-Account** | One account per transport | Multiple accounts per plugin | Shared across domain |

## Why Self-Host Your XMPP Transport Gateways?

Running your own XMPP transport gateways gives you complete control over message routing and data privacy. When you use public bridge services, all your cross-protocol messages pass through a third-party server that can read, log, or modify them. Self-hosting eliminates this trust requirement — your messages stay on infrastructure you control. For organizations that need to integrate legacy IRC channels with modern chat workflows, Biboumi provides a seamless bridge without exposing internal conversations to external services.

The consolidation benefit is substantial for power users who participate in communities across multiple platforms. Instead of running five different chat applications — each with its own notification system, UI quirks, and resource consumption — a single XMPP client connects to everything through your self-hosted gateways. This approach also future-proofs your chat history: when a proprietary platform shuts down or changes its API, your XMPP archive preserves your conversations independently. For the XMPP server side, our [XMPP server comparison](../ejabberd-vs-prosody-vs-openfire-self-hosted-xmpp-jabber-server-guide-2026/) covers choosing the right foundation for your gateway infrastructure.

From a federation perspective, XMPP gateways represent the open web philosophy in practice — they break down walled gardens by providing interoperability between otherwise incompatible networks. If you're interested in the broader messaging ecosystem, check our [Matrix bridges guide](../2026-04-28-mautrix-whatsapp-telegram-signal-discord-self-hosted-matrix-bridges-guide-2026/) for the Matrix-based alternative to XMPP bridging. The choice between Spectrum 2 and Slidge often comes down to your operational preferences: Spectrum 2 offers battle-tested stability with its multi-process architecture, while Slidge provides faster plugin development and simpler deployment at the cost of being newer.

For IRC-heavy communities, Biboumi remains the gold standard despite its narrower scope. The IRC protocol has decades of accumulated quirks and conventions that general-purpose bridges struggle to handle correctly — nick registration, channel services, SASL authentication, and CTCP commands are all handled properly by Biboumi's dedicated implementation. Combined with a self-hosted IRC server like the options in our [IRC server guide](../2026-05-12-self-hosted-irc-servers-ngircd-inspircd-unrealircd-guide/), you can build a complete, self-contained chat infrastructure that bridges old and new protocols.

## FAQ

### Do I need a separate XMPP server to run transport gateways?

Yes — Spectrum 2, Slidge, and Biboumi all connect to an existing XMPP server as external components. The gateway registers as a service on your XMPP domain (e.g., `irc-gateway.example.com`), and users discover it through service discovery. Prosody and Ejabberd are the most common choices and have excellent component protocol support.

### How are messages translated between protocols?

Each gateway maintains a mapping between XMPP features and the target protocol's capabilities. For text messages, the translation is straightforward. For features like message reactions, file sharing, and read receipts, the gateway must map between different implementations — for example, Telegram reactions become XMPP message reactions (XEP-0444), and Discord file uploads are converted to XMPP HTTP Upload (XEP-0363).

### Can I bridge the same external account through multiple XMPP clients?

Slidge supports multiple XMPP accounts connecting to the same external account (e.g., two XMPP users sharing a Telegram bot account). Spectrum 2 and Biboumi use a simpler model where each XMPP user gets their own isolated connection. For IRC, Biboumi's domain-level approach means all XMPP users appear to share the same IRC connections, which is actually more natural for IRC channels.

### What happens when a proprietary platform changes its API?

This is the main operational risk of running transport gateways. When Telegram, Discord, or WhatsApp change their API, the corresponding plugin or backend may break until the developers release an update. Spectrum 2's process isolation means a broken backend doesn't crash your other transports. Slidge's single-process design means a plugin crash could affect all bridges — but its Python plugin system allows faster fixes since new plugin versions can be hot-reloaded.

### Why would I choose Biboumi over a general-purpose gateway's IRC support?

Biboumi handles IRC-specific features that general-purpose gateways often get wrong: CTCP requests (VERSION, PING, TIME), DCC file transfers, channel operator status tracking, and correct handling of IRC numeric replies. If your primary use case is bridging IRC to XMPP, Biboumi provides a more authentic IRC experience. If you need multiple protocols, Spectrum 2 or Slidge are better choices.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted XMPP Transport Gateways: Spectrum 2 vs Slidge vs Biboumi",
  "description": "Comprehensive comparison of self-hosted XMPP transport gateway frameworks: Spectrum 2 multi-process architecture, Slidge Python plugin system, and Biboumi IRC bridge. Includes Docker Compose configurations for bridging IRC, Telegram, Discord, and other protocols to XMPP.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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
