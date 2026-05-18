---
title: "Self-Hosted TR-069 ACS: GenieACS vs OktopUSP vs freeACS for CPE Management"
date: "2026-05-18"
tags: ["tr069", "cpe-management", "network-management", "self-hosted", "isp-tools"]
draft: false
---

The TR-069 (Technical Report 069) protocol, also known as CWMP (CPE WAN Management Protocol), enables remote management of customer premise equipment (CPE) such as routers, modems, VoIP phones, and IoT gateways. Self-hosting an ACS (Auto Configuration Server) gives ISPs, MSPs, and homelab operators full control over device provisioning, firmware updates, and configuration management. This guide compares three open-source ACS platforms: **GenieACS**, **OktopUSP**, and **freeACS**.

## What Is TR-069 / CWMP?

TR-069 is a broadband forum standard that defines how an ACS remotely manages CPE devices. The protocol operates over HTTP/HTTPS and supports:

- **Remote configuration** — push parameter changes to devices
- **Firmware management** — schedule and monitor OTA updates
- **Diagnostics** — run ping, traceroute, and speed tests on CPE
- **Event reporting** — receive notifications when devices boot, connect, or encounter errors
- **File transfer** — upload/download configuration files and firmware images

The CPE initiates connections to the ACS (typically on port 7547), which allows devices behind NAT to be managed without port forwarding.

## Comparison: GenieACS vs OktopUSP vs freeACS

| Feature | GenieACS | OktopUSP | freeACS |
|---------|----------|----------|---------|
| **Protocol** | TR-069 (CWMP) | TR-369 (USP) + TR-069 | TR-069 (CWMP) |
| **Language** | JavaScript (Node.js) | Java | Java |
| **Database** | MongoDB | MongoDB/PostgreSQL | MySQL |
| **Web UI** | Built-in | Built-in | Built-in |
| **REST API** | Yes | Yes | Limited |
| **Firmware Management** | Yes | Yes | Yes |
| **Provisioning Templates** | Yes (scriptable) | Yes (policy-based) | Yes |
| **Multi-vendor Support** | Extensive | Good | Good |
| **Scalability** | High (100k+ devices) | High | Medium |
| **Docker Support** | Official images | Official images | Manual build |
| **Stars / Activity** | 767+ (2026-04) | 115+ (2026-02) | 165+ (2024-04) |
| **License** | AGPL-3.0 | Apache-2.0 | GPL-3.0 |

## Deploying GenieACS

GenieACS is the most widely deployed open-source TR-069 ACS, known for its JavaScript-based scripting engine and high scalability.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  genieacs-ui:
    image: genieacs/genieacs:latest
    container_name: genieacs-ui
    restart: unless-stopped
    ports:
      - "3000:3000"
      - "7547:7547"
      - "7557:7557"
    environment:
      - GENIEACS_NOS_ADDRESS=0.0.0.0
      - GENIEACS_NOS_PORT=7547
      - GENIEACS_UI_ADDRESS=0.0.0.0
      - GENIEACS_UI_PORT=3000
      - GENIEACS_MONGO_URL=mongodb://mongodb:27017/genieacs
    depends_on:
      - mongodb
    networks:
      - genieacs-net

  genieacs-cwmp:
    image: genieacs/genieacs:latest
    container_name: genieacs-cwmp
    restart: unless-stopped
    ports:
      - "7567:7567"
    environment:
      - GENIEACS_CWMP_ADDRESS=0.0.0.0
      - GENIEACS_CWMP_PORT=7567
      - GENIEACS_MONGO_URL=mongodb://mongodb:27017/genieacs
    depends_on:
      - mongodb
    networks:
      - genieacs-net

  mongodb:
    image: mongo:6
    container_name: genieacs-mongo
    restart: unless-stopped
    volumes:
      - mongodb-data:/data/db
    networks:
      - genieacs-net

volumes:
  mongodb-data:

networks:
  genieacs-net:
    driver: bridge
```

### GenieACS Architecture

GenieACS uses a microservices architecture with three components:

1. **genieacs-cwmp** — handles TR-069 sessions with CPE devices (port 7567)
2. **genieacs-nbi** — North Bound Interface for external API calls
3. **genieacs-ui** — Web management interface (port 3000)
4. **MongoDB** — persistent storage for device data, presets, and logs

### Provisioning Script Example

```javascript
// GenieACS preset script — configure WAN on first boot
if (!declare("InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1")) {
  declare("InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username", {value: "isp-user"});
  declare("InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Password", {value: "isp-pass"});
  declare("InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Enable", {value: true});
}
```

## Deploying OktopUSP

OktopUSP is a unified platform supporting both TR-369 (USP — the next-generation protocol) and legacy TR-069, making it ideal for organizations transitioning between protocols.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  oktopus:
    image: oktopusp/oktopus:latest
    container_name: oktopus-acs
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "7547:7547"
    environment:
      - OKTOP_DB_URL=mongodb://mongodb:27017/oktopus
      - OKTOP_ACS_URL=http://acs.example.com:7547
      - OKTOP_LOG_LEVEL=info
    depends_on:
      - mongodb
    volumes:
      - ./oktopus-config:/etc/oktopus:ro
    networks:
      - oktopus-net

  mongodb:
    image: mongo:6
    container_name: oktopus-mongo
    restart: unless-stopped
    volumes:
      - oktopus-mongo-data:/data/db
    networks:
      - oktopus-net

volumes:
  oktopus-mongo-data:

networks:
  oktopus-net:
    driver: bridge
```

### OktopUSP Key Features

- **Dual protocol support** — manages both TR-069 and TR-369 (USP) devices from a single platform
- **Policy engine** — define configuration policies that automatically apply to device groups
- **USP controller** — acts as a STOMP endpoint for USP agents, enabling real-time device management
- **IoT support** — extended data model for IoT device management beyond traditional CPE

## Deploying freeACS

freeACS is a lightweight, Java-based TR-069 ACS with a simple web interface and MySQL backend.

### Installation (Manual Build)

freeACS does not have official Docker images. The recommended deployment is a manual build:

```bash
# Clone and build
git clone https://github.com/freeacs/freeacs.git
cd freeacs

# Build with Maven
mvn clean package -DskipTests

# Deploy the WAR file to Tomcat
cp web/target/freeacs-web*.war /opt/tomcat/webapps/ROOT.war
```

### Database Setup (MySQL)

```sql
CREATE DATABASE freeacs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'freeacs'@'localhost' IDENTIFIED BY 'strong-password';
GRANT ALL ON freeacs.* TO 'freeacs'@'localhost';
FLUSH PRIVILEGES;
```

### Reverse Proxy Configuration (Nginx)

```nginx
server {
    listen 80;
    server_name acs.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ACS-server {
        proxy_pass http://localhost:8080;
        client_max_body_size 50m;
    }
}
```

## CPE Configuration

To connect a CPE device to your ACS, configure the following on the device:

```
ManagementServer.URL = http://your-acs-server:7547
ManagementServer.PeriodicInformEnable = true
ManagementServer.PeriodicInformInterval = 3600
ManagementServer.ConnectionRequestURL = http://device-ip:7547
ManagementServer.Username = cpe-user
ManagementServer.Password = cpe-pass
```

Most modern routers and gateways support TR-069 configuration through their admin web interface or via a provisioning file.

## Monitoring and Troubleshooting

```bash
# GenieACS: Check connected devices via API
curl -s http://localhost:7557/devices | python3 -m json.tool

# MongoDB: Query device count
mongosh --eval "db.devices.countDocuments()" genieacs

# freeACS: View ACS logs
tail -f /opt/tomcat/logs/catalina.out | grep TR-069
```

## Choosing the Right ACS Platform

| Scenario | Recommendation |
|----------|---------------|
| Large-scale ISP deployment (10k+ devices) | **GenieACS** — proven scalability, mature ecosystem |
| Future-proofing with TR-369/USP | **OktopUSP** — only open-source option with USP support |
| Simple deployment, small network | **freeACS** — lightweight, easy to understand |
| JavaScript customization needed | **GenieACS** — scripting engine for provisioning logic |
| Multi-protocol environment (TR-069 + USP) | **OktopUSP** — unified platform for both protocols |

## Security Considerations for TR-069 Deployments

Securing your TR-069 ACS infrastructure is critical because the protocol has broad control over managed devices. A compromised ACS can push malicious configurations, install backdoor firmware, or exfiltrate sensitive network data from thousands of connected devices.

**Always use HTTPS** for ACS-to-CPE communication. TR-069 over plain HTTP transmits credentials and configuration data in cleartext. Deploy a reverse proxy with TLS termination (Nginx, Caddy, or Traefik) and obtain a certificate from Lets Encrypt. Configure CPE devices to validate the server certificate — many routers skip validation by default, which defeats the purpose of TLS.

**Implement device authentication** using ACS username/password pairs or client certificates. Do not use a single shared credential for all CPE devices. GenieACS supports per-device authentication through its device database, and OktopUSP supports X.509 certificate-based device identification for USP connections.

**Restrict ACS access by IP range** when possible. If your CPE fleet uses predictable IP ranges (such as a specific ISP subscriber block), configure firewall rules to only allow TR-069 connections from those ranges. This prevents unauthorized devices from registering with your ACS or flooding it with fake Inform messages.

**Rate-limit periodic informs** to prevent denial-of-service. CPE devices that misconfigure their PeriodicInformInterval to a very low value (e.g., every 10 seconds) can overwhelm your ACS. Configure server-side rate limiting at the reverse proxy level and monitor Inform frequency in your ACS logs.

**Audit provisioning scripts** before deploying them to production. A GenieACS preset script with a typo can misconfigure thousands of devices simultaneously. Test scripts against a staging ACS instance with a small device group before rolling out to your full fleet.

## Why Self-Host Your ACS?

Self-hosting a TR-069 ACS provides complete control over your device management infrastructure. Commercial ACS platforms charge per-device licensing fees that quickly become prohibitive at scale. An open-source ACS eliminates these costs while giving you direct access to device data, configuration histories, and firmware images.

**Data sovereignty is critical** — your ACS holds the complete configuration state of every managed device. Hosting this externally means a third party can see your network topology, firmware versions, and configuration changes. Self-hosting keeps this sensitive operational data within your infrastructure.

**Vendor independence** matters when managing multi-vendor device fleets. Commercial ACS platforms often prioritize their own hardware partners. Open-source platforms treat all TR-069 compliant devices equally, and the community actively contributes data models for diverse equipment.

For broader network device management, our [firmware OTA management guide](../2026-05-07-self-hosted-firmware-ota-update-management-hawkbit-rauc-swupdate-guide/) covers HawkBit, RAUC, and SWUpdate. For AAA server infrastructure, our [FreeRADIUS comparison](../2026-04-25-freeradius-vs-toughradius-vs-tac-plus-self-hosted-aaa-servers-2026/) covers authentication and authorization platforms. For IoT firmware platforms, our [ESPHome comparison](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) covers embedded device management.

## FAQ

### What is the difference between TR-069 and TR-369?

TR-069 (CWMP) is the original CPE management protocol using HTTP/HTTPS. TR-369 (USP — User Services Platform) is the next-generation protocol that adds MQTT, CoAP, and STOMP transport options, real-time messaging, and a more flexible data model. OktopUSP supports both; GenieACS and freeACS support TR-069 only.

### Can I manage consumer routers with a self-hosted ACS?

Yes, most ISP-provided routers and many consumer routers (TP-Link, Asus, MikroTik) support TR-069. Check your device admin interface for TR-069 or Remote Management settings. You configure the ACS URL on the device, and it will connect to your server.

### Do I need to expose port 7547 to the internet?

For CPE behind NAT, yes — the ACS must be reachable from the CPE network. Use HTTPS with a valid TLS certificate. Many deployments place the ACS behind a reverse proxy with TLS termination and route traffic through a load balancer.

### How many devices can GenieACS manage?

GenieACS is designed for scale and has been deployed in environments managing over 100,000 CPE devices. Performance depends on MongoDB capacity and the number of concurrent CPE connections. Horizontal scaling is possible by running multiple CWMP and NBI instances.

### Is TR-069 still relevant in 2026?

Yes. TR-069 remains the dominant protocol for CPE management in ISP networks worldwide. TR-369 (USP) is gaining traction but has not replaced TR-069. Most new CPE devices support both protocols.

### Can I use these ACS platforms for IoT device management?

GenieACS and OktopUSP can manage IoT devices that implement the TR-069 data model or the USP data model. OktopUSP is particularly well-suited for IoT due to its native USP support and extended device models.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TR-069 ACS: GenieACS vs OktopUSP vs freeACS for CPE Management",
  "description": "Compare GenieACS, OktopUSP, and freeACS for self-hosted TR-069 CPE management. Includes Docker Compose configs, provisioning scripts, and deployment guides.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
