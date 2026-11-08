---
title: "Podman Quadlet vs Docker Compose in 2026: Which Declarative Stack Should Run Your Server?"
description: "Docker Compose is the default way to run containers on a single host — but Podman Quadlet turns containers into native systemd units. A practical 2026 comparison with real unit files, migration steps, and the pitfalls of each approach."
date: "2026-11-08"
tags: ["self-hosted", "podman", "docker", "systemd", "containers"]
draft: false
cover: "/img/screenshots/podman-desktop-compose-ui.jpg"
---

Here is the scenario that breaks the Compose-only habit: the host reboots at 2 a.m. for a kernel update. Your stack comes back — but the app container beats the database by four seconds, retries twice, gives up, and stays dead until someone notices. Compose has `depends_on`, but it does not have a real supervisor, real ordering against system services, or a way to restart *just* the broken container without touching the rest of the stack.

Podman Quadlet exists precisely for that gap. Instead of a daemon that owns your containers, you write `.container` files that systemd's generator turns into ordinary service units. No daemon, no second supervisor, no ordering surprises: `systemd` already knows how to start things in order, on boot, with dependencies, timers and journald logging.

So which one should run your server in 2026? Short answer: both can, but they optimise for different things.

## TL;DR: The 30-Second Verdict

- **You deploy multi-service app stacks, share them with a team, or use `docker compose` in CI** → stay on **Docker Compose**. It is the lingua franca, and nothing beats it for a 6-service stack you tear down and rebuild daily.
- **You run long-lived infrastructure on one host — reverse proxy, database, a handful of services — and want boot ordering you can reason about** → use **Podman Quadlet**. Containers become systemd units, logged in journald, started by the init system.
- **You need rootless containers with systemd semantics** → Quadlet. Rootless Podman plus user units plus `loginctl enable-linger` is the cleanest story available today.
- **You want one file for dev and prod, with profiles and overrides** → Compose. Quadlet has no equivalent of `--profile` or `compose.override.yaml`.
- **You are migrating tomorrow** → do not rewrite everything. Compose for apps you iterate on, Quadlet for infrastructure that must survive reboots untouched.

## Quick Comparison: Compose vs Quadlet

| Dimension | Docker Compose | Podman Quadlet |
|---|---|---|
| Repository activity (Nov 2026) | `docker/compose` — 38.6k stars, active | Part of `containers/podman` — 33.2k stars, active |
| Declarative format | `compose.yaml` (multi-service) | One `.container` / `.volume` / `.network` / `.pod` file per object |
| Process supervisor | Docker daemon (or podman-compose) | systemd, natively |
| Boot behaviour | Requires `docker.service`, containers with `restart:` policies | Generated units start at boot, ordered by systemd |
| Dependency ordering | `depends_on` + `condition: service_healthy` | `Requires=` / `After=` in the `[Unit]` section |
| Health checks | `healthcheck:` block, visible in `docker ps` | Container-level `HealthCmd=`; systemd sees unit state |
| Rootless | Possible, extra setup | First-class: user units under `~/.config/containers/systemd/` |
| Image auto-update | Watchtower or external tooling | `AutoUpdate=registry` + `podman-auto-update.timer` |
| Profiles / overrides | Yes (`--profile`, `compose.override.yaml`) | No equivalent |
| Logging | `docker logs`, json-file driver | journald (`journalctl --user -u name.service`) |
| Learning curve | Low — one YAML file | Medium — you must understand systemd units |
| Best fit | App stacks, dev loops, CI | Single-host infrastructure, appliances |

## Decision Matrix: Pick in 10 Seconds

| Your workload | Use | Why |
|---|---|---|
| Nextcloud + Postgres + Redis + reverse proxy | Quadlet | Long-lived, needs ordering after `network-online.target` |
| A dev stack you rebuild 10× a day | Compose | `down -v && up -d` is one command |
| CI job that spins up services for tests | Compose | Ephemeral by design; no systemd in most CI runners |
| Rootless services on a shared host | Quadlet | User units + linger, no daemon socket to secure |
| Something you `git pull` and redeploy weekly | Compose | Overrides and `.env` interpolation are mature |
| An appliance-style box that must always come back | Quadlet | Survives reboot without any third-party supervisor |

## Docker Compose: Still the Best Tool for Stacks

Compose's strength is that it models an *application*, not a machine. One file describes services, networks, volumes, health checks and startup order, and the same file works on a laptop, in CI, and on the server. That portability is why it won.

```yaml
# compose.yaml — health-gated startup order
services:
  db:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD}
      POSTGRES_DB: app
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app"]
      interval: 5s
      timeout: 3s
      retries: 10

  app:
    image: ghcr.io/example/app:1.8.2
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgres://postgres:${DB_PASSWORD}@db:5432/app
    ports:
      - "8080:8080"

volumes:
  db_data:
```

![Podman Desktop showing a Compose project and its containers](/img/screenshots/podman-desktop-compose-ui.jpg "A Compose stack running in Podman Desktop — the same compose.yaml is portable across engines")

Two things to know before you rely on it for infrastructure:

1. **`restart: unless-stopped` is not a supervisor.** It restarts crashed containers, but it does not order them against the rest of the machine, and it does not know that your NFS mount is not ready yet.
2. **Health-gated `depends_on` only applies at start.** If the database restarts later, the app is not restarted with it. For stateful dependencies you still need retry logic in the app.

If you want a UI on top of Compose, our [Portainer vs Dockge vs Coolify comparison](../2026-05-14-portainer-compose-vs-dockge-vs-coolify-docker-compose-management-ui/) covers the management layer, and the [Compose vs podman-compose vs nerdctl comparison](../docker-compose-vs-podman-compose-vs-nerdctl-container-compose-tools-2026/) covers the CLI implementations.

## Quadlet: Containers as Real systemd Services

Quadlet shipped in Podman 4.4 and has since become the recommended replacement for `podman generate systemd`, which is deprecated. You drop a `.container` file into a search path, run `systemctl daemon-reload`, and systemd's generator materialises a unit named after the file.

Search paths (rootful): `/etc/containers/systemd/`, `/usr/share/containers/systemd/`, `/run/containers/systemd/`.
Rootless: `~/.config/containers/systemd/` and `$XDG_RUNTIME_DIR/containers/systemd/`.

Here is the same database as above, as a Quadlet unit:

```ini
# ~/.config/containers/systemd/app-db.container
[Unit]
Description=Application PostgreSQL
Wants=network-online.target
After=network-online.target

[Container]
Image=docker.io/library/postgres:17-alpine
ContainerName=app-db
Environment=POSTGRES_PASSWORD=change-me
Environment=POSTGRES_DB=app
Volume=app-db-data.volume:/var/lib/postgresql/data:Z
PublishPort=127.0.0.1:5432:5432
HealthCmd=pg_isready -U postgres -d app
HealthInterval=10s
HealthRetries=10
AutoUpdate=registry

[Service]
Restart=always
TimeoutStartSec=300

[Install]
WantedBy=default.target
```

And the volume it references, plus the application unit that must start after it:

```ini
# ~/.config/containers/systemd/app-db-data.volume
[Volume]
VolumeName=app-db-data

# ~/.config/containers/systemd/app.container
[Unit]
Description=Application server
Wants=app-db.service
After=app-db.service
Requires=app-db.service

[Container]
Image=ghcr.io/example/app:1.8.2
ContainerName=app
Environment=DATABASE_URL=postgres://postgres:change-me@app-db:5432/app
PublishPort=8080:8080

[Service]
Restart=always

[Install]
WantedBy=default.target
```

Activate it:

```bash
# one-time, rootless: keep user services running after logout
loginctl enable-linger "$USER"

systemctl --user daemon-reload
systemctl --user start app-db.service app.service
systemctl --user status app.service
journalctl --user -u app.service -f --no-pager
```

Note what happened: `After=app-db.service` is ordinary systemd ordering, and `Requires=` makes the dependency explicit in both directions. That is the whole pitch — you are not learning a new orchestration model, you are using the one the operating system already has.

### Pods for multi-container groups

When several containers must share a network namespace (the classic "app + sidecar" pattern), Quadlet has a `.pod` unit, and members join it with `Pod=`:

```ini
# ~/.config/containers/systemd/web.pod
[Pod]
PodName=web
PublishPort=443:443
```

```ini
# ~/.config/containers/systemd/web-sidecar.container
[Container]
Image=docker.io/library/nginx:1.27-alpine
Pod=web.pod
```

For Kubernetes YAML you already have, a `.kube` unit runs it through `podman kube play` — useful when you want portable manifests without a cluster.

### Automatic image updates

`AutoUpdate=registry` plus the shipped timer replaces Watchtower:

```bash
systemctl --user enable --now podman-auto-update.timer
podman auto-update --dry-run    # see what would change before it changes
```

Pin digests for anything you do not want auto-bumped — `Image=ghcr.io/example/app@sha256:...` opts that unit out of the update logic.

## Migrating a Compose Stack to Quadlet

There is no one-shot converter worth trusting, but the mapping is mechanical:

| Compose | Quadlet |
|---|---|
| `image:` | `Image=` |
| `ports:` | `PublishPort=` |
| `volumes:` (named) | `.volume` unit + `Volume=name.volume:/path` |
| `volumes:` (bind, SELinux host) | `Volume=/host/path:/path:Z` |
| `environment:` | `Environment=` or `EnvironmentFile=` |
| `depends_on` + `condition` | `Requires=` + `After=` on the unit name |
| `healthcheck:` | `HealthCmd=` / `HealthInterval=` / `HealthRetries=` |
| `restart: unless-stopped` | `[Service] Restart=always` |
| `networks:` | `.network` unit + `Network=name.network` |

Practical order that works: start with the database and its volume, verify `systemctl --user status`, then the app, then the proxy. Keep the Compose file in the repository as the development entry point — nothing stops you running `podman compose up` locally and Quadlet in production from the same image tags.

## Pitfalls: What Actually Breaks

- **Forgetting `daemon-reload`.** Quadlet files are read by a systemd generator. Edit a unit and nothing changes until you run `systemctl --user daemon-reload`. This is the number-one "my change did nothing" cause.
- **Trying to `systemctl enable` a nonexistent unit.** Generated units do not appear in `systemctl list-unit-files` as normal units until reload; start them by name and let `[Install]` handle boot.
- **SELinux volume denials.** On Fedora/RHEL hosts, bind mounts need `:Z` (private label) or `:z` (shared). Without it the container starts and then cannot write — silently, in the app's own logs.
- **Rootless ports below 1024.** Either publish on a high port and put a rootful reverse proxy in front, or set `net.ipv4.ip_unprivileged_port_start=80` — a system-wide change worth understanding before you make it.
- **No `depends_on` semantics for readiness.** `After=` orders start attempts, not readiness. Use `HealthCmd` and let the app retry, or add an `ExecStartPre` check.
- **Losing user services on logout.** Without `loginctl enable-linger`, rootless units die with the session. This surprises people exactly once.
- **Auto-update without a rollback plan.** `AutoUpdate=registry` follows the tag. If `:latest` breaks, you find out at 3 a.m. Pin versions for anything stateful.

For the kernel-level details behind rootless container networking and UID mapping, see our [rootless container runtimes comparison](../2026-05-09-rootless-container-runtimes-docker-podman-containerd-guide/), and if you are deciding between application containers and full system containers, the [Incus vs LXD vs Podman guide](../2026-04-24-incus-vs-lxd-vs-podman-self-hosted-container-virtualization-guide-2026/) covers that boundary.

## FAQ

### Is Quadlet a replacement for Docker Compose?

No. Quadlet replaces the *supervisor* layer, not the application model. Compose describes a multi-service app in one file with profiles and overrides; Quadlet describes individual systemd-managed containers. Many teams run Compose in development and Quadlet in production, using identical image tags.

### Do I need Podman installed to use Quadlet?

Yes — Quadlet is a Podman feature, shipped since Podman 4.4 and read by a systemd generator that Podman installs. There is no Docker equivalent; Docker relies on its own daemon with `restart:` policies.

### Can Quadlet containers start before the network is up?

Add `Wants=network-online.target` and `After=network-online.target` to the `[Unit]` section. This is more reliable than Compose's behaviour, which depends on the Docker daemon's own ordering after boot.

### How do I see logs for a Quadlet container?

`journalctl --user -u <name>.service` for rootless units, `journalctl -u <name>.service` for rootful ones. Because output goes to journald you get rotation, rate limiting and `-f` following for free — no log driver configuration needed.

### Does Quadlet support automatic image updates?

Yes, through `AutoUpdate=registry` in the `[Container]` section plus `podman-auto-update.timer`. Unlike Watchtower it is part of Podman itself, and `podman auto-update --dry-run` lets you preview changes. Pin an image digest to exclude a unit from updates.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Podman Quadlet vs Docker Compose in 2026: Which Declarative Stack Should Run Your Server?",
  "description": "A practical comparison of Docker Compose and Podman Quadlet for single-host container deployments in 2026, including real unit files, a migration mapping, and rootless pitfalls.",
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
