---
title: "wait-for-it vs dockerize vs wait4x in 2026: Stop Using sleep 10 in Your Entrypoint"
date: "2026-11-11"
tags: ["docker", "container-orchestration", "devops", "self-hosted", "wait-strategies"]
draft: false
cover: "/img/screenshots/wait4x-logo.jpg"
description: "A hands-on comparison of wait-for-it, dockerize, and wait4x for container startup ordering — with real configs, protocol support, and the failure modes that break production deploys."
---

Your API container booted in 400ms. Your Postgres container took nine seconds to accept connections. The `sleep 10` in your entrypoint worked for eleven months — until the day the database had to replay a WAL segment and recovery took 14 seconds. The container crash-looped, the orchestrator marked the service unhealthy, and your deploy failed at 2am for a reason that had nothing to do with the code you shipped.

That is the entire argument against fixed sleeps: they encode a guess about someone else's boot time. This article compares the three tools teams actually reach for — **wait-for-it**, **dockerize**, and **wait4x** — using live repository data, their real command syntax, and the specific situation where each one wins.

## TL;DR: Which One Should You Use?

**If you write Docker Compose files and nothing else, use the native `depends_on` + `healthcheck` pair — it needs zero extra binaries.** If you need a wait tool in a container image, choose **wait4x** for new projects (20+ protocols, exponential backoff, actively releasing, Apache-2.0). Choose **dockerize** if you also need config templating from environment variables in the same binary. Choose **wait-for-it** only if you are maintaining an existing image that already depends on it — its last commit was June 2024 and it only speaks TCP.

| | wait-for-it | dockerize | wait4x |
|---|---|---|---|
| **Stars** | 9,765 | 5,205 | 1,382 |
| **Last push** | 2024-06-10 | 2026-10-21 | 2026-11-10 |
| **License** | MIT | MIT | Apache-2.0 |
| **Language** | Bash | Go | Go |
| **Image size impact** | ~0 (copy the script) | ~20 MB static binary | ~15 MB static binary |
| **Protocol coverage** | TCP only | TCP, HTTP(S), file, unix socket | TCP, HTTP(S), DNS, PostgreSQL, MySQL, MariaDB, Redis, MongoDB, RabbitMQ, Kafka, InfluxDB, SMTP, SSH, shell command, and more |
| **Auth-aware checks** | No | HTTP headers | DB credentials, Redis AUTH, full URIs |
| **Retry control** | Timeout + interval flags | `-timeout`, `-wait-retry-interval` | Timeout, backoff, exponential backoff, invert-check |
| **Extra features** | None | Go template rendering of config files | Run command after wait, parallel checks, reverse checks |
| **Maintenance signal** | Dormant | Active | Very active |

## Decision Matrix: Match the Tool to the Job

| Your situation | Pick | Why |
|---|---|---|
| Compose-only stack, no custom entrypoint | **Native healthcheck** | No third binary to audit or pin; the condition is expressed in the same file as the services |
| Image must stay tiny (distroless, Alpine, scratch) | **wait-for-it** (vendored) | A single bash script; but it only checks that a port is open |
| You also template nginx.conf / app.conf from env vars | **dockerize** | One binary does both wait and template, so you avoid adding a second tool |
| Waiting on Postgres/MySQL/Redis/Kafka readiness, not just a port | **wait4x** | It actually authenticates and runs a query; an open port is not a ready database |
| Kubernetes deployment | **None of the three** | Use readiness/liveness probes and init containers; startup ordering is the scheduler's job |
| CI job that must block on a service container | **wait4x** | Parallel checks and JSON-friendly exit codes make CI scripts shorter |

## Why `sleep 10` Is a Latent Outage

A port being open is not the same as a service being ready. Postgres binds its socket before it finishes crash recovery. MySQL listens while it is still replaying the redo log. Redis answers `PING` before it finishes loading an RDB file — and if you write during that window, you can lose data when the load completes and the dataset is swapped in.

There are three escalating levels of correctness:

1. **Fixed sleep** — guesses at boot time. Breaks on slow disks, cold caches, larger datasets, and noisy neighbours.
2. **Port check** — better, but still a lie for stateful services that bind early.
3. **Protocol-level readiness** — authenticate, run a trivial query, check the expected status code or body. This is the only level that survives real recovery scenarios.

The tools below sit at levels 2 and 3, plus the Compose-native mechanism that the Docker ecosystem added precisely because everyone was shipping `sleep` scripts.

## wait-for-it: The Ubiquitous Bash Script

`vishnubob/wait-for-it` (9,765 stars, MIT) is the tool most people copy into a Dockerfile first. It is a pure bash script — no binary, no architecture concerns, no glibc version issues. That portability is exactly why it spread.

```dockerfile
FROM alpine:3.20
RUN apk add --no-cache bash postgresql-client
COPY wait-for-it.sh /usr/local/bin/wait-for-it.sh
RUN chmod +x /usr/local/bin/wait-for-it.sh

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/usr/bin/env bash
set -euo pipefail

/usr/local/bin/wait-for-it.sh db:5432 --timeout=30 --strict -- \
  echo "postgres is accepting connections"
```

The `--strict` flag matters: without it, wait-for-it exits 0 even when the timeout expires, so a failed dependency silently produces a broken container. `--` separates the wait from the command it should run afterwards.

**The trade-off:** it checks `tcp://db:5432` and nothing more. A Postgres instance in recovery accepts TCP connections but rejects queries, so `--strict` passes and your app fails on the first `SELECT`. Its last commit was **2024-06-10**, and the README has not gained new capability in years. It is fine as legacy glue; it is not the tool to adopt in a new image in 2026.

## dockerize: Wait Plus Config Templating

`jwilder/dockerize` (5,205 stars, MIT, last push 2026-10-21) is a Go binary that does two jobs: wait for dependencies, and render Go templates from environment variables. The second job is why it still gets installed — teams that need `nginx.conf` or an app config generated at boot can do it without adding `envsubst`, `gomplate`, or a custom entrypoint script.

Its `-wait` flag accepts explicit URL schemes, and it rejects malformed values at startup instead of silently waiting forever:

```bash
# TCP, HTTP with an auth header, and a generated file
dockerize \
  -wait tcp://db:5432 \
  -wait http://web:80/health \
  -wait file:///tmp/generated-file \
  -timeout 30s \
  -wait-retry-interval 2s \
  ./start-server
```

The accepted forms are `tcp://host:port`, `http(s)://host[:port][/path]`, `file:///abs/path`, and `unix:///abs/path`. Relative file paths are rejected — `file://rel/path` fails because `rel` would be parsed as a hostname, which is a helpful failure rather than a mysterious hang.

A realistic Compose integration for an app that waits on both a database and a reverse proxy:

```yaml
services:
  app:
    image: ghcr.io/example/app:1.4.0
    entrypoint: ["/usr/local/bin/dockerize"]
    command:
      - "-wait"
      - "tcp://db:5432"
      - "-wait"
      - "http://proxy:80/health"
      - "-timeout"
      - "60s"
      - "/app/server"
    depends_on:
      - db
      - proxy
```

Where dockerize falls short is depth of the readiness check. The HTTP wait can assert a header or a status, but there is no native Postgres/Redis/Kafka handshake — for those you are back to "port is open", which is the exact false positive we started with.

## wait4x: Protocol-Aware Readiness

`wait4x/wait4x` (1,382 stars, Apache-2.0, last push 2026-11-10) treats readiness as a protocol problem rather than a socket problem. It ships subcommands per service type and, critically, verifies the service can actually answer.

```bash
# TCP port
wait4x tcp localhost:3306

# HTTP with status code and body assertion
wait4x http https://api.example.com/health \
  --expect-status-code 200 \
  --expect-body-regex '"status":"UP"'

# Real Postgres handshake over a URI
wait4x postgresql 'postgres://user:pass@localhost:5432/mydb?sslmode=disable'

# Redis with a key assertion
wait4x redis redis://localhost:6379 --expect-key "session:active"

# Parallel checks across three services
wait4x tcp 127.0.0.1:5432 127.0.0.1:6379 127.0.0.1:27017
```

Two flags change how it behaves in practice. `-- ./start-app.sh` runs a command once the check passes, which means you can use wait4x directly as an entrypoint without a wrapper script. `--invert-check` waits for a port to become *free* — the pattern you need when a container must not start until the previous process has fully released its socket.

In Compose, that replaces a whole entrypoint script:

```yaml
services:
  worker:
    image: ghcr.io/example/worker:2.1.0
    entrypoint: ["/usr/local/bin/wait4x"]
    command:
      - "postgresql"
      - "postgres://app:secret@db:5432/appdb?sslmode=disable"
      - "--timeout"
      - "90s"
      - "--"
      - "/app/worker"
    depends_on:
      - db
```

It also supports DNS checks and shell-command checks, which covers the awkward cases — waiting on a migration container to finish, or on a DNS record to resolve inside a private network. The cost is a smaller community than wait-for-it: 1,382 stars means fewer Stack Overflow answers when something behaves unexpectedly.

## The Approach Most Teams Should Actually Use

If your services are defined in Compose, you do not need any of the three binaries. Compose can gate startup on a healthcheck, and the healthcheck is where you express real readiness:

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d postgres"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s

  api:
    image: ghcr.io/example/api:3.2.1
    depends_on:
      db:
        condition: service_healthy
```

`condition: service_healthy` blocks the API container until the healthcheck passes, and `start_period` gives slow starters room to recover without being counted as failures. This is declarative, visible in the same file as the service definition, and requires no extra binary in the image.

The limitation is scope: this only works inside Compose. The moment the same container runs under Kubernetes, systemd units, or a bare `docker run`, the healthcheck condition disappears and you are back to needing an in-container wait — or better, a readiness probe.

## Pitfalls That Bite in Production

**Waiting in the wrong layer.** If the orchestrator can restart your container, waiting is not a fix — it is a delay. Kubernetes will restart a crashing pod anyway; use a readiness probe so traffic is withheld instead.

**No upper bound on the wait.** A wait tool without `--timeout` will hang until the orchestrator's own timeout fires, which produces a confusing error far from the real cause. Always set an explicit timeout shorter than the platform's kill window.

**Checking the port instead of the protocol.** `nc -z db 5432` succeeds during Postgres crash recovery. If your app's first action is a schema migration, that success is meaningless. Use `pg_isready` or a protocol-aware check.

**Forgetting `--strict` in wait-for-it.** The default exits 0 on timeout, so a broken dependency yields a "healthy" container that fails later. This single flag has caused more confusing incidents than any other detail in this article.

**Waiting on a dependency that will never come up.** If the database container failed to start due to a bad volume permission, your app will wait for the full timeout and then fail with a message about the app, not the database. Check dependency health in CI before deploying.

**Templating secrets with dockerize.** `dockerize -template` renders into the container filesystem. If that path is a mounted volume, you have just written credentials to the host. Render to `tmpfs` or keep templating out of the image entirely.

**Ignoring boot-time variance.** A wait loop that succeeds in 800ms locally and takes 40s on a cold production node is not a bug in the wait tool — it is a signal that the dependency needs `start_period` tuning, or that the data volume is too large to recover quickly.

## FAQ

### Is wait-for-it still maintained in 2026?

Effectively no. The last push to `vishnubob/wait-for-it` was **2024-06-10**, and the project has not added new protocol support in years. It still works as a TCP port check, so vendoring it into an existing image is reasonable, but new projects should use a maintained tool or Compose healthchecks.

### Can I use `depends_on` alone without a healthcheck?

No. Plain `depends_on` only controls start *order*, not readiness — Compose starts the dependency container first and immediately moves on. You need `condition: service_healthy` plus a `healthcheck` block for the ordering to mean anything.

### What is the difference between readiness and liveness?

Readiness answers "should this container receive traffic?" and a failing readiness probe removes it from the load balancer without restarting it. Liveness answers "is this container broken beyond recovery?" and a failing liveness probe restarts it. Startup ordering is a readiness concern; using a liveness probe for it causes restart loops during slow boots.

### Does wait4x work inside Kubernetes init containers?

Yes, and it is a common pattern when a pod must wait for an external database that is not part of the same release. However, for in-cluster dependencies, a readiness probe or an init container with a simple `until pg_isready; do sleep 1; done` loop is usually simpler and adds no third-party binary.

### How much does a wait binary cost in image size?

`dockerize` and `wait4x` are Go static binaries in the 15-20 MB range. On Alpine that can double a small image. `wait-for-it` is a few kilobytes of bash but requires a bash interpreter, which distroless images do not have — a common reason teams ship a wait tool as a multi-stage copy and then discover `exec format error`.

For related reading on managing these stacks day to day, see our comparison of [Docker Compose management UIs](../2026-05-14-portainer-compose-vs-dockge-vs-coolify-docker-compose-management-ui/), the guide to [dev containers vs Docker Compose for reproducible environments](../2026-11-08-dev-containers-vs-docker-compose-reproducible-environments/), and the breakdown of [Podman Quadlet vs Docker Compose for systemd-managed containers](../2026-11-08-podman-quadlet-vs-docker-compose-systemd-containers/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "wait-for-it vs dockerize vs wait4x in 2026: Stop Using sleep 10 in Your Entrypoint",
  "description": "Hands-on comparison of wait-for-it, dockerize, and wait4x for container startup ordering, with real configs, protocol support, and production failure modes.",
  "datePublished": "2026-11-11",
  "dateModified": "2026-11-11",
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
