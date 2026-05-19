---
title: "Self-Hosted Diameter Protocol AAA Servers: FreeDiameter vs Open5GS HSS vs Kamailio Diameter"
date: "2026-05-19"
tags: ["diameter-protocol", "aaa-server", "freediameter", "open5gs", "kamailio", "telecom", "5g-core", "network-infrastructure"]
draft: false
---

The Diameter protocol is the successor to RADIUS for Authentication, Authorization, and Accounting (AAA) in modern telecommunications networks. While RADIUS remains popular for enterprise network access control, Diameter is the standard for 3GPP LTE/5G core networks, IMS (IP Multimedia Subsystem), and carrier-grade AAA services.

This guide compares three open-source Diameter implementations: **FreeDiameter**, the **Open5GS HSS/AAA** component, and **Kamailio's Diameter module**. Each serves different use cases from research and testing to production 5G core deployment.

## What Is the Diameter Protocol?

Diameter (RFC 6733) is an AAA protocol designed to address the limitations of RADIUS in modern networks:

- **TCP/SCTP transport**: Unlike RADIUS's UDP-only transport, Diameter supports TCP and SCTP for reliable delivery
- **TLS security**: Built-in TLS support for encrypted AAA communication
- **Failover support**: Peer-to-peer architecture with automatic failover between Diameter agents
- **Extensible AVPs**: Attribute-Value Pairs (AVPs) allow protocol extension without breaking compatibility
- **Stateful connections**: Persistent connections between peers for improved reliability
- **Realm-based routing**: Diameter agents can route requests based on realm (domain) information

Diameter is used in:
- **LTE/5G mobile cores**: HSS, MME, PCRF, and OCS all use Diameter interfaces
- **Wi-Fi offloading**: Hotspot 2.0 and EAP-AKA' use Diameter for AAA
- **Fixed broadband**: BNG (Broadband Network Gateway) authentication via Diameter
- **IMS**: SIP-based multimedia services use Diameter for billing and policy control
- **Enterprise AAA**: Large-scale RADIUS replacement for carrier environments

## FreeDiameter: Open-Source Diameter Implementation

[FreeDiameter](https://github.com/verteiltesysteme/freediameter) (200+ stars) is a fully open-source Diameter protocol implementation designed for research, testing, and production AAA deployments. It provides a complete Diameter stack with extensible extension framework.

**Key features:**

- Full RFC 6733 Diameter protocol compliance
- TCP and SCTP transport support
- TLS encryption for Diameter peer connections
- Extension framework in C for custom Diameter applications
- Includes sample extensions: DIAMETER_EAP, DIAMETER_BASE_ACCOUNTING
- Peer discovery and realm-based routing
- Docker deployment via community images
- Active development with regular releases

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  freediameter:
    image: verteiltesysteme/freediameter:latest
    container_name: freediameter
    restart: unless-stopped
    ports:
      - "3868:3868/tcp"
      - "3868:3868/sctp"
    volumes:
      - ./freediameter-config:/etc/freediameter
      - ./freediameter-log:/var/log/freediameter
      - ./freediameter-certs:/etc/freediameter/certs:ro
    environment:
      - FD_CONF_FILE=/etc/freediameter/freediameter.conf
      - FD_LOG_LEVEL=DEBUG
    cap_add:
      - NET_ADMIN
```

FreeDiameter configuration:

```conf
# freediameter.conf
Identity = "aaa.example.com";
Realm = "example.com";
Port = 3868;
Port_sec = 3869;
No_SCTP;

# TLS configuration
TLS_Cred = "/etc/freediameter/certs/cert.pem";
TLS_CA = "/etc/freediameter/certs/ca.pem";

# Peers
Peer { "hss.example.com"; No_TCP; No_SCTP; };
Peer { "pcrf.example.com"; No_TCP; Connect = "hss.example.com"; };

# Extensions
LoadExtension = "extensions/dict_eap.fdx" : "eap_entry";
LoadExtension = "extensions/dict_dcca.fdx" : "dcca_entry";
LoadExtension = "extensions/dict_rfc5777.fdx";
```

## Open5GS HSS: 5G Core Diameter AAA

[Open5GS](https://github.com/open5gs/open5gs) (2,570+ stars) is a complete open-source 5G Core and EPC implementation. Its HSS (Home Subscriber Server) component provides Diameter-based AAA for LTE/EPC networks, implementing the S6a, Cx, and Sh interfaces.

**Key features:**

- Full 5G Core implementation with all network functions
- HSS with Diameter S6a interface (MME-HSS authentication)
- UDM/UDR for 5G service-based architecture
- PCRF/PCF for policy and charging control
- Integrated with MongoDB for subscriber data storage
- Web-based management UI for subscriber provisioning
- Docker deployment via docker-compose
- Production-ready with carrier-grade reliability

### Docker Compose Deployment

Open5GS provides a complete docker-compose setup:

```yaml
version: "3.8"
services:
  mongodb:
    image: mongo:6.0
    container_name: open5gs-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"

  hss:
    image: open5gs/hss:latest
    container_name: open5gs-hss
    restart: unless-stopped
    volumes:
      - ./open5gs-config/hss:/open5gs/etc/open5gs
      - ./open5gs-config/hss/freeDiameter:/open5gs/etc/freeDiameter
    depends_on:
      - mongodb

  mme:
    image: open5gs/mme:latest
    container_name: open5gs-mme
    restart: unless-stopped
    volumes:
      - ./open5gs-config/mme:/open5gs/etc/open5gs
      - ./open5gs-config/mme/freeDiameter:/open5gs/etc/freeDiameter
    depends_on:
      - hss

  webui:
    image: open5gs/webui:latest
    container_name: open5gs-webui
    restart: unless-stopped
    ports:
      - "9999:9999"
    environment:
      - DB_URI=mongodb://mongodb/open5gs
    depends_on:
      - mongodb
```

### Subscriber Provisioning via Web UI

Open5GS provides a web interface for managing subscribers:

1. Access the web UI at `http://<server>:9999`
2. Add a new subscriber with IMSI, MSISDN, and APN configuration
3. Configure QoS profiles, APN settings, and AMBR limits
4. The HSS automatically makes subscriber data available via Diameter S6a

## Kamailio Diameter Module: SIP+Diameter Integration

[Kamailio](https://github.com/kamailio/kamailio) (2,200+ stars) is a high-performance SIP server that includes a Diameter module (`app_diam`) for integrating SIP-based services with Diameter AAA infrastructure.

**Key features:**

- Diameter client and server functionality within Kamailio
- Integration with Rf and Ro interfaces for IMS charging
- SIP-to-Diameter gateway capabilities
- High-performance SIP routing with Diameter-based authorization
- Lua and Python scripting for custom Diameter logic
- Supports millions of calls per second
- Docker deployment via official Kamailio images

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kamailio:
    image: kamailio/kamailio:5.7-alpine
    container_name: kamailio-diameter
    restart: unless-stopped
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "3868:3868/tcp"
    volumes:
      - ./kamailio-config:/etc/kamailio
      - ./kamailio-diameter:/etc/kamailio/diameter
      - ./kamailio-log:/var/log/kamailio
    command:
      - "-f"
      - "/etc/kamailio/kamailio.cfg"
      - "-m"
      - "128"
      - "-M"
      - "16"
      - "-E"
      - "-e"
```

Kamailio configuration with Diameter module:

```cfg
# kamailio.cfg
#!define WITH_DIAMETER

#!ifdef WITH_DIAMETER
loadmodule "app_diam.so"
modparam("app_diam", "config_file", "/etc/kamailio/diameter/diameter.xml")
modparam("app_diam", "diameter_realm", "example.com")
modparam("app_diam", "diameter_identity", "sip.example.com")
#!endif

request_route {
    # Diameter authorization check
    if (is_method("INVITE")) {
        if (!diam_auth_check()) {
            sl_send_reply("403", "Forbidden - Diameter auth failed");
            exit;
        }
    }
    # Continue with SIP routing
    route(RELAY);
}
```

## Comparison: FreeDiameter vs Open5GS HSS vs Kamailio Diameter

| Feature | FreeDiameter | Open5GS HSS | Kamailio Diameter |
|---------|-------------|-------------|-------------------|
| **Primary purpose** | Diameter protocol stack | 5G Core HSS/AAA | SIP server with Diameter |
| **Diameter interfaces** | Generic (extensible) | S6a, Cx, Sh, Gx | Rf, Ro, generic |
| **Transport** | TCP, SCTP | TCP | TCP, SCTP |
| **TLS support** | Yes | Via FreeDiameter | Limited |
| **Peer routing** | Yes (realm-based) | Yes (S6a only) | Yes |
| **Subscriber database** | Extension-dependent | MongoDB | External (DB, LDAP) |
| **Management UI** | No | Yes (web UI) | No (CLI only) |
| **5G support** | No (LTE/EPC) | Yes (full 5G Core) | IMS only |
| **SIP integration** | No | No | Yes (native) |
| **Docker support** | Community images | Official compose | Official images |
| **License** | BSD | AGPL v3 | GPL v2 |
| **GitHub stars** | 200+ | 2,570+ | 2,200+ |
| **Best for** | Research, custom Diameter apps | LTE/5G mobile core | IMS/SIP+Diameter integration |

## Choosing the Right Diameter Implementation

**Choose FreeDiameter if:**
- You need a standalone, extensible Diameter protocol stack
- You're building custom Diameter applications or research prototypes
- You need full RFC 6733 compliance with TLS support
- You want to write custom Diameter extensions in C
- You're deploying Diameter for non-telecom AAA (enterprise, broadband)

**Choose Open5GS HSS if:**
- You're building a complete LTE/5G core network
- You need S6a interface for MME-HSS authentication
- You want a web-based subscriber management UI
- You need MongoDB-backed subscriber data storage
- You're deploying a production-grade mobile core

**Choose Kamailio Diameter if:**
- You need SIP-to-Diameter gateway functionality
- You're building an IMS charging and policy platform
- You want Diameter authorization integrated with SIP routing
- You need high-performance SIP processing with Diameter AAA
- You're deploying carrier-grade VoIP/UC infrastructure

## Why Self-Host Your Diameter AAA Server?

Running Diameter AAA infrastructure on-premises is essential for telecom operators, MVNOs, and enterprises managing carrier-grade networks. Self-hosted Diameter servers provide complete control over subscriber data, AAA policies, and interconnect peering arrangements.

Self-hosted Diameter servers offer several advantages:

**Subscriber data sovereignty**: All subscriber authentication, authorization, and billing data stays within your infrastructure. No subscriber profiles are shared with cloud AAA vendors or third-party HSS providers.

**Interconnect control**: Diameter peer connections to roaming partners, interconnect providers, and wholesale carriers are managed directly. You control the peering topology, realm routing, and security policies.

**Regulatory compliance**: Telecom regulations in most jurisdictions require operators to maintain direct control over subscriber authentication and billing systems. Self-hosted Diameter servers meet these requirements.

**Custom AVP support**: You can implement proprietary AVPs for custom services, billing models, or network features without depending on cloud vendor APIs.

**Cost efficiency**: Carrier-grade cloud HSS/Diameter services charge per-subscriber or per-transaction fees. Self-hosted implementations eliminate these recurring costs.

For related AAA infrastructure, see our [FreeRADIUS vs ToughRADIUS vs TACACS+ comparison](../2026-04-25-freeradius-vs-toughradius-vs-tac-plus-self-hosted-aaa-servers-2026/) and [NAC platforms guide](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/). For telecom core networks, check our [NETCONF/YANG guide](../2026-05-18-netopeer2-vs-opendaylight-vs-confd-netconf-yang-guide/).

## FAQ

### What is the difference between RADIUS and Diameter?

Diameter is the successor to RADIUS (RFC 2865) designed for modern carrier networks. Key differences: Diameter uses TCP/SCTP instead of UDP (reliable transport), has built-in TLS support, supports stateful connections with automatic failover, uses Attribute-Value Pairs (AVPs) instead of RADIUS attributes (extensible), supports peer-to-peer routing (not just client-server), and provides better error handling and accounting.

### Can FreeDiameter be used in production telecom networks?

Yes, FreeDiameter is used in production by several telecom operators and MVNOs. It provides full RFC 6733 compliance with TLS, SCTP support, and an extensible extension framework. However, for full 5G Core deployments, Open5GS is recommended as it includes all required 3GPP interfaces (S6a, Cx, Sh, Gx) out of the box.

### Does Open5GS support 5G Service-Based Architecture (SBA)?

Yes, Open5GS implements both the LTE/EPC architecture (with Diameter interfaces) and the 5G SBA (with HTTP/2-based service interfaces). The HSS component provides Diameter S6a for LTE devices, while the UDM/UDR provides 5G service-based interfaces for 5G devices.

### Can Kamailio act as a Diameter server?

Kamailio's Diameter module primarily acts as a Diameter client (sending CCR/CCR-A messages to external Diameter servers). It can also function as a Diameter agent for routing, but it's not a full Diameter server like FreeDiameter. For full Diameter server functionality, use FreeDiameter alongside Kamailio.

### How do I secure Diameter peer connections?

Diameter supports TLS encryption for peer-to-peer communication. Configure TLS certificates in your Diameter configuration (FreeDiameter uses `TLS_Cred` and `TLS_CA` directives). Use certificate-based peer authentication, restrict allowed peer identities, and enable SCTP transport for additional reliability.

### What Diameter interfaces does Open5GS implement?

Open5GS HSS implements S6a (MME-HSS for LTE authentication), Cx (IMS-CSCF to HSS for SIP registration), and Sh (AS to HSS for subscriber data). The PCRF implements Gx (PCEF-PCRF for policy and charging control). For 5G, the UDM implements service-based interfaces (Nudm) instead of Diameter.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Diameter Protocol AAA Servers: FreeDiameter vs Open5GS HSS vs Kamailio Diameter",
  "description": "Compare three open-source Diameter AAA server implementations for telecom and carrier networks: FreeDiameter, Open5GS HSS, and Kamailio Diameter module.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
