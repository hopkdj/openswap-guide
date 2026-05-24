---
title: "Self-Hosted Linux Init Systems: OpenRC vs s6 vs runit for Server Management (2026)"
date: "2026-05-25"
tags: ["linux", "init-system", "systemd", "self-hosted", "comparison", "guide"]
draft: false
description: "Compare OpenRC, s6, and runit as alternatives to systemd for self-hosted Linux servers. Service management, dependency handling, and deployment guides."
---

The init system is the first process started by the Linux kernel (PID 1) and is responsible for booting the system, starting services, and handling shutdown. While systemd dominates the Linux server landscape, many administrators prefer alternative init systems for their simplicity, transparency, and smaller attack surface.

This guide compares three mature init systems for self-hosted servers: **OpenRC** (the Gentoo and Alpine Linux default), **s6** (the modern supervision suite from skarnet), and **runit** (the minimal init used by Void Linux and Docker base images). Each offers a fundamentally different philosophy for service management.

## Why Choose an Alternative Init System?

Systemd is feature-rich but controversial. Its monolithic design bundles service management, logging, networking, device management, and more into a single codebase exceeding 1.4 million lines of code. For administrators who value simplicity and auditability, alternative init systems offer focused, smaller implementations that do one thing well.

**Attack surface reduction** is the primary security argument. OpenRC (~30,000 lines), s6 (~25,000 lines for the supervision suite), and runit (~8,000 lines) are each dramatically smaller than systemd. Fewer lines of code running as PID 1 means fewer potential vulnerabilities in the most privileged process on your system.

**Boot speed** is another factor. Minimal init systems can boot a server in under 2 seconds because they start only essential services in parallel without the complex dependency resolution that systemd performs. For container environments and embedded systems, this translates to faster time-to-service.

**Transparency and debugging** improve with simpler init systems. When a service fails to start, runit and s6 provide clear, text-based supervision logs. OpenRC uses straightforward shell scripts that any administrator can read and modify. Understanding and fixing service issues is easier when the init system's behavior is predictable and documented.

For container-specific process management, see our [supervisord vs s6-overlay vs runit guide](../2026-04-25-supervisord-vs-s6-overlay-vs-runit-self-hosted-process-management/) and [container init processes comparison](../2026-05-22-container-init-processes-tini-dumb-init-docker-in/). For broader system monitoring, our [Linux OOM prevention guide](../2026-05-27-self-hosted-linux-oom-prevention-earlyoom-systemd) covers memory management across init systems.

## OpenRC: Dependency-Based Init for Gentoo and Alpine

[OpenRC](https://github.com/OpenRC/openrc) (1,837+ stars) is a dependency-based init system that serves as the default for Gentoo Linux and Alpine Linux. It uses a runlevel system with explicit service dependencies defined in shell scripts.

### Features

- **Runlevel management** — boot, default, nonetwork, and custom runlevels
- **Dependency resolution** — services declare `need`, `use`, `want`, and `before`/`after` relationships
- **Shell-based service scripts** — all service definitions are readable POSIX shell scripts
- **cgroup support** — optional process tracking and resource isolation via cgroups
- **No daemon required** — OpenRC scripts run directly without a persistent supervisor daemon
- **Cross-platform** — works on Linux, FreeBSD, NetBSD, and macOS

### Service Script Example

Service scripts live in `/etc/init.d/` and follow a standard structure:

```bash
#!/sbin/openrc-run
description="Nginx HTTP server"
command="/usr/sbin/nginx"
command_args="-c /etc/nginx/nginx.conf"
pidfile="/run/nginx.pid"
output_log="/var/log/nginx/openrc.log"
error_log="/var/log/nginx/openrc-error.log"

depend() {
    need net localmount
    use dns logger
    after firewall
}

start_pre() {
    checkconfig || return 1
}
```

### Managing Services

```bash
# Start a service
rc-service nginx start

# Enable at boot
rc-update add nginx default

# Check status
rc-service nginx status

# List all services
rc-status

# View service dependencies
rc-status --all --tree
```

### Installation on Debian/Ubuntu

```bash
apt install openrc
# During installation, choose whether to replace systemd as PID 1
# For container or secondary use, keep systemd and use OpenRC for service management only
```

### Docker Deployment

OpenRC is commonly used as the init system in Alpine-based containers:

```dockerfile
FROM alpine:latest
RUN apk add --no-cache nginx openrc
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-openrc /etc/init.d/nginx
RUN chmod +x /etc/init.d/nginx && rc-update add nginx default
CMD ["/sbin/init"]
```

## s6: Modern Process Supervision Suite

[s6](https://github.com/skarnet/s6) (931+ stars) is a small suite of Unix programs designed for process supervision, service management, and logging. Created by Laurent Bercot, s6 follows the Unix philosophy of small, composable tools.

### Features

- **Process supervision** — automatic restart, lifecycle management, and notification
- **Service dependencies** — declarative dependency graphs with parallel startup
- **s6-rc** — service manager that handles dependency ordering and startup sequencing
- **s6-log** — high-performance structured logging with automatic rotation
- **s6-svscan** — the supervisor daemon that monitors service directories
- **Minimal footprint** — each tool is independently small and auditable
- **No shell required** — service definitions are configuration files, not scripts

### Service Definition

Services are defined by creating a directory in `/etc/s6-rc/sourced/` with a `type` file and a `run` script:

```
/etc/s6-rc/sourced/nginx/
├── type              # contains "longrun"
├── dependencies-data # lists dependent services
├── run               # executable script to start the service
└── finish            # optional cleanup script
```

`run` script:

```bash
#!/command/execlineb
foreground {
    redirfd -w 1 /var/log/nginx/access.log
    redirfd -w 2 /var/log/nginx/error.log
}
exec /usr/sbin/nginx -g "daemon off;"
```

### Managing Services

```bash
# Compile the service database
s6-rc-compile /etc/s6-rc/compiled /etc/s6-rc/sourced

# Start a service
s6-rc -u change nginx

# Stop a service
s6-rc -d change nginx

# Start with dependencies
s6-rc -u change nginx nginx-dependency

# List running services
s6-rc -a list

# Check service state
s6-svstat /run/s6-rc/servicedirs/nginx
```

### Docker Deployment with s6-overlay

```dockerfile
FROM alpine:latest
ADD https://github.com/just-containers/s6-overlay/releases/download/v3.2.0.2/s6-overlay-noarch.tar.xz /tmp/
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz
COPY ./s6-rc-compiled /etc/s6-rc/compiled
CMD ["/init"]
```

## runit: Minimal Service Supervisor

[runit](https://github.com/void-linux/runit) (282+ stars on void-linux fork) is an init scheme with process supervision for Unix-like systems. Used by Void Linux as its default init and by many Docker images as a lightweight PID 1, runit is the simplest of the three systems compared here.

### Features

- **Three-stage boot** — stage 1 (system initialization), stage 2 (service supervision), stage 3 (shutdown)
- **Service directories** — each service is a directory with a `run` script
- **Automatic restart** — supervised processes are restarted immediately if they exit
- **Log supervision** — each service can have an associated log service
- **Minimal codebase** — approximately 8,000 lines of C code
- **Cross-platform** — Linux, macOS, FreeBSD, NetBSD support

### Service Definition

Services live in `/etc/sv/` with a single `run` script:

```bash
#!/bin/sh
exec 2>&1
exec chpst -u nginx /usr/sbin/nginx -g "daemon off;"
```

Create a log service in `/etc/sv/nginx/log/run`:

```bash
#!/bin/sh
exec svlogd -tt /var/log/nginx
```

### Managing Services

```bash
# Start a service
sv start nginx

# Stop a service
sv stop nginx

# Enable at boot (symlink to /etc/runit/runsvdir/default/)
ln -s /etc/sv/nginx /etc/runit/runsvdir/default/

# Check status
sv status nginx
# Output: run: nginx: (pid 1234) 12345s

# Restart
sv restart nginx

# Send signal
sv once nginx    # run once, do not restart
sv pause nginx   # send SIGSTOP
sv cont nginx    # send SIGCONT

# List all services
sv status /etc/runit/runsvdir/default/*
```

### Docker Deployment

runit is the most common init system in minimal Docker images:

```dockerfile
FROM alpine:latest
RUN apk add --no-cache runit nginx
RUN mkdir -p /etc/sv/nginx
COPY nginx-run /etc/sv/nginx/run
RUN chmod +x /etc/sv/nginx/run && ln -s /etc/sv/nginx /etc/runit/runsvdir/default/
CMD ["/usr/bin/runsvdir", "/etc/runit/runsvdir/default"]
```

## Feature Comparison

| Feature | OpenRC | s6 | runit |
|---------|--------|-----|-------|
| **Primary role** | System init + service manager | Process supervision suite | Minimal init + supervisor |
| **Lines of code** | ~30,000 | ~25,000 (suite) | ~8,000 |
| **Service definitions** | Shell scripts in `/etc/init.d/` | Config files + execline scripts | `run` scripts in `/etc/sv/` |
| **Dependency management** | Yes (need/use/want/before/after) | Yes (s6-rc dependency database) | No (manual ordering) |
| **Runlevels** | Yes (boot, default, custom) | Yes (service bundles) | No (single run state) |
| **Logging** | Via external logger | Built-in (s6-log) | Via svlogd per service |
| **Automatic restart** | No (needs external monitor) | Yes (s6-svscan) | Yes (runsvdir) |
| **Container friendly** | Moderate (needs init wrapper) | Yes (s6-overlay) | Yes (native) |
| **Learning curve** | Low (familiar shell scripts) | Medium (execline syntax) | Low (simple run scripts) |
| **Used by** | Gentoo, Alpine, Devuan | skarnet projects, containers | Void Linux, Docker images |
| **GitHub stars** | 1,837+ | 931+ | 282+ |
| **Best for** | Full Linux distributions | Advanced process supervision | Minimal containers and servers |

## Choosing the Right Init System

**Use OpenRC** when you want a full-featured init system with familiar shell-based service scripts. It's the most systemd-like alternative, offering runlevels, dependency management, and a comprehensive service ecosystem. Ideal for servers where you need traditional init system capabilities without systemd's complexity.

**Use s6** when you need advanced process supervision with reliable dependency management. Its s6-rc service manager provides the most sophisticated dependency resolution of the three, and s6-log offers structured logging without external dependencies. Best for infrastructure where service reliability and proper lifecycle management are critical.

**Use runit** when simplicity is paramount. Its minimal design means less to understand, less to configure, and less that can go wrong. The straightforward `run` script model makes service definitions trivially simple. Ideal for containers, embedded systems, and administrators who value minimalism.

## FAQ

### Can I replace systemd with OpenRC on an existing system?

Yes, but it requires careful migration. On Debian, install the `openrc` package and select it as the default init during installation. On Gentoo, OpenRC is the default. The migration involves replacing systemd unit files with OpenRC service scripts and ensuring all dependencies are properly declared. Always test on a non-production system first.

### Does s6 work without execline?

Yes, but execline is recommended. Service `run` scripts can be written in any shell (bash, sh, dash), but execline (also from skarnet) provides a cleaner, non-Turing-complete syntax that avoids common shell scripting pitfalls. The s6 documentation strongly recommends using execline for all service definitions.

### Can runit handle service dependencies?

Not natively. runit starts all services in parallel and does not resolve dependencies. If service B depends on service A, you must either: (1) add a sleep or retry loop in service B's `run` script, (2) use s6-rc on top of runit (which is possible), or (3) manage dependency ordering externally. This is runit's primary limitation compared to OpenRC and s6.

### Which init system is best for Docker containers?

runit is the most common choice for container PID 1 due to its minimal footprint and simplicity. s6-overlay (s6's Docker adaptation) is also popular when you need service dependencies inside containers. OpenRC is less common in containers because it expects a full system environment.

### Do these init systems support cgroups?

OpenRC has optional cgroup support for process tracking and resource isolation. s6 can work with cgroups but does not manage them directly. runit has no cgroup integration. If you need cgroup-based resource management, OpenRC is the most capable of the three, though systemd remains the most comprehensive.

### How do I migrate from systemd to an alternative init?

1. Install the alternative init system alongside systemd
2. Create equivalent service definitions (unit files → init scripts/run scripts)
3. Test all services in the new init system
4. Reboot with the alternative init as PID 1 (via kernel boot parameter `init=/sbin/openrc-init` or equivalent)
5. Remove systemd packages after verifying all services work
Always maintain a rescue boot option (GRUB entry with `init=/bin/sh`) in case the migration fails.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Init Systems: OpenRC vs s6 vs runit for Server Management (2026)",
  "description": "Compare OpenRC, s6, and runit as alternatives to systemd for self-hosted Linux servers.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
