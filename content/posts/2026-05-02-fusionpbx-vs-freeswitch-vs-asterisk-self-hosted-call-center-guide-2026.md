---
title: "FusionPBX vs FreeSWITCH vs Asterisk: Self-Hosted Call Center Software Guide 2026"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "call-center", "voip", "telephony", "freeswitch", "asterisk", "fusionpbx"]
draft: false
description: "Compare FusionPBX, FreeSWITCH, and Asterisk for self-hosted call center deployment. Complete guide with Docker configs, queue management, IVR setup, and agent dashboard configuration in 2026."
---

Running a call center on proprietary platforms like Five9, Talkdesk, or Amazon Connect means your customer conversations flow through third-party infrastructure — with per-agent pricing that scales into thousands of dollars per month. Self-hosted call center software gives you complete control over call routing, queue management, agent monitoring, and customer data while eliminating recurring licensing costs.

In this guide, we compare three open-source platforms that power self-hosted call centers: **FusionPBX** (1,000 stars, the leading web-based multi-tenant PBX and voice switch built on FreeSWITCH), **FreeSWITCH** (4,827 stars, the modular telephony platform that serves as the engine behind dozens of commercial products), and **Asterisk** (3,213 stars, the original open-source PBX with decades of enterprise deployment history).

## Why Self-Host Your Call Center?

Commercial cloud call center platforms charge $50-$300 per agent per month, and that pricing assumes you are comfortable with:

- **Customer data residency**: Call recordings, transcripts, and CRM data stored on vendor servers subject to their retention policies and potential subpoena exposure.
- **Vendor lock-in**: Switching cloud call center providers requires retraining agents, reconfiguring IVR flows, and migrating contact databases — a multi-month process.
- **Internet dependency**: Cloud call centers fail when your internet connection drops. Self-hosted systems route calls over SIP trunks with local PSTN failover.
- **Customization limits**: Cloud platforms restrict how deeply you can modify call flows, integrate with internal systems, or customize agent dashboards.

Self-hosting gives you unlimited agents, custom integrations, and data ownership. The trade-off is operational responsibility — you manage the infrastructure, handle upgrades, and ensure high availability.

## Quick Comparison Table

| Feature | FusionPBX | FreeSWITCH | Asterisk |
|---|---|---|---|
| **Architecture** | Web UI for FreeSWITCH | Modular telephony engine | Monolithic PBX with modules |
| **Multi-tenant** | Yes (built-in domain isolation) | Via mod_xml_curl + custom logic | Via Asterisk Realtime (ARA) |
| **Web UI** | Full admin and agent portal | None (FS_CLI, REST API) | None (CLI, AMI/ARI API) |
| **Call Queues** | Yes (via mod_callcenter) | Yes (mod_callcenter) | Yes (app_queue) |
| **IVR/Menu** | Visual IVR designer | XML/ESL scripting | Dialplan (extensions.conf) |
| **Agent Dashboard** | Built-in (web-based) | Custom (via REST API) | Custom (via AMI/ARI) |
| **Call Recording** | Built-in | Via mod_dptools/record | Via app_mixmonitor |
| **CRM Integration** | Via API/webhooks | Via mod_httapi/ESL events | Via AMI events/ARI REST |
| **Predictive Dialer** | Via third-party module | Custom implementation | Via app_dialer/GoAutoDial |
| **Video Support** | Yes (WebRTC) | Yes (mod_rtc, mod_verto) | Limited (via app_meetme) |
| **Docker Deployment** | Community images | Official images | Official images |
| **GitHub Stars** | 1,000 | 4,827 | 3,213 |
| **Last Update** | April 2026 | April 2026 | April 2026 |

## FusionPBX: The Multi-Tenant Call Center Platform

FusionPBX is a web-based management interface built on top of FreeSWITCH. It provides a full-featured admin portal for configuring domains, extensions, call queues, IVR menus, and agent groups — all through a browser without touching XML configuration files.

FusionPBX's standout feature is native multi-tenancy. A single FusionPBX instance can serve multiple organizations (domains), each with its own extensions, queues, and call routing rules. This makes it ideal for hosting providers and managed service providers running call centers for multiple clients.

### FusionPBX Docker Compose Deployment

FusionPBX provides community Docker images. Here is a production-ready deployment with PostgreSQL and FreeSWITCH:

```yaml
version: "3.8"

services:
  fusionpbx:
    image: zephyrbase/fusionpbx:latest
    container_name: fusionpbx
    hostname: fusionpbx.example.com
    ports:
      - "80:80"
      - "443:443"
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "5080:5080/udp"
      - "7443:7443"
      - "16384-32768:16384-32768/udp"
    volumes:
      - fusionpbx-config:/etc/fusionpbx
      - fusionpbx-recordings:/var/lib/fusionpbx/archive
      - freeswitch-config:/etc/freeswitch
      - freeswitch-sounds:/usr/share/freeswitch/sounds
    environment:
      - TZ=UTC
      - FUSIONPBX_DB_DRIVER=pgsql
      - FUSIONPBX_DB_HOST=postgres
      - FUSIONPBX_DB_NAME=fusionpbx
      - FUSIONPBX_DB_USER=fusionpbx
      - FUSIONPBX_DB_PASSWORD=YOUR_SECURE_PASSWORD
    restart: unless-stopped

  postgres:
    image: docker.io/library/postgres:15
    container_name: fusionpbx-db
    volumes:
      - fusionpbx-db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=fusionpbx
      - POSTGRES_USER=fusionpbx
      - POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD
    restart: unless-stopped

volumes:
  fusionpbx-config:
  fusionpbx-recordings:
  freeswitch-config:
  freeswitch-sounds:
  fusionpbx-db-data:
```

After deployment, access the web UI at `https://your-server` and complete the initial setup wizard. Configure call queues through the web interface:

```
Call Center → Queues → Add
  Queue Name: Sales Team
  Strategy: ring-all (or longest-waiting-agent)
  Time Base Score: Queue
  Max Wait Time: 300 seconds
  Music on Hold: default
```

### Key FusionPBX Features

- **Multi-Domain Management**: Each tenant gets isolated extensions, queues, and call recordings. No cross-domain data leakage.
- **Visual IVR Designer**: Build interactive voice response menus through a drag-and-drop interface. No XML editing required.
- **Hot Desking**: Agents can log into any phone with their extension credentials — ideal for shift-based call centers.
- **Call Center Reports**: Built-in reporting shows queue wait times, agent talk time, abandoned calls, and service level metrics.

## FreeSWITCH: The Telephony Engine

FreeSWITCH is the underlying telephony engine that powers FusionPBX, SignalWire, and dozens of commercial VoIP products. While it has no built-in web UI, its modular architecture and Event Socket Layer (ESL) make it the most programmable telephony platform available.

FreeSWITCH's `mod_callcenter` module provides enterprise-grade queue management with agent states (Logged Out, On Break, Ready, In Queue), skill-based routing, and maximum wait time enforcement. The ESL API lets you build custom agent dashboards, CRM integrations, and real-time monitoring tools.

### FreeSWITCH Docker Compose Deployment

FreeSWITCH provides official Docker images. Here is a production deployment with SIP and WebRTC support:

```yaml
version: "3.8"

services:
  freeswitch:
    image: signalwire/freeswitch:latest
    container_name: freeswitch
    hostname: freeswitch.example.com
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "5080:5080/udp"
      - "7443:7443"
      - "16384-32768:16384-32768/udp"
    volumes:
      - freeswitch-conf:/etc/freeswitch
      - freeswitch-recordings:/var/lib/freeswitch/recordings
      - freeswitch-sounds:/usr/share/freeswitch/sounds
    environment:
      - TZ=UTC
      - EVENT_SOCKET_PASSWORD=ClueCon
    restart: unless-stopped

volumes:
  freeswitch-conf:
  freeswitch-recordings:
  freeswitch-sounds:
```

Configure call center queues in FreeSWITCH's XML configuration:

```xml
<!-- /etc/freeswitch/autoload_configs/callcenter.conf.xml -->
<configuration name="callcenter.conf" description="Call Center">
  <settings>
    <param name="odbc-dsn" value="pgsql://host=localhost dbname=freeswitch user=fs password=SECRET"/>
  </settings>

  <queues>
    <queue name="support@default">
      <param name="strategy" value="longest-idle-agent"/>
      <param name="moh-sound" value="$${hold_music}"/>
      <param name="time-base-score" value="system"/>
      <param name="max-wait-time" value="300"/>
      <param name="max-wait-time-with-no-agent" value="60"/>
      <param name="reject-delay-time" value="10"/>
      <param name="busy-delay-time" value="60"/>
      <param name="no-agent-no-ring" value="true"/>
    </queue>
  </queues>
</configuration>
```

Connect agents to the queue via ESL commands:

```bash
# Connect via Event Socket
fs_cli -H 127.0.0.1 -P 8021 -p ClueCon

# Agent login
callcenter_config agent add 1001@default 1001@default

# Assign agent to queue
callcenter_config tier add support@default 1001@default 1 1
```

### Key FreeSWITCH Features

- **Modular Architecture**: Over 200 modules for SIP, WebRTC, conferencing, text-to-speech, speech recognition, and fax. Load only what you need.
- **Event Socket Layer**: Real-time event streaming for building custom agent dashboards, call analytics, and CRM integrations in any programming language.
- **Dialplan Flexibility**: XML, Lua, JavaScript, or Python dialplans. Route calls based on caller ID, time of day, database lookups, or HTTP API responses.
- **Carrier-Grade Scalability**: Handles thousands of concurrent calls on commodity hardware. Used by Tier-1 telecom providers worldwide.

## Asterisk: The Original Open-Source PBX

Asterisk, created by Mark Spencer in 1999, is the grandparent of open-source telephony. Its `app_queue` module provides call center queue management with multiple distribution strategies (ringall, roundrobin, leastrecent, fewestcalls, random, rrmemory).

While Asterisk's dialplan syntax (extensions.conf) has a steeper learning curve than FusionPBX's web UI, it offers unmatched flexibility for custom call routing logic. Asterisk's Asterisk Manager Interface (AMI) and Asterisk REST Interface (ARI) provide APIs for building custom agent applications.

### Asterisk Docker Compose Deployment

Asterisk provides official Docker images via the Asterisk project repository:

```yaml
version: "3.8"

services:
  asterisk:
    image: asterisk/asterisk:21-certified
    container_name: asterisk
    hostname: asterisk.example.com
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "8088:8088"
      - "16384-32768:16384-32768/udp"
    volumes:
      - asterisk-conf:/etc/asterisk
      - asterisk-sounds:/var/lib/asterisk/sounds
      - asterisk-recordings:/var/spool/asterisk/monitor
    restart: unless-stopped

volumes:
  asterisk-conf:
  asterisk-sounds:
  asterisk-recordings:
```

Configure call queues in Asterisk's `queues.conf`:

```ini
; /etc/asterisk/queues.conf
[sales]
music = default
strategy = ringall
timeout = 15
retry = 5
wrapuptime = 5
maxlen = 20
servicelevel = 30
joinmessage = You are now in the sales queue.
positionannounce = You are ${QUEUEPOS} in line.
timeoutrestart = yes
member => SIP/agent1,Agent 1
member => SIP/agent2,Agent 2
member => SIP/agent3,Agent 3
```

Define queue behavior in the dialplan (`extensions.conf`):

```ini
; /etc/asterisk/extensions.conf
[callcenter]
exten => 500,1,Answer()
 same => n,Wait(1)
 same => n,Queue(sales,t,,,300)
 same => n,Hangup()

exten => 501,1,Answer()
 same => n,Wait(1)
 same => n,Queue(support,,,60,300)
 same => n,Hangup()
```

### Key Asterisk Features

- **Dialplan Flexibility**: Write complex call routing logic using a domain-specific language in `extensions.conf`. Conditional branching, database lookups, and HTTP API calls are all native.
- **Channel Drivers**: Support for SIP, IAX2, PJSIP, DAHDI (analog/PRI), and WebRTC. Connect to any telephony hardware or SIP trunk provider.
- **AMI and ARI**: The Asterisk Manager Interface provides event-driven monitoring and control. The Asterisk REST Interface offers a modern HTTP-based API for building agent applications.
- **MixMonitor**: Built-in call recording with post-recording hooks for transcription, analysis, or storage upload.

## Choosing the Right Call Center Platform

| Criteria | Choose FusionPBX If... | Choose FreeSWITCH If... | Choose Asterisk If... |
|---|---|---|---|
| **Team size** | Small to medium teams (1-50 agents) | Engineering teams building custom platforms | Teams with telephony engineering experience |
| **Multi-tenant** | Yes — built-in domain isolation | Requires custom development | Requires Asterisk Realtime (ARA) setup |
| **Web UI needed** | Yes — full admin and agent portal | No — build your own via ESL | No — build your own via ARI |
| **Customization** | Moderate (configurable via UI) | Unlimited (code-level control) | High (dialplan programming) |
| **Time to deploy** | Hours (web wizard) | Days (XML + ESL setup) | Days (dialplan + AMI setup) |
| **Learning curve** | Low (web interface) | Steep (XML, ESL, C modules) | Moderate (dialplan syntax) |
| **Best for** | SMBs, MSPs, hosting providers | Telecom vendors, product builders | Enterprises with telecom engineers |

## FAQ

### What is the difference between a PBX and a call center platform?

A PBX (Private Branch Exchange) handles basic call routing — extensions, voicemail, and call transfer. A call center platform adds queue management, agent state tracking, IVR menus, call recording, reporting, and CRM integration. All three tools in this guide can function as either a PBX or a call center, depending on how you configure them.

### Can I run a call center with remote agents using these tools?

Yes. All three platforms support SIP endpoints over the internet. Agents can use softphones (Linphone, Zoiper, MicroSIP) on laptops or mobile SIP apps on smartphones. FreeSWITCH and Asterisk also support WebRTC for browser-based agent connections without installing any software.

### How many concurrent calls can a self-hosted call center handle?

A properly sized FreeSWITCH or Asterisk server on modern hardware can handle 500-2,000 concurrent calls. FusionPBX inherits FreeSWITCH's capacity since it uses FreeSWITCH as its telephony engine. Actual capacity depends on codec choice (G.711 uses more CPU than G.729), call recording overhead, and whether transcoding is needed.

### Do these platforms support predictive dialing for outbound campaigns?

FreeSWITCH's `mod_callcenter` and Asterisk's `app_dial` can be configured for predictive dialing, but dedicated predictive dialer functionality (like Vicidial's algorithm) requires additional modules or custom development. For production outbound campaigns, consider integrating with GoAutoDial (built on Asterisk) or building a custom dialer using the ESL/ARI APIs.

### How do I integrate these platforms with a CRM like HubSpot or Salesforce?

FreeSWITCH uses its Event Socket Layer to push call events (answered, hung up, queued) to external applications via TCP. Asterisk provides AMI (TCP-based) and ARI (REST API) for the same purpose. FusionPBX exposes a REST API and webhook system. In all cases, you build a middleware application that listens for call events and updates your CRM via its API — displaying caller info on agent screens when calls arrive.

### Can I migrate from a cloud call center to a self-hosted platform?

Yes, but the migration effort depends on your current setup. Extension numbers and SIP trunk configurations transfer directly. IVR flows and queue configurations need to be recreated in the new platform's format. Call history and recordings may require custom export/import scripts. Plan for a 2-4 week migration project for a 20-agent call center.

## Final Recommendation

For **small to medium businesses** that want a ready-to-use call center with a web interface, FusionPBX is the fastest path to production. Its multi-tenant architecture also makes it ideal for hosting providers managing call centers for multiple clients. For **engineering teams** building custom telephony products, FreeSWITCH's modular architecture and Event Socket API provide unmatched flexibility. For **organizations with existing Asterisk expertise** or complex dialplan requirements, Asterisk's mature ecosystem and extensive documentation make it a reliable foundation.

For related reading, see our [Kamailio vs Asterisk vs FreeSWITCH VoIP/PBX comparison](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/) and [Postal vs Stalwart vs Haraka SMTP relay guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "FusionPBX vs FreeSWITCH vs Asterisk: Self-Hosted Call Center Software Guide 2026",
  "description": "Compare FusionPBX, FreeSWITCH, and Asterisk for self-hosted call center deployment. Complete guide with Docker configs, queue management, IVR setup, and agent dashboard configuration.",
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
