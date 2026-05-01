---
title: "Self-Hosted Docker Cron Schedulers: Ofelia vs docker-crontab vs docker-cron Guide"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "docker", "cron", "scheduling", "automation"]
draft: false
---

If you run workloads in Docker containers, traditional cron jobs on the host OS won't cut it. You need a scheduler that understands Docker — one that can start, stop, and manage containerized tasks with proper logging, networking, and resource constraints.

While general-purpose job schedulers like Cronicle and Rundeck handle broad scheduling needs, Docker-native cron schedulers are purpose-built for container environments. This guide compares three lightweight Docker cron schedulers: **Ofelia**, **docker-crontab**, and **docker-cron**.

## Quick Comparison Table

| Feature | Ofelia | docker-crontab | docker-cron |
|---|---|---|---|
| GitHub Stars | ~3,824 | ~315 | ~100 |
| Runtime | Go binary | Shell wrapper | Alpine + cron |
| Configuration | Labels on containers | External crontab file | Internal crontab |
| Local Jobs | Yes (run inside scheduler) | No | Yes |
| Service Jobs | Yes (run inside target container) | No | No |
| Volume Jobs | Yes (run with specific volumes) | No | No |
| Web UI | No (CLI/daemon only) | No | No |
| Docker Socket | Required | Required | Not required |
| Last Updated | Active (2026) | Dormant (2023) | Active (2025) |
| License | MIT | MIT | MIT |
| Best For | Label-based job definitions | Simple cron-on-Docker | Lightweight standalone |

## Ofelia — The Label-Driven Scheduler

[Ofelia](https://github.com/mcuadros/ofelia) is a Docker-native job scheduler written in Go. Its standout feature is label-based configuration — you define cron jobs directly in Docker Compose labels on any container, and Ofelia picks them up automatically.

### Key Features

- **Label-based configuration**: Define jobs as Docker labels, no separate config files
- **Three job types**:
  - `local`: Run commands inside the Ofelia container
  - `service`: Run commands inside any running Docker container
  - `volume`: Run commands with specific Docker volumes mounted
- **Overlap prevention**: Skip new job executions if previous run is still active
- **Notifications**: Send job results via email or Slack
- **Execution history**: Track job runs, durations, and exit codes
- **No web UI needed**: Runs as a lightweight daemon with CLI inspection

### Docker Compose Configuration

The label-based approach means you define jobs on the containers that execute them:

```yaml
version: "3.8"

services:
  # The Ofelia scheduler daemon
  ofelia:
    image: mcuadros/ofelia:latest
    container_name: ofelia
    restart: always
    depends_on:
      - app-worker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

  # Application with scheduled backup job
  app-worker:
    image: myapp:latest
    container_name: app-worker
    labels:
      ofelia.enabled: "true"
      ofelia.job-exec.backup.schedule: "@every 6h"
      ofelia.job-exec.backup.command: "python /app/backup.py"
      ofelia.job-exec.backup.user: "app"
      ofelia.job-exec.backup.no-overlap: "true"

  # Database cleanup job
  db-cleanup:
    image: postgres:15-alpine
    container_name: app-db
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secure-password
    volumes:
      - db-data:/var/lib/postgresql/data
    labels:
      ofelia.job-exec.db-vacuum.schedule: "0 3 * * *"
      ofelia.job-exec.db-vacuum.command: "vacuumdb --analyze --full -U app -d myapp"
      ofelia.job-exec.db-vacuum.no-overlap: "true"

  # Local maintenance job (runs in Ofelia container)
  # Defined via config file mounted into Ofelia
  # ofelia.job-local.cleanup.schedule: "0 0 * * 0"
  # ofelia.job-local.cleanup.command: "curl -f http://app-worker:8080/health"

volumes:
  db-data:
```

### Configuration File Alternative

If you prefer a config file over labels, Ofelia also supports a TOML configuration:

```toml
[job-exec "app-backup"]
schedule = @every 6h
container = app-worker
command = python /app/backup.py
user = app
no-overlap = true

[job-exec "db-vacuum"]
schedule = 0 3 * * *
container = app-db
command = vacuumdb --analyze --full -U app -d myapp
no-overlap = true

[job-local "health-check"]
schedule = @every 5m
command = curl -sf http://app-worker:8080/health || exit 1
```

Run Ofelia with the config file:

```bash
docker run -d \
  --name ofelia \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v $(pwd)/ofelia.toml:/etc/ofelia/config.toml \
  mcuadros/ofelia:latest daemon
```

## docker-crontab — The Simple Wrapper

[docker-crontab](https://github.com/willfarrell/docker-crontab) is a minimal Docker image that runs cron inside a container, using a mounted crontab file to schedule commands. It's straightforward: mount your crontab, define commands, and let cron handle the rest.

### Key Features

- **Simple crontab syntax**: Uses standard cron format everyone knows
- **Lightweight**: Based on Alpine Linux, ~5MB image
- **Log rotation**: Built-in log management for scheduled jobs
- **Environment support**: Pass environment variables to cron jobs
- **No Docker socket needed**: Jobs run inside the container, not on the host

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  docker-crontab:
    image: willfarrell/crontab:latest
    container_name: docker-crontab
    restart: always
    volumes:
      - ./crontab:/etc/crontabs/root:ro
      - crontab-logs:/var/log/cron
    environment:
      - TZ=UTC
      - BACKUP_DIR=/backups

volumes:
  crontab-logs:
```

### Crontab File

Create a `crontab` file in the same directory:

```
# m h dom mon dow command
# Backup database every 6 hours
0 */6 * * * /usr/bin/pg_dump -h db -U app myapp > /backups/backup_$(date +\%Y\%m\%d_\%H\%M).sql

# Clean old backups daily at 2 AM
0 2 * * * find /backups -name "*.sql" -mtime +30 -delete

# Health check every 5 minutes
*/5 * * * * curl -sf http://app:8080/health || echo "Health check failed at $(date)"
```

## docker-cron — The Alpine-Based Standalone

[docker-cron](https://github.com/monlor/docker-cron) is a lightweight Alpine-based Docker image designed for running cron jobs with automatic log rotation. It's similar to docker-crontab but includes built-in support for startup commands and a cleaner logging setup.

### Key Features

- **Alpine-based**: Minimal image size, fast startup
- **Startup commands**: Run commands when the container starts
- **Log rotation**: Automatic log management with configurable rotation
- **Simple configuration**: Mount crontab file and go
- **Timezone support**: Set timezone via environment variable

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  docker-cron:
    image: monlor/docker-cron:latest
    container_name: docker-cron
    restart: always
    volumes:
      - ./crontab:/etc/crontabs/root:ro
      - cron-logs:/var/log
    environment:
      - TZ=Asia/Shanghai

volumes:
  cron-logs:
```

### Crontab Example

```
# Database backup every 6 hours
0 */6 * * * docker exec app-db pg_dump -U app myapp > /backups/myapp_$(date +\%Y\%m\%d).sql 2>&1

# Application restart weekly
0 4 * * 0 docker restart app-worker

# Log rotation daily
0 0 * * * find /var/log -name "*.log" -mtime +7 -delete
```

## Choosing the Right Docker Cron Scheduler

### Use Ofelia When:
- You want label-based job definitions integrated into Docker Compose
- You need to run jobs inside other containers (service jobs)
- You want overlap prevention and execution tracking
- You manage multiple containers with different scheduled tasks

### Use docker-crontab When:
- You prefer standard crontab syntax and file-based configuration
- You need a simple, lightweight cron-in-Docker solution
- Your scheduled tasks run inside the cron container itself
- You want minimal dependencies and a tiny image footprint

### Use docker-cron When:
- You need startup commands in addition to cron jobs
- You want built-in log rotation and timezone support
- You prefer Alpine-based images for security and size
- Your cron jobs are straightforward and don't need container introspection

## Why Use Docker-Native Cron Schedulers?

Traditional host-level cron can't see inside Docker containers, making it awkward to schedule container-specific tasks. Docker-native schedulers like Ofelia solve this by either monitoring the Docker socket (to execute commands inside containers) or running as containers themselves with proper volume and network access.

For broader task orchestration beyond simple cron scheduling, see our [workflow orchestration guide](../dagu-vs-netflix-conductor-vs-airflow-self-hosted-workflow-orchestration-guide-2026/). If you need distributed task scheduling across multiple servers, our [distributed task scheduling comparison](../2026-04-29-xxl-job-vs-powerjob-vs-dolphinscheduler-distributed-task-scheduling-guide-2026/) covers enterprise-grade solutions. For automation workflows that trigger on events rather than schedules, check our [workflow automation guide](../automatisch-vs-n8n-vs-activepieces-self-hosted-workflow-automation-2026/).

## FAQ

### What is the difference between Ofelia and traditional cron?

Traditional cron runs on the host OS and executes commands in the host environment. Ofelia runs inside a Docker container and uses the Docker API to execute commands inside other containers, on specific volumes, or locally within the Ofelia container. This means Ofelia can run backup commands inside a database container, health checks inside an app container, or cleanup commands with specific volume mounts — all without SSH access to the host.

### Do I need to mount the Docker socket for Ofelia?

Yes, for `job-exec` and `job-volume` types, Ofelia needs read access to `/var/run/docker.sock` to communicate with the Docker daemon. This allows it to list containers, execute commands inside them, and mount volumes. If you only use `job-local` type, you don't need the socket, but most users rely on service jobs for their Docker scheduling needs.

### Can I use these schedulers with Docker Swarm or Kubernetes?

Ofelia works with Docker Swarm since it uses the standard Docker API. For Kubernetes, you'd typically use Kubernetes-native CronJob resources instead. docker-crontab and docker-cron are single-node solutions that work on any Docker host but don't have built-in cluster awareness.

### How do I monitor scheduled job execution?

Ofelia tracks job execution history internally — you can inspect the Ofelia container logs to see job runs, durations, and exit codes. docker-crontab and docker-cron log to standard container logs, which you can view with `docker logs docker-crontab`. For production monitoring, pipe these logs into your centralized logging system (e.g., Loki, Graylog, or Elasticsearch).

### Is it safe to mount the Docker socket into a container?

Mounting `/var/run/docker.sock` gives the container full control over the Docker daemon — effectively root access to the host. This is necessary for Ofelia's operation but is a security consideration. Mitigate risk by: running Ofelia with a non-root user inside the container, using Docker socket proxies (like `tecnativa/docker-socket-proxy`) to limit API access, and ensuring Ofelia's configuration doesn't expose sensitive data.

### Can I schedule Docker Compose operations with these tools?

Yes, but indirectly. You can't run `docker-compose up/down` inside a container without Docker Compose installed. Instead, use `docker start/stop` commands for individual containers, or install Docker Compose inside the Ofelia/docker-cron container for compose-level operations. For complex deployment scheduling, consider dedicated CI/CD tools instead.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Docker Cron Schedulers: Ofelia vs docker-crontab vs docker-cron Guide",
  "description": "Compare Docker-native cron schedulers — Ofelia, docker-crontab, and docker-cron — with compose configs, label-based scheduling, and container job execution.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
