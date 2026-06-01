---
title: "Self-Hosted Wake-on-LAN Web Dashboards: UpSnap vs wolweb vs LANtern Compared (2026)"
date: "2026-06-01"
tags: ["wake-on-lan", "network-management", "self-hosted", "remote-access", "home-lab", "infrastructure", "wol", "dashboard"]
draft: false
---

## Introduction

Remote power management is a critical capability for any self-hosted infrastructure. Whether you manage a home lab, a remote office, or a colocated server, the ability to wake machines from across the network saves electricity while keeping services accessible when needed. **Wake-on-LAN (WoL)** has been the industry standard for out-of-band power-on since the 1990s, but the core mechanism — sending a "magic packet" to a target MAC address — hasn't changed. What *has* evolved is how we interact with it. Modern self-hosted WoL web dashboards replace cryptic CLI commands and SSH sessions with polished web interfaces, device grouping, scheduling, and integration with tools like Home Assistant.

This article compares three self-hosted Wake-on-LAN web dashboards — **UpSnap**, **wolweb**, and **LANtern** — to help you choose the right tool for remotely powering on your machines.

## Why Self-Host a Wake-on-LAN Dashboard?

Running your own WoL dashboard offers several advantages over vendor-specific remote management tools or cloud-dependent services. First, **data privacy**: your device inventory, MAC addresses, and network topology never leave your local network. Unlike cloud-based remote management platforms that require agent software and outbound connections, a self-hosted WoL dashboard operates entirely within your trusted LAN. Second, **integration flexibility**: a self-hosted solution can be paired with reverse proxies, VPN gateways, and home automation platforms. You can trigger a wake event from a Home Assistant automation, a cron job, or a custom script. Third, **cost**: commercial out-of-band management solutions like Intel vPro or server-grade IPMI require licensed hardware or additional subscription fees. A WoL web dashboard running on a Raspberry Pi or a small Docker host costs nothing beyond the compute resources you already have.

For broader remote access infrastructure, see our [self-hosted remote desktop guide](../self-hosted-remote-desktop-guacamole-rustdesk-meshcentral-guide/). If you need full remote monitoring and management capabilities beyond just waking machines, check out our [comparison of Tactical RMM, MeshCentral, and OpenRMM](../2026-05-02-tactical-rmm-vs-meshcentral-vs-openrmm-self-hosted-remote-monitoring-management-guide/). For secure remote access via SSH jump hosts, our [bastion server guide](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/) covers the topic in depth.

## Tool Comparison

| Feature | UpSnap | wolweb | LANtern |
|---------|--------|--------|---------|
| **GitHub Stars** | 5,744 | 426 | 41 |
| **Language** | Go + SvelteKit | Go + Bootstrap | JavaScript |
| **Database** | PocketBase (SQLite) | None (stateless) | SQLite |
| **Device Grouping** | Yes (tags/favorites) | No | No |
| **Scheduling** | Yes (cron-based) | No | No |
| **Authentication** | Built-in (OIDC, Basic) | None | PIN lock |
| **PWA Support** | Yes | No | Yes |
| **Docker Image** | Yes (multi-arch) | Yes | Yes |
| **Active Development** | Very active (2026) | Moderate (2025) | Active (2026) |
| **Resource Usage** | ~30MB RAM | ~5MB RAM | ~25MB RAM |
| **REST API** | Yes (PocketBase) | Minimal (WoL only) | Yes |

## UpSnap

[UpSnap](https://github.com/seriousm4x/UpSnap) is the clear leader in the self-hosted WoL space with **5,744 GitHub stars** and an active development pace. Built with Go and SvelteKit, it uses PocketBase as its embedded database, providing a full REST API, authentication, and real-time capabilities out of the box. UpSnap supports device grouping via tags, favorites for quick access, cron-based scheduling for automated wake times, and integration with Home Assistant. Its Docker image is multi-architecture (amd64, arm64, armv7), making it ideal for Raspberry Pi deployments.

```yaml
# docker-compose.yml for UpSnap
version: "3.8"
services:
  upsnap:
    image: ghcr.io/seriousm4x/upsnap:latest
    container_name: upsnap
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./upsnap/data:/app/pb_data
    environment:
      - TZ=UTC
      - UPSNAP_INTERVAL=@every 60s
      - UPSNAP_SCAN_RANGE=192.168.1.0/24
```

Key features: UpSnap automatically scans your network for devices, lets you assign friendly names and tags, and can wake devices on a schedule. The scanning interval and subnet are configurable via environment variables. Network host mode is required for sending magic packets — WoL packets must originate from the same broadcast domain as the target devices.

## wolweb

[wolweb](https://github.com/sameerdhoot/wolweb) takes a minimalist approach. Written in Go with Bootstrap for the UI, it's entirely stateless — no database, no authentication, no complexity. You configure devices with MAC addresses, names, and optional IP addresses in a simple configuration file or through the web interface. It stores configuration as JSON on disk. This simplicity makes wolweb ideal for small networks where you just need a clean web UI to wake a handful of machines.

```yaml
# docker-compose.yml for wolweb
version: "3.8"
services:
  wolweb:
    image: sameerdhoot/wolweb:latest
    container_name: wolweb
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./wolweb/config:/app/config
    environment:
      - WOLWEB_PORT=8089
      - WOLWEB_TITLE=My WoL Dashboard
    ports:
      - "8089:8089"
```

wolweb's simplicity is both its strength and its limitation. There is no device discovery or network scanning — you must know your MAC addresses beforehand. The UI is clean and functional, but there is no scheduling, no API for automation, and no authentication layer. If you need a quick, reliable WoL trigger with minimal overhead, wolweb delivers exactly that.

## LANtern

[LANtern](https://github.com/allxm4/LANtern) is the newest entrant, offering a PWA-first experience with PIN lock authentication and a modern responsive UI. Built with JavaScript, it uses SQLite for persistent device storage and supports both manual device entry and basic network scanning. Its PWA support means you can install it on your phone's home screen for one-tap wake access — a convenient feature for when you're away from your desk.

```yaml
# docker-compose.yml for LANtern
version: "3.8"
services:
  lantern:
    image: ghcr.io/allxm4/lantern:latest
    container_name: lantern
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./lantern/data:/app/data
    environment:
      - TZ=UTC
      - PIN=1234
    ports:
      - "3000:3000"
```

LANtern's PIN lock provides basic access control without the overhead of full OIDC integration. For home lab use cases where you want family members to be able to wake devices without exposing admin credentials, this is a practical middle ground. The PWA install experience is particularly well-executed, making it feel like a native mobile app.

## Deployment Architecture

All three tools require **network host mode** (or macvlan) in Docker because WoL magic packets are sent as broadcast frames to the local subnet. A magic packet consists of six bytes of `0xFF` followed by the target device's MAC address repeated 16 times — this must be broadcast on the local network segment where the target device resides. If your Docker host is on a different VLAN or subnet than the target devices, you will need to configure a WoL relay or use directed subnet broadcasts.

For external access, deploy any of these behind a reverse proxy like Nginx or Caddy with TLS. Since WoL dashboards don't handle sensitive data beyond device MAC addresses and names, a basic TLS reverse proxy with optional HTTP authentication is sufficient. For home lab scenarios, consider combining a WoL dashboard with a WireGuard VPN tunnel so you can wake machines from outside your network without exposing the dashboard to the public internet.

## Security Considerations

While WoL dashboards are lower-risk than general-purpose remote management tools, consider these security practices: (1) always use a reverse proxy with TLS for external access, (2) enable authentication (UpSnap's OIDC or LANtern's PIN) rather than exposing an unprotected dashboard, (3) restrict access by IP if behind a VPN, (4) network host mode in Docker exposes the container to all host interfaces — use this only when necessary and consider macvlan as an alternative, (5) log wake events and review them periodically to detect unauthorized use.

## FAQ

### How does Wake-on-LAN actually work?

WoL works by sending a specially crafted broadcast frame called a "magic packet" to the target device's MAC address. The packet contains the synchronization stream `FF FF FF FF FF FF` followed by the target MAC address repeated 16 times. The target device's network interface card (NIC) listens for this pattern even when the system is powered off (as long as the NIC has standby power). Upon detecting the magic packet addressed to its MAC, the NIC signals the motherboard to initiate a full boot sequence. The target must have WoL enabled in BIOS/UEFI and the NIC must support it.

### Do I need network host mode in Docker?

Yes, typically. Magic packets are sent as Ethernet broadcast frames (destination `FF:FF:FF:FF:FF:FF`), which must originate from the same broadcast domain as the target. Docker's default bridge network creates an isolated subnet with NAT, so packets sent from a bridged container will not reach physical devices on the host's network. Using `network_mode: host` gives the container direct access to the host's network interfaces. An alternative is macvlan networking, which assigns the container its own MAC address on the physical network.

### Can I wake devices across VLANs or subnets?

By default, no — magic packets are link-local broadcasts and do not cross subnet boundaries. To wake devices on different subnets, you can use directed subnet broadcasts (sending the magic packet to the broadcast address of the remote subnet, e.g., `192.168.2.255`), but this requires your router to forward directed broadcasts (usually disabled for security reasons). The more practical approach is to run a WoL relay or agent on each subnet.

### What about shutting down devices remotely?

WoL only handles power-on — it cannot shut down or reboot devices. For graceful shutdown, you need an agent running on the target system (SSH, RPC, or a management agent). UpSnap includes basic ping-based status checking but does not handle shutdown. For full remote power management including shutdown, reboot, and monitoring, consider tools like MeshCentral or Tactical RMM, which we cover in our [RMM comparison guide](../2026-05-02-tactical-rmm-vs-meshcentral-vs-openrmm-self-hosted-remote-monitoring-management-guide/).

### Which dashboard should I choose?

Choose **UpSnap** if you want the most feature-rich experience with scheduling, device groups, network scanning, and Home Assistant integration. It's the clear winner for serious home lab setups. Choose **wolweb** if you value minimalism and don't need bells and whistles — it's perfect for managing 3-5 devices on a small network. Choose **LANtern** if you prioritize mobile access and PWA support. Its PIN lock is a nice touch for shared household use. All three are free, open-source, and Docker-deployable with minimal resource requirements.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform, where you can bet on everything from election outcomes to regulatory timelines. Unlike gambling, this is a genuine information market: the more you know, the better your odds. I've made solid returns predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Wake-on-LAN Web Dashboards: UpSnap vs wolweb vs LANtern Compared (2026)",
  "description": "Compare three self-hosted Wake-on-LAN web dashboards — UpSnap, wolweb, and LANtern — for remotely powering on machines in your home lab or infrastructure. Includes Docker Compose configs, feature comparison table, and deployment best practices.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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
