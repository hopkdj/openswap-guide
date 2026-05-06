---
title: "Chaosblade vs Pumba vs Toxiproxy: Self-Hosted Chaos Engineering & Fault Injection 2026"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "chaos-engineering", "testing", "reliability"]
draft: false
---

Building resilient systems requires more than hope — it requires deliberate testing under failure conditions. Chaos engineering is the practice of intentionally injecting failures into your systems to verify that they degrade gracefully, recover automatically, and maintain acceptable performance during outages.

Three open-source tools lead the self-hosted chaos engineering space, each targeting different layers of the infrastructure stack: **Chaosblade** for comprehensive infrastructure-level chaos, **Pumba** for container-level fault injection, and **Toxiproxy** for network-level condition simulation. This guide compares their capabilities, deployment models, and ideal use cases.

## Chaosblade: Enterprise-Grade Chaos Engineering Platform

[Chaosblade](https://github.com/chaosblade-io/chaosblade) (6,300+ GitHub stars) is an open-source chaos engineering toolkit originally developed at Alibaba. It provides a comprehensive suite of fault injection capabilities spanning the entire infrastructure stack — from operating system resources to application-level behaviors.

**Key features:**

- **Multi-layer chaos experiments** — OS, container, application, network, and cloud resource faults
- **Rich experiment types** — CPU, memory, disk I/O, network delay/loss, process kill, JVM faults, Kubernetes chaos
- **CLI and API interfaces** — run experiments from command line or programmatically via REST API
- **Kubernetes operator** — deploy as a Kubernetes operator for cluster-wide chaos experiments
- **Experiment management** — create, schedule, and manage chaos experiments with reproducibility
- **Cloud provider support** — integrates with AWS, Alibaba Cloud, and other cloud APIs for resource-level faults
- **Observability integration** — connects with monitoring systems to measure impact during experiments

Chaosblade's breadth is its defining characteristic. While other tools focus on specific failure domains (containers, network proxies), Chaosblade covers everything from burning CPU cycles to killing Kubernetes pods to injecting JVM exceptions.

### Deploying Chaosblade with Docker

```yaml
services:
  chaosblade:
    image: chaosbladeio/chaosblade:latest
    container_name: chaosblade
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /lib/modules:/lib/modules
    command: blade create docker cpu fullload --docker-name myapp --cpu-percent 80
    restart: "no"
```

For Kubernetes deployments, Chaosblade provides an operator:

```yaml
apiVersion: chaosblade.io/v1alpha1
kind: ChaosExperiment
metadata:
  name: pod-network-delay
spec:
  scope: namespace
  target: pod
  action: network-delay
  desc: "Inject network delay on target pods"
  matchers:
  - name: namespace
    value: ["production"]
  - name: labels
    value: ["app=my-service"]
  - name: time
    value: ["5000"]
  - name: interface
    value: ["eth0"]
```

## Pumba: Container Chaos and Network Emulation

[Pumba](https://github.com/alexei-led/pumba) (3,000+ GitHub stars) is a container-focused chaos testing tool that provides network emulation, container killing, and resource stress testing. It operates by interacting with the Docker daemon to manipulate containers directly.

**Key features:**

- **Container lifecycle chaos** — kill, pause, and restart containers on schedule
- **Network emulation** — delay, loss, duplication, corruption, and reordering of network packets
- **Resource stress testing** — CPU, memory, and I/O stress on containerized workloads
- **TC-based networking** — uses Linux traffic control (tc) for realistic network condition simulation
- **Scheduling** — cron-like scheduling for recurring chaos experiments
- **Multiple Docker hosts** — support for Docker Swarm and multiple Docker daemon targets
- **No agent required** — runs as a single container with Docker socket access

Pumba excels at container-level chaos experiments. If you run Docker or Docker Swarm and want to test how your containers handle network degradation, resource starvation, or unexpected restarts, Pumba is purpose-built for this.

### Deploying Pumba with Docker

Pumba runs as a container with access to the Docker socket:

```yaml
services:
  pumba:
    image: gaiaadm/pumba:latest
    container_name: pumba
    privileged: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: >
      pumba netem --duration 5m --interval 1m delay --time 200 --jitter 50 --correlation 80 re2:myapp-*
    restart: unless-stopped
    labels:
      - "pumba.enable=true"
```

Common Pumba chaos commands:

```bash
# Add 100ms network delay with 20ms jitter to all containers matching pattern
pumba netem delay --time 100 --jitter 20 re2:my-service

# Kill random containers every 30 seconds
pumba kill --interval 30s re2:worker-*

# Stress CPU on matching containers
pumba stress --duration 2m --stress-cpu 2 re2:api-*
```

## Toxiproxy: Network Condition Simulation Proxy

[Toxiproxy](https://github.com/Shopify/toxiproxy) (12,000+ GitHub stars) is a TCP proxy developed by Shopify that simulates network conditions between your application and its dependencies. Instead of manipulating containers or infrastructure directly, Toxiproxy sits between services as a proxy and injects network faults at the TCP level.

**Key features:**

- **TCP proxy with fault injection** — sits between services and modifies traffic
- **Five toxicity types** — latency, bandwidth, slow_close, timeout, and slicer
- **API-driven configuration** — add, modify, and remove toxicities via REST API
- **Language-agnostic** — works with any TCP-based service (databases, caches, APIs)
- **Per-connection control** — apply different conditions to different connections
- **Lightweight** — single Go binary, minimal resource footprint
- **Client libraries** — official libraries for Go, Ruby, Python, Java, and Node.js

Toxiproxy's approach is fundamentally different from Chaosblade and Pumba. Instead of attacking the infrastructure, it attacks the network connection between services. This makes it ideal for testing how your application handles slow databases, intermittent cache connections, or flaky API dependencies.

### Deploying Toxiproxy with Docker

```yaml
services:
  toxiproxy:
    image: ghcr.io/shopify/toxiproxy:latest
    container_name: toxiproxy
    ports:
      - "8474:8474"  # API port
      - "10000-10100:10000-10100"  # Proxy ports
    restart: unless-stopped

  postgres-with-toxiproxy:
    image: postgres:16-alpine
    container_name: postgres
    environment:
      POSTGRES_PASSWORD: password
    restart: unless-stopped
```

Configure a proxy with latency and bandwidth limitations:

```bash
# Create a proxy for PostgreSQL with 200ms latency
curl -X POST http://localhost:8474/proxies   -d '{
    "name": "postgres",
    "listen": "0.0.0.0:10000",
    "upstream": "postgres:5432",
    "enabled": true
  }'

# Add latency toxicity
curl -X POST http://localhost:8474/proxies/postgres/toxics   -d '{
    "name": "slow-postgres",
    "type": "latency",
    "toxicity": 1.0,
    "attributes": { "latency": 200, "jitter": 50 }
  }'

# Add bandwidth limitation (50 KB/s)
curl -X POST http://localhost:8474/proxies/postgres/toxics   -d '{
    "name": "throttled-postgres",
    "type": "bandwidth",
    "toxicity": 1.0,
    "attributes": { "rate": 50 }
  }'
```

## Feature Comparison

| Feature | Chaosblade | Pumba | Toxiproxy |
|---------|-----------|-------|-----------|
| **Primary target** | Full infrastructure stack | Docker containers | TCP connections |
| **Approach** | Direct fault injection | Container manipulation | Proxy-based interception |
| **Fault types** | CPU, memory, disk, network, process, JVM, K8s | Container kill/pause, network, resource stress | Latency, bandwidth, timeout, slow_close, slicer |
| **Kubernetes support** | Native operator | Limited (via Docker) | No (network-level only) |
| **Docker support** | Yes | Yes (primary) | Yes (runs in container) |
| **Scheduling** | Experiment management | Cron-like scheduling | Manual via API |
| **Resource usage** | Moderate (multi-component) | Low (single container) | Minimal (single Go binary) |
| **Configuration** | CLI + YAML experiments | CLI + Docker labels | REST API + JSON |
| **Observability** | Built-in metrics and reporting | Log-based | API-based status |
| **Complexity** | High (many components) | Medium | Low (simple proxy) |
| **Best for** | Comprehensive chaos programs | Container resilience testing | Application-level fault tolerance |

## Which Chaos Tool Should You Choose?

**Choose Chaosblade if:**
- You need comprehensive fault injection across the entire stack
- You run Kubernetes and want native operator integration
- You want to test JVM applications, cloud resources, and OS-level faults
- You are building a formal chaos engineering practice with experiment management

**Choose Pumba if:**
- You run Docker or Docker Swarm and want container-level chaos
- You need realistic network emulation with tc-based traffic control
- You want simple, recurring chaos experiments with cron-like scheduling
- You prefer a single-container deployment with Docker socket access

**Choose Toxiproxy if:**
- You want to test application-level fault tolerance without touching infrastructure
- You need to simulate slow databases, flaky caches, or degraded API connections
- You prefer a lightweight, API-driven approach
- You want per-connection fault control with programmatic management

## Why Practice Chaos Engineering?

Chaos engineering is not about breaking things — it is about building confidence that your systems can handle failure gracefully. Without deliberate failure injection, you only discover resilience gaps during actual outages, when the cost of failure is highest.

Self-hosted chaos engineering tools let you run experiments in staging and production environments without relying on external SaaS platforms. This is critical for organizations with data sovereignty requirements or those running entirely on-premises infrastructure. Running chaos experiments regularly builds institutional knowledge about system behavior under stress and identifies failure modes before they impact users.

The three tools in this guide complement each other well. Toxiproxy tests application-level fault tolerance, Pumba validates container resilience, and Chaosblade exercises the full infrastructure stack. For teams building comprehensive resilience programs, using all three in combination provides coverage from the TCP layer up to the Kubernetes orchestration layer.

For complementary reliability practices, see our [circuit breaker and fault tolerance guide](../2026-05-01-self-hosted-circuit-breaker-envoy-haproxy-linkerd-fault-tolerance-guide/) for architectural patterns that work alongside chaos engineering. If you want to understand the foundational chaos testing concepts, our [original fault injection comparison](../2026-04-20-toxiproxy-vs-pumba-vs-chaosmonkey-self-hosted-fault-injection-chaos-testing-guide-2026/) covers the tools that started the self-hosted chaos engineering movement.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Chaosblade vs Pumba vs Toxiproxy: Self-Hosted Chaos Engineering & Fault Injection 2026",
  "description": "Compare Chaosblade, Pumba, and Toxiproxy for self-hosted chaos engineering and fault injection testing. Infrastructure, container, and network-level chaos tools.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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

## FAQ

### Is chaos engineering safe for production environments?

Chaos engineering in production requires careful planning. Start with blast-radius-limited experiments that affect only a small percentage of traffic or a single availability zone. Always define clear rollback procedures and monitor experiments in real-time. Tools like Toxiproxy and Pumba allow you to disable faults instantly via API, providing a safety net. Never run chaos experiments in production without first validating them in staging environments.

### Can I run Chaosblade without Kubernetes?

Yes. Chaosblade supports Docker containers, standalone processes, and bare-metal servers in addition to Kubernetes. The Docker mode lets you inject faults into containers without a Kubernetes cluster. For process-level experiments, Chaosblade can target specific PIDs on the host system. The Kubernetes operator is optional — the CLI works independently.

### Does Toxiproxy support HTTP/2 or gRPC?

Toxiproxy operates at the TCP layer, so it works transparently with any TCP-based protocol including HTTP/2 and gRPC. Since it modifies raw TCP traffic, the application-layer protocol is irrelevant — latency, bandwidth, and connection faults are injected below the protocol layer.

### How does Pumba simulate network conditions?

Pumba uses Linux traffic control (tc) with the netem (network emulator) module to simulate network conditions. This provides realistic delay, jitter, packet loss, duplication, reordering, and corruption at the kernel level. The tc-based approach is more accurate than application-level delay simulation because it affects the actual network stack behavior.

### What is the difference between chaos engineering and load testing?

Load testing verifies system behavior under expected high-traffic conditions. Chaos engineering verifies system behavior under unexpected failure conditions — network partitions, server crashes, dependency failures, and resource exhaustion. They are complementary practices: load testing answers "can we handle the traffic?" while chaos engineering answers "can we survive the failures?"

### Can these tools work together in a single test?

Yes. A comprehensive chaos experiment might use Toxiproxy to add database latency while Pumba kills a random container and Chaosblade stresses CPU on the remaining nodes. The key is coordinating experiments so you can attribute observed behavior to specific faults. Run single-variable experiments first, then combine tools for multi-failure scenario testing once you understand individual failure modes.
