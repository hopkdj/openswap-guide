---
title: "Self-Hosted Super-Server: systemd Socket Activation vs xinetd vs s6-networking"
date: "2026-05-22"
tags: ["super-server", "socket-activation", "xinetd", "systemd", "process-management"]
draft: false
---

A super-server (also called an internet superserver) listens on multiple network ports and spawns the appropriate service daemon when a connection arrives. Instead of running dozens of services that each consume memory waiting for connections, a super-server centralizes port listening and launches services on demand.

This architecture provides significant advantages for self-hosted infrastructure: reduced memory footprint, centralized access logging, built-in rate limiting, and simplified service management. In this guide, we compare three approaches to super-server functionality: **systemd socket activation**, **xinetd**, and **s6-networking**.

## What Is a Super-Server?

Traditional service management runs each daemon as a persistent process listening on its assigned port. A super-server changes this model:

1. The super-server binds to all configured ports
2. When a connection arrives on a port, the super-server spawns the corresponding service
3. The service handles the connection and exits (or persists, depending on configuration)
4. Resources are only consumed when services are actively handling connections

This is particularly valuable for:
- **Low-traffic services** that don't need persistent processes
- **Resource-constrained environments** like embedded systems or containers
- **Security-sensitive services** that benefit from on-demand execution
- **Centralized logging and access control** across multiple services

---

## systemd Socket Activation

systemd's socket activation is the modern standard for on-demand service startup on Linux systems using systemd. Services define socket units that listen on ports, and systemd spawns the service when the first connection arrives.

### Architecture

systemd socket activation uses two unit types:
- **`.socket` unit**: Defines the listening socket (port, address, protocol)
- **`.service` unit**: Defines the actual service process

When a connection arrives on the socket, systemd starts the service and passes the pre-bound socket file descriptor. The service inherits the listening socket, enabling zero-downtime restarts.

### Key Features

- **Zero-downtime restarts**: Socket stays bound while the service restarts
- **Parallel activation**: Multiple sockets can trigger services simultaneously
- **File descriptor passing**: Services receive pre-bound sockets via `sd_listen_fds()`
- **Integration**: Native part of systemd — no additional software needed
- **Resource limits**: Full systemd cgroup integration for CPU, memory, and I/O limits
- **Journal logging**: Automatic integration with systemd-journald

### Configuration Example

Create a socket unit (`/etc/systemd/system/echo.socket`):

```ini
[Unit]
Description=Echo Service Socket

[Socket]
ListenStream=9999
Accept=yes
MaxConnections=100
MaxConnectionsPerSource=10

[Install]
WantedBy=sockets.target
```

Create the corresponding service unit (`/etc/systemd/system/echo@.service`):

```ini
[Unit]
Description=Echo Service Instance

[Service]
ExecStart=/usr/bin/cat
StandardInput=socket
StandardOutput=socket
```

Enable and start:

```bash
systemctl enable --now echo.socket
```

### Docker Deployment

```yaml
services:
  systemd-socket-demo:
    image: alpine:latest
    command: ["sh", "-c", "apk add socat && socat TCP-LISTEN:8080,fork EXEC:/bin/cat"]
    ports:
      - "8080:8080"
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 64M
```

---

## xinetd — The Classic Super-Server

xinetd (extended Internet services daemon) is the successor to inetd, providing a configurable super-server with advanced access control, logging, and rate limiting features.

### Architecture

xinetd reads a single configuration file (`/etc/xinetd.conf`) and per-service files in `/etc/xinetd.d/`. It manages all configured services from a single daemon process, spawning the appropriate service handler for each incoming connection.

### Key Features

- **Access control**: `only_from` and `no_access` directives for IP-based filtering
- **Rate limiting**: `cps` (connections per second), `instances`, `per_source` limits
- **Time-based access**: `access_times` restricts service availability to specific hours
- **Logging**: Per-service logging with configurable log levels
- **IPv6 support**: Full dual-stack networking
- **TCP Wrappers integration**: Optional libwrap support for additional access control

### Configuration Example

```
service echo
{
    disable         = no
    socket_type     = stream
    protocol        = tcp
    wait            = no
    user            = root
    server          = /usr/bin/cat
    instances       = 50
    cps             = 100 2
    per_source      = 5
    only_from       = 10.0.0.0/8 192.168.0.0/16
    log_type        = FILE /var/log/xinetd-echo.log
    log_on_success  = HOST PID
    log_on_failure  = HOST RECORD
}
```

### Docker Compose Deployment

```yaml
services:
  xinetd:
    image: linuxserver/xinetd:latest
    network_mode: host
    cap_add:
      - NET_BIND_SERVICE
    volumes:
      - ./xinetd.conf:/etc/xinetd.conf:ro
      - ./xinetd.d:/etc/xinetd.d:ro
      - ./services:/usr/local/services:ro
      - ./logs:/var/log
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    restart: unless-stopped
```

### When to Use xinetd

- You need fine-grained access control per service
- You want centralized rate limiting without additional tools
- You're managing legacy systems where systemd is not available
- You need time-based service availability restrictions

---

## s6-networking — The Modern Minimalist

s6-networking is part of the s6 suite of process supervision tools from skarnet.org. It provides network service management through s6's unique supervision tree model.

### Architecture

s6-networking uses a different philosophy than systemd or xinetd:
- **s6-tcpserver**: Listens on TCP ports and spawns services per connection
- **s6-svscan**: Supervises all s6 services in a directory tree
- **s6-log**: Provides structured, rotation-aware logging
- **s6-rc**: Dependency-aware service orchestration

Each service runs under s6 supervision with automatic restart, logging, and health monitoring.

### Key Features

- **Supervision tree**: Every service is monitored and automatically restarted on failure
- **Structured logging**: Timestamped, rotation-aware logs with minimal overhead
- **Dependency management**: s6-rc handles service startup ordering
- **Minimal footprint**: Extremely lightweight compared to systemd
- **Portable**: Works on any POSIX system, not tied to a specific init system
- **Security**: Runs services with minimal privileges by default

### Configuration Example

Create a service directory for your TCP service:

```bash
mkdir -p /etc/s6/sv/my-service
```

Create the `run` script (`/etc/s6/sv/my-service/run`):

```sh
#!/usr/bin/execlineb
# s6-tcpserver configuration
s6-tcpserver -v -c 50 -b /tmp/my-service.sock 0.0.0.0 9999   /usr/local/bin/my-service-handler
```

Create the log service (`/etc/s6/sv/my-service/log/run`):

```sh
#!/usr/bin/execlineb
s6-log /var/log/my-service
```

Enable the service:

```bash
ln -s /etc/s6/sv/my-service /etc/s6/scanned/
s6-svc -u /etc/s6/sv/my-service
```

### Docker Compose Deployment

```yaml
services:
  s6-networking:
    image: ghcr.io/skarnet/s6-overlay:latest
    network_mode: host
    cap_add:
      - NET_BIND_SERVICE
    volumes:
      - ./s6-services:/etc/s6/sv:ro
      - ./s6-logs:/var/log
      - /var/run/s6:/var/run/s6
    environment:
      - S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0
    restart: unless-stopped
```

### When to Use s6-networking

- You're running in containers and need a lightweight init system
- You want automatic service supervision and restart
- You need structured logging without a full logging stack
- You prefer a minimalist, UNIX-philosophy approach over feature-heavy alternatives

---

## Comparison Table

| Feature | systemd Socket | xinetd | s6-networking |
|---------|---------------|--------|---------------|
| **Type** | Init system feature | Standalone daemon | Supervision suite |
| **Footprint** | Part of systemd (~30MB) | Single binary (~180KB) | Suite (~2MB) |
| **Access Control** | Via firewall rules | Built-in IP/ACL | Via s6-rc rules |
| **Rate Limiting** | Via systemd limits | Built-in (cps, per_source) | Via s6-tcpserver flags |
| **Zero-Downtime Restart** | Yes (FD passing) | No | Via s6 supervision |
| **Centralized Logging** | journald | xinetd logging | s6-log |
| **Dependency Management** | Yes (Requires/Wants) | No | s6-rc |
| **Container Support** | Limited (systemd in containers) | Good (standalone) | Excellent (s6-overlay) |
| **Configuration Format** | INI-style units | Custom config | Shell scripts |
| **Learning Curve** | Medium | Low | High |
| **Active Development** | Yes (systemd project) | Maintenance mode | Yes (skarnet.org) |

## Why Self-Host a Super-Server?

Running dozens of independent service daemons wastes resources. Each persistent process consumes memory for its runtime, holds open file descriptors, and requires individual monitoring. A super-server consolidates this overhead:

- **Memory efficiency**: Services only consume RAM when handling connections
- **Simplified management**: One configuration point for multiple services
- **Better security**: Services can be isolated to minimal privileges
- **Reduced attack surface**: Listening sockets are centralized and controllable
- **Consistent logging**: All connection events logged through a single point

For home labs and small infrastructure, super-servers can reduce idle memory usage by 30-50% compared to running each service as a persistent daemon.

### Security Best Practices

1. **Restrict access**: Use IP-based filtering (xinetd `only_from`, s6-tcpserver `-a`, or firewall rules)
2. **Rate limit**: Prevent connection flooding with `cps` limits or equivalent
3. **Minimize privileges**: Run service handlers as non-root users
4. **Monitor logs**: Centralized logging makes it easier to detect intrusion attempts
5. **Use TLS**: Terminate TLS before the super-server, or configure per-service encryption
6. **Regular audits**: Review which services are enabled and disable unused ones

For related reading on process management, see our [supervisord vs s6-overlay vs runit guide](../2026-04-25-supervisord-vs-s6-overlay-vs-runit-self-hosted-process-management/) and [XDP/eBPF network tools comparison](../2026-05-13-self-hosted-xdp-ebpf-network-firewalls-xdp-tools-bpftool-cilium-ebpf-guide/). For container security hardening, check our [Docker security guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/).

## FAQ

### What is the difference between a super-server and a regular service manager?

A regular service manager (like systemd or OpenRC) starts and stops individual services. A super-server specifically manages network services by listening on ports and spawning service handlers only when connections arrive. The key difference is on-demand activation — services don't run continuously.

### Can I migrate from xinetd to systemd socket activation?

Yes. Each xinetd service configuration can be converted to a systemd socket unit + service unit pair. The `socket_type` becomes `ListenStream`/`ListenDatagram`, `wait` maps to `Accept`, and access control moves to firewall rules or systemd's `IPAddressAllow`/`IPAddressDeny` directives.

### Does systemd socket activation work for UDP services?

Yes. Use `ListenDatagram=` instead of `ListenStream=` in the socket unit. systemd will buffer incoming UDP packets until the service starts, then pass the socket to the service. This is useful for DNS, SNMP, and syslog services.

### Why would I use s6-networking over systemd?

s6-networking is significantly lighter weight, works in containers where systemd struggles, and provides a supervision model that automatically restarts failed services. It's ideal for minimal container images, embedded systems, and environments where you don't want a full init system.

### How do I monitor which services are being triggered by a super-server?

- **systemd**: `systemctl status *.socket` and `journalctl -u <service>`
- **xinetd**: Check `/var/log/xinetd.log` or the per-service log files configured in `log_type`
- **s6-networking**: `s6-svstat /etc/s6/sv/*/` for service status, check s6-log directories

### Is xinetd still maintained?

xinetd receives occasional security patches but is essentially in maintenance mode. The last significant feature updates were years ago. For new deployments, systemd socket activation (on systemd-based systems) or s6-networking (for containers) are recommended alternatives.

### Can a super-server handle TLS connections?

Not directly. Super-servers typically handle raw TCP/UDP connections. For TLS, you would either: (1) use stunnel or sslh as a TLS front-end that forwards to the super-server, (2) configure each service to handle TLS itself, or (3) use a reverse proxy like Nginx that terminates TLS and forwards to backend services managed by the super-server.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Super-Server: systemd Socket Activation vs xinetd vs s6-networking",
  "description": "Compare three super-server approaches for on-demand service activation: systemd socket activation, xinetd, and s6-networking. Covers architecture, deployment, and security.",
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
