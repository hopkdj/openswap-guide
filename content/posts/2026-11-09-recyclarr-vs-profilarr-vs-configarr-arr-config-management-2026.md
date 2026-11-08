---
title: "Recyclarr vs Profilarr vs Configarr in 2026: Which Arr Config Tool Should You Actually Use?"
date: "2026-11-09"
draft: false
tags: ["self-hosted", "media-automation", "arr-stack", "configuration-management", "docker"]
cover: "/img/screenshots/profilarr-dashboard.jpg"
description: "A hands-on comparison of Recyclarr, Profilarr and Configarr for syncing TRaSH Guides quality profiles and custom formats into Sonarr and Radarr in 2026."
---

Your Sonarr instance has 41 custom formats. Radarr has 38. You run a 4K instance too, so that is 117 objects that drift every time the TRaSH Guides team revises a release group score. Clicking through that by hand is not configuration management — it is data entry with extra steps, and one forgotten `CF` score is the difference between grabbing a clean WEB-DL and a 30 GB remux with three audio tracks.

That is the problem three open-source tools solve: **Recyclarr**, **Profilarr**, and **Configarr**. All three read TRaSH Guides definitions and push them into your *arr instances through the API. They differ violently in how much control you get and how much of your sanity you trade for it.

## TL;DR / Quick Verdict

**If you already run the standard TRaSH setup and want it to keep working — install Recyclarr, schedule it hourly, forget it exists.** It is the most battle-tested option by a wide margin and the only one whose YAML format the TRaSH Guides documentation itself assumes.

**If you manage multiple instances and want to see what changed before it lands — pick Profilarr.** It ships a real web UI, a central library of quality profiles, and diff views instead of blind cron jobs.

**If TRaSH Guides is only the starting point and you maintain your own custom formats — pick Configarr.** It merges TRaSH definitions with local YAML and inline definitions in a deterministic order, which neither of the other two does cleanly.

Running two of them at once is the one thing you must not do. They will overwrite each other's quality profile scores on every sync, and you will spend a weekend wondering why your Radarr keeps flip-flopping.

## Side-by-Side Comparison

All figures pulled from the projects' GitHub repositories on 2026-11-09.

| Dimension | Recyclarr | Profilarr | Configarr |
|---|---|---|---|
| Stars | 2,151 | 2,770 | 673 |
| Language | C# (.NET) | TypeScript | TypeScript |
| License | MIT | AGPL-3.0 | AGPL-3.0 |
| Last commit | 2026-11-08 | 2026-11-07 | 2026-11-06 |
| Interface | CLI + cron daemon | Web UI + API | CLI + cron |
| Config format | `recyclarr.yml` | UI-managed + export | `config.yml` |
| TRaSH Guide sync | Native, first-class | Native | Native |
| Custom formats of your own | Limited | Yes, via library | Yes, three merge layers |
| Multi-instance | Yes, per-instance blocks | Yes, central server registry | Yes, arrays |
| Docker image | `ghcr.io/recyclarr/recyclarr:8` | `ghcr.io/dictionarry-hub/profilarr:develop` | `ghcr.io/raydak-labs/configarr:latest` |
| Learning curve | Low if you like YAML | Low if you like clicking | Medium |
| Best fit | Single-admin homelab | Multi-instance households | Config-as-code purists |

## Use Case Decision Matrix

| Your situation | Use this | Why |
|---|---|---|
| One Radarr, one Sonarr, stock TRaSH profiles | Recyclarr | Five-line YAML, cron schedule, zero UI maintenance |
| Three instances, two users, different profile sets | Profilarr | Central library with per-instance assignment and visual diffs |
| You maintain 20 custom formats of your own | Configarr | Merge order TRaSH → local files → inline config is explicit |
| You want to review changes before they hit production | Profilarr | Sync preview and drift detection in the browser |
| You run everything in GitOps and never open a browser | Configarr | Config file is the source of truth, diffable in Git |
| You are on ARM64 (Raspberry Pi, Oracle A1) | Any of the three | All publish multi-arch images |
| You want the smallest possible footprint | Recyclarr | Single static binary, ~50 MB RAM, `read_only` container |

## Recyclarr — The Reference Implementation

Recyclarr has been the default answer since 2022, and the ecosystem treats its configuration format as the lingua franca. The tool syncs custom formats, quality definitions, media naming, and media management settings from TRaSH Guides, and it does so idempotently: if the remote state already matches, nothing is written.

The deployment is deliberately boring. Create `config/recyclarr.yml`:

```yaml
radarr:
  movies:
    base_url: http://radarr:7878
    api_key: !env_var RADARR_API_KEY
    replace_existing_custom_formats: true
    quality_definition:
      type: movie
    quality_profiles:
      - name: HD Bluray + WEB
        reset_unmatched_scores:
          enabled: true
        upgrade:
          allowed: true
          until_quality: Bluray-1080p
          until_score: 10000
        min_format_score: 0

sonarr:
  series:
    base_url: http://sonarr:8989
    api_key: !env_var SONARR_API_KEY
    replace_existing_custom_formats: false
    quality_definition:
      type: series
    quality_profiles:
      - name: WEB-1080p
        reset_unmatched_scores:
          enabled: true
```

Note what the API key does *not* do: it does not get written into Git. The `!env_var` tag is Recyclarr's mechanism for pulling secrets from the environment at runtime, which is the only reason this file is safe to version-control.

The official container is intentionally minimal:

```yaml
services:
  recyclarr:
    image: ghcr.io/recyclarr/recyclarr:8
    container_name: recyclarr
    user: 1000:1000
    volumes:
      - ./config:/config
    environment:
      TZ: Europe/Berlin
      CRON_SCHEDULE: "0 3 * * *"
    restart: unless-stopped
```

Two details bite people here. First, **the `latest` tag does not exist** — Recyclarr publishes major-version tags only, so `:8` is correct and `:latest` will fail to pull. Second, the container runs as the UID you pass in `user:`; if `/config` is owned by root, the container starts and then silently fails to write its cache.

A manual sync is a single command, which makes it easy to wire into a systemd timer or a CI job instead of the built-in scheduler:

```bash
docker exec recyclarr recyclarr sync
docker exec recyclarr recyclarr list custom-formats radarr
```

The last command is the underrated feature: it prints every custom format Recyclarr knows about with its score, so you can audit drift without opening Radarr at all.

Where Recyclarr falls short is anything TRaSH Guides does not model. You can define your own custom formats, but you cannot express multi-step merge logic, and the config file grows into a small program once you maintain more than two profiles.

## Profilarr — Configuration Management With a Face

Profilarr reframes the problem as a *management* problem rather than a *sync* problem. It runs a server that holds a library of quality profiles, custom formats, and regular expressions, then lets you assign that library to registered *arr instances. The UI shows you what will change before you commit it.

![Profilarr quality profile library and instance overview](/img/screenshots/profilarr-dashboard.jpg "Profilarr dashboard showing the quality profile library and connected Radarr and Sonarr instances")

The Compose file from the project repository is short. The optional `parser` service powers regular expression testing against real release names, which is worth running if you write your own formats:

```yaml
services:
  profilarr:
    image: ghcr.io/dictionarry-hub/profilarr:develop
    container_name: profilarr
    restart: unless-stopped
    ports:
      - "6869:6868"
    volumes:
      - ./config:/config
    environment:
      - PUID=1000
      - PGID=1000
      - UMASK=022
      - TZ=Etc/UTC
      - PARSER_HOST=parser
      - PARSER_PORT=5000
    depends_on:
      parser:
        condition: service_healthy

  parser:
    image: ghcr.io/dictionarry-hub/profilarr-parser:develop
    container_name: profilarr-parser
    restart: unless-stopped
    expose:
      - "5000"
```

The `develop` tag is not a typo — the project publishes its actively maintained build there, and pinning to `latest` may leave you on a stale snapshot. Check the repository's tags before you freeze a version in production.

The practical advantage shows up the moment you have more than one instance. With Recyclarr, a 1080p profile and a 4K profile live in the same YAML file and you copy-paste blocks to add a second instance. With Profilarr you define `HD Bluray + WEB` once, assign it to `radarr-main` and `radarr-4k`, and change the score in one place. When the TRaSH Guides team bumps a release group, the diff view tells you exactly which instances are affected before anything is written.

The trade-off is state. Profilarr keeps its own database of what it believes your instances contain, so a manual change inside Radarr's interface gets flagged as drift rather than silently accepted. That is the correct behaviour for configuration management and it is also the reason some homelab users bounce off it — the tool will keep telling you that you have unmanaged changes.

## Configarr — Config-as-Code Without Compromise

Configarr is the newest of the three and the most explicit about merging. Its selling point is a documented precedence order: **TRaSH Guides first, then local custom format files, then formats defined inline in the config**. Last writer wins, deterministically, and you can see the whole stack in one file.

```yaml
sonarr:
  - name: main
    base_url: http://sonarr:8989
    api_key: !env SONARR_API_KEY
    quality_definition:
      type: series
    include:
      - template: sonarr-quality-definition-series
      - template: sonarr-v4-quality-profile-web-1080p
      - template: sonarr-v4-custom-formats-web-1080p
    custom_formats:
      - trash_ids:
          - 496f355514737f7d83bf7aa4d24f8169
        assign_scores_to:
          - name: WEB-1080p
            score: 101
    replace_existing_custom_formats: true

radarr:
  - name: movies
    base_url: http://radarr:7878
    api_key: !env RADARR_API_KEY
    quality_definition:
      type: movie
    include:
      - template: radarr-quality-definition-movie
    custom_formats:
      - trash_regex: German
        assign_scores_to:
          - name: HD Bluray + WEB
```

The `!env`, `!secret`, and `!file` tags are the reason this tool exists: every value can come from the environment, a secrets file, or a mounted file, which means the config itself contains no credentials and no environment-specific drift.

Deployment is a single container with a mounted config directory:

```yaml
services:
  configarr:
    image: ghcr.io/raydak-labs/configarr:latest
    container_name: configarr
    restart: unless-stopped
    volumes:
      - ./config:/app/config
    environment:
      TZ: Europe/Berlin
      LOG_LEVEL: info
```

Run it on demand rather than on a schedule if you prefer explicit control:

```bash
docker run --rm -v ./config:/app/config \
  -e SONARR_API_KEY="$SONARR_API_KEY" \
  ghcr.io/raydak-labs/configarr:latest
```

Configarr explicitly supports Sonarr v4 and the v5 beta plus Radarr v5, v6, and v7 through the same API v3 surface, and it detects the Sonarr API version at runtime. That matters in 2026 because Radarr v7 and Sonarr v5 changed authentication defaults, and older sync tools that hard-coded API v3 paths without version detection started failing on the develop channel.

The cost is documentation depth. Recyclarr has years of Stack Overflow answers and a dedicated docs site; Configarr has a config template and a growing documentation site. If something breaks at 1 a.m., Recyclarr is easier to debug from memory.

## Pitfalls and Migration Notes

**Never run two of these tools against the same instance.** All three write quality profile scores through the same API endpoints. If Recyclarr syncs at 03:00 and Profilarr syncs at 03:05 with a different library version, your scores will oscillate and your downloads will become inexplicably bad. Pick one and disable the others' schedulers.

**`replace_existing_custom_formats: true` deletes formats you created by hand.** It is the single most destructive option in all three tools. Turn it on for a clean instance; leave it off on an instance where you have hand-tuned formats, and let the tool add rather than replace.

**API keys are not the same as the web UI password.** Radarr and Sonarr expose the key under Settings → General. A 401 in the logs almost always means you copied the wrong field, not that the container is broken.

**Quality profile *names* must match exactly.** TRaSH templates reference profiles by name. If you renamed `HD Bluray + WEB` to `HD Bluray + WEB (custom)`, the sync will create a second profile instead of updating the first, and you will end up with two profiles competing for the same releases.

**Score zero is not the same as no score.** A custom format that exists but is scored 0 still participates in decisions in some *arr versions. `reset_unmatched_scores` is what normalises this, and leaving it disabled is a common cause of "why did it grab that release" threads.

## Why Self-Host Your Media Automation At All?

The honest answer is that the alternative is worse in three specific ways.

First, **cost**. A hosted media automation stack that covers library management, indexer aggregation, and quality enforcement runs well past the price of a small VPS per year, and it still requires you to host the storage. A single 4 GB VPS running Sonarr, Radarr, Prowlarr, and one of these config tools costs less than a streaming subscription and does not raise prices annually.

Second, **data ownership**. Watch history, quality preferences, and library metadata are the most commercially valuable data a household produces. Keeping them in a PostgreSQL volume you control means no export requests and no terms-of-service changes.

Third, **correctness**. The entire reason these three tools exist is that quality enforcement is a maintenance problem. TRaSH Guides update weekly. A managed service gives you whatever profile its operators chose; a self-hosted sync tool gives you a diff and a rollback.

If you are still assembling the stack, our [Sonarr vs Radarr vs Prowlarr vs Bazarr comparison](../sonarr-vs-radarr-vs-prowlarr-vs-bazarr-lidarr-self-hosted-media-automation-2026/) covers which services you actually need, and the [download automation guide](../2026-04-30-autobrr-vs-jackett-vs-prowlarr-self-hosted-download-automation-guide-2026/) explains how indexers and filters fit together. Once people start requesting titles, the [Overseerr vs Jellyseerr vs Ombi breakdown](../2026-04-21-overseerr-vs-jellyseerr-vs-ombi-self-hosted-media-requests-guide-2026/) handles the front door.

## FAQ

**Do I need Recyclarr if I already use Profilarr?**
No, and you should not run both. They write to the same quality profile endpoints. Choose one: Profilarr if you want a UI and multi-instance library management, Recyclarr if you want a cron job and a YAML file.

**Does Recyclarr work with Radarr v7 and Sonarr v5?**
Yes. Recyclarr tracks the *arr API surface closely, and current releases handle the v7 authentication changes. The `develop` images of Radarr and Sonarr change behaviour frequently, so pin your *arr images to stable tags if sync failures would disrupt your household.

**Can these tools create quality profiles from scratch?**
Recyclarr and Configarr both create profiles from TRaSH templates, including custom formats and scores. Profilarr creates profiles from its internal library, which can be seeded from TRaSH or built by hand in the interface. None of them will invent a scoring scheme for you.

**What happens if I edit a quality profile manually after a sync?**
On the next sync, Recyclarr will overwrite the managed fields unless you disable that behaviour for the profile. Profilarr will flag the drift and show it to you before applying changes. Configarr will overwrite anything matched by its merge layers. This is why the tools are mutually exclusive in practice.

**How often should the sync run?**
Daily is enough for most households. TRaSH Guides revisions are not emergencies, and a nightly 03:00 sync keeps scores current without repeatedly hitting the *arr API. Run it manually after you change your own config.

**Is a database required?**
Recyclarr needs only a config directory and a cache. Configarr needs only a config directory. Profilarr keeps a database inside its `/config` volume, so back that volume up alongside your *arr configuration if you want to preserve your library.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Recyclarr vs Profilarr vs Configarr in 2026: Which Arr Config Tool Should You Actually Use?",
  "description": "Hands-on comparison of Recyclarr, Profilarr and Configarr for syncing TRaSH Guides quality profiles and custom formats into Sonarr and Radarr.",
  "datePublished": "2026-11-09",
  "dateModified": "2026-11-09",
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
