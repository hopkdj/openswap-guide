---
title: "Coturn vs Restund vs Pion TURN: Best Self-Hosted TURN/STUN Servers 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "webrtc", "networking", "coturn"]
draft: false
description: "Complete guide to self-hosted TURN and STUN servers in 2026. Compare Coturn, Restund, and Pion TURN with Docker setups, configuration examples, performance benchmarks, and security hardening."
---

Every self-hosted real-time communication setup eventually hits the same wall: NAT. Whether you're running Jitsi Meet, [nextcloud](https://nextcloud.com/) Talk, a Matrix homeserver with VoIP, or a custom WebRTC application, roughly 20–30% of connections will fail without a TURN relay. STUN helps devices discover their public addresses, but when symmetric NATs or strict firewalls block direct peer-to-peer traffic, you need a TURN server to relay media.

Running your own TURN/STUN server means no reliance on free public relays (which are slow, throttled, or unreliable), full control over your media infrastructure, and compliance with data sovereignty requirements. This guide compares the three leading open-source TURN/STUN servers—**Coturn**, **Restund**, and **Pion TURN**—and walks you through production deployment.

## Why Self-Host Your TURN/STUN Server?

Public STUN servers are abundant and generally fine for NAT discovery. Google's `stun.l.google.com:19302` is the most widely used. But public **TURN** servers are a different story. The reasons to self-host:

- **Reliability**: Free TURN servers throttle bandwidth, impose session limits, or disappear without notice. Your users' calls shouldn't depend on someone else's goodwill.
- **Performance**: A self-hosted TURN server on the same network or in a nearby data center dramatically reduces latency and jitter for relayed media.
- **Security and Privacy**: TURN relays all media traffic. Running it yourself means your audio, video, and data channels never touch an untrusted third party.
- **Cost**: Running Coturn on a $5/month VPS handles thousands of concurrent sessions. Commercial TURN services charge per-gigabyte or per-session, which adds up quickly.
- **Compliance**: GDPR, HIPAA, and similar regulations may require media to stay within your infrastructure. A self-hosted TURN server gives you that guarantee.
- **Full Stack Control**: When your TURN, SFU, and signaling servers are all self-hosted, you have end-to-end visibility into your real-time communication stack.

## What Are STUN and TURN?

The protocols work together as part of the ICE (Interactive Connectivity Establishment) framework:

- **STUN** (Session Traversal Utilities for NAT, RFC 5389): A lightweight protocol that helps a device behind NAT discover its public IP address and port. It's a "what's my address?" service. STUN doesn't relay media—it just tells each peer how to reach the other directly.
- **TURN** (Traversal Using Relays around NAT, RFC 5766): When direct P2P fails, TURN acts as a relay. Both peers send and receive media through the TURN server. This adds latency and consumes server bandwidth, but it guarantees connectivity.
- **TURN over TLS (TURNS)**: Encrypts the TURN signaling and relayed traffic using TLS on port 5349 (TCP or UDP/DTLS). Recommended for production deployments.

In practice, ICE tries STUN first (direct connection), then falls back to TURN (relay). A good TURN server is your safety net for the connections that would otherwise fail.

## Coturn: The Industry Standard

**Coturn** is the most widely deployed open-source TURN/STUN server. It's the default TURN server for Jitsi Meet, Nextcloud Talk, and countless Matrix homeservers. Written in C/C++, it's battle-tested, feature-complete, and actively maintained.

### Key Features

- Full STUN/TURN/TURN-TCP/TURN-TLS/TURN-DTLS support
- REST API authentication with HMAC-based time-limited tokens
- Redis, MySQL, PostgreSQL, and MongoDB backends[prometheus](https://prometheus.io/)ntial storage
- Prometheus metrics export
- Horizontal scaling via shared Redis backend
- Mobile ICE support (RFC 6544)
- IPv6 support
- Bandwidth quotas and per-user rate limiting
- WebRT[docker](https://www.docker.com/)mized defaults

### Docker Deployment

```yaml
# docker-compose.yml
version: "3.8"

services:
  coturn:
    image: coturn/coturn:latest
    container_name: coturn
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./turnserver.conf:/etc/coturn/turnserver.conf:ro
      - ./certs:/etc/coturn/certs:ro
    environment:
      - DETECT_EXTERNAL_IP=yes
      - DETECT_RELAY_IP=yes
```

`network_mode: host` is strongly recommended for Coturn. TURN needs to bind directly to specific ports, and NAT traversal works more reliably when the server sees the real network interface. If host networking isn't available, you'll need to map a large UDP port range.

### Configuration

Here's a production-ready `turnserver.conf`:

```ini
# === Network ===
listening-port=3478
tls-listening-port=5349
min-port=49152
max-port=65535

# === External IPs ===
# Replace with your server's public IP
external-ip=203.0.113.50

# If behind NAT, use: external-ip=PUBLIC_IP/INTERNAL_IP
# external-ip=203.0.113.50/10.0.0.5

# === TLS Certificates ===
cert=/etc/coturn/certs/fullchain.pem
pkey=/etc/coturn/certs/privkey.pem

# === Authentication ===
lt-cred-mech
realm=turn.yourdomain.com
use-auth-secret
static-auth-secret=YOUR_SHARED_SECRET_HERE

# For Redis-backed auth (clustering):
# redis-userdb="ip=127.0.0.1 dbname=0 password=redis_pass"

# === Security ===
fingerprint
stale-nonce=3600
no-cli
no-stdout-log
verbose

# === Quotas ===
total-quota=0
user-quota=12
max-alloc-time=3600
```

### Firewall Rules

```bash
# UFW (Ubuntu/Debian)
ufw allow 3478/udp
ufw allow 3478/tcp
ufw allow 5349/udp
ufw allow 5349/tcp
ufw allow 49152:65535/udp

# For remote admin (optional)
ufw allow from 10.0.0.0/8 to any port 5766
```

### System Tuning for High Load

```bash
# Increase UDP buffer sizes
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728
sysctl -w net.ipv4.udp_mem="2097152 4194304 8388608"

# Persist across reboots
cat >> /etc/sysctl.conf << EOF
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.udp_mem=2097152 4194304 8388608
EOF
sysctl -p
```

## Restund: The Lightweight Alternative

**Restund** is a modular STUN/TURN server written in C by the same author as the libre and re libraries (used by the BareSIP project). It's designed for minimal resource consumption, making it ideal for embedded systems, edge deployments, or low-traffic homelabs.

### Key Features

- Binary size under 500KB
- Plugin-based architecture (STUN, TURN, HTTP auth, monitoring)
- Built on the `re` network library (RFC-compliant)
- UDP/TCP/TLS/DTLS support via plugins
- HTTP endpoint for real-time statistics
- Extremely simple configuration

### Building and Deploying

Restund doesn't have an official Docker image on Docker Hub, but building it is straightforward:

```dockerfile
FROM alpine:3.19 AS builder

RUN apk add --no-cache build-base linux-headers openssl-dev

RUN apk add --no-cache git make
RUN git clone https://github.com/creytiv/re.git /re && \
    cd /re && make -j$(nproc) && make install

RUN git clone https://github.com/creytiv/restund.git /restund && \
    cd /restund && make -j$(nproc) && make install

FROM alpine:3.19
RUN apk add --no-cache libressl
COPY --from=builder /usr/local/lib/libre.so* /usr/local/lib/
COPY --from=builder /usr/local/bin/restund /usr/local/bin/
COPY --from=builder /usr/local/lib/restund /usr/local/lib/restund

EXPOSE 3478/udp 3478/tcp 5349/udp 5349/tcp
CMD ["restund", "-f", "/etc/restund.conf"]
```

```yaml
# docker-compose.yml
version: "3.8"

services:
  restund:
    build: .
    container_name: restund
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./restund.conf:/etc/restund.conf:ro
```

### Configuration

```ini
# restund.conf

# Network bindings
udp_port    3478
tcp_port    3478

# TLS (requires openssl module)
# tls_port    5349
# tls_cert    /etc/restund/cert.pem
# tls_pkey    /etc/restund/key.pem

# Authentication realm
realm       turn.yourdomain.com

# Load modules
module      /usr/local/lib/restund/stun.so
module      /usr/local/lib/restund/turn.so
module      /usr/local/lib/restund/sys.so
module      /usr/local/lib/restund/httpauth.so

# TURN relay settings
turn_relay_addr 0.0.0.0
turn_min_port   49152
turn_max_port   65535

# Auth credentials file (username:password per line)
# turn_auth_file  /etc/restund/passwd
```

Restund's simplicity is both its strength and limitation. It lacks built-in Redis-backed clustering, Prometheus metrics, and REST API auth. But for deployments with fewer than 100 concurrent sessions, it's remarkably efficient.

## Pion TURN: The Go-Native Option

**Pion TURN** is part of the Pion WebRTC ecosystem—a pure Go implementation of WebRTC and its supporting protocols. Unlike Coturn and Restund, Pion TURN is primarily designed as an embeddable library rather than a standalone server, though it ships with a CLI tool (`turn-server`) that works as a drop-in TURN server.

### Key Features

- Pure Go implementation—cross-platform, single binary, no C dependencies
- STUN/TURN/TURN-TLS support
- Native integration with `pion/webrtc` for in-process relay (zero-copy)
- JSON-based configuration
- Prometheus metrics built in
- Redis and PostgreSQL auth backends (via community packages)
- Permission-based allocation model

### Docker Deployment

```yaml
# docker-compose.yml
version: "3.8"

services:
  pion-turn:
    image: pion/turn:latest
    container_name: pion-turn
    restart: unless-stopped
    ports:
      - "3478:3478/udp"
      - "3478:3478/tcp"
      - "5349:5349/tcp"
      - "49152-65535:49152-65535/udp"
    volumes:
      - ./turn.json:/config/turn.json:ro
      - ./certs:/etc/pion/turn/certs:ro
    command: ["turn-server", "-config", "/config/turn.json"]
```

### Configuration

```json
{
  "port": 3478,
  "externalIP": "203.0.113.50",
  "realm": "turn.yourdomain.com",
  "authMechanism": "secret",
  "authSecret": {
    "key": "YOUR_SHARED_SECRET_HERE",
    "algorithm": "HMAC-SHA1"
  },
  "relayAddress": "0.0.0.0",
  "minPort": 49152,
  "maxPort": 65535,
  "tls": {
    "enabled": true,
    "cert": "/etc/pion/turn/certs/cert.pem",
    "key": "/etc/pion/turn/certs/key.pem",
    "port": 5349
  },
  "metrics": {
    "enabled": true,
    "port": 9090,
    "path": "/metrics"
  }
}
```

### Embedding in a Go Application

If you're building a WebRTC application in Go, Pion TURN's real power comes from embedding it directly:

```go
package main

import (
	"log"
	"github.com/pion/turn/v3"
)

func main() {
	server, err := turn.NewServer(turn.ServerConfig{
		Realm: "turn.yourdomain.com",
		AuthHandler: func(username, realm string, srcAddr net.Addr) ([]byte, bool) {
			// Custom auth logic here
			return []byte("secret"), true
		},
		PacketConnConfigs: []turn.PacketConnConfig{
			{
				PacketConn:            udpListener,
				RelayAddressGenerator: &turn.RelayAddressGeneratorStatic{
					RelayAddress: net.ParseIP("203.0.113.50"),
					Address:      "0.0.0.0",
				},
			},
		},
	})
	if err != nil {
		log.Fatal(err)
	}
	defer server.Close()

	select {} // Block forever
}
```

This approach eliminates the network hop between your TURN server and WebRTC media handler—ideal for high-performance, single-service deployments.

## Comparison Matrix

| Feature | Coturn | Restund | Pion TURN |
|---|---|---|---|
| **Language** | C/C++ | C | Go |
| **Binary Size** | ~1.2 MB | ~500 KB | ~10–15 MB |
| **Memory Footprint** | 50–200 MB | 5–20 MB | 30–100 MB |
| **Concurrency** | Multi-threaded | Single-threaded | Goroutines |
| **TLS / TURNS** | Yes (OpenSSL) | Yes (plugin) | Yes (crypto/tls) |
| **Redis / DB Auth** | Redis, MySQL, PG, Mongo | Limited | Redis, PG (community) |
| **Prometheus Metrics** | Yes | No | Yes |
| **Clustering** | Yes (Redis sync) | No | No (custom code) |
| **WebRTC Optimized** | Yes | Partially | Yes (native) |
| **REST API Auth** | Yes | No | Custom handler |
| **Active Maintenance** | High | Low–Medium | High |
| **Best For** | Production, enterprise | Embedded, homelab | Go apps, cloud-native |

## Performance Benchmarks

Performance varies based on hardware, network tuning, and workload. These are reference numbers from published benchmarks and community reports:

| Server | Hardware | Concurrent Allocations | Allocations/sec | Notes |
|---|---|---|---|---|
| **Coturn** | 1 vCPU / 1 GB RAM | ~500 | ~2,000 | Baseline small VPS |
| **Coturn** | 2 vCPU / 2 GB RAM | ~2,000 | ~5,000 | Sweet spot for most deployments |
| **Coturn** | 4 vCPU / 4 GB RAM | ~8,000 | ~10,000 | High-traffic production |
| **Restund** | 1 vCPU / 512 MB RAM | ~200–500 | ~1,000 | Single-threaded limit |
| **Pion TURN** | 2 vCPU / 2 GB RAM | ~5,000+ | ~7,000 | Goroutine concurrency shines |
| **Pion TURN** (in-process) | 2 vCPU / 2 GB RAM | ~10,000+ | N/A | Zero-copy with pion/webrtc |

**Bandwidth considerations**: TURN relay throughput is typically 70–85% of raw NIC bandwidth due to UDP encapsulation overhead. TLS adds ~10–15% CPU cost. On a 1 Gbps NIC, expect ~700–800 Mbps sustained relay throughput.

### Kernel Tuning Impact

Proper `sysctl` configuration can improve Coturn throughput by 20–30%. The UDP memory buffer settings shown earlier are essential for any server handling more than a few hundred concurrent allocations. Without them, you'll see packet drops under load.

## Integrating with Popular Self-Hosted Services

### Jitsi Meet

Jitsi Meet bundles Coturn by default in its Docker deployment. The configuration lives in the `coturn` service:

```yaml
# In Jitsi's docker-compose.yml
coturn:
  image: jitsi/coturn
  restart: unless-stopped
  environment:
    - PUBLIC_IP=${PUBLIC_IP}
    - COTURN_RELAY_PORT=3478
    - COTURN_LISTENING_PORT=3478
    - COTURN_TLS_LISTENING_PORT=5349
  volumes:
    - ${CONFIG}/coturn:/config:Z
  ports:
    - "3478:3478/udp"
    - "3478:3478/tcp"
    - "5349:5349/udp"
    - "5349:5349/tcp"
  network_mode: host
```

Jitsi's VideoBridge (`jvb`) auto-discovers the TURN server via the internal network. Enable REST auth in `turnserver.conf` for token-based allocation per conference.

### Nextcloud Talk

Nextcloud Talk uses Coturn for its WebRTC relay. Configuration is managed through `occ` commands:

```bash
# Set TURN server in Nextcloud
occ config:app:set spreed turn_servers --value \
  '{"servers":[{"urls":["turn:turn.yourdomain.com:3478?transport=udp","turn:turn.yourdomain.com:3478?transport=tcp","turns:turn.yourdomain.com:5349?transport=tcp"],"secret":"YOUR_SHARED_SECRET","protocols":"udp,tcp"}]}'

# Verify
occ config:app:get spreed turn_servers
```

A 2 vCPU / 2 GB VPS running Coturn handles ~500 concurrent Nextcloud Talk sessions comfortably.

### Matrix / Synapse

Matrix homeservers need TURN for VoIP calls between federated servers. Add this to your `homeserver.yaml`:

```yaml
turn_uris:
  - "turn:turn.yourdomain.com:3478?transport=udp"
  - "turn:turn.yourdomain.com:3478?transport=tcp"
  - "turns:turn.yourdomain.com:5349?transport=tcp"
turn_shared_secret: "YOUR_SHARED_SECRET_HERE"
turn_user_lifetime: "1h"
```

Both Coturn and Pion TURN work well with Matrix. Coturn is more common in the Matrix community due to its long history and Redis clustering support for large federations.

## Security Best Practices

Running a TURN server without proper authentication turns it into an **open relay**—anyone on the internet can use your bandwidth to relay traffic. Follow these rules:

### 1. Never Run an Open Relay

Always enable authentication. Coturn's `use-auth-secret` with HMAC tokens is the most practical approach:

```ini
use-auth-secret
static-auth-secret=YOUR_SECRET_KEY
```

Your application generates time-limited tokens:

```python
import hmac, hashlib, time, base64

def generate_turn_token(secret, username, lifetime=86400):
    expires = int(time.time()) + lifetime
    token = f"{username}:{expires}"
    signature = hmac.new(
        secret.encode(), token.encode(), hashlib.sha1
    ).digest()
    return base64.b64encode(signature).decode(), expires
```

### 2. Always Use TLS in Production

Deploy TURN over TLS (TURNS) on port 5349. Use Let's Encrypt for certificates:

```bash
certbot certonly --standalone -d turn.yourdomain.com

# Coturn needs combined cert + key in PEM format
cat /etc/letsencrypt/live/turn.yourdomain.com/fullchain.pem \
    /etc/letsencrypt/live/turn.yourdomain.com/privkey.pem \
    > /etc/coturn/certs/combined.pem
```

### 3. Restrict Relay Port Range

Limiting `min-port` and `max-port` makes firewall rules manageable and prevents port exhaustion:

```ini
min-port=49152
max-port=65535
```

### 4. Set User Quotas

Prevent any single user from consuming all relay capacity:

```ini
user-quota=12
total-quota=0
```

### 5. Disable the Admin Console

Coturn's CLI admin interface listens on port 5766. In production, disable it:

```ini
no-cli
```

### 6. Monitor and Alert

Enable Prometheus metrics and monitor:

- Total active allocations
- Allocation creation rate
- Authentication failure rate (spikes indicate abuse attempts)
- Bandwidth utilization

```bash
# Coturn Prometheus endpoint
curl http://localhost:9641/metrics
```

## Which Should You Choose?

**Choose Coturn if:**
- You're running Jitsi, Nextcloud Talk, Matrix, or any mainstream self-hosted communication tool
- You need clustering for horizontal scaling
- You want Redis/MySQL/PostgreSQL-backed authentication
- You need battle-tested production reliability

**Choose Restund if:**
- You're deploying on resource-constrained hardware (Raspberry Pi, edge devices)
- You have fewer than 100 concurrent sessions
- You prefer a minimal, single-binary solution
- You don't need clustering or advanced auth backends

**Choose Pion TURN if:**
- You're building a Go-based WebRTC application
- You want to embed the TURN server in your application process
- You need zero-copy relay with `pion/webrtc`
- You prefer JSON configuration and modern Go tooling

For the vast majority of self-hosters, **Coturn is the right choice**. It's the default for every major self-hosted communication platform, handles enterprise-scale traffic, and has the most mature feature set. The other two excel in their niches, but Coturn is the safe, proven option.

## Quick Start: Get Coturn Running in 5 Minutes

```bash
# 1. Create directory structure
mkdir -p ~/coturn/{config,certs}
cd ~/coturn

# 2. Generate a self-signed cert for testing
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem \
  -out certs/cert.pem -days 365 -nodes \
  -subj "/CN=turn.yourdomain.com"

# 3. Generate a shared secret
SECRET=$(openssl rand -hex 32)
echo "Shared secret: $SECRET"

# 4. Create config
cat > config/turnserver.conf << EOF
listening-port=3478
tls-listening-port=5349
min-port=49152
max-port=65535
external-ip=YOUR_PUBLIC_IP
cert=/etc/coturn/certs/cert.pem
pkey=/etc/coturn/certs/key.pem
lt-cred-mech
realm=turn.yourdomain.com
use-auth-secret
static-auth-secret=$SECRET
fingerprint
stale-nonce=3600
no-cli
verbose
EOF

# 5. Launch
docker run -d --name coturn --network host \
  -v $(pwd)/config/turnserver.conf:/etc/coturn/turnserver.conf:ro \
  -v $(pwd)/certs:/etc/coturn/certs:ro \
  coturn/coturn:latest

# 6. Test
turnutils_uclient -u testuser -w $(echo -n "testuser:$(date +%s):$SECRET" | openssl dgst -sha1 -hmac "$SECRET" -binary | base64) \
  -m 1000 YOUR_PUBLIC_IP
```

Replace `YOUR_PUBLIC_IP` with your server's public address and `turn.yourdomain.com` with your domain. Once verified, integrate the TURN server into your WebRTC application or self-hosted communication platform.

Your users' calls will thank you.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
