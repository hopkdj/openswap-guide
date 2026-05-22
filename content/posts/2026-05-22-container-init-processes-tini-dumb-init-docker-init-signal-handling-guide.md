---
title: "Self-Hosted Container Init Processes: tini vs dumb-init vs docker-init for Signal Handling (2026)"
date: "2026-05-22"
tags: ["docker", "containers", "init-process", "signal-handling", "pid1", "process-management"]
draft: false
---

Every container runs with PID 1 as its first process. This init process has a critical responsibility that most developers overlook: **signal handling and zombie process reaping**. Using the wrong PID 1 process leads to containers that ignore shutdown signals, accumulate zombie processes, and refuse to stop gracefully. This guide compares three init process solutions: **tini**, **dumb-init**, and **docker-init**.

## The PID 1 Problem in Containers

In a standard Linux system, PID 1 (systemd, SysVinit, or OpenRC) handles two responsibilities that other processes do not:

1. **Signal forwarding**: When the kernel sends SIGTERM or SIGINT to PID 1, the default behavior is to **ignore** the signal. Only processes that explicitly install signal handlers will respond to shutdown signals.

2. **Zombie reaping**: When a child process exits, it becomes a zombie until its parent calls `wait()`. PID 1 is responsible for reaping zombies that become orphaned (when their original parent dies before waiting).

Most application processes (Node.js, Python, Java, etc.) are not designed to be PID 1. They don't install SIGTERM handlers and they don't reap orphaned children. Running them directly as PID 1 in a container causes:

- **Graceful shutdown failures**: `docker stop` sends SIGTERM to PID 1, which ignores it. After 10 seconds, Docker sends SIGKILL, terminating the process without cleanup.
- **Zombie accumulation**: If your application spawns child processes (workers, subprocesses) and they exit, they remain as zombies consuming PID table entries.
- **Unreliable health checks**: A container with a dead PID 1 but living child processes appears healthy to Docker's health check.

For related reading on container process management, see our [Supervisord vs s6-overlay vs Runit guide](../2026-04-25-supervisord-vs-s6-overlay-vs-runit-self-hosted-process-management/) and our [OCI Runtime Hooks guide](../2026-05-16-self-hosted-oci-runtime-hooks-umoci-seccomp-bpf-add-hooks-guide/). For container security hardening, check our [Container Security Hardening guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide/).

## tini

[tini](https://github.com/krallin/tini) is a tiny but valid init process for containers. It was created by Thomas Orozco and is now included by default in Docker as `docker-init`.

### How tini Works

tini runs as PID 1 and performs two functions:
1. **Signal forwarding**: Registers signal handlers for SIGTERM, SIGINT, SIGHUP, SIGQUIT, and forwards them to the child process.
2. **Zombie reaping**: Calls `waitpid()` in a loop to reap any zombie children.

### Docker Compose with tini

```yaml
version: "3.8"

services:
  webapp:
    image: node:20-alpine
    init: true  # Enables docker-init (tini) automatically
    command: ["node", "server.js"]
    ports:
      - "3000:3000"
    restart: unless-stopped
```

The `init: true` flag automatically injects tini as PID 1. Alternatively, install tini manually:

```dockerfile
FROM node:20-alpine

# Install tini
RUN apk add --no-cache tini

# Set tini as entrypoint
ENTRYPOINT ["tini", "--"]
CMD ["node", "server.js"]
```

### Custom Signal Handling

tini supports signal forwarding to process groups and custom subreaping:

```dockerfile
# Forward signals to all processes in the process group
ENTRYPOINT ["tini", "-g", "--"]
CMD ["sh", "-c", "node server.js & worker.js & wait"]

# Use tini as a subreaper (reap zombies from grandchildren)
ENTRYPOINT ["tini", "-s", "--"]
```

### Key Features

- **Minimal**: 23KB binary, zero dependencies
- **Signal forwarding**: Forwards all standard signals to child process
- **Zombie reaping**: Reaps all orphaned zombie children
- **Process group support**: `-g` flag forwards signals to entire process group
- **Subreaping**: `-s` flag acts as a subreaper for complex process trees
- **Docker default**: Built into Docker as `docker-init` via `--init` flag
- **Well-tested**: Used in millions of production containers

## dumb-init

[dumb-init](https://github.com/Yelp/dumb-init) is a simple init system written in C by Yelp. It is designed to be a drop-in replacement for any container entrypoint.

### How dumb-init Works

Like tini, dumb-init runs as PID 1, forwards signals, and reaps zombies. However, dumb-init has additional features for signal rewriting and session management.

### Docker Compose with dumb-init

```yaml
version: "3.8"

services:
  webapp:
    image: python:3.12-slim
    entrypoint: ["dumb-init", "--"]
    command: ["python", "-m", "flask", "run", "--host=0.0.0.0"]
    ports:
      - "5000:5000"
    restart: unless-stopped
```

### Dockerfile with dumb-init

```dockerfile
FROM python:3.12-slim

# Install dumb-init from Debian/Ubuntu repos
RUN apt-get update && apt-get install -y dumb-init && rm -rf /var/lib/apt/lists/*

# Rewrite SIGTERM to SIGQUIT for graceful shutdown (Java/Go apps)
ENTRYPOINT ["dumb-init", "--rewrite", "15:3", "--"]
CMD ["java", "-jar", "/app/myapp.jar"]
```

### Signal Rewriting

dumb-init's unique feature is signal rewriting, which maps incoming signals to different signals for the child process:

```bash
# Map SIGTERM (15) to SIGQUIT (3) for Java apps
dumb-init --rewrite 15:3 -- java -jar app.jar

# Map SIGINT (2) to SIGTERM (15) for apps that handle SIGTERM but not SIGINT
dumb-init --rewrite 2:15 -- myapp

# Multiple rewrites
dumb-init --rewrite 15:3 --rewrite 2:15 -- myapp
```

This is particularly useful for:
- **Java applications**: JVM handles SIGQUIT gracefully for shutdown hooks, but may ignore SIGTERM
- **Go applications**: Some Go apps handle SIGQUIT but not SIGTERM
- **Legacy applications**: Applications expecting specific signals that Docker doesn't send by default

### Key Features

- **Signal rewriting**: Map any signal to any other signal
- **Session leadership**: Can run as session leader for proper terminal behavior
- **Verbose mode**: `--verbose` flag for debugging signal flow
- **C implementation**: No runtime dependencies, compiled to static binary
- **Yelp-backed**: Developed and maintained by Yelp's infrastructure team
- **Strict mode**: `--strict` mode for debugging with enhanced signal handling

## docker-init (Built-in tini)

`docker-init` is Docker's built-in init process, which is essentially a packaged version of tini. It's activated via the `--init` flag or the `init: true` Compose option.

### Usage

```bash
# CLI usage
docker run --init -p 3000:3000 node:20-alpine node server.js

# Docker Compose
services:
  webapp:
    image: node:20-alpine
    init: true
    command: ["node", "server.js"]
```

### How It Differs from Manual tini

| Aspect | docker-init | Manual tini |
|--------|-------------|-------------|
| **Installation** | Built into Docker | Must install in image |
| **Version** | Fixed by Docker version | Choose specific version |
| **Configuration** | No custom flags | Full tini CLI options |
| **Image size** | No impact on image | Adds ~23KB to image |
| **Process group** | Default forwarding | `-g` for process group |

### Docker daemon.json Default Init

You can enable init by default for all containers:

```json
{
  "init": true,
  "init-path": "/usr/bin/docker-init"
}
```

This eliminates the need to specify `init: true` in every Compose file.

## Comparison Table

| Feature | tini | dumb-init | docker-init |
|---------|------|-----------|-------------|
| **Language** | C | C | C (tini fork) |
| **Binary Size** | 23KB | 15KB | 150KB |
| **Signal Forwarding** | Yes | Yes | Yes |
| **Zombie Reaping** | Yes | Yes | Yes |
| **Signal Rewriting** | No | Yes | No |
| **Process Group Mode** | Yes (`-g`) | Yes | No |
| **Subreaping** | Yes (`-s`) | No | No |
| **Docker Built-in** | Yes (as docker-init) | No | Yes |
| **Image Installation** | Required (if not using docker-init) | Required | Not required |
| **GitHub Stars** | 10,000+ | 5,000+ | N/A (Docker built-in) |
| **Best For** | General containers | Apps needing signal mapping | Simple Docker setups |

## When to Use Each Tool

### Use docker-init (tini) when:
- You're using Docker and want zero-configuration init
- Your application just needs basic signal forwarding and zombie reaping
- You don't want to modify your Dockerfile or add packages

### Use manual tini when:
- You need process group signal forwarding (`-g` flag)
- You're using Podman or containerd (not Docker)
- You need subreaping for complex process trees (`-s` flag)
- You want a specific version of tini regardless of Docker version

### Use dumb-init when:
- Your application needs signal rewriting (e.g., SIGTERM → SIGQUIT for Java)
- You need verbose debugging of signal flow
- You're running applications that have specific signal expectations
- You want the smallest possible init binary (15KB vs 23KB)

## Verification: Testing Signal Handling

Verify your init process handles signals correctly:

```bash
# Start a container with init
docker run --init -d --name test-signal node:20-alpine   sh -c 'trap "echo GOT_SIGTERM; exit 0" TERM; echo PID: $$; sleep 3600'

# Send SIGTERM and check response
docker stop --time=30 test-signal
docker logs test-signal
# Should show: "GOT_SIGTERM"

# Without init, the signal would be ignored and Docker would SIGKILL after 10s
```

For zombie reaping verification:

```bash
docker run --init -d --name test-zombie node:20-alpine   sh -c 'while true; do (sleep 1 &); sleep 2; done'

# Check for zombies inside the container
docker exec test-zombie ps aux
# Without init: zombie processes accumulate
# With init: no zombies visible
```

## FAQ

### Do I need an init process if my application handles SIGTERM?

If your application explicitly installs a SIGTERM handler and doesn't spawn child processes, you might not need an init. However, most applications don't handle SIGTERM by default, and even if they do, they won't reap orphaned zombies. Using an init process is a cheap insurance policy — it adds negligible overhead and prevents hard-to-debug shutdown issues.

### Does docker-init add overhead to my container?

No measurable overhead. docker-init (tini) is a tiny C program that does two things: forward signals and reap zombies. It uses minimal CPU and memory. The only impact is an additional process in your process tree (PID 1 instead of your application directly).

### Can I use tini with Podman?

Yes. Podman doesn't have a built-in init like Docker's `--init` flag, but you can install tini in your image and set it as the entrypoint: `ENTRYPOINT ["tini", "--"]`. Alternatively, Podman supports `--init` in newer versions using the same tini binary.

### Why does dumb-init rewrite SIGTERM to SIGQUIT for Java?

The JVM's shutdown hooks are triggered by SIGTERM, but some Java frameworks (particularly older ones) have custom signal handlers that respond better to SIGQUIT. Additionally, some application servers (like older Tomcat versions) use SIGQUIT for graceful shutdown. The `--rewrite 15:3` flag ensures the JVM receives the signal it expects for clean shutdown.

### What is zombie reaping and why does it matter?

When a process exits, it becomes a "zombie" — its process table entry remains until the parent calls `wait()`. If the parent exits without waiting, the zombie is reparented to PID 1, which must reap it. In containers without an init, orphaned zombies accumulate and consume PID table entries. On systems with limited PID space (default: 32768), enough zombies can prevent new processes from spawning.

### Can I use both tini and dumb-init?

No, and you shouldn't need to. Both serve the same purpose as PID 1 init processes. Using two init processes would create unnecessary nesting (init → init → app). Choose one based on your needs: docker-init for simplicity, tini for process group support, or dumb-init for signal rewriting.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Init Processes: tini vs dumb-init vs docker-init for Signal Handling (2026)",
  "description": "Compare container init processes for PID 1 signal handling and zombie reaping: tini, dumb-init, and docker-init.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
