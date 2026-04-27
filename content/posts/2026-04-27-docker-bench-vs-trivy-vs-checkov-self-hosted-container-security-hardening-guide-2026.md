---
title: "Docker Bench vs Trivy vs Checkov: Self-Hosted Container Security Hardening Guide 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "security", "docker", "containers"]
draft: false
description: "Compare Docker Bench for Security, Trivy, and Checkov for self-hosted container hardening, CIS benchmark auditing, and misconfiguration scanning in 2026."
---

Running containers in production without security hardening is one of the most common mistakes teams make. A default Docker installation ships with dozens of configuration choices that deviate from security best practices — running as root, sharing the host namespace, exposing privileged ports, and mounting sensitive filesystem paths without restriction.

This guide compares three open-source tools that audit and enforce container security baselines: **Docker Bench for Security**, **Trivy**, and **Checkov**. Each takes a different approach to hardening, from CIS benchmark compliance checks to infrastructure-as-code misconfiguration scanning. We'll cover installation, configuration, and real-world usage so you can pick the right tool for your self-hosted environment.

## Why Harden Your Containers?

Containers share the host kernel, which means a misconfigured container can compromise the entire system. The CIS Docker Benchmark alone lists over 100 security checks covering host configuration, Docker daemon settings, container runtime options, and image build practices.

Hardening your containers addresses three core risks:

- **Privilege escalation** — containers running as root or with `--privileged` flag can escape to the host
- **Data exposure** — volumes mounted without `:ro` (read-only) flags allow write access to sensitive host paths
- **Network exposure** — containers binding to `0.0.0.0` without firewall rules are reachable from any network

The tools covered in this guide automate the detection of these misconfigurations, saving hours of manual audit work.

## Docker Bench for Security: CIS Benchmark Auditing

Docker Bench for Security is the official Docker Inc. tool that implements the CIS Docker Benchmark as an automated shell script. It runs dozens of checks against your Docker host configuration, daemon settings, and running containers.

| Attribute | Docker Bench for Security |
|---|---|
| **GitHub** | docker/docker-bench-security |
| **Stars** | 9,623 |
| **Language** | Shell |
| **Last Updated** | October 2024 |
| **License** | Apache 2.0 |
| **Focus** | CIS Docker Benchmark compliance |
| **Deployment** | Docker container or host script |

### How It Works

The tool connects to your Docker daemon (read-only via the socket) and runs a series of checks organized into categories:

1. **Host configuration** — kernel parameters, AppArmor/SELinux status, partitioning
2. **Docker daemon configuration** — storage driver, logging, live restore, user namespaces
3. **Daemon configuration files** — permissions on `/etc/docker/daemon.json`
4. **Container images and build files** — `docker commit`, `HEALTHCHECK` presence, update policies
5. **Container runtime** — privileged mode, PID namespace sharing, network mode, memory limits
6. **Docker security operations** — swarm mode, secrets management
7. **Docker swarm configuration** — manager/workernode settings (if applicable)

Each check is marked as **PASS**, **WARN**, or **INFO**, making it easy to spot failures at a glance.

### Installation via Docker Compose

The easiest way to run Docker Bench is inside a container with access to the host Docker socket and relevant filesystem paths:

```yaml
services:
  docker-bench-security:
    build: .
    cap_add:
      - audit_control
    labels:
      - docker_bench_security
    pid: host
    stdin_open: true
    tty: true
    volumes:
      - /var/lib:/var/lib:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /usr/lib/systemd:/usr/lib/systemd:ro
      - /etc:/etc:ro
```

Build and run:

```bash
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security
docker compose up
```

### Running Specific Tests

You can target specific test categories using the `-t` flag:

```bash
# Run only container runtime checks
docker run --rm --net host --pid host --userns host \
  --cap-add audit_control \
  -v /etc:/etc:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /usr/lib/systemd:/usr/lib/systemd:ro \
  -l docker_bench_security \
  docker/docker-bench-security \
  -t 5_check_docker_security
```

### Sample Output

```
[INFO] 1 - Host Configuration
[WARN] 1.1  - Ensure a separate partition for containers has been created
[PASS] 1.2  - Ensure the container host has been Hardened
[PASS] 1.3  - Ensure Docker is up to date
[WARN] 1.4  - Ensure only trusted users are allowed to control Docker daemon

[INFO] 5 - Container Runtime Configuration
[WARN] 5.4  - Ensure privileged containers are not running
[WARN] 5.9  - Ensure the host's network namespace is not shared
[PASS] 5.15 - Ensure the host's process namespace is not shared
```

## Trivy: Multi-Purpose Security Scanner

Trivy by Aqua Security is a comprehensive security scanner that goes far beyond container hardening. It scans container images, filesystems, Git repositories, and Kubernetes clusters for vulnerabilities, misconfigurations, secrets, and software bill of materials (SBOM).

| Attribute | Trivy |
|---|---|
| **GitHub** | aquasecurity/trivy |
| **Stars** | 34,718 |
| **Language** | Go |
| **Last Updated** | April 2026 |
| **License** | Apache 2.0 |
| **Focus** | Vulnerabilities, misconfigurations, secrets, SBOM |
| **Deployment** | CLI binary or Docker container |

### Container Misconfiguration Scanning

Trivy's config scanner supports Docker Compose, Dockerfile, and Kubernetes manifests. It checks against built-in policies derived from CIS benchmarks and best practices:

```bash
# Scan a Dockerfile for misconfigurations
trivy config Dockerfile

# Scan a docker-compose.yml file
trivy config docker-compose.yml

# Scan a directory of IaC files
trivy config ./deploy/
```

### Sample Misconfiguration Output

```
docker-compose.yml (dockerfile)
=============================
Tests: 7 (SUCCESSES: 5, FAILURES: 2, EXCEPTIONS: 0)
Failures: 2 (UNKNOWN: 0, LOW: 0, MEDIUM: 1, HIGH: 1, CRITICAL: 0)

HIGH: Image 'app:latest' uses 'latest' tag
══════════════════════════════════════════
Using 'latest' tag makes builds non-reproducible

MEDIUM: Container runs as root user
═══════════════════════════════════
No user specified in Dockerfile; defaults to root
```

### Installing Trivy

```bash
# Debian/Ubuntu
sudo apt-get install wget apt-transport-https gnupg
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | \
  sudo gpg --dearmor -o /usr/share/keyrings/trivy.gpg
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] \
  https://aquasecurity.github.io/trivy-repo/deb \
  generic main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy

# Or via Docker
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v $HOME/.cache:/root/.cache/ \
  aquasec/trivy:latest image nginx:latest
```

### Running as a Self-Hosted Scanner

You can run Trivy on a schedule via cron to audit all running images:

```bash
#!/bin/bash
# /usr/local/bin/trivy-audit.sh
trivy image --format table --severity HIGH,CRITICAL \
  $(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v '<none>') \
  >> /var/log/trivy-audit.log 2>&1
```

Add to crontab for daily runs:

```
0 2 * * * /usr/local/bin/trivy-audit.sh
```

## Checkov: Infrastructure-as-Code Security

Checkov by Bridgecrew (now part of Prisma Cloud) is a static analysis tool for infrastructure-as-code. It scans Terraform, CloudFormation, Kubernetes, Dockerfile, and Docker Compose files against hundreds of built-in policies covering security, compliance, and best practices.

| Attribute | Checkov |
|---|---|
| **GitHub** | bridgecrewio/checkov |
| **Stars** | 8,670 |
| **Language** | Python |
| **Last Updated** | April 2026 |
| **License** | Apache 2.0 |
| **Focus** | IaC misconfiguration scanning across cloud providers |
| **Deployment** | Python package or Docker container |

### Docker and Compose Scanning

Checkov includes policies specifically for Dockerfile and Docker Compose files:

```bash
# Scan a Dockerfile
checkov -f Dockerfile

# Scan a docker-compose file
checkov -f docker-compose.yml

# Scan a directory
checkov -d ./infrastructure/ --framework dockerfile
```

### Sample Output

```
Check: CKV_DOCKER_2: "Ensure that HEALTHCHECK instructions have been added to container images"
        FAILED for resource: /Dockerfile.main
        File: /Dockerfile.main:1-20
        Guide: https://docs.prismacloud.io/en/enterprise-edition/...

Check: CKV_DOCKER_7: "Ensure the base image uses a non latest version"
        PASSED for resource: /Dockerfile.main

Check: CKV2_DOCKERCOMPOSE_1: "Ensure container uses a non-root user"
        FAILED for resource: /docker-compose.yml
        File: /docker-compose.yml:5-15
```

### Installing Checkov

```bash
# Via pip
pip install checkov

# Via Docker
docker run --tty --volume /tmp:/tf \
  bridgecrew/checkov --directory /tf --framework dockerfile

# CI/CD integration (GitHub Actions example)
# .github/workflows/checkov.yml
name: Checkov
on: [push]
jobs:
  checkov:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Checkov
        uses: bridgecrewio/checkov-action@master
        with:
          directory: ./
          framework: dockerfile,dockercompose
```

## Comparison: Docker Bench vs Trivy vs Checkov

| Feature | Docker Bench | Trivy | Checkov |
|---|---|---|---|
| **Primary Focus** | CIS Docker Benchmark | Multi-purpose security | IaC misconfiguration |
| **Dockerfile Scanning** | Partial (build checks) | Yes | Yes (detailed policies) |
| **Docker Compose** | No (runtime only) | Yes | Yes |
| **Running Container Audit** | Yes (primary feature) | No | No |
| **Vulnerability Scanning** | No | Yes (CVE database) | No |
| **Secret Detection** | No | Yes | No |
| **Kubernetes Scanning** | No | Yes | Yes |
| **Custom Policies** | No | Yes (Rego/OPA) | Yes (Python/YAML) |
| **CI/CD Integration** | Manual/scripted | Native | Native (GitHub Actions) |
| **Output Formats** | Console only | JSON, SARIF, Table, CycloneDX | JSON, JUnit, SARIF, CLI |
| **Language** | Shell | Go | Python |
| **Stars** | 9,623 | 34,718 | 8,670 |
| **Best For** | Runtime compliance checks | Comprehensive scanning | Build-time IaC checks |

### When to Use Each Tool

- **Docker Bench** — Run periodically on production hosts to verify CIS Docker Benchmark compliance. Best for audit and compliance teams who need documented proof of security posture.
- **Trivy** — Use as your all-in-one scanner in CI/CD pipelines. Catches vulnerabilities, misconfigurations, and secrets in a single pass. Ideal for development teams.
- **Checkov** — Deploy as a pre-commit or CI gate for infrastructure-as-code files. Its granular policy controls make it the best choice for enforcing standards across Docker Compose and Dockerfile repositories.

## Recommended Hardening Workflow

For a complete self-hosted container security pipeline, combine all three tools at different stages:

### Stage 1: Build-Time Checks (Checkov + Trivy)

```yaml
# .github/workflows/container-security.yml
name: Container Security
on:
  push:
    paths:
      - 'Dockerfile'
      - 'docker-compose.yml'
jobs:
  checkov:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install checkov
      - run: checkov -f Dockerfile -f docker-compose.yml --framework dockerfile,dockercompose

  trivy-config:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: '.'
          severity: 'HIGH,CRITICAL'
          exit-code: '1'
```

### Stage 2: Image Scanning (Trivy)

After building your container image, scan for vulnerabilities:

```bash
docker build -t myapp:latest .
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:latest
```

### Stage 3: Runtime Auditing (Docker Bench)

Schedule Docker Bench to run weekly on production hosts:

```bash
#!/bin/bash
# /opt/scripts/docker-bench-audit.sh
cd /opt/docker-bench-security
docker compose up --exit-code-from docker-bench-security \
  2>&1 | tee /var/log/docker-bench-$(date +%Y%m%d).log
```

```cron
0 3 * * 0 /opt/scripts/docker-bench-audit.sh
```

### Hardening Quick-Reference Checklist

```yaml
# /etc/docker/daemon.json - Essential security settings
{
  "userns-remap": "default",
  "live-restore": true,
  "no-new-privileges": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

## Hardened Docker Compose Example

Here's a production-ready compose file that passes most Docker Bench checks:

```yaml
services:
  app:
    image: myapp:1.2.3
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    tmpfs:
      - /tmp:size=100M
    volumes:
      - app-data:/data:rw
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - backend

  proxy:
    image: caddy:2-alpine
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    ports:
      - "127.0.0.1:8080:8080"
    networks:
      - backend

volumes:
  app-data:

networks:
  backend:
    driver: bridge
    internal: true
```

Key hardening principles applied:

- **Non-root user** — every container runs as UID 1000
- **Read-only filesystem** — mutable state isolated to tmpfs and named volumes
- **Capability dropping** — all capabilities dropped, only `NET_BIND_SERVICE` re-added where needed
- **No new privileges** — prevents privilege escalation via setuid binaries
- **Resource limits** — memory and CPU caps prevent runaway containers
- **Internal network** — backend network not exposed to host
- **Healthchecks** — enables automatic restart on failure
- **Pinned image tags** — no `latest` tags for reproducible builds

## Additional Hardening Tips

### Enable User Namespace Remapping

User namespace remapping maps container root to an unprivileged host user:

```bash
# /etc/docker/daemon.json
{
  "userns-remap": "default"
}

# Or map a specific range
{
  "userns-remap": "dockremap:dockremap"
}
```

### Enable AppArmor or SELinux Profiles

```bash
# Apply AppArmor profile to a container
docker run --security-opt apparmor=docker-default nginx:alpine

# Or use SELinux
docker run --security-opt label=type:container_t nginx:alpine
```

### Disable Inter-Container Communication

```bash
# Create an isolated network
docker network create --opt com.docker.network.bridge.enable_icc=false isolated-net

# Run containers on this network
docker run --network isolated-net myapp
```

### Use Content Trust for Image Verification

```bash
# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Pull only signed images
docker pull nginx:latest
```

For related reading on container security, see our [container image scanning guide](../self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide/) and [Kubernetes hardening comparison](../kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/). If you're also managing IaC security, check our [Checkov vs TFsec vs Trivy comparison](../checkov-vs-tfsec-vs-trivy-self-hosted-iac-security-scanning-2026/).

## FAQ

### What is the CIS Docker Benchmark?

The CIS Docker Benchmark is a set of security configuration guidelines published by the Center for Internet Security. It covers host configuration, Docker daemon settings, container images, and runtime options. Docker Bench for Security automates these checks, making compliance verification a single command.

### Can Trivy replace Docker Bench for Security?

Not entirely. Trivy excels at scanning container images and IaC files for misconfigurations and vulnerabilities, but it does not audit running containers or the Docker daemon configuration on the host. Docker Bench fills this gap by checking the live environment. For comprehensive coverage, use both: Trivy at build time and Docker Bench at runtime.

### Does Checkov scan running containers?

No. Checkov performs static analysis on infrastructure-as-code files (Dockerfile, docker-compose.yml, Terraform, etc.). It catches misconfigurations before deployment but cannot audit containers already running on a host. Pair it with Docker Bench for full lifecycle coverage.

### How often should I run container security audits?

Run Trivy scans on every build in your CI/CD pipeline (zero extra cost). Run Checkov as a pre-commit hook or PR check. Run Docker Bench on production hosts weekly via cron, and immediately after any Docker daemon configuration change or host update.

### What is the difference between vulnerability scanning and misconfiguration scanning?

Vulnerability scanning checks for known CVEs in package dependencies (e.g., OpenSSL 1.1.1 has CVE-2023-0464). Misconfiguration scanning checks for insecure settings (e.g., container running as root, privileged mode enabled). Trivy does both; Docker Bench and Checkov focus on misconfigurations only.

### Can I write custom policies for these tools?

Trivy supports custom policies via Rego (OPA) language for config scanning. Checkov allows custom policies in Python or YAML format. Docker Bench does not support custom policies — it strictly implements the CIS Docker Benchmark. If you need custom runtime checks, consider combining Docker Bench output with a custom script.

### Are these tools suitable for production environments?

Yes. All three tools are read-only by design. Docker Bench connects to the Docker socket in read-only mode. Trivy and Checkov analyze files without modifying them. None of these tools change your system configuration — they only report findings.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Docker Bench vs Trivy vs Checkov: Self-Hosted Container Security Hardening Guide 2026",
  "description": "Compare Docker Bench for Security, Trivy, and Checkov for self-hosted container hardening, CIS benchmark auditing, and misconfiguration scanning in 2026.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
