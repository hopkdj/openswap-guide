---
title: "Self-Hosted Virtual Tabletop RPG Platforms: MapTool vs FoundryVTT vs PlanarAlly"
date: "2026-06-06"
tags: ["gaming", "self-hosted", "docker", "rpg", "tabletop", "multiplayer"]
draft: false
---

## Introduction

Tabletop role-playing games have been a cornerstone of social gaming for decades. While nothing beats gathering around a physical table with friends, remote play has become increasingly common — and for good reason. Self-hosted virtual tabletop (VTT) platforms give game masters full control over their campaign worlds, character sheets, dice rolling, and tactical maps, all accessible through a web browser.

In this guide, we compare three leading self-hosted VTT platforms: **MapTool**, **FoundryVTT**, and **PlanarAlly**. Each takes a different approach to the virtual tabletop experience, and your choice will depend on your group's needs, technical comfort level, and preferred game system.

## Comparison Table

| Feature | MapTool | FoundryVTT | PlanarAlly |
|---------|---------|------------|------------|
| **License** | Open Source (Apache 2.0) | Proprietary (one-time purchase) | Open Source (MIT) |
| **GitHub Stars** | 912+ | 365+ | 522+ |
| **Web-Based** | Yes (Java client or web) | Yes (Node.js server) | Yes (Python/TypeScript) |
| **Docker Support** | Community images | Official Docker image | Community images |
| **Dynamic Lighting** | Yes (VBL system) | Yes (advanced) | Yes (basic) |
| **Character Sheets** | Community frameworks | Built-in system modules | Manual tokens |
| **Dice Rolling** | Advanced macro system | Built-in + module API | Basic rolling |
| **Multiplayer** | LAN + port forwarding | Built-in networking | WebSocket-based |
| **System Agnostic** | Fully system-agnostic | Game system modules | Fully system-agnostic |
| **Plugin Ecosystem** | Macros + frameworks | 1,000+ modules | Limited extensions |
| **Learning Curve** | Steep (macro language) | Moderate | Gentle |

## MapTool: The Open Source Veteran

MapTool has been the go-to open source VTT for nearly two decades. Built in Java, it offers a staggering level of customization through its macro scripting language — you can automate nearly anything from dice rolls to complex combat mechanics.

The program uses a Vision Blocking Layer (VBL) system for dynamic lighting and fog of war, letting you draw walls that block player vision in real time. It supports multiple map layers, token states, and a robust initiative tracker.

### Getting Started with MapTool (Docker)

```yaml
# docker-compose.yml for MapTool server
version: "3.8"
services:
  maptool:
    image: nuntius35/maptool:latest
    container_name: maptool-server
    ports:
      - "51234:51234"
    environment:
      - MT_MAX_MEMORY=2048M
      - MT_MIN_MEMORY=512M
    volumes:
      - ./campaigns:/data/campaigns
      - ./assets:/data/assets
      - ./logs:/data/logs
    restart: unless-stopped
```

While MapTool is powerful, its Java-based architecture and macro-heavy workflow mean a steeper learning curve. The community maintains extensive framework libraries for popular systems like D&D 5e, Pathfinder, and Savage Worlds, but setting them up requires patience.

## FoundryVTT: The Modern Powerhouse

FoundryVTT is the current darling of the VTT world — and for good reason. It runs as a Node.js web server, which means players connect through their browser without installing anything. Game masters purchase a one-time license and self-host the server wherever they want: a home machine, a VPS, or even a Raspberry Pi.

The platform ships with over 1,000 community modules through its built-in package manager, covering everything from animated spell effects to advanced calendar systems. Each game system (D&D 5e, Pathfinder 2e, Call of Cthulhu, etc.) has its own dedicated module with character sheets, compendium content, and automation rules.

### FoundryVTT Docker Setup

```yaml
# docker-compose.yml for FoundryVTT
version: "3.8"
services:
  foundry:
    image: felddy/foundryvtt:latest
    container_name: foundry-vtt
    ports:
      - "30000:30000"
    environment:
      - FOUNDRY_ADMIN_KEY=your-admin-password
      - FOUNDRY_LICENSE_KEY=your-license-key
      - FOUNDRY_HOSTNAME=your-domain.com
    volumes:
      - ./foundry-data:/data
      - ./foundry-modules:/data/Data/modules
    restart: unless-stopped
```

FoundryVTT's key strength is its "it just works" experience. The audiovisual features — dynamic lighting, walls, ambient sounds, and music playlists — create an immersive tabletop environment that few competitors match. However, it is not open source; the one-time $50 license fee funds ongoing development by a dedicated team.

## PlanarAlly: The Lightweight Companion

PlanarAlly takes a different approach: rather than trying to be a complete VTT with character sheets and rule automation, it focuses on being the best possible tactical map and token manager. Think of it as "the battle map that talks to your existing tools."

Built in Python with a TypeScript frontend, PlanarAlly excels at dynamic lighting, multi-floor maps, and intuitive token movement. It doesn't try to replace your character sheets or rulebooks — it provides the shared visual space and leaves the rest to your group's preferred tools.

### PlanarAlly Docker Setup

```yaml
# docker-compose.yml for PlanarAlly
version: "3.8"
services:
  planarally:
    image: ghcr.io/kruptein/planarally:latest
    container_name: planarally
    ports:
      - "8000:8000"
    volumes:
      - ./planarally-data:/data
    environment:
      - PA_SECRET_KEY=your-secret-key-here
      - PA_HOST=0.0.0.0
    restart: unless-stopped
```

PlanarAlly is ideal for groups that already use D&D Beyond, physical character sheets, or other external tools and just need a shared battle map. Its lightweight design makes it fast even on low-end hardware, and the MIT license means it's truly free.

## Why Self-Host Your Virtual Tabletop?

Running your own VTT server rather than paying a subscription to hosted services like Roll20 or D&D Beyond Maps gives you several key advantages. You own your campaign data — every map, token, character sheet, and chat log stays on your hardware, permanently accessible even if the service shuts down. No monthly fees means a one-time setup cost that pays for itself within months.

Self-hosting also means no player count limits. Hosted VTT services typically restrict free tiers to 5-6 players, which is a problem for larger gaming groups. With your own server, you control the limits. You can also customize every aspect of the experience — from custom dice mechanics to house rule automation — without being constrained by what a service provider allows.

For groups that already run game server infrastructure, adding a VTT fits naturally into your existing setup. If you're already hosting game servers for titles like Minecraft, the same knowledge applies. See our guide on [self-hosted Minecraft server platforms](../2026-05-07-self-hosted-minecraft-server-platforms-papermc-purpur-fabric-guide/) for more on hosting game infrastructure. For broader game server management, check our comparison of [game server control panels](../pterodactyl-vs-pufferpanel-vs-crafty-controller-game-server-panels-2026/).

Finally, privacy matters. Your campaign notes, homebrew rules, and world-building content stay on your server — not on a third-party platform's cloud. For groups that value creative ownership and data sovereignty, self-hosting is the clear choice. If you're interested in other self-hosted multiplayer platforms, see our guide on [open-source game server platforms](../2026-05-07-self-hosted-game-server-platforms-minetest-openttd-openra-guide/).

## Which VTT Should You Choose?

**Choose MapTool if** you want maximum customization, don't mind a learning curve, and value a fully open source stack. It's the choice for technically-minded GMs who want complete control over every dice roll and combat mechanic.

**Choose FoundryVTT if** you want the best out-of-box experience, value audiovisual polish, and are willing to pay a one-time license fee. It's the choice for GMs who want to spend time prepping adventures, not configuring software.

**Choose PlanarAlly if** you already use external character management tools and just need a fast, reliable battle map with excellent dynamic lighting. It's the choice for groups that want a lightweight, focused tool rather than an all-in-one platform.

## FAQ

### Do I need a powerful server to run a VTT?

Not necessarily. MapTool can run on modest hardware with 2GB of RAM. FoundryVTT recommends 2GB+ RAM for the server, with more needed for complex scenes. PlanarAlly is the lightest of the three, running comfortably on a Raspberry Pi 4. The main bottleneck is usually network upload speed if players are connecting remotely.

### Can players connect without installing anything?

Yes, if you use the web-based options. FoundryVTT and PlanarAlly are fully browser-based — players only need a modern web browser. MapTool requires a Java client for the full experience, though community projects are working on browser-based alternatives using WebRTC.

### Do these VTTs support D&D 5e?

All three support D&D 5e to varying degrees. FoundryVTT has the most complete 5e integration through its official D&D 5e game system module, including the SRD compendium. MapTool has community-maintained 5e frameworks with automated character sheets and combat tracking. PlanarAlly is system-agnostic and works alongside any external character manager.

### What about dynamic lighting and line of sight?

FoundryVTT has the most advanced dynamic lighting system, with support for walls, doors, terrain, one-way visibility, and animated light sources. MapTool's Vision Blocking Layer (VBL) is powerful but less intuitive to set up. PlanarAlly has solid basic dynamic lighting with multi-floor support and clean wall-drawing tools.

### Can I migrate my campaign from Roll20 to a self-hosted VTT?

Yes, several tools exist for this purpose. The R20Converter and Roll20 Exporter browser extensions can export Roll20 campaigns into formats compatible with FoundryVTT and MapTool. The conversion process typically handles maps, tokens, and journal entries, though some manual cleanup is usually needed for macros and dynamic lighting.

### Is there mobile/tablet support?

FoundryVTT has a touch-friendly module called TouchVTT that improves mobile compatibility, though the experience is still optimized for desktop. MapTool and PlanarAlly are primarily designed for desktop use. For tablet play, FoundryVTT offers the best experience of the three.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Virtual Tabletop RPG Platforms: MapTool vs FoundryVTT vs PlanarAlly",
  "description": "Compare MapTool, FoundryVTT, and PlanarAlly for self-hosted virtual tabletop gaming. Includes Docker Compose setups, feature comparison, and deployment guide.",
  "datePublished": "2026-06-06",
  "dateModified": "2026-06-06",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
