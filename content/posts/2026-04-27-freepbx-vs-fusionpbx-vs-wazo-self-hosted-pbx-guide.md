---
title: "FreePBX vs FusionPBX vs Wazo: Best Self-Hosted PBX Platforms 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "voip", "telephony"]
draft: false
description: "Compare FreePBX, FusionPBX, and Wazo — the top open-source self-hosted PBX platforms. Includes Docker deployment guides, feature comparisons, and configuration examples for building your own business phone system."
---

Building a self-hosted business phone system used to require expensive proprietary hardware and vendor lock-in. Today, three mature open-source PBX platforms let you run a full-featured telephony system on your own infrastructure: **FreePBX**, **FusionPBX**, and **Wazo**.

This guide compares these platforms side by side, covers Docker deployment options, and provides configuration examples to help you choose the right PBX for your self-hosted infrastructure.

## Why Self-Host Your PBX?

Running your own PBX platform gives you complete control over your business communications:

- **No per-seat licensing fees** — open-source PBX platforms are free regardless of how many extensions you add
- **Full data sovereignty** — call recordings, voicemails, and call detail records stay on your servers
- **Deep customization** — modify dialplans, IVR flows, and integrations without vendor restrictions
- **Integration with existing infrastructure** — connect to your own SIP trunks, gateways, and CRM systems
- **Resilience** — no dependency on a third-party cloud provider's uptime

For organizations that already self-host their email, file storage, and collaboration tools, adding a self-hosted PBX is a natural extension of that philosophy.

## FreePBX: The Most Popular Asterisk GUI

[FreePBX](https://www.freepbx.org/) is the most widely deployed open-source PBX platform, serving as a web-based management interface for Asterisk. Originally created by Schmooze Communications and now maintained by Sangoma Technologies, FreePBX powers millions of phone systems worldwide.

### Key Features

- Web-based GUI for managing extensions, trunks, routes, and IVRs
- Module-based architecture with 200+ free and commercial modules
- Built-in call recording, voicemail, and conferencing
- REST API for integrations
- Support for SIP, IAX2, and PJSIP protocols
- Fail2ban integration for brute-force protection

### GitHub Stats

The FreePBX framework module has **71 stars** on GitHub, with the core module at **180 stars**. While the GitHub presence is modest (much of the code is distributed through their own module repository), FreePBX is actively maintained with regular security updates.

### Installation (Docker)

FreePBX does not provide an official Docker Compose file, but the community maintains several working images. The most popular approach uses the [wisteful/freepbx](https://hub.docker.com/r/wisteful/freepbx) image:

```yaml
version: '3.8'

services:
  freepbx:
    image: wisteful/freepbx:latest
    container_name: freepbx
    restart: unless-stopped
    ports:
      - "80:80"
      - "5060:5060/udp"
      - "5160:5160/udp"
      - "18000-18100:18000-18100/udp"
    environment:
      - TZ=UTC
    volumes:
      - freepbx_data:/data
      - freepbx_etc:/etc/freepbx
    networks:
      - pbx-net

  mysql:
    image: mariadb:10.5
    container_name: freepbx-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: freepbx_secret
      MYSQL_DATABASE: asterisk
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - pbx-net

volumes:
  freepbx_data:
  freepbx_etc:
  mysql_data:

networks:
  pbx-net:
    driver: bridge
```

### Configuration Example: Setting Up a SIP Trunk

After installing FreePBX, navigate to **Connectivity > Trunks** to add a SIP trunk:

```ini
; /etc/asterisk/pjsip.conf (managed by FreePBX GUI)
[my-trunk]
type=endpoint
context=from-trunk
disallow=all
allow=ulaw
allow=alaw
transport=udp
direct_media=no

[my-trunk]
type=aor
max_contacts=1

[my-trunk]
type=auth
auth_type=userpass
username=your_sip_username
password=your_sip_password
```

FreePBX manages these configurations automatically through its GUI, but understanding the underlying Asterisk config helps with troubleshooting.

## FusionPBX: Multi-Tenant FreeSWITCH Platform

[FusionPBX](https://www.fusionpbx.com/) is a full-featured, domain-based multi-tenant PBX built on FreeSWITCH. Created by Mark J. Crane, FusionPBX offers enterprise-grade features including true multi-tenancy, making it ideal for service providers and organizations managing multiple departments or clients.

### Key Features

- True multi-tenant architecture — isolate clients or departments
- Built on FreeSWITCH for superior audio processing
- Domain-based provisioning for auto-configuring IP phones
- Advanced call center features with queue management
- Real-time call detail records (CDR) and billing
- Native support for WebRTC, SRTP, and TLS
- High-availability clustering support

### GitHub Stats

FusionPBX has **997 stars** on GitHub, with the last commit on April 25, 2026. The project is written primarily in PHP and has a very active development community.

### Installation (Traditional + Docker)

FusionPBX provides an install script rather than Docker images. Here's the standard Debian installation:

```bash
# Download and run the FusionPBX install script
cd /usr/src
git clone https://github.com/fusionpbx/fusionpbx-install.sh.git
cd fusionpbx-install.sh/debian
./install.sh
```

For Docker deployments, you can build a custom compose setup:

```yaml
version: '3.8'

services:
  fusionpbx:
    image: fusionpbx/fusionpbx:latest
    container_name: fusionpbx
    restart: unless-stopped
    network_mode: host
    environment:
      - TZ=UTC
      - FUSIONPBX_DB_HOST=postgres
      - FUSIONPBX_DB_NAME=fusionpbx
      - FUSIONPBX_DB_USER=fusionpbx
      - FUSIONPBX_DB_PASSWORD=fusion_secret
    volumes:
      - fusionpbx_etc:/etc/fusionpbx
      - fusionpbx_var:/var/lib/fusionpbx
    depends_on:
      - postgres

  freeswitch:
    image: signalwire/freeswitch:latest
    container_name: freeswitch
    restart: unless-stopped
    network_mode: host
    volumes:
      - freeswitch_conf:/etc/freeswitch
      - freeswitch_recordings:/var/lib/freeswitch/recordings
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    container_name: fusionpbx-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: fusionpbx
      POSTGRES_USER: fusionpbx
      POSTGRES_PASSWORD: fusion_secret
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  fusionpbx_etc:
  fusionpbx_var:
  freeswitch_conf:
  freeswitch_recordings:
  pg_data:
```

### Configuration Example: Multi-Tenant Setup

FusionPBX's multi-tenancy is managed through the GUI. Each domain acts as a separate tenant:

```xml
<!-- /etc/freeswitch/sip_profiles/internal.xml -->
<profile name="internal">
  <param name="auth-calls" value="true"/>
  <param name="apply-inbound-acl" value="domains"/>
  <param name="local-network-acl" value="localnet.auto"/>
  <param name="manage-presence" value="true"/>
  <param name="sip-port" value="5060"/>
  <param name="rtp-ip" value="$${local_ip_v4}"/>
  <param name="sip-ip" value="$${local_ip_v4}"/>
</profile>
```

FusionPBX automatically generates FreeSWITCH XML configurations based on your GUI settings, managing the complex mapping between domains and dialplans.

## Wazo: Modern Unified Communications Platform

[Wazo](https://wazo-platform.org/) is a modern, API-first unified communications platform built on Asterisk. Unlike FreePBX and FusionPBX, Wazo was designed from the ground up with a microservices architecture and a comprehensive REST API, making it ideal for organizations that want to integrate telephony deeply into their applications.

### Key Features

- Microservices architecture with separate daemons for each function
- REST API for all operations — no GUI-only configuration
- CTI (Computer Telephony Integration) with real-time events via WebSocket
- Built-in provisioning system for IP phones
- Call queue management with real-time statistics
- WebRTC support with built-in browser-based phone (wazo-webrc)
- Plugin architecture for custom integrations

### GitHub Stats

Wazo is split across multiple microservice repositories under the [wazo-platform](https://github.com/wazo-platform) organization. Key repos include `wazo-confd` (12 stars), `wazo-calld` (36 stars), and `wazo-docker` (17 stars). The project is actively maintained with recent updates in April 2026.

### Installation (Docker Compose)

Wazo provides an official Docker Compose setup, making it the easiest of the three to deploy in containers:

```yaml
version: '3.8'

services:
  nginx:
    image: nginx
    ports:
      - '127.0.0.1:8443:443'
    volumes:
      - ./etc/nginx.conf:/etc/nginx/conf.d/config.conf:ro
      - ./certs:/certs:ro
    depends_on:
      - agentd
      - calld
      - confd
      - dird
      - webhookd
      - websocketd

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: wazo
      POSTGRES_USER: wazo
      POSTGRES_PASSWORD: wazo_secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    expose:
      - "5432"

  rabbitmq:
    image: rabbitmq:3
    expose:
      - "5672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  asterisk:
    image: wazoplatform/wazo-asterisk
    network_mode: host
    volumes:
      - ./etc/asterisk:/etc/asterisk:ro
      - recordings:/var/spool/asterisk
    depends_on:
      - postgres
      - rabbitmq

  confd:
    image: wazoplatform/wazo-confd
    expose:
      - 9486
    depends_on:
      - postgres
      - rabbitmq

  calld:
    image: wazoplatform/wazo-calld
    expose:
      - 9491
    depends_on:
      - postgres
      - rabbitmq

  dird:
    image: wazoplatform/wazo-dird
    expose:
      - 9493
    depends_on:
      - postgres
      - rabbitmq

  webhookd:
    image: wazoplatform/wazo-webhookd
    expose:
      - 9495
    depends_on:
      - rabbitmq

volumes:
  pgdata:
  rabbitmq_data:
  recordings:
```

### Configuration Example: API-Driven Extension Creation

Wazo's API-first approach means you can manage everything programmatically:

```bash
# Get an authentication token
TOKEN=$(curl -s -X POST "https://localhost:9497/0.1/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret", "expiration": 3600}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Create a new extension via the REST API
curl -s -X POST "https://localhost:9486/1.1/users" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "John",
    "lastname": "Doe",
    "email": "john@example.com",
    "line_name": "line-john-doe"
  }'

# Add a SIP line to the user
curl -s -X POST "https://localhost:9486/1.1/users/$USER_ID/lines" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "sip",
    "endpoint_sip": {
      "name": "john-sip",
      "label": "John Doe SIP",
      "templates": ["default"]
    }
  }'
```

## Comparison Table

| Feature | FreePBX | FusionPBX | Wazo |
|---------|---------|-----------|------|
| **Engine** | Asterisk | FreeSWITCH | Asterisk |
| **License** | GPLv3 | MPL 1.1 | GPLv3 |
| **Multi-tenant** | No (per-installation) | Yes (domain-based) | Yes (tenant-based) |
| **Docker Support** | Community images | Community/Custom | Official docker-compose |
| **API** | REST (limited) | REST API | Full REST + WebSocket |
| **Architecture** | Monolithic | Monolithic | Microservices |
| **Phone Provisioning** | Yes (via Endpoint Manager) | Yes (built-in) | Yes (provd service) |
| **WebRTC** | Via modules | Native | Native (wazo-webrc) |
| **Call Recording** | Yes | Yes | Yes |
| **Call Center/Queues** | Yes (Queue module) | Yes (built-in) | Yes (calld service) |
| **High Availability** | Limited | Yes (clustering) | Yes (microservice scaling) |
| **Programming Language** | PHP/Python | PHP | Python |
| **Database** | MySQL/MariaDB | PostgreSQL | PostgreSQL |
| **Message Queue** | None | None | RabbitMQ |
| **GitHub Stars** | ~250 (combined) | 997 | ~65 (combined) |
| **Best For** | SMBs, single-site | MSPs, multi-tenant | Developers, API-first |

## Which Should You Choose?

### Choose FreePBX if:
- You want the most mature and widely-deployed platform
- You need the largest ecosystem of modules and community support
- You're running a single-site or small multi-site deployment
- Your team already knows Asterisk

### Choose FusionPBX if:
- You need true multi-tenant isolation (MSPs, managed services)
- You prefer FreeSWITCH's audio processing capabilities
- You need high-availability clustering
- You're deploying for multiple departments or clients on one instance

### Choose Wazo if:
- You want an API-first platform for deep application integration
- You need real-time CTI events via WebSocket
- You prefer modern microservices architecture
- You want official Docker Compose deployment out of the box

For related reading, see our [VoIP PBX engines comparison (Kamailio vs Asterisk vs FreeSWITCH)](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/) and [self-hosted video conferencing with Jitsi](../self-hosted-video-conferencing-jitsi-guide/).

## FAQ

### Can I run a self-hosted PBX without a dedicated server?

Yes. All three platforms can run on a modest VPS with 2-4 CPU cores and 4GB RAM for small deployments (up to ~50 concurrent calls). FreePBX and FusionPBX also support bare-metal installation on older hardware you may already have.

### How do I connect my self-hosted PBX to the public telephone network?

You need a SIP trunk provider. Popular options include Twilio, VoIP.ms, and Flowroute. Configure the SIP trunk credentials in your PBX GUI (FreePBX: Connectivity > Trunks, FusionPBX: Account > SIP, Wazo: via API or GUI) and route outbound calls through it.

### Is it legal to run your own PBX?

Yes, running a PBX is legal in most jurisdictions. You must comply with emergency calling regulations (E911 in the US) and call recording consent laws. Consult local telecom regulations for specific requirements.

### Can I migrate from FreePBX to FusionPBX or Wazo?

Migration is possible but not automatic. You'll need to manually recreate extensions, trunks, IVR flows, and dialplans. Call detail records and voicemail can be exported and imported, but the process requires planning. Consider running both systems in parallel during migration.

### Do these platforms support encrypted calls?

All three platforms support TLS for SIP signaling and SRTP for media encryption. FusionPBX and Wazo have the most straightforward WebRTC setup for browser-based encrypted calls. FreePBX requires additional module configuration for full SRTP support.

### How do I back up my PBX configuration?

- **FreePBX**: Use the built-in Backup & Restore module, or `fwconsole backup --all`
- **FusionPBX**: Use the GUI backup tool or export the PostgreSQL database with `pg_dump`
- **Wazo**: Use `wazo-backup` CLI tool or back up the PostgreSQL database and `/etc/wazo` configuration

### What SIP phones work with these platforms?

All three support standard SIP phones. Yealink, Grandstream, and Polycom phones are widely compatible. FusionPBX and Wazo have built-in provisioning systems that can auto-configure supported phone models. FreePBX requires the Endpoint Manager module for auto-provisioning.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "FreePBX vs FusionPBX vs Wazo: Best Self-Hosted PBX Platforms 2026",
  "description": "Compare FreePBX, FusionPBX, and Wazo — the top open-source self-hosted PBX platforms. Includes Docker deployment guides, feature comparisons, and configuration examples.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
