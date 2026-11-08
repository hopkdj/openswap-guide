---
title: "Self-Hosting on ARM64 in 2026: Raspberry Pi 5 vs Hetzner Ampere vs Oracle A1"
description: "A hands-on comparison of three ARM64 self-hosting platforms in 2026 — Raspberry Pi 5 at home, Hetzner CAX cloud servers, and Oracle's always-free Ampere A1 — with real pricing, multi-arch build commands, and the pitfalls that break arm64 deployments."
date: "2026-11-08"
tags: ["self-hosted", "arm64", "homelab", "docker", "cloud"]
draft: false
---

Your x86 VPS got more expensive again, the watt-meter on your old tower server reads 90 W idle, and half the services you actually run are a reverse proxy, a database, and three containers that never exceed 2 GB of RAM. That is exactly the workload ARM64 was waiting for.

But "just use ARM" hides a real fork in the road: a $80 Raspberry Pi under your desk, a €3.79/month Ampere cloud instance with a real IPv4 address, or a free Oracle tenancy that hands you 24 GB of RAM and then makes you fight for capacity. They are not interchangeable, and the failure modes are completely different. This guide breaks down which one to pick, what it actually costs, and how to keep multi-arch images from silently breaking your deploy.

## TL;DR: The 30-Second Verdict

- **Learning, tinkering, home automation, media serving** → Raspberry Pi 5 (8 GB) with an NVMe HAT. Cheap, silent, 5–7 W idle, and you own the hardware.
- **Public-facing services that must be up at 3 a.m.** → Hetzner CAX (Ampere Altra). From €3.79/month, real bandwidth, real IPv4, snapshots, and no SD card to corrupt.
- **Batch jobs, CI runners, staging clusters, big-memory experiments** → Oracle Ampere A1 always-free tier (4 OCPU / 24 GB). Unbeatable price, but provisioning is capacity-gated and idle instances can be reclaimed.
- **Do not** run a production Postgres or an Elasticsearch node on a Pi's SD card. This is the single most common way people lose a weekend of data.

## Quick Comparison: ARM64 Self-Hosting Platforms

| | Raspberry Pi 5 | Hetzner CAX11 / CAX21 | Oracle Ampere A1 (always free) |
|---|---|---|---|
| **CPU** | 4× Cortex-A76 @ 2.4 GHz | 2 / 4 dedicated Ampere Altra vCPU | 4 OCPU (Ampere Altra), up to 4 total |
| **RAM** | 4 / 8 / 16 GB LPDDR4X | 4 GB / 8 GB | 24 GB |
| **Storage** | microSD, or NVMe via M.2 HAT+ (PCIe 2.0 x1) | 40 GB / 80 GB local NVMe SSD | 200 GB block volume (total, free) |
| **Network** | 1 GbE, Wi-Fi 5 | 1 Gbps shared, 20 TB traffic included | 1 Gbps, 10 TB egress/month |
| **Public IPv4** | No (CGNAT or tunnel needed) | Yes | Yes (reserved public IP) |
| **Price (list, Nov 2026)** | ~$80 one-off (8 GB) + storage + power | €3.79 / €6.49 per month | $0 |
| **Idle power** | 5–7 W | n/a (shared host) | n/a |
| **Uptime risk** | Home power, ISP, SD wear | Provider-level SLA | Capacity + idle reclamation |
| **Best for** | Homelab, local-first services | Small production stacks | CI, batch, staging, experiments |

Both cloud options are genuine ARM64 servers — `uname -m` returns `aarch64` on all three, and the same container images run on each. What differs is everything around the CPU.

## Decision Matrix: Pick Your Platform in 10 Seconds

| Your situation | Recommended platform | Why |
|---|---|---|
| First self-hosted setup, < 10 containers | Raspberry Pi 5, 8 GB | Lowest total cost, no monthly bill, huge tutorial ecosystem |
| Nextcloud + Immich + a small Postgres for family use | Raspberry Pi 5 + NVMe HAT | Local storage is cheap; throughput is fine for 2–5 users |
| A SaaS product with paying users | Hetzner CAX21 | Dedicated vCPU, IPv4, snapshots, 20 TB traffic |
| GitLab runner or nightly build farm | Oracle A1 (4 OCPU / 24 GB) | Free, ephemeral workloads tolerate reclamation risk |
| You need 32 GB+ RAM on ARM | Hetzner CAX41 or Oracle A1 (up to 24 GB free) | Pi tops out at 16 GB |
| Strict data-residency at home, no cloud | Raspberry Pi 5, boot from NVMe | No third party touches the disk |

## Raspberry Pi 5: The Cheapest Way to Learn ARM64

The Pi 5 is a genuinely capable server: four Cortex-A76 cores at 2.4 GHz, up to 16 GB of LPDDR4X, a real PCIe 2.0 lane exposed through the FPC connector, and gigabit Ethernet with PoE+ support through a HAT. For a reverse proxy, Home Assistant, a couple of databases and a media indexer, it is more than enough — the bottleneck is almost always storage I/O, not CPU.

**Buy the NVMe HAT.** A microSD card doing database writes will die, usually within a year, usually at the worst moment. An M.2 HAT+ plus a 500 GB NVMe drive costs about as much as the board and turns the Pi into a machine you can trust:

```bash
# /boot/firmware/config.txt — enable PCIe Gen 3 on the Pi 5
dtparam=pciex1
dtparam=pciex1_gen=3

# Verify the drive is visible after reboot
lsblk
sudo nvme list
```

A minimal Docker stack that runs comfortably on 4 GB of RAM:

```yaml
# compose.yaml — Pi 5 friendly stack
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data

  forgejo:
    image: codeberg.org/forgejo/forgejo:11
    restart: unless-stopped
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - FORGEJO__server__ROOT_URL=https://git.example.com/
    volumes:
      - forgejo:/data
    ports:
      - "3000:3000"

volumes:
  caddy_data:
  forgejo:
```

Install Docker from the official convenience script (it detects `aarch64` and pulls the right packages):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker
```

Two Pi-specific rules worth taping to the wall: set `gpu_mem=16` if you run headless (the default split wastes RAM), and keep swap on the NVMe, not the SD card, or disable it entirely and rely on cgroups limits. For a deeper look at running containers without root on small boards, see our [rootless container runtimes comparison](../2026-05-09-rootless-container-runtimes-docker-podman-containerd-guide/) — it matters more on a shared home network than on a single-tenant VPS.

## Hetzner Ampere CAX: The Best Price/Performance for Public Services

Hetzner's CAX line runs on Ampere Altra processors with **dedicated** vCPUs — no noisy-neighbour stealing, which is the main reason a €6.49 CAX21 often outperforms a €12 x86 VPS on single-threaded web workloads. The lineup scales from 2 vCPU / 4 GB (CAX11, €3.79/mo) to 16 vCPU / 32 GB (CAX41, €24.49/mo), each with local NVMe and 20 TB of included traffic.

Pricing changes; treat the numbers above as a starting point and confirm on the provider's pricing page before you budget. What does not change is the operational shape: you get a public IPv4, snapshots, a firewall, and cloud-init, which means a full stack can be reproducible from a YAML file.

```yaml
#cloud-config
# Hetzner Cloud user-data: bootstrap a CAX instance with Docker + Compose
package_update: true
packages:
  - ca-certificates
  - curl
  - git
runcmd:
  - curl -fsSL https://get.docker.com | sh
  - systemctl enable --now docker
  - mkdir -p /srv/stack
  - cd /srv/stack && git clone https://github.com/example/stack.git .
  - docker compose up -d
```

One habit that pays for itself: put the data volume on a Hetzner Volume and snapshot it on a schedule, so a rebuild is `cloud-init` plus a volume attach instead of a restore-from-memory exercise. And because CAX instances are plain vanilla `aarch64`, every `linux/arm64` image on Docker Hub runs unmodified — no emulation layer, no rebuild.

## Oracle Ampere A1: 24 GB of Free RAM With a Catch

Oracle's always-free tier includes **4 OCPU and 24 GB of RAM** on Ampere A1, plus 200 GB of block storage and 10 TB of monthly egress. As raw capacity per dollar, nothing else on this list is close: a 4-core, 24 GB ARM machine for free is enough to run a small Kubernetes cluster, a GitLab runner, or a staging copy of your production stack.

Two caveats decide whether it works for you:

1. **Capacity is not guaranteed.** `Out of host capacity` is the error everyone hits when creating an A1 instance in a busy region. Retry across availability domains, try a smaller shape (2 OCPU / 12 GB provisions more often than 4/24), or script the retry loop and walk away.
2. **Idle always-free instances can be reclaimed.** Treat this tier as preemptible infrastructure: no single point of failure, no unique data, everything reproducible from a repository.

That second point is not a reason to avoid it — it is a reason to design for it. Keep state in object storage or on the block volume with backups elsewhere, and keep the bootstrap in `cloud-init` so a reclaimed instance is a 6-minute rebuild rather than an incident.

```bash
# Verify you are actually on Ampere, not an x86 fallback shape
uname -m          # aarch64
lscpu | grep -E "Model name|Architecture|CPU\(s\)"

# A1 instances ship with a tuned kernel; check what you got
free -h
nproc
```

## Building and Running Multi-Arch Images

The single most common ARM64 self-hosting failure is not hardware — it is an image that only exists for `amd64`. You find out when the container exits instantly with `exec format error`.

Check before you pull:

```bash
docker manifest inspect library/postgres:17 | grep -A2 '"architecture"'
# or, cleaner:
docker buildx imagetools inspect postgres:17 --format '{{json .Manifest}}' | head -c 400
```

Build your own images for both architectures in one command:

```bash
# one-time: register emulators on the build host
docker run --privileged --rm tonistiigi/binfmt --install all

docker buildx create --name multiarch --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/example/app:1.4.0 \
  --push .
```

If you cannot rebuild an image, pin the platform explicitly in Compose so the failure is loud instead of mysterious:

```yaml
services:
  legacy-app:
    image: example/legacy:2.1
    platform: linux/amd64   # runs under QEMU emulation — slow, but works
```

Emulation is a bridge, not a destination: a JVM service under QEMU on a Pi 5 can be 5–10× slower than the same container built natively. Anything you run permanently should have a real `linux/arm64` build.

## Pitfalls That Bite ARM64 Self-Hosters

- **SD card write amplification.** Databases, container logs and image layers all write constantly. Boot from NVMe or mount `/var/lib/docker` on an SSD.
- **Missing arm64 tags on niche images.** Popular stacks (Postgres, Redis, Nginx, Caddy, Grafana, Prometheus) are all multi-arch. Long-tail vendor appliances often are not — check before you design around them.
- **Memory limits, not swap.** A 4 GB Pi will happily thrash itself to death. Set `mem_limit` in Compose and let the OOM killer do its job instead of the kernel swapping for minutes.
- **32-bit userland.** Raspberry Pi OS 64-bit is mandatory for anything containerised at scale; the 32-bit build still exists and will waste your afternoon.
- **Thermal throttling.** A Pi 5 under sustained load drops from 2.4 GHz to 1.5 GHz without a heatsink. If you are compiling images on-device, buy the active cooler.
- **Backups that only exist on the same disk.** Snapshots on the same provider are not backups. Copy them somewhere else on a schedule.

If you are weighing container runtimes for these boards rather than the hardware itself, our [rootless container infrastructure guide](../2026-05-10-rootless-container-infrastructure-rootlesskit-fuse-overlayfs-slirp4netns-guide/) covers the kernel features involved, and the [Incus vs LXD vs Podman comparison](../2026-04-24-incus-vs-lxd-vs-podman-self-hosted-container-virtualization-guide-2026/) is the right starting point if you want system containers instead of application containers.

## FAQ

### Is a Raspberry Pi 5 fast enough to run Docker in production?

For a handful of low-traffic services, yes — a Pi 5 with NVMe handles a reverse proxy, a database and a few containers for a small team without trouble. "Production" becomes a problem when you need redundancy, guaranteed IOPS, or more than 16 GB of RAM. At that point a Hetzner CAX instance is cheaper than the downtime.

### Can I run the same Docker Compose file on a Pi, a Hetzner CAX server and Oracle A1?

Yes, as long as every image has a `linux/arm64` variant. Compose files are architecture-agnostic; only the images matter. Add a `platform:` key for the rare image that is `amd64`-only, or rebuild it with `docker buildx --platform linux/arm64`.

### What does `exec format error` mean in `docker logs`?

It means the container image does not contain a binary for your CPU architecture — you pulled an `amd64` image onto an `aarch64` host. Check with `docker manifest inspect <image>` and either switch to a multi-arch tag or enable QEMU emulation through `binfmt`.

### Is Oracle's Ampere A1 tier really free forever?

The always-free allowance (4 OCPU, 24 GB RAM, 200 GB block storage) has no expiry, but instances are subject to capacity limits at creation time and Oracle may reclaim idle always-free resources. Keep the workload reproducible and back up anything you would miss.

### How much does it cost to run a Raspberry Pi 5 as a server for a year?

At 5–7 W average and a typical €0.30/kWh tariff, the electricity is roughly €13–18 per year. Add the board (~$80 for 8 GB), an NVMe HAT and a drive, and year one lands around $150–200 — after which the marginal cost is power and your time.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosting on ARM64 in 2026: Raspberry Pi 5 vs Hetzner Ampere vs Oracle A1",
  "description": "A hands-on comparison of Raspberry Pi 5, Hetzner CAX Ampere servers and Oracle's free Ampere A1 tier for self-hosting in 2026, including multi-arch Docker builds and common arm64 pitfalls.",
  "datePublished": "2026-11-08",
  "dateModified": "2026-11-08",
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
