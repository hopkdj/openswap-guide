---
title: "Self-Hosted Device Farm & Remote Testing 2026: STF vs Selenoid vs Moon"
date: "2026-05-09"
tags: ["testing", "device-farm", "browser-automation", "mobile-testing", "docker", "kubernetes"]
draft: false
---

Running browser and mobile tests at scale requires access to real devices and browser instances. Cloud device farms like BrowserStack and Sauce Labs charge premium prices for what amounts to managed Selenium grids. For teams that need testing infrastructure under their own control, self-hosted device farms offer a cost-effective alternative with full data sovereignty.

## What Is a Self-Hosted Device Farm?

A device farm is a centralized platform that manages pools of testing resources — browsers, mobile devices, or virtual machines — and exposes them through standard automation APIs (Selenium WebDriver, Appium, Playwright). Instead of running tests on a developer's laptop or paying per-minute for cloud services, teams deploy their own infrastructure and route test traffic to it.

Self-hosted device farms solve several problems:

- **Cost control**: No per-minute billing. You pay for the hardware once and run unlimited tests.
- **Data privacy**: Test data, credentials, and internal URLs never leave your network.
- **Custom environments**: Install proprietary fonts, certificates, or network configurations that cloud providers don't support.
- **Unlimited concurrency**: Scale to as many parallel sessions as your hardware allows.

## OpenSTF (Smartphone Test Farm)

[OpenSTF](https://github.com/openstf/stf) is a web-based platform for managing and debugging smartphones and tablets at scale. Originally developed at CyberAgent in Japan, it remains one of the most comprehensive self-hosted device management solutions.

### Key Features

- **Real device management**: Control Android and iOS devices through a web interface. Remote screen sharing, touch simulation, and keyboard input work through the browser.
- **Device provisioning**: Reserve devices for exclusive use or share them across team members with time-based allocation.
- **App installation**: Push APKs and IPA files directly to connected devices through the web UI.
- **Remote debugging**: Access `adb` commands, logcat output, and device screenshots remotely.
- **User management**: Role-based access control with LDAP integration.

### Architecture

STF uses a microservice architecture with several components:

```yaml
version: "3.8"
services:
  stf-app:
    image: openstf/stf:latest
    ports:
      - "7100:3000"
    environment:
      - STF_SECRET=your-secret-key
      - STF_AUTH_URL=http://your-domain:7100/auth/mock/
    depends_on:
      - rethinkdb
      - provider

  stf-provider:
    image: openstf/stf:latest
    command: stf provider --name provider01 --min-port 7400 --max-port 7700
    privileged: true
    volumes:
      - /dev/bus/usb:/dev/bus/usb
    depends_on:
      - rethinkdb

  rethinkdb:
    image: rethinkdb:2.4
    ports:
      - "28015:28015"
    volumes:
      - rethinkdb_data:/data

  adb:
    image: sorccu/adb:latest
    network_mode: host
    privileged: true

volumes:
  rethinkdb_data:
```

### Strengths and Limitations

STF excels at real device management. The web interface is intuitive, and the ability to remotely control physical phones through a browser is powerful. However, STF requires physical devices connected via USB to the provider nodes. It doesn't support headless browser testing or virtual device emulation.

## Selenoid

[Selenoid](https://github.com/aerokube/selenoid) is a lightweight Selenium Hub replacement that runs browsers inside Docker containers. Developed by Aerokube, it's designed for high-density browser testing without the overhead of full virtual machines.

### Key Features

- **Container-based browsers**: Each test session gets an isolated Docker container running the exact browser version needed.
- **Video recording**: Built-in video capture of test sessions for debugging failed tests.
- **Log retention**: Console logs, VNC streams, and session metadata are preserved for post-mortem analysis.
- **Multiple browser support**: Chrome, Firefox, Opera, and Microsoft Edge in various versions.
- **Low resource overhead**: Containers start in under a second, significantly faster than VM-based solutions.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  selenoid:
    image: aerokube/selenoid:latest-release
    ports:
      - "4444:4444"
    volumes:
      - ./config:/etc/selenoid
      - /var/run/docker.sock:/var/run/docker.sock
      - ./logs:/opt/selenoid/logs
    environment:
      - TZ=UTC

  selenoid-ui:
    image: aerokube/selenoid-ui:latest-release
    ports:
      - "8080:8080"
    command: ["--selenoid-uri", "http://selenoid:4444"]
    depends_on:
      - selenoid
```

Browser configuration is managed through a `browsers.json` file:

```json
{
  "chrome": {
    "default": "120.0",
    "versions": {
      "120.0": {
        "image": "selenoid/chrome:120.0",
        "port": "4444",
        "tmpfs": {"/tmp": "size=512m"}
      },
      "119.0": {
        "image": "selenoid/chrome:119.0",
        "port": "4444",
        "tmpfs": {"/tmp": "size=512m"}
      }
    }
  },
  "firefox": {
    "default": "121.0",
    "versions": {
      "121.0": {
        "image": "selenoid/firefox:121.0",
        "port": "4444"
      }
    }
  }
}
```

### Strengths and Limitations

Selenoid is ideal for browser testing at scale. The container-based approach means you can run hundreds of parallel sessions on a single powerful server. Video recording and log capture make debugging straightforward. However, Selenoid only supports browsers — it cannot run mobile device tests or native app automation.

## Moon (by Aerokube)

[Moon](https://github.com/aerokube/moon) is Aerokube's Kubernetes-native browser automation platform. It extends the Selenoid concept to cloud-native environments, providing elastic scaling and multi-tenant support through Kubernetes operators.

### Key Features

- **Kubernetes-native**: Deploys as a Kubernetes operator, managing browser pods automatically.
- **Elastic scaling**: Browser pods scale up and down based on test queue depth.
- **Multi-tenant support**: Different teams can have isolated browser pools with separate quotas.
- **Quota management**: Resource limits per user or team prevent runaway test suites from consuming all capacity.
- **Cloud provider integration**: Works with any Kubernetes distribution — EKS, GKE, AKS, or on-prem.

### Kubernetes Deployment

```yaml
apiVersion: moon.aerokube.com/v1
kind: Moon
metadata:
  name: moon-cluster
  namespace: testing
spec:
  api:
    port: 4444
  quota:
    default:
      chrome: 100
      firefox: 50
  browsers:
    chrome:
      defaultVersion: "120.0"
      versions:
        - version: "120.0"
          image: "selenoid/chrome:120.0"
        - version: "119.0"
          image: "selenoid/chrome:119.0"
    firefox:
      defaultVersion: "121.0"
      versions:
        - version: "121.0"
          image: "selenoid/firefox:121.0"
  resources:
    limits:
      cpu: "1"
      memory: "1Gi"
    requests:
      cpu: "500m"
      memory: "512Mi"
```

### Strengths and Limitations

Moon is the best choice for organizations already running Kubernetes. The operator pattern provides seamless integration with existing CI/CD pipelines, and the quota system ensures fair resource allocation across teams. The main limitation is complexity — you need a working Kubernetes cluster and familiarity with operators.

## Comparison Table

| Feature | OpenSTF | Selenoid | Moon |
|---------|---------|----------|------|
| **Primary Use** | Real mobile devices | Browser testing | Kubernetes browser testing |
| **Device Support** | Android, iOS (physical) | Browsers only | Browsers only |
| **Deployment** | Docker Compose | Docker Compose | Kubernetes Operator |
| **Scalability** | Limited by USB ports | Hundreds per host | Elastic (cluster-wide) |
| **Video Recording** | No | Yes | Yes |
| **VNC Access** | Yes (screen sharing) | Yes | Yes |
| **Quota Management** | Device reservation | Basic | Advanced (per-tenant) |
| **Multi-Tenant** | Limited (user roles) | No | Yes |
| **API** | REST + WebSocket | Selenium WebDriver | Selenium WebDriver |
| **Min Hardware** | USB-connected devices | Any Docker host | Kubernetes cluster |
| **License** | Apache 2.0 | Apache 2.0 | Commercial (free tier) |
| **GitHub Stars** | ~1,800+ | ~2,600+ | ~270+ |

## Choosing the Right Solution

**Choose OpenSTF when**: You need to test on real physical devices. If your application has mobile-specific features — camera access, GPS, push notifications, device-specific UI quirks — nothing replaces actual hardware. STF's web-based remote control makes it practical for distributed QA teams.

**Choose Selenoid when**: Your testing needs are browser-focused and you want maximum session density per server. Selenoid's container approach means a single 32-core machine can comfortably run 100+ parallel browser sessions. The built-in video recording and log capture eliminate the need for separate debugging infrastructure.

**Choose Moon when**: You have a Kubernetes cluster and need elastic scaling with multi-tenant support. Moon's quota system and operator-based deployment make it ideal for large organizations where multiple teams share testing infrastructure.

## Why Self-Host Your Testing Infrastructure?

Cloud device farms charge per minute of device usage. For teams running thousands of tests daily, these costs accumulate rapidly. A typical enterprise BrowserStack plan costs $150-400/month per seat, and that doesn't include custom environments or extended session timeouts.

Self-hosted infrastructure converts variable costs into fixed ones. A single server with 64GB RAM and 16 cores running Selenoid can replace a $500/month cloud plan. For organizations with existing hardware, the marginal cost is essentially zero.

Beyond economics, self-hosting provides control over your testing environment. You can install internal CA certificates, configure custom DNS entries, set up network throttling profiles, and capture full session artifacts — capabilities that are restricted or unavailable on shared cloud platforms.

For teams already running [Kubernetes batch schedulers](../volcano-vs-yunikorn-vs-kueue-kubernetes-batch-scheduler-guide-2026/) for workloads like data processing, Moon integrates naturally into the same cluster. Similarly, organizations using [container update tools](../watchtower-vs-diun-vs-dockcheck-docker-container-update-tools-2026/) for Docker infrastructure can apply the same automation patterns to their testing containers.

For teams managing browser testing alongside other [end-to-end testing tools](../self-hosted-e2e-testing-tools-playwright-cypress-selenium-guide-2026/), device farms provide the physical device layer that complements browser-based testing. Organizations already running [Kubernetes batch schedulers](../volcano-vs-yunikorn-vs-kueue-kubernetes-batch-scheduler-guide-2026/) can deploy Moon alongside their existing workload management infrastructure.

## FAQ

### What is the difference between a device farm and a browser grid?

A device farm manages physical hardware — smartphones, tablets, and sometimes IoT devices — providing remote access through a web interface. A browser grid (like Selenium Grid or Selenoid) manages virtual browser instances running in containers or VMs. Device farms are essential for mobile testing; browser grids are better for web application testing at scale.

### Can Selenoid run mobile browser tests?

Selenoid runs desktop browser instances in Docker containers. It can simulate mobile viewport sizes and user agents, but it cannot run actual mobile browsers or native mobile apps. For real mobile testing, you need a solution like OpenSTF that connects to physical devices.

### Does OpenSTF support iOS devices?

Yes, OpenSTF supports both Android and iOS devices. iOS support requires macOS host machines with Xcode installed, as Apple's development tools are needed for device communication. Android devices work on Linux, macOS, and Windows hosts.

### How many parallel sessions can Selenoid handle?

Selenoid's session limit depends on your server's resources. Each browser container typically needs 512MB-1GB of RAM and 0.5-1 CPU core. A server with 64GB RAM and 16 cores can run 50-100 parallel Chrome sessions. Use `--limit` flag to set the maximum concurrent sessions.

### Is Moon free to use?

Moon offers a free Community Edition that supports up to 10 concurrent browser sessions. The Enterprise Edition provides unlimited sessions, advanced quota management, and support. For small teams, the free tier is sufficient for development and moderate CI/CD workloads.

### How do I connect physical devices to OpenSTF?

Connect devices via USB to the machine running the STF provider. Enable USB debugging on Android devices (Developer Options > USB Debugging). For iOS, trust the computer and ensure `usbmuxd` is running. Multiple devices can connect to a single provider through a USB hub.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Device Farm & Remote Testing 2026: STF vs Selenoid vs Moon",
  "description": "Compare OpenSTF, Selenoid, and Moon for self-hosted device farm and browser testing infrastructure. Includes Docker Compose configs, Kubernetes deployment, and pricing analysis.",
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
