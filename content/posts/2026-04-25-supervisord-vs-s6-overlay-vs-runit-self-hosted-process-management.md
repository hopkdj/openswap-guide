---
title: "Supervisord vs s6-overlay vs Runit: Best Process Manager 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "docker", "containers"]
draft: false
description: "Compare Supervisord, s6-overlay, and Runit for self-hosted process management. Complete guide with Docker configurations, setup instructions, and performance benchmarks."
---

When running multiple services inside a single container or managing background daemons on a self-hosted server, you need a reliable process supervisor. Without one, orphaned processes accumulate, crashed services stay dead, and logs mix together into an unreadable mess.

This guide compares three battle-tested process management tools: **Supervisord**, **s6-overlay**, and **Runit** — evaluating them for container deployments, self-hosted infrastructure, and production reliability.

## Why Self-Hosted Process Management Matters

A process supervisor is the first process (PID 1) inside a container or on a server. It handles:

- **Zombie process reaping** — collects exit statuses of child processes so the kernel doesn't accumulate zombie entries
- **Service restarts** — automatically restarts crashed daemons without manual intervention
- **Log separation** — captures stdout/stderr per-service instead of mixing everything into one stream
- **Graceful shutdown** — sends proper signals (SIGTERM, then SIGKILL) to all children on stop
- **Dependency ordering** — starts services in the correct sequence (database before web app)

Docker's default PID 1 behavior is notoriously bad at signal handling and zombie reaping. If your container runs a shell script that starts two services, only the shell gets signals — the children are orphaned. A proper process supervisor fixes this.

## Tool Overview

### Supervisord

[Supervisord](https://github.com/Supervisor/supervisor) is the most widely known process manager in the Python ecosystem. With **9,036 GitHub stars** and adoption across thousands of Docker images, it uses a simple INI-style configuration format and includes a web UI for monitoring. It was last updated in December 2025 and runs on Python 3.

Supervisord excels at straightforward service management where you need a quick, readable configuration and optional HTTP-based control interface. It is commonly included in Python-based Docker images and is the default choice in many legacy Dockerfiles.

### s6-overlay

[s6-overlay](https://github.com/just-containers/s6-overlay) (4,447 stars) is a container-specific process supervision suite built on the [s6](https://skarnet.org/software/s6/) toolset by Laurent Bercot. Written primarily in C with shell scripting glue, it was actively updated as recently as February 2026.

s6-overlay is the engine behind the popular [LinuxServer.io](https://www.linuxserver.io/) Docker images, which serve millions of self-hosted users. It uses a directory-based configuration approach where each service gets its own folder containing `run`, `finish`, and optional `check` scripts. This design makes it highly flexible for complex multi-service containers.

### Runit

[Runit](https://github.com/void-linux/runit) (272 stars) is a minimal, Unix-compatible init scheme and service supervisor. Written in C, it is the default init system for Void Linux. While its GitHub repository sees infrequent updates (last commit March 2024), Runit itself is extremely stable — the codebase is mature and changes rarely because it works correctly.

Runit uses a `service/` directory with executable `run` scripts, similar in concept to s6 but with a simpler, more bare-bones design. It has no built-in web UI, no INI config files — just shell scripts and symlinks. This simplicity is both its greatest strength and limitation.

## Feature Comparison

| Feature | Supervisord | s6-overlay | Runit |
|---------|-------------|------------|-------|
| **Language** | Python | C + Shell | C |
| **GitHub Stars** | 9,036 | 4,447 | 272 |
| **Last Updated** | Dec 2025 | Feb 2026 | Mar 2024 |
| **Configuration** | INI files | Directory-based scripts | Directory-based scripts |
| **Web UI** | Yes (built-in) | No | No |
| **Container-Optimized** | No (general-purpose) | Yes (designed for Docker) | No (general init) |
| **Zombie Reaping** | Yes | Yes | Yes |
| **Signal Forwarding** | Partial | Full | Full |
| **Dependency Ordering** | Yes (`depends_on`) | Yes (`dependencies.d/`) | Manual (order in `run`) |
| **Log Management** | Per-service log files | s6-log pipelines | s6-log or manual |
| **Health Checks** | Via external scripts | Built-in (`check` script) | Via external scripts |
| **Package Install** | `pip install supervisor` | Docker image layers | `apt install runit` |
| **Overhead** | Moderate (Python runtime) | Minimal | Minimal |
| **Learning Curve** | Low | Medium | Medium |

## Installation and Configuration

### Supervisord

Install via pip:

```bash
pip install supervisor
```

Generate a default config file:

```bash
echo_supervisord_conf > /etc/supervisord.conf
```

A typical `supervisord.conf` for managing two services (e.g., a web app and a worker):

```ini
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0
loglevel=info

[program:webapp]
command=gunicorn app:app --bind 0.0.0.0:8000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:worker]
command=celery -A app worker --loglevel=info
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[inet_http_server]
port=0.0.0.0:9001
username=admin
password=your-secure-password
```

Docker Compose example running Supervisord as PID 1:

```yaml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
      - "9001:9001"
    volumes:
      - ./supervisord.conf:/etc/supervisord.conf:ro
    command: ["/usr/local/bin/supervisord", "-c", "/etc/supervisord.conf"]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "supervisorctl", "status"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### s6-overlay

s6-overlay is not installed via a package manager — it is layered into Docker images. Here is a complete Dockerfile example:

```dockerfile
FROM alpine:3.19

# Install s6-overlay (check latest version on GitHub releases)
ARG S6_VERSION="v3.2.0.2"
ADD https://github.com/just-containers/s6-overlay/releases/download/${S6_VERSION}/s6-overlay-noarch.tar.xz /tmp/
ADD https://github.com/just-containers/s6-overlay/releases/download/${S6_VERSION}/s6-overlay-x86_64.tar.xz /tmp/
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
    tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz && \
    rm /tmp/*.tar.xz

# Create service directories
RUN mkdir -p /etc/s6-overlay/s6-rc.d/{myapp,myworker}/contents.d \
             /etc/s6-overlay/s6-rc.d/{myapp,myworker}/dependencies.d \
             /etc/s6-overlay/s6-services/myapp \
             /etc/s6-overlay/s6-services/myworker

# Web application service
RUN echo '#!/usr/bin/execlineb' > /etc/s6-overlay/s6-rc.d/myapp/run && \
    echo 'exec gunicorn app:app --bind 0.0.0.0:8000' >> /etc/s6-overlay/s6-rc.d/myapp/run && \
    chmod +x /etc/s6-overlay/s6-rc.d/myapp/run && \
    echo 'myapp' > /etc/s6-overlay/s6-rc.d/myapp/type

# Worker service (depends on myapp)
RUN echo '#!/usr/bin/execlineb' > /etc/s6-overlay/s6-rc.d/myworker/run && \
    echo 'exec celery -A app worker --loglevel=info' >> /etc/s6-overlay/s6-rc.d/myworker/run && \
    chmod +x /etc/s6-overlay/s6-rc.d/myworker/run && \
    echo 'myworker' > /etc/s6-overlay/s6-rc.d/myworker/type

ENTRYPOINT ["/init"]
```

Docker Compose example:

```yaml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    restart: unless-stopped
    # s6-overlay handles all process supervision internally
    # No extra command needed — /init is the ENTRYPOINT
```

### Runit

Install on Debian/Ubuntu:

```bash
apt-get update && apt-get install -y runit runit-init
```

Create a service definition for a web application:

```bash
# Create the service directory
mkdir -p /etc/sv/webapp

# Create the run script
cat > /etc/sv/webapp/run << 'RUNEOF'
#!/bin/sh
exec 2>&1
cd /app
exec gunicorn app:app --bind 0.0.0.0:8000
RUNEOF

chmod +x /etc/sv/webapp/run
```

Create a log service:

```bash
mkdir -p /etc/sv/webapp/log

cat > /etc/sv/webapp/log/run << 'RUNEOF'
#!/bin/sh
exec svlogd -tt /var/log/webapp
RUNEOF

chmod +x /etc/sv/webapp/log/run
mkdir -p /var/log/webapp
```

Enable and start the service:

```bash
# Create symlink to activate
ln -s /etc/sv/webapp /etc/service/webapp

# Check status
sv status /etc/service/webapp

# Restart
sv restart /etc/service/webapp
```

Docker Compose with Runit as PID 1:

```yaml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./services:/etc/sv:ro
    command: ["runsvdir", "-P", "/etc/service"]
    restart: unless-stopped
```

Where `services/webapp/run` contains the same script shown above.

## Performance and Resource Usage

Process supervisor overhead matters most in resource-constrained containers and edge deployments:

| Metric | Supervisord | s6-overlay | Runit |
|--------|-------------|------------|-------|
| **Memory (RSS)** | ~25-40 MB (Python runtime) | ~2-5 MB | ~1-3 MB |
| **Startup Time** | 0.5-1.0s | 0.1-0.3s | 0.1-0.2s |
| **Binary Size** | N/A (Python package) | ~4 MB (overlay tarball) | ~200 KB (installed) |
| **PID 1 Correctness** | Partial (needs `exec`) | Full (designed for PID 1) | Full (init system) |
| **Signal Handling** | Partial (SIGTERM only) | Full (all POSIX signals) | Full (all POSIX signals) |

Supervisord's Python runtime adds noticeable memory overhead, which matters when running many small containers on a single host. s6-overlay and Runit, both written in C, consume negligible resources.

For PID 1 correctness — the critical job of signal forwarding and zombie reaping — s6-overlay and Runit are architecturally superior. Supervisord requires careful `exec` wrapper usage to avoid becoming a zombie factory itself.

## When to Choose Each Tool

### Choose Supervisord When

- You are managing processes on a **traditional server** (not containers)
- You want a **web UI** for monitoring and controlling services remotely
- Your team is already **familiar with INI-style configs**
- You need **RPC/API access** to manage services programmatically
- Memory overhead is not a concern (full VMs, not tight containers)

Supervisord remains the go-to choice for VPS-based deployments where you want to manage multiple daemons with a simple configuration file and optional HTTP monitoring dashboard.

### Choose s6-overlay When

- You are building **Docker containers** with multiple services
- You want **LinuxServer.io compatibility** (their entire catalog uses s6)
- You need **built-in health checks** per service
- You want **fine-grained lifecycle control** (prepare, run, finish phases)
- You need **dependency ordering** between services in the same container

s6-overlay is the best choice for containerized multi-service deployments. Its directory-based service definitions and execline scripting provide maximum flexibility with minimal overhead.

### Choose Runit When

- You want the **simplest possible** process supervisor
- You are running on **Void Linux** or similar minimal distributions
- You prefer **shell scripts over INI configs** or complex toolchains
- You need an **init system**, not just a process supervisor
- You value **extreme stability** and proven correctness over features

Runit is the minimalist's choice. It does one thing — supervise processes — and does it with near-perfect reliability. If you do not need a web UI, RPC, or complex dependency graphs, Runit's simplicity is an advantage.

## Security Considerations

All three tools run as root by default (required for PID 1). However, they differ in how they handle privilege separation:

- **Supervisord**: Can drop privileges per-program using `user=` directive. The web UI should always be behind a reverse proxy with TLS.
- **s6-overlay**: Supports `s6-setuidgid` for per-service privilege dropping. Services can run as unprivileged users while the supervisor stays as root.
- **Runit**: Requires manual privilege dropping in the `run` script (e.g., `exec chpst -u nobody your-command`). No built-in web UI reduces attack surface.

For container deployments, running the entire container as a non-root user (via Docker's `USER` directive) is ideal. s6-overlay supports this pattern natively, while Supervisord and Runit require additional configuration.

## Migration Tips

Moving from Supervisord to s6-overlay in a Docker image:

1. Remove `supervisor` from `requirements.txt` or `apt install`
2. Replace `supervisord.conf` with s6 service directories under `/etc/s6-overlay/s6-rc.d/`
3. Convert each `[program:X]` section to a `run` script in the corresponding s6 service directory
4. Change the `CMD` from `supervisord -c /etc/supervisord.conf` to `ENTRYPOINT ["/init"]`
5. Test that all services start and restart correctly

The main gotcha is that s6-overlay uses [execline](https://skarnet.org/software/execline/) by default, which has different syntax from shell scripts. However, you can use `#!/bin/sh -e` in your `run` scripts if you prefer standard shell syntax.

For related reading, see our [container runtime comparison](../containerd-vs-cri-o-vs-podman-self-hosted-container-runtimes-guide-2026/) for how process supervisors fit into the broader container architecture, and our [container management dashboards guide](../self-hosted-container-management-dashboards-portainer-dockge-yacht-guide/) for tools that complement process supervision at the orchestration level. If you are also exploring container image building, our [container build tools comparison](../buildah-vs-kaniko-vs-earthly-self-hosted-container-build-tools-guide-2026/) covers how to include process supervisors in your custom images.

## FAQ

### What is PID 1 and why does it matter in Docker containers?

PID 1 is the first process started in any Unix system. In Docker, it receives all signals sent to the container and is responsible for reaping zombie processes. If PID 1 does not handle signals correctly, `docker stop` will wait 10 seconds and then send SIGKILL — causing data loss. A proper process supervisor (s6-overlay, Runit) handles signal forwarding and zombie reaping automatically.

### Can I use Supervisord inside a Docker container?

Yes, Supervisord works inside Docker containers, but it is not designed specifically for containers. You need to ensure that Supervisord itself runs with `nodaemon=true` and that child processes are launched with `exec` to ensure proper signal handling. For new container projects, s6-overlay is the better choice because it is purpose-built for the container environment.

### Does s6-overlay work with non-Docker container runtimes?

Yes. s6-overlay works with any OCI-compatible container runtime, including Podman, containerd, CRI-O, and LXC. It does not depend on Docker specifically. The overlay is just a set of binaries and scripts layered into the filesystem, with `/init` as the entrypoint.

### Is Runit suitable for managing services on a production server?

Yes, Runit is widely used in production. It is the default init system for Void Linux and has been deployed on thousands of servers for over a decade. Its simplicity is a feature — fewer lines of code means fewer bugs. However, if you need a web UI or programmatic API for service management, Supervisord or a dedicated orchestrator may be a better fit.

### How do I monitor services managed by these process supervisors?

Supervisord provides a built-in web UI (on port 9001 by default) and an XML-RPC API. s6-overlay includes `s6-svstat` and `s6-printf` commands for status checking, which you can integrate with Prometheus exporters or shell-based monitoring scripts. Runit provides `sv status` commands. For all three, you can also use external monitoring tools that check HTTP health endpoints or process existence.

### Can I run these supervisors alongside systemd?

On traditional Linux servers, systemd is typically PID 1. Supervisord, s6-overlay, and Runit can all run as subordinate service managers under systemd — systemd starts the supervisor, and the supervisor manages its child processes. In containers, however, the process supervisor replaces systemd as PID 1, since systemd is not designed to run inside containers (though `systemd-nspawn` and container-systemd variants exist).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Supervisord vs s6-overlay vs Runit: Best Process Manager 2026",
  "description": "Compare Supervisord, s6-overlay, and Runit for self-hosted process management. Complete guide with Docker configurations, setup instructions, and performance benchmarks.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
