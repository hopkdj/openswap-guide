---
title: "Komari vs CheckCle vs Beszel in 2026: Which Self-Hosted Server Monitor Actually Fits?"
date: "2026-10-27"
tags: ["monitoring", "self-hosted", "server-monitoring", "observability", "devops"]
draft: false
description: "A hands-on comparison of Komari, CheckCle and Beszel: three lightweight Go-based self-hosted monitoring stacks. Deploy configs, alerting behavior, storage model and real trade-offs."
---

Your monitoring stack should not be heavier than the services it watches. That is the uncomfortable truth behind the latest wave of self-hosted monitors: teams abandoned Prometheus + Grafana + Alertmanager for a single VPS because the observability bill and the operational surface outgrew the workload. **Komari (6,612 stars), CheckCle (3,309 stars) and Beszel (26,565 stars) attack that problem from three different angles** — and picking the wrong one costs you either visibility or an afternoon of reverse-proxy debugging.

## TL;DR — the 30-second verdict

- **Pick Beszel** if you run 2-30 Linux boxes or Docker hosts and want the least work: one hub, one tiny agent, historical charts, alerts. It is the most mature of the three and the safest default.
- **Pick Komari** if you want a public-facing status page with a themeable, good-looking dashboard and a single binary you can deploy in 60 seconds. It is the "on-call wall display" choice.
- **Pick CheckCle** if uptime and synthetic checks matter as much as CPU graphs — HTTP/TCP/DNS probes, distributed checkers, incident tracking and on-call escalation in one box.

None of the three will replace a real metrics pipeline at 500 hosts. All three will replace your `watch uptime-kuma` reflexes at 5.

## Side-by-side comparison

| Dimension | Komari | CheckCle | Beszel |
|---|---|---|---|
| Written in | Go | Go + PocketBase | Go |
| GitHub stars (Oct 2026) | 6,612 | 3,309 | 26,565 |
| Last commit | 2026-10-26 | 2026-07-17 | 2026-10-25 |
| Agent model | Lightweight agent pushes to hub | Agent / remote checks | Hub + agent, SSH fallback |
| Default port | 25774 | 8090 | 8090 (agent 45876) |
| Storage | Embedded DB in `./data` | PocketBase (SQLite) | SQLite in `/beszel_data` |
| Historical charts | Yes, per-node | Yes, plus uptime history | Yes, with Docker stats |
| Synthetic checks (HTTP/TCP/DNS) | Basic | Yes, core feature | No (status monitoring only) |
| Alert channels | Webhook / Telegram-style hooks | Email, Slack, Discord, ntfy, Gotify, Notifiarr | Email, webhook, Shoutrrr-compatible |
| Reverse proxy needs | WebSocket support | HTTP only | WebSocket support |
| Cost | Free, self-hosted | Free, self-hosted | Free, self-hosted |

The star counts are live from GitHub as of this writing — and they tell the real story: Beszel has roughly 4x Komari's community and 8x CheckCle's. That matters when an update breaks your dashboard at 2 a.m.

## Decision matrix: pick in 10 seconds

| Your situation | Use this | Why |
|---|---|---|
| 3 VPS, you want graphs and Docker stats today | **Beszel** | Hub + agent in one compose file, alerts built in |
| Public status page for clients | **Komari** | Themeable dashboard, cheap to expose, single binary |
| You need HTTP/SSL expiry/TCP probes plus incidents | **CheckCle** | Synthetic checks and incident workflow are first-class |
| Mixed cloud + home lab, some hosts can't run an agent | **Beszel** | SSH-based collection fallback |
| Kiosk display on a TV in the office | **Komari** | Best-looking default UI of the three |
| Regulated environment, everything on one box | **CheckCle** | PocketBase keeps users, checks and incidents in one SQLite file |

## Komari — the dashboard people actually screenshot

Komari is a Go monitor with an agent-per-host model and a genuinely good-looking web UI. The install is deliberately boring, which is exactly what you want on a monitoring box:

```bash
docker run -d \
  --name komari \
  --restart unless-stopped \
  -p 25774:25774 \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/komari-monitor/komari:latest
```

That is the whole deployment. Open `http://your-host:25774`, create the admin account on first boot, then add nodes in the panel — each node gets a token you paste into the agent installer. Binary installs are documented at `komari.wiki` under the quick-start guide if you prefer systemd over containers.

What Komari gets right: the node card layout, the per-node latency/load charts, and the fact that everything lives in `./data` so a backup is `tar czf komari.tgz data/`. What it gets wrong: alerting is thinner than the alternatives, and the design assumes your dashboard is exposed over a reverse proxy. Because live data flows over WebSocket, a Caddy or Nginx config that forgets the upgrade headers gives you a dashboard that loads once and then freezes — the single most common Komari support question.

## CheckCle — uptime checks with an incident workflow

CheckCle is the only one of the three that treats "is the service up" as a first-class measurement alongside CPU and memory. It ships as a single Go binary with PocketBase underneath, listens on 8090, and persists everything to `/mnt/pb_data`:

```yaml
version: '3.9'
services:
  checkcle:
    image: operacle/checkcle:latest
    container_name: checkcle
    restart: unless-stopped
    ports:
      - "127.0.0.1:8090:8090"
    volumes:
      - /opt/pb_data:/mnt/pb_data
    ulimits:
      nofile:
        soft: 4096
        hard: 8192
```

Note the bind address: `127.0.0.1:8090:8090` instead of the project's default `8090:8090`. CheckCle's admin panel has no built-in TLS, so publishing it on a public interface is a bad first day. Put Caddy in front:

```caddyfile
monitor.example.com {
    reverse_proxy 127.0.0.1:8090
    encode zstd gzip
}
```

CheckCle's differentiators are HTTP/TCP/DNS checks with assertions, distributed checkers (so the probe runs from somewhere other than the box being probed), and incident records you can actually attach a timeline to. The cost is maintenance velocity: its last commit is **2026-07-17**, roughly three months behind the other two. That is not dead, but it is a slower bus, and you should read the changelog before depending on a new feature.

## Beszel — the boring, correct default

Beszel splits into a hub (UI, SQLite, alerts) and an agent that runs on each monitored host. The hub is the only thing you expose:

```yaml
services:
  beszel:
    image: henrygd/beszel:latest
    container_name: beszel
    restart: unless-stopped
    ports:
      - "8090:8090"
    volumes:
      - ./beszel_data:/beszel_data

  beszel-agent:
    image: henrygd/beszel-agent:latest
    container_name: beszel-agent
    restart: unless-stopped
    network_mode: host
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./beszel_agent_data:/var/lib/beszel-agent
    environment:
      LISTEN: 45876
      KEY: "${KEY}"
```

Two details bite people. First, `KEY` is generated by the hub when you add a system — copy it from the UI, do not invent one, or the agent will connect and immediately be rejected. Second, `network_mode: host` is required for the agent to report per-container stats correctly; bridging it hides the host's network interfaces and your bandwidth graphs will read as zero.

Beszel's strength is that it answers the questions a small team actually asks: CPU/memory/disk/network per host, per-container Docker usage, historical retention with configurable aging, and alerts that fire on thresholds you set per system. Its weakness: no synthetic HTTP checks. If your definition of "up" is "the API returns 200", Beszel will tell you the box is healthy while your app is on fire.

For a deeper look at how Beszel behaves as a standalone deployment, our [lightweight server monitoring guide](../2026-05-02-beszel-lightweight-self-hosted-server-monitoring-guide/) walks through the hub/agent handshake in detail. If you need probes and error budgets rather than resource graphs, the [synthetic monitoring comparison](../2026-04-28-gatus-vs-k6-vs-uptime-kuma-self-hosted-synthetic-monitoring-guide-2026/) covers that ground, and the [metrics stack comparison](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide-2026/) explains when you should just run a real time-series database instead.

## Why self-host monitoring at all?

Because the alternative is renting visibility. Hosted monitors charge per seat and per check, and the free tiers quietly cap retention at a few days — enough to see an outage, not enough to prove a trend. A self-hosted monitor keeps raw samples for as long as your disk allows, which is what you need for capacity planning: "disk grows 2 GB a week, we have eleven weeks" is a sentence a 7-day retention window cannot produce.

There is also a security argument. A monitoring agent sees your internal topology, hostnames, open ports and resource usage — a map of exactly where to attack. Running the hub inside your own network means that map never leaves. And a practical one: when your ISP link dies, a hosted monitor emails you about it; your own monitor on a second provider tells you *which* link died and for how long.

The trade-off is real and worth stating plainly: you are now the SRE for your monitoring. That means a backup of the SQLite file, an uptime check on the checker, and a documented restore procedure. Which brings us to the mistakes people make in week one.

## Pitfalls that cost people an evening

**1. Exposing the agent port.** Beszel's agent listens on 45876 with a shared key; CheckCle and Komari similarly assume a trusted network. Never publish those ports to the internet — bind the hub only, and firewall agent traffic to the hub's address.

**2. Forgetting WebSocket upgrade headers.** Komari and Beszel both push live samples over WebSocket. Nginx needs `proxy_set_header Upgrade $http_upgrade;` and `proxy_set_header Connection "upgrade";` on the location block, or charts stop updating after the first paint.

**3. Backing up the container, not the data.** All three keep state in a SQLite-family file. `docker commit` is not a backup. Stop the container (or use SQLite's online backup), copy the directory, and test the restore once — CheckCle's PocketBase data, Beszel's `beszel_data`, and Komari's `data/` folder are the only things that matter.

**4. Alerting on the wrong metric.** Disk percentage without a growth-rate check will page you at 90% forever. Alert on "will fill within 72 hours" instead, or you will train yourself to ignore the alarm — the most expensive failure mode in monitoring.

**5. Sampling every container.** Docker stats collection on a host with 60 containers can cost more than the app it monitors. Exclude ephemeral build containers with label filters, or your monitor becomes the workload.

**6. Letting the monitor's clock drift.** These tools compare agent timestamps to hub time. A host with NTP disabled shows flat gaps in every graph and looks like packet loss. Run `timedatectl` before you file the bug.

## FAQ

### Komari vs Beszel — which is lighter?

Both are Go binaries with small footprints, but Beszel's agent is the leaner of the two in practice because it pushes a compact set of samples and lets the hub do the storage work. Komari trades a little more per-node overhead for a richer default dashboard. On a 1 vCPU / 1 GB VPS, either fits; pick by UI preference, not by RAM.

### Does CheckCle replace Uptime Kuma?

For HTTP/TCP/DNS checks with incident tracking and multiple notification channels, yes — CheckCle covers that ground and adds system metrics. Uptime Kuma still wins on sheer simplicity and on the number of prebuilt notification integrations. If you already run Uptime Kuma and only lack host metrics, add Beszel rather than migrating.

### Can I run all three at once?

Yes, and it is not crazy: Beszel for resource history, CheckCle for probes and incidents, Komari for the wall display. They use different ports (8090, 8090, 25774), so run CheckCle and Beszel on separate hosts or remap one — `-p 8091:8090`. Just remember that three SQLite files means three backups.

### How much retention can I keep?

Retention is disk-bound. A rough figure for a small fleet: SQLite sample rows in the low hundreds of bytes, so 20 hosts at 60-second resolution is roughly 100-150 MB per month before rollups. All three downsample old data; set the rollup window to 30-90 days and keep raw samples for a week.

### Do these work without Docker?

Komari and CheckCle publish binaries and support systemd; Beszel's agent is a static binary that installs as a service on Linux, FreeBSD and macOS. The hub is the only part that is container-first in practice. If you are on BSD or an appliance OS, verify the agent architecture (`arm64` vs `amd64`) before you start.

### What about alerting to a phone at 3 a.m.?

All three support webhooks, which is the most portable path: point the webhook at ntfy, Gotify or a Discord/Slack incoming hook and you get push notifications without running an SMTP relay. CheckCle has the most native channels; Beszel's Shoutrrr-compatible URLs cover most chat platforms; Komari expects you to wire the webhook yourself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Komari vs CheckCle vs Beszel in 2026: Which Self-Hosted Server Monitor Actually Fits?",
  "description": "Hands-on comparison of Komari, CheckCle and Beszel for self-hosted server monitoring: deploy configs, alerting, storage model and trade-offs.",
  "datePublished": "2026-10-27",
  "dateModified": "2026-10-27",
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
