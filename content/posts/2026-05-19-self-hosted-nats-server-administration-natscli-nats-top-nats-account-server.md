---
title: "Self-Hosted NATS Server Administration: natscli vs nats-top vs nats-account-server"
date: "2026-05-19"
tags: ["nats", "messaging", "administration", "monitoring", "self-hosted"]
draft: false
---

NATS has emerged as one of the most popular open-source messaging systems for cloud-native architectures, offering a simple yet powerful publish-subscribe and request-reply communication layer. With over 19,000 GitHub stars and adoption by major organizations, NATS powers everything from microservices communication to IoT data pipelines. But managing a production NATS deployment requires more than just starting the server -- you need proper administration, monitoring, and account management tools.

## What Is NATS and Why Does It Need Administration Tools?

NATS (Neural Autonomic Transport System) is a high-performance messaging system originally developed by Derek Collison and now maintained by the Cloud Native Computing Foundation. It supports three core messaging patterns: publish-subscribe for fan-out communication, request-reply for synchronous RPC, and queue groups for load-balanced processing.

NATS 2.0 introduced a major security overhaul with JWT-based authentication, account isolation, and operator management. This means a single NATS server can now host multiple isolated "accounts" (tenants), each with its own users, permissions, and streams. Managing this multi-tenant setup requires dedicated tools.

Key administration needs for NATS include:
- **Server Monitoring:** Real-time visibility into connections, subscriptions, message throughput, and memory usage
- **Account Management:** Creating and managing JWT accounts, users, and permissions
- **CLI Operations:** Interacting with servers, accounts, and streams from the command line
- **Security Configuration:** Managing operator keys, account signing keys, and user credentials
- **JetStream Administration:** Managing streams, consumers, and message retention policies

## Comparison: natscli vs nats-top vs nats-account-server

| Feature | natscli | nats-top | nats-account-server |
|---------|---------|----------|---------------------|
| GitHub Stars | 773+ | 400+ | 92+ |
| Primary Purpose | Full CLI management | Server monitoring (top-like) | JWT account hosting |
| Language | Go | Go | Go |
| JetStream Support | Full (streams, consumers) | No | No |
| Account Management | Full (add/edit/delete) | No | Hosts JWT accounts |
| Real-Time Monitoring | Stats commands | Continuous top display | HTTP/NATS endpoints |
| Authentication | NKey/JWT/Token | NKey/Token | HTTP JWT hosting |
| Docker Image | Official | Community | Official |
| Multi-Server | Yes (context switching) | Single server | Multiple accounts |
| Stream/Consumer Admin | Yes | No | No |
| Installation | Binary/Go install | Binary/Go install | Binary/Docker |

## natscli: The Complete NATS Command-Line Interface

**Repository:** [nats-io/natscli](https://github.com/nats-io/natscli) -- 773+ stars

natscli is the official command-line interface for NATS, maintained by the core NATS team. It provides comprehensive management capabilities for servers, accounts, users, streams, and consumers. Think of it as the `kubectl` for NATS -- a single tool that handles virtually every administrative task.

### Key Features

- **Server Management:** Query server info, list connections, and monitor health
- **Account Operations:** Create accounts, add users, set permissions, and generate credentials
- **JetStream Administration:** Create streams, manage consumers, inspect messages, and monitor flow control
- **Context System:** Save server connection profiles for easy switching between environments
- **Benchmarking:** Built-in pub/sub throughput and latency testing

### Docker Deployment

```yaml
version: "3.8"

services:
  nats-server:
    image: nats:2.10-alpine
    container_name: nats-server
    command:
      - "--js"
      - "--http_port=8222"
      - "--config=/etc/nats/nats.conf"
    ports:
      - "4222:4222"
      - "8222:8222"
      - "6222:6222"
    volumes:
      - ./nats-data:/data
      - ./nats.conf:/etc/nats/nats.conf
    restart: unless-stopped

  natscli:
    image: natsio/natscli:latest
    container_name: natscli
    command: sleep infinity
    environment:
      - NATS_URL=nats://nats-server:4222
    depends_on:
      - nats-server
    restart: unless-stopped
```

### NATS Server Configuration

```conf
# nats.conf
server_name: "nats-prod-01"

listen: "0.0.0.0:4222"
http_port: 8222

jetstream {
  store_dir: "/data/jetstream"
  max_memory: 1GB
  max_file: 10GB
}

accounts: {
  APP: {
    users: [
      { user: "app_user", password: "SECRET" }
    ]
    jetstream: {
      max_memory: 512MB
      max_file: 5GB
    }
  }
  MONITOR: {
    users: [
      { user: "monitor", password: "MONITOR_SECRET" }
    ]
  }
}
```

### Common natscli Commands

```bash
# Add a server context
nats context add production --server nats://prod-server:4222

# Select a context
nats context select production

# List all connections
nats server list connections

# Create a JetStream stream
nats stream add ORDERS --subjects "orders.*" --max-msgs 1000000 --retention limits

# Monitor stream info
nats stream info ORDERS

# Publish a message
nats pub orders.new '{"item": "widget", "qty": 50}'

# Subscribe to a subject
nats sub "orders.*"

# Benchmark pub/sub performance
nats bench orders.bench --pub 1 --sub 4 --msgs 100000
```

## nats-top: Real-Time Server Monitoring

**Repository:** [nats-io/nats-top](https://github.com/nats-io/nats-top) -- 400+ stars

nats-top provides a `top`-like real-time monitoring interface for NATS servers. It displays live connection statistics, subscription counts, message throughput, and memory usage in a terminal dashboard that updates continuously.

### Key Features

- **Real-Time Dashboard:** Continuously updated view of server statistics
- **Connection Listing:** See all active connections with IP, uptime, and subscription count
- **Sort Controls:** Sort connections by subscriptions, pending bytes, or messages in/out
- **Slow Consumer Detection:** Identify connections that are falling behind on message processing
- **Lightweight:** Single Go binary with no external dependencies

### Installation and Usage

```bash
# Install via Go
go install github.com/nats-io/nats-top@latest

# Or download pre-built binary
curl -L https://github.com/nats-io/nats-top/releases/latest/download/nats-top-linux-amd64.tar.gz | tar xz
sudo mv nats-top /usr/local/bin/

# Connect to a local server
nats-top -s nats://localhost:4222

# Connect with credentials
nats-top -s nats://admin:secret@server:4222

# Sort by pending bytes (find slow consumers)
nats-top -s nats://localhost:4222 -sort pending_bytes
```

### Monitoring Output

```
NATS server version 2.10.18 (uptime: 14d 6h 23m)

Server:
  CPU:  0.3%  Go:  14  Connections:   240  Subscriptions:  1,847
  MEM: 156MB  Slots:  0  Routes:        4  Routes:           4

  In Msgs: 45,230    Bytes: 12.4 MB    Slow:  0
 Out Msgs: 128,450   Bytes: 34.7 MB    Slow:  0

Connections:
  CID      IP                    Subs    In Msgs     Out Msgs    Pending   Uptime
  142      10.0.1.15:49201       12      1,245       3,456       0 B       14d
  143      10.0.1.16:52100       8       892         2,100       1.2 KB    14d
  144      10.0.1.17:38456       24      4,500       12,300      0 B       14d
```

## nats-account-server: JWT Account Management

**Repository:** [nats-io/nats-account-server](https://github.com/nats-io/nats-account-server) -- 92+ stars

The NATS Account Server is a specialized component that hosts JWT (JSON Web Token) accounts for NATS 2.0+ deployments. It provides HTTP and NATS endpoints where NATS servers can fetch account configurations, enabling centralized account management across distributed server clusters.

### Key Features

- **JWT Account Hosting:** Stores and serves account JWTs to NATS servers
- **NKey-Based Security:** Uses NKey cryptographic signing for account verification
- **HTTP and NATS Protocols:** Accounts accessible via both HTTP REST and NATS messaging
- **Operator Management:** Supports operator-to-account trust chains
- **Hot Reloading:** Account changes propagate to servers without restart

### Docker Deployment

```yaml
version: "3.8"

services:
  nats-account-server:
    image: natsio/nats-account-server:latest
    container_name: nats-account-server
    command:
      - "--config=/etc/nats/account-server.conf"
    ports:
      - "9090:9090"
    volumes:
      - ./account-data:/data
      - ./account-server.conf:/etc/nats/account-server.conf
    restart: unless-stopped

  nats-server:
    image: nats:2.10-alpine
    container_name: nats-server
    command:
      - "--config=/etc/nats/nats.conf"
    ports:
      - "4222:4222"
    volumes:
      - ./nats.conf:/etc/nats/nats.conf
    depends_on:
      - nats-account-server
    restart: unless-stopped
```

### Account Server Configuration

```conf
# account-server.conf
host: "0.0.0.0"
port: 9090

store: {
  dir: "/data/accounts"
}

operator: "./operator.jwt"
system_account: "./system_account.jwt"

logging: {
  debug: false
  trace: false
}
```

### NATS Server Account Resolver Configuration

```conf
# nats.conf -- Configure NATS server to fetch accounts from account server
resolver: URL("http://nats-account-server:9090/jwt/v1/accounts/")

operator: ./operator.jwt
system_account: ./system_account.jwt
```

## Choosing the Right NATS Administration Tool

These three tools serve complementary purposes in a production NATS deployment:

**natscli** is your primary administration tool. Use it for day-to-day operations: creating streams, managing consumers, checking server health, benchmarking performance, and troubleshooting connectivity issues. Every NATS administrator should have natscli installed.

**nats-top** is your monitoring companion. Keep it running in a terminal session during operations to watch real-time server behavior. It excels at identifying slow consumers, connection spikes, and message throughput anomalies.

**nats-account-server** is your security backbone for multi-tenant deployments. When you need JWT-based authentication, account isolation, or operator-managed credentials, the account server provides the centralized account hosting that NATS servers query for authorization decisions.

### Security Best Practices for NATS Administration

1. **Use NKeys for Authentication:** NATS NKeys provide Ed25519-based authentication that is more secure than password-based auth
2. **Enable TLS:** Always encrypt NATS server connections with TLS certificates
3. **Separate System Account:** Use a dedicated system account for server-to-server communication
4. **Account Isolation:** Create separate accounts for each application or team
5. **Monitor Slow Consumers:** Set `max_pending` limits and monitor nats-top for slow consumer warnings

## Production Deployment Architecture

```
                    ┌─────────────────────────┐
                    │   nats-account-server    │
                    │   (JWT Account Hosting)  │
                    │   Port: 9090             │
                    └───────────┬─────────────┘
                                │ HTTP/NATS
                    ┌───────────▼─────────────┐
                    │     NATS Server 1       │
                    │   Port: 4222            │
                    │   Monitor: 8222         │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │     NATS Server 2       │
                    │   Port: 4222            │
                    │   Monitor: 8222         │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
    ┌─────────▼──────┐ ┌───────▼─────┐ ┌────────▼────────┐
    │   natscli      │ │  nats-top   │ │  Applications   │
    │  (Admin Ops)   │ │ (Monitoring)│ │  (Pub/Sub)      │
    └────────────────┘ └─────────────┘ └─────────────────┘
```

## Why Self-Host NATS Administration Tools?

Message broker administration is often an afterthought in infrastructure planning. Teams deploy NATS for its simplicity and performance, then manage it through ad-hoc scripts and manual telnet sessions. This approach works initially but becomes a significant operational risk as the messaging layer becomes the backbone of your microservices architecture.

Self-hosted NATS administration tools provide the visibility and control needed to run messaging infrastructure reliably. Real-time monitoring through nats-top reveals connection patterns, message throughput, and slow consumers before they cascade into service outages. The natscli tool provides a standardized interface for stream management, user provisioning, and server diagnostics that replaces fragile shell scripts.

Running these tools self-hosted rather than relying on external SaaS monitoring has important advantages. Your messaging traffic data stays within your network boundary, which is critical for compliance-regulated industries. Administration tools are available even during network partitions when SaaS services may be unreachable. And there are no per-server or per-connection licensing fees -- all three tools discussed here are completely open source.

For broader messaging infrastructure, see our [Knative Eventing vs APISIX vs NATS JetStream event gateway guide](../2026-05-06-knative-eventing-vs-apisix-event-bridge-vs-nats-jetstream-event-gateway-guide/). For message queue server options, our [NSQ vs Beanstalkd vs Artemis comparison](../2026-05-17-self-hosted-message-queue-servers-nsq-beanstalkd-artemis-guide/) covers lightweight alternatives. For RabbitMQ monitoring, check our [RabbitMQ monitoring dashboard guide](../2026-05-26-self-hosted-rabbitmq-monitoring-dashboard-rabbitscout-exporter-management-guide/).

## FAQ

### What is the difference between natscli and nats-top?

natscli is a full-featured command-line interface for managing NATS servers, accounts, streams, and consumers. nats-top is a specialized monitoring tool that provides a real-time, continuously updating dashboard of server statistics. Use natscli for administration tasks (creating, deleting, configuring) and nats-top for live monitoring.

### Does NATS support multi-tenancy?

Yes. NATS 2.0 introduced account-based multi-tenancy using JWT tokens. Each account is isolated from others, with its own users, permissions, and JetStream resources. The nats-account-server hosts these JWT accounts, and NATS servers fetch account configurations at startup and on-demand.

### How do I migrate from NATS 1.0 to NATS 2.0 accounts?

Migration requires creating an operator keypair, generating account JWTs for each existing user group, and reconfiguring your NATS servers to use the account resolver. The natscli tool provides commands like `nats account add` and `nats user add` to streamline the process. Plan for a maintenance window as the authentication model changes significantly.

### Can nats-top connect to a NATS cluster?

nats-top connects to a single NATS server at a time. In a clustered setup, you can connect to any node in the cluster to see its local connection statistics. For cluster-wide monitoring, you would need to run nats-top against each node separately or use NATS Server's monitoring HTTP endpoint with a dashboard tool.

### What is JetStream and do I need it?

JetStream is NATS's built-in persistence layer, providing message storage, stream management, and consumer groups. If you need message durability, replay capabilities, or exactly-once delivery semantics, enable JetStream with the `--js` flag. For simple fire-and-forget pub/sub, JetStream is optional. natscli provides full JetStream administration capabilities.

### How do I back up NATS JetStream data?

JetStream data is stored in the `store_dir` configured in your NATS server config. Back up this directory regularly using standard filesystem backup tools. For running servers, use `nats server request` to flush pending writes before taking a snapshot. NATS 2.10+ also supports stream snapshots via `nats stream backup`.

### Is the NATS Account Server required for single-tenant deployments?

No. For single-tenant or small deployments, you can configure accounts directly in the NATS server configuration file. The account server becomes valuable when you have multiple NATS servers that need to share account configurations, or when you need centralized JWT account management with hot reloading capabilities.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NATS Server Administration: natscli vs nats-top vs nats-account-server",
  "description": "Compare three open-source NATS administration tools: natscli (CLI management), nats-top (real-time monitoring), and nats-account-server (JWT account hosting). Includes Docker configs and production deployment guide.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
