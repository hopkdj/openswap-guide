---
title: "Self-Hosted Weather APIs in 2026: Open-Meteo vs Pirate Weather vs Bright Sky"
date: "2026-09-22"
tags: ["self-hosted", "weather", "api", "open-data", "open-source"]
draft: false
cover: "/img/screenshots/pirateweather-devportal.jpg"
---

Every weather integration you have ever written is a bet on someone else's API key. Free tiers shrink, per-call pricing arrives, rate limits tighten, and one day your dashboard returns `401 Unauthorized` because a billing card expired. Meanwhile the underlying data — **numerical weather prediction model output** — is largely public and free. The gap between "free public model data" and "a JSON endpoint your app can call" is exactly what self-hosted weather APIs fill.

**TL;DR — the quick verdict:** For a general-purpose replacement for a commercial forecast API, run **Open-Meteo** — it is the most complete self-hosted option, ships an official Docker Compose stack and a published container image, and serves an API shape you can point existing clients at. If your code was written against the retired Dark Sky API and you want minimal changes, use **Pirate Weather**. If you specifically want German DWD observational and forecast data with a small, readable Python codebase, deploy **Bright Sky**. And if you want a Python toolkit to query many national weather services from one interface — including bulk historical downloads — install **Wetterdienst**.

## The Comparison Table

Star counts and last-commit dates were pulled from GitHub while writing this article.

| Project | What it actually is | Language | Stars | Last commit | Deployment style |
|---|---|---|---|---|---|
| **Open-Meteo** | Full forecast API server: ingests ICON and other models, serves JSON | Swift (server), API-compatible clients | 6,233 | 2026-09-22 | Official `docker-compose.yml` + `ghcr.io/open-meteo/open-meteo` image |
| **Pirate Weather** | Drop-in Dark Sky API replacement, community-run | Multi-part (API, data pipeline, Home Assistant client) | 908 | 2026-09-21 | Repo-based deployment; companion client repos |
| **Bright Sky** | HTTP API over German DWD open data, with radar and alerts | Python (Flask + worker) | 420 | 2026-04-27 | Official `docker-compose.yml` with PostgreSQL 17 and Redis 7 |
| **Wetterdienst** | Python library and REST service for many national weather services | Python | 451 | 2026-09-22 | `compose.yml` with `backend` / `app` profiles |

The star counts tell you something important about this niche: **Open-Meteo is roughly seven times more popular than the next project**, and that popularity is a proxy for how many field-tested edge cases have been ironed out. It also has the only officially published container image in the group, which removes an entire class of "build fails on my machine" problems.

## Which Weather API Should You Deploy?

| Your requirement | Recommended | Why |
|---|---|---|
| Replace a commercial forecast API in existing code | **Open-Meteo** | Serves a documented JSON forecast endpoint; official Compose file starts with `docker compose up` |
| Dark Sky-style response format, minimal client changes | **Pirate Weather** | Built explicitly as an API-compatible successor |
| Official national weather service data, small auditable codebase | **Bright Sky** | Thin API layer over DWD open data, PostgreSQL + Redis only |
| Bulk historical time series for analysis or model training | **Wetterdienst** | Designed for programmatic access to many providers, not just one |
| Home Assistant custom weather card | **Pirate Weather** | Dedicated integration repo maintained alongside the API |
| Air-gapped or on-prem only | **Open-Meteo** | Self-contained model sync into local storage, no outbound calls at request time |

## Open-Meteo: The Full Forecast Server

Open-Meteo is not a proxy that forwards requests to somebody else's API — it **downloads numerical model output and serves it from your own database**. That distinction matters: once the sync has run, your API answers requests without touching the public internet, which makes it usable for latency-sensitive and network-restricted environments.

The repository ships a Docker Compose file whose own comment block documents the exact start command and a sample query:

```yaml
# Docker Compose file for running the Open-Meteo API on Docker
# Start with: docker compose up
#
# http://0.0.0.0:8080/v1/forecast?latitude=47.1&longitude=8.6&hourly=temperature_2m&models=icon_global

volumes:
  open_meteo_database:

x-shared_environment: &shared_environment
  LOG_LEVEL: info

services:
  open-meteo-sync:
      image: ghcr.io/open-meteo/open-meteo
      container_name: open-meteo-sync
      environment:
        <<: *shared_environment
      command: sync dwd_icon temperature_2m --past-days 2 --repeat-interval 1 --concurrent 1
      volumes:
       - open_meteo_database:/app/data
      restart: always

  open-meteo:
    image: ghcr.io/open-meteo/open-meteo
    container_name: open-meteo-api
    volumes:
      - open_meteo_database:/app/data
    build:
      context: .
    environment:
      <<: *shared_environment
    ports:
      - '8080:8080'
    user: '0'
```

Read that sync command closely, because it defines both the cost model and the operational rhythm of the deployment:

```bash
# What the compose file runs, unpacked:
#   dwd_icon        => the DWD ICON model as the data source
#   temperature_2m  => only this variable is ingested
#   --past-days 2   => keep a two-day rolling window
#   --repeat-interval 1 => re-sync hourly
#   --concurrent 1  => one download worker at a time
```

Every variable you add multiplies storage and ingest time. A useful production pattern is to start with exactly the variables your application consumes, watch the growth of the `open_meteo_database` volume for a week, and only then widen the set. Query it like any other HTTP API:

```bash
# Verify the container is serving data
curl -s "http://localhost:8080/v1/forecast?latitude=47.1&longitude=8.6&hourly=temperature_2m&models=icon_global" \
  | head -c 300
```

![Pirate Weather developer portal](/img/screenshots/pirateweather-devportal.jpg "Pirate Weather developer portal — official project asset")

## Pirate Weather: The Dark Sky Successor You Can Run Yourself

When Apple retired the Dark Sky API, a large amount of embedded and hobbyist code was left pointing at a dead endpoint. Pirate Weather was built to be the **API-compatible replacement**, and it is organised as a small family of repositories: the API and data pipeline itself, a Home Assistant integration, and a code-sharing repository for clients.

That structure is worth understanding before you deploy it: you are not installing a single monolith, you are installing an API layer plus the pipeline that feeds it. In practice that means:

- Budget for **two moving parts** (data ingestion and API serving) rather than one container.
- Pin your versions. With three coordinated repositories, an unpinned upgrade can land a client that expects a different payload than your server emits.
- If your goal is a Home Assistant weather card, deploy the integration repository alongside the API and treat the pair as one unit.

The commercial argument for self-hosting a Dark Sky replacement is straightforward: those endpoints were metered and rate-limited, and a self-hosted instance is neither. The trade-off is that you now own the ingestion pipeline, so you need monitoring on the pipeline's freshness — an API that answers correctly with six-hour-old data is worse than one that fails loudly.

## Bright Sky and Wetterdienst: The Data-First Approach

**Bright Sky** takes the opposite architectural stance from Open-Meteo. Rather than syncing model output into a large local store, it exposes the **German national weather service (DWD) open data** through a small Python API backed by PostgreSQL and Redis. The whole stack is three services, and the repository's Compose file is short enough to read in full before you deploy it:

```yaml
services:
  postgres:
    image: postgres:17-alpine
    shm_size: 512mb
    environment:
      POSTGRES_PASSWORD: pgpass
    volumes:
      - .data:/var/lib/postgresql/data
    restart: unless-stopped
  redis:
    image: redis:7-alpine
    restart: unless-stopped
  worker:
    <<: *brightsky
    command: --migrate work
    restart: unless-stopped
  web:
    <<: *brightsky
    command: serve --bind 0.0.0.0:5000
    restart: unless-stopped
    ports:
      - 5000:5000
```

Note two things. First, the API binds to **port 5000** and the `worker` service runs migrations before serving — so a fresh deployment needs the worker up, not just the web container. Second, the example password in the upstream file is `pgpass`; replacing it before your first start is not optional, and you should bind PostgreSQL to a private network rather than publishing its port.

**Wetterdienst** is the analyst's tool rather than a replacement API. It ships a `compose.yml` with **profiles** — `backend` and `app` — so you can start only the REST service, only the frontend, or both, depending on whether your consumers are scripts or humans. If your workload is "download twenty years of hourly observations for twelve stations and fit a model", Wetterdienst is built for that and Open-Meteo is not.

![Wetterdienst summary output](/img/screenshots/wetterdienst-summary.jpg "Wetterdienst documentation output — official project asset")

## Pitfalls When Self-Hosting Weather Data

- **Storage grows faster than you expect.** Weather data is three-dimensional: variable × location × time. Ingesting a full model with dozens of variables can consume hundreds of gigabytes per month. Start with one variable and one model.
- **Freshness is your real SLA.** Nobody cares that your API is up if the data behind it is stale. Export a timestamp of the newest ingested observation and alert on it, not just on container health.
- **The example credentials in upstream Compose files must be changed.** `POSTGRES_PASSWORD: pgpass` is a placeholder, and publishing port 5000 or 8080 directly to the internet without a reverse proxy exposes an API with no authentication in front of it.
- **Licensing differs from data licensing.** The software licence (AGPL for Open-Meteo, MIT for Wetterdienst) is separate from the terms attached to the weather data you ingest. Check the data provider's attribution requirements before you serve it publicly.
- **Model choice changes your answers.** ICON, GFS, and regional models disagree — sometimes by several degrees. If you switch models during a migration, your historical comparisons break. Record which model produced every stored forecast.
- **Do not run bulk ingestion on the same disk as your database without thinking.** Sync workers are I/O heavy; co-locating them with PostgreSQL on a single spinning disk is a reliable way to make your API slow under load.

## Why Self-Host Your Weather Data?

Three reasons keep coming up in practice. **Independence from pricing changes**: a self-hosted forecast API is a fixed infrastructure cost, and it does not get more expensive because your application became popular. **Latency and offline operation**: when the data is local, a request never waits on a third-party round trip, and a network incident upstream does not take your product down with it. **Data lineage**: when you serve your own forecasts, you know which model run produced them, when it was ingested, and what post-processing was applied — an audit trail you simply cannot get from a black-box endpoint.

Self-hosting weather data is also the natural complement to running your own observation hardware. If you already operate station software, the [weather station software comparison](../2026-05-04-self-hosted-weather-station-software-weewx-meteobridge-weather34-guide/) covers how to collect and publish your own measurements, and the [air quality monitoring platforms guide](../2026-06-04-self-hosted-air-quality-monitoring-airrohr-luftdaten-sensor-community-guide/) shows the same self-hosted pattern applied to sensor networks. Combining local observations with self-hosted forecast data is how you build a dashboard that no commercial API can match.

## FAQ

**Can I run Open-Meteo with no internet connection at all?**
No — the sync step downloads model output from upstream providers and requires outbound access. Once the sync has completed, however, the API serves requests from local storage, so brief network outages do not affect your users. For genuinely air-gapped operation you need to mirror the model files manually across the boundary.

**How much disk space does a minimal Open-Meteo deployment need?**
It depends entirely on how many variables and models you ingest. The safe way to size it is empirical: run the sync with a single variable and a two-day window for one week, measure the volume growth, then multiply by the variable count you actually need. A single-variable, single-model setup is measured in tens of gigabytes; a full variable set is measured in hundreds.

**Is Pirate Weather a true drop-in for Dark Sky?**
It was built for that purpose and ships client repositories to smooth the transition, but you should still diff the response fields your application reads against the new payload. Treat it as a compatible rewrite and run one staging deployment before cutting production traffic over.

**Does Bright Sky work outside Germany?**
Its data source is the German national weather service, so its coverage and value are concentrated there. If your users are elsewhere, choose Open-Meteo (which ingests multiple national models) or use Wetterdienst to pull from the provider that covers your region.

**What should I monitor on a self-hosted weather API?**
Four things: container health, the timestamp of the newest ingested data, response latency for a representative query, and storage growth rate. The freshness timestamp is the signal that catches real incidents — everything else usually stays green while your forecast quietly ages.

**Can I serve a self-hosted weather API to third parties?**
Technically yes, and the software licences generally allow it, but the data provider's attribution and redistribution terms are what govern you. Put a reverse proxy with TLS and rate limiting in front of the API, and check the upstream provider's terms before publishing anything commercial.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Weather APIs in 2026: Open-Meteo vs Pirate Weather vs Bright Sky",
  "description": "Compare self-hosted weather forecast APIs — Open-Meteo, Pirate Weather, Bright Sky and Wetterdienst — with real Docker Compose configurations, storage planning guidance and operational pitfalls.",
  "datePublished": "2026-09-22",
  "dateModified": "2026-09-22",
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
