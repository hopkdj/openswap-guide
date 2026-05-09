---
title: "Self-Hosted Serial Server: ser2net vs conserver vs socat Guide"
date: "2026-05-09"
tags: ["comparison", "guide", "self-hosted", "networking", "infrastructure", "serial"]
draft: false
---

Managing serial devices across a distributed infrastructure is a challenge that many homelab operators and enterprise IT teams face daily. Whether you are connecting to console ports on network switches, reading data from industrial sensors, or managing legacy hardware, a serial server bridges the gap between physical serial ports and network-accessible interfaces. In this guide, we compare three powerful open-source solutions — **ser2net**, **conserver**, and **socat** — for self-hosting serial device access over your network.

## What Is a Serial Server and Why It Matters

A serial server takes a physical serial port (RS-232, RS-485, or USB-to-serial) and makes it accessible over TCP/IP. This allows you to manage serial devices from anywhere on your network — or even over the internet — without physically being near the hardware.

Self-hosted serial servers are essential for:

- **Network equipment management** — accessing console ports on routers, switches, and firewalls for configuration and recovery
- **Industrial IoT** — reading sensor data from Modbus RTU devices, PLCs, and environmental monitors
- **Embedded development** — debugging microcontrollers and single-board computers via serial console
- **Legacy system support** — maintaining serial-connected UPS units, barcode scanners, and point-of-sale systems
- **Remote site management** — accessing serial devices at branch offices without on-site visits

## ser2net — The Dedicated Serial-to-Network Bridge

**ser2net** is the most widely used serial-to-network daemon on Linux systems. It maps serial ports to TCP ports, allowing any TCP client to connect and communicate with the serial device as if it were directly attached. With over 580 stars on GitHub and active maintenance, it is the standard choice for this use case.

### Key Features

- **Multiple port mapping** — serve multiple serial devices on different TCP ports simultaneously
- **RFC 2217 support** — Telnet Com Port Control option for baud rate, parity, and flow control negotiation
- **Raw TCP mode** — simple transparent serial-to-TCP bridge for basic use cases
- **Persistent connections** — maintains serial port state across client disconnects
- **UDP support** — bidirectional UDP mode for broadcast-style serial data distribution
- **Configuration file driven** — clean, declarative configuration for complex setups

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install ser2net
```

On Alpine Linux:

```bash
apk add ser2net
```

Build from source:

```bash
git clone https://github.com/cminyard/ser2net.git
cd ser2net
./autogen.sh
./configure
make
sudo make install
```

### Configuration

The configuration file is located at `/etc/ser2net.yaml` (modern YAML format) or `/etc/ser2net.conf` (legacy format):

```yaml
# /etc/ser2net.yaml
connection: &con00
  accepter: tcp,2000
  connector: serialdev,/dev/ttyS0,9600n81,local
  options:
    kickolduser: true

connection: &con01
  accepter: tcp,2001
  connector: serialdev,/dev/ttyUSB0,115200n81,local
  options:
    kickolduser: true

connection: &con02
  accepter: tcp,2002
  connector: serialdev,/dev/ttyUSB1,9600e71,local
  enable: on
```

Legacy format (still widely used):

```
# /etc/ser2net.conf
2000:raw:0:/dev/ttyS0:9600 8DATABITS NONE 1STOPBIT
2001:raw:0:/dev/ttyUSB0:115200 8DATABITS NONE 1STOPBIT
2002:telnet:0:/dev/ttyUSB1:9600 8DATABITS EVENPARITY 1STOPBIT
```

### Docker Deployment

```dockerfile
FROM alpine:latest
RUN apk add --no-cache ser2net
COPY ser2net.yaml /etc/ser2net.yaml
EXPOSE 2000-2010
ENTRYPOINT ["ser2net", "-n"]
```

```bash
docker build -t ser2net-server .
docker run -d --name ser2net \
  --device=/dev/ttyUSB0 \
  --device=/dev/ttyS0 \
  -p 2000-2010:2000-2010 \
  -v $(pwd)/ser2net.yaml:/etc/ser2net.yaml \
  ser2net-server
```

### Connecting to a ser2net Server

```bash
# Using netcat
nc ser2net-server 2000

# Using socat
socat -,raw,echo=0 tcp:ser2net-server:2000

# Using telnet (for RFC 2217 negotiation)
telnet ser2net-server 2000

# Using Python
python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('ser2net-server', 2000))
s.send(b'AT\r\n')
print(s.recv(1024))
"
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Setup complexity | Low | Simple config file, works immediately |
| Multi-port support | Excellent | Unlimited serial-to-TCP mappings |
| RFC 2217 support | Yes | Full Telnet Com Port Control |
| Authentication | None | No built-in access control |
| Logging | Basic | syslog integration |
| Docker support | Good | Official package in most repos |

## conserver — The Enterprise Serial Console Manager

**conserver** is a more feature-rich serial console management system designed for enterprise environments. It provides centralized access to serial consoles with multi-user support, logging, and authentication. Originally developed by Bryan Stansell, it has been actively maintained with recent updates in 2026.

### Key Features

- **Multi-user access** — multiple users can connect to the same serial console simultaneously
- **Access control** — fine-grained read/write permissions per user and per console
- **Session logging** — automatic logging of all serial console activity
- **Break signal support** — send break signals for console recovery
- **Timestamped logging** — every character is logged with timestamps for audit trails
- **Master/slave mode** — designate read-only and read-write access levels
- **Configuration management** — centralized config with device discovery

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install conserver-server conserver-client
```

Build from source:

```bash
git clone https://github.com/conserver/conserver.git
cd conserver
./autogen.sh
./configure
make
sudo make install
```

### Configuration

The main configuration file is `/etc/conserver.cf`:

```
# /etc/conserver.cf

# Default settings
default * {
    type device;
    parity none;
    baud 9600;
    logfile /var/log/conserver/&.log;
    timestamp 1hab;
    rw *;
}

# Network switch console
console switch-console {
    device /dev/ttyS0;
    baud 9600;
    parity none;
    master admin;
    rw admin,operator;
    ro viewer;
}

# Router console
console router-console {
    device /dev/ttyUSB0;
    baud 115200;
    parity none;
    rw admin;
}

# UPS serial monitor
console ups-monitor {
    device /dev/ttyUSB1;
    baud 2400;
    parity even;
    ro *;
}
```

### Docker Deployment

```dockerfile
FROM alpine:latest
RUN apk add --no-cache conserver
COPY conserver.cf /etc/conserver.cf
EXPOSE 782
ENTRYPOINT ["conserved", "-d"]
```

```bash
docker build -t conserver-server .
docker run -d --name conserver \
  --device=/dev/ttyS0 \
  --device=/dev/ttyUSB0 \
  -p 782:782 \
  -v $(pwd)/conserver.cf:/etc/conserver.cf \
  -v /var/log/conserver:/var/log/conserver \
  conserver-server
```

### Client Usage

```bash
# Connect to a console
console switch-console

# Read-only connection
console -r ups-monitor

# Monitor mode (watch without typing)
console -M switch-console

# Break signal
console -b switch-console

# Force disconnect all users
console -F switch-console
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Setup complexity | Moderate | More complex config, steeper learning curve |
| Multi-user support | Excellent | Simultaneous access with permissions |
| Access control | Strong | Per-user read/write permissions |
| Session logging | Excellent | Full timestamped audit trails |
| Authentication | Yes | Built-in user management |
| Docker support | Moderate | Requires config and log volume mounts |

## socat — The Universal Relay Tool

**socat** (SOcket CAT) is a general-purpose relay tool that can connect virtually any two data channels — serial ports, TCP sockets, UDP, pipes, files, and more. While not specifically designed as a serial server, its flexibility makes it an excellent lightweight alternative.

### Key Features

- **Universal connectivity** — connect any two data channels, not just serial
- **No daemon mode needed** — can be run on-demand or as a background process
- **SSL/TLS encryption** — built-in support for encrypted serial connections
- **Process spawning** — can fork to handle multiple concurrent connections
- **Bidirectional relay** — full-duplex communication between any two endpoints
- **Already installed** — available on virtually every Linux distribution

### Installation

```bash
# Debian/Ubuntu
sudo apt install socat

# Alpine
apk add socat

# RHEL/CentOS
sudo yum install socat
```

### Usage Examples

```bash
# Basic serial to TCP
socat /dev/ttyS0,raw,echo=0,b9600 TCP-LISTEN:2000,fork

# Serial to TCP with SSL encryption
socat /dev/ttyUSB0,raw,echo=0,b115200 \
  OPENSSL-LISTEN:2001,cert=/etc/ssl/certs/serial.pem,fork

# TCP to serial (reverse direction)
socat TCP-LISTEN:2002,fork /dev/ttyS0,raw,echo=0,b9600

# Serial to UDP broadcast
socat /dev/ttyS0,raw,echo=0,b9600 UDP-DATAGRAM:255.255.255.255:9000

# Persistent background service
nohup socat /dev/ttyUSB0,raw,echo=0,b9600 \
  TCP-LISTEN:2000,fork,reuseaddr > /dev/null 2>&1 &
```

### Docker Deployment

```dockerfile
FROM alpine:latest
RUN apk add --no-cache socat
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/bin/sh
# entrypoint.sh
exec socat /dev/ttyUSB0,raw,echo=0,b115200 \
  TCP-LISTEN:2000,fork,reuseaddr
```

```bash
docker build -t socat-serial .
docker run -d --name socat-serial \
  --device=/dev/ttyUSB0 \
  -p 2000:2000 \
  socat-serial
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Setup complexity | Low | One-liner command |
| Flexibility | Excellent | Any-to-any data relay |
| SSL/TLS support | Yes | Built-in encryption |
| Configuration management | Manual | No config file, CLI-driven |
| Multi-device support | Manual | Need separate process per device |
| Access control | None | No built-in authentication |

## Comparison Table: ser2net vs conserver vs socat

| Feature | ser2net | conserver | socat |
|---------|---------|-----------|-------|
| **Primary purpose** | Serial-to-network | Console management | Universal relay |
| **Multi-device support** | Excellent (config file) | Excellent (config file) | Manual (one process each) |
| **RFC 2217** | Yes | No | No |
| **Multi-user access** | No (exclusive) | Yes (simultaneous) | No (exclusive per fork) |
| **Access control** | No | Yes (per-user) | No |
| **Session logging** | Basic | Full timestamped | None |
| **SSL/TLS** | No | No | Yes |
| **Authentication** | No | Yes | No |
| **UDP support** | Yes | No | Yes |
| **Configuration** | YAML/config file | Config file | CLI arguments |
| **Docker friendly** | Good | Moderate | Excellent |
| **GitHub stars** | 585 | 142 | N/A (classic) |
| **Last update** | 2026 | 2026 | Maintained |

## Choosing the Right Serial Server for Your Infrastructure

**Choose ser2net if** you need a dedicated serial-to-network bridge with minimal configuration. It is the best choice for straightforward scenarios where you want to expose serial ports over TCP with RFC 2217 support for baud rate negotiation. Its simple YAML configuration and low resource usage make it ideal for homelabs and small deployments.

**Choose conserver if** you need enterprise-grade serial console management with multi-user access, authentication, and full audit logging. It is essential for data centers, network operations centers, and any environment where multiple administrators need simultaneous access to serial consoles with proper access controls.

**Choose socat if** you need quick, ad-hoc serial-to-TCP bridging or want encrypted serial connections. It excels as a lightweight tool for temporary setups, testing, or situations where SSL/TLS encryption of serial traffic is required. Its universal relay capability also means it can bridge serial devices to non-TCP destinations.

## Why Self-Host Your Serial Server?

Commercial serial server appliances from Moxa, Digi, and Lantronix cost $200-$2,000 per unit. Self-hosting with open-source software on a Raspberry Pi or small Linux server gives you the same functionality at a fraction of the cost, with full control over configuration, security, and data handling.

**Cost savings** are immediate and substantial. A $35 Raspberry Pi running ser2net can manage 4+ USB-to-serial adapters, replacing a $500+ commercial serial server. The software is free, the hardware is commodity-grade, and there are no licensing fees.

**Data sovereignty** matters when your serial devices include industrial sensors, UPS monitors, or network equipment consoles. With a self-hosted solution, all serial communication stays within your network — no cloud connectivity, no third-party access, and no vendor lock-in.

**Flexibility** is unmatched. You can run these tools on any Linux hardware, customize the configuration to your exact needs, integrate with your existing monitoring and alerting systems, and modify the source code if required. Commercial appliances are locked down and inflexible by comparison.

For network equipment management, see our [SSH bastion and jump server guide](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/).
For hardware-level server management, check our [IPMI, Redfish, and OpenBMC comparison](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/).
For terminal access alternatives, our [web SSH access guide](../2026-04-29-shellhub-vs-sshwifty-vs-wetty-self-hosted-web-ssh-access-guide-2026/) covers browser-based options.

## FAQ

### What is the difference between a serial server and a terminal server?

A serial server bridges a single serial port to a network connection (TCP/UDP). A terminal server aggregates multiple serial ports and provides centralized network access to all of them. ser2net and conserver both function as terminal servers when configured with multiple ports. socat handles one port at a time.

### Can I access serial devices over the internet securely?

Yes, but you should add encryption. socat supports SSL/TLS natively. For ser2net and conserver, place them behind an SSH tunnel, WireGuard VPN, or a reverse proxy with TLS termination. Never expose raw serial ports to the internet without encryption — they provide unauthenticated access to critical infrastructure.

### How do I troubleshoot a serial connection that is not working?

First, verify the device exists: `ls -la /dev/ttyUSB0`. Then test with a direct terminal: `screen /dev/ttyUSB0 9600`. If that works, the issue is in the server configuration. Check baud rate, parity, and stop bits match the device specifications. Use `stty -F /dev/ttyUSB0` to verify current settings.

### Can multiple users connect to the same serial port simultaneously?

Only **conserver** supports true multi-user simultaneous access to the same serial console. ser2net and socat (with fork) allow multiple connections, but only one can actively communicate at a time — additional connections are queued or rejected depending on configuration.

### What baud rates are supported?

All three tools support standard baud rates from 300 to 921,600 bps. The actual maximum depends on your hardware — USB-to-serial adapters typically max out at 921,600, while native UART ports can reach 3-4 Mbps. Common rates are 9600, 19200, 38400, 57600, and 115200.

### How do I monitor serial server uptime and connection status?

For ser2net, check `systemctl status ser2net` and review syslog entries. For conserver, use `consadmin` to list active connections and console status. For socat, use `ps aux | grep socat` or monitor the listening port with `ss -tlnp | grep 2000`. Integrate with Prometheus node_exporter or custom scripts for automated monitoring.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Serial Server: ser2net vs conserver vs socat Guide",
  "description": "Compare ser2net, conserver, and socat for self-hosted serial device access over TCP/IP. Learn Docker deployment, configuration, and best practices for serial server management.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
