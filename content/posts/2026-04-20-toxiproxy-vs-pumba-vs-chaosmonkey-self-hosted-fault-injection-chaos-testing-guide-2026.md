---
title: "Toxiproxy vs Pumba vs Chaos Monkey: Self-Hosted Fault Injection Guide 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "chaos-engineering", "fault-injection", "resilience-testing"]
draft: false
description: "Compare Toxiproxy, Pumba, and Chaos Monkey for self-hosted fault injection and chaos testing. Complete setup guides with Docker Compose configs and practical examples for building resilient distributed systems."
---

Building resilient distributed systems requires more than unit tests and load tests. You need to verify your applications survive real-world failures: network latency, dropped packets, service crashes, and infrastructure outages. Fault injection tools let you deliberately break things in staging environments so your production systems can handle failures gracefully.

This guide compares three self-hosted fault injection and chaos testing tools: **Toxiproxy** (Shopify), **Pumba** (Aleksei Babenko), and **Chaos Monkey** (Netflix). Each represents a different approach to chaos engineering — from network-level proxy manipulation to container lifecycle disruption to infrastructure-level instance termination.

For teams already practicing chaos engineering at the [kubernetes](https://kubernetes.io/) level, our [chaos engineering guide covering Litmus, Chaos Mesh, and Chaos Toolkit](../self-hosted-chaos-engineering-litmus-chaos-mesh-chaos-toolkit-guide-2026/) provides complementary tools. This article focuses on the network, container, and infrastructure layers where fault injection starts.

## Why Self-Host Fault Injection Tools?

Fault injection is a core practice of chaos engineering — the discipline of experimenting on a system to build confidence in its ability to withstand turbulent conditions. While cloud providers offer managed chaos testing services, self-hosted tools give you:

- **Full control over failure scenarios** — define exactly what breaks, when, and how
- **No data leaving your network** — all fault injection runs on your infrastructure
- **CI/CD integration** — run chaos tests automatically before every deployment
- **Cost predictability** — no per-test or per-hour charges from cloud vendors
- **Customizable toxics** — write your own fault injection logic when built-in options aren't enough

Whether you are testing database connection resilience, verifying retry logic, or validating circuit breakers, self-hosted fault injection tools integrate directly into your development and staging pipelines.

## Toxiproxy: Network Proxy for Deterministic Chaos

[Toxiproxy](https://github.com/Shopify/toxiproxy) was built by Shopify to prove that their applications don't have single points of failure. It acts as a TCP proxy between your application and its dependencies (databases, caches, APIs), allowing you to inject specific network conditions on demand.

**GitHub Stats:** 11,971 stars · Last updated April 2026 · Written in Go

### How Toxiproxy Works

Toxiproxy sits between your application and downstream services. When you configure a proxy, all traffic flows through Toxiproxy first, which can then apply "toxics" — fault conditions like latency, bandwidth limits, connection resets, or timeouts.

```
Your App ──► Toxiproxy (port 22220) ──► MySQL (port 3306)
              ↑
         Configure toxics via HTTP API
```

### Toxiproxy [docker](https://www.docker.com/) Compose Setup

```yaml
version: "3.8"

services:
  toxiproxy:
    image: ghcr.io/shopify/toxiproxy:latest
    container_name: toxiproxy
    ports:
      - "8474:8474"   # Control API
      - "22220:22220" # MySQL proxy
      - "22221:22221" # Redis proxy
      - "22222:22222" # PostgreSQL proxy
    command: >
      -config=/config/proxies.json
    volumes:
      - ./toxiproxy-config:/config
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: testdb
    ports:
      - "3306:3306"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Toxiproxy Configuration

Create `toxiproxy-config/proxies.json` to define your proxies:

```json
{
  "mysql_proxy": {
    "listen": "[::]:22220",
    "upstream": "mysql:3306",
    "enabled": true
  },
  "redis_proxy": {
    "listen": "[::]:22221",
    "upstream": "redis:6379",
    "enabled": true
  }
}
```

### Injecting Network Faults with Toxiproxy

Once the proxy is running, use the CLI or HTTP API to inject faults:

```bash
# Add 500ms latency with 20% jitter to MySQL responses
toxiproxy-cli toxic add -t latency -a latency=500,jitter=200 mysql_proxy

# Simulate a slow connection by limiting bandwidth to 100 KB/s
toxiproxy-cli toxic add -t bandwidth -a rate=100 mysql_proxy

# Drop all connections (simulates server down)
toxiproxy-cli toxic add -t timeout mysql_proxy

# Reset connections randomly (simulates unstable network)
toxiproxy-cli toxic add -t reset_peer mysql_proxy

# Remove a toxic to restore normal operation
toxiproxy-cli toxic remove --toxic latency mysql_proxy

# Check current proxy status
toxiproxy-cli list
```

### Toxiproxy Toxic Types

| Toxic | Effect | Use Case |
|-------|--------|----------|
| `latency` | Adds delay to data transmission | Test timeout handling and retry logic |
| `bandwidth` | Limits throughput rate | Verify behavior under slow network |
| `slow_close` | Delays TCP socket close | Test connection pool resilience |
| `timeout` | Stops all data transmission | Simulate complete network outage |
| `reset_peer` | Sends TCP RST packets | Test reconnection logic |
| `limit_data` | Closes connection after N bytes | Test partial response handling |

Toxiproxy's strength is **deterministic testing**. You control exactly which connections are affected and when, making it ideal for automated test suites. For teams that also use API mock servers in their testing pipeline, Toxiproxy pairs well with tools like [WireMock, Mockoon, and MockServer](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mockserver-guide-2026/) to create comprehensive test environments.

## Pumba: Container-Level Chaos Engineering

[Pumba](https://github.com/alexei-led/pumba) brings chaos engineering directly to Docker and containerd containers. Inspired by Netflix Chaos Monkey, Pumba can kill, stop, pause containers, inject network delays, and stress-test resources — all from a single tool.

**GitHub Stats:** 3,011 stars · Last updated April 2026 · Written in Go

### How Pumba Works

Pumba connects to the Docker API or containerd API to manage target containers. For network chaos, it creates a helper container that shares the target's network namespace, allowing it to manipulate traffic using Linux `tc` (traffic control) and `iptables`.

Pumba supports two network chaos methods:
- **netem** — manipulates outgoing traffic using Linux `tc`: delay, packet loss, corruption, duplication, rate limiting
- **iptables** — manipulates incoming traffic using `iptables`: packet loss with random or nth-packet matching

### Pumba Docker Setup

Pumba runs as a container itself, mounting the Docker socket to manage other containers:

```yaml
version: "3.8"

services:
  pumba:
    image: ghcr.io/alexei-led/pumba:latest
    container_name: pumba
    restart: "no"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: >
      --interval 30s
      netem --duration 20s
      delay --time 200 --jitter 50 --distribution normal
      re2:app-.*

  app-web:
    image: nginx:alpine
    container_name: app-web
    ports:
      - "8080:80"

  app-api:
    image: node:18-alpine
    container_name: app-api
    command: ["node", "server.js"]
```

### Pumba Chaos Commands

```bash
# Kill random containers matching a pattern every 30 seconds
pumba kill --interval 30s re2:app-.*

# Stop a specific container for 10 seconds, then restart
pumba stop --duration 10s app-api

# Pause all containers with "worker" in the name
pumba pause re2:.*worker.*

# Add 100ms network delay with 50ms jitter to all app containers
pumba netem --duration 60s delay --time 100 --jitter 50 re2:app-.*

# Simulate 10% packet loss on outgoing traffic
pumba netem --duration 60s loss --loss 10 re2:app-.*

# Duplicate 5% of packets (simulates network issues)
pumba netem --duration 60s duplicate --duplicate 5 re2:app-.*

# Stress test CPU (8 workers at 90% load) for 60 seconds
pumba stress --duration 60s --workers 8 --cpu-load 90 re2:app-.*

# Stress test memory (consume 256MB) for 30 seconds
pumba stress --duration 30s --vm-bytes 256M --vm 1 re2:app-.*
```

### Pumba Network Chaos Options

| Command | Effect | Underlying Technology |
|---------|--------|----------------------|
| `netem delay` | Add latency to egress traffic | Linux `tc` (traffic control) |
| `netem loss` | Drop outgoing packets | Linux `tc netem` |
| `netem corrupt` | Corrupt packet data | Linux `tc netem` |
| `netem duplicate` | Duplicate packets | Linux `tc netem` |
| `netem rate` | Limit bandwidth | Linux `tc TBF` |
| `iptables loss` | Drop incoming packets | Linux `iptables` |

Pumba's key advantage is **container lifecycle management**. Unlike Toxiproxy (which only affects network traffic), Pumba can kill, stop, pause, and restart entire containers. Combined with its ability to stress CPU and memory, it provides comprehensive chaos testing for containerized environments.

## Chaos Monkey: Infrastructure-Level Resilience Testing

[Chaos Monkey](https://github.com/Netflix/chaosmonkey) is the original chaos engineering tool created by Netflix. It randomly terminates virtual machine instances and containers running in production, forcing engineers to build services that survive infrastructure failures.

**GitHub Stats:** 16,825 stars · Last updated January 2025 · Written in Go

### How Chaos Monkey Works

Chaos Monkey integrates with [Spinnaker](https://spinnaker.io/), Netflix's continuous delivery platform. It discovers all running applications and their instances, then randomly terminates a subset during business hours. The randomness ensures that failures cannot be predicted or worked around — your systems must be genuinely resilient.

Chaos Monkey operates at the **infrastructure layer**, terminating entire VMs or containers rather than manipulating individual network connections. This tests a different failure mode than Toxiproxy or Pumba.

### Chaos Monkey Configuration

Chaos Monkey is configured through a YAML file that defines termination policies:

```yaml
chaosmonkey:
  enabled: true
  accounts:
    - name: my-account
      chaosMonkey:
        enabled: true
        meanTimeBetweenKillsInWorkDays: 5
        minTimeBetweenKillsInWorkDays: 1
        groupings:
          - cluster
          - region
        regions:
          - us-east-1
          - us-west-2
        exceptions:
          - account: my-account
            stack: production
            detail: critical-db
            cluster: postgres-primary
```

### Deployment with Spinnaker

```bash
# Deploy Chaos Monkey as a Docker container
docker run -d \
  --name chaosmonkey \
  -v /etc/chaosmonkey:/config \
  -e SPINNAKER_URL=http://spinnaker:8084 \
  ghcr.io/netflix/chaosmonkey:latest \
  --config /config/chaosmonkey.yml

# Verify it's running and connected to Spinnaker
docker logs chaosmonkey | grep "connected"
```

### Chaos Monkey Scheduling

Chaos Monkey respects configurable business hours and can be tuned for different environments:

| Setting | Description | Recommended Value |
|---------|-------------|-------------------|
| `meanTimeBetweenKillsInWorkDays` | Average days between terminations per group | 1-5 for staging, 5-30 for production |
| `minTimeBetweenKillsInWorkDays` | Minimum gap between terminations | 1 day |
| `groupings` | How to group instances for targeting | cluster, region, or app |
| `whitelist` | Applications exempt from termination | Leave empty for maximum coverage |

**Important note:** Chaos Monkey requires Spinnaker as a dependency, which adds significant operational overhead. If you do not already run Spinnaker, consider Toxiproxy or Pumba for simpler setups.

## Feature Comparison: Toxiproxy vs Pumba vs Chaos Monkey

| Feature | Toxiproxy | Pumba | Chaos Monkey |
|---------|-----------|-------|--------------|
| **Primary Focus** | Network proxy toxics | Container chaos | Infrastructure termination |
| **Fault Types** | Latency, bandwidth, timeout, reset | Kill, stop, pause, netem, stress | Instance termination |
| **Network Control** | TCP-level proxy | tc + iptables | None (full instance kill) |
| **Container Support** | Docker, standalone | Docker, containerd | Spinnaker-managed |
| **CI/CD Integration** | Excellent (HTTP API + CLI) | Good (CLI-driven) | Limited (requires Spinnaker) |
| **Deterministic Testing** | Yes (exact control) | Yes (targeted patterns) | No (random by design) |
| **Setup Com[plex](https://www.plex.tv/)ity** | Low | Low | High (Spinnaker required) |
| **Language** | Go | Go | Go |
| **Stars** | 11,971 | 3,011 | 16,825 |
| **Best For** | Application-level resilience | Container resiliency | Infrastructure resiliency |

## Choosing the Right Tool

### Use Toxiproxy When:
- You need **deterministic, reproducible** fault injection for automated tests
- You want to test specific network conditions (latency, bandwidth, connection drops)
- Your architecture uses TCP-based services (databases, caches, message queues)
- You need fine-grained control over which connections are affected
- You want to integrate fault injection into CI/CD pipelines

### Use Pumba When:
- You run **Docker or containerd** workloads and want container-level chaos
- You need to test container lifecycle failures (kill, stop, pause, restart)
- You want to stress-test CPU and memory alongside network chaos
- You need asymmetric network control (different rules for incoming vs outgoing)
- You prefer a single tool for multiple chaos types

### Use Chaos Monkey When:
- You already run **Spinnaker** for continuous delivery
- You want to test **infrastructure-level** failures (VM termination)
- Your team is ready for production chaos engineering
- You need random, unpredictable failure injection (not deterministic testing)
- You operate at cloud scale with many instances per service

## Combining Tools: A Real-World Testing Pipeline

The most resilient teams use multiple tools together. Here is a practical testing pipeline:

```yaml
# docker-compose.test.yml — Full chaos testing environment
version: "3.8"

services:
  # Network fault injection layer
  toxiproxy:
    image: ghcr.io/shopify/toxiproxy:latest
    ports:
      - "8474:8474"
      - "22220:22220"
    command: -config=/config/proxies.json
    volumes:
      - ./proxies.json:/config/proxies.json

  # Container chaos layer
  pumba:
    image: ghcr.io/alexei-led/pumba:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: >
      --interval 60s
      netem --duration 10s
      delay --time 50 re2:api-.*

  # Your application
  api-server:
    build: ./api
    depends_on:
      - db
      - redis

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: testpass

  redis:
    image: redis:7-alpine

  # Load testing to exercise the system under chaos
  load-tester:
    image: ghcr.io/grafana/k6:latest
    command: run /scripts/load_test.js
    volumes:
      - ./k6-scripts:/scripts
    depends_on:
      - api-server
```

This setup runs load tests while Toxiproxy injects network latency and Pumba introduces container-level disruptions, giving you a realistic picture of how your system handles compound failures.

If you are also interested in measuring system behavior under sustained traffic, check out our [k6 vs Locust vs Gatling load testing comparison](../k6-vs-locust-vs-gatling-self-hosted-load-testing-guide-2026/) for complementary tools that pair well with fault injection.

## FAQ

### What is the difference between chaos engineering and fault injection?

Chaos engineering is the broader discipline of experimenting on systems to build confidence in their ability to withstand turbulent production conditions. Fault injection is a specific technique within chaos engineering where you deliberately introduce faults (network delays, service crashes, packet loss) to test how systems respond. Toxiproxy focuses on fault injection at the network layer, while Chaos Monkey practices chaos engineering at the infrastructure level.

### Can I use Toxiproxy in production?

Toxiproxy is primarily designed for testing and staging environments. While it is production-capable, most teams use it during development and CI/CD to verify resilience before deploying. In production, tools like Chaos Monkey or Pumba (with careful scheduling) are more appropriate because they test real infrastructure failures rather than simulated network conditions.

### Does Pumba require root access?

Pumba needs access to the Docker socket (`/var/run/docker.sock`) which typically requires root or docker group membership. For network chaos using `tc` and `iptables`, the helper container requires the `NET_ADMIN` capability. In production, configure appropriate RBAC policies and consider running Pumba in a dedicated chaos testing namespace.

### How do I choose between Toxiproxy and Pumba?

Choose Toxiproxy if you need fine-grained control over individual network connections (e.g., adding latency to specific database queries). Choose Pumba if you want to test container lifecycle failures (killing, pausing, restarting containers) alongside network chaos. For comprehensive testing, use both: Toxiproxy for connection-level faults and Pumba for container-level disruptions.

### Is Chaos Monkey still actively maintained?

Chaos Monkey's last significant update was in early 2025, and it remains stable but not actively developed. The tool is mature and production-proven at Netflix's scale. However, many teams have moved toward newer alternatives like Chaos Mesh or Litmus Chaos for Kubernetes-native chaos engineering. Chaos Monkey's main requirement — Spinnaker integration — can be a barrier for teams not already using that platform.

### How do I automate fault injection in my CI/CD pipeline?

Toxiproxy is the easiest to automate thanks to its HTTP API. A typical CI/CD flow looks like:

```bash
# 1. Start Toxiproxy and dependencies
docker-compose up -d toxiproxy db redis

# 2. Run baseline tests (no faults)
toxiproxy-cli list
pytest tests/ --resilience

# 3. Inject faults and rerun tests
toxiproxy-cli toxic add -t latency -a latency=500 mysql_proxy
pytest tests/ --resilience --tolerant

# 4. Clean up
docker-compose down
```

Pumba can also be scripted via its CLI with `--interval` flags for recurring chaos patterns during extended test runs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Toxiproxy vs Pumba vs Chaos Monkey: Self-Hosted Fault Injection Guide 2026",
  "description": "Compare Toxiproxy, Pumba, and Chaos Monkey for self-hosted fault injection and chaos testing. Complete setup guides with Docker Compose configs and practical examples for building resilient distributed systems.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
