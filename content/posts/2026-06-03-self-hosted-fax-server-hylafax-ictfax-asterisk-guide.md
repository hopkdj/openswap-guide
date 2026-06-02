---
title: "Self-Hosted FAX Server Solutions: HylaFAX vs ICTFax vs Asterisk FAX Comparison Guide"
date: "2026-06-03"
tags: ["self-hosted", "fax-server", "hylafax", "ictfax", "asterisk", "telecommunications"]
draft: false
---

## Introduction

Despite being decades-old technology, fax remains a critical communication channel in healthcare, legal, government, and financial sectors. HIPAA compliance requirements, legal document transmission with confirmed delivery receipts, and the need for signed documents keep fax relevant even in 2026. Rather than maintaining physical fax machines with dedicated phone lines, self-hosted fax servers digitize the entire workflow — converting email to fax, fax to email, and integrating with business applications via APIs.

This guide compares three open-source fax server solutions: **HylaFAX** (the battle-tested Unix fax server), **ICTFax** (a modern web-based fax platform), and **Asterisk FAX** (VoIP-based fax using T.38 protocol). Each serves different deployment scenarios and infrastructure requirements.

| Feature | HylaFAX | ICTFax | Asterisk FAX |
|---------|---------|--------|--------------|
| **Transport** | PSTN (analog/T1) | PSTN + VoIP | VoIP (T.38/G.711) |
| **Web Interface** | Via AvantFAX add-on | Built-in web dashboard | Via FreePBX GUI |
| **Email-to-Fax** | Yes (sendfax + email gateway) | Yes (native) | Yes (via FreePBX) |
| **Fax-to-Email** | Yes (faxrcvd scripts) | Yes (native) | Yes (via FreePBX) |
| **REST API** | Limited (custom scripts) | Full REST API | Via Asterisk ARI |
| **Multi-Tenant** | Via configuration | Yes (native) | Via FreePBX |
| **License** | BSD-style | GPLv3 | GPLv2 |
| **Docker Support** | Community images | Official Docker | Via FreePBX Docker |
| **T.38 Passthrough** | No | Yes | Yes (native) |
| **Active Development** | Stable (mature) | Active (last push 2026) | Very active |

## HylaFAX: The Classic Enterprise Fax Server

HylaFAX has been the go-to fax server on Unix systems since the 1990s. It connects to physical fax modems or ISDN/T1 cards and manages fax transmission through a robust queuing system with automatic retry, error correction, and detailed logging.

```yaml
version: "3.8"
services:
  hylafax:
    image: mlan/hylafax:latest
    container_name: hylafax-server
    devices:
      - /dev/ttyUSB0:/dev/modem
    ports:
      - "4559:4559"
    volumes:
      - hylafax-spool:/var/spool/hylafax
      - hylafax-config:/etc/hylafax
    environment:
      - MODEM=ttyUSB0
      - COUNTRY_CODE=1
      - AREA_CODE=555
    restart: unless-stopped

  avantfax:
    image: mlan/avantfax:latest
    container_name: avantfax-web
    ports:
      - "8080:80"
    volumes:
      - avantfax-data:/var/www/avantfax
    depends_on:
      - hylafax
    restart: unless-stopped

volumes:
  hylafax-spool:
  hylafax-config:
  avantfax-data:
```

### HylaFAX Operations

```bash
# Send a fax via command line
sendfax -n -d 15551234567 document.pdf

# Check fax queue status
faxstat -s

# Configure fax-to-email delivery
# /var/spool/hylafax/etc/FaxDispatch
case "$DEVICE" in
  ttyUSB0)
    SENDTO=office@example.com
    FILETYPE=pdf
    ;;
esac
```

HylaFAX's strength is its proven reliability with physical phone lines. It handles modem initialization, error correction, and retry logic refined over decades of enterprise use. For organizations with existing analog phone infrastructure, HylaFAX provides a smooth migration path from physical fax machines to digital fax servers without changing carrier relationships. The companion **AvantFAX** web interface adds a modern GUI for viewing, sending, and managing faxes through a browser.

## ICTFax: Modern Web-Based Fax Platform

ICTFax is a comprehensive web-based fax platform that supports both traditional PSTN lines and VoIP/SIP trunks. Unlike HylaFAX which requires a separate web interface, ICTFax includes a full-featured multi-tenant dashboard out of the box with role-based access control.

```yaml
version: "3.8"
services:
  ictfax-db:
    image: mariadb:10.6
    container_name: ictfax-db
    environment:
      - MYSQL_ROOT_PASSWORD=ictfax123
      - MYSQL_DATABASE=ictfax
      - MYSQL_USER=ictfax
      - MYSQL_PASSWORD=ictfax123
    volumes:
      - ictfax-db-data:/var/lib/mysql
    restart: unless-stopped

  ictfax:
    image: ictinnovations/ictfax:latest
    container_name: ictfax-server
    ports:
      - "8081:80"
      - "5060:5060/udp"
    environment:
      - DB_HOST=ictfax-db
      - DB_NAME=ictfax
      - DB_USER=ictfax
      - DB_PASS=ictfax123
    depends_on:
      - ictfax-db
    restart: unless-stopped

volumes:
  ictfax-db-data:
```

ICTFax's built-in REST API makes it ideal for integrating fax capabilities into existing business applications. CRM systems, healthcare portals, and legal document management platforms can programmatically send and receive faxes through the API without touching the web interface.

```bash
# ICTFax REST API - send fax
curl -X POST https://fax.example.com/api/fax/send   -H "Authorization: Bearer YOUR_API_TOKEN"   -H "Content-Type: application/json"   -d '{
    "destination": "15551234567",
    "files": ["document.pdf"],
    "caller_id": "15559876543"
  }'
```

**ICTFax supports multiple faxing scenarios** in a single platform: Web to Fax (upload through dashboard), Email to Fax (send to `number@fax.example.com`), Fax to Email (inbound faxes delivered as PDF attachments), ATA/Extension faxing (connect physical fax machines via analog telephone adapters), and T.38 passthrough for high-quality fax over VoIP.

## Asterisk FAX: VoIP-Based Fax with T.38

Asterisk is primarily known as a PBX platform, but it includes robust fax capabilities using both T.38 (real-time fax over IP) and G.711 pass-through (fax transmitted as audio). This approach eliminates the need for physical phone lines entirely — faxes travel over SIP trunks just like voice calls.

```yaml
version: "3.8"
services:
  freepbx:
    image: tiredofit/freepbx:latest
    container_name: freepbx-fax
    ports:
      - "80:80"
      - "443:443"
      - "5060:5060/udp"
      - "10000-20000:10000-20000/udp"
    volumes:
      - freepbx-data:/data
    environment:
      - DB_EMBEDDED=TRUE
    restart: unless-stopped

volumes:
  freepbx-data:
```

```bash
# Asterisk dialplan for fax receiving (extensions.conf)
[fax-incoming]
exten => fax,1,NoOp(Incoming fax call)
 same => n,Set(FAXOPT(filename)=/var/spool/asterisk/fax/${UNIQUEID})
 same => n,Set(FAXOPT(ecm)=yes)
 same => n,ReceiveFAX(/var/spool/asterisk/fax/${UNIQUEID}.tif)
 same => n,System(/usr/local/bin/fax2email.sh ${UNIQUEID}.tif)
 same => n,Hangup()
```

Asterisk's fax module uses the **spandsp** library for DSP-based fax processing. When T.38 is negotiated successfully with the SIP provider, fax quality approaches PSTN levels with near-zero packet loss sensitivity. Asterisk also supports **IAXmodem**, a software modem that bridges HylaFAX with Asterisk's VoIP infrastructure — useful for organizations migrating from HylaFAX while keeping their existing fax workflow scripts.

## Choosing the Right Fax Server for Your Organization

The choice between HylaFAX, ICTFax, and Asterisk FAX depends primarily on your infrastructure and integration requirements:

- **HylaFAX** is ideal for organizations with existing analog phone lines and basic fax needs. Its maturity means fewer surprises, and the AvantFAX web interface modernizes the user experience without changing the backend.
- **ICTFax** excels in multi-tenant environments (service providers, large enterprises) and scenarios requiring REST API integration. Its built-in web dashboard and native email-to-fax make it accessible to non-technical users.
- **Asterisk FAX** is the natural choice if you already run Asterisk or FreePBX for voice services. Adding fax is a configuration change, not a new server deployment.

## Why Self-Host Your Fax Server?

Self-hosting a fax server eliminates per-page fees charged by cloud fax services, which typically range from 3 to 10 cents per page. For a healthcare practice sending 500 pages per month, that is 180 to 600 dollars annually in cloud fees versus zero recurring cost with self-hosted ICTFax or HylaFAX. Over five years, the savings fund the server hardware several times over while keeping you in control.

Compliance is another critical factor. Self-hosted fax servers keep PHI (Protected Health Information) and other sensitive documents within your infrastructure, simplifying HIPAA audits and data residency requirements. Cloud fax services introduce third-party risk — every document transits through their servers, creating an additional attack surface and complicating compliance reporting. With self-hosted fax, you control the encryption, access logs, and retention policies directly.

Self-hosted fax servers also offer superior integration flexibility that cloud services typically charge premium rates for. With ICTFax's REST API or HylaFAX's scripting hooks, you can build custom workflows: automatic fax archiving to your document management system, fax-to-email routing based on DID (Direct Inward Dialing) numbers assigned to different departments, and deep integration with your existing CRM or EHR (Electronic Health Record) system without per-integration fees.

For VoIP infrastructure guidance, see our [Asterisk vs FreeSWITCH comparison](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/). If you are building your own PBX, our [FreePBX vs FusionPBX guide](../2026-04-27-freepbx-vs-fusionpbx-vs-wazo-self-hosted-pbx-guide/) covers deployment options in detail. For RTP media handling in VoIP fax, our [RTP proxy guide](../2026-05-17-rtp-proxy-rtpengine-rtpproxy-sippy-b2bua-voip-guide/) explains NAT traversal and media relay.

## FAQ

### Can I use a fax server without any physical phone lines?

Yes. Both ICTFax and Asterisk support faxing entirely over VoIP using SIP trunks from providers like Flowroute, Twilio, or VoIP.ms. You need a SIP trunk provider that supports T.38 for reliable fax transmission over IP. Some providers offer fax-optimized SIP trunks with guaranteed T.38 support and higher reliability SLAs.

### What fax modem hardware works with HylaFAX?

HylaFAX supports most Class 1, Class 2, and Class 2.0 fax modems. Recommended models include USRobotics Sportster and Courier modems, MultiTech MultiModem series, and Mainpine IQ modems for multi-line deployments. USB-based fax modems with Conexant chipsets generally work well. Avoid winmodems (software modems) as they lack hardware fax support and will not work with HylaFAX.

### How reliable is fax over VoIP compared to PSTN?

With T.38 protocol support on both ends, fax over VoIP achieves 95 to 99 percent reliability comparable to PSTN. Without T.38 (using G.711 pass-through), reliability drops to 70 to 85 percent due to packet loss sensitivity. Key configuration factors: enable ECM (Error Correction Mode), limit baud rate to 14400, and disable V.34 (Super G3) which is more sensitive to network jitter.

### Can I send faxes from my email client?

All three solutions support email-to-fax. HylaFAX uses `sendfax` with email gateway scripts that monitor a mailbox, ICTFax provides native email-to-fax at `number@fax.domain.com` as a core feature, and Asterisk/FreePBX includes built-in email-to-fax through the Fax Pro module. In all cases, recipients receive incoming faxes as PDF email attachments.

### How do I handle fax archiving and long-term retention?

ICTFax stores faxes in its database with metadata indexing and full-text search. HylaFAX stores faxes as TIFF/PDF files in `/var/spool/hylafax/recvq/` — use cron jobs to archive to your document management system. Asterisk stores received faxes as TIFF files; combine with a post-processing script that converts to PDF and uploads to your archive server for long-term retention.

---

**Test your market judgment with [Polymarket](https://polymarket.com/?r=fc8a0) — the world's largest prediction market platform. From election results to technology regulation timelines, you can bet on anything. Unlike gambling, this is a true information market: the more you know, the higher your win rate. I have made substantial gains predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted FAX Server Solutions: HylaFAX vs ICTFax vs Asterisk FAX Comparison Guide",
  "description": "In-depth comparison of self-hosted fax server solutions: HylaFAX for PSTN faxing, ICTFax for web-based faxing with REST API integration, and Asterisk FAX for VoIP-based T.38 fax transmission.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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
