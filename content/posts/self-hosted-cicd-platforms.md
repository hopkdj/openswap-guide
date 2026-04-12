---
title: "Best Self-Hosted CI/CD Platforms 2026: Woodpecker vs Gitea Actions vs Drone"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy", "cicd", "devops"]
draft: false
description: "A comprehensive comparison of the best self-hosted CI/CD platforms in 2026. Learn how to deploy Woodpecker CI, Gitea Actions, and Drone with Docker, and choose the right pipeline tool for your infrastructure."
---

Continuous Integration and Continuous Deployment (CI/CD) is the backbone of modern software development. For teams and individuals who value data sovereignty, privacy, and full control over their build infrastructure, self-hosted CI/CD platforms are no longer a nice-to-have — they are a necessity.

In 2026, the landscape of self-hosted CI/CD has matured significantly. GitHub Actions set the standard for pipeline-as-code, and several open-source projects now bring that same developer experience to your own servers. This guide compares the three most compelling options: Woodpecker CI, Gitea Actions, and Drone — with practical setup instructions for each.

## Why Self-Host Your CI/CD Pipeline

Running your own CI/CD infrastructure delivers concrete advantages that cloud-hosted alternatives simply cannot match:

**Full data control.** Your source code, build artifacts, secrets, and logs never leave your network. For organizations handling sensitive intellectual property, regulated data, or client projects, this is often a compliance requirement rather than an optional preference.

**Unlimited build minutes.** Cloud CI providers charge by the minute or by concurrent job slots. With self-hosted infrastructure, your only limits are the hardware you provision. Running hundreds of builds a day costs nothing beyond your server's electricity.

**Custom build environments.** Need a specific GPU, a licensed compiler, or access to internal network resources? Self-hosted runners can tap into any hardware or network topology you control.

**Cost predictability.** A single VPS with 8 CPU cores and 16 GB RAM costs roughly $40–60/month and can handle the CI/CD workload of dozens of repositories. Compare that to per-minute billing on cloud platforms during heavy development sprints.

**No vendor lock-in.** Your pipelines are defined in YAML files checked into your repository. If you switch platforms later, the migration is a configuration change, not a rewrite.

## Woodpecker CI: The Lightweight Contender

Woodpecker CI is a community-driven fork of the original Drone CI. After Drone was acquired by Harness in 2021, the community created Woodpecker to keep the project truly open-source and independently governed. Today, Woodpecker is one of the most actively maintained CI/CD projects in the self-hosted space.

### Architecture

Woodpecker follows a simple server-agent model:

- **Server** — receives webhooks from your Git platform, schedules pipelines, and serves the web UI
- **Agent** — pulls jobs from the server, executes pipeline steps inside isolated containers, and reports results back

The architecture supports multiple agents across different machines, making it easy to scale horizontally.

### Key Features

- Native integration with Gitea, GitHub, GitLab, and Bitbucket
- Pipeline-as-code using `.woodpecker.yml` in your repository root
- Docker, Kubernetes, and local process backends
- Built-in secret management with per-repository scoping
- Matrix pipelines for testing across multiple environments simultaneously
- Approval gates for deployment stages
- Plugin ecosystem with 100+ community plugins

### Installation with Docker Compose

Here is a production-ready Docker Compose setup for Woodpecker CI behind a reverse proxy:

```yaml
version: "3.8"

services:
  woodpecker-server:
    image: woodpeckerci/woodpecker-server:latest
    container_name: woodpecker-server
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - woodpecker-data:/var/lib/woodpecker
    restart: unless-stopped
    environment:
      - WOODPECKER_OPEN=true
      - WOODPECKER_HOST=https://ci.example.com
      - WOODPECKER_GITEA=true
      - WOODPECKER_GITEA_URL=https://git.example.com
      - WOODPECKER_GITEA_CLIENT=${GITEA_CLIENT_ID}
      - WOODPECKER_GITEA_SECRET=${GITEA_CLIENT_SECRET}
      - WOODPECKER_AGENT_SECRET=${AGENT_SECRET}

  woodpecker-agent:
    image: woodpeckerci/woodpecker-agent:latest
    container_name: woodpecker-agent
    command: agent
    restart: unless-stopped
    depends_on:
      - woodpecker-server
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WOODPECKER_SERVER=woodpecker-server:9000
      - WOODPECKER_AGENT_SECRET=${AGENT_SECRET}

volumes:
  woodpecker-data:
```

Generate a secure agent secret and start the stack:

```bash
AGENT_SECRET=$(openssl rand -hex 32)
export AGENT_SECRET

# Set your OAuth credentials from Gitea
export GITEA_CLIENT_ID="your-client-id"
export GITEA_CLIENT_SECRET="your-client-secret"

docker compose up -d
```

### Example Pipeline

A typical Go project pipeline in Woodpecker looks like this:

```yaml
steps:
  lint:
    image: golangci/golangci-lint:latest
    commands:
      - golangci-lint run ./...

  test:
    image: golang:1.22
    commands:
      - go test -v -race -coverprofile=coverage.out ./...
    environment:
      CGO_ENABLED: "1"

  build:
    image: golang:1.22
    commands:
      - go build -ldflags="-s -w" -o ./bin/app ./cmd/server

  docker:
    image: plugins/docker
    settings:
      repo: registry.example.com/myapp
      tags: [latest, "${CI_COMMIT_SHA:0:8}"]
      username:
        from_secret: registry_user
      password:
        from_secret: registry_pass
    when:
      branch: main
      event: push
```

The matrix feature lets you test across multiple Go versions in parallel:

```yaml
steps:
  test:
    image: golang:${GO_VERSION}
    commands:
      - go test -v ./...
    matrix:
      GO_VERSION:
        - "1.21"
        - "1.22"
        - "1.23"
```

## Gitea Actions: GitHub Actions Compatibility

Gitea Actions is a built-in CI/CD system that ships with Gitea starting from version 1.19. Its defining feature is near-complete compatibility with GitHub Actions workflows. If your team already uses GitHub Actions syntax, migrating to Gitea Actions requires zero changes to your pipeline files.

### Architecture

Gitea Actions integrates directly into the Gitea application:

- **Gitea server** — acts as both the Git platform and the workflow orchestrator
- **Act runner** — a standalone runner application (based on the `act` project) that executes workflow jobs

The tight integration means no separate CI server to manage — everything lives inside your existing Gitea instance.

### Key Features

- Full GitHub Actions workflow syntax compatibility (`.github/workflows/*.yml`)
- Reuse thousands of existing GitHub Actions from the marketplace
- No additional server to deploy — runs inside Gitea
- Artifact storage and caching built into Gitea
- Runner labels for targeting specific hardware (Linux, Windows, ARM64)
- Secret and variable management at organization, repository, and environment levels

### Installation

If you already run Gitea, enabling Actions requires two steps:

**Step 1:** Enable Actions in your `app.ini`:

```ini
[actions]
ENABLED = true
```

**Step 2:** Deploy an act runner:

```yaml
version: "3.8"

services:
  gitea:
    image: gitea/gitea:latest
    container_name: gitea
    ports:
      - "127.0.0.1:3000:3000"
      - "127.0.0.1:2222:22"
    volumes:
      - gitea-data:/data
    restart: unless-stopped

  gitea-runner:
    image: gitea/act_runner:latest
    container_name: gitea-runner
    restart: unless-stopped
    depends_on:
      - gitea
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - runner-config:/config
    environment:
      - CONFIG_FILE=/config/config.yaml
      - GITEA_INSTANCE_URL=http://gitea:3000
      - GITEA_RUNNER_REGISTRATION_TOKEN=${RUNNER_TOKEN}
      - GITEA_RUNNER_NAME=docker-runner
      - GITEA_RUNNER_LABELS=ubuntu-latest:docker://node:16-bullseye,ubuntu-22.04:docker://node:16-bullseye

volumes:
  gitea-data:
  runner-config:
```

Register the runner by obtaining a registration token from your Gitea instance:

```bash
# Get the token from Gitea admin settings, then:
export RUNNER_TOKEN="your-registration-token"
docker compose up -d gitea-runner
```

### Example Workflow

Because Gitea Actions uses GitHub Actions syntax, existing workflows work out of the box:

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: npm

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-node${{ matrix.node-version }}
          path: coverage/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Push to registry
        run: |
          echo "${{ secrets.REGISTRY_PASS }}" | docker login registry.example.com -u ${{ secrets.REGISTRY_USER }} --password-stdin
          docker push myapp:${{ github.sha }}
```

The `actions/checkout`, `actions/setup-node`, and `actions/upload-artifact` actions all work without modification because Gitea Actions fetches them from the GitHub Actions marketplace at runtime.

## Drone CI: The Enterprise-Grade Option

Drone CI, now owned by Harness, remains available as an open-source project. It pioneered the container-native CI/CD approach where every pipeline step runs inside an ephemeral Docker container. Drone's commercial backing gives it enterprise features that community projects are still catching up to.

### Architecture

Drone's architecture is nearly identical to Woodpecker's (Woodpecker was originally forked from Drone):

- **Server** — webhook receiver, pipeline scheduler, and web UI
- **Runner** — job executor that communicates with the server via gRPC

The key difference is that Drone's open-source version has some feature limitations compared to the paid Harness offering.

### Key Features

- Container-native pipeline execution (each step is a container)
- Pipeline-as-code with `.drone.yml`
- Support for GitHub, Gitea, GitLab, Bitbucket, and Bitbucket Server
- Approval gates and deployment targets
- Secrets management with HashiCorp Vault integration
- Pipeline signing and verification for supply chain security
- Shared pipeline configurations via templates

### Installation

```yaml
version: "3.8"

services:
  drone-server:
    image: drone/drone:2
    container_name: drone-server
    ports:
      - "127.0.0.1:8080:80"
    volumes:
      - drone-data:/data
    restart: unless-stopped
    environment:
      - DRONE_GITEA_SERVER=https://git.example.com
      - DRONE_GITEA_CLIENT_ID=${GITEA_CLIENT_ID}
      - DRONE_GITEA_CLIENT_SECRET=${GITEA_CLIENT_SECRET}
      - DRONE_RPC_SECRET=${RPC_SECRET}
      - DRONE_SERVER_HOST=ci.example.com
      - DRONE_SERVER_PROTO=https
      - DRONE_USER_CREATE=username:admin,admin:true

  drone-runner:
    image: drone/drone-runner-docker:1
    container_name: drone-runner
    restart: unless-stopped
    depends_on:
      - drone-server
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DRONE_RPC_PROTO=http
      - DRONE_RPC_HOST=drone-server
      - DRONE_RPC_SECRET=${RPC_SECRET}
      - DRONE_RUNNER_CAPACITY=2
      - DRONE_RUNNER_NAME=docker-runner

volumes:
  drone-data:
```

Start the stack:

```bash
export RPC_SECRET=$(openssl rand -hex 16)
export GITEA_CLIENT_ID="your-client-id"
export GITEA_CLIENT_SECRET="your-client-secret"

docker compose up -d
```

### Example Pipeline

```yaml
kind: pipeline
type: docker
name: default

steps:
  - name: lint
    image: golangci/golangci-lint:latest
    commands:
      - golangci-lint run --timeout=5m

  - name: test
    image: golang:1.22
    commands:
      - go test -v -cover ./...
    environment:
      GOFLAGS: -mod=readonly

  - name: build
    image: golang:1.22
    commands:
      - go build -o bin/app ./cmd/...

  - name: publish
    image: plugins/docker
    settings:
      repo: registry.example.com/myapp
      tags: ${DRONE_COMMIT_SHA:0:8}
      username:
        from_secret: docker_username
      password:
        from_secret: docker_password
    when:
      branch:
        - main
      event:
        - push

trigger:
  branch:
    - main
    - develop
  event:
    - push
    - pull_request
```

## Feature Comparison

| Feature | Woodpecker CI | Gitea Actions | Drone CI |
|---|---|---|---|
| **License** | Apache 2.0 | MIT | Apache 2.0 |
| **GitHub Actions Compatible** | No | Yes | No |
| **Git Platform Support** | Gitea, GitHub, GitLab, Bitbucket | Gitea only (native) | Gitea, GitHub, GitLab, Bitbucket |
| **Pipeline Syntax** | Custom YAML | GitHub Actions YAML | Custom YAML |
| **Matrix Builds** | Yes | Yes | Via include/exclude |
| **Caching** | Yes (volume, S3, GCS) | Yes (built-in actions) | Yes (plugins) |
| **Secret Management** | Built-in, per-repo | Org, repo, env scope | Built-in, Vault integration |
| **Kubernetes Backend** | Yes | Via custom runner | Via Kubernetes runner |
| **Pipeline Templates** | Yes (central config) | Via reusable workflows | Yes (shared configs) |
| **Web UI** | Modern, responsive | Gitea integrated | Clean, minimal |
| **Community Plugins** | 100+ | GitHub Actions marketplace | 50+ |
| **Active Development** | Very active | Very active | Moderate |
| **Governance** | Community (Codeberg) | Gitea org | Harness (commercial) |
| **Resource Usage** | Low (~200MB server) | Medium (inside Gitea) | Low (~200MB server) |
| **Minimum RAM** | 512 MB | 1 GB (with Gitea) | 512 MB |

## Performance and Resource Requirements

All three platforms share a similar resource profile because they rely on Docker for step isolation. Here is what you can expect on modest hardware:

**Woodpecker CI** — The server process uses approximately 150–250 MB of RAM and negligible CPU when idle. Each agent adds roughly 100 MB plus the memory required for active pipeline containers. A 4-core VPS with 4 GB RAM comfortably runs the server and 2 concurrent agents.

**Gitea Actions** — Since the orchestrator runs inside Gitea itself, the resource cost is absorbed by your existing Gitea instance. The act runner uses about 200 MB of RAM. If you already run Gitea on a 2 GB VPS, adding Actions requires bumping to 4 GB for comfortable operation.

**Drone CI** — Nearly identical to Woodpecker in resource consumption. The open-source version supports up to 2 concurrent pipelines per runner; the commercial version removes this limit.

For teams running fewer than 50 repositories with moderate build frequency, any single-server deployment handles the workload. Beyond that, adding agent nodes on separate machines provides linear scaling.

## Security Considerations

Self-hosting CI/CD shifts the security responsibility to you. Here are the essential hardening steps that apply to all three platforms:

**1. Network isolation.** Place the CI/CD server behind a reverse proxy with TLS termination. Never expose the internal gRPC port (used by agents) to the public internet. The Nginx configuration below demonstrates the pattern:

```nginx
server {
    listen 443 ssl http2;
    server_name ci.example.com;

    ssl_certificate /etc/ssl/certs/ci.example.com.crt;
    ssl_certificate_key /etc/ssl/private/ci.example.com.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**2. Runner isolation.** Run agents on a separate host or VM from the server. If a malicious pipeline escapes its container (rare but possible), it cannot reach the server's database or secrets.

**3. Container image verification.** Configure runners to only pull images from your private registry, or use image digest pinning to prevent supply chain attacks:

```yaml
# Woodpecker / Drone — pin to a specific image digest
steps:
  build:
    image: golang@sha256:abc123def456...
    commands:
      - go build ./...
```

**4. Secret scoping.** Never store production credentials in CI/CD secrets unless the pipeline explicitly requires them. Use short-lived tokens and per-repository secret scopes to limit blast radius.

**5. Resource limits.** Set Docker resource constraints on runner containers to prevent a runaway build from consuming all system resources:

```bash
# Limit each container to 2 CPU cores and 4 GB RAM
docker run --cpus=2 --memory=4g your-image
```

Both Woodpecker and Drone support per-pipeline resource limits in their configuration.

## Which Platform Should You Choose?

The decision comes down to your existing infrastructure and workflow preferences:

**Choose Gitea Actions if** you already run Gitea as your Git platform. The zero-setup integration and GitHub Actions compatibility make it the path of least resistance. Your team can reuse existing workflow files without any changes, and you maintain a single application instead of managing a separate CI server.

**Choose Woodpecker CI if** you want a lightweight, truly open-source CI/CD platform with strong community governance. It works with any major Git platform, has a clean modern UI, and is actively developed by a passionate community. The custom YAML syntax is straightforward and well-documented.

**Choose Drone CI if** you need enterprise features like Vault integration, pipeline signing, or commercial support. The open-source version is fully functional for most use cases, and the Harness backing means the project is unlikely to disappear.

For a brand-new self-hosted setup where you are choosing your entire stack from scratch, the combination of Gitea + Gitea Actions provides the most integrated experience. For teams migrating away from cloud CI who want maximum flexibility, Woodpecker CI offers the best balance of features, community, and independence.

## Getting Started Checklist

Once you have selected and deployed your platform, follow these steps to onboard your first repository:

1. **Register an OAuth application** on your Git platform and configure the client ID/secret in your CI/CD server settings
2. **Enable the repository** in the CI/CD web UI — this registers the webhook
3. **Add a pipeline file** (`.woodpecker.yml`, `.drone.yml`, or `.github/workflows/ci.yml`) to your repository
4. **Configure secrets** for any credentials your pipeline needs (registry passwords, deployment tokens)
5. **Trigger your first build** by pushing a commit — the webhook should fire automatically
6. **Monitor the build** in the web UI and iterate on your pipeline configuration

With your CI/CD pipeline running on your own infrastructure, every build, every artifact, and every log entry stays under your control. That is the foundation of a truly self-hosted development workflow.
