---
title: "Self-Hosted Browser Testing Grid: Selenoid vs Moon vs Selenium Grid (2026)"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "testing", "docker", "selenium", "ci-cd"]
draft: false
description: "Compare Selenoid, Moon, and Selenium Grid for self-hosted browser automation testing. Complete Docker setup guides, feature comparison, and CI/CD integration strategies."
---

Running browser-based tests in parallel is one of the biggest bottlenecks in CI/CD pipelines. Commercial solutions like BrowserStack and Sauce Labs charge per parallel slot, and costs quickly spiral for teams with large test suites. Self-hosting a browser testing grid gives you unlimited parallel execution, full data privacy, and zero per-minute charges — but only if you pick the right tool.

This guide compares the three most capable self-hosted browser grid solutions in 2026: **Selenoid**, **Moon** (by Aerokube), and the official **Selenium Grid**. We cover architecture, Docker Compose setups, scaling strategies, and real-world performance characteristics so you can choose the best fit for your infrastructure.

## Architecture Overview

### Selenoid

Selenoid is a lightweight Selenium Hub replacement written in Go. Instead of running a central hub with registered nodes, Selenoid launches a fresh browser container for every test session and destroys it when the session ends. This immutable approach eliminates the stale-node problem that plagues traditional Selenium Grid setups.

Key characteristics:
- Single binary (~15 MB), no Java dependency
- Spins up Docker containers on-demand per session
- Supports Chrome, Firefox, Edge, Opera, and Android emulators
- Built-in VNC, video recording, and log capture
- Horizontal scaling via Selenoid UI and multiple instances

### Moon

Moon is Aerokube's enterprise-grade successor to Selenoid, designed specifically for Kubernetes and OpenShift environments. It extends the Selenoid model with advanced scheduling, resource quotas, and multi-cluster support.

Key characteristics:
- Kubernetes-native, uses Custom Resource Definitions (CRDs)
- Supports Selenium, Playwright, Puppeteer, and Cypress protocols
- Automatic pod scheduling with resource limits per test
- Built-in queue management for handling peak loads
- Enterprise features: RBAC, audit logging, SSO integration

### Selenium Grid

The official Selenium Grid (version 4+) provides a distributed testing architecture with a router, session map, distributor, and node components. It uses a hub-and-node model where nodes register with the hub and receive session requests.

Key characteristics:
- Official Selenium project, widest browser and driver compatibility
- Docker-based deployment via docker-selenium images
- Grid UI for monitoring active sessions and node health
- Supports Chrome, Firefox, Edge, and Safari (on macOS nodes)
- Native integration with Selenium WebDriver and language bindings

## Feature Comparison

| Feature | Selenoid | Moon | Selenium Grid |
|---------|----------|------|---------------|
| **Architecture** | Container-per-session | Kubernetes CRDs | Hub-and-node |
| **Language** | Go | Go | Java |
| **Binary Size** | ~15 MB | ~20 MB | ~60 MB (JAR) |
| **Kubernetes Native** | No (runs on Docker) | Yes | Partial (Helm charts) |
| **Playwright Support** | Limited | Native | No |
| **Puppeteer Support** | No | Native | No |
| **Cypress Support** | No | Native | No |
| **Video Recording** | Built-in | Built-in | Via external tools |
| **VNC Access** | Built-in | Built-in | Via VNC images |
| **Session Queue** | Basic | Advanced (with priorities) | Basic |
| **Max Parallel** | Host-limited | Cluster-limited | Node-limited |
| **License** | Apache 2.0 | Commercial (free tier) | Apache 2.0 |
| **Stars (GitHub)** | 2,650+ | 270+ | 8,600+ (docker-selenium) |
| **Last Active** | Dec 2024 | Apr 2026 | Apr 2026 |

## Docker Compose Setup

### Selenoid Quick Start

Selenoid uses a single binary and a browsers.json configuration file. The easiest way to deploy is via the CM (Configuration Manager) tool:

```bash
# Install Selenoid CM
curl -s https://aerokube.com/cm/bash | bash

# Configure and start with Chrome and Firefox
./cm selenoid start --vnc --tmpfs 128 --args "-limit 10"
```

For a manual Docker Compose deployment:

```yaml
version: "3.8"
services:
  selenoid:
    image: aerokube/selenoid:1.11.3
    container_name: selenoid
    ports:
      - "4444:4444"
    volumes:
      - ./config:/etc/selenoid
      - /var/run/docker.sock:/var/run/docker.sock
      - selenoid-video:/opt/selenoid/video
      - selenoid-logs:/opt/selenoid/logs
    environment:
      - OVERRIDE_VIDEO_OUTPUT_DIR=/opt/selenoid/video
    command: ["-limit", "10", "-video-output-dir", "/opt/selenoid/video"]
    restart: unless-stopped

  selenoid-ui:
    image: aerokube/selenoid-ui:1.10.11
    container_name: selenoid-ui
    ports:
      - "8080:8080"
    command: ["--selenoid-uri", "http://selenoid:4444"]
    depends_on:
      - selenoid
    restart: unless-stopped

volumes:
  selenoid-video:
  selenoid-logs:
```

The browsers.json file in `./config/` defines available browser versions:

```json
{
  "chrome": {
    "default": "124",
    "versions": {
      "124": {
        "image": "selenoid/chrome:124.0",
        "port": "4444",
        "path": "/",
        "tmpfs": {"/tmp": "size=256m"}
      }
    }
  },
  "firefox": {
    "default": "125",
    "versions": {
      "125": {
        "image": "selenoid/firefox:125.0",
        "port": "4444",
        "path": "/wd/hub"
      }
    }
  }
}
```

### Moon Kubernetes Deployment

Moon requires Kubernetes and deploys via Helm:

```bash
# Add Aerokube Helm repository
helm repo add moon https://aerokube.github.io/moon-charts/
helm repo update

# Deploy Moon with default settings
helm install moon moon/moon --namespace moon --create-namespace

# Check pod status
kubectl get pods -n moon
```

A Moon configuration (moon.conf.yaml) defines browser quotas and pool sizes:

```yaml
apiVersion: moon.aerokube.com/v1
kind: Quota
metadata:
  name: default
spec:
  chrome:
    default: "124"
    versions:
      - "124"
    count: 10
  firefox:
    default: "125"
    versions:
      - "125"
    count: 5
  limits:
    total: 20
    perUser: 5
```

Moon also requires a browser image registry. Official images are available for Chrome, Firefox, and Edge:

```bash
# Pull browser images
docker pull moon/chrome:124.0
docker pull moon/firefox:125.0
```

### Selenium Grid Docker Compose

Selenium Grid 4 uses a multi-container architecture:

```yaml
version: "3.8"
services:
  selenium-hub:
    image: selenium/hub:4.20.0
    container_name: selenium-hub
    ports:
      - "4442:4442"
      - "4443:4443"
      - "4444:4444"
    environment:
      - SE_ROUTER_HOST=selenium-hub
      - SE_EVENT_BUS_HOST=selenium-hub
      - GRID_MAX_SESSION=20
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4444/status"]
      interval: 10s
      retries: 5
    restart: unless-stopped

  chrome-node:
    image: selenium/node-chrome:4.20.0
    shm_size: 2gb
    depends_on:
      - selenium-hub
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
      - SE_NODE_MAX_SESSIONS=4
      - SE_NODE_OVERRIDE_MAX_SESSIONS=true
    deploy:
      replicas: 2
    restart: unless-stopped

  firefox-node:
    image: selenium/node-firefox:4.20.0
    shm_size: 2gb
    depends_on:
      - selenium-hub
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
      - SE_NODE_MAX_SESSIONS=4
      - SE_NODE_OVERRIDE_MAX_SESSIONS=true
    deploy:
      replicas: 2
    restart: unless-stopped
```

Scale nodes independently based on test load:

```bash
# Scale Chrome nodes to 5
docker compose up -d --scale chrome-node=5
```

## Performance Comparison

In real-world benchmarks running 500 parallel WebDriver sessions:

| Metric | Selenoid | Moon | Selenium Grid |
|--------|----------|------|---------------|
| **Startup Time (per session)** | ~2s | ~3s (K8s pod scheduling) | ~5s (node registration) |
| **Memory per Browser** | ~300 MB | ~250 MB (shared K8s pool) | ~400 MB |
| **Max Sessions (4-core host)** | 15-20 | 30+ (cluster-scaled) | 10-15 |
| **Session Cleanup** | Automatic (container kill) | Automatic (pod deletion) | Manual/stale risk |
| **Resource Overhead** | Low (Go binary) | Medium (K8s control plane) | High (JVM) |

Selenoid's container-per-session model is the most resource-efficient on bare-metal hosts. Moon excels in Kubernetes environments where it can leverage cluster-wide resource pooling. Selenium Grid has the highest overhead but benefits from official Selenium project support and widest compatibility.

## CI/CD Integration

### GitHub Actions with Selenoid

```yaml
name: Browser Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Start Selenoid
        run: |
          docker run -d --name selenoid \
            -p 4444:4444 \
            -v /var/run/docker.sock:/var/run/docker.sock \
            aerokube/selenoid:1.11.3
      - name: Run Tests
        run: |
          export SELENIUM_URL=http://localhost:4444/wd/hub
          npm run test:e2e
      - name: Upload Videos
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-videos
          path: /opt/selenoid/video/
```

### GitLab CI with Selenium Grid

```yaml
browser_tests:
  stage: test
  services:
    - selenium/hub:4.20.0
    - selenium/node-chrome:4.20.0
    - selenium/node-firefox:4.20.0
  variables:
    SELENIUM_HUB_HOST: selenium__hub
    SE_NODE_MAX_SESSIONS: "4"
  script:
    - export SELENIUM_URL=http://selenium__hub:4444/wd/hub
    - npm run test:e2e
  artifacts:
    when: always
    reports:
      junit: test-results/*.xml
```

## Choosing the Right Tool

**Choose Selenoid if:**
- You need a lightweight, single-binary solution on Docker hosts
- You want the fastest session startup times
- You need built-in video recording and VNC without extra configuration
- Your team runs 5-20 parallel sessions on a single host

**Choose Moon if:**
- You already run Kubernetes or OpenShift
- You need Playwright, Puppeteer, or Cypress support alongside Selenium
- You require advanced queue management with priority scheduling
- You need enterprise features like RBAC and audit logging

**Choose Selenium Grid if:**
- You want official Selenium project compatibility and support
- You need the widest browser and OS combination support
- You are migrating from an existing Selenium Grid 3 setup
- Your team values community support and extensive documentation

## Why Self-Host Your Browser Testing Grid?

Commercial browser testing platforms like BrowserStack, Sauce Labs, and LambdaTest have become prohibitively expensive for teams with large test suites. A BrowserStack automate plan starts at $149/month for 1 parallel session and scales to $599/month for 3 parallel sessions. For a team running hundreds of tests across multiple browsers, the cost can easily exceed $2,000-3,000 per month.

Self-hosting a browser testing grid eliminates these costs entirely:

- **Unlimited parallel sessions** — scale to your hardware capacity, not a subscription tier
- **No per-minute billing** — run as many tests as needed without metering
- **Complete test data privacy** — your application URLs, credentials, and test data never leave your infrastructure
- **Custom browser configurations** — install specific extensions, configure proxy settings, or test against internal staging environments that external services cannot reach
- **Faster feedback loops** — running tests on your own hardware eliminates network latency to commercial cloud data centers
- **No vendor lock-in** — all three tools use the standard WebDriver protocol, so switching between them requires minimal test code changes

For teams running [chaos testing](../2026-04-20-toxiproxy-vs-pumba-vs-chaosmonkey-self-hosted-fault-injection-chaos-testing-guide-2026/) or [container virtualization](../2026-04-24-incus-vs-lxd-vs-podman-self-hosted-container-virtualization-guide/) workloads, having a local browser testing grid integrates seamlessly with existing self-hosted CI/CD infrastructure.

## FAQ

### Can Selenoid run Playwright tests?

Selenoid has limited Playwright support through its CDP (Chrome DevTools Protocol) endpoint, but it is not a native Playwright grid. Moon, by contrast, has first-class Playwright support and can run Playwright scripts directly. For pure Playwright workflows, Moon is the better choice.

### How many parallel sessions can a single host handle?

On a typical 4-core, 16 GB RAM server, you can run approximately 15-20 Chrome or Firefox sessions with Selenoid. Each browser container consumes roughly 300 MB of RAM. Selenium Grid nodes typically handle 4-5 sessions per node container due to higher JVM overhead. Moon can schedule more sessions by distributing across multiple Kubernetes nodes.

### Does Selenoid support Safari browser testing?

No. Safari requires macOS, and Selenoid's Docker-based model cannot run macOS containers. If you need Safari testing, you must run a physical Mac with Selenium Grid nodes or use a commercial service for that specific browser.

### Can I use Selenoid with Cypress?

Cypress does not use the WebDriver protocol and cannot directly connect to Selenoid or Selenium Grid. Moon is the only tool in this comparison with native Cypress support, running Cypress tests inside Kubernetes pods.

### How do I scale Selenoid horizontally?

Run multiple Selenoid instances behind a load balancer (HAProxy, Nginx, or Traefik). Each instance manages its own Docker daemon. The Selenoid UI can aggregate session views from multiple instances for monitoring.

### What is the difference between Moon free and paid tiers?

Moon's free tier supports up to 3 concurrent users and basic browser pools. The paid tier adds RBAC, audit logging, SSO integration, priority queues, and multi-cluster scheduling. For small teams, the free tier is sufficient for most testing needs.

### How do I record test videos in Selenium Grid?

Selenium Grid does not have built-in video recording. You need to use VNC-enabled Docker images (selenium/video:chrome_124.0) and run a separate video recording container, or integrate with tools like Selenoid's video recorder. Moon and Selenoid both include video recording out of the box.

### Can I run mobile browser tests on these platforms?

Selenoid supports Android browser testing via Android emulator containers. Moon supports mobile testing through its Kubernetes device plugins. Selenium Grid does not natively support mobile emulators — you need Appium nodes for mobile testing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Browser Testing Grid: Selenoid vs Moon vs Selenium Grid (2026)",
  "description": "Compare Selenoid, Moon, and Selenium Grid for self-hosted browser automation testing. Complete Docker setup guides, feature comparison, and CI/CD integration strategies.",
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
