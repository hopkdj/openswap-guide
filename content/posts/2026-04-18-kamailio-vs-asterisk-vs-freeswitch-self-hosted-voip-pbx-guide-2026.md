---
title: "Kamailio vs Asterisk vs FreeSWITCH: Best Self-Hosted VoIP/PBX Server 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "voip", "pbx", "telephony", "sip"]
draft: false
description: "Compare Kamailio, Asterisk, and FreeSWITCH — the top three open-source VoIP/PBX servers. Complete deployment guide with Docker configs, feature comparison, and setup instructions for self-hosted telephony in 2026."
---

Building your own telephone system used to require expensive proprietary hardware and vendor lock-in. Today, three mature open-source projects — **Kamailio**, **Asterisk**, and **FreeSWITCH** — let you run a full-featured VoIP/PBX server on commodity hardware, handling everything from SIP registration and call routing to voicemail, conferencing, and IVR menus.

Whether you're replacing a costly 3CX license, building a carrier-grade SIP proxy, or setting up a homelab PBX for your small office, this guide compares the three leading options and shows you exactly how to deploy each one.

## Why Self-Host Your Own VoIP/PBX System?

Commercial PBX solutions like 3CX, RingCentral, and Vonage charge per-user licensing fees that scale painfully as your organization grows. They also require your call signaling and media to traverse third-party infrastructure — a privacy concern for businesses handling sensitive communications.

Self-hosting your VoIP stack gives you:

- **Full control over call routing** — no vendor-imposed limits on simultaneous calls or features
- **Complete data ownership** — call recordings, CDRs, and voicemail never leave your network
- **No per-seat licensing** — open-source means unlimited extensions and trunks
- **Custom integrations** — direct API access to CRM, helpdesk, or monitoring systems
- **Cost savings** — eliminate recurring per-user fees that can run $20-50/month per seat

The tradeoff is operational com[plex](https://www.plex.tv/)ity. You're responsible for SIP security, NAT traversal, codec negotiation, and high availability. But with the right tool choice and proper configuration, a self-hosted VoIP system is both reliable and cost-effective at any scale.

## Kamailio: The High-Performance SIP Proxy

[**Kamailio**](https://www.kamailio.org/) (formerly OpenSER) is a SIP server designed for large-scale deployments. It doesn't handle media itself — instead, it routes SIP signaling between endpoints, media servers, and gateways. Think of it as the traffic controller for VoIP traffic.

As of April 2026, Kamailio has **2,798 GitHub stars** and receives regular updates (last pushed April 18, 2026). It's written in C and known for handling tens of thousands of concurrent SIP sessions on modest hardware.

### When to Choose Kamailio

- You need a **SIP proxy/load balancer** for thousands of users
- You want to build a carrier-grade SIP infrastructure
- You need fine-grained control over SIP routing logic
- You plan to pair it with a separate media server (RTPengine, Sippy B2BUA)

Kamailio excels at **registration, authentication, routing, and load distribution**. It's not a PBX — it won't give you voicemail, IVR, or conferencing out of the box. Those require pairing Kamailio with a media server like Asterisk or FreeSWITCH.

### Key Strengths

| Capability | Details |
|---|---|
| Throughput | 6,000+ calls per second on a single server |
| Scalability | Proven in deployments with 1M+ subscribers |
| Modules | 200+ modules for auth, routing, database, caching, presence |
| Scripting | Custom routing logic via Kamailio Configuration Language |
| HA | Native support for clustering and state replication |

## Asterisk: The Classic Open-Source PBX

[**Asterisk**](https://www.asterisk.org/) by Sangoma is the most well-known open-source telephony platform. First released in 1999, it's a full PBX that handles both SIP signaling and media processing — meaning it can register phones, route calls, play IVR menus, record conversations, and host conference bridges all in one process.

As of April 2026, Asterisk has **3,192 GitHub stars** with the last update on April 16, 2026. It's written in C and has the largest community and ecosystem of the three options.

### When to Choose Asterisk

- You want a **complete PBX** out of the box — extensions, voicemail, IVR, queues
- You're building a small-to-medium business phone system
- You want the largest community, most tutorials, and widest third-party support
- You need broad hardware compatibility (analog FXO/FXS cards, ISDN PRI)

Asterisk is the Swiss Army knife of VoIP. It does almost everything, though not always at the highest performance level. For organizations under ~500 concurrent calls, Asterisk is often the simplest and most practical choice.

### Key Strengths

| Capability | Details |
|---|---|
| PBX Features | Extensions, voicemail, IVR, queues, ring groups, call parking |
| Protocol Support | SIP, IAX2, PJSIP, H.323, MGCP |
| Codec Support | G.711, G.729, G.722, OPUS, VP8, H.264 |
| Integrations | AGI (Asterisk Gateway Interface), ARI (REST API), AMI (manager) |
| Hardware | Analog and digital telephony cards via DAHDI |

## FreeSWITCH: The Modern Software-Defined Telecom Stack

[**FreeSWITCH**](https://freeswitch.org/) by SignalWire is the newest of the three, designed as a "software-defined telecom stack." It handles both signaling and media like Asterisk, but with a more modular architecture, better scalability, and support for modern protocols like WebRTC out of the box.

As of April 2026, FreeSWITCH has **4,804 GitHub stars** with the last update on April 2, 2026. It's written in C and is actively maintained by the SignalWire team.

### When to Choose FreeSWITCH

- You need **WebRTC support** for browser-based softphones
- You want a modular, scalable architecture for growing workloads
- You're building a communications platform (not just a PBX)
- You need high-quality audio processing with built-in echo cancellation

FreeSWITCH sits between Kamailio's raw performance and Asterisk's feature completeness. It's often described as "Asterisk done differently" — similar capabilities but with a cleaner internal design and better handling of concurrent sessions.

### Key Strengths

| Capability | Details |
|---|---|
| WebRTC | Native support for browser-based audio/video calls |
| Scalability | Better concurrent call handling than Asterisk |
| Modularity | Clean module architecture, easy to extend |
| Conference | Advanced conference bridge with video layout support |
| Scripting | Lua, JavaScript, Python, and ESL (Event Socket Library) |

## Feature Comparison Table

| Feature | Kamailio | Asterisk | FreeSWITCH |
|---|---|---|---|
| **Primary Role** | SIP Proxy/Router | Full PBX | Full PBX / Telecom Stack |
| **Media Handling** | No (requires RTPengine) | Yes (built-in) | Yes (built-in) |
| **SIP Support** | Excellent | Good (PJSIP) | Excellent |
| **WebRTC** | Via rtpengine | Via res_pjsip | Native |
| **Voicemail** | No | Yes | Yes |
| **IVR/Auto-Attendant** | No | Yes | Yes |
| **Conference Bridge** | No | Yes | Yes (advanced) |
| **Call Recording** | No | Yes | Yes |
| **Max Concurrent Calls** | 100,000+ (proxy only) | ~2,000-5,000 | ~5,000-10,000 |
| **Configuration** | Config language + modules | Dialplan + config files | XML dialplan + Lua/JS |
| **API Access** | RPC/Mi, HTTP | AMI, ARI (REST) | ESL (Event Socket) |
| **Database Backend[redis](https://redis.io/)MySQL, PostgreSQL, Redis | SQLite, ODBC | SQLite, PostgreSQL, ODBC |
| **Learning Curve** | Steep | Moderate | Moderate-Steeper |
| **Community Size** | Large | Largest | Medium |
| **Latest Release** | 5.8.x | 20.x | 1.10.x |

## Deployment Guide

### [docker](https://www.docker.com/)ing Kamailio with Docker

Kamailio is ideal for containerized deployment since it's a lightweight SIP proxy without media processing overhead.

Create a `docker-compose.yml` for Kamailio with a MySQL backend for user registration:

```yaml
version: "3.8"

services:
  kamailio:
    image: kamailio/kamailio:5.8
    container_name: kamailio
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./kamailio.cfg:/etc/kamailio/kamailio.cfg:ro
      - ./kamctlrc:/etc/kamailio/kamctlrc:ro
    depends_on:
      - mysql

  mysql:
    image: mysql:8
    container_name: kamailio-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: kamailio_root_pass
      MYSQL_DATABASE: kamailio
      MYSQL_USER: kamailio
      MYSQL_PASSWORD: kamailio_db_pass
    volumes:
      - kamailio_mysql_data:/var/lib/mysql

volumes:
  kamailio_mysql_data:
```

The critical piece is the `kamailio.cfg` routing configuration. A minimal SIP proxy config:

```cfg
#!KAMAILIO

# Global parameters
listen=udp:0.0.0.0:5060
listen=tcp:0.0.0.0:5060

# Database URL
#!define DBURL "mysql://kamailio:kamailio_db_pass@localhost/kamailio"

loadmodule "db_mysql.so"
loadmodule "auth.so"
loadmodule "auth_db.so"
loadmodule "registrar.so"
loadmodule "rr.so"
loadmodule "sl.so"
loadmodule "tm.so"
loadmodule "usrloc.so"
loadmodule "textopsx.so"

modparam("usrloc", "db_mode", 2)
modparam("usrloc", "db_url", DBURL)
modparam("auth_db", "calculate_ha1", yes)
modparam("auth_db", "password_column", "password")

request_route {
    if (is_method("REGISTER")) {
        if (!www_authorize("kamailio.local", "subscriber")) {
            www_challenge("kamailio.local", "0");
            exit;
        }
        save("location");
        exit;
    }

    if (is_method("INVITE")) {
        if (!proxy_authorize("kamailio.local", "subscriber")) {
            proxy_challenge("kamailio.local", "0");
            exit;
        }
        record_route();
        t_relay();
        exit;
    }

    sl_send_reply("405", "Method Not Allowed");
}
```

### Deploying Asterisk with Docker

Asterisk requires access to audio devices and specific ports for RTP media (10000-20000 UDP).

```yaml
version: "3.8"

services:
  asterisk:
    image: asterisk/asterisk:20
    container_name: asterisk
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./asterisk/etc:/etc/asterisk:rw
      - ./asterisk/var:/var/lib/asterisk:rw
      - ./asterisk/log:/var/log/asterisk:rw
      - ./asterisk/spool:/var/spool/asterisk:rw
    cap_add:
      - NET_ADMIN
```

A minimal `sip.conf` for Asterisk 20 using the PJSIP channel driver (`pjsip.conf`):

```ini
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060

[transport-tcp]
type=transport
protocol=tcp
bind=0.0.0.0:5060

[1000]
type=endpoint
context=internal
disallow=all
allow=ulaw,alaw,opus
auth=auth_1000
aors=1000

[auth_1000]
type=auth
auth_type=userpass
password=SecurePass123!
username=1000

[1000]
type=aor
max_contacts=1
remove_existing=yes

[internal]
type=endpoint
context=internal

[default]
type=endpoint
context=default
```

And a basic dialplan in `extensions.conf`:

```ini
[internal]
exten => 1000,1,Answer()
 same => n,Playback(demo-congrats)
 same => n,Hangup()

exten => 1001,1,Dial(PJSIP/1001,30)
 same => n,Voicemail(1001@default,u)
 same => n,Hangup()
```

### Deploying FreeSWITCH with Docker

FreeSWITCH's Docker deployment is the most resource-intensive due to its built-in media processing.

```yaml
version: "3.8"

services:
  freeswitch:
    image: signalwire/freeswitch:latest
    container_name: freeswitch
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./freeswitch/conf:/etc/freeswitch:rw
      - ./freeswitch/log:/var/log/freeswitch:rw
      - ./freeswitch/recordings:/var/lib/freeswitch/recordings:rw
    environment:
      - EXTERNAL_RTP_IP=YOUR_PUBLIC_IP
      - EXTERNAL_SIP_IP=YOUR_PUBLIC_IP
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

FreeSWITCH uses XML configuration files. A minimal `vars.xml` snippet for defining extensions:

```xml
<X-PRE-PROCESS cmd="set" data="default_password=SecurePass123!"/>
<X-PRE-PROCESS cmd="set" data="external_rtp_ip=stun:stun.freeswitch.org"/>
<X-PRE-PROCESS cmd="set" data="external_sip_ip=stun:stun.freeswitch.org"/>
```

For production, set `external_rtp_ip` and `external_sip_ip` to your public IP or domain name. FreeSWITCH's NAT handling is more sophisticated than Asterisk's, using STUN by default for automatic discovery.

## Choosing the Right VoIP Server

Your decision comes down to one question: **do you need media processing?**

- **Choose Kamailio** if you only need SIP signaling — routing, load balancing, or a SIP front-end. Pair it with a media server for full PBX functionality. Many large deployments use Kamailio as the front-end with Asterisk or FreeSWITCH handling media in the backend.
- **Choose Asterisk** if you want a complete, self-contained PBX with the largest community and the most tutorials available. It's the safest choice for most small-to-medium deployments.
- **Choose FreeSWITCH** if you need modern features like WebRTC, advanced conferencing, or are building a communications platform that needs to scale beyond what Asterisk comfortably handles.

For most homelab and small business use cases, **Asterisk** is the path of least resistance. For carrier-scale or WebRTC-first deployments, **FreeSWITCH** is worth the additional learning curve. For pure SIP proxy workloads at any scale, **Kamailio** is unmatched.

## Security Considerations for Self-Hosted VoIP

VoIP systems are frequent targets for toll fraud and SIP scanning attacks. Essential security measures include:

1. **Fail2ban integration** — All three servers log authentication failures in parseable formats. Configure Fail2ban to block IPs after repeated failed registration attempts.
2. **SIP TLS** — Encrypt SIP signaling with TLS certificates. For FreeSWITCH and Asterisk, this means configuring TLS transports. See our [PKI and certificate management guide](../self-hosted-pki-certificate-management-step-ca-caddy-nginx-proxy-manager-2026/) for setting up your own CA.
3. **SRTP for media** — Enable Secure RTP to encrypt voice/video streams. All three support SRTP, but it must be explicitly configured on each endpoint.
4. **Network segmentation** — Place your VoIP server on a dedicated VLAN. SIP servers should not be directly exposed to the internet without a firewall. Our [firewall and router guide](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide-2026/) covers network segmentation best practices.
5. **Strong passwords** — SIP extensions use simple username/password authentication. Enforce complex passwords and rotate them regularly.
6. **IP whitelisting for trunks** — If you use SIP trunks to connect to PSTN providers, restrict trunk access to specific provider IPs.

## Related Projects in the Self-Hosted Communications Stack

A VoIP server is just one piece of a complete self-hosted communications infrastructure. Consider pairing it with:

- **[Matrix/Synapse](../matrix-synapse-self-hosted-messaging-guide/)** for persistent messaging that complements real-time voice
- **[Jitsi Meet](../self-hosted-video-conferencing-jitsi-guide/)** for browser-based video conferencing alongside your SIP infrastructure
- **[MediamTX/RTMP streaming](../self-hosted-live-streaming-owncast-mediamtx-nginx-rtmp-guide-2026/)** for broadcast scenarios that integrate with FreeSWITCH's conferencing capabilities

## FAQ

### What is the difference between a SIP proxy and a PBX?

A SIP proxy (like Kamailio) only handles SIP signaling — it routes registration, call setup, and teardown messages between endpoints. It does not process audio/video media. A PBX (like Asterisk or FreeSWITCH) handles both signaling and media, providing features like voicemail, IVR menus, call recording, and conference bridges. Many large deployments use a SIP proxy as the front-end with PBX servers handling media in the backend.

### Can I run Kamailio, Asterisk, and FreeSWITCH together?

Yes — this is actually a common architecture for large deployments. Kamailio acts as the SIP front-end (handling registration, authentication, and load distribution), while Asterisk or FreeSWITCH handles media processing (conferencing, IVR, voicemail). This separates signaling from media, allowing each layer to scale independently.

### Do I need a static IP address for my self-hosted VoIP server?

For inbound SIP calls from the public internet, yes — you need either a static IP or a Dynamic DNS service. For internal deployments (LAN-only), a static internal IP is sufficient. If you're behind NAT, you'll also need to configure port forwarding for SIP (5060 TCP/UDP) and RTP media ports (typically 10000-20000 UDP).

### Is self-hosted VoIP legal?

Yes, running your own PBX is legal in virtually all jurisdictions. However, if you connect to the PSTN (public switched telephone network) through a SIP trunk provider, you may need to comply with local telecommunications regulations, emergency calling (E911) requirements, and lawful intercept obligations. Consult local regulations before offering telephony services to the public.

### How many concurrent calls can each server handle?

Performance depends heavily on hardware, codecs, and configuration. As rough guidelines: **Kamailio** (SIP proxy only) can handle 100,000+ concurrent SIP sessions on a well-tuned server. **Asterisk** typically handles 2,000-5,000 concurrent calls with media processing. **FreeSWITCH** handles 5,000-10,000 concurrent calls. These numbers assume multi-core servers (8+ cores) with adequate RAM and network bandwidth.

### Which VoIP server supports WebRTC natively?

FreeSWITCH has the most mature native WebRTC support, including automatic codec negotiation and built-in STUN/TURN handling. Asterisk supports WebRTC via the PJSIP channel driver but requires more manual configuration. Kamailio can proxy WebRTC signaling but requires an external media server (like RTPengine) to handle the WebRTC media streams.

### How do I protect my VoIP server from toll fraud?

Toll fraud occurs when attackers register to your PBX and make expensive international calls. Essential protections include: (1) using strong passwords for all extensions, (2) enabling Fail2ban for SIP authentication failures, (3) restricting international dialing in your dialplan, (4) using IP whitelisting for SIP trunks, (5) monitoring CDRs (call detail records) for unusual patterns, and (6) never exposing your PBX admin ports to the internet.

### Can I use these servers with analog phone lines?

Asterisk has the best support for analog hardware through DAHDI (Digium Asterisk Hardware Device Interface), which supports FXO (connect to analog phone lines) and FXS (connect analog phones) cards. FreeSWITCH has limited hardware support via mod_dahdi_codec. Kamailio does not support analog hardware at all — it's a pure SIP/IP solution.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kamailio vs Asterisk vs FreeSWITCH: Best Self-Hosted VoIP/PBX Server 2026",
  "description": "Compare Kamailio, Asterisk, and FreeSWITCH — the top three open-source VoIP/PBX servers. Complete deployment guide with Docker configs, feature comparison, and setup instructions for self-hosted telephony in 2026.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
