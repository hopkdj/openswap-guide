---
title: "Errbot vs Hubot vs Maubot: Self-Hosted ChatOps Bot Frameworks Guide 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "chatops", "automation"]
draft: false
description: "Compare Errbot, Hubot, and Maubot — three open-source chatbot frameworks for building self-hosted DevOps automation bots. Installation guides, plugin ecosystems, and Docker configs."
---

When your infrastructure spans dozens of services, running commands through a shared terminal becomes impractical. ChatOps solves this by bringing operations into your team's messaging platform — deploy, monitor, restart, and troubleshoot directly from chat channels.

Instead of paying for proprietary SaaS bot platforms, you can self-host your ChatOps bot using open-source frameworks. This guide compares three popular options: **Errbot** (Python), **Hubot** (Node.js), and **Maubot** (Python/Matrix-native), helping you choose the right foundation for your self-hosted automation stack.

## Why Self-Host Your ChatOps Bot?

Self-hosting a chatbot framework gives you full control over:

- **Data privacy**: Bot logs, command history, and credentials never leave your infrastructure
- **No vendor lock-in**: Switch between Slack, Discord, Matrix, or XMPP backends without rebuilding
- **Cost**: All three frameworks are free and open-source — no per-seat or per-message pricing
- **Custom plugins**: Build domain-specific commands tailored to your infrastructure
- **Air-gapped deployments**: Run entirely offline for security-sensitive environments

For teams already running self-hosted chat platforms like Mattermost or Matrix, pairing them with a self-hosted bot framework creates a complete private communication and automation stack. If you're evaluating team chat platforms, see our [Mattermost vs Rocket.Chat vs Zulip comparison](../mattermost-vs-rocketchat-vs-zulip/) for a detailed breakdown.

## Quick Comparison Table

| Feature | Errbot | Hubot | Maubot |
|---|---|---|---|
| **Language** | Python 3.10+ | Node.js (CoffeeScript/JS/TS) | Python 3.10+ |
| **GitHub Stars** | 3,275 | 16,783 | 869 |
| **Last Updated** | January 2026 | March 2026 | April 2026 |
| **Primary Backend** | Multi (Slack, Discord, XMPP, IRC, Telegram) | Multi (Slack, Discord, Teams, IRC) | Matrix-only |
| **Plugin Language** | Python | CoffeeScript/JavaScript/TypeScript | Python |
| **Plugin Ecosystem** | 100+ official/community | 1,000+ community scripts | Growing (Matrix ecosystem) |
| **Web UI** | No | No | Yes (management frontend) |
| **Docker Support** | Official Dockerfile | Community images | Official Dockerfile + docker scripts |
| **Storage** | SQLite, PostgreSQL, MySQL | Redis, file-based | SQLite, PostgreSQL |
| **License** | GPL-3.0 | MIT | AGPL-3.0 |
| **Best For** | Multi-platform bots, Python teams | Mature ecosystem, JS/TS teams | Matrix-native deployments |

## Errbot: Python-Powered Multi-Platform Bot

[Errbot](https://github.com/errbotio/errbot) is the most versatile option for teams that need a single bot to connect across multiple chat platforms. Written in Python, it supports Slack, Discord, Telegram, XMPP, IRC, and more through its backend system.

### Key Features

- **Multi-backend support**: Connect to 10+ chat platforms simultaneously
- **Rich plugin system**: Write plugins in Python with decorators for commands, flows, and webhooks
- **Built-in admin commands**: Restart, install plugins, manage backends from chat
- **Persistence layer**: Stores plugin data in SQLite, PostgreSQL, or MySQL
- **Web server**: Expose webhook endpoints for external integrations
- **Chat flows**: Build multi-step conversational workflows

### Installation

#### Docker (Recommended)

Errbot provides an official multi-stage Dockerfile that builds from Python 3.12 with optional backend extras:

```dockerfile
# Dockerfile
ARG INSTALL_EXTRAS=irc,XMPP,telegram,slack

FROM python:3.12 AS build
ARG INSTALL_EXTRAS

WORKDIR /wheel
COPY . .
RUN pip wheel --wheel-dir=/wheel wheel . .[${INSTALL_EXTRAS}]

FROM python:3.12-slim
ARG INSTALL_EXTRAS

RUN --mount=from=build,source=/wheel,target=/wheel \
    pip install --no-cache-dir --no-index --find-links /wheel \
    errbot errbot[${INSTALL_EXTRAS}]

RUN useradd --create-home --shell /bin/bash errbot
USER errbot
WORKDIR /home/errbot
RUN errbot --init

EXPOSE 3141 3142
VOLUME /home/errbot
STOPSIGNAL SIGINT
ENTRYPOINT [ "/usr/local/bin/errbot" ]
```

#### Docker Compose

```yaml
version: "3.8"
services:
  errbot:
    build:
      context: ./errbot
      args:
        INSTALL_EXTRAS: "slack,discord,telegram"
    volumes:
      - ./data:/home/errbot
      - ./plugins:/home/errbot/plugins
      - ./config.py:/home/errbot/config.py
    restart: unless-stopped
    environment:
      - TZ=UTC
    ports:
      - "3141:3141"
      - "3142:3142"
```

#### Configuration

Create a `config.py` to define your backend and credentials:

```python
# config.py
BACKEND = 'Slack'
BOT_DATA_DIR = '/home/errbot/data'
BOT_EXTRA_PLUGIN_DIR = '/home/errbot/plugins'
BOT_EXTRA_BACKEND_DIR = '/home/errbot/backends'

BOT_IDENTITY = {
    'token': 'xoxb-YOUR-SLACK-BOT-TOKEN',
}

BOT_ADMINS = ('@your-admin',)
BOT_PREFIX = '!'
```

### Sample Plugin

```python
from errbot import BotPlugin, botcmd

class InfraOps(BotPlugin):
    """Infrastructure operations plugin."""

    @botcmd
    def deploy(self, msg, args):
        """Deploy a service to production."""
        service = args.strip() if args else "unknown"
        yield f"🚀 Starting deployment of `{service}`..."
        yield f"✅ `{service}` deployed successfully."

    @botcmd
    def status(self, msg, args):
        """Check status of all services."""
        services = ["api", "web", "worker", "db"]
        for svc in services:
            yield f"🟢 {svc}: running (uptime 99.97%)"
```

For teams looking to go beyond simple bot commands and build full workflow automations, our [Huginn vs n8n vs Activepieces guide](../huginn-vs-n8n-vs-activepieces-self-hosted-ifttt-alternatives-2026/) covers complementary self-hosted automation platforms.

## Hubot: The OG ChatOps Framework

[Hubot](https://github.com/github/hubot), created by GitHub, is the original ChatOps bot framework. Written in Node.js with CoffeeScript (now supporting JavaScript and TypeScript), it has the largest ecosystem of community scripts and adapters.

### Key Features

- **Largest plugin ecosystem**: 1,000+ community-contributed scripts
- **Battle-tested**: Powers bots at GitHub, Stack Overflow, and thousands of companies
- **Adapter system**: Connect to Slack, Discord, Microsoft Teams, IRC, and more
- **Script loading**: Drop scripts into `scripts/` directory for auto-loading
- **Environment-based config**: Simple `.env` or systemd environment file configuration
- **Heredoc support**: Create scripts directly in chat with `/hubot script create`

### Installation

#### npm Install

```bash
# Install Hubot generator globally
npm install -g yo generator-hubot

# Create a new bot
mkdir myhubot && cd myhubot
yo hubot

# Install a backend adapter
npm install hubot-slack
# or: npm install hubot-discord
# or: npm install hubot-teams
```

#### Docker Compose

Hubot doesn't provide an official Dockerfile, but community images work reliably:

```yaml
version: "3.8"
services:
  hubot:
    image: node:20-alpine
    working_dir: /home/hubot
    volumes:
      - ./hubot:/home/hubot
      - ./scripts:/home/hubot/scripts
    command: >
      sh -c "
        npm install &&
        ./bin/hubot --adapter slack
      "
    environment:
      - HUBOT_SLACK_TOKEN=xoxb-YOUR-SLACK-BOT-TOKEN
      - HUBOT_NAME=opsbot
      - HUBOT_OWNER=your-team
      - TZ=UTC
    restart: unless-stopped
```

#### systemd Service

Hubot's repository includes a production-ready systemd unit file:

```ini
[Unit]
Description=Hubot ChatOps Bot
Requires=network.target
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/hubot
User=hubot
Restart=always
RestartSec=10
Environment="HUBOT_SLACK_TOKEN=xoxb-YOUR-TOKEN"
ExecStart=/opt/hubot/bin/hubot --adapter slack

[Install]
WantedBy=multi-user.target
```

### Sample Script

```javascript
// scripts/deploy.js
module.exports = (robot) => {
  robot.respond(/deploy (\w+)/i, (msg) => {
    const service = msg.match[1];
    msg.send(`🚀 Deploying ${service}...`);

    setTimeout(() => {
      msg.send(`✅ ${service} deployed successfully!`);
    }, 3000);
  });

  robot.respond(/status/i, (msg) => {
    const services = [
      { name: 'api', status: '🟢 healthy', latency: '42ms' },
      { name: 'web', status: '🟢 healthy', latency: '38ms' },
      { name: 'worker', status: '🟡 degraded', latency: '210ms' },
    ];
    const report = services.map(s =>
      `${s.name}: ${s.status} (${s.latency})`
    ).join('\n');
    msg.send(`**Service Status**\n${report}`);
  });
};
```

## Maubot: Matrix-Native Bot Platform

[Maubot](https://github.com/maubot/maubot) is purpose-built for the Matrix protocol. If your team uses Matrix (Synapse, Dendrite) as its primary communication platform, Maubot offers the deepest integration with built-in E2E encryption support and a web-based management interface.

### Key Features

- **Matrix-first**: Native Matrix protocol support with full E2E encryption
- **Web management UI**: Install, configure, and manage bot instances from a browser
- **Python plugin system**: Clean plugin API with type hints and async support
- **Multi-instance**: Run multiple bot instances with separate configurations
- **Plugin marketplace**: Share and install plugins from a central repository
- **Database backend**: SQLite (default) or PostgreSQL for production
- **Docker-ready**: Official Dockerfile with Alpine-based slim images

### Installation

#### Docker Compose

Maubot provides an official Dockerfile that builds a multi-stage image with a Node.js frontend builder and Alpine runtime:

```yaml
version: "3.8"
services:
  maubot:
    build:
      context: ./maubot
      dockerfile: Dockerfile
    volumes:
      - ./data:/opt/maubot/data
      - ./logs:/opt/maubot/logs
      - ./plugins:/opt/maubot/plugins
      - ./config.yaml:/opt/maubot/config.yaml
    ports:
      - "29316:29316"
    restart: unless-stopped
    environment:
      - TZ=UTC

  # Optional PostgreSQL backend
  maubot-db:
    image: postgres:16-alpine
    volumes:
      - maubot-postgres:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: maubot
      POSTGRES_PASSWORD: maubot-secret
      POSTGRES_DB: maubot
    restart: unless-stopped

volumes:
  maubot-postgres:
```

#### Configuration

```yaml
# config.yaml
debug_logging: false
database:
  type: sqlite
  path: /opt/maubot/data/maubot.db
server:
  hostname: 0.0.0.0
  port: 29316
  secret: your-management-secret
plugin_directories:
  root: /opt/maubot/plugins
log:
  path: /opt/maubot/logs/maubot.log
  max_file_size: 10M
  max_files: 5
```

#### Accessing the Management UI

After starting the container, open `http://your-server:29316/_matrix/maubot` in your browser. The web interface lets you:

- Create and manage bot instances
- Install plugins from the marketplace
- Configure plugin settings per instance
- View logs and monitor health

### Sample Plugin

```python
# plugin.py
from mautrix.util.config import BaseProxyConfig, ConfigUpdate
from maubot import Plugin, MessageEvent
from maubot.handlers import command

class InfraBot(Plugin):
    @command.new(help="Check infrastructure status")
    async def status(self, evt: MessageEvent) -> None:
        services = [
            ("API Gateway", "healthy", "42ms"),
            ("Web Frontend", "healthy", "38ms"),
            ("Worker Pool", "degraded", "210ms"),
        ]
        report = "📊 **Service Status**\n\n"
        for name, state, latency in services:
            icon = "🟢" if state == "healthy" else "🟡"
            report += f"{icon} {name}: {latency}\n"
        await evt.respond(report)

    @command.argument("service", pass_raw=True)
    async def deploy(self, evt: MessageEvent, service: str) -> None:
        await evt.respond(f"🚀 Deploying `{service}`...")
        await evt.respond(f"✅ `{service}` deployed successfully!")
```

For teams using Matrix as their communication backbone, Maubot pairs well with self-hosted Matrix bridges. Check our [Matrix bridges guide](../2026-04-28-mautrix-whatsapp-telegram-signal-discord-self-hosted-matrix-bridges-guide-2026/) to connect WhatsApp, Telegram, and Signal into your Matrix deployment.

## Backend Support Comparison

| Platform | Errbot | Hubot | Maubot |
|---|---|---|---|
| Slack | ✅ Native | ✅ Adapter | ❌ (use bridge) |
| Discord | ✅ Native | ✅ Adapter | ❌ (use bridge) |
| Matrix | ✅ Via mautrix-backend | ❌ | ✅ Native |
| Telegram | ✅ Native | ✅ Adapter | ❌ (use bridge) |
| XMPP | ✅ Native | ✅ Adapter | ❌ |
| IRC | ✅ Native | ✅ Adapter | ❌ |
| Microsoft Teams | ❌ | ✅ Adapter | ❌ |
| Mattermost | ✅ Via webhook | ❌ | ❌ |
| E2E Encryption | ❌ | ❌ | ✅ Full support |

## Plugin Ecosystem Comparison

### Errbot Plugins

Errbot uses Python packages installable via `pip`. Popular plugins include:

- **Health**: Monitor server uptime and alert on failures
- **Docker**: Manage containers from chat (`docker ps`, `docker restart`)
- **Jira**: Create and update Jira tickets
- **GitHub**: Search repos, review PRs, check CI status
- **AWS**: Start/stop EC2 instances, check CloudWatch metrics

Install plugins directly from chat:
```
!repos install https://github.com/errbotio/errbot-docker
```

### Hubot Scripts

Hubot scripts are npm packages. The ecosystem is massive:

- **hubot-deploy**: Deployment orchestration
- **hubot-diagnostics**: System health checks
- **hubot-jenkins**: Jenkins CI integration
- **hubot-rules**: Define team rules and policies
- **hubot-maps**: ASCII map generation (classic Hubot fun)

```bash
npm install hubot-deploy hubot-diagnostics hubot-jenkins
```

### Maubot Plugins

Maubot plugins use a `.mbp` package format. The ecosystem is smaller but Matrix-focused:

- **Matrix polls**: Create and manage polls
- **Matrix reminders**: Set timed reminders
- **Matrix RSS**: Feed RSS updates into rooms
- **Matrix moderation**: Automated room moderation tools
- **Custom Python plugins**: Full async Python with Matrix API access

```bash
# Install from the management UI or CLI
mbc plugin install com.example.infra-bot
```

## Which Should You Choose?

### Choose Errbot if:

- You need to connect to **multiple chat platforms** from a single bot
- Your team is comfortable with **Python**
- You want a built-in plugin management system
- You need webhook endpoints for external integrations

### Choose Hubot if:

- You want the **largest plugin ecosystem** available
- Your team works in **JavaScript/TypeScript**
- You're deploying to Slack or Discord with mature adapter support
- You want battle-tested stability (13+ years of production use)

### Choose Maubot if:

- Your primary platform is **Matrix**
- You need **end-to-end encryption** for bot communications
- You want a **web-based management interface** out of the box
- You prefer running multiple bot instances with centralized management

## FAQ

### Can I run multiple ChatOps bots at the same time?

Yes. Each framework runs as an independent process. You can run Errbot for Slack/Discord, Maubot for Matrix, and Hubot for Microsoft Teams simultaneously. They don't interfere with each other as long as they connect to different channels or rooms.

### Do these bots support end-to-end encryption?

Only Maubot supports E2E encryption natively through the Matrix protocol. Errbot and Hubot transmit messages in plaintext to the chat backend. If encryption is required, consider using Maubot on Matrix, or adding a TLS-encrypted transport layer for bot-to-server communication.

### How do I add custom commands to my bot?

Each framework has a plugin system: Errbot uses Python decorators (`@botcmd`), Hubot uses JavaScript event listeners (`robot.respond`), and Maubot uses Python command handlers (`@command.new`). Write your logic in the supported language, drop the file in the plugins/scripts directory, and restart the bot.

### Can these bots execute shell commands on my server?

Yes, but you should implement proper access controls. All three frameworks can execute subprocess commands, but you should restrict which admin users can trigger them, validate all input arguments, and avoid running commands as root. Use a dedicated service account with minimal permissions.

### Which framework is easiest to self-host with Docker?

Errbot and Maubot both provide official Dockerfiles that build cleanly. Errbot's multi-stage build produces a slim Python 3.12 image. Maubot's build is more complex (Node.js frontend builder + Alpine runtime) but results in a smaller final image. Hubot requires a custom Dockerfile or community image since it has no official Dockerfile.

### Can I migrate from one framework to another?

There's no automatic migration path since plugin formats differ. However, the command interface (what users type in chat) can remain consistent if you document your bot's command syntax and reimplement the same commands in the new framework's plugin language. Export your configuration and credentials, then rebuild the plugins in the target framework.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Errbot vs Hubot vs Maubot: Self-Hosted ChatOps Bot Frameworks Guide 2026",
  "description": "Compare Errbot, Hubot, and Maubot — three open-source chatbot frameworks for building self-hosted DevOps automation bots. Installation guides, plugin ecosystems, and Docker configs.",
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
