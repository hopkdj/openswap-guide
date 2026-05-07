---
title: "Self-Hosted Minecraft Server Platforms: PaperMC vs Purpur vs Fabric"
date: "2026-05-07"
draft: false
tags: ["gaming", "minecraft", "self-hosted", "server", "docker", "papermc"]
description: "Compare self-hosted Minecraft server platforms — PaperMC, Purpur, and Fabric — for running optimized, modded, or vanilla-compatible Minecraft servers with Docker."
---

Running a self-hosted Minecraft server gives you complete control over gameplay rules, performance tuning, mod selection, and player access. While Mojang provides an official vanilla server, the community has developed several high-performance server platforms that dramatically improve gameplay, add configurability, and enable mod support. This guide compares three leading open-source Minecraft server platforms: **PaperMC**, **Purpur**, and **Fabric**.

## Why Run a Self-Hosted Minecraft Server?

Self-hosting a Minecraft server offers advantages over Minecraft Realms and third-party hosting providers:

**Full control over server configuration:** Adjust view distance, tick rate, entity spawn limits, and performance settings to match your hardware. Realms and managed hosts impose fixed configurations that may not suit your player count or world size.

**No recurring subscription costs:** Minecraft Realms costs $7.99-$14.99/month for up to 10 players. A self-hosted server on your own hardware or VPS costs only the infrastructure expense — many players run servers on existing home servers or low-cost $5-10/month VPS instances.

**Unlimited mod and plugin support:** Realms does not support server-side modifications. Self-hosted servers allow unlimited plugins (PaperMC/Purpur) or mods (Fabric), from performance optimizations to entirely new gameplay mechanics.

**Complete data ownership:** Your world saves, player data, and server logs stay on your infrastructure. No dependency on third-party backup schedules or data retention policies.

## PaperMC

[PaperMC](https://github.com/PaperMC/Paper) is the most widely used Minecraft server platform, with over 12,000 GitHub stars. It is a high-performance fork of Spigot that fixes gameplay and mechanics inconsistencies, optimizes the server engine, and adds extensive configuration options — all while maintaining full compatibility with vanilla Minecraft clients and Spigot/Bukkit plugins.

**Key features:**

- Up to 3x performance improvement over vanilla server
- Full Spigot/Bukkit plugin compatibility
- Extensive configuration via `paper-global.yml`
- Async chunk loading and entity tracking
- Anti-xray and anti-cheat protections
- Configurable redstone behavior and tick timing
- Active development with weekly builds

**Performance improvements:** PaperMC optimizes critical server paths including chunk loading, entity behavior logic, block physics, and network I/O. Key optimizations include asynchronous chunk generation, reduced entity tick overhead, and configurable view distance per-player. For a server with 20+ players, PaperMC typically reduces CPU usage by 30-50% compared to the vanilla server.

```yaml
# Docker Compose for PaperMC
services:
  minecraft:
    image: itzg/minecraft-server:latest
    ports:
      - "25565:25565"
    environment:
      - EULA=TRUE
      - TYPE=PAPER
      - VERSION=1.21.4
      - MEMORY=4G
      - MAX_PLAYERS=50
      - DIFFICULTY=hard
      - ONLINE_MODE=TRUE
      - VIEW_DISTANCE=10
      - SIMULATION_DISTANCE=6
      - ALLOW_NETHER=TRUE
      - SPAWN_ANIMALS=TRUE
      - SPAWN_MONSTERS=TRUE
      - SPAWN_NPCS=TRUE
    volumes:
      - ./data:/data
      - ./plugins:/data/plugins
      - ./world:/data/world
      - ./config:/data/config
    restart: unless-stopped
```

```yaml
# paper-global.yml - key performance settings
settings:
  velocity-support:
    enabled: false
  unsupported-settings:
    allow-headless-pistons: false

chunk-system:
  gen-parallelism: default
  max-concurrent-chunk-loads: 500

fixes:
  disable-unloaded-chunk-entity-removal: true
  fix-entity-tracker-desync: true
  fix-items-merging-through-walls: true

anti-xray:
  enabled: true
  engine-mode: 1
  max-block-height: 64
```

## Purpur

[Purpur](https://github.com/PurpurMC/Purpur) is a fork of PaperMC that adds even more configuration options and gameplay features. With 2,300+ GitHub stars, it targets server administrators who want granular control over every aspect of Minecraft gameplay — from mob behavior to item mechanics to player experience settings.

**Key features:**

- Everything in PaperMC (100% Paper plugin compatibility)
- 500+ additional configuration options
- Customizable mob behavior (spawning, behavior patterns, drops)
- Player experience settings (sleep voting, AFK handling, inventory settings)
- Gameplay tweaks (dolphin speed, turtle breeding, ender pearl cooldowns)
- Built-in quality-of-life features (armor stand rotation, anvil mechanics)
- Weekly builds tracking Paper upstream

**Purpur's philosophy** is "everything should be configurable." Where PaperMC makes opinionated choices about gameplay behavior, Purpur exposes nearly every server-side mechanic as a configuration toggle. This makes Purpur the most customizable Minecraft server platform available.

```yaml
# Docker Compose for Purpur
services:
  minecraft:
    image: itzg/minecraft-server:latest
    ports:
      - "25565:25565"
    environment:
      - EULA=TRUE
      - TYPE=PURPUR
      - VERSION=1.21.4
      - MEMORY=6G
      - MAX_PLAYERS=100
      - DIFFICULTY=normal
      - ONLINE_MODE=TRUE
      - VIEW_DISTANCE=12
      - PURPUR_CONFIG_YAML=/data/config/purpur.yml
    volumes:
      - ./data:/data
      - ./plugins:/data/plugins
      - ./world:/data/world
      - ./config:/data/config
    restart: unless-stopped
```

```yaml
# purpur.yml - sample gameplay customizations
world-settings:
  default:
    mob-spawning:
      wandering-trader:
        spawn-minutes:
          enabled: false
      pillager-patrols:
        spawn-chance: 0.2
        spawn-delay:
          per-player: false
    gameplay-mechanics:
      entity-lifespan: 0
      remove-arrows-in-player: 60
      use-vanilla-damage-ticks-for-freezing: false
    misc:
      disable-credits-screen: true
      allow-water-placement-in-the-end: true
      fix-projectile-looting-transfer: true

settings:
  command:
    spy-from-console: true
  entity:
    enderman:
      ignore-players-wearing-pumpkin: false
    zombie:
      take-flame-damage: true
```

## Fabric

[Fabric](https://github.com/FabricMC/fabric) is a lightweight, experimental modding toolchain for Minecraft. Unlike PaperMC and Purpur (which focus on server-side plugins and performance), Fabric provides a modding API that enables deep gameplay modifications — new blocks, items, dimensions, entities, and mechanics. The Fabric ecosystem includes the Fabric Loader (mod loader), Fabric API (core API for mod developers), and Yarn (Minecraft mapping project).

**Key features:**

- Lightweight modding framework (minimal performance overhead)
- 3,000+ community mods available
- Server-side and client-side mod support
- Active modding community with weekly updates
- Compatible with OptiFine alternatives (Sodium, Iris)
- Yarn mappings for mod development
- Minimal changes to vanilla behavior (unlike Paper's optimizations)

**Fabric vs PaperMC:** Fabric and PaperMC serve different purposes. Fabric enables deep gameplay modifications (new dimensions, custom biomes, tech mods) at the cost of vanilla performance. PaperMC optimizes the vanilla server experience with plugins that add features without changing core mechanics. Some servers run both using compatibility layers like Cardboard or Arclight, but this setup is not officially supported and can cause plugin/mod conflicts.

```yaml
# Docker Compose for Fabric Server
services:
  minecraft:
    image: itzg/minecraft-server:latest
    ports:
      - "25565:25565"
    environment:
      - EULA=TRUE
      - TYPE=FABRIC
      - VERSION=1.21.4
      - MEMORY=4G
      - MAX_PLAYERS=30
      - ONLINE_MODE=TRUE
      - VIEW_DISTANCE=8
      - INIT_MEMORY=2G
      - MAX_MEMORY=6G
      - FABRIC_API=TRUE
    volumes:
      - ./data:/data
      - ./mods:/data/mods
      - ./world:/data/world
      - ./config:/data/config
    restart: unless-stopped
```

```yaml
# Server properties for Fabric
server.properties:
  # Core settings
  server-port=25565
  max-players=30
  view-distance=8
  simulation-distance=6
  difficulty=normal
  gamemode=survival
  hardcore=false
  
  # Performance
  max-tick-time=60000
  enable-command-block=false
  spawn-npcs=true
  spawn-animals=true
  spawn-monsters=true
  
  # Network
  online-mode=true
  enforce-secure-profile=true
  prevent-proxy-connections=false
  network-compression-threshold=256
```

```bash
# Install Fabric mods (download to ./mods directory)
# Example: Essential mods for a Fabric server
curl -L -o mods/fabric-api-*.jar \
  "https://cdn.modrinth.com/data/P7dR8mSH/versions/latest/fabric-api.jar"

curl -L -o mods/lithium-*.jar \
  "https://cdn.modrinth.com/data/gvQqBUqZ/versions/latest/lithium.jar"

curl -L -o mods/phosphor-*.jar \
  "https://cdn.modrinth.com/data/hEOCdOgZ/versions/latest/phosphor.jar"
```

## Comparison Table

| Feature | PaperMC | Purpur | Fabric |
|---------|---------|--------|--------|
| **License** | GPL-3.0 | GPL-3.0 | Apache 2.0 / MIT |
| **GitHub Stars** | 12,237+ | 2,355+ | 3,054+ |
| **Based On** | Spigot | PaperMC | Vanilla |
| **Plugin System** | Bukkit/Spigot plugins | Bukkit/Spigot plugins | Fabric mods |
| **Performance** | Excellent (3x vanilla) | Excellent (Paper base) | Good (with Lithium) |
| **Vanilla Compat** | Full (100%) | Full (100%) | Full (requires client mods) |
| **Config Options** | ~200 settings | ~500+ settings | Mod-dependent |
| **Mod Support** | No (plugins only) | No (plugins only) | Full mod support |
| **Client Mods Required** | No | No | Yes (for mod features) |
| **Best For** | Plugin servers, survival | Highly customized servers | Modded gameplay |
| **Update Frequency** | Weekly | Weekly | Weekly |
| **Memory Usage** | 2-4 GB | 2-4 GB | 2-6 GB (mod-dependent) |

## Choosing the Right Minecraft Server Platform

**Choose PaperMC if** you want the best balance of performance and plugin compatibility. PaperMC is the industry standard for self-hosted Minecraft servers — it runs 99% of public survival servers, minigame networks, and community servers. The massive plugin ecosystem (10,000+ plugins) means you can add virtually any feature without writing code.

**Choose Purpur if** you want maximum configurability and don't want to install plugins for minor gameplay tweaks. Purpur exposes 500+ configuration options that would otherwise require plugins. It is ideal for small-to-medium servers where the administrator wants fine-grained control over every gameplay mechanic without managing dozens of plugins.

**Choose Fabric if** you want deep gameplay modifications — new dimensions, custom biomes, technology mods, magic systems, or entirely new game modes. Fabric is the choice for modded servers where players install matching client-side mods. It is less suitable for public vanilla-style servers because players must install the same mods on their clients.

## Why Self-Host Minecraft?

Beyond cost savings, self-hosting Minecraft servers offers unique benefits:

**Custom world generation:** Configure custom world seeds, terrain generation settings, and biome distributions. Create entirely unique worlds with flat terrain, amplified hills, or custom dimensions (with Fabric mods).

**Whitelist and access control:** Maintain a player whitelist, enforce IP bans, and configure permission groups using plugins like LuckPerms. You control who joins your server and what they can do.

**Automated backups:** Schedule automated world backups using cron jobs or Docker volume snapshots. Protect against griefing, corruption, or accidental world deletion. Many server operators maintain hourly incremental backups and daily full backups.

**Cross-play support:** With plugins like GeyserMC, you can enable Bedrock Edition (mobile, console, Windows 10) players to join your Java Edition server. This is impossible on Minecraft Realms without third-party proxies.

For teams managing game server infrastructure at scale, our [game server platforms comparison](../2026-05-07-self-hosted-game-server-platforms-minetest-openttd-openra-guide/) covers self-hosted alternatives for other classic games, and our [game server management panels guide](../pterodactyl-vs-pufferpanel-vs-crafty-controller-game-server-panels-2026/) covers web-based management for multiple game servers.

## FAQ

### Can I switch from vanilla Minecraft server to PaperMC or Purpur without losing my world?

Yes. PaperMC and Purpur are drop-in replacements for the vanilla server. Simply stop your vanilla server, replace the server JAR with the PaperMC or Purpur JAR, and restart. Your world data, player inventories, and building progress are fully preserved. PaperMC reads the same world format as vanilla Minecraft.

### Do Fabric mods require players to install mods on their clients?

For most gameplay modifications, yes — Fabric mods that add new blocks, items, or mechanics require matching client-side mods. However, server-only Fabric mods (like Lithium for performance optimization, or anti-cheat mods) work without any client changes. Always check each mod's documentation to confirm whether client-side installation is required.

### How much RAM does a self-hosted Minecraft server need?

For a PaperMC server with 10-20 players: 4 GB is recommended minimum. For Purpur with 30+ players: 6-8 GB. For Fabric with heavy mods: 6-10 GB depending on mod count. Allocate at least 2 GB for the JVM heap and additional memory for chunk caching. Use the `-Xms` and `-Xmx` flags to set initial and maximum heap size.

### Can I run PaperMC plugins on Fabric, or Fabric mods on PaperMC?

No. PaperMC uses the Bukkit/Spigot plugin API, while Fabric uses its own modding API. These are fundamentally incompatible systems. However, compatibility layers like Cardboard (Fabric mod that runs Bukkit plugins) and Arclight (hybrid server) exist, but they are unofficial, may cause crashes, and are not recommended for production servers.

### How do I update a self-hosted Minecraft server?

For PaperMC and Purpur: download the latest JAR from the official website or API, stop the server, replace the JAR file, and restart. Most Docker images (like `itzg/minecraft-server`) automatically download the latest version on container restart when `TYPE=PAPER` or `TYPE=PURPUR` is set. For Fabric: update the Fabric Loader JAR and individual mods in the `mods` directory. Always back up your world before updating.

### Is self-hosting a Minecraft server legal?

Yes. Mojang's EULA explicitly allows players to run their own Minecraft servers. The only restriction is that you cannot charge players for access to the server (except through approved donation mechanisms that don't provide gameplay advantages). Running a self-hosted server for personal or community use is fully compliant with Mojang's terms.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Minecraft Server Platforms: PaperMC vs Purpur vs Fabric",
  "description": "Compare self-hosted Minecraft server platforms for running optimized, modded, or vanilla-compatible servers with Docker.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
