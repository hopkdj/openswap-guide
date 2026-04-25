---
title: "Screwdriver CI vs Agola vs Prow: Self-Hosted CI/CD Platforms 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "ci-cd", "continuous-delivery"]
draft: false
description: "Compare three powerful self-hosted CI/CD platforms: Screwdriver CI (Yahoo), Agola (Sorint.lab), and Prow (Kubernetes SIGs). Deployment guides, feature comparison, and Docker Compose configs for building your own build infrastructure."
---

## Why Self-Host Your CI/CD Platform?

Public CI/CD services like GitHub Actions, CircleCI, and GitLab.com are convenient, but they come with limitations: per-minute billing, shared runners with unpredictable performance, and vendor lock-in. For teams running hundreds of builds daily, the costs add up quickly.

Self-hosted CI/CD platforms give you full control over your build infrastructure. You choose the hardware, manage the scheduling, and keep your source code and build artifacts on-premises. This is especially critical for organizations with compliance requirements (SOC 2, HIPAA, FedRAMP) that restrict where build artifacts can be processed.

Three mature open-source CI/CD platforms stand out in 2026: **Screwdriver CI** (developed and maintained by Yahoo), **Agola** (created by Sorint.lab), and **Prow** (the Kubernetes SIGs project that builds Kubernetes itself). Each takes a fundamentally different approach to continuous delivery.

## Screwdriver CI: The Yahoo Build Platform

Screwdriver began as an internal tool at Yahoo in 2012 to replace Jenkins, which had become unstable at their build scale. It was open-sourced in 2016 and rebuilt from scratch with modern architecture. Screwdriver is a pluggable, executor-agnostic service built on Node.js.

- **GitHub**: [screwdriver-cd/screwdriver](https://github.com/screwdriver-cd/screwdriver) — 1,042 stars, last updated April 2026
- **Language**: JavaScript (Node.js)
- **License**: BSD 3-Clause
- **Website**: [screwdriver.cd](http://screwdriver.cd)

### Architecture

Screwdriver follows a microservices architecture with distinct components:

| Component | Purpose | Docker Image |
|-----------|---------|-------------|
| API | REST API, build orchestration, webhooks | `screwdrivercd/screwdriver` |
| UI | Web dashboard for pipelines and builds | `screwdrivercd/ui` |
| Store | Artifact and log storage | `screwdrivercd/store` |
| Launcher | Build job entrypoint | `screwdrivercd/launcher` |
| Executor | Runs builds (Docker, Kubernetes, or Nomad) | `screwdrivercd/executor-docker` |

### Configuration

Screwdriver is configured via a `screwdriver.yaml` file in your repository root, similar to GitHub Actions:

```yaml
shared:
  image: node:20

jobs:
  main:
    requires: [~commit]
    steps:
      - install: npm install
      - test: npm test
      - build: npm run build
    environment:
      NODE_ENV: production
```

### Deployment with Docker Compose

A minimal Screwdriver deployment requires the API, UI, and a database:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: screwdriver
      POSTGRES_USER: sd
      POSTGRES_PASSWORD: sd-password
    volumes:
      - pg-data:/var/lib/postgresql/data

  screwdriver-api:
    image: screwdrivercd/screwdriver:latest
    ports:
      - "8080:8080"
    environment:
      SECRET: "your-secret-here"
      ECOSYSTEM_UI: "http://localhost:4200"
      STORE_URI: "http://localhost:8081"
      EXECUTOR_TYPE: "docker"
      SCM_GITHUB_ENABLED: "true"
      SCM_GITHUB_CLIENT: "your-github-oauth-client-id"
      SCM_GITHUB_SECRET: "your-github-oauth-secret"
      DATABASE_TYPE: "sequelize"
      DATABASE_DIALECT: "postgres"
      DATABASE_HOST: "postgres"
      DATABASE_PORT: 5432
      DATABASE_DATABASE: "screwdriver"
      DATABASE_USERNAME: "sd"
      DATABASE_PASSWORD: "sd-password"
    depends_on:
      - postgres

  screwdriver-ui:
    image: screwdrivercd/ui:latest
    ports:
      - "4200:80"
    environment:
      SDAPI_URI: "http://localhost:8080"

  screwdriver-store:
    image: screwdrivercd/store:latest
    ports:
      - "8081:8081"
    volumes:
      - store-data:/tmp/store

volumes:
  pg-data:
  store-data:
```

**Key considerations**: Screwdriver requires OAuth setup with your SCM provider (GitHub, GitLab, or Bitbucket). The `SECRET` environment variable must be a strong random string. For production, use the Kubernetes executor and the official Helm chart (`screwdriver-cd/screwdriver-chart`).

## Agola: CI/CD Redefined

Agola takes a radically different approach to CI/CD. Created by Sorint.lab, it is designed from the ground up as a distributed, highly available system where every component can scale independently. The core concept is **Runs** — containerized task workflows that support fan-in, fan-out, and matrix execution patterns.

- **GitHub**: [agola-io/agola](https://github.com/agola-io/agola) — 1,610 stars, last updated September 2025
- **Language**: Go
- **License**: Apache 2.0
- **Website**: [agola.io](https://agola.io)

### Architecture

Agola's architecture is unique — it can run as a single process for small deployments or scale to a distributed cluster:

| Component | Purpose |
|-----------|---------|
| Config Store | Distributed configuration management |
| Scheduler | Orchestrates run execution across executors |
| Executor | Runs tasks in containers (Docker or Kubernetes) |
| Gateway | Web UI and API gateway |
| Notifier | Handles notifications and webhooks |

### Run Definition

Agola uses a `.agola/config.yml` file in your repository:

```yaml
runs:
  - name: test
    when:
      branch:
        - main
        - develop
    tasks:
      - name: unit-test
        runtime:
          type: pod
          containers:
            - image: golang:1.22
        steps:
          - type: clone
          - type: run
            command: |
              go mod download
              go test ./...
      - name: build
        depends:
          - unit-test
        runtime:
          type: pod
          containers:
            - image: golang:1.22
        steps:
          - type: clone
          - type: run
            command: go build -o myapp ./cmd/main.go
```

### Deployment with Docker Compose

Agola ships with an official `agolademo` that includes both Agola and Gitea for a complete self-contained CI/CD environment:

```yaml
name: agolademo

services:
  agola:
    image: "sorintlab/agolademo"
    command: serve --components all-base,executor
    configs:
      - source: agola
        target: /config.yml
    networks:
      net1:
        ipv4_address: 172.30.0.2
    ports:
      - "8000:8000"
    volumes:
      - agola-data:/data/agola
      - /var/run/docker.sock:/var/run/docker.sock

  gitea:
    image: gitea/gitea:1.21.6
    restart: always
    environment:
      - USER_UID=1000
      - USER_GID=1000
    configs:
      - source: gitea
        target: /data/gitea/conf/app.ini
    networks:
      net1:
        ipv4_address: 172.30.0.3
    volumes:
      - gitea-data:/data

networks:
  net1:
    ipam:
      driver: default
      config:
        - subnet: 172.30.0.0/16
          gateway: 172.30.0.1

volumes:
  agola-data:
  gitea-data:

configs:
  agola:
    file: ./agola/config.yml
  gitea:
    file: ./gitea/app.ini
```

**Key considerations**: Agola's `all-base,executor` mode combines all control plane components with the executor in a single process — ideal for small teams. For larger deployments, split these into separate services. Agola supports GitHub, GitLab, and Gitea as SCM providers simultaneously in a single installation.

## Prow: Kubernetes-Native CI/CD

Prow is the CI/CD system that builds the Kubernetes project itself. Developed by the Kubernetes SIGs, it is a Kubernetes-native system that runs as a set of microservices within a Kubernetes cluster. Prow uses GitHub pull requests as its primary interface — commenting `/test` on a PR triggers the build.

- **GitHub**: [kubernetes-sigs/prow](https://github.com/kubernetes-sigs/prow) — 282 stars, last updated April 2026
- **Language**: Go
- **License**: Apache 2.0
- **Documentation**: [prow.k8s.io](https://prow.k8s.io)

### Architecture

Prow is a collection of Kubernetes-native microservices, each with a specific responsibility:

| Component | Purpose |
|-----------|---------|
| Deck | Web UI for viewing jobs and status |
| Horologium | Triggers periodic and cron jobs |
| Plank | Creates and manages ProwJobs (Kubernetes CRDs) |
| Sinker | Cleans up completed and orphaned ProwJobs |
| Hook | Receives GitHub webhooks and triggers jobs |
| Tide | Manages the merge queue with automatic retesting |
| Deck | Dashboard and job log viewer |

### Pipeline Definition

Prow uses `prow.yaml` files in your repository or a centralized `config.yaml`:

```yaml
presubmits:
  - name: pull-myproject-test
    always_run: true
    decorate: true
    spec:
      containers:
        - image: golang:1.22
          command:
            - make
          args:
            - test
          resources:
            requests:
              cpu: 500m
              memory: 512Mi

postsubmits:
  - name: post-myproject-deploy
    branches:
      - main
    decorate: true
    spec:
      containers:
        - image: golang:1.22
          command:
            - make
          args:
            - deploy
```

### Deployment on Kubernetes

Prow is designed to run on Kubernetes. A minimal deployment requires applying the Prow manifests:

```bash
# Install Prow CRDs
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/prow/main/cluster/deck_deployment.yaml

# Deploy core Prow components
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/prow/main/cluster/hook_deployment.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/prow/main/cluster/plank_deployment.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/prow/main/cluster/sinker_deployment.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/prow/main/cluster/horologium_deployment.yaml

# Configure Prow (create prow configmap)
kubectl create configmap config \
  --from-file=config.yaml=./prow-config.yaml \
  --namespace=prow

# Deploy Tide for PR management
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/prow/main/cluster/tide_deployment.yaml
```

**Key considerations**: Prow requires a running Kubernetes cluster — it cannot run on plain Docker. It is tightly integrated with GitHub and uses GitHub App or OAuth for authentication. The Tide component provides automatic PR merging when all tests pass, similar to GitHub's branch protection merge queue.

## Feature Comparison

| Feature | Screwdriver CI | Agola | Prow |
|---------|---------------|-------|------|
| **Language** | Node.js | Go | Go |
| **GitHub Stars** | 1,042 | 1,610 | 282 |
| **Last Updated** | April 2026 | September 2025 | April 2026 |
| **License** | BSD 3-Clause | Apache 2.0 | Apache 2.0 |
| **Minimum Infra** | Docker Compose | Docker Compose | Kubernetes required |
| **Web UI** | Full-featured | Built-in | Deck dashboard |
| **SCM Support** | GitHub, GitLab, Bitbucket | GitHub, GitLab, Gitea | GitHub (primary) |
| **Executor** | Docker, K8s, Nomad | Docker, Kubernetes | Kubernetes pods |
| **Pipeline Config** | `screwdriver.yaml` | `.agola/config.yml` | `prow.yaml` / configmap |
| **PR-based Trigger** | Via webhooks | Via webhooks | Native (`/test` comments) |
| **Auto-merge** | No | No | Yes (Tide) |
| **Cron Jobs** | Yes | Yes | Yes (Horologium) |
| **Matrix Builds** | Via parallel jobs | Native fan-in/fan-out | Via ProwJob templates |
| **Artifact Storage** | Built-in Store | Volumes | External (GCS, S3) |
| **Scalability** | Horizontal (services) | Distributed cluster | Kubernetes-native |
| **Best For** | Enterprise teams | Small to medium teams | Kubernetes projects |

## When to Choose Each Platform

### Choose Screwdriver CI if:
- You need a mature, enterprise-grade platform with Yahoo-scale battle testing
- Your team prefers Node.js-based tooling and configuration
- You want flexible executor options (Docker, Kubernetes, Nomad)
- You need multi-SCM support with a unified dashboard

### Choose Agola if:
- You want a Go-based system that can run as a single binary or scale to a cluster
- You value the "runs" model with native fan-in/fan-out task workflows
- You want a quick start with the `agolademo` (includes Gitea)
- Your team prefers declarative, Git-tracked configuration

### Choose Prow if:
- Your infrastructure is already on Kubernetes
- You want GitHub PR-native CI with `/test` comment triggers
- You need automatic PR merging with Tide
- You want to run the same CI system that builds Kubernetes itself

For teams looking at simpler CI/CD alternatives, our [Woodpecker CI vs Drone CI vs Gitea Actions guide](../2026-04-19-woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/) covers lighter-weight options. If you need Kubernetes-native workflows, see our [Tekton vs Argo Workflows vs Jenkins X comparison](../tekton-vs-argo-workflows-vs-jenkins-x-self-hosted-kubernetes-native-cicd-guide-2026/) for alternatives. For portable pipeline engines, [Dagger](../dagger-self-hosted-cicd-pipeline-engine-portable-devops-guide-2026/) offers a different approach.

## FAQ

### Can I run all three platforms on a single server?

Screwdriver CI and Agola both support Docker Compose deployments and can run on a single server with 4+ GB RAM. Prow requires a Kubernetes cluster, which adds significant overhead — it is not suitable for single-server deployments. If you have a small team and limited infrastructure, Agola's single-process mode is the most resource-efficient option.

### Which platform is easiest to set up?

Agola's `agolademo` is the fastest path to a working CI/CD system — it bundles Agola with Gitea in a single Docker Compose file. Screwdriver requires separate configuration of OAuth credentials, database, and multiple services. Prow has the steepest learning curve as it requires Kubernetes knowledge and a running cluster.

### Do these platforms support self-hosted Git servers?

Yes. Screwdriver supports self-hosted GitHub Enterprise and GitLab instances. Agola supports self-hosted Gitea, GitLab, and GitHub Enterprise. Prow primarily targets github.com but can work with GitHub Enterprise Server through the same webhook mechanism.

### How do these handle secrets?

Screwdriver has a built-in secrets plugin with per-pipeline secret storage. Agola supports encrypted variables in its configuration. Prow relies on Kubernetes Secrets mounted into test pods — you manage them through Kubernetes RBAC. For teams needing dedicated secret management, see our [Vault vs Infisical vs Passbolt guide](../2026-04-25-vault-vs-infisical-vs-passbolt-self-hosted-secrets-rotation/).

### Which platform has the most active development?

Screwdriver CI has the most consistent commit activity (last update April 2026) with active maintenance by Yahoo's team. Prow is also actively maintained by the Kubernetes SIGs (last update April 2026). Agola's last commit was in September 2025, but the project is considered stable for production use.

### Can I migrate from GitHub Actions to any of these?

Screwdriver's `screwdriver.yaml` syntax is closest to GitHub Actions — both use step-based job definitions with environment variables. Agola's run model is conceptually different with its fan-in/fan-out task graphs. Prow's configuration is Kubernetes-native and requires the most adaptation from GitHub Actions workflows.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Screwdriver CI vs Agola vs Prow: Self-Hosted CI/CD Platforms 2026",
  "description": "Compare three powerful self-hosted CI/CD platforms: Screwdriver CI (Yahoo), Agola (Sorint.lab), and Prow (Kubernetes SIGs). Deployment guides, feature comparison, and Docker Compose configs for building your own build infrastructure.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
